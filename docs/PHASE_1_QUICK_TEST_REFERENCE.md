# Phase 1: Quick Test Reference 🚀

**Quick reference for rapid manual testing of Phase 1 improvements**

---

## 🏃‍♂️ Quick Setup (2 minutes)

```bash
# Terminal 1: Start backend
cd /Users/sam/database-guru
source venv/bin/activate
python -m uvicorn src.main:app --reload --port 8000

# Terminal 2: Enable auto-learning
cd /Users/sam/database-guru
source venv/bin/activate
sqlite3 database_guru.db "UPDATE system_settings SET auto_learning_enabled = 1, apply_mode = 'immediate';"
```

---

## ✅ Critical Test: Learned Corrections Working?

**The most important test - does the fixed async pipeline work?**

```bash
# 1. Submit high-confidence feedback
curl -X POST "http://localhost:8000/api/feedback/" \
  -H "Content-Type: application/json" \
  -d '{
    "query_id": 1,
    "feedback_type": "sql_correction",
    "corrected_sql": "SELECT * FROM products LIMIT 10",
    "correction_description": "Fixed typo",
    "user_confidence": 0.95
  }' | jq '.applied_successfully, .learned_correction_id'

# 2. Check database
sqlite3 database_guru.db "SELECT COUNT(*) FROM learned_corrections;"
```

**Expected**:
- API returns: `true` and a `learned_correction_id`
- Database returns: `1` (or more)
- Logs show: `✨ AUTO-APPLIED: High confidence feedback automatically learned!`

**If learned_corrections count is 0, Phase 1 FAILED!** ❌

---

## 🎯 Test All Tiers (5 minutes)

### Tier 1 (≥90% - STRICT)
```bash
curl -X POST "http://localhost:8000/api/feedback/" \
  -H "Content-Type: application/json" \
  -d '{"query_id": 1, "feedback_type": "sql_correction", "corrected_sql": "SELECT * FROM users", "correction_description": "Test Tier 1", "user_confidence": 0.95}' | jq '.applied_successfully'
```
**Expected**: `true`, Log: `🚀 TIER 1`

### Tier 2 (≥80% - MODERATE)
```bash
curl -X POST "http://localhost:8000/api/feedback/" \
  -H "Content-Type: application/json" \
  -d '{"query_id": 1, "feedback_type": "sql_correction", "corrected_sql": "SELECT id FROM users", "correction_description": "Test Tier 2", "user_confidence": 0.85}' | jq '.applied_successfully'
```
**Expected**: `true`, Log: `⚡ TIER 2`

### Tier 3 (≥70% - QUEUE)
```bash
# First, enable deferred mode
sqlite3 database_guru.db "UPDATE system_settings SET apply_mode = 'deferred';"

curl -X POST "http://localhost:8000/api/feedback/" \
  -H "Content-Type: application/json" \
  -d '{"query_id": 1, "feedback_type": "sql_correction", "corrected_sql": "SELECT name FROM users", "correction_description": "Test Tier 3", "user_confidence": 0.75}' | jq '.applied_successfully'
```
**Expected**: `false`, Log: `📋 TIER 3`

### Manual (<70%)
```bash
curl -X POST "http://localhost:8000/api/feedback/" \
  -H "Content-Type: application/json" \
  -d '{"query_id": 1, "feedback_type": "sql_correction", "corrected_sql": "SELECT * FROM users", "correction_description": "Low confidence", "user_confidence": 0.65}' | jq '.applied_successfully'
```
**Expected**: `false`, Log: `👁️ Low confidence`

---

## 🛡️ Security Test: Destructive Operations Blocked?

```bash
curl -X POST "http://localhost:8000/api/feedback/" \
  -H "Content-Type: application/json" \
  -d '{"query_id": 1, "feedback_type": "sql_correction", "corrected_sql": "DELETE FROM users WHERE id = 1", "correction_description": "Malicious", "user_confidence": 0.99}' | jq '.applied_successfully, .user_notes'
```

