from __future__ import annotations

import pandas as pd

from src.config import get_config
from src.services.data_service import load_processed_sales_data
from src.services.forecast_service import run_forecast_pipeline
from src.utils import get_db_connection


def run_pipeline(horizon_days: int = 30) -> pd.DataFrame:
    """Run the Prophet forecasting pipeline and persist results.

    Args:
        horizon_days: Forecast horizon in days.

    Returns:
        Dataframe containing the forecast results.
    """
    engine = get_db_connection()
    if not engine:
        return pd.DataFrame()

    config = get_config()
    sales_df = load_processed_sales_data(config)
    forecast_df, _ = run_forecast_pipeline(engine, sales_df, horizon_days=horizon_days, config=config)
    return forecast_df


if __name__ == "__main__":
    run_pipeline()
