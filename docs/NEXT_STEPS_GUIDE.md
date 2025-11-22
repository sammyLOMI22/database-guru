# Next Steps Guide - Database Guru

**Date**: November 9, 2025
**Current Status**: Phase 2 Complete - Non-SQL Feedback Fully Integrated
**System Health**: ✅ Excellent (66/66 tests passing, all components functional)

---

## Executive Summary

The Database Guru feedback system has completed two major phases:
- ✅ **Phase 1** (Nov 9): Fixed learning pipeline, implemented 3-tier auto-approval
- ✅ **Phase 2** (Nov 9): Implemented non-SQL feedback handling (column/table/result patterns)

**Current Capabilities**:
- ✅ Auto-learns from SQL corrections (Tier 1/2/3 system)
- ✅ Auto-learns from column name corrections (instant)
- ✅ Auto-learns from table name corrections (instant)
- ✅ Auto-learns from result validation patterns (instant)
- ✅ 66/66 tests passing for all feedback components

**What's Next**: Integration with query processing + UI enhancements

---

## Quick Start Priorities

### 🔥 Immediate (Next 1-2 Days)

#### 1. Test Phase 2 Integration (30 minutes)
**Purpose**: Verify non-SQL feedback learning works end-to-end

**Manual Test Steps**:
```bash
# 1. Start the application
./start.sh

# 2. Submit column name correction
curl -X POST http://localhost:8000/api/feedback/ \
  -H "Content-Type: application/json" \
  -d '{
    "query_id": 1,
    "feedback_type": "column_name",
    "correction_description": "Column is unit_price not price",
    "correction_details": {
      "source_column": "price",
      "target_column": "unit_price",
      "table_name": "products"
    },
    "user_confidence": 1.0
  }'

# 3. Check logs for learning confirmation
# Look for: "✅ Column mapping learned: price → unit_price"

# 4. Verify in database
sqlite3 database_guru.db "SELECT * FROM column_mappings ORDER BY id DESC LIMIT 1;"

# 5. Check feedback was marked as applied
sqlite3 database_guru.db "SELECT applied_successfully, user_notes FROM user_feedback ORDER BY id DESC LIMIT 1;"
```

**Expected Results**:
- ✅ Feedback marked as `applied_successfully=true`
- ✅ New record in `column_mappings` table
- ✅ Log shows "✅ Column mapping learned"
- ✅ `user_notes` contains `[AUTO-LEARNED] Column mapping created: id=X`

**Repeat for**:
- Table name corrections
- Result validation patterns

---

#### 2. Run Database Migrations (5 minutes)
**Purpose**: Ensure production database has all required tables

```bash
# Run Phase 2 migrations if not already done
python scripts/add_non_sql_feedback_tables.py

# Add connection_name field to mapping tables
python scripts/add_connection_name_to_mappings.py

# Verify tables exist
sqlite3 database_guru.db "
SELECT name FROM sqlite_master
WHERE type='table'
AND name IN ('column_mappings', 'table_mappings', 'result_validation_patterns');
"
# Should return all 3 table names
```

---

#### 3. Monitor Initial Usage (Ongoing)
**Purpose**: Track how often learned patterns are being created

**Key Metrics to Watch**:
```sql
-- Check daily feedback volume
SELECT
    DATE(created_at) as date,
    feedback_type,
    COUNT(*) as count,
    SUM(CASE WHEN applied_successfully THEN 1 ELSE 0 END) as learned
FROM user_feedback
WHERE created_at >= DATE('now', '-7 days')
GROUP BY DATE(created_at), feedback_type
ORDER BY date DESC;

-- Check mapping usage
SELECT COUNT(*) as total_column_mappings FROM column_mappings;
SELECT COUNT(*) as total_table_mappings FROM table_mappings;
SELECT COUNT(*) as total_result_patterns FROM result_validation_patterns;

-- Check most learned patterns
SELECT source_column, target_column, table_name, times_applied
FROM column_mappings
ORDER BY times_applied DESC
LIMIT 10;
```

---

### 🚀 High Priority (Next Week)

#### 4. Integrate Learned Mappings with Query Planning (4-6 hours)
**Purpose**: Actually use the learned column/table mappings during SQL generation

**File**: `src/llm/query_planning_agent.py`

