
import gradio as gr
import plotly.graph_objects as go
import tempfile
import os
import re
from datetime import datetime
from html import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable
)
from reportlab.graphics.shapes import Drawing, String, Rect, Line

# ============================================================
# INSTITUTION DETAILS — CHANGE THESE BEFORE PUBLISHING
# ============================================================

INSTITUTION_NAME = "YOUR INSTITUTION NAME"
INSTITUTION_TAGLINE = "ACADEMIC EXCELLENCE • STUDENT PERFORMANCE"

# ============================================================
# PREMIUM DESIGN COLOURS
# ============================================================

WARM_WHITE = "#F5F3EE"
CHARCOAL = "#202522"
SAGE_GREEN = "#526B5D"
BRONZE = "#A77B46"
MUTED_GREY = "#D9D5CC"
BORDER = "#E2DED5"
SOFT_TEXT = "#696C64"
RED = "#A9473F"

SUBJECTS = [
    "Mathematics", "Science", "English",
    "Hindi", "Social Science", "Sanskrit"
]

# ============================================================
# RESULT AND GRADING LOGIC
# ============================================================

def subject_grade(mark):
    if mark < 33:
        return "F"
    if mark >= 90:
        return "A+"
    if mark >= 80:
        return "A"
    if mark >= 70:
        return "B"
    if mark >= 60:
        return "C"
    if mark >= 45:
        return "D"
    return "E"


def evaluate_result(marks, grace_applied=False):
    total = sum(marks)
    percentage = total / 600 * 100

    failed_indices = [
        i for i, mark in enumerate(marks)
        if mark < 33
    ]

    # Demonstration grace policy:
    # Grace pass is allowed only if officially approved,
    # exactly one subject is below 33, and that mark is at least 28.
    # Verify the actual institution's policy before real use.

    grace_pass = (
        grace_applied
        and len(failed_indices) == 1
        and marks[failed_indices[0]] >= 28
    )

    if not failed_indices:
        status = "PASS"
        overall_grade = subject_grade(
            min(100, round(percentage))
        )

    elif grace_pass:
        status = "PASS * GRTH"
        overall_grade = subject_grade(
            min(100, round(percentage))
        )

    else:
        status = "FAIL"
        overall_grade = "F"

    return (
        total, percentage, overall_grade,
        status, grace_pass
    )


# ============================================================
# PDF PERFORMANCE CHART
# ============================================================

def make_pdf_chart(marks):
    width, height = 490, 205
    drawing = Drawing(width, height)

    left, bottom = 36, 35
    plot_width, plot_height = 420, 135

    # Grid lines and axis labels
    for value in range(0, 101, 20):
        y = bottom + plot_height * value / 100

        drawing.add(Line(
            left, y,
            left + plot_width, y,
            strokeColor=colors.HexColor(BORDER),
            strokeWidth=0.6
        ))

        drawing.add(String(
            left - 24, y - 3,
            str(value),
            fontName="Helvetica",
            fontSize=8,
            fillColor=colors.HexColor(SOFT_TEXT)
        ))

    # Minimum passing threshold
    pass_y = bottom + plot_height * 33 / 100

    drawing.add(Line(
        left, pass_y,
        left + plot_width, pass_y,
        strokeColor=colors.HexColor(BRONZE),
        strokeWidth=1,
        strokeDashArray=[4, 3]
    ))

    bar_space = plot_width / len(SUBJECTS)
    bar_width = 30

    for i, (subject, mark) in enumerate(
        zip(SUBJECTS, marks)
    ):
        x = (
            left + i * bar_space
            + (bar_space - bar_width) / 2
        )

        bar_height = plot_height * mark / 100

        if mark >= 85:
            fill = colors.HexColor(BRONZE)
        elif mark >= 33:
            fill = colors.HexColor(SAGE_GREEN)
        else:
            fill = colors.HexColor(RED)

        drawing.add(Rect(
            x, bottom,
            bar_width, bar_height,
            fillColor=fill,
            strokeColor=None
        ))

        drawing.add(String(
            x + bar_width / 2,
            bottom + bar_height + 5,
            str(mark),
            textAnchor="middle",
            fontName="Helvetica-Bold",
            fontSize=8,
            fillColor=colors.HexColor(CHARCOAL)
        ))

        label = subject

        if len(label) > 12:
            label = label[:11] + "."

        drawing.add(String(
            x + bar_width / 2,
            bottom - 13,
            label,
            textAnchor="middle",
            fontName="Helvetica",
            fontSize=6.5,
            fillColor=colors.HexColor(CHARCOAL)
        ))

    drawing.add(String(
        left, height - 10,
        "SUBJECT-WISE PERFORMANCE",
        fontName="Helvetica-Bold",
        fontSize=10,
        fillColor=colors.HexColor(CHARCOAL)
    ))

    return drawing


