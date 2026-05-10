"""
src/clients.py
==============
Agent client abstraction following SOLID principles.

SOLID MAP:
  S (SRP)  -> OpenCodeClient has ONE reason to change: the opencode CLI interface.
  O (OCP)  -> AgentFactory is open for extension (new roles/models) but closed
               for modification (existing roles never break).
  L (LSP)  -> Any AgentClient implementation can substitute another transparently.
  I (ISP)  -> AgentClient exposes only what nodes need: run(prompt, session_id).
  D (DIP)  -> Graph nodes depend on the AgentClient abstraction, not on concrete
               CLI wrappers. build_graph() receives clients via DI.

ARCHITECTURE:
  AgentClient (ABC)      <-- interface that all clients must implement
     └─ OpenCodeClient    <-- concrete: wraps `opencode run --model ...`

  AgentFactory            <-- creates configured clients per role (optimizer,
                               architect, complex_coder, simple_coder, finalizer)
"""

import os
import re
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import ClassVar


def _strip_ansi(text: str) -> str:
    """Remove terminal color codes from CLI output."""
    return re.sub(r'\x1b\[[0-9;]*[mGKHF]', '', text)


# =============================================================================
# AGENT CLIENT INTERFACE  (Dependency Inversion Principle)
# =============================================================================
# Nodes depend on this abstraction, never on concrete CLI wrappers.
# -----------------------------------------------------------------------------

class AgentClient(ABC):
    """
    Interface for AI agent clients.

    Every agent in the system (architect, coder, optimizer, finalizer)
    communicates through this single-method contract.
    """

    @abstractmethod
    def run(self, prompt: str, session_id: str = "") -> str:
        """
        Execute a prompt and return the plain-text response.

        Args:
            prompt:     The full prompt text to send.
            session_id: Optional session ID for continuity across calls.

        Returns:
            The agent's response as a clean string.

        Raises:
            RuntimeError: If the underlying subprocess fails.
        """
        ...


# =============================================================================
# OPENCODE CLIENT  (Single Responsibility Principle)
# =============================================================================
# Wraps ONE CLI tool (opencode). Model selection is a constructor parameter,
# not a separate implementation. This keeps the class focused and simple.
# -----------------------------------------------------------------------------

class OpenCodeClient(AgentClient):
    """
    Concrete agent client backed by the opencode CLI.

    Supports any model available in the opencode configuration via the
    `--model` flag (format: provider/model, e.g. 'opencode-go/deepseek-v4-pro').
    """

    def __init__(self, model: str, timeout: int = 180) -> None:
        self._model = model
        self._timeout = timeout

    @property
    def model(self) -> str:
        """The model identifier used by this client (provider/model format)."""
        return self._model

    def run(self, prompt: str, session_id: str = "") -> str:
        """
        Spawn `opencode run --model <model>` and return clean stdout.

        Session continuity is achieved via `--session` when session_id is
        provided, letting opencode maintain its own internal context.
        """
        cmd = ["opencode", "run", "--model", self._model]
        if session_id:
            cmd.extend(["--session", session_id])
        cmd.append(prompt)

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=self._timeout
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

    All model identifiers use the `provider/model` format expected by the
    opencode CLI (e.g. 'opencode-go/deepseek-v4-pro').

    Environment variables override defaults:
      MACROAI_OPTIMIZER_MODEL, MACROAI_ARCHITECT_MODEL,
      MACROAI_COMPLEX_MODEL,   MACROAI_SIMPLE_MODEL,
      MACROAI_FINALIZER_MODEL
    """

    optimizer: str = "opencode-go/deepseek-v4-flash"
    architect: str = "opencode-go/deepseek-v4-pro"
    complex_coder: str = "opencode-go/deepseek-v4-pro"
    simple_coder: str = "opencode-go/deepseek-v4-flash"
    finalizer: str = "opencode-go/deepseek-v4-pro"

    _ENV_MAP: ClassVar[dict[str, str]] = {
        "MACROAI_OPTIMIZER_MODEL": "optimizer",
        "MACROAI_ARCHITECT_MODEL": "architect",
        "MACROAI_COMPLEX_MODEL": "complex_coder",
        "MACROAI_SIMPLE_MODEL": "simple_coder",
        "MACROAI_FINALIZER_MODEL": "finalizer",
    }

    @classmethod
    def from_env(cls) -> "ModelConfig":
        """Create a ModelConfig, overriding defaults from environment variables."""
        overrides: dict[str, str] = {}
        for env_var, field_name in cls._ENV_MAP.items():
            value = os.getenv(env_var)
            if value:
                overrides[field_name] = value
        if overrides:
            # Use dataclass replace-like pattern via constructor
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
# Creates AgentClient instances per role. To add a new role or swap a model,
# extend the config or factory method — no existing code changes.
# -----------------------------------------------------------------------------

class AgentFactory:
    """
    Factory for creating fully-wired AgentClient instances per role.

    Usage:
        factory = AgentFactory()
        optimizer = factory.create_optimizer()
        architect = factory.create_architect()
        ...
    """

    def __init__(self, config: ModelConfig | None = None) -> None:
        self._config = config or ModelConfig.from_env()

    @property
    def config(self) -> ModelConfig:
        return self._config

    def create_optimizer(self) -> AgentClient:
        """Client for the optimizer node (prompt refinement)."""
        return OpenCodeClient(model=self._config.optimizer)

    def create_architect(self) -> AgentClient:
        """Client for the architect node (task planning & complexity classification)."""
        return OpenCodeClient(model=self._config.architect)

    def create_complex_coder(self) -> AgentClient:
        """Client for complex tasks (algorithms, business logic, integrations)."""
        return OpenCodeClient(model=self._config.complex_coder)

    def create_simple_coder(self) -> AgentClient:
        """Client for simple tasks (boilerplate, data structures, scaffolding)."""
        return OpenCodeClient(model=self._config.simple_coder)

    def create_finalizer(self) -> AgentClient:
        """Client for the finalizer node (session memory archival)."""
        return OpenCodeClient(model=self._config.finalizer)
