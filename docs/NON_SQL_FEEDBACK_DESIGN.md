# Non-SQL Feedback Implementation Design

**Date**: November 9, 2025
**Status**: Phase 2 - Design
**Priority**: HIGH (26% of feedback currently unusable)

---

## Executive Summary

This document outlines the implementation plan for handling three non-SQL feedback types that are currently ignored by the system:
- **table_name** corrections (114 pending items - 9.9% of feedback)
- **column_name** corrections (74 pending items - 6.4% of feedback)
- **result_issue** reports (114 pending items - 9.9% of feedback)

**Total Impact**: 302 feedback items (26% of all feedback) will become actionable.

---

## Current System Analysis

### ✅ What's Already In Place

1. **Data Model** (`src/database/models.py`):
   - `UserFeedback` table supports all 4 feedback types
   - `correction_details` JSON field for structured data
   - `applied_successfully` flag for tracking application

2. **API Endpoint** (`src/api/endpoints/feedback.py`):
   - `/feedback/` POST endpoint accepts all feedback types
   - `/feedback/apply` POST endpoint for manual application
   - Auto-learning with 3-tier system (≥90%, ≥80%, ≥70%)

3. **Existing Components**:
   - `LocationMapper` - Maps location names to codes (e.g., "New York" → "NY")
   - `SchemaValidator` - Validates tables/columns with fuzzy matching
   - `FeedbackValidator` - Validates corrections before auto-learning

### ❌ What's Missing

1. **Storage** for learned mappings:
   - No table for column aliases/mappings
   - No table for table aliases/mappings
   - No table for result validation patterns

2. **Application Logic**:
   - No handler for `feedback_type == 'table_name'`
   - No handler for `feedback_type == 'column_name'`
   - No handler for `feedback_type == 'result_issue'`

3. **Integration**:
   - SchemaValidator doesn't check learned mappings
   - Query planner doesn't use learned aliases
   - Result verifier doesn't use learned patterns

---

## Design Approach

### Option 1: Separate Tables (Recommended) ✅

**Pros**:
- Clean separation of concerns
- Type-safe queries
- Easy to extend with specific fields
- Better indexing performance

**Cons**:
- More tables to maintain
- More complex queries for "all corrections"

### Option 2: Generic Mapping Table

**Pros**:
- Single table for all mappings
- Simpler data model

**Cons**:
- Less type-safe
- Harder to query efficiently
- Mixed concerns in one table

**Decision**: Use **Option 1** for better maintainability and performance.

---

## Implementation Plan

### 1. New Database Tables

#### Table: `column_mappings`
```sql
CREATE TABLE column_mappings (
    id INTEGER PRIMARY KEY,

    -- Mapping details
    source_column VARCHAR(255) NOT NULL,      -- User's incorrect name
    target_column VARCHAR(255) NOT NULL,      -- Correct column name
    table_name VARCHAR(255) NULL,             -- Specific table (NULL = all tables)
    database_type VARCHAR(50) NOT NULL,       -- postgres, mysql, duckdb, etc.

    -- Context
    description TEXT NULL,                    -- Why this mapping exists
    example_query TEXT NULL,                  -- Example query where this applies

    -- Learning metadata
    times_applied INTEGER DEFAULT 0,
    success_rate FLOAT DEFAULT 1.0,
    confidence_score FLOAT DEFAULT 1.0,

    -- Source tracking
    learned_from_feedback_id INTEGER NULL,    -- FK to user_feedback
    created_by VARCHAR(50) DEFAULT 'system',  -- 'user', 'admin', 'system'

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_applied_at TIMESTAMP NULL,

    -- Indexes
    INDEX idx_source_column (source_column),
    INDEX idx_target_column (target_column),
    INDEX idx_table_name (table_name),
    INDEX idx_database_type (database_type),
    UNIQUE INDEX idx_mapping (source_column, target_column, table_name, database_type)
);
```

#### Table: `table_mappings`
```sql
CREATE TABLE table_mappings (
    id INTEGER PRIMARY KEY,

    -- Mapping details
    source_table VARCHAR(255) NOT NULL,       -- User's incorrect name
    target_table VARCHAR(255) NOT NULL,       -- Correct table name
    database_type VARCHAR(50) NOT NULL,       -- postgres, mysql, duckdb, etc.

    -- Context
    description TEXT NULL,                    -- Why this mapping exists
    example_query TEXT NULL,                  -- Example query where this applies
    mapping_type VARCHAR(50) DEFAULT 'alias', -- 'alias', 'location', 'synonym'

    -- Learning metadata
    times_applied INTEGER DEFAULT 0,
    success_rate FLOAT DEFAULT 1.0,
    confidence_score FLOAT DEFAULT 1.0,

    -- Source tracking
    learned_from_feedback_id INTEGER NULL,    -- FK to user_feedback
    created_by VARCHAR(50) DEFAULT 'system',  -- 'user', 'admin', 'system'

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_applied_at TIMESTAMP NULL,

    -- Indexes
    INDEX idx_source_table (source_table),
    INDEX idx_target_table (target_table),
    INDEX idx_database_type (database_type),
    UNIQUE INDEX idx_mapping (source_table, target_table, database_type)
);
```