**Implementation**:
```python
# Add imports
from src.llm.column_mapper import ColumnMapper
from src.llm.table_mapper import TableMapper

# In create_plan() method, before generating SQL:
async def create_plan(
    self,
    question: str,
    schema_info: Dict[str, Any],
    connection_name: str,  # NEW: Pass from caller
    database_type: str,
    ...
) -> QueryPlan:
    # ... existing plan creation logic ...

    # NEW: Apply learned mappings to generated SQL
    column_mapper = ColumnMapper(db_session=self.db_session)
    table_mapper = TableMapper(db_session=self.db_session)

    # Apply column mappings
    corrected_sql, col_applied = await column_mapper.apply_mappings(
        sql=plan.generated_sql,
        table_name=plan.primary_table,
        connection_name=connection_name,
        database_type=database_type
    )

    # Apply table mappings
    corrected_sql, tbl_applied = await table_mapper.apply_mappings(
        sql=corrected_sql,
        connection_name=connection_name,
        database_type=database_type
    )

    if col_applied or tbl_applied:
        logger.info(
            f"✨ Applied {len(col_applied)} column and {len(tbl_applied)} table mappings"
        )
        plan.generated_sql = corrected_sql
        plan.trace.steps.append({
            "stage": "mapping_application",
            "column_mappings": col_applied,
            "table_mappings": tbl_applied
        })

    return plan
```

**Testing**:
1. Create a column mapping (price → unit_price)
2. Ask question: "Show me products with price over 100"
3. Verify generated SQL uses `unit_price` instead of `price`
4. Check trace shows mapping was applied

**Impact**: Users won't have to correct the same column/table names repeatedly!

---

#### 5. Integrate Result Validation with Result Verification Agent (3-4 hours)
**Purpose**: Detect result issues automatically during query execution

**File**: `src/llm/result_verification_agent.py`

**Implementation**:
```python
# Add import
from src.llm.result_pattern_learner import ResultPatternLearner

# In verify_result() method:
async def verify_result(
    self,
    sql: str,
    result_data: List[Dict[str, Any]],
    row_count: int,
    connection_name: str,  # NEW: Pass from caller
    table_name: Optional[str] = None,
    ...
) -> VerificationResult:
    # ... existing validation logic ...

    # NEW: Check against learned patterns
    pattern_learner = ResultPatternLearner(db_session=self.db_session)

    validation_result = await pattern_learner.validate_result(
        sql=sql,
        result_data=result_data,
        row_count=row_count,
        table_name=table_name
    )

    if not validation_result.is_valid:
        logger.warning(
            f"⚠️ Learned pattern detected issue: {validation_result.message}"
        )

        return VerificationResult(
            is_valid=False,
            issues=[validation_result.message],
            warnings=[],
            suggestions=[validation_result.suggestion] if validation_result.suggestion else [],
            confidence=0.8,
            should_regenerate=True
        )

    # ... continue with existing validation ...

    return VerificationResult(is_valid=True, ...)
```

**Testing**:
1. Create empty result pattern (table: users, filters: status=inactive)
2. Execute query: "SELECT * FROM users WHERE status = 'inactive'"
3. Verify system detects issue and suggests fix
4. Check logs show pattern was triggered

**Impact**: Automatically detect and warn about common result problems!

---

#### 6. Add Mapping Management API Endpoints (2-3 hours)
**Purpose**: Allow viewing and managing learned patterns via API

**File**: `src/api/endpoints/mappings.py` (NEW)

**Endpoints to Create**:
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.dependencies.common import get_db
from src.llm.column_mapper import ColumnMapper
from src.llm.table_mapper import TableMapper
from src.llm.result_pattern_learner import ResultPatternLearner

router = APIRouter(prefix="/mappings", tags=["Mappings"])

