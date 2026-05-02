import os
import sys
from typing import Tuple

import pandas as pd
from sqlalchemy.engine import Engine

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.config import AnalyticsConfig, get_config
from src.utils import get_db_connection, safe_read_sql


def load_raw_data(
    engine: Engine,
    config: AnalyticsConfig | None = None,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Pull the required raw tables from Supabase.

    Args:
        engine: SQLAlchemy engine for Supabase.
        config: Optional analytics configuration.

    Returns:
        Tuple of orders, items, products, payments, customers dataframes.
    """
    print("⏳ Loading raw data from Supabase...")
    resolved_config = config or get_config()
    try:
        orders = safe_read_sql(f"SELECT * FROM {resolved_config.raw_orders_table}", engine)
        items = safe_read_sql(f"SELECT * FROM {resolved_config.raw_items_table}", engine)
        products = safe_read_sql(f"SELECT * FROM {resolved_config.raw_products_table}", engine)
        payments = safe_read_sql(f"SELECT * FROM {resolved_config.raw_payments_table}", engine)
        customers = safe_read_sql(f"SELECT * FROM {resolved_config.raw_customers_table}", engine)

        print(f"Loaded: Orders({len(orders)}), Items({len(items)})")
        return orders, items, products, payments, customers
    except Exception as e:
        print(f"Error loading data: {e}")
        return None, None, None, None, None

def transform_data(
    orders: pd.DataFrame,
    items: pd.DataFrame,
    products: pd.DataFrame,
    payments: pd.DataFrame,
    customers: pd.DataFrame,
    config: AnalyticsConfig | None = None,
) -> pd.DataFrame:
    """Merge raw tables and clean the data for analytics.

    Args:
        orders: Orders dataframe.
        items: Order items dataframe.
        products: Products dataframe.
        payments: Payments dataframe.
        customers: Customers dataframe.
        config: Optional analytics configuration.

    Returns:
        Cleaned, enriched dataframe ready for analytics.
    """
    print("⏳ Transforming data...")
    resolved_config = config or get_config()

    # 1. Merge Orders with Items (One order can have multiple items)
    # This is an INNER JOIN (we only want orders that actually have items)
    merged = pd.merge(orders, items, on=resolved_config.id_col, how='inner')

    # 2. Merge with Products (to get categories)
    if 'product_id' in merged.columns and 'product_id' in products.columns:
        merged = pd.merge(merged, products[['product_id', 'product_category_name']], on='product_id', how='left')

    # 3. Merge with Customers (to get location)
    customer_columns = [column for column in ['customer_id', 'customer_city', 'customer_state'] if column in customers.columns]
    if 'customer_id' in merged.columns and customer_columns:
        merged = pd.merge(merged, customers[customer_columns], on='customer_id', how='left')

    # 4. Merge with Payments (to get payment type)
    # Note: An order can have multiple payments (split bill). We take the first one for simplicity in this MVP.
    if resolved_config.id_col in payments.columns:
        payments_unique = payments.drop_duplicates(subset=[resolved_config.id_col], keep='first')
        payment_columns = [column for column in [resolved_config.id_col, 'payment_type', 'payment_value'] if column in payments_unique.columns]
        merged = pd.merge(merged, payments_unique[payment_columns], on=resolved_config.id_col, how='left')

    # 5. Data Type Conversions (Crucial for Time Series)
    date_cols = [column for column in ['order_purchase_timestamp', 'order_approved_at', 'order_delivered_carrier_date', 
                 'order_delivered_customer_date', 'order_estimated_delivery_date'] if column in merged.columns]

    for col in date_cols:
        merged[col] = pd.to_datetime(merged[col], errors='coerce')

    # 6. Feature Engineering (Creating new useful columns)
    # Calculate 'Delivery Days' (Actual delivery time)
    if 'order_delivered_customer_date' in merged.columns and 'order_purchase_timestamp' in merged.columns:
        merged['delivery_days'] = (merged['order_delivered_customer_date'] - merged['order_purchase_timestamp']).dt.days
    
    # Calculate 'Delay' (Negative means early, Positive means late)
    if 'order_delivered_customer_date' in merged.columns and 'order_estimated_delivery_date' in merged.columns:
        merged['delay_days'] = (merged['order_delivered_customer_date'] - merged['order_estimated_delivery_date']).dt.days

    # 7. Cleaning
    # Drop rows where critical info is missing
    required_drop_columns = [column for column in [resolved_config.date_col, resolved_config.value_col] if column in merged.columns]
    if required_drop_columns:
        merged.dropna(subset=required_drop_columns, inplace=True)
    
    # Translate categories (Optional: simple cleanup)
    if 'product_category_name' in merged.columns:
        merged['product_category_name'] = merged['product_category_name'].fillna('unknown')
    
    print(f"Transformation Complete. Master Table Shape: {merged.shape}")
    return merged

def save_to_warehouse(df: pd.DataFrame, engine: Engine, config: AnalyticsConfig | None = None) -> None:
    """Upload the clean master table to Supabase.

    Args:
        df: Cleaned analytics dataframe.
        engine: SQLAlchemy engine for Supabase.
        config: Optional analytics configuration.
    """
    print("⏳ Uploading processed data to Supabase...")
    resolved_config = config or get_config()
    try:
        table_name = resolved_config.fact_table_name
        df.to_sql(table_name, engine, if_exists='replace', index=False, chunksize=1000)
        if resolved_config.legacy_fact_table_name != table_name:
            df.to_sql(resolved_config.legacy_fact_table_name, engine, if_exists='replace', index=False, chunksize=1000)
        print(f"Success! '{table_name}' is live with {len(df)} rows.")
    except Exception as e:
        print(f"Error uploading: {e}")

def run_pipeline() -> None:
    """Run the end-to-end transformation pipeline.

    Returns:
        None.
    """
    engine = get_db_connection()
    if not engine:
        return

    resolved_config = get_config()

    # 1. Extract
    orders, items, products, payments, customers = load_raw_data(engine, resolved_config)
    if orders is None:
        return

    # 2. Transform
    clean_data = transform_data(orders, items, products, payments, customers, resolved_config)

    # 3. Load
    save_to_warehouse(clean_data, engine, resolved_config)

if __name__ == "__main__":
    run_pipeline()