#### Table: `result_validation_patterns`
```sql
CREATE TABLE result_validation_patterns (
    id INTEGER PRIMARY KEY,

    -- Pattern details
    pattern_type VARCHAR(50) NOT NULL,        -- 'empty_result', 'null_values', 'suspicious_count', etc.
    pattern_description TEXT NOT NULL,         -- Human-readable description

    -- Matching criteria (JSON)
    matching_criteria JSON NOT NULL,          -- e.g., {"sql_pattern": "COUNT(*)", "expected_min": 1}

    -- Action to take
    action VARCHAR(50) NOT NULL,              -- 'regenerate', 'flag', 'suggest_correction'
    suggestion TEXT NULL,                      -- What to suggest to user

    -- Learning metadata
    times_triggered INTEGER DEFAULT 0,
    times_helpful INTEGER DEFAULT 0,          -- User confirmed it helped
    confidence_score FLOAT DEFAULT 1.0,

    -- Source tracking
    learned_from_feedback_id INTEGER NULL,    -- FK to user_feedback

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_triggered_at TIMESTAMP NULL,

    -- Indexes
    INDEX idx_pattern_type (pattern_type),
    INDEX idx_confidence (confidence_score)
);
```

### 2. New Python Classes

#### File: `src/llm/column_mapper.py` (NEW)
```python
class ColumnMapper:
    """
    Manages column name mappings and aliases

    Features:
    - Learn from user feedback
    - Apply mappings during query planning
    - Suggest correct column names with fuzzy matching
    - Track mapping success rates
    """

    async def learn_from_feedback(
        self,
        source_column: str,
        target_column: str,
        table_name: Optional[str],
        database_type: str,
        feedback_id: int
    ) -> int:
        """Create a new column mapping from user feedback"""

    async def apply_mapping(
        self,
        sql: str,
        table_name: Optional[str],
        database_type: str
    ) -> Tuple[str, List[str]]:
        """Apply learned mappings to SQL, return (modified_sql, applied_mappings)"""

    async def suggest_correct_column(
        self,
        incorrect_column: str,
        table_name: Optional[str],
        database_type: str
    ) -> Optional[str]:
        """Suggest correct column name based on learned mappings"""
```

#### File: `src/llm/table_mapper.py` (NEW)
```python
class TableMapper:
    """
    Manages table name mappings and aliases

    Features:
    - Learn from user feedback
    - Apply mappings during query planning
    - Integrate with LocationMapper for location-based tables
    - Track mapping success rates
    """

    async def learn_from_feedback(
        self,
        source_table: str,
        target_table: str,
        database_type: str,
        mapping_type: str,
        feedback_id: int
    ) -> int:
        """Create a new table mapping from user feedback"""

    async def apply_mapping(
        self,
        sql: str,
        database_type: str
    ) -> Tuple[str, List[str]]:
        """Apply learned mappings to SQL, return (modified_sql, applied_mappings)"""

    async def suggest_correct_table(
        self,
        incorrect_table: str,
        database_type: str
    ) -> Optional[str]:
        """Suggest correct table name based on learned mappings"""
```

#### File: `src/llm/result_pattern_learner.py` (NEW)
```python
class ResultPatternLearner:
    """
    Learns patterns from result issues reported by users

    Features:
    - Store result validation patterns
    - Detect similar issues in future queries
    - Suggest query corrections or regeneration
    - Track pattern effectiveness
    """

    async def learn_from_feedback(
        self,
        query: QueryHistory,
        result_issue_description: str,
        feedback_id: int
    ) -> int:
        """Create a new result validation pattern"""

    async def check_result(
        self,
        query: QueryHistory,
        result: Any
    ) -> Optional[Dict[str, Any]]:
        """Check if result matches any known issue patterns"""

    async def suggest_correction(
        self,
        query: QueryHistory,
        pattern_id: int
    ) -> Optional[str]:
        """Suggest correction based on learned pattern"""
```

### 3. Update Existing Files

#### Update: `src/api/endpoints/feedback.py`

