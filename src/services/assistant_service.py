from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Dict, List, Tuple

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.config import get_config
from src.utils import safe_read_sql


@dataclass
class AssistantConfig:
    """Configuration for the AI assistant."""

    model: str
    max_rows: int = 200


def _get_assistant_config() -> AssistantConfig:
    model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash-002")
    return AssistantConfig(model=model)


def _get_gemini_client():
    try:
        import google.generativeai as genai
    except ImportError as exc:  # pragma: no cover - handled by UI
        raise RuntimeError("Gemini SDK is not installed. Add 'google-generativeai' to requirements.txt") from exc

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set in the environment.")

    genai.configure(api_key=api_key)
    return genai


def get_target_tables() -> List[str]:
    """Return the primary and legacy table names used for analytics."""
    config = get_config()
    return [
        config.fact_table_name,
        config.forecast_table_name,
        config.legacy_fact_table_name,
        config.legacy_forecast_table_name,
    ]


def load_table_schema(engine: Engine, table_names: List[str]) -> pd.DataFrame:
    """Fetch column metadata for the requested tables."""
    if not table_names:
        return pd.DataFrame()

    placeholders = ", ".join([f":t{i}" for i in range(len(table_names))])
    query = text(
        f"""
        SELECT table_name, column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name IN ({placeholders})
        ORDER BY table_name, ordinal_position;
        """
    )
    params = {f"t{i}": name for i, name in enumerate(table_names)}
    return pd.read_sql(query, engine, params=params)


def build_schema_text(schema_df: pd.DataFrame) -> str:
    """Build a compact schema description for prompting."""
    if schema_df.empty:
        return "No schema metadata available."

    grouped: Dict[str, List[str]] = {}
    for _, row in schema_df.iterrows():
        grouped.setdefault(row["table_name"], []).append(f"{row['column_name']} ({row['data_type']})")

    lines = []
    for table, columns in grouped.items():
        lines.append(f"Table {table}: " + ", ".join(columns))
    return "\n".join(lines)


def _is_safe_sql(sql: str) -> bool:
    if not sql:
        return False

    normalized = sql.strip().lower()
    if not normalized.startswith("select"):
        return False

    banned = ["insert ", "update ", "delete ", "drop ", "alter ", "truncate ", "create ", "grant ", "revoke "]
    if any(keyword in normalized for keyword in banned):
        return False

    if ";" in normalized:
        return False

    return True


def _enforce_limit(sql: str, max_rows: int) -> str:
    if re.search(r"\blimit\s+\d+\b", sql, re.IGNORECASE):
        return sql
    return f"{sql} LIMIT {max_rows}"


def _resolve_model_name(genai, preferred: str) -> str:
    """Pick a model that supports generateContent, falling back when needed."""
    try:
        models = list(genai.list_models())
    except Exception:
        return preferred

    supported = [m.name.replace("models/", "") for m in models if "generateContent" in getattr(m, "supported_generation_methods", [])]
    if not supported:
        return preferred
    if preferred in supported:
        return preferred

    # Prefer a Gemini 1.5 flash/pro model when available.
    for candidate in supported:
        if candidate.startswith("gemini-1.5-flash"):
            return candidate
    for candidate in supported:
        if candidate.startswith("gemini-1.5"):
            return candidate
    return supported[0]


def _is_data_question(question: str, schema_df: pd.DataFrame) -> bool:
    if not question or not question.strip():
        return False

    normalized = question.lower()
    data_keywords = [
        "data",
        "dataset",
        "table",
        "column",
        "row",
        "rows",
        "count",
        "sum",
        "total",
        "average",
        "trend",
        "kpi",
        "metric",
        "sales",
        "revenue",
        "orders",
        "forecast",
        "customers",
        "products",
        "payments",
    ]
    if any(keyword in normalized for keyword in data_keywords):
        return True

    if schema_df.empty:
        return False

    table_names = {str(name).lower() for name in schema_df["table_name"].unique()}
    column_names = {str(name).lower() for name in schema_df["column_name"].unique()}
    if any(name in normalized for name in table_names):
        return True
    if any(name in normalized for name in column_names):
        return True

    return False


def generate_general_response(question: str) -> Tuple[str, str]:
    """Generate a non-SQL conversational response."""
    config = _get_assistant_config()
    genai = _get_gemini_client()
    prompt = (
        "You are a helpful assistant for the DataPulse app.\n"
        "Respond conversationally.\n"
        "If the user asks for data analysis, ask them to rephrase as a data question.\n"
        f"Question: {question}\n"
    )

    model_name = _resolve_model_name(genai, config.model)
    model = genai.GenerativeModel(model_name)
    response = model.generate_content(prompt)
    answer = (response.text or "").strip()
    return answer, model_name


def generate_sql(question: str, schema_text: str) -> Tuple[str, str]:
    """Generate SQL for a user question. Returns (sql, model)."""
    config = _get_assistant_config()
    genai = _get_gemini_client()

    prompt = (
        "You are a SQL analyst for a PostgreSQL database.\n"
        "Return only a single SQL SELECT statement and nothing else.\n"
        "Rules: use only the tables listed in the schema, avoid semicolons, include a LIMIT clause if needed.\n"
        f"Schema:\n{schema_text}\n"
        f"Question: {question}\n"
    )

    model_name = _resolve_model_name(genai, config.model)
    model = genai.GenerativeModel(model_name)
    response = model.generate_content(prompt)
    sql = (response.text or "").strip()
    sql = _enforce_limit(sql, config.max_rows)
    return sql, model_name


def _summarize_dataframe(dataframe: pd.DataFrame) -> str:
    if dataframe.empty:
        return "No rows returned."

    summary_lines = [f"Rows: {len(dataframe):,}", f"Columns: {', '.join(dataframe.columns)}"]

    for col in dataframe.columns:
        if pd.api.types.is_datetime64_any_dtype(dataframe[col]):
            min_v = dataframe[col].min()
            max_v = dataframe[col].max()
            summary_lines.append(f"{col} range: {min_v} to {max_v}")
        elif pd.api.types.is_numeric_dtype(dataframe[col]):
            summary_lines.append(f"{col} sum: {dataframe[col].sum():,.2f}")

    preview = dataframe.head(50).to_csv(index=False)
    summary_lines.append("Preview:\n" + preview)
    return "\n".join(summary_lines)


def generate_answer(question: str, sql: str, dataframe: pd.DataFrame, schema_text: str) -> Tuple[str, str]:
    """Generate a natural language answer from query results."""
    config = _get_assistant_config()
    summary = _summarize_dataframe(dataframe)

    prompt = (
        "You are a business analytics assistant.\n"
        "Answer the question using the provided SQL and data summary.\n"
        "Provide concise insights and 2-3 recommendations if applicable.\n"
        "If the data is insufficient, say what is missing.\n"
        f"Schema:\n{schema_text}\n"
        f"SQL:\n{sql}\n"
        f"Data Summary:\n{summary}\n"
        f"Question: {question}\n"
    )

    genai = _get_gemini_client()
    model_name = _resolve_model_name(genai, config.model)
    model = genai.GenerativeModel(model_name)
    response = model.generate_content(prompt)
    answer = (response.text or "").strip()
    return answer, model_name


def run_question(engine: Engine, question: str) -> Tuple[str, str, pd.DataFrame, str]:
    """Run the full assistant pipeline: schema -> SQL -> query -> answer."""
    table_names = get_target_tables()
    schema_df = load_table_schema(engine, table_names)
    schema_text = build_schema_text(schema_df)

    if not _is_data_question(question, schema_df):
        answer, model = generate_general_response(question)
        return "", answer, pd.DataFrame(), model

    sql, model = generate_sql(question, schema_text)
    if not _is_safe_sql(sql):
        message = "I couldn't generate a safe SQL query. Please rephrase as a data question."
        return "", message, pd.DataFrame(), model

    dataframe = safe_read_sql(sql, engine)
    answer, _ = generate_answer(question, sql, dataframe, schema_text)
    return sql, answer, dataframe, model
