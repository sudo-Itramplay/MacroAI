import {
  Chart,
  DoughnutController,
  ArcElement,
  BarController,
  BarElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  Legend,
} from 'chart.js';
import { formatDuration, formatDistance, startOfWeek, getWeekNumber } from '../utils/helpers.js';

Chart.register(
  DoughnutController,
  ArcElement,
  BarController,
  BarElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  Legend
);

/** @type {Record<string, string>} */
const SPORT_COLORS = {
  swim: '#3b82f6',
  bike: '#22c55e',
  run: '#ef4444',
};

/** @type {Record<string, string>} */
const SPORT_LABELS = {
  swim: 'Swimming',
  bike: 'Cycling',
  run: 'Running',
};

const WEEKS_SHOWN = 12;

/**
 * @param {import('../storage.js').StorageService} storageService
 * @param {import('../auth.js').AuthService} authService
 * @returns {(container: HTMLElement, params?: object) => Promise<void>}
 */
export function createDashboardView(storageService, authService) {
  if (!storageService || typeof storageService.queryByIndex !== 'function') {
    throw new TypeError('storageService must be a StorageService instance');
  }
  if (!authService || typeof authService.getCurrentUser !== 'function') {
    throw new TypeError('authService must be an AuthService instance');
  }

  /** @type {Chart | null} */
  let doughnutChart = null;
  /** @type {Chart | null} */
  let barChart = null;

  /**
   * @param {object[]} workouts
   * @returns {Record<string, {hours: number, distance: number}>}
   */
  function computeSportTotals(workouts) {
    /** @type {Record<string, {hours: number, distance: number}>} */
    const totals = {};
    for (const sport of Object.keys(SPORT_COLORS)) {
      totals[sport] = { hours: 0, distance: 0 };
    }
    for (const w of workouts) {
      if (!totals[w.sport]) continue;
      totals[w.sport].hours += w.duration / 60;
      totals[w.sport].distance += w.distance;
    }
    return totals;
  }

  /**
   * @param {object[]} workouts
   * @returns {{labels: string[], swim: number[], bike: number[], run: number[]}}
   */
  function computeWeeklyVolume(workouts) {
    const now = new Date();
    const weekData = new Map();

    for (let i = WEEKS_SHOWN - 1; i >= 0; i--) {
      const d = new Date(now);
      d.setDate(d.getDate() - i * 7);
      const key = getWeekNumber(d).toString();
      weekData.set(key, { swim: 0, bike: 0, run: 0 });
    }

    for (const w of workouts) {
      const key = getWeekNumber(new Date(w.date)).toString();
      if (weekData.has(key)) {
        weekData.get(key)[w.sport] += w.duration / 60;
      }
    }

    const labels = [];
    const swim = [];
    const bike = [];
    const run = [];
    for (const [label, data] of weekData) {
      labels.push(`W${label}`);
      swim.push(Math.round(data.swim * 10) / 10);
      bike.push(Math.round(data.bike * 10) / 10);
      run.push(Math.round(data.run * 10) / 10);
    }
    return { labels, swim, bike, run };
  }

  /**
   * @param {object[]} workouts
   * @returns {number}
   */
  function computeStreak(workouts) {
    if (workouts.length === 0) return 0;
    const days = new Set();
    for (const w of workouts) {
      days.add(w.date.slice(0, 10));
    }
    let streak = 0;
    const d = new Date();
    d.setHours(0, 0, 0, 0);
    while (true) {
      const key = d.toISOString().slice(0, 10);
      if (days.has(key)) {
        streak++;
        d.setDate(d.getDate() - 1);
      } else {
        break;
      }
    }
    return streak;
  }

  /**
   * @param {string} str
   * @returns {string}
   */
  function escapeHtml(str) {
    const el = document.createElement('span');
    el.textContent = str;
    return el.innerHTML;
  }

  /**
   * @param {HTMLElement} container
   * @param {object[]} workouts
   */
  function renderStats(container, workouts) {
    const totals = computeSportTotals(workouts);
    const totalHours = workouts.reduce((s, w) => s + w.duration / 60, 0);
    const totalDistance = workouts.reduce((s, w) => s + w.distance, 0);
    const streak = computeStreak(workouts);

    const statsEl = container.querySelector('.dashboard__stats');
    if (!statsEl) return;

    statsEl.innerHTML = `
      <div class="dashboard__stat-card">
        <span class="dashboard__stat-value">${Math.round(totalHours * 10) / 10}h</span>
        <span class="dashboard__stat-label">Total Hours</span>
      </div>
      <div class="dashboard__stat-card">
        <span class="dashboard__stat-value">${formatDistance(totalDistance)}</span>
        <span class="dashboard__stat-label">Total Distance</span>
      </div>
      ${Object.entries(totals)
        .map(
          ([sport, t]) => `
        <div class="dashboard__stat-card dashboard__stat-card--${escapeHtml(sport)}">
          <span class="dashboard__stat-value">${Math.round(t.hours * 10) / 10}h / ${formatDistance(t.distance)}</span>
          <span class="dashboard__stat-label">${escapeHtml(SPORT_LABELS[sport] || sport)}</span>
        </div>`
        )
        .join('')}
      <div class="dashboard__stat-card dashboard__stat-card--streak">
        <span class="dashboard__stat-value">${streak}</span>
        <span class="dashboard__stat-label">Day Streak</span>
      </div>
    `;
  }

  /**
   * @param {HTMLElement} container
   * @param {object[]} workouts
   */
  function renderCharts(container, workouts) {
    const totals = computeSportTotals(workouts);
    const weekly = computeWeeklyVolume(workouts);

    const doughnutCanvas = /** @type {HTMLCanvasElement} */ (
      container.querySelector('#dashboard-doughnut')
    );
    const barCanvas = /** @type {HTMLCanvasElement} */ (
      container.querySelector('#dashboard-bar')
    );

    if (doughnutChart) {
      doughnutChart.destroy();
      doughnutChart = null;
    }
    if (barChart) {
      barChart.destroy();
      barChart = null;
    }

    if (doughnutCanvas) {
      doughnutChart = new Chart(doughnutCanvas, {
        type: 'doughnut',
        data: {
          labels: Object.keys(totals).map((s) => SPORT_LABELS[s] || s),
          datasets: [
            {
              data: Object.values(totals).map((t) => Math.round(t.hours * 10) / 10),
              backgroundColor: Object.keys(totals).map((s) => SPORT_COLORS[s] || '#888'),
              borderWidth: 0,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { position: 'bottom' },
            tooltip: {
              callbacks: {
                label: (ctx) => ` ${ctx.parsed}h`,
              },
            },
          },
        },
      });
    }

    if (barCanvas) {
      barChart = new Chart(barCanvas, {
        type: 'bar',
        data: {
          labels: weekly.labels,
          datasets: [
            {
              label: 'Swim',
              data: weekly.swim,
              backgroundColor: SPORT_COLORS.swim,
            },
            {
              label: 'Bike',
              data: weekly.bike,
              backgroundColor: SPORT_COLORS.bike,
            },
            {
              label: 'Run',
              data: weekly.run,
              backgroundColor: SPORT_COLORS.run,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            x: { stacked: true },
            y: { stacked: true, title: { display: true, text: 'Hours' } },
          },
          plugins: {
            legend: { position: 'bottom' },
            tooltip: {
              callbacks: {
                label: (ctx) => ` ${ctx.dataset.label}: ${ctx.parsed.y}h`,
              },
            },
          },
        },
      });
    }
  }

  /**
   * @param {HTMLElement} container
   * @param {object[]} allWorkouts
   * @param {string} startFilter
   * @param {string} endFilter
   * @param {string} sportFilter
   */
  function applyFiltersAndRender(container, allWorkouts, startFilter, endFilter, sportFilter) {
    let filtered = allWorkouts;
    if (startFilter) {
      filtered = filtered.filter((w) => w.date >= startFilter);
    }
    if (endFilter) {
      const end = endFilter + 'T23:59:59';
      filtered = filtered.filter((w) => w.date <= end);
    }
    if (sportFilter) {
      filtered = filtered.filter((w) => w.sport === sportFilter);
    }
    renderStats(container, filtered);
    renderCharts(container, filtered);
  }

  /**
   * @param {HTMLElement} container
   * @param {object} [_params]
   */
  async function renderDashboardView(container, _params) {
    const user = await authService.getCurrentUser();
    if (!user) return;

    const allWorkouts = await storageService.queryByIndex('workouts', 'userId', user.id);
    allWorkouts.sort((a, b) => a.date.localeCompare(b.date));

    container.innerHTML = `
      <div class="dashboard">
        <div class="dashboard__header">
          <h2 class="dashboard__title">Dashboard</h2>
          <div class="dashboard__filters">
            <label>
              From
              <input type="date" id="dashboard-filter-start" class="dashboard__filter-input" />
            </label>
            <label>
              To
              <input type="date" id="dashboard-filter-end" class="dashboard__filter-input" />
            </label>
            <label>
              Sport
              <select id="dashboard-filter-sport" class="dashboard__filter-input">
                <option value="">All</option>
                <option value="swim">Swim</option>
                <option value="bike">Bike</option>
                <option value="run">Run</option>
              </select>
            </label>
          </div>
        </div>
        <div class="dashboard__stats"></div>
        <div class="dashboard__charts">
          <div class="dashboard__chart-container">
            <h3 class="dashboard__chart-title">Sport Distribution</h3>
            <div class="dashboard__chart-wrapper">
              <canvas id="dashboard-doughnut"></canvas>
            </div>
          </div>
          <div class="dashboard__chart-container">
            <h3 class="dashboard__chart-title">Weekly Volume (Last ${WEEKS_SHOWN} Weeks)</h3>
            <div class="dashboard__chart-wrapper">
              <canvas id="dashboard-bar"></canvas>
            </div>
          </div>
        </div>
      </div>
    `;

    const startInput = /** @type {HTMLInputElement} */ (
      container.querySelector('#dashboard-filter-start')
    );
    const endInput = /** @type {HTMLInputElement} */ (
      container.querySelector('#dashboard-filter-end')
    );
    const sportInput = /** @type {HTMLSelectElement} */ (
      container.querySelector('#dashboard-filter-sport')
    );

    function onFilterChange() {
      applyFiltersAndRender(
        container,
        allWorkouts,
        startInput.value,
        endInput.value,
        sportInput.value
      );
    }

    startInput.addEventListener('change', onFilterChange);
    endInput.addEventListener('change', onFilterChange);
    sportInput.addEventListener('change', onFilterChange);

    applyFiltersAndRender(container, allWorkouts, '', '', '');
  }

  return renderDashboardView;
}
