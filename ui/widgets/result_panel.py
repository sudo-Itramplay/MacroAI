"""
ui/widgets/result_panel.py
===========================
Panel dret: visualitzador del codi generat o resum del projecte.

Quan sha completat tot el graf mostra:
  - Resum del projecte (directori, fitxers creats, tasques completades)
  - Ultim codi generat amb ressaltat de sintaxi Python

El TextArea es read_only i suporta seleccio de text nadiua (Ctrl+C).
"""

import os
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Label, Static, TextArea


class ResultPanel(Widget):
    """Mostra el resultat final del graf: fitxers creats i ultim codi generat."""
    DEFAULT_CSS = """
    ResultPanel {
        layout: vertical;
        padding: 1;
    }
    ResultPanel #agent-badge {
        height: auto;
        max-height: 5;
        margin-bottom: 1;
    }
    ResultPanel TextArea {
        height: 1fr;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("CODI GENERAT", classes="panel-title")
        yield Static("Esperant execucio...", id="agent-badge", markup=True)
        yield TextArea(
            "",
            id="code-area",
            language="python",
            read_only=True,
            show_line_numbers=True,
        )

    def show_result(self, code: str, output_dir: str, task_index: int, total_tasks: int) -> None:
        lines = []
        if output_dir and os.path.isdir(output_dir):
            lines.append(f"[bold]Directori:[/bold] {output_dir}")
            try:
                files = []
                for root, dirs, filenames in os.walk(output_dir):
                    for fn in filenames:
                        rp = os.path.relpath(os.path.join(root, fn), output_dir)
                        files.append(rp)
                if files:
                    lines.append(f"[bold]Fitxers ({len(files)}):[/bold]")
                    for f in sorted(files)[:12]:
                        lines.append(f"  • {f}")
                    if len(files) > 12:
                        lines.append(f"  ... i {len(files) - 12} mes")
            except Exception:
                pass
        lines.append(f"[bold]Tasques:[/bold] {task_index}/{total_tasks} completades")
        badge = "\n".join(lines)
        self.query_one("#agent-badge", Static).update(badge)
        self.query_one("#code-area", TextArea).load_text(code or "(cap codi generat)")

    def clear(self) -> None:
        self.query_one("#agent-badge", Static).update("Esperant execucio...")
        self.query_one("#code-area", TextArea).load_text("")
