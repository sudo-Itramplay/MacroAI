"""
tests/test_scaffolder.py
=========================
Unit tests for the scaffolder_node.

WHAT WE TEST:
  - Creates parent dirs and empty target files declared in plan_md.
  - Skips files that already exist (never overwrites).
  - Handles a missing output_dir or plan gracefully.
"""

import os

from src.agents import make_scaffolder_node


_PLAN = """\
# Project Plan: Test

## Tasks

### [SIMPLE] Models
- **File**: `src/models.py`
- **Description**: dataclasses

### [COMPLEX] Engine
- **File**: `src/engine/core.py`
- **Description**: main loop

### [SIMPLE] Config
- **File**: `config.py`
- **Description**: env loader
"""


def test_scaffolder_creates_files_and_dirs(tmp_path):
    node = make_scaffolder_node()
    node({"output_dir": str(tmp_path), "plan_md": _PLAN})

    expected = ["src/models.py", "src/engine/core.py", "config.py"]
    for rel in expected:
        path = tmp_path / rel
        assert path.exists(), f"Expected {rel} to be created"
        assert path.read_text() == "", f"{rel} should be empty"


def test_scaffolder_skips_existing(tmp_path):
    existing = tmp_path / "src" / "models.py"
    existing.parent.mkdir(parents=True)
    existing.write_text("# already here")

    node = make_scaffolder_node()
    node({"output_dir": str(tmp_path), "plan_md": _PLAN})

    # Existing content untouched
    assert existing.read_text() == "# already here"
    # New ones created
    assert (tmp_path / "src" / "engine" / "core.py").exists()
    assert (tmp_path / "config.py").exists()


def test_scaffolder_no_plan_returns_empty(tmp_path):
    node = make_scaffolder_node()
    result = node({"output_dir": str(tmp_path), "plan_md": ""})
    assert result == {}
    assert os.listdir(tmp_path) == []


def test_scaffolder_no_output_dir_returns_empty(tmp_path):
    node = make_scaffolder_node()
    result = node({"output_dir": "", "plan_md": _PLAN})
    assert result == {}
