"""AI Assistant page rendering."""

from __future__ import annotations

import os

import streamlit as st

from src.services.assistant_service import run_question


def show(engine, navigate_to) -> None:
    """Render the AI Assistant page."""
    st.title("AI Assistant")
    st.caption("Ask questions about sales, products, and forecasts in plain language.")

    if not engine:
        st.error("Database connection is unavailable. Please check Supabase status.")
        if st.button("Return to Dashboard"):
            navigate_to("Business Insights")
        return

    if not os.getenv("GEMINI_API_KEY"):
        st.warning("GEMINI_API_KEY is not set. Add it to your environment to enable the assistant.")
        return

    if "assistant_messages" not in st.session_state:
        st.session_state.assistant_messages = []

    for message in st.session_state.assistant_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("sql"):
                with st.expander("SQL used"):
                    st.code(message["sql"], language="sql")
            if message.get("preview"):
                with st.expander("Data preview"):
                    st.dataframe(message["preview"], use_container_width=True, hide_index=True)

    question = st.chat_input("Ask about sales performance, top products, or promo timing...")
    if not question:
        return

    st.session_state.assistant_messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                sql, answer, dataframe, model = run_question(engine, question)
            except Exception as exc:
                st.error(f"Assistant error: {exc}")
                return

        st.markdown(answer)
        with st.expander("SQL used"):
            st.code(sql, language="sql")
        if not dataframe.empty:
            with st.expander("Data preview"):
                st.dataframe(dataframe.head(200), use_container_width=True, hide_index=True)

    st.session_state.assistant_messages.append(
        {
            "role": "assistant",
            "content": answer,
            "sql": sql,
            "preview": dataframe.head(50) if not dataframe.empty else None,
            "model": model,
        }
    )
