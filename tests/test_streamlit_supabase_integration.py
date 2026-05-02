from datetime import datetime

import pandas as pd
from sqlalchemy import create_engine

from src.services.data_service import load_dashboard_data
import src.utils as utils


def test_dashboard_data_loads_from_engine(monkeypatch) -> None:
    """Verify the dashboard data loader works with a database engine.

    This is a boundary test for the frontend data loader and the Supabase
    access layer, using SQLite as a lightweight stand-in.
    """
    engine = create_engine("sqlite:///:memory:")
    sample = pd.DataFrame(
        {
            "order_purchase_timestamp": [
                datetime(2023, 1, 1),
                datetime(2023, 1, 2),
            ],
            "order_id": ["o1", "o2"],
            "customer_unique_id": ["c1", "c2"],
            "price": [120.0, 180.0],
        }
    )
    sample.to_sql("processed_sales_data", engine, index=False)
    forecast = pd.DataFrame(
        {
            "ds": [datetime(2023, 1, 3)],
            "yhat": [150.0],
            "yhat_lower": [130.0],
            "yhat_upper": [170.0],
        }
    )
    forecast.to_sql("sales_forecast", engine, index=False)

    monkeypatch.setattr(utils, "get_db_connection", lambda: engine)

    sales_df, forecast_df = load_dashboard_data()

    assert not sales_df.empty
    assert not forecast_df.empty
    assert "order_purchase_timestamp" in sales_df.columns
    assert "yhat" in forecast_df.columns
