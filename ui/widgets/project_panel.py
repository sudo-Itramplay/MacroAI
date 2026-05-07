"""
ui/widgets/project_panel.py
============================
Panel esquerre de la UI: llista de sessions i creació de noves.

DESCOBERTA DE SESSIONS
-----------------------
Escanegem el directori .macroai_memory/ al directori de treball actual.
Cada fitxer .md correspon a una sessió (session_id = nom del fitxer sense .md).
Ordenem alfabèticament per fer la llista predictible.

COMUNICACIÓ AMB EL PARE (l'App)
---------------------------------
Usem el sistema de missatges de Textual en comptes de callbacks.
  ProjectPanel.SessionSelected  -> l'usuari ha clicat una sessió existent
  ProjectPanel.SessionCreated   -> l'usuari ha creat una nova sessió

L'App escolta aquests missatges amb @on(ProjectPanel.SessionSelected).
"""

import os
from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Label, ListView, ListItem, Input, Button


class _SessionItem(ListItem):
    """
    ListItem personalitzat que emmagatzema el session_id directament.
    Evitem extreure el text del Label (fràgil) guardant el valor al widget.
    """
    def __init__(self, session_id: str) -> None:
        super().__init__(Label(f"  {session_id}"))
        self.session_id = session_id


class ProjectPanel(Widget):
    """
    Panel lateral esquerre per a la gestió de sessions de projecte.

    Mostra les sessions existents i permet crear-ne de noves.
    Emet missatges Textual cap a l'App quan l'estat canvia.
    """

    MEMORY_DIR = ".macroai_memory"

    DEFAULT_CSS = """
    ProjectPanel {
        layout: vertical;
        padding: 1;
    }
    ProjectPanel #session-list {
        height: 1fr;
        border: solid $primary-darken-3;
        margin-bottom: 1;
    }
    ProjectPanel .label-small {
        color: $text-muted;
        text-style: italic;
    }
    ProjectPanel #create-session-btn {
        width: 100%;
        margin-top: 1;
    }
    """

    # -- Missatges de Textual emesos cap a l'App --

    class SessionSelected(Message):
        """L'usuari ha seleccionat una sessió existent de la llista."""
        def __init__(self, session_id: str) -> None:
            self.session_id = session_id
            super().__init__()

    class SessionCreated(Message):
        """L'usuari ha introduït un nou nom de sessió i confirmat."""
        def __init__(self, session_id: str) -> None:
            self.session_id = session_id
            super().__init__()

    def compose(self) -> ComposeResult:
        yield Label("PROJECTES", classes="panel-title")
        yield ListView(id="session-list")
        yield Label("Nova sessió:", classes="label-small")
        yield Input(placeholder="nom-de-sessio", id="new-session-input")
        yield Button("+ Crear sessió", id="create-session-btn", variant="success")

    def on_mount(self) -> None:
        self._refresh_list()

    def _refresh_list(self) -> None:
        """
        Omple el ListView amb les sessions descobertes al directori de memòria.
        Crida-la després de crear o eliminar sessions per mantenir la llista fresca.
        """
        lv = self.query_one("#session-list", ListView)
        lv.clear()

        if not os.path.isdir(self.MEMORY_DIR):
            lv.append(ListItem(Label("  (cap sessió)")))
            return

        sessions = sorted(
            fname[:-3]
            for fname in os.listdir(self.MEMORY_DIR)
            if fname.endswith(".md")
        )

        if not sessions:
            lv.append(ListItem(Label("  (cap sessió)")))
        else:
            for s in sessions:
                lv.append(_SessionItem(s))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Delegació de la selecció a l'App via missatge Textual."""
        if isinstance(event.item, _SessionItem):
            self.post_message(self.SessionSelected(event.item.session_id))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id != "create-session-btn":
            return
        inp = self.query_one("#new-session-input", Input)
        session_id = inp.value.strip()
        if not session_id:
            return
        inp.value = ""
        self.post_message(self.SessionCreated(session_id))
        # Refresquem per si el nou fitxer ja existia o s'acaba de crear
        self.set_timer(0.5, self._refresh_list)
