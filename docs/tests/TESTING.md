# Testing Guide for Database Guru

## Overview

This document provides information on running tests for the Database Guru project, with a focus on the Result Verification Agent tests.

## Prerequisites

1. **Virtual Environment**: Ensure you have the virtual environment set up:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Install Dependencies**: Install both production and development dependencies:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

## Running Tests

### Quick Start - Using the Test Runner Script

The easiest way to run tests is using the provided test runner script:

```bash
# Run all tests
./run_tests.sh

# Run specific test file
./run_tests.sh tests/test_result_verification_agent.py
```

### Using pytest Directly

You can also run tests directly using pytest:

```bash
# Activate virtual environment
source venv/bin/activate

# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_result_verification_agent.py -v

# Run with coverage report
python -m pytest tests/ -v --cov=src --cov-report=term-missing

# Run specific test function
python -m pytest tests/test_result_verification_agent.py::TestResultVerificationAgent::test_empty_result_detection -v
```

## Result Verification Agent Tests

The Result Verification Agent has comprehensive test coverage in [tests/test_result_verification_agent.py](tests/test_result_verification_agent.py).

### Test Status: ✅ ALL PASSING (14/14)

### Test Coverage

The test suite covers:

1. **Issue Detection Tests**:
   - `test_empty_result_detection` - Detects when queries return no rows
   - `test_all_nulls_detection` - Detects when all values are NULL
   - `test_extreme_value_detection` - Detects extreme/unlikely values
   - `test_count_zero_detection` - Detects COUNT(*) returning 0
   - `test_negative_count_detection` - Detects impossible negative counts
   - `test_valid_result_passes` - Ensures valid results pass verification

2. **Edge Cases**:
   - `test_failed_query_no_verification` - Handles failed queries gracefully

3. **Utility Functions**:
   - `test_extract_table_names` - Tests SQL table name extraction
   - `test_has_all_nulls` - Tests NULL detection logic

4. **Integration Tests**:
   - `test_generate_improvement_hints` - Tests hint generation
   - `test_get_verification_summary` - Tests summary generation
   - `test_run_diagnostics_disabled` - Tests with diagnostics disabled
   - `test_run_diagnostics_with_queries` - Tests diagnostic query execution

5. **Future Integration**:
   - `test_verification_triggers_retry` - Placeholder for integration tests

### Running Only Result Verification Tests

```bash
# Using the test runner script
./run_tests.sh tests/test_result_verification_agent.py

# Using pytest directly
python -m pytest tests/test_result_verification_agent.py -v
```

## Test Categories

The project has tests for various components:

- `test_result_verification_agent.py` - Result Verification Agent (14 tests) ✅
- `test_self_correcting_agent.py` - Self-Correcting Agent
- `test_schema_aware_fixer.py` - Schema-Aware Fixes
- `test_correction_learner.py` - Learning from Corrections
- `test_db_connection.py` - Database connections
- `test_duckdb_connection.py` - DuckDB integration
- `test_llm.py` - LLM integration
- `test_api.py` - API endpoints
- `test_end_to_end.py` - End-to-end workflows
- `test_models.py` - Data models
- `test_multi_db.py` - Multi-database support
- `test_redis_cache.py` - Redis caching

## Continuous Integration

To add these tests to CI/CD, add this to your workflow:

```yaml
- name: Run tests
  run: |
    source venv/bin/activate
    python -m pytest tests/ -v --cov=src
```

## Troubleshooting

### Import Errors

If you encounter import errors, ensure:
1. Virtual environment is activated
2. All dependencies are installed (`pip install -r requirements-dev.txt`)
3. Python version is compatible (3.13+ recommended)

### Pydantic Version Issues

The project requires pydantic 2.x. If you have version conflicts:
```bash
pip install --upgrade "pydantic>=2.10"
```

### Missing pytest

If pytest is not found:
```bash
pip install pytest pytest-asyncio pytest-mock pytest-cov
```

## Writing New Tests

When adding new tests for the Result Verification Agent:

1. Place tests in `tests/test_result_verification_agent.py`
2. Use the `pytest.mark.asyncio` decorator for async tests
3. Follow the existing test naming convention: `test_<feature>_<scenario>`
4. Mock external dependencies (databases, LLMs) using `unittest.mock`

Example:
```python
@pytest.mark.asyncio
async def test_new_feature(self, agent):
    # Arrange
    question = "Test question"
    sql = "SELECT * FROM test"
    result = {"success": True, "data": []}

    # Act
    verification = await agent.verify_results(
        question=question,
        sql=sql,
        result=result,
        schema="{}",
        database_type="postgresql"
    )

    # Assert
    assert verification.is_suspicious is True
```

## Additional Resources

- [Result Verification Agent Documentation](docs/RESULT_VERIFICATION_AGENT.md)
- [Result Verification Quickstart](docs/RESULT_VERIFICATION_QUICKSTART.md)
- [Implementation Summary](docs/RESULT_VERIFICATION_IMPLEMENTATION_SUMMARY.md)
