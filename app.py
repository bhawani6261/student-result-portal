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
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image as PDFImage
)

INSTITUTION_NAME = "NAHUSH PUBLIC HIGH SCHOOL MOHLA"
INSTITUTION_TAGLINE = "Academic Excellence • Student Performance"

MAX_SUBJECTS = 10
PASS_PERCENTAGE = 33
PASS_COLOR = "#167A43"
FAIL_COLOR = "#B42318"

# Suggested presets: verify these subjects against the school's curriculum.
CLASS_PRESETS = {
    "Class 1": [
        ("English", 100), ("Hindi", 100),
        ("Mathematics", 100), ("EVS", 100)
    ],
    "Class 2": [
        ("English", 100), ("Hindi", 100),
        ("Mathematics", 100), ("EVS", 100)
    ],
    "Class 3": [
        ("English", 100), ("Hindi", 100),
        ("Mathematics", 100), ("EVS", 100)
    ],
    "Class 4": [
        ("English", 100), ("Hindi", 100),
        ("Mathematics", 100), ("EVS", 100)
    ],
    "Class 5": [
        ("English", 100), ("Hindi", 100),
        ("Mathematics", 100), ("EVS", 100)
    ],
    "Class 6": [
        ("English", 100), ("Hindi", 100), ("Mathematics", 100),
        ("Science", 100), ("Social Science", 100), ("Sanskrit", 100)
    ],
    "Class 7": [
        ("English", 100), ("Hindi", 100), ("Mathematics", 100),
        ("Science", 100), ("Social Science", 100), ("Sanskrit", 100)
    ],
    "Class 8": [
        ("English", 100), ("Hindi", 100), ("Mathematics", 100),
        ("Science", 100), ("Social Science", 100), ("Sanskrit", 100)
    ],
    "Class 9": [
        ("English", 100), ("Hindi", 100), ("Mathematics", 100),
        ("Science", 100), ("Social Science", 100), ("Sanskrit", 100)
    ],
    "Class 10": [
        ("English", 100), ("Hindi", 100), ("Mathematics", 100),
        ("Science", 100), ("Social Science", 100), ("Sanskrit", 100)
    ],
    "Class 11 (Science)": [
        ("English", 100), ("Physics", 100), ("Chemistry", 100),
        ("Mathematics", 100), ("Biology", 100)
    ],
    "Class 11 (Commerce)": [
        ("English", 100), ("Accountancy", 100),
        ("Business Studies", 100), ("Economics", 100),
        ("Mathematics", 100)
    ],
    "Class 11 (Arts)": [
        ("English", 100), ("History", 100),
        ("Political Science", 100), ("Geography", 100),
        ("Economics", 100)
    ],
    "Class 12 (Science)": [
        ("English", 100), ("Physics", 100), ("Chemistry", 100),
        ("Mathematics", 100), ("Biology", 100)
    ],
    "Class 12 (Commerce)": [
        ("English", 100), ("Accountancy", 100),
        ("Business Studies", 100), ("Economics", 100),
        ("Mathematics", 100)
    ],
    "Class 12 (Arts)": [
        ("English", 100), ("History", 100),
        ("Political Science", 100), ("Geography", 100),
        ("Economics", 100)
    ],
}

CSS = """
:root {
    --paper:#F5F3EE;
    --ink:#202522;
    --sage:#526B5D;
    --bronze:#A77B46;
    --muted:#777970;
    --line:#D9D5CC;
}
.gradio-container {
    background:var(--paper)!important;
    color:var(--ink)!important;
    max-width:1220px!important;
    margin:auto!important;
}
#hero {
    padding:28px 30px;
    border:1px solid var(--line);
    border-radius:18px;
    background:linear-gradient(135deg,#fffefa,#ebe9e1);
    margin-bottom:18px;
}
#hero h1 {
    color:var(--ink);
    margin:0;
    font-size:2rem;
}
#hero p {
    color:var(--muted);
    margin:8px 0 0;
    letter-spacing:.08em;
    font-size:.78rem;
}
.panel {
    border:1px solid var(--line)!important;
    border-radius:16px!important;
    background:#FFFEFA!important;
}
button.primary {
    background:var(--sage)!important;
    border-color:var(--sage)!important;
}
footer {
    display:none!important;
}
"""


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


