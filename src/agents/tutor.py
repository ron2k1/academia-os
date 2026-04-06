"""Tutor agent for interactive class-specific tutoring sessions."""
from __future__ import annotations

from pydantic import BaseModel

from src.agents.base import BaseAgent
from src.agents.tutor_helpers import parse_memory_update, write_session


class TutorResult(BaseModel):
    """Result of a tutor session."""

    response: str
    memory_update: dict | None = None
    session_file: str


class TutorAgent(BaseAgent):
    """Interactive tutor scoped to a single class.

    Loads class context from the vault, runs a tutoring session
    via the Claude CLI, parses memory updates, and logs the session.
    """

    agent_name = "tutor"

    def build_context(self) -> str:
        """Load _index.md, context.md, topics.md, and last 3 sessions.

        Returns:
            Assembled context string for prompt injection.
        """
        parts: list[str] = []
        for path in ("_index.md", "context.md", "topics.md"):
            if self.vault.exists(path):
                parts.append(f"## {path}\n{self.vault.read(path)}")
        sessions = sorted(self.vault.list("sessions/"))[-3:]
        for s in sessions:
            name = s.split("/")[-1] if "/" in s else s
            parts.append(f"## {name}\n{self.vault.read(s)}")
        return "\n\n".join(parts)

    def run(self, message: str, **kwargs: object) -> dict:
        """Run a tutor session.

        Args:
            message: The student's question or topic.

        Returns:
            TutorResult as a dict.
        """
        context = self.build_context()
        system_prompt = self.load_prompt("tutor")
        system_prompt = system_prompt.replace(
            "{CLASS_NAME}", self.class_config.name
        )
        result = self.spawner.spawn(
            message=message,
            system_prompt=system_prompt,
            model=self.model,
            context=context,
        )
        self.emit_complete(result.wall_time_ms, result.exit_code)
        memory_update = parse_memory_update(result.stdout)
        session_file = write_session(
            self.vault,
            self.class_config.id,
            message,
            result.stdout,
        )
        return TutorResult(
            response=result.stdout,
            memory_update=memory_update,
            session_file=session_file,
        ).model_dump()
