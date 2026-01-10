# Phase 1: Manual Test Plan 🧪

**Purpose**: Verify all Phase 1 feedback system improvements are working correctly in a live environment.

**Time Required**: ~30-45 minutes
**Prerequisites**: Backend server running, database initialized, test data available

---

## 🔧 Setup: Prepare Test Environment

### Step 1: Start the Backend Server

```bash
cd /Users/sam/database-guru

# Activate virtual environment
source venv/bin/activate

# Start backend with logging
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000 --log-level info
```

**Expected Output**:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
```

**Keep this terminal open for monitoring logs.**

---

### Step 2: Verify System Settings

Open a new terminal and check current configuration:

```bash
cd /Users/sam/database-guru
source venv/bin/activate

# Check system settings
sqlite3 database_guru.db "SELECT * FROM system_settings;"
```

**Expected Output**:
```
1|0|0.75|immediate|1|strict|1|0|1|1|90|2025-XX-XX XX:XX:XX|2025-XX-XX XX:XX:XX
```

**Verify**:
- `confidence_threshold` = **0.75** (column 3) ✅
- `auto_learning_enabled` = **0** (disabled by default for safety)

### Step 3: Enable Auto-Learning (For Testing)

```bash
sqlite3 database_guru.db "UPDATE system_settings SET auto_learning_enabled = 1;"
sqlite3 database_guru.db "SELECT auto_learning_enabled, confidence_threshold FROM system_settings;"
```

**Expected Output**:
```
1|0.75
```

✅ Auto-learning is now enabled for testing.

### Step 4: Check Initial Database State

```bash
# Check current feedback count
sqlite3 database_guru.db "SELECT COUNT(*) FROM user_feedback;"

# Check learned corrections count (should be 0)
sqlite3 database_guru.db "SELECT COUNT(*) FROM learned_corrections;"
```

**Expected Output**:
```
1208  (or similar - total feedback entries)
0     (learned corrections - currently empty)
```

---

## 🧪 Test 1: Verify Learned Corrections Pipeline (CRITICAL)

**Objective**: Confirm async CorrectionLearner creates learned corrections successfully.

### Step 1.1: Create a Query with an Error

First, create a query that will have an error (we'll submit feedback for it):

```bash
curl -X POST "http://localhost:8000/api/query/" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "SELECT * FROM prodcuts LIMIT 10",
    "database_id": 1
  }'
```

**Note the query_id from the response** (e.g., `"id": 123`)

### Step 1.2: Submit Tier 1 Feedback (≥90% confidence)

```bash
curl -X POST "http://localhost:8000/api/feedback/" \
  -H "Content-Type: application/json" \
  -d '{
    "query_id": 123,
    "feedback_type": "sql_correction",
    "corrected_sql": "SELECT * FROM products LIMIT 10",
    "correction_description": "Fixed typo: prodcuts -> products",
    "user_confidence": 0.95
  }' | jq .
```

**Expected Response**:
```json
{
  "id": <feedback_id>,
  "query_id": 123,
  "feedback_type": "sql_correction",
  "applied_successfully": true,
  "learned_correction_id": <correction_id>,
  "user_confidence": 0.95,
  ...
}
```

**Verify**:
- ✅ `applied_successfully`: **true**
- ✅ `learned_correction_id`: **not null** (has a value)

### Step 1.3: Check Server Logs

Look for these log messages in the backend terminal:

```
🚀 TIER 1: High confidence feedback (≥90%), attempting auto-apply with STRICT validation...
🔍 Validating user correction with STRICT mode testing...
✅ Validation PASSED: Validation successful
🎓 Learning from correction: error_type=TABLE_NOT_FOUND, db_type=sqlite
✨ Created NEW learned correction: id=1, error_type=TABLE_NOT_FOUND, description=Fix for missing table: prodcuts
✨ AUTO-APPLIED: High confidence feedback automatically learned! feedback_id=X, learned_correction_id=1
```

**Verify**:
- ✅ Logs show **TIER 1** processing
- ✅ Logs show **STRICT** validation mode
- ✅ Logs show **🎓 Learning from correction**
- ✅ Logs show **✨ Created NEW learned correction**
- ✅ Logs show **✨ AUTO-APPLIED**

### Step 1.4: Verify Database Entry

```bash
# Check learned corrections table
sqlite3 database_guru.db "SELECT id, error_type, database_type, table_pattern, times_applied, confidence_score FROM learned_corrections;"
```

**Expected Output**:
```
1|TABLE_NOT_FOUND|sqlite|prodcuts|1|0.7
```

**Verify**:
- ✅ Entry exists in `learned_corrections` table
- ✅ `error_type` = TABLE_NOT_FOUND
- ✅ `times_applied` = 1
- ✅ `confidence_score` = 0.7 (initial confidence)

✅ **TEST 1 PASSED**: Learned corrections pipeline is working!

---

## 🧪 Test 2: Tier 2 Auto-Approval (≥80%, Moderate Validation)

**Objective**: Verify Tier 2 processes feedback with moderate validation.

### Step 2.1: Create Another Query

```bash
curl -X POST "http://localhost:8000/api/query/" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "SELECT pric FROM products",
    "database_id": 1
  }'
