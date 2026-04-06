"""Abstract base class for all AcademiaOS sub-agents."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path

from src.config.schemas import ClassConfig
from src.observability.events import EventType, emit
from src.tools.vault import VaultTool

from .spawner import ClaudeSpawner

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"


class BaseAgent(ABC):
    """Abstract base for all AcademiaOS sub-agents.

    Subclasses must set ``agent_name`` and implement
    ``build_context`` and ``run``.
    """

    agent_name: str  # must be set by subclass

    def __init__(
        self,
        class_config: ClassConfig,
        vault: VaultTool,
        spawner: ClaudeSpawner,
        model: str,
    ) -> None:
        """Initialize the base agent.

        Args:
            class_config: Configuration for the target class.
            vault: VaultTool instance scoped to the class.
            spawner: ClaudeSpawner for subprocess invocations.
            model: Model identifier for CLI calls.
        """
        self.class_config = class_config
        self.vault = vault
        self.spawner = spawner
        self.model = model

    @abstractmethod
    def build_context(self) -> str:
        """Assemble vault context for injection into the prompt."""
        ...

    @abstractmethod
    def run(self, message: str, **kwargs: object) -> dict:
        """Execute the agent and return a result dict."""
        ...

    def load_prompt(self, prompt_name: str) -> str:
        """Load a system prompt from the prompts/ directory.

        Args:
            prompt_name: Filename stem (without extension).

        Returns:
            The contents of the prompt file.

        Raises:
            FileNotFoundError: If the prompt file does not exist.
        """
        path = PROMPTS_DIR / f"{prompt_name}.md"
        if not path.is_file():
            raise FileNotFoundError(f"Prompt not found: {path}")
        return path.read_text(encoding="utf-8")

    def emit_spawn(self, pid: int, context_size: int) -> None:
        """Emit an agent.spawn observability event.

        Args:
            pid: Process ID of the spawned subprocess.
            context_size: Size of the injected context in bytes.
        """
        emit(
            EventType.AGENT_SPAWN,
            {"pid": pid, "context_size": context_size},
            class_id=self.class_config.id,
            agent=self.agent_name,
        )

    def emit_complete(
        self, wall_time_ms: float, exit_code: int
    ) -> None:
        """Emit an agent.complete observability event.

        Args:
            wall_time_ms: Wall-clock time in milliseconds.
            exit_code: Subprocess exit code.
        """
        emit(
            EventType.AGENT_COMPLETE,
            {"wall_time_ms": wall_time_ms, "exit_code": exit_code},
            class_id=self.class_config.id,
            agent=self.agent_name,
        )
