"""
Tests for Schema Health Analyzer (Phase 12.3)

Tests the schema health analysis with:
- Structural analysis (missing PKs, orphaned FKs, wide tables, naming)
- Index analysis and suggestions
- Normalization issue detection
- LLM-enhanced insights and recommendations
"""

import asyncio
import json
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.lineage.schema_health_analyzer import (
    SchemaHealthAnalyzer,
    SchemaHealthReport,
    IndexSuggestion,
    SchemaIssue,
    NormalizationIssue,
    TableHealthSummary,
    HealthGrade,
    IssueSeverity,
    IssueCategory,
    StructuralAnalyzer,
    IndexAnalyzer,
    get_schema_health_analyzer,
)


@pytest.fixture
def mock_ollama_client():
    """Create a mock OllamaClient."""
    client = MagicMock()
    client.generate = AsyncMock()
    return client


@pytest.fixture
def sample_schema():
    """Create a sample database schema."""
    return {
        "tables": {
            "users": {
                "columns": [
                    {"name": "id", "type": "INTEGER", "nullable": False},
                    {"name": "email", "type": "VARCHAR(255)", "nullable": False},
                    {"name": "name", "type": "VARCHAR(100)", "nullable": True},
                    {"name": "created_at", "type": "TIMESTAMP", "nullable": True},
                ],
                "primary_keys": ["id"],
                "foreign_keys": [],
                "indexes": [{"name": "idx_users_email", "columns": ["email"]}],
            },
            "orders": {
                "columns": [
                    {"name": "id", "type": "INTEGER", "nullable": False},
                    {"name": "user_id", "type": "INTEGER", "nullable": False},
                    {"name": "amount", "type": "DECIMAL(10,2)", "nullable": False},
                    {"name": "status", "type": "VARCHAR(50)", "nullable": True},
                    {"name": "order_date", "type": "DATE", "nullable": True},
                ],
                "primary_keys": ["id"],
                "foreign_keys": [
                    {"column": "user_id", "referred_table": "users", "referred_column": "id"}
                ],
                "indexes": [],
            },
            "products": {
                "columns": [
                    {"name": "id", "type": "INTEGER", "nullable": False},
                    {"name": "name", "type": "VARCHAR(200)", "nullable": False},
                    {"name": "price", "type": "DECIMAL(10,2)", "nullable": False},
                ],
                "primary_keys": ["id"],
                "foreign_keys": [],
                "indexes": [],
            },
        },
        "summary": {
            "total_tables": 3,
            "total_columns": 12,
        },
    }


@pytest.fixture
def schema_with_issues():
    """Create a schema with various issues for testing."""
    return {
        "tables": {
            "logs": {
                "columns": [
                    {"name": "log_id", "type": "INTEGER", "nullable": False},
                    {"name": "message", "type": "TEXT", "nullable": True},
                    {"name": "user", "type": "VARCHAR(50)", "nullable": True},  # Reserved word
                    {"name": "date", "type": "DATE", "nullable": True},  # Reserved word
                ],
                "primary_keys": [],  # Missing PK
                "foreign_keys": [],
                "indexes": [],
            },
            "audit_trail": {
                "columns": [
                    {"name": "id", "type": "INTEGER", "nullable": False},
                    {"name": "data", "type": "TEXT", "nullable": True},  # Potential embedded data
                    {"name": "metadata", "type": "JSON", "nullable": True},  # JSON column
                ],
                "primary_keys": ["id"],
                "foreign_keys": [
                    {"column": "ref_id", "referred_table": "nonexistent_table", "referred_column": "id"}
                ],  # Orphaned FK
                "indexes": [],
            },
            "contacts": {
                "columns": [
                    {"name": "id", "type": "INTEGER", "nullable": False},
                    {"name": "phone1", "type": "VARCHAR(20)", "nullable": True},
                    {"name": "phone2", "type": "VARCHAR(20)", "nullable": True},
                    {"name": "phone3", "type": "VARCHAR(20)", "nullable": True},  # 1NF violation
                    {"name": "address1", "type": "VARCHAR(200)", "nullable": True},
                    {"name": "address2", "type": "VARCHAR(200)", "nullable": True},  # 1NF violation
                ],
                "primary_keys": ["id"],
                "foreign_keys": [],
                "indexes": [],
            },
        },
        "summary": {
            "total_tables": 3,
            "total_columns": 13,
        },
    }


