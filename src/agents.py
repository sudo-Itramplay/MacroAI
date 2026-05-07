"""
src/agents.py
=============
This module contains the HEART of the multi-agent system.

WHAT IT DOES:
  1. Defines AgentState    -> the shared data structure that passes through the graph.
  2. Wraps CLI tools       -> runs Kimi, Claude, and OpenCode as subprocesses.
  3. Manages session memory-> saves/loads compressed memory so the AI feels "stateful"
                              even though every call is a fresh subprocess.
  4. Implements the nodes  -> architect_node, claude_coder_node, opencode_coder_node,
                              and the special finalize_node that dumps memory.

ARCHITECTURE NOTES:
  - We do NOT use API keys or cloud SDKs. Each agent is just a local CLI binary
    spawned via Python's subprocess module.
  - Because every subprocess starts fresh, we inject "memory_context" into every
    prompt. This lets the agents "remember" what happened in previous runs.
  - Kimi and OpenCode support native --session flags, so the CLI itself can also
    keep its own internal continuity. Claude gets memory injected via prompt.
"""

import os
import re
import subprocess
from typing import Callable, Optional, TypedDict


# =============================================================================
# MEMORY PERSISTENCE LAYER
# =============================================================================
# Every session gets its own .md file inside this folder.
# The gitignore keeps these out of the repo so you don't leak project details.
# ---------------------------------------------------------------------------
MEMORY_DIR = ".macroai_memory"


# =============================================================================
# LOG SINK  --  Mecanisme d'observabilitat per a la UI (opcional)
# =============================================================================
# Quan la UI (ui/runner.py) arrenca, registra un callback via configure_log_sink().
# Cada cop que un node crida _emit(), el callback rep el missatge i el reenvia
# a l'asyncio.Queue del GraphRunner, que la UI llegeix per actualitzar els widgets.
#
# Si no hi ha cap sink registrat (ús des de main.py en mode CLI), _emit() és
# un no-op. main.py segueix funcionant sense cap canvi.
# ---------------------------------------------------------------------------

LogSink = Callable[[str, str, bool], None]
_log_sink: Optional[LogSink] = None


def configure_log_sink(sink: Optional[LogSink]) -> None:
    """
    Registra (o elimina) el callback de log de la UI.
    Cridat per GraphRunner (ui/runner.py) en iniciar i acabar cada execució.
    """
    global _log_sink
    _log_sink = sink


def _emit(agent: str, message: str, is_error: bool = False) -> None:
    """Envia un event al sink registrat. Si no n'hi ha, és un no-op."""
    if _log_sink is not None:
        _log_sink(agent, message, is_error)


# =============================================================================
# AgentState  --  The "shared notebook" that every node reads and writes
# =============================================================================
# LangGraph passes this dict from node to node. Each node returns a partial
# dict with only the keys it wants to update. The graph merges them automatically.
#
# Fields:
#   project_requirements  --  High-level description of what the user wants.
#   current_task          --  The atomic task the Architect decided to tackle NOW.
#   complexity            --  'simple' -> OpenCode, 'complexa' -> Claude.
#   generated_code        --  The code produced by whichever coder ran.
#   session_id            --  Human-readable ID for this project thread.
#   memory_context        --  Compressed text dump from previous runs (the "brain").
# ---------------------------------------------------------------------------
class AgentState(TypedDict):
    project_requirements: str
    current_task: str
    complexity: str
    generated_code: str
    session_id: str
    memory_context: str


def _memory_file(session_id: str) -> str:
    """Return the full filesystem path for a session's memory file."""
    os.makedirs(MEMORY_DIR, exist_ok=True)   # lazy-create the folder on first use
    return os.path.join(MEMORY_DIR, f"{session_id}.md")


def load_memory(session_id: str) -> str:
    """
    Load the previously-saved memory dump for a given session.
    Returns empty string if this is the very first run (no file yet).
    Called by main.py before the graph starts.
    """
    path = _memory_file(session_id)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def save_memory(session_id: str, content: str) -> None:
    """
    Persist the compressed memory dump to disk.
    Called by finalize_node at the very end of every run.
    """
    path = _memory_file(session_id)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


