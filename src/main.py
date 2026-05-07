from src.graph import build_graph
from src.agents import load_memory


def main():
    session_id = "macroai-session"  # Canvia aixo per projectes diferents

    app = build_graph()

    initial_state = {
        "project_requirements": "Sistema de login d'usuaris",
        "current_task": "Crear la classe d'usuari base i les seves propietats",
        "complexity": "",
        "generated_code": "",
        "session_id": session_id,
        "memory_context": load_memory(session_id)
    }

    print(f"Executant sistema multiagent (sessio: {session_id})...")
    resultat = app.invoke(initial_state)

    print("\n--- RESULTAT FINAL ---")
    print(f"Decisio Kimi: {resultat['complexity']}")
    print(f"Codi Generat:\n{resultat['generated_code']}")
    print(f"\nMemoria guardada a .macroai_memory/{session_id}.md")


if __name__ == "__main__":
    main()
