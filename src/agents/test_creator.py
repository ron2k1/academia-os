"""Test Creator agent for assembling practice exams."""
from __future__ import annotations

import logging

from src.agents.base import BaseAgent
from src.agents.question_creator import QuestionCreatorAgent, QuestionSpec

logger = logging.getLogger(__name__)


class TestCreatorAgent(BaseAgent):
    """Assembles practice tests from generated or provided questions.

    Can chain to QuestionCreatorAgent to generate questions first,
    then formats them into a complete practice exam.
    """

    agent_name = "test-creator"

    def build_context(self) -> str:
        """Load existing tests and question bank for reference.

        Returns:
            Context string with existing tests and questions.
        """
        parts: list[str] = []
        if self.vault.exists("topics.md"):
            parts.append(
                f"## topics.md\n{self.vault.read('topics.md')}"
            )
        test_files = self.vault.list("tests/")
        for tf in test_files[-3:]:
            try:
                name = tf.split("/")[-1] if "/" in tf else tf
                parts.append(
                    f"## {name}\n{self.vault.read(tf)}"
                )
            except FileNotFoundError:
                continue
        return "\n\n".join(parts) if parts else ""

    def run(self, message: str, **kwargs: object) -> dict:
        """Generate a practice test.

        If questions are provided in kwargs, uses them directly.
        Otherwise chains to QuestionCreatorAgent to generate questions.

        Args:
            message: Description of desired test (topics, difficulty).

        Returns:
            Dict with test markdown, vault path, and question count.
        """
        questions = kwargs.get("questions")
        if isinstance(questions, list) and questions:
            return self._assemble_test(message, questions)
        return self._generate_and_assemble(message, **kwargs)

    def _generate_and_assemble(
        self, message: str, **kwargs: object
    ) -> dict:
        """Chain to QuestionCreatorAgent then assemble a test.

        Args:
            message: Test description for question generation.

        Returns:
            Dict with test markdown, vault path, and question count.
        """
        topics = kwargs.get("topics", [])
        count = kwargs.get("count", 10)
        difficulty = kwargs.get("difficulty", "medium")
        if not isinstance(topics, list):
            topics = [str(topics)]
        if not isinstance(count, int):
            count = 10
        if not isinstance(difficulty, str):
            difficulty = "medium"
        spec = QuestionSpec(
            topics=topics if topics else ["general"],
            count=count,
            difficulty=difficulty,
        )
        qc_agent = QuestionCreatorAgent(
            class_config=self.class_config,
            vault=self.vault,
            spawner=self.spawner,
            model=self.model,
        )
        questions = qc_agent.run_spec(spec)
        return self._assemble_test(message, questions)

    def _assemble_test(
        self, message: str, questions: list[dict]
    ) -> dict:
        """Assemble questions into a formatted practice test.

        Args:
            message: Original request for context.
            questions: List of question dicts from QuestionCreatorAgent.

        Returns:
            Dict with test markdown, vault path, and question count.
        """
        context = self.build_context()
        questions_block = _format_questions_for_prompt(questions)
        system_prompt = self.load_prompt("test-creator")
        combined_message = (
            f"{message}\n\n"
            f"## Questions to include\n{questions_block}"
        )
        result = self.spawner.spawn(
            message=combined_message,
            system_prompt=system_prompt,
            model=self.model,
            context=context,
        )
        self.emit_complete(result.wall_time_ms, result.exit_code)
        vault_path = self._save_test(result.stdout)
        return {
            "test_markdown": result.stdout,
            "vault_path": vault_path,
            "question_count": len(questions),
        }

    def _save_test(self, content: str) -> str:
        """Save the assembled test to the vault.

        Args:
            content: Test markdown content.

        Returns:
            Vault-relative path where the test was written.
        """
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        filename = f"tests/{now.strftime('%Y%m%d-%H%M%S')}.md"
        self.vault.write(filename, content)
        return filename


def _format_questions_for_prompt(questions: list[dict]) -> str:
    """Format question dicts into a readable block for the prompt.

    Args:
        questions: List of question dicts.

    Returns:
        Formatted string with numbered questions.
    """
    if not questions:
        return "(No questions provided -- generate from scratch)"
    lines: list[str] = []
    for i, q in enumerate(questions, 1):
        text = q.get("question", q.get("text", str(q)))
        difficulty = q.get("difficulty", "unknown")
        topic = q.get("topic", "general")
        lines.append(
            f"{i}. [{difficulty}] ({topic}) {text}"
        )
    return "\n".join(lines)
