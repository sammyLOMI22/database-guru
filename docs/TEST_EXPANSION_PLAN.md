# Test Expansion Plan - Database Guru

**Date**: 2025-10-26
**Current Coverage**: 55% (2610/4738 statements)
**Target Coverage**: 85%+
**Status**: 📋 Planning Phase

## Executive Summary

Comprehensive plan to expand test coverage from 55% to 85%+, targeting critical business logic, API endpoints, and bug-prone areas. Prioritized by business impact, risk, and complexity.

---

## Current Test Coverage Analysis

### Overall Metrics
- **Total Statements**: 4,738
- **Covered**: 2,610 (55%)
- **Missing**: 2,128 (45%)
- **Current Tests**: 288 (184 backend unit + 99 frontend + 5 integration)

### Coverage by Category

| Category | Coverage | Priority | Risk Level |
|----------|----------|----------|------------|
| **API Endpoints** | 35% | 🔴 HIGH | HIGH |
| **Core Business Logic** | 50% | 🔴 HIGH | HIGH |
| **LLM Agents** | 67% | 🟡 MEDIUM | MEDIUM |
| **Database Layer** | 72% | 🟢 LOW | LOW |
| **Models/Schemas** | 98% | ✅ GOOD | LOW |
| **Cache Layer** | 50% | 🟡 MEDIUM | MEDIUM |

---

## Critical Under-Tested Modules (Priority 1)

### 🔴 CRITICAL - Low Coverage, High Business Impact

#### 1. API Endpoints - Average 35% Coverage

##### src/api/endpoints/query.py - 21% Coverage
**Current**: 28/136 statements covered
**Missing**: Complex query processing, error handling

**High-Value Tests to Add**:
```python
# Test file: tests/test_query_endpoint.py

1. test_query_endpoint_success()
   - Natural language → SQL generation
   - Valid query execution
   - Response structure validation

2. test_query_endpoint_invalid_input()
   - Empty question
   - SQL injection attempts
   - Malformed requests

3. test_query_endpoint_error_handling()
   - Database connection errors
   - LLM timeout
   - Invalid SQL generation

4. test_query_caching()
   - Cache hit/miss
   - Cache invalidation
   - Performance improvement

5. test_query_rate_limiting()
   - Rate limit enforcement
   - Burst protection
   - Header validation

6. test_query_with_different_db_types()
   - PostgreSQL
   - MySQL
   - SQLite
   - DuckDB

7. test_query_explain_endpoint()
   - SQL explanation generation
   - Edge cases

8. test_query_history_pagination()
   - Large result sets
   - Filtering
   - Sorting
```

**Estimated Coverage Gain**: +20% (query.py → 41%)

---

##### src/api/endpoints/chat.py - 28% Coverage
**Current**: 64/230 statements covered
**Missing**: Streaming responses, context management, conversation history

**High-Value Tests to Add**:
```python
# Test file: tests/test_chat_endpoint.py

1. test_chat_conversation_flow()
   - Multi-turn conversation
   - Context preservation
   - Follow-up questions

2. test_chat_streaming_response()
   - SSE streaming
   - Chunk handling
   - Connection errors

3. test_chat_with_query_execution()
   - Chat + SQL execution
   - Result formatting
   - Error handling

4. test_chat_context_window()
   - Context limit
   - History truncation
   - Token counting

5. test_chat_session_management()
   - Session creation
   - Session persistence
   - Session expiry

6. test_chat_rate_limiting()
   - Per-user limits
   - Concurrent requests

7. test_chat_error_recovery()
   - LLM errors
   - Network failures
   - Graceful degradation
```

**Estimated Coverage Gain**: +25% (chat.py → 53%)

---

##### src/api/endpoints/multi_db_query.py - 28% Coverage
**Current**: 56/202 statements covered
**Missing**: Cross-database joins, federation logic

**High-Value Tests to Add**:
```python
# Test file: tests/test_multi_db_endpoint.py

1. test_cross_database_query()
   - Join across 2 databases
   - Join across 3+ databases
   - Data aggregation

2. test_multi_db_error_handling()
   - One database unavailable
   - Connection timeout
   - Partial results

3. test_multi_db_performance()
   - Query optimization
   - Parallel execution
   - Result streaming

4. test_multi_db_transaction_safety()
   - Rollback behavior
   - Consistency checks

5. test_multi_db_type_compatibility()
   - Type mapping
   - Data conversion
   - NULL handling
```