# =============================================================================
# HELPERS
# =============================================================================

def _strip_ansi(text: str) -> str:
    """
    Remove terminal color codes from CLI output.
    Tools like Kimi and OpenCode sometimes print ANSI escape sequences
    (\x1b[32m...\x1b[0m) even in --quiet mode. We strip them so downstream
    code sees clean plain text.
    """
    return re.sub(r'\x1b\[[0-9;]*[mGKHF]', '', text)


# =============================================================================
# SUBPROCESS WRAPPERS  --  One per CLI tool
# =============================================================================
# Each function builds the correct command-line arguments, runs the binary,
# checks for errors, and returns the stdout as a clean string.
#
# DESIGN CHOICE: subprocess.run instead of API clients
#   Pros: No API keys, no rate limits, no network latency to cloud endpoints,
#         uses your existing paid CLI subscriptions.
#   Cons: Each call is a cold start; we mitigate that with session --flags
#         and by injecting memory_context into every prompt.
# ---------------------------------------------------------------------------

def _run_kimi(prompt: str, session_id: str = "") -> str:
    """
    Spawn the Kimi CLI (Moonshot) in quiet, auto-approve mode.

    Args:
        prompt:     The full text prompt to send.
        session_id: If provided, adds --session <id> so Kimi internally
                    resumes its own native session (keeps its own continuity).
    """
    cmd = ["kimi", "--quiet", "--afk"]
    if session_id:
        cmd.extend(["--session", session_id])
    cmd.extend(["--prompt", prompt])

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if result.returncode != 0:
        raise RuntimeError(f"Kimi error: {result.stderr.strip()}")
    return _strip_ansi(result.stdout).strip()


def _run_claude(prompt: str, session_id: str = "") -> str:
    """
    Spawn the Claude CLI in non-interactive print mode.

    NOTE ON session_id:
        Claude's CLI does not expose a --session flag in this wrapper,
        so session continuity is achieved purely by injecting the
        memory_context string directly into the prompt text.
    """
    result = subprocess.run(
        ["claude", "--print", "-p", prompt],
        capture_output=True, text=True, timeout=180
    )
    if result.returncode != 0:
        raise RuntimeError(f"Claude error: {result.stderr.strip()}")
    return result.stdout.strip()


def _run_opencode(message: str, session_id: str = "") -> str:
    """
    Spawn the OpenCode CLI in non-interactive run mode.

    Args:
        message:    The user message / prompt.
        session_id: If provided, adds --session <id> for native continuity.
    """
    cmd = ["opencode", "run"]
    if session_id:
        cmd.extend(["--session", session_id])
    cmd.append(message)

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if result.returncode != 0:
        raise RuntimeError(f"OpenCode error: {result.stderr.strip()}")
    return _strip_ansi(result.stdout).strip()


# =============================================================================
# MEMORY INJECTION HELPER
# =============================================================================
# This is the "glue" that makes stateless subprocesses feel stateful.
# We take the raw memory dump (a big block of text) and wrap it in a
# standardized preamble. Then we append that preamble to EVERY prompt.
#
# Why it works:
#   The AI sees the memory as if it were part of the original instructions.
#   It doesn't know it's "resuming"; it just uses the facts provided.
# ---------------------------------------------------------------------------

def _memory_block(ctx: str) -> str:
    """
    Format a raw memory string into a prompt preamble.
    Returns empty string if there is no memory (first run).
    """
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
# THE FINALIZER PROMPT  --  "Memory Archivist"
# =============================================================================
# This is the prompt we send to Kimi at the end of EVERY run.
# Its job: compress the entire session into a tiny, dense packet
# so the NEXT run can load it and pick up exactly where we left off.
#
# We force the output into a <MEMORY_DUMP> block with strict sections.
# This makes parsing reliable and keeps the format predictable.
# ---------------------------------------------------------------------------

