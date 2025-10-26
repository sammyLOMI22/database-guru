# Smart Auto-Learning System - Complete Guide

## Overview

Database Guru features **Smart Auto-Learning with Enterprise Security**, an intelligent system that automatically applies high-confidence user feedback to improve future query generation - with production-grade validation to prevent bad corrections.

## 🛡️ Security First

**IMPORTANT:** This system now includes comprehensive validation and security controls:
- ✅ **Validates corrections** before auto-applying (not just "does it run?")
- ✅ **Blocks ALL destructive operations** (DELETE, UPDATE, DROP, ALTER, TRUNCATE)
- ✅ **Compares original vs corrected** to ensure actual improvement
- ✅ **Pattern detection** blocks suspicious changes
- ✅ **Audit trail** logs all decisions

See **[VALIDATION_SYSTEM.md](VALIDATION_SYSTEM.md)** and **[SECURITY_POLICY.md](SECURITY_POLICY.md)** for details.

## How It Works

### Confidence-Based Routing

When a user submits feedback, the system routes it based on confidence level:

```
┌─────────────────────────────────────────────────────┐
│           User Submits Feedback                     │
│        (with confidence: 0.0 - 1.0)                 │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
         ┌───────────────┐
         │ Auto-Learning │
         │   Enabled?    │
         └───────┬───────┘
                 │
         ┌───────┴───────┐
         │               │
        YES             NO
         │               │
         ▼               ▼
┌────────────────┐   Save for
│ Check          │   manual review
│ Confidence     │
└────────┬───────┘
         │
    ┌────┴─────┬──────────┬────────────┐
    │          │          │            │
High (≥90%)  Med (70-89%) Low (<70%)   │
    │          │          │            │
    ▼          ▼          ▼            │
┌─────────┐ ┌─────────┐ ┌──────────┐  │
│Auto-    │ │Queue for│ │ Manual   │  │
│Apply    │ │Batch    │ │ Review   │  │
│Immediate│ │(deferred│ │ Required │  │
│         │ │  mode)  │ │          │  │
└─────────┘ └─────────┘ └──────────┘  │
    │          │          │            │
    └──────────┴──────────┴────────────┘
                 │
                 ▼
          Feedback Saved
```

### Auto-Learning Rules

| Confidence | Behavior | Notes |
|-----------|----------|-------|
| **≥90% (High)** | Auto-apply immediately | Correction tested (optional) then added to learning system |
| **70-89% (Medium)** | Queue for batch processing* | Saved for admin review, can be applied in bulk |
| **<70% (Low)** | Manual review required | Saved but requires explicit admin approval |

\* Only in "deferred" apply mode

## Configuration

### Settings Panel

Access the Settings panel via the **⚙️ Settings** tab in the UI.

### Available Settings

#### 1. Auto-Learning Master Toggle
- **Enable Auto-Learning**: ON/OFF
- When OFF, all feedback requires manual review
- When ON, high-confidence feedback is auto-applied

#### 2. Confidence Threshold
- **Range**: 50% - 100%
- **Default**: 80%
- **Purpose**: Minimum confidence for auto-application
- Currently fixed at 90% for high confidence, but threshold is stored for future features

#### 3. Apply Mode
- **Immediate**: Only high-confidence (≥90%) auto-applied, medium requires manual review
- **Deferred**: Medium-confidence (70-89%) queued for batch processing
- **Default**: Immediate

#### 4. Test Before Learning
- **ON** (Recommended): Execute corrected SQL to verify it works before learning
- **OFF**: Skip testing, trust user correction blindly
- **Default**: ON

#### 5. Audit Log
- **Enable Audit Log**: Track all auto-applied feedback
- **Retention Days**: How long to keep logs (1-365 days, default: 90)

## API Endpoints

### Get Settings
```bash
GET /api/settings/
```

**Response:**
```json
{
  "id": 1,
  "auto_learning_enabled": false,
  "confidence_threshold": 0.80,
  "apply_mode": "immediate",
  "test_before_learning": true,
  "enable_audit_log": true,
  "max_audit_log_days": 90,
  "created_at": "2025-10-25T19:19:40.114266",
  "updated_at": "2025-10-25T19:19:40.114268"
}
```

