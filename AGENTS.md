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
optimizer → planner → scaffolder → executor → {complex|simple} → executor (loop)
                                                executor → finalize → END
```

- **optimizer** — fast model refines raw user input into structured spec
- **planner** — powerful model generates `plan.md` with `[COMPLEX]`/`[SIMPLE]` tasks
- **scaffolder** — deterministic (no AI), pre-creates directory tree and empty target files declared in the plan; skips existing files
- **executor** — dispatches next pending task, writes coder output to files (Safe mode only), loops until all tasks done
- **complex** — powerful model handles algorithms, business logic, integrations
- **simple** — fast model handles boilerplate, data classes, scaffolding
- **finalize** — compresses session into `<MEMORY_DUMP>` for next run

The executor writes files, not the coders. Coders return code strings; executor writes to `macroai_projects/<session_id>/<target_file>`.

## Key Files

| File | Purpose |
|------|---------|
| `src/clients.py` | `AgentClient` ABC, `OpenCodeClient`, `ModelConfig`, `AgentFactory` — SOLID DI layer |
| `src/agents.py` | `AgentState`, plan parser, node factories (`make_*_node`, including `make_scaffolder_node`), memory persistence |
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

**`subprocess.TimeoutExpired` is now caught in `OpenCodeClient.run()`.**
A clear error with the model name and duration is raised. Default timeout is 600s, configurable via `MACROAI_TIMEOUT`.

**`--continue` is NOT used.**
Each `opencode run` is independent. Carrying conversation history across all coder calls via `--continue` caused unbounded context growth (50K+ tokens by task 5–10) and timeouts. Context the coders need is now passed via `-f plan.md` and `-f memory.md` at call time (see `_coder_attachments` in `agents.py`).

**`--session` is NOT passed to opencode CLI.**
The opencode `--session` flag requires an existing session ID (`ses_abc123`), not a custom string. Cross-call continuity is handled by MacroAI's memory system (`memory.md` + plan attachments), not opencode's native sessions.

**Permission modes: Safe (default) vs Auto.**
Toggled at runtime via `set_auto_approve(bool)` in `clients.py`, surfaced in the UI by the `a` keybinding and the `[SAFE]/[AUTO]` indicator in the StatePanel/subtitle.
- **Safe**: opencode runs without `--dangerously-skip-permissions`. Coders return code as text; the executor writes the file. Fully headless, no permission prompts.
- **Auto**: opencode receives `--dangerously-skip-permissions` and `--dir <output_dir>`. Coders are told to use opencode's native write tool; the prompt asks for `'done'` as the response. Faster (smaller responses) but trusts opencode to not touch anything outside `output_dir`.

The mode resets to Safe on every UI start (no persistence). Coders pick the right prompt via `is_auto_approve()` in `agents.py:_coder_prompt`; the executor only writes a file when `generated_code` is non-empty (i.e. Safe mode).

**`--variant minimal` on fast roles.**
`AgentFactory.create_optimizer()` and `create_simple_coder()` set `variant="minimal"` for lower reasoning effort on simple tasks. Architect, complex coder, and finalizer get full reasoning.

**memory.md is regenerated each call.**
`_write_session_memory_file()` writes the (truncated, 4000-char) memory dump into `output_dir/memory.md` before each coder call so opencode can read it via `-f`. The canonical store is still `.macroai_memory/<session>.md` — `output_dir/memory.md` is just a per-call reflection.

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
| `MACROAI_TIMEOUT` | `600` | Max seconds per opencode call (increase if tasks time out) |

### UI keybindings

| Key | Action |
|-----|--------|
| `Ctrl+R` | Run the graph with the current input |
| `Ctrl+L` | Clear the log panel |
| `a` | Toggle Safe/Auto permission mode |
| `Q` | Quit |

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
