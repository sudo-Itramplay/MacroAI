"""
src/main.py
===========
ENTRY POINT of the application.

WHAT HAPPENS WHEN YOU RUN:
  $ python src/main.py

  1. We pick a session_id (e.g. "macroai-session").
  2. We load any previous memory for that session from disk.
  3. We build the LangGraph (see graph.py).
  4. We pack everything into an initial AgentState dictionary.
  5. We invoke the graph. It will:
       a. Run architect_node  (Kimi plans)
       b. Route to a coder    (Claude or OpenCode)
       c. Run finalize_node   (Kimi dumps memory)
  6. We print the results and tell you where the memory was saved.

HOW TO USE MULTIPLE PROJECTS:
  Just change the session_id string below. Each session gets its own
  .macroai_memory/<session_id>.md file, so projects never collide.
"""

from src.graph import build_graph
from src.agents import load_memory


def main():
    # -------------------------------------------------------------------------
    # SESSION ID  --  Think of this as the "project name" or "thread name".
    # -------------------------------------------------------------------------
    # If you want to work on something completely different, change this
    # to a new string (e.g. "api-refactor", "bugfix-login", etc.).
    # The old memory will remain on disk and you can come back anytime.
    # -------------------------------------------------------------------------
    session_id = "macroai-session"

    # Build the compiled graph (a one-time setup cost).
    app = build_graph()

    # -------------------------------------------------------------------------
    # INITIAL STATE  --  This is the "seed" data that kicks off the graph.
    # -------------------------------------------------------------------------
    # In a real application you might read project_requirements from a CLI
    # argument, a file, or a user prompt. Here we hard-code an example.
    #
    # memory_context is loaded from disk. On the very first run it will be
    # an empty string "". On subsequent runs it will contain the compressed
    # dump from finalize_node, giving the Architect full continuity.
    # -------------------------------------------------------------------------
    initial_state = {
        "project_requirements": "Sistema de login d'usuaris",
        "current_task": "Crear la classe d'usuari base i les seves propietats",
        "complexity": "",           # filled in by architect_node
        "generated_code": "",       # filled in by whichever coder runs
        "session_id": session_id,   # ties this run to a memory file
        "memory_context": load_memory(session_id)   # "" on first run
    }

    print(f"Executant sistema multiagent (sessio: {session_id})...")

    # -------------------------------------------------------------------------
    # INVOKE THE GRAPH
    # -------------------------------------------------------------------------
    # app.invoke() blocks until the graph reaches END.
    # It returns the FINAL AgentState after all nodes have executed.
    # -------------------------------------------------------------------------
    resultat = app.invoke(initial_state)

    # -------------------------------------------------------------------------
    # DISPLAY RESULTS
    # -------------------------------------------------------------------------
    print("\n--- RESULTAT FINAL ---")
    print(f"Decisio Kimi (Architect): {resultat['complexity']}")
    print(f"Codi Generat:\n{resultat['generated_code']}")
    print(f"\n[OK] Memoria guardada a .macroai_memory/{session_id}.md")
    print("      (Aquesta memoria es carregara automaticament en la propera execucio)")


# Standard Python idiom: only run main() when this file is executed directly.
if __name__ == "__main__":
    main()