Add handlers for non-SQL feedback types in `submit_feedback()` and `apply_feedback_to_learning()`:

```python
# In submit_feedback() - after line 93
if settings and settings.auto_learning_enabled:
    # Existing SQL correction logic (lines 93-305)
    if feedback.corrected_sql:
        # ... existing tier logic ...

    # NEW: Handle table_name corrections
    elif feedback.feedback_type == 'table_name' and feedback.correction_details:
        # Auto-apply table name corrections with confidence-based tiers
        if feedback.user_confidence >= 0.80:  # Tier 1 & 2
            table_mapper = TableMapper(db_session=db)
            await table_mapper.learn_from_feedback(
                source_table=feedback.correction_details.get('from'),
                target_table=feedback.correction_details.get('to'),
                database_type=query.database_type,
                mapping_type='user_correction',
                feedback_id=feedback_record.id
            )
            feedback_record.applied_successfully = True
            feedback_record.applied_at = datetime.utcnow()
            await db.commit()

    # NEW: Handle column_name corrections
    elif feedback.feedback_type == 'column_name' and feedback.correction_details:
        # Auto-apply column name corrections with confidence-based tiers
        if feedback.user_confidence >= 0.80:  # Tier 1 & 2
            column_mapper = ColumnMapper(db_session=db)
            await column_mapper.learn_from_feedback(
                source_column=feedback.correction_details.get('from'),
                target_column=feedback.correction_details.get('to'),
                table_name=feedback.correction_details.get('table'),
                database_type=query.database_type,
                feedback_id=feedback_record.id
            )
            feedback_record.applied_successfully = True
            feedback_record.applied_at = datetime.utcnow()
            await db.commit()

    # NEW: Handle result_issue feedback
    elif feedback.feedback_type == 'result_issue':
        # Store result validation pattern
        pattern_learner = ResultPatternLearner(db_session=db)
        await pattern_learner.learn_from_feedback(
            query=query,
            result_issue_description=feedback.correction_description or '',
            feedback_id=feedback_record.id
        )
        feedback_record.applied_successfully = True
        feedback_record.applied_at = datetime.utcnow()
        await db.commit()
```

#### Update: `src/core/schema_validator.py`

Integrate column/table mappers for intelligent suggestions:

```python
class SchemaValidator:
    def __init__(self, schema: Dict[str, Any], db_session: Optional[AsyncSession] = None):
        # ... existing init ...
        self.column_mapper = ColumnMapper(db_session) if db_session else None
        self.table_mapper = TableMapper(db_session) if db_session else None

    async def suggest_column_name(self, column: str, table: str) -> List[str]:
        """Get suggestions including learned mappings"""
        suggestions = []

        # Check learned mappings first
        if self.column_mapper:
            learned_suggestion = await self.column_mapper.suggest_correct_column(
                incorrect_column=column,
                table_name=table,
                database_type=self.database_type
            )
            if learned_suggestion:
                suggestions.append(f"{learned_suggestion} (learned from feedback)")

        # Fall back to fuzzy matching
        fuzzy_suggestions = self._fuzzy_match_column(column, table)
        suggestions.extend(fuzzy_suggestions)

        return suggestions
```

#### Update: `src/llm/result_verification_agent.py`

Check for known result patterns:

```python
class ResultVerificationAgent:
    def __init__(self, db_session: Optional[AsyncSession] = None):
        # ... existing init ...
        self.pattern_learner = ResultPatternLearner(db_session) if db_session else None

    async def verify_result(self, query: QueryHistory, result: Any) -> VerificationResult:
        # ... existing verification logic ...

        # Check for known result patterns
        if self.pattern_learner:
            pattern_match = await self.pattern_learner.check_result(query, result)
            if pattern_match:
                return VerificationResult(
                    is_valid=False,
                    confidence=pattern_match['confidence'],
                    issues=[f"Known issue: {pattern_match['description']}"],
                    suggestions=[pattern_match['suggestion']]
                )
```

---

## Data Flow

### Table Name Correction Flow

```
1. User submits feedback:
   POST /api/feedback
   {
     "query_id": 123,
     "feedback_type": "table_name",
     "correction_details": {
       "from": "customer",
       "to": "customers",
       "reason": "Table name is plural"
     },
     "user_confidence": 0.95
   }

2. System creates feedback record

3. Auto-learning (if confidence >= 0.80):
   - TableMapper.learn_from_feedback()
   - Creates entry in table_mappings
   - Marks feedback.applied_successfully = true

4. Future queries:
   - SchemaValidator checks table_mappings
   - Suggests "customers" when "customer" is used
   - Query planner uses correct table name
```

### Column Name Correction Flow

```
1. User submits feedback:
   POST /api/feedback
   {
     "query_id": 456,
     "feedback_type": "column_name",
     "correction_details": {
       "from": "price",
       "to": "unit_price",
       "table": "products",
       "reason": "Column is named unit_price in schema"
     },
     "user_confidence": 0.90
   }

2. System creates feedback record

3. Auto-learning (if confidence >= 0.80):
   - ColumnMapper.learn_from_feedback()
   - Creates entry in column_mappings
   - Marks feedback.applied_successfully = true

4. Future queries:
   - SchemaValidator checks column_mappings
   - Suggests "unit_price" when "price" is used in products table
   - Query planner uses correct column name
```

### Result Issue Flow

```
1. User submits feedback:
   POST /api/feedback
   {
     "query_id": 789,
     "feedback_type": "result_issue",
     "correction_description": "Query returns empty results but should find customers in NY",
     "correction_details": {
       "issue_type": "empty_result",
       "expected": "non-empty result set",
       "actual": "0 rows",
       "context": "User asked for 'New York' but query used 'NY'"
     },
     "user_confidence": 0.85
   }

2. System creates feedback record

3. Learning:
   - ResultPatternLearner.learn_from_feedback()
   - Creates pattern in result_validation_patterns
   - Links to LocationMapper for future NY/New York issues

4. Future queries:
   - ResultVerificationAgent checks patterns
   - Detects similar empty result scenarios
   - Suggests query regeneration with location expansion
```

---

## Testing Strategy

### 1. Unit Tests

**File**: `tests/test_column_mapper.py` (NEW)
```python
- test_learn_column_mapping()
- test_apply_column_mapping()
- test_suggest_correct_column()
- test_mapping_with_specific_table()
- test_mapping_across_all_tables()
```

**File**: `tests/test_table_mapper.py` (NEW)
```python
- test_learn_table_mapping()
- test_apply_table_mapping()
- test_suggest_correct_table()
- test_location_based_mapping()
```

**File**: `tests/test_result_pattern_learner.py` (NEW)
```python
- test_learn_result_pattern()
- test_check_result_against_patterns()
- test_suggest_correction()
- test_pattern_effectiveness_tracking()
```

### 2. Integration Tests

**File**: `tests/test_non_sql_feedback_integration.py` (NEW)
```python
- test_submit_table_name_feedback_and_auto_apply()
- test_submit_column_name_feedback_and_auto_apply()
- test_submit_result_issue_feedback()
- test_table_mapping_used_in_future_query()
- test_column_mapping_used_in_future_query()
- test_result_pattern_detected_in_future_query()
```

### 3. API Tests

**File**: `tests/test_feedback_api.py` (UPDATE)
```python
- test_submit_table_name_feedback()
- test_submit_column_name_feedback()
- test_submit_result_issue_feedback()
- test_apply_table_name_feedback()
- test_apply_column_name_feedback()
- test_non_sql_feedback_stats()
```

---

## Frontend Integration

### UI Updates Required

1. **Feedback Submission Form** (`frontend/src/components/QueryInterface.tsx`):
   - Add form fields for table_name corrections
   - Add form fields for column_name corrections
   - Add form for result_issue reporting

2. **Feedback Dashboard** (`frontend/src/components/FeedbackStats.tsx`):
   - Show "Apply" button for table_name feedback (not just "Info Only")
   - Show "Apply" button for column_name feedback (not just "Info Only")
   - Show mapped corrections count
   - Add badge for "Mapping Applied" status

3. **Query Results View**:
   - Add "Report Result Issue" button
   - Add dropdown for common result issues:
     - Empty results (expected data)
     - NULL values (should have data)
     - Suspicious counts
     - Incorrect data
     - Performance issue

---

## Migration Script

**File**: `scripts/add_non_sql_feedback_tables.py` (NEW)

```python
"""
Add tables for non-SQL feedback handling

Creates:
- column_mappings
- table_mappings
- result_validation_patterns

Run with: python scripts/add_non_sql_feedback_tables.py
"""
```

---

## Metrics & Monitoring

### Success Metrics

1. **Mapping Usage**:
   - Column mappings created per week
   - Table mappings created per week
   - Mapping success rate (applied successfully / total attempts)
   - Mappings reused in future queries

2. **Result Patterns**:
   - Patterns created per week
   - Patterns triggered (detected similar issues)
   - Pattern helpfulness (user confirmed vs rejected)

