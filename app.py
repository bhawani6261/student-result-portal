
import os
import io
import html
import tempfile
from datetime import datetime

import gradio as gr
import plotly.graph_objects as go
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image as PDFImage, PageBreak,
)

# ============================================================
# SCHOOL BRANDING
# Replace the temporary emblem with the school's real logo later.
# ============================================================

SCHOOL_NAME = "NAHUSH PUBLIC HIGH SCHOOL"
SCHOOL_LOCATION = "MOHLA, KATNI (M.P.)"
TAGLINE = "Academic Excellence • Student Performance • Bright Future"

DEFAULT_ADDRESS = "Main Road, Mohla, Katni - 483501 (M.P.)"
DEFAULT_PHONE = "+91 12345 67890"
DEFAULT_EMAIL = "nahushpublicschool@gmail.com"

MAX_SUBJECTS = 10
PASS_PERCENTAGE = 33.0

NAVY = "#17365D"
DARK_NAVY = "#0B2455"
PALE_BLUE = "#EAF3FC"
PALEST_BLUE = "#F5F9FE"
GRID_BLUE = "#AFC6E0"
TEXT_COLOR = "#142D52"
MUTED = "#536984"

# Suggested presets: verify these against the school's curriculum.
CLASS_PRESETS = {
    **{
        f"Class {i}": [
            ("English", 100),
            ("Hindi", 100),
            ("Mathematics", 100),
            ("EVS" if i <= 5 else "Science", 100),
        ] + (
            [] if i <= 5 else [
                ("Social Science", 100),
                ("Sanskrit", 100),
            ]
        )
        for i in range(1, 11)
    },
    "Class 11 (Science)": [
        ("English", 100), ("Physics", 100),
        ("Chemistry", 100), ("Mathematics", 100),
        ("Biology", 100),
    ],
    "Class 11 (Commerce)": [
        ("English", 100), ("Accountancy", 100),
        ("Business Studies", 100), ("Economics", 100),
        ("Mathematics", 100),
    ],
    "Class 11 (Arts)": [
        ("English", 100), ("History", 100),
        ("Political Science", 100), ("Geography", 100),
        ("Economics", 100),
    ],
    "Class 12 (Science)": [
        ("English", 100), ("Physics", 100),
        ("Chemistry", 100), ("Mathematics", 100),
        ("Biology", 100),
    ],
    "Class 12 (Commerce)": [
        ("English", 100), ("Accountancy", 100),
        ("Business Studies", 100), ("Economics", 100),
        ("Mathematics", 100),
    ],
    "Class 12 (Arts)": [
        ("English", 100), ("History", 100),
        ("Political Science", 100), ("Geography", 100),
        ("Economics", 100),
    ],
}

CSS = f"""
.gradio-container {{
    max-width: 1280px !important;
    margin: auto !important;
    background: #F3F7FC !important;
    color: {TEXT_COLOR} !important;
}}

#hero {{
    border: 1px solid #C7D7EA;
    border-radius: 14px;
    padding: 24px;
    background: linear-gradient(135deg, #FFFFFF, #EAF3FC);
    margin-bottom: 16px;
}}

#hero h1 {{
    color: {DARK_NAVY};
    font-size: clamp(1.4rem, 3vw, 2.1rem);
    margin: 0;
    font-weight: 800;
}}

#hero p {{
    color: {MUTED};
    margin: 7px 0 0;
}}

.panel {{
    border: 1px solid #C7D7EA !important;
    border-radius: 13px !important;
    background: #FFFFFF !important;
}}

button.primary {{
    background: {NAVY} !important;
    border-color: {NAVY} !important;
}}

footer {{
    display: none !important;
}}
"""


def esc(value):
    """Escape user-entered content before inserting it into HTML/PDF."""
    return html.escape(str(value if value is not None else ""))


def grade_for(percentage):
    if percentage >= 90:
        return "A+"
    if percentage >= 80:
        return "A"
    if percentage >= 70:
        return "B+"
    if percentage >= 60:
        return "B"
    if percentage >= 50:
        return "C"
    if percentage >= 33:
        return "D"
    return "F"


# ============================================================
# DYNAMIC SUBJECT PRESETS
# ============================================================

