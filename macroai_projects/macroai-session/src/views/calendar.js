import { Calendar } from '@fullcalendar/core';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import { StorageService } from '../storage.js';
import { AuthService } from '../auth.js';
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

/** Breakpoint (px) below which calendar switches to list view */
const MOBILE_BREAKPOINT = 640;

/**
 * Build a factory that produces the calendar view renderer.
 * @param {StorageService} storageService
 * @param {AuthService} authService
 * @returns {function(HTMLElement, Object<string,string>): void}
 */
export function createCalendarView(storageService, authService) {
  if (!(storageService instanceof StorageService)) {
    throw new TypeError('createCalendarView requires a StorageService instance');
  }
  if (!(authService instanceof AuthService)) {
    throw new TypeError('createCalendarView requires an AuthService instance');
  }

  /** @type {Calendar|null} */
  let calendarInstance = null;

  /** @type {ResizeObserver|null} */
  let resizeObserver = null;

  /** @type {HTMLElement|null} Popover currently open */
  let activePopover = null;

  /**
   * Load all workouts for the current user and map to FullCalendar event objects.
   * @returns {Promise<object[]>}
   */
  async function loadEvents() {
    const user = await authService.getCurrentUser();
    if (!user) return [];

    const workouts = await storageService.queryByIndex('workouts', 'userId', user.id);

    return workouts.map((w) => ({
      id: w.id,
      title: `${SPORT_LABELS[w.sport] ?? w.sport} — ${formatDuration(w.duration)}`,
      start: w.date,
      allDay: true,
      backgroundColor: SPORT_COLORS[w.sport] ?? '#6b7280',
      borderColor: SPORT_COLORS[w.sport] ?? '#6b7280',
      textColor: '#ffffff',
      extendedProps: {
        sport: w.sport,
        duration: w.duration,
        distance: w.distance,
        notes: w.notes ?? '',
      },
    }));
  }

  /**
   * Close and remove the active popover if one exists.
   */
  function closePopover() {
    if (activePopover) {
      activePopover.remove();
      activePopover = null;
    }
  }

  /**
   * Show a detail popover anchored near the clicked event.
   * @param {object} info — FullCalendar event click info
   */
  function showEventPopover(info) {
    closePopover();

    const { event, jsEvent } = info;
    const { sport, duration, distance, notes } = event.extendedProps;

    const popover = document.createElement('div');
    popover.className = 'calendar-popover';
    popover.innerHTML = `
      <div class="calendar-popover__header" style="background:${SPORT_COLORS[sport] ?? '#6b7280'}">
        <span class="calendar-popover__sport">${SPORT_LABELS[sport] ?? sport}</span>
        <button class="calendar-popover__close" aria-label="Close">&times;</button>
      </div>
      <div class="calendar-popover__body">
        <div class="calendar-popover__row">
          <span class="calendar-popover__label">Duration</span>
          <span class="calendar-popover__value">${formatDuration(duration)}</span>
        </div>
        <div class="calendar-popover__row">
          <span class="calendar-popover__label">Distance</span>
          <span class="calendar-popover__value">${formatDistance(distance)}</span>
        </div>
        ${notes ? `<div class="calendar-popover__notes">${escapeHtml(notes)}</div>` : ''}
      </div>
      <div class="calendar-popover__footer">
        <button class="btn btn-sm btn-primary calendar-popover__edit">Edit</button>
        <button class="btn btn-sm btn-danger calendar-popover__delete">Delete</button>
      </div>
    `;

    document.body.appendChild(popover);
    activePopover = popover;

    // Position relative to click
    const rect = info.el.getBoundingClientRect();
    const popRect = popover.getBoundingClientRect();
    let top = rect.bottom + window.scrollY + 8;
    let left = rect.left + window.scrollX;

    // Keep within viewport
    if (left + popRect.width > window.innerWidth - 16) {
      left = window.innerWidth - popRect.width - 16;
    }
    if (top + popRect.height > window.innerHeight + window.scrollY - 16) {
      top = rect.top + window.scrollY - popRect.height - 8;
    }

    popover.style.top = `${top}px`;
    popover.style.left = `${Math.max(8, left)}px`;

    // Close button
    popover.querySelector('.calendar-popover__close').addEventListener('click', (e) => {
      e.stopPropagation();
      closePopover();
    });

    // Edit button → navigate to edit route
    popover.querySelector('.calendar-popover__edit').addEventListener('click', (e) => {
      e.stopPropagation();
      closePopover();
      getRouter().navigate(`#/workouts/${event.id}/edit`);
    });

    // Delete button
    popover.querySelector('.calendar-popover__delete').addEventListener('click', async (e) => {
      e.stopPropagation();
      if (!confirm('Delete this workout?')) return;
      try {
        await storageService.delete('workouts', event.id);
        event.remove();
        closePopover();
      } catch (err) {
        console.error('Failed to delete workout:', err);
      }
    });
  }

  /**
   * Render a fallback table list for small screens.
   * @param {HTMLElement} container
   * @param {object[]} events
   */
  function renderMobileList(container, events) {
    const sorted = [...events].sort((a, b) => (a.start > b.start ? -1 : 1));
    const listEl = container.querySelector('.calendar-mobile-list');
    if (!listEl) return;

    if (sorted.length === 0) {
      listEl.innerHTML = '<p class="calendar-empty">No workouts yet. Tap a date to add one!</p>';
      return;
    }

    listEl.innerHTML = sorted
      .map(
        (ev) => `
        <div class="calendar-list-item" data-id="${ev.id}" style="border-left:4px solid ${ev.backgroundColor}">
          <div class="calendar-list-item__date">${formatEventDate(ev.start)}</div>
          <div class="calendar-list-item__info">
            <span class="calendar-list-item__sport">${ev.title}</span>
            <span class="calendar-list-item__dist">${formatDistance(ev.extendedProps.distance)}</span>
          </div>
        </div>
      `
      )
      .join('');

    listEl.querySelectorAll('.calendar-list-item').forEach((item) => {
      item.addEventListener('click', () => {
        getRouter().navigate(`#/workouts/${item.dataset.id}/edit`);
      });
    });
  }

  /**
   * Main render function.
   * @param {HTMLElement} container — the #app element
   * @param {Object<string,string>} _params
   */
  return async function renderCalendarView(container, _params) {
    // Clean up previous instance
    if (calendarInstance) {
      calendarInstance.destroy();
      calendarInstance = null;
    }
    if (resizeObserver) {
      resizeObserver.disconnect();
      resizeObserver = null;
    }
    closePopover();

    container.innerHTML = `
      <div class="calendar-view">
        <div class="calendar-toolbar">
          <h2 class="calendar-toolbar__title">Workout Calendar</h2>
          <button class="btn btn-primary calendar-toolbar__add" type="button">+ New Workout</button>
        </div>
        <div id="calendar-container"></div>
        <div class="calendar-mobile-list"></div>
      </div>
    `;

    const calendarEl = container.querySelector('#calendar-container');
    const addBtn = container.querySelector('.calendar-toolbar__add');

    addBtn.addEventListener('click', () => {
      getRouter().navigate('#/workouts/new');
    });

    // Close popover on outside click
    document.addEventListener('click', (e) => {
      if (activePopover && !activePopover.contains(e.target) && !e.target.closest('.fc-event')) {
        closePopover();
      }
    });

    // Close popover on Escape
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') closePopover();
    });

    const events = await loadEvents();
    const isMobile = window.innerWidth < MOBILE_BREAKPOINT;

    calendarInstance = new Calendar(calendarEl, {
      plugins: [dayGridPlugin, timeGridPlugin, interactionPlugin],
      initialView: isMobile ? 'dayGridDay' : 'dayGridMonth',
      headerToolbar: {
        left: 'prev,next today',
        center: 'title',
        right: 'dayGridMonth,timeGridWeek,timeGridDay',
      },
      events,
      editable: false,
      selectable: true,
      selectMirror: true,
      dayMaxEvents: 3,
      eventClick(info) {
        info.jsEvent.preventDefault();
        showEventPopover(info);
      },
      dateClick(info) {
        closePopover();
        // Pre-fill date and navigate to new workout form
        const dateStr = info.dateStr;
        getRouter().navigate(`#/workouts/new?date=${encodeURIComponent(dateStr)}`);
      },
      windowResize() {
        if (window.innerWidth < MOBILE_BREAKPOINT) {
          calendarInstance.changeView('dayGridDay');
          calendarEl.style.display = 'none';
          renderMobileList(container, events);
        } else {
          calendarInstance.changeView('dayGridMonth');
          calendarEl.style.display = '';
          const listEl = container.querySelector('.calendar-mobile-list');
          if (listEl) listEl.innerHTML = '';
        }
      },
    });

    calendarInstance.render();

    // Initial mobile check
    if (isMobile) {
      calendarEl.style.display = 'none';
      renderMobileList(container, events);
    }

    // Watch for container resize to toggle views
    resizeObserver = new ResizeObserver(() => {
      const mobile = window.innerWidth < MOBILE_BREAKPOINT;
      if (mobile && calendarInstance.view.type !== 'dayGridDay') {
        calendarInstance.changeView('dayGridDay');
        calendarEl.style.display = 'none';
        renderMobileList(container, events);
      } else if (!mobile && calendarInstance.view.type === 'dayGridDay') {
        calendarInstance.changeView('dayGridMonth');
        calendarEl.style.display = '';
        const listEl = container.querySelector('.calendar-mobile-list');
        if (listEl) listEl.innerHTML = '';
      }
    });
    resizeObserver.observe(container);
  };
}

/**
 * Escape HTML entities to prevent XSS in user-provided text.
 * @param {string} str
 * @returns {string}
 */
function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

/**
 * Format an ISO date string for display in the mobile list.
 * @param {string} isoDate
 * @returns {string}
 */
function formatEventDate(isoDate) {
  const d = new Date(isoDate);
  return d.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' });
}
