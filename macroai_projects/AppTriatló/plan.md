# Project Plan: triathlon-tracker

## Architecture
FastAPI backend with SQLAlchemy ORM persisting to SQLite — zero-config, single-file database. RESTful API exposes CRUD for training sessions plus aggregation endpoints for dashboard stats. Vanilla HTML/CSS/JS frontend consumes the API, uses Chart.js for per-sport trend visualization, and hash-based client-side routing for a single-page feel. All UI text in Catalan.

## Project Structure
- `backend/database.py` - SQLAlchemy engine, session factory, `Base` declarative
- `backend/models.py` - `TrainingSession` ORM model
- `backend/schemas.py` - Pydantic request/response schemas
- `backend/routers/sessions.py` - CRUD + aggregation endpoints
- `backend/main.py` - FastAPI app, CORS middleware, router mount, static file serving
- `frontend/index.html` - Single-page shell: nav tabs, form modal, dashboard panels
- `frontend/css/style.css` - Responsive mobile-first layout, sport color coding
- `frontend/js/api.js` - Fetch wrapper for all backend endpoints
- `frontend/js/app.js` - DOM manipulation, form handling, session list rendering, routing
- `frontend/js/charts.js` - Chart.js initialization and per-sport trend graphs
- `requirements.txt` - Python dependencies
- `README.md` - Setup and run instructions

## Tasks

### [SIMPLE] Database engine and session factory
- **File**: `backend/database.py`
- **Description**: Create SQLAlchemy `engine` pointing to `./triathlon.db`, `SessionLocal` factory, `Base = declarative_base()`. Expose `get_db()` dependency for FastAPI.

### [SIMPLE] TrainingSession ORM model
- **File**: `backend/models.py`
- **Description**: Define `TrainingSession(Base)` with columns: `id` (Integer PK autoincrement), `date` (Date), `sport` (Enum: swim/bike/run), `duration_minutes` (Float), `distance_km` (Float), `notes` (Text, nullable), `created_at` (DateTime), `updated_at` (DateTime). Table name `training_sessions`.

### [SIMPLE] Pydantic request/response schemas
- **File**: `backend/schemas.py`
- **Description**: `SessionCreate(date, sport, duration_minutes, distance_km, notes?)`, `SessionUpdate` (all optional), `SessionResponse` (includes id, created_at, updated_at). `SportEnum` literal `swim|bike|run`. `DashboardStats` schema: `sport`, `total_sessions`, `total_distance_km`, `total_duration_min`, `avg_distance`, `avg_duration`. `TrendPoint` schema: `date`, `distance_km`, `duration_minutes`.

### [COMPLEX] CRUD + aggregation API endpoints
- **File**: `backend/routers/sessions.py`
- **Description**: FastAPI `APIRouter` prefix `/api/sessions`. Endpoints: `POST /` (create), `GET /` (list with optional `?sport=` filter, sort by date desc), `GET /{id}`, `PUT /{id}`, `DELETE /{id}`. `GET /api/dashboard/stats` returns per-sport aggregated totals (sum distance, sum duration, count, averages) via SQLAlchemy `func.sum`/`func.avg` grouped by sport. `GET /api/dashboard/trends?sport=&days=30` returns date-sorted time-series points for charting. Handle 404 on missing session.

### [SIMPLE] FastAPI app setup with CORS and static serving
- **File**: `backend/main.py`
- **Description**: Create `FastAPI(title="Triathlon Tracker")`, add `CORSMiddleware` (allow all origins for local dev), mount sessions router, serve `frontend/` as `StaticFiles` at `/`, mount `index.html` as `HTMLResponse` at root. Include `lifespan` or startup event to call `Base.metadata.create_all(engine)`.

### [SIMPLE] Requirements file
- **File**: `requirements.txt`
- **Description**: Pin `fastapi`, `uvicorn[standard]`, `sqlalchemy`, `pydantic`, `python-multipart`. Add comment for install: `pip install -r requirements.txt`.

### [SIMPLE] HTML single-page shell
- **File**: `frontend/index.html`
- **Description**: Semantic HTML5 structure: header with app title "Triathlon Tracker", nav tabs (Sessions / Dashboard), main content area with two sections toggled by JS. Sessions section: session list container + floating add button triggering modal form. Dashboard section: three sport stat cards (swim/bike/run) + chart canvas containers. Modal with form fields: date input, sport select, duration (min), distance (km), notes textarea. Link Chart.js CDN, `style.css`, `api.js`, `app.js`, `charts.js`.

### [SIMPLE] Responsive CSS styling
- **File**: `frontend/css/style.css`
- **Description**: Mobile-first layout with CSS Grid/Flexbox. Sport color scheme: swim=#3498db, bike=#2ecc71, run=#e74c3c. Card-based session list, responsive stat cards (3-col desktop, 1-col mobile). Modal overlay with centered form. Tab active states. Chart containers with aspect-ratio. Touch-friendly button sizes (min 44px).

### [COMPLEX] Frontend API client module
- **File**: `frontend/js/api.js`
- **Description**: Export `API` object with methods: `getSessions(sport?)`, `getSession(id)`, `createSession(data)`, `updateSession(id, data)`, `deleteSession(id)`, `getDashboardStats()`, `getDashboardTrends(sport, days)`. Each method does `fetch` to `/api/...`, parses JSON, handles errors with try/catch returning `{data, error}` tuple.

### [COMPLEX] Frontend app logic — sessions CRUD + routing
- **File**: `frontend/js/app.js`
- **Description**: On DOMContentLoaded: hash-based routing (`#sessions`, `#dashboard`). `renderSessionList(sport?)`: fetch sessions, build DOM cards with edit/delete buttons, date formatted as `dd/mm/yyyy`. `openModal(session?)`: populate form for create or edit. `handleFormSubmit`: validate, call API create/update, close modal, re-render. `deleteSession(id)`: confirm dialog, call API delete, re-render. Sport filter buttons (Tots/Swim/Bike/Run) that re-render list. Catalan labels: "Afegir sessió", "Editar", "Eliminar", "Desar", "Cancel·lar", "Sensacions".

### [COMPLEX] Dashboard stats aggregation and display
- **File**: `frontend/js/app.js` (shared with above, dashboard section)
- **Description**: `renderDashboard()`: call `getDashboardStats()`, populate three sport cards showing total sessions, total distance (km), total duration (hours:min format), averages. Call `getDashboardTrends()` per sport, pass data to charts module. Handle empty state ("Cap sessió registrada"). Auto-refresh on tab switch.

### [COMPLEX] Chart visualization with Chart.js
- **File**: `frontend/js/charts.js`
- **Description**: `initCharts()` called on dashboard load. Create two Chart.js instances per sport (6 total, or 2 with sport selector): line chart for distance over time, line chart for duration over time. X-axis: dates. Y-axis: values. Sport-specific colors from CSS vars. Responsive config, Catalan axis labels ("Distància (km)", "Durada (min)", "Data"). `updateCharts(trendsData)` destroys and recreates charts with new data. Tooltip with date formatting.

### [SIMPLE] README with setup instructions
- **File**: `README.md`
- **Description**: Sections: Descripció, Requisits (Python 3.10+), Instal·lació (`pip install -r requirements.txt`), Execució (`uvicorn backend.main:app --reload`), Obre `http://localhost:8000`. Brief API docs reference.