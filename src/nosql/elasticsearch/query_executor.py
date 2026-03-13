"""Elasticsearch query executor - runs Query DSL via AsyncElasticsearch."""
import asyncio
import logging
import time
from typing import Any, Dict, List

from src.nosql.result_formatter import normalize_nosql_result

logger = logging.getLogger(__name__)


class ElasticsearchQueryExecutor:
    """Execute Elasticsearch queries safely."""

    def __init__(
        self,
        client,  # AsyncElasticsearch
        max_results: int = 1000,
        timeout_seconds: int = 30,
        allow_write: bool = False,
    ):
        self.client = client
        self.max_results = max_results
        self.timeout_seconds = timeout_seconds
        self.allow_write = allow_write

    # Keys that indicate a write/mutate operation when found at top level
    _WRITE_TOP_LEVEL = frozenset({
        "update", "delete", "upsert", "doc", "doc_as_upsert",
    })

    # Keys that indicate scripting when found at any depth
    _SCRIPT_KEYS = frozenset({
        "script", "scripted_metric", "script_score", "script_fields",
    })

    def _contains_script(self, obj: Any) -> List[str]:
        """Recursively check for script-related keys in a nested dict."""
        found = []
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key in self._SCRIPT_KEYS:
                    found.append(key)
                else:
                    found.extend(self._contains_script(value))
        elif isinstance(obj, list):
            for item in obj:
                found.extend(self._contains_script(item))
        return found

    async def execute(self, query_dsl: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a Query DSL dict and return normalized results."""
        # Block write operations unless explicitly allowed
        if not self.allow_write:
            write_keys = self._WRITE_TOP_LEVEL & set(query_dsl.keys())
            if write_keys:
                return normalize_nosql_result(
                    data=[], execution_time_ms=0,
                    error=f"Write operation not allowed (found keys: {', '.join(write_keys)}). Enable allow_write.",
                )

            # Recursively check for script usage at any depth
            script_keys = self._contains_script(query_dsl)
            if script_keys:
                return normalize_nosql_result(
                    data=[], execution_time_ms=0,
                    error=f"Script execution not allowed (found: {', '.join(set(script_keys))}). Enable allow_write.",
                )

        start_time = time.time()

        try:
            result = await asyncio.wait_for(
                self._execute_search(query_dsl),
                timeout=self.timeout_seconds,
            )
            elapsed_ms = (time.time() - start_time) * 1000
            return normalize_nosql_result(
                data=result, execution_time_ms=elapsed_ms,
                max_rows=self.max_results,
            )

        except asyncio.TimeoutError:
            elapsed_ms = (time.time() - start_time) * 1000
            return normalize_nosql_result(
                data=[], execution_time_ms=elapsed_ms,
                error=f"Query timed out after {self.timeout_seconds}s",
            )

        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            logger.error(f"Elasticsearch query error: {e}", exc_info=True)
            return normalize_nosql_result(
                data=[], execution_time_ms=elapsed_ms, error=str(e),
            )

    async def _execute_search(self, query_dsl: Dict[str, Any]) -> List[Dict]:
        """Execute search and flatten results."""
        index = query_dsl.get("index", "*")
        body = {k: v for k, v in query_dsl.items() if k != "index" and v is not None}

        # Enforce max_results server-side regardless of LLM-generated size
        body["size"] = min(body.get("size", self.max_results), self.max_results, 100)

        response = await self.client.search(index=index, body=body)

        rows = []

        # Extract hits
        hits = response.get("hits", {}).get("hits", [])
        for hit in hits:
            row = {"_id": hit.get("_id"), "_score": hit.get("_score")}
            source = hit.get("_source", {})
            row.update(self._flatten_source(source))
            rows.append(row)

        # Extract aggregation results (appended alongside hits if both present)
        aggs = response.get("aggregations", {})
        if aggs:
            agg_rows = self._flatten_aggregations(aggs)
            if rows:
                # Both hits and aggregations — return aggregations as a separate section
                for agg_row in agg_rows:
                    agg_row["_type"] = "aggregation"
                rows.extend(agg_rows)
            else:
                rows = agg_rows

        return rows

    def _flatten_source(self, source: Dict, prefix: str = "") -> Dict:
        """Flatten nested _source fields with dot notation."""
        result = {}
        for key, value in source.items():
            full_key = f"{prefix}{key}" if prefix else key
            if isinstance(value, dict) and prefix.count(".") < 2:
                result.update(self._flatten_source(value, f"{full_key}."))
            else:
                result[full_key] = value
        return result

    def _flatten_aggregations(self, aggs: Dict) -> List[Dict]:
        """Convert aggregation results to list of dicts."""
        rows = []
        for agg_name, agg_data in aggs.items():
            if "buckets" in agg_data:
                for bucket in agg_data["buckets"]:
                    row = {"key": bucket.get("key"), "doc_count": bucket.get("doc_count")}
                    # Include sub-aggregations
                    for sub_key, sub_val in bucket.items():
                        if isinstance(sub_val, dict) and "value" in sub_val:
                            row[sub_key] = sub_val["value"]
                    rows.append(row)
            elif "value" in agg_data:
                rows.append({agg_name: agg_data["value"]})

        return rows
