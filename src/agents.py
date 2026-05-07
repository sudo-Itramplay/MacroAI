import os
import re
import subprocess
from typing import TypedDict


MEMORY_DIR = ".macroai_memory"


class AgentState(TypedDict):
    project_requirements: str
    current_task: str
    complexity: str
    generated_code: str
    session_id: str
    memory_context: str


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


def _strip_ansi(text: str) -> str:
    return re.sub(r'\x1b\[[0-9;]*[mGKHF]', '', text)


def _run_kimi(prompt: str, session_id: str = "") -> str:
    cmd = ["kimi", "--quiet", "--afk"]
    if session_id:
        cmd.extend(["--session", session_id])
    cmd.extend(["--prompt", prompt])
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if result.returncode != 0:
        raise RuntimeError(f"Kimi error: {result.stderr.strip()}")
    return _strip_ansi(result.stdout).strip()


def _run_claude(prompt: str, session_id: str = "") -> str:
    # Claude CLI: native session resume is not assumed; memory is injected via prompt.
    result = subprocess.run(
        ["claude", "--print", "-p", prompt],
        capture_output=True, text=True, timeout=180
    )
    if result.returncode != 0:
        raise RuntimeError(f"Claude error: {result.stderr.strip()}")
    return result.stdout.strip()


def _run_opencode(message: str, session_id: str = "") -> str:
    cmd = ["opencode", "run"]
    if session_id:
        cmd.extend(["--session", session_id])
    cmd.append(message)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if result.returncode != 0:
        raise RuntimeError(f"OpenCode error: {result.stderr.strip()}")
    return _strip_ansi(result.stdout).strip()


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


FINALIZER_PROMPT = """\
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
"""


def architect_node(state: AgentState):
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
    return {"complexity": complexity, "current_task": task_description}


def claude_coder_node(state: AgentState):
    memory = _memory_block(state.get("memory_context", ""))
    prompt = (
        f"You are an expert software engineer. Solve this complex task and output ONLY the code:\n"
        f"{state['current_task']}{memory}"
    )
    return {"generated_code": _run_claude(prompt, state.get("session_id", ""))}


def opencode_coder_node(state: AgentState):
    memory = _memory_block(state.get("memory_context", ""))
    message = (
        f"Write the code for this task, output ONLY the code:\n"
        f"{state['current_task']}{memory}"
    )
    return {"generated_code": _run_opencode(message, state.get("session_id", ""))}


def finalize_node(state: AgentState):
    existing_memory = state.get("memory_context", "")[:6000]
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
    match = re.search(r'<MEMORY_DUMP>(.*?)</MEMORY_DUMP>', response, re.DOTALL)
    dump = match.group(1).strip() if match else response
    save_memory(state.get("session_id", "default"), dump)
    return {"memory_context": dump}
