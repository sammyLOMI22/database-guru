# Test Script Guide

The enhanced `run_tests.sh` script now automatically discovers all test files and organizes them into categories for easy testing.

## Quick Reference

### List All Available Tests
```bash
./run_tests.sh --list
```

### Run All Tests (Default)
```bash
./run_tests.sh
```

### Run All Tests with Coverage
```bash
./run_tests.sh all
```

## Test Categories

### Core/Unit Tests
Tests database connections, models, schema validation, and executor:
```bash
./run_tests.sh core
```
**Includes:** 11 test files (db_connection, llm, duckdb, models, executor, schema_validator, schema_sampling, schema_validation_standalone, schema_cache, agent_trace, formatting)

### Agent Tests
Tests all AI agents (self-correcting, query planning, confidence scoring):
```bash
./run_tests.sh agents
```
**Includes:** 6 test files (self_correcting_agent, schema_aware_fixer, confidence_scorer, correction_learner, query_planning_agent, result_verification_agent)

### API/Endpoint Tests
Tests all REST API endpoints:
```bash
./run_tests.sh api
```
**Includes:** 9 test files (api, query_endpoints, conversation_api, feedback_api, streaming_api, multi_db_streaming_api, mappings_api, cache_endpoints, index_recommendations_api)

### Feedback System Tests
Tests user feedback submission and validation:
```bash
./run_tests.sh feedback
```
**Includes:** 3 test files (feedback_api, feedback_validator, feedback_integration)

### Parallel Execution Tests
Tests parallel corrections and multi-database execution:
```bash
./run_tests.sh parallel
```
**Includes:** 2 test files (parallel_corrections, parallel_multi_db)

### Streaming Tests
Tests streaming response functionality:
```bash
./run_tests.sh streaming
```
**Includes:** 3 test files (streaming, streaming_api, multi_db_streaming_api)

### Cache Tests
Tests Redis and semantic caching:
```bash
./run_tests.sh cache
```
**Includes:** 3 test files (redis_cache, semantic_caching, cache_endpoints)

### Mapping/Learning Tests
Tests column/table mapping and pattern learning:
```bash
./run_tests.sh mapping
```
**Includes:** 4 test files (column_mapper, table_mapper, result_pattern_learner, mapping_cache)

### Security Tests
Tests prompt injection protection:
```bash
./run_tests.sh security
```
**Includes:** 1 test file (prompt_sanitizer) - 29 comprehensive security tests

### Tools Tests
Tests index advisor and schema tools:
```bash
./run_tests.sh tools
```
**Includes:** 3 test files (tools, index_advisor, index_tools)

### Cleanup Tests
Tests session and history deletion:
```bash
./run_tests.sh cleanup
```
**Includes:** 2 test files (chat_session_deletion, query_history_deletion)

### Integration Tests
Tests end-to-end workflows:
```bash
./run_tests.sh integration
```
**Includes:** 3 test files (end_to_end, multi_db, conversational_memory)

## Running Specific Test Files

### By Full Filename
```bash
./run_tests.sh test_prompt_sanitizer.py
```

### By Shorthand (without test_ prefix or .py extension)
```bash
./run_tests.sh prompt_sanitizer
```

## Examples

```bash
# Run only security tests
./run_tests.sh security

# Run only parallel execution tests
./run_tests.sh parallel

# Run a specific test file
./run_tests.sh test_semantic_caching.py

# Run all tests with coverage report
./run_tests.sh all

# List all available tests and categories
./run_tests.sh --list
```

## Adding New Tests

The script automatically discovers new test files! Just add a new test file to the `tests/` directory with the naming pattern `test_*.py` and it will:

1. Appear in the `--list` output
2. Be included when running all tests
3. Be runnable individually by filename

To add a test to a category, edit the `run_tests.sh` file and add the test filename to the appropriate category case statement.

## Current Test Count

**Total: 47 test files** across 12 categories

Last updated: November 29, 2025
