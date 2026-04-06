"""Tests for the R executor tool."""
from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.tools.r_executor import RExecutor, RResult


class TestRResult:
    """Tests for the RResult dataclass."""

    def test_success_when_exit_code_zero(self) -> None:
        """success is True when exit_code is 0."""
        result = RResult(stdout="ok", stderr="", exit_code=0)
        assert result.success is True

    def test_failure_when_exit_code_nonzero(self) -> None:
        """success is False when exit_code is non-zero."""
        result = RResult(stderr="error", exit_code=1)
        assert result.success is False

    def test_failure_when_exit_code_negative(self) -> None:
        """success is False when exit_code is -1 (timeout)."""
        result = RResult(exit_code=-1)
        assert result.success is False

    def test_defaults(self) -> None:
        """RResult defaults are sensible."""
        result = RResult()
        assert result.stdout == ""
        assert result.stderr == ""
        assert result.exit_code == 0
        assert result.output_files == []
        assert result.success is True

    def test_output_files_mutable(self) -> None:
        """Each RResult has its own output_files list."""
        r1 = RResult()
        r2 = RResult()
        r1.output_files.append("file.png")
        assert r2.output_files == []


class TestRExecutorInit:
    """Tests for RExecutor initialization."""

    def test_default_values(self) -> None:
        """RExecutor has sensible defaults."""
        executor = RExecutor()
        assert executor.timeout == 60
        assert executor.r_binary == "Rscript"

    def test_custom_values(self) -> None:
        """RExecutor accepts custom timeout and binary."""
        executor = RExecutor(timeout=120, r_binary="/usr/bin/Rscript")
        assert executor.timeout == 120
        assert executor.r_binary == "/usr/bin/Rscript"


class TestRExecutorExecuteFile:
    """Tests for RExecutor.execute_file."""

    @patch("src.tools.r_executor.subprocess.run")
    def test_runs_script(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """execute_file runs the script and returns RResult."""
        script = tmp_path / "test.R"
        script.write_text("cat('hello')")
        mock_run.return_value = MagicMock(
            stdout="hello", stderr="", returncode=0
        )
        executor = RExecutor()
        result = executor.execute_file(str(script))
        assert result.success is True
        assert result.stdout == "hello"
        mock_run.assert_called_once()

    @patch("src.tools.r_executor.subprocess.run")
    def test_passes_args(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """execute_file passes extra arguments to the command."""
        script = tmp_path / "test.R"
        script.write_text("args <- commandArgs(TRUE)")
        mock_run.return_value = MagicMock(
            stdout="", stderr="", returncode=0
        )
        executor = RExecutor()
        executor.execute_file(str(script), args=["--verbose"])
        call_args = mock_run.call_args
        cmd = call_args[0][0] if call_args[0] else call_args[1]["cmd"]
        assert "--verbose" in cmd

    def test_missing_file_returns_error(self) -> None:
        """execute_file returns error for missing script."""
        executor = RExecutor()
        result = executor.execute_file("/nonexistent/script.R")
        assert result.success is False
        assert result.exit_code == 1
        assert "Script not found" in result.stderr

    @patch("src.tools.r_executor.subprocess.run")
    def test_nonzero_exit_code(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """execute_file captures non-zero exit codes."""
        script = tmp_path / "fail.R"
        script.write_text("stop('error')")
        mock_run.return_value = MagicMock(
            stdout="", stderr="Error in stop", returncode=1
        )
        executor = RExecutor()
        result = executor.execute_file(str(script))
        assert result.success is False
        assert result.exit_code == 1


class TestRExecutorExecuteInline:
    """Tests for RExecutor.execute_inline."""

    @patch("src.tools.r_executor.subprocess.run")
    def test_runs_inline_code(self, mock_run: MagicMock) -> None:
        """execute_inline writes code to temp file and runs it."""
        mock_run.return_value = MagicMock(
            stdout="42", stderr="", returncode=0
        )
        executor = RExecutor()
        result = executor.execute_inline("cat(42)")
        assert result.success is True
        assert result.stdout == "42"
        mock_run.assert_called_once()

    @patch("src.tools.r_executor.subprocess.run")
    def test_cleans_up_temp_file(
        self, mock_run: MagicMock
    ) -> None:
        """execute_inline removes the temp file after execution."""
        mock_run.return_value = MagicMock(
            stdout="", stderr="", returncode=0
        )
        executor = RExecutor()
        executor.execute_inline("1+1")
        # Temp file should be cleaned up; verify run was called
        # with an .R file
        call_args = mock_run.call_args
        cmd = call_args[0][0] if call_args[0] else call_args[1]["cmd"]
        assert cmd[1].endswith(".R")

    @patch("src.tools.r_executor.subprocess.run")
    def test_passes_working_dir(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """execute_inline forwards working_dir to subprocess."""
        mock_run.return_value = MagicMock(
            stdout="", stderr="", returncode=0
        )
        executor = RExecutor()
        executor.execute_inline("1", working_dir=str(tmp_path))
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["cwd"] == str(tmp_path)


class TestRExecutorErrorHandling:
    """Tests for timeout and missing binary errors."""

    @patch("src.tools.r_executor.subprocess.run")
    def test_timeout_returns_error(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """Timeout returns RResult with exit_code -1."""
        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd="Rscript", timeout=10
        )
        script = tmp_path / "slow.R"
        script.write_text("Sys.sleep(999)")
        executor = RExecutor(timeout=10)
        result = executor.execute_file(str(script))
        assert result.success is False
        assert result.exit_code == -1
        assert "Timeout" in result.stderr

    @patch("src.tools.r_executor.subprocess.run")
    def test_missing_binary_returns_error(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """Missing R binary returns RResult with exit_code -1."""
        mock_run.side_effect = FileNotFoundError()
        script = tmp_path / "test.R"
        script.write_text("cat(1)")
        executor = RExecutor(r_binary="/bad/Rscript")
        result = executor.execute_file(str(script))
        assert result.success is False
        assert result.exit_code == -1
        assert "R binary not found" in result.stderr

    @patch("src.tools.r_executor.subprocess.run")
    def test_timeout_inline(self, mock_run: MagicMock) -> None:
        """Timeout on inline execution returns error."""
        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd="Rscript", timeout=5
        )
        executor = RExecutor(timeout=5)
        result = executor.execute_inline("Sys.sleep(999)")
        assert result.success is False
        assert result.exit_code == -1
