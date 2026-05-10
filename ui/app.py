"""
ui/app.py
=========
Aplicacio principal de MacroAI basada en Textual (TUI async-native).

PER QUE TEXTUAL I NO UNA WEB UI?
----------------------------------
  1. Tots els agents son CLI: l'entorn natural es el terminal.
  2. Cap latencia de navegador ni problemes de CORS.
  3. Textual es async-native: encaixa perfectament amb la nostra
     arquitectura de asyncio + ThreadPoolExecutor.
  4. Funciona directament a Hyprland/alacritty sense cap servei extern.

LAYOUT DE LA PANTALLA
----------------------
  ┌──────────────────────────────────────────────────────────┐
  │ MacroAI  |  sessio: macroai-session          [Q] Sortir  │
  ├──────────────┬────────────────────┬────────────────────  │
  │  PROJECTES   │  PIPELINE          │  CODI GENERAT        │
  │  (sessions)  │  ✓ optimizer ...   │  (TextArea)          │
  │              ├────────────────────┤                      │
  │              │  REQUERIMENT       │                      │
  │              │  [_____________]   │                      │
  │              │  [▶ Executar]      │                      │
  │              ├────────────────────┤                      │
  │              │  LOG EN VIU        │                      │
  │              │  (RichLog scroll)  │                      │
  └──────────────┴────────────────────┴──────────────────────┘

GESTIO DE LA CONCURRENCIA
--------------------------
  @work(exclusive=True) garanteix que nomes una execucio del graf
  corre alhora. Internament:
    - asyncio.create_task(runner.run(...))  -> executa el graf
    - asyncio.create_task(_poll_queues())   -> polling de les cues de log/estat
  Ambdues tasques corren concurrent en el bucle asyncio de Textual.
"""

import asyncio
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, Button, Label
from textual.containers import Horizontal, Vertical
from textual import on, work

from src.clients import is_auto_approve, set_auto_approve
from ui.runner import GraphRunner, LogEntry, StateSnapshot
from ui.widgets import ProjectPanel, LogPanel, StatePanel, ResultPanel


