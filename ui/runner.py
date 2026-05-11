"""
ui/runner.py
============
Async bridge between LangGraph (sync, blocking) and the Textual UI (async).

Uses ThreadPoolExecutor + call_soon_threadsafe for thread-safe Queue injection.

THREAD-SAFETY CONTRACT:
  - _run_graph_sync() runs in a ThreadPoolExecutor worker thread.
  - _log_sink_callback() and _run_graph_sync() use call_soon_threadsafe()
    to safely enqueue LogEntry and StateSnapshot objects into asyncio Queues.
  - The UI's _poll_queues() drains these queues from the main asyncio loop.
  - configure_log_sink(None) in the finally block clears the global sink
    so no stale references leak between runs.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Optional

from src.graph import build_graph
from src.agents import configure_log_sink, AgentState, MemoryStore
from src.clients import AgentFactory


@dataclass
class LogEntry:
    """A single log line emitted by a graph node or the runner itself."""
    agent: str       # 'optimizer'|'architect'|'complex'|'simple'|'finalizer'|'system'
    message: str
    is_error: bool = False


@dataclass
class StateSnapshot:
    """Partial state update from a single graph node execution."""
    node_name: str
    partial_state: dict


class GraphRunner:
    """Orchestrates graph execution from the Textual UI.

    Responsibilities:
      - Builds the LangGraph from an AgentFactory
      - Runs the graph in a background thread (ThreadPoolExecutor)
      - Bridges log entries and state snapshots to the UI via asyncio Queues
      - Manages the MemoryStore for session persistence

    The factory is injected via constructor (DIP) for testability.
    """

    def __init__(self, factory: AgentFactory | None = None) -> None:
        self.log_queue: asyncio.Queue[LogEntry] = asyncio.Queue()
        self.state_queue: asyncio.Queue[StateSnapshot] = asyncio.Queue()
        self._executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="macroai-graph"
        )
        self._running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._factory = factory or AgentFactory()
        self._graph = build_graph(self._factory)

    def _log_sink_callback(self, agent: str, message: str, is_error: bool = False) -> None:
        if self._loop and not self._loop.is_closed():
            entry = LogEntry(agent=agent, message=message, is_error=is_error)
            self._loop.call_soon_threadsafe(self.log_queue.put_nowait, entry)

    def _run_graph_sync(self, initial_state: AgentState) -> dict:
        merged = dict(initial_state)
        for chunk in self._graph.stream(initial_state):
            for node_name, partial_state in chunk.items():
                if partial_state is None:
                    continue
                snap = StateSnapshot(node_name=node_name, partial_state=partial_state)
                if self._loop:
                    self._loop.call_soon_threadsafe(self.state_queue.put_nowait, snap)
                merged.update(partial_state)
        return merged

    async def run(self, session_id: str, requirements: str) -> dict:
        """Execute the full graph for a session. Returns the final merged state."""
        self._loop = asyncio.get_running_loop()
        self._running = True
        configure_log_sink(self._log_sink_callback)

        store = MemoryStore()
        memory_context = store.load_memory(session_id)
        initial_state: AgentState = {
            "project_requirements": requirements,
            "current_task": "",
            "complexity": "",
            "generated_code": "",
            "session_id": session_id,
            "memory_context": memory_context,
            "plan_md": "",
            "task_index": 0,
            "total_tasks": 0,
            "target_file": "",
            "output_dir": "",
        }

        await self.log_queue.put(LogEntry("system", f"Sessio iniciada: {session_id}"))
        if memory_context:
            await self.log_queue.put(LogEntry("system", "Memoria anterior carregada."))

        try:
            result = await self._loop.run_in_executor(
                self._executor, self._run_graph_sync, initial_state
            )
            await self.log_queue.put(LogEntry("system", "Graf completat correctament."))
            return result
        except Exception as exc:
            await self.log_queue.put(LogEntry("system", f"Error fatal: {exc}", is_error=True))
            raise
        finally:
            self._running = False
            configure_log_sink(None)

    @property
    def is_running(self) -> bool:
        return self._running

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False)
