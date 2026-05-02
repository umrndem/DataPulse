"""Shared helper utilities for UI rendering."""

import pandas as pd
import plotly.graph_objects as go


def format_metric_value(column_name: str, value: float) -> str:
    """Format KPI values for display based on column semantics."""
    lowered = column_name.lower()
    if any(keyword in lowered for keyword in ["profit", "revenue", "sales", "amount", "value"]):
        return f"${value:,.2f}"
    if any(keyword in lowered for keyword in ["quantity", "count", "units", "orders", "items"]):
        return f"{value:,.0f}"
    return f"{value:,.2f}"


def build_dynamic_weekly_chart(
    dataframe: pd.DataFrame,
    date_col: str,
    numeric_columns: list[str],
) -> go.Figure:
    """Build a multi-series weekly trend chart for mapped numeric columns."""
    unique_columns = list(dict.fromkeys(numeric_columns))

    chart_frame = pd.DataFrame()
    for column in unique_columns:
        series = (
            dataframe[[date_col, column]]
            .set_index(date_col)
            .resample("W")[column]
            .sum()
            .rename(column)
        )
        chart_frame = pd.concat([chart_frame, series], axis=1) if not chart_frame.empty else series.to_frame()

    chart_frame = chart_frame.reset_index().rename(columns={date_col: "date"})
    fig = go.Figure()
    for column in unique_columns:
        fig.add_trace(go.Scatter(x=chart_frame["date"], y=chart_frame[column], name=column, mode="lines"))
    fig.update_layout(plot_bgcolor="white", margin=dict(l=0, r=0, t=10, b=0), xaxis_title="", yaxis_title="")
    return fig