3. **Feedback Processing**:
   - % of non-SQL feedback auto-applied (target: 50-75% like SQL)
   - Time to apply non-SQL feedback (target: <100ms like SQL)
   - Non-SQL feedback backlog reduction (target: 0 pending)

### Monitoring Queries

```sql
-- Column mappings created recently
SELECT COUNT(*) as new_mappings
FROM column_mappings
WHERE created_at > datetime('now', '-7 days');

-- Table mappings usage
SELECT
    source_table,
    target_table,
    times_applied,
    success_rate
FROM table_mappings
ORDER BY times_applied DESC
LIMIT 10;

-- Result patterns effectiveness
SELECT
    pattern_type,
    COUNT(*) as times_triggered,
    AVG(CASE WHEN times_helpful > 0 THEN 1.0 ELSE 0.0 END) as helpfulness_rate
FROM result_validation_patterns
GROUP BY pattern_type;
```

---

## Implementation Phases

### Phase 2a: Foundation (6-8 hours)
- [ ] Create database migration script
- [ ] Implement ColumnMapper class
- [ ] Implement TableMapper class
- [ ] Implement ResultPatternLearner class
- [ ] Add unit tests for new classes

### Phase 2b: Integration (4-6 hours)
- [ ] Update feedback.py endpoint
- [ ] Integrate with SchemaValidator
- [ ] Integrate with ResultVerificationAgent
- [ ] Add integration tests
- [ ] Update API documentation

### Phase 2c: Frontend (4-6 hours)
- [ ] Update feedback submission UI
- [ ] Add "Apply" buttons for non-SQL feedback
- [ ] Update feedback dashboard
- [ ] Add result issue reporting UI
- [ ] Frontend testing

### Phase 2d: Testing & Deployment (2-3 hours)
- [ ] Manual testing
- [ ] Database migration in staging
- [ ] Monitor metrics
- [ ] Production deployment

**Total Estimate**: 16-23 hours

---

## Security Considerations

### 1. SQL Injection Protection

- Table/column mappings are string replacements - MUST validate before applying
- Use parameterized queries when testing mappings
- Sanitize all user-provided correction_details

### 2. Validation

- Verify target_table exists in schema before creating mapping
- Verify target_column exists in schema before creating mapping
- Limit mapping strings to alphanumeric + underscore
- Prevent circular mappings (A → B → A)

### 3. Rate Limiting

- Limit mapping creation per user (prevent spam)
- Require minimum confidence (e.g., 0.70) for auto-application
- Admin approval for mappings used in production queries

---

## Backward Compatibility

### Data Model
- ✅ No breaking changes - using existing UserFeedback table
- ✅ correction_details JSON field already exists
- ✅ New tables are additive

### API
- ✅ No breaking changes - feedback_type already supports all types
- ✅ Existing endpoints work unchanged
- ✅ New functionality is opt-in

### Deployment
- ✅ Can deploy without downtime
- ✅ Run migration script during maintenance window
- ✅ Old feedback data remains accessible

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Bad mappings learned | Users get wrong suggestions | Require 0.80+ confidence, allow admin review |
| Circular mappings | Infinite loops | Detect and prevent during creation |
| Performance impact | Slower query planning | Index mappings, cache frequently used ones |
| Schema drift | Mappings become stale | Track success rate, auto-disable low performers |
| User confusion | UI too complex | Simple forms, good tooltips, examples |

---

## Future Enhancements (Phase 3)

1. **Mapping Approval Workflow**:
   - Admin dashboard for reviewing high-impact mappings
   - User voting on mapping quality
   - Automatic retirement of low-success mappings

2. **Advanced Pattern Learning**:
   - ML-based pattern detection
   - Semantic similarity for mapping suggestions
   - Context-aware mapping (query intent based)

3. **Cross-Database Learning**:
   - Learn mappings from one database, suggest for similar schemas
   - Database-agnostic mapping rules
   - Schema evolution tracking

4. **Analytics Dashboard**:
   - Mapping effectiveness trends
   - Most common corrections
   - User contribution leaderboard

---

## Conclusion

This design enables Database Guru to learn from **all** user feedback, not just SQL corrections. By implementing table/column mappings and result validation patterns, we'll:

- ✅ Make 26% more feedback actionable (302 items)
- ✅ Improve schema suggestion accuracy
- ✅ Detect and prevent repeated result issues
- ✅ Provide better user experience

**Expected Impact**: **35-50% improvement in query accuracy** through accumulated non-SQL learnings.

---

**Status**: Ready for implementation (Phase 2a)
**Next Step**: Create database migration and implement ColumnMapper class
**Questions/Feedback**: See GitHub issues or Slack #database-guru
