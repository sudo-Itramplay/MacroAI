"""
ui/widgets/state_panel.py
==========================
Panel superior central: visualitzador del pipeline de LangGraph.

DISSENY
-------
Mostra els 5 nodes del pipeline com una barra de progrés textual:
  [optimizer] → [architect] → [coder] → [finalize]

Cada node té un indicador:
  [dim]·[/dim]  -> pendent
  [yellow]▶[/yellow] -> en curs (just completat, en espera del següent)
  [green]✓[/green]   -> completat

A sota mostra els camps clau de l'AgentState:
  current_task  (truncat a 70 chars)
  complexity    (verd=simple, vermell=complexa)
"""

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Label
from textual.widgets import Static
from textual.containers import Horizontal

from ui.runner import StateSnapshot

# Ordre dels nodes tal com els emet graph.stream()
_NODE_ORDER = ["optimizer", "architect", "claude", "opencode", "finalize"]
# Labels curts per a la barra de progrés
_NODE_LABELS = {
    "optimizer": "optimizer",
    "architect": "architect",
    "claude":    "claude",
    "opencode":  "opencode",
    "finalize":  "finalize",
}


class StatePanel(Widget):
    """
    Visualitza el progrés dels nodes del pipeline i l'AgentState actual.

    update_from_snapshot() s'ha de cridar des del bucle asyncio (thread-safe).
    """

    DEFAULT_CSS = """
    StatePanel {
        layout: vertical;
        padding: 1;
        height: auto;
    }
    StatePanel #pipeline-bar {
        height: 1;
        margin-bottom: 1;
    }
    StatePanel .state-field {
        color: $text-muted;
        height: 1;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._completed_nodes: list[str] = []

    def compose(self) -> ComposeResult:
        yield Label("PIPELINE", classes="panel-title")
        yield Static("", id="pipeline-bar", markup=True)
        yield Static("Tasca: —", id="task-field", classes="state-field", markup=True)
        yield Static("Complexitat: —", id="complexity-field", classes="state-field", markup=True)

    def on_mount(self) -> None:
        self._render_pipeline()

    def _render_pipeline(self) -> None:
        """
        Reconstrueix la barra de progrés del pipeline.
        Llegim _completed_nodes per saber fins a quin punt hem arribat.
        """
        parts: list[str] = []
        for node in _NODE_ORDER:
            label = _NODE_LABELS[node]
            if node in self._completed_nodes:
                # Distingim claude/opencode: ambdós apareixen a 'coder'
                parts.append(f"[green]✓ {label}[/green]")
            else:
                parts.append(f"[dim]· {label}[/dim]")
        bar = "  →  ".join(parts)
        self.query_one("#pipeline-bar", Static).update(bar)

    def update_from_snapshot(self, snap: StateSnapshot) -> None:
        """
        Actualitza el panel quan LangGraph completa un node.
        Cridat des del bucle asyncio de la UI.
        """
        # Marquem el node com a completat
        if snap.node_name not in self._completed_nodes:
            self._completed_nodes.append(snap.node_name)
        self._render_pipeline()

        # Actualitzem els camps de l'estat si el node els ha modificat
        partial = snap.partial_state

        if "current_task" in partial:
            task = (partial["current_task"] or "—")[:70]
            self.query_one("#task-field", Static).update(f"Tasca: {task}")

        if "complexity" in partial and partial["complexity"]:
            c = partial["complexity"]
            color = "red" if "complexa" in c else "green"
            self.query_one("#complexity-field", Static).update(
                f"[{color}]Complexitat: {c}[/{color}]"
            )

    def reset(self) -> None:
        """Reinicia el panel per a una nova execució."""
        self._completed_nodes = []
        self._render_pipeline()
        self.query_one("#task-field", Static).update("Tasca: —")
        self.query_one("#complexity-field", Static).update("Complexitat: —")
