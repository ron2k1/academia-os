"""Question Creator agent for generating structured practice questions."""
from __future__ import annotations

import json
import logging

from pydantic import BaseModel

from src.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class QuestionSpec(BaseModel):
    """Specification for question generation."""

    topics: list[str]
    count: int = 5
    difficulty: str = "medium"
    format: str = "json"
    include_solutions: bool = True
    style_reference: str | None = None


class QuestionCreatorAgent(BaseAgent):
    """Generates structured practice questions via the Claude CLI.

    Returns questions as parsed JSON matching the schema defined
    in the question-creator system prompt.
    """

    agent_name = "question-creator"

    def build_context(self) -> str:
        """Load existing questions from the vault to avoid duplicates.

        Returns:
            Existing questions context or empty string.
        """
        parts: list[str] = []
        question_files = self.vault.list("questions/")
        for qf in question_files[-5:]:
            try:
                parts.append(self.vault.read(qf))
            except FileNotFoundError:
                continue
        if parts:
            return "## Existing Questions\n" + "\n".join(parts)
        return ""

    def run(self, message: str, **kwargs: object) -> dict:
        """Generate questions from a free-form message.

        Args:
            message: Description of desired questions.

        Returns:
            Dict with raw_json string and parsed questions list.
        """
        spec = kwargs.get("spec")
        if isinstance(spec, QuestionSpec):
            return self._run_with_spec(message, spec)
        return self._run_freeform(message)

    def run_spec(self, spec: QuestionSpec) -> list[dict]:
        """Generate questions from a structured spec.

        Args:
            spec: QuestionSpec defining topics, count, difficulty.

        Returns:
            List of question dicts parsed from the agent output.
        """
        message = self._spec_to_message(spec)
        result = self._run_freeform(message)
        return result.get("questions", [])

    def _run_freeform(self, message: str) -> dict:
        """Run the question creator with a free-form message.

        Args:
            message: The user's question generation request.

        Returns:
            Dict with raw_json and questions keys.
        """
        context = self.build_context()
        system_prompt = self.load_prompt("question-creator")
        result = self.spawner.spawn(
            message=message,
            system_prompt=system_prompt,
            model=self.model,
            context=context,
        )
        self.emit_complete(result.wall_time_ms, result.exit_code)
        questions = _parse_questions_json(result.stdout)
        return {"raw_json": result.stdout, "questions": questions}

    def _run_with_spec(
        self, message: str, spec: QuestionSpec
    ) -> dict:
        """Run with both a message and a structured spec.

        Args:
            message: Additional context from the user.
            spec: Structured question specification.

        Returns:
            Dict with raw_json and questions keys.
        """
        spec_message = self._spec_to_message(spec)
        combined = f"{spec_message}\n\nAdditional context: {message}"
        return self._run_freeform(combined)

    def _spec_to_message(self, spec: QuestionSpec) -> str:
        """Convert a QuestionSpec to a natural language message.

        Args:
            spec: The question specification.

        Returns:
            Formatted message string for the agent.
        """
        topics_str = ", ".join(spec.topics)
        return (
            f"Generate {spec.count} {spec.difficulty} questions "
            f"on: {topics_str}. "
            f"Include solutions: {spec.include_solutions}."
        )


def _parse_questions_json(text: str) -> list[dict]:
    """Extract and parse questions JSON from agent output.

    Handles cases where JSON is embedded in markdown code fences.

    Args:
        text: Raw agent output text.

    Returns:
        List of question dicts, or empty list on parse failure.
    """
    cleaned = text.strip()
    if "```json" in cleaned:
        start = cleaned.index("```json") + 7
        end = cleaned.index("```", start)
        cleaned = cleaned[start:end].strip()
    elif "```" in cleaned:
        start = cleaned.index("```") + 3
        end = cleaned.index("```", start)
        cleaned = cleaned[start:end].strip()
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict) and "questions" in parsed:
            return parsed["questions"]
        if isinstance(parsed, list):
            return parsed
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("Failed to parse questions JSON: %s", exc)
    return []
