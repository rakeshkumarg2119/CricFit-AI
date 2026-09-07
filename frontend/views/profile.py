import streamlit as st

def render_profile_page():
    """Render Athlete Profile Page."""
    user = st.session_state.get("user") or {}
    history = st.session_state.get("report_history", [])
    
    total_analyses = len(history)
    if history:
        scores = [r.get("overall_score", 0) for r in history if r.get("overall_score") is not None]
        highest_score = max(scores) if scores else "N/A"
        
        # Calculate lowest scoring metric as actual focus area
        focus_counts = {}
        for r in history:
            metrics = r.get("metrics", {})
            if metrics:
                lowest_metric = min(metrics.items(), key=lambda x: x[1])[0]
                focus_counts[lowest_metric] = focus_counts.get(lowest_metric, 0) + 1
        
        if focus_counts:
            top_focus = max(focus_counts.items(), key=lambda x: x[1])[0].replace("_", " ").title()
        else:
            top_focus = "General Biomechanics"
    else:
        highest_score = "N/A"
        top_focus = "N/A"
    
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
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown(
            f"""
            <div style="background: rgba(15, 23, 42, 0.8); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 20px; padding: 28px; text-align: center;">
                <div style="width: 90px; height: 90px; border-radius: 50%; background: linear-gradient(135deg, #06B6D4, #3B82F6); margin: 0 auto 16px auto; display: flex; justify-content: center; align-items: center; font-size: 2.5rem; color: white; box-shadow: 0 8px 20px rgba(6, 182, 212, 0.3);">
                    🏏
                </div>
                <h3 style="color: #FFFFFF; font-weight: 800; margin: 0 0 4px 0;">{user.get('name', 'Athlete')}</h3>
                <p style="color: #06B6D4; font-size: 0.85rem; font-weight: 600; margin: 0 0 12px 0;">Cricket Athlete</p>
                <div style="background: rgba(30, 41, 59, 0.6); padding: 8px 14px; border-radius: 12px; font-size: 0.8rem; color: #94A3B8;">
                    {user.get('email', 'Not logged in')}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        
    with col2:
        score_display = f"{highest_score} <span style='font-size: 0.8rem; color: #64748B;'>/100</span>" if highest_score != "N/A" else "N/A"
        
        st.markdown(
            f"""
            <div style="background: rgba(15, 23, 42, 0.8); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 20px; padding: 28px;">
                <h4 style="color: #F8FAFC; margin: 0 0 20px 0; font-size: 1.2rem; font-weight: 800;">
                    🏅 ATHLETE STATS OVERVIEW
                </h4>
                
                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px;">
                    <div style="background: rgba(30, 41, 59, 0.6); padding: 18px; border-radius: 14px;">
                        <span style="font-size: 0.8rem; color: #94A3B8;">Total Video Analyses</span>
                        <div style="font-size: 1.8rem; font-weight: 900; color: #06B6D4; margin-top: 4px;">{total_analyses}</div>
                    </div>
                    
                    <div style="background: rgba(30, 41, 59, 0.6); padding: 18px; border-radius: 14px;">
                        <span style="font-size: 0.8rem; color: #94A3B8;">Highest Fitness Score</span>
                        <div style="font-size: 1.8rem; font-weight: 900; color: #10B981; margin-top: 4px;">{score_display}</div>
                    </div>
                    
                    <div style="background: rgba(30, 41, 59, 0.6); padding: 18px; border-radius: 14px;">
                        <span style="font-size: 0.8rem; color: #94A3B8;">Stance</span>
                        <div style="font-size: 1.1rem; font-weight: 700; color: #F8FAFC; margin-top: 6px;">{user.get('preferred_activity', 'Cricket Athlete')}</div>
                    </div>
                    
                    <div style="background: rgba(30, 41, 59, 0.6); padding: 18px; border-radius: 14px;">
                        <span style="font-size: 0.8rem; color: #94A3B8;">Primary Focus Area</span>
                        <div style="font-size: 1.1rem; font-weight: 700; color: #F59E0B; margin-top: 6px;">{top_focus}</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
