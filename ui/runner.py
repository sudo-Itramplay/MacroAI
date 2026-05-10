"""
ui/runner.py
============
Async bridge between LangGraph (sync, blocking) and the Textual UI (async).

Uses ThreadPoolExecutor + call_soon_threadsafe for thread-safe Queue injection.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Optional

from src.graph import build_graph
from src.agents import configure_log_sink, AgentState, load_memory
from src.clients import AgentFactory


@dataclass
class LogEntry:
    agent: str       # 'optimizer'|'architect'|'complex'|'simple'|'finalizer'|'system'
    message: str
    is_error: bool = False


@dataclass
class StateSnapshot:
    node_name: str
    partial_state: dict


class GraphRunner:
    def __init__(self) -> None:
        self.log_queue: asyncio.Queue[LogEntry] = asyncio.Queue()
        self.state_queue: asyncio.Queue[StateSnapshot] = asyncio.Queue()
        self._executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="macroai-graph"
        )
        self._running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._factory = AgentFactory()
        self._graph = build_graph(self._factory)

    def _log_sink_callback(self, agent: str, message: str, is_error: bool = False) -> None:
        if self._loop and not self._loop.is_closed():
            entry = LogEntry(agent=agent, message=message, is_error=is_error)
            self._loop.call_soon_threadsafe(self.log_queue.put_nowait, entry)

    def _run_graph_sync(self, initial_state: AgentState) -> dict:
        merged = dict(initial_state)
        for chunk in self._graph.stream(initial_state):
            for node_name, partial_state in chunk.items():
                snap = StateSnapshot(node_name=node_name, partial_state=partial_state)
                if self._loop:
                    self._loop.call_soon_threadsafe(self.state_queue.put_nowait, snap)
                merged.update(partial_state)
        return merged

    async def run(self, session_id: str, requirements: str) -> dict:
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
