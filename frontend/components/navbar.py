import streamlit as st
from config import APP_NAME, APP_TAGLINE

def render_navbar():
    """Render top branding navbar header."""
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown(
            f"""
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 8px;">
                <div style="background: linear-gradient(135deg, #06B6D4, #3B82F6); padding: 8px 14px; border-radius: 12px; font-weight: 900; font-size: 1.4rem; color: white; box-shadow: 0 4px 14px rgba(6, 182, 212, 0.3);">
                    🏏 CF
                </div>
                <div>
                    <h2 style="margin: 0; padding: 0; font-weight: 800; background: linear-gradient(90deg, #FFFFFF, #94A3B8); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                        {APP_NAME}
                    </h2>
                    <p style="margin: 0; font-size: 0.85rem; color: #94A3B8; font-weight: 500;">
                        {APP_TAGLINE}
                    </p>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        
    with col2:
        api_badge = '<span style="background: #064E3B; color: #10B981; border: 1px solid #10B981; padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 600;">FASTAPI CONNECTED</span>'
        
        st.markdown(
            f"""
            <div style="text-align: right; padding-top: 8px;">
                {api_badge}
            </div>
            """,
            unsafe_allow_html=True
        )
    st.markdown("<hr style='border: 0; height: 1px; background: rgba(255, 255, 255, 0.1); margin-bottom: 24px;' />", unsafe_allow_html=True)
