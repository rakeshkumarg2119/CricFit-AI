import streamlit as st
from config import PAGES

def init_session_state():
    """Initialize all session_state variables with safe default values."""
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    
    if "user" not in st.session_state:
        st.session_state.user = None
        
    if "current_page" not in st.session_state:
        st.session_state.current_page = PAGES["LOGIN"]
        
    if "selected_activity" not in st.session_state:
        st.session_state.selected_activity = None
        
    if "uploaded_video" not in st.session_state:
        st.session_state.uploaded_video = None
        
    if "analysis_result" not in st.session_state:
        st.session_state.analysis_result = None
        
    if "report_history" not in st.session_state:
        st.session_state.report_history = []

    if "viewing_report_detail" not in st.session_state:
        st.session_state.viewing_report_detail = None


def navigate_to(page_name, activity=None):
    """Navigate to a specified page and update state."""
    st.session_state.current_page = page_name
    if activity:
        st.session_state.selected_activity = activity
    st.rerun()


def login_user(email, name="Athlete"):
    """Authenticate and log in a user with real input data."""
    st.session_state.logged_in = True
    display_name = name.strip() if name and name.strip() else email.split("@")[0].title()
    st.session_state.user = {
        "name": display_name,
        "email": email.strip(),
        "preferred_activity": "Cricket Athlete",
    }
    st.session_state.current_page = PAGES["HOME"]
    st.rerun()


def logout_user():
    """Logout the current user and reset state."""
    st.session_state.logged_in = False
    st.session_state.user = None
    st.session_state.current_page = PAGES["LOGIN"]
    st.session_state.uploaded_video = None
    st.session_state.analysis_result = None
    st.rerun()


def save_current_report(report_data):
    """Save a real analysis report into session report history."""
    if "report_history" not in st.session_state:
        st.session_state.report_history = []
    
    if report_data and report_data not in st.session_state.report_history:
        st.session_state.report_history.insert(0, report_data)
