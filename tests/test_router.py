# tests/test_router.py
import pytest
from src.graph import route_task
from src.agents import AgentState


def test_route_task_complexa():
    estat_simulat: AgentState = {
        "project_requirements": "Test",
        "current_task": "Test",
        "complexity": "complexa",
        "generated_code": "",
        "session_id": "test-session",
        "memory_context": ""
    }

    resultat = route_task(estat_simulat)
    assert resultat == "claude", "Les tasques complexes han d'anar a Claude"


def test_route_task_simple():
    estat_simulat: AgentState = {
        "project_requirements": "Test",
        "current_task": "Test",
        "complexity": "simple",
        "generated_code": "",
        "session_id": "test-session",
        "memory_context": ""
    }

    resultat = route_task(estat_simulat)
    assert resultat == "opencode", "Les tasques simples han d'anar a Open Code Go"
