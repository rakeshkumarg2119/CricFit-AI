import streamlit as st
import requests
from components.report_card import render_saved_report_card
from components.report_view import render_full_report_view
from utils.session import navigate_to
from config import PAGES, BACKEND_URL


# ─────────────────────────────────────────────────────────────────────────────
# Helper fetchers
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_fitness_reports(user_id: str):
    """Fetch fitness reports from backend (MongoDB-backed)."""
    try:
        url = f"{BACKEND_URL.rstrip('/')}/reports/{user_id}"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        return None
    except Exception:
        return None


def _fetch_injury_reports(user_id: str):
    """Fetch injury reports from backend."""
    try:
        url = f"{BACKEND_URL.rstrip('/')}/injury/reports/{user_id}"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        return None
    except Exception:
        return None


def _delete_fitness_report(user_id: str, report_id: str) -> bool:
    """Send DELETE request to backend to remove a fitness report."""
    try:
        url = f"{BACKEND_URL.rstrip('/')}/reports/{user_id}/{report_id}"
        resp = requests.delete(url, timeout=8)
        return resp.status_code == 200
    except Exception:
        return False


def _format_timestamp(ts_str: str) -> str:
    """Format ISO timestamp to readable date+time string."""
    if not ts_str:
        return "Unknown date"
    try:
        from datetime import datetime
        ts_str = ts_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(ts_str)
        return dt.strftime("%d %b %Y  •  %I:%M %p UTC")
    except Exception:
        return ts_str[:16] if len(ts_str) >= 16 else ts_str


# ─────────────────────────────────────────────────────────────────────────────
# Main Page
# ─────────────────────────────────────────────────────────────────────────────