@pytest.fixture
def sample_queries():
    """Create sample queries for index analysis."""
    return [
        "SELECT * FROM orders WHERE user_id = 1",
        "SELECT * FROM orders WHERE user_id = 2 AND status = 'pending'",
        "SELECT * FROM orders WHERE user_id = 3",
        "SELECT * FROM orders WHERE status = 'completed'",
        "SELECT o.*, u.name FROM orders o JOIN users u ON o.user_id = u.id",
        "SELECT o.*, u.name FROM orders o JOIN users u ON o.user_id = u.id WHERE o.status = 'pending'",
    ]


@pytest.fixture
def structural_analyzer():
    """Create a StructuralAnalyzer instance."""
    return StructuralAnalyzer()


@pytest.fixture
def analyzer(mock_ollama_client):
    """Create a SchemaHealthAnalyzer with mock client."""
    return SchemaHealthAnalyzer(
        ollama_client=mock_ollama_client,
        timeout_seconds=5.0,
    )


# =============================================================================
# Dataclass Tests
# =============================================================================

class TestIndexSuggestion:
    """Tests for IndexSuggestion dataclass."""

    def test_index_suggestion_to_dict(self):
        """Test index suggestion serialization."""
        suggestion = IndexSuggestion(
            table_name="orders",
            columns=["user_id"],
            index_type="btree",
            reason="Used in 10 queries",
            estimated_impact="high",
            create_sql="CREATE INDEX idx_orders_user_id ON orders (user_id);",
            query_count_benefiting=10,
        )

        result = suggestion.to_dict()

        assert result["table_name"] == "orders"
        assert result["columns"] == ["user_id"]
        assert result["index_type"] == "btree"
        assert result["estimated_impact"] == "high"
        assert result["query_count_benefiting"] == 10

    def test_index_suggestion_defaults(self):
        """Test default values."""
        suggestion = IndexSuggestion(
            table_name="users",
            columns=["email"],
        )

        assert suggestion.index_type == "btree"
        assert suggestion.reason == ""
        assert suggestion.estimated_impact == "medium"


class TestSchemaIssue:
    """Tests for SchemaIssue dataclass."""

    def test_schema_issue_to_dict(self):
        """Test schema issue serialization."""
        issue = SchemaIssue(
            category="integrity",
            severity="error",
            title="Missing Primary Key",
            description="Table 'logs' has no primary key",
            affected_objects=["logs"],
            recommendation="Add a primary key",
        )

        result = issue.to_dict()

        assert result["category"] == "integrity"
        assert result["severity"] == "error"
        assert result["title"] == "Missing Primary Key"
        assert result["affected_objects"] == ["logs"]


class TestNormalizationIssue:
    """Tests for NormalizationIssue dataclass."""

    def test_normalization_issue_to_dict(self):
        """Test normalization issue serialization."""
        issue = NormalizationIssue(
            table_name="contacts",
            issue_type="1NF",
            description="Repeated columns detected",
            affected_columns=["phone1", "phone2", "phone3"],
            recommendation="Create separate phone table",
        )

        result = issue.to_dict()

        assert result["table_name"] == "contacts"
        assert result["issue_type"] == "1NF"
        assert len(result["affected_columns"]) == 3


class TestTableHealthSummary:
    """Tests for TableHealthSummary dataclass."""

    def test_table_summary_to_dict(self):
        """Test table summary serialization."""
        summary = TableHealthSummary(
            table_name="users",
            column_count=5,
            has_primary_key=True,
            foreign_key_count=0,
            index_count=2,
            issues=[
                SchemaIssue(
                    category="naming",
                    severity="info",
                    title="Naming Issue",
                    description="Column name uses reserved word",
                )
            ],
        )

        result = summary.to_dict()

        assert result["table_name"] == "users"
        assert result["column_count"] == 5
        assert result["has_primary_key"] is True
        assert len(result["issues"]) == 1