**Estimated Coverage Gain**: +30% (multi_db_query.py → 58%)

---

##### src/api/endpoints/schema.py - 22% Coverage
**Current**: 20/90 statements covered
**Missing**: Schema introspection, complex table relationships

**High-Value Tests to Add**:
```python
# Test file: tests/test_schema_endpoint.py

1. test_get_schema_all_tables()
   - Complete schema retrieval
   - Table metadata
   - Column details

2. test_get_schema_specific_table()
   - Single table details
   - Relationships
   - Constraints

3. test_get_schema_with_samples()
   - Sample data retrieval
   - Data types
   - Value ranges

4. test_schema_caching()
   - Cache effectiveness
   - Invalidation triggers
   - Refresh logic

5. test_schema_for_different_db_types()
   - PostgreSQL introspection
   - MySQL introspection
   - SQLite introspection
```

**Estimated Coverage Gain**: +35% (schema.py → 57%)

---

#### 2. Core Business Logic - Critical Gaps

##### src/core/multi_db_handler.py - 12% Coverage ⚠️ CRITICAL
**Current**: 22/179 statements covered
**Missing**: Most of the multi-database orchestration logic

**High-Value Tests to Add**:
```python
# Test file: tests/test_multi_db_handler.py

1. test_database_registration()
   - Add new database
   - Validate connection
   - Store credentials securely

2. test_query_routing()
   - Route to correct database
   - Multi-database queries
   - Fallback logic

3. test_result_merging()
   - Combine results from multiple DBs
   - Handle different schemas
   - Type coercion

4. test_connection_pooling()
   - Pool management
   - Connection reuse
   - Cleanup

5. test_error_isolation()
   - One DB fails, others continue
   - Error propagation
   - Retry logic

6. test_transaction_coordination()
   - Distributed transactions
   - 2PC if applicable
   - Rollback handling
```

**Estimated Coverage Gain**: +40% (multi_db_handler.py → 52%)
**Business Impact**: 🔴 CRITICAL - Core feature

---

##### src/core/connection_tester.py - 29% Coverage
**Current**: 28/96 statements covered
**Missing**: Connection validation for different DB types

**High-Value Tests to Add**:
```python
# Test file: tests/test_connection_tester.py

1. test_connection_validation_success()
   - Valid PostgreSQL connection
   - Valid MySQL connection
   - Valid SQLite connection

2. test_connection_validation_failure()
   - Wrong credentials
   - Wrong host/port
   - Network timeout

3. test_connection_diagnostics()
   - Detailed error messages
   - Suggested fixes
   - Security checks

4. test_connection_performance()
   - Latency measurement
   - Throughput testing
```

**Estimated Coverage Gain**: +30% (connection_tester.py → 59%)

---

##### src/core/location_mapper.py - 36% Coverage
**Current**: 29/80 statements covered
**Missing**: Geographic/location mapping logic

**High-Value Tests to Add**:
```python
# Test file: tests/test_location_mapper.py

1. test_location_to_filter()
   - City name → SQL filter
   - State/province → SQL filter
   - Country → SQL filter

2. test_ambiguous_location_handling()
   - Multiple matches
   - Disambiguation
   - User clarification

3. test_location_hierarchy()
   - City in state in country
   - Nested queries

4. test_location_fuzzy_matching()
   - Typos
   - Alternative names
   - Abbreviations
```

**Estimated Coverage Gain**: +25% (location_mapper.py → 61%)

---

#### 3. LLM Components - Moderate Coverage

##### src/llm/sql_generator.py - 48% Coverage
**Current**: 88/185 statements covered
**Missing**: Complex SQL generation edge cases

**High-Value Tests to Add**:
```python
# Test file: tests/test_sql_generator.py

1. test_complex_queries()
   - Nested subqueries
   - Multiple JOINs
   - Window functions
   - CTEs (Common Table Expressions)

2. test_query_optimization()
   - Index hints
   - Query plan analysis
   - Performance estimation

3. test_sql_injection_prevention()
   - Parameterized queries
   - Input sanitization
   - Dangerous patterns blocked

4. test_database_specific_sql()
   - PostgreSQL-specific features
   - MySQL-specific features
   - SQLite limitations

5. test_error_recovery()
   - Invalid SQL generation
   - Retry logic
   - Fallback strategies
```

