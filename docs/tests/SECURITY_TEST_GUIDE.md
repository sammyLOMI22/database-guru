# Security Testing Guide - Auto-Learning Validation

## Quick Security Tests

Test the enhanced security and validation features of the auto-learning system.

## Prerequisites

```bash
# 1. Start backend
source venv/bin/activate
python src/main.py

# 2. Enable auto-learning with strict validation
curl -X PUT http://localhost:8000/api/settings/ \
  -H "Content-Type: application/json" \
  -d '{
    "auto_learning_enabled": true,
    "validation_mode": "strict",
    "test_before_learning": true
  }'
```

## Test 1: Safe SELECT Correction (Should Auto-Apply ✅)

**Scenario:** Fix a table name typo - safe operation

```bash
# Submit a query (will fail with table not found)
QUERY_RESPONSE=$(curl -s -X POST http://localhost:8000/api/query/ \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Show all users from the usr table",
    "connection_id": 1
  }')

# Extract query_id
QUERY_ID=$(echo $QUERY_RESPONSE | jq -r '.query_id')
echo "Query ID: $QUERY_ID"

# Submit high-confidence feedback with corrected table name
curl -X POST http://localhost:8000/api/feedback/ \
  -H "Content-Type: application/json" \
  -d "{
    \"query_id\": $QUERY_ID,
    \"feedback_type\": \"sql_correction\",
    \"corrected_sql\": \"SELECT * FROM users\",
    \"correction_description\": \"Table is 'users' not 'usr'\",
    \"user_confidence\": 0.95
  }"
```

**Expected Result:**
```json
{
  "applied_successfully": true,
  "learned_correction_id": 1,
  ...
}
```

**Logs Should Show:**
```
🔍 Validating user correction with comprehensive testing...
✅ Corrected SQL succeeded
❌ Original SQL failed: no such table: usr
✅ No suspicious patterns detected
✨ AUTO-APPLIED: High confidence feedback automatically learned!
```

## Test 2: DELETE Operation (Should Block ❌)

**Scenario:** User tries to submit DELETE - should be blocked

```bash
curl -X POST http://localhost:8000/api/feedback/ \
  -H "Content-Type: application/json" \
  -d '{
    "query_id": 1,
    "feedback_type": "sql_correction",
    "corrected_sql": "DELETE FROM users WHERE id = 999",
    "correction_description": "Remove this user",
    "user_confidence": 1.0
  }'
```

**Expected Result:**
```json
{
  "applied_successfully": false,
  "user_notes": "[AUTO-APPLY REJECTED] BLOCKED: Added destructive operation 'delete from'...",
  ...
}
```

**Logs Should Show:**
```
🔍 Validating user correction with comprehensive testing...
❌ SUSPICIOUS: BLOCKED: Added destructive operation 'delete from'.
   Destructive operations require manual admin approval, even with WHERE clauses.
⚠️ Auto-apply REJECTED by validator
```

## Test 3: UPDATE Operation (Should Block ❌)

**Scenario:** User tries to submit UPDATE - should be blocked

```bash
curl -X POST http://localhost:8000/api/feedback/ \
  -H "Content-Type: application/json" \
  -d '{
    "query_id": 2,
    "feedback_type": "sql_correction",
    "corrected_sql": "UPDATE products SET price = 0 WHERE id = 1",
    "correction_description": "Fix price",
    "user_confidence": 0.95
  }'
```

**Expected Result:**
```json
{
  "applied_successfully": false,
  "user_notes": "[AUTO-APPLY REJECTED] BLOCKED: Added destructive operation 'update'...",
  ...
}
```

## Test 4: DROP TABLE (Should Block ❌)

**Scenario:** Malicious attempt to drop table

```bash
curl -X POST http://localhost:8000/api/feedback/ \
  -H "Content-Type: application/json" \
  -d '{
    "query_id": 3,
    "feedback_type": "sql_correction",
    "corrected_sql": "DROP TABLE sessions",
    "correction_description": "Clean up",
    "user_confidence": 1.0
  }'
```

**Expected Result:**
```json
{
  "applied_successfully": false,
  "user_notes": "[AUTO-APPLY REJECTED] BLOCKED: Added destructive operation 'drop table'...",
  ...
}
```

## Test 5: Operation Type Change (Should Block ❌)

**Scenario:** User changes SELECT to DELETE

```bash
curl -X POST http://localhost:8000/api/feedback/ \
  -H "Content-Type: application/json" \
  -d '{
    "query_id": 4,
    "feedback_type": "sql_correction",
    "corrected_sql": "DELETE FROM logs WHERE level = \"ERROR\"",
    "correction_description": "Remove errors",
    "user_confidence": 0.90
  }'
```

**Expected Result:** BLOCKED (destructive operation + operation type change)

## Test 6: Low Confidence (Should Not Auto-Apply)

**Scenario:** User submits with low confidence

```bash
curl -X POST http://localhost:8000/api/feedback/ \
  -H "Content-Type: application/json" \
  -d '{
    "query_id": 5,
    "feedback_type": "sql_correction",
    "corrected_sql": "SELECT * FROM customers",
    "correction_description": "Not sure about this",
    "user_confidence": 0.60
  }'
```

**Expected Result:**
```json
{
  "applied_successfully": false,
  ...
}
```

**Logs Should Show:**
```
👁️ Low confidence feedback (<70%), manual review required
```

## Test 7: Medium Confidence + Deferred Mode

**Scenario:** Test batch queueing for medium confidence

```bash
# Enable deferred mode
curl -X PUT http://localhost:8000/api/settings/ \
  -H "Content-Type: application/json" \
  -d '{"apply_mode": "deferred"}'

# Submit medium confidence feedback
curl -X POST http://localhost:8000/api/feedback/ \
  -H "Content-Type: application/json" \
  -d '{
    "query_id": 6,
    "feedback_type": "column_name",
    "corrected_sql": "SELECT user_id FROM orders",
    "correction_description": "Column is user_id not customer_id",
    "user_confidence": 0.75
  }'
```

**Expected Result:** Feedback saved but not auto-applied (queued for batch)

**Logs Should Show:**
```
📋 Medium confidence feedback (70-89%), queued for batch processing
```

## Test 8: Validation Mode - Moderate

**Scenario:** Test with less strict validation

```bash
# Switch to moderate mode
curl -X PUT http://localhost:8000/api/settings/ \
  -H "Content-Type: application/json" \
  -d '{"validation_mode": "moderate"}'

# Submit feedback
curl -X POST http://localhost:8000/api/feedback/ \
  -H "Content-Type: application/json" \
  -d '{
    "query_id": 7,
    "feedback_type": "sql_correction",
    "corrected_sql": "SELECT * FROM users WHERE created_at > DATE(\"now\", \"-30 days\")",
    "correction_description": "Add date filter for performance",
    "user_confidence": 0.95
  }'
```

**Expected Result:** May auto-apply even if original SQL also works (query refinement)

## Test 9: Check Settings

```bash
# View current settings
curl http://localhost:8000/api/settings/

# View feedback stats
curl http://localhost:8000/api/feedback/stats

# View recent feedback
curl http://localhost:8000/api/feedback/recent
```

## Test 10: Reset to Safe Defaults

```bash
# Reset all settings to safe defaults
curl -X POST http://localhost:8000/api/settings/reset

# Verify reset
curl http://localhost:8000/api/settings/ | jq '{
  auto_learning_enabled,
  validation_mode,
  allow_destructive_auto_learn
}'
```

**Expected:**
```json
{
  "auto_learning_enabled": false,
  "validation_mode": "strict",
  "allow_destructive_auto_learn": false
}
```

## Comprehensive Test Script

Run all tests at once:

