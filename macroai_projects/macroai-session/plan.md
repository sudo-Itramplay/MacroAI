Now I have context on the existing scaffold. Let me create the complete plan:

# Project Plan: triathlon-dashboard

## Architecture
React SPA with Vite, using React Router for view switching (Dashboard, Log, Analytics). State managed via custom hooks wrapping localStorage persistence. Chart.js/Recharts for visualization. Existing scaffold provides `useWorkouts` hook with CRUD + filtering + stats, `WorkoutList` component, and constants. Remaining work: TypeScript migration, routing, dashboard/analytics views, workout form, and chart integration.

## Project Structure
- `src/types.ts` — Workout, Filter, Stats type definitions
- `src/data/constants.ts` — Discipline enums, sort options, defaults (migrated)
- `src/hooks/useLocalStorage.ts` — Generic localStorage hook (migrated)
- `src/hooks/useWorkouts.ts` — Workout CRUD, filtering, stats computation (migrated)
- `src/components/Layout.tsx` — App shell with nav sidebar/header
- `src/components/WorkoutList.tsx` — Workout card list (migrated)
- `src/components/WorkoutForm.tsx` — Add/edit workout form
- `src/components/WorkoutFilters.tsx` — Discipline/date/sort filter controls
- `src/components/DashboardStats.tsx` — Summary stat cards
- `src/components/WeeklyVolumeChart.tsx` — Weekly hours bar/line chart
- `src/components/DisciplinePieChart.tsx` — Discipline distribution pie chart
- `src/components/TrendLineChart.tsx` — Distance/duration trends over time
- `src/pages/DashboardPage.tsx` — Dashboard view composing stats + charts
- `src/pages/LogPage.tsx` — Workout log view with filters + form + list
- `src/pages/AnalyticsPage.tsx` — Detailed charts and breakdown view
- `src/App.tsx` — Router setup (migrated)
- `src/main.tsx` — Vite entry point
- `index.html` — HTML shell
- `vite.config.ts` — Vite configuration
- `tsconfig.json` — TypeScript configuration
- `package.json` — Dependencies

## Tasks

### [SIMPLE] ✅ Project scaffolding and config
- **File**: `package.json`, `vite.config.ts`, `tsconfig.json`, `index.html`, `src/main.tsx`
- **Description**: Initialize Vite + React + TypeScript project. Install deps: `react`, `react-dom`, `react-router-dom`, `chart.js`, `react-chartjs-2` (or `recharts`). Create `vite.config.ts` with React plugin, `tsconfig.json` with strict mode, `index.html` with root div, `src/main.tsx` rendering `<App />`.

### [SIMPLE] ✅ Type definitions
- **File**: `src/types.ts`
- **Description**: Define TypeScript interfaces/types: `Workout { id: string; date: string; discipline: Discipline; duration: number; distance: number | null; notes: string | null; intensity: number | null; }`, `Discipline = 'swim' | 'bike' | 'run'`, `WorkoutFilters { discipline: Discipline | null; dateFrom: string | null; dateTo: string | null; sortBy: SortField; sortAsc: boolean; }`, `SortField = 'date' | 'duration' | 'distance'`, `Stats { weeklyHours: Record<string, number>; monthlyHours: Record<string, number>; distanceByDiscipline: Record<Discipline, number>; totalWorkouts: number; totalDuration: number; totalDistance: number; }`.

### [SIMPLE] ✅ Constants and defaults (migrate to TS)
- **File**: `src/data/constants.ts`
- **Description**: Migrate `constants.js` to TypeScript. Export `DISCIPLINES`, `SORT_OPTIONS`, `DEFAULT_FILTERS`, `newWorkout()`. Add `INTENSITY_RANGE = [1, 10]` for RPE scale. Type all exports.

### [SIMPLE] ✅ useLocalStorage hook (migrate to TS)
- **File**: `src/hooks/useLocalStorage.ts`
- **Description**: Migrate to TypeScript as generic `useLocalStorage<T>(key: string, initialValue: T): [T, (value: T | ((prev: T) => T)) => void]`. Lazy JSON.parse on mount, JSON.stringify on set, try-catch fallback.

### [COMPLEX] ✅ useWorkouts hook (migrate to TS + add intensity)
- **File**: `src/hooks/useWorkouts.ts`
- **Description**: Migrate to TypeScript. Add `intensity` field to `addWorkout` and `updateWorkout`. Extend `stats` to include `totalWorkouts`, `totalDuration`, `totalDistance`, and `intensityTrend` (avg RPE per week). Preserve existing `toISOWeek`, `compareValues`, filtering, sorting logic. Return type: `UseWorkoutsReturn`.