```

**Note the query_id from response** (e.g., `"id": 124`)

### Step 2.2: Submit Tier 2 Feedback (80-89% confidence)

```bash
curl -X POST "http://localhost:8000/api/feedback/" \
  -H "Content-Type: application/json" \
  -d '{
    "query_id": 124,
    "feedback_type": "sql_correction",
    "corrected_sql": "SELECT price FROM products",
    "correction_description": "Fixed column typo: pric -> price",
    "user_confidence": 0.85
  }' | jq .
```

**Expected Response**:
```json
{
  "id": <feedback_id>,
  "query_id": 124,
  "feedback_type": "sql_correction",
  "applied_successfully": true,
  "learned_correction_id": <correction_id>,
  "user_confidence": 0.85,
  ...
}
```

### Step 2.3: Check Server Logs

Look for **Tier 2** specific messages:

```
⚡ TIER 2: Medium-high confidence feedback (≥80%), attempting auto-apply with MODERATE validation...
🔍 Validating user correction with MODERATE mode testing...
✅ Validation PASSED: Validation successful
🎓 Learning from correction: error_type=COLUMN_NOT_FOUND, db_type=sqlite
✨ Created NEW learned correction: id=2, error_type=COLUMN_NOT_FOUND, description=Fix for missing column: pric
✨ AUTO-APPLIED (TIER 2): Medium-high confidence feedback automatically learned!
```

**Verify**:
- ✅ Logs show **⚡ TIER 2** (not Tier 1)
- ✅ Logs show **MODERATE** validation mode (not STRICT)
- ✅ Logs show successful learning

### Step 2.4: Verify Database

```bash
sqlite3 database_guru.db "SELECT id, error_type, column_pattern, times_applied FROM learned_corrections WHERE id = 2;"
```

**Expected Output**:
```
2|COLUMN_NOT_FOUND|pric|1
```

✅ **TEST 2 PASSED**: Tier 2 auto-approval with moderate validation works!

---

## 🧪 Test 3: Tier 3 Queueing (70-79%, Deferred Mode)

**Objective**: Verify Tier 3 queues feedback for batch processing (doesn't auto-apply).

### Step 3.1: Ensure Deferred Mode

```bash
sqlite3 database_guru.db "UPDATE system_settings SET apply_mode = 'deferred';"
sqlite3 database_guru.db "SELECT apply_mode FROM system_settings;"
```

**Expected Output**:
```
deferred
```

### Step 3.2: Submit Tier 3 Feedback (70-79% confidence)

```bash
curl -X POST "http://localhost:8000/api/feedback/" \
  -H "Content-Type: application/json" \
  -d '{
    "query_id": 124,
    "feedback_type": "sql_correction",
    "corrected_sql": "SELECT * FROM customers WHERE state = '\''CA'\''",
    "correction_description": "Added state filter",
    "user_confidence": 0.75
  }' | jq .