class TestSchemaHealthReport:
    """Tests for SchemaHealthReport dataclass."""

    def test_report_to_dict(self):
        """Test complete report serialization."""
        report = SchemaHealthReport(
            connection_id=1,
            database_name="test_db",
            grade=HealthGrade.GOOD.value,
            score=80,
            table_count=5,
            total_issues=3,
            critical_issues=0,
            summary="Schema health is good",
            recommendations=["Add indexes", "Fix naming"],
            llm_used=True,
        )

        result = report.to_dict()

        assert result["connection_id"] == 1
        assert result["database_name"] == "test_db"
        assert result["grade"] == "B"
        assert result["score"] == 80
        assert result["llm_used"] is True

    def test_report_post_init_timestamp(self):
        """Test automatic timestamp generation."""
        report = SchemaHealthReport(
            connection_id=1,
            database_name="test",
        )

        assert report.analyzed_at is not None


# =============================================================================
# StructuralAnalyzer Tests
# =============================================================================

class TestStructuralAnalyzer:
    """Tests for StructuralAnalyzer."""

    def test_find_missing_primary_keys(self, structural_analyzer, schema_with_issues):
        """Test detection of missing primary keys."""
        missing = structural_analyzer.find_missing_primary_keys(schema_with_issues)

        assert "logs" in missing
        assert "audit_trail" not in missing
        assert "contacts" not in missing

    def test_find_orphaned_foreign_keys(self, structural_analyzer, schema_with_issues):
        """Test detection of orphaned foreign keys."""
        orphans = structural_analyzer.find_orphaned_foreign_keys(schema_with_issues)

        assert len(orphans) == 1
        assert orphans[0]["table"] == "audit_trail"
        assert orphans[0]["references"] == "nonexistent_table"

    def test_find_orphaned_fks_no_issues(self, structural_analyzer, sample_schema):
        """Test no orphaned FKs in valid schema."""
        orphans = structural_analyzer.find_orphaned_foreign_keys(sample_schema)

        assert len(orphans) == 0

    def test_detect_circular_references(self, structural_analyzer):
        """Test detection of circular FK references."""
        circular_schema = {
            "tables": {
                "a": {
                    "columns": [],
                    "primary_keys": ["id"],
                    "foreign_keys": [{"column": "b_id", "referred_table": "b"}],
                    "indexes": [],
                },
                "b": {
                    "columns": [],
                    "primary_keys": ["id"],
                    "foreign_keys": [{"column": "c_id", "referred_table": "c"}],
                    "indexes": [],
                },
                "c": {
                    "columns": [],
                    "primary_keys": ["id"],
                    "foreign_keys": [{"column": "a_id", "referred_table": "a"}],
                    "indexes": [],
                },
            }
        }

        cycles = structural_analyzer.detect_circular_references(circular_schema)

        assert len(cycles) > 0
        # Cycle should include a -> b -> c -> a

    def test_find_wide_tables(self, structural_analyzer):
        """Test detection of wide tables."""
        wide_schema = {
            "tables": {
                "narrow": {
                    "columns": [{"name": f"col{i}"} for i in range(5)],
                },
                "wide": {
                    "columns": [{"name": f"col{i}"} for i in range(35)],
                },
            }
        }

        wide_tables = structural_analyzer.find_wide_tables(wide_schema, threshold=30)

        assert len(wide_tables) == 1
        assert wide_tables[0]["table"] == "wide"
        assert wide_tables[0]["column_count"] == 35

    def test_find_naming_issues_reserved_words(self, structural_analyzer, schema_with_issues):
        """Test detection of reserved word usage."""
        issues = structural_analyzer.find_naming_issues(schema_with_issues)

        reserved_word_issues = [i for i in issues if i["type"] == "reserved_word"]
        assert len(reserved_word_issues) >= 2  # 'user' and 'date' columns

    def test_find_missing_not_null(self, structural_analyzer, sample_schema):
        """Test detection of columns that should be NOT NULL."""
        issues = structural_analyzer.find_missing_not_null(sample_schema)

        # 'created_at' in users is nullable but typically should be NOT NULL
        created_at_issues = [i for i in issues if "created_at" in i.get("column", "")]
        assert len(created_at_issues) >= 1


# =============================================================================
# IndexAnalyzer Tests
# =============================================================================

