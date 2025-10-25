# Security & Validation - Quick Start

## TL;DR

Database Guru's auto-learning system now has **enterprise-grade security**:

✅ **Safe Operations** → Auto-learned
❌ **Destructive Operations** → BLOCKED (even at 100% confidence)

## 30-Second Setup

```bash
# 1. Initialize system settings (fresh install or first-time setup)
python init_system_settings.py

# 2. Enable auto-learning with strict validation
curl -X PUT http://localhost:8000/api/settings/ \
  -H "Content-Type: application/json" \
  -d '{
    "auto_learning_enabled": true,
    "validation_mode": "strict",
    "test_before_learning": true
  }'

# 3. Done! Submit feedback and watch it auto-validate
```

## What Gets Auto-Learned? ✅

```sql
-- Safe SELECT operations
SELECT * FROM users                          ✅ Auto-learned
SELECT COUNT(*) FROM products                ✅ Auto-learned
SELECT name, email FROM customers            ✅ Auto-learned
```

## What Gets BLOCKED? ❌

```sql
-- Destructive operations (NEVER auto-learned)
DELETE FROM users WHERE id = 1               ❌ BLOCKED
UPDATE products SET price = 0                ❌ BLOCKED
DROP TABLE logs                              ❌ BLOCKED
ALTER TABLE users ADD COLUMN                 ❌ BLOCKED
TRUNCATE TABLE sessions                      ❌ BLOCKED
```

**Even with:**
- ✅ 100% user confidence
- ✅ Perfect WHERE clauses
- ✅ High validation scores

## How Validation Works

```
User submits feedback (confidence: 95%)
         ↓
1. Confidence Check: ≥90%? → YES
         ↓
2. Execute Corrected SQL: Success? → YES
         ↓
3. Execute Original SQL: Fails? → YES (strict mode)
         ↓
4. Check Patterns: Destructive ops? → NO
         ↓
5. Operation Type: Changed? → NO
         ↓
✨ AUTO-APPLIED!
```

If **ANY** check fails → Rejected & saved for manual review

## Validation Modes

| Mode | Best For | Safety | Auto-Apply Rate |
|------|----------|--------|----------------|
| **Strict** | Production | 🛡️🛡️🛡️ Maximum | Low (safest) |
| **Moderate** | Staging | 🛡️🛡️ Balanced | Medium |
| **Lenient** | Dev/Test | 🛡️ Minimal | High (risky) |

**Recommendation:** Always use **Strict** in production

## Quick Tests

**Test safe correction:**
```bash
curl -X POST http://localhost:8000/api/feedback/ \
  -H "Content-Type: application/json" \
  -d '{
    "query_id": 1,
    "feedback_type": "sql_correction",
    "corrected_sql": "SELECT * FROM users",
    "user_confidence": 0.95
  }'

# Expected: applied_successfully = true
```

**Test blocked DELETE:**
```bash
curl -X POST http://localhost:8000/api/feedback/ \
  -H "Content-Type: application/json" \
  -d '{
    "query_id": 2,
    "feedback_type": "sql_correction",
    "corrected_sql": "DELETE FROM users WHERE id = 1",
    "user_confidence": 1.0
  }'

# Expected: applied_successfully = false
# user_notes: "[AUTO-APPLY REJECTED] BLOCKED..."
```

## Check Status

```bash
# Current settings
curl http://localhost:8000/api/settings/

# Feedback stats
curl http://localhost:8000/api/feedback/stats

# Recent feedback
curl http://localhost:8000/api/feedback/recent | \
  jq '.[] | {corrected_sql, applied_successfully}'
```

## Security Checklist

Production-ready when:

- [ ] `auto_learning_enabled` = true
- [ ] `validation_mode` = **"strict"**
- [ ] `test_before_learning` = true
- [ ] `allow_destructive_auto_learn` = **false**
- [ ] `require_admin_approval` = true
- [ ] Monitoring enabled
- [ ] Team trained

## Complete Documentation

- **[VALIDATION_SYSTEM.md](VALIDATION_SYSTEM.md)** - Technical deep dive
- **[SECURITY_POLICY.md](SECURITY_POLICY.md)** - Enterprise security policy
- **[SECURITY_ENHANCEMENTS_SUMMARY.md](SECURITY_ENHANCEMENTS_SUMMARY.md)** - What changed
- **[AUTO_LEARNING_GUIDE.md](AUTO_LEARNING_GUIDE.md)** - User guide
- **[tests/SECURITY_TEST_GUIDE.md](tests/SECURITY_TEST_GUIDE.md)** - Testing guide

## Default Settings (SAFE)

```json
{
  "auto_learning_enabled": false,
  "validation_mode": "strict",
  "test_before_learning": true,
  "allow_destructive_auto_learn": false,
  "require_admin_approval": true
}
```

## Emergency: Disable Auto-Learning

```bash
curl -X PUT http://localhost:8000/api/settings/ \
  -d '{"auto_learning_enabled": false}'
```

## Key Principle

> **Better to reject 100 legitimate corrections
> than auto-apply 1 destructive mistake.**

The system is **paranoid by design** - and that's a good thing! 🛡️
