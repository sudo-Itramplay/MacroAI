"""
ui/widgets/result_panel.py
===========================
Panel dret: visualitzador del codi generat.

Usa TextArea en mode read-only per oferir:
  - Scroll vertical/horitzontal
  - Selecció de text per copiar
  - Ressaltat de sintaxi Python (si Textual el suporta)
  - Numeració de línies

El badge a la capçalera indica quin agent ha generat el codi:
  [cyan]   OpenCode  -> tasca 'simple'
  [orange] Claude    -> tasca 'complexa'
"""

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Label, Static, TextArea


class ResultPanel(Widget):
    """
    Mostra el codi generat per l'agent codificador actiu.

    show_code() s'ha de cridar des del bucle asyncio de la UI,
    un cop el GraphRunner ha completat l'execució.
    """

    DEFAULT_CSS = """
    ResultPanel {
        layout: vertical;
        padding: 1;
    }
    ResultPanel #agent-badge {
        height: 1;
        margin-bottom: 1;
    }
    ResultPanel TextArea {
        height: 1fr;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("CODI GENERAT", classes="panel-title")
        yield Static("Esperant execució...", id="agent-badge", markup=True)
        yield TextArea(
            "",
            id="code-area",
            language="python",
            read_only=True,
            show_line_numbers=True,
        )

    def show_code(self, code: str, complexity: str) -> None:
        """
        Actualitza el panel amb el codi generat i el badge de l'agent.

        Args:
            code:       El codi generat (string en brut).
            complexity: El valor del camp complexity de l'AgentState.
        """
        if "complexa" in (complexity or ""):
            agent_name = "Claude"
            color = "orange1"
        else:
            agent_name = "OpenCode"
            color = "cyan"

        badge = f"[bold {color}]▶ Generat per {agent_name}[/bold {color}]"
        self.query_one("#agent-badge", Static).update(badge)
        self.query_one("#code-area", TextArea).load_text(code or "(cap codi generat)")

    def clear(self) -> None:
        """Neteja el panel per a una nova execució."""
        self.query_one("#agent-badge", Static).update("Esperant execució...")
        self.query_one("#code-area", TextArea).load_text("")
