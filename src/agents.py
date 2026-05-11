"""
src/agents.py
=============
Core of the multi-agent system with multi-task planning support.

WHAT IT DOES:
  1. Defines AgentState with task queue, plan, and output directory fields.
  2. Manages session memory and project output directories via MemoryStore.
  3. Implements the nodes:
     - optimizer_node   -> refines the user's raw prompt.
     - planner_node     -> creates a full project plan with [COMPLEX]/[SIMPLE] tasks.
     - scaffolder_node  -> pre-creates directories and empty target files.
     - executor_node    -> dispatches the next pending task to the right coder.
     - complex_coder    -> handles complex tasks.
     - simple_coder     -> handles simple tasks.
     - finalize_node    -> saves compressed memory for next run.

ARCHITECTURE NOTES:
  - All agents use OpenCode CLI with different --model flags per role (SOLID DIP).
  - The planner writes plan.md to the project directory.
  - Coders pass plan.md and memory.md as -f attachments instead of inlining
    them in the prompt — keeps the prompt small and bounded across tasks.
  - Permission mode (Safe/Auto) controls whether opencode writes files itself
    (Auto: native write tool) or returns code as text (Safe: executor writes).

SOLID MAP:
  S (SRP)  -> MemoryStore owns all persistence. Node factories own prompts.
              parse_plan_tasks() is a pure stateless parser.
  O (OCP)  -> New node types can be added by creating a new make_*_node factory
              without modifying existing nodes or the MemoryStore.
  L (LSP)  -> Any AgentClient implementation works in any node factory.
  I (ISP)  -> Node factories only receive the dependencies they actually use.
  D (DIP)  -> Node factories depend on AgentClient and MemoryStore abstractions,
              never on global state or concrete file paths.
"""

import os
import re
from typing import Callable, Optional, TypedDict

from src.clients import AgentClient, is_auto_approve

# =============================================================================
# CONSTANTS
# =============================================================================

MEMORY_DIR = ".macroai_memory"
PROJECTS_DIR = os.getenv("MACROAI_PROJECTS_DIR", os.path.join(os.getcwd(), "macroai_projects"))

# Cap memory_context payload sent to coders (chars). The finalizer uses its
# own larger cap (6000) because it merges/rewrites the dump.
_CODER_MEMORY_CAP = 4000


# =============================================================================
# LOG SINK  (injected by GraphRunner, consumed by node factories via _emit)
# =============================================================================

LogSink = Callable[[str, str, bool], None]
_log_sink: Optional[LogSink] = None


def configure_log_sink(sink: Optional[LogSink]) -> None:
    """Register or clear the log sink. Called by GraphRunner on run start/end."""
    global _log_sink
    _log_sink = sink


def _emit(agent: str, message: str, is_error: bool = False) -> None:
    """Emit a log entry through the registered sink (if any)."""
    if _log_sink is not None:
        _log_sink(agent, message, is_error)


# =============================================================================
# AgentState  (shared state dictionary passed through the LangGraph)
# =============================================================================

class AgentState(TypedDict, total=False):
    """TypedDict with total=False: all fields are optional.

    LangGraph merges partial state updates from each node. A node only needs
    to return the keys it wants to update; missing keys preserve their current
    value. Always use state.get("key", default) — never state["key"].
    """
    project_requirements: str   # Raw or optimized user spec
    current_task: str           # Description of the task being coded
    complexity: str             # "complexa" or "simple" (Catalan, from plan parser)
    generated_code: str         # Code output from the active coder (Safe mode)
    session_id: str             # Session identifier for memory persistence
    memory_context: str         # Compressed memory dump from prior runs
    plan_md: str                # Full markdown plan with [COMPLEX]/[SIMPLE] tasks
    task_index: int             # Current position in the task list
    total_tasks: int            # Total number of tasks in the plan
    target_file: str            # Relative path of the file being generated
    output_dir: str             # Absolute path to the project output directory


# =============================================================================
# HELPERS  (pure functions, no I/O)
# =============================================================================

