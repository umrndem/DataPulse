import os
import sys
from typing import Tuple

import streamlit as st

# Ensure DB connection works
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from src.config import MappingError, get_config
from src.pages import assistant, home, insights, login, pipeline, settings
from src.services.auth_service import ensure_user_management_table, initialize_super_admin
from src.services.data_service import load_dashboard_data
from src.ui.components import render_sidebar, render_top_nav
from src.ui.styles import apply_global_styles
from src.utils import get_db_connection


# ==========================================
# 1. PAGE CONFIGURATION & STYLES
# ==========================================
apply_global_styles()


# ==========================================
# 2. STATE ROUTER & RBAC INITIALIZATION
# ==========================================
def init_session_state() -> None:
    """Initialize session state defaults."""
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "current_page" not in st.session_state:
        st.session_state.current_page = "Home / Hub"
    if "role" not in st.session_state:
        st.session_state.role = None
    if "email" not in st.session_state:
        st.session_state.email = None
    if "full_name" not in st.session_state:
        st.session_state.full_name = None


# ==========================================
# 3. DATABASE CONNECTION & DATA LOADING
# ==========================================
@st.cache_resource
def get_cached_engine():
    """Get cached database engine for performance."""
    return get_db_connection()


@st.cache_resource
def initialize_database(_engine) -> None:
    """Run one-time database initialization for this app process."""
    ensure_user_management_table(_engine)
    initialize_super_admin(_engine)


@st.cache_data(ttl=300)
def load_data(_engine) -> Tuple:
    """Load sales and forecast data for the dashboard."""
    return load_dashboard_data(get_config(), engine=_engine)


def navigate_to(page_name: str) -> None:
    """Update the current page in session state and rerun the app."""
    st.session_state.current_page = page_name
    st.rerun()


init_session_state()

_engine = get_cached_engine()
if _engine:
    initialize_database(_engine)


# ==========================================
# 4. VIEW ROUTER
# ==========================================
if not st.session_state.logged_in:
    login.show(get_cached_engine)
else:
    try:
        df, forecast_df = load_data(_engine)
    except MappingError as exc:
        st.error(str(exc))
        st.stop()

    engine = get_cached_engine()
    if engine is None:
        st.warning("Supabase is currently paused or unavailable. Data may be stale.")

    render_top_nav(navigate_to)
    dates = render_sidebar(df, st.session_state.current_page, st.session_state.role, navigate_to)

    if st.session_state.current_page == "Home / Hub":
        home.show(navigate_to)
    elif st.session_state.current_page == "Business Insights":
        insights.show(df, forecast_df, engine, dates)
    elif st.session_state.current_page == "AI Assistant":
        assistant.show(engine, navigate_to)
    elif st.session_state.current_page == "Data Pipeline":
        pipeline.show(df, forecast_df, engine, navigate_to)
    elif st.session_state.current_page == "Settings":
        settings.show(df, engine, navigate_to)
