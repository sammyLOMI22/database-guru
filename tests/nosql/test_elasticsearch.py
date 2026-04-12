"""Tests for Elasticsearch NoSQL support."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.nosql.elasticsearch.error_classifier import classify_error
from src.nosql.elasticsearch.query_dsl_generator import QueryDSLGenerator
from src.nosql.elasticsearch.query_executor import ElasticsearchQueryExecutor
from src.nosql.elasticsearch.schema_inspector import ElasticsearchSchemaInspector
from src.llm.self_correcting_agent import ErrorType


# ── Elasticsearch error classifier ───────────────────────────────────────

class TestElasticsearchErrorClassifier:
    def test_index_not_found(self):
        error_type, _ = classify_error("index_not_found_exception: no such index [missing]")
        assert error_type == ErrorType.TABLE_NOT_FOUND

    def test_field_not_found(self):
        error_type, _ = classify_error("unknown field [bad_field] in mapping")
        assert error_type == ErrorType.COLUMN_NOT_FOUND

    def test_no_mapping(self):
        error_type, _ = classify_error("no mapping found for [field] in order to sort on")
        assert error_type == ErrorType.COLUMN_NOT_FOUND

    def test_parsing_exception(self):
        error_type, _ = classify_error("parsing_exception: Expected [VALUE] but got [END]")
        assert error_type == ErrorType.SYNTAX_ERROR

    def test_query_shard_exception(self):
        error_type, _ = classify_error("query_shard_exception: failed to create query")
        assert error_type == ErrorType.SYNTAX_ERROR

    def test_illegal_argument(self):
        error_type, _ = classify_error("illegal_argument_exception: invalid value for parameter")
        assert error_type == ErrorType.TYPE_MISMATCH

    def test_security(self):
        error_type, _ = classify_error("security_exception: missing authentication")
        assert error_type == ErrorType.PERMISSION_DENIED

    def test_timeout(self):
        error_type, _ = classify_error("timeout: query phase exceeded")
        assert error_type == ErrorType.TIMEOUT

    def test_unknown(self):
        error_type, _ = classify_error("some elastic error")
        assert error_type == ErrorType.UNKNOWN


# ── Query DSL generator ──────────────────────────────────────────────────

class TestQueryDSLGenerator:
    def setup_method(self):
        self.gen = QueryDSLGenerator(MagicMock())

    def test_parse_direct_json(self):
        response = json.dumps({
            "index": "logs",
            "query": {"match": {"message": "error"}},
            "size": 50,
        })
        result = self.gen._parse_response(response)
        assert result["index"] == "logs"
        assert result["query"]["match"]["message"] == "error"

    def test_parse_json_in_code_block(self):
        response = '```json\n{"index": "users", "query": {"match_all": {}}}\n```'
        result = self.gen._parse_response(response)
        assert result["index"] == "users"

    def test_parse_json_surrounded_by_text(self):
        response = 'Here is the query:\n{"index": "products", "query": {"term": {"status": "active"}}}\nDone.'
        result = self.gen._parse_response(response)
        assert result["index"] == "products"

    def test_parse_invalid_raises(self):
        with pytest.raises(ValueError, match="No JSON found"):
            self.gen._parse_response("not json at all")

    def test_display_string(self):
        query = {"index": "logs", "query": {"match_all": {}}, "size": 10}
        s = self.gen.query_to_display_string(query)
        assert "GET /logs/_search" in s
        assert "match_all" in s

    def test_display_string_excludes_index(self):
        query = {"index": "users", "query": {"match_all": {}}}
        s = self.gen.query_to_display_string(query)
        # Body should not contain "index" key
        body_part = s.split("\n", 1)[1] if "\n" in s else ""
        parsed = json.loads(body_part) if body_part else {}
        assert "index" not in parsed

    @pytest.mark.asyncio
    async def test_generate(self):
        ollama = AsyncMock()
        ollama.generate.return_value = json.dumps({
            "index": "logs",
            "query": {"match": {"level": "error"}},
        })
        gen = QueryDSLGenerator(ollama)
        result = await gen.generate(question="show errors", schema="ES schema")
        assert result["index"] == "logs"
        ollama.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_with_error_context(self):
        ollama = AsyncMock()
        ollama.generate.return_value = json.dumps({
            "index": "logs",
            "query": {"match": {"level": "error"}},
        })
        gen = QueryDSLGenerator(ollama)
        result = await gen.generate_with_error_context(
            question="show errors",
            schema="ES schema",
            previous_query="GET /log/_search",
            error_message="index_not_found",
        )
        assert result["index"] == "logs"
        # Verify error context was included in prompt
        call_args = ollama.generate.call_args
        prompt = call_args.kwargs.get("prompt", "")
        assert "PREVIOUS ATTEMPT FAILED" in prompt


# ── Elasticsearch query executor ─────────────────────────────────────────

class TestElasticsearchQueryExecutor:
    @pytest.mark.asyncio
    async def test_execute_search_hits(self):
        mock_client = AsyncMock()
        mock_client.search.return_value = {
            "hits": {
                "total": {"value": 2},
                "hits": [
                    {"_id": "1", "_score": 1.5, "_source": {"name": "Alice", "age": 30}},
                    {"_id": "2", "_score": 1.2, "_source": {"name": "Bob", "age": 25}},
                ],
            },
        }

        executor = ElasticsearchQueryExecutor(client=mock_client, max_results=100)
        query_dsl = {"index": "users", "query": {"match_all": {}}}
        result = await executor.execute(query_dsl)

        assert result["success"] is True
        assert result["row_count"] == 2
        # Check flattened data
        assert result["data"][0]["name"] == "Alice"
        assert result["data"][0]["_id"] == "1"

    @pytest.mark.asyncio
    async def test_execute_aggregation(self):
        mock_client = AsyncMock()
        mock_client.search.return_value = {
            "hits": {"total": {"value": 0}, "hits": []},
            "aggregations": {
                "status_count": {
                    "buckets": [
                        {"key": "active", "doc_count": 100},
                        {"key": "inactive", "doc_count": 20},
                    ]
                }
            },
        }

        executor = ElasticsearchQueryExecutor(client=mock_client)
        query_dsl = {
            "index": "users",
            "query": {"match_all": {}},
            "aggs": {"status_count": {"terms": {"field": "status"}}},
            "size": 0,
        }
        result = await executor.execute(query_dsl)

        assert result["success"] is True
        assert result["row_count"] == 2
        assert result["data"][0]["key"] == "active"
        assert result["data"][0]["doc_count"] == 100

    @pytest.mark.asyncio
    async def test_execute_timeout(self):
        mock_client = AsyncMock()
        mock_client.search.side_effect = Exception("timeout: query exceeded")

        executor = ElasticsearchQueryExecutor(client=mock_client, timeout_seconds=5)
        result = await executor.execute({"index": "logs", "query": {}})

        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_default_size_applied(self):
        mock_client = AsyncMock()
        mock_client.search.return_value = {"hits": {"hits": []}}

        executor = ElasticsearchQueryExecutor(client=mock_client, max_results=200)
        await executor.execute({"index": "logs", "query": {"match_all": {}}})

        call_kwargs = mock_client.search.call_args
        body = call_kwargs.kwargs.get("body", call_kwargs[1].get("body", {}))
        assert body.get("size") == 100  # min(max_results, 100)

    @pytest.mark.asyncio
    async def test_nested_source_flattened(self):
        mock_client = AsyncMock()
        mock_client.search.return_value = {
            "hits": {
                "hits": [
                    {
                        "_id": "1",
                        "_score": 1.0,
                        "_source": {
                            "name": "Alice",
                            "address": {"city": "NYC", "zip": "10001"},
                        },
                    }
                ],
            },
        }

        executor = ElasticsearchQueryExecutor(client=mock_client)
        result = await executor.execute({"index": "users", "query": {}})

        assert result["success"] is True
        row = result["data"][0]
        assert row["address.city"] == "NYC"
        assert row["address.zip"] == "10001"


# ── Elasticsearch schema inspector ───────────────────────────────────────

class TestElasticsearchSchemaInspector:
    @pytest.mark.asyncio
    async def test_get_schema(self):
        mock_client = AsyncMock()
        mock_client.cat.indices.return_value = [
            {"index": "users", "docs.count": "1500"},
            {"index": ".kibana", "docs.count": "10"},  # system index, should be skipped
        ]
        mock_client.indices.get_mapping.return_value = {
            "users": {
                "mappings": {
                    "properties": {
                        "name": {"type": "text"},
                        "age": {"type": "integer"},
                        "email": {"type": "keyword"},
                    }
                }
            }
        }

        inspector = ElasticsearchSchemaInspector(mock_client)
        schema = await inspector.get_schema()

        assert "users" in schema["tables"]
        assert ".kibana" not in schema["tables"]
        assert schema["tables"]["users"]["row_count"] == 1500

        col_names = [c["name"] for c in schema["tables"]["users"]["columns"]]
        assert "name" in col_names
        assert "age" in col_names
        assert "email" in col_names

    @pytest.mark.asyncio
    async def test_nested_properties(self):
        mock_client = AsyncMock()
        mock_client.cat.indices.return_value = [
            {"index": "events", "docs.count": "100"},
        ]
        mock_client.indices.get_mapping.return_value = {
            "events": {
                "mappings": {
                    "properties": {
                        "timestamp": {"type": "date"},
                        "user": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "keyword"},
                                "name": {"type": "text"},
                            },
                        },
                    }
                }
            }
        }

        inspector = ElasticsearchSchemaInspector(mock_client)
        schema = await inspector.get_schema()

        col_names = [c["name"] for c in schema["tables"]["events"]["columns"]]
        assert "timestamp" in col_names
        assert "user" in col_names
        assert "user.id" in col_names
        assert "user.name" in col_names

    def test_format_schema_for_llm(self):
        schema = {
            "tables": {
                "logs": {
                    "columns": [
                        {"name": "message", "type": "text"},
                        {"name": "level", "type": "keyword"},
                    ],
                    "row_count": 5000,
                },
            },
            "database_type": "elasticsearch",
        }

        inspector = ElasticsearchSchemaInspector(MagicMock())
        output = inspector.format_schema_for_llm(schema)

        assert "Elasticsearch" in output
        assert "logs" in output
        assert "5000" in output
        assert "message: text" in output
        assert "level: keyword" in output


# ── Elasticsearch handler ────────────────────────────────────────────────

class TestElasticsearchHandler:
    @pytest.mark.asyncio
    async def test_handler_error_result(self):
        from src.nosql.elasticsearch.handler import ElasticsearchHandler

        conn = MagicMock()
        conn.name = "test_es"
        conn.database_type = "elasticsearch"

        with patch("src.nosql.elasticsearch.handler.ElasticsearchClientPool.get_instance", side_effect=Exception("Connection refused")):
            handler = ElasticsearchHandler()
            result = await handler.handle(question="search logs", connection=conn)

        assert result["success"] is False
        assert "Connection refused" in result["error"]
        assert result["agent_trace"] is not None

    @pytest.mark.asyncio
    async def test_handler_success_shape(self):
        from src.nosql.elasticsearch.handler import ElasticsearchHandler

        mock_es = AsyncMock()
        mock_es.search.return_value = {
            "hits": {"hits": [{"_id": "1", "_score": 1.0, "_source": {"msg": "hello"}}]},
        }

        mock_pool = AsyncMock()
        mock_pool.get_client.return_value = mock_es

        mock_ollama = AsyncMock()
        mock_ollama.client = True
        mock_ollama.generate.return_value = json.dumps({
            "index": "logs",
            "query": {"match_all": {}},
        })

        mock_schema = {
            "tables": {"logs": {"columns": [{"name": "msg", "type": "text"}], "row_count": 100}},
            "database_type": "elasticsearch",
        }

        conn = MagicMock()
        conn.name = "test_es"
        conn.database_type = "elasticsearch"
        conn.schema_cache = None

        with patch("src.nosql.elasticsearch.handler.ElasticsearchClientPool.get_instance", return_value=mock_pool), \
             patch("src.nosql.elasticsearch.handler.get_llm_client", return_value=mock_ollama), \
             patch("src.nosql.elasticsearch.handler.ElasticsearchSchemaInspector") as MockInspector:

            mock_inspector = AsyncMock()
            mock_inspector.get_schema.return_value = mock_schema
            mock_inspector.format_schema_for_llm.return_value = "DATABASE: Elasticsearch"
            MockInspector.return_value = mock_inspector

            handler = ElasticsearchHandler()
            result = await handler.handle(question="search logs", connection=conn)

        assert result["success"] is True
        assert "sql" in result
        assert "result" in result
        assert "attempts" in result
        assert "agent_trace" in result
        assert result["total_attempts"] == 1