def preset_updates(class_level):
    preset = CLASS_PRESETS.get(
        class_level, CLASS_PRESETS["Class 5"]
    )

    # Output order:
    # count, parent-row visibility, then 3 controls per subject.
    updates = [gr.update(value=len(preset))]

    updates.extend(
        gr.update(visible=(i < len(preset)))
        for i in range(MAX_SUBJECTS)
    )

    for i in range(MAX_SUBJECTS):
        if i < len(preset):
            subject, maximum = preset[i]
            updates.extend([
                gr.update(value=subject),
                gr.update(value=maximum),
                gr.update(value=0),
            ])
        else:
            updates.extend([
                gr.update(value=f"Subject {i + 1}"),
                gr.update(value=100),
                gr.update(value=0),
            ])

    return updates


def update_subject_rows(count):
    count = max(1, min(MAX_SUBJECTS, int(count or 1)))
    return [
        gr.update(visible=(i < count))
        for i in range(MAX_SUBJECTS)
    ]


# ============================================================
# PDF PAGE DESIGN
# ============================================================

def draw_watermark(canvas, doc):
    """Draw a pale watermark and border on every PDF page."""
    canvas.saveState()

    width, height = A4

    canvas.setStrokeColor(colors.HexColor("#B7CDE5"))
    canvas.setLineWidth(0.7)
    canvas.rect(
        7 * mm, 7 * mm,
        width - 14 * mm, height - 14 * mm,
        stroke=1, fill=0,
    )

    # Very subtle watermark behind the report content.
    canvas.setFillColor(colors.HexColor("#E2EDF9"))
    canvas.setFont("Helvetica-Bold", 24)
    canvas.translate(width / 2, height / 2)
    canvas.rotate(32)
    canvas.drawCentredString(
        0, 0, "NAHUSH PUBLIC HIGH SCHOOL"
    )

    canvas.restoreState()


def make_header(styles, address, phone, email):
    # Temporary school emblem. Replace with the actual logo when available.
    emblem = Table(
        [[Paragraph(
            '<font color="#17365D"><b>NPS</b></font>'
            '<br/><font size="7">MOHLA</font>',
            styles["Emblem"],
        )]],
        colWidths=[24 * mm],
        rowHeights=[24 * mm],
    )

    emblem.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1.2, colors.HexColor(NAVY)),
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))

    school_text = [
        Paragraph(esc(SCHOOL_NAME), styles["SchoolName"]),
        Paragraph(esc(SCHOOL_LOCATION), styles["SchoolLocation"]),
        Paragraph(esc(TAGLINE), styles["Tagline"]),
        Paragraph(
            f"{esc(address)} &nbsp; | &nbsp; "
            f"{esc(phone)} &nbsp; | &nbsp; {esc(email)}",
            styles["Contact"],
        ),
    ]

    header = Table(
        [[emblem, school_text]],
        colWidths=[28 * mm, 151 * mm],
    )

    header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, 0), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, -1), 1.1,
         colors.HexColor(NAVY)),
    ]))

    return header


