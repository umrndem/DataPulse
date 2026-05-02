"""Settings page rendering."""

import pandas as pd
import streamlit as st

from src.config import get_config
from src.services.auth_service import create_user, delete_user, get_all_users
from src.utils import (
    delete_processed_sales_data,
    fetch_latest_logs,
    get_target_goal,
    update_target_goal,
    write_log,
)


def show(df: pd.DataFrame, engine, navigate_to) -> None:
    """Render the Settings page (Admin-only)."""
    if st.session_state.role != "Admin":
        st.error("🔐 Access Denied: Settings is restricted to Admins only.")
        if st.button("← Return to Dashboard"):
            navigate_to("Business Insights")
        st.stop()

    st.title("Platform Settings")
    st.markdown("Manage your DataPulse enterprise preferences and users.")

    st.subheader("User Management")

    with st.form("create_user_form"):
        st.markdown("#### Add New User")
        new_email = st.text_input("Email Address", placeholder="user@company.com")
        new_name = st.text_input("Full Name", placeholder="John Doe")
        new_password = st.text_input("Password", type="password", placeholder="••••••••••••")
        new_role = st.selectbox("Role", ["Viewer", "Admin"])

        if st.form_submit_button("Create User", use_container_width=True):
            if not new_email or not new_name or not new_password:
                st.error("Please fill in all fields.")
            else:
                if create_user(engine, new_email, new_password, new_name, new_role):
                    write_log(engine, "INFO", f"Created new user: {new_email} with role {new_role}")
                    st.success(f"✅ User {new_email} created successfully.")
                    st.rerun()
                else:
                    st.error("Failed to create user. Email may already exist.")

    st.divider()

    st.markdown("#### Manage Users")
    users_df = get_all_users(engine)

    if users_df.empty:
        st.info("No users found.")
    else:
        st.dataframe(users_df[["email", "full_name", "role", "created_at"]], use_container_width=True, hide_index=True)

        st.markdown("#### Delete User")
        user_to_delete = st.selectbox("Select user to delete", users_df["email"].tolist(), key="delete_user_select")

        col_confirm, col_delete = st.columns(2)
        with col_confirm:
            confirm = st.checkbox(f"I understand this will permanently remove {user_to_delete}")
        with col_delete:
            if st.button("Delete User", use_container_width=True, disabled=not confirm):
                user_id = users_df[users_df["email"] == user_to_delete]["id"].values[0]
                if delete_user(engine, user_id):
                    write_log(engine, "WARN", f"Deleted user: {user_to_delete}")
                    st.success(f"✅ User {user_to_delete} deleted successfully.")
                    st.rerun()
                else:
                    st.error("Failed to delete user.")

    st.divider()

    st.subheader("Target Goal")
    if not engine:
        st.error("Supabase connection unavailable. Please verify DATABASE_URL.")
    else:
        current_goal = get_target_goal(engine, default_value=0.0)
        goal_input = st.number_input("Target Goal (Revenue)", min_value=0.0, value=float(current_goal), step=1000.0)
        if st.button("Update Target Goal", type="primary"):
            try:
                update_target_goal(engine, goal_input)
                write_log(engine, "INFO", f"Updated target goal to {goal_input}")
                st.toast("Target goal updated.", icon="✅")
            except Exception as exc:
                write_log(engine, "ERROR", f"Target goal update failed: {exc}")
                st.error(f"Failed to update target goal: {exc}")

    st.subheader("System Logs")
    if engine:
        log_df = fetch_latest_logs(engine, limit=25)
        if log_df.empty:
            st.info("No logs available yet.")
        else:
            st.dataframe(log_df, use_container_width=True, hide_index=True)

    st.subheader("Data Reset Controls")
    st.caption(f"Delete a date range from {get_config().fact_table_name} to re-run ingestion.")
    if engine and not df.empty:
        config = get_config()
        if config.date_col in df.columns:
            min_date = pd.to_datetime(df[config.date_col], errors="coerce").min().date()
            max_date = pd.to_datetime(df[config.date_col], errors="coerce").max().date()
            delete_dates = st.date_input("Delete Range", [min_date, max_date], min_value=min_date, max_value=max_date)
            confirm_delete = st.checkbox("I understand this action is irreversible.")
            if confirm_delete and st.button("Delete Range", use_container_width=True):
                if len(delete_dates) == 2:
                    rows_deleted = delete_processed_sales_data(engine, delete_dates[0], delete_dates[1])
                    write_log(engine, "WARN", f"Deleted {rows_deleted} rows from {config.fact_table_name}")
                    st.toast(f"Deleted {rows_deleted} rows.", icon="🧹")
                    st.cache_data.clear()
        else:
            st.warning(f"Date column '{config.date_col}' not found in dataset.")

    st.subheader("System Actions")
    if st.button("Clear Application Cache", type="primary"):
        st.cache_data.clear()
        st.toast("Memory cleared successfully!", icon="🧹")
