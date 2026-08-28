"""
Step 6: Render a DocumentPlan into a .pdf file using reportlab.
No LLM involvement here — pure deterministic Python.
"""
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem, Table, TableStyle
)
from schemas import DocumentPlan


def _build_table(table_data) -> Table:
    """Convert a Table schema object into a reportlab Table flowable."""
    data = [table_data.headers]
    for row in table_data.rows:
        # Pad or truncate rows to match header count
        padded = (row + [""] * len(table_data.headers))[:len(table_data.headers)]
        data.append(padded)

    tbl = Table(data, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4472C4")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F2F2F2")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("TOPPADDING", (0, 1), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F2F2")]),
    ]))
    return tbl


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

        for table_data in section.tables:
            if table_data.headers:
                story.append(Spacer(1, 6))
                story.append(_build_table(table_data))
                story.append(Spacer(1, 6))

        story.append(Spacer(1, 12))

    doc.build(story)
    return output_path
