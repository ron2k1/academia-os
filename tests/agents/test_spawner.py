"""Tests for Claude CLI spawner (mocked subprocess calls)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.agents.spawner import ClaudeSpawner, SpawnResult, spawn_claude


class TestSpawnResult:
    """Tests for the SpawnResult model."""

    def test_defaults(self) -> None:
        """SpawnResult has sensible defaults."""
        result = SpawnResult()
        assert result.stdout == ""
        assert result.stderr == ""
        assert result.exit_code == 0
        assert result.wall_time_ms == 0.0
        assert result.pid == 0


class TestClaudeSpawner:
    """Tests for the ClaudeSpawner class (all subprocess calls mocked)."""

    def _mock_popen(
        self,
        stdout: str = "response",
        stderr: str = "",
        returncode: int = 0,
        pid: int = 12345,
    ) -> MagicMock:
        """Create a mock Popen instance.

        Args:
            stdout: Mock stdout output.
            stderr: Mock stderr output.
            returncode: Mock return code.
            pid: Mock process ID.

        Returns:
            Configured MagicMock for Popen.
        """
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = (stdout, stderr)
        mock_proc.returncode = returncode
        mock_proc.pid = pid
        return mock_proc

    @patch("src.agents.spawner.subprocess.Popen")
    def test_spawn_basic(self, mock_popen_cls: MagicMock) -> None:
        """Basic spawn returns stdout and metadata."""
        mock_popen_cls.return_value = self._mock_popen()
        spawner = ClaudeSpawner()
        result = spawner.spawn("Hello")

        assert result.stdout == "response"
        assert result.exit_code == 0
        assert result.pid == 12345
        assert result.wall_time_ms > 0

    @patch("src.agents.spawner.subprocess.Popen")
    def test_spawn_with_context(self, mock_popen_cls: MagicMock) -> None:
        """Context is prepended in XML block."""
        mock_proc = self._mock_popen()
        mock_popen_cls.return_value = mock_proc
        spawner = ClaudeSpawner()
        spawner.spawn("question", context="vault notes")

        call_args = mock_proc.communicate.call_args
        stdin_text = call_args[1]["input"]
        assert "<context>" in stdin_text
        assert "vault notes" in stdin_text
        assert "question" in stdin_text

    @patch("src.agents.spawner.subprocess.Popen")
    def test_spawn_with_system_prompt(
        self, mock_popen_cls: MagicMock
    ) -> None:
        """System prompt is passed via --system-prompt flag."""
        mock_popen_cls.return_value = self._mock_popen()
        spawner = ClaudeSpawner()
        spawner.spawn("msg", system_prompt="Be helpful")

        cmd = mock_popen_cls.call_args[0][0]
        assert "--system-prompt" in cmd
        assert "Be helpful" in cmd

    @patch("src.agents.spawner.subprocess.Popen")
    def test_spawn_with_model(self, mock_popen_cls: MagicMock) -> None:
        """Model is passed via --model flag."""
        mock_popen_cls.return_value = self._mock_popen()
        spawner = ClaudeSpawner()
        spawner.spawn("msg", model="claude-opus-4-20250514")

        cmd = mock_popen_cls.call_args[0][0]
        assert "--model" in cmd
        assert "claude-opus-4-20250514" in cmd

    @patch("src.agents.spawner.subprocess.Popen")
    def test_spawn_timeout(self, mock_popen_cls: MagicMock) -> None:
        """TimeoutError is raised when subprocess times out."""
        import subprocess

        mock_proc = self._mock_popen()
        mock_proc.communicate.side_effect = subprocess.TimeoutExpired(
            cmd="claude", timeout=5
        )
        mock_popen_cls.return_value = mock_proc

        spawner = ClaudeSpawner(timeout_seconds=5)
        with pytest.raises(TimeoutError, match="timed out"):
            spawner.spawn("slow request")

    @patch("src.agents.spawner.subprocess.Popen")
    def test_spawn_stderr_captured(
        self, mock_popen_cls: MagicMock
    ) -> None:
        """Stderr is captured in the result."""
        mock_popen_cls.return_value = self._mock_popen(
            stderr="warning msg", returncode=1
        )
        spawner = ClaudeSpawner()
        result = spawner.spawn("msg")

        assert result.stderr == "warning msg"
        assert result.exit_code == 1

    @patch("src.agents.spawner.subprocess.Popen")
    def test_spawn_no_context(self, mock_popen_cls: MagicMock) -> None:
        """Without context, no XML block is in stdin."""
        mock_proc = self._mock_popen()
        mock_popen_cls.return_value = mock_proc
        spawner = ClaudeSpawner()
        spawner.spawn("just a message")

        stdin_text = mock_proc.communicate.call_args[1]["input"]
        assert "<context>" not in stdin_text
        assert stdin_text == "just a message"


class TestSpawnClaude:
    """Tests for the spawn_claude convenience wrapper."""

    @patch("src.agents.spawner.subprocess.Popen")
    def test_returns_stdout(self, mock_popen_cls: MagicMock) -> None:
        """spawn_claude returns just the stdout string."""
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = ("the answer", "")
        mock_proc.returncode = 0
        mock_proc.pid = 999
        mock_popen_cls.return_value = mock_proc

        result = spawn_claude("what is 2+2")
        assert result == "the answer"
