"""Homework Finisher agent with anti-slop 5-pass pipeline."""
from __future__ import annotations

import logging

from pydantic import BaseModel

from src.agents.base import BaseAgent

logger = logging.getLogger(__name__)

PASSES = ("Draft", "Style", "Correctness", "Humanize", "Review")


class HomeworkResult(BaseModel):
    """Result of a homework finisher run."""

    final_output: str
    pass_outputs: dict[str, str]
    vault_path: str


class HomeworkFinisherAgent(BaseAgent):
    """Produces polished homework submissions via a 5-pass pipeline.

    Passes: Draft -> Style -> Correctness -> Humanize -> Review.
    Each pass refines the previous output with a specific focus.
    """

    agent_name = "homework-finisher"

    def build_context(self) -> str:
        """Load class context, style guides, and past homework.

        Returns:
            Assembled context for homework generation.
        """
        parts: list[str] = []
        for path in ("context.md", "topics.md"):
            if self.vault.exists(path):
                parts.append(
                    f"## {path}\n{self.vault.read(path)}"
                )
        hw_files = self.vault.list("homework/")
        for hf in hw_files[-3:]:
            try:
                name = hf.split("/")[-1] if "/" in hf else hf
                parts.append(
                    f"## {name}\n{self.vault.read(hf)}"
                )
            except FileNotFoundError:
                continue
        return "\n\n".join(parts) if parts else ""

    def run(self, message: str, **kwargs: object) -> dict:
        """Run the 5-pass homework pipeline.

        Args:
            message: The homework assignment description.

        Returns:
            HomeworkResult as a dict.
        """
        context = self.build_context()
        system_prompt = self.load_prompt("homework-finisher")
        pass_outputs = self._run_pipeline(
            message, system_prompt, context
        )
        final = pass_outputs[PASSES[-1]]
        vault_path = self._save_homework(message, final)
        return HomeworkResult(
            final_output=final,
            pass_outputs=pass_outputs,
            vault_path=vault_path,
        ).model_dump()

    def _run_pipeline(
        self,
        message: str,
        system_prompt: str,
        context: str,
    ) -> dict[str, str]:
        """Execute all 5 passes sequentially.

        Args:
            message: Original homework assignment.
            system_prompt: The homework-finisher system prompt.
            context: Vault context string.

        Returns:
            Dict mapping pass name to its output.
        """
        outputs: dict[str, str] = {}
        current = message
        for pass_name in PASSES:
            current = self._run_pass(
                pass_name, current, system_prompt, context
            )
            outputs[pass_name] = current
        return outputs

    def _run_pass(
        self,
        pass_name: str,
        content: str,
        system_prompt: str,
        context: str,
    ) -> str:
        """Execute a single pass of the pipeline.

        Args:
            pass_name: Name of the current pass.
            content: Input content for this pass.
            system_prompt: Base system prompt.
            context: Vault context string.

        Returns:
            Refined output from this pass.
        """
        pass_message = (
            f"## Current Pass: {pass_name}\n\n"
            f"Apply the {pass_name} pass to the following:\n\n"
            f"{content}"
        )
        result = self.spawner.spawn(
            message=pass_message,
            system_prompt=system_prompt,
            model=self.model,
            context=context,
        )
        self.emit_complete(result.wall_time_ms, result.exit_code)
        return result.stdout

    def _save_homework(
        self, assignment: str, final_output: str
    ) -> str:
        """Save the finished homework to the vault.

        Args:
            assignment: Original assignment description.
            final_output: Final polished output.

        Returns:
            Vault-relative path where homework was saved.
        """
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        filename = f"homework/{now.strftime('%Y%m%d-%H%M%S')}.md"
        content = (
            f"# Homework - {now.strftime('%Y-%m-%d %H:%M')}\n\n"
            f"## Assignment\n{assignment}\n\n"
            f"## Solution\n{final_output}\n"
        )
        self.vault.write(filename, content)
        return filename
