"""
ui/runner.py
============
Pont asíncron entre LangGraph (síncron, blocking) i la UI Textual (asíncron).

PROBLEMA FONAMENTAL
-------------------
LangGraph i els tres CLIs (kimi, claude, opencode) bloquegen el fil
d'execució mentre esperen la resposta del subprocés. Si els executéssim
directament al bucle asyncio de Textual, congelaríem tota la UI.

SOLUCIÓ: asyncio + ThreadPoolExecutor
--------------------------------------
- El graf corre en un ThreadPoolExecutor d'1 worker (execució seqüencial).
- asyncio.get_event_loop().run_in_executor() delega el treball al thread
  sense bloquejar el bucle principal.
- El thread del graf NO pot escriure directament a les asyncio.Queue perquè
  no és thread-safe. Usa _loop.call_soon_threadsafe() que és l'únic camí
  segur per injectar crides al bucle asyncio des d'un thread extern.

FLUX DE DADES
-------------
  Thread del graf:
    agents._emit()  ->  _log_sink_callback()  ->  call_soon_threadsafe(log_queue.put_nowait)
    graph.stream()  ->  StateSnapshot         ->  call_soon_threadsafe(state_queue.put_nowait)

  Bucle asyncio (UI):
    _poll_queues()  ->  log_queue.get_nowait()   ->  LogPanel.add_entry()
                    ->  state_queue.get_nowait()  ->  StatePanel.update_from_snapshot()
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Optional

from src.graph import build_graph
from src.agents import configure_log_sink, AgentState, load_memory


@dataclass
class LogEntry:
    """Un missatge de log d'un agent CLI o del sistema de control."""
    agent: str        # 'kimi' | 'claude' | 'opencode' | 'system'
    message: str
    is_error: bool = False


@dataclass
class StateSnapshot:
    """
    Captura de l'estat del graf just després de completar un node.
    LangGraph emet un d'aquests per cada node que finalitza.
    """
    node_name: str    # nom del node completat ('architect', 'claude', etc.)
    partial_state: dict  # només els camps que el node ha actualitzat


class GraphRunner:
    """
    Orquestra l'execució del graf LangGraph de forma no bloquejant.

    Atributs públics (llegir des de la UI):
        log_queue   : asyncio.Queue[LogEntry]    -- logs dels CLIs
        state_queue : asyncio.Queue[StateSnapshot] -- actualitzacions de node
        is_running  : bool                        -- True mentre el graf corre
    """

    def __init__(self) -> None:
        self.log_queue: asyncio.Queue[LogEntry] = asyncio.Queue()
        self.state_queue: asyncio.Queue[StateSnapshot] = asyncio.Queue()

        # 1 worker = execució seqüencial del graf, sense condicions de carrera
        self._executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="macroai-graph"
        )
        self._running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._graph = build_graph()

    # ------------------------------------------------------------------
    # Privats
    # ------------------------------------------------------------------

    def _log_sink_callback(
        self, agent: str, message: str, is_error: bool = False
    ) -> None:
        """
        Callback registrat a agents.py. S'invoca des del thread del executor.
        call_soon_threadsafe és imprescindible: asyncio.Queue.put_nowait no és
        thread-safe quan es crida des d'un thread extern al bucle asyncio.
        """
        if self._loop and not self._loop.is_closed():
            entry = LogEntry(agent=agent, message=message, is_error=is_error)
            self._loop.call_soon_threadsafe(self.log_queue.put_nowait, entry)

    def _run_graph_sync(self, initial_state: AgentState) -> dict:
        """
        Executa graph.stream() de forma síncrona. Corre dins el thread pool.

        graph.stream() en comptes de graph.invoke() ens dona visibilitat dels
        estats intermedis: emetem un StateSnapshot per cada node completat
        sense esperar que tot el graf acabi.
        """
        merged = dict(initial_state)
        # chunk = {'nom_node': {camp: valor_nou, ...}}
        for chunk in self._graph.stream(initial_state):
            for node_name, partial_state in chunk.items():
                snap = StateSnapshot(
                    node_name=node_name, partial_state=partial_state
                )
                if self._loop:
                    self._loop.call_soon_threadsafe(
                        self.state_queue.put_nowait, snap
                    )
                merged.update(partial_state)
        return merged

    # ------------------------------------------------------------------
    # Públics
    # ------------------------------------------------------------------

    async def run(self, session_id: str, requirements: str) -> dict:
        """
        Punt d'entrada asíncron per a la UI. Inicia el graf i retorna
        l'AgentState final quan el graf arriba a END.

        La UI crida aquest mètode via asyncio.create_task() per no bloquejar-se.
        """
        self._loop = asyncio.get_running_loop()
        self._running = True
        configure_log_sink(self._log_sink_callback)

        memory_context = load_memory(session_id)
        initial_state: AgentState = {
            "project_requirements": requirements,
            "current_task": "",
            "complexity": "",
            "generated_code": "",
            "session_id": session_id,
            "memory_context": memory_context,
        }

        await self.log_queue.put(
            LogEntry("system", f"Sessió iniciada: {session_id}")
        )
        if memory_context:
            await self.log_queue.put(
                LogEntry("system", "Memòria anterior carregada.")
            )

        try:
            result = await self._loop.run_in_executor(
                self._executor, self._run_graph_sync, initial_state
            )
            await self.log_queue.put(
                LogEntry("system", "Graf completat correctament.")
            )
            return result
        except Exception as exc:
            await self.log_queue.put(
                LogEntry("system", f"Error fatal: {exc}", is_error=True)
            )
            raise
        finally:
            self._running = False
            configure_log_sink(None)  # netegem el sink per evitar fuites

    @property
    def is_running(self) -> bool:
        return self._running

    def shutdown(self) -> None:
        """Allibera el thread pool quan l'aplicació tanca."""
        self._executor.shutdown(wait=False)
