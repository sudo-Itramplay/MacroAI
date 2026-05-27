import { StorageService } from '../storage.js';
import { AuthService } from '../auth.js';
import { Workout } from '../models/workout.js';
import { formatDuration, formatDistance } from '../utils/helpers.js';
import { getRouter } from '../router.js';

/** @type {Record<string, string>} Sport → CSS color */
const SPORT_COLORS = {
  swim: '#3b82f6',
  bike: '#22c55e',
  run: '#ef4444',
};

/** @type {Record<string, string>} Sport → display label */
const SPORT_LABELS = {
  swim: 'Swim',
  bike: 'Bike',
  run: 'Run',
};

/** @type {number} Default rows per page */
const PAGE_SIZE = 20;

/**
 * Build the workout list view renderer with filter/search and pagination.
 * @param {StorageService} storageService
 * @param {AuthService} authService
 * @returns {function(HTMLElement, Object<string,string>): Promise<void>}
 */
export function createWorkoutList(storageService, authService) {
  if (!(storageService instanceof StorageService)) {
    throw new TypeError('createWorkoutList requires a StorageService instance');
  }
  if (!(authService instanceof AuthService)) {
    throw new TypeError('createWorkoutList requires an AuthService instance');
  }

  /** @type {AbortController|null} */
  let abortController = null;

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
   * Format an ISO date string for display.
   * @param {string} isoDate
   * @returns {string}
   */
  function formatDate(isoDate) {
    const d = new Date(isoDate);
    return d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
  }

  /**
   * Truncate a string to a max length with ellipsis.
   * @param {string} str
   * @param {number} [maxLen=40]
   * @returns {string}
   */
  function truncate(str, maxLen = 40) {
    if (!str || str.length <= maxLen) return str ?? '';
    return str.slice(0, maxLen - 1) + '\u2026';
  }

  /**
   * Load workouts for the current user, optionally filtered by date range and sport.
   * @param {string} userId
   * @param {string|null} startDate — ISO date string (YYYY-MM-DD)
   * @param {string|null} endDate — ISO date string (YYYY-MM-DD)
   * @param {string|null} sport — 'swim' | 'bike' | 'run' | null
   * @returns {Promise<object[]>}
   */
  async function loadWorkouts(userId, startDate, endDate, sport) {
    /** @type {object[]} */
    let workouts;

    if (startDate && endDate) {
      const startIso = new Date(startDate + 'T00:00:00').toISOString();
      const endIso = new Date(endDate + 'T23:59:59.999').toISOString();
      workouts = await storageService.queryByRange('workouts', 'userId_date', [userId, startIso], [userId, endIso]);
    } else {
      workouts = await storageService.queryByIndex('workouts', 'userId', userId);
    }

    if (sport) {
      workouts = workouts.filter((w) => w.sport === sport);
    }

    // Sort by date descending
    workouts.sort((a, b) => (a.date > b.date ? -1 : a.date < b.date ? 1 : 0));
    return workouts;
  }

  /**
   * Render the filter bar HTML.
   * @param {object} filters
   * @param {string|null} filters.startDate
   * @param {string|null} filters.endDate
   * @param {string|null} filters.sport
   * @returns {string}
   */
  function renderFilterBar({ startDate, endDate, sport }) {
    return `
      <div class="workout-list-filters">
        <div class="filter-group">
          <label class="form-label" for="wl-start">From</label>
          <input class="form-input" id="wl-start" type="date" value="${escapeHtml(startDate ?? '')}" />
        </div>
        <div class="filter-group">
          <label class="form-label" for="wl-end">To</label>
          <input class="form-input" id="wl-end" type="date" value="${escapeHtml(endDate ?? '')}" />
        </div>
        <div class="filter-group">
          <label class="form-label" for="wl-sport">Sport</label>
          <select class="form-input" id="wl-sport">
            <option value="" ${!sport ? 'selected' : ''}>All sports</option>
            ${Workout.SPORTS.map(
              (s) => `<option value="${s}" ${sport === s ? 'selected' : ''}>${SPORT_LABELS[s]}</option>`
            ).join('')}
          </select>
        </div>
        <div class="filter-group filter-group--actions">
          <button class="btn btn-primary" id="wl-apply" type="button">Apply</button>
          <button class="btn" id="wl-reset" type="button">Reset</button>
        </div>
      </div>
    `;
  }

  /**
   * Render the workout table rows.
   * @param {object[]} workouts — slice for current page
   * @returns {string}
   */
  function renderTableRows(workouts) {
    if (workouts.length === 0) {
      return `<tr><td colspan="6" class="workout-list-empty">No workouts found.</td></tr>`;
    }

    return workouts
      .map(
        (w) => `
        <tr data-id="${w.id}">
          <td>${formatDate(w.date)}</td>
          <td>
            <span class="sport-badge" style="background:${SPORT_COLORS[w.sport] ?? '#6b7280'}">
              ${SPORT_LABELS[w.sport] ?? w.sport}
            </span>
          </td>
          <td>${formatDuration(w.duration)}</td>
          <td>${formatDistance(w.distance)}</td>
          <td class="workout-list-notes">${escapeHtml(truncate(w.notes))}</td>
          <td class="workout-list-actions">
            <button class="btn btn-sm btn-primary wl-edit" data-id="${w.id}" aria-label="Edit">Edit</button>
            <button class="btn btn-sm btn-danger wl-delete" data-id="${w.id}" aria-label="Delete">Delete</button>
          </td>
        </tr>
      `
      )
      .join('');
  }

  /**
   * Render pagination controls.
   * @param {number} totalItems
   * @param {number} currentPage — 0-indexed
   * @returns {string}
   */
  function renderPagination(totalItems, currentPage) {
    const totalPages = Math.ceil(totalItems / PAGE_SIZE);
    if (totalPages <= 1) return '';

    const buttons = [];
    buttons.push(
      `<button class="btn btn-sm wl-page" data-page="${currentPage - 1}" ${currentPage === 0 ? 'disabled' : ''}>&laquo; Prev</button>`
    );

    const startPage = Math.max(0, currentPage - 2);
    const endPage = Math.min(totalPages, currentPage + 3);

    if (startPage > 0) {
      buttons.push(`<button class="btn btn-sm wl-page" data-page="0">1</button>`);
      if (startPage > 1) buttons.push(`<span class="pagination-ellipsis">&hellip;</span>`);
    }

    for (let i = startPage; i < endPage; i++) {
      buttons.push(
        `<button class="btn btn-sm wl-page ${i === currentPage ? 'btn-primary' : ''}" data-page="${i}">${i + 1}</button>`
      );
    }

    if (endPage < totalPages) {
      if (endPage < totalPages - 1) buttons.push(`<span class="pagination-ellipsis">&hellip;</span>`);
      buttons.push(`<button class="btn btn-sm wl-page" data-page="${totalPages - 1}">${totalPages}</button>`);
    }

    buttons.push(
      `<button class="btn btn-sm wl-page" data-page="${currentPage + 1}" ${currentPage >= totalPages - 1 ? 'disabled' : ''}>Next &raquo;</button>`
    );

    return `
      <div class="workout-list-pagination">
        ${buttons.join('')}
        <span class="pagination-info">${totalItems} workout${totalItems !== 1 ? 's' : ''}</span>
      </div>
    `;
  }

  /**
   * Main render function.
   * @param {HTMLElement} container — the #app element
   * @param {Object<string,string>} _params
   */
  return async function renderWorkoutList(container, _params) {
    // Abort any in-flight operations from previous render
    if (abortController) abortController.abort();
    abortController = new AbortController();
    const signal = abortController.signal;

    const user = await authService.getCurrentUser();
    if (!user) return;

    /** @type {{ startDate: string|null, endDate: string|null, sport: string|null }} */
    let filters = { startDate: null, endDate: null, sport: null };
    /** @type {number} */
    let currentPage = 0;
    /** @type {object[]} */
    let allWorkouts = [];

    /**
     * Re-render the table body and pagination based on current state.
     */
    function refreshTable() {
      const tbody = container.querySelector('#wl-tbody');
      const paginationEl = container.querySelector('#wl-pagination');
      if (!tbody) return;

      const start = currentPage * PAGE_SIZE;
      const pageSlice = allWorkouts.slice(start, start + PAGE_SIZE);
      tbody.innerHTML = renderTableRows(pageSlice);
      if (paginationEl) {
        paginationEl.innerHTML = renderPagination(allWorkouts.length, currentPage);
        bindPaginationEvents();
      }
      bindRowEvents();
    }

    /**
     * Bind edit/delete actions on table rows.
     */
    function bindRowEvents() {
      container.querySelectorAll('.wl-edit').forEach((btn) => {
        btn.addEventListener('click', (e) => {
          e.stopPropagation();
          getRouter().navigate(`#/workouts/${btn.dataset.id}/edit`);
        });
      });

      container.querySelectorAll('.wl-delete').forEach((btn) => {
        btn.addEventListener('click', async (e) => {
          e.stopPropagation();
          if (!confirm('Delete this workout? This cannot be undone.')) return;
          try {
            await storageService.delete('workouts', btn.dataset.id);
            allWorkouts = allWorkouts.filter((w) => w.id !== btn.dataset.id);
            // Adjust page if we deleted the last item on the current page
            const totalPages = Math.ceil(allWorkouts.length / PAGE_SIZE);
            if (currentPage >= totalPages && currentPage > 0) currentPage = totalPages - 1;
            refreshTable();
          } catch (err) {
            console.error('Failed to delete workout:', err);
          }
        });
      });
    }

    /**
     * Bind pagination button events.
     */
    function bindPaginationEvents() {
      container.querySelectorAll('.wl-page').forEach((btn) => {
        btn.addEventListener('click', () => {
          const page = Number(btn.dataset.page);
          if (Number.isNaN(page) || page < 0) return;
          const totalPages = Math.ceil(allWorkouts.length / PAGE_SIZE);
          if (page >= totalPages) return;
          currentPage = page;
          refreshTable();
          // Scroll to top of table
          container.querySelector('.workout-list-table-wrap')?.scrollIntoView({ behavior: 'smooth' });
        });
      });
    }

    /**
     * Apply filters and reload data.
     */
    async function applyFilters() {
      const startInput = /** @type {HTMLInputElement} */ (container.querySelector('#wl-start'));
      const endInput = /** @type {HTMLInputElement} */ (container.querySelector('#wl-end'));
      const sportInput = /** @type {HTMLSelectElement} */ (container.querySelector('#wl-sport'));

      filters.startDate = startInput?.value || null;
      filters.endDate = endInput?.value || null;
      filters.sport = sportInput?.value || null;
      currentPage = 0;

      if (signal.aborted) return;
      allWorkouts = await loadWorkouts(user.id, filters.startDate, filters.endDate, filters.sport);
      if (signal.aborted) return;
      refreshTable();
    }

    // Initial render
    container.innerHTML = `
      <div class="workout-list-view">
        <div class="workout-list-header">
          <h2 class="workout-list-title">Workouts</h2>
          <button class="btn btn-primary wl-new" type="button">+ New Workout</button>
        </div>
        ${renderFilterBar(filters)}
        <div class="workout-list-table-wrap">
          <table class="workout-list-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Sport</th>
                <th>Duration</th>
                <th>Distance</th>
                <th>Notes</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody id="wl-tbody">
              <tr><td colspan="6" class="workout-list-empty">Loading\u2026</td></tr>
            </tbody>
          </table>
        </div>
        <div id="wl-pagination"></div>
      </div>
    `;

    // New workout button
    container.querySelector('.wl-new')?.addEventListener('click', () => {
      getRouter().navigate('#/workouts/new');
    });

    // Apply filter button
    container.querySelector('#wl-apply')?.addEventListener('click', () => {
      applyFilters();
    });

    // Reset filters button
    container.querySelector('#wl-reset')?.addEventListener('click', () => {
      filters = { startDate: null, endDate: null, sport: null };
      const startInput = /** @type {HTMLInputElement} */ (container.querySelector('#wl-start'));
      const endInput = /** @type {HTMLInputElement} */ (container.querySelector('#wl-end'));
      const sportInput = /** @type {HTMLSelectElement} */ (container.querySelector('#wl-sport'));
      if (startInput) startInput.value = '';
      if (endInput) endInput.value = '';
      if (sportInput) sportInput.value = '';
      currentPage = 0;
      applyFilters();
    });

    // Enter key on date inputs triggers filter
    ['wl-start', 'wl-end'].forEach((id) => {
      container.querySelector(`#${id}`)?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') applyFilters();
      });
    });

    // Initial data load
    allWorkouts = await loadWorkouts(user.id, null, null, null);
    if (signal.aborted) return;
    refreshTable();
  };
}
