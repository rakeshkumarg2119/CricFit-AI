import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from components.charts import render_progress_line_chart
from utils.session import navigate_to
from config import PAGES, BACKEND_URL


def _fetch_fitness_reports(user_id: str):
    """Fetch user's fitness analysis reports from backend (MongoDB-backed)."""
    try:
        url = f"{BACKEND_URL.rstrip('/')}/reports/{user_id}"
        resp = requests.get(url, timeout=8)
        if resp.status_code == 200:
            return resp.json()
        return []
    except Exception:
        return []


def _format_date(ts_str: str) -> str:
    """Format ISO timestamp into clean date string."""
    if not ts_str:
        return "Recent"
    try:
        ts_clean = ts_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(ts_clean)
        return dt.strftime("%d %b %Y, %I:%M %p")
    except Exception:
        return str(ts_str)[:16]


def render_progress_page():
    """Render physical fitness progression over time."""
    st.markdown(
        """
        <div style="margin-bottom: 20px;">
            <h1 style="font-size: 2.2rem; font-weight: 900; margin: 0; color: #FFFFFF;">
                📈 Progress Tracking
            </h1>
            <p style="font-size: 1rem; color: #94A3B8; margin-top: 6px;">
                Track your movement quality, biomechanical stability, and physical fitness improvements across multiple recorded sessions.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    user = st.session_state.get("user") or {}
    user_id = user.get("_id", "anonymous")

    # Fetch database reports and merge with session state
    db_reports = _fetch_fitness_reports(user_id) or []
    session_history = st.session_state.get("report_history", [])

    all_reports = list(db_reports)
    db_ids = {str(r.get("id", "")) for r in all_reports} | {str(r.get("_id", "")) for r in all_reports}
    for sr in session_history:
        sr_id = str(sr.get("id", ""))
        if sr_id and sr_id not in db_ids:
            all_reports.append(sr)

    # ── Activity Filter Control ──────────────────────────────────────────────
    filter_option = st.segmented_control(
        "Filter by Activity",
        options=["All Activities", "Batting", "Bowling", "Yo-Yo"],
        default="All Activities",
        key="prog_activity_filter",
        label_visibility="collapsed"
    )

    if filter_option == "Batting":
        filtered_reports = [r for r in all_reports if str(r.get("activity", "")).lower() == "batting"]
    elif filter_option == "Bowling":
        filtered_reports = [r for r in all_reports if str(r.get("activity", "")).lower() == "bowling"]
    elif filter_option == "Yo-Yo":
        filtered_reports = [r for r in all_reports if "yoyo" in str(r.get("activity", "")).lower()]
    else:
        filtered_reports = all_reports

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # ── CASE 0: No Reports Found ─────────────────────────────────────────────
    if len(filtered_reports) == 0:
        with st.container(border=True):
            st.markdown(
                f"""
                <div style="text-align: center; padding: 36px 20px;">
                    <div style="font-size: 3rem; margin-bottom: 12px;">📊</div>
                    <h3 style="color: #F8FAFC; margin: 0 0 8px 0; font-weight: 800;">
                        No analysis records found for {filter_option}
                    </h3>
                    <p style="color: #94A3B8; font-size: 0.95rem; max-width: 520px; margin: 0 auto 24px auto;">
                        Record or upload video sessions to start tracking your performance trajectory, score improvements, and kinetic stability over time.
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("🏏 Analyze Batting Video", key="btn_prog_empty_batting", type="primary"):
                    navigate_to(PAGES["BATTING"], activity="batting")
            with col2:
                if st.button("🏃 Analyze Bowling Video", key="btn_prog_empty_bowling", type="primary"):
                    navigate_to(PAGES["BOWLING"], activity="bowling")
            with col3:
                if st.button("⏱️ Start Yo-Yo Test", key="btn_prog_empty_yoyo", type="primary"):
                    navigate_to(PAGES["YOYO"], activity="yoyo")
        return

    # ── CASE 1: Exactly 1 Report (Baseline Only) ─────────────────────────────
    if len(filtered_reports) == 1:
        rep = filtered_reports[0]
        score = rep.get("overall_score", 0)
        mov_qual = rep.get("movement_quality", 0)
        risk = rep.get("risk_level", "Low")
        act = rep.get("activity", "Session").title()

        with st.container(border=True):
            st.markdown(
                f"""
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; flex-wrap: wrap; gap: 10px;">
                    <div>
                        <span style="background: rgba(6,182,212,0.15); color: #06B6D4; border: 1px solid rgba(6,182,212,0.3); padding: 4px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 700;">
                            BASELINE ESTABLISHED
                        </span>
                        <h3 style="color: #FFFFFF; font-size: 1.4rem; font-weight: 800; margin: 8px 0 2px 0;">
                            First {act} Session Recorded
                        </h3>
                        <p style="color: #94A3B8; font-size: 0.88rem; margin: 0;">
                            Recorded: {_format_date(rep.get('saved_at') or rep.get('timestamp', ''))}
                        </p>
                    </div>
                    <div style="text-align: center; background: rgba(6,182,212,0.1); border: 1px solid rgba(6,182,212,0.25); border-radius: 14px; padding: 10px 22px;">
                        <div style="font-size: 2rem; font-weight: 900; color: #06B6D4;">{score}<span style="font-size: 0.85rem; color: #64748B;">/100</span></div>
                        <div style="font-size: 0.72rem; color: #94A3B8; font-weight: 600;">Baseline Score</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            k1, k2, k3 = st.columns(3)
            with k1:
                with st.container(border=True):
                    st.metric("Overall Score", f"{score}/100")
            with k2:
                with st.container(border=True):
                    st.metric("Movement Quality", f"{mov_qual}/100")
            with k3:
                with st.container(border=True):
                    st.metric("Injury Risk Level", risk)

            st.info("💡 Complete 1 more video analysis to unlock multi-session progress graphs, comparative trajectory charts, and improvement delta metrics!")
        return

    # ── CASE 2: Multiple Reports (Progress Tracking Unlocked!) ────────────────
    latest = filtered_reports[0]
    earliest = filtered_reports[-1]
    latest_score = latest.get("overall_score", 0)
    earliest_score = earliest.get("overall_score", 0)
    score_diff = latest_score - earliest_score

    highest_score = max((r.get("overall_score", 0) for r in filtered_reports), default=0)
    latest_mq = latest.get("movement_quality", 0)
    earliest_mq = earliest.get("movement_quality", 0)
    mq_diff = latest_mq - earliest_mq

    delta_color = "#10B981" if score_diff >= 0 else "#EF4444"
    delta_sign = "+" if score_diff >= 0 else ""

    # ── 1. KPI Summary Cards ─────────────────────────────────────────────────
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        with st.container(border=True):
            st.metric(
                label="Total Sessions",
                value=f"{len(filtered_reports)} recorded",
                help="Total number of completed video analyses in this category."
            )
    with kpi2:
        with st.container(border=True):
            st.metric(
                label="Latest Score",
                value=f"{latest_score}/100",
                delta=f"{delta_sign}{score_diff} vs baseline" if len(filtered_reports) >= 2 else None,
            )
    with kpi3:
        with st.container(border=True):
            st.metric(
                label="Movement Quality",
                value=f"{latest_mq}/100",
                delta=f"{'+' if mq_diff >= 0 else ''}{mq_diff} pts",
            )
    with kpi4:
        with st.container(border=True):
            st.metric(
                label="Highest Score",
                value=f"{highest_score}/100",
                help="Your personal best fitness score recorded to date."
            )

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # ── 2. Score Trajectory Over Time Chart ──────────────────────────────────
    with st.container(border=True):
        st.markdown(
            """
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <div>
                    <h3 style="color: #FFFFFF; font-size: 1.25rem; font-weight: 800; margin: 0;">
                        📈 Multi-Session Biomechanical Trajectory
                    </h3>
                    <p style="color: #94A3B8; font-size: 0.85rem; margin: 4px 0 0 0;">
                        Evolution of Overall Score, Movement Quality, Balance, Mobility &amp; Stability across sessions.
                    </p>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        # Note: render_progress_line_chart expects list sorted newest-first and internally reverses it
        render_progress_line_chart(filtered_reports)

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # ── 3. Session-by-Session Comparison Breakdown ───────────────────────────
    with st.container(border=True):
        st.markdown(
            """
            <h3 style="color: #FFFFFF; font-size: 1.25rem; font-weight: 800; margin: 0 0 14px 0;">
                📋 Session History Breakdown
            </h3>
            """,
            unsafe_allow_html=True
        )

        table_data = []
        for idx, rep in enumerate(filtered_reports):
            rep_id = rep.get("id") or rep.get("_id", "N/A")
            activity = rep.get("activity", "Unknown").title()
            date_str = _format_date(rep.get("saved_at") or rep.get("timestamp", ""))
            ov_score = rep.get("overall_score", 0)
            mq = rep.get("movement_quality", 0)
            risk = rep.get("risk_level", "Low")

            table_data.append({
                "Session": f"Session #{len(filtered_reports) - idx}",
                "Activity": activity,
                "Date": date_str,
                "Overall Score": f"{ov_score}/100",
                "Movement Quality": f"{mq}/100",
                "Risk Level": risk,
                "Report ID": rep_id
            })

        df_display = pd.DataFrame(table_data)
        st.dataframe(
            df_display,
            hide_index=True,
            column_config={
                "Session": st.column_config.TextColumn("Session", width="small"),
                "Activity": st.column_config.TextColumn("Activity", width="small"),
                "Date": st.column_config.TextColumn("Recorded Date", width="medium"),
                "Overall Score": st.column_config.TextColumn("Overall Score", width="small"),
                "Movement Quality": st.column_config.TextColumn("Movement Quality", width="small"),
                "Risk Level": st.column_config.TextColumn("Injury Risk", width="small"),
                "Report ID": st.column_config.TextColumn("Report ID", width="medium"),
            }
        )

