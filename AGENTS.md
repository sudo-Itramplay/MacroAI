# AGENTS.md — MacroAI

## Quick Reference

```bash
# Setup (first time)
./init.sh                    # creates venv, installs deps, checks opencode CLI

# Run
python main_ui.py            # Textual TUI (recommended)
python src/main.py           # CLI mode (minimal)

# Verify before committing
ruff check .                 # linter
bandit -r . -ll -ii          # security
pytest tests/ -v             # tests (must use venv: ./venv/bin/python -m pytest tests/ -v)
```

CI runs these three in order on push/PR to `main`. If any fails, the build fails.

## Architecture

All agents use a single CLI tool (`opencode`) with different `--model` flags. No kimi, no claude binaries.

```
optimizer → planner → executor → {complex|simple} → executor (loop)
                                   executor → finalize → END
```

- **optimizer** — fast model refines raw user input into structured spec
- **planner** — powerful model generates `plan.md` with `[COMPLEX]`/`[SIMPLE]` tasks
- **executor** — dispatches next pending task, writes coder output to files, loops until all tasks done
- **complex** — powerful model handles algorithms, business logic, integrations
- **simple** — fast model handles boilerplate, data classes, scaffolding
- **finalize** — compresses session into `<MEMORY_DUMP>` for next run

The executor writes files, not the coders. Coders return code strings; executor writes to `macroai_projects/<session_id>/<target_file>`.

## Key Files

| File | Purpose |
|------|---------|
| `src/clients.py` | `AgentClient` ABC, `OpenCodeClient`, `ModelConfig`, `AgentFactory` — SOLID DI layer |
| `src/agents.py` | `AgentState`, plan parser, node factories (`make_*_node`), memory persistence |
| `src/graph.py` | `build_graph(factory)` wires nodes + edges, `route_next()` router |
| `src/main.py` | CLI entry point |
| `main_ui.py` | Textual UI entry point |
| `ui/runner.py` | `GraphRunner` — async bridge (ThreadPoolExecutor + asyncio.Queue) |
| `ui/widgets/` | Textual panels: project, log, state, result |

## Gotchas

**Complexity value is `"complexa"` (Catalan), not `"complex"`.**
The plan format uses `[COMPLEX]` in English, but `parse_plan_tasks()` maps it to `"complexa"` internally. The router checks `"complexa" in state.get("complexity", "")`. Don't change this without updating both the parser and router.

**`AgentState` uses `total=False` — all fields are optional.**
Always use `state.get("field", default)` never `state["field"]`. Missing keys return `None` silently.

**`PROJECTS_DIR` is read at import time** (`os.getenv(...)` in `agents.py:34`).
Changing the env var after Python imports the module has no effect. Set it before starting the app.

**`_log_sink` is a module-level global singleton.**
Only one `GraphRunner` can register a sink at a time. `configure_log_sink(None)` in the runner's `finally` block clears it. Fine for single-app use; don't run multiple runners concurrently.

**No `src/__init__.py`.**
`main.py` uses `sys.path.insert(0, ...)` to make `from src.graph import ...` work when run directly. The UI entry (`main_ui.py`) works because it's run from the project root where `src/` is a package.

**`update_plan_task_status()` preserves `[COMPLEX]`/`[SIMPLE]` tags.**
It adds a `✅` marker but keeps the tag so `parse_plan_tasks()` still finds the task. If you break this, the executor loop will think fewer tasks exist and exit early.

**`subprocess.TimeoutExpired` is not caught in `OpenCodeClient.run()`.**
The 180s timeout raises `subprocess.TimeoutExpired` which propagates as a generic exception. `GraphRunner` catches it broadly. If you need specific error messages, catch it in `run()`.

## SOLID Map

| Principle | Where |
|-----------|-------|
| **S** (SRP) | `OpenCodeClient` — one reason to change: opencode CLI interface |
| **O** (OCP) | `AgentFactory` — add roles/models without modifying existing code |
| **L** (LSP) | Any `AgentClient` subclass can replace another (same `run()` contract) |
| **I** (ISP) | `AgentClient` ABC exposes only `run(prompt, session_id)` |
| **D** (DIP) | `build_graph()` receives `AgentFactory`, nodes receive `AgentClient` via injection |

## Configuration

Environment variables (`.env` or shell):

| Variable | Default | Purpose |
|----------|---------|---------|
| `OPENCODE_API_KEY` | — | Required by opencode CLI for authentication |
| `MACROAI_OPTIMIZER_MODEL` | `opencode-go/deepseek-v4-flash` | Fast model for optimizer |
| `MACROAI_ARCHITECT_MODEL` | `opencode-go/deepseek-v4-pro` | Powerful model for planner |
| `MACROAI_COMPLEX_MODEL` | `opencode-go/deepseek-v4-pro` | Powerful model for complex tasks |
| `MACROAI_SIMPLE_MODEL` | `opencode-go/deepseek-v4-flash` | Fast model for simple tasks |
| `MACROAI_FINALIZER_MODEL` | `opencode-go/deepseek-v4-pro` | Powerful model for memory archival |
| `MACROAI_PROJECTS_DIR` | `./macroai_projects` | Base directory for generated project files |

Model format: `provider/model` (e.g. `opencode-go/deepseek-v4-pro`). List available models with `opencode models`.

## Plan Format (strict)

The planner generates this exact structure. The regex parser depends on it:

```markdown
### [COMPLEX] Brief task title
- **File**: `relative/path.py`
- **Description**: What to implement, exact class/function names.

### [SIMPLE] Brief task title
- **File**: `relative/path2.py`
- **Description**: What to implement.
```

- Every task MUST have `### [COMPLEX]` or `### [SIMPLE]` header
- Every task MUST have `**File**:` with a relative path
- `**Description**:` is optional (falls back to title text)
- Order matters: SIMPLE tasks first, COMPLEX after (dependency order)

## Directory Layout

```
.macroai_memory/<session>.md     # session memory (gitignored)
macroai_projects/<session>/      # generated project output
  plan.md                        # the plan with task status markers
  *.py (etc.)                    # generated code files
```