```bash
#!/bin/bash
# save as: test_security.sh

echo "🔐 Security Test Suite for Auto-Learning"
echo "=========================================="

# Test 1: Safe correction
echo ""
echo "Test 1: Safe SELECT correction (should auto-apply)"
curl -s -X POST http://localhost:8000/api/feedback/ \
  -H "Content-Type: application/json" \
  -d '{"query_id": 1, "feedback_type": "sql_correction", "corrected_sql": "SELECT * FROM users", "user_confidence": 0.95}' \
  | jq '{applied_successfully, learned_correction_id}'

# Test 2: DELETE blocked
echo ""
echo "Test 2: DELETE operation (should block)"
curl -s -X POST http://localhost:8000/api/feedback/ \
  -H "Content-Type: application/json" \
  -d '{"query_id": 2, "feedback_type": "sql_correction", "corrected_sql": "DELETE FROM users WHERE id = 1", "user_confidence": 1.0}' \
  | jq '{applied_successfully, user_notes}'

# Test 3: UPDATE blocked
echo ""
echo "Test 3: UPDATE operation (should block)"
curl -s -X POST http://localhost:8000/api/feedback/ \
  -H "Content-Type": application/json" \
  -d '{"query_id": 3, "feedback_type": "sql_correction", "corrected_sql": "UPDATE products SET price = 0", "user_confidence": 0.95}' \
  | jq '{applied_successfully, user_notes}'

# Test 4: DROP blocked
echo ""
echo "Test 4: DROP TABLE operation (should block)"
curl -s -X POST http://localhost:8000/api/feedback/ \
  -H "Content-Type: application/json" \
  -d '{"query_id": 4, "feedback_type": "sql_correction", "corrected_sql": "DROP TABLE sessions", "user_confidence": 1.0}' \
  | jq '{applied_successfully, user_notes}'

echo ""
echo "=========================================="
echo "✅ Security tests complete!"
echo "Check logs for detailed validation output"
```

## Expected Security Behavior Summary

| Test | Operation | Confidence | Should Auto-Apply? | Reason |
|------|-----------|------------|-------------------|---------|
| 1 | SELECT (fix table name) | 95% | ✅ YES | Safe operation, high confidence |
| 2 | DELETE FROM | 100% | ❌ NO | Destructive operation |
| 3 | UPDATE SET | 95% | ❌ NO | Destructive operation |
| 4 | DROP TABLE | 100% | ❌ NO | Destructive operation |
| 5 | DELETE (operation change) | 90% | ❌ NO | Changed operation type |
| 6 | SELECT | 60% | ❌ NO | Low confidence (<70%) |
| 7 | SELECT (medium conf) | 75% | ⚠️ DEFERRED | Queued for batch |
| 8 | SELECT (refinement) | 95% | ✅ MAYBE | Moderate mode allows |

## Monitoring & Debugging

```bash
# Watch logs in real-time
tail -f logs/app.log | grep -i "validation\|blocked\|auto-apply"

# Check learned corrections
curl http://localhost:8000/learned-corrections/ | jq '.[] | {id, corrected_sql, source}'

# View validation details in feedback
curl http://localhost:8000/api/feedback/recent | jq '.[] | {
  id,
  corrected_sql,
  applied_successfully,
  user_notes
}'
```

## Troubleshooting

**Auto-learning not working:**
1. Check settings: `curl http://localhost:8000/api/settings/`
2. Ensure `auto_learning_enabled: true`
3. Verify `test_before_learning: true`
4. Check logs for validation failures

**All feedback being rejected:**
1. Verify validation_mode (try "moderate" or "lenient")
2. Check if corrections are destructive operations
3. Ensure corrected SQL actually works
4. Verify database connection is active

**No validation logs:**
1. Check `test_before_learning` is enabled
2. Verify confidence ≥90%
3. Ensure feedback has `corrected_sql`

## Production Checklist

Before enabling auto-learning in production:

- [ ] `validation_mode` = **"strict"**
- [ ] `test_before_learning` = **true**
- [ ] `allow_destructive_auto_learn` = **false**
- [ ] Monitoring/alerting configured
- [ ] Team trained on security policy
- [ ] Rollback procedure documented
- [ ] Regular audit reviews scheduled

---

**Security First!** The system is designed to be paranoid about what it auto-learns. Better to reject 100 legitimate corrections than auto-apply 1 destructive mistake.
