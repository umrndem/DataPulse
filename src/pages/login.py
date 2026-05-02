"""Login page rendering."""

import time

import streamlit as st

from src.services.auth_service import authenticate_user
from src.utils import write_log


def show(get_engine) -> None:
    """Render the login screen."""
    col_img, col_form, _ = st.columns([1.2, 1, 0.2], gap="large")

    with col_img:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.image(
            "https://img.freepik.com/free-vector/data-extraction-concept-illustration_114360-4766.jpg",
            use_container_width=True,
        )

    with col_form:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.markdown('<div class="login-header">Welcome Back</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-sub">Log in to your DataPulse Enterprise account</div>', unsafe_allow_html=True)

        email_input = st.text_input("Work Email", placeholder="admin@datapulse.local")
        password_input = st.text_input("Password", type="password", placeholder="••••••••••••")
        st.markdown('<div class="forgot-pass">Forgot password?</div>', unsafe_allow_html=True)

        if st.button("Log In", type="primary", use_container_width=True):
            if not email_input or not password_input:
                st.error("Please enter both email and password.")
            else:
                with st.spinner("Authenticating securely..."):
                    auth_engine = get_engine()
                    if auth_engine:
                        user = authenticate_user(auth_engine, email_input, password_input)
                        if user:
                            st.session_state.logged_in = True
                            st.session_state.email = user["email"]
                            st.session_state.full_name = user["full_name"]
                            st.session_state.role = user["role"]
                            write_log(auth_engine, "INFO", f"User {email_input} logged in with role {user['role']}")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error("Invalid email or password.")
                    else:
                        st.error("Database connection failed. Please try again.")

        st.markdown(
            "<p style='text-align: center; margin-top: 35px; color: #64748b;'>"
            "Don't have an account? Contact your administrator to request access."
            "</p>",
            unsafe_allow_html=True,
        )
