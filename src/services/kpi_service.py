from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Dict, Optional

import pandas as pd

from src.config import AnalyticsConfig, MappingError, get_config


@dataclass
class KPIResult:
    """Container for key business metrics."""

    total_revenue: float
    total_orders: int
    total_customers: int
    average_order_value: float
    numeric_metrics: Dict[str, float] = field(default_factory=dict)


def _resolve_config(config: Optional[AnalyticsConfig] = None) -> AnalyticsConfig:
    """Return an explicit config or the cached default."""
    return config or get_config()


def calculate_kpis(dataframe: pd.DataFrame, config: Optional[AnalyticsConfig] = None) -> KPIResult:
    """Calculate core KPI values plus dynamic numeric metrics.

    Args:
        dataframe: Filtered analytics dataframe.
        config: Optional analytics configuration.

    Returns:
        KPIResult with computed metrics.

    Raises:
        MappingError: If the configured columns are missing.
    """
    resolved_config = _resolve_config(config)
    resolved_config.validate_dataframe(dataframe, required_columns=[resolved_config.value_col, resolved_config.id_col])

    total_revenue = float(pd.to_numeric(dataframe[resolved_config.value_col], errors="coerce").fillna(0).sum())
    total_orders = int(dataframe[resolved_config.id_col].nunique()) if resolved_config.id_col in dataframe.columns else len(dataframe)

    customer_col: Optional[str] = resolved_config.user_col if resolved_config.user_col in dataframe.columns else None
    total_customers = int(dataframe[customer_col].nunique()) if customer_col else total_orders
    average_order_value = total_revenue / total_orders if total_orders > 0 else 0.0

    numeric_metrics = calculate_numeric_metrics(dataframe, resolved_config)

    return KPIResult(
        total_revenue=total_revenue,
        total_orders=total_orders,
        total_customers=total_customers,
        average_order_value=average_order_value,
        numeric_metrics=numeric_metrics,
    )


def calculate_numeric_metrics(
    dataframe: pd.DataFrame,
    config: Optional[AnalyticsConfig] = None,
) -> Dict[str, float]:
    """Summarize every numeric column as a KPI-friendly total.

    Args:
        dataframe: Analytics dataframe.
        config: Optional analytics configuration.

    Returns:
        Ordered mapping of numeric column names to summed values.
    """
    resolved_config = _resolve_config(config)
    resolved_columns = resolved_config.canonical_metric_columns(dataframe)
    totals: OrderedDict[str, float] = OrderedDict()

    for column in resolved_columns:
        totals[column] = float(pd.to_numeric(dataframe[column], errors="coerce").fillna(0).sum())

    return totals


def build_daily_revenue_series(
    dataframe: pd.DataFrame,
    config: Optional[AnalyticsConfig] = None,
) -> pd.DataFrame:
    """Aggregate sales into a daily revenue time series.

    Args:
        dataframe: Sales dataframe with a timestamp and value column.
        config: Optional analytics configuration.

    Returns:
        Dataframe with columns [order_purchase_timestamp, price] or the configured aliases.
    """
    resolved_config = _resolve_config(config)
    resolved_config.validate_dataframe(dataframe, required_columns=[resolved_config.date_col, resolved_config.value_col])

    # Resample at a daily cadence to stabilize Prophet inputs and chart trendlines.
    daily_revenue = (
        dataframe.set_index(resolved_config.date_col)
        .resample("D")[resolved_config.value_col]
        .sum()
        .reset_index()
    )
    return daily_revenue
