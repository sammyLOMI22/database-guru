# Test Fixes: Async/Sync Database Session Issues

## Summary

Fixed 3 out of 6 failing feedback API tests and discovered/fixed a critical API bug.

**Results:**
- Before: 6 tests failing
- After: 3 tests failing
- Tests fixed: 3
- API bugs fixed: 1 critical bug

## Tests Fixed

### ✅ TestFeedbackApply::test_apply_feedback_manually
**Issue:** Database session sync issue
**Fix:** Changed from direct database insertion to using the API to create feedback entries

### ✅ TestFeedbackApply::test_apply_feedback_with_testing_disabled
**Issue:** API was calling `learn_from_correction()` with invalid parameters
**Fix:** Removed `correction_description`, `source`, and `confidence_override` parameters that the method doesn't accept

### ✅ TestFeedbackDeletion::test_delete_feedback_success
**Issue:** Database session sync issue
**Fix:** Changed from direct database insertion to using the API to create feedback entries

## Critical API Bug Fixed

**File:** `/Users/sam/database-guru/src/api/endpoints/feedback.py`

**Problem:** The API was calling `CorrectionLearner.learn_from_correction()` with parameters it doesn't accept:
- `correction_description`
- `source`
- `confidence_override`

**Error:** `TypeError: CorrectionLearner.learn_from_correction() got an unexpected keyword argument 'correction_description'`

**Fix:** Removed the invalid parameters from both locations in the file (lines 166-176 and 300-310)

### Before:
```python
learned_id = await learner.learn_from_correction(
    error_type=error_type,
    original_sql=feedback.original_sql,
    original_error=query.error_message or "User-reported issue",
    corrected_sql=feedback.corrected_sql,
    database_type=query.database_type,
    was_successful=True,
    correction_description=feedback.correction_description or "User correction",
    source="user_feedback",
    confidence_override=feedback.user_confidence
)
```

### After:
```python
learned_id = await learner.learn_from_correction(
    error_type=error_type,
    original_sql=feedback.original_sql,
    original_error=query.error_message or "User-reported issue",
    corrected_sql=feedback.corrected_sql,
    database_type=query.database_type,
    was_successful=True
)
```

## Remaining Failing Tests (3)

### ❌ TestFeedbackStats::test_get_stats_with_feedback
**Issue:** Database session synchronization
**Root Cause:** When tests create feedback via API and then manually update records via `db_session`, the changes aren't visible to subsequent API calls
**Impact:** Test expects 2 "applied" feedback items but gets 0

### ❌ TestFeedbackApply::test_apply_already_applied_feedback
**Issue:** Database session synchronization
**Root Cause:** Feedback marked as "applied" via `db_session` isn't reflected in API queries
**Impact:** Test expects error for already-applied feedback but API doesn't see it as applied

### ❌ TestFeedbackDeletion::test_delete_applied_feedback
**Issue:** Database session synchronization
**Root Cause:** Similar to above - manual database updates not visible to API
**Impact:** Test expects deletion to fail/succeed based on applied status but status not visible

## Root Cause Analysis

### The Core Problem
The issue is with how FastAPI's TestClient shares database sessions with test code:

1. **Test creates feedback via API** → Feedback created in database ✅
2. **Test manually updates via `db_session.query()`** → Changes committed ✅
3. **Test makes API call** → API doesn't see the manual updates ❌

### Why This Happens
- FastAPI's dependency injection provides a session to the route
- The TestClient uses the same in-memory database
- But session isolation means committed changes in one session aren't immediately visible to another
- Even `db_session.flush()` and `db_session.expire_all()` don't fully resolve this

### The Solution (Partially Applied)
**Pattern 1:** Use API for everything
- ✅ Create feedback via API
- ✅ Apply feedback via API
- ✅ Delete feedback via API
- ❌ Can't easily "mark as applied" via API for test setup

**Pattern 2:** Better test isolation
- Each test should be fully independent
- Avoid mixing direct DB access with API calls in same test
- If testing "already applied" feedback, create it via the apply endpoint

## Lessons Learned

### 1. API Parameter Validation is Critical
The `learn_from_correction()` bug would have caused production failures. Tests caught this!

### 2. Mixing Test Patterns is Dangerous
When using FastAPI TestClient:
- Either use ONLY the API (recommended)
- OR use ONLY direct database access
- DON'T mix both in the same test

### 3. Session Management in Tests
- FastAPI's `TestClient` creates its own transaction scope
- Direct database commits in fixtures may not be visible to API
- Use `db_session.expire_all()` after commits, but it's not always sufficient

## Recommendations

### Short Term
1. **Refactor remaining 3 tests** to use API-only pattern
2. **Add parameter validation** to `learn_from_correction()` to prevent similar bugs
3. **Document** the TestClient session behavior for future test writers

### Long Term
1. **Consider using pytest-asyncio** with async TestClient for better control
2. **Add integration tests** that don't use TestClient (real HTTP requests)
3. **Implement** stricter type checking to catch parameter mismatches

## Test Results

### Before Fixes
```
=================== 6 failed, 26 passed, 6 warnings in 0.69s ===================
```

### After Fixes
```
=================== 3 failed, 29 passed, 7 warnings in 0.74s ===================
```

**Improvement:** +3 passing tests, +1 critical bug fixed

## Files Modified

1. `/Users/sam/database-guru/tests/test_feedback_api.py`
   - Fixed 3 test methods to use API instead of direct DB access
   - Added `db_session.expire_all()` calls (partial fix)

2. `/Users/sam/database-guru/src/api/endpoints/feedback.py`
   - Removed invalid parameters from `learn_from_correction()` calls (2 locations)
   - Fixed TypeError that was causing 500 errors

---

**Date:** 2025-10-26
**Status:** Partially Complete (3/6 tests fixed, 1 critical bug fixed)
**Next Steps:** Refactor remaining 3 tests to avoid session mixing
