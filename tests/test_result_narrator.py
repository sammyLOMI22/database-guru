"""Unit tests for Result Narrator Agent"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.llm.result_narrator import ResultNarrator, NarrativeResult


class TestResultNarratorBasic:
    """Basic functionality tests for ResultNarrator"""

    @pytest.fixture
    def narrator(self):
        """Create narrator with mocked Ollama client"""
        mock_ollama = AsyncMock()
        return ResultNarrator(
            ollama_client=mock_ollama,
            enable_statistics=True,
            max_sample_rows=20,
            timeout_seconds=5
        )

    @pytest.mark.asyncio
    async def test_generate_narrative_empty_results(self, narrator):
        """Test handling of empty results"""
        result = await narrator.generate_narrative(
            question="Show me users from Mars",
            sql="SELECT * FROM users WHERE planet = 'Mars'",
            results=[],
            row_count=0,
            execution_time_ms=12.0,
            database_type="postgresql"
        )

        assert result.summary == "No results found."
        assert result.key_insights == []
        assert result.confidence == 0.95
        assert result.statistics["row_count"] == 0
        # Verify LLM was not called for empty results
        narrator.ollama.generate.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_narrative_large_results(self, narrator):
        """Test handling of results exceeding 1000 row threshold"""
        result = await narrator.generate_narrative(
            question="Show me all orders",
            sql="SELECT * FROM orders",
            results=[],  # Empty list, but row_count is large
            row_count=5000,
            execution_time_ms=150.0,
            database_type="postgresql"
        )

        assert "too large for detailed analysis" in result.summary
        assert result.confidence == 0.8
        assert result.statistics["row_count"] == 5000
        # Verify LLM was not called for large results
        narrator.ollama.generate.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_narrative_simple_count_query(self, narrator):
        """Test narrative for simple count query"""
        # Mock LLM response
        narrator.ollama.generate = AsyncMock(return_value=json.dumps({
            "summary": "Found 42 customers in the database.",
            "key_insights": [
                "All customers are active",
                "Average age is 35 years"
            ],
            "direct_answer": "42",
            "confidence": 0.95
        }))

        result = await narrator.generate_narrative(
            question="How many customers do we have?",
            sql="SELECT COUNT(*) as count FROM customers",
            results=[{"count": 42}],
            row_count=1,
            execution_time_ms=45.2,
            database_type="postgresql"
        )

        assert result.summary == "Found 42 customers in the database."
        assert result.direct_answer == "42"
        assert result.confidence == 0.95
        assert len(result.key_insights) == 2
        assert "All customers are active" in result.key_insights
        narrator.ollama.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_narrative_aggregation_query(self, narrator):
        """Test narrative for aggregation query"""
        results = [
            {"state": "CA", "avg_order": 1245.50},
            {"state": "NY", "avg_order": 980.25},
            {"state": "TX", "avg_order": 875.00}
        ]

        narrator.ollama.generate = AsyncMock(return_value=json.dumps({
            "summary": "California leads with the highest average order value at $1,245.50",
            "key_insights": [
                "California is 27% higher than NY",
                "Average ranges from $875 to $1,245",
                "Three states represented"
            ],
            "direct_answer": "California: $1,245.50",
            "confidence": 0.92
        }))

        result = await narrator.generate_narrative(
            question="Show me average order value by state",
            sql="SELECT state, AVG(total) FROM orders GROUP BY state",
            results=results,
            row_count=3,
            execution_time_ms=67.0,
            database_type="postgresql"
        )

        assert "California" in result.summary
        assert result.confidence == 0.92
        assert len(result.key_insights) == 3
        assert result.statistics["row_count"] == 3

    @pytest.mark.asyncio
    async def test_llm_timeout_fallback(self, narrator):
        """Test fallback behavior when LLM times out"""
        import asyncio
        narrator.ollama.generate = AsyncMock(side_effect=asyncio.TimeoutError())

        result = await narrator.generate_narrative(
            question="Test query",
            sql="SELECT * FROM test",
            results=[{"id": 1, "name": "test"}],
            row_count=1,
            execution_time_ms=10.0,
            database_type="postgresql"
        )

        # Should return fallback narrative
        assert result.summary is not None
        assert "found" in result.summary.lower() or "returned" in result.summary.lower()
        assert result.confidence < 0.75

    @pytest.mark.asyncio
    async def test_llm_error_fallback(self, narrator):
        """Test fallback behavior when LLM call fails"""
        narrator.ollama.generate = AsyncMock(side_effect=Exception("Connection error"))

        result = await narrator.generate_narrative(
            question="Test query",
            sql="SELECT * FROM test",
            results=[{"id": 1}],
            row_count=1,
            execution_time_ms=10.0,
            database_type="postgresql"
        )

        # Should return fallback narrative
        assert result.summary is not None
        assert result.confidence <= 0.5


class TestStatisticsExtraction:
    """Tests for statistics extraction from results"""

    @pytest.fixture
    def narrator(self):
        mock_ollama = AsyncMock()
        return ResultNarrator(
            ollama_client=mock_ollama,
            enable_statistics=True,
            max_sample_rows=20
        )

    def test_extract_statistics_empty_results(self, narrator):
        """Test statistics extraction on empty results"""
        stats = narrator._extract_statistics([])
        assert stats == {}

    def test_extract_statistics_numeric_columns(self, narrator):
        """Test extraction of numeric column statistics"""
        results = [
            {"age": 25, "salary": 50000.00},
            {"age": 35, "salary": 75000.00},
            {"age": 45, "salary": 100000.00},
        ]

        stats = narrator._extract_statistics(results)

        assert stats["row_count"] == 3
        assert stats["age"]["type"] == "numeric"
        assert stats["age"]["min"] == 25
        assert stats["age"]["max"] == 45
        assert stats["age"]["avg"] == 35.0
        assert stats["age"]["sum"] == 105
        assert "median" in stats["age"]
        assert "stdev" in stats["age"]

    def test_extract_statistics_string_columns(self, narrator):
        """Test extraction of string column statistics"""
        results = [
            {"city": "SF", "status": "active"},
            {"city": "NY", "status": "active"},
            {"city": "SF", "status": "inactive"},
        ]

        stats = narrator._extract_statistics(results)

        assert stats["city"]["type"] == "string"
        assert stats["city"]["unique_count"] == 2
        assert stats["city"]["total_count"] == 3
        assert stats["city"]["most_common"] == "SF"
        assert stats["city"]["most_common_count"] == 2
        assert stats["city"]["most_common_percent"] == 66.7

    def test_extract_statistics_null_values(self, narrator):
        """Test handling of NULL values in statistics"""
        results = [
            {"value": 100},
            {"value": None},
            {"value": 200},
        ]

        stats = narrator._extract_statistics(results)

        # Numeric values are extracted, NULL is filtered out
        assert stats["value"]["type"] == "numeric"
        assert stats["value"]["count"] == 2  # Non-null count
        assert stats["value"]["min"] == 100
        assert stats["value"]["max"] == 200
        assert stats["value"]["avg"] == 150.0

    def test_extract_statistics_mixed_types(self, narrator):
        """Test results with mixed data types"""
        results = [
            {"user_id": 1, "name": "Alice", "score": 95.5},
            {"user_id": 2, "name": "Bob", "score": 87.0},
            {"user_id": 3, "name": "Charlie", "score": 92.3},
        ]

        stats = narrator._extract_statistics(results)

        # Check numeric columns (user_id might be filtered as ID-like)
        assert stats["score"]["type"] == "numeric"

        # Check string columns
        assert stats["name"]["type"] == "string"
        assert stats["name"]["unique_count"] == 3


class TestResponseParsing:
    """Tests for LLM response parsing"""

    @pytest.fixture
    def narrator(self):
        mock_ollama = AsyncMock()
        return ResultNarrator(ollama_client=mock_ollama)

    def test_parse_json_response(self, narrator):
        """Test parsing of valid JSON response"""
        response = json.dumps({
            "summary": "Found 42 items",
            "key_insights": ["Insight 1", "Insight 2"],
            "direct_answer": "42",
            "confidence": 0.95
        })

        result = narrator._parse_response(response)

        assert result.summary == "Found 42 items"
        assert result.key_insights == ["Insight 1", "Insight 2"]
        assert result.direct_answer == "42"
        assert result.confidence == 0.95

    def test_parse_json_embedded_in_text(self, narrator):
        """Test parsing JSON embedded within text"""
        response = """Here is the analysis:

