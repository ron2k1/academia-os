"""Tests for the document generator tool."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.tools.doc_generator import DocFormat, DocGenerator


class TestDocFormat:
    """Tests for the DocFormat enum."""

    def test_all_formats_exist(self) -> None:
        """All expected formats are defined."""
        assert DocFormat.DOCX.value == "docx"
        assert DocFormat.PDF.value == "pdf"
        assert DocFormat.MARKDOWN.value == "markdown"

    def test_is_string_enum(self) -> None:
        """DocFormat members are strings."""
        assert isinstance(DocFormat.DOCX, str)
        assert DocFormat.MARKDOWN == "markdown"


class TestDocGeneratorInit:
    """Tests for DocGenerator initialization."""

    def test_creates_output_dir(self, tmp_path: Path) -> None:
        """DocGenerator creates output directory if it doesn't exist."""
        out_dir = tmp_path / "docs" / "output"
        assert not out_dir.exists()
        DocGenerator(out_dir)
        assert out_dir.exists()

    def test_existing_dir_ok(self, tmp_path: Path) -> None:
        """DocGenerator works with existing directory."""
        DocGenerator(tmp_path)
        assert tmp_path.exists()


class TestDocGeneratorCreateMarkdown:
    """Tests for markdown document creation."""

    def test_creates_markdown_file(self, tmp_path: Path) -> None:
        """create() with MARKDOWN writes content to .md file."""
        gen = DocGenerator(tmp_path)
        result = gen.create(
            content="# Hello\n\nWorld",
            filename="test",
            fmt=DocFormat.MARKDOWN,
        )
        assert result == tmp_path / "test.md"
        assert result.exists()
        assert result.read_text(encoding="utf-8") == "# Hello\n\nWorld"

    def test_markdown_ignores_title(self, tmp_path: Path) -> None:
        """create() with MARKDOWN writes content as-is."""
        gen = DocGenerator(tmp_path)
        result = gen.create(
            content="Body text",
            filename="notitle",
            fmt=DocFormat.MARKDOWN,
            title="Title",
        )
        # MARKDOWN create() does not prepend title
        content = result.read_text(encoding="utf-8")
        assert content == "Body text"


class TestDocGeneratorCreatePdf:
    """Tests for PDF stub generation."""

    def test_creates_md_fallback(self, tmp_path: Path) -> None:
        """create_pdf writes a .md file as fallback."""
        gen = DocGenerator(tmp_path)
        result = gen.create_pdf(
            content="PDF content here",
            filename="report",
        )
        assert result == tmp_path / "report.md"
        assert result.exists()
        content = result.read_text(encoding="utf-8")
        assert "PDF content here" in content

    def test_pdf_prepends_title(self, tmp_path: Path) -> None:
        """create_pdf prepends title as H1 when provided."""
        gen = DocGenerator(tmp_path)
        result = gen.create_pdf(
            content="Body",
            filename="titled",
            title="My Report",
        )
        content = result.read_text(encoding="utf-8")
        assert content.startswith("# My Report")
        assert "Body" in content

    def test_pdf_no_title(self, tmp_path: Path) -> None:
        """create_pdf without title writes content directly."""
        gen = DocGenerator(tmp_path)
        result = gen.create_pdf(
            content="Just content",
            filename="plain",
        )
        content = result.read_text(encoding="utf-8")
        assert content == "Just content"

    def test_create_dispatches_to_pdf(self, tmp_path: Path) -> None:
        """create() with PDF format dispatches to create_pdf."""
        gen = DocGenerator(tmp_path)
        result = gen.create(
            content="Test",
            filename="dispatch",
            fmt=DocFormat.PDF,
        )
        assert result.suffix == ".md"


class TestDocGeneratorCreateDocx:
    """Tests for DOCX generation."""

    def test_create_docx_with_mock(self, tmp_path: Path) -> None:
        """create_docx generates a DOCX file when python-docx available."""
        try:
            import docx  # noqa: F401

            gen = DocGenerator(tmp_path)
            result = gen.create_docx(
                content="# Heading\n\nParagraph text",
                filename="test",
                title="Test Doc",
            )
            assert result == tmp_path / "test.docx"
            assert result.exists()
        except ImportError:
            pytest.skip("python-docx not installed")

    def test_create_docx_heading_levels(
        self, tmp_path: Path
    ) -> None:
        """create_docx handles ##, ### headings."""
        try:
            import docx  # noqa: F401

            gen = DocGenerator(tmp_path)
            content = "# H1\n\n## H2\n\n### H3\n\nPlain text"
            result = gen.create_docx(
                content=content, filename="headings"
            )
            assert result.exists()
        except ImportError:
            pytest.skip("python-docx not installed")

    def test_create_docx_import_error(
        self, tmp_path: Path
    ) -> None:
        """create_docx raises ImportError when python-docx missing."""
        gen = DocGenerator(tmp_path)
        with patch.dict("sys.modules", {"docx": None}):
            with pytest.raises(ImportError, match="python-docx"):
                gen.create_docx(
                    content="test", filename="fail"
                )

    def test_create_dispatches_to_docx(
        self, tmp_path: Path
    ) -> None:
        """create() with DOCX format dispatches to create_docx."""
        try:
            import docx  # noqa: F401

            gen = DocGenerator(tmp_path)
            result = gen.create(
                content="Test content",
                filename="dispatch",
                fmt=DocFormat.DOCX,
            )
            assert result.suffix == ".docx"
        except ImportError:
            pytest.skip("python-docx not installed")


class TestDocGeneratorEdgeCases:
    """Edge case tests for DocGenerator."""

    def test_unsupported_format_raises(
        self, tmp_path: Path
    ) -> None:
        """create() raises ValueError for unsupported format."""
        gen = DocGenerator(tmp_path)
        with pytest.raises(ValueError, match="Unsupported format"):
            gen.create(
                content="test",
                filename="bad",
                fmt="html",  # type: ignore[arg-type]
            )

    def test_empty_content(self, tmp_path: Path) -> None:
        """create() handles empty content gracefully."""
        gen = DocGenerator(tmp_path)
        result = gen.create(
            content="", filename="empty", fmt=DocFormat.MARKDOWN
        )
        assert result.exists()
        assert result.read_text(encoding="utf-8") == ""

    def test_string_output_dir(self, tmp_path: Path) -> None:
        """DocGenerator accepts string path as output_dir."""
        gen = DocGenerator(str(tmp_path / "subdir"))
        assert gen.output_dir.exists()
