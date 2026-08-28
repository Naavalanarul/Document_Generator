"""
Unit tests for ingestion.clean_text() and ingestion.chunk_text().
These are pure functions — no LLM or filesystem needed.
"""
import sys
from pathlib import Path

# Ensure Backend is on sys.path so `from ingestion import ...` works
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ingestion import clean_text, chunk_text


# ── clean_text ─────────────────────────────────────────────────────────────────

class TestCleanText:
    def test_empty_string(self):
        assert clean_text("") == ""

    def test_whitespace_only(self):
        assert clean_text("   \n\n  \n  ") == ""

    def test_bullet_glyphs_replaced(self):
        # Various bullet-like glyphs should become •
        # Note: \u2022 IS •, so we only test glyphs that differ from the replacement char
        for glyph in ["\x7f", "\uf0b7", "\uf0a7", "\u25cf"]:
            result = clean_text(f"Item {glyph} one")
            assert "•" in result
            assert glyph not in result
        # \u2022 is already •, so it should stay
        assert "•" in clean_text("Item \u2022 one")

    def test_excessive_blank_lines_collapsed(self):
        text = "paragraph one\n\n\n\n\nparagraph two"
        result = clean_text(text)
        # Should have at most 2 newlines between paragraphs
        assert "\n\n\n" not in result
        assert "paragraph one\n\nparagraph two" == result

    def test_trailing_whitespace_stripped(self):
        text = "hello   \nworld   \n"
        result = clean_text(text)
        for line in result.splitlines():
            assert line == line.rstrip()

    def test_preserves_meaningful_content(self):
        text = "First paragraph.\n\nSecond paragraph with numbers 42 and dates 2024-01-01."
        result = clean_text(text)
        assert "First paragraph." in result
        assert "42" in result
        assert "2024-01-01" in result


# ── chunk_text ─────────────────────────────────────────────────────────────────

class TestChunkText:
    def test_short_text_single_chunk(self):
        text = "Short text."
        result = chunk_text(text, max_chars=3000)
        assert result == ["Short text."]

    def test_empty_string(self):
        result = chunk_text("")
        assert result == [""]

    def test_exact_limit_single_chunk(self):
        # Text exactly at max_chars should not be split
        text = "x" * 100
        result = chunk_text(text, max_chars=100)
        assert len(result) == 1

    def test_long_text_splits(self):
        # Build text that clearly exceeds max_chars
        paras = [f"Paragraph {i}. " + "word " * 50 for i in range(20)]
        text = "\n\n".join(paras)
        result = chunk_text(text, max_chars=500, overlap=50)
        assert len(result) > 1
        # Every chunk should be within limit (approximately — overlap can cause slight overage)
        for chunk in result:
            # Allow some tolerance for overlap prepending
            assert len(chunk) < 1000

    def test_overlap_present(self):
        # With overlap, the tail of chunk N should appear at the start of chunk N+1
        paras = [f"Paragraph {i}. " + "filler " * 40 for i in range(10)]
        text = "\n\n".join(paras)
        chunks = chunk_text(text, max_chars=300, overlap=100)
        if len(chunks) >= 2:
            tail_of_first = chunks[0][-100:]
            assert tail_of_first in chunks[1]

    def test_no_empty_chunks(self):
        text = "A\n\nB\n\nC\n\nD\n\nE"
        result = chunk_text(text, max_chars=5, overlap=0)
        for chunk in result:
            assert chunk.strip() != ""

    def test_excessive_blank_lines_normalized(self):
        text = "para one\n\n\n\n\npara two"
        result = chunk_text(text, max_chars=3000)
        # Should normalize to double newlines
        assert "\n\n\n" not in result[0]