def build_pdf(data):
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=11 * mm,
        bottomMargin=12 * mm,
    )

    base = getSampleStyleSheet()

    styles = {
        "SchoolName": ParagraphStyle(
            "SchoolName", parent=base["Title"],
            fontName="Helvetica-Bold", fontSize=15, leading=18,
            alignment=TA_CENTER, textColor=colors.HexColor(DARK_NAVY),
            spaceAfter=0,
        ),
        "SchoolLocation": ParagraphStyle(
            "SchoolLocation", parent=base["Normal"],
            fontName="Helvetica-Bold", fontSize=10, leading=12,
            alignment=TA_CENTER, textColor=colors.HexColor(DARK_NAVY),
        ),
        "Tagline": ParagraphStyle(
            "Tagline", parent=base["Normal"],
            fontSize=7.5, leading=10, alignment=TA_CENTER,
            textColor=colors.HexColor(MUTED),
        ),
        "Contact": ParagraphStyle(
            "Contact", parent=base["Normal"],
            fontSize=6.8, leading=9, alignment=TA_CENTER,
            textColor=colors.HexColor(TEXT_COLOR),
        ),
        "Emblem": ParagraphStyle(
            "Emblem", parent=base["Normal"],
            alignment=TA_CENTER, fontSize=15, leading=17,
        ),
        "Section": ParagraphStyle(
            "Section", parent=base["Heading2"],
            fontName="Helvetica-Bold", fontSize=10.5, leading=13,
            textColor=colors.HexColor(DARK_NAVY),
            spaceBefore=4, spaceAfter=5,
        ),
        "Small": ParagraphStyle(
            "Small", parent=base["Normal"],
            fontSize=7.3, leading=9, textColor=colors.HexColor(TEXT_COLOR),
        ),
        "Center": ParagraphStyle(
            "Center", parent=base["Normal"],
            fontSize=7.2, leading=9, alignment=TA_CENTER,
            textColor=colors.HexColor(TEXT_COLOR),
        ),
    }

    story = []
    address = data["school_address"] or DEFAULT_ADDRESS
    phone = data["school_contact"] or DEFAULT_PHONE
    email = data["school_email"] or DEFAULT_EMAIL

    # -------------------- PAGE 1 --------------------
    story.append(make_header(styles, address, phone, email))
    story.append(Spacer(1, 3 * mm))

    title_style = ParagraphStyle(
        "TitleBand", parent=base["Heading1"],
        fontName="Helvetica-Bold", fontSize=15, leading=18,
        alignment=TA_CENTER, textColor=colors.white,
    )

    title = Table(
        [[Paragraph("<b>STUDENT REPORT CARD</b>", title_style)]],
        colWidths=[179 * mm],
    )
    title.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(NAVY)),
        ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor(NAVY)),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))

    story.extend([title, Spacer(1, 2 * mm)])

    session_line = (
        f"Academic Session: <b>{esc(data['session'] or '—')}</b>"
        f" &nbsp; | &nbsp; Class: <b>{esc(data['class_level'])}</b>"
        f" &nbsp; | &nbsp; Section: <b>{esc(data['section'] or '—')}</b>"
    )

    story.extend([
        Paragraph(
            session_line,
            ParagraphStyle(
                "SessionLine", parent=base["Normal"],
                fontSize=8.5, leading=11, alignment=TA_CENTER,
                textColor=colors.HexColor(DARK_NAVY),
            ),
        ),
        Spacer(1, 2 * mm),
    ])

    info_rows = [
        [
            Paragraph("<b>Student Name</b>", styles["Small"]),
            ":",
            Paragraph(esc(data["student"]), styles["Small"]),
            Paragraph("<b>Roll Number</b>", styles["Small"]),
            ":",
            Paragraph(esc(data["roll"]), styles["Small"]),
        ],
        [
            Paragraph("<b>Father's Name</b>", styles["Small"]),
            ":",
            Paragraph(esc(data["father"] or "—"), styles["Small"]),
            Paragraph("<b>Date of Birth</b>", styles["Small"]),
            ":",
            Paragraph(esc(data["dob"] or "—"), styles["Small"]),
        ],
        [
            Paragraph("<b>Mother's Name</b>", styles["Small"]),
            ":",
            Paragraph(esc(data["mother"] or "—"), styles["Small"]),
            Paragraph("<b>Admission No.</b>", styles["Small"]),
            ":",
            Paragraph(esc(data["admission"] or "—"), styles["Small"]),
        ],
        [
            Paragraph("<b>Class & Section</b>", styles["Small"]),
            ":",
            Paragraph(
                esc(data["class_level"] + " - " + (data["section"] or "—")),
                styles["Small"],
            ),
            Paragraph("<b>Issue Date</b>", styles["Small"]),
            ":",
            Paragraph(datetime.now().strftime("%d %B %Y"), styles["Small"]),
        ],
    ]

    info_table = Table(
        info_rows,
        colWidths=[27 * mm, 4 * mm, 57 * mm, 27 * mm, 4 * mm, 60 * mm],
    )

    info_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor(PALE_BLUE)),
        ("BACKGROUND", (3, 0), (3, -1), colors.HexColor(PALE_BLUE)),
        ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor(GRID_BLUE)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))

    if data["photo"] and os.path.isfile(data["photo"]):
        try:
            photo = PDFImage(
                data["photo"], width=25 * mm, height=30 * mm
            )
            photo_table = Table(
                [[info_table, photo]],
                colWidths=[153 * mm, 26 * mm],
            )
            photo_table.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]))
            story.append(photo_table)
        except Exception:
            story.append(info_table)
    else:
        story.append(info_table)

    story.extend([
        Spacer(1, 3 * mm),
        Paragraph("SUBJECT-WISE PERFORMANCE", styles["Section"]),
    ])

    marks_rows = [[
        "Sr. No.", "Subject", "Maximum Marks",
        "Marks Obtained", "Percentage", "Grade", "Status",
    ]]

    for index, (subject, maximum, mark) in enumerate(data["subjects"], 1):
        subject_pct = mark / maximum * 100
        marks_rows.append([
            str(index), esc(subject), f"{maximum:g}", f"{mark:g}",
            f"{subject_pct:.1f}%", grade_for(subject_pct),
            "Pass" if subject_pct >= PASS_PERCENTAGE else "Fail",
        ])

    marks_rows.append([
        "", "TOTAL", f"{data['max_total']:g}", f"{data['total']:g}",
        f"{data['percentage']:.2f}%", data["grade"], "—",
    ])

    marks = Table(
        marks_rows,
        colWidths=[13 * mm, 42 * mm, 27 * mm, 29 * mm,
                   25 * mm, 18 * mm, 25 * mm],
        repeatRows=1,
    )

    marks.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(NAVY)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor(PALE_BLUE)),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor(GRID_BLUE)),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.1),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (2, 1), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))

    story.append(marks)
    story.extend([
        Spacer(1, 3 * mm),
        Paragraph("RESULT SUMMARY", styles["Section"]),
    ])

    summary = Table(
        [[
            Paragraph("<b>RESULT</b>", styles["Small"]),
            Paragraph(
                f"<b>{data['status']}</b>",
                ParagraphStyle(
                    "Result", parent=styles["Small"], fontSize=14, leading=16,
                    textColor=colors.HexColor(
                        NAVY if data["status"] == "PASS" else "#8B1E35"
                    ),
                ),
            ),
            Paragraph("<b>PERCENTAGE</b>", styles["Small"]),
            Paragraph(f"<b>{data['percentage']:.2f}%</b>", styles["Small"]),
            Paragraph("<b>GRADE</b>", styles["Small"]),
            Paragraph(f"<b>{data['grade']}</b>", styles["Small"]),
            Paragraph("<b>DISTINCTIONS</b>", styles["Small"]),
            Paragraph(f"<b>{len(data['distinctions'])}</b>", styles["Small"]),
        ]],
        colWidths=[
            18 * mm, 25 * mm, 25 * mm, 25 * mm,
            16 * mm, 18 * mm, 28 * mm, 24 * mm,
        ],
    )

    summary.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(PALE_BLUE)),
        ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor(NAVY)),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor(GRID_BLUE)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))

    story.extend([
        summary,
        Spacer(1, 2 * mm),
        Paragraph(
            f"<b>Remarks:</b> {esc(data['remarks'] or 'Keep working consistently and aim for progress in every subject.')}",
            styles["Small"],
        ),
        Spacer(1, 5 * mm),
    ])

    signature = Table(
        [
            ["____________________________", "____________________________"],
            ["Class Teacher", "Principal"],
        ],
        colWidths=[89.5 * mm, 89.5 * mm],
    )
    signature.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(signature)

    story.extend([
        Spacer(1, 3 * mm),
        Paragraph(
            "KNOWLEDGE  |  DISCIPLINE  |  CHARACTER  |  BRIGHT FUTURE",
            ParagraphStyle(
                "Footer1", parent=styles["Center"], fontSize=7.5,
                textColor=colors.HexColor(NAVY),
            ),
        ),
    ])

    # -------------------- PAGE 2 --------------------
    story.append(PageBreak())
    story.append(make_header(styles, address, phone, email))
    story.extend([
        Spacer(1, 4 * mm),
        Paragraph("GRADING SCALE", styles["Section"]),
    ])

    grading_rows = [
        ["Grade", "Percentage Range", "Performance Level", "Description"],
        ["A+", "90%–100%", "Outstanding", "Excellent performance"],
        ["A", "80%–89%", "Excellent", "Very good performance"],
        ["B+", "70%–79%", "Very Good", "Good performance"],
        ["B", "60%–69%", "Good", "Satisfactory performance"],
        ["C", "50%–59%", "Average", "Needs improvement"],
        ["D", "33%–49%", "Below Average", "Requires improvement"],
        ["F", "Below 33%", "Fail", "Below pass threshold"],
    ]

    grading = Table(
        grading_rows,
        colWidths=[20 * mm, 37 * mm, 45 * mm, 77 * mm],
        repeatRows=1,
    )
    grading.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(NAVY)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor(GRID_BLUE)),
        ("FONTSIZE", (0, 0), (-1, -1), 7.8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))

    story.extend([
        grading,
        Spacer(1, 4 * mm),
        Paragraph("SUBJECT DETAILS", styles["Section"]),
    ])

    detail_rows = [[
        "Subject", "Full Marks", "Pass Marks (33%)",
        "Marks Obtained", "Percentage", "Grade",
    ]]

    for subject, maximum, mark in data["subjects"]:
        subject_pct = mark / maximum * 100
        detail_rows.append([
            esc(subject), f"{maximum:g}",
            f"{maximum * PASS_PERCENTAGE / 100:g}",
            f"{mark:g}", f"{subject_pct:.1f}%", grade_for(subject_pct),
        ])

    detail_rows.append([
        "TOTAL", f"{data['max_total']:g}", "—",
        f"{data['total']:g}", f"{data['percentage']:.2f}%",
        data["grade"],
    ])

    detail = Table(
        detail_rows,
        colWidths=[44 * mm, 25 * mm, 30 * mm,
                   30 * mm, 27 * mm, 23 * mm],
        repeatRows=1,
    )

    detail.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(NAVY)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor(PALE_BLUE)),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor(GRID_BLUE)),
        ("FONTSIZE", (0, 0), (-1, -1), 7.6),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))

    story.extend([
        detail,
        Spacer(1, 4 * mm),
        Paragraph("IMPORTANT NOTES", styles["Section"]),
    ])

    notes = [
        "Pass mark is configured as 33% in each subject; confirm school policy.",
        "This is a computer-generated report card. Signature requirements depend on school policy.",
        "In case of discrepancy, please contact the school office.",
        "Grading and promotion must follow the school's and relevant education board's approved rules.",
        "This report card is intended for academic use only.",
    ]

    notes_table = Table(
        [
            [f"{i + 1}.", Paragraph(esc(note), styles["Small"])]
            for i, note in enumerate(notes)
        ],
        colWidths=[8 * mm, 171 * mm],
    )
    notes_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(PALEST_BLUE)),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor(GRID_BLUE)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))

    story.extend([
        notes_table,
        Spacer(1, 10 * mm),
        signature,
        Spacer(1, 5 * mm),
        Paragraph(
            f"{esc(SCHOOL_NAME)} • {esc(SCHOOL_LOCATION)}",
            ParagraphStyle(
                "SealText", parent=styles["Center"], fontSize=9,
                textColor=colors.HexColor(NAVY),
            ),
        ),
        Spacer(1, 4 * mm),
        Paragraph(
            "KNOWLEDGE  |  DISCIPLINE  |  CHARACTER  |  BRIGHT FUTURE",
            ParagraphStyle(
                "Footer2", parent=styles["Center"], fontSize=7.5,
                textColor=colors.HexColor(NAVY),
            ),
        ),
    ])

    doc.build(
        story,
        onFirstPage=draw_watermark,
        onLaterPages=draw_watermark,
    )

    buffer.seek(0)
    return buffer.getvalue()


