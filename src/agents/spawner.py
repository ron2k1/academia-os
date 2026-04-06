"""Claude CLI subprocess spawner and management."""
from __future__ import annotations

import logging
import random
import subprocess
import time

from pydantic import BaseModel, Field

from src.config.defaults import DEFAULT_AGENT_MODEL, DEFAULT_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)

# Retry defaults
DEFAULT_MAX_RETRIES = 3
DEFAULT_BASE_DELAY = 2.0
DEFAULT_MAX_DELAY = 30.0
DEFAULT_JITTER = 0.5


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

    def spawn_with_retry(
        self,
        message: str,
        system_prompt: str = "",
        model: str = DEFAULT_AGENT_MODEL,
        context: str = "",
        max_retries: int = DEFAULT_MAX_RETRIES,
        base_delay: float = DEFAULT_BASE_DELAY,
        max_delay: float = DEFAULT_MAX_DELAY,
        jitter: float = DEFAULT_JITTER,
    ) -> SpawnResult:
        """Spawn with exponential backoff retry on transient failures.

        Retries on non-zero exit codes and timeouts. Each retry waits
        an exponentially increasing delay with random jitter to avoid
        thundering-herd effects.

        Args:
            message: The user message to send.
            system_prompt: Optional system prompt passed via flag.
            model: Model identifier for ``--model`` flag.
            context: Optional context block prepended to the message.
            max_retries: Maximum number of retry attempts.
            base_delay: Initial delay in seconds before first retry.
            max_delay: Cap on the delay between retries.
            jitter: Random jitter factor (0.0-1.0) applied to delay.

        Returns:
            SpawnResult from the first successful invocation.

        Raises:
            TimeoutError: If all attempts time out.
            RuntimeError: If all retry attempts are exhausted.
        """
        last_error: Exception | None = None
        last_result: SpawnResult | None = None

        for attempt in range(max_retries + 1):
            try:
                result = self.spawn(
                    message=message,
                    system_prompt=system_prompt,
                    model=model,
                    context=context,
                )
                if result.exit_code == 0:
                    if attempt > 0:
                        logger.info(
                            "Spawn succeeded on attempt %d/%d",
                            attempt + 1,
                            max_retries + 1,
                        )
                    return result

                last_result = result
                logger.warning(
                    "Spawn attempt %d/%d failed with exit code %d: %s",
                    attempt + 1,
                    max_retries + 1,
                    result.exit_code,
                    result.stderr[:200] if result.stderr else "(no stderr)",
                )
            except TimeoutError as exc:
                last_error = exc
                logger.warning(
                    "Spawn attempt %d/%d timed out: %s",
                    attempt + 1,
                    max_retries + 1,
                    exc,
                )

            # Don't sleep after the last attempt
            if attempt < max_retries:
                delay = min(base_delay * (2 ** attempt), max_delay)
                if jitter > 0:
                    delay += random.uniform(0, jitter * delay)
                logger.info("Retrying in %.1fs...", delay)
                time.sleep(delay)

        # All attempts exhausted
        if last_error:
            raise TimeoutError(
                f"All {max_retries + 1} spawn attempts timed out"
            ) from last_error

        if last_result:
            raise RuntimeError(
                f"All {max_retries + 1} spawn attempts failed. "
                f"Last exit code: {last_result.exit_code}. "
                f"Last stderr: {last_result.stderr[:300]}"
            )

        raise RuntimeError("Unexpected: no result and no error after retries")

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
