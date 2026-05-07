"""
tests/test_router.py
====================
UNIT TESTS for the routing logic.

WHAT WE TEST:
  The route_task() function in graph.py is the "traffic cop" that decides
  whether a task goes to Claude (complex) or OpenCode (simple).
  These tests verify that decision is correct for both cases.

WHAT WE DON'T TEST:
  We do NOT call actual LLMs here. The tests run entirely offline.
  That's why they're fast and safe to run in CI (GitHub Actions).

HOW TO RUN:
  $ pytest tests/ -v
"""

import pytest
from src.graph import route_task
from src.agents import AgentState


def test_route_task_complexa():
    """
    GIVEN an AgentState where the Architect marked complexity as 'complexa'
    WHEN route_task() is called
    THEN it should return 'claude' so the hard task goes to the advanced coder.
    """
    estat_simulat: AgentState = {
        "project_requirements": "Test",
        "current_task": "Test",
        "complexity": "complexa",   # <-- the key input
        "generated_code": "",
        "session_id": "test-session",
        "memory_context": ""
    }

    resultat = route_task(estat_simulat)

    assert resultat == "claude", "Les tasques complexes han d'anar a Claude"


def test_route_task_simple():
    """
    GIVEN an AgentState where the Architect marked complexity as 'simple'
    WHEN route_task() is called
    THEN it should return 'opencode' so the easy task goes to the basic coder.
    """
    estat_simulat: AgentState = {
        "project_requirements": "Test",
        "current_task": "Test",
        "complexity": "simple",     # <-- the key input
        "generated_code": "",
        "session_id": "test-session",
        "memory_context": ""
    }

    resultat = route_task(estat_simulat)

    assert resultat == "opencode", "Les tasques simples han d'anar a Open Code Go"