```

**Expected Response**:
```json
{
  "id": <feedback_id>,
  "query_id": 124,
  "applied_successfully": false,  // NOT auto-applied
  "learned_correction_id": null,  // Not learned yet
  "user_confidence": 0.75,
  ...
}
```

### Step 3.3: Check Server Logs

```
📋 TIER 3: Medium confidence feedback (70-89%), queued for batch processing (feedback_id=X)
```

**Verify**:
- ✅ Logs show **📋 TIER 3**
- ✅ Logs say "queued for batch processing"
- ✅ No auto-apply messages

### Step 3.4: Verify Database

```bash
# Check this feedback was NOT auto-applied
sqlite3 database_guru.db "SELECT applied_successfully, learned_correction_id FROM user_feedback WHERE user_confidence = 0.75 ORDER BY id DESC LIMIT 1;"
```

**Expected Output**:
```
0|   (applied_successfully=false, learned_correction_id=null)
```

✅ **TEST 3 PASSED**: Tier 3 correctly queues for manual review!

---

## 🧪 Test 4: Below 70% - Manual Review Required

**Objective**: Verify low-confidence feedback requires manual review.

### Step 4.1: Submit Low Confidence Feedback (<70%)

```bash
curl -X POST "http://localhost:8000/api/feedback/" \
  -H "Content-Type: application/json" \
  -d '{
    "query_id": 124,
    "feedback_type": "sql_correction",
    "corrected_sql": "SELECT * FROM products ORDER BY price DESC",
    "correction_description": "Not sure about this correction",
    "user_confidence": 0.65
  }' | jq .
```

**Expected Response**:
```json
{
  "applied_successfully": false,
  "learned_correction_id": null,
  "user_confidence": 0.65,
  ...
}
```

### Step 4.2: Check Server Logs

```
👁️ Low confidence feedback (<70%), manual review required (feedback_id=X)
```

**Verify**:
- ✅ Logs show **👁️** emoji
- ✅ Logs say "manual review required"
- ✅ No validation or learning attempted

✅ **TEST 4 PASSED**: Low confidence correctly requires manual review!

---

## 🧪 Test 5: Duplicate Correction Detection

**Objective**: Verify duplicate corrections update existing entries instead of creating new ones.

### Step 5.1: Submit Similar Feedback to Test 1

```bash
curl -X POST "http://localhost:8000/api/feedback/" \
  -H "Content-Type: application/json" \
  -d '{
    "query_id": 123,
    "feedback_type": "sql_correction",
    "corrected_sql": "SELECT id, name FROM products LIMIT 10",
    "correction_description": "Another fix for prodcuts typo",
    "user_confidence": 0.92
  }' | jq .
```

### Step 5.2: Check Server Logs

```
🎓 Learning from correction: error_type=TABLE_NOT_FOUND, db_type=sqlite
✅ Updated existing learned correction: id=1, times_applied=2, confidence=0.8
```

**Verify**:
- ✅ Logs show **✅ Updated existing** (not "Created NEW")
- ✅ `times_applied` increased
- ✅ `confidence` increased

### Step 5.3: Verify Database

```bash
sqlite3 database_guru.db "SELECT id, times_applied, confidence_score FROM learned_corrections WHERE id = 1;"
```

**Expected Output**:
```
1|2|0.8  (times_applied=2, confidence increased from 0.7 to 0.8)
```

✅ **TEST 5 PASSED**: Duplicate detection works correctly!

---

## 🧪 Test 6: Validation Rejection (Security Test)

**Objective**: Verify destructive operations are blocked by validation.

### Step 6.1: Submit Destructive SQL

```bash
curl -X POST "http://localhost:8000/api/feedback/" \
  -H "Content-Type: application/json" \
  -d '{
    "query_id": 124,
    "feedback_type": "sql_correction",
    "corrected_sql": "DELETE FROM products WHERE price < 10",
    "correction_description": "Remove cheap products",
    "user_confidence": 0.95
  }' | jq .
```

**Expected Response**:
```json
{
  "applied_successfully": false,
  "learned_correction_id": null,
  "user_notes": "[AUTO-APPLY REJECTED] BLOCKED: Added destructive operation 'delete from'...",
  ...
}
```

### Step 6.2: Check Server Logs

```
⚠️ Auto-apply REJECTED by validator: BLOCKED: Added destructive operation 'delete from'...
```

**Verify**:
- ✅ Feedback saved but NOT applied
- ✅ Validation rejection message in `user_notes`
- ✅ Logs show rejection reason

✅ **TEST 6 PASSED**: Security validation blocks destructive operations!

---

## 🧪 Test 7: Cleanup Script (Dry-Run)

**Objective**: Verify cleanup script safely identifies test data.

### Step 7.1: Run Cleanup Script (Dry-Run)

```bash
cd /Users/sam/database-guru
source venv/bin/activate

