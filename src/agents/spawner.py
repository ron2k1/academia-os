"""Claude CLI subprocess spawner and management."""
from __future__ import annotations

import subprocess
import time

from pydantic import BaseModel, Field

from src.config.defaults import DEFAULT_AGENT_MODEL, DEFAULT_TIMEOUT_SECONDS


class SpawnResult(BaseModel):
    """Result of a Claude CLI subprocess invocation."""

    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    wall_time_ms: float = 0.0
    pid: int = 0


class ClaudeSpawner:
    """Spawn ``claude --print`` CLI subprocesses with context injection.

    Each call runs a fresh subprocess, pipes in the message (with
    optional context block), and captures all output.
    """

    def __init__(
        self,
        binary: str = "claude",
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        """Initialize the spawner.

        Args:
            binary: Path or name of the claude CLI binary.
            timeout_seconds: Maximum wall-clock seconds per invocation.
        """
        self.binary = binary
        self.timeout_seconds = timeout_seconds

    def spawn(
        self,
        message: str,
        system_prompt: str = "",
        model: str = DEFAULT_AGENT_MODEL,
        context: str = "",
    ) -> SpawnResult:
        """Spawn a claude CLI subprocess and capture the result.

        Builds a command like::

            echo "<input>" | claude --print [--model MODEL]
                [--system-prompt PROMPT]

        Context (if provided) is prepended inside a ``<context>`` XML
        block before the message.

        Args:
            message: The user message to send.
            system_prompt: Optional system prompt passed via flag.
            model: Model identifier for ``--model`` flag.
            context: Optional context block prepended to the message.

        Returns:
            SpawnResult with stdout, stderr, exit code, timing, and PID.

        Raises:
            TimeoutError: If the subprocess exceeds timeout_seconds.
        """
        stdin_text = self._build_stdin(message, context)
        cmd = self._build_command(model, system_prompt)
        return self._run(cmd, stdin_text)

    def _build_stdin(self, message: str, context: str) -> str:
        """Build the stdin text with optional context block.

        Args:
            message: The user message.
            context: Optional context to wrap in XML tags.

        Returns:
            Combined stdin string.
        """
        if context:
            return f"<context>\n{context}\n</context>\n\n{message}"
        return message

    def _build_command(
        self, model: str, system_prompt: str
    ) -> list[str]:
        """Build the subprocess command list.

        Args:
            model: Model identifier.
            system_prompt: Optional system prompt.

        Returns:
            Command as a list of strings.
        """
        cmd = [self.binary, "--print"]
        if model:
            cmd.extend(["--model", model])
        if system_prompt:
            cmd.extend(["--system-prompt", system_prompt])
        return cmd

    def _run(
        self, cmd: list[str], stdin_text: str
    ) -> SpawnResult:
        """Execute the subprocess and return results.

        Args:
            cmd: Command list to execute.
            stdin_text: Text to pipe to stdin.

        Returns:
            SpawnResult with captured output and metadata.

        Raises:
            TimeoutError: If the subprocess exceeds the timeout.
        """
        start = time.monotonic()
        try:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            stdout, stderr = proc.communicate(
                input=stdin_text,
                timeout=self.timeout_seconds,
            )
            wall_ms = (time.monotonic() - start) * 1000
            return SpawnResult(
                stdout=stdout,
                stderr=stderr,
                exit_code=proc.returncode,
                wall_time_ms=wall_ms,
                pid=proc.pid,
            )
        except subprocess.TimeoutExpired as exc:
            proc.kill()
            proc.communicate()
            raise TimeoutError(
                f"Claude CLI timed out after {self.timeout_seconds}s"
            ) from exc


def spawn_claude(message: str, **kwargs: str | int) -> str:
    """Convenience wrapper that spawns Claude and returns stdout.

    Args:
        message: The user message.
        **kwargs: Passed through to ClaudeSpawner.spawn().

    Returns:
        The stdout string from the Claude CLI.
    """
    spawner = ClaudeSpawner()
    result = spawner.spawn(message, **kwargs)
    return result.stdout
