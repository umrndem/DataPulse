from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Dict, Iterable, List

import pandas as pd


class MappingError(ValueError):
    """Raised when a configured column mapping does not match the dataframe."""


@dataclass(frozen=True)
class AnalyticsConfig:
    """Runtime configuration for business-agnostic analytics workflows.

    The config maps generic business concepts to actual dataset columns and
    resolves table names for the current deployment.
    """

    business_name: str = "datapulse"
    date_col: str = "order_purchase_timestamp"
    value_col: str = "price"
    id_col: str = "order_id"
    user_col: str = "customer_unique_id"
    raw_orders_table: str = "orders"
    raw_items_table: str = "order_items"
    raw_products_table: str = "products"
    raw_payments_table: str = "order_payments"
    raw_customers_table: str = "customers"
    raw_reviews_table: str = "order_reviews"
    source_table_map: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> "AnalyticsConfig":
        """Build a config from environment variables.

        Returns:
            AnalyticsConfig populated from the current environment.
        """
        source_table_map = _load_source_table_map(os.getenv("SOURCE_TABLE_MAP_JSON", "{}"))
        return cls(
            business_name=os.getenv("BUSINESS_NAME", "datapulse").strip() or "datapulse",
            date_col=os.getenv("DATE_COL", "order_purchase_timestamp").strip() or "order_purchase_timestamp",
            value_col=os.getenv("VALUE_COL", "price").strip() or "price",
            id_col=os.getenv("ID_COL", "order_id").strip() or "order_id",
            user_col=os.getenv("USER_COL", "customer_unique_id").strip() or "customer_unique_id",
            raw_orders_table=os.getenv("RAW_ORDERS_TABLE", "orders").strip() or "orders",
            raw_items_table=os.getenv("RAW_ITEMS_TABLE", "order_items").strip() or "order_items",
            raw_products_table=os.getenv("RAW_PRODUCTS_TABLE", "products").strip() or "products",
            raw_payments_table=os.getenv("RAW_PAYMENTS_TABLE", "order_payments").strip() or "order_payments",
            raw_customers_table=os.getenv("RAW_CUSTOMERS_TABLE", "customers").strip() or "customers",
            raw_reviews_table=os.getenv("RAW_REVIEWS_TABLE", "order_reviews").strip() or "order_reviews",
            source_table_map=source_table_map,
        )

    @property
    def fact_table_name(self) -> str:
        """Return the business fact table name."""
        return f"{self.business_name}_fact"

    @property
    def forecast_table_name(self) -> str:
        """Return the business forecast table name."""
        return f"{self.business_name}_forecast"

    @property
    def legacy_fact_table_name(self) -> str:
        """Return the legacy fact table name for backward compatibility."""
        return "processed_sales_data"

    @property
    def legacy_forecast_table_name(self) -> str:
        """Return the legacy forecast table name for backward compatibility."""
        return "sales_forecast"

    def required_columns(self) -> List[str]:
        """Return the canonical columns required by the dashboard.
        
        Note: user_col is optional; only date_col, value_col, and id_col are required.
        """
        return [self.date_col, self.value_col, self.id_col]

    def validate_dataframe(
        self,
        dataframe: pd.DataFrame,
        required_columns: Iterable[str] | None = None,
    ) -> None:
        """Validate that the dataframe includes the requested columns.

        Args:
            dataframe: Input dataframe to validate.
            required_columns: Optional subset of columns to enforce.

        Raises:
            MappingError: If one or more required columns are missing.
        """
        columns_to_check = list(required_columns) if required_columns is not None else self.required_columns()
        missing = [column for column in columns_to_check if column not in dataframe.columns]
        if missing:
            raise MappingError(
                "Mapping Error: missing required columns "
                f"{missing}. Update BUSINESS_NAME / DATE_COL / VALUE_COL / ID_COL / USER_COL or the source mapping."
            )

    def canonical_metric_columns(self, dataframe: pd.DataFrame) -> List[str]:
        """Return numeric columns suitable for KPI cards.

        Args:
            dataframe: Dataframe to inspect.

        Returns:
            Sorted list of numeric column names excluding mapping columns and other identifiers.
        """
        excluded = {self.date_col, self.id_col, self.user_col}
        numeric_columns = [
            column
            for column in dataframe.columns
            if column not in excluded and pd.api.types.is_numeric_dtype(dataframe[column])
        ]
        return numeric_columns

    def resolve_source_table_name(self, file_name: str) -> str:
        """Resolve the destination raw table name for an uploaded file.

        Args:
            file_name: Raw CSV file name.

        Returns:
            Target Supabase table name for the raw file.
        """
        normalized_file = _normalize_table_name(file_name.replace(".csv", ""))
        if normalized_file in self.source_table_map:
            return self.source_table_map[normalized_file]
        if file_name in self.source_table_map:
            return self.source_table_map[file_name]
        return normalized_file

    def raw_table_for_role(self, role: str) -> str:
        """Resolve a canonical raw table name by its logical role.

        Args:
            role: Logical role name such as orders or customers.

        Returns:
            The configured raw table name.
        """
        role_map = {
            "orders": self.raw_orders_table,
            "items": self.raw_items_table,
            "products": self.raw_products_table,
            "payments": self.raw_payments_table,
            "customers": self.raw_customers_table,
            "reviews": self.raw_reviews_table,
        }
        return role_map[role]


@lru_cache(maxsize=1)
def get_config() -> AnalyticsConfig:
    """Return the cached runtime analytics configuration."""
    return AnalyticsConfig.from_env()


def _load_source_table_map(raw_value: str) -> Dict[str, str]:
    """Parse the optional source table mapping from JSON.

    Args:
        raw_value: JSON encoded source table map.

    Returns:
        Mapping of raw file stems to Supabase table names.
    """
    if not raw_value.strip():
        return {}
    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError:
        return {}
    if not isinstance(parsed, dict):
        return {}
    return {str(key): str(value) for key, value in parsed.items()}


def _normalize_table_name(value: str) -> str:
    """Normalize a name into a PostgreSQL-safe table identifier."""
    lowered = value.lower().strip()
    lowered = re.sub(r"[^a-z0-9]+", "_", lowered)
    lowered = re.sub(r"_+", "_", lowered).strip("_")
    return lowered
