#!/usr/bin/env python3
"""
Render an executive incident report to a one-page PDF using reportlab.

Usage:
    python render_report.py '<json>'

<json> is an object with the keys: title, executive_summary, timeline,
root_cause, impact, remedial_steps. Prints {"pdf_path": "..."} on success,
or {"error": "..."} on failure.
"""
import sys, os, json, uuid, traceback
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.enums import TA_LEFT

# CWD when this script runs via get_skill_script is the skill's own
# folder, not the project root -- so REPORTS_DIR can't be a plain
# relative path. Anchor it to this file's location instead: four levels
# up from skills/incident-report/scripts/ is the project root.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
REPORTS_DIR = os.path.join(_PROJECT_ROOT, "static", "reports")

def _prep(text: str) -> str:
    """
    Paragraph text is a small XML-like markup (supports <b>, <br/>, etc.),
    so literal &, <, > in report content must be escaped or they'll be
    parsed as markup instead of displayed. Also convert real newlines to
    <br/> so multi-line fields (e.g. a timeline with one event per line)
    wrap as separate lines instead of running together.
    """
    if not isinstance(text, str):
        text = str(text)
    return escape(text).replace("\n", "<br/>")

def build_report_pdf(report: dict) -> str:
    """
    Render an executive incident report dict to a one-page PDF and return
    its path. Expects the keys title, executive_summary, timeline,
    root_cause, impact, remedial_steps.
    """
    os.makedirs(REPORTS_DIR, exist_ok=True)
    filename = f"incident-report-{uuid.uuid4().hex}.pdf"
    path = os.path.join(REPORTS_DIR, filename)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle", parent=styles["Title"], alignment=TA_LEFT, fontSize=18
    )
    meta_style = ParagraphStyle(
        "Meta", parent=styles["Normal"], fontSize=9, textColor="#555555"
    )
    heading_style = ParagraphStyle(
        "SectionHeading", parent=styles["Heading2"], spaceBefore=12, spaceAfter=4
    )
    body_style = ParagraphStyle(
        "Body", parent=styles["BodyText"], fontSize=10, leading=14
    )

    doc = SimpleDocTemplate(
        path,
        pagesize=LETTER,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
    )

    story = [
        Paragraph(_prep(report.get("title", "Incident Report")), title_style),
        Paragraph(datetime.now().strftime("Generated %Y-%m-%d %H:%M"), meta_style),
        Spacer(1, 0.2 * inch),
    ]

    for heading, key in [
        ("Executive Summary", "executive_summary"),
        ("Timeline", "timeline"),
        ("Root Cause", "root_cause"),
        ("Impact", "impact"),
        ("Recommended Remedial Steps", "remedial_steps"),
    ]:
        story.append(Paragraph(heading, heading_style))
        story.append(Paragraph(_prep(report.get(key, "")), body_style))

    doc.build(story)
    return path

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "expected one JSON argument"}))
        sys.exit(1)

    try:
        report = json.loads(sys.argv[1])
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"invalid JSON argument: {e}"}))
        sys.exit(1)

    try:
        path = build_report_pdf(report)
    except Exception as e:
        print(json.dumps({
            "error": f"failed to render PDF: {e}",
            "traceback": traceback.format_exc()
        }))
        sys.exit(1)

    print(json.dumps({"filename": os.path.basename(path)}))

if __name__ == "__main__":
    main()