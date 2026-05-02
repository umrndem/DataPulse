import pandas as pd

from src.services.kpi_service import calculate_kpis


def test_calculate_kpis_revenue_and_aov() -> None:
    """Validate revenue and AOV calculations on a known dataset."""
    sample = pd.DataFrame(
        {
            "order_id": ["o1", "o2", "o3"],
            "customer_unique_id": ["c1", "c2", "c1"],
            "customer_id": ["c1", "c2", "c1"],
            "price": [100.0, 200.0, 300.0],
        }
    )

    kpis = calculate_kpis(sample)

    assert kpis.total_revenue == 600.0
    assert kpis.total_orders == 3
    assert kpis.average_order_value == 200.0
