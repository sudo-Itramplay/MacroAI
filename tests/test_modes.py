"""
tests/test_modes.py
====================
Unit tests for the Safe/Auto permission mode toggle in clients.py.

WHAT WE TEST:
  - Default mode is Safe.
  - set_auto_approve flips the flag.
  - OpenCodeClient.run includes/excludes --dangerously-skip-permissions
    according to the active mode.
  - --variant flag is included when configured.
  - -f attachments are passed when files exist.
"""

import subprocess
from unittest.mock import patch, MagicMock

import pytest

from src.clients import (
    OpenCodeClient,
    is_auto_approve,
    set_auto_approve,
)


@pytest.fixture(autouse=True)
def _reset_mode():
    """Each test starts in Safe mode."""
    set_auto_approve(False)
    yield
    set_auto_approve(False)


def _fake_completed(stdout: str = "ok", returncode: int = 0):
    proc = MagicMock()
    proc.stdout = stdout
    proc.stderr = ""
    proc.returncode = returncode
    return proc


def test_default_is_safe():
    assert is_auto_approve() is False


def test_toggle_mode():
    set_auto_approve(True)
    assert is_auto_approve() is True
    set_auto_approve(False)
    assert is_auto_approve() is False


def test_safe_mode_omits_dangerous_flag():
    client = OpenCodeClient(model="provider/model")
    with patch.object(subprocess, "run", return_value=_fake_completed()) as m:
        client.run("hello")
    cmd = m.call_args[0][0]
    assert "--dangerously-skip-permissions" not in cmd


def test_auto_mode_includes_dangerous_flag():
    set_auto_approve(True)
    client = OpenCodeClient(model="provider/model")
    with patch.object(subprocess, "run", return_value=_fake_completed()) as m:
        client.run("hello")
    cmd = m.call_args[0][0]
    assert "--dangerously-skip-permissions" in cmd


def test_variant_flag_passed():
    client = OpenCodeClient(model="provider/model", variant="minimal")
    with patch.object(subprocess, "run", return_value=_fake_completed()) as m:
        client.run("hi")
    cmd = m.call_args[0][0]
    assert "--variant" in cmd
    assert cmd[cmd.index("--variant") + 1] == "minimal"


def test_no_continue_flag_ever():
    client = OpenCodeClient(model="provider/model")
    with patch.object(subprocess, "run", return_value=_fake_completed()) as m:
        client.run("a")
        client.run("b")
        client.run("c")
    for call in m.call_args_list:
        assert "--continue" not in call[0][0]


def test_files_attached_when_exist(tmp_path):
    plan = tmp_path / "plan.md"
    plan.write_text("# plan")
    missing = tmp_path / "missing.md"

    client = OpenCodeClient(model="provider/model")
    with patch.object(subprocess, "run", return_value=_fake_completed()) as m:
        client.run("hi", files=[str(plan), str(missing)])
    cmd = m.call_args[0][0]
    assert "-f" in cmd
    assert str(plan) in cmd
    # Missing files are skipped, not passed to opencode.
    assert str(missing) not in cmd


def test_cwd_passed_as_dir(tmp_path):
    client = OpenCodeClient(model="provider/model")
    with patch.object(subprocess, "run", return_value=_fake_completed()) as m:
        client.run("hi", cwd=str(tmp_path))
    cmd = m.call_args[0][0]
    assert "--dir" in cmd
    assert cmd[cmd.index("--dir") + 1] == str(tmp_path)


def test_timeout_raises_runtime_error():
    client = OpenCodeClient(model="provider/model", timeout=1)
    with patch.object(
        subprocess, "run", side_effect=subprocess.TimeoutExpired(cmd="opencode", timeout=1)
    ):
        with pytest.raises(RuntimeError, match="timeout"):
            client.run("hi")