class TestIndexAnalyzer:
    """Tests for IndexAnalyzer."""

    def test_analyze_where_clauses(self, sample_schema, sample_queries):
        """Test WHERE clause column analysis."""
        analyzer = IndexAnalyzer(sample_schema, {"queries": sample_queries})
        where_usage = analyzer.analyze_where_clauses(sample_queries)

        # user_id should be detected from multiple queries
        assert "orders" in where_usage or "o" in where_usage

    def test_analyze_join_columns(self, sample_schema, sample_queries):
        """Test JOIN column analysis."""
        analyzer = IndexAnalyzer(sample_schema, {"queries": sample_queries})
        join_usage = analyzer.analyze_join_columns(sample_queries)

        # Should detect join on user_id and id
        assert len(join_usage) > 0

    def test_suggest_indexes(self, sample_schema, sample_queries):
        """Test index suggestion generation."""
        analyzer = IndexAnalyzer(sample_schema, {"queries": sample_queries})
        suggestions = analyzer.suggest_indexes(min_query_count=2)

        # Should suggest indexes based on query patterns
        # Note: depends on the regex matching in the analyzer

    def test_index_exists_check(self, sample_schema):
        """Test existing index detection."""
        analyzer = IndexAnalyzer(sample_schema, {"queries": []})

        # email index exists in users table
        assert analyzer._index_exists("users", ["email"])

        # user_id index doesn't exist in orders
        assert not analyzer._index_exists("orders", ["user_id"])

    def test_index_exists_prefix_match(self, sample_schema):
        """Test prefix index matching."""
        schema_with_composite = {
            "tables": {
                "test": {
                    "columns": [],
                    "primary_keys": [],
                    "indexes": [{"columns": ["a", "b", "c"]}],
                }
            }
        }
        analyzer = IndexAnalyzer(schema_with_composite, {"queries": []})

        # Prefix matches should work
        assert analyzer._index_exists("test", ["a"])
        assert analyzer._index_exists("test", ["a", "b"])
        assert not analyzer._index_exists("test", ["b", "c"])  # Not a prefix

    def test_suggest_composite_indexes(self, sample_schema):
        """Test composite index suggestion."""
        queries = [
            "SELECT * FROM orders WHERE user_id = 1 AND status = 'pending'",
            "SELECT * FROM orders WHERE user_id = 2 AND status = 'completed'",
            "SELECT * FROM orders WHERE user_id = 3 AND status = 'pending'",
            "SELECT * FROM orders WHERE user_id = 4 AND status = 'shipped'",
        ]
        analyzer = IndexAnalyzer(sample_schema, {"queries": queries})
        suggestions = analyzer.suggest_composite_indexes(min_co_occurrence=2)

        # Should potentially suggest composite index on (user_id, status)


# =============================================================================
# SchemaHealthAnalyzer Tests
# =============================================================================