# Column mappings
@router.get("/columns")
async def get_column_mappings(
    connection_name: Optional[str] = None,
    table_name: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """List learned column mappings"""
    # Implementation

@router.delete("/columns/{mapping_id}")
async def delete_column_mapping(
    mapping_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a column mapping"""
    mapper = ColumnMapper(db_session=db)
    deleted = await mapper.delete_mapping(mapping_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Mapping not found")

@router.get("/columns/stats")
async def get_column_mapping_stats(
    database_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get column mapping statistics"""
    mapper = ColumnMapper(db_session=db)
    return await mapper.get_mapping_stats(database_type)

# Table mappings (similar structure)
@router.get("/tables")
@router.delete("/tables/{mapping_id}")
@router.get("/tables/stats")

# Result patterns (similar structure)
@router.get("/patterns")
@router.delete("/patterns/{pattern_id}")
@router.get("/patterns/stats")
@router.post("/patterns/{pattern_id}/helpful")
async def mark_pattern_helpful(
    pattern_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Mark a pattern as helpful"""
    learner = ResultPatternLearner(db_session=db)
    success = await learner.mark_pattern_helpful(pattern_id)
    if not success:
        raise HTTPException(status_code=404, detail="Pattern not found")
```

**Register Router**:
```python
# In src/main.py
from src.api.endpoints import mappings

app.include_router(mappings.router, prefix="/api")
```

---

#### 7. Create Mappings Dashboard UI Component (4-6 hours)
**Purpose**: Display learned patterns in frontend

**Files to Create**:
- `frontend/src/components/LearnedMappingsPanel.tsx`
- `frontend/src/components/MappingStatsDisplay.tsx`
- `frontend/src/services/mappingsApi.ts`

**Component Structure**:
```typescript
// LearnedMappingsPanel.tsx
interface LearnedMappingsPanelProps {
  connectionName?: string;
}

export const LearnedMappingsPanel: React.FC<LearnedMappingsPanelProps> = ({
  connectionName
}) => {
  const [activeTab, setActiveTab] = useState<'columns' | 'tables' | 'patterns'>('columns');

  return (
    <div className="learned-mappings-panel">
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="columns">Column Mappings</TabsTrigger>
          <TabsTrigger value="tables">Table Mappings</TabsTrigger>
          <TabsTrigger value="patterns">Result Patterns</TabsTrigger>
        </TabsList>

        <TabsContent value="columns">
          <ColumnMappingsList connectionName={connectionName} />
        </TabsContent>

        <TabsContent value="tables">
          <TableMappingsList connectionName={connectionName} />
        </TabsContent>

        <TabsContent value="patterns">
          <ResultPatternsList />
        </TabsContent>
      </Tabs>

      <MappingStatsDisplay />
    </div>
  );
};

// Display format
interface ColumnMapping {
  id: number;
  source_column: string;
  target_column: string;
  table_name: string | null;
  connection_name: string;
  times_applied: number;
  confidence_score: number;
}

const ColumnMappingsList = () => {
  // Display as table:
  // Source → Target | Table | Connection | Times Used | Confidence | Actions
  // price → unit_price | products | sales_db | 15 | 0.95 | [Delete]
};
```

**Integration**:
Add to main app or settings page:
```typescript
// In App.tsx or SettingsPage.tsx
import { LearnedMappingsPanel } from './components/LearnedMappingsPanel';

<Section title="Learned Patterns">
  <LearnedMappingsPanel connectionName={currentConnection} />
</Section>
```

---

### 📊 Medium Priority (Next 2 Weeks)

#### 8. Add Pattern Effectiveness Analytics (4-6 hours)
**Purpose**: Track how well learned patterns are working

**Metrics Dashboard**:
```typescript
interface PatternEffectivenessMetrics {
  // Column Mappings
  totalColumnMappings: number;
  totalColumnApplications: number;
  mostUsedColumnMappings: Array<{
    source: string;
    target: string;
    table: string;
    timesApplied: number;
  }>;

  // Table Mappings
  totalTableMappings: number;
  totalTableApplications: number;

  // Result Patterns
  totalPatterns: number;
  totalTriggers: number;
  totalHelpful: number;
  helpfulnessRate: number;
  patternsByType: {
    empty_result: number;
    missing_data: number;
    suspicious_values: number;
  };
}
```

**Display**:
- Line chart: Mapping applications over time
- Pie chart: Pattern types distribution
- Bar chart: Most frequently used mappings
- Success rate: Helpfulness percentage

---

#### 9. Implement Fuzzy Column/Table Name Suggestions (6-8 hours)
**Purpose**: Auto-suggest corrections when user enters wrong name

**Enhancement to ColumnMapper/TableMapper**:
```python
# In ColumnMapper
async def suggest_from_schema(
    self,
    incorrect_column: str,
    available_columns: List[str],
    connection_name: str,
    database_type: str
) -> Optional[str]:
    """
    Suggest correct column based on:
    1. Learned mappings (exact match)
    2. Fuzzy similarity to available columns
    3. Common patterns (e.g., 'email' → 'email_address')
    """

    # First check learned mappings
    suggestion = await self.suggest_correct_column(
        incorrect_column=incorrect_column,
        table_name=None,
        connection_name=connection_name,
        database_type=database_type
    )

    if suggestion:
        return suggestion

    # Fall back to fuzzy matching
    from src.llm.column_mapper import find_similar_columns
    matches = find_similar_columns(
        target_column=incorrect_column,
        available_columns=available_columns,
        threshold=0.6
    )

    return matches[0][0] if matches else None
```

**Integration with SchemaValidator**:
```python
# In SchemaValidator
if column_not_found:
    suggestion = await column_mapper.suggest_from_schema(
        incorrect_column=column_name,
        available_columns=schema.columns,
        connection_name=connection_name,
        database_type=database_type
    )

    if suggestion:
        return ValidationResult(
            valid=False,
            message=f"Column '{column_name}' not found. Did you mean '{suggestion}'?",
            suggestion=suggestion
        )
```

---

#### 10. Add Batch Pattern Learning (3-4 hours)
**Purpose**: Learn multiple patterns from historical feedback

**Script**: `scripts/learn_from_historical_feedback.py`

```python
"""
Learn patterns from historical feedback that wasn't auto-applied

This script:
1. Finds all pending feedback with high confidence
2. Validates corrections
3. Bulk applies to learning systems
4. Reports results
"""

async def learn_from_historical():
    # Get high-confidence pending feedback
    pending = await get_pending_feedback(min_confidence=0.85)

    results = {
        'column_mappings': 0,
        'table_mappings': 0,
        'result_patterns': 0,
        'failed': 0
    }

    for feedback in pending:
        try:
            if feedback.feedback_type == 'column_name':
                await learn_column_mapping(feedback)
                results['column_mappings'] += 1
            # ... etc
        except Exception as e:
            logger.error(f"Failed to learn from feedback {feedback.id}: {e}")
            results['failed'] += 1

    print(f"Learned {results['column_mappings']} column mappings")
    print(f"Learned {results['table_mappings']} table mappings")
    print(f"Learned {results['result_patterns']} result patterns")
    print(f"Failed: {results['failed']}")
```

---

### 🔮 Future Enhancements (Backlog)

#### 11. Machine Learning for Pattern Detection (20+ hours)
- Train model on historical feedback
- Auto-detect common patterns
- Predict which corrections user will want

#### 12. Cross-Database Pattern Generalization (10-15 hours)
- Learn patterns that work across multiple databases
- Suggest mappings based on similar database schemas
- Transfer learning between connections

#### 13. User-Specific Preferences (8-10 hours)
- Per-user column/table preferences
- User-specific confidence thresholds
- Personalized suggestion ranking

#### 14. Pattern Confidence Decay (4-6 hours)
- Reduce confidence of unused patterns over time
- Auto-archive stale patterns
- Prompt for pattern revalidation

#### 15. Advanced Result Validation (10-15 hours)
- Statistical anomaly detection
- Expected value range learning
- Temporal pattern validation

---

## Testing Checklist

### Before Each Release

**Unit Tests**:
- [ ] All 66 mapper tests passing
- [ ] New integration tests passing
- [ ] No regressions in existing tests

**Integration Tests**:
- [ ] Column mapping end-to-end flow
- [ ] Table mapping end-to-end flow
- [ ] Result pattern learning and validation
- [ ] Mapping application during query planning

**Manual Tests**:
- [ ] Submit column name feedback → Verify learned
- [ ] Submit table name feedback → Verify learned
- [ ] Submit result issue feedback → Verify pattern created
- [ ] Execute query with learned mapping → Verify applied
- [ ] Trigger result pattern → Verify validation message
- [ ] View mappings in UI → Verify display
- [ ] Delete mapping → Verify removed

**Performance Tests**:
- [ ] 100 concurrent feedback submissions
- [ ] 1000 mappings applied per query
- [ ] Pattern validation under load

---

## Monitoring & Observability

### Key Metrics to Track

**Daily**:
```sql
-- Feedback volume
SELECT feedback_type, COUNT(*)
FROM user_feedback
WHERE DATE(created_at) = DATE('now')
GROUP BY feedback_type;

-- Learning rate
SELECT
    COUNT(*) as submitted,
    SUM(applied_successfully) as learned,
    ROUND(100.0 * SUM(applied_successfully) / COUNT(*), 1) as rate
FROM user_feedback
WHERE DATE(created_at) = DATE('now');
```

**Weekly**:
```sql
-- Mapping usage
SELECT
    'Column Mappings' as type,
    COUNT(*) as total,
    SUM(times_applied) as applications
FROM column_mappings
UNION ALL
SELECT
    'Table Mappings',
    COUNT(*),
    SUM(times_applied)
FROM table_mappings;

-- Pattern effectiveness
SELECT
    pattern_type,
    COUNT(*) as patterns,
    SUM(times_triggered) as triggers,
    SUM(times_helpful) as helpful,
    ROUND(100.0 * SUM(times_helpful) / NULLIF(SUM(times_triggered), 0), 1) as rate
FROM result_validation_patterns
GROUP BY pattern_type;
```

**Monthly**:
- Review low-usage mappings (consider archiving)
- Review high-usage patterns (document as best practices)
- Analyze failure patterns (improve validation)

---

## Troubleshooting Guide

### Issue: Mappings not being created

**Check**:
1. Logs show `"📋 Processing column name feedback"` ?
2. `correction_details` properly formatted?
3. Database connection exists for query?
4. No errors in `_handle_non_sql_feedback()`?

**Fix**:
- Verify correction_details schema
- Check connection_name extraction logic
- Review error logs

### Issue: Mappings created but not applied

**Solution**: Integrate with Query Planning Agent (Step 4 above)

### Issue: Pattern triggered incorrectly

**Check**:
1. Pattern matching criteria too broad?
2. Confidence threshold too low?
3. False positive in validation logic?

**Fix**:
- Adjust pattern matching_criteria
- Increase confidence threshold
- Review `_check_pattern_match()` logic

---

## Documentation Updates Needed

- [ ] Update API documentation (Swagger/OpenAPI)
- [ ] Update user guide with non-SQL feedback examples
- [ ] Add mapping management to admin guide
- [ ] Create pattern learning best practices doc
- [ ] Update troubleshooting guide

---

## Success Metrics (30-Day Goals)

| Metric | Current | Target | How to Measure |
|--------|---------|--------|----------------|
| Column Mappings Learned | 0 | 50+ | `SELECT COUNT(*) FROM column_mappings` |
| Table Mappings Learned | 0 | 30+ | `SELECT COUNT(*) FROM table_mappings` |
| Result Patterns Learned | 0 | 20+ | `SELECT COUNT(*) FROM result_validation_patterns` |
| Mapping Applications | 0 | 200+ | `SELECT SUM(times_applied) FROM column_mappings` |
| Pattern Helpfulness Rate | N/A | >70% | `SELECT 100*SUM(times_helpful)/SUM(times_triggered) FROM result_validation_patterns` |
| Non-SQL Feedback Processed | 0% | 90%+ | `SELECT 100*SUM(applied_successfully)/COUNT(*) FROM user_feedback WHERE feedback_type != 'sql_correction'` |

---

## Quick Reference

### Key Files
- `src/llm/column_mapper.py` - Column mapping logic
- `src/llm/table_mapper.py` - Table mapping logic
- `src/llm/result_pattern_learner.py` - Result pattern logic
- `src/api/endpoints/feedback.py` - Feedback integration
- `docs/NON_SQL_FEEDBACK_INTEGRATION.md` - Integration guide
- `docs/PHASE_2_NON_SQL_FEEDBACK_COMPLETE.md` - Completion summary

### Key Commands
```bash
# Run all tests
./run_tests.sh

# Run mapper tests only
python -m pytest tests/test_column_mapper.py tests/test_table_mapper.py tests/test_result_pattern_learner.py -v

# Check learned patterns
sqlite3 database_guru.db "SELECT COUNT(*) FROM column_mappings;"
sqlite3 database_guru.db "SELECT COUNT(*) FROM table_mappings;"
sqlite3 database_guru.db "SELECT COUNT(*) FROM result_validation_patterns;"

# View recent feedback
sqlite3 database_guru.db "SELECT id, feedback_type, applied_successfully FROM user_feedback ORDER BY created_at DESC LIMIT 10;"
```

---

**Last Updated**: November 9, 2025
**Status**: Ready for Phase 3 - Integration & UI
**Owner**: Development Team
**Priority**: High - Core functionality complete, integration needed for full value