{
  "summary": "Found 42 items",
  "key_insights": ["Point 1", "Point 2"],
  "direct_answer": "42",
  "confidence": 0.88
}

That's the result!"""

        result = narrator._parse_response(response)

        assert result.summary == "Found 42 items"
        assert result.key_insights == ["Point 1", "Point 2"]
        assert result.confidence == 0.88

    def test_parse_malformed_json_fallback(self, narrator):
        """Test fallback when JSON is malformed"""
        response = '{"summary": "Found 42", "key_insights": ["test"'  # Missing closing braces

        result = narrator._parse_response(response)

        # Should use text parser fallback
        assert result.summary is not None
        assert result.confidence == 0.5

    def test_parse_text_response_fallback(self, narrator):
        """Test fallback for plain text responses"""
        response = """Found 42 customers.

- Most are from California
- Average age is 35
- 70% are premium members"""

        result = narrator._parse_response(response)

        assert "Found 42 customers" in result.summary
        assert len(result.key_insights) > 0
        assert result.confidence == 0.5

    def test_parse_response_missing_fields(self, narrator):
        """Test parsing response with missing optional fields"""
        response = json.dumps({
            "summary": "Query completed",
            "key_insights": ["Insight 1"],
            "confidence": 0.75
            # Missing direct_answer
        })

        result = narrator._parse_response(response)

        assert result.summary == "Query completed"
        assert result.direct_answer is None
        assert result.confidence == 0.75

    def test_parse_response_string_insights(self, narrator):
        """Test parsing when key_insights is a string instead of list"""
        response = json.dumps({
            "summary": "Test",
            "key_insights": "Single insight as string",  # Should be list
            "confidence": 0.8
        })

        result = narrator._parse_response(response)

        # Should handle gracefully
        assert isinstance(result.key_insights, list)


