"""
tests/test_router.py
====================
UNIT TESTS for the routing logic.

WHAT WE TEST:
  The route_next() function decides:
    - "complex" when complexity is "complexa" and tasks remain
    - "simple"  when complexity is "simple" and tasks remain
    - "finalize" when all tasks are done

HOW TO RUN:
  $ pytest tests/ -v
"""

import pytest
from src.graph import route_next


def build_state(complexity: str, task_index: int = 0, total_tasks: int = 1) -> dict:
    return {
        "project_requirements": "Test",
        "current_task": "Test task",
        "complexity": complexity,
        "generated_code": "",
        "session_id": "test-session",
        "memory_context": "",
        "plan_md": "",
        "task_index": task_index,
        "total_tasks": total_tasks,
        "target_file": "test.py",
        "output_dir": "/tmp/test",
    }


def test_route_complexa():
    """Complex task with remaining tasks → 'complex'"""
    assert route_next(build_state("complexa", 0, 3)) == "complex"


def test_route_simple():
    """Simple task with remaining tasks → 'simple'"""
    assert route_next(build_state("simple", 1, 3)) == "simple"


def test_route_finalize_all_done():
    """All tasks done → 'finalize'"""
    assert route_next(build_state("complexa", 3, 3)) == "finalize"
    assert route_next(build_state("simple", 2, 2)) == "finalize"


def test_route_finalize_empty_plan():
    """Empty plan (0 tasks) → 'finalize'"""
    assert route_next(build_state("", 0, 0)) == "finalize"
