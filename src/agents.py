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
     - complex_coder    -> handles complex tasks, writes to file.
     - simple_coder     -> handles simple tasks, writes to file.
     - finalize_node    -> saves compressed memory for next run.

ARCHITECTURE NOTES:
  - All agents use OpenCode CLI with different --model flags per role (SOLID DIP).
  - The planner writes plan.md to the project directory.
  - The executor loops until all tasks are done, then routes to finalize.
  - Each coder writes its output to the target file in the project folder.
"""

import os
import re
from typing import Callable, Optional, TypedDict

from src.clients import AgentClient

# =============================================================================
# DIRECTORIES
# =============================================================================
MEMORY_DIR = ".macroai_memory"
PROJECTS_DIR = os.getenv("MACROAI_PROJECTS_DIR", os.path.join(os.getcwd(), "macroai_projects"))


def _project_dir(session_id: str) -> str:
    """Absolute path to the project output directory for a session."""
    return os.path.join(PROJECTS_DIR, session_id)


def _ensure_project_dir(session_id: str) -> str:
    """Create (if needed) and return the project output directory."""
    path = _project_dir(session_id)
    os.makedirs(path, exist_ok=True)
    return path


# =============================================================================
# LOG SINK -- Observability mechanism for the UI (optional)
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
# AgentState -- The shared notebook that every node reads and writes
# =============================================================================
class AgentState(TypedDict, total=False):
    project_requirements: str
    current_task: str
    complexity: str
    generated_code: str
    session_id: str
    memory_context: str
    # Multi-task planning
    plan_md: str           # Full project plan in markdown
    task_index: int        # Current task position (0-based)
    total_tasks: int       # Total number of tasks in the plan
    target_file: str       # Relative path for current task's output
    output_dir: str        # Absolute project output directory


# =============================================================================
# MEMORY PERSISTENCE LAYER
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


# =============================================================================
# MEMORY INJECTION HELPER
# =============================================================================
def _memory_block(ctx: str) -> str:
    if not ctx or not ctx.strip():
        return ""
    return (
        "\n\n--- RESUMED SESSION MEMORY ---\n"
        f"{ctx.strip()}\n"
        "--- END MEMORY ---\n"
        "Treat the above memory as your active working context. "
        "Do NOT mention you are reading a memory dump; just use the facts."
    )


# =============================================================================
# PLAN PARSER -- Extracts structured tasks from plan.md
# =============================================================================
_PLAN_TASK_RE = re.compile(
    r'###\s*\[(COMPLEX|SIMPLE)\]\s*(.+?)\n(.*?)(?=\n###\s*\[|$)',
    re.DOTALL
)
_FILE_RE = re.compile(r'\*\*File\*\*:\s*`?([^\s`\n]+)`?')
_DESC_RE = re.compile(r'\*\*Description\*\*:\s*(.+?)(?:\n\*\*|$)', re.DOTALL)


def parse_plan_tasks(plan_md: str) -> list[dict]:
    """
    Parse a plan.md string into a list of task dicts.

    Each task dict has:
        description: str   -- what to implement
        complexity: str    -- "complexa" or "simple"
        target_file: str   -- relative path to write to
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
# PLAN FILE PERSISTENCE
# =============================================================================
def save_plan(output_dir: str, plan_md: str) -> str:
    """Write plan.md to the project directory. Returns the full path."""
    plan_path = os.path.join(output_dir, "plan.md")
    os.makedirs(output_dir, exist_ok=True)
    with open(plan_path, "w", encoding="utf-8") as f:
        f.write(plan_md)
    return plan_path


