"""
src/clients.py
==============
Agent client abstraction following SOLID principles.

SOLID MAP:
  S (SRP)  -> OpenCodeClient has ONE reason to change: the opencode CLI interface.
  O (OCP)  -> AgentFactory is open for extension (new roles/models) but closed
               for modification (existing roles never break).
  L (LSP)  -> Any AgentClient implementation can substitute another transparently.
  I (ISP)  -> AgentClient exposes only what nodes need: run(prompt, ...).
  D (DIP)  -> Graph nodes depend on the AgentClient abstraction, not on concrete
               CLI wrappers. build_graph() receives clients via DI.

ARCHITECTURE:
  AgentClient (ABC)      <-- interface that all clients must implement
     └─ OpenCodeClient    <-- concrete: wraps `opencode run --model ...`

  AgentFactory            <-- creates configured clients per role (optimizer,
                               architect, complex_coder, simple_coder, finalizer)

PERMISSION MODES (Safe / Auto):
  Safe (default) -> opencode runs without --dangerously-skip-permissions.
                    Coders return code as text; the executor writes the file.
  Auto           -> opencode is given --dangerously-skip-permissions and may
                    use its native write tool to modify files directly.
                    Toggled at runtime via set_auto_approve(True).

NO --continue:
  Each call is independent. Context the model needs (plan, memory, prior code)
  is passed via -f file attachments at call time. This keeps prompts bounded
  and prevents the unbounded session-history growth that caused timeouts.
"""

import os
import re
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar


# Runtime permission mode. Default Safe. Toggled by the UI (or tests).
_auto_approve: bool = False


def set_auto_approve(value: bool) -> None:
    """Enable/disable opencode's --dangerously-skip-permissions for new calls."""
    global _auto_approve
    _auto_approve = bool(value)


def is_auto_approve() -> bool:
    """Current permission mode. True = Auto (auto-approve), False = Safe."""
    return _auto_approve


def _strip_ansi(text: str) -> str:
    """Remove terminal color codes from CLI output."""
    return re.sub(r"\x1b\[[0-9;]*[mGKHF]", "", text)


def _resolve_timeout(override: int | None) -> int:
    """Return the effective timeout: explicit override, env var, or default 600."""
    if override is not None:
        return override
    try:
        return int(os.getenv("MACROAI_TIMEOUT", "600"))
    except (ValueError, TypeError):
        return 600


# =============================================================================
# AGENT CLIENT INTERFACE  (Dependency Inversion Principle)
# =============================================================================


class AgentClient(ABC):
    """Interface for AI agent clients."""

    @abstractmethod
    def run(
        self,
        prompt: str,
        session_id: str = "",
        files: list[str] | None = None,
        cwd: str | None = None,
    ) -> str:
        """
        Execute a prompt and return the plain-text response.

        Args:
            prompt:     The full prompt text to send.
            session_id: Reserved for future use (currently unused — see module docstring).
            files:      Optional file paths to attach via opencode's -f flag.
            cwd:        Optional working directory for opencode (--dir).

        Returns:
            The agent's response as a clean string.

        Raises:
            RuntimeError: If the underlying subprocess fails or times out.
        """
        ...


# =============================================================================
# OPENCODE CLIENT  (Single Responsibility Principle)
# =============================================================================