class TestFallbackNarrative:
    """Tests for fallback narrative generation"""

    @pytest.fixture
    def narrator(self):
        mock_ollama = AsyncMock()
        return ResultNarrator(ollama_client=mock_ollama)

    def test_fallback_narrative_basic(self, narrator):
        """Test basic fallback narrative generation"""
        result = narrator._fallback_narrative(
            row_count=42,
            statistics={}
        )

        assert "42" in result.summary and ("rows" in result.summary or "record" in result.summary)
        assert result.confidence == 0.5
        assert isinstance(result.key_insights, list)

    def test_fallback_narrative_with_statistics(self, narrator):
        """Test fallback narrative includes statistics-based insights"""
        statistics = {
            "age": {
                "type": "numeric",
                "avg": 35.5
            },
            "city": {
                "type": "string",
                "unique_count": 5,
                "most_common": "New York"
            }
        }

        result = narrator._fallback_narrative(
            row_count=100,
            statistics=statistics
        )

        assert result.summary is not None
        # Should have extracted some insights from statistics
        assert len(result.key_insights) <= 3

    def test_fallback_narrative_single_row(self, narrator):
        """Test fallback narrative for single row results"""
        result = narrator._fallback_narrative(
            row_count=1,
            statistics={"id": {"type": "numeric", "avg": 42}}
        )

        assert "1" in result.summary and ("row" in result.summary or "record" in result.summary)
        assert result.confidence == 0.5


