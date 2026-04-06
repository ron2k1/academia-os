"""Vault tool for Obsidian-style markdown vault CRUD and search."""
from __future__ import annotations

from pathlib import Path

from src.utils.paths import ensure_dir, safe_relative_path


class VaultTool:
    """Read, write, list, and search files in a class vault.

    Each vault is scoped to a single class and rooted at
    ``<vaults_root>/<class_id>/``.  All user-supplied paths are
    relative to this root; path traversal via ``..`` is rejected.
    """

    def __init__(self, class_id: str, vaults_root: str) -> None:
        """Initialize the vault tool.

        Args:
            class_id: Identifier for the class (used as subdirectory).
            vaults_root: Absolute path to the vaults root directory.
        """
        self.class_id = class_id
        self.root = Path(vaults_root) / class_id
        ensure_dir(self.root)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def read(self, path: str) -> str:
        """Read the contents of a file in the vault.

        Args:
            path: Relative path within the vault.

        Returns:
            File contents as a string.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If path traversal is detected.
        """
        full = self._resolve(path)
        if not full.is_file():
            raise FileNotFoundError(f"Vault file not found: {path}")
        return full.read_text(encoding="utf-8")

    def write(
        self, path: str, content: str, append: bool = False
    ) -> None:
        """Write content to a file in the vault.

        Creates parent directories as needed.

        Args:
            path: Relative path within the vault.
            content: Text content to write.
            append: If True, append instead of overwrite.

        Raises:
            ValueError: If path traversal is detected.
        """
        full = self._resolve(path)
        ensure_dir(full.parent)
        mode = "a" if append else "w"
        with open(full, mode, encoding="utf-8") as f:
            f.write(content)

    def list(self, directory: str = ".") -> list[str]:
        """List files in a vault directory, returning relative paths.

        Args:
            directory: Relative directory path within the vault.

        Returns:
            Sorted list of relative file paths (POSIX-style strings).

        Raises:
            ValueError: If path traversal is detected.
        """
        full = self._resolve(directory)
        if not full.is_dir():
            return []
        results: list[str] = []
        for item in sorted(full.rglob("*")):
            if item.is_file():
                rel = item.relative_to(self.root)
                results.append(rel.as_posix())
        return results

    def search(self, query: str) -> list[dict[str, str | int]]:
        """Search vault files for lines containing the query string.

        Args:
            query: Case-insensitive search string.

        Returns:
            List of dicts with keys: path, line (1-based), context.

        Raises:
            ValueError: If query is empty.
        """
        if not query.strip():
            raise ValueError("Search query must not be empty")
        query_lower = query.lower()
        results: list[dict[str, str | int]] = []
        for file_path in sorted(self.root.rglob("*")):
            if not file_path.is_file():
                continue
            self._search_file(file_path, query_lower, results)
        return results

    def exists(self, path: str) -> bool:
        """Check whether a file exists in the vault.

        Args:
            path: Relative path within the vault.

        Returns:
            True if the file exists, False otherwise.

        Raises:
            ValueError: If path traversal is detected.
        """
        full = self._resolve(path)
        return full.is_file()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve(self, relative: str) -> Path:
        """Resolve a relative path safely within the vault root.

        Args:
            relative: Relative path string.

        Returns:
            Absolute Path within the vault.

        Raises:
            ValueError: If path traversal is detected.
        """
        return safe_relative_path(self.root, relative)

    def _search_file(
        self,
        file_path: Path,
        query_lower: str,
        results: list[dict[str, str | int]],
    ) -> None:
        """Search a single file for matching lines.

        Args:
            file_path: Absolute path to the file.
            query_lower: Lowercased query string.
            results: Accumulator list to append matches to.
        """
        try:
            text = file_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            return
        rel = file_path.relative_to(self.root).as_posix()
        for line_num, line in enumerate(text.splitlines(), start=1):
            if query_lower in line.lower():
                results.append({
                    "path": rel,
                    "line": line_num,
                    "context": line.strip(),
                })
