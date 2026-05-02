"""Shared UI components for navigation and layout."""

from typing import List

import pandas as pd
import streamlit as st

from src.config import get_config


def render_top_nav(navigate_to) -> None:
    """Render the top navigation bar."""
    nav_col1, _, nav_col3 = st.columns([2.5, 7, 2.5])

    with nav_col1:
        if st.button("📊 DataPulse Enterprise", use_container_width=True):
            navigate_to("Home / Hub")

    with nav_col3:
        with st.popover("👤 User Profile", use_container_width=True):
            st.markdown(f"**{st.session_state.full_name}**")
            st.caption(f"{st.session_state.role}")
            st.caption(st.session_state.email)
            st.divider()
            if st.button("⚙️ Account Settings", use_container_width=True):
                navigate_to("Settings")
            if st.button("🚪 Log Out", use_container_width=True, type="primary"):
                st.session_state.logged_in = False
                st.session_state.role = None
                st.session_state.email = None
                st.session_state.full_name = None
                st.rerun()

    st.markdown("<hr class='nav-divider'>", unsafe_allow_html=True)


def render_sidebar(
    dataframe: pd.DataFrame,
    current_page: str,
    role: str | None,
    navigate_to,
) -> List:
    """Render sidebar navigation and filters. Returns selected date range."""
    dates: List = []
    with st.sidebar:
        st.markdown("### System Menu")
        pages = ["Home / Hub", "Business Insights", "AI Assistant", "Data Pipeline", "Settings"]

        if role == "Viewer":
            allowed_pages = ["Home / Hub", "Business Insights"]
        else:
            allowed_pages = pages

        selected_page = st.radio(
            "Navigation",
            allowed_pages,
            index=allowed_pages.index(current_page) if current_page in allowed_pages else 0,
            label_visibility="collapsed",
        )

        if selected_page != current_page:
            navigate_to(selected_page)

        if role == "Viewer" and current_page not in allowed_pages:
            st.warning("⚠️ You don't have permission to access this page. Redirecting...")
            navigate_to("Business Insights")

        st.divider()

        if current_page == "Business Insights" and not dataframe.empty:
            st.markdown("### 🎯 Global Filters")
            config = get_config()
            if config.date_col in dataframe.columns:
                min_d = pd.to_datetime(dataframe[config.date_col]).min().date()
                max_d = pd.to_datetime(dataframe[config.date_col]).max().date()
                default_start = max_d - pd.DateOffset(months=6) if (max_d - min_d).days > 180 else min_d
                dates = st.date_input("Date Range", [default_start.date(), max_d], min_value=min_d, max_value=max_d)
            else:
                st.warning(f"Mapping Error: '{config.date_col}' is missing from the dataset.")

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("**Advanced Grouping**")
            st.checkbox("Include B2B Sales", value=True)
            st.checkbox("Show Anomaly Markers", value=False)
            st.selectbox("Region Focus", ["Global (All)", "North America", "LATAM", "EMEA"])

    return dates
