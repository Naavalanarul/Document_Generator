"""
The LLM outputs one of these shapes. The generators consume it.
Neither side knows about the other — the schema is the only coupling.

Design decisions:
  - Bullet objects in docs (support sub_bullets), plain strings in slides
    (slides must be scannable in 3 seconds; nesting defeats that)
  - paragraphs AND bullets are separate lists in Section so generators
    can apply different Word/PDF styles to each
  - subtitle is always present (defaults to "") so the LLM always has
    a named slot to put one — prevents hallucinated key names
  - DocumentPlan and PresentationPlan are separate schemas because slides
    have fundamentally different structural constraints from doc sections
"""
from typing import List
from pydantic import BaseModel, Field


# ── Shared ─────────────────────────────────────────────────────────────────────

class Bullet(BaseModel):
    text: str
    sub_bullets: List[str] = Field(default_factory=list)
    # One level of nesting max — deliberate. Deeper nesting in a document
    # is almost always a sign the content needs restructuring, not more indents.


# ── Word + PDF ─────────────────────────────────────────────────────────────────

class Section(BaseModel):
    heading: str
    paragraphs: List[str] = Field(default_factory=list)
    bullets: List[Bullet] = Field(default_factory=list)


class DocumentPlan(BaseModel):
    title: str
    subtitle: str = ""
    sections: List[Section] = Field(default_factory=list)


# ── PowerPoint ─────────────────────────────────────────────────────────────────

class Slide(BaseModel):
    title: str
    bullets: List[str] = Field(default_factory=list)  # plain strings, not Bullet objects
    speaker_notes: str = ""


class PresentationPlan(BaseModel):
    title: str
    subtitle: str = ""
    slides: List[Slide] = Field(default_factory=list)