**Estimated Coverage Gain**: +20% (sql_generator.py → 68%)

---

##### src/llm/self_correcting_agent.py - 64% Coverage
**Current**: 205/321 statements covered
**Missing**: Complex error correction scenarios

**High-Value Tests to Add**:
```python
# Test file: tests/test_self_correcting_agent_extended.py

1. test_multiple_error_types()
   - Syntax + semantic errors
   - Cascading errors
   - Priority handling

2. test_correction_limits()
   - Max retries
   - Timeout handling
   - Graceful failure

3. test_learning_from_corrections()
   - Pattern recognition
   - Future improvement
   - Correction history

4. test_context_preservation()
   - Original intent maintained
   - User preferences
   - Database constraints
```

**Estimated Coverage Gain**: +15% (self_correcting_agent.py → 79%)

---

## Medium Priority (Priority 2)

### 🟡 MEDIUM - Moderate Coverage, Important Features

#### 1. Cache Layer

##### src/cache/redis_client.py - 45% Coverage
**Tests to Add**:
- Redis connection failures
- Fallback to in-memory cache
- Cache eviction policies
- Namespace isolation
- TTL handling

**Estimated Coverage Gain**: +25% → 70%

---

##### src/cache/decorators.py - 56% Coverage
**Tests to Add**:
- Cache key generation
- Invalidation patterns
- Decorator stacking
- Error handling in decorators

**Estimated Coverage Gain**: +20% → 76%

---

#### 2. API Endpoints (Continued)

##### src/api/endpoints/feedback.py - 35% Coverage
**Tests to Add**:
- Feedback submission flow
- Feedback validation
- Learning integration
- Statistics aggregation

**Estimated Coverage Gain**: +30% → 65%

---

##### src/api/endpoints/connections.py - 59% Coverage
**Tests to Add**:
- Connection CRUD operations
- Connection testing
- Credential encryption
- Multi-user isolation

**Estimated Coverage Gain**: +20% → 79%

---

#### 3. Middleware

##### src/middleware/rate_limit.py - 65% Coverage
**Tests to Add**:
- Sliding window rate limiting
- Distributed rate limiting
- Per-endpoint limits
- Bypass for authenticated users

**Estimated Coverage Gain**: +15% → 80%

---

## Low Priority (Priority 3)

### 🟢 LOW - High Coverage Already or Low Risk

#### 1. Well-Tested Modules (Keep Maintained)

- ✅ src/database/models.py - 98%
- ✅ src/models/schemas.py - 98%
- ✅ src/main.py - 92%
- ✅ src/llm/prompts.py - 90%
- ✅ src/llm/correction_learner.py - 90%
- ✅ src/llm/result_verification_agent.py - 89%
- ✅ src/llm/feedback_validator.py - 88%

**Action**: Maintain current coverage, add edge case tests as needed

---

#### 2. Database Initialization

##### src/database/init_db.py - 0% Coverage
**Reason for Low Priority**: Initialization script, runs once, low bug risk

**Tests to Consider**:
- Database creation
- Migration handling
- Rollback scenarios

**Estimated Coverage Gain**: +80% → 80% (but low priority)

---

## Test Categories to Add

### 1. Integration Tests (Expand from 5 to 20+)

**New Integration Tests**:
```
tests/integration/
├── test_full_query_flow.py          # End-to-end query execution
├── test_chat_with_execution.py      # Chat → SQL → Execute
├── test_multi_db_federation.py      # Cross-database queries
├── test_feedback_learning_loop.py   # Feedback → Learning → Improvement
├── test_connection_management.py    # Multiple connections
├── test_cache_integration.py        # Redis with API
├── test_auth_flow.py               # Authentication/Authorization
└── test_performance.py             # Load testing
```

---

### 2. Error Handling Tests