# Run in dry-run mode (safe, no changes)
python scripts/cleanup_test_feedback.py <<< "no"
```

**Expected Output**:
```
================================================================================
TEST DATA CLEANUP TOOL
================================================================================

🧹 Starting test data cleanup...
Mode: DRY RUN (no changes)

Current database state:
  Total feedback entries: 1208
  Total learned corrections: 2

Found 652 feedback entries matching test patterns
Found 0 orphaned feedback entries

================================================================================
PREVIEW: 652 feedback entries will be deleted:
================================================================================

--- Entry 1 (ID: 12) ---
Type: sql_correction
Description: Test with confidence 0.0
...

🔍 DRY RUN MODE: No changes made
Run with dry_run=False to actually delete 652 entries

Cleanup cancelled by user
```

**Verify**:
- ✅ Script identifies test entries
- ✅ Shows preview of deletions
- ✅ No actual changes made (dry-run)

✅ **TEST 7 PASSED**: Cleanup script works safely!

---

## 🧪 Test 8: End-to-End Feedback Lifecycle

**Objective**: Complete workflow from query error → feedback → learning → reuse.

### Step 8.1: Create Query with Error

```bash
curl -X POST "http://localhost:8000/api/query/" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Show me all users from the userz table",
    "database_id": 1
  }'
```

**Expected**: Query fails with TABLE_NOT_FOUND error.

### Step 8.2: Submit High-Confidence Correction

```bash
curl -X POST "http://localhost:8000/api/feedback/" \
  -H "Content-Type: application/json" \
  -d '{
    "query_id": <query_id_from_step_8.1>,
    "feedback_type": "sql_correction",
    "corrected_sql": "SELECT * FROM users",
    "correction_description": "Fixed table name: userz -> users",
    "user_confidence": 0.98
  }' | jq .
```

**Verify**:
- ✅ `applied_successfully`: true
- ✅ `learned_correction_id`: not null

### Step 8.3: Create Similar Error Again

```bash
curl -X POST "http://localhost:8000/api/query/" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "SELECT id, name FROM userz",
    "database_id": 1
  }'
```

### Step 8.4: Check if Learned Correction is Suggested

Look for logs showing learned corrections being retrieved:

```
Found 1 applicable corrections for TABLE_NOT_FOUND
```

**Verify**:
- ✅ System retrieves learned corrections
- ✅ Similar error pattern detected

✅ **TEST 8 PASSED**: Complete feedback lifecycle works!

---

## 📊 Final Verification Checklist

After completing all tests, verify the overall system state:

### Database State

```bash
# Count learned corrections (should be 3-4)
sqlite3 database_guru.db "SELECT COUNT(*) FROM learned_corrections;"

# View all learned corrections
sqlite3 database_guru.db "SELECT id, error_type, times_applied, confidence_score FROM learned_corrections;"

# Count auto-applied feedback
sqlite3 database_guru.db "SELECT COUNT(*) FROM user_feedback WHERE applied_successfully = 1;"

# View tier distribution
sqlite3 database_guru.db "
SELECT
  CASE
    WHEN user_confidence >= 0.90 THEN 'Tier 1 (≥90%)'
    WHEN user_confidence >= 0.80 THEN 'Tier 2 (≥80%)'
    WHEN user_confidence >= 0.70 THEN 'Tier 3 (≥70%)'
    ELSE 'Manual (<70%)'
  END as tier,
  COUNT(*) as count,
  SUM(CASE WHEN applied_successfully = 1 THEN 1 ELSE 0 END) as auto_applied
FROM user_feedback
WHERE created_at > datetime('now', '-1 hour')
GROUP BY tier;
"
```

**Expected Output (Approximate)**:
```
Learned Corrections: 3-4
Auto-Applied Feedback: 3-4 (from Tier 1 & 2)

Tier Distribution:
Tier 1 (≥90%)   | 3  | 3
Tier 2 (≥80%)   | 1  | 1
Tier 3 (≥70%)   | 1  | 0
Manual (<70%)   | 1  | 0
```

### System Health

```bash
# Check for errors in logs
grep "ERROR" backend.log | tail -20

