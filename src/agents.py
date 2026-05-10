"""
src/agents.py
=============
Core of the multi-agent system with multi-task planning support.

WHAT IT DOES:
  1. Defines AgentState with task queue, plan, and output directory fields.
  2. Manages session memory and project output directories.
  3. Implements the nodes:
     - optimizer_node   -> refines the user's raw prompt.
     - planner_node     -> creates a full project plan with [COMPLEX]/[SIMPLE] tasks.
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
"""

import os
import re
from typing import Callable, Optional, TypedDict

from src.clients import AgentClient, is_auto_approve

# =============================================================================
# DIRECTORIES
# =============================================================================
MEMORY_DIR = ".macroai_memory"
PROJECTS_DIR = os.getenv("MACROAI_PROJECTS_DIR", os.path.join(os.getcwd(), "macroai_projects"))

# Cap memory_context payload sent to coders (chars). The finalizer uses its
# own larger cap (6000) because it merges/rewrites the dump.
_CODER_MEMORY_CAP = 4000


def _project_dir(session_id: str) -> str:
    return os.path.join(PROJECTS_DIR, session_id)


def _ensure_project_dir(session_id: str) -> str:
    path = _project_dir(session_id)
    os.makedirs(path, exist_ok=True)
    return path


# =============================================================================
# LOG SINK
# =============================================================================
LogSink = Callable[[str, str, bool], None]
_log_sink: Optional[LogSink] = None


def configure_log_sink(sink: Optional[LogSink]) -> None:
    global _log_sink
    _log_sink = sink


def _emit(agent: str, message: str, is_error: bool = False) -> None:
    if _log_sink is not None:
        _log_sink(agent, message, is_error)


# =============================================================================
# AgentState
# =============================================================================
class AgentState(TypedDict, total=False):
    project_requirements: str
    current_task: str
    complexity: str
    generated_code: str
    session_id: str
    memory_context: str
    plan_md: str
    task_index: int
    total_tasks: int
    target_file: str
    output_dir: str


# =============================================================================
# MEMORY PERSISTENCE
# =============================================================================
def _memory_file(session_id: str) -> str:
    os.makedirs(MEMORY_DIR, exist_ok=True)
    return os.path.join(MEMORY_DIR, f"{session_id}.md")


def load_memory(session_id: str) -> str:
    path = _memory_file(session_id)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def save_memory(session_id: str, content: str) -> None:
    path = _memory_file(session_id)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def _write_session_memory_file(output_dir: str, memory_context: str) -> str | None:
    """
    Persist the session memory into the project dir as memory.md so it can
    be passed via -f. Returns the absolute path or None if memory is empty.
    """
    if not memory_context or not memory_context.strip() or not output_dir:
        return None
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, "memory.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(memory_context.strip())
    return path


def _coder_attachments(state: "AgentState") -> list[str]:
    """
    Build the list of -f attachments for a coder call: plan.md and memory.md
    (if present). Both live under output_dir.
    """
    output_dir = state.get("output_dir", "")
    attachments: list[str] = []
    if not output_dir:
        return attachments

    plan_path = os.path.join(output_dir, "plan.md")
    if os.path.exists(plan_path):
        attachments.append(plan_path)

    memory_path = _write_session_memory_file(
        output_dir,
        (state.get("memory_context", "") or "")[:_CODER_MEMORY_CAP],
    )
    if memory_path:
        attachments.append(memory_path)

    return attachments


# =============================================================================
# PLAN PARSER
# =============================================================================
_PLAN_TASK_RE = re.compile(
    r'###\s*\[(COMPLEX|SIMPLE)\]\s*(.+?)\n(.*?)(?=\n###\s*\[|$)',
    re.DOTALL
)
_FILE_RE = re.compile(r'\*\*File\*\*:\s*`?([^\s`\n]+)`?')
_DESC_RE = re.compile(r'\*\*Description\*\*:\s*(.+?)(?:\n\*\*|$)', re.DOTALL)


