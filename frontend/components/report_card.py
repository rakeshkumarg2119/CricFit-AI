import streamlit as st
import requests
from config import BACKEND_URL


def _format_timestamp(ts_str: str) -> str:
    """Format ISO timestamp to readable string."""
    if not ts_str:
        return "Unknown date"
    try:
        from datetime import datetime
        ts_str = ts_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(ts_str)
        return dt.strftime("%d %b %Y  •  %I:%M %p UTC")
    except Exception:
        return ts_str[:16] if len(ts_str) >= 16 else ts_str


def _get_activity_icon(activity: str) -> str:
    icons = {
        "batting": "🏏",
        "bowling": "🏃",
        "yoyo": "⚡",
        "yoyo_test": "⚡",
    }
    return icons.get(activity.lower(), "📊")


def _get_activity_label(activity: str) -> str:
    labels = {
        "batting": "Batting Analysis",
        "bowling": "Bowling Analysis",
        "yoyo": "Yo-Yo Test",
        "yoyo_test": "Yo-Yo Test",
    }
    return labels.get(activity.lower(), activity.title())


def render_saved_report_card(report, on_view_click, on_delete_click=None, key_prefix=""):
    """
    Render a report item card for the My Reports page.
    Includes View, PDF Download, and Delete buttons with proper timestamps.
    """
    report_id = report.get("id") or report.get("_id", "N/A")
    activity = report.get("activity", "Batting")
    activity_label = _get_activity_label(activity)
    icon = _get_activity_icon(activity)

    raw_ts = report.get("saved_at") or report.get("timestamp") or report.get("date_str", "")
    timestamp_display = _format_timestamp(raw_ts) if raw_ts and raw_ts not in ("Recent", "") else "Unknown time"

    overall_score = report.get("overall_score", 75)
    movement_quality = report.get("movement_quality", 80)
    risk_level = report.get("risk_level", "Low")
    pdf_url = report.get("pdf_url", "")

    risk_color_map = {"Low": "#10B981", "Moderate": "#F59E0B", "High": "#EF4444", "Very High": "#EF4444"}
    risk_color = risk_color_map.get(risk_level, "#94A3B8")
    score_color = "#10B981" if overall_score >= 80 else ("#F59E0B" if overall_score >= 60 else "#EF4444")

    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg, rgba(15,23,42,0.92) 0%, rgba(20,30,55,0.85) 100%);
            border: 1px solid rgba(255,255,255,0.07);
            border-left: 4px solid {score_color};
            border-radius: 18px;
            padding: 20px 24px 14px 24px;
            margin-bottom: 10px;
            box-shadow: 0 4px 24px rgba(0,0,0,0.3);
        ">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 14px; flex-wrap: wrap; gap: 10px;">
                <div style="display: flex; align-items: center; gap: 14px;">
                    <div style="font-size: 1.7rem; background: rgba(30,41,59,0.9); padding: 12px; border-radius: 14px; border: 1px solid rgba(255,255,255,0.06); line-height: 1;">{icon}</div>
                    <div>
                        <div style="font-size: 1.05rem; font-weight: 800; color: #FFFFFF; margin-bottom: 3px;">{activity_label}</div>
                        <div style="font-size: 0.77rem; color: #64748B; font-weight: 600; letter-spacing: 0.3px;">🕐 {timestamp_display}</div>
                        <div style="font-size: 0.72rem; color: #475569; margin-top: 2px;">ID: {report_id}</div>
                    </div>
                </div>
                <div style="text-align: center; background: rgba(6,182,212,0.08); border: 1px solid rgba(6,182,212,0.2); border-radius: 14px; padding: 8px 18px;">
                    <div style="font-size: 1.5rem; font-weight: 900; color: {score_color}; line-height: 1;">{overall_score}<span style="font-size: 0.75rem; color: #64748B;">/100</span></div>
                    <div style="font-size: 0.72rem; color: #94A3B8; font-weight: 600; margin-top: 2px;">Overall Score</div>
                </div>
            </div>
            <div style="display: flex; gap: 20px; font-size: 0.82rem; color: #CBD5E1; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 12px; flex-wrap: wrap;">
                <div>Movement Quality: <strong style="color: #F8FAFC;">{movement_quality}/100</strong></div>
                <div>Risk Level: <strong style="color: {risk_color};">{risk_level}</strong></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    btn_cols = st.columns([3, 3, 2])

    with btn_cols[0]:
        if st.button("👁️ View Full Report", key=f"{key_prefix}view_rep_{report_id}", type="primary"):
            on_view_click(report)

    with btn_cols[1]:
        pdf_bytes = None
        if pdf_url:
            full_pdf_url = f"{BACKEND_URL.rstrip('/')}{pdf_url}"
            try:
                resp = requests.get(full_pdf_url, timeout=8)
                if resp.status_code == 200:
                    pdf_bytes = resp.content
            except Exception:
                pass

        if pdf_bytes is None and report_id and report_id != "N/A":
            try:
                fallback_url = f"{BACKEND_URL.rstrip('/')}/download/pdf/{report_id}"
                resp = requests.get(fallback_url, timeout=8)
                if resp.status_code == 200:
                    pdf_bytes = resp.content
            except Exception:
                pass

        if pdf_bytes:
            activity_slug = activity.lower().replace(" ", "_")
            pdf_filename = f"CricFit-AI_{activity_slug}_report_{report_id}.pdf"
            st.download_button(
                label="📄 Download PDF",
                data=pdf_bytes,
                file_name=pdf_filename,
                mime="application/pdf",
                key=f"{key_prefix}dl_pdf_{report_id}",
            )
        else:
            st.button("📄 PDF Unavailable", key=f"{key_prefix}dl_pdf_na_{report_id}", disabled=True)

    with btn_cols[2]:
        if st.button("🗑️ Delete", key=f"{key_prefix}del_rep_{report_id}"):
            if on_delete_click:
                on_delete_click(report_id)

    st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)

