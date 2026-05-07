# tests/test_router.py
import pytest
from main import route_task, AgentState

def test_route_task_complexa():
    # Definim un estat simulat amb la sortida esperada de Kimi
    estat_simulat: AgentState = {
        "project_requirements": "Test",
        "current_task": "Test",
        "complexity": "complexa",
        "generated_code": ""
    }
    
    # Comprovem que l'enrutador dirigeix correctament a Claude
    resultat = route_task(estat_simulat)
    assert resultat == "claude", "Les tasques complexes han d'anar a Claude"

def test_route_task_simple():
    # Definim un estat simulat alternatiu
    estat_simulat: AgentState = {
        "project_requirements": "Test",
        "current_task": "Test",
        "complexity": "simple",
        "generated_code": ""
    }
    
    # Comprovem que l'enrutador dirigeix a Open Code Go
    resultat = route_task(estat_simulat)
    assert resultat == "opencode", "Les tasques simples han d'anar a Open Code Go"
