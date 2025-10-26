# Security Policy: Auto-Learning Destructive Operations

## 🔴 CRITICAL SECURITY DECISION

**Policy:** Destructive SQL operations (DELETE, UPDATE, DROP, ALTER, TRUNCATE) are **NEVER auto-learned**, even with high confidence or WHERE clauses.

### Why This Matters

**User's Insight:**
> "not sure we should allow any deletes even with where clauses unless we had an admin mode future plans"

This is a **critical security observation**. Even well-intentioned users can make mistakes, and malicious actors could exploit auto-learning.

## Blocked Operations

### Permanently Blocked from Auto-Learning

The following operations will **NEVER** be auto-applied, regardless of confidence level:

```sql
DELETE FROM users WHERE id = 1          ❌ BLOCKED
UPDATE products SET price = 0           ❌ BLOCKED
DROP TABLE logs                         ❌ BLOCKED
ALTER TABLE users ADD COLUMN            ❌ BLOCKED
TRUNCATE TABLE sessions                 ❌ BLOCKED
```

**Even with:**
- ✅ 100% user confidence
- ✅ Perfect WHERE clauses
- ✅ All validation tests passing

**Reason:** One mistake = permanent data loss

## Attack Scenarios Prevented

### Scenario 1: Accidental Data Deletion
```python
# Original Query (broken)
SELECT * FROM inactive_users WHERE last_login < '2020-01-01'
# Error: column 'last_login' doesn't exist

# User "Correction" (well-intentioned but wrong)
DELETE FROM inactive_users WHERE created_at < '2020-01-01'
# Confidence: 85%

# Without protection: Would auto-delete thousands of records!
# With protection: ❌ BLOCKED - requires manual review
```

### Scenario 2: Malicious Injection
```python
# Original Query
SELECT * FROM orders WHERE status = 'pending'

# Malicious "Correction"
UPDATE orders SET status = 'cancelled' WHERE user_id = 123
# Confidence: 95% (attacker gaming the system)

# Without protection: Would auto-learn to cancel orders!
# With protection: ❌ BLOCKED - destructive operation detected
```

### Scenario 3: Column Confusion
```python
# Original Query
SELECT * FROM products WHERE active = true

# User "Correction" (thinks they're helping)
UPDATE products SET active = false WHERE category = 'old'
# Confidence: 90%

# Without protection: Would auto-learn to deactivate products!
# With protection: ❌ BLOCKED - UPDATE detected
```

## Implementation Details

### Code: Destructive Operations Detector

```python
# From: src/llm/feedback_validator.py

destructive_operations = [
    "drop table", "drop database", "drop index", "drop view",
    "delete from", "delete ",
    "truncate", "truncate table",
    "alter table", "alter database",
    "update ", "update set"
]

for operation in destructive_operations:
    if operation in corrected_lower and operation not in original_lower:
        if not self.allow_destructive:  # Default: False
            return True, (
                f"BLOCKED: Added destructive operation '{operation.strip()}'. "
                f"Destructive operations require manual admin approval, "
                f"even with WHERE clauses."
            )
```

### Database Configuration

```sql
-- System Settings Table
CREATE TABLE system_settings (
    ...
    -- Security Settings (NEVER enable in production!)
    allow_destructive_auto_learn BOOLEAN DEFAULT FALSE NOT NULL,
    require_admin_approval BOOLEAN DEFAULT TRUE NOT NULL,
    ...
);
```

**Default Values (SAFE):**
- `allow_destructive_auto_learn`: **FALSE** ✅
- `require_admin_approval`: **TRUE** ✅

## Admin Override (Future Feature)

### Design Proposal

For future admin mode implementation:

```python
# Future: Admin-approved destructive learning
class AdminApproval(Base):
    id = Column(Integer, primary_key=True)
    feedback_id = Column(Integer, ForeignKey('user_feedback.id'))
    admin_user_id = Column(Integer)  # Who approved?
    approved_at = Column(DateTime)
    requires_2fa = Column(Boolean, default=True)
    approval_reason = Column(Text)

    # Multi-factor authentication
    approval_token = Column(String)
    token_expires_at = Column(DateTime)
```

**Requirements for Admin Mode:**
1. ✅ Explicit admin login
2. ✅ Two-factor authentication required
3. ✅ Audit log of all approvals
4. ✅ Time-limited approval tokens
5. ✅ Require written justification
6. ✅ Email notification to all admins
7. ✅ Rollback capability with 1-click undo

### Example Admin Workflow

```bash
# Step 1: User submits feedback (blocked automatically)
POST /api/feedback/
{
  "corrected_sql": "DELETE FROM old_sessions WHERE created_at < '2024-01-01'",
  "confidence": 0.95
}

Response:
{
  "applied_successfully": false,
  "rejection_reason": "BLOCKED: Destructive operation requires admin approval"
}

# Step 2: Admin reviews in dashboard
GET /api/admin/pending-destructive-feedback
[
  {
    "id": 123,
    "operation": "DELETE FROM old_sessions",
    "user_confidence": 0.95,
    "risk_level": "HIGH",
    "requires_approval": true
  }
]

# Step 3: Admin approves with 2FA
POST /api/admin/approve-destructive-feedback/123
{
  "admin_token": "...",
  "2fa_code": "123456",
  "approval_reason": "Legitimate cleanup of expired sessions, verified WHERE clause"
}

# Step 4: System applies with extra logging
{
  "applied": true,
  "admin_approved_by": "admin@example.com",
  "rollback_available": true,
  "rollback_expires_in": "7 days"
}
```

