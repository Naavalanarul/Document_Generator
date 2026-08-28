"""
Schema validation edge-case tests.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from pydantic import ValidationError
from schemas import (
    Bullet, Table, Section, DocumentPlan, PresentationPlan, Slide,
)


class TestTable:
    def test_valid_table(self):
        t = Table(headers=["Name", "Age"], rows=[["Alice", "30"], ["Bob", "25"]])
        assert len(t.headers) == 2
        assert len(t.rows) == 2

    def test_empty_rows(self):
        t = Table(headers=["Col1"])
        assert t.rows == []

    def test_missing_headers_fails(self):
        with pytest.raises(ValidationError):
            Table(rows=[["a", "b"]])  # headers is required


class TestSection:
    def test_empty_section(self):
        s = Section(heading="Intro")
        assert s.paragraphs == []
        assert s.bullets == []
        assert s.tables == []

    def test_section_with_all_fields(self):
        s = Section(
            heading="Summary",
            paragraphs=["Some text."],
            bullets=[Bullet(text="item 1", sub_bullets=["sub a"])],
            tables=[Table(headers=["X", "Y"], rows=[["1", "2"]])],
        )
        assert s.heading == "Summary"
        assert len(s.tables) == 1


class TestDocumentPlan:
    def test_minimal_document(self):
        dp = DocumentPlan(title="Test")
        assert dp.subtitle == ""
        assert dp.sections == []
        assert dp.sources == []

    def test_document_with_sources(self):
        dp = DocumentPlan(
            title="Research",
            sources=["https://example.com", "https://other.com"],
        )
        assert len(dp.sources) == 2

    def test_missing_title_fails(self):
        with pytest.raises(ValidationError):
            DocumentPlan()


class TestPresentationPlan:
    def test_minimal_presentation(self):
        pp = PresentationPlan(title="Slides")
        assert pp.slides == []
        assert pp.sources == []

    def test_slide_defaults(self):
        s = Slide(title="Intro")
        assert s.bullets == []
        assert s.speaker_notes == ""

    def test_missing_title_fails(self):
        with pytest.raises(ValidationError):
            PresentationPlan()


class TestBullet:
    def test_bullet_defaults(self):
        b = Bullet(text="Hello")
        assert b.sub_bullets == []

    def test_bullet_with_sub(self):
        b = Bullet(text="Main", sub_bullets=["sub1", "sub2"])
        assert len(b.sub_bullets) == 2