def preset_updates(class_level):
    preset = CLASS_PRESETS[class_level]
    updates = [gr.update(value=len(preset))]

    for i in range(MAX_SUBJECTS):
        if i < len(preset):
            subject, maximum = preset[i]
            updates.extend([
                gr.update(value=subject, visible=True),
                gr.update(value=maximum, visible=True),
                gr.update(value=0, visible=True),
            ])
        else:
            updates.extend([
                gr.update(value=f"Subject {i + 1}", visible=False),
                gr.update(value=100, visible=False),
                gr.update(value=0, visible=False),
            ])

    return updates


def update_subject_rows(count):
    count = max(1, min(MAX_SUBJECTS, int(count)))
    updates = []

    for i in range(MAX_SUBJECTS):
        visible = i < count
        updates.extend([gr.update(visible=visible)] * 3)

    return updates


def create_pdf(
    student, roll, gender, dob, parent_name, class_level,
    section, session, school_address, school_contact,
    student_photo, subject_rows, total, max_total,
    pct, grade, status, distinctions, grace_note
):
    buff = io.BytesIO()

    doc = SimpleDocTemplate(
        buff,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm
    )

    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="Institution",
        parent=styles["Title"],
        alignment=TA_CENTER,
        textColor=colors.HexColor("#202522"),
        fontSize=17,
        leading=21,
        spaceAfter=3
    ))

    styles.add(ParagraphStyle(
        name="Tagline",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        textColor=colors.HexColor("#62675F"),
        fontSize=8,
        leading=11,
        spaceAfter=7
    ))

    styles.add(ParagraphStyle(
        name="Small",
        parent=styles["Normal"],
        fontSize=8,
        leading=10
    ))

    story = [
        Paragraph(
            html.escape(INSTITUTION_NAME),
            styles["Institution"]
        ),
        Paragraph(
            html.escape(INSTITUTION_TAGLINE),
            styles["Tagline"]
        ),
    ]

    address_line = " | ".join(
        value for value in [school_address.strip(), school_contact.strip()]
        if value
    )

    if address_line:
        story.append(
            Paragraph(html.escape(address_line), styles["Small"])
        )

    story.extend([
        Spacer(1, 3 * mm),
        Paragraph("STUDENT REPORT CARD", styles["Heading1"]),
        Spacer(1, 2 * mm)
    ])

    if student_photo and os.path.isfile(student_photo):
        try:
            photo = PDFImage(
                student_photo,
                width=25 * mm,
                height=29 * mm
            )
            photo.hAlign = "RIGHT"
            story.extend([photo, Spacer(1, 2 * mm)])
        except Exception:
            pass

    student_info = [
        ["Student Name", html.escape(student),
         "Roll Number", html.escape(roll)],
        ["Father / Mother", html.escape(parent_name or "—"),
         "Date of Birth", html.escape(dob or "—")],
        ["Class", html.escape(class_level),
         "Section", html.escape(section or "—")],
        ["Academic Session", html.escape(session or "—"),
         "Gender", html.escape(gender or "—")],
        ["Issue Date", datetime.now().strftime("%d %b %Y"), "", ""],
    ]

    info_table = Table(
        student_info,
        colWidths=[30 * mm, 53 * mm, 30 * mm, 53 * mm]
    )

    info_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E9E7DF")),
        ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#E9E7DF")),
        ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#C9C5BB")),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))

    story.extend([
        info_table,
        Spacer(1, 5 * mm),
        Paragraph("Subject-wise Performance", styles["Heading2"])
    ])

    rows = [[
        "Subject", "Maximum Marks", "Marks Obtained",
        "Percentage", "Status"
    ]]

    for subject, maximum, mark in subject_rows:
        subject_pct = mark / maximum * 100
        rows.append([
            html.escape(subject),
            f"{maximum:g}",
            f"{mark:g}",
            f"{subject_pct:.1f}%",
            "Pass" if subject_pct >= PASS_PERCENTAGE
            else "Needs Improvement"
        ])

    rows.append([
        "TOTAL",
        f"{max_total:g}",
        f"{total:g}",
        f"{pct:.2f}%",
        ""
    ])

    marks_table = Table(
        rows,
        colWidths=[48 * mm, 28 * mm, 28 * mm, 25 * mm, 37 * mm],
        repeatRows=1
    )

    marks_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#344A3E")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E9E7DF")),
        ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#C9C5BB")),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))

    story.extend([
        marks_table,
        Spacer(1, 5 * mm),
        Paragraph("Final Summary", styles["Heading2"])
    ])

    summary = Table([
        ["Total Marks", f"{total:g} / {max_total:g}"],
        ["Percentage", f"{pct:.2f}%"],
        ["Grade", grade],
        ["Overall Result", status],
        [
            "Distinction Subjects (85%+)",
            ", ".join(distinctions) if distinctions else "None"
        ],
    ], colWidths=[55 * mm, 111 * mm])

    summary.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E9E7DF")),
        (
            "TEXTCOLOR", (1, 3), (1, 3),
            colors.HexColor(PASS_COLOR if status == "PASS" else FAIL_COLOR)
        ),
        ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#C9C5BB")),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))

    story.extend([summary, Spacer(1, 3 * mm)])

    if grace_note:
        story.append(
            Paragraph(html.escape(grace_note), styles["Small"])
        )

    signature_table = Table([
        ["____________________________", "____________________________"],
        ["Class Teacher Signature", "Principal Signature"]
    ], colWidths=[83 * mm, 83 * mm])

    signature_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
    ]))

    story.extend([
        Spacer(1, 13 * mm),
        signature_table,
        Spacer(1, 5 * mm),
        Paragraph(
            "For official use, verify the school's approved subjects, "
            "grading and grace-mark policy.",
            styles["Italic"]
        )
    ])

    doc.build(story)
    buff.seek(0)
    return buff.getvalue()


