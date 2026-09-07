import streamlit as st
from components.score_card import render_score_card
from components.metric_card import render_metrics_grid
from components.recommendation_card import render_recommendation_card, render_strengths_and_improvements
from components.charts import render_radar_chart, render_horizontal_bar_chart
from utils.session import save_current_report, navigate_to
from config import PAGES


def render_full_report_view(report, on_reset_callback=None):
    """
    Render the complete, high-fidelity Fitness Report dashboard.
    Shared across Batting page, Bowling page, and My Reports detail viewer.
    """
    activity       = report.get("activity", "batting").title()
    date_str       = report.get("date_str", "Today")
    overall_score  = report.get("overall_score", 78)
    risk_level     = report.get("risk_level", "Low")
    metrics        = report.get("metrics", {})
    strengths      = report.get("strengths", [])
    areas_to_improve = report.get("areas_to_improve", [])
    ai_summary     = report.get("ai_summary", "")
    recommendations = report.get("recommendations", [])

    # ── Report Title ──────────────────────────────────────────────────
    st.markdown(
        """
        <h2 style="text-align:center; font-size:1.8rem; font-weight:900; color:#FFFFFF;
                   letter-spacing:-0.5px; margin-bottom:20px;">
            🏏 CRICFIT AI FITNESS REPORT
        </h2>
        """,
        unsafe_allow_html=True
    )

    # ── 1. Overall Score Card ─────────────────────────────────────────
    render_score_card(overall_score, activity=activity,
                      date_str=date_str, risk_level=risk_level)

    # ── 2. Movement Metrics ───────────────────────────────────────────
    st.markdown(
        """<h3 style="color:#F8FAFC;font-weight:800;margin:28px 0 16px 0;font-size:1.2rem;">
            📊 MOVEMENT METRICS
        </h3>""",
        unsafe_allow_html=True
    )

    chart_col, grid_col = st.columns([1, 1], gap="large")

    with chart_col:
        st.markdown(
            """<div style="background:rgba(15,23,42,0.7);border:1px solid rgba(255,255,255,0.07);
                           border-radius:16px;padding:18px;">
                <p style="color:#94A3B8;font-size:0.8rem;font-weight:700;
                           text-align:center;margin:0 0 4px 0;text-transform:uppercase;
                           letter-spacing:0.8px;">Biomechanical Radar</p>
            """,
            unsafe_allow_html=True
        )
        render_radar_chart(metrics)
        st.markdown("</div>", unsafe_allow_html=True)

    with grid_col:
        render_metrics_grid(metrics)

    # ── Horizontal Bar Chart ──────────────────────────────────────────
    st.markdown("<div style='margin-top:8px;'>", unsafe_allow_html=True)
    render_horizontal_bar_chart(metrics)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── 3. AI Insight Card ────────────────────────────────────────────
    st.markdown(
        f"""
        <div style="background:linear-gradient(135deg,rgba(6,182,212,0.12),rgba(59,130,246,0.10));
                    border:1px solid rgba(6,182,212,0.4);border-radius:18px;
                    padding:24px 28px;margin-bottom:28px;
                    box-shadow:0 4px 20px rgba(6,182,212,0.1);">
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">
                <span style="font-size:1.4rem;">🤖</span>
                <h3 style="color:#06B6D4;margin:0;font-size:1.15rem;font-weight:800;
                           text-transform:uppercase;letter-spacing:0.5px;">
                    CricFit AI Insight
                </h3>
            </div>
            <p style="color:#F1F5F9;font-size:1rem;line-height:1.65;margin:0;font-style:italic;">
                "{ai_summary}"
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # ── 4. Strengths & Weaknesses ─────────────────────────────────────
    st.markdown(
        """<h3 style="color:#F8FAFC;font-weight:800;margin-bottom:16px;font-size:1.2rem;">
            ⚡ PERFORMANCE BREAKDOWN
        </h3>""",
        unsafe_allow_html=True
    )
    render_strengths_and_improvements(strengths, areas_to_improve)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── 5. Fitness Recommendations ────────────────────────────────────
    st.markdown(
        """<h3 style="color:#F8FAFC;font-weight:800;margin-bottom:16px;font-size:1.2rem;">
            💪 PERSONALISED FITNESS PLAN
        </h3>""",
        unsafe_allow_html=True
    )

    rec_cols = st.columns(min(len(recommendations), 3)) if len(recommendations) > 1 else [st.container()]
    for idx, exercise in enumerate(recommendations):
        with rec_cols[idx % len(rec_cols)]:
            render_recommendation_card(exercise)

    st.markdown(
        """<hr style="border:0;height:1px;background:rgba(255,255,255,0.08);margin:28px 0;">""",
        unsafe_allow_html=True
    )

    # ── 6. Report Actions ─────────────────────────────────────────────
    col_act1, col_act2, col_act3 = st.columns(3)

    report_id = report.get("id", "")
    already_saved = any(
        r.get("id") == report_id
        for r in st.session_state.get("report_history", [])
    )

    with col_act1:
        if already_saved:
            st.button("✅ SAVED", key="btn_already_saved",
                      use_container_width=True, disabled=True)
        else:
            if st.button("💾 SAVE REPORT", key="btn_save_report",
                         use_container_width=True, type="primary"):
                save_current_report(report)
                st.toast("Report saved to My Reports!", icon="🎉")
                st.rerun()

    with col_act2:
        if st.button("🔄 ANALYSE ANOTHER", key="btn_another_video",
                     use_container_width=True):
            if on_reset_callback:
                on_reset_callback()

    with col_act3:
        if st.button("🏠 BACK TO HOME", key="btn_report_home",
                     use_container_width=True):
            navigate_to(PAGES["HOME"])