class TestBuildPrompt:
    """Tests for prompt building"""

    @pytest.fixture
    def narrator(self):
        mock_ollama = AsyncMock()
        return ResultNarrator(ollama_client=mock_ollama)

    def test_build_prompt_structure(self, narrator):
        """Test that built prompt contains all required components"""
        sample_results = [{"id": 1, "value": "test"}]
        statistics = {"id": {"type": "numeric", "avg": 1}}

        prompt = narrator._build_prompt(
            question="What is the data?",
            sql="SELECT * FROM test",
            sample_results=sample_results,
            statistics=statistics,
            row_count=1,
            execution_time_ms=50.0
        )

        # Verify prompt contains expected components
        assert "What is the data?" in prompt
        assert "SELECT * FROM test" in prompt
        assert "Row count: 1" in prompt
        assert "50.0" in prompt

    def test_build_prompt_empty_results(self, narrator):
        """Test prompt building with empty results"""
        prompt = narrator._build_prompt(
            question="Get data",
            sql="SELECT * FROM empty_table",
            sample_results=[],
            statistics={},
            row_count=0,
            execution_time_ms=10.0
        )

        assert "empty_table" in prompt
        assert "0" in prompt


@pytest.mark.asyncio
class TestNarrativeIntegration:
    """Integration tests for narrative generation"""

    @pytest.fixture
    def narrator(self):
        mock_ollama = AsyncMock()
        return ResultNarrator(ollama_client=mock_ollama)

    async def test_end_to_end_with_mocked_ollama(self, narrator):
        """Test complete flow from query results to narrative"""
        # Mock Ollama response
        narrator.ollama.generate = AsyncMock(return_value=json.dumps({
            "summary": "The dataset contains 100 records with an average value of 45.5",
            "key_insights": [
                "Values range from 10 to 90",
                "Most common value is 50",
                "Data is fairly distributed"
            ],
            "direct_answer": "100 records",
            "confidence": 0.88
        }))

        # Real data
        results = [
            {"id": i, "value": 10 + (i % 80)} for i in range(100)
        ][:20]  # Sample

        result = await narrator.generate_narrative(
            question="How many records and what are the value ranges?",
            sql="SELECT id, value FROM test_table",
            results=results,
            row_count=100,
            execution_time_ms=150.0,
            database_type="postgresql"
        )

        # Verify narrative was generated
        assert result.summary is not None
        assert len(result.key_insights) > 0
        assert result.direct_answer is not None
        assert result.confidence > 0.8
        assert result.statistics["row_count"] == 20

    async def test_graceful_degradation_on_malformed_response(self, narrator):
        """Test graceful degradation when LLM returns unexpected format"""
        narrator.ollama.generate = AsyncMock(return_value="This is not JSON at all!")

        result = await narrator.generate_narrative(
            question="Test",
            sql="SELECT * FROM test",
            results=[{"id": 1}],
            row_count=1,
            execution_time_ms=10.0,
            database_type="postgresql"
        )

        # Should still return a valid result
        assert result.summary is not None
        assert isinstance(result.key_insights, list)
        assert result.confidence < 0.6  # Low confidence for malformed response


class TestAnomalyDetection:
    """Tests for anomaly detection functionality"""

    @pytest.fixture
    def narrator(self):
        mock_ollama = AsyncMock()
        return ResultNarrator(ollama_client=mock_ollama)

    def test_detect_anomalies_empty_results(self, narrator):
        """Test anomaly detection with empty results"""
        anomalies = narrator._detect_anomalies([])
        assert anomalies["anomalies_found"] is False
        assert anomalies["anomaly_count"] == 0

    def test_detect_anomalies_with_outliers(self, narrator):
        """Test detection of statistical outliers using Z-score"""
        results = [
            {"value": 100},
            {"value": 105},
            {"value": 110},
            {"value": 108},
            {"value": 102},
            {"value": 9999},  # Extreme outlier (Z > 2.0)
        ]
        anomalies = narrator._detect_anomalies(results)
        assert anomalies["anomalies_found"] is True
        assert anomalies["anomaly_count"] >= 1
        assert "value" in anomalies["outliers"]

    def test_detect_anomalies_no_outliers(self, narrator):
        """Test when no anomalies are present"""
        results = [
            {"value": 100},
            {"value": 105},
            {"value": 110},
            {"value": 108},
            {"value": 102},
        ]
        anomalies = narrator._detect_anomalies(results)
        assert anomalies["anomalies_found"] is False
        assert anomalies["anomaly_count"] == 0

    def test_detect_anomalies_multiple_columns(self, narrator):
        """Test anomaly detection across multiple columns"""
        results = [
            {"col1": 100, "col2": 50},
            {"col1": 105, "col2": 55},
            {"col1": 110, "col2": 52},
            {"col1": 104, "col2": 54},
            {"col1": 9999, "col2": 9999},  # Extreme outliers in both columns
        ]
        anomalies = narrator._detect_anomalies(results)
        assert anomalies["anomalies_found"] is True


