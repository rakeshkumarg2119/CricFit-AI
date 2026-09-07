import streamlit as st

def render_saved_report_card(report, on_view_click):
    """
    Render a report item card for the My Reports page.
    """
    report_id = report.get("id")
    activity = report.get("activity", "Batting").title()
    date_str = report.get("date_str", "Recent")
    overall_score = report.get("overall_score", 75)
    movement_quality = report.get("movement_quality", 80)
    
    icon = "🏏" if activity.lower() == "batting" else "🏃"
    
    st.markdown(
        f"""
        <div style="background: rgba(15, 23, 42, 0.8); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 16px; padding: 20px; margin-bottom: 16px; transition: transform 0.2s;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <div style="font-size: 1.8rem; background: rgba(30, 41, 59, 0.8); padding: 10px; border-radius: 12px;">
                        {icon}
                    </div>
                    <div>
                        <h4 style="margin: 0; color: #FFFFFF; font-size: 1.1rem; font-weight: 800;">{activity} Analysis</h4>
                        <div style="font-size: 0.8rem; color: #94A3B8;">{date_str} • ID: {report_id}</div>
                    </div>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 1.4rem; font-weight: 900; color: #06B6D4;">
                        {overall_score} <span style="font-size: 0.75rem; color: #64748B;">/100</span>
                    </div>
                    <div style="font-size: 0.75rem; color: #10B981; font-weight: 600;">Overall Fitness</div>
                </div>
            </div>
            <div style="display: flex; gap: 20px; font-size: 0.85rem; color: #CBD5E1; border-top: 1px solid rgba(255, 255, 255, 0.05); padding-top: 12px;">
                <div>Movement Quality: <strong style="color: #F8FAFC;">{movement_quality}/100</strong></div>
                <div>Risk Level: <strong style="color: #10B981;">{report.get('risk_level', 'Low')}</strong></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("👁️ View Report", key=f"view_rep_{report_id}", use_container_width=True):
            on_view_click(report)
