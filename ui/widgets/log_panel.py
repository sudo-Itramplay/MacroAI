"""
ui/widgets/log_panel.py
========================
Panel central inferior: log en temps real dels agents CLI.

CODIFICACIÓ DE COLORS PER AGENT
---------------------------------
  violet  -> Kimi   (Arquitecte i Archivist de memòria)
  orange  -> Claude (Codificador complex)
  cyan    -> OpenCode (Optimitzador i codificador simple)
  white   -> Sistema (missatges de control del runner)

Usem RichLog de Textual que suporta markup Rich i té scroll automàtic.
"""

from datetime import datetime
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Label, RichLog

from ui.runner import LogEntry

# Mapeig d'agent -> (color Rich, badge curt)
_AGENT_STYLE: dict[str, tuple[str, str]] = {
    "kimi":     ("violet",    "KIMI "),
    "claude":   ("orange1",   "CLAUD"),
    "opencode": ("cyan",      "OC   "),
    "system":   ("dim white", "SYS  "),
}


class LogPanel(Widget):
    """
    Widget de log en temps real.

    La UI crida add_entry() des del _poll_queues() de l'App per afegir
    cada LogEntry que el GraphRunner emet durant l'execució del graf.
    """

    DEFAULT_CSS = """
    LogPanel {
        layout: vertical;
        padding: 1;
    }
    LogPanel RichLog {
        height: 1fr;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("LOG EN VIU", classes="panel-title")
        yield RichLog(id="rich-log", highlight=False, markup=True, wrap=True)

    def add_entry(self, entry: LogEntry) -> None:
        """
        Afegeix una entrada de log al widget.
        Cridat des del fil asyncio de la UI (thread-safe via call_soon_threadsafe).
        """
        color, badge = _AGENT_STYLE.get(entry.agent, ("white", "?????"))
        ts = datetime.now().strftime("%H:%M:%S")

        if entry.is_error:
            line = f"[dim]{ts}[/dim] [bold red][{badge}][/bold red] [red]{entry.message}[/red]"
        else:
            line = f"[dim]{ts}[/dim] [bold {color}][{badge}][/bold {color}] {entry.message}"

        self.query_one(RichLog).write(line)

    def add_system(self, message: str, is_error: bool = False) -> None:
        """Drecera per afegir missatges de sistema sense construir un LogEntry."""
        self.add_entry(LogEntry(agent="system", message=message, is_error=is_error))

    def clear_log(self) -> None:
        """Buida el log (útil en iniciar una nova execució)."""
        self.query_one(RichLog).clear()
