"""Home/Hub page rendering."""

import streamlit as st


def show(navigate_to) -> None:
    """Render the Home / Hub page."""
    st.title("Enterprise Hub")
    st.markdown("Select a module to view real-time data and manage infrastructure.")
    st.markdown("<br>", unsafe_allow_html=True)

    r1c1, r1c2, r1c3 = st.columns(3)
    with r1c1:
        st.markdown(
            '<div class="hub-card"><div class="hub-title">📈 Core Dashboard</div>'
            '<div class="hub-desc">Top-level KPIs, revenue metrics, and global sales trends.</div></div>',
            unsafe_allow_html=True,
        )
        if st.button("Open Dashboard", use_container_width=True, key="btn_dash"):
            navigate_to("Business Insights")
    with r1c2:
        st.markdown(
            '<div class="hub-card"><div class="hub-title">🥧 Product Insights</div>'
            '<div class="hub-desc">Deep dive into category performance and channel distribution.</div></div>',
            unsafe_allow_html=True,
        )
        if st.button("Open Insights", use_container_width=True, key="btn_ins"):
            navigate_to("Business Insights")
    with r1c3:
        if st.session_state.role == "Viewer":
            st.markdown(
                '<div class="hub-card" style="opacity: 0.5;">'
                '<div class="hub-title">☁️ ETL Pipeline Monitor</div>'
                '<div class="hub-desc">Restricted: Admin-only access</div></div>',
                unsafe_allow_html=True,
            )
            st.button("Open Pipeline (Restricted)", use_container_width=True, key="btn_pipe", disabled=True)
        else:
            st.markdown(
                '<div class="hub-card"><div class="hub-title">☁️ ETL Pipeline Monitor</div>'
                '<div class="hub-desc">Monitor Supabase sync status, database health, and logs.</div></div>',
                unsafe_allow_html=True,
            )
            if st.button("Open Pipeline", use_container_width=True, key="btn_pipe"):
                navigate_to("Data Pipeline")

    r2c1, r2c2, r2c3 = st.columns(3)
    with r2c1:
        st.markdown(
            '<div class="hub-card"><div class="hub-title">🗂️ Master Data Viewer</div>'
            '<div class="hub-desc">Query and export raw, row-level transactional data.</div></div>',
            unsafe_allow_html=True,
        )
        if st.button("View Data Table", use_container_width=True, key="btn_data"):
            navigate_to("Business Insights")
    with r2c2:
        st.markdown(
            '<div class="hub-card"><div class="hub-title">📉 Prophet ML Engine</div>'
            '<div class="hub-desc">Review 30-day AI forecasts and model confidence intervals.</div></div>',
            unsafe_allow_html=True,
        )
        if st.button("View Predictions", use_container_width=True, key="btn_fc"):
            navigate_to("Business Insights")
    with r2c3:
        if st.session_state.role == "Viewer":
            st.markdown(
                '<div class="hub-card" style="opacity: 0.5;">'
                '<div class="hub-title">⚙️ System Settings</div>'
                '<div class="hub-desc">Restricted: Admin-only access</div></div>',
                unsafe_allow_html=True,
            )
            st.button("Open Settings (Restricted)", use_container_width=True, key="btn_set", disabled=True)
        else:
            st.markdown(
                '<div class="hub-card"><div class="hub-title">⚙️ System Settings</div>'
                '<div class="hub-desc">Manage API keys, dark mode, and user permissions.</div></div>',
                unsafe_allow_html=True,
            )
            if st.button("Open Settings", use_container_width=True, key="btn_set"):
                navigate_to("Settings")