def update_plan_task_status(plan_md: str, task_index: int, status: str) -> str:
    """
    Mark the nth task in the plan as done/in-progress while preserving
    the [COMPLEX]/[SIMPLE] tag so parse_plan_tasks() still works.
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


# =============================================================================
# THE FINALIZER PROMPT
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
# PLANNER PROMPT -- Generates the full project plan
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
# Every node follows DIP: receives AgentClient via factory injection.
#
# FLOW:
#   optimizer → planner → executor → [complex|simple] → executor (loop)
#                        executor → finalize → END
# ---------------------------------------------------------------------------

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
        refined = client.run(message, state.get("session_id", ""))
        _emit("optimizer", "Prompt optimitzat.")
        return {"project_requirements": refined}

    return optimizer_node


def make_planner_node(client: AgentClient):
    """
    NODE 1: The Planner (replaces Architect).
    ==========================================
    Takes the structured spec and generates a full project plan
    with [COMPLEX] / [SIMPLE] tasks, output directory, and file structure.

    Writes plan.md to the project directory.
    """

    def planner_node(state: AgentState):
        _emit("architect", "Elaborant pla de projecte (Planner)...")
        session_id = state.get("session_id", "default")
        output_dir = _ensure_project_dir(session_id)

        memory = _memory_block(state.get("memory_context", ""))
        prompt = (
            f"{PLANNER_PROMPT}\n\n"
            f"### PROJECT SPECIFICATION ###\n"
            f"{state['project_requirements']}{memory}\n\n"
            "Generate the complete plan now."
        )

        plan_md = client.run(prompt, session_id)

        # Save plan.md to project directory
        plan_path = save_plan(output_dir, plan_md)

        # Parse tasks
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
    NODE 2: The Executor (Task Dispatcher).
    ========================================
    Ran BEFORE each coder and AFTER each coder (loop).

    On entry:
      - If generated_code is present → write it to target_file, advance index.
      - If pending tasks remain → dispatch next task (set current_task, complexity).
      - If all tasks done → return without complexity (router goes to finalize).
    """

    def executor_node(state: AgentState):
        task_index = state.get("task_index", 0)
        total_tasks = state.get("total_tasks", 0)
        generated = state.get("generated_code", "")
        target = state.get("target_file", "")
        output_dir = state.get("output_dir", "")
        plan_md = state.get("plan_md", "")

        # --- Write file if we just came from a coder ---
        if generated and target and output_dir:
            file_path = os.path.join(output_dir, target)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(generated)
            _emit("system", f"Escrit: {target} ({len(generated)} chars)")

            # Mark task as done in plan.md (keeps [COMPLEX]/[SIMPLE] tag)
            updated = update_plan_task_status(plan_md, task_index, "done")
            save_plan(output_dir, updated)
            plan_md = updated
            task_index += 1

        # --- Dispatch next task (or finish) ---
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
        }

    return executor_node


def make_complex_coder_node(client: AgentClient):
    """
    NODE 3A: The Complex Coder.
    ============================
    Handles [COMPLEX] tasks: algorithms, business logic, integrations.
    Receives exact task description, target file, and project context.
    """

    def complex_coder_node(state: AgentState):
        task = state.get("current_task", "")
        target = state.get("target_file", "")
        output_dir = state.get("output_dir", "")
        memory = _memory_block(state.get("memory_context", ""))

        _emit("complex", f"Codificant [COMPLEX]: {task[:60]}...")
        prompt = (
            f"You are an expert software engineer. Implement this COMPLEX task.\n\n"
            f"TASK: {task}\n"
            f"TARGET FILE: {target}\n"
            f"PROJECT DIRECTORY: {output_dir}\n"
            f"{memory}\n"
            f"Output ONLY the complete, production-ready code for this file. "
            f"Include ALL imports, type hints, docstrings, and error handling. "
            f"No explanations, no markdown fences — just the raw code."
        )
        code = client.run(prompt, state.get("session_id", ""))
        _emit("complex", f"Completat: {target}")
        return {"generated_code": code}

    return complex_coder_node


def make_simple_coder_node(client: AgentClient):
    """
    NODE 3B: The Simple Coder.
    ===========================
    Handles [SIMPLE] tasks: data classes, config, boilerplate, scaffolding.
    """

    def simple_coder_node(state: AgentState):
        task = state.get("current_task", "")
        target = state.get("target_file", "")
        output_dir = state.get("output_dir", "")
        memory = _memory_block(state.get("memory_context", ""))

        _emit("simple", f"Codificant [SIMPLE]: {task[:60]}...")
        message = (
            f"Implement this SIMPLE task.\n\n"
            f"TASK: {task}\n"
            f"TARGET FILE: {target}\n"
            f"PROJECT DIRECTORY: {output_dir}\n"
            f"{memory}\n"
            f"Output ONLY the complete code for this file. "
            f"Include ALL imports and type hints. "
            f"No explanations, no markdown fences — just the raw code."
        )
        code = client.run(message, state.get("session_id", ""))
        _emit("simple", f"Completat: {target}")
        return {"generated_code": code}

    return simple_coder_node


def make_finalize_node(client: AgentClient):
    """
    NODE 4: The Memory Archivist.
    ==============================
    Runs AFTER all tasks complete. Compresses session into memory dump.
    """

    def finalize_node(state: AgentState):
        _emit("finalizer", "Arxivant memoria de sessio...")
        existing_memory = state.get("memory_context", "")[:6000]
        plan_md = state.get("plan_md", "")[:2000]

        prompt = (
            f"{FINALIZER_PROMPT}\n\n"
            f"Session ID: {state.get('session_id', 'default')}\n"
            f"Project: {state['project_requirements'][:500]}\n"
            f"Output directory: {state.get('output_dir', '')}\n"
            f"Plan summary:\n{plan_md}\n\n"
            f"Existing memory to merge/update:\n{existing_memory}\n\n"
            "Produce the updated <MEMORY_DUMP>."
        )

        response = client.run(prompt, state.get("session_id", ""))

        match = re.search(r'<MEMORY_DUMP>(.*?)</MEMORY_DUMP>', response, re.DOTALL)
        dump = match.group(1).strip() if match else response

        save_memory(state.get("session_id", "default"), dump)
        _emit("finalizer", "Memoria guardada al disc.")
        return {"memory_context": dump}

    return finalize_node
