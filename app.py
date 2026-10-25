import io
from datetime import datetime
import gradio as gr
import plotly.graph_objects as go
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

INSTITUTION_NAME = "YOUR INSTITUTION NAME"
INSTITUTION_TAGLINE = "ACADEMIC EXCELLENCE • STUDENT PERFORMANCE"
SUBJECTS = ["Mathematics", "Science", "English", "Hindi", "Social Science", "Sanskrit"]
CSS = """
:root { --paper:#F5F3EE; --ink:#202522; --sage:#526B5D; --bronze:#A77B46; --muted:#777970; --line:#D9D5CC; }
.gradio-container { background:var(--paper)!important; color:var(--ink)!important; max-width:1180px!important; margin:auto!important; }
#hero { padding:28px 30px; border:1px solid var(--line); border-radius:18px; background:linear-gradient(135deg,#fffefa,#ebe9e1); margin-bottom:18px; }
#hero h1 { color:var(--ink); margin:0; font-size:2rem; letter-spacing:-.03em; }
#hero p { color:var(--muted); margin:8px 0 0; letter-spacing:.08em; font-size:.78rem; }
.panel { border:1px solid var(--line)!important; border-radius:16px!important; background:#FFFEFA!important; }
button.primary { background:var(--sage)!important; border-color:var(--sage)!important; }
footer { display:none!important; }
"""

def grade_for(p):
    if p >= 90: return "A+"
    if p >= 80: return "A"
    if p >= 70: return "B+"
    if p >= 60: return "B"
    if p >= 50: return "C"
    if p >= 33: return "D"
    return "F"

