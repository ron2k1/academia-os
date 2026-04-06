"""Tests for the relay response post-processing module."""
from __future__ import annotations

from src.orchestrator.relay import relay_response


class TestRelayResponseDefaults:
    """Tests for relay_response with default settings."""

    def test_strips_xml_blocks_by_default(self) -> None:
        """XML blocks are stripped by default."""
        raw = "Hello<memory_update>data</memory_update> world"
        result = relay_response(raw)
        assert "memory_update" not in result
        assert "Hello" in result
        assert "world" in result

    def test_preserves_text_around_xml(self) -> None:
        """Text before and after XML blocks is preserved."""
        raw = "Before <tag>content</tag> After"
        result = relay_response(raw)
        assert result == "Before  After"

    def test_multiline_xml_block(self) -> None:
        """Strips XML blocks that span multiple lines."""
        raw = "Start\n<notes>\nLine 1\nLine 2\n</notes>\nEnd"
        result = relay_response(raw)
        assert "notes" not in result
        assert "Start" in result
        assert "End" in result

    def test_multiple_xml_blocks(self) -> None:
        """Strips multiple distinct XML blocks."""
        raw = "<a>x</a> middle <b>y</b>"
        result = relay_response(raw)
        assert "middle" in result
        assert "<a>" not in result
        assert "<b>" not in result

    def test_no_xml_blocks(self) -> None:
        """Returns text unchanged when no XML blocks present."""
        raw = "Plain text with no blocks"
        result = relay_response(raw)
        assert result == "Plain text with no blocks"


class TestRelayResponseCodeFences:
    """Tests for code fence stripping."""

    def test_does_not_strip_code_fences_by_default(self) -> None:
        """Code fences are preserved when strip_code_fences=False."""
        raw = "```python\nprint('hi')\n```"
        result = relay_response(raw, strip_code_fences=False)
        assert "```" in result

    def test_strips_code_fences_when_enabled(self) -> None:
        """Code fences are removed, content preserved."""
        raw = "```python\nprint('hi')\n```"
        result = relay_response(raw, strip_code_fences=True)
        assert "```" not in result
        assert "print('hi')" in result

    def test_strips_plain_code_fences(self) -> None:
        """Strips code fences without language specifier."""
        raw = "```\nsome code\n```"
        result = relay_response(raw, strip_code_fences=True)
        assert "```" not in result
        assert "some code" in result

    def test_multiple_code_fences(self) -> None:
        """Strips multiple code fence blocks."""
        raw = "```py\na\n``` then ```js\nb\n```"
        result = relay_response(raw, strip_code_fences=True)
        assert "```" not in result
        assert "a" in result
        assert "b" in result


class TestRelayResponseMaxLength:
    """Tests for max_length truncation."""

    def test_no_truncation_when_under_limit(self) -> None:
        """Text under max_length is not truncated."""
        raw = "Short text"
        result = relay_response(
            raw, strip_xml_blocks=False, max_length=100
        )
        assert result == "Short text"
        assert "[Truncated]" not in result

    def test_truncates_at_max_length(self) -> None:
        """Text over max_length is truncated with marker."""
        raw = "A" * 200
        result = relay_response(
            raw, strip_xml_blocks=False, max_length=50
        )
        assert result.endswith("[Truncated]")
        assert len(result) < 200

    def test_no_truncation_when_none(self) -> None:
        """No truncation when max_length is None."""
        raw = "A" * 10000
        result = relay_response(
            raw, strip_xml_blocks=False, max_length=None
        )
        assert "[Truncated]" not in result


class TestRelayResponseCombined:
    """Tests for combined options."""

    def test_strip_xml_and_fences(self) -> None:
        """Both XML and code fence stripping work together."""
        raw = "<meta>info</meta>\n```py\ncode\n```\nPlain"
        result = relay_response(
            raw, strip_xml_blocks=True, strip_code_fences=True
        )
        assert "meta" not in result
        assert "```" not in result
        assert "code" in result
        assert "Plain" in result

    def test_all_options(self) -> None:
        """All three options work together."""
        raw = "<x>y</x> ```\nlong code\n``` " + "Z" * 100
        result = relay_response(
            raw,
            strip_xml_blocks=True,
            strip_code_fences=True,
            max_length=30,
        )
        assert "<x>" not in result
        assert "```" not in result
        assert "[Truncated]" in result

    def test_empty_string(self) -> None:
        """Empty input returns empty string."""
        result = relay_response("")
        assert result == ""

    def test_whitespace_only(self) -> None:
        """Whitespace-only input returns empty string."""
        result = relay_response("   \n\n  ")
        assert result == ""

    def test_strips_leading_trailing_whitespace(self) -> None:
        """Output is always stripped of leading/trailing whitespace."""
        raw = "  \n  Hello world  \n  "
        result = relay_response(raw, strip_xml_blocks=False)
        assert result == "Hello world"