def calculate(
    student, roll, gender, dob, parent_name, class_level,
    section, session, school_address, school_contact,
    student_photo, active_count, grace_enabled, grace_allowance,
    *values
):
    if not student or not student.strip():
        raise gr.Error("Please enter the student's name.")

    if not roll or not roll.strip():
        raise gr.Error("Please enter the roll number.")

    if (
        grace_allowance is None
        or float(grace_allowance) < 0
        or float(grace_allowance) > PASS_PERCENTAGE
    ):
        raise gr.Error("Grace allowance must be between 0 and 33.")

    subject_rows = []

    for i in range(int(active_count)):
        subject = str(values[i * 3] or "").strip()
        maximum = values[i * 3 + 1]
        mark = float(values[i * 3 + 2] or 0)

        if not subject:
            raise gr.Error(f"Please enter a name for subject {i + 1}.")

        if maximum is None or float(maximum) <= 0:
            raise gr.Error(
                f"Maximum marks for {subject} must be greater than zero."
            )

        maximum = float(maximum)

        if mark < 0 or mark > maximum:
            raise gr.Error(
                f"Marks for {subject} must be between 0 and {maximum:g}."
            )

        subject_rows.append((subject, maximum, mark))

    max_total = sum(row[1] for row in subject_rows)
    total = sum(row[2] for row in subject_rows)
    pct = total / max_total * 100 if max_total else 0

    fails = [
        i for i, (_, maximum, mark) in enumerate(subject_rows)
        if mark / maximum * 100 < PASS_PERCENTAGE
    ]

    allowance = float(grace_allowance or 0)

    grace_used = bool(
        grace_enabled
        and allowance > 0
        and len(fails) == 1
        and PASS_PERCENTAGE - allowance
        <= subject_rows[fails[0]][2] / subject_rows[fails[0]][1] * 100
        < PASS_PERCENTAGE
    )

    passed = len(fails) == 0 or grace_used
    status = "PASS" if passed else "FAIL"
    grade = grade_for(pct) if passed else "F"

    distinctions = [
        subject for subject, maximum, mark in subject_rows
        if mark / maximum * 100 >= 85
    ]

    grace_note = (
        "Grace pass applied using the configured demo allowance. "
        "Confirm this matches school policy."
        if grace_used else ""
    )

    subjects = [row[0] for row in subject_rows]
    percentages = [row[2] / row[1] * 100 for row in subject_rows]

    fig = go.Figure(go.Bar(
        x=subjects,
        y=percentages,
        text=[f"{p:.1f}%" for p in percentages],
        textposition="outside",
        marker_color=[
            "#A77B46" if p >= 85 else "#526B5D"
            for p in percentages
        ],
        hovertemplate="%{x}: %{y:.1f}%<extra></extra>"
    ))

    fig.update_layout(
        title="Subject Performance Overview",
        yaxis=dict(
            title="Marks (% of maximum)",
            range=[0, 110],
            dtick=20
        ),
        template="plotly_white",
        height=390,
        paper_bgcolor="#FFFEFA",
        plot_bgcolor="#FFFEFA",
        font=dict(color="#202522"),
        margin=dict(l=20, r=20, t=55, b=75)
    )

    status_color = PASS_COLOR if passed else FAIL_COLOR
    status_bg = "#E8F6ED" if passed else "#FDECEC"

    result_html = (
        f'<div style="border:2px solid {status_color};'
        f'border-left:10px solid {status_color};padding:20px;'
        f'background:{status_bg};border-radius:14px;color:#202522">'
        f'<div style="display:inline-block;background:{status_color};'
        f'color:#fff;padding:10px 28px;border-radius:999px;'
        f'font-size:25px;font-weight:900;letter-spacing:1.5px;'
        f'margin-bottom:12px">{status}</div>'
        f'<h3 style="margin:3px 0 10px;color:#202522">'
        f'{html.escape(student)} '
        f'<span style="font-size:14px;font-weight:500">'
        f'| Roll No: {html.escape(roll)}</span></h3>'
        f'<p><b>Class:</b> {html.escape(class_level)} &nbsp;'
        f'<b>Section:</b> {html.escape(section or "—")}</p>'
        f'<p style="font-size:18px"><b>Total:</b> '
        f'{total:g}/{max_total:g} &nbsp;'
        f'<b>Percentage:</b> {pct:.2f}%</p>'
                f'<p><b>Grade:</b> {grade} &nbsp; '
        f'<b>Distinctions:</b> '
        f'{", ".join(html.escape(x) for x in distinctions) if distinctions else "None"}</p>'
        f'{f"<p><b>{html.escape(grace_note)}</b></p>" if grace_note else ""}'
        f'</div>'
    )

    pdf_bytes = create_pdf(
        student.strip(), roll.strip(), gender, dob, parent_name,
        class_level, section, session, school_address, school_contact,
        student_photo, subject_rows, total, max_total, pct,
        grade, status, distinctions, grace_note
    )

    safe_roll = "".join(
        ch if ch.isalnum() or ch in "-_" else "_"
        for ch in roll.strip()
    )

    pdf_path = os.path.join(
        tempfile.gettempdir(),
        f"marksheet_{safe_roll}.pdf"
    )

    with open(pdf_path, "wb") as file:
        file.write(pdf_bytes)

    return result_html, fig, pdf_path