class TestSchemaHealthAnalyzer:
    """Tests for SchemaHealthAnalyzer."""

    def test_run_structural_analysis(self, analyzer, schema_with_issues):
        """Test structural analysis integration."""
        issues = analyzer._run_structural_analysis(schema_with_issues)

        # Should find missing PK in logs
        missing_pk = [i for i in issues if "Missing Primary Key" in i.title]
        assert len(missing_pk) >= 1

        # Should find orphaned FK
        orphaned_fk = [i for i in issues if "Orphaned" in i.title]
        assert len(orphaned_fk) >= 1

    def test_analyze_normalization(self, analyzer, schema_with_issues):
        """Test normalization analysis."""
        issues = analyzer._analyze_normalization(schema_with_issues)

        # Should find 1NF violations (phone1, phone2, phone3)
        phone_issues = [
            i for i in issues
            if "phone" in ", ".join(i.affected_columns).lower()
        ]
        assert len(phone_issues) >= 1

        # Should find potential embedded data (JSON metadata)
        json_issues = [
            i for i in issues
            if "metadata" in ", ".join(i.affected_columns).lower()
        ]
        assert len(json_issues) >= 1

    def test_calculate_score_excellent(self, analyzer):
        """Test score calculation for excellent schema."""
        report = SchemaHealthReport(
            connection_id=1,
            database_name="test",
            table_count=5,
        )
        report.table_summaries = [
            TableHealthSummary("t1", 5, True, 0, 2),
            TableHealthSummary("t2", 3, True, 1, 1),
        ]

        result = analyzer._calculate_score(report)

        assert result.score >= 90
        assert result.grade == HealthGrade.EXCELLENT.value

    def test_calculate_score_with_issues(self, analyzer):
        """Test score deduction for issues."""
        report = SchemaHealthReport(
            connection_id=1,
            database_name="test",
            table_count=5,
        )
        report.anti_patterns = [
            SchemaIssue(IssueCategory.INTEGRITY.value, IssueSeverity.CRITICAL.value, "Critical Issue", ""),
            SchemaIssue(IssueCategory.INTEGRITY.value, IssueSeverity.ERROR.value, "Error Issue", ""),
            SchemaIssue(IssueCategory.NAMING.value, IssueSeverity.WARNING.value, "Warning", ""),
        ]
        report.table_summaries = [
            TableHealthSummary("t1", 5, True, 0, 0),
        ]

        result = analyzer._calculate_score(report)

        # Critical: -20, Error: -10, Warning: -5 = -35
        assert result.score <= 70

    def test_calculate_score_missing_pk(self, analyzer):
        """Test score deduction for missing primary keys."""
        report = SchemaHealthReport(
            connection_id=1,
            database_name="test",
            table_count=3,
        )
        report.table_summaries = [
            TableHealthSummary("t1", 5, False, 0, 0),  # Missing PK
            TableHealthSummary("t2", 3, False, 0, 0),  # Missing PK
            TableHealthSummary("t3", 2, True, 0, 0),
        ]

        result = analyzer._calculate_score(report)

        # Each missing PK: -10
        assert result.score <= 80

    def test_generate_fallback_summary_excellent(self, analyzer):
        """Test fallback summary for excellent schema."""
        report = SchemaHealthReport(
            connection_id=1,
            database_name="test",
            table_count=10,
            score=95,
        )
        report.anti_patterns = []

        summary = analyzer._generate_fallback_summary(report)

        assert "excellent" in summary.lower()
        assert "10 tables" in summary

    def test_generate_fallback_summary_poor(self, analyzer):
        """Test fallback summary for poor schema."""
        report = SchemaHealthReport(
            connection_id=1,
            database_name="test",
            table_count=5,
            score=35,
        )
        report.anti_patterns = [SchemaIssue("", "", "", "") for _ in range(10)]

        summary = analyzer._generate_fallback_summary(report)

        assert "attention" in summary.lower()

    def test_extract_json_object(self, analyzer):
        """Test JSON extraction from LLM response."""
        response = '''Here's my analysis:
        {
            "summary": "Good schema",
            "grade": "B",
            "recommendations": ["Add indexes"]
        }
        Some trailing text.'''

        result = analyzer._extract_json_object(response)

        assert result is not None
        parsed = json.loads(result)
        assert parsed["grade"] == "B"

    def test_extract_json_object_nested(self, analyzer):
        """Test JSON extraction with nested objects."""
        response = '''Analysis:
        {
            "summary": "Test",
            "additional_issues": [
                {"title": "Issue 1", "description": "Desc"}
            ]
        }'''

        result = analyzer._extract_json_object(response)

        assert result is not None
        parsed = json.loads(result)
        assert len(parsed["additional_issues"]) == 1

    def test_extract_json_object_with_strings(self, analyzer):
        """Test JSON extraction with special characters in strings."""
        response = '''{
            "summary": "Schema has \\"good\\" design with {special} chars"
        }'''

        result = analyzer._extract_json_object(response)

        assert result is not None

    def test_extract_json_object_no_json(self, analyzer):
        """Test JSON extraction when no JSON present."""
        response = "This response has no JSON data."

        result = analyzer._extract_json_object(response)

        assert result is None


