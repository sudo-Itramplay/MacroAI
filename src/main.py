"""
src/main.py
===========
ENTRY POINT of the application (CLI mode).

WHAT HAPPENS WHEN YOU RUN:
  $ python src/main.py

  1. We pick a session_id (e.g. "macroai-session").
  2. We load any previous memory for that session from disk.
  3. We build the LangGraph with a configured AgentFactory.
  4. We pack everything into an initial AgentState.
  5. We invoke the graph. It will:
       a. Run optimizer_node  (fast model structures the spec)
       b. Run planner_node    (powerful model creates full project plan)
       c. Loop: executor dispatches tasks to complex/simple coders
       d. Run finalize_node   (compresses memory for next run)
  6. We print results and output directory.

CONFIGURATION:
  MACROAI_PROJECTS_DIR  -- base directory for project outputs
                           (default: ./macroai_projects)
  MACROAI_*_MODEL       -- per-role model overrides
"""

import sys
from pathlib import Path

if __name__ == "__main__" and str(Path(__file__).resolve().parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.graph import build_graph
from src.agents import load_memory, PROJECTS_DIR
from src.clients import AgentFactory


def main():
    session_id = "macroai-session"

    factory = AgentFactory()
    app = build_graph(factory)

    initial_state = {
        "project_requirements": "Sistema de login d'usuaris amb roles i permisos",
        "current_task": "",
        "complexity": "",
        "generated_code": "",
        "session_id": session_id,
        "memory_context": load_memory(session_id),
        "plan_md": "",
        "task_index": 0,
        "total_tasks": 0,
        "target_file": "",
        "output_dir": "",
    }

    print(f"Executant sistema multiagent (sessio: {session_id})...")
    print(f"Directori projectes: {PROJECTS_DIR}")
    print(f"Models: optim={factory.config.optimizer}, "
          f"plan={factory.config.architect}, "
          f"complex={factory.config.complex_coder}, "
          f"simple={factory.config.simple_coder}")

    resultat = app.invoke(initial_state)

    print("\n--- RESULTAT FINAL ---")
    print(f"Tasques completades: {resultat.get('task_index', 0)}/{resultat.get('total_tasks', 0)}")
    print(f"Directori sortida: {resultat.get('output_dir', 'N/A')}")
    print(f"\n[OK] Memoria guardada a .macroai_memory/{session_id}.md")
    print("      (Aquesta memoria es carregara automaticament en la propera execucio)")


if __name__ == "__main__":
    main()
