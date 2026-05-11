I'll analyze the current project structure and generate the implementation plan.
# Project Plan: Training Log SPA

## Architecture
Single-page web application using vanilla JavaScript with modular ES6 classes, localStorage for persistence, and CSS Grid/Flexbox for responsive mobile-first layout. The app follows a Model-View-Controller pattern with a central `App` controller coordinating between `TrainingStore` (data layer), calendar/dashboard views, and UI components. All text in Catalan (ca-ES).

## Project Structure
- `index.html` - Main HTML shell with semantic structure
- `css/styles.css` - Global styles, CSS variables, responsive grid
- `css/calendar.css` - Calendar-specific styles and discipline colors
- `css/dashboard.css` - Dashboard cards, charts, stats
- `js/app.js` - App controller, routing, initialization
- `js/store.js` - TrainingStore class, localStorage CRUD, export
- `js/models.js` - TrainingSession data class, validation
- `js/views/calendar.js` - CalendarView class, monthly/weekly rendering
- `js/views/dashboard.js` - DashboardView class, stats, charts
- `js/views/log.js` - LogView class, session form, list
- `js/views/filter.js` - FilterView class, discipline toggles
- `js/utils/dates.js` - Date helpers, ca-ES formatting
- `js/utils/charts.js` - Canvas chart rendering (line/bar)
- `js/i18n.js` - Catalan translations, locale config

## Tasks

### [SIMPLE] Project scaffolding and HTML shell
- **File**: `index.html`
- **Description**: Create HTML5 boilerplate with viewport meta, ca-ES lang attribute, semantic sections (header, nav, main, footer), script modules, CSS links. Include `<div id="app">` container.

### [SIMPLE] CSS variables and global styles
- **File**: `css/styles.css`
- **Description**: Define CSS custom properties for colors (swim: blue, bike: green, run: orange), spacing, typography. Mobile-first base styles, utility classes, responsive breakpoints.

### [SIMPLE] Calendar styles and discipline colors
- **File**: `css/calendar.css`
- **Description**: Grid layout for month/week views, day cell styles, discipline color badges, today highlight, responsive calendar grid.

### [SIMPLE] Dashboard styles
- **File**: `css/dashboard.css`
- **Description**: Stat cards grid, chart containers, streak display, responsive stacking for mobile.

### [SIMPLE] Catalan translations and locale
- **File**: `js/i18n.js`
- **Description**: Export `I18n` object with `ca` translations (months, days, disciplines: Natació/Bicicleta/Córrer, UI labels). Date formatting functions using `Intl.DateTimeFormat('ca-ES')`.

### [SIMPLE] Date utility functions
- **File**: `js/utils/dates.js`
- **Description**: Functions: `getMonthDays(year, month)`, `getWeekDays(date)`, `formatDate(date, format)`, `isSameDay(d1, d2)`, `getWeekNumber(date)`. All use ca-ES locale.

### [SIMPLE] TrainingSession data model
- **File**: `js/models.js`
- **Description**: `TrainingSession` class with properties: `id` (uuid), `date` (Date), `discipline` (enum: swim/bike/run), `duration` (minutes), `distance` (km), `intensity` (1-5), `heartRate` (optional bpm), `notes` (string). Validation methods for each field.

### [COMPLEX] TrainingStore with localStorage persistence
- **File**: `js/store.js`
- **Description**: `TrainingStore` class implementing CRUD operations. Methods: `getAll()`, `getById(id)`, `getByDateRange(start, end)`, `getByDiscipline(discipline)`, `save(session)`, `delete(id)`, `exportJSON()`, `exportCSV()`. localStorage key: `training_sessions`. Auto-generate UUIDs. Observable pattern for UI updates.

### [SIMPLE] Filter view component
- **File**: `js/views/filter.js`
- **Description**: `FilterView` class rendering discipline toggle buttons (swim/bike/run/all). Emits `filterChange` event with active disciplines array. Visual state for active/inactive toggles.

### [COMPLEX] Calendar view with month/week modes
- **File**: `js/views/calendar.js`
- **Description**: `CalendarView` class rendering monthly grid (6x7) or weekly view. Methods: `renderMonth(year, month)`, `renderWeek(date)`, `addSession(session)`, `highlightDays(sessions)`. Click day to add/view sessions. Navigation arrows for prev/next. Responsive: week view on mobile, month on desktop.

### [COMPLEX] Dashboard view with stats and charts
- **File**: `js/views/dashboard.js`
- **Description**: `DashboardView` class displaying: total hours/distance per discipline per week/month (stat cards), line chart for volume trends (last 12 weeks), streak tracker (consecutive days with sessions). Canvas-based chart rendering.

### [SIMPLE] Chart utility functions
- **File**: `js/utils/charts.js`
- **Description**: Functions: `drawLineChart(canvas, data, options)`, `drawBarChart(canvas, data, options)`. Support multiple datasets (one per discipline), axis labels, responsive canvas sizing.

### [COMPLEX] Training log form and list view
- **File**: `js/views/log.js`
- **Description**: `LogView` class with form for creating/editing sessions (date picker, discipline select, duration/distance/intensity inputs, notes textarea). Validation feedback. List of recent sessions with edit/delete actions. Mobile-friendly form layout.

### [COMPLEX] App controller and routing
- **File**: `js/app.js`
- **Description**: `App` class initializing store, views, and event listeners. Hash-based routing (#calendar, #dashboard, #log). Coordinates filter changes across views. Handles session CRUD flow (form submit → store → view update). Keyboard shortcuts for quick navigation.

## Dependency Order
1. `index.html`, CSS files, `i18n.js`, `dates.js` (foundational)
2. `models.js`, `store.js` (data layer)
3. `filter.js`, `charts.js` (utilities)
4. `calendar.js`, `dashboard.js`, `log.js` (views)
5. `app.js` (controller, depends on all above)