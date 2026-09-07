"""
CRICFIT AI — Master Report View Component
=========================================
Uses st.html() (Streamlit 1.31+) for all HTML rendering — bypasses the
Markdown pipeline entirely, so no unsafe_allow_html issues.
"""

import html
import streamlit as st
from config import BACKEND_URL, PAGES
from components.score_card import render_score_card
from components.metric_card import render_metrics_grid
from components.recommendation_card import render_strengths_and_improvements
from components.charts import render_radar_chart, render_horizontal_bar_chart
from utils.session import save_current_report, navigate_to


def render_full_report_view(report, on_reset_callback=None):
    """Renders the unified, rich athlete report dashboard."""

    activity   = html.escape(str(report.get("activity", "batting")).title())
    date_str   = html.escape(str(report.get("date_str", "Today")))
    overall_score = int(report.get("overall_score", 78))
    risk_level = html.escape(str(report.get("risk_level", "Low")))
    metrics    = report.get("metrics", {})
    strengths  = report.get("strengths", [])
    areas_to_improve = report.get("areas_to_improve", [])
    ai_summary = report.get("ai_summary", "")
    technique_analysis = report.get("technique_analysis", "")
    exercises  = report.get("exercises", [])
    how_following_improves = report.get("how_following_improves", "")
    nutrition_plan = report.get("nutrition_plan", {})
    annotated_video_url = report.get("annotated_video_url")
    pdf_url    = report.get("pdf_url")
    report_id  = html.escape(str(report.get("id", "REP-001")))

    # ── Report Header ────────────────────────────────────────────────────────
    st.html(f"""
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">
        <div>
            <span style="background:rgba(6,182,212,0.15);color:#06B6D4;
                         border:1px solid rgba(6,182,212,0.4);padding:4px 12px;
                         border-radius:20px;font-size:0.8rem;font-weight:800;letter-spacing:0.5px;">
                {activity.upper()} BIOMECHANICAL REPORT
            </span>
            <h1 style="font-size:2.2rem;font-weight:900;margin:8px 0 0 0;color:#FFFFFF;">
                Athlete Movement Analysis
            </h1>
            <p style="color:#94A3B8;font-size:0.9rem;margin:4px 0 0 0;">
                ID: <b>{report_id}</b> | Analyzed: <b>{date_str}</b>
            </p>
        </div>
    </div>
    """)

    # ── Telemetry Badge ───────────────────────────────────────────────────────
    if "shot_classification" in report:
        shot = report["shot_classification"]
        shot_lbl  = html.escape(str(shot.get("label", "")).replace("_", " ").upper())
        shot_conf = round(float(shot.get("confidence", 0.0)) * 100, 1)
        st.html(f"""
        <div style="background:linear-gradient(90deg,rgba(6,182,212,0.2),rgba(59,130,246,0.1));
                    border:1px solid rgba(6,182,212,0.5);border-radius:14px;padding:14px 20px;
                    margin-bottom:20px;display:flex;align-items:center;justify-content:space-between;">
            <div>
                <span style="color:#94A3B8;font-size:0.8rem;font-weight:700;text-transform:uppercase;">
                    Detected Batting Stroke</span>
                <h3 style="color:#FFFFFF;margin:2px 0 0 0;font-size:1.3rem;font-weight:800;">
                    &#x1F3CF; {shot_lbl}</h3>
            </div>
            <div style="text-align:right;">
                <span style="color:#06B6D4;font-size:1.3rem;font-weight:900;">{shot_conf}%</span>
                <div style="color:#94A3B8;font-size:0.75rem;font-weight:600;">AI Vision Confidence</div>
            </div>
        </div>
        """)
    elif "closest_pro_match" in report:
        match    = report["closest_pro_match"]
        pro_name = match.get("player", "Pro Bowler")
        arm  = report.get("arm_classification",  {}).get("label", "").upper()
        pace = report.get("pace_classification", {}).get("label", "").upper()
        st.html(f"""
        <div style="background:linear-gradient(90deg,rgba(59,130,246,0.2),rgba(16,185,129,0.1));
                    border:1px solid rgba(59,130,246,0.5);border-radius:14px;padding:14px 20px;
                    margin-bottom:20px;display:flex;align-items:center;justify-content:space-between;">
            <div>
                <span style="color:#94A3B8;font-size:0.8rem;font-weight:700;text-transform:uppercase;">
                    Bowling Action Profile</span>
                <h3 style="color:#FFFFFF;margin:2px 0 0 0;font-size:1.3rem;font-weight:800;">
                    &#x26A1; {arm} {pace}</h3>
            </div>
            <div style="text-align:right;">
                <span style="color:#10B981;font-size:1.15rem;font-weight:800;">&#x1F3AF; {pro_name}</span>
                <div style="color:#94A3B8;font-size:0.75rem;font-weight:600;">Closest Pro Bowler Match</div>
            </div>
        </div>
        """)
    elif "shuttle_metrics" in report:
        shuttle_m  = report["shuttle_metrics"]
        shuttles   = shuttle_m.get("shuttles_detected", 0)
        trend      = shuttle_m.get("cadence_trend", "stable").upper()
        late_count = report.get("rest_compliance", {}).get("late_recovery_count", 0)
        st.html(f"""
        <div style="background:linear-gradient(90deg,rgba(245,158,11,0.2),rgba(6,182,212,0.1));
                    border:1px solid rgba(245,158,11,0.5);border-radius:14px;padding:14px 20px;
                    margin-bottom:20px;display:flex;align-items:center;justify-content:space-between;">
            <div>
                <span style="color:#94A3B8;font-size:0.8rem;font-weight:700;text-transform:uppercase;">
                    Yo-Yo Shuttle Tracking</span>
                <h3 style="color:#FFFFFF;margin:2px 0 0 0;font-size:1.3rem;font-weight:800;">
                    &#x23F1; {shuttles} Shuttles Completed</h3>
            </div>
            <div style="text-align:right;">
                <span style="color:#F59E0B;font-size:1.15rem;font-weight:800;">Cadence: {trend}</span>
                <div style="color:#94A3B8;font-size:0.75rem;font-weight:600;">Late Recoveries: {late_count}</div>
            </div>
        </div>
        """)

    # ── 1. Overall Score Card ─────────────────────────────────────────────────
    try:
        render_score_card(overall_score, activity=activity, date_str=date_str, risk_level=risk_level)
    except Exception as e:
        st.warning(f"Score card unavailable: {e}")

    # ── 2. Biomechanical Radar & Metrics Grid ─────────────────────────────────
    st.html('<h3 style="color:#F8FAFC;font-weight:800;margin:28px 0 16px 0;font-size:1.2rem;">'
            '&#x1F4CA; BIOMECHANICAL METRICS (0 \u2013 100)</h3>')

    chart_col, grid_col = st.columns([1, 1], gap="large")
    with chart_col:
        st.html('<p style="color:#94A3B8;font-size:0.8rem;font-weight:700;text-align:center;'
                'margin:0 0 4px 0;text-transform:uppercase;letter-spacing:0.8px;">Biomechanical Radar</p>')
        try:
            render_radar_chart(metrics)
        except Exception:
            st.info("Radar chart unavailable.")

    with grid_col:
        try:
            render_metrics_grid(metrics)
        except Exception as e:
            st.warning(f"Metrics grid unavailable: {e}")

    try:
        render_horizontal_bar_chart(metrics)
    except Exception:
        pass

    # ── 3. AI Plain-Language Assessment ──────────────────────────────────────
    summary_html    = html.escape(str(ai_summary or "Analysis completed."))
    technique_html  = html.escape(str(technique_analysis or ""))
    technique_block = (
        f'<p style="color:#CBD5E1;font-size:0.95rem;line-height:1.6;margin:0;'
        f'border-top:1px solid rgba(255,255,255,0.08);padding-top:10px;">'
        f'<b>Movement Detail:</b> {technique_html}</p>'
    ) if technique_html else ""

    st.html(f"""
    <div style="background:linear-gradient(135deg,rgba(6,182,212,0.12),rgba(59,130,246,0.10));
                border:1px solid rgba(6,182,212,0.45);border-radius:18px;
                padding:24px 28px;margin:28px 0;box-shadow:0 4px 20px rgba(6,182,212,0.1);">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">
            <span style="font-size:1.5rem;">&#x1F916;</span>
            <h3 style="color:#06B6D4;margin:0;font-size:1.2rem;font-weight:800;
                       text-transform:uppercase;letter-spacing:0.5px;">
                CricFit AI Plain-Language Breakdown
            </h3>
        </div>
        <p style="color:#F8FAFC;font-size:1.05rem;line-height:1.7;margin:0 0 12px 0;">{summary_html}</p>
        {technique_block}
    </div>
    """)

    if annotated_video_url:
        st.html('<h3 style="color:#F8FAFC;font-weight:800;margin-bottom:14px;font-size:1.2rem;">'
                '&#x1F4F9; AI MOVEMENT SKELETON TRACKING &amp; TELEMETRY VIDEO</h3>')
        video_full_url = f"{BACKEND_URL.rstrip('/')}{annotated_video_url}"
        try:


            col_v1, col_v2, col_v3 = st.columns([1, 2.2, 1])
            with col_v2:
                st.video(video_full_url)

        except Exception:

            st.html(f"""
            <div style="background:rgba(15,23,42,0.6);border:1px solid rgba(6,182,212,0.3);border-radius:12px;padding:14px;">
                <p style="color:#94A3B8;margin:0 0 8px 0;font-size:0.9rem;">Annotated video generated successfully:</p>
                <a href="{html.escape(video_full_url)}" target="_blank" style="color:#06B6D4;font-weight:700;">
                    &#x1F4F9; Open Annotated Video in New Tab
                </a>
            </div>
            """)

    # ── 5. Performance Breakdown ──────────────────────────────────────────────
    st.html('<h3 style="color:#F8FAFC;font-weight:800;margin-bottom:16px;font-size:1.2rem;">'
            '&#x26A1; PERFORMANCE BREAKDOWN</h3>')
    try:
        render_strengths_and_improvements(strengths, areas_to_improve)
    except Exception as e:
        st.warning(f"Performance breakdown unavailable: {e}")

    # ── 6. Fitness Drills ─────────────────────────────────────────────────────
    st.html('<h3 style="color:#F8FAFC;font-weight:800;margin:28px 0 16px 0;font-size:1.2rem;">'
            '&#x1F4AA; TARGETED CRICKET FITNESS DRILLS &amp; IMPROVEMENT MECHANICS</h3>')

    if exercises:
        num_cols = max(1, min(len(exercises), 3))
        cols = st.columns(num_cols)
        for idx, ex in enumerate(exercises):
            with cols[idx % num_cols]:
                ex_name  = html.escape(str(ex.get("exercise_name") or f"Drill {idx+1}"))
                target   = html.escape(str(ex.get("target_area") or "Biomechanics"))
                sets_reps = html.escape(str(ex.get("sets_and_reps") or "3 sets x 10 reps"))
                diff_raw = str(ex.get("difficulty") or "Intermediate")
                diff     = html.escape(diff_raw.upper())
                how_imp  = html.escape(str(ex.get("how_it_improves") or "Improves kinetic chain power."))
                st.html(f"""
                <div style="background:rgba(15,23,42,0.85);border:1px solid rgba(6,182,212,0.25);
                            border-radius:16px;padding:20px;margin-bottom:16px;">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                        <span style="background:rgba(6,182,212,0.15);color:#06B6D4;padding:2px 8px;
                                     border-radius:8px;font-size:0.75rem;font-weight:700;">{diff}</span>
                        <span style="color:#94A3B8;font-size:0.8rem;">{sets_reps}</span>
                    </div>
                    <h4 style="color:#FFFFFF;font-size:1.05rem;font-weight:800;margin:4px 0 6px 0;">{ex_name}</h4>
                    <p style="color:#06B6D4;font-size:0.8rem;font-weight:700;margin:0 0 10px 0;">
                        &#x1F3AF; Target: {target}</p>
                    <p style="color:#CBD5E1;font-size:0.85rem;line-height:1.5;margin:0;
                              border-top:1px solid rgba(255,255,255,0.06);padding-top:8px;">
                        <b>Why this works:</b> {how_imp}
                    </p>
                </div>
                """)

    if how_following_improves:
        how_fol_clean = html.escape(str(how_following_improves))
        st.html(f"""
        <div style="background:rgba(16,185,129,0.08);border:1px solid rgba(16,185,129,0.35);
                    border-radius:14px;padding:16px 20px;margin-top:14px;">
            <h5 style="color:#10B981;margin:0 0 6px 0;font-size:0.95rem;font-weight:800;">
                &#x1F680; LONG-TERM PERFORMANCE TRANSFORMATION</h5>
            <p style="color:#E2E8F0;font-size:0.9rem;line-height:1.6;margin:0;">{how_fol_clean}</p>
        </div>
        """)

    # ── 7. Nutrition Plan ─────────────────────────────────────────────────────
    if nutrition_plan and isinstance(nutrition_plan, dict):
        st.html('<h3 style="color:#F8FAFC;font-weight:800;margin:28px 0 16px 0;font-size:1.2rem;">'
                '&#x1F957; CRICKET NUTRITION &amp; RECOVERY GUIDELINES</h3>')
        nc1, nc2, nc3 = st.columns(3, gap="medium")
        pre_fuel = html.escape(str(nutrition_plan.get("pre_workout") or "Complex carbohydrates and light protein 90m before."))
        post_repair = html.escape(str(nutrition_plan.get("post_workout") or "High protein + electrolytes within 45m."))
        hydr_strategy = html.escape(str(nutrition_plan.get("hydration_strategy") or "500ml water with sodium before training."))
        with nc1:
            st.html(f"""
            <div style="background:rgba(15,23,42,0.7);border:1px solid rgba(255,255,255,0.08);
                        border-radius:14px;padding:18px;">
                <h5 style="color:#F59E0B;margin:0 0 6px 0;font-size:0.9rem;font-weight:800;">
                    &#x26A1; PRE-TRAINING FUEL</h5>
                <p style="color:#CBD5E1;font-size:0.85rem;line-height:1.5;margin:0;">
                    {pre_fuel}</p>
            </div>
            """)
        with nc2:
            st.html(f"""
            <div style="background:rgba(15,23,42,0.7);border:1px solid rgba(255,255,255,0.08);
                        border-radius:14px;padding:18px;">
                <h5 style="color:#10B981;margin:0 0 6px 0;font-size:0.9rem;font-weight:800;">
                    &#x1F969; POST-TRAINING REPAIR</h5>
                <p style="color:#CBD5E1;font-size:0.85rem;line-height:1.5;margin:0;">
                    {post_repair}</p>
            </div>
            """)
        with nc3:
            st.html(f"""
            <div style="background:rgba(15,23,42,0.7);border:1px solid rgba(255,255,255,0.08);
                        border-radius:14px;padding:18px;">
                <h5 style="color:#06B6D4;margin:0 0 6px 0;font-size:0.9rem;font-weight:800;">
                    &#x1F4A7; HYDRATION &amp; FOODS</h5>
                <p style="color:#CBD5E1;font-size:0.85rem;line-height:1.5;margin:0;">
                    {hydr_strategy}</p>
            </div>
            """)

    st.html("<hr style='border:0;height:1px;background:rgba(255,255,255,0.08);margin:28px 0;'>")

    # ── 8. Action Buttons ─────────────────────────────────────────────────────
    col_act1, col_act2, col_act3, col_act4 = st.columns(4)

    already_saved = any(
        r.get("id") == report_id
        for r in st.session_state.get("report_history", [])
    )

    with col_act1:
        if already_saved:
            st.button("✅ SAVED", key="btn_already_saved", disabled=True, use_container_width=True)
        else:
            if st.button("💾 SAVE REPORT", key="btn_save_report", type="primary", use_container_width=True):
                save_current_report(report)
                st.toast("Report saved to My Reports!", icon="🎉")
                st.rerun()

    with col_act2:
        if pdf_url:
            pdf_clean_url = html.escape(f"{BACKEND_URL.rstrip('/')}{pdf_url}")
            st.html(f"""
            <a href="{pdf_clean_url}" target="_blank" style="text-decoration:none;">
                <div style="background:linear-gradient(135deg,#0284C7,#0369A1);color:#FFFFFF;
                            font-weight:700;font-size:0.9rem;padding:11px 16px;
                            border-radius:14px;text-align:center;">
                    &#x1F4C4; DOWNLOAD PDF
                </div>
            </a>
            """)
        else:
            st.button("📄 PDF NOT READY", disabled=True, use_container_width=True)

    with col_act3:
        if st.button("🔄 ANALYSE ANOTHER", key="btn_another_video", use_container_width=True):
            if on_reset_callback:
                on_reset_callback()

    with col_act4:
        if st.button("🏠 BACK TO HOME", key="btn_report_home", use_container_width=True):
            navigate_to(PAGES["HOME"])