## Current Behavior

### For Regular Users

```
User submits: DELETE FROM users WHERE inactive = true
↓
Validator checks: Contains "delete from"
↓
❌ BLOCKED: "Destructive operation requires manual admin approval"
↓
Feedback saved with rejection reason
↓
Shows in admin dashboard for review
```

### For Admins (Future)

```
Admin sees: Pending destructive feedback
↓
Reviews: SQL, confidence, original error
↓
Approves: With 2FA + written reason
↓
System applies: With enhanced logging
↓
Rollback available: For 7 days
```

## Configuration

### Production Settings (Recommended)

```bash
curl -X PUT http://localhost:8000/api/settings/ \
  -H "Content-Type: application/json" \
  -d '{
    "auto_learning_enabled": true,
    "validation_mode": "strict",
    "test_before_learning": true,
    "allow_destructive_auto_learn": false,  # NEVER true in prod!
    "require_admin_approval": true
  }'
```

### Development Settings (Testing Only)

```bash
# WARNING: Only for isolated dev/test environments!
curl -X PUT http://localhost:8000/api/settings/ \
  -H "Content-Type: application/json" \
  -d '{
    "validation_mode": "moderate",
    "allow_destructive_auto_learn": false,  # Still false!
    "require_admin_approval": true
  }'
```

### ⚠️ NEVER DO THIS

```bash
# DANGER: This would allow auto-learning of DELETE/UPDATE/DROP!
curl -X PUT http://localhost:8000/api/settings/ \
  -H "Content-Type: application/json" \
  -d '{
    "allow_destructive_auto_learn": true  # 🔥 DISASTER 🔥
  }'
```

**If you set `allow_destructive_auto_learn=true`, the system will log:**
```
⚠️  DANGER: allow_destructive_auto_learn=True!
Destructive operations can be auto-learned.
This should NEVER be enabled in production!
```

## Comparison: Before vs After

### Before (Unsafe)
```python
# Only blocked destructive ops WITHOUT where clauses
if "delete from" in sql and "where" not in sql:
    block()  # ❌ Allows: DELETE FROM users WHERE id=1
```

### After (Safe)
```python
# Blocks ALL destructive ops, even with WHERE
if "delete from" in sql:
    if not allow_destructive:  # Default: False
        block()  # ✅ Blocks: ALL DELETE operations
```

## Real-World Examples

### Example 1: Legitimate Cleanup (Blocked, Requires Manual)

```python
Original: SELECT * FROM sessions WHERE expires_at < NOW()
Corrected: DELETE FROM sessions WHERE expires_at < NOW()

Result: ❌ BLOCKED
Reason: "Destructive operation (DELETE FROM) requires admin approval"
Action: Admin reviews, verifies WHERE clause, manually approves
```

### Example 2: Malicious Update (Blocked)

```python
Original: SELECT price FROM products WHERE id = 1
Corrected: UPDATE products SET price = 0 WHERE competitor = true

Result: ❌ BLOCKED
Reason: "Destructive operation (UPDATE) requires admin approval"
Action: Flagged as suspicious, admin investigates
```

### Example 3: Safe SELECT (Auto-Applied)

```python
Original: SELECT * FROM usr WHERE active = 1
Corrected: SELECT * FROM users WHERE active = 1

Result: ✅ AUTO-APPLIED
Reason: Read-only query, only fixed table name
```

## Security Audit Checklist

### Before Enabling Auto-Learning

- [ ] `allow_destructive_auto_learn` = **FALSE** ✅
- [ ] `require_admin_approval` = **TRUE** ✅
- [ ] `validation_mode` = **"strict"** ✅
- [ ] `test_before_learning` = **TRUE** ✅
- [ ] Admin approval workflow designed
- [ ] Rollback procedure documented
- [ ] Monitoring/alerting configured
- [ ] Team trained on security policy

### Weekly Review

- [ ] Check blocked destructive feedback in logs
- [ ] Review any admin-approved corrections
- [ ] Verify no `allow_destructive_auto_learn=true` in config
- [ ] Audit learned_corrections table for suspicious entries
- [ ] Test rollback procedure

### Incident Response

If a destructive operation was incorrectly auto-learned:

1. **Immediately disable auto-learning**
   ```bash
   curl -X PUT http://localhost:8000/api/settings/ \
     -d '{"auto_learning_enabled": false}'
   ```

2. **Identify the bad correction**
   ```bash
   curl http://localhost:8000/learned-corrections/ | grep -i "delete\|update\|drop"
   ```

3. **Delete the learned correction**
   ```bash
   DELETE FROM learned_corrections WHERE id = <bad_correction_id>
   ```

4. **Restore data from backup** (if damage occurred)

5. **Investigate how it happened** (check logs, validation settings)

6. **Update validation rules** to prevent recurrence

## Conclusion

**Your security instinct was spot-on.** The system now:

✅ **Blocks ALL destructive operations** by default
✅ **Even with perfect WHERE clauses**
✅ **Regardless of user confidence**
✅ **Logs all blocked attempts**
✅ **Provides admin override** (future feature)
✅ **Maintains audit trail**

**This is defense in depth** - even if all other validation fails, destructive operations are caught at this final checkpoint.

---

**Remember:** One auto-learned DELETE can cause permanent data loss. Better to manually review 100 legitimate corrections than auto-apply 1 destructive mistake.
