# Lineage Intelligence Testing Guide

This guide covers how to test the Lineage Intelligence features (Phase 12) in Database Guru.

## Overview

The Lineage Intelligence system includes 5 components, each with comprehensive test coverage:

| Component | Test File | Test Count |
|-----------|-----------|------------|
| Lineage Narrator | `tests/test_lineage_narrator.py` | 474 tests |
| Impact Advisor | `tests/test_impact_advisor.py` | 455 tests |
| Schema Health Analyzer | `tests/test_schema_health.py` | 817 tests |
| Pattern Intelligence | `tests/test_pattern_intelligence.py` | 584 tests |
| Conversational Lineage | `tests/test_lineage_conversation.py` | 630 tests |

## Running Tests

### Run All Lineage Intelligence Tests

```bash
# Activate virtual environment
source venv/bin/activate

# Run all Phase 12 tests
./run_tests.sh tests/test_lineage_narrator.py tests/test_impact_advisor.py \
  tests/test_schema_health.py tests/test_pattern_intelligence.py \
  tests/test_lineage_conversation.py

# Or using pytest directly
python -m pytest tests/test_lineage_*.py tests/test_impact_advisor.py \
  tests/test_schema_health.py tests/test_pattern_intelligence.py -v
```

### Run Individual Component Tests

```bash
# Lineage Narrator (Phase 12.1)
./run_tests.sh tests/test_lineage_narrator.py

# Impact Advisor (Phase 12.2)
./run_tests.sh tests/test_impact_advisor.py

# Schema Health Analyzer (Phase 12.3)
./run_tests.sh tests/test_schema_health.py

# Pattern Intelligence (Phase 12.4)
./run_tests.sh tests/test_pattern_intelligence.py

# Conversational Lineage (Phase 12.5)
./run_tests.sh tests/test_lineage_conversation.py
```

### Run with Coverage

```bash
python -m pytest tests/test_lineage_narrator.py tests/test_impact_advisor.py \
  tests/test_schema_health.py tests/test_pattern_intelligence.py \
  tests/test_lineage_conversation.py \
  --cov=src/lineage --cov-report=html

# Open coverage report
open htmlcov/index.html
```

## Test Categories

### Unit Tests

Each component has unit tests that mock LLM responses:

```python
# Example: Testing LineageNarrator with mocked Ollama
@pytest.fixture
def mock_ollama_client():
    client = MagicMock()
    client.generate = AsyncMock(return_value={
        "response": '{"summary": "Test summary", "confidence": 0.85}'
    })
    return client

async def test_generate_narrative(mock_ollama_client):
    narrator = LineageNarrator(ollama_client=mock_ollama_client)
    narrative = await narrator.generate_narrative(lineage_graph)
    assert narrative.summary == "Test summary"
    assert narrative.confidence == 0.85
```

### Integration Tests

Tests that verify component interactions:

```python
@pytest.mark.integration
async def test_impact_advisor_with_real_analyzer():
    """Test Impact Advisor uses ImpactAnalyzer correctly."""
    advisor = await get_impact_advisor(db=test_db)
    advice = await advisor.analyze_with_recommendations(
        db=test_db,
        change_type="rename_column",
        table_name="customers",
        column_name="state"
    )
    assert advice.impact is not None
    assert advice.migration_plan is not None
```

### Timeout Tests

Tests that verify graceful degradation on LLM timeout:

```python
async def test_narrative_timeout_fallback():
    """Verify fallback narrative on LLM timeout."""
    narrator = LineageNarrator(timeout_seconds=0.001)  # Very short timeout
    narrative = await narrator.generate_narrative(lineage_graph)
    # Should return fallback, not raise exception
    assert narrative.summary != ""
    assert narrative.confidence < 0.5  # Low confidence for fallback
```

## Component-Specific Testing

### 1. Lineage Narrator (Phase 12.1)

**Key test areas:**
- Narrative generation from lineage graphs
- Column explanation extraction
- Transformation explanation
- Timeout handling and fallback
- JSON parsing with malformed responses

