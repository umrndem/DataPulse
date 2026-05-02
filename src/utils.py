import os
import time
from datetime import date, datetime
from typing import Optional

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from dotenv import load_dotenv

from src.config import get_config

# Load environment variables from .env file
load_dotenv()


def _is_transient_db_error(error: Exception) -> bool:
    """Check whether an exception looks like a transient Supabase pause/timeout.

    Args:
        error: The exception raised during a database operation.

    Returns:
        True if the error appears to be transient or pause-related.
    """
    message = str(error).lower()
    pause_markers = [
        "pause",
        "paused",
        "timeout",
        "timed out",
        "connection refused",
        "terminating connection",
        "could not connect",
    ]
    return any(marker in message for marker in pause_markers)


def get_db_connection(retries: int = 2, retry_delay: float = 1.5) -> Optional[Engine]:
    """Create a SQLAlchemy engine for Supabase with basic retry handling.

    Args:
        retries: Number of retry attempts for transient errors.
        retry_delay: Seconds to wait between retry attempts.

    Returns:
        A SQLAlchemy Engine if successful; otherwise None.
    """
    db_url = os.getenv("DATABASE_URL")

    if not db_url:
        raise ValueError("DATABASE_URL not found. Please check your .env file.")

    last_error: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            engine = create_engine(db_url, pool_pre_ping=True)
            with engine.connect():
                pass
            return engine
        except OperationalError as exc:
            last_error = exc
            if attempt < retries and _is_transient_db_error(exc):
                time.sleep(retry_delay)
                continue
            break
        except SQLAlchemyError as exc:
            last_error = exc
            break

    print(f"Error connecting to database: {last_error}")
    return None


def safe_read_sql(query: str, engine: Engine) -> pd.DataFrame:
    """Run a SQL query and return a dataframe with defensive error handling.

    Args:
        query: SQL query to execute.
        engine: SQLAlchemy engine.

    Returns:
        A dataframe result, or an empty dataframe on failure.
    """
    try:
        return pd.read_sql(query, engine)
    except Exception as exc:
        print(f"Error reading SQL: {exc}")
        return pd.DataFrame()


def safe_to_sql(
    dataframe: pd.DataFrame,
    table_name: str,
    engine: Engine,
    if_exists: str = "replace",
    chunksize: int = 1000,
) -> None:
    """Write a dataframe to SQL with defensive error handling.

    Args:
        dataframe: Dataframe to persist.
        table_name: Destination table name.
        engine: SQLAlchemy engine.
        if_exists: Pandas if_exists mode.
        chunksize: Batch size for inserts.
    """
    try:
        dataframe.to_sql(table_name, engine, if_exists=if_exists, index=False, chunksize=chunksize)
    except Exception as exc:
        print(f"Error writing to SQL: {exc}")


def ensure_admin_tables(engine: Engine) -> None:
    """Ensure admin tables exist for target goals and system logs.

    Args:
        engine: SQLAlchemy engine.
    """
    create_target_goals = """
        CREATE TABLE IF NOT EXISTS target_goals (
            setting_key TEXT PRIMARY KEY,
            goal_value NUMERIC NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """
    create_system_logs = """
        CREATE TABLE IF NOT EXISTS system_logs (
            id BIGSERIAL PRIMARY KEY,
            log_level TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """
    with engine.begin() as conn:
        conn.execute(text(create_target_goals))
        conn.execute(text(create_system_logs))


def get_target_goal(engine: Engine, default_value: float = 0.0) -> float:
    """Fetch the latest target goal value from Supabase.

    Args:
        engine: SQLAlchemy engine.
        default_value: Fallback value when no goal is configured.

    Returns:
        The target goal value.
    """
    ensure_admin_tables(engine)
    query = """
        SELECT goal_value
        FROM target_goals
        WHERE setting_key = 'primary_target'
        LIMIT 1;
    """
    df = safe_read_sql(query, engine)
    if df.empty or "goal_value" not in df.columns:
        return default_value
    return float(df.iloc[0]["goal_value"])


def update_target_goal(engine: Engine, goal_value: float) -> None:
    """Create or update the target goal value.

    Args:
        engine: SQLAlchemy engine.
        goal_value: The target goal to store.
    """
    ensure_admin_tables(engine)
    upsert_sql = """
        INSERT INTO target_goals (setting_key, goal_value, updated_at)
        VALUES ('primary_target', :goal_value, NOW())
        ON CONFLICT (setting_key)
        DO UPDATE SET goal_value = EXCLUDED.goal_value, updated_at = NOW();
    """
    with engine.begin() as conn:
        conn.execute(text(upsert_sql), {"goal_value": goal_value})


def fetch_latest_logs(engine: Engine, limit: int = 50) -> pd.DataFrame:
    """Fetch recent system logs from Supabase.

    Args:
        engine: SQLAlchemy engine.
        limit: Maximum number of log rows to return.

    Returns:
        Dataframe of recent log entries.
    """
    ensure_admin_tables(engine)
    query = """
        SELECT id, log_level, message, created_at
        FROM system_logs
        ORDER BY created_at DESC
        LIMIT :limit;
    """
    try:
        return pd.read_sql(text(query), engine, params={"limit": limit})
    except Exception as exc:
        print(f"Error reading logs: {exc}")
        return pd.DataFrame()


def write_log(engine: Engine, log_level: str, message: str) -> None:
    """Write a system log row to Supabase.

    Args:
        engine: SQLAlchemy engine.
        log_level: Log severity label.
        message: Human-readable log message.
    """
    ensure_admin_tables(engine)
    insert_sql = """
        INSERT INTO system_logs (log_level, message)
        VALUES (:log_level, :message);
    """
    with engine.begin() as conn:
        conn.execute(text(insert_sql), {"log_level": log_level, "message": message})


def delete_processed_sales_data(engine: Engine, start_date: date, end_date: date) -> int:
    """Delete fact rows within a date range.

    Args:
        engine: SQLAlchemy engine.
        start_date: Inclusive start date.
        end_date: Inclusive end date.

    Returns:
        Count of rows deleted.
    """
    config = get_config()
    delete_sql = f"""
        DELETE FROM {config.fact_table_name}
        WHERE {config.date_col}::date >= :start_date
          AND {config.date_col}::date <= :end_date;
    """
    with engine.begin() as conn:
        result = conn.execute(text(delete_sql), {"start_date": start_date, "end_date": end_date})
        if config.legacy_fact_table_name != config.fact_table_name:
            conn.execute(text(f"DELETE FROM {config.legacy_fact_table_name} WHERE {config.date_col}::date >= :start_date AND {config.date_col}::date <= :end_date;"), {"start_date": start_date, "end_date": end_date})
        return int(result.rowcount or 0)

if __name__ == "__main__":
    # Test the connection when running this file directly
    engine = get_db_connection()
    if engine:
        print("Successfully connected to Supabase.")