def create_pdf(name, roll, gender, marks, total, pct, grade, status, distinctions, note):
    buff = io.BytesIO()
    doc = SimpleDocTemplate(buff, pagesize=A4, rightMargin=18*mm, leftMargin=18*mm, topMargin=16*mm, bottomMargin=16*mm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Inst", parent=styles["Title"], alignment=TA_CENTER, textColor=colors.HexColor("#202522"), fontSize=18, leading=22))
    styles.add(ParagraphStyle(name="Tag", parent=styles["Normal"], alignment=TA_CENTER, textColor=colors.HexColor("#777970"), fontSize=8, leading=12, spaceAfter=14))
    story = [Paragraph(INSTITUTION_NAME, styles["Inst"]), Paragraph(INSTITUTION_TAGLINE, styles["Tag"]), Paragraph("STUDENT RESULT / MARKSHEET", styles["Heading1"]), Spacer(1, 5*mm)]
    info = [["Student Name", name, "Roll Number", roll], ["Gender", gender, "Issue Date", datetime.now().strftime("%d %b %Y")]]
    t = Table(info, colWidths=[28*mm, 55*mm, 28*mm, 55*mm])
    t.setStyle(TableStyle([("BACKGROUND",(0,0),(0,-1),colors.HexColor("#E9E7DF")),("BACKGROUND",(2,0),(2,-1),colors.HexColor("#E9E7DF")),("GRID",(0,0),(-1,-1),.5,colors.HexColor("#D9D5CC")),("FONTSIZE",(0,0),(-1,-1),9),("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8)]))
    story += [t, Spacer(1,7*mm), Paragraph("Subject-wise Performance", styles["Heading2"])]
    rows = [["Subject","Max Marks","Obtained","Result"]]
    for s,m in zip(SUBJECTS,marks): rows.append([s,"100",str(m),"Pass" if m>=33 else "Needs Improvement"])
    rows.append(["TOTAL","600",str(total),""])
    t2 = Table(rows, colWidths=[65*mm,30*mm,30*mm,41*mm], repeatRows=1)
    t2.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#526B5D")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("BACKGROUND",(0,-1),(-1,-1),colors.HexColor("#E9E7DF")),("GRID",(0,0),(-1,-1),.5,colors.HexColor("#D9D5CC")),("FONTSIZE",(0,0),(-1,-1),9),("ALIGN",(1,1),(-1,-1),"CENTER"),("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7)]))
    story += [t2, Spacer(1,7*mm), Paragraph("Final Summary", styles["Heading2"])]
    summ = Table([["Percentage",f"{pct:.2f}%"],["Grade",grade],["Overall Status",status],["Distinction Subjects (85+)",", ".join(distinctions) if distinctions else "None"]], colWidths=[55*mm,111*mm])
    summ.setStyle(TableStyle([("BACKGROUND",(0,0),(0,-1),colors.HexColor("#E9E7DF")),("GRID",(0,0),(-1,-1),.5,colors.HexColor("#D9D5CC")),("FONTSIZE",(0,0),(-1,-1),9),("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8)]))
    story += [summ, Spacer(1,5*mm)]
    if note: story.append(Paragraph(note, styles["Normal"]))
    story += [Spacer(1,15*mm), Paragraph("__________________________                         __________________________", styles["Normal"]), Paragraph("Class Teacher Signature                                      Principal Signature", styles["Normal"]), Spacer(1,6*mm), Paragraph("Demo marksheet. Verify official grading rules before formal use.", styles["Italic"])]
    doc.build(story)
    buff.seek(0)
    return buff.getvalue()

def calculate(name, roll, gender, *vals):
    grace_ok = bool(vals[-1])
    marks = [int(round(float(x or 0))) for x in vals[:-1]]
    if not name or not name.strip(): raise gr.Error("Please enter the student's name.")
    if not roll or not roll.strip(): raise gr.Error("Please enter the roll number.")
    if any(x < 0 or x > 100 for x in marks): raise gr.Error("Each subject mark must be between 0 and 100.")
    total = sum(marks); pct = total/600*100
    fails = [i for i,m in enumerate(marks) if m < 33]
    grace_used = bool(grace_ok and len(fails)==1 and 28 <= marks[fails[0]] <= 32)
    passed = len(fails)==0 or grace_used
    status = "PASS" if passed else "FAIL"
    grade = grade_for(pct) if passed else "F"
    distinctions = [SUBJECTS[i] for i,m in enumerate(marks) if m >= 85]
    note = "Grace pass applied under the demo policy." if grace_used else ""
    fig = go.Figure(go.Bar(x=SUBJECTS, y=marks, text=marks, textposition="outside",
        marker_color=["#A77B46" if m>=85 else "#526B5D" for m in marks],
        hovertemplate="%{x}: %{y}/100<extra></extra>"))
    fig.update_layout(title="Subject Performance Overview", yaxis=dict(title="Marks (out of 100)",range=[0,110],dtick=20),
        template="plotly_white", height=380, paper_bgcolor="#FFFEFA", plot_bgcolor="#FFFEFA",
        font=dict(color="#202522"), margin=dict(l=20,r=20,t=55,b=55))
    html = f'<div style="border-left:4px solid #A77B46;padding:16px;background:#FFFEFA;border-radius:10px"><h2 style="color:#526B5D">{status}</h2><p><b>Student:</b> {name} | <b>Roll No:</b> {roll}</p><p><b>Total:</b> {total}/600 | <b>Percentage:</b> {pct:.2f}%</p><p><b>Grade:</b> {grade} | <b>Distinction subjects:</b> {", ".join(distinctions) if distinctions else "None"}</p>{f"<p>{note}</p>" if note else ""}</div>'
    data = create_pdf(name, roll, gender, marks, total, pct, grade, status, distinctions, note)
    return html, fig, (f"marksheet_{roll.strip().replace(' ','_')}.pdf", data)

with gr.Blocks(title="Student Result Portal", css=CSS) as app:
    gr.HTML(f'<div id="hero"><h1>Student Result Portal</h1><p>{INSTITUTION_TAGLINE}</p></div>')
    gr.Markdown("Enter student details and marks to generate a result summary, performance chart, and downloadable PDF marksheet.")
    with gr.Row():
        with gr.Column():
            with gr.Group(elem_classes=["panel"]):
                gr.Markdown("### Student Information")
                name = gr.Textbox(label="Student Name", placeholder="Enter full name")
                roll = gr.Textbox(label="Roll Number", placeholder="Enter roll number")
                gender = gr.Dropdown(["Female","Male","Other","Prefer not to say"], label="Gender", value="Prefer not to say")
            with gr.Group(elem_classes=["panel"]):
                gr.Markdown("### Subject Marks (each out of 100)")
                mark_inputs = [gr.Number(label=s, value=0, minimum=0, maximum=100, precision=0) for s in SUBJECTS]
                grace = gr.Checkbox(label="Officially approved grace policy applies (demo: one subject with 28–32 marks)", value=False)
                submit = gr.Button("Calculate Result & Generate Marksheet", variant="primary")
        with gr.Column():
            result = gr.HTML(label="Result Summary")
            chart = gr.Plot(label="Performance Chart")
            pdf = gr.File(label="Download PDF Marksheet")
    submit.click(calculate, inputs=[name,roll,gender,*mark_inputs,grace], outputs=[result,chart,pdf])
    gr.Markdown("*Educational demo only. Confirm your institution's official grading and grace-mark rules before formal use.*")

if __name__ == "__main__":
    app.launch()
