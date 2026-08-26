"""
Step 6: Render a DocumentPlan into a .docx file using python-docx.
No LLM involvement here — pure deterministic Python.
"""
from docx import Document
from docx.shared import Pt
from schemas import DocumentPlan


def generate_docx(plan: DocumentPlan, output_path: str) -> str:
    doc = Document()

    # Title
    doc.add_heading(plan.title, level=0)

    # Subtitle
    if plan.subtitle:
        p = doc.add_paragraph(plan.subtitle)
        p.runs[0].italic = True
        p.runs[0].font.size = Pt(13)

    # Sections
    for section in plan.sections:
        doc.add_heading(section.heading, level=1)

        for para_text in section.paragraphs:
            doc.add_paragraph(para_text)

        for bullet in section.bullets:
            doc.add_paragraph(bullet.text, style="List Bullet")
            for sub in bullet.sub_bullets:
                doc.add_paragraph(sub, style="List Bullet 2")

    doc.save(output_path)
    return output_path