# ============================================================
# PROFESSIONAL PDF MARKSHEET
# ============================================================

def create_report_pdf(
    name, roll, gender, marks, total,
    percentage, grade, status, grace_pass
):
    safe_roll = re.sub(
        r"[^A-Za-z0-9_-]", "_", roll
    )[:40]

    filepath = os.path.join(
        tempfile.gettempdir(),
        f"Report_Card_{safe_roll or 'student'}.pdf"
    )

    page_w, page_h = A4

    left = 16 * mm
    right = 16 * mm
    usable_w = page_w - left - right

    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=right,
        leftMargin=left,
        topMargin=15 * mm,
        bottomMargin=18 * mm,
        title=f"Academic Report Card - {name}",
        author=INSTITUTION_NAME
    )

    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="Institution",
        fontName="Helvetica-Bold",
        fontSize=19,
        leading=23,
        textColor=colors.HexColor(CHARCOAL),
        alignment=TA_CENTER
    ))

    styles.add(ParagraphStyle(
        name="SubInstitution",
        fontName="Helvetica",
        fontSize=8,
        leading=12,
        textColor=colors.HexColor(SOFT_TEXT),
        alignment=TA_CENTER
    ))

    styles.add(ParagraphStyle(
        name="ReportTitle",
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor(SAGE_GREEN),
        alignment=TA_CENTER
    ))

    styles.add(ParagraphStyle(
        name="SectionHeading",
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor(BRONZE),
        spaceBefore=2,
        spaceAfter=6
    ))

    styles.add(ParagraphStyle(
        name="BodyCustom",
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor(CHARCOAL)
    ))

    styles.add(ParagraphStyle(
        name="SmallCustom",
        fontName="Helvetica",
        fontSize=7,
        leading=9,
        textColor=colors.HexColor(SOFT_TEXT)
    ))

    styles.add(ParagraphStyle(
        name="HeaderWhite",
        fontName="Helvetica-Bold",
        fontSize=7.2,
        leading=9,
        textColor=colors.white,
        alignment=TA_CENTER
    ))

    styles.add(ParagraphStyle(
        name="CellCenter",
        fontName="Helvetica",
        fontSize=7.8,
        leading=10,
        textColor=colors.HexColor(CHARCOAL),
        alignment=TA_CENTER
    ))

    styles.add(ParagraphStyle(
        name="MetricValue",
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=17,
        textColor=colors.HexColor(CHARCOAL),
        alignment=TA_CENTER
    ))

    styles.add(ParagraphStyle(
        name="MetricLabel",
        fontName="Helvetica-Bold",
        fontSize=6.5,
        leading=9,
        textColor=colors.HexColor(SOFT_TEXT),
        alignment=TA_CENTER
    ))

    P = lambda txt, style="BodyCustom": Paragraph(
        str(txt), styles[style]
    )

    story = []

    report_id = "SRP-" + datetime.now().strftime(
        "%Y%m%d-%H%M%S"
    )

    # Institutional header
    story.append(P(
        escape(INSTITUTION_NAME),
        "Institution"
    ))

    story.append(P(
        escape(INSTITUTION_TAGLINE),
        "SubInstitution"
    ))

    story.append(Spacer(1, 1 * mm))

    story.append(P(
        "ACADEMIC REPORT CARD",
        "ReportTitle"
    ))

    story.append(Spacer(1, 3 * mm))

    story.append(HRFlowable(
        width="100%",
        thickness=2,
        color=colors.HexColor(BRONZE)
    ))

    story.append(Spacer(1, 3 * mm))

    # Student and report information
    info_data = [
        [
            P("<b>STUDENT DETAILS</b>", "SectionHeading"),
            P("<b>REPORT INFORMATION</b>", "SectionHeading")
        ],
        [
            P(
                f"<b>Name:</b> {escape(name)}<br/>"
                f"<b>Roll Number:</b> {escape(roll)}<br/>"
                f"<b>Gender:</b> {escape(str(gender))}<br/>"
                f"<b>Assessment:</b> Academic Result"
            ),
            P(
                f"<b>Report No.:</b> {report_id}<br/>"
                f"<b>Date:</b> "
                f"{datetime.now().strftime('%d %B %Y')}<br/>"
                f"<b>Total Subjects:</b> 6<br/>"
                f"<b>Maximum Marks:</b> 600"
            )
        ]
    ]

    info_table = Table(
        info_data,
        colWidths=[
            usable_w * 0.5,
            usable_w * 0.5
        ]
    )

    info_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1),
         colors.HexColor(WARM_WHITE)),
        ("BOX", (0, 0), (-1, -1), 0.6,
         colors.HexColor(BORDER)),
        ("INNERGRID", (0, 0), (-1, -1), 0.4,
         colors.HexColor(BORDER)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))

    story.append(info_table)
    story.append(Spacer(1, 4 * mm))

    # Marks table
    story.append(P(
        "SUBJECT-WISE MARKS",
        "SectionHeading"
    ))

    header = [
        "S. No.",
        "Subject",
        "Max. Marks",
        "Min. Marks",
        "Obtained Marks",
        "Grade / Result"
    ]

    marks_data = [
        [P(h, "HeaderWhite") for h in header]
    ]

    for i, (subject, mark) in enumerate(
        zip(SUBJECTS, marks), 1
    ):
        sg = subject_grade(mark)

        if mark < 33 and grace_pass:
            result = "* GRTH"
            cell_grade = "E"
        elif mark < 33:
            result = "FAIL"
            cell_grade = "F"
        elif mark >= 85:
            result = "* DISTN"
            cell_grade = sg
        else:
            result = "PASS"
            cell_grade = sg

        marks_data.append([
            P(str(i), "CellCenter"),
            P(escape(subject)),
            P("100", "CellCenter"),
            P("33", "CellCenter"),
            P(f"<b>{mark}</b>", "CellCenter"),
            P(
                f"<b>{cell_grade} / {result}</b>",
                "CellCenter"
            )
        ])

    # Total row
    marks_data.append([
        P("", "CellCenter"),
        P("<b>TOTAL</b>"),
        P("<b>600</b>", "CellCenter"),
        P("—", "CellCenter"),
        P(f"<b>{total}</b>", "CellCenter"),
        P(
            f"<b>{grade} / {status}</b>",
            "CellCenter"
        )
    ])

    widths = [
        usable_w * 0.09,
        usable_w * 0.25,
        usable_w * 0.15,
        usable_w * 0.14,
        usable_w * 0.19,
        usable_w * 0.18
    ]

    marks_table = Table(
        marks_data,
        colWidths=widths,
        repeatRows=1
    )

    marks_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0),
         colors.HexColor(CHARCOAL)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, 1), (-1, -2),
         colors.white),
        ("BACKGROUND", (0, -1), (-1, -1),
         colors.HexColor("#E8E5DD")),
        ("BOX", (0, 0), (-1, -1), 0.7,
         colors.HexColor(BORDER)),
        ("INNERGRID", (0, 0), (-1, -1), 0.4,
         colors.HexColor(BORDER)),
        ("LINEABOVE", (0, -1), (-1, -1), 1.2,
         colors.HexColor(BRONZE)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))

    for row_index, mark in enumerate(marks, start=1):
        if mark >= 85:
            marks_table.setStyle(TableStyle([
                ("BACKGROUND", (5, row_index), (5, row_index),
                 colors.HexColor(SAGE_GREEN)),
                ("TEXTCOLOR", (5, row_index), (5, row_index),
                 colors.white)
            ]))

        elif mark < 33 and grace_pass:
            marks_table.setStyle(TableStyle([
                ("BACKGROUND", (5, row_index), (5, row_index),
                 colors.HexColor(BRONZE)),
                ("TEXTCOLOR", (5, row_index), (5, row_index),
                 colors.white)
            ]))

        elif mark < 33:
            marks_table.setStyle(TableStyle([
                ("TEXTCOLOR", (5, row_index), (5, row_index),
                 colors.HexColor(RED))
            ]))

    story.append(marks_table)
    story.append(Spacer(1, 4 * mm))

    # Result summary
    story.append(P(
        "RESULT SUMMARY",
        "SectionHeading"
    ))

    summary = Table([
        [
            P(str(total), "MetricValue"),
            P(f"{percentage:.2f}%", "MetricValue"),
            P(grade, "MetricValue"),
            P(status, "MetricValue")
        ],
        [
            P("TOTAL MARKS / 600", "MetricLabel"),
            P("PERCENTAGE", "MetricLabel"),
            P("FINAL GRADE", "MetricLabel"),
            P("RESULT STATUS", "MetricLabel")
        ]
    ], colWidths=[usable_w / 4] * 4)

    summary.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1),
         colors.HexColor("#E8E5DD")),
        ("BACKGROUND", (1, 0), (1, -1),
         colors.HexColor("#E1E9E2")),
        ("BACKGROUND", (2, 0), (2, -1),
         colors.HexColor("#F0E8DC")),
        ("BACKGROUND", (3, 0), (3, -1),
         colors.HexColor(
             "#E1E9E2" if "PASS" in status
             else "#F7E8E5"
         )),
        ("BOX", (0, 0), (-1, -1), 0.5,
         colors.HexColor(BORDER)),
        ("INNERGRID", (0, 0), (-1, -1), 0.5,
         colors.HexColor(BORDER)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, 0), 10),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 3),
        ("TOPPADDING", (0, 1), (-1, 1), 3),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 10),
    ]))

    story.append(summary)
    story.append(Spacer(1, 4 * mm))

    # Performance chart
    story.append(P(
        "SUBJECT-WISE PERFORMANCE",
        "SectionHeading"
    ))

    story.append(make_pdf_chart(marks))
    story.append(Spacer(1, 3 * mm))

    # Grade legend
    story.append(P(
        "GRADE & RESULT LEGEND",
        "SectionHeading"
    ))

    legend_data = [
        [
            P("<b>Grade</b>"),
            P("<b>Percentage range</b>"),
            P("<b>Meaning</b>")
        ],
        [P("A+"), P("90–100"), P("Outstanding")],
        [P("A"), P("80–89"), P("Excellent")],
        [P("B"), P("70–79"), P("Very good")],
        [P("C"), P("60–69"), P("Good")],
        [P("D"), P("45–59"), P("Satisfactory")],
        [P("E"), P("33–44"), P("Needs improvement")],
        [P("F"), P("Below 33"), P("Fail")],
        [
            P("* DISTN"),
            P("85 marks or above"),
            P("Distinction")
        ],
        [
            P("* GRTH"),
            P("Official grace applied"),
            P("Grace pass")
        ]
    ]

    legend = Table(
        legend_data,
        colWidths=[
            usable_w * 0.19,
            usable_w * 0.33,
            usable_w * 0.48
        ]
    )

    legend.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0),
         colors.HexColor(WARM_WHITE)),
        ("BOX", (0, 0), (-1, -1), 0.5,
         colors.HexColor(BORDER)),
        ("INNERGRID", (0, 0), (-1, -1), 0.35,
         colors.HexColor(BORDER)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))

    story.append(legend)
    story.append(Spacer(1, 4 * mm))

    # Academic remarks
    if grace_pass:
        remarks = (
            "Grace pass is indicated according to the demonstration rule. "
            "Verify official institutional approval before issuing."
        )
    elif any(mark < 33 for mark in marks):
        remarks = (
            "The student has marks below the minimum passing threshold "
            "in one or more subjects."
        )
    else:
        remarks = (
            f"The student has secured {percentage:.2f}% with Grade {grade}. "
            "The student has met the minimum passing requirement in every subject."
        )

    story.append(P(
        "ACADEMIC REMARKS",
        "SectionHeading"
    ))

    remarks_table = Table(
        [[P(escape(remarks))]],
        colWidths=[usable_w]
    )

    remarks_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1),
         colors.HexColor("#E8EEE9")),
        ("BOX", (0, 0), (-1, -1), 0.5,
         colors.HexColor(BORDER)),
        ("LINEBEFORE", (0, 0), (0, -1), 2,
         colors.HexColor(SAGE_GREEN)),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))

    story.append(remarks_table)
    story.append(Spacer(1, 7 * mm))

    # Signature lines
    signatures = Table([
        [
            "____________________",
            "____________________",
            "____________________"
        ],
        [
            "Class Teacher",
            "Head of Department",
            "Authorised Signatory"
        ]
    ], colWidths=[usable_w / 3] * 3)

    signatures.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("TEXTCOLOR", (0, 0), (-1, -1),
         colors.HexColor(CHARCOAL)),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))

    story.append(signatures)
    story.append(Spacer(1, 4 * mm))

    story.append(HRFlowable(
        width="100%",
        thickness=0.5,
        color=colors.HexColor(BORDER)
    ))

    story.append(Spacer(1, 2 * mm))

    story.append(P(
        "SYSTEM-GENERATED REPORT. Confirm official grading and grace "
        "policies before using this document as an official marksheet.",
        "SmallCustom"
    ))

    # Page border and footer
    def draw_page(canvas, document):
        canvas.saveState()

        canvas.setFillColor(colors.HexColor(WARM_WHITE))
        canvas.rect(
            0, 0, page_w, page_h,
            stroke=0, fill=1
        )

        canvas.setStrokeColor(colors.HexColor(BORDER))
        canvas.setLineWidth(0.7)

        canvas.rect(
            8 * mm, 8 * mm,
            page_w - 16 * mm,
            page_h - 16 * mm,
            stroke=1, fill=0
        )

        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor(SOFT_TEXT))

        canvas.drawString(
            left, 9 * mm,
            INSTITUTION_NAME
        )

        canvas.drawRightString(
            page_w - right,
            9 * mm,
            f"Page {document.page}"
        )

        canvas.restoreState()

    doc.build(
        story,
        onFirstPage=draw_page,
        onLaterPages=draw_page
    )

    return filepath