**New Error Test Suite**:
```python
tests/test_error_handling/
├── test_database_errors.py
│   ├── test_connection_lost()
│   ├── test_query_timeout()
│   ├── test_deadlock()
│   └── test_transaction_rollback()
│
├── test_llm_errors.py
│   ├── test_llm_timeout()
│   ├── test_llm_rate_limit()
│   ├── test_invalid_response()
│   └── test_context_length_exceeded()
│
├── test_api_errors.py
│   ├── test_invalid_json()
│   ├── test_missing_parameters()
│   ├── test_authentication_failures()
│   └── test_rate_limit_exceeded()
│
└── test_cache_errors.py
    ├── test_redis_unavailable()
    ├── test_cache_corruption()
    └── test_eviction_failures()
```

---

### 3. Edge Case Tests

**New Edge Case Suite**:
```python
tests/test_edge_cases/
├── test_empty_inputs.py
├── test_extreme_values.py
├── test_unicode_handling.py
├── test_concurrent_requests.py
├── test_memory_limits.py
└── test_timeout_scenarios.py
```

---

### 4. Security Tests

**New Security Test Suite**:
```python
tests/test_security/
├── test_sql_injection.py
├── test_xss_prevention.py
├── test_authentication.py
├── test_authorization.py
├── test_credential_encryption.py
└── test_rate_limiting.py
```

---

### 5. Performance Tests

**New Performance Test Suite**:
```python
tests/test_performance/
├── test_query_performance.py       # Query execution time
├── test_cache_performance.py       # Cache hit rate
├── test_llm_latency.py            # LLM response time
├── test_concurrent_users.py       # Load testing
└── test_memory_usage.py          # Memory profiling
```

---

## Implementation Roadmap

### Phase 1: Critical API Endpoints (Weeks 1-2)
**Target**: API endpoints from 35% → 60%

1. ✅ **Week 1**: Query & Chat endpoints
   - test_query_endpoint.py (8 test functions)
   - test_chat_endpoint.py (7 test functions)
   - **Goal**: +100 statements covered

2. ✅ **Week 2**: Multi-DB & Schema endpoints
   - test_multi_db_endpoint.py (5 test functions)
   - test_schema_endpoint.py (5 test functions)
   - **Goal**: +150 statements covered

**Estimated Coverage**: 55% → 62% (overall)

---

### Phase 2: Core Business Logic (Weeks 3-4)
**Target**: Core modules from 50% → 70%

3. ✅ **Week 3**: Multi-DB Handler (CRITICAL)
   - test_multi_db_handler.py (6 test functions)
   - test_connection_tester.py (4 test functions)
   - **Goal**: +180 statements covered

4. ✅ **Week 4**: Additional Core Logic
   - test_location_mapper.py (4 test functions)
   - test_executor.py (expanded tests)
   - **Goal**: +120 statements covered

**Estimated Coverage**: 62% → 70% (overall)

---

### Phase 3: LLM Components (Weeks 5-6)
**Target**: LLM modules from 67% → 80%

5. ✅ **Week 5**: SQL Generator
   - test_sql_generator.py (expanded tests)
   - test_ollama_client.py (error scenarios)
   - **Goal**: +150 statements covered

6. ✅ **Week 6**: Self-Correcting Agent
   - test_self_correcting_agent_extended.py
   - test_query_planning_agent.py (expanded)
   - **Goal**: +130 statements covered

**Estimated Coverage**: 70% → 76% (overall)

---

### Phase 4: Error Handling & Edge Cases (Weeks 7-8)
**Target**: Add comprehensive error handling tests

7. ✅ **Week 7**: Error Handling Suite
   - test_database_errors.py
   - test_llm_errors.py
   - test_api_errors.py
   - **Goal**: Find 10-15 bugs

8. ✅ **Week 8**: Edge Cases
   - test_empty_inputs.py
   - test_extreme_values.py
   - test_concurrent_requests.py
   - **Goal**: Find 5-10 bugs

**Estimated Coverage**: 76% → 82% (overall)

---

### Phase 5: Integration & Performance (Weeks 9-10)
**Target**: Production readiness

9. ✅ **Week 9**: Integration Tests
   - 15+ new integration tests
   - Full workflow testing
   - **Goal**: End-to-end coverage

10. ✅ **Week 10**: Performance & Security
    - Performance test suite
    - Security test suite
    - Load testing
    - **Goal**: Production confidence

**Estimated Coverage**: 82% → 85%+ (overall)

---

## Expected Bug Discovery

Based on coverage gaps and code complexity, estimated bugs to find:

