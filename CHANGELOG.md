# Changelog

## [Unreleased] — Subprocess CLI Architecture + Session Memory

### Overview
The entire LLM integration layer was rebuilt from API-key-based LangChain bindings to thin **subprocess wrappers** that invoke the local CLI tools you already have installed (Kimi, Claude, OpenCode). This removes all API-key management, quota anxiety, and vendor SDK dependencies. A **session memory persistence layer** was added so multi-step projects survive across process restarts.

---

### Breaking Changes

- **Removed API-key dependencies**
  - Deleted: `langchain-anthropic`, `langchain-openai`, `python-dotenv` from the dependency tree.
  - Deleted: `.env` and `.env.example` are no longer required (kept for backwards compatibility but unused).
  - The system now expects `kimi`, `claude`, and `opencode` binaries to be available in `$PATH`.

- **AgentState expanded**
  - Added `session_id: str` — groups related runs into a named session.
  - Added `memory_context: str` — compressed working memory injected into every prompt so subprocess sessions feel stateful.

---

### Added

#### 1. Subprocess CLI Wrappers (`src/agents.py`)

| Agent | CLI Call | Session Flag | Behaviour |
|-------|----------|--------------|-----------|
| **Kimi** (Architect) | `kimi --quiet --afk --prompt "..."` | `--session <id>` | Final message only, auto-approve, native session resume. |
| **Claude** (Complex) | `claude --print -p "..."` | *injected via prompt* | Non-interactive output. Memory is prepended to the prompt because the Claude CLI does not expose a native session flag in this wrapper. |
| **OpenCode** (Simple) | `opencode run "message"` | `--session <id>` | Non-interactive by default, native session resume. |

#### 2. Session Memory System (`src/agents.py`)

- **`MEMORY_DIR = ".macroai_memory"`** — per-session markdown files are stored here (gitignored).
- **`load_memory(session_id)`** — reads the existing dump on startup.
- **`save_memory(session_id, content)`** — writes the updated dump after `finalize_node`.
- **`_memory_block(ctx)`** — formats the raw dump into an invisible preamble that every agent prompt receives. Agents are instructed to treat it as active context without mentioning they are reading a memory dump.

#### 3. Finalize Node (`finalize_node` in `src/agents.py`)

A new graph node runs **after** both coders (`claude` → `finalize` → `END`, `opencode` → `finalize` → `END`).

It sends a strict system prompt (the *Session Memory Archivist*) to Kimi that forces a compressed `<MEMORY_DUMP>` block containing:

- `[PROJECT_STATE]` — active files, architecture decisions, broken bits.
- `[TASK_STACK]` — done / in-progress / pending.
- `[KEY_DECISIONS]` — rationale for important choices.
- `[SCRATCHPAD]` — debug notes and dead ends.
- `[NEXT_ACTION]` — the single highest-priority next step.

Rules enforced by the prompt:
1. Extreme brevity, dense shorthand.
2. 100 % self-contained — no references to "above" or "earlier".
3. Full file paths and exact identifiers.
4. No markdown outside `<MEMORY_DUMP>`.
5. Merge and update existing memory rather than blind replacement.

#### 4. Graph Flow Update (`src/graph.py`)

```
architect --[complexa]--> claude --> finalize --> END
          --[simple]----> opencode --> finalize --> END
```

The `finalize` node is unconditional after coding; every run ends with a memory snapshot.

#### 5. Entrypoint Resume (`src/main.py`)

```python
session_id = "macroai-session"
initial_state = {
    ...,
    "session_id": session_id,
    "memory_context": load_memory(session_id)  # "" on first run, full dump afterwards
}
```

Changing `session_id` lets you maintain parallel project contexts without collision.

---

### Changed

- **`src/agents.py`**
  - Replaced LangChain `ChatAnthropic` / `ChatOpenAI` / `ChatMoonshot` invocations with `_run_kimi()`, `_run_claude()`, `_run_opencode()`.
  - Every agent node now accepts and injects `memory_context` into its prompt.
  - `_run_kimi()` and `_run_opencode()` accept an optional `session_id` and forward it via `--session`.

- **`src/graph.py`**
  - Added `"finalize"` node.
  - Changed terminal edges from `claude → END` and `opencode → END` to `claude → finalize → END` and `opencode → finalize → END`.

- **`src/main.py`**
  - Imports `load_memory` from `src.agents`.
  - Sets `session_id` in the initial state.
  - Loads previous memory into `memory_context` before invoking the graph.
  - Prints the memory file path on completion.

- **`tests/test_router.py`**
  - Updated `AgentState` fixtures to include `session_id` and `memory_context` keys so they remain valid after the schema expansion.

- **`.gitignore`**
  - Added `.macroai_memory/` to prevent session dumps from being committed.

- **`requirements.txt`**
  - Removed `langchain-anthropic`, `langchain-openai`, `python-dotenv`.
  - Kept only `langgraph>=0.2` and `langchain-core>=0.3`.

---

### Prompts

#### Session Memory Archivist (used by `finalize_node`)

```text
You are the Session Memory Archivist. Your sole job is to compress the entire working context of this session into a dense, self-contained memory packet.

A future AI instance will read ONLY this packet to resume work. It will have zero prior context. This dump IS its context.

Output STRICTLY inside a single <MEMORY_DUMP> ... </MEMORY_DUMP> block. Use this exact internal structure:

[PROJECT_STATE]
- Active files & purposes
- Architecture decisions locked in
- Unfinished / broken components

[TASK_STACK]
- Done: <list>
- In-Progress: <list>
- Pending: <list>

[KEY_DECISIONS]
- <decision> | Rationale: <why>

[SCRATCHPAD]
- Debug notes, hypotheses, dead ends worth remembering

[NEXT_ACTION]
- The single highest-priority next step with full context

RULES:
1. EXTREME BREVITY. Use dense shorthand, abbreviations, and bullet points.
2. NEVER reference "above", "earlier", or "the file I mentioned". This must be 100% self-contained.
3. Include FULL file paths and exact function / class names.
4. No markdown outside <MEMORY_DUMP>. No greetings. No summaries.
5. If an existing memory block is provided below, MERGE and UPDATE it rather than replacing blindly.
```

---

### Migration Notes

If you were using the previous API-key version:

1. **Uninstall obsolete packages:**
   ```bash
   pip uninstall langchain-anthropic langchain-openai python-dotenv
   ```
2. **Ensure CLIs are in `$PATH`:**
   ```bash
   which kimi claude opencode
   ```
3. **Delete old `.env` if desired** — it is no longer read.
4. **Run once** to generate the first memory dump; subsequent runs will automatically resume context.
