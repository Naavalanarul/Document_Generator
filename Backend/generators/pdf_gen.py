"""
Step 6: Render a DocumentPlan into a .pdf file using reportlab.
No LLM involvement here — pure deterministic Python.
"""
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem
)
from schemas import DocumentPlan


def generate_pdf(plan: DocumentPlan, output_path: str) -> str:
    doc = SimpleDocTemplate(
        output_path,
        pagesize=LETTER,
        topMargin=1 * inch, bottomMargin=1 * inch,
        leftMargin=1 * inch, rightMargin=1 * inch,
    )

    styles = getSampleStyleSheet()
    subtitle_style = ParagraphStyle(
        "Subtitle", parent=styles["Normal"],
        fontSize=13, textColor="#555555", spaceAfter=20,
    )

    story = [Paragraph(plan.title, styles["Title"])]

    if plan.subtitle:
        story.append(Paragraph(plan.subtitle, subtitle_style))

    story.append(Spacer(1, 12))

    for section in plan.sections:
        story.append(Paragraph(section.heading, styles["Heading1"]))

        for para_text in section.paragraphs:
            story.append(Paragraph(para_text, styles["BodyText"]))
            story.append(Spacer(1, 6))

        if section.bullets:
            items = []
            for bullet in section.bullets:
                items.append(ListItem(Paragraph(bullet.text, styles["BodyText"])))
                for sub in bullet.sub_bullets:
                    items.append(
                        ListItem(Paragraph(sub, styles["BodyText"]), leftIndent=36)
                    )
            story.append(ListFlowable(items, bulletType="bullet"))

        story.append(Spacer(1, 12))

    doc.build(story)
    return output_path