### [SIMPLE] ✅ App shell layout
- **File**: `src/components/Layout.tsx`
- **Description**: Create `Layout` component with sidebar nav (Dashboard, Log, Analytics links using React Router `<NavLink>`) and main content area via `<Outlet />`. Responsive: sidebar collapses to top nav on mobile.

### [SIMPLE] ✅ Workout filters component
- **File**: `src/components/WorkoutFilters.tsx`
- **Description**: Filter controls: discipline toggle buttons (swim/bike/run/all), date range inputs (from/to), sort dropdown (date/duration/distance) with asc/desc toggle. Calls `setFilters` from `useWorkouts`.

### [COMPLEX] ✅ Workout form with validation
- **File**: `src/components/WorkoutForm.tsx`
- **Description**: Form for add/edit. Fields: date (date input), discipline (select), distance (number, optional), duration (hours+minutes+seconds inputs or single seconds input), intensity/RPE (1-10 slider/select, optional), notes (textarea, optional). Validation: discipline required, duration > 0 required. On submit calls `addWorkout` or `updateWorkout`. Reset form after add. Pre-fill on edit.

### [SIMPLE] ✅ Workout list component (migrate to TS)
- **File**: `src/components/WorkoutList.tsx`
- **Description**: Migrate existing JSX to TSX. Add intensity/RPE display. Add edit button per workout that opens `WorkoutForm` in edit mode. Type props: `{ workouts: Workout[]; onDelete: (id: string) => void; onEdit: (workout: Workout) => void; }`.

### [COMPLEX] ✅ Dashboard stats cards
- **File**: `src/components/DashboardStats.tsx`
- **Description**: Summary cards: total workouts count, total hours trained, total distance (km), avg RPE. Discipline breakdown mini-cards (swim/bike/run hours + distance). Uses `stats` from `useWorkouts`. Format durations as `Xh Ym`, distances as `X.X km`.

### [COMPLEX] ✅ Weekly volume chart
- **File**: `src/components/WeeklyVolumeChart.tsx`
- **Description**: Bar or line chart showing training hours per week over last 8-12 weeks. X-axis: week labels (W01, W02...). Y-axis: hours. Stacked by discipline (swim/bike/run colors). Uses `stats.weeklyHours`. Implement with Chart.js (`react-chartjs-2`) or Recharts.

### [COMPLEX] ✅ Discipline distribution pie chart
- **File**: `src/components/DisciplinePieChart.tsx`
- **Description**: Pie/donut chart showing % of total training time by discipline. Uses `stats.distanceByDiscipline` or compute duration per discipline from workouts. Legend with discipline labels + colors (swim=blue, bike=green, run=red).

### [COMPLEX] ✅ Trend line chart
- **File**: `src/components/TrendLineChart.tsx`
- **Description**: Line chart showing distance or duration trend over time. X-axis: months or weeks. Y-axis: distance (km) or hours. Multiple lines for each discipline. Toggle between distance/duration view. Uses `stats.monthlyHours` and per-discipline aggregation.

### [SIMPLE] ✅ Dashboard page
- **File**: `src/pages/DashboardPage.tsx`
- **Description**: Compose `DashboardStats`, `WeeklyVolumeChart`, `DisciplinePieChart`. Show recent 5 workouts as a mini-list. Layout: stats row at top, charts in grid below, recent sessions at bottom.

### [SIMPLE] Log page
- **File**: `src/pages/LogPage.tsx`
- **Description**: Compose `WorkoutFilters`, `WorkoutForm` (add mode), `WorkoutList`. Manage `editingWorkout` state for edit mode. Pass `onEdit` to list which sets `editingWorkout` and scrolls to form.

### [SIMPLE] Analytics page
- **File**: `src/pages/AnalyticsPage.tsx`
- **Description**: Full-page charts view: `WeeklyVolumeChart`, `DisciplinePieChart`, `TrendLineChart` with more space. Add discipline filter to scope charts. Summary table of bests (longest workout, highest volume week, etc.).

### [COMPLEX] App router setup
- **File**: `src/App.tsx`
- **Description**: React Router v6 setup. Routes: `/` → `DashboardPage`, `/log` → `LogPage`, `/analytics` → `AnalyticsPage`. All wrapped in `Layout`. `useWorkouts` instantiated once at app level and passed via props or context. Handle initial redirect.