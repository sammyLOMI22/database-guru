"""Normalize NoSQL query results to match SQLExecutor's return contract.

Every NoSQL executor pipes results through normalize_nosql_result() so that
downstream code (result narration, query history, frontend) works unchanged.
"""
import logging
from datetime import datetime, date
from decimal import Decimal
from typing import Any, Dict, List, Optional

try:
    from bson import ObjectId
except ImportError:
    ObjectId = None

logger = logging.getLogger(__name__)


def _serialize_value(value: Any) -> Any:
    """Serialize a single value for JSON transport.

    Mirrors SQLExecutor._serialize_value() to ensure consistent output.
    """
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8")
        except UnicodeDecodeError:
            return f"<binary {len(value)} bytes>"
    if isinstance(value, Decimal):
        return float(value)
    if ObjectId is not None and isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, dict):
        return {k: _serialize_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize_value(v) for v in value]
    return value


def normalize_nosql_result(
    data: List[Dict[str, Any]],
    execution_time_ms: float,
    error: Optional[str] = None,
    max_rows: int = 1000,
) -> Dict[str, Any]:
    """Convert raw NoSQL results to the SQLExecutor result contract.

    Args:
        data: List of document dicts from the NoSQL query
        execution_time_ms: Query execution time in milliseconds
        error: Error message if the query failed
        max_rows: Maximum rows to return (truncates beyond this)

    Returns:
        Dict matching SQLExecutor.execute_query() shape:
        {success, data, columns, row_count, execution_time_ms, truncated, error, compiled}
    """
    if error:
        return {
            "success": False,
            "data": [],
            "columns": [],
            "row_count": 0,
            "execution_time_ms": round(execution_time_ms, 2),
            "truncated": False,
            "error": error,
            "compiled": False,
        }

    truncated = len(data) > max_rows
    if truncated:
        data = data[:max_rows]

    # Extract column names from union of all keys across rows
    all_keys: set = set()
    for row in data:
        if isinstance(row, dict):
            all_keys.update(row.keys())
    columns = sorted(all_keys)

    # Serialize values for JSON transport
    serialized_data = []
    for row in data:
        if isinstance(row, dict):
            serialized_data.append(
                {k: _serialize_value(row.get(k)) for k in columns}
            )
        else:
            # Scalar result (e.g. from COUNT or DISTINCT)
            serialized_data.append({"value": _serialize_value(row)})
            if "value" not in columns:
                columns = ["value"]

    return {
        "success": True,
        "data": serialized_data,
        "columns": columns,
        "row_count": len(serialized_data),
        "execution_time_ms": round(execution_time_ms, 2),
        "truncated": truncated,
        "error": None,
        "compiled": False,
    }
