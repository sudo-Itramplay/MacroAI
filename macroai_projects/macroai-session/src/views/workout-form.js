import { StorageService } from '../storage.js';
import { AuthService } from '../auth.js';
import { Workout } from '../models/workout.js';
import { generateId } from '../utils/helpers.js';
import { getRouter } from '../router.js';

/** @type {Record<string, string>} Sport → display label */
const SPORT_LABELS = {
  swim: 'Swim',
  bike: 'Bike',
  run: 'Run',
};

/**
 * Build the workout form view renderer (create / edit).
 * @param {StorageService} storageService
 * @param {AuthService} authService
 * @returns {function(HTMLElement, Object<string,string>): Promise<void>}
 */
export function createWorkoutForm(storageService, authService) {
  if (!(storageService instanceof StorageService)) {
    throw new TypeError('createWorkoutForm requires a StorageService instance');
  }
  if (!(authService instanceof AuthService)) {
    throw new TypeError('createWorkoutForm requires an AuthService instance');
  }

  /**
   * Escape HTML entities to prevent XSS.
   * @param {string} str
   * @returns {string}
   */
  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  /**
   * Parse query string from the current hash.
   * @returns {Object<string, string>}
   */
  function parseQueryParams() {
    const hash = window.location.hash;
    const qIndex = hash.indexOf('?');
    if (qIndex === -1) return {};

    const params = {};
    const search = hash.slice(qIndex + 1);
    for (const pair of search.split('&')) {
      const [key, value] = pair.split('=');
      if (key) {
        params[decodeURIComponent(key)] = decodeURIComponent(value ?? '');
      }
    }
    return params;
  }

  /**
   * Render the form into the container.
   * @param {HTMLElement} container
   * @param {object} workout — existing workout or empty defaults
   * @param {boolean} isEdit
   * @param {string|null} prefillDate — ISO date string from query param
   */
  function renderForm(container, workout, isEdit, prefillDate) {
    const dateValue = workout.date
      ? workout.date.slice(0, 10)
      : prefillDate ?? new Date().toISOString().slice(0, 10);
    const sportValue = workout.sport ?? '';
    const durationValue = workout.duration != null ? String(workout.duration) : '';
    const distanceValue = workout.distance != null ? String(workout.distance) : '';
    const notesValue = workout.notes ?? '';

    container.innerHTML = `
      <div class="workout-form-view">
        <div class="workout-form-header">
          <h2 class="workout-form-title">${isEdit ? 'Edit Workout' : 'New Workout'}</h2>
        </div>
        <form id="workout-form" class="workout-form" novalidate>
          <div class="form-group">
            <label class="form-label" for="wf-date">Date</label>
            <input class="form-input" id="wf-date" type="date" value="${escapeHtml(dateValue)}" required />
            <span class="form-error" id="wf-date-error"></span>
          </div>
          <div class="form-group">
            <label class="form-label" for="wf-sport">Sport</label>
            <select class="form-input" id="wf-sport" required>
              <option value="" disabled ${sportValue === '' ? 'selected' : ''}>Select sport…</option>
              ${Workout.SPORTS.map(
                (s) =>
                  `<option value="${s}" ${sportValue === s ? 'selected' : ''}>${SPORT_LABELS[s]}</option>`
              ).join('')}
            </select>
            <span class="form-error" id="wf-sport-error"></span>
          </div>
          <div class="form-group">
            <label class="form-label" for="wf-duration">Duration (minutes)</label>
            <input class="form-input" id="wf-duration" type="number" min="1" step="1"
                   value="${escapeHtml(durationValue)}" placeholder="e.g. 45" required />
            <span class="form-error" id="wf-duration-error"></span>
          </div>
          <div class="form-group">
            <label class="form-label" for="wf-distance">Distance (km)</label>
            <input class="form-input" id="wf-distance" type="number" min="0" step="0.1"
                   value="${escapeHtml(distanceValue)}" placeholder="e.g. 5.0" required />
            <span class="form-error" id="wf-distance-error"></span>
          </div>
          <div class="form-group">
            <label class="form-label" for="wf-notes">Notes (optional)</label>
            <textarea class="form-input" id="wf-notes" rows="3"
                      placeholder="How did it go?">${escapeHtml(notesValue)}</textarea>
          </div>
          <div class="form-error form-error--general" id="wf-general-error"></div>
          <div class="workout-form-actions">
            <button class="btn btn-primary" type="submit">
              ${isEdit ? 'Save Changes' : 'Create Workout'}
            </button>
            <button class="btn" type="button" id="wf-cancel">Cancel</button>
          </div>
        </form>
      </div>
    `;
  }

  /**
   * Clear all inline error messages.
   * @param {HTMLElement} container
   */
  function clearErrors(container) {
    container.querySelectorAll('.form-error').forEach((el) => {
      el.textContent = '';
    });
  }

  /**
   * Show an error message under a specific field.
   * @param {HTMLElement} container
   * @param {string} id
   * @param {string} message
   */
  function showError(container, id, message) {
    const el = container.querySelector(`#${id}`);
    if (el) el.textContent = message;
  }

  /**
   * Main render function.
   * @param {HTMLElement} container — the #app element
   * @param {Object<string,string>} params — route params (contains `id` for edit)
   */
  return async function renderWorkoutForm(container, params) {
    const user = await authService.getCurrentUser();
    if (!user) return;

    const isEdit = params && params.id;
    let workout = {};

    if (isEdit) {
      const existing = await storageService.get('workouts', params.id);
      if (!existing) {
        container.innerHTML = `
          <div class="workout-form-view">
            <p class="calendar-empty">Workout not found.</p>
            <div class="workout-form-actions">
              <button class="btn btn-primary" id="wf-back">Back to Calendar</button>
            </div>
          </div>
        `;
        container.querySelector('#wf-back').addEventListener('click', () => {
          getRouter().navigate('#/calendar');
        });
        return;
      }
      workout = existing;
    }

    const prefillDate = isEdit ? null : parseQueryParams().date ?? null;

    renderForm(container, workout, !!isEdit, prefillDate);

    const form = container.querySelector('#workout-form');
    const cancelBtn = container.querySelector('#wf-cancel');

    cancelBtn.addEventListener('click', () => {
      getRouter().navigate('#/calendar');
    });

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      clearErrors(container);

      const dateInput = /** @type {HTMLInputElement} */ (container.querySelector('#wf-date'));
      const sportInput = /** @type {HTMLSelectElement} */ (container.querySelector('#wf-sport'));
      const durationInput = /** @type {HTMLInputElement} */ (container.querySelector('#wf-duration'));
      const distanceInput = /** @type {HTMLInputElement} */ (container.querySelector('#wf-distance'));
      const notesInput = /** @type {HTMLTextAreaElement} */ (container.querySelector('#wf-notes'));

      const dateVal = dateInput.value;
      const sportVal = sportInput.value;
      const durationVal = durationInput.value;
      const distanceVal = distanceInput.value;
      const notesVal = notesInput.value.trim();

      let hasError = false;

      if (!dateVal) {
        showError(container, 'wf-date-error', 'Date is required');
        hasError = true;
      }
      if (!sportVal) {
        showError(container, 'wf-sport-error', 'Please select a sport');
        hasError = true;
      }
      if (!durationVal || Number(durationVal) <= 0) {
        showError(container, 'wf-duration-error', 'Duration must be a positive number');
        hasError = true;
      }
      if (distanceVal === '' || Number(distanceVal) < 0) {
        showError(container, 'wf-distance-error', 'Distance must be zero or a positive number');
        hasError = true;
      }
      if (hasError) return;

      const workoutData = {
        id: isEdit ? params.id : generateId(),
        userId: user.id,
        date: new Date(dateVal + 'T00:00:00').toISOString(),
        sport: sportVal,
        duration: Number(durationVal),
        distance: Number(distanceVal),
        notes: notesVal || undefined,
      };

      const validationErrors = Workout.validate(workoutData);
      if (validationErrors.length > 0) {
        showError(container, 'wf-general-error', validationErrors.join(', '));
        return;
      }

      try {
        await storageService.put('workouts', workoutData);
        getRouter().navigate('#/calendar');
      } catch (err) {
        showError(container, 'wf-general-error', err.message ?? 'Failed to save workout');
      }
    });
  };
}