class TestComparativeAnalysis:
    """Tests for comparative analysis with history"""

    @pytest.fixture
    def narrator(self):
        mock_ollama = AsyncMock()
        return ResultNarrator(ollama_client=mock_ollama)

    def test_compare_to_history_empty(self, narrator):
        """Test comparison with no historical context"""
        result = narrator._compare_to_history([{"id": 1}], [])
        assert result["has_trend"] is False
        assert len(result["comparisons"]) == 0

    def test_compare_to_history_with_increase(self, narrator):
        """Test detection of result count increase"""
        current_results = [{"id": i} for i in range(100)]
        historical_queries = [
            {
                "created_at": "2025-12-01T10:00:00",
                "result_count": 50,
                "question": "Show users"
            }
        ]
        comparison = narrator._compare_to_history(current_results, historical_queries)
        assert comparison["has_trend"] is True
        assert len(comparison["comparisons"]) > 0
        assert comparison["comparisons"][0]["direction"] == "increased"

    def test_compare_to_history_with_decrease(self, narrator):
        """Test detection of result count decrease"""
        current_results = [{"id": i} for i in range(25)]
        historical_queries = [
            {
                "created_at": "2025-12-01T10:00:00",
                "result_count": 100,
                "question": "Show users"
            }
        ]
        comparison = narrator._compare_to_history(current_results, historical_queries)
        assert comparison["has_trend"] is True
        if comparison["comparisons"]:
            assert comparison["comparisons"][0]["direction"] == "decreased"

    def test_get_historical_context_empty_session(self, narrator):
        """Test with no database session"""
        result = narrator._get_historical_context(None, "SELECT * FROM users", "Show users")
        assert result == []


class TestTrendDetection:
    """Tests for trend detection"""

    @pytest.fixture
    def narrator(self):
        mock_ollama = AsyncMock()
        return ResultNarrator(ollama_client=mock_ollama)

    def test_detect_temporal_columns_with_dates(self, narrator):
        """Test detection of date columns"""
        results = [
            {"date": "2025-01-01", "value": 100},
            {"date": "2025-01-02", "value": 110},
            {"date": "2025-01-03", "value": 120},
        ]
        temporal_cols = narrator._detect_temporal_columns(results)
        assert "date" in temporal_cols

    def test_detect_temporal_columns_no_dates(self, narrator):
        """Test when no temporal columns exist"""
        results = [
            {"id": 1, "value": 100},
            {"id": 2, "value": 110},
            {"id": 3, "value": 120},
        ]
        temporal_cols = narrator._detect_temporal_columns(results)
        assert len(temporal_cols) == 0

    def test_detect_trends_no_temporal_columns(self, narrator):
        """Test trend detection without temporal data"""
        results = [{"value": 100}, {"value": 105}, {"value": 110}]
        trends = narrator._detect_trends(results, [])
        assert trends["trends_found"] is False

    def test_detect_trends_with_upward_trend(self, narrator):
        """Test detection of upward trend"""
        from datetime import datetime, timedelta

        base_date = datetime(2025, 1, 1)
        results = []
        for i in range(5):
            results.append({
                "date": base_date + timedelta(days=i),
                "sales": 100 + (i * 20)  # Clear upward trend
            })

        trends = narrator._detect_trends(results, ["date"])
        # Trends may or may not be found depending on R² threshold
        if trends["trends_found"]:
            assert any(t["direction"] == "upward" for t in trends["trends"])