class OpenCodeClient(AgentClient):
    """
    Concrete agent client backed by the opencode CLI.

    Each call is a fresh `opencode run` invocation. Context the model needs
    must be passed in the prompt or via the `files` parameter (-f attachments).
    """

    def __init__(
        self,
        model: str,
        timeout: int | None = None,
        variant: str = "",
    ) -> None:
        self._model = model
        self._timeout = _resolve_timeout(timeout)
        self._variant = variant

    @property
    def model(self) -> str:
        return self._model

    @property
    def variant(self) -> str:
        return self._variant

    def run(
        self,
        prompt: str,
        session_id: str = "",
        files: list[str] | None = None,
        cwd: str | None = None,
    ) -> str:
        """Spawn `opencode run` and return clean stdout."""
        cmd: list[str] = ["opencode", "run", "--model", self._model]

        if self._variant:
            cmd.extend(["--variant", self._variant])

        if cwd:
            cmd.extend(["--dir", cwd])

        if is_auto_approve():
            cmd.append("--dangerously-skip-permissions")

        for path in files or []:
            if path and os.path.exists(path):
                cmd.extend(["-f", path])

        cmd.append(prompt)

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=self._timeout
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(
                f"OpenCode[{self._model}] timeout after {self._timeout}s. "
                f"Increase MACROAI_TIMEOUT (env var) or use a faster model."
            )

        if result.returncode != 0:
            raise RuntimeError(
                f"OpenCode[{self._model}] error: {result.stderr.strip()}"
            )
        return _strip_ansi(result.stdout).strip()


# =============================================================================
# MODEL CONFIG  (Value Object)
# =============================================================================


@dataclass(frozen=True)
class ModelConfig:
    """
    Immutable configuration mapping roles to opencode model identifiers.

    Environment variables override defaults:
      MACROAI_OPTIMIZER_MODEL, MACROAI_ARCHITECT_MODEL,
      MACROAI_COMPLEX_MODEL,   MACROAI_SIMPLE_MODEL,
      MACROAI_FINALIZER_MODEL
    """

    optimizer: str = "opencode-go/deepseek-v4-flash"
    architect: str = "opencode-go/mimo-v2.5-pro"
    complex_coder: str = "opencode-go/mimo-v2.5-pro"
    simple_coder: str = "opencode-go/deepseek-v4-flash"
    finalizer: str = "opencode-go/kimi-K2.6"

    _ENV_MAP: ClassVar[dict[str, str]] = {
        "MACROAI_OPTIMIZER_MODEL": "optimizer",
        "MACROAI_ARCHITECT_MODEL": "architect",
        "MACROAI_COMPLEX_MODEL": "complex_coder",
        "MACROAI_SIMPLE_MODEL": "simple_coder",
        "MACROAI_FINALIZER_MODEL": "finalizer",
    }

    @classmethod
    def from_env(cls) -> "ModelConfig":
        overrides: dict[str, str] = {}
        for env_var, field_name in cls._ENV_MAP.items():
            value = os.getenv(env_var)
            if value:
                overrides[field_name] = value
        if overrides:
            defaults = {
                "optimizer": cls.optimizer,
                "architect": cls.architect,
                "complex_coder": cls.complex_coder,
                "simple_coder": cls.simple_coder,
                "finalizer": cls.finalizer,
            }
            defaults.update(overrides)
            return cls(**defaults)
        return cls()


# =============================================================================
# AGENT FACTORY  (Open/Closed Principle)
# =============================================================================


class AgentFactory:
    """
    Factory for creating fully-wired AgentClient instances per role.

    Roles tagged "fast" (optimizer, simple_coder) get --variant minimal so the
    model spends less effort on reasoning. Roles handling architecture or
    complex code get full reasoning effort.
    """

    def __init__(self, config: ModelConfig | None = None) -> None:
        self._config = config or ModelConfig.from_env()

    @property
    def config(self) -> ModelConfig:
        return self._config

    def create_optimizer(self) -> AgentClient:
        return OpenCodeClient(model=self._config.optimizer, variant="minimal")

    def create_architect(self) -> AgentClient:
        return OpenCodeClient(model=self._config.architect)

    def create_complex_coder(self) -> AgentClient:
        return OpenCodeClient(model=self._config.complex_coder)

    def create_simple_coder(self) -> AgentClient:
        return OpenCodeClient(model=self._config.simple_coder, variant="minimal")

    def create_finalizer(self) -> AgentClient:
        return OpenCodeClient(model=self._config.finalizer)
