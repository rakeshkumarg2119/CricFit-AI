"""
CricFit AI — PDF Report Generator Service
=========================================
Generates professional, printable, high-fidelity PDF fitness & biomechanical
assessment reports for Cricket Batting, Bowling, and Yo-Yo tests.
"""

import os
import uuid
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

OUTPUTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")
PDF_REPORTS_DIR = os.path.join(OUTPUTS_DIR, "reports")
os.makedirs(PDF_REPORTS_DIR, exist_ok=True)


def generate_pdf_report(report_data: dict) -> str:
    """
    Generates a beautifully structured PDF document from the enriched analysis report
    and returns the relative/absolute filepath.
    """
    report_id = report_data.get("id", f"REP-{uuid.uuid4().hex[:8].upper()}")
    filename = f"cricfit_report_{report_id}.pdf"
    pdf_path = os.path.join(PDF_REPORTS_DIR, filename)

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    # Custom styling
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#0F172A'),
        alignment=TA_LEFT
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#64748B'),
        alignment=TA_LEFT
    )

    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=17,
        textColor=colors.HexColor('#0284C7'),
        spaceBefore=14,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor('#1E293B')
    )

    body_bold = ParagraphStyle(
        'BodyBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor('#0F172A')
    )

    story = []

    # --- Header Banner Table ---
    activity = str(report_data.get("activity", "Cricket Biomechanics")).upper()
    date_str = report_data.get("date_str", datetime.now().strftime("%d %b %Y, %I:%M %p"))
    overall_score = report_data.get("overall_score", 78)
    risk_level = report_data.get("risk_level", "Low")

    header_left = [
        Paragraph("<b>CRICFIT AI — PERFORMANCE REPORT</b>", title_style),
        Paragraph(f"Activity: <b>{activity}</b>  |  Report ID: {report_id}  |  Date: {date_str}", subtitle_style)
    ]
    
    score_badge = [
        Paragraph(f"<font size=22 color='#0284C7'><b>{overall_score}</b></font><font size=11 color='#64748B'>/100</font>", ParagraphStyle('ScoreNum', alignment=TA_CENTER, leading=24)),
        Paragraph(f"<b>Overall Score</b> ({risk_level} Risk)", ParagraphStyle('ScoreLbl', alignment=TA_CENTER, fontSize=8, textColor=colors.HexColor('#475569')))
    ]

    header_table = Table([[header_left, score_badge]], colWidths=[380, 150])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BACKGROUND', (1,0), (1,0), colors.HexColor('#F0F9FF')),
        ('BOX', (1,0), (1,0), 1, colors.HexColor('#BAE6FD')),
        ('LEFTPADDING', (1,0), (1,0), 10),
        ('RIGHTPADDING', (1,0), (1,0), 10),
        ('TOPPADDING', (1,0), (1,0), 8),
        ('BOTTOMPADDING', (1,0), (1,0), 8),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#E2E8F0"), spaceBefore=4, spaceAfter=10))

    # --- Section 1: Everyday AI Analysis & Plain Language Breakdown ---
    story.append(Paragraph("1. ATHLETE PERFORMANCE & TECHNICAL SUMMARY", section_heading))
    summary_text = report_data.get("ai_summary", "Detailed assessment performed.")
    story.append(Paragraph(summary_text, body_style))
    story.append(Spacer(1, 8))

    # Activity-specific badge highlight
    if "shot_classification" in report_data:
        shot_lbl = report_data["shot_classification"].get("label", "").replace("_", " ").title()
        shot_conf = round(report_data["shot_classification"].get("confidence", 0.0) * 100, 1)
        story.append(Paragraph(f"<b>Identified Stroke:</b> {shot_lbl} (AI Confidence: {shot_conf}%)", body_bold))
    elif "closest_pro_match" in report_data:
        pro_name = report_data["closest_pro_match"].get("player", "Reference Bowler")
        arm_pace = f"{report_data.get('arm_classification', {}).get('label', '')} {report_data.get('pace_classification', {}).get('label', '')}".title()
        story.append(Paragraph(f"<b>Action Profile:</b> {arm_pace}  |  <b>Closest Pro Bowler Match:</b> {pro_name}", body_bold))
    elif "shuttle_metrics" in report_data:
        shuttles = report_data["shuttle_metrics"].get("shuttles_detected", 0)
        trend = report_data["shuttle_metrics"].get("cadence_trend", "stable").title()
        story.append(Paragraph(f"<b>Shuttles Detected:</b> {shuttles}  |  <b>Cadence Trend:</b> {trend}", body_bold))

    story.append(Spacer(1, 8))

    # --- Section 2: Biomechanical Movement Metrics Table ---
    story.append(Paragraph("2. BIOMECHANICAL METRICS (0 – 100)", section_heading))
    metrics = report_data.get("metrics", {})
    metric_rows = [["Biomechanical Metric", "Score", "Standard Benchmark", "Status"]]
    for k, v in metrics.items():
        name = k.replace("_", " ").title()
        score = int(v) if v is not None else 0
        status = "Elite" if score >= 85 else ("Good" if score >= 70 else ("Needs Work" if score >= 55 else "Poor"))
        metric_rows.append([name, f"{score}/100", "75.0 / 100", status])

    if len(metric_rows) > 1:
        metrics_table = Table(metric_rows, colWidths=[200, 90, 130, 110])
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F1F5F9')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#0F172A')),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 9),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
            ('ALIGN', (1,0), (-1,-1), 'CENTER'),
        ]))
        story.append(metrics_table)

    story.append(Spacer(1, 10))

    # --- Section 3: Prescribed Fitness Exercises & Improvement Mechanics ---
    story.append(Paragraph("3. TARGETED CRICKET FITNESS DRILLS & IMPROVEMENT MECHANICS", section_heading))
    exercises = report_data.get("exercises", [])
    if not exercises and "recommendations" in report_data:
        # Fallback to standard recommendations if structured exercises format differs
        exercises = report_data.get("recommendations", [])

    for idx, ex in enumerate(exercises, 1):
        if isinstance(ex, dict):
            ex_name = ex.get("exercise_name") or ex.get("exercise") or ex.get("title") or f"Drill {idx}"
            target = ex.get("target_area") or ex.get("target") or "Biomechanics"
            sets_reps = ex.get("sets_and_reps") or f"{ex.get('sets', '3')} sets × {ex.get('duration', '30s')}"
            how_improves = ex.get("how_it_improves") or ex.get("reason") or ex.get("explanation") or "Improves kinetic chain power."
            
            ex_cell = [
                Paragraph(f"<b>{idx}. {ex_name}</b> ({sets_reps}) — <i>Target: {target}</i>", body_bold),
                Paragraph(f"<b>How this fixes your technique:</b> {how_improves}", body_style)
            ]
            t = Table([[ex_cell]], colWidths=[530])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
                ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
                ('TOPPADDING', (0,0), (-1,-1), 6),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                ('LEFTPADDING', (0,0), (-1,-1), 8),
                ('RIGHTPADDING', (0,0), (-1,-1), 8),
            ]))
            story.append(t)
            story.append(Spacer(1, 6))

    # Long-term improvement note
    long_term = report_data.get("how_following_improves")
    if long_term:
        story.append(Spacer(1, 4))
        story.append(Paragraph(f"<b>Long-Term Performance Impact:</b> {long_term}", body_style))

    story.append(Spacer(1, 10))

    # --- Section 4: Cricket Nutrition & Recovery Diet Plan ---
    nutrition = report_data.get("nutrition_plan", {})
    if nutrition and isinstance(nutrition, dict):
        story.append(Paragraph("4. CRICKET NUTRITION & RECOVERY GUIDELINES", section_heading))
        nutri_rows = []
        if "pre_workout" in nutrition:
            nutri_rows.append([Paragraph("<b>Pre-Training Energy:</b>", body_bold), Paragraph(str(nutrition["pre_workout"]), body_style)])
        if "post_workout" in nutrition:
            nutri_rows.append([Paragraph("<b>Post-Training Recovery:</b>", body_bold), Paragraph(str(nutrition["post_workout"]), body_style)])
        if "hydration_strategy" in nutrition:
            nutri_rows.append([Paragraph("<b>Hydration Strategy:</b>", body_bold), Paragraph(str(nutrition["hydration_strategy"]), body_style)])
        if "key_foods" in nutrition and isinstance(nutrition["key_foods"], list):
            foods_txt = " • " + " • ".join(nutrition["key_foods"])
            nutri_rows.append([Paragraph("<b>Key Power Foods:</b>", body_bold), Paragraph(foods_txt, body_style)])

        if nutri_rows:
            nutri_table = Table(nutri_rows, colWidths=[150, 380])
            nutri_table.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F0FDF4')),
                ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#BBF7D0')),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#DCFCE7')),
                ('TOPPADDING', (0,0), (-1,-1), 5),
                ('BOTTOMPADDING', (0,0), (-1,-1), 5),
                ('LEFTPADDING', (0,0), (-1,-1), 8),
                ('RIGHTPADDING', (0,0), (-1,-1), 8),
            ]))
            story.append(nutri_table)

    # --- Footer ---
    story.append(Spacer(1, 16))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CBD5E1"), spaceBefore=6, spaceAfter=8))
    footer_text = Paragraph(
        "<i>Generated by CricFit AI Biomechanics Engine. For high-performance athletic development and injury prevention.</i>",
        ParagraphStyle('Footer', alignment=TA_CENTER, fontSize=8, textColor=colors.HexColor('#94A3B8'))
    )
    story.append(footer_text)

    # Build document
    doc.build(story)
    return pdf_path
