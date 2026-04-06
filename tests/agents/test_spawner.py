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
        # First call raises TimeoutExpired; second call (after kill)
        # returns normally to drain buffers.
        mock_proc.communicate.side_effect = [
            subprocess.TimeoutExpired(cmd="claude", timeout=5),
            ("", ""),
        ]
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


class TestSpawnWithRetry:
    """Tests for the spawn_with_retry method (exponential backoff)."""

    def _mock_popen(
        self,
        stdout: str = "response",
        stderr: str = "",
        returncode: int = 0,
        pid: int = 12345,
    ) -> MagicMock:
        """Create a mock Popen instance."""
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = (stdout, stderr)
        mock_proc.returncode = returncode
        mock_proc.pid = pid
        return mock_proc

    @patch("src.agents.spawner.time.sleep")
    @patch("src.agents.spawner.subprocess.Popen")
    def test_success_first_attempt(
        self, mock_popen_cls: MagicMock, mock_sleep: MagicMock
    ) -> None:
        """Returns immediately when the first attempt succeeds."""
        mock_popen_cls.return_value = self._mock_popen()
        spawner = ClaudeSpawner()
        result = spawner.spawn_with_retry("msg", max_retries=2)

        assert result.exit_code == 0
        assert result.stdout == "response"
        mock_sleep.assert_not_called()

    @patch("src.agents.spawner.time.sleep")
    @patch("src.agents.spawner.subprocess.Popen")
    def test_success_after_failure(
        self, mock_popen_cls: MagicMock, mock_sleep: MagicMock
    ) -> None:
        """Retries and succeeds after transient failures."""
        fail_proc = self._mock_popen(returncode=1, stderr="transient error")
        ok_proc = self._mock_popen(stdout="recovered")

        mock_popen_cls.side_effect = [fail_proc, fail_proc, ok_proc]
        spawner = ClaudeSpawner()
        result = spawner.spawn_with_retry(
            "msg", max_retries=3, base_delay=0.01, jitter=0
        )

        assert result.exit_code == 0
        assert result.stdout == "recovered"
        assert mock_sleep.call_count == 2  # slept before attempt 2 and 3

    @patch("src.agents.spawner.time.sleep")
    @patch("src.agents.spawner.subprocess.Popen")
    def test_all_attempts_fail_raises_runtime_error(
        self, mock_popen_cls: MagicMock, mock_sleep: MagicMock
    ) -> None:
        """Raises RuntimeError when all attempts return non-zero exit code."""
        mock_popen_cls.return_value = self._mock_popen(
            returncode=1, stderr="persistent failure"
        )
        spawner = ClaudeSpawner()

        with pytest.raises(RuntimeError, match="All 3 spawn attempts failed"):
            spawner.spawn_with_retry(
                "msg", max_retries=2, base_delay=0.01, jitter=0
            )

    @patch("src.agents.spawner.time.sleep")
    @patch("src.agents.spawner.subprocess.Popen")
    def test_all_attempts_timeout_raises_timeout_error(
        self, mock_popen_cls: MagicMock, mock_sleep: MagicMock
    ) -> None:
        """Raises TimeoutError when all attempts time out."""
        import subprocess as _sp

        mock_proc = self._mock_popen()
        mock_proc.communicate.side_effect = [
            _sp.TimeoutExpired(cmd="claude", timeout=5),
            ("", ""),  # kill drain
            _sp.TimeoutExpired(cmd="claude", timeout=5),
            ("", ""),
        ]
        mock_popen_cls.return_value = mock_proc

        spawner = ClaudeSpawner(timeout_seconds=5)
        with pytest.raises(TimeoutError, match="All 2 spawn attempts timed out"):
            spawner.spawn_with_retry(
                "msg", max_retries=1, base_delay=0.01, jitter=0
            )

    @patch("src.agents.spawner.time.sleep")
    @patch("src.agents.spawner.subprocess.Popen")
    def test_exponential_delay(
        self, mock_popen_cls: MagicMock, mock_sleep: MagicMock
    ) -> None:
        """Sleep delays increase exponentially between attempts."""
        mock_popen_cls.return_value = self._mock_popen(
            returncode=1, stderr="fail"
        )
        spawner = ClaudeSpawner()

        with pytest.raises(RuntimeError):
            spawner.spawn_with_retry(
                "msg",
                max_retries=3,
                base_delay=1.0,
                max_delay=100.0,
                jitter=0,
            )

        # delays: 1*2^0=1, 1*2^1=2, 1*2^2=4
        delays = [call.args[0] for call in mock_sleep.call_args_list]
        assert len(delays) == 3
        assert delays[0] == pytest.approx(1.0)
        assert delays[1] == pytest.approx(2.0)
        assert delays[2] == pytest.approx(4.0)

    @patch("src.agents.spawner.time.sleep")
    @patch("src.agents.spawner.subprocess.Popen")
    def test_delay_capped_at_max(
        self, mock_popen_cls: MagicMock, mock_sleep: MagicMock
    ) -> None:
        """Delay never exceeds max_delay."""
        mock_popen_cls.return_value = self._mock_popen(
            returncode=1, stderr="fail"
        )
        spawner = ClaudeSpawner()

        with pytest.raises(RuntimeError):
            spawner.spawn_with_retry(
                "msg",
                max_retries=5,
                base_delay=10.0,
                max_delay=15.0,
                jitter=0,
            )

        delays = [call.args[0] for call in mock_sleep.call_args_list]
        for d in delays:
            assert d <= 15.0


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