**Expected**:
- `applied_successfully`: `false`
- `user_notes`: Contains `"BLOCKED: Added destructive operation 'delete from'"`
- Log: `⚠️ Auto-apply REJECTED by validator`

**If this auto-applies, SECURITY FAILURE!** 🚨

---

## 🧹 Cleanup Test

```bash
# Dry-run (safe)
python scripts/cleanup_test_feedback.py <<< "no"
```

**Expected**: Shows ~652 test entries to delete, makes NO changes.

---

## 📊 Quick Database Checks

```bash
# Count learned corrections (should be > 0)
sqlite3 database_guru.db "SELECT COUNT(*) FROM learned_corrections;"

# View learned corrections
sqlite3 database_guru.db "SELECT id, error_type, times_applied, confidence_score FROM learned_corrections;"

# Auto-applied count
sqlite3 database_guru.db "SELECT COUNT(*) FROM user_feedback WHERE applied_successfully = 1;"

# Tier distribution (last hour)
sqlite3 database_guru.db "
SELECT
  CASE
    WHEN user_confidence >= 0.90 THEN 'Tier 1 (≥90%)'
    WHEN user_confidence >= 0.80 THEN 'Tier 2 (≥80%)'
    WHEN user_confidence >= 0.70 THEN 'Tier 3 (≥70%)'
    ELSE 'Manual (<70%)'
  END as tier,
  COUNT(*) as count,
  SUM(CASE WHEN applied_successfully = 1 THEN 1 ELSE 0 END) as applied
FROM user_feedback
WHERE created_at > datetime('now', '-1 hour')
GROUP BY tier;
"
```

---

## 🔍 Quick Log Checks

```bash
# Count successful auto-applies
grep "✨ AUTO-APPLIED" backend.log | wc -l

# Count tier usage
grep "🚀 TIER 1" backend.log | wc -l
grep "⚡ TIER 2" backend.log | wc -l
grep "📋 TIER 3" backend.log | wc -l

# Check for errors
grep "❌ CRITICAL" backend.log | tail -5
```

---

## ✅ Pass/Fail Checklist

Quick checklist for sign-off:

- [ ] **Learned corrections created** (count > 0)
- [ ] **Tier 1 auto-applies** (≥90%)
- [ ] **Tier 2 auto-applies** (≥80%)
- [ ] **Tier 3 queues** (≥70%)
- [ ] **Manual review required** (<70%)
- [ ] **Destructive operations blocked**
- [ ] **Cleanup script works**
- [ ] **Logs show correct emojis** (🚀⚡📋👁️)

**If ALL checked, Phase 1 is READY FOR PRODUCTION!** ✅

---

## 🔧 Quick Troubleshooting

**No learned corrections?**
```bash
# Enable auto-learning
sqlite3 database_guru.db "UPDATE system_settings SET auto_learning_enabled = 1;"
```

**All feedback rejected?**
```bash
# Check validation mode
sqlite3 database_guru.db "SELECT validation_mode FROM system_settings;"
# Should be 'strict' for Tier 1, system uses 'moderate' for Tier 2
```

**Tier 2 not working?**
```bash
# Ensure immediate mode for Tier 1 & 2
sqlite3 database_guru.db "UPDATE system_settings SET apply_mode = 'immediate';"
```

---

## 🚀 Production Deployment Command

After all tests pass:

```bash
# 1. Disable auto-learning until you're ready
sqlite3 database_guru.db "UPDATE system_settings SET auto_learning_enabled = 0;"

# 2. Run cleanup (if desired)
python scripts/cleanup_test_feedback.py  # Type 'yes' when prompted

# 3. Restart backend
pkill -f uvicorn
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000

# 4. Enable auto-learning in production
sqlite3 database_guru.db "UPDATE system_settings SET auto_learning_enabled = 1;"
```

---

**Time to complete**: ~10 minutes
**Last updated**: November 9, 2025
**Status**: Ready for use
