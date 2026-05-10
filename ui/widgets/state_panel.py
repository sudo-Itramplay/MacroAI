"""
ui/widgets/state_panel.py
==========================
Panel superior central: visualitzador del pipeline i progres de tasques.

Mostra:
  - Barra de pipeline: [optimizer] -> [planner] -> [executor/coders] -> [finalize]
  - Progres de tasques: Tasca 3/7 [COMPLEX] ...
  - Fitxer actual: src/engine.py
"""

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Label, Static

from ui.runner import StateSnapshot

_NODE_ORDER = ["optimizer", "planner", "scaffolder", "complex", "simple", "executor", "finalize"]
_NODE_LABELS = {
    "optimizer":  "optimizer",
    "planner":    "planner",
    "scaffolder": "scaffold",
    "complex":    "coder+",
    "simple":     "coder-",
    "executor":   "dispatch",
    "finalize":   "finalize",
}


class StatePanel(Widget):
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
        self._task_index = 0
        self._total_tasks = 0
        self._complexity = ""
        self._current_task = ""

    def compose(self) -> ComposeResult:
        yield Label("PIPELINE", classes="panel-title")
        yield Static("", id="pipeline-bar", markup=True)
        yield Static("Mode: —", id="mode-field", classes="state-field", markup=True)
        yield Static("Progres: —", id="progress-field", classes="state-field", markup=True)
        yield Static("Tasca: —", id="task-field", classes="state-field", markup=True)
        yield Static("Fitxer: —", id="file-field", classes="state-field", markup=True)

    def set_mode(self, auto: bool) -> None:
        """Update the Safe/Auto indicator."""
        if auto:
            text = "Mode: [bold red]AUTO[/bold red]  (opencode pot escriure fitxers directament)"
        else:
            text = "Mode: [bold green]SAFE[/bold green]  (executor escriu els fitxers)"
        try:
            self.query_one("#mode-field", Static).update(text)
        except Exception:
            pass

    def on_mount(self) -> None:
        self._render_pipeline()
        self.set_mode(False)

    def _render_pipeline(self) -> None:
        parts: list[str] = []
        for node in _NODE_ORDER:
            label = _NODE_LABELS[node]
            if node in self._completed_nodes:
                parts.append(f"[green]✓ {label}[/green]")
            else:
                parts.append(f"[dim]· {label}[/dim]")
        bar = "  →  ".join(parts)
        self.query_one("#pipeline-bar", Static).update(bar)

    def update_from_snapshot(self, snap: StateSnapshot) -> None:
        if snap.node_name not in self._completed_nodes:
            self._completed_nodes.append(snap.node_name)
        self._render_pipeline()

        partial = snap.partial_state

        if "task_index" in partial:
            self._task_index = partial["task_index"]
        if "total_tasks" in partial:
            self._total_tasks = partial["total_tasks"]
        if "complexity" in partial:
            self._complexity = partial["complexity"] or self._complexity
        if "current_task" in partial:
            self._current_task = partial["current_task"] or self._current_task

        # Progress bar
        if self._total_tasks > 0:
            done = min(self._task_index, self._total_tasks)
            pct = done * 100 // self._total_tasks
            bar_filled = "█" * (pct // 10)
            bar_empty = "░" * (10 - pct // 10)
            c = self._complexity
            tag = "COMPLEX" if "complexa" in c else ("SIMPLE" if c else "?")
            color = "yellow" if "complexa" in c else ("cyan" if c else "dim")
            self.query_one("#progress-field", Static).update(
                f"Progres: [{bar_filled}{bar_empty}] {done}/{self._total_tasks}  "
                f"[bold {color}]{tag}[/bold {color}]"
            )

        # Current task
        task = (self._current_task or (partial.get("current_task") or "—"))[:70]
        if task != "—":
            self.query_one("#task-field", Static).update(f"Tasca: {task}")

        # Target file
        if "target_file" in partial and partial["target_file"]:
            self.query_one("#file-field", Static).update(f"Fitxer: {partial['target_file']}")

    def reset(self) -> None:
        self._completed_nodes = []
        self._task_index = 0
        self._total_tasks = 0
        self._complexity = ""
        self._current_task = ""
        self._render_pipeline()
        self.query_one("#progress-field", Static).update("Progres: —")
        self.query_one("#task-field", Static).update("Tasca: —")
        self.query_one("#file-field", Static).update("Fitxer: —")
