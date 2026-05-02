from __future__ import annotations

from typing import Tuple

import pandas as pd
from sqlalchemy.engine import Engine

from src.config import AnalyticsConfig, MappingError, get_config
from src.utils import safe_read_sql


def _load_table_with_fallback(engine, primary_table: str, fallback_table: str) -> pd.DataFrame:
    """Load a table and fall back to a legacy name when necessary."""
    dataframe = safe_read_sql(f"SELECT * FROM {primary_table}", engine)
    if not dataframe.empty:
        return dataframe
    if fallback_table != primary_table:
        return safe_read_sql(f"SELECT * FROM {fallback_table}", engine)
    return dataframe


def load_processed_sales_data(
    config: AnalyticsConfig | None = None,
    engine: Engine | None = None,
) -> pd.DataFrame:
    """Load the processed sales dataset from Supabase.

    Args:
        config: Optional analytics configuration.
        engine: Optional database engine to reuse.

    Returns:
        Dataframe containing processed sales data.

    Raises:
        MappingError: If the configured columns are missing.
    """
    from src.utils import get_db_connection

    resolved_config = config or get_config()
    resolved_engine = engine or get_db_connection()
    if not resolved_engine:
        return pd.DataFrame()

    dataframe = _load_table_with_fallback(
        resolved_engine,
        resolved_config.fact_table_name,
        resolved_config.legacy_fact_table_name,
    )
    if dataframe.empty:
        return dataframe

    resolved_config.validate_dataframe(
        dataframe,
        required_columns=resolved_config.required_columns(),
    )
    dataframe = dataframe.copy()
    dataframe[resolved_config.date_col] = pd.to_datetime(dataframe[resolved_config.date_col], errors="coerce")
    dataframe[resolved_config.value_col] = pd.to_numeric(dataframe[resolved_config.value_col], errors="coerce").fillna(0)
    return dataframe


def load_sales_forecast(
    config: AnalyticsConfig | None = None,
    engine: Engine | None = None,
) -> pd.DataFrame:
    """Load the sales forecast dataset from Supabase.

    Args:
        config: Optional analytics configuration.
        engine: Optional database engine to reuse.

    Returns:
        Dataframe containing forecast data.
    """
    from src.utils import get_db_connection

    resolved_config = config or get_config()
    resolved_engine = engine or get_db_connection()
    if not resolved_engine:
        return pd.DataFrame()

    forecast = _load_table_with_fallback(
        resolved_engine,
        resolved_config.forecast_table_name,
        resolved_config.legacy_forecast_table_name,
    )
    if forecast.empty:
        return forecast

    if "ds" in forecast.columns:
        forecast["ds"] = pd.to_datetime(forecast["ds"], errors="coerce")
    return forecast


def load_dashboard_data(
    config: AnalyticsConfig | None = None,
    engine: Engine | None = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Load the processed sales data and forecast for the dashboard.

    Args:
        config: Optional analytics configuration.
        engine: Optional database engine to reuse.

    Returns:
        Tuple of (processed sales dataframe, forecast dataframe).
    """
    resolved_config = config or get_config()
    sales_df = load_processed_sales_data(resolved_config, engine=engine)
    forecast_df = load_sales_forecast(resolved_config, engine=engine)
    return sales_df, forecast_df