# ============================================================
# RESULT CALCULATION
# ============================================================

def calculate(
    student, roll, gender, dob, father, mother, admission,
    class_level, section, session, school_address,
    school_contact, school_email, photo, count, remarks, *values
):
    student = (student or "").strip()
    roll = (roll or "").strip()

    if not student:
        raise gr.Error("Please enter the student name.")
    if not roll:
        raise gr.Error("Please enter the roll number.")

    try:
        count = int(count)
    except (TypeError, ValueError):
        raise gr.Error("Choose a valid subject count.")

    if not 1 <= count <= MAX_SUBJECTS:
        raise gr.Error("Subject count must be between 1 and 10.")

    subjects = []

    for i in range(count):
        name = str(values[i * 3] or "").strip()

        try:
            maximum = float(values[i * 3 + 1])
            mark = float(values[i * 3 + 2] or 0)
        except (TypeError, ValueError):
            raise gr.Error(f"Enter valid marks for subject {i + 1}.")

        if not name:
            raise gr.Error(f"Enter a name for subject {i + 1}.")
        if maximum <= 0:
            raise gr.Error(f"Maximum marks for {name} must be above zero.")
        if mark < 0 or mark > maximum:
            raise gr.Error(
                f"Marks for {name} must be between 0 and {maximum:g}."
            )

        subjects.append((name, maximum, mark))

    max_total = sum(row[1] for row in subjects)
    total = sum(row[2] for row in subjects)
    percentage = total / max_total * 100 if max_total else 0

    failed = [
        name for name, maximum, mark in subjects
        if mark / maximum * 100 < PASS_PERCENTAGE
    ]

    status = "PASS" if not failed else "FAIL"
    grade = grade_for(percentage) if status == "PASS" else "F"

    distinctions = [
        name for name, maximum, mark in subjects
        if mark / maximum * 100 >= 85
    ]

    # Chart
    labels = [row[0] for row in subjects]
    percentages = [row[2] / row[1] * 100 for row in subjects]

    fig = go.Figure(
        go.Bar(
            x=labels,
            y=percentages,
            text=[f"{value:.1f}%" for value in percentages],
            textposition="outside",
            marker_color=[
                NAVY if value >= 85 else "#7FA1C8"
                for value in percentages
            ],
            cliponaxis=False,
            hovertemplate="%{x}: %{y:.1f}%<extra></extra>",
        )
    )

    fig.update_layout(
        title="Subject Performance Overview",
        yaxis=dict(
            title="Marks (% of maximum)",
            range=[0, 112],
            dtick=20,
        ),
        template="plotly_white",
        height=390,
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(color=TEXT_COLOR),
        margin=dict(l=30, r=20, t=60, b=85),
    )

    # Explicit text colors prevent invisible text in the result box.
    status_color = NAVY if status == "PASS" else "#8B1E35"
    status_bg = "#EAF3FC" if status == "PASS" else "#FBEFF1"

    result_html = f"""
    <div style="
        box-sizing:border-box;
        width:100%;
        overflow-wrap:anywhere;
        border:2px solid {status_color};
        border-left:8px solid {status_color};
        padding:20px;
        background:{status_bg};
        border-radius:12px;
        color:#142D52 !important;
        font-family:Arial,sans-serif;
        line-height:1.75;">
      <div style="
          display:inline-block;
          background:{status_color};
          color:#FFFFFF !important;
          padding:9px 26px;
          border-radius:5px;
          font-size:23px;
          font-weight:800;
          margin-bottom:12px;">
          {status}
      </div>
      <h3 style="margin:4px 0 10px;color:#142D52 !important;">
        {esc(student)}
        <span style="font-size:14px;font-weight:500;color:#142D52 !important;">
          | Roll No: {esc(roll)}
        </span>
      </h3>
      <p style="margin:5px 0;color:#142D52 !important;">
        <b>Class:</b> {esc(class_level)}
        &nbsp; <b>Section:</b> {esc(section or '—')}
      </p>
      <p style="font-size:17px;margin:7px 0;color:#142D52 !important;">
        <b>Total:</b> {total:g}/{max_total:g}
        &nbsp; <b>Percentage:</b> {percentage:.2f}%
      </p>
      <p style="margin:5px 0;color:#142D52 !important;">
        <b>Grade:</b> {grade}
        &nbsp; <b>Distinctions:</b>
        {', '.join(esc(x) for x in distinctions) if distinctions else 'None'}
      </p>
    </div>
    """

    data = {
        "student": student,
        "roll": roll,
        "gender": gender,
        "dob": dob,
        "father": father,
        "mother": mother,
        "admission": admission,
        "class_level": class_level,
        "section": section,
        "session": session,
        "school_address": school_address,
        "school_contact": school_contact,
        "school_email": school_email,
        "photo": photo,
        "subjects": subjects,
        "total": total,
        "max_total": max_total,
        "percentage": percentage,
        "grade": grade,
        "status": status,
        "distinctions": distinctions,
        "remarks": remarks,
    }

    pdf_bytes = build_pdf(data)

    safe_roll = "".join(
        char if char.isalnum() or char in "-_" else "_"
        for char in roll
    ) or "student"

    filename = (
        f"marksheet_{safe_roll}_"
        f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.pdf"
    )
    pdf_path = os.path.join(tempfile.gettempdir(), filename)

    with open(pdf_path, "wb") as file:
        file.write(pdf_bytes)

    return result_html, fig, pdf_path