class MacroAIApp(App):
    """Aplicacio TUI principal de MacroAI."""

    TITLE = "MacroAI"
    SUB_TITLE = "Sistema Multiagent (OpenCode + LangGraph)"

    CSS = """
    Screen {
        layout: horizontal;
        background: $surface;
    }

    ProjectPanel {
        width: 26;
        height: 100%;
        border-right: solid $primary-darken-2;
    }

    #center-pane {
        width: 1fr;
        height: 100%;
        layout: vertical;
    }

    StatePanel {
        height: auto;
        max-height: 11;
        border-bottom: solid $primary-darken-2;
    }

    #input-area {
        height: auto;
        padding: 1;
        border-bottom: solid $primary-darken-2;
        layout: vertical;
    }

    #requirements-input {
        width: 1fr;
        margin-bottom: 1;
    }

    #run-button {
        width: 100%;
    }

    LogPanel {
        height: 1fr;
    }

    ResultPanel {
        width: 42;
        height: 100%;
        border-left: solid $primary-darken-2;
    }

    .panel-title {
        text-style: bold;
        color: $accent;
    }

    .label-small {
        color: $text-muted;
        text-style: italic;
    }
    """

    BINDINGS = [
        ("ctrl+r", "run_graph", "Executar"),
        ("ctrl+l", "clear_log", "Netejar log"),
        ("a", "toggle_mode", "Safe/Auto"),
        ("q", "quit", "Sortir"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.runner = GraphRunner()
        self._selected_session = "macroai-session"

    # ------------------------------------------------------------------
    # Composicio de la pantalla
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal():
            yield ProjectPanel(id="project-panel")
            with Vertical(id="center-pane"):
                yield StatePanel(id="state-panel")
                with Vertical(id="input-area"):
                    yield Label("Requeriment del projecte:", classes="label-small")
                    yield Input(
                        placeholder="Descriu la funcionalitat a implementar...",
                        id="requirements-input",
                    )
                    yield Button("▶  Executar graf", id="run-button", variant="primary")
                yield LogPanel(id="log-panel")
            yield ResultPanel(id="result-panel")
        yield Footer()

    def on_mount(self) -> None:
        self._update_subtitle()
        # Always start in Safe mode (no persistence between runs).
        set_auto_approve(False)
        self.query_one(StatePanel).set_mode(False)
        self.query_one(LogPanel).add_system(
            "Benvingut a MacroAI. Selecciona una sessio i introdueix un requeriment."
        )
        self.query_one(LogPanel).add_system(
            "Mode actual: SAFE. Premsa 'a' per togglejar a AUTO."
        )

    # ------------------------------------------------------------------
    # Handlers dels missatges dels widgets fills
    # ------------------------------------------------------------------

    @on(ProjectPanel.SessionSelected)
    def _on_session_selected(self, msg: ProjectPanel.SessionSelected) -> None:
        self._selected_session = msg.session_id
        self._update_subtitle()
        self.query_one(LogPanel).add_system(
            f"Sessio seleccionada: {msg.session_id}"
        )

    @on(ProjectPanel.SessionCreated)
    def _on_session_created(self, msg: ProjectPanel.SessionCreated) -> None:
        self._selected_session = msg.session_id
        self._update_subtitle()
        self.query_one(LogPanel).add_system(
            f"Nova sessio creada: {msg.session_id}"
        )

    @on(Button.Pressed, "#run-button")
    def _on_run_pressed(self, _: Button.Pressed) -> None:
        self.action_run_graph()

    # ------------------------------------------------------------------
    # Accions (binding + programatic)
    # ------------------------------------------------------------------

    def action_run_graph(self) -> None:
        """Inicia l'execucio del graf si no hi ha una en curs."""
        if self.runner.is_running:
            self.query_one(LogPanel).add_system(
                "Ja hi ha una execucio en curs. Espera que acabi."
            )
            return
        requirements = self.query_one("#requirements-input", Input).value.strip()
        if not requirements:
            self.query_one(LogPanel).add_system(
                "Introdueix un requeriment abans d'executar."
            )
            return
        self._execute_graph(requirements)

    def action_clear_log(self) -> None:
        self.query_one(LogPanel).clear_log()

    def action_toggle_mode(self) -> None:
        """Toggle between Safe and Auto permission modes."""
        if self.runner.is_running:
            self.query_one(LogPanel).add_system(
                "No es pot canviar el mode mentre el graf corre.",
                is_error=True,
            )
            return
        new_value = not is_auto_approve()
        set_auto_approve(new_value)
        self.query_one(StatePanel).set_mode(new_value)
        label = "AUTO" if new_value else "SAFE"
        warn = "  (opencode escriura fitxers directament)" if new_value else ""
        self.query_one(LogPanel).add_system(f"Mode canviat a {label}.{warn}")
        self._update_subtitle()

    # ------------------------------------------------------------------
    # Worker principal (execucio asincrona del graf)
    # ------------------------------------------------------------------

    @work(exclusive=True)
    async def _execute_graph(self, requirements: str) -> None:
        """
        Worker de Textual: gestiona tot el cicle d'execucio del graf.

        @work(exclusive=True) garanteix que si es crida mentre ja corre,
        la nova crida es descarta automaticament.

        Dins el worker:
          - run_task  : executa el graf al ThreadPoolExecutor
          - poll_task : llegeix les cues i actualitza els widgets cada 80ms
          Les dues tasques corren concurrent en el bucle asyncio de Textual.
        """
        log = self.query_one(LogPanel)
        state_panel = self.query_one(StatePanel)
        result_panel = self.query_one(ResultPanel)
        btn = self.query_one("#run-button", Button)

        # Preparem la UI per a la nova execucio
        btn.disabled = True
        btn.label = "⏳  Executant..."
        log.clear_log()
        state_panel.reset()
        result_panel.clear()

        run_task = asyncio.create_task(
            self.runner.run(self._selected_session, requirements)
        )
        poll_task = asyncio.create_task(
            self._poll_queues(log, state_panel)
        )

        try:
            result = await run_task
            # Esperem que el poll buidi les cues restants
            await poll_task

            result_panel.show_result(
                result.get("generated_code", "(cap codi generat)"),
                result.get("output_dir", ""),
                result.get("task_index", 0),
                result.get("total_tasks", 0),
            )
            # Actualitzem la llista de sessions per reflectir la nova memoria guardada
            self.query_one(ProjectPanel)._refresh_list()

        except Exception as exc:
            log.add_system(f"Error durant l'execucio: {exc}", is_error=True)
            poll_task.cancel()
        finally:
            btn.disabled = False
            btn.label = "▶  Executar graf"

    async def _poll_queues(self, log: LogPanel, state: StatePanel) -> None:
        """
        Llegeix periodicament les cues del runner i actualitza els widgets.

        Continua mentre el graf corre O mentre queden items a les cues.
        El sleep de 80ms es un balanc entre responsivitat de la UI i CPU usage.
        """
        while (
            self.runner.is_running
            or not self.runner.log_queue.empty()
            or not self.runner.state_queue.empty()
        ):
            # Drena tots els logs disponibles en aquest cicle
            while not self.runner.log_queue.empty():
                try:
                    entry: LogEntry = self.runner.log_queue.get_nowait()
                    log.add_entry(entry)
                except asyncio.QueueEmpty:
                    break

            # Drena tots els snapshots d'estat disponibles en aquest cicle
            while not self.runner.state_queue.empty():
                try:
                    snap: StateSnapshot = self.runner.state_queue.get_nowait()
                    state.update_from_snapshot(snap)
                except asyncio.QueueEmpty:
                    break

            await asyncio.sleep(0.08)

    # ------------------------------------------------------------------
    # Cicle de vida
    # ------------------------------------------------------------------

    def _update_subtitle(self) -> None:
        mode = "AUTO" if is_auto_approve() else "SAFE"
        self.sub_title = f"[{mode}]  sessio: {self._selected_session}"

    def on_unmount(self) -> None:
        """Alliberem el thread pool en tancar l'aplicacio."""
        self.runner.shutdown()