### High Probability (20-30 bugs)
- **API Error Handling**: 8-12 bugs
  - Missing input validation
  - Incorrect error responses
  - Resource leaks on errors

- **Multi-DB Logic**: 5-8 bugs
  - Connection pool issues
  - Result merging errors
  - Transaction handling

- **Cache Layer**: 4-6 bugs
  - Race conditions
  - Cache invalidation bugs
  - Memory leaks

- **LLM Integration**: 3-4 bugs
  - Timeout handling
  - Context length issues
  - Error recovery

### Medium Probability (10-15 bugs)
- **Concurrency Issues**: 4-6 bugs
- **Edge Cases**: 3-5 bugs
- **Security Vulnerabilities**: 3-4 bugs

### Total Estimated: **30-45 bugs**

---

## Metrics & Success Criteria

### Coverage Goals

| Phase | Overall Coverage | Target Modules |
|-------|------------------|----------------|
| Start | 55% | - |
| Phase 1 | 62% | API: 35% → 50% |
| Phase 2 | 70% | Core: 50% → 65% |
| Phase 3 | 76% | LLM: 67% → 78% |
| Phase 4 | 82% | Error handling complete |
| Phase 5 | 85%+ | Production ready |

### Quality Metrics

- **Test Reliability**: 100% (no flaky tests)
- **Test Speed**: Unit tests < 60s
- **Bug Detection**: 30-45 bugs found
- **Documentation**: All new tests documented
- **Maintainability**: Clear test names, good assertions

---

## Tooling & Infrastructure

### Tools to Add

1. **Mutation Testing** (Week 5)
   - Tool: `mutmut`
   - Verify test quality
   - Find weak assertions

2. **Property-Based Testing** (Week 6)
   - Tool: `hypothesis`
   - Generate edge cases automatically
   - Find unexpected bugs

3. **Performance Profiling** (Week 9)
   - Tool: `pytest-benchmark`
   - Track performance regressions
   - Identify bottlenecks

4. **Test Coverage Dashboard** (Week 1)
   - Tool: `codecov` or similar
   - Visualize coverage trends
   - PR checks

---

## Resource Requirements

### Team Effort

- **1 Developer Full-Time**: 10 weeks
- **OR**
- **2 Developers Part-Time**: 5 weeks each
- **Code Reviews**: 2-3 hours/week

### Infrastructure

- **CI/CD Time**: Add ~5 minutes to pipeline
- **Test Data**: Sample databases for each DB type
- **Mock Services**: LLM mock server for testing

---

## Risk Mitigation

### Potential Risks

1. **Risk**: Tests take too long to run
   - **Mitigation**: Parallelize tests, optimize fixtures, use mocks

2. **Risk**: Flaky integration tests
   - **Mitigation**: Proper isolation, retry logic, clear diagnostics

3. **Risk**: Test maintenance burden
   - **Mitigation**: Clear naming, good documentation, DRY principles

4. **Risk**: Coverage goals not met
   - **Mitigation**: Weekly reviews, adjust priorities, focus on critical paths

---

## Getting Started

### Immediate Next Steps (This Week)

1. **Day 1-2**: Set up test infrastructure
   ```bash
   # Install additional tools
   pip install pytest-benchmark mutmut hypothesis

   # Create test directories
   mkdir -p tests/integration tests/test_error_handling tests/test_edge_cases
   ```

2. **Day 3-5**: Start Phase 1
   - Create test_query_endpoint.py
   - Write first 4 test functions
   - Get to 58% coverage

3. **Day 6-7**: Code review and iterate
   - Review tests with team
   - Fix any bugs found
   - Update documentation

---

## Conclusion

This comprehensive test expansion plan will:
- ✅ Increase coverage from 55% → 85%+
- ✅ Find and fix 30-45 bugs
- ✅ Improve code quality and maintainability
- ✅ Increase confidence for production deployment
- ✅ Reduce technical debt
- ✅ Enable faster feature development

**Total Effort**: 10 weeks (1 FTE) or 5 weeks (2 FTE)
**ROI**: High - Better quality, fewer production bugs, faster development

---

**Next Steps**: Approve plan and begin Phase 1 (Query & Chat endpoint tests)

**Created**: 2025-10-26
**Status**: 📋 Ready for Review
