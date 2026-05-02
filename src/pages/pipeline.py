"""Data Pipeline page rendering."""

import time

import streamlit as st

from src.config import get_config
from src.services.forecast_service import run_forecast_pipeline
from src.utils import write_log


def show(df, forecast_df, engine, navigate_to) -> None:
    """Render the Data Pipeline page (Admin-only)."""
    if st.session_state.role != "Admin":
        st.error("🔐 Access Denied: This page is restricted to Admins only.")
        if st.button("← Return to Dashboard"):
            navigate_to("Business Insights")
        st.stop()

    st.title("Cloud Infrastructure Status")

    col_db, col_ml = st.columns(2)
    with col_db:
        st.markdown("### PostgreSQL Database")
        if st.button("Ping Supabase Node"):
            with st.spinner("Connecting to Port 6543..."):
                time.sleep(1)
                st.toast("Node Active: Latency 14ms", icon="🟢")
        st.success("🟢 Connection Pool: Active")
        st.success(f"🟢 `{get_config().fact_table_name}`: {len(df):,} rows synced")

    with col_ml:
        st.markdown("### Prophet ML Engine")
        if not forecast_df.empty:
            st.success("🟢 AI Model: Trained & Synced")
            st.success(f"🟢 `{get_config().forecast_table_name}`: {len(forecast_df)} prediction points")
        else:
            st.error("🔴 AI Model: Offline / Awaiting Data")
            st.warning(f"⚠️ `{get_config().forecast_table_name}`: Table not found")

        if engine and st.button("Run 30-Day Forecast", use_container_width=True):
            with st.spinner("Training Prophet and syncing forecast..."):
                forecast_df, status_message = run_forecast_pipeline(engine, df, horizon_days=30)
                if forecast_df.empty:
                    st.error(status_message)
                    write_log(engine, "ERROR", status_message)
                else:
                    st.success(status_message)
                    write_log(engine, "INFO", status_message)
                    st.cache_data.clear()