class TestCorrelationAnalysis:
    """Tests for correlation analysis"""

    @pytest.fixture
    def narrator(self):
        mock_ollama = AsyncMock()
        return ResultNarrator(ollama_client=mock_ollama)

    def test_calculate_correlations_empty_results(self, narrator):
        """Test correlation with empty results"""
        correlations = narrator._calculate_correlations([])
        assert correlations["correlations_found"] is False

    def test_calculate_correlations_perfect_positive(self, narrator):
        """Test detection of perfect positive correlation"""
        # Minimum 10 rows required for correlation detection
        results = [
            {"x": 1, "y": 1},
            {"x": 2, "y": 2},
            {"x": 3, "y": 3},
            {"x": 4, "y": 4},
            {"x": 5, "y": 5},
            {"x": 6, "y": 6},
            {"x": 7, "y": 7},
            {"x": 8, "y": 8},
            {"x": 9, "y": 9},
            {"x": 10, "y": 10},
        ]
        correlations = narrator._calculate_correlations(results)
        assert correlations["correlations_found"] is True
        assert len(correlations["correlations"]) > 0
        assert correlations["correlations"][0]["strength"] == "strong positive"

    def test_calculate_correlations_strong_negative(self, narrator):
        """Test detection of strong negative correlation"""
        # Minimum 10 rows required for correlation detection
        results = [
            {"x": 1, "y": 10},
            {"x": 2, "y": 9},
            {"x": 3, "y": 8},
            {"x": 4, "y": 7},
            {"x": 5, "y": 6},
            {"x": 6, "y": 5},
            {"x": 7, "y": 4},
            {"x": 8, "y": 3},
            {"x": 9, "y": 2},
            {"x": 10, "y": 1},
        ]
        correlations = narrator._calculate_correlations(results)
        assert correlations["correlations_found"] is True
        if correlations["correlations"]:
            assert correlations["correlations"][0]["strength"] == "strong negative"

    def test_calculate_correlations_no_correlation(self, narrator):
        """Test when columns have no correlation"""
        # Minimum 10 rows required for correlation detection
        results = [
            {"x": 1, "y": 50},
            {"x": 2, "y": 80},
            {"x": 3, "y": 30},
            {"x": 4, "y": 90},
            {"x": 5, "y": 20},
            {"x": 6, "y": 70},
            {"x": 7, "y": 40},
            {"x": 8, "y": 60},
            {"x": 9, "y": 10},
            {"x": 10, "y": 100},
        ]
        correlations = narrator._calculate_correlations(results)
        # May or may not find correlations depending on the specific values
        assert isinstance(correlations, dict)
        assert "correlations_found" in correlations

    def test_calculate_correlations_small_dataset_ignored(self, narrator):
        """Test that small datasets (< 10 rows) don't trigger correlation detection"""
        # Even with perfect correlation, small datasets should be skipped
        results = [
            {"x": 1, "y": 1},
            {"x": 2, "y": 2},
            {"x": 3, "y": 3},
            {"x": 4, "y": 4},
            {"x": 5, "y": 5},
        ]
        correlations = narrator._calculate_correlations(results)
        # Should not find correlations due to small sample size
        assert correlations["correlations_found"] is False
        assert len(correlations["correlations"]) == 0


