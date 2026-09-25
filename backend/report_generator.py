"""
report_generator.py - Official Municipal Heat Risk Report PDF Generator
Produces a high-quality, professional, printable light-background document
using ReportLab with zero external system binaries.
"""

import io
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether
)


def _get_ist_time_str(dt: Optional[datetime] = None) -> str:
    """Return formatted Indian Standard Time (UTC+5:30) string."""
    if dt is None:
        dt = datetime.now(timezone.utc)
    ist_tz = timezone(timedelta(hours=5, minutes=30))
    ist_dt = dt.astimezone(ist_tz)
    return ist_dt.strftime("%d %b %Y, %I:%M %p IST")


def _derive_forecast_trend_summary(forecast: List[Dict[str, Any]]) -> str:
    """Derive a one-line written summary of the 7-day thermal trajectory."""
    if not forecast or len(forecast) < 2:
        return "Thermal conditions are projected to remain relatively stable over the forecast period."

    first_days_wbgt = sum(float(d.get("wbgt", 30)) for d in forecast[:2]) / 2.0
    last_days_wbgt = sum(float(d.get("wbgt", 30)) for d in forecast[-2:]) / 2.0
    diff = round(last_days_wbgt - first_days_wbgt, 1)

    peak_day = max(forecast, key=lambda x: float(x.get("wbgt", 0)))
    peak_date_str = peak_day.get("date", "")
    try:
        p_dt = datetime.strptime(peak_date_str, "%Y-%m-%d")
        peak_weekday = p_dt.strftime("%A")
    except Exception:
        peak_weekday = peak_date_str

    if diff >= 1.2:
        return f"Thermal stress is projected to escalate through {peak_weekday} (peak WBGT {peak_day.get('wbgt')}°C) before stabilizing."
    elif diff <= -1.2:
        return f"Thermal load is projected to peak early near {peak_weekday} before easing toward the end of the week."
    elif float(peak_day.get("wbgt", 0)) >= 32.0:
        return f"Sustained high thermal stress is projected across the week, peaking on {peak_weekday} with WBGT reaching {peak_day.get('wbgt')}°C."
    else:
        return f"Thermal risk remains moderate and steady across the 7-day period, with peak thermal window on {peak_weekday}."


def _get_risk_guidance(category: str) -> str:
    """Return formal administrative guidance based on the current risk category."""
    cat = (category or "").strip().lower()
    if "severe" in cat:
        return (
            "CRITICAL DIRECTIVE: Thermal stress has reached life-threatening severity. "
            "Enforce immediate cessation of non-essential outdoor labor between 11:00 AM and 4:30 PM. "
            "Mobilize civil defense and emergency medical response teams for active heat stroke triage, "
            "activate municipal cooling shelters at maximum capacity, and ensure uninterrupted power supply to primary health facilities."
        )
    elif "extreme" in cat:
        return (
            "HIGH-PRIORITY DIRECTIVE: Extreme thermal conditions pose immediate danger of heat illness. "
            "Enforce mandatory shaded hydration rest cycles for outdoor and construction workers. "
            "Deploy municipal water distribution tankers to densely populated informal settlements, transit stations, and markets, "
            "and instruct all government dispensaries to maintain stocked ORS electrolytes and cooling packs."
        )
    elif "danger" in cat:
        return (
            "OPERATIONAL ADVISORY: Hazardous thermal environment. Issue public heat health advisories "
            "via municipal broadcast channels and transit loudspeaker systems. Reschedule strenuous municipal and sanitation activities "
            "to early morning hours, and ensure primary health centers monitor pediatric and geriatric admissions for dehydration."
        )
    elif "caution" in cat:
        return (
            "MONITORING ADVISORY: Moderate thermal burden. Maintain regular municipal water kiosk operations, "
            "ensure adequate drinking water access across public transit corridors, and monitor vulnerable residential care facilities."
        )
    else:
        return (
            "ROUTINE DIRECTIVE: Thermal conditions currently remain within baseline physiological tolerances. "
            "Continue standard seasonal monitoring, maintain public water facilities, and review departmental heat action readiness."
        )