def render_reports_page():
    """Render saved reports history page."""

    # If user selected a specific report to view in detail
    if st.session_state.get("viewing_report_detail"):
        report = st.session_state.viewing_report_detail
        if st.button("⬅️ BACK TO MY REPORTS LIST", key="btn_back_reports_list"):
            st.session_state.viewing_report_detail = None
            st.rerun()
        st.markdown("<br>", unsafe_allow_html=True)
        render_full_report_view(report, on_reset_callback=lambda: st.session_state.update({"viewing_report_detail": None}))
        return

    # Page Header
    st.markdown(
        """
        <div style="margin-bottom: 28px;">
            <h1 style="font-size: 2.2rem; font-weight: 900; margin: 0; color: #FFFFFF;">
                📊 My Reports
            </h1>
            <p style="font-size: 1.05rem; color: #94A3B8; margin-top: 6px;">
                Your complete history of AI fitness and injury screening reports — with timestamps, PDF downloads and delete options.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    tab1, tab2 = st.tabs(["🏏 Fitness Reports", "🩺 Injury Reports"])

    # ─────────────────────────────────────────
    # TAB 1: Fitness Reports (MongoDB + session fallback)
    # ─────────────────────────────────────────
    with tab1:
        user_id = st.session_state.get("user", {}).get("_id", "anonymous")

        # Try to fetch from MongoDB via backend
        db_reports = _fetch_fitness_reports(user_id)

        # Merge in-session history (local, for reports made this session but not yet in DB)
        session_history = st.session_state.get("report_history", [])

        if db_reports is None and not session_history:
            # Backend completely unreachable
            st.warning("⚠️ Could not connect to the reports service. Please ensure the backend is running.")
            if st.button("🔄 Retry", key="btn_retry_fitness"):
                st.rerun()

        elif (db_reports is not None and len(db_reports) == 0) and len(session_history) == 0:
            # No reports at all
            st.markdown(
                """
                <div style="border: 1px dashed rgba(255,255,255,0.15); border-radius: 20px; padding: 50px 40px; text-align: center; background: rgba(15,23,42,0.4); margin: 30px 0;">
                    <div style="font-size: 3.5rem; margin-bottom: 14px;">📁</div>
                    <h3 style="color: #F8FAFC; margin: 0 0 10px 0; font-weight: 800;">No fitness reports yet</h3>
                    <p style="color: #94A3B8; font-size: 0.95rem; max-width: 500px; margin: 0 auto 28px auto;">
                        Upload a batting, bowling, or Yo-Yo test video to generate your first AI biomechanics report.
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("🏏 Analyze Batting", key="btn_rep_empty_batting", type="primary"):
                    navigate_to(PAGES["BATTING"], activity="batting")
            with c2:
                if st.button("🏃 Analyze Bowling", key="btn_rep_empty_bowling", type="primary"):
                    navigate_to(PAGES["BOWLING"], activity="bowling")
            with c3:
                if st.button("⏱️ Analyze Yo-Yo Test", key="btn_rep_empty_yoyo", type="primary"):
                    navigate_to(PAGES["YOYO"], activity="yoyo")


        else:
            # Combine: prefer DB reports, append any session-only records not already in DB
            all_reports = list(db_reports or [])

            # Supplement with any session history reports that aren't already in DB
            db_ids = {str(r.get("id", "")) for r in all_reports} | {str(r.get("_id", "")) for r in all_reports}
            for sr in session_history:
                sr_id = str(sr.get("id", ""))
                if sr_id and sr_id not in db_ids:
                    all_reports.append(sr)

            # ── Header controls ───────────────────────────────────────────────
            hdr_col1, hdr_col2 = st.columns([5, 1])
            with hdr_col1:
                st.markdown(
                    f"<p style='color: #06B6D4; font-weight: 700; margin-bottom: 20px;'>"
                    f"Showing <strong>{len(all_reports)}</strong> saved fitness analysis report(s):</p>",
                    unsafe_allow_html=True
                )
            with hdr_col2:
                if st.button("🗑️ Clear All", key="btn_clear_all_reports", help="Remove all session reports (MongoDB records must be deleted individually)"):
                    st.session_state.report_history = []
                    st.toast("Session history cleared. MongoDB records still exist.")
                    st.rerun()

            # ── Report cards ──────────────────────────────────────────────────
            def on_view(rep):
                st.session_state.viewing_report_detail = rep
                st.rerun()

            def on_delete(rep_id):
                deleted = _delete_fitness_report(user_id, rep_id)
                if deleted:
                    # Also remove from session history if present
                    st.session_state.report_history = [
                        r for r in st.session_state.get("report_history", [])
                        if str(r.get("id", "")) != str(rep_id) and str(r.get("_id", "")) != str(rep_id)
                    ]
                    st.toast(f"✅ Report {rep_id} deleted successfully.")
                else:
                    # Still remove from session even if DB delete failed (it's a session-only record)
                    prev_len = len(st.session_state.get("report_history", []))
                    st.session_state.report_history = [
                        r for r in st.session_state.get("report_history", [])
                        if str(r.get("id", "")) != str(rep_id) and str(r.get("_id", "")) != str(rep_id)
                    ]
                    if len(st.session_state.get("report_history", [])) < prev_len:
                        st.toast(f"✅ Session report removed.")
                    else:
                        st.toast(f"⚠️ Could not delete report from database.", icon="⚠️")
                st.rerun()

            for report in all_reports:
                render_saved_report_card(report, on_view_click=on_view, on_delete_click=on_delete)

    # ─────────────────────────────────────────
    # TAB 2: Injury Reports
    # ─────────────────────────────────────────
    with tab2:
        user_id = st.session_state.get("user", {}).get("_id", "anonymous")
        injury_reports = _fetch_injury_reports(user_id)

        if injury_reports is None:
            st.error("Unable to connect to the injury analysis service right now.")
            if st.button("Try Again", key="btn_injury_report_retry"):
                st.rerun()
        elif len(injury_reports) == 0:
            st.markdown(
                """
                <div style="border: 1px dashed rgba(255,255,255,0.15); border-radius: 20px; padding: 50px 40px; text-align: center; background: rgba(15,23,42,0.4); margin: 30px 0;">
                    <div style="font-size: 3.5rem; margin-bottom: 14px;">🩺</div>
                    <h3 style="color: #F8FAFC; margin: 0 0 10px 0; font-weight: 800;">No injury screenings yet</h3>
                    <p style="color: #94A3B8; font-size: 0.95rem; max-width: 500px; margin: 0 auto 28px auto;">
                        Use the Injury Detection feature to screen your symptoms and track your history here.
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )
            if st.button("🩺 Check For Injury", key="btn_rep_go_injury", type="primary"):
                navigate_to(PAGES["INJURY_DETECTION"])

        else:
            stage_labels = {1: "Minor", 2: "Moderate", 3: "Significant", 4: "HIGH-RISK / URGENT"}
            stage_colors = {1: "#10B981", 2: "#F59E0B", 3: "#F97316", 4: "#EF4444"}

            st.markdown(
                f"<p style='color: #06B6D4; font-weight: 700; margin-bottom: 20px;'>Showing <strong>{len(injury_reports)}</strong> past injury screening(s):</p>",
                unsafe_allow_html=True
            )

            for rep in injury_reports:
                result = rep.get("analysis_result", {})
                stage = rep.get("stage", 1)
                color = stage_colors.get(stage, "#94A3B8")
                label = stage_labels.get(stage, "Unknown")
                condition = result.get("possible_condition", "Unknown")
                raw_ts = rep.get("created_at", "")
                ts_display = _format_timestamp(raw_ts) if raw_ts else "Unknown date"

                st.markdown(
                    f"""
                    <div style="background: rgba(15,23,42,0.7); border: 1px solid rgba(255,255,255,0.08);
                                border-left: 4px solid {color}; border-radius: 14px;
                                padding: 20px 24px; margin-bottom: 16px;">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px;">
                            <div>
                                <span style="color: #64748B; font-size: 0.77rem; font-weight: 700; letter-spacing: 0.4px;">
                                    🩺 INJURY SCREENING · 🕐 {ts_display}
                                </span>
                                <h4 style="color: #F8FAFC; font-size: 1.1rem; font-weight: 800; margin: 6px 0 6px 0;">
                                    Possible concern: {condition}
                                </h4>
                                <span style="background: {color}20; color: {color}; border: 1px solid {color}50;
                                             padding: 3px 10px; border-radius: 20px; font-size: 0.78rem; font-weight: 700;">
                                    Stage {stage} — {label} Concern
                                </span>
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )


