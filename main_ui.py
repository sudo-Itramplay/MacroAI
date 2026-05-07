"""
main_ui.py
==========
Punt d'entrada de la Interfície d'Usuari de MacroAI.

ÚS:
    python main_ui.py

Alternativa CLI (sense UI):
    python src/main.py
"""

from ui.app import MacroAIApp


def main() -> None:
    app = MacroAIApp()
    app.run()


if __name__ == "__main__":
    main()