with gr.Blocks(
    title="Nahush Public High School Mohla - Student Result Portal"
) as app:

    gr.HTML(
        f'<div id="hero"><h1>{html.escape(INSTITUTION_NAME)}</h1>'
        f'<p>{html.escape(INSTITUTION_TAGLINE)}</p></div>'
    )

    gr.Markdown(
        "Generate a student result summary, subject performance chart "
        "and downloadable PDF report card."
    )

    with gr.Row():
        with gr.Column(scale=1):

            with gr.Group(elem_classes=["panel"]):
                gr.Markdown("### Student & School Information")

                student = gr.Textbox(
                    label="Student Name",
                    placeholder="Enter student's full name"
                )

                roll = gr.Textbox(
                    label="Roll Number",
                    placeholder="Enter roll number"
                )

                gender = gr.Dropdown(
                    ["Female", "Male", "Other", "Prefer not to say"],
                    label="Gender",
                    value="Prefer not to say"
                )

                dob = gr.Textbox(
                    label="Date of Birth",
                    placeholder="e.g. 23/03/2012"
                )

                parent_name = gr.Textbox(
                    label="Father / Mother Name",
                    placeholder="Enter parent/guardian name"
                )

                class_level = gr.Dropdown(
                    list(CLASS_PRESETS.keys()),
                    label="Class / Stream",
                    value="Class 5"
                )

                with gr.Row():
                    section = gr.Textbox(
                        label="Class / Section",
                        placeholder="e.g. A"
                    )

                    session = gr.Textbox(
                        label="Academic Session",
                        placeholder="e.g. 2026-27"
                    )

                school_address = gr.Textbox(
                    label="School Address",
                    placeholder="Enter school address"
                )

                school_contact = gr.Textbox(
                    label="School Contact",
                    placeholder="Phone / email"
                )

                student_photo = gr.Image(
                    label="Student Photo (optional)",
                    type="filepath",
                    height=180
                )

            with gr.Group(elem_classes=["panel"]):
                gr.Markdown("### Subject Marks")

                gr.Markdown(
                    "Choose a class preset, then edit subject names "
                    "and maximum marks if required."
                )

                active_count = gr.Slider(
                    minimum=1,
                    maximum=MAX_SUBJECTS,
                    step=1,
                    value=4,
                    label="Number of subjects"
                )

                grace_enabled = gr.Checkbox(
                    label="Enable grace marks option",
                    value=True
                )

                grace_allowance = gr.Number(
                    label="Grace allowance (percentage points)",
                    value=0,
                    minimum=0,
                    maximum=33,
                    precision=1
                )

                gr.Markdown(
                    "Pass mark is currently 33% per subject. "
                    "Verify the school's official rules."
                )

                subject_controls = []
                default_subjects = CLASS_PRESETS["Class 5"]

                for i in range(MAX_SUBJECTS):
                    with gr.Row(visible=(i < len(default_subjects))):
                        subject_box = gr.Textbox(
                            label=f"Subject {i + 1}",
                            value=(
                                default_subjects[i][0]
                                if i < len(default_subjects)
                                else f"Subject {i + 1}"
                            ),
                            scale=3
                        )

                        max_box = gr.Number(
                            label="Maximum",
                            value=100,
                            minimum=1,
                            precision=0,
                            scale=1
                        )

                        mark_box = gr.Number(
                            label="Obtained",
                            value=0,
                            minimum=0,
                            precision=1,
                            scale=1
                        )

                    subject_controls.extend([
                        subject_box, max_box, mark_box
                    ])

                submit = gr.Button(
                    "Generate Result & PDF Marksheet",
                    variant="primary"
                )

        with gr.Column(scale=1):
            result = gr.HTML(label="Result Summary")
            chart = gr.Plot(label="Performance Chart")
            pdf = gr.File(label="Download PDF Report Card")

    class_outputs = [active_count]

    for i in range(MAX_SUBJECTS):
        class_outputs.extend(subject_controls[i * 3:i * 3 + 3])

    class_level.change(
        preset_updates,
        inputs=[class_level],
        outputs=class_outputs
    )

    count_outputs = []

    for i in range(MAX_SUBJECTS):
        count_outputs.extend(subject_controls[i * 3:i * 3 + 3])

    active_count.change(
        update_subject_rows,
        inputs=[active_count],
        outputs=count_outputs
    )

    submit.click(
        calculate,
        inputs=[
            student, roll, gender, dob, parent_name,
            class_level, section, session, school_address,
            school_contact, student_photo, active_count,
            grace_enabled, grace_allowance, *subject_controls
        ],
        outputs=[result, chart, pdf]
    )

    gr.Markdown(
        "*Educational report-card demo. Confirm the school's official "
        "subjects, grading and grace-mark policy before formal use.*"
    )


if __name__ == "__main__":
    app.launch(
        server_name="0.0.0.0",
        server_port=int(os.environ.get("PORT", "10000"))
    )