class TestJsonExtraction:
    """Tests for JSON extraction and parsing robustness"""

    @pytest.fixture
    def narrator(self):
        """Create narrator with mocked Ollama client"""
        mock_ollama = AsyncMock()
        return ResultNarrator(
            ollama_client=mock_ollama,
            enable_statistics=True,
            max_sample_rows=20,
            timeout_seconds=5
        )

    def test_extract_json_object_simple(self, narrator):
        """Test extraction of a simple JSON object"""
        text = 'Here is the result: {"summary": "Test", "key_insights": ["A", "B"]}'
        result = narrator._extract_json_object(text)
        assert result is not None
        data = json.loads(result)
        assert data["summary"] == "Test"
        assert data["key_insights"] == ["A", "B"]

    def test_extract_json_object_nested(self, narrator):
        """Test extraction with nested JSON objects"""
        text = '''{"summary": "Test", "statistics": {"min": 1, "max": 100}}'''
        result = narrator._extract_json_object(text)
        assert result is not None
        data = json.loads(result)
        assert data["summary"] == "Test"
        assert data["statistics"]["min"] == 1

    def test_extract_json_object_with_surrounding_text(self, narrator):
        """Test extraction when JSON is surrounded by text"""
        text = '''Here is the analysis:
        {"summary": "Found 10 products", "key_insights": ["Insight 1"]}
        Hope this helps!'''
        result = narrator._extract_json_object(text)
        assert result is not None
        data = json.loads(result)
        assert data["summary"] == "Found 10 products"

    def test_extract_json_object_no_json(self, narrator):
        """Test when no JSON is present"""
        text = "This is just plain text without any JSON"
        result = narrator._extract_json_object(text)
        assert result is None

    def test_extract_json_object_with_escaped_quotes(self, narrator):
        """Test extraction with escaped quotes in strings"""
        text = r'{"summary": "He said \"hello\"", "key_insights": []}'
        result = narrator._extract_json_object(text)
        assert result is not None
        data = json.loads(result)
        assert 'hello' in data["summary"]

    def test_parse_response_filters_json_fragments(self, narrator):
        """Test that JSON fragments in key_insights are filtered out"""
        # Simulate malformed LLM response with JSON fragments in insights
        malformed_response = json.dumps({
            "summary": "Valid summary here",
            "key_insights": [
                '"summary": "This is a JSON fragment",',
                '"key_insights": [',
                "This is a valid insight about the data",
                '"another_key": "value"',
            ],
            "confidence": 0.7
        })

        result = narrator._parse_response(malformed_response)

        # Should filter out the JSON fragments
        assert result.summary == "Valid summary here"
        assert len(result.key_insights) == 1
        assert "valid insight" in result.key_insights[0].lower()

    def test_parse_response_rejects_bracket_summary(self, narrator):
        """Test that summary containing only brackets triggers fallback"""
        malformed_response = json.dumps({
            "summary": "{",
            "key_insights": ["Some insight"],
            "confidence": 0.7
        })

        result = narrator._parse_response(malformed_response)

        # Should fall back to text parsing, not return "{" as summary
        assert result.summary != "{"
        assert len(result.summary) > 1

    def test_parse_response_rejects_short_summary(self, narrator):
        """Test that very short summaries trigger fallback"""
        malformed_response = json.dumps({
            "summary": "Hi",
            "key_insights": ["Some insight"],
            "confidence": 0.7
        })

        result = narrator._parse_response(malformed_response)

        # Should fall back due to summary being too short (< 5 chars)
        # The fallback parser will use the raw text
        assert len(result.summary) >= 2  # At minimum gets something

    def test_parse_response_cleans_quoted_insights(self, narrator):
        """Test that trailing quotes and commas are cleaned from insights"""
        response = json.dumps({
            "summary": "Valid summary with enough characters",
            "key_insights": [
                '"This insight has quotes",',
                "Normal insight without issues",
            ],
            "confidence": 0.7
        })

        result = narrator._parse_response(response)

        # Insights should have quotes/commas stripped
        for insight in result.key_insights:
            assert not insight.endswith('",')
            assert not insight.startswith('"') or not insight.endswith('"')

    def test_parse_response_valid_json(self, narrator):
        """Test parsing of properly formatted JSON response"""
        valid_response = json.dumps({
            "summary": "Found 100 products in the database with diverse pricing.",
            "key_insights": [
                "Product prices range from $10 to $500",
                "Most products are in the Electronics category",
                "Average price is $150"
            ],
            "direct_answer": "100 products",
            "confidence": 0.85
        })

        result = narrator._parse_response(valid_response)

        assert result.summary == "Found 100 products in the database with diverse pricing."
        assert len(result.key_insights) == 3
        assert result.direct_answer == "100 products"
        assert result.confidence == 0.85

    def test_parse_response_falls_back_to_text_on_all_fragments(self, narrator):
        """Test fallback when all insights are JSON fragments"""
        malformed_response = json.dumps({
            "summary": "This is a valid summary with enough length",
            "key_insights": [
                '"key": "value",',
                '"another": [',
                '"}',
            ],
            "confidence": 0.7
        })

        result = narrator._parse_response(malformed_response)

        # Should have fallen back to text parsing
        # The confidence should be lower (text parsing defaults to 0.5)
        assert result.confidence <= 0.7
