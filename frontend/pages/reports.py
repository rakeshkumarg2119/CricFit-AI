import streamlit as st
import requests
from components.report_card import render_saved_report_card
from components.report_view import render_full_report_view
from utils.session import navigate_to
from config import PAGES, BACKEND_URL

def fetch_injury_reports(user_id):
    """Fetch injury reports from FastAPI backend."""
    try:
        url = f"{BACKEND_URL.rstrip('/')}/injury/reports/{user_id}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception:
        return None  # None signals a connection error

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

    st.markdown(
        """
        <div style="margin-bottom: 24px;">
            <h1 style="font-size: 2.2rem; font-weight: 900; margin: 0; color: #FFFFFF;">
                📊 My Reports
            </h1>
            <p style="font-size: 1.05rem; color: #94A3B8; margin-top: 6px;">
                Review and track your saved AI fitness and injury screening reports.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    tab1, tab2 = st.tabs(["🏏 Fitness Reports", "🩺 Injury Reports"])

    # ─────────────────────────────────────────
    # TAB 1: Fitness Reports
    # ─────────────────────────────────────────
    with tab1:
        history = st.session_state.get("report_history", [])
        
        if not history or len(history) == 0:
            st.markdown(
                """
                <div style="border: 1px dashed rgba(255, 255, 255, 0.15); border-radius: 20px; padding: 40px; text-align: center; background: rgba(15, 23, 42, 0.4); margin: 30px 0;">
                    <div style="font-size: 3.5rem; margin-bottom: 12px;">📁</div>
                    <h3 style="color: #F8FAFC; margin: 0 0 8px 0; font-weight: 800;">No fitness reports yet.</h3>
                    <p style="color: #94A3B8; font-size: 0.95rem; max-width: 500px; margin: 0 auto 24px auto;">
                        Upload a batting or bowling video to create your first real AI report.
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🏏 Analyze Batting Movement", key="btn_rep_empty_batting", use_container_width=True, type="primary"):
                    navigate_to(PAGES["BATTING"], activity="batting")
            with col2:
                if st.button("🏃 Analyze Bowling Movement", key="btn_rep_empty_bowling", use_container_width=True, type="primary"):
                    navigate_to(PAGES["BOWLING"], activity="bowling")
        else:
            st.markdown(f"<p style='color: #06B6D4; font-weight: 700;'>Showing {len(history)} saved fitness analysis report(s):</p>", unsafe_allow_html=True)
            
            def set_view_detail(rep):
                st.session_state.viewing_report_detail = rep
                st.rerun()
                
            for report in history:
                render_saved_report_card(report, on_view_click=set_view_detail)
                
            if st.button("🗑️ Clear Reports History", key="btn_clear_history"):
                st.session_state.report_history = []
                st.toast("Report history cleared.")
                st.rerun()

    # ─────────────────────────────────────────
    # TAB 2: Injury Reports (from MongoDB)
    # ─────────────────────────────────────────
    with tab2:
        user_id = st.session_state.get("user", {}).get("_id", "anonymous")
        injury_reports = fetch_injury_reports(user_id)

        if injury_reports is None:
            st.error("Unable to connect to the injury analysis service right now.")
            if st.button("Try Again", key="btn_injury_report_retry"):
                st.rerun()
        elif len(injury_reports) == 0:
            st.markdown(
                """
                <div style="border: 1px dashed rgba(255, 255, 255, 0.15); border-radius: 20px; padding: 40px; text-align: center; background: rgba(15, 23, 42, 0.4); margin: 30px 0;">
                    <div style="font-size: 3.5rem; margin-bottom: 12px;">🩺</div>
                    <h3 style="color: #F8FAFC; margin: 0 0 8px 0; font-weight: 800;">No injury screenings yet.</h3>
                    <p style="color: #94A3B8; font-size: 0.95rem; max-width: 500px; margin: 0 auto 24px auto;">
                        Use the Injury Detection feature to screen your symptoms and track your history here.
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )
            if st.button("🩺 Check For Injury", key="btn_rep_go_injury", use_container_width=True, type="primary"):
                navigate_to(PAGES["INJURY_DETECTION"])
        else:
            stage_labels = {1: "Minor", 2: "Moderate", 3: "Significant", 4: "HIGH-RISK / URGENT"}
            stage_colors = {1: "#10B981", 2: "#F59E0B", 3: "#F97316", 4: "#EF4444"}

            st.markdown(f"<p style='color: #06B6D4; font-weight: 700;'>Showing {len(injury_reports)} past injury screening(s):</p>", unsafe_allow_html=True)

            for rep in injury_reports:
                result = rep.get("analysis_result", {})
                stage = rep.get("stage", 1)
                color = stage_colors.get(stage, "#94A3B8")
                label = stage_labels.get(stage, "Unknown")
                condition = result.get("possible_condition", "Unknown")
                created = rep.get("created_at", "")[:10] if rep.get("created_at") else "Unknown date"

                st.markdown(
                    f"""
                    <div style="background: rgba(15,23,42,0.7); border: 1px solid rgba(255,255,255,0.08);
                                border-left: 4px solid {color}; border-radius: 14px;
                                padding: 20px 24px; margin-bottom: 16px;">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px;">
                            <div>
                                <span style="color: #94A3B8; font-size: 0.78rem; font-weight: 700; letter-spacing: 0.5px;">
                                    🩺 INJURY SCREENING · {created}
                                </span>
                                <h4 style="color: #F8FAFC; font-size: 1.15rem; font-weight: 800; margin: 6px 0 4px 0;">
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