FINALIZER_PROMPT = """\
You are the Session Memory Archivist. Your sole job is to compress the entire working context of this session into a dense, self-contained memory packet.

TWO types of AI agents will read this dump in the future:
  - CLAUDE:    handles complex logic, algorithms, integrations, debugging.
  - OPENCODE:  handles boilerplate, data structures, repetitive scaffolding.

Output STRICTLY inside a single <MEMORY_DUMP> ... </MEMORY_DUMP> block. Use this EXACT internal structure:

[PROJECT_STATE]
- Active files: <path> | purpose
- Architecture decisions locked in
- Unfinished / broken components

[TASK_STACK]
- Done: <list>
- In-Progress: <list>
- Pending[CLAUDE]: <tasks that need complex reasoning>
- Pending[OPENCODE]: <tasks that are boilerplate/repetitive>

[KEY_DECISIONS]
- <decision> | Rationale: <why> | Owner: CLAUDE|OPENCODE

[SCRATCHPAD]
- Debug notes, hypotheses, dead ends, known failure modes

[NEXT_ACTION]
- Target: CLAUDE|OPENCODE
- Task: <single highest-priority next step with full context>
- Files: <exact paths to touch>
- Signature: <exact function/class name to create or modify>

RULES:
1. EXTREME BREVITY. Dense shorthand, abbreviations, bullet points only.
2. NEVER reference "above", "earlier", or "the file I mentioned". 100% self-contained.
3. Include FULL file paths and exact function/class names.
4. No markdown outside <MEMORY_DUMP>. No greetings. No summaries.
5. Tag every pending task with [CLAUDE] or [OPENCODE] so the router can skip reading.
6. If an existing memory block is provided, MERGE and UPDATE — do not replace blindly.
"""


# =============================================================================
# GRAPH NODES  --  Each one is a step in the LangGraph pipeline
# =============================================================================
# A "node" is just a Python function that receives the current AgentState,
# does some work (usually calling an AI via subprocess), and returns a
# dictionary of the fields it wants to update.
#
# FLOW:
#   architect_node -> route_task -> [claude_coder_node OR opencode_coder_node]
#                                   -> finalize_node -> END
# ---------------------------------------------------------------------------

def opencode_optimizer_node(state: AgentState):
    """
    NODE 0: El Traductor de Prompts (OpenCode)
    -------------------------------------------
    Rep el requeriment brut de l'usuari i el converteix en una especificació
    neta i estructurada que l'Arquitecte (Kimi) pot consumir directament.

    Flux de dades:
      state['project_requirements'] (text brut de l'usuari)
        -> OpenCode reformula
        -> state['project_requirements'] (especificació estructurada)

    Per que OpenCode i no Kimi?
      OpenCode és el més econòmic del sistema. No té sentit gastar tokens de
      Kimi en tasques de formatació quan OpenCode pot fer-ho igualment bé.
    """
    _emit("opencode", "Optimitzant prompt de l'usuari...")
    message = (
        "You are a prompt engineering specialist. "
        "Rewrite the following raw user requirement into a precise, structured "
        "software specification for an architect AI. "
        "Use bullet points for clarity. Separate functional requirements from "
        "technical constraints. Output ONLY the refined specification:\n\n"
        f"{state['project_requirements']}"
    )
    refined = _run_opencode(message, state.get("session_id", ""))
    _emit("opencode", "Prompt optimitzat.")
    return {"project_requirements": refined}


def architect_node(state: AgentState):
    """
    NODE 1: The Architect (Kimi)
    -------------------------------
    Reads the project requirements + any resumed memory.
    Decides WHAT to do next and HOW HARD it is.

    Output format expected from Kimi:
        Line 1: "simple" or "complexa"
        Line 2+: the refined atomic task description

    Returns:
        {"complexity": "simple|complexa", "current_task": "..."}
    """
    _emit("kimi", "Analitzant requeriments (Arquitecte)...")
    memory = _memory_block(state.get("memory_context", ""))
    prompt = (
        f"You are a software Architect. Analyse this requirement: {state['project_requirements']}\n"
        f"Current task context: {state['current_task']}{memory}\n"
        "1. Refine the atomic task to implement.\n"
        "2. Classify the complexity strictly as 'complexa' or 'simple'.\n"
        "Reply with ONLY the complexity word on the first line, "
        "and the refined task description on the second line. No extra text."
    )
    response = _run_kimi(prompt, state.get("session_id", "")).split('\n')
    complexity = response[0].strip().lower()
    task_description = "\n".join(response[1:]).strip()
    _emit("kimi", f"Complexitat: {complexity} | {task_description[:60]}")
    return {"complexity": complexity, "current_task": task_description}


def claude_coder_node(state: AgentState):
    """
    NODE 2A: The Advanced Coder (Claude)
    -------------------------------------
    Handles 'complexa' tasks: algorithms, business logic, hard integrations.
    Receives the refined task + memory context.
    Returns the raw code as a string.
    """
    _emit("claude", f"Codificant tasca complexa: {state['current_task'][:60]}...")
    memory = _memory_block(state.get("memory_context", ""))
    prompt = (
        f"You are an expert software engineer. Solve this complex task and output ONLY the code:\n"
        f"{state['current_task']}{memory}"
    )
    return {"generated_code": _run_claude(prompt, state.get("session_id", ""))}


def opencode_coder_node(state: AgentState):
    """
    NODE 2B: The Basic Coder (OpenCode)
    ------------------------------------
    Handles 'simple' tasks: boilerplate, data structures, repetitive code.
    Receives the refined task + memory context.
    Returns the raw code as a string.
    """
    _emit("opencode", f"Codificant tasca simple: {state['current_task'][:60]}...")
    memory = _memory_block(state.get("memory_context", ""))
    message = (
        f"Write the code for this task, output ONLY the code:\n"
        f"{state['current_task']}{memory}"
    )
    return {"generated_code": _run_opencode(message, state.get("session_id", ""))}


def finalize_node(state: AgentState):
    """
    NODE 3: The Memory Archivist (Kimi)
    ------------------------------------
    Runs AFTER coding, every single time.

    WHAT IT DOES:
      1. Collects everything that happened this run:
         project name, task, complexity, generated code snippet.
      2. Loads the PREVIOUS memory dump (up to 6000 chars to stay within
         reasonable context windows).
      3. Sends all of that to Kimi with the FINALIZER_PROMPT.
      4. Kimi returns a new <MEMORY_DUMP> block.
      5. We parse the block, save it to disk, and return it into the state
         so the graph has it for the remainder of this execution.

    WHY THIS MATTERS:
      Without this step, every new python src/main.py would be a blank slate.
      With it, the Architect sees the full project history on the next run.
    """
    _emit("kimi", "Arxivant memòria de sessió (Memory Archivist)...")
    # Truncate existing memory so we don't blow past the context window.
    # 6000 chars is a safe heuristic for most local CLI models.
    existing_memory = state.get("memory_context", "")[:6000]

    # Build the mega-prompt for the Archivist
    prompt = (
        f"{FINALIZER_PROMPT}\n\n"
        f"Session ID: {state.get('session_id', 'default')}\n"
        f"Project: {state['project_requirements']}\n"
        f"Task: {state['current_task']}\n"
        f"Complexity: {state['complexity']}\n"
        f"Generated code snippet:\n{state['generated_code'][:2000]}\n\n"
        f"Existing memory to merge/update:\n{existing_memory}\n\n"
        "Produce the updated <MEMORY_DUMP>."
    )

    response = _run_kimi(prompt, state.get("session_id", ""))

    # Extract the <MEMORY_DUMP>...</MEMORY_DUMP> block using regex.
    # re.DOTALL makes '.' match newlines, so we can grab multi-line dumps.
    match = re.search(r'<MEMORY_DUMP>(.*?)</MEMORY_DUMP>', response, re.DOTALL)
    dump = match.group(1).strip() if match else response

    # Persist to disk so the NEXT python run can load it.
    save_memory(state.get("session_id", "default"), dump)
    _emit("kimi", "Memòria guardada al disc.")
    return {"memory_context": dump}
