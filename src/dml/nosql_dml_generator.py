"""NoSQL DML generator — translates RowChangeSchema to native write operations.

Deterministic translation (no LLM). Each NoSQL database type gets its own
method set that produces DMLStatement objects with a native_operation dict
the executor can dispatch directly.
"""
import json
import logging
from typing import Any, Dict, List

from src.dml.models import ChangeType, DMLStatement, RowChangeSchema

logger = logging.getLogger(__name__)


class NoSQLDMLGenerator:
    """Generate native NoSQL write operations from RowChangeSchema objects."""

    def __init__(self, database_type: str):
        self.database_type = database_type
        self._gen = _GENERATORS.get(database_type)
        if not self._gen:
            raise ValueError(f"Unsupported NoSQL type for DML: {database_type}")

    def generate_statements(
        self, changes: List[RowChangeSchema]
    ) -> List[DMLStatement]:
        """Convert a list of row changes to DMLStatements with native_operation."""
        # Order: DELETE first, then UPDATE, then INSERT (same as SQL DML)
        ordered = sorted(changes, key=lambda c: _OP_ORDER.get(c.change_type, 9))
        return [self._gen(c) for c in ordered]

    def generate_preview_script(
        self, changes: List[RowChangeSchema]
    ) -> str:
        """Human-readable preview string for all statements."""
        stmts = self.generate_statements(changes)
        return "\n".join(s.display_sql for s in stmts)


_OP_ORDER = {ChangeType.DELETE: 0, ChangeType.UPDATE: 1, ChangeType.INSERT: 2}


# ── Helpers ─────────────────────────────────────────────────────────


def _json_val(v: Any) -> str:
    """Format a value for display (JSON-ish)."""
    if v is None:
        return "null"
    if isinstance(v, str):
        return json.dumps(v)
    return str(v)


# ── MongoDB ─────────────────────────────────────────────────────────


def _mongo_generate(change: RowChangeSchema) -> DMLStatement:
    collection = change.table_name
    pk = change.primary_key

    if change.change_type == ChangeType.INSERT:
        doc = change.new_row_data or {}
        display = f"db.{collection}.insertOne({json.dumps(doc, default=str)})"
        native = {
            "method": "insert_one",
            "collection": collection,
            "document": doc,
        }

    elif change.change_type == ChangeType.UPDATE:
        updates = {c.column: c.new_value for c in change.changes}
        display = (
            f"db.{collection}.updateOne("
            f"{json.dumps(pk, default=str)}, "
            f"{{$set: {json.dumps(updates, default=str)}}})"
        )
        native = {
            "method": "update_one",
            "collection": collection,
            "filter": pk,
            "update": {"$set": updates},
        }

    else:  # DELETE
        display = f"db.{collection}.deleteOne({json.dumps(pk, default=str)})"
        native = {
            "method": "delete_one",
            "collection": collection,
            "filter": pk,
        }

    return DMLStatement(
        display_sql=display,
        parameterized_sql=display,
        change_type=change.change_type,
        table_name=collection,
        native_operation=native,
    )


# ── Cassandra (CQL) ────────────────────────────────────────────────


def _cassandra_generate(change: RowChangeSchema) -> DMLStatement:
    table = change.table_name

    if change.change_type == ChangeType.INSERT:
        doc = change.new_row_data or {}
        cols = ", ".join(doc.keys())
        vals = ", ".join(_cql_val(v) for v in doc.values())
        display = f"INSERT INTO {table} ({cols}) VALUES ({vals})"
        native = {
            "cql": f"INSERT INTO {table} ({cols}) VALUES ({', '.join(['%s'] * len(doc))})",
            "params": list(doc.values()),
        }

    elif change.change_type == ChangeType.UPDATE:
        sets = ", ".join(
            f"{c.column} = {_cql_val(c.new_value)}" for c in change.changes
        )
        where = " AND ".join(
            f"{k} = {_cql_val(v)}" for k, v in change.primary_key.items()
        )
        display = f"UPDATE {table} SET {sets} WHERE {where}"

        set_placeholders = ", ".join(f"{c.column} = %s" for c in change.changes)
        where_placeholders = " AND ".join(f"{k} = %s" for k in change.primary_key)
        params = [c.new_value for c in change.changes] + list(
            change.primary_key.values()
        )
        native = {
            "cql": f"UPDATE {table} SET {set_placeholders} WHERE {where_placeholders}",
            "params": params,
        }

    else:  # DELETE
        where = " AND ".join(
            f"{k} = {_cql_val(v)}" for k, v in change.primary_key.items()
        )
        display = f"DELETE FROM {table} WHERE {where}"

        where_placeholders = " AND ".join(f"{k} = %s" for k in change.primary_key)
        native = {
            "cql": f"DELETE FROM {table} WHERE {where_placeholders}",
            "params": list(change.primary_key.values()),
        }

    return DMLStatement(
        display_sql=display,
        parameterized_sql=display,
        change_type=change.change_type,
        table_name=table,
        native_operation=native,
    )


def _cql_val(v: Any) -> str:
    """Format a value for CQL display."""
    if v is None:
        return "null"
    if isinstance(v, str):
        return f"'{v.replace(chr(39), chr(39)+chr(39))}'"
    return str(v)


# ── DynamoDB (PartiQL) ─────────────────────────────────────────────


