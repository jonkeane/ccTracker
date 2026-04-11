import streamlit as st
from pathlib import Path
from app_initialization import ensure_app_session_state_initialized

# Configure page
st.set_page_config(
    page_title="Credit Card Tracker",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded"
)


@st.cache_resource
def _load_custom_css():
    """Load app-wide custom CSS."""
    css_file = Path(__file__).parent / "styles" / "app.css"
    with open(css_file) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


_load_custom_css()
ensure_app_session_state_initialized()

# Define navigation pages
pages = [
    st.Page("pages/1_benefits_tracker.py", title="Benefits Tracker", icon="💳"),
    st.Page("pages/2_hyatt_nights.py", title="Hyatt Nights", icon="🏨"),
    st.Page("pages/3_bilt_cash.py", title="Bilt Cash", icon="🏠"),
]

# Navigation
navigation = st.navigation(pages)
navigation.run()

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray; font-size: 0.8em;'>"
    "Credit Card Tracker • Last updated: Today"
    "</div>",
    unsafe_allow_html=True
)
