from src.graph import build_graph

def main():
    app = build_graph()
    
    # Dades inicials de prova
    initial_state = {
        "project_requirements": "Sistema de login d'usuaris",
        "current_task": "Crear la classe d'usuari base i les seves propietats",
        "complexity": "",
        "generated_code": ""
    }
    
    print("Executant sistema multiagent...")
    resultat = app.invoke(initial_state)
    
    print("\n--- RESULTAT FINAL ---")
    print(f"Decisió Kimi: {resultat['complexity']}")
    print(f"Codi Generat:\n{resultat['generated_code']}")

if __name__ == "__main__":
    main()