def parse_plan_tasks(plan_md: str) -> list[dict]:
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
# PLAN FILE PERSISTENCE
# =============================================================================
def save_plan(output_dir: str, plan_md: str) -> str:
    plan_path = os.path.join(output_dir, "plan.md")
    os.makedirs(output_dir, exist_ok=True)
    with open(plan_path, "w", encoding="utf-8") as f:
        f.write(plan_md)
    return plan_path


def update_plan_task_status(plan_md: str, task_index: int, status: str) -> str:
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


# =============================================================================
# FINALIZER PROMPT
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


# =============================================================================
# PLANNER PROMPT
# =============================================================================
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
# GRAPH NODE FACTORIES
# =============================================================================

def make_optimizer_node(client: AgentClient):
    """NODE 0: Refines raw user input into a structured spec."""

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


def make_planner_node(client: AgentClient):
    """NODE 1: Creates the full project plan with [COMPLEX]/[SIMPLE] tasks."""

    def planner_node(state: AgentState):
        _emit("architect", "Elaborant pla de projecte (Planner)...")
        session_id = state.get("session_id", "default")
        output_dir = _ensure_project_dir(session_id)

        # Persist memory to disk so the planner reads it via -f if available.
        memory_ctx = (state.get("memory_context", "") or "")[:_CODER_MEMORY_CAP * 2]
        memory_path = _write_session_memory_file(output_dir, memory_ctx)

        prompt = (
            f"{PLANNER_PROMPT}\n\n"
            f"### PROJECT SPECIFICATION ###\n"
            f"{state['project_requirements']}\n\n"
            f"{'A memory.md from a prior session is attached. Use it as context. ' if memory_path else ''}"
            "Generate the complete plan now."
        )

        files = [memory_path] if memory_path else None
        plan_md = client.run(prompt, files=files)

        plan_path = save_plan(output_dir, plan_md)
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


def make_executor_node():
    """
    NODE 2: Task Dispatcher.

    On entry:
      - If generated_code is present (Safe mode coder return) → write it.
        In Auto mode coders write the file themselves, so generated_code is
        empty and this branch is skipped.
      - Mark the previous task done in plan.md, advance index.
      - Dispatch next task or fall through to finalize.
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
            updated = update_plan_task_status(plan_md, task_index, "done")
            save_plan(output_dir, updated)
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


def _coder_prompt(task: str, target: str, output_dir: str, complexity_label: str) -> str:
    """Build the per-call coder prompt. Auto mode tells opencode to write the
    file with its native tool; Safe mode asks for raw code via stdout."""
    if is_auto_approve():
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


def make_complex_coder_node(client: AgentClient):
    """NODE 3A: Complex Coder. Algorithms, business logic, integrations."""

    def complex_coder_node(state: AgentState):
        task = state.get("current_task", "")
        target = state.get("target_file", "")
        output_dir = state.get("output_dir", "")

        _emit("complex", f"Codificant [COMPLEX]: {task[:60]}...")
        prompt = _coder_prompt(task, target, output_dir, "COMPLEX")
        files = _coder_attachments(state)

        response = client.run(prompt, files=files, cwd=output_dir or None)
        _emit("complex", f"Completat: {target}")

        # Auto mode: opencode wrote the file; don't echo the response as code.
        generated = "" if is_auto_approve() else response
        return {"generated_code": generated}

    return complex_coder_node


def make_simple_coder_node(client: AgentClient):
    """NODE 3B: Simple Coder. Data classes, config, boilerplate."""

    def simple_coder_node(state: AgentState):
        task = state.get("current_task", "")
        target = state.get("target_file", "")
        output_dir = state.get("output_dir", "")

        _emit("simple", f"Codificant [SIMPLE]: {task[:60]}...")
        prompt = _coder_prompt(task, target, output_dir, "SIMPLE")
        files = _coder_attachments(state)

        response = client.run(prompt, files=files, cwd=output_dir or None)
        _emit("simple", f"Completat: {target}")

        generated = "" if is_auto_approve() else response
        return {"generated_code": generated}

    return simple_coder_node


def make_finalize_node(client: AgentClient):
    """NODE 4: Memory Archivist. Compresses session into memory dump."""

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

        save_memory(state.get("session_id", "default"), dump)
        _emit("finalizer", "Memoria guardada al disc.")
        return {"memory_context": dump}

    return finalize_node
