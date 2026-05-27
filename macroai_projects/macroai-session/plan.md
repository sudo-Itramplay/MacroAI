Here's the complete implementation plan:

---

# Project Plan: triathlon-tracker

## Architecture
Single-page app (vanilla JS + Vite) with client-side routing. All data persists in IndexedDB via a thin `StorageService` abstraction. FullCalendar renders the calendar view; Chart.js powers the dashboard. Auth is simulated (hashed passwords stored locally, session via sessionStorage). No backend — fully offline-capable.

## Project Structure
- `index.html` — Shell HTML with nav + view containers
- `src/main.js` — App entry: router init, auth guard
- `src/router.js` — Hash-based SPA router (`#/login`, `#/calendar`, `#/dashboard`, etc.)
- `src/storage.js` — IndexedDB wrapper: `StorageService` class (CRUD for users, workouts)
- `src/auth.js` — `AuthService`: register, login, logout, session check
- `src/models/user.js` — `User` class (id, username, email, passwordHash, createdAt)
- `src/models/workout.js` — `Workout` class (id, userId, date, sport, duration, distance, notes)
- `src/views/login.js` — Login/register form rendering + handlers
- `src/views/calendar.js` — FullCalendar integration, workout display on grid
- `src/views/dashboard.js` — Chart.js charts, summary stats, streaks
- `src/views/workout-form.js` — Create/edit workout modal or form
- `src/views/workout-list.js` — Filterable/searchable workout table
- `src/utils/validators.js` — Email regex, non-empty string, date validation
- `src/utils/helpers.js` — Format duration, compute weekly volume, streak calc
- `styles.css` — Responsive CSS (flexbox/grid), mobile-first
- `package.json` — Dependencies: vite, fullcalendar, chart.js

## Tasks

### [SIMPLE] ✅ Project scaffolding and dependencies
- **File**: `package.json`
- **Description**: Create `package.json` with vite as dev dependency, fullcalendar (`@fullcalendar/core`, `@fullcalendar/daygrid`, `@fullcalendar/timegrid`, `@fullcalendar/interaction`), and `chart.js`. Add `dev`, `build` scripts.

### [SIMPLE] ✅ Shell HTML and base styles
- **File**: `index.html`, `styles.css`
- **Description**: `index.html` with `<nav>`, `<main id="app">`, script tag (type=module). `styles.css` with CSS reset, responsive layout (mobile-first flexbox/grid), nav styling, form styling, modal overlay, table styles.

### [SIMPLE] ✅ User model
- **File**: `src/models/user.js`
- **Description**: `User` class with fields: `id` (string UUID), `username` (string, non-empty), `email` (string, email regex validated), `passwordHash` (string), `createdAt` (ISO string). Include `static validate(user)` returning error array.

### [SIMPLE] ✅ Workout model
- **File**: `src/models/workout.js`
- **Description**: `Workout` class with fields: `id` (string UUID), `userId` (string), `date` (ISO string), `sport` (enum: `'swim'`, `'bike'`, `'run'`), `duration` (number, minutes), `distance` (number, km), `notes` (string, optional). Include `static validate(workout)` and `static SPORTS` enum constant.

### [SIMPLE] ✅ Validators utility
- **File**: `src/utils/validators.js`
- **Description**: Export `isValidEmail(str)` using RFC-ish regex, `isNonEmpty(str)`, `isValidDate(str)` (ISO parse check), `isPositiveNumber(n)`. Pure functions, no side effects.

### [SIMPLE] ✅ Helper utilities
- **File**: `src/utils/helpers.js`
- **Description**: Export `generateId()` (crypto.randomUUID or fallback), `formatDuration(minutes)` → `"1h 23m"`, `formatDistance(km)` → `"12.5 km"`, `getWeekNumber(date)`, `startOfWeek(date)`, `endOfWeek(date)`.