# ============================================================
# PREMIUM WEBSITE CSS
# ============================================================

CSS = """
:root {
    --warm-white: #F5F3EE;
    --charcoal: #202522;
    --sage: #526B5D;
    --bronze: #A77B46;
    --border: #E2DED5;
    --muted: #696C64;
}

.gradio-container {
    max-width: 1180px !important;
    margin: 0 auto !important;
    padding: 20px 22px 30px !important;
    background: var(--warm-white) !important;
    font-family: Inter, Arial, Helvetica, sans-serif !important;
}

body, .gradio-container {
    background: var(--warm-white) !important;
}

#topbar {
    background: var(--charcoal);
    color: var(--warm-white);
    padding: 20px 26px;
    border-radius: 8px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 16px;
    margin-bottom: 24px;
    border-bottom: 3px solid var(--bronze);
}

.brand {
    font-size: 16px;
    font-weight: 800;
    letter-spacing: 1.8px;
}

.brand-sub {
    font-size: 10px;
    color: #D9D5CC;
    letter-spacing: 2px;
    margin-top: 6px;
}

.top-label {
    font-size: 10px;
    color: #D8C3A6;
    letter-spacing: 1.4px;
    text-align: right;
    line-height: 1.8;
}

#hero {
    padding: 28px 8px 30px;
    border-bottom: 1px solid #D9D5CC;
    margin-bottom: 28px;
}

.eyebrow, .section-eyebrow {
    color: var(--bronze);
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 2px;
    margin-bottom: 10px;
}

.hero-title {
    color: var(--charcoal);
    font-size: clamp(32px, 5vw, 49px);
    font-weight: 750;
    line-height: 1.08;
    letter-spacing: -1.3px;
    margin: 0 0 14px;
}

.hero-description {
    color: var(--muted);
    font-size: 13px;
    line-height: 1.85;
    max-width: 680px;
}

.section-heading {
    color: var(--charcoal);
    font-size: 22px;
    font-weight: 750;
    letter-spacing: -.4px;
    margin-bottom: 7px;
}

.section-description {
    color: var(--muted);
    font-size: 12px;
    line-height: 1.75;
    margin-bottom: 18px;
}

#formpanel {
    background: #EEECE6;
    border: 1px solid var(--border);
    border-radius: 9px;
    padding: 24px;
    box-shadow: 0 5px 18px rgba(32,37,34,.035);
}

#formpanel label {
    color: var(--charcoal) !important;
    font-weight: 650 !important;
}

#formpanel input,
#formpanel select,
#formpanel textarea {
    background: #FBFAF7 !important;
    border: 1px solid #D5D1C8 !important;
    color: var(--charcoal) !important;
    border-radius: 6px !important;
}

#formpanel input:focus,
#formpanel select:focus {
    border-color: var(--sage) !important;
    box-shadow: 0 0 0 2px rgba(82,107,93,.12) !important;
}

#calculate-btn {
    background: var(--sage) !important;
    color: white !important;
    border: 1px solid var(--sage) !important;
    border-radius: 6px !important;
    font-weight: 750 !important;
    min-height: 46px;
    transition: .18s ease;
}

#calculate-btn:hover {
    background: #43584C !important;
}

#reset-btn {
    background: transparent !important;
    color: var(--charcoal) !important;
    border: 1px solid #C8C3B9 !important;
    border-radius: 6px !important;
    min-height: 46px;
}

.result-panel {
    background: #FBFAF7;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 23px;
    margin: 10px 0 16px;
    box-shadow: 0 4px 15px rgba(32,37,34,.025);
}

.profile-heading {
    font-size: 26px;
    color: var(--charcoal);
    font-weight: 750;
    overflow-wrap: anywhere;
    margin-bottom: 12px;
    letter-spacing: -.4px;
}

.profile-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 12px 25px;
    color: var(--muted);
    font-size: 10px;
    letter-spacing: 1px;
}

.metric-card {
    min-height: 150px;
    padding: 21px;
    border-radius: 8px;
    margin: 5px 0 12px;
    box-sizing: border-box;
    box-shadow: 0 4px 14px rgba(32,37,34,.035);
}

.metric-dark {
    background: var(--charcoal);
    color: var(--warm-white);
}

.metric-sage {
    background: var(--sage);
    color: white;
}

.metric-light {
    background: #E6E2D9;
    color: var(--charcoal);
    border: 1px solid #D8D3C9;
}

.metric-label {
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 1.5px;
    margin-bottom: 18px;
    opacity: .82;
}

.metric-value {
    font-size: clamp(26px, 3vw, 37px);
    font-weight: 750;
    overflow-wrap: anywhere;
    letter-spacing: -.7px;
}

.metric-value span {
    font-size: 13px;
    font-weight: 400;
    opacity: .75;
    letter-spacing: 0;
}

.metric-foot {
    font-size: 11px;
    margin-top: 10px;
    opacity: .8;
}

.grade-value {
    font-size: 36px;
    font-weight: 750;
}

.grade-description {
    font-size: 11px;
    margin-top: 6px;
    color: var(--muted);
}

.status-pill {
    display: inline-block;
    padding: 6px 11px;
    margin-top: 12px;
    border-radius: 4px;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 1px;
}

#chart-panel {
    background: #FBFAF7;
    border: 1px solid var(--border);
    border-radius: 9px;
    padding: 12px;
    box-shadow: 0 4px 16px rgba(32,37,34,.025);
}

#footer {
    border-top: 1px solid #D9D5CC;
    padding: 20px 5px;
    margin-top: 32px;
    color: var(--muted);
    font-size: 11px;
    line-height: 1.9;
}

button, input, select {
    transition: border-color .15s ease, background .15s ease;
}

@media (max-width: 640px) {
    .gradio-container {
        padding: 12px 10px 22px !important;
    }

    #topbar {
        padding: 17px;
        align-items: flex-start;
    }

    .brand {
        font-size: 13px;
    }

    .brand-sub {
        font-size: 9px;
        letter-spacing: 1.2px;
    }

    .top-label {
        font-size: 8px;
    }

    #hero {
        padding: 24px 4px;
    }

    #formpanel {
        padding: 15px;
    }

    .metric-card {
        min-height: 125px;
        padding: 16px;
    }
}
"""