### Update Settings
```bash
PUT /api/settings/
Content-Type: application/json

{
  "auto_learning_enabled": true,
  "confidence_threshold": 0.85,
  "apply_mode": "deferred"
}
```

All fields are optional (partial update).

### Reset to Defaults
```bash
POST /api/settings/reset
```

Resets all settings to their default values.

## Usage Examples

### Example 1: Enable Auto-Learning

**Via UI:**
1. Go to **⚙️ Settings** tab
2. Toggle **Enable Auto-Learning** to ON
3. Adjust **Confidence Threshold** if desired (optional)
4. Click **Save Changes**

**Via API:**
```bash
curl -X PUT http://localhost:8000/api/settings/ \
  -H "Content-Type: application/json" \
  -d '{"auto_learning_enabled": true}'
```

### Example 2: Submit High-Confidence Feedback (Auto-Applied)

**Scenario:** User corrects a query with 95% confidence

**Request:**
```bash
curl -X POST http://localhost:8000/api/feedback/ \
  -H "Content-Type: application/json" \
  -d '{
    "query_id": 123,
    "feedback_type": "sql_correction",
    "corrected_sql": "SELECT * FROM users WHERE active = true",
    "correction_description": "Should filter for active users only",
    "user_confidence": 0.95
  }'
```

**Backend Behavior:**
1. ✅ Feedback saved with confidence 95%
2. 🔍 Auto-learning enabled? → YES
3. ⚡ Confidence ≥90%? → YES
4. 🧪 Test corrected SQL (if enabled)
5. ✨ **AUTO-APPLIED** - Adds to learning system immediately
6. 📝 Returns feedback with `applied_successfully: true`

**Logs:**
```
User feedback submitted: id=5, type=sql_correction, query_id=123, confidence=0.95
Auto-learning enabled: threshold=0.8, mode=immediate, test=True
🚀 High confidence feedback (≥90%), attempting auto-apply... (feedback_id=5)
Testing user correction before auto-learning...
✨ AUTO-APPLIED: High confidence feedback automatically learned! feedback_id=5, learned_correction_id=12
```

### Example 3: Submit Medium-Confidence Feedback (Queued)

**Scenario:** User corrects with 75% confidence, deferred mode enabled

**Request:**
```bash
curl -X PUT http://localhost:8000/api/settings/ \
  -H "Content-Type: application/json" \
  -d '{"apply_mode": "deferred"}'

curl -X POST http://localhost:8000/api/feedback/ \
  -H "Content-Type: application/json" \
  -d '{
    "query_id": 124,
    "feedback_type": "column_name",
    "corrected_sql": "SELECT user_id FROM orders",
    "correction_description": "Column is user_id not customer_id",
    "user_confidence": 0.75
  }'
```

**Backend Behavior:**
1. ✅ Feedback saved with confidence 75%
2. 🔍 Auto-learning enabled? → YES
3. ⚡ Confidence ≥90%? → NO
4. 📋 Confidence ≥70% AND mode=deferred? → YES
5. **QUEUED** for batch processing
6. 📝 Returns feedback with `applied_successfully: false` (pending review)

**Logs:**
```
User feedback submitted: id=6, type=column_name, query_id=124, confidence=0.75
📋 Medium confidence feedback (70-89%), queued for batch processing (feedback_id=6)
```

### Example 4: Submit Low-Confidence Feedback (Manual Review)

**Request:**
```bash
curl -X POST http://localhost:8000/api/feedback/ \
  -H "Content-Type: application/json" \
  -d '{
    "query_id": 125,
    "feedback_type": "result_issue",
    "correction_description": "Results seem incomplete",
    "user_confidence": 0.60
  }'
```

**Backend Behavior:**
1. ✅ Feedback saved with confidence 60%
2. 🔍 Auto-learning enabled? → YES
3. ⚡ Confidence <70%? → YES
4. 👁️ **MANUAL REVIEW** required
5. 📝 Returns feedback with `applied_successfully: false`

**Logs:**
```
User feedback submitted: id=7, type=result_issue, query_id=125, confidence=0.6
👁️ Low confidence feedback (<70%), manual review required (feedback_id=7)
```

## Testing Auto-Learning

### Test Script