# ============================================================
# GRADIO INTERFACE
# ============================================================

with gr.Blocks(
    title="Nahush Public High School | Student Result Portal"
) as app:

    gr.HTML(
        f'<div id="hero">'
        f'<h1>{esc(SCHOOL_NAME)} — {esc(SCHOOL_LOCATION)}</h1>'
        f'<p>{esc(TAGLINE)}</p>'
        f'</div>'
    )

    gr.Markdown(
        "Create a student result summary and a two-page PDF report card. "
        "Review all information before generating."
    )

    with gr.Row():
        with gr.Column(scale=1):

            with gr.Group(elem_classes=["panel"]):
                gr.Markdown("### Student Information")

                student = gr.Textbox(label="Student Name")
                roll = gr.Textbox(label="Roll Number")

                gender = gr.Dropdown(
                    ["Female", "Male", "Other", "Prefer not to say"],
                    label="Gender",
                    value="Prefer not to say",
                )

                dob = gr.Textbox(
                    label="Date of Birth",
                    placeholder="e.g. 22 July 2007",
                )

                father = gr.Textbox(label="Father's Name")
                mother = gr.Textbox(label="Mother's Name")
                admission = gr.Textbox(
                    label="Admission Number (optional)"
                )

                class_level = gr.Dropdown(
                    list(CLASS_PRESETS.keys()),
                    label="Class / Stream",
                    value="Class 5",
                )

                with gr.Row():
                    section = gr.Textbox(
                        label="Section", placeholder="A"
                    )
                    session = gr.Textbox(
                        label="Academic Session",
                        placeholder="2026–27",
                    )

                photo = gr.Image(
                    label="Student Photo (optional)",
                    type="filepath",
                    height=170,
                )

            with gr.Group(elem_classes=["panel"]):
                gr.Markdown("### School Details")

                school_address = gr.Textbox(
                    label="School Address", value=DEFAULT_ADDRESS
                )
                school_contact = gr.Textbox(
                    label="School Phone", value=DEFAULT_PHONE
                )
                school_email = gr.Textbox(
                    label="School Email", value=DEFAULT_EMAIL
                )

            with gr.Group(elem_classes=["panel"]):
                gr.Markdown("### Subject Marks")

                count = gr.Slider(
                    1, MAX_SUBJECTS,
                    step=1,
                    value=len(CLASS_PRESETS["Class 5"]),
                    label="Number of subjects",
                )

                gr.Markdown(
                    "Class presets can be edited. The current pass mark "
                    "is 33% per subject; verify the school's official rules."
                )

                subject_controls = []
                subject_rows = []
                initial = CLASS_PRESETS["Class 5"]

                for i in range(MAX_SUBJECTS):
                    row = gr.Row(visible=(i < len(initial)))
                    subject_rows.append(row)

                    with row:
                        subject_name = gr.Textbox(
                            label=f"Subject {i + 1}",
                            value=(
                                initial[i][0]
                                if i < len(initial)
                                else f"Subject {i + 1}"
                            ),
                            scale=3,
                        )

                        maximum = gr.Number(
                            label="Maximum",
                            value=initial[i][1] if i < len(initial) else 100,
                            minimum=1,
                            precision=0,
                            scale=1,
                        )

                        obtained = gr.Number(
                            label="Obtained",
                            value=0,
                            minimum=0,
                            precision=1,
                            scale=1,
                        )

                    subject_controls.extend([
                        subject_name, maximum, obtained
                    ])

                remarks = gr.Textbox(
                    label="Teacher Remarks (optional)",
                    placeholder="A short, constructive remark",
                    lines=2,
                )

                submit = gr.Button(
                    "Generate Result & PDF Marksheet",
                    variant="primary",
                )

        with gr.Column(scale=1):
            result = gr.HTML(label="Result Summary")
            chart = gr.Plot(label="Performance Chart")
            pdf = gr.File(label="Download PDF Report Card")

    # Class changes update the count, parent rows and field values.
    class_outputs = [count, *subject_rows, *subject_controls]

    class_level.change(
        fn=preset_updates,
        inputs=[class_level],
        outputs=class_outputs,
    )

    # Manual count changes show/hide the parent subject rows.
    count.change(
        fn=update_subject_rows,
        inputs=[count],
        outputs=subject_rows,
    )

    submit.click(
        fn=calculate,
        inputs=[
            student, roll, gender, dob, father, mother, admission,
            class_level, section, session, school_address,
            school_contact, school_email, photo, count, remarks,
            *subject_controls,
        ],
        outputs=[result, chart, pdf],
    )

    gr.Markdown(
        "*Demo template: verify the official school logo, school codes, "
        "subjects, maximum marks, grading rules, pass criteria and "
        "signature requirements before official use.*"
    )


# ============================================================
# RENDER DEPLOYMENT
# ============================================================

if __name__ == "__main__":
    app.launch(
        server_name="0.0.0.0",
        server_port=int(os.environ.get("PORT", "10000")),
        css=CSS,
    )
    