def _dynamodb_generate(change: RowChangeSchema) -> DMLStatement:
    table = change.table_name
    quoted_table = f'"{table}"'

    if change.change_type == ChangeType.INSERT:
        doc = change.new_row_data or {}
        val_str = ", ".join(
            f"'{k}': {_partiql_val(v)}" for k, v in doc.items()
        )
        display = f"INSERT INTO {quoted_table} VALUE {{{val_str}}}"
        # Use ? placeholders for safe parameterized execution
        param_val_str = ", ".join(f"'{k}': ?" for k in doc)
        parameterized = f"INSERT INTO {quoted_table} VALUE {{{param_val_str}}}"
        native = {
            "partiql": parameterized,
            "parameters": [_partiql_typed(v) for v in doc.values()],
        }

    elif change.change_type == ChangeType.UPDATE:
        sets = ", ".join(
            f"{c.column} = {_partiql_val(c.new_value)}" for c in change.changes
        )
        where = " AND ".join(
            f"{k} = {_partiql_val(v)}" for k, v in change.primary_key.items()
        )
        display = f"UPDATE {quoted_table} SET {sets} WHERE {where}"
        param_sets = ", ".join(f"{c.column} = ?" for c in change.changes)
        param_where = " AND ".join(f"{k} = ?" for k in change.primary_key)
        parameterized = f"UPDATE {quoted_table} SET {param_sets} WHERE {param_where}"
        native = {
            "partiql": parameterized,
            "parameters": (
                [_partiql_typed(c.new_value) for c in change.changes]
                + [_partiql_typed(v) for v in change.primary_key.values()]
            ),
        }

    else:  # DELETE
        where = " AND ".join(
            f"{k} = {_partiql_val(v)}" for k, v in change.primary_key.items()
        )
        display = f"DELETE FROM {quoted_table} WHERE {where}"
        param_where = " AND ".join(f"{k} = ?" for k in change.primary_key)
        parameterized = f"DELETE FROM {quoted_table} WHERE {param_where}"
        native = {
            "partiql": parameterized,
            "parameters": [_partiql_typed(v) for v in change.primary_key.values()],
        }

    return DMLStatement(
        display_sql=display,
        parameterized_sql=display,
        change_type=change.change_type,
        table_name=table,
        native_operation=native,
    )


def _partiql_val(v: Any) -> str:
    """Format a value for PartiQL display."""
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    return f"'{v}'"


def _partiql_typed(v: Any) -> Dict[str, Any]:
    """Convert a Python value to a DynamoDB typed parameter dict."""
    if v is None:
        return {"NULL": True}
    if isinstance(v, bool):
        return {"BOOL": v}
    if isinstance(v, int):
        return {"N": str(v)}
    if isinstance(v, float):
        return {"N": str(v)}
    return {"S": str(v)}


# ── Elasticsearch ──────────────────────────────────────────────────


def _elasticsearch_generate(change: RowChangeSchema) -> DMLStatement:
    index = change.table_name
    doc_id = change.primary_key.get("_id")

    if change.change_type == ChangeType.INSERT:
        doc = change.new_row_data or {}
        display = f"POST /{index}/_doc\n{json.dumps(doc, indent=2, default=str)}"
        body = {k: v for k, v in doc.items() if k != "_id"}
        native = {
            "method": "index",
            "index": index,
            "body": body,
        }
        # If new_row_data has _id, use it as the document ID
        if doc.get("_id"):
            native["id"] = str(doc["_id"])

    elif change.change_type == ChangeType.UPDATE:
        updates = {c.column: c.new_value for c in change.changes}
        display = (
            f"POST /{index}/_update/{doc_id}\n"
            f'{json.dumps({"doc": updates}, indent=2, default=str)}'
        )
        native = {
            "method": "update",
            "index": index,
            "id": str(doc_id),
            "body": {"doc": updates},
        }

    else:  # DELETE
        display = f"DELETE /{index}/_doc/{doc_id}"
        native = {
            "method": "delete",
            "index": index,
            "id": str(doc_id),
        }

    return DMLStatement(
        display_sql=display,
        parameterized_sql=display,
        change_type=change.change_type,
        table_name=index,
        native_operation=native,
    )


# ── Redis (HASH only) ─────────────────────────────────────────────


def _redis_generate(change: RowChangeSchema) -> DMLStatement:
    key = change.table_name

    if change.change_type == ChangeType.INSERT:
        doc = change.new_row_data or {}
        pairs = " ".join(f"{k} {_json_val(v)}" for k, v in doc.items())
        display = f"HSET {key} {pairs}"
        native = {
            "command": "HSET",
            "key": key,
            "mapping": doc,
        }

    elif change.change_type == ChangeType.UPDATE:
        updates = {c.column: c.new_value for c in change.changes}
        pairs = " ".join(f"{k} {_json_val(v)}" for k, v in updates.items())
        display = f"HSET {key} {pairs}"
        native = {
            "command": "HSET",
            "key": key,
            "mapping": updates,
        }

    else:  # DELETE
        # If specific fields are in changes, delete those fields; otherwise delete the key
        fields = [c.column for c in change.changes] if change.changes else []
        if fields:
            display = f"HDEL {key} {' '.join(fields)}"
            native = {
                "command": "HDEL",
                "key": key,
                "fields": fields,
            }
        else:
            display = f"DEL {key}"
            native = {
                "command": "DEL",
                "key": key,
            }

    return DMLStatement(
        display_sql=display,
        parameterized_sql=display,
        change_type=change.change_type,
        table_name=key,
        native_operation=native,
    )


# ── Registry ───────────────────────────────────────────────────────

_GENERATORS = {
    "mongodb": _mongo_generate,
    "cassandra": _cassandra_generate,
    "dynamodb": _dynamodb_generate,
    "elasticsearch": _elasticsearch_generate,
    "redis": _redis_generate,
}
