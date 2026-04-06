"""R code executor tool for running R scripts and inline code."""
from __future__ import annotations

import logging
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 60


@dataclass
class RResult:
    """Result of an R code execution.

    Attributes:
        stdout: Standard output from the R process.
        stderr: Standard error from the R process.
        exit_code: Process exit code (0 = success).
        output_files: List of file paths created by the script.
    """

    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    output_files: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """Whether the execution completed successfully.

        Returns:
            True if exit code is 0.
        """
        return self.exit_code == 0


class RExecutor:
    """Execute R code via the Rscript CLI.

    Supports running R script files and inline code strings.
    Captures stdout, stderr, and tracks output files.
    """

    def __init__(
        self,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
        r_binary: str = "Rscript",
    ) -> None:
        """Initialize the R executor.

        Args:
            timeout: Maximum execution time in seconds.
            r_binary: Path to the Rscript binary.
        """
        self.timeout = timeout
        self.r_binary = r_binary

    def execute_file(
        self,
        script_path: str | Path,
        args: list[str] | None = None,
    ) -> RResult:
        """Execute an R script file.

        Args:
            script_path: Path to the .R script file.
            args: Optional command-line arguments for the script.

        Returns:
            RResult with execution details.
        """
        path = Path(script_path)
        if not path.is_file():
            return RResult(
                stderr=f"Script not found: {path}",
                exit_code=1,
            )
        cmd = [self.r_binary, str(path)]
        if args:
            cmd.extend(args)
        return self._run(cmd, cwd=str(path.parent))

    def execute_inline(
        self,
        code: str,
        working_dir: str | Path | None = None,
    ) -> RResult:
        """Execute inline R code by writing to a temp file.

        Args:
            code: R code string to execute.
            working_dir: Optional working directory for execution.

        Returns:
            RResult with execution details.
        """
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".R",
            delete=False,
            encoding="utf-8",
        ) as tmp:
            tmp.write(code)
            tmp_path = tmp.name
        cwd = str(working_dir) if working_dir else None
        try:
            return self._run(
                [self.r_binary, tmp_path], cwd=cwd
            )
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def _run(
        self,
        cmd: list[str],
        cwd: str | None = None,
    ) -> RResult:
        """Run a subprocess command and capture results.

        Args:
            cmd: Command and arguments.
            cwd: Working directory for the subprocess.

        Returns:
            RResult with captured output.
        """
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=cwd,
            )
            return RResult(
                stdout=proc.stdout,
                stderr=proc.stderr,
                exit_code=proc.returncode,
            )
        except subprocess.TimeoutExpired:
            logger.warning("R execution timed out after %ds", self.timeout)
            return RResult(
                stderr=f"Timeout after {self.timeout}s",
                exit_code=-1,
            )
        except FileNotFoundError:
            logger.error("R binary not found: %s", self.r_binary)
            return RResult(
                stderr=f"R binary not found: {self.r_binary}",
                exit_code=-1,
            )
