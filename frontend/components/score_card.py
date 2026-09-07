import streamlit as st
from utils.helpers import get_score_status


def render_score_card(score, activity="Batting", date_str="Today", risk_level="Low"):
    """
    Render circular overall score dashboard header card with conic-gradient gauge.
    Uses st.html() for reliable HTML rendering in Streamlit 1.31+.
    """
    status_info = get_score_status(score)
    status_text = status_info["status"]
    color = status_info["color"]
    emoji = status_info["emoji"]

    activity_icon = "&#x1F3CF;" if activity.lower() == "batting" else "&#x1F3C3;"
    risk_color = "#10B981" if risk_level.lower() == "low" else "#F59E0B"
    conic_deg = round(float(score) * 3.6, 1)

    st.html(f"""
    <div style="background:linear-gradient(135deg,rgba(15,23,42,0.9),rgba(30,41,59,0.8));
                border:1px solid rgba(6,182,212,0.3);border-radius:20px;padding:28px;
                margin-bottom:24px;box-shadow:0 10px 30px rgba(0,0,0,0.4);text-align:center;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
            <div style="text-align:left;">
                <span style="background:rgba(6,182,212,0.15);color:#06B6D4;border:1px solid #06B6D4;
                             padding:4px 12px;border-radius:20px;font-size:0.8rem;
                             font-weight:700;text-transform:uppercase;">
                    {activity_icon} {activity.upper()} REPORT
                </span>
                <div style="font-size:0.85rem;color:#94A3B8;margin-top:6px;">
                    Analysis Date: <strong style="color:#E2E8F0;">{date_str}</strong>
                </div>
            </div>
            <div style="text-align:right;">
                <span style="font-size:0.8rem;color:#94A3B8;">Injury Risk: </span>
                <strong style="color:{risk_color};font-size:0.9rem;">{risk_level}</strong>
            </div>
        </div>

        <div style="display:flex;justify-content:center;align-items:center;margin:20px 0;">
            <div style="position:relative;width:170px;height:170px;border-radius:50%;
                        background:conic-gradient({color} {conic_deg}deg, #1E293B {conic_deg}deg);
                        display:flex;justify-content:center;align-items:center;
                        box-shadow:0 0 25px rgba(6,182,212,0.2);">
                <div style="width:140px;height:140px;border-radius:50%;background:#0B0F19;
                            display:flex;flex-direction:column;justify-content:center;align-items:center;">
                    <span style="font-size:2.8rem;font-weight:900;color:#FFFFFF;line-height:1;">{score}</span>
                    <span style="font-size:0.85rem;color:#64748B;font-weight:600;">OUT OF 100</span>
                </div>
            </div>
        </div>

        <div style="margin-top:10px;">
            <h4 style="margin:0;font-size:1.2rem;font-weight:700;color:#F8FAFC;">
                Overall Fitness Rating: <span style="color:{color};">{emoji} {status_text}</span>
            </h4>
            <p style="margin:6px 0 0 0;font-size:0.85rem;color:#94A3B8;">
                Biomechanical rating based on pose estimation &amp; AI movement modeling
            </p>
        </div>
    </div>
    """)