class TestSchemaHealthAnalyzerLLM:
    """Tests for LLM integration in SchemaHealthAnalyzer."""

    @pytest.fixture
    def complete_schema(self):
        """Create a complete schema structure for LLM tests."""
        return {
            "tables": {
                "users": {
                    "columns": [
                        {"name": "id", "type": "INTEGER", "nullable": False},
                        {"name": "email", "type": "VARCHAR(255)", "nullable": False},
                    ],
                    "primary_keys": ["id"],
                    "foreign_keys": [],
                    "indexes": [],
                }
            },
            "summary": {"table_count": 1, "total_columns": 2},
            "relationships": [],
        }

    @pytest.mark.asyncio
    async def test_generate_llm_insights_success(self, mock_ollama_client, complete_schema):
        """Test successful LLM insight generation."""
        llm_response = json.dumps({
            "summary": "Schema is well-designed",
            "grade": "A",
            "recommendations": ["Consider adding more indexes"],
            "additional_issues": [],
        })
        mock_ollama_client.generate.return_value = llm_response

        analyzer = SchemaHealthAnalyzer(
            ollama_client=mock_ollama_client,
            timeout_seconds=5.0,
        )

        report = SchemaHealthReport(connection_id=1, database_name="test")

        result = await analyzer._generate_llm_insights(complete_schema, {}, report, 5.0)

        assert result is not None
        assert result["grade"] == "A"
        assert "well-designed" in result["summary"]

    @pytest.mark.asyncio
    async def test_generate_llm_insights_timeout(self, mock_ollama_client, complete_schema):
        """Test LLM timeout handling."""
        async def slow_generate(*args, **kwargs):
            await asyncio.sleep(10)
            return "{}"

        mock_ollama_client.generate = slow_generate

        analyzer = SchemaHealthAnalyzer(
            ollama_client=mock_ollama_client,
            timeout_seconds=0.1,
        )

        report = SchemaHealthReport(connection_id=1, database_name="test")

        result = await analyzer._generate_llm_insights(complete_schema, {}, report, 0.1)

        assert result is None

    @pytest.mark.asyncio
    async def test_generate_llm_insights_error(self, mock_ollama_client, complete_schema):
        """Test LLM error handling."""
        mock_ollama_client.generate.side_effect = Exception("API Error")

        analyzer = SchemaHealthAnalyzer(
            ollama_client=mock_ollama_client,
            timeout_seconds=5.0,
        )

        report = SchemaHealthReport(connection_id=1, database_name="test")

        result = await analyzer._generate_llm_insights(complete_schema, {}, report, 5.0)

        assert result is None


class TestHealthGrades:
    """Tests for grade calculations."""

    def test_health_grade_values(self):
        """Test HealthGrade enum values."""
        assert HealthGrade.EXCELLENT.value == "A"
        assert HealthGrade.GOOD.value == "B"
        assert HealthGrade.FAIR.value == "C"
        assert HealthGrade.POOR.value == "D"
        assert HealthGrade.CRITICAL.value == "F"

    def test_issue_severity_values(self):
        """Test IssueSeverity enum values."""
        assert IssueSeverity.INFO.value == "info"
        assert IssueSeverity.WARNING.value == "warning"
        assert IssueSeverity.ERROR.value == "error"
        assert IssueSeverity.CRITICAL.value == "critical"

    def test_issue_category_values(self):
        """Test IssueCategory enum values."""
        assert IssueCategory.INDEXING.value == "indexing"
        assert IssueCategory.NORMALIZATION.value == "normalization"
        assert IssueCategory.NAMING.value == "naming"


class TestBuildTableSummaries:
    """Tests for table summary building."""

    def test_build_table_summaries(self, analyzer, sample_schema):
        """Test table summary generation."""
        report = SchemaHealthReport(connection_id=1, database_name="test")
        report.anti_patterns = [
            SchemaIssue(
                category="naming",
                severity="info",
                title="Test Issue",
                description="Desc",
                affected_objects=["users"],
            )
        ]
        report.index_suggestions = [
            IndexSuggestion(
                table_name="orders",
                columns=["user_id"],
            )
        ]

        summaries = analyzer._build_table_summaries(sample_schema, report)

        assert len(summaries) == 3

        users_summary = next(s for s in summaries if s.table_name == "users")
        assert users_summary.has_primary_key is True
        assert users_summary.column_count == 4
        assert len(users_summary.issues) == 1

        orders_summary = next(s for s in summaries if s.table_name == "orders")
        assert len(orders_summary.suggestions) == 1


class TestGetSchemaHealthAnalyzer:
    """Tests for factory function."""

    @pytest.mark.asyncio
    async def test_get_analyzer_without_db(self):
        """Test factory without database session."""
        with patch("src.llm.ollama_client.get_ollama_client") as mock_get_client:
            mock_get_client.return_value = MagicMock()

            analyzer = await get_schema_health_analyzer()

            assert analyzer is not None
            assert analyzer.client is not None

    @pytest.mark.asyncio
    async def test_get_analyzer_with_model_override(self):
        """Test factory with model override."""
        with patch("src.llm.ollama_client.get_ollama_client") as mock_get_client:
            mock_get_client.return_value = MagicMock()

            analyzer = await get_schema_health_analyzer(model="custom-model")

            assert analyzer.model == "custom-model"