def _project_dir(session_id: str) -> str:
    """Return the absolute output directory path for a session."""
    return os.path.join(PROJECTS_DIR, session_id)


def _ensure_project_dir(session_id: str) -> str:
    """Create the project directory if needed and return its path."""
    path = _project_dir(session_id)
    os.makedirs(path, exist_ok=True)
    return path


# =============================================================================
# MemoryStore  (SRP: all persistence lives here)
# =============================================================================

class MemoryStore:
    """Encapsulates all file I/O for session memory and plan persistence.

    Responsibilities:
      - Load/save compressed memory dumps (.macroai_memory/<session>.md)
      - Save/update plan.md files in project directories
      - Write per-call memory.md snapshots for coder -f attachments
      - Build the attachment list for coder calls

    Thread-safety: All methods are stateless (no mutable instance state beyond
    constructor args). Safe to call from the ThreadPoolExecutor thread.
    """

    def __init__(
        self,
        memory_dir: str = MEMORY_DIR,
        projects_dir: str = PROJECTS_DIR,
    ) -> None:
        self._memory_dir = memory_dir
        self._projects_dir = projects_dir

    # -- Session memory persistence --

    def _memory_file(self, session_id: str) -> str:
        """Return the path to the session's memory dump file."""
        os.makedirs(self._memory_dir, exist_ok=True)
        return os.path.join(self._memory_dir, f"{session_id}.md")

    def load_memory(self, session_id: str) -> str:
        """Load the compressed memory dump for a session, or '' if none exists."""
        path = self._memory_file(session_id)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def save_memory(self, session_id: str, content: str) -> None:
        """Persist the compressed memory dump to disk."""
        path = self._memory_file(session_id)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    def write_session_memory_file(self, output_dir: str, memory_context: str) -> str | None:
        """Write memory.md into the project dir for -f attachment.

        Returns the absolute path, or None if memory_context is empty.
        """
        if not memory_context or not memory_context.strip() or not output_dir:
            return None
        os.makedirs(output_dir, exist_ok=True)
        path = os.path.join(output_dir, "memory.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(memory_context.strip())
        return path

    # -- Plan file persistence --

    def save_plan(self, output_dir: str, plan_md: str) -> str:
        """Write plan.md to the project directory. Returns the absolute path."""
        plan_path = os.path.join(output_dir, "plan.md")
        os.makedirs(output_dir, exist_ok=True)
        with open(plan_path, "w", encoding="utf-8") as f:
            f.write(plan_md)
        return plan_path

    def update_plan_task_status(self, plan_md: str, task_index: int, status: str) -> str:
        """Mark a task as done/in-progress in the plan markdown.

        Preserves the [COMPLEX]/[SIMPLE] tag so parse_plan_tasks() still finds it.
        Returns the updated markdown string.
        """
        count = 0
        def _replace(m):
            nonlocal count
            if count == task_index:
                count += 1
                complexity_raw = m.group(1)
                title = m.group(2).strip()
                icon = "✅" if status == "done" else "🔄"
                return f"### [{complexity_raw}] {icon} {title}"
            count += 1
            return m.group(0)

        return re.sub(
            r'###\s*\[(COMPLEX|SIMPLE)\]\s*(.+)',
            _replace,
            plan_md
        )

    # -- Coder attachment helpers --

    def coder_attachments(self, state: "AgentState") -> list[str]:
        """Build the -f attachment list for a coder call: plan.md + memory.md.

        Both files live under output_dir. Memory.md is written fresh each call
        so the coder always sees the latest compressed context.
        """
        output_dir = state.get("output_dir", "")
        attachments: list[str] = []
        if not output_dir:
            return attachments

        plan_path = os.path.join(output_dir, "plan.md")
        if os.path.exists(plan_path):
            attachments.append(plan_path)

        memory_path = self.write_session_memory_file(
            output_dir,
            (state.get("memory_context", "") or "")[:_CODER_MEMORY_CAP],
        )
        if memory_path:
            attachments.append(memory_path)

        return attachments


# =============================================================================
# PLAN PARSER  (pure function, no I/O — stateless)
# =============================================================================

_PLAN_TASK_RE = re.compile(
    r'###\s*\[(COMPLEX|SIMPLE)\]\s*(.+?)\n(.*?)(?=\n###\s*\[|$)',
    re.DOTALL
)
_FILE_RE = re.compile(r'\*\*File\*\*:\s*`?([^\s`\n]+)`?')
_DESC_RE = re.compile(r'\*\*Description\*\*:\s*(.+?)(?:\n\*\*|$)', re.DOTALL)


def parse_plan_tasks(plan_md: str) -> list[dict]:
    """Parse the plan markdown into a list of task dicts.

    Each dict has keys: description, complexity ("complexa"|"simple"), target_file.
    The [COMPLEX]/[SIMPLE] tags are mapped to Catalan "complexa"/"simple" internally
    because the router checks `"complexa" in complexity`.
    """
    tasks: list[dict] = []
    for match in _PLAN_TASK_RE.finditer(plan_md):
        complexity_raw = match.group(1).lower()
        title = match.group(2).strip()
        body = match.group(3).strip()

        complexity = "complexa" if complexity_raw == "complex" else "simple"

        file_match = _FILE_RE.search(body)
        target_file = file_match.group(1) if file_match else f"task_{len(tasks):03d}.py"

        desc_match = _DESC_RE.search(body)
        description = desc_match.group(1).strip() if desc_match else title

        tasks.append({
            "description": description,
            "complexity": complexity,
            "target_file": target_file,
        })
    return tasks


# =============================================================================
# PROMPT TEMPLATES
# =============================================================================

FINALIZER_PROMPT = """\
You are the Session Memory Archivist. Your sole job is to compress the entire working context of this session into a dense, self-contained memory packet.

TWO types of coder agents will read this dump in the future:
  - COMPLEX:  handles complex logic, algorithms, integrations, debugging.
  - SIMPLE:   handles boilerplate, data structures, repetitive scaffolding.

Output STRICTLY inside a single <MEMORY_DUMP> ... </MEMORY_DUMP> block. Use this EXACT internal structure:

[PROJECT_STATE]
- Active files: <path> | purpose
- Architecture decisions locked in
- Unfinished / broken components

[TASK_STACK]
- Done: <list>
- In-Progress: <list>
- Pending[COMPLEX]: <tasks that need complex reasoning>
- Pending[SIMPLE]: <tasks that are boilerplate/repetitive>

[KEY_DECISIONS]
- <decision> | Rationale: <why> | Target: COMPLEX|SIMPLE

[SCRATCHPAD]
- Debug notes, hypotheses, dead ends, known failure modes

[NEXT_ACTION]
- Target: COMPLEX|SIMPLE
- Task: <single highest-priority next step with full context>
- Files: <exact paths to touch>
- Signature: <exact function/class name to create or modify>

RULES:
1. EXTREME BREVITY. Dense shorthand, abbreviations, bullet points only.
2. NEVER reference "above", "earlier", or "the file I mentioned". 100% self-contained.
3. Include FULL file paths and exact function/class names.
4. No markdown outside <MEMORY_DUMP>. No greetings. No summaries.
5. Tag every pending task with [COMPLEX] or [SIMPLE] so the router can skip reading.
6. If an existing memory block is provided, MERGE and UPDATE -- do not replace blindly.
"""


PLANNER_PROMPT = """\
You are a Senior Software Architect. Your job is to create a complete implementation plan for the following project specification.

Break the project into atomic, ordered tasks. Each task MUST be tagged as [COMPLEX] or [SIMPLE]:

- [COMPLEX] = algorithms, business logic, integrations, state machines, physics, AI, concurrency.
- [SIMPLE] = data classes, config, enums, boilerplate, scaffolding, simple properties, plain CRUD.

OUTPUT FORMAT (STRICT):
```
# Project Plan: <short-name>

## Architecture
<2-4 sentences about architecture, patterns, key decisions>

## Project Structure
- `<relative/path.py>` - Purpose of the file
- `<relative/path2.py>` - Purpose of the file

## Tasks

### [SIMPLE] Brief task title
- **File**: `<relative/path.py>`
- **Description**: What to implement, classes/functions to create.

### [COMPLEX] Brief task title
- **File**: `<relative/path.py>`
- **Description**: What to implement, algorithm details, edge cases.

(continue for ALL tasks)
```

RULES:
1. Order tasks by dependency: foundational first, dependent later.
2. EVERY task MUST have a target File path.
3. Include ALL files in the Project Structure section.
4. SIMPLE tasks first (data models, config) then COMPLEX (logic, integration).
5. Use exact class/function names in descriptions.
6. Output ONLY the plan, no extra text.
"""


# =============================================================================
# GRAPH NODE FACTORIES  (DIP: each receives its dependencies via parameters)
# =============================================================================

def make_optimizer_node(client: AgentClient):
    """NODE 0: Refines raw user input into a structured spec.

    Uses a fast model (variant=minimal) to rewrite the user's free-text
    requirement into a bullet-point specification suitable for the architect.
    No memory or plan dependencies — only reads project_requirements.
    """

    def optimizer_node(state: AgentState):
        _emit("optimizer", "Optimitzant prompt de l'usuari...")
        message = (
            "You are a prompt engineering specialist. "
            "Rewrite the following raw user requirement into a precise, structured "
            "software specification for an architect AI. "
            "Use bullet points for clarity. Separate functional requirements from "
            "technical constraints. Output ONLY the refined specification:\n\n"
            f"{state['project_requirements']}"
        )
        refined = client.run(message)
        _emit("optimizer", "Prompt optimitzat.")
        return {"project_requirements": refined}

    return optimizer_node


def make_planner_node(client: AgentClient, store: MemoryStore):
    """NODE 1: Creates the full project plan with [COMPLEX]/[SIMPLE] tasks.

    Receives a MemoryStore to persist the plan and load prior session memory.
    Writes plan.md to the output directory and parses task count for logging.
    """

    def planner_node(state: AgentState):
        _emit("architect", "Elaborant pla de projecte (Planner)...")
        session_id = state.get("session_id", "default")
        output_dir = _ensure_project_dir(session_id)

        # Persist memory to disk so the planner reads it via -f if available.
        memory_ctx = (state.get("memory_context", "") or "")[:_CODER_MEMORY_CAP * 2]
        memory_path = store.write_session_memory_file(output_dir, memory_ctx)

        prompt = (
            f"{PLANNER_PROMPT}\n\n"
            f"### PROJECT SPECIFICATION ###\n"
            f"{state['project_requirements']}\n\n"
            f"{'A memory.md from a prior session is attached. Use it as context. ' if memory_path else ''}"
            "Generate the complete plan now."
        )

        files = [memory_path] if memory_path else None
        plan_md = client.run(prompt, files=files)

        plan_path = store.save_plan(output_dir, plan_md)
        tasks = parse_plan_tasks(plan_md)
        total = len(tasks)

        _emit("architect",
              f"Pla creat: {total} tasques ({sum(1 for t in tasks if t['complexity']=='complexa')} complexes, "
              f"{sum(1 for t in tasks if t['complexity']=='simple')} simples)")
        _emit("system", f"Directori: {output_dir}")
        _emit("system", f"Pla guardat a: {plan_path}")

        return {
            "plan_md": plan_md,
            "task_index": 0,
            "total_tasks": total,
            "output_dir": output_dir,
            "current_task": "",
            "complexity": "",
        }

    return planner_node


def make_scaffolder_node():
    """NODE 1.5: Scaffolder (deterministic, no AI call).

    Runs AFTER the planner and BEFORE the executor. Pre-creates the directory
    structure and empty target files declared in the plan. Skips existing files
    (never overwrites). Solves two problems:
      1. opencode's write tool fails when parent dirs don't exist.
      2. Coders consulting sibling files get predictable existence guarantees.

    Designed to be extended (e.g., seed __init__.py, license headers) without
    changing the graph topology.
    """

    def scaffolder_node(state: AgentState):
        output_dir = state.get("output_dir", "")
        plan_md = state.get("plan_md", "")
        if not output_dir or not plan_md:
            _emit("system", "Scaffolder: sense plan o output_dir, saltant.", is_error=True)
            return {}

        tasks = parse_plan_tasks(plan_md)
        created = 0
        skipped = 0
        for task in tasks:
            target = task.get("target_file", "")
            if not target:
                continue
            file_path = os.path.join(output_dir, target)
            os.makedirs(os.path.dirname(file_path) or output_dir, exist_ok=True)
            if os.path.exists(file_path):
                skipped += 1
                continue
            with open(file_path, "a", encoding="utf-8"):
                pass
            created += 1

        _emit("system",
              f"Scaffolding: {created} fitxers creats, {skipped} ja existents.")
        return {}

    return scaffolder_node


def make_executor_node(store: MemoryStore):
    """NODE 2: Task Dispatcher (loops until all tasks are done).

    On entry:
      - If generated_code is present (Safe mode coder return) → write it.
        In Auto mode coders write the file themselves, so generated_code is
        empty and this branch is skipped.
      - Mark the previous task done in plan.md, advance index.
      - Dispatch next task or fall through to finalize.

    Uses MemoryStore to persist plan status updates.
    """

    def executor_node(state: AgentState):
        task_index = state.get("task_index", 0)
        total_tasks = state.get("total_tasks", 0)
        generated = state.get("generated_code", "")
        target = state.get("target_file", "")
        output_dir = state.get("output_dir", "")
        plan_md = state.get("plan_md", "")
        had_active_task = bool(target) and task_index < total_tasks

        # Safe mode: coder returned code text, executor writes it.
        if generated and target and output_dir:
            file_path = os.path.join(output_dir, target)
            os.makedirs(os.path.dirname(file_path) or output_dir, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(generated)
            _emit("system", f"Escrit: {target} ({len(generated)} chars)")

        # Advance the task index whenever we just came back from a coder.
        # (Auto mode: no generated_code, but the coder still ran — detected
        # by the presence of an active target_file.)
        if had_active_task:
            updated = store.update_plan_task_status(plan_md, task_index, "done")
            store.save_plan(output_dir, updated)
            plan_md = updated
            task_index += 1
            if not generated:
                _emit("system", f"Tasca {target} completada (Auto mode).")

        # Dispatch next task
        if task_index < total_tasks:
            tasks = parse_plan_tasks(plan_md)
            if task_index < len(tasks):
                next_task = tasks[task_index]
                _emit("system",
                      f"Tasca {task_index + 1}/{total_tasks} "
                      f"[{'COMPLEX' if next_task['complexity'] == 'complexa' else 'SIMPLE'}]: "
                      f"{next_task['description'][:60]}")
                return {
                    "current_task": next_task["description"],
                    "complexity": next_task["complexity"],
                    "target_file": next_task["target_file"],
                    "task_index": task_index,
                    "plan_md": plan_md,
                    "generated_code": "",
                }

        _emit("system", f"Totes les {total_tasks} tasques completades.")
        return {
            "task_index": task_index,
            "plan_md": plan_md,
            "generated_code": "",
            "target_file": "",
            "complexity": "",
        }

    return executor_node


def _coder_prompt(task: str, target: str, output_dir: str, complexity_label: str, auto_approve: bool) -> str:
    """Build the per-call coder prompt.

    In Auto mode, tells opencode to use its native write tool and reply 'done'.
    In Safe mode, asks for raw code via stdout (executor writes the file).

    The auto_approve parameter is injected by the caller rather than reading
    the global is_auto_approve() — this keeps the function pure and testable.
    """
    if auto_approve:
        return (
            f"Implement this {complexity_label} task by writing the code to "
            f"`{target}` using your write tool.\n\n"
            f"TASK: {task}\n"
            f"TARGET FILE (relative to project root): {target}\n"
            f"PROJECT ROOT: {output_dir}\n\n"
            "The attached `plan.md` is the full project plan; `memory.md` (if "
            "attached) is prior session context. Read them as needed.\n\n"
            "Include ALL imports, type hints and minimal docstrings. Production-ready code. "
            "When the file is written, reply with just 'done'."
        )
    return (
        f"Implement this {complexity_label} task.\n\n"
        f"TASK: {task}\n"
        f"TARGET FILE: {target}\n"
        f"PROJECT DIRECTORY: {output_dir}\n\n"
        "The attached `plan.md` is the full project plan; `memory.md` (if "
        "attached) is prior session context. Read them as needed.\n\n"
        "Output ONLY the complete, production-ready code for this file. "
        "Include ALL imports, type hints and docstrings. "
        "No explanations, no markdown fences — just the raw code."
    )


def make_complex_coder_node(client: AgentClient, store: MemoryStore):
    """NODE 3A: Complex Coder. Algorithms, business logic, integrations.

    Uses a powerful model (full reasoning) for tasks tagged [COMPLEX].
    Reads plan.md and memory.md via -f attachments built by MemoryStore.
    """

    def complex_coder_node(state: AgentState):
        task = state.get("current_task", "")
        target = state.get("target_file", "")
        output_dir = state.get("output_dir", "")

        _emit("complex", f"Codificant [COMPLEX]: {task[:60]}...")
        prompt = _coder_prompt(task, target, output_dir, "COMPLEX", is_auto_approve())
        files = store.coder_attachments(state)

        response = client.run(prompt, files=files, cwd=output_dir or None)
        _emit("complex", f"Completat: {target}")

        # Auto mode: opencode wrote the file; don't echo the response as code.
        generated = "" if is_auto_approve() else response
        return {"generated_code": generated}

    return complex_coder_node


def make_simple_coder_node(client: AgentClient, store: MemoryStore):
    """NODE 3B: Simple Coder. Data classes, config, boilerplate.

    Uses a fast model (variant=minimal) for tasks tagged [SIMPLE].
    Same attachment strategy as complex_coder_node.
    """

    def simple_coder_node(state: AgentState):
        task = state.get("current_task", "")
        target = state.get("target_file", "")
        output_dir = state.get("output_dir", "")

        _emit("simple", f"Codificant [SIMPLE]: {task[:60]}...")
        prompt = _coder_prompt(task, target, output_dir, "SIMPLE", is_auto_approve())
        files = store.coder_attachments(state)

        response = client.run(prompt, files=files, cwd=output_dir or None)
        _emit("simple", f"Completat: {target}")

        generated = "" if is_auto_approve() else response
        return {"generated_code": generated}

    return simple_coder_node


def make_finalize_node(client: AgentClient, store: MemoryStore):
    """NODE 4: Memory Archivist. Compresses session into memory dump.

    Runs after all tasks are done. Sends the full session context to a
    powerful model and asks it to produce a <MEMORY_DUMP> block. The dump
    is persisted via MemoryStore for the next run.
    """

    def finalize_node(state: AgentState):
        _emit("finalizer", "Arxivant memoria de sessio...")
        existing_memory = (state.get("memory_context", "") or "")[:6000]
        plan_md = (state.get("plan_md", "") or "")[:2000]

        prompt = (
            f"{FINALIZER_PROMPT}\n\n"
            f"Session ID: {state.get('session_id', 'default')}\n"
            f"Project: {state['project_requirements'][:500]}\n"
            f"Output directory: {state.get('output_dir', '')}\n"
            f"Plan summary:\n{plan_md}\n\n"
            f"Existing memory to merge/update:\n{existing_memory}\n\n"
            "Produce the updated <MEMORY_DUMP>."
        )

        response = client.run(prompt)

        match = re.search(r'<MEMORY_DUMP>(.*?)</MEMORY_DUMP>', response, re.DOTALL)
        dump = match.group(1).strip() if match else response

        store.save_memory(state.get("session_id", "default"), dump)
        _emit("finalizer", "Memoria guardada al disc.")
        return {"memory_context": dump}

    return finalize_node