```bash
# 1. Enable auto-learning
curl -X PUT http://localhost:8000/api/settings/ \
  -H "Content-Type: application/json" \
  -d '{"auto_learning_enabled": true}'

# 2. Submit a query (will likely fail first time)
curl -X POST http://localhost:8000/api/query/ \
  -H "Content-Type: application/json" \
  -d '{"question": "Show all users from the user table"}'

# Note the query_id from response

# 3. Submit high-confidence feedback
curl -X POST http://localhost:8000/api/feedback/ \
  -H "Content-Type: application/json" \
  -d '{
    "query_id": <QUERY_ID>,
    "feedback_type": "sql_correction",
    "corrected_sql": "SELECT * FROM users",
    "correction_description": "Table is users not user",
    "user_confidence": 0.95
  }'

# 4. Check feedback was auto-applied
curl http://localhost:8000/api/feedback/recent

# 5. Try the same query again - should auto-correct now!
curl -X POST http://localhost:8000/api/query/ \
  -H "Content-Type: application/json" \
  -d '{"question": "Show all users from the user table"}'
```

### Expected Results

1. First query fails with "table user does not exist"
2. Feedback is auto-applied (logs show "✨ AUTO-APPLIED")
3. Feedback response has `applied_successfully: true`
4. Second identical query auto-corrects to use "users" table
5. Query succeeds without user intervention

## Monitoring Auto-Learning

### View Auto-Applied Feedback

```bash
# Get recent feedback
curl http://localhost:8000/api/feedback/recent

# Get feedback stats
curl http://localhost:8000/api/feedback/stats
```

**Response:**
```json
{
  "total_feedback": 15,
  "applied_to_learning": 12,
  "pending": 3,
  "by_type": {
    "sql_correction": 10,
    "column_name": 3,
    "table_name": 2
  }
}
```

### View Learned Corrections

```bash
curl http://localhost:8000/learned-corrections/
```

## Safety Features

### 1. Test Before Learning (Recommended: ON)
- Executes corrected SQL before adding to learning system
- Prevents learning from incorrect user feedback
- Fails gracefully if correction doesn't work

### 2. Confidence Threshold
- Only very high confidence (≥90%) auto-applied
- Medium/low confidence requires review
- User sets their own confidence per feedback

### 3. Audit Trail
- All auto-applied feedback logged
- Can review what was learned automatically
- Rollback possible (delete learned_correction)

### 4. Graceful Failure
- If auto-apply fails, feedback still saved
- Error logged but doesn't block user
- Can be manually reviewed and applied later

## Troubleshooting

### Auto-Learning Not Working

**Check:**
1. Is auto-learning enabled?
   ```bash
   curl http://localhost:8000/api/settings/
   ```
2. Is confidence ≥90%?
3. Does feedback have `corrected_sql`?
4. Check backend logs for errors

### Correction Failed Testing

**Logs will show:**
```
⚠️ Auto-apply skipped: Corrected SQL failed testing: <error>
```

**Solutions:**
- Review the corrected SQL
- Fix and resubmit feedback
- Or disable "test before learning" (not recommended)

### No Active Connection

**Logs will show:**
```
⚠️ Auto-apply skipped: No active connection for testing
```

**Solution:**
- Ensure a database connection is active
- Or disable "test before learning"

## Best Practices

### For Users
1. **Be confident**: Only use high confidence (≥90%) for corrections you're certain about
2. **Test first**: Verify your corrected SQL works before submitting
3. **Describe clearly**: Help future reviewers understand the correction
4. **Start conservative**: Use lower confidence if uncertain

### For Admins
1. **Start with auto-learning OFF**: Test manually first
2. **Enable gradually**: Turn on after observing feedback quality
3. **Keep testing ON**: Prevents learning bad corrections
4. **Review periodically**: Check auto-applied feedback in dashboard
5. **Monitor logs**: Watch for failed auto-applies

## Version History

- **v3.1** (2025-10-25): Smart Auto-Learning (Option 3) implemented
  - Confidence-based routing
  - Auto-apply for high-confidence feedback
  - Settings UI and API
  - Test before learning
  - Audit logging

---

**Database Guru is now a fully autonomous, self-improving SQL system!** 🚀