```bash
# Run narrator tests
./run_tests.sh tests/test_lineage_narrator.py -v

# Run specific test class
python -m pytest tests/test_lineage_narrator.py::TestLineageNarratorGeneration -v
```

**Test fixtures:**
- `sample_lineage_graph` - Complex query with JOINs and aggregations
- `simple_lineage_graph` - Basic SELECT query
- `mock_ollama_client` - Mocked LLM client

### 2. Impact Advisor (Phase 12.2)

**Key test areas:**
- Migration plan generation
- SQL patch creation
- Risk explanation generation
- Change type handling (rename, drop, etc.)
- LLM response parsing

```bash
# Run impact advisor tests
./run_tests.sh tests/test_impact_advisor.py -v

# Run SQL patch tests specifically
python -m pytest tests/test_impact_advisor.py::TestSQLPatchGeneration -v
```

**Test fixtures:**
- `sample_impact_analysis` - Pre-computed impact data
- `affected_queries` - Sample affected query list
- `mock_db_session` - Mocked database session

### 3. Schema Health Analyzer (Phase 12.3)

**Key test areas:**
- Health grade calculation (A-F)
- Index suggestion generation
- Normalization issue detection
- Anti-pattern detection
- Per-table health summaries

```bash
# Run schema health tests
./run_tests.sh tests/test_schema_health.py -v

# Run grade calculation tests
python -m pytest tests/test_schema_health.py::TestHealthGradeCalculation -v
```

**Test fixtures:**
- `sample_schema` - Database schema with various issues
- `healthy_schema` - Well-designed schema (Grade A)
- `problematic_schema` - Schema with many issues (Grade D/F)

### 4. Pattern Intelligence (Phase 12.4)

**Key test areas:**
- Bottleneck root cause analysis
- Anti-pattern detection (SELECT *, N+1, etc.)
- Optimization suggestion generation
- Trend analysis
- Query history processing

```bash
# Run pattern intelligence tests
./run_tests.sh tests/test_pattern_intelligence.py -v

# Run anti-pattern detection tests
python -m pytest tests/test_pattern_intelligence.py::TestAntiPatternDetection -v
```

**Test fixtures:**
- `sample_heatmap_data` - Query pattern data
- `bottleneck_data` - High-latency table data
- `query_history` - Sample query history

### 5. Conversational Lineage (Phase 12.5)

**Key test areas:**
- Question classification (lineage, impact, pattern, etc.)
- Answer generation for each question type
- Multi-turn conversation context
- Follow-up suggestion generation
- Session management

```bash
# Run conversation tests
./run_tests.sh tests/test_lineage_conversation.py -v

# Run question classification tests
python -m pytest tests/test_lineage_conversation.py::TestQuestionClassifier -v
```

**Test fixtures:**
- `sample_questions` - Questions for each type
- `conversation_context` - Multi-turn context
- `mock_connection` - Database connection mock

## Manual Testing

### API Testing with curl

```bash
# 1. Test Lineage Narrative
curl -X POST "http://localhost:8000/api/lineage/parse?explain=true" \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "SELECT c.name, SUM(o.total) FROM customers c JOIN orders o ON c.id = o.customer_id GROUP BY c.name"
  }'

# 2. Test Impact Advisor
curl -X POST http://localhost:8000/api/lineage/impact/advise \
  -H "Content-Type: application/json" \
  -d '{
    "change_type": "rename_column",
    "table_name": "customers",
    "column_name": "state",
    "new_value": "region",
    "include_patches": true
  }'

# 3. Test Schema Health
curl http://localhost:8000/api/lineage/schema/health/1

# 4. Test Pattern Intelligence
curl http://localhost:8000/api/lineage/patterns/1/analyze?time_range=30

# 5. Test Conversational Lineage
curl -X POST http://localhost:8000/api/lineage/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the most used tables?",
    "connection_id": 1
  }'
```

### UI Testing Checklist

