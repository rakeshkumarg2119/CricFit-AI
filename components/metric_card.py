import streamlit as st
from utils.helpers import get_score_status

def render_metric_card(title, score):
    """
    Render a stylized metric card with title, numerical score, progress bar,
    and textual status badge (not color alone).
    """
    status_info = get_score_status(score)
    status_text = status_info["status"]
    color = status_info["color"]
    emoji = status_info["emoji"]
    
    st.markdown(
        f"""
        <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 16px; padding: 18px; margin-bottom: 12px; backdrop-filter: blur(10px);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <div style="font-weight: 700; color: #E2E8F0; font-size: 0.95rem; display: flex; align-items: center; gap: 6px;">
                    {title}
                </div>
                <div style="font-size: 1.25rem; font-weight: 800; color: #FFFFFF;">
                    {score} <span style="font-size: 0.85rem; color: #64748B; font-weight: 500;">/100</span>
                </div>
            </div>
            
            <div style="width: 100%; background: #1E293B; height: 10px; border-radius: 10px; overflow: hidden; margin-bottom: 12px;">
                <div style="width: {score}%; background: linear-gradient(90deg, {color}, #3B82F6); height: 100%; border-radius: 10px; transition: width 1s ease-in-out;"></div>
            </div>
            
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-size: 0.78rem; color: #94A3B8;">Status</span>
                <span style="background: rgba(255, 255, 255, 0.05); border: 1px solid {color}; color: {color}; padding: 3px 10px; border-radius: 20px; font-size: 0.78rem; font-weight: 700; display: inline-flex; align-items: center; gap: 4px;">
                    {emoji} {status_text}
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_metrics_grid(metrics):
    """Render a 2-column or 3-column grid of all core fitness metrics."""
    metric_labels = [
        ("Balance", metrics.get("balance", 0)),
        ("Lower Body Stability", metrics.get("lower_body_stability", 0)),
        ("Hip Mobility", metrics.get("hip_mobility", 0)),
        ("Core Stability", metrics.get("core_stability", 0)),
        ("Coordination", metrics.get("coordination", 0)),
        ("Body Symmetry", metrics.get("body_symmetry", 0)),
        ("Movement Quality", metrics.get("movement_quality", 0)),
    ]
    
    col1, col2 = st.columns(2)
    for idx, (title, score) in enumerate(metric_labels):
        with col1 if idx % 2 == 0 else col2:
            render_metric_card(title, score)
