import streamlit as st
import requests
from config import BACKEND_URL

def _fetch_user_reports(user_id: str):
    """Fetch user reports from backend for accurate profile metrics."""
    try:
        url = f"{BACKEND_URL.rstrip('/')}/reports/{user_id}"
        resp = requests.get(url, timeout=6)
        if resp.status_code == 200:
            return resp.json()
        return []
    except Exception:
        return []

def render_profile_page():
    """Render Athlete Profile Page."""
    user = st.session_state.get("user") or {}
    user_id = user.get("_id", "anonymous")
    
    # Merge DB reports and in-session history
    db_reports = _fetch_user_reports(user_id) or []
    session_history = st.session_state.get("report_history", [])
    
    all_reports = list(db_reports)
    db_ids = {str(r.get("id", "")) for r in all_reports} | {str(r.get("_id", "")) for r in all_reports}
    for sr in session_history:
        sr_id = str(sr.get("id", ""))
        if sr_id and sr_id not in db_ids:
            all_reports.append(sr)

    total_analyses = len(all_reports)
    if all_reports:
        scores = [r.get("overall_score", 0) for r in all_reports if r.get("overall_score") is not None]
        highest_score = max(scores) if scores else "N/A"
        
        # Calculate lowest scoring metric as actual focus area
        focus_counts = {}
        for r in all_reports:
            metrics = r.get("metrics", {})
            if metrics and isinstance(metrics, dict):
                lowest_metric = min(metrics.items(), key=lambda x: x[1])[0]
                focus_counts[lowest_metric] = focus_counts.get(lowest_metric, 0) + 1
        
        if focus_counts:
            top_focus = max(focus_counts.items(), key=lambda x: x[1])[0].replace("_", " ").title()
        else:
            top_focus = "General Biomechanics"
    else:
        highest_score = "N/A"
        top_focus = "General Conditioning"
    
    st.markdown(
        """
        <div style="margin-bottom: 24px;">
            <h1 style="font-size: 2.2rem; font-weight: 900; margin: 0; color: #FFFFFF;">
                👤 Athlete Profile
            </h1>
            <p style="font-size: 1.05rem; color: #94A3B8; margin-top: 6px;">
                Manage your profile details and view high-level performance metrics from real analyses.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    col1, col2 = st.columns([1, 2], gap="large")
    
    with col1:
        with st.container(border=True):
            st.html(
                f"""
                <div style="text-align: center; padding: 12px 0;">
                    <div style="width: 84px; height: 84px; border-radius: 50%; background: linear-gradient(135deg, #06B6D4, #3B82F6); margin: 0 auto 14px auto; display: flex; justify-content: center; align-items: center; font-size: 2.3rem; color: white; box-shadow: 0 8px 20px rgba(6, 182, 212, 0.3);">
                        🏏
                    </div>
                    <h3 style="color: #FFFFFF; font-weight: 800; margin: 0 0 4px 0;">{user.get('name', 'Athlete')}</h3>
                    <p style="color: #06B6D4; font-size: 0.85rem; font-weight: 600; margin: 0 0 12px 0;">Cricket Athlete</p>
                    <div style="background: rgba(30, 41, 59, 0.6); padding: 8px 12px; border-radius: 12px; font-size: 0.8rem; color: #94A3B8; word-break: break-all;">
                        {user.get('email', 'Not logged in')}
                    </div>
                </div>
                """
            )
        
    with col2:
        with st.container(border=True):
            st.html(
                """
                <h4 style="color: #F8FAFC; margin: 0 0 16px 0; font-size: 1.15rem; font-weight: 800;">
                    🏅 ATHLETE STATS OVERVIEW
                </h4>
                """
            )
            
            sc1, sc2 = st.columns(2)
            with sc1:
                with st.container(border=True):
                    st.metric(label="Total Video Analyses", value=total_analyses)
                with st.container(border=True):
                    st.metric(label="Stance / Discipline", value=user.get('preferred_activity', 'Cricket Athlete'))
            with sc2:
                with st.container(border=True):
                    val_str = f"{highest_score}/100" if highest_score != "N/A" else "N/A"
                    st.metric(label="Highest Fitness Score", value=val_str)
                with st.container(border=True):
                    st.metric(label="Primary Focus Area", value=top_focus)