### [COMPLEX] ✅ IndexedDB storage service
- **File**: `src/storage.js`
- **Description**: `StorageService` class wrapping IndexedDB with two object stores: `users` (keyPath: `id`, index on `email`) and `workouts` (keyPath: `id`, index on `userId`, `date`, `sport`). Methods: `init()` → opens DB (versioned migrations), `put(store, item)`, `get(store, id)`, `getAll(store)`, `delete(store, id)`, `queryByIndex(store, indexName, value)`, `queryByRange(store, indexName, lower, upper)`. Returns Promises. Handle DB version upgrades for schema changes.

### [COMPLEX] ✅ Auth service
- **File**: `src/auth.js`
- **Description**: `AuthService` class depending on `StorageService`. Methods: `register(username, email, password)` → validate, hash password (SHA-256 via SubtleCrypto), check email uniqueness, store user, return user. `login(email, password)` → lookup by email index, hash input, compare, store session in sessionStorage. `logout()` → clear sessionStorage. `getCurrentUser()` → read sessionStorage, fetch user from DB. `isLoggedIn()` → boolean.

### [COMPLEX] ✅ Hash-based SPA router
- **File**: `src/router.js`
- **Description**: `Router` class. Listens on `hashchange`. Route table maps `#/login`, `#/calendar`, `#/dashboard`, `#/workouts/new`, `#/workouts/:id/edit` → view render functions. Each view function receives the `#app` container and route params. Auth guard: redirect to `#/login` if not logged in (except login route). Export singleton `router`.

### [SIMPLE] ✅ Login/register view
- **File**: `src/views/login.js`
- **Description**: `renderLoginView(container)` function. Renders tabbed form (Login | Register). Login: email + password fields, submit → `AuthService.login()` → redirect `#/calendar`. Register: username + email + password + confirm, validate, submit → `AuthService.register()` → auto-login. Show inline validation errors. Responsive layout.

### [COMPLEX] ✅ Calendar view with FullCalendar
- **File**: `src/views/calendar.js`
- **Description**: `renderCalendarView(container)` function. Imports FullCalendar core + dayGridMonth + timeGridWeek + timeGridDay + interaction plugin. Loads workouts for current user from `StorageService`, maps to FullCalendar events (color-coded by sport: swim=blue, bike=green, run=red). Click event → show detail popover or navigate to edit. Date click → open new workout form with pre-filled date. Responsive: switch to list view on small screens. Handle month/week/day toggle.

### [COMPLEX] ✅ Dashboard view with Chart.js
- **File**: `src/views/dashboard.js`
- **Description**: `renderDashboardView(container)` function. Computes: total hours per sport, total distance per sport, weekly volume (last 12 weeks stacked bar chart), current streak (consecutive days with workouts). Renders 4 summary stat cards + 2 Chart.js canvases (doughnut for sport distribution, stacked bar for weekly volume). Responsive grid layout. Recomputes on date range filter change.

### [COMPLEX] ✅ Workout form (create/edit)
- **File**: `src/views/workout-form.js`
- **Description**: `renderWorkoutForm(container, workoutId?)` function. If `workoutId` provided, load existing workout for edit; otherwise create new. Fields: date (date input), sport (select: swim/bike/run), duration (number input, minutes), distance (number input, km), notes (textarea). Validate on submit via `Workout.validate()`. On save → `StorageService.put()` → redirect to calendar. Cancel → back to calendar.

### [COMPLEX] ✅ Workout list with filter/search
- **File**: `src/views/workout-list.js`
- **Description**: `renderWorkoutList(container)` function. Renders filterable table: date range picker (start/end date inputs), sport dropdown filter (all/swim/bike/run). Query `StorageService` by index range (`userId` + `date` range + optional `sport`). Table columns: date, sport (badge), duration, distance, notes (truncated), actions (edit/delete). Sort by date descending. Pagination or virtual scroll for large datasets. Delete with confirmation.

### [SIMPLE] ✅ App entry point and router init
- **File**: `src/main.js`
- **Description**: Import `StorageService`, `AuthService`, `Router`, all views. On DOMContentLoaded: init StorageService (async `open()`), wire routes to view render functions, start router. Show loading state until DB ready.

---

This plan orders 8 SIMPLE tasks (models, config, UI scaffolding) before 5 COMPLEX tasks (storage, auth, routing, calendar, dashboard). Each task targets specific files with concrete class/function names.