"""Global Streamlit styles and page configuration."""

import streamlit as st


def apply_global_styles() -> None:
    """Apply page config and shared CSS styling."""
    st.set_page_config(page_title="DataPulse | Enterprise Analytics", page_icon="📈", layout="wide")

    st.markdown(
        """
        <style>
        /* Pull the content up to accommodate the Navbar */
        .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
        header {visibility: hidden;}

        /* Clean Metric Cards */
        div[data-testid="metric-container"] {
            background-color: #ffffff; border: 1px solid #e2e8f0;
            padding: 15px; border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.02);
            border-left: 4px solid #3b82f6;
        }
        div[data-testid="stMetricValue"] { color: #1e293b; font-size: 26px; font-weight: 800; }
        div[data-testid="stMetricLabel"] { color: #64748b; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px; }

        /* Login Screen Layout */
        .login-header { font-size: 36px; font-weight: 800; color: #0f172a; margin-bottom: 5px; }
        .login-sub { color: #64748b; font-size: 16px; margin-bottom: 25px; }
        .forgot-pass { color: #3b82f6; font-size: 14px; text-align: right; margin-top: -10px; margin-bottom: 15px; cursor: pointer; }

        /* Hub Cards Styling */
        .hub-card {
            background-color: #ffffff; padding: 22px; border-radius: 12px;
            border: 1px solid #e2e8f0; height: 145px; margin-bottom: 15px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.02); transition: 0.2s ease-in-out;
        }
        .hub-card:hover { border-color: #3b82f6; box-shadow: 0 10px 15px rgba(59, 130, 246, 0.1); }
        .hub-title { font-size: 18px; font-weight: 700; color: #0f172a; margin-bottom: 8px;}
        .hub-desc { font-size: 14px; color: #64748b; line-height: 1.4; }

        /* Navbar Separator */
        hr.nav-divider { margin-top: 5px; margin-bottom: 20px; border-color: #f1f5f9; }
        </style>
        """,
        unsafe_allow_html=True,
    )