# Check for successful learning
grep "✨ AUTO-APPLIED" backend.log | wc -l

# Check tier distribution in logs
grep "TIER 1" backend.log | wc -l
grep "TIER 2" backend.log | wc -l
grep "TIER 3" backend.log | wc -l
```

---

## ✅ Success Criteria

All tests should pass with these results:

- ✅ **Test 1**: Learned corrections created (async pipeline working)
- ✅ **Test 2**: Tier 2 auto-approval with moderate validation
- ✅ **Test 3**: Tier 3 queuing for batch review
- ✅ **Test 4**: Low confidence requires manual review
- ✅ **Test 5**: Duplicate corrections update existing entries
- ✅ **Test 6**: Destructive operations blocked by validation
- ✅ **Test 7**: Cleanup script safely identifies test data
- ✅ **Test 8**: End-to-end lifecycle works correctly

### Critical Success Indicators:

1. ✅ `learned_corrections` table has entries (not zero!)
2. ✅ Tier 1 & 2 feedback auto-applied successfully
3. ✅ Tier 3 queued (not auto-applied)
4. ✅ Destructive operations blocked
5. ✅ Logs show correct emoji-based tier indicators
6. ✅ No ERROR messages in logs

---

## 🔧 Troubleshooting

### Issue: No learned corrections created

**Check**:
```bash
sqlite3 database_guru.db "SELECT auto_learning_enabled FROM system_settings;"
```
Should be **1** (enabled).

**Fix**:
```bash
sqlite3 database_guru.db "UPDATE system_settings SET auto_learning_enabled = 1;"
```

### Issue: All feedback goes to Tier 3

**Check**:
```bash
sqlite3 database_guru.db "SELECT apply_mode FROM system_settings;"
```
Should be **"immediate"** for Tier 1 & 2 to work.

**Fix**:
```bash
sqlite3 database_guru.db "UPDATE system_settings SET apply_mode = 'immediate';"
```

### Issue: Validation always fails

**Check logs** for validation failure reasons. Common causes:
- Original SQL and corrected SQL both succeed (use MODERATE mode)
- Suspicious patterns detected
- Database connection issues

---

## 📝 Test Results Template

Use this template to record your test results:

```
PHASE 1 MANUAL TEST RESULTS
Date: _______________
Tester: _______________

Test 1 - Learned Corrections Pipeline: [ ] PASS  [ ] FAIL
  - Learned correction created: [ ] YES  [ ] NO
  - Database entry verified: [ ] YES  [ ] NO

Test 2 - Tier 2 Auto-Approval: [ ] PASS  [ ] FAIL
  - Moderate validation used: [ ] YES  [ ] NO
  - Auto-applied successfully: [ ] YES  [ ] NO

Test 3 - Tier 3 Queueing: [ ] PASS  [ ] FAIL
  - Queued for batch: [ ] YES  [ ] NO
  - Not auto-applied: [ ] YES  [ ] NO

Test 4 - Manual Review: [ ] PASS  [ ] FAIL
  - Correctly flagged: [ ] YES  [ ] NO

Test 5 - Duplicate Detection: [ ] PASS  [ ] FAIL
  - Updated existing: [ ] YES  [ ] NO
  - times_applied incremented: [ ] YES  [ ] NO

Test 6 - Security Validation: [ ] PASS  [ ] FAIL
  - Destructive blocked: [ ] YES  [ ] NO

Test 7 - Cleanup Script: [ ] PASS  [ ] FAIL
  - Test data identified: [ ] YES  [ ] NO
  - Dry-run safe: [ ] YES  [ ] NO

Test 8 - End-to-End: [ ] PASS  [ ] FAIL
  - Complete workflow: [ ] YES  [ ] NO

OVERALL RESULT: [ ] ALL PASS  [ ] ISSUES FOUND

Issues/Notes:
_____________________________________________
_____________________________________________
```

---

**Test Plan Status**: Ready for execution
**Estimated Duration**: 30-45 minutes
**Required Resources**: Backend server, database, API access

**Next Steps After Testing**:
1. Document any failures or issues
2. Re-run failed tests after fixes
3. Proceed to Phase 2 if all tests pass
4. Consider staging deployment

---

*Created: November 9, 2025*
*For: Phase 1 Feedback System Improvements*
*Version: 1.0*