# ============================================================
# CALCULATE RESULT, BUILD GRAPH AND GENERATE PDF
# ============================================================

def calculate_result(name, roll, gender, grace_applied, *marks):
    name = str(name or "").strip()
    roll = str(roll or "").strip()

    if not name:
        raise gr.Error(
            "Please enter the student's full name."
        )

    if not roll:
        raise gr.Error(
            "Please enter the roll number."
        )

    if not gender:
        raise gr.Error(
            "Please select gender."
        )

    clean_marks = []

    for subject, mark in zip(SUBJECTS, marks):
        if mark is None:
            raise gr.Error(
                f"Please enter marks for {subject}."
            )

        try:
            mark = float(mark)
        except (ValueError, TypeError):
            raise gr.Error(
                f"Invalid marks for {subject}."
            )

        if not 0 <= mark <= 100:
            raise gr.Error(
                f"{subject}: marks must be between 0 and 100."
            )

        if not mark.is_integer():
            raise gr.Error(
                f"{subject}: enter whole-number marks."
            )

        clean_marks.append(int(mark))

    total, percentage, grade, status, grace_pass = (
        evaluate_result(clean_marks, grace_applied)
    )

    # Student information panel
    profile_html = f"""
    <div class="result-panel">
        <div class="section-eyebrow">STUDENT RECORD</div>
        <div class="profile-heading">{escape(name)}</div>
        <div class="profile-meta">
            <span>ROLL NUMBER: {escape(roll)}</span>
            <span>GENDER: {escape(str(gender))}</span>
        </div>
    </div>
    """

    # Total marks card
    total_html = f"""
    <div class="metric-card metric-dark">
        <div class="metric-label">TOTAL MARKS</div>
        <div class="metric-value">{total}<span> / 600</span></div>
        <div class="metric-foot">Aggregate score</div>
    </div>
    """

    # Percentage card
    percentage_html = f"""
    <div class="metric-card metric-sage">
        <div class="metric-label">PERCENTAGE</div>
        <div class="metric-value">{percentage:.2f}<span>%</span></div>
        <div class="metric-foot">Overall academic performance</div>
    </div>
    """

    descriptions = {
        "A+": "Outstanding performance",
        "A": "Excellent performance",
        "B": "Very good performance",
        "C": "Good performance",
        "D": "Satisfactory performance",
        "E": "Needs improvement",
        "F": "One or more subjects below passing marks"
    }

    status_color = (
        SAGE_GREEN if "PASS" in status else RED
    )

    status_bg = (
        "#E8EEE9" if "PASS" in status
        else "#F7E8E5"
    )

    grade_html = f"""
    <div class="metric-card metric-light">
        <div class="metric-label">FINAL GRADE</div>
        <div class="grade-value">{grade}</div>
        <div class="grade-description">{descriptions[grade]}</div>
        <div class="status-pill"
             style="background:{status_bg};color:{status_color};">
            {escape(status)}
        </div>
    </div>
    """

    # Animated Plotly graph
    bar_colors = [
        BRONZE if mark >= 85
        else SAGE_GREEN if mark >= 33
        else RED
        for mark in clean_marks
    ]

    fig = go.Figure(
        data=[
            go.Bar(
                x=SUBJECTS,
                y=[0] * len(clean_marks),
                marker=dict(
                    color=bar_colors,
                    line=dict(
                        color=WARM_WHITE,
                        width=1.5
                    )
                ),
                text=[
                    f"{mark}/100"
                    for mark in clean_marks
                ],
                textposition="outside",
                customdata=clean_marks,
                hovertemplate=(
                    "<b>%{x}</b><br>"
                    "Marks: %{customdata}/100"
                    "<extra></extra>"
                )
            )
        ],
        frames=[
            go.Frame(
                name="final",
                data=[
                    go.Bar(
                        y=clean_marks,
                        text=[
                            f"{mark}/100"
                            for mark in clean_marks
                        ]
                    )
                ]
            )
        ]
    )

    fig.update_layout(
        title=dict(
            text="SUBJECT-WISE PERFORMANCE",
            x=0.03,
            font=dict(
                size=17,
                color=CHARCOAL
            )
        ),
        paper_bgcolor="#FBFAF7",
        plot_bgcolor="#FBFAF7",
        font=dict(
            family="Arial, sans-serif",
            color=CHARCOAL
        ),
        height=400,
        margin=dict(
            l=35, r=25, t=75, b=80
        ),
        yaxis=dict(
            title="Marks obtained",
            range=[0, 115],
            dtick=20,
            gridcolor=BORDER,
            zeroline=False
        ),
        xaxis=dict(
            title="",
            tickangle=-15,
            showgrid=False
        ),
        showlegend=False,
        bargap=0.38,
        transition=dict(
            duration=800,
            easing="cubic-in-out"
        ),
        updatemenus=[
            dict(
                type="buttons",
                showactive=False,
                x=1,
                y=1.16,
                xanchor="right",
                yanchor="top",
                buttons=[
                    dict(
                        label="Play chart",
                        method="animate",
                        args=[
                            ["final"],
                            {
                                "frame": {
                                    "duration": 800,
                                    "redraw": True
                                },
                                "transition": {
                                    "duration": 700
                                },
                                "mode": "immediate"
                            }
                        ]
                    )
                ]
            )
        ]
    )

    fig.add_hline(
        y=33,
        line_dash="dash",
        line_color=BRONZE,
        annotation_text="Minimum passing marks: 33",
        annotation_position="bottom right"
    )

    # Create PDF
    pdf_path = create_report_pdf(
        name,
        roll,
        gender,
        clean_marks,
        total,
        percentage,
        grade,
        status,
        grace_pass
    )

    return (
        profile_html,
        total_html,
        percentage_html,
        grade_html,
        fig,
        pdf_path
    )


