from __future__ import annotations

from typing import Tuple

import pandas as pd
from prophet import Prophet
from sqlalchemy.engine import Engine

from src.config import AnalyticsConfig, MappingError, get_config
from src.utils import safe_to_sql


def _resolve_config(config: AnalyticsConfig | None = None) -> AnalyticsConfig:
    """Return an explicit config or the cached default."""
    return config or get_config()


def prepare_prophet_training_data(
    dataframe: pd.DataFrame,
    config: AnalyticsConfig | None = None,
) -> pd.DataFrame:
    """Aggregate sales to daily totals and format for Prophet.

    Args:
        dataframe: Processed sales dataframe.
        config: Optional analytics configuration.

    Returns:
        Dataframe with columns [ds, y] for Prophet.

    Raises:
        MappingError: If the configured date or value columns are missing.
    """
    resolved_config = _resolve_config(config)
    resolved_config.validate_dataframe(dataframe, required_columns=[resolved_config.date_col, resolved_config.value_col])

    daily = (
        dataframe.set_index(resolved_config.date_col)
        .resample("D")[resolved_config.value_col]
        .sum()
        .reset_index()
    )
    daily.rename(columns={resolved_config.date_col: "ds", resolved_config.value_col: "y"}, inplace=True)
    daily = daily.dropna(subset=["ds", "y"])
    return daily


def train_prophet_model(training_data: pd.DataFrame) -> Prophet:
    """Train a Prophet model on prepared training data.

    Args:
        training_data: Dataframe with columns [ds, y].

    Returns:
        Trained Prophet model.

    Raises:
        ValueError: If training data is insufficient.
    """
    if training_data.empty or len(training_data) < 30:
        raise ValueError("Insufficient data to train Prophet (need at least 30 rows).")

    model = Prophet(
        daily_seasonality=True,
        weekly_seasonality=True,
        yearly_seasonality=True,
        interval_width=0.9,
    )
    model.fit(training_data)
    return model


def generate_forecast(model: Prophet, horizon_days: int = 30) -> pd.DataFrame:
    """Generate a forecast horizon using a trained Prophet model.

    Args:
        model: Trained Prophet model.
        horizon_days: Number of days to forecast.

    Returns:
        Dataframe with columns [ds, yhat, yhat_lower, yhat_upper].
    """
    future = model.make_future_dataframe(periods=horizon_days, freq="D")
    forecast = model.predict(future)
    return forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]]


def run_forecast_pipeline(
    engine: Engine,
    sales_df: pd.DataFrame,
    horizon_days: int = 30,
    config: AnalyticsConfig | None = None,
) -> Tuple[pd.DataFrame, str]:
    """Train Prophet and persist a fresh forecast to Supabase.

    Args:
        engine: SQLAlchemy engine.
        sales_df: Processed sales dataframe.
        horizon_days: Forecast horizon in days.
        config: Optional analytics configuration.

    Returns:
        Tuple of (forecast dataframe, status message).
    """
    resolved_config = _resolve_config(config)
    try:
        training_data = prepare_prophet_training_data(sales_df, resolved_config)
        model = train_prophet_model(training_data)
        forecast = generate_forecast(model, horizon_days=horizon_days)
        safe_to_sql(forecast, resolved_config.forecast_table_name, engine, if_exists="replace", chunksize=1000)
        if resolved_config.legacy_forecast_table_name != resolved_config.forecast_table_name:
            safe_to_sql(forecast, resolved_config.legacy_forecast_table_name, engine, if_exists="replace", chunksize=1000)
        return forecast, "Forecast pipeline completed successfully."
    except Exception as exc:
        return pd.DataFrame(), f"Forecast pipeline failed: {exc}"
