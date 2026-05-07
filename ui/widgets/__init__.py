# Exportem tots els widgets per facilitar els imports a app.py.
from ui.widgets.project_panel import ProjectPanel
from ui.widgets.log_panel import LogPanel
from ui.widgets.state_panel import StatePanel
from ui.widgets.result_panel import ResultPanel

__all__ = ["ProjectPanel", "LogPanel", "StatePanel", "ResultPanel"]