def generate_official_pdf_report(
    district_data: Dict[str, Any],
    forecast_data: List[Dict[str, Any]],
    mortality_analogue: Optional[Dict[str, Any]] = None,
    checklist: Optional[List[Dict[str, Any]]] = None,
    officer_name: Optional[str] = "Duty Officer"
) -> bytes:
    """
    Generate an official, structured, light-themed municipal PDF report.
    Returns the binary content of the generated PDF document.
    """
    buffer = io.BytesIO()

    # Standard Letter page with clean 36pt (0.5 in) margins
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    base_styles = getSampleStyleSheet()

    # Custom light professional typography palette
    style_title = ParagraphStyle(
        "DocTitle",
        parent=base_styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=17,
        leading=21,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=2
    )

    style_subtitle = ParagraphStyle(
        "DocSubtitle",
        parent=base_styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#475569"),
        spaceAfter=6
    )

    style_badge = ParagraphStyle(
        "DocBadge",
        parent=base_styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#0369a1"),
        alignment=2  # Right-aligned
    )

    style_section_heading = ParagraphStyle(
        "SectionHeading",
        parent=base_styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=8,
        spaceAfter=5
    )

    style_body = ParagraphStyle(
        "BodyTextCustom",
        parent=base_styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=4
    )

    style_bold_label = ParagraphStyle(
        "BoldLabel",
        parent=base_styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#0f172a")
    )

    style_table_header = ParagraphStyle(
        "TableHeader",
        parent=base_styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.white,
        alignment=1
    )

    style_table_cell = ParagraphStyle(
        "TableCell",
        parent=base_styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#0f172a"),
        alignment=1
    )

    style_footer = ParagraphStyle(
        "DocFooter",
        parent=base_styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=9,
        textColor=colors.HexColor("#64748b"),
        alignment=1
    )

    story = []

    # 1. Header Bar & Official Classification
    district_name = district_data.get("name") or district_data.get("district", "Chennai")
    state_name = district_data.get("state", "Tamil Nadu")
    current_time_str = _get_ist_time_str()

    header_table_data = [
        [
            Paragraph("<b>CLIMATEGUARD INDIA — OFFICIAL HEAT RISK REPORT</b>", style_title),
            Paragraph("<b>FOR OFFICIAL USE ONLY</b><br/><font color='#64748b'>MUNICIPAL DIRECTIVE</font>", style_badge)
        ],
        [
            Paragraph(f"<b>District Scope:</b> {district_name.upper()} ({state_name}) &nbsp;|&nbsp; <b>Report Generated:</b> {current_time_str}", style_subtitle),
            Paragraph(f"<b>Officer:</b> {officer_name or 'Duty Officer'}", style_badge)
        ]
    ]
    t_header = Table(header_table_data, colWidths=[400, 140])
    t_header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(t_header)

    # Thin primary accent rule
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284c7"), spaceBefore=4, spaceAfter=8))

    # 2. Current Conditions Section
    story.append(Paragraph("1. CURRENT METEOROLOGICAL & THERMAL STRESS CONDITIONS", style_section_heading))

    temp = district_data.get("temp") or district_data.get("temperature", 32.0)
    rh = district_data.get("rh") or district_data.get("humidity", 55.0)
    wind = district_data.get("wind") or district_data.get("wind_speed", 3.0)
    wbgt = district_data.get("wbgt", 29.8)
    hi = district_data.get("hi") or district_data.get("heat_index", 36.5)
    utci = district_data.get("utci", 31.0)
    category = district_data.get("category", "Caution")
    hss = district_data.get("heat_stress_score", 45)

    # Risk badge tint
    cat_upper = category.upper()
    cat_bg = "#fef2f2" if "SEVERE" in cat_upper or "EXTREME" in cat_upper else ("#fff7ed" if "DANGER" in cat_upper else "#fefce8")
    cat_text_color = "#991b1b" if "SEVERE" in cat_upper or "EXTREME" in cat_upper else ("#c2410c" if "DANGER" in cat_upper else "#854d0e")

    curr_table_data = [
        [
            Paragraph("<b>Ambient Temperature:</b>", style_bold_label),
            Paragraph(f"{temp}°C", style_body),
            Paragraph("<b>Wet-Bulb Globe Temp (WBGT):</b>", style_bold_label),
            Paragraph(f"<b>{wbgt}°C</b>", style_body)
        ],
        [
            Paragraph("<b>Relative Humidity:</b>", style_bold_label),
            Paragraph(f"{rh}%", style_body),
            Paragraph("<b>Rothfusz Heat Index:</b>", style_bold_label),
            Paragraph(f"{hi}°C", style_body)
        ],
        [
            Paragraph("<b>Wind Velocity:</b>", style_bold_label),
            Paragraph(f"{wind} m/s", style_body),
            Paragraph("<b>Universal Thermal Index (UTCI):</b>", style_bold_label),
            Paragraph(f"<b>{utci}°C</b>", style_body)
        ],
        [
            Paragraph("<b>Heat Stress Score:</b>", style_bold_label),
            Paragraph(f"{hss}/100", style_body),
            Paragraph("<b>Current Risk Category:</b>", style_bold_label),
            Paragraph(f"<font color='{cat_text_color}'><b>{category.upper()}</b></font>", style_body)
        ]
    ]

    t_curr = Table(curr_table_data, colWidths=[140, 130, 150, 120])
    t_curr.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(t_curr)
    story.append(Spacer(1, 8))

    # 3. Health Impact Analysis Section
    story.append(Paragraph("2. HEALTH IMPACT ANALYSIS & VULNERABILITY CONTEXT", style_section_heading))

    elderly = district_data.get("elderly_pct", 11.2)
    workers = district_data.get("outdoor_worker_pct", 24.5)

    if mortality_analogue and isinstance(mortality_analogue, dict):
        match_scenario = mortality_analogue.get("analogue_scenario") or (
            mortality_analogue.get("analogues", [{}])[0] if mortality_analogue.get("analogues") else {}
        )
        sim_summary = mortality_analogue.get("summary", {})
        baseline_rate = sim_summary.get("baseline_mortality_rate_per_100000", 1.8)
        sim_rate = sim_summary.get("average_mortality_rate_per_100000", 2.6)
        sim_deaths = sim_summary.get("average_simulated_deaths", 3.4)
        match_date = match_scenario.get("date", "Summer 2025 Analogue")
        match_state = match_scenario.get("state", state_name)
        match_wbgt = match_scenario.get("wbgt_c", 30.5)
        match_temp = match_scenario.get("maximum_temperature_c", 37.0)

        health_text = (
            f"<b>Historical Thermal Scenario Match:</b> Calibrated against analogous heat conditions from "
            f"<b>{match_date} ({match_state})</b> with historical peak ambient {match_temp}°C and WBGT {match_wbgt}°C. "
            f"Under sustained exposure equivalent to this scenario, simulated research models indicate an elevated heat-health burden with "
            f"an estimated <b>{sim_rate} per 100,000</b> projected heat-related mortality rate (baseline: {baseline_rate}/100k, "
            f"approx. {sim_deaths} daily statistical casualties across comparable municipal catchments)."
        )
    else:
        health_text = (
            "Historical synthetic analogue matching indicates baseline thermal risk for this geographic zone. "
            "Elderly cohorts and outdoor unorganized labor remain the primary vulnerable groups requiring prioritized municipal protection."
        )

    demographic_text = (
        f"<b>Demographic Exposure Profile:</b> Senior population (aged 60+): <b>{elderly}%</b> | "
        f"Outdoor / informal labor workforce: <b>{workers}%</b>. "
        f"Vulnerability is concentrated among daily-wage construction laborers, agricultural workers, delivery couriers, and elders without active indoor air cooling."
    )

    story.append(Paragraph(health_text, style_body))
    story.append(Paragraph(demographic_text, style_body))
    story.append(Spacer(1, 6))

    # 4. 7-Day Forecast Section
    story.append(Paragraph("3. 7-DAY THERMAL TRAJECTORY FORECAST", style_section_heading))

    # Trend summary
    trend_summary = _derive_forecast_trend_summary(forecast_data)
    story.append(Paragraph(f"<b>Trajectory Summary:</b> {trend_summary}", style_body))
    story.append(Spacer(1, 4))

    # Forecast Table
    fc_headers = [
        Paragraph("<b>Date / Day</b>", style_table_header),
        Paragraph("<b>Max Temp</b>", style_table_header),
        Paragraph("<b>WBGT</b>", style_table_header),
        Paragraph("<b>UTCI</b>", style_table_header),
        Paragraph("<b>Heat Index</b>", style_table_header),
        Paragraph("<b>Risk Tier</b>", style_table_header)
    ]
    fc_table_rows = [fc_headers]

    for d in forecast_data[:7]:
        d_str = d.get("date", "")
        try:
            parsed_dt = datetime.strptime(d_str, "%Y-%m-%d")
            label_date = parsed_dt.strftime("%a, %d %b")
        except Exception:
            label_date = d_str

        t_max = d.get("temp_max") or d.get("temp", "—")
        w_val = d.get("wbgt", "—")
        u_val = d.get("utci", "—")
        h_val = d.get("hi") or d.get("heat_index", "—")
        cat_val = d.get("category", "Low")

        fc_table_rows.append([
            Paragraph(label_date, style_table_cell),
            Paragraph(f"{t_max}°C", style_table_cell),
            Paragraph(f"<b>{w_val}°C</b>", style_table_cell),
            Paragraph(f"{u_val}°C", style_table_cell),
            Paragraph(f"{h_val}°C", style_table_cell),
            Paragraph(f"<b>{cat_val}</b>", style_table_cell)
        ])

    t_fc = Table(fc_table_rows, colWidths=[95, 85, 85, 85, 95, 95])
    t_fc.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0284c7")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t_fc)
    story.append(Spacer(1, 8))

    # 5. Actions Taken & Directive Checklist Section
    story.append(Paragraph("4. MUNICIPAL HEAT ACTION PLAN DIRECTIVES & ACTIONS TAKEN", style_section_heading))

    checklist_items = checklist or []
    completed_actions = [item for item in checklist_items if item.get("checked")]
    pending_actions = [item for item in checklist_items if not item.get("checked")]

    if completed_actions:
        story.append(Paragraph("<b>The duty officer has completed the following actions:</b>", style_body))
        for act in completed_actions:
            lbl = act.get("label", "Municipal Directive Action")
            by = act.get("checkedBy") or officer_name or "Duty Officer"
            at_raw = act.get("checkedAt")
            if at_raw:
                try:
                    dt_obj = datetime.fromisoformat(at_raw.replace("Z", "+00:00"))
                    at_str = _get_ist_time_str(dt_obj)
                except Exception:
                    at_str = str(at_raw)
            else:
                at_str = current_time_str

            story.append(Paragraph(
                f"&nbsp;&nbsp;•&nbsp;&nbsp;<b>[COMPLETED]</b> {lbl} &nbsp;&mdash;&nbsp; <i>Completed by {by} at {at_str}</i>",
                style_body
            ))
    else:
        story.append(Paragraph("<i>No actions have been verified as completed yet for the current duty shift.</i>", style_body))

    if pending_actions:
        story.append(Spacer(1, 3))
        story.append(Paragraph("<b>Pending actions:</b>", style_body))
        for act in pending_actions:
            lbl = act.get("label", "Municipal Directive Action")
            story.append(Paragraph(
                f"&nbsp;&nbsp;•&nbsp;&nbsp;<font color='#b45309'><b>[PENDING]</b></font> {lbl}",
                style_body
            ))

    story.append(Spacer(1, 8))

    # 6. Recommended Next Steps
    story.append(Paragraph("5. RECOMMENDED NEXT STEPS & OPERATIONAL DIRECTIVES", style_section_heading))
    guidance = _get_risk_guidance(category)
    story.append(Paragraph(guidance, style_body))
    story.append(Spacer(1, 10))

    # 7. Document Footer
    story.append(HRFlowable(width="100%", thickness=0.75, color=colors.HexColor("#e2e8f0"), spaceBefore=4, spaceAfter=6))
    story.append(Paragraph(
        f"Generated by ClimateGuard India Early Warning System &bull; Operational Report ID: CG-REP-{district_data.get('id', 'DIST').upper()}-{datetime.utcnow().strftime('%Y%m%d%H%M')} &bull; Strictly for Official Government and Civil Defense Use",
        style_footer
    ))

    # Build the PDF into the buffer
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