# ============================================================
# RESET FORM
# ============================================================

def reset_form():
    return (
        "", "", None, False,
        None, None, None, None, None, None,
        "", "", "", "", None, None
    )


# ============================================================
# BUILD THE GRADIO WEBSITE
# ============================================================

with gr.Blocks(
    theme=gr.themes.Base(
        primary_hue="green",
        secondary_hue="stone",
        neutral_hue="stone"
    ),
    css=CSS,
    title="Student Result Portal"
) as app:

    gr.HTML("""
    <div id="topbar">
        <div>
            <div class="brand">ACADEMIC RECORDS</div>
            <div class="brand-sub">STUDENT RESULT PORTAL</div>
        </div>
        <div class="top-label">
            ACADEMIC PERFORMANCE<br>
            INDIVIDUAL REPORTS
        </div>
    </div>

    <div id="hero">
        <div class="eyebrow">ACADEMIC RECORDS</div>
        <div class="hero-title">Student Result<br>Portal</div>
        <div class="hero-description">
            Generate individual academic results and polished,
            printable PDF report cards with subject-wise analysis.
        </div>
    </div>

    <div class="section-eyebrow">
        01 / STUDENT INFORMATION
    </div>

    <div class="section-heading">
        Enter student details
    </div>

    <div class="section-description">
        Complete all fields and enter marks out of 100 per subject.
    </div>
    """)

    with gr.Group(elem_id="formpanel"):

        with gr.Row():
            name_input = gr.Textbox(
                label="Student full name",
                placeholder="Enter full name",
                scale=2
            )

            roll_input = gr.Textbox(
                label="Roll number",
                placeholder="Enter roll number"
            )

            gender_input = gr.Dropdown(
                choices=["Male", "Female", "Other"],
                label="Gender",
                value=None
            )

        gr.HTML("""
        <div class="section-eyebrow"
             style="margin-top:20px;">
            SUBJECT ASSESSMENT / 100 MARKS EACH
        </div>
        """)

        with gr.Row():
            math_input = gr.Number(
                label="Mathematics",
                minimum=0,
                maximum=100,
                precision=0
            )

            science_input = gr.Number(
                label="Science",
                minimum=0,
                maximum=100,
                precision=0
            )

        with gr.Row():
            english_input = gr.Number(
                label="English",
                minimum=0,
                maximum=100,
                precision=0
            )

            hindi_input = gr.Number(
                label="Hindi",
                minimum=0,
                maximum=100,
                precision=0
            )

        with gr.Row():
            social_input = gr.Number(
                label="Social Science",
                minimum=0,
                maximum=100,
                precision=0
            )

            sanskrit_input = gr.Number(
                label="Sanskrit",
                minimum=0,
                maximum=100,
                precision=0
            )

        grace_input = gr.Checkbox(
            label=(
                "Official grace marks have been approved "
                "for this student"
            ),
            value=False
        )

        with gr.Row():
            calculate_btn = gr.Button(
                "GENERATE RESULT & PDF",
                elem_id="calculate-btn"
            )

            reset_btn = gr.Button(
                "RESET FORM",
                elem_id="reset-btn"
            )

    gr.HTML("""
    <div style="margin-top:30px;">
        <div class="section-eyebrow">
            02 / ACADEMIC SUMMARY
        </div>

        <div class="section-heading">
            Individual student result
        </div>

        <div class="section-description">
            Review the result, explore the chart and download
            the report card.
        </div>
    </div>
    """)

    profile_output = gr.HTML()

    with gr.Row():
        total_output = gr.HTML()
        percentage_output = gr.HTML()
        grade_output = gr.HTML()

    with gr.Group(elem_id="chart-panel"):
        chart_output = gr.Plot(
            label="Subject-wise performance"
        )

    pdf_output = gr.File(
        label="Download individual PDF report card",
        interactive=False
    )

    gr.HTML("""
    <div id="footer">
        <strong style="color:#202522;">
            STUDENT RESULT PORTAL
        </strong><br>

        Individual academic report generation system.<br>

        Demo grading policy: passing threshold 33;
        distinction at 85+.<br>

        Grace-pass rules are illustrative and must be confirmed
        against official institutional policy before real use.
    </div>
    """)

    # Inputs
    form_inputs = [
        name_input,
        roll_input,
        gender_input,
        grace_input,
        math_input,
        science_input,
        english_input,
        hindi_input,
        social_input,
        sanskrit_input
    ]

    # Outputs
    result_outputs = [
        profile_output,
        total_output,
        percentage_output,
        grade_output,
        chart_output,
        pdf_output
    ]

    calculate_btn.click(
        fn=calculate_result,
        inputs=form_inputs,
        outputs=result_outputs
    )

    reset_btn.click(
        fn=reset_form,
        inputs=[],
        outputs=form_inputs + result_outputs
    )


# ============================================================
# PUBLIC SHARE LINK
# ============================================================

# Gradio creates a temporary public URL.
# Keep this cell running while people use the link.
# For a permanent URL, deploy the app to a hosting platform.

app.launch()
