"""Business Insights page rendering."""

import io

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.config import MappingError, get_config
from src.services.kpi_service import build_daily_revenue_series, calculate_kpis, calculate_numeric_metrics
from src.ui.helpers import build_dynamic_weekly_chart, format_metric_value
from src.utils import get_target_goal


def show(df: pd.DataFrame, forecast_df: pd.DataFrame, engine, dates) -> None:
    """Render the Business Insights page."""
    if df.empty:
        st.warning("⚠️ Database connected, but the fact table is empty. Please run the ingestion/transformation pipeline.")
        st.stop()

    config = get_config()
    try:
        config.validate_dataframe(df)
    except MappingError as exc:
        st.error(str(exc))
        st.stop()

    if len(dates) == 2:
        masked = df.copy()
        masked[config.date_col] = pd.to_datetime(masked[config.date_col], errors="coerce")
        mask = (masked[config.date_col].dt.date >= dates[0]) & (masked[config.date_col].dt.date <= dates[1])
        f_df = masked.loc[mask].copy()
    else:
        f_df = df.copy()

    if f_df.empty:
        st.info("No data available for this date range. Please adjust the sidebar filters.")
        st.stop()

    title_dates = f"({dates[0]} to {dates[1]})" if len(dates) == 2 else ""
    st.markdown(
        f"### 📊 Business Insights <span style='font-size: 16px; color: #64748b; font-weight: normal; margin-left: 10px;'>{title_dates}</span>",
        unsafe_allow_html=True,
    )

    kpis = calculate_kpis(f_df, config)
    target_goal_value = get_target_goal(engine, default_value=0.0) if engine else 0.0
    target_goal_label = f"${target_goal_value/1_000_000:,.1f}M" if target_goal_value > 0 else "N/A"

    primary_metrics = [
        ("Mapped Value Total", kpis.total_revenue),
        ("Mapped Record Count", float(kpis.total_orders)),
        ("Mapped User Count", float(kpis.total_customers)),
        ("Mapped AOV", kpis.average_order_value),
        ("Target Goal", target_goal_value),
    ]
    primary_columns = st.columns(len(primary_metrics))
    for column, (label, value) in zip(primary_columns, primary_metrics):
        if label == "Target Goal":
            column.metric(label, target_goal_label)
        else:
            column.metric(label, format_metric_value(label, value))

    additional_metrics = calculate_numeric_metrics(f_df, config)
    if additional_metrics:
        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("Dynamic KPI Cards")
        metric_items = list(additional_metrics.items())
        columns_per_row = 4
        for start_index in range(0, len(metric_items), columns_per_row):
            row = st.columns(min(columns_per_row, len(metric_items) - start_index))
            for column, (metric_name, metric_value) in zip(row, metric_items[start_index:start_index + columns_per_row]):
                column.metric(metric_name.replace("_", " ").title(), format_metric_value(metric_name, metric_value))

    st.markdown("<br>", unsafe_allow_html=True)
    c_bar, c_pie = st.columns([3, 1])
    with c_bar:
        trend_columns = [column for column in [config.value_col] + list(additional_metrics.keys()) if column in f_df.columns]
        if trend_columns:
            trend_fig = build_dynamic_weekly_chart(f_df, config.date_col, trend_columns)
            trend_fig.update_layout(title="Mapped Metric Trends", xaxis_title="", yaxis_title="Weekly Sum")
            st.plotly_chart(trend_fig, use_container_width=True)
        else:
            st.info("No numeric columns were available for charting.")

    with c_pie:
        if "payment_type" in f_df.columns:
            pie_data = f_df["payment_type"].value_counts().reset_index()
            fig_pie = px.pie(
                pie_data,
                names="payment_type",
                values="count",
                hole=0.6,
                title="Channel Distribution",
                color_discrete_sequence=["#3b82f6", "#10b981", "#f59e0b"],
            )
        else:
            pie_source = f_df.copy()
            pie_source["Day"] = pd.to_datetime(pie_source[config.date_col], errors="coerce").dt.day_name()
            pie_data = pie_source["Day"].value_counts().reset_index()
            fig_pie = px.pie(
                pie_data,
                names="Day",
                values="count",
                hole=0.6,
                title="Record Distribution",
                color_discrete_sequence=["#3b82f6", "#93c5fd", "#1e3a8a", "#bfdbfe"],
            )

        fig_pie.update_layout(margin=dict(l=0, r=0, t=30, b=0), showlegend=False)
        st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)
    c_line, c_table = st.columns([1, 1])

    with c_line:
        st.subheader("AI Sales Forecasting (30-Day Outlook)")
        if not forecast_df.empty:
            history_series = build_daily_revenue_series(f_df, config)
            fig_line = go.Figure()
            fig_line.add_trace(
                go.Scatter(
                    x=forecast_df["ds"],
                    y=forecast_df["yhat"],
                    name="Prophet Target",
                    line=dict(color="#10b981", dash="dot", width=3),
                )
            )
            fig_line.add_trace(
                go.Scatter(
                    x=history_series[config.date_col],
                    y=history_series[config.value_col],
                    name="Actual Sales",
                    line=dict(color="#3b82f6", width=2),
                )
            )
            fig_line.update_layout(
                plot_bgcolor="white",
                margin=dict(l=0, r=0, t=10, b=0),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            history_series = build_daily_revenue_series(f_df, config)
            fig_line = px.area(
                history_series.tail(60),
                x=config.date_col,
                y=config.value_col,
                color_discrete_sequence=["#cbd5e1"],
            )
            fig_line.update_layout(plot_bgcolor="white", margin=dict(l=0, r=0, t=10, b=0), xaxis_title="", yaxis_title="")
            st.plotly_chart(fig_line, use_container_width=True)
            st.info(
                "💡 **ML Pipeline Offline:** The Prophet engine is awaiting training data. Currently displaying historical baseline. "
                "Run `prediction_pipeline.py` to unlock AI insights."
            )

    with c_table:
        st.subheader(f"Master Data Table ({len(f_df):,} records)")
        display_cols = [column for column in [config.date_col, config.id_col, config.user_col, config.value_col] if column in f_df.columns]
        display_cols.extend([column for column in additional_metrics.keys() if column in f_df.columns and column not in display_cols])
        display_df = f_df[display_cols].copy()
        display_df.sort_values(by=config.date_col, ascending=False, inplace=True)
        if config.value_col in display_df.columns:
            display_df[config.value_col] = display_df[config.value_col].apply(lambda x: f"${x:,.2f}")

        st.dataframe(display_df, use_container_width=True, hide_index=True, height=350)

        st.markdown("#### Export Filtered Data")
        csv_buffer = io.StringIO()
        f_df.to_csv(csv_buffer, index=False)
        st.download_button(
            label="Download CSV",
            data=csv_buffer.getvalue(),
            file_name="datapulse_filtered_export.csv",
            mime="text/csv",
            use_container_width=True,
        )
