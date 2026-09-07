import streamlit as st
from components.charts import render_progress_line_chart
from utils.session import navigate_to
from config import PAGES

def render_progress_page():
    """Render physical fitness progression over time."""
    st.markdown(
        """
        <div style="margin-bottom: 24px;">
            <h1 style="font-size: 2.2rem; font-weight: 900; margin: 0; color: #FFFFFF;">
                📈 Progress Tracking
            </h1>
            <p style="font-size: 1.05rem; color: #94A3B8; margin-top: 6px;">
                Track your movement quality and physical fitness improvements over multiple real analyses.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    history = st.session_state.get("report_history", [])
    
    if len(history) < 2:
        st.markdown(
            """
            <div style="border: 1px dashed rgba(255, 255, 255, 0.15); border-radius: 20px; padding: 40px; text-align: center; background: rgba(15, 23, 42, 0.4); margin: 20px 0;">
                <div style="font-size: 3.5rem; margin-bottom: 12px;">📊</div>
                <h3 style="color: #F8FAFC; margin: 0 0 8px 0; font-weight: 800;">No progress data available yet.</h3>
                <p style="color: #94A3B8; font-size: 0.95rem; max-width: 550px; margin: 0 auto 24px auto;">
                    Progress tracking requires at least 2 real saved analysis reports. Perform another video analysis to view your performance trajectory over time.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🏏 Analyze Batting Video", key="btn_prog_empty_batting", use_container_width=True, type="primary"):
                navigate_to(PAGES["BATTING"], activity="batting")
        with col2:
            if st.button("🏃 Analyze Bowling Video", key="btn_prog_empty_bowling", use_container_width=True, type="primary"):
                navigate_to(PAGES["BOWLING"], activity="bowling")
        return
        
    # Calculate progress metrics strictly from actual real reports
    latest_score = history[0].get("overall_score", 0)
    earliest_score = history[-1].get("overall_score", 0)
    diff = latest_score - earliest_score
    
    trend_color = "#10B981" if diff >= 0 else "#EF4444"
    trend_sign = "+" if diff >= 0 else ""
    
    st.markdown(
        f"""
        <div style="background: rgba(15, 23, 42, 0.8); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 16px; padding: 20px; margin-bottom: 24px; display: flex; align-items: center; justify-content: space-between;">
            <div>
                <span style="font-size: 0.8rem; color: #94A3B8; font-weight: 700; text-transform: uppercase;">FITNESS IMPROVEMENT</span>
                <h3 style="margin: 4px 0 0 0; color: #FFFFFF; font-size: 1.4rem;">
                    Your overall fitness score changed by <strong style="color: {trend_color};">{trend_sign}{diff} points</strong> across {len(history)} analyses.
                </h3>
            </div>
            <div style="background: rgba(16, 185, 129, 0.15); border: 1px solid {trend_color}; padding: 12px 20px; border-radius: 14px; text-align: center;">
                <div style="font-size: 1.8rem; font-weight: 900; color: {trend_color};">{trend_sign}{diff}</div>
                <div style="font-size: 0.75rem; color: #CBD5E1;">SCORE DELTA</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    st.markdown("<h3 style='color: #F8FAFC; font-weight: 800; margin-bottom: 16px;'>📈 SCORE TRAJECTORY OVER TIME</h3>", unsafe_allow_html=True)
    render_progress_line_chart(history)
