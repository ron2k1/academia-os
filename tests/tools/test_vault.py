"""Tests for the VaultTool."""
from __future__ import annotations

from pathlib import Path

import pytest

from src.tools.vault import VaultTool


class TestVaultWrite:
    """Tests for VaultTool.write()."""

    def test_write_creates_file(self, vault: VaultTool) -> None:
        """Writing creates a new file with content."""
        vault.write("hello.md", "# Hello\n")
        content = vault.read("hello.md")
        assert content == "# Hello\n"

    def test_write_creates_subdirectory(self, vault: VaultTool) -> None:
        """Writing to a nested path creates parent directories."""
        vault.write("deep/nested/file.md", "content")
        assert vault.exists("deep/nested/file.md")

    def test_write_overwrite(self, vault: VaultTool) -> None:
        """Writing again overwrites existing content."""
        vault.write("over.md", "first")
        vault.write("over.md", "second")
        assert vault.read("over.md") == "second"

    def test_write_append(self, vault: VaultTool) -> None:
        """Append mode adds to existing content."""
        vault.write("app.md", "line1\n")
        vault.write("app.md", "line2\n", append=True)
        content = vault.read("app.md")
        assert "line1\n" in content
        assert "line2\n" in content


class TestVaultRead:
    """Tests for VaultTool.read()."""

    def test_read_existing(self, vault: VaultTool) -> None:
        """Read returns the contents of an existing file."""
        vault.write("doc.md", "Hello world")
        assert vault.read("doc.md") == "Hello world"

    def test_read_missing(self, vault: VaultTool) -> None:
        """Read raises FileNotFoundError for missing files."""
        with pytest.raises(FileNotFoundError):
            vault.read("missing.md")


class TestVaultList:
    """Tests for VaultTool.list()."""

    def test_list_files(self, vault: VaultTool) -> None:
        """List returns relative paths of all files."""
        vault.write("a.md", "a")
        vault.write("sub/b.md", "b")
        files = vault.list(".")
        assert "test-class/a.md" in files
        assert "test-class/sub/b.md" in files

    def test_list_empty(self, vault: VaultTool) -> None:
        """List on empty directory returns empty list."""
        files = vault.list("nonexistent")
        assert files == []


class TestVaultSearch:
    """Tests for VaultTool.search()."""

    def test_search_finds_match(self, vault: VaultTool) -> None:
        """Search finds lines containing the query."""
        vault.write("notes.md", "# Notes\nLinear regression is important\n")
        results = vault.search("regression")
        assert len(results) >= 1
        assert results[0]["context"] == "Linear regression is important"

    def test_search_case_insensitive(self, vault: VaultTool) -> None:
        """Search is case-insensitive."""
        vault.write("doc.md", "HELLO World\n")
        results = vault.search("hello")
        assert len(results) >= 1

    def test_search_empty_query(self, vault: VaultTool) -> None:
        """Empty query raises ValueError."""
        with pytest.raises(ValueError, match="must not be empty"):
            vault.search("")

    def test_search_returns_line_numbers(self, vault: VaultTool) -> None:
        """Search results include 1-based line numbers."""
        vault.write("multi.md", "line1\nline2\ntarget here\nline4\n")
        results = vault.search("target")
        assert results[0]["line"] == 3


class TestVaultExists:
    """Tests for VaultTool.exists()."""

    def test_exists_true(self, vault: VaultTool) -> None:
        """Exists returns True for existing files."""
        vault.write("there.md", "yes")
        assert vault.exists("there.md") is True

    def test_exists_false(self, vault: VaultTool) -> None:
        """Exists returns False for missing files."""
        assert vault.exists("nope.md") is False


class TestVaultSecurity:
    """Tests for vault path traversal prevention."""

    def test_path_traversal_blocked(self, vault: VaultTool) -> None:
        """Path traversal via '..' is rejected."""
        with pytest.raises(ValueError, match="traversal"):
            vault.read("../../etc/passwd")

    def test_path_traversal_in_write(self, vault: VaultTool) -> None:
        """Path traversal in write is also rejected."""
        with pytest.raises(ValueError, match="traversal"):
            vault.write("../escape.md", "bad")
