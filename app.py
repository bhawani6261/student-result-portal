
import io
import os
import tempfile
import html
from datetime import datetime

import gradio as gr
import plotly.graph_objects as go
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image as PDFImage,
)

# ============================================================
# SCHOOL SETTINGS
# ============================================================

INSTITUTION_NAME = "NAHUSH PUBLIC HIGH SCHOOL MOHLA"
INSTITUTION_TAGLINE = "Academic Excellence • Student Performance"

MAX_SUBJECTS = 10
PASS_PERCENTAGE = 33

NAVY = "#17365D"
LIGHT_BLUE = "#EAF1F8"
MUTED_BLUE = "#61718A"
PASS_COLOR = "#17365D"
FAIL_COLOR = "#7A263A"

# Suggested templates only.
# Confirm subjects and maximum marks with the school's curriculum.
CLASS_PRESETS = {
    "Class 1": [
        ("English", 100), ("Hindi", 100),
        ("Mathematics", 100), ("EVS", 100),
    ],
    "Class 2": [
        ("English", 100), ("Hindi", 100),
        ("Mathematics", 100), ("EVS", 100),
    ],
    "Class 3": [
        ("English", 100), ("Hindi", 100),
        ("Mathematics", 100), ("EVS", 100),
    ],
    "Class 4": [
        ("English", 100), ("Hindi", 100),
        ("Mathematics", 100), ("EVS", 100),
    ],
    "Class 5": [
        ("English", 100), ("Hindi", 100),
        ("Mathematics", 100), ("EVS", 100),
    ],
    "Class 6": [
        ("English", 100), ("Hindi", 100),
        ("Mathematics", 100), ("Science", 100),
        ("Social Science", 100), ("Sanskrit", 100),
    ],
    "Class 7": [
        ("English", 100), ("Hindi", 100),
        ("Mathematics", 100), ("Science", 100),
        ("Social Science", 100), ("Sanskrit", 100),
    ],
    "Class 8": [
        ("English", 100), ("Hindi", 100),
        ("Mathematics", 100), ("Science", 100),
        ("Social Science", 100), ("Sanskrit", 100),
    ],
    "Class 9": [
        ("English", 100), ("Hindi", 100),
        ("Mathematics", 100), ("Science", 100),
        ("Social Science", 100), ("Sanskrit", 100),
    ],
    "Class 10": [
        ("English", 100), ("Hindi", 100),
        ("Mathematics", 100), ("Science", 100),
        ("Social Science", 100), ("Sanskrit", 100),
    ],
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


# ============================================================
# WEB APP STYLING
# ============================================================

CSS = """
:root {
    --paper: #F4F7FB;
    --ink: #172B4D;
    --navy: #17365D;
    --muted: #61718A;
    --line: #D6E0EC;
}

.gradio-container {
    background: var(--paper) !important;
    color: var(--ink) !important;
    max-width: 1240px !important;
    margin: auto !important;
}

#hero {
    padding: 26px 30px;
    border: 1px solid var(--line);
    border-radius: 14px;
    background: linear-gradient(135deg, #FFFFFF, #EAF1FA);
    margin-bottom: 18px;
}

#hero h1 {
    color: var(--navy);
    margin: 0;
    font-size: 1.9rem;
    letter-spacing: -.025em;
}

#hero p {
    color: var(--muted);
    margin: 8px 0 0;
    letter-spacing: .06em;
    font-size: .8rem;
}

.panel {
    border: 1px solid var(--line) !important;
    border-radius: 14px !important;
    background: #FFFFFF !important;
}

button.primary {
    background: var(--navy) !important;
    border-color: var(--navy) !important;
}

footer {
    display: none !important;
}
"""


# ============================================================
# GRADING
# ============================================================

def grade_for(pct):
    if pct >= 90:
        return "A+"
    if pct >= 80:
        return "A"
    if pct >= 70:
        return "B+"
    if pct >= 60:
        return "B"
    if pct >= 50:
        return "C"
    if pct >= 33:
        return "D"
    return "F"


# ============================================================
# DYNAMIC SUBJECT ROWS
# ============================================================

def preset_updates(class_level):
    """Update the count, parent row visibility, and preset fields."""
    preset = CLASS_PRESETS.get(
        class_level,
        CLASS_PRESETS["Class 5"],
    )

    # Output order:
    # 1. Active subject count
    # 2. Parent row visibility for all subjects
    # 3. Subject name, maximum marks, obtained marks for each row
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
    """Show only the number of subject rows selected by the user."""
    count = max(1, min(MAX_SUBJECTS, int(count or 1)))

    return [
        gr.update(visible=(i < count))
        for i in range(MAX_SUBJECTS)
    ]


# ============================================================
# PDF WATERMARK
# ============================================================

def draw_watermark(canvas, doc):
    """Draw a subtle school watermark and border on every PDF page."""
    canvas.saveState()

    page_width, page_height = A4

    # Thin page border
    canvas.setStrokeColor(colors.HexColor("#D9E5F2"))
    canvas.setLineWidth(0.6)
    canvas.roundRect(
        8 * mm,
        8 * mm,
        page_width - 16 * mm,
        page_height - 16 * mm,
        3 * mm,
        stroke=1,
        fill=0,
    )

    # Pale blue diagonal watermark
    canvas.translate(page_width / 2, page_height / 2)
    canvas.rotate(32)
    canvas.setFillColor(colors.HexColor("#EAF1F8"))
    canvas.setFont("Helvetica-Bold", 23)
    canvas.drawCentredString(0, 0, INSTITUTION_NAME)

    canvas.setFont("Helvetica", 10)
    canvas.drawCentredString(
        0,
        -9 * mm,
        "ACADEMIC EXCELLENCE • STUDENT PERFORMANCE",
    )

    canvas.restoreState()


# ============================================================
# PDF MARKSHEET
# ============================================================

def create_pdf(
    student,
    roll,
    gender,
    dob,
    parent_name,
    class_level,
    section,
    session,
    school_address,
    school_contact,
    student_photo,
    subject_rows,
    total,
    max_total,
    pct,
    grade,
    status,
    distinctions,
    grace_note,
):
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
    )

    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="Institution",
            parent=styles["Title"],
            alignment=TA_CENTER,
            textColor=colors.HexColor(NAVY),
            fontSize=17,
            leading=21,
            spaceAfter=3,
        )
    )

    styles.add(
        ParagraphStyle(
            name="Tagline",
            parent=styles["Normal"],
            alignment=TA_CENTER,
            textColor=colors.HexColor(MUTED_BLUE),
            fontSize=8,
            leading=11,
            spaceAfter=7,
        )
    )

    styles.add(
        ParagraphStyle(
            name="Small",
            parent=styles["Normal"],
            fontSize=8,
            leading=10,
        )
    )

    story = [
        Paragraph(
            html.escape(INSTITUTION_NAME),
            styles["Institution"],
        ),
        Paragraph(
            html.escape(INSTITUTION_TAGLINE),
            styles["Tagline"],
        ),
    ]

    address_line = " | ".join(
        value.strip()
        for value in [school_address or "", school_contact or ""]
        if value.strip()
    )

    if address_line:
        story.append(
            Paragraph(
                html.escape(address_line),
                styles["Small"],
            )
        )

    story.extend([
        Spacer(1, 3 * mm),
        Paragraph("STUDENT REPORT CARD", styles["Heading1"]),
        Spacer(1, 2 * mm),
    ])

    # Optional student photograph
    if student_photo and os.path.isfile(student_photo):
        try:
            photo = PDFImage(
                student_photo,
                width=25 * mm,
                height=29 * mm,
            )
            photo.hAlign = "RIGHT"
            story.extend([photo, Spacer(1, 2 * mm)])
        except Exception:
            # A bad or unsupported photo should not block the marksheet.
            pass

    student_info = [
        [
            "Student Name",
            html.escape(student),
            "Roll Number",
            html.escape(roll),
        ],
        [
            "Father / Mother",
            html.escape(parent_name or "—"),
            "Date of Birth",
            html.escape(dob or "—"),
        ],
        [
            "Class",
            html.escape(class_level),
            "Section",
            html.escape(section or "—"),
        ],
        [
            "Academic Session",
            html.escape(session or "—"),
            "Gender",
            html.escape(gender or "—"),
        ],
        [
            "Issue Date",
            datetime.now().strftime("%d %b %Y"),
            "",
            "",
        ],
    ]

    info_table = Table(
        student_info,
        colWidths=[30 * mm, 53 * mm, 30 * mm, 53 * mm],
    )

    info_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor(LIGHT_BLUE)),
        ("BACKGROUND", (2, 0), (2, -1), colors.HexColor(LIGHT_BLUE)),
        ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#D2DCE8")),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))

    story.extend([
        info_table,
        Spacer(1, 5 * mm),
        Paragraph("Subject-wise Performance", styles["Heading2"]),
    ])

    marks_rows = [[
        "Subject",
        "Maximum Marks",
        "Marks Obtained",
        "Percentage",
        "Status",
    ]]

    for subject, maximum, mark in subject_rows:
        subject_pct = mark / maximum * 100

        marks_rows.append([
            html.escape(subject),
            f"{maximum:g}",
            f"{mark:g}",
            f"{subject_pct:.1f}%",
            "Pass" if subject_pct >= PASS_PERCENTAGE else "Needs Improvement",
        ])

    marks_rows.append([
        "TOTAL",
        f"{max_total:g}",
        f"{total:g}",
        f"{pct:.2f}%",
        "",
    ])

    marks_table = Table(
        marks_rows,
        colWidths=[48 * mm, 28 * mm, 28 * mm, 25 * mm, 37 * mm],
        repeatRows=1,
    )

    marks_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(NAVY)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor(LIGHT_BLUE)),
        ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#D2DCE8")),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TEXTCOLOR", (1, 1), (-1, -2), colors.HexColor("#172B4D")),
    ]))

    story.extend([
        marks_table,
        Spacer(1, 5 * mm),
        Paragraph("Final Summary", styles["Heading2"]),
    ])

    summary = Table(
        [
            ["Total Marks", f"{total:g} / {max_total:g}"],
            ["Percentage", f"{pct:.2f}%"],
            ["Grade", grade],
            ["Overall Result", status],
            [
                "Distinction Subjects (85%+)",
                ", ".join(distinctions) if distinctions else "None",
            ],
        ],
        colWidths=[55 * mm, 111 * mm],
    )

    summary.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor(LIGHT_BLUE)),
        (
            "TEXTCOLOR",
            (1, 3),
            (1, 3),
            colors.HexColor(PASS_COLOR if status == "PASS" else FAIL_COLOR),
        ),
        ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#D2DCE8")),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))

    story.extend([summary, Spacer(1, 3 * mm)])

    if grace_note:
        story.append(
            Paragraph(html.escape(grace_note), styles["Small"])
        )

    story.extend([
        Spacer(1, 13 * mm),
        Table(
            [
                ["____________________________", "____________________________"],
                ["Class Teacher Signature", "Principal Signature"],
            ],
            colWidths=[83 * mm, 83 * mm],
            style=TableStyle([
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
            ]),
        ),
        Spacer(1, 5 * mm),
        Paragraph(
            "For official use, verify the school's approved subjects, "
            "grading and grace-mark policy.",
            styles["Italic"],
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
# CALCULATE RESULT, CHART, AND PDF
# ============================================================

def calculate(
    student,
    roll,
    gender,
    dob,
    parent_name,
    class_level,
    section,
    session,
    school_address,
    school_contact,
    student_photo,
    active_count,
    grace_enabled,
    grace_allowance,
    *values,
):
    student = (student or "").strip()
    roll = (roll or "").strip()

    if not student:
        raise gr.Error("Please enter the student's name.")

    if not roll:
        raise gr.Error("Please enter the roll number.")

    try:
        allowance = float(grace_allowance or 0)
    except (TypeError, ValueError):
        raise gr.Error("Please enter a valid grace allowance.")

    if allowance < 0 or allowance > PASS_PERCENTAGE:
        raise gr.Error(
            "Grace allowance must be between 0 and 33 percentage points."
        )

    try:
        count = int(active_count)
    except (TypeError, ValueError):
        raise gr.Error("Please select a valid number of subjects.")

    if count < 1 or count > MAX_SUBJECTS:
        raise gr.Error("The number of subjects must be between 1 and 10.")

    subject_rows = []

    for i in range(count):
        subject = str(values[i * 3] or "").strip()
        maximum_value = values[i * 3 + 1]
        mark_value = values[i * 3 + 2]

        if not subject:
            raise gr.Error(f"Please enter a name for subject {i + 1}.")

        try:
            maximum = float(maximum_value)
            mark = float(mark_value or 0)
        except (TypeError, ValueError):
            raise gr.Error(f"Enter valid marks for {subject}.")

        if maximum <= 0:
            raise gr.Error(
                f"Maximum marks for {subject} must be greater than zero."
            )

        if mark < 0 or mark > maximum:
            raise gr.Error(
                f"Marks for {subject} must be between 0 and {maximum:g}."
            )

        subject_rows.append((subject, maximum, mark))

    max_total = sum(row[1] for row in subject_rows)
    total = sum(row[2] for row in subject_rows)
    pct = total / max_total * 100 if max_total else 0

    # A subject fails if its percentage is below the configured pass mark.
    fails = [
        i
        for i, (_, maximum, mark) in enumerate(subject_rows)
        if (mark / maximum * 100) < PASS_PERCENTAGE
    ]

    # Grace is applied only when enabled, the allowance is positive,
    # and exactly one subject is within the allowed percentage-point range.
    grace_used = False

    if grace_enabled and allowance > 0 and len(fails) == 1:
        failed_index = fails[0]
        _, failed_maximum, failed_mark = subject_rows[failed_index]
        failed_pct = failed_mark / failed_maximum * 100

        grace_used = (
            PASS_PERCENTAGE - allowance
            <= failed_pct
            < PASS_PERCENTAGE
        )

    passed = len(fails) == 0 or grace_used
    status = "PASS" if passed else "FAIL"
    grade = grade_for(pct) if passed else "F"

    distinctions = [
        subject
        for subject, maximum, mark in subject_rows
        if mark / maximum * 100 >= 85
    ]

    grace_note = (
        "Grace pass applied using the configured demo allowance. "
        "Confirm this matches school policy."
        if grace_used
        else ""
    )

    # Subject performance chart
    subjects = [row[0] for row in subject_rows]
    percentages = [
        row[2] / row[1] * 100
        for row in subject_rows
    ]

    fig = go.Figure(
        go.Bar(
            x=subjects,
            y=percentages,
            text=[f"{value:.1f}%" for value in percentages],
            textposition="outside",
            marker_color=[
                "#17365D" if value >= 85 else "#7B9BC2"
                for value in percentages
            ],
            hovertemplate="%{x}: %{y:.1f}%<extra></extra>",
        )
    )

    fig.update_layout(
        title="Subject Performance Overview",
        yaxis=dict(
            title="Marks (% of maximum)",
            range=[0, 110],
            dtick=20,
        ),
        template="plotly_white",
        height=390,
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(color="#172B4D"),
        margin=dict(l=20, r=20, t=55, b=75),
    )

    # Escape user-entered text before inserting it into HTML.
    safe_student = html.escape(student)
    safe_roll = html.escape(roll)
    safe_class = html.escape(class_level or "")
    safe_section = html.escape(section or "—")
    distinction_text = (
        ", ".join(html.escape(item) for item in distinctions)
        if distinctions
        else "None"
    )

    status_color = PASS_COLOR if passed else FAIL_COLOR
    status_bg = "#EAF1F8" if passed else "#F9ECEF"

    grace_html = (
        f"<p><b>{html.escape(grace_note)}</b></p>"
        if grace_note
        else ""
    )

    result_html = (
        f'<div style="border:2px solid {status_color};'
        f'border-left:8px solid {status_color};'
        f'padding:20px;background:{status_bg};border-radius:12px;'
        f'color:#172B4D">'
        f'<div style="display:inline-block;background:{status_color};'
        f'color:#fff;padding:10px 28px;border-radius:5px;'
        f'font-size:24px;font-weight:800;letter-spacing:1px;'
        f'margin-bottom:12px">{status}</div>'
        f'<h3 style="margin:3px 0 10px;color:#172B4D">'
        f'{safe_student} '
        f'<span style="font-size:14px;font-weight:500">'
        f'| Roll No: {safe_roll}</span></h3>'
        f'<p><b>Class:</b> {safe_class} &nbsp; '
        f'<b>Section:</b> {safe_section}</p>'
        f'<p style="font-size:18px"><b>Total:</b> '
        f'{total:g}/{max_total:g} &nbsp; '
        f'<b>Percentage:</b> {pct:.2f}%</p>'
        f'<p><b>Grade:</b> {grade} &nbsp; '
        f'<b>Distinctions:</b> {distinction_text}</p>'
        f'{grace_html}</div>'
    )

    # Create the PDF file.
    pdf_bytes = create_pdf(
        student,
        roll,
        gender,
        dob,
        parent_name,
        class_level,
        section,
        session,
        school_address,
        school_contact,
        student_photo,
        subject_rows,
        total,
        max_total,
        pct,
        grade,
        status,
        distinctions,
        grace_note,
    )

    safe_filename_roll = "".join(
        char if char.isalnum() or char in "-_" else "_"
        for char in roll
    ) or "student"

    # Unique filename helps prevent collisions between repeated submissions.
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    pdf_path = os.path.join(
        tempfile.gettempdir(),
        f"marksheet_{safe_filename_roll}_{timestamp}.pdf",
    )

    with open(pdf_path, "wb") as file:
        file.write(pdf_bytes)

    return result_html, fig, pdf_path


# ============================================================
# GRADIO INTERFACE
# ============================================================

with gr.Blocks(
    title="Nahush Public High School Mohla - Student Result Portal"
) as app:

    gr.HTML(
        f'<div id="hero">'
        f'<h1>{html.escape(INSTITUTION_NAME)}</h1>'
        f'<p>{html.escape(INSTITUTION_TAGLINE)}</p>'
        f'</div>'
    )

    gr.Markdown(
        "Generate a student result summary, subject performance chart "
        "and downloadable PDF report card."
    )

    with gr.Row():

        # ----------------------------------------------------
        # LEFT COLUMN: STUDENT INFORMATION AND SUBJECT MARKS
        # ----------------------------------------------------
        with gr.Column(scale=1):

            with gr.Group(elem_classes=["panel"]):
                gr.Markdown("### Student & School Information")

                student = gr.Textbox(
                    label="Student Name",
                    placeholder="Enter student's full name",
                )

                roll = gr.Textbox(
                    label="Roll Number",
                    placeholder="Enter roll number",
                )

                gender = gr.Dropdown(
                    [
                        "Female",
                        "Male",
                        "Other",
                        "Prefer not to say",
                    ],
                    label="Gender",
                    value="Prefer not to say",
                )

                dob = gr.Textbox(
                    label="Date of Birth",
                    placeholder="e.g. 23/03/2012",
                )

                parent_name = gr.Textbox(
                    label="Father / Mother Name",
                    placeholder="Enter parent/guardian name",
                )

                class_level = gr.Dropdown(
                    list(CLASS_PRESETS.keys()),
                    label="Class / Stream",
                    value="Class 5",
                )

                with gr.Row():
                    section = gr.Textbox(
                        label="Class / Section",
                        placeholder="e.g. A",
                    )

                    session = gr.Textbox(
                        label="Academic Session",
                        placeholder="e.g. 2026-27",
                    )

                school_address = gr.Textbox(
                    label="School Address",
                    placeholder="Enter school address",
                )

                school_contact = gr.Textbox(
                    label="School Contact",
                    placeholder="Phone / email",
                )

                student_photo = gr.Image(
                    label="Student Photo (optional)",
                    type="filepath",
                    height=180,
                )

            with gr.Group(elem_classes=["panel"]):
                gr.Markdown("### Subject Marks")

                gr.Markdown(
                    "Choose a class preset, then review or edit the "
                    "subject names and marks before generating the result."
                )

                active_count = gr.Slider(
                    minimum=1,
                    maximum=MAX_SUBJECTS,
                    step=1,
                    value=len(CLASS_PRESETS["Class 5"]),
                    label="Number of subjects",
                )

                grace_enabled = gr.Checkbox(
                    label="Enable grace marks option",
                    value=False,
                )

                grace_allowance = gr.Number(
                    label=(
                        "Grace allowance (percentage points; "
                        "set according to school policy)"
                    ),
                    value=0,
                    minimum=0,
                    maximum=33,
                    precision=1,
                )

                gr.Markdown(
                    "Pass mark is currently set to 33% per subject. "
                    "Confirm this against the school's approved rules."
                )

                subject_controls = []
                subject_row_components = []
                default_subjects = CLASS_PRESETS["Class 5"]

                for i in range(MAX_SUBJECTS):
                    subject_row = gr.Row(
                        visible=(i < len(default_subjects))
                    )
                    subject_row_components.append(subject_row)

                    with subject_row:
                        subject_box = gr.Textbox(
                            label=f"Subject {i + 1}",
                            value=(
                                default_subjects[i][0]
                                if i < len(default_subjects)
                                else f"Subject {i + 1}"
                            ),
                            scale=3,
                        )

                        max_box = gr.Number(
                            label="Maximum",
                            value=(
                                default_subjects[i][1]
                                if i < len(default_subjects)
                                else 100
                            ),
                            minimum=1,
                            precision=0,
                            scale=1,
                        )

                        mark_box = gr.Number(
                            label="Obtained",
                            value=0,
                            minimum=0,
                            precision=1,
                            scale=1,
                        )

                    subject_controls.extend([
                        subject_box,
                        max_box,
                        mark_box,
                    ])

                submit = gr.Button(
                    "Generate Result & PDF Marksheet",
                    variant="primary",
                )

        # ----------------------------------------------------
        # RIGHT COLUMN: RESULT, CHART, PDF
        # ----------------------------------------------------
        with gr.Column(scale=1):
            result = gr.HTML(label="Result Summary")
            chart = gr.Plot(label="Performance Chart")
            pdf = gr.File(label="Download PDF Report Card")

    # --------------------------------------------------------
    # CLASS PRESET EVENT
    # Outputs: count + parent rows + all subject input fields
    # --------------------------------------------------------
    class_outputs = [
        active_count,
        *subject_row_components,
        *subject_controls,
    ]

    class_level.change(
        fn=preset_updates,
        inputs=[class_level],
        outputs=class_outputs,
    )

    # --------------------------------------------------------
    # MANUAL SUBJECT COUNT EVENT
    # Only parent row visibility changes here.
    # --------------------------------------------------------
    active_count.change(
        fn=update_subject_rows,
        inputs=[active_count],
        outputs=subject_row_components,
    )

    # --------------------------------------------------------
    # GENERATE RESULT EVENT
    # --------------------------------------------------------
    submit.click(
        fn=calculate,
        inputs=[
            student,
            roll,
            gender,
            dob,
            parent_name,
            class_level,
            section,
            session,
            school_address,
            school_contact,
            student_photo,
            active_count,
            grace_enabled,
            grace_allowance,
            *subject_controls,
        ],
        outputs=[result, chart, pdf],
    )

    gr.Markdown(
        "*School report-card demo. Subject presets are suggested templates. "
        "Verify subjects, maximum marks, grading, pass criteria and grace "
        "policy against the school's official requirements before formal use.*"
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