#### Lineage Narrator
- [ ] Parse SQL with "Generate Explanation" checked
- [ ] Verify narrative panel appears
- [ ] Check summary, data flow, column explanations
- [ ] Verify confidence score displays
- [ ] Test with complex multi-join queries

#### Impact Advisor
- [ ] Select change type from dropdown
- [ ] Enter table and column names
- [ ] Check "Include SQL Patches"
- [ ] Verify migration plan steps display
- [ ] Check SQL patches are copyable
- [ ] Verify risk level badge color

#### Schema Health Dashboard
- [ ] Select a database connection
- [ ] Verify health grade displays (A-F)
- [ ] Check score bar fills correctly
- [ ] Expand index suggestions section
- [ ] Verify CREATE INDEX SQL is copyable
- [ ] Check anti-patterns section
- [ ] Review per-table summaries

#### Pattern Intelligence
- [ ] Select connection and time range
- [ ] Switch between Analysis/Bottlenecks/Trends views
- [ ] Verify bottleneck cards display
- [ ] Check optimization suggestions
- [ ] Verify anti-pattern badges
- [ ] Review trend charts

#### Conversational Lineage
- [ ] Type a question and submit
- [ ] Verify question type badge appears
- [ ] Check answer displays with supporting data
- [ ] Click a follow-up suggestion
- [ ] Verify context is maintained
- [ ] Try questions of each type

## Writing New Tests

### Test Template

```python
"""Tests for [Component Name]."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.lineage.your_component import YourComponent

@pytest.fixture
def mock_ollama_client():
    """Create mocked Ollama client."""
    client = MagicMock()
    client.generate = AsyncMock(return_value={
        "response": '{"key": "value"}'
    })
    return client

@pytest.fixture
def sample_data():
    """Create sample test data."""
    return {...}

class TestYourComponent:
    """Tests for YourComponent."""

    @pytest.mark.asyncio
    async def test_basic_functionality(self, mock_ollama_client, sample_data):
        """Test basic operation."""
        component = YourComponent(ollama_client=mock_ollama_client)
        result = await component.process(sample_data)
        assert result is not None

    @pytest.mark.asyncio
    async def test_error_handling(self, mock_ollama_client):
        """Test error handling."""
        mock_ollama_client.generate.side_effect = Exception("LLM Error")
        component = YourComponent(ollama_client=mock_ollama_client)
        # Should handle gracefully
        result = await component.process({})
        assert result.is_fallback

    @pytest.mark.asyncio
    async def test_timeout_fallback(self):
        """Test timeout produces fallback."""
        component = YourComponent(timeout_seconds=0.001)
        result = await component.process({})
        assert result.confidence < 0.5
```

### Mocking Best Practices

1. **Mock LLM responses** - Always mock `ollama_client.generate()`
2. **Mock database sessions** - Use `AsyncMock` for async sessions
3. **Use realistic data** - Match production response formats
4. **Test edge cases** - Empty data, malformed JSON, timeouts

## Troubleshooting Test Failures

### Common Issues

**1. Async test not running:**
```python
# Add marker to async tests
@pytest.mark.asyncio
async def test_something():
    ...
```

**2. Mock not applied:**
```python
# Ensure patch path matches import location
@patch('src.lineage.component.OllamaClient')
```

**3. JSON parsing errors:**
```python
# Ensure mock response is valid JSON string
mock.generate.return_value = {"response": '{"valid": "json"}'}
```

**4. Database session issues:**
```python
# Use proper async mock
db = AsyncMock(spec=AsyncSession)
db.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(...)))
```

## CI/CD Integration

Tests run automatically on:
- Push to any branch
- Pull request creation
- Nightly scheduled runs

See `.github/workflows/tests.yml` for configuration.

## Related Documentation

- [Testing Guide](TESTING_GUIDE.md) - General testing practices
- [Lineage Intelligence User Guide](../LINEAGE_INTELLIGENCE_USER_GUIDE.md) - Feature documentation
- [Data Lineage Guide](../DATA_LINEAGE_GUIDE.md) - Core lineage features
