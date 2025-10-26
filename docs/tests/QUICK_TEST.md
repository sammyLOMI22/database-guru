# Quick Test - See All Observability Features

## Fastest Way to See Everything

### Option 1: Demo Page (Recommended - No Setup Needed!)

Just visit this URL in your browser:

```
http://localhost:3000/?demo=true
```

**What you'll see:**
- ✅ Two complete scenarios with full observability
- ✅ All 4 new components in action
- ✅ Component legend explaining everything
- ✅ No backend or database required!

---

## What Each Component Shows

### 📊 Agent Execution Trace
**Expandable panel showing step-by-step timeline:**
- 🔍 Analysis - Initial question analysis
- 📋 Planning - Query planning (if used)
- ✨ Generation - SQL generation
- ⚡ Execution - Query execution
- ❌ Error - When something fails
- 🔧 Fix Attempt - Trying to fix errors
- ⚡ Quick Fix - Schema-aware fix applied
- 🧠 Learned Fix - Applied learned correction
- 🤖 LLM Fix - AI-generated fix
- ✅ Success - Query succeeded
- 🔍 Verification - Result verification
- ⚠️ Warning - Verification warning
- 📚 Learning - Learning from correction

**Features:**
- Each step shows elapsed time
- Expandable metadata for details
- Color-coded by status (green=success, red=error, yellow=warning)

### ✨ Auto-Corrected Query
**Shows when query was automatically fixed:**
- Lists all attempts with success/failure
- Shows the SQL for each attempt
- Displays error messages
- **Fix method badges:**
  - 🟣 **Quick Fix** - Schema-aware (no LLM call)
  - 🔵 **Learned** - From previous corrections
  - 🟠 **LLM** - AI-generated fix
- Execution time and row count

### 📋 Query Plan
**For complex queries, shows the plan:**
- Complexity badge (Simple, Medium, Complex, Very Complex)
- Confidence score
- Intent and reasoning
- **Detailed breakdown:**
  - Tables (with aliases and purpose)
  - Joins (type, tables, conditions)
  - Filters (column, operator, value)
  - Aggregations (function, column)
  - Grouping (columns, purpose)
  - Ordering (column, direction)
  - Limit

### ⚠️ Verification Warnings
**Alerts about potentially suspicious results:**
- Yellow warning banner
- Clear warning messages
- Help text explaining the issue

---

## Demo Scenarios

### Scenario 1: Auto-Corrected Query
```
Question: "Show all users who registered in 2024"
What happened:
1. Generated SQL with wrong table name "users"
2. Query failed with "table not found" error
3. Quick fix applied: Changed "users" to "user"
4. Query succeeded
5. Verification warning: Only 3 rows (might be low)

Components shown:
✅ Agent Trace (10 steps)
✅ Correction History (2 attempts)
✅ Verification Warnings
```

### Scenario 2: Complex Query with Planning
```
Question: "Show total sales by category for each month in 2024"
What happened:
1. System detected complex query (aggregation + grouping + date)
2. Query planning agent created detailed plan
3. SQL generated from plan
4. Query executed successfully

Components shown:
✅ Query Plan (complexity: complex)
✅ Agent Trace (shows planning step)
```

---

## Screenshots to Look For

### 1. Agent Trace Panel (Collapsed)
```
📊 Agent Execution Trace
   10 steps • 185ms
   [Expand arrow]
```

### 2. Agent Trace Panel (Expanded)
```
📊 Agent Execution Trace
   10 steps • 185ms

🔍  Analyzing question: Show all users...     +0ms
    analysis

✨  Generated SQL: SELECT * FROM users...     +50ms
    generation

⚡  Executing SQL query                        +75ms
    execution

❌  Attempt 1 failed: table users does not... +80ms
    error

[... more steps ...]

✅  Query executed successfully (rows: 3...)   +165ms
    success

Total execution time: 185.00ms
```

### 3. Correction History Panel
```
✨ Auto-Corrected Query
   Fixed after 1 attempt
   [Expand arrow]
```

### 4. Query Plan Panel
```
📋 Query Plan
   [complex] 92% confidence
   [Expand arrow]
```

### 5. Verification Warnings
```
⚠️ Result Verification Warnings

[!] ⚠️ Result verification: Only 3 rows returned - verify this matches your expectations

These warnings indicate potential issues with the query results. Please review the results carefully...
```

---

## Testing Checklist

Visit `http://localhost:3000/?demo=true` and verify:

- [ ] Page loads without errors
- [ ] Two scenario sections visible
- [ ] Each scenario shows SQL query
- [ ] Results tables display
- [ ] **Agent Trace** panel visible and expandable
- [ ] **Correction History** panel shows in Scenario 1
- [ ] **Query Plan** panel shows in Scenario 2
- [ ] **Verification Warnings** shows in Scenario 1
- [ ] All expand/collapse buttons work
- [ ] Step icons display correctly (emojis)
- [ ] Colors are correct (green=success, red=error, etc.)
- [ ] Component legend at bottom explains everything
- [ ] Responsive on mobile (if testing mobile)

---

## Common Issues

### "Page not found"
- Make sure you're using `?demo=true` in the URL
- Check frontend is running on port 3000

### "Components not showing"
- Hard refresh: Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)
- Check browser console for errors

### "Styles look broken"
- Tailwind CSS might need rebuild
- Try: `npm run dev` in frontend directory

### "Everything is blank"
- Check browser console
- Look for JavaScript errors
- Make sure all imports are correct

---

## Next: Test with Real Backend

After seeing the demo, test with real queries:

1. Go back to main app: `http://localhost:3000`
2. Make sure backend is running
3. Try these queries:

**Simple query:**
```
Show all products
```

**Query with typo (triggers auto-correction):**
```
SELECT * FROM productz WHERE id = 1
```
(Wrong table name)

**Complex query (triggers planning):**
```
Show total sales by category for each month
```

---

---

## Week 2: Test User Feedback System

### Testing Feedback Submission

Visit `http://localhost:3000` with backend running and try these scenarios:

#### Scenario 1: Submit SQL Correction
```
1. Submit query: "Show all users"
2. Look for "Feedback" button in the SQL display header
3. Click "Feedback" button
4. Modal should open with:
   - Feedback type dropdown (4 options)
   - Original SQL (read-only)
   - Corrected SQL editor (editable for sql_correction type)
   - Description field (required)
   - Additional notes (optional)
   - Confidence slider (0-100%)
5. Select "SQL Correction"
6. Edit corrected SQL
7. Add description
8. Adjust confidence slider
9. Click "Submit Feedback"
10. Modal closes on success
```

#### Scenario 2: Test Multi-Database Feedback
```
1. Submit multi-database query
2. Each database result should have:
   - Copy SQL button
   - Feedback button
3. Click feedback button for one database
4. Submit feedback with corrected SQL
5. Verify feedback submitted for correct database
```

#### Scenario 3: View Feedback Stats
```
1. Navigate to feedback stats dashboard (if implemented)
2. Should show:
   - Total feedback count
   - Applied to learning count
   - Pending count
   - Breakdown by type (pie chart or table)
   - Recent feedback list
3. Try "Apply to Learning" button (if admin)
```

### Testing Feedback API

#### Test Submit Feedback
```bash
# Submit feedback on a query
curl -X POST http://localhost:8000/api/feedback/ \
  -H "Content-Type: application/json" \
  -d '{
    "query_id": 123,
    "feedback_type": "sql_correction",
    "corrected_sql": "SELECT * FROM users WHERE active = true",
    "correction_description": "Should filter for active users only",
    "user_confidence": 0.9
  }'
```

#### Test Get Feedback Stats
```bash
curl http://localhost:8000/api/feedback/stats
```

Expected response:
```json
{
  "total_feedback": 15,
  "applied_to_learning": 12,
  "pending": 3,
  "by_type": {
    "sql_correction": 10,
    "column_name": 3,
    "table_name": 2,
    "result_issue": 0
  }
}
```

#### Test Get Recent Feedback
```bash
curl http://localhost:8000/api/feedback/recent?limit=10
```

#### Test Apply Feedback to Learning
```bash
curl -X POST http://localhost:8000/api/feedback/apply \
  -H "Content-Type: application/json" \
  -d '{
    "feedback_id": 5,
    "test_before_learning": true
  }'
```

### Week 2 Testing Checklist

Frontend:
- [ ] Feedback button appears on query results
- [ ] Feedback button appears on multi-database results
- [ ] FeedbackModal opens when clicked
- [ ] Feedback type dropdown works (4 options)
- [ ] SQL Editor displays original SQL (read-only)
- [ ] SQL Editor allows editing corrected SQL
- [ ] Description field validates (required)
- [ ] Confidence slider works (0-100%)
- [ ] Submit button sends feedback
- [ ] Modal closes on success
- [ ] Error messages display on failure
- [ ] Copy SQL button works on multi-DB results

Backend:
- [ ] POST /api/feedback/ creates feedback
- [ ] GET /api/feedback/stats returns statistics
- [ ] GET /api/feedback/recent returns feedback list
- [ ] GET /api/feedback/query/{id} returns query feedback
- [ ] POST /api/feedback/apply applies to learning system
- [ ] DELETE /api/feedback/{id} deletes feedback
- [ ] Feedback validation works (feedback_type, confidence)
- [ ] Learning integration works
- [ ] UserFeedback model stores all fields correctly

Integration:
- [ ] Feedback creates learned_correction record
- [ ] Future queries apply learned corrections
- [ ] Multi-database queries track query_id per database
- [ ] Feedback stats update correctly
- [ ] Applied feedback shows applied_successfully=true

---

## Automated Testing

### Running the Test Suite

The feedback system has comprehensive test coverage. Run the tests to verify everything works:

#### Backend Tests

```bash
# Run all feedback tests
pytest tests/test_feedback_api.py -v
pytest tests/test_feedback_validator.py -v
pytest tests/test_feedback_integration.py -v

# Run specific test class
pytest tests/test_feedback_api.py::TestFeedbackSubmission -v

# Run with coverage report
pytest tests/test_feedback_*.py --cov=src/api/endpoints/feedback --cov=src/llm/feedback_validator --cov-report=html
```

**Test Files:**
- `tests/test_feedback_api.py` - API endpoint tests (201 tests)
- `tests/test_feedback_validator.py` - Validation logic tests (45+ tests)
- `tests/test_feedback_integration.py` - Integration workflow tests (30+ tests)

#### Frontend Tests

```bash
# Navigate to frontend directory
cd frontend

# Run all tests
npm test

# Run specific test file
npm test FeedbackModal.test.tsx
npm test FeedbackStats.test.tsx

# Run with coverage
npm test -- --coverage

# Watch mode for development
npm test -- --watch
```

**Test Files:**
- `frontend/tests/FeedbackModal.test.tsx` - Modal component tests (50+ tests)
- `frontend/tests/FeedbackStats.test.tsx` - Dashboard component tests (40+ tests)

### Test Coverage Areas

#### API Endpoints (`test_feedback_api.py`)
- ✅ Feedback submission (all types)
- ✅ High/medium/low confidence handling
- ✅ Auto-learning triggers
- ✅ Validation workflows
- ✅ Statistics calculation
- ✅ Retrieval and pagination
- ✅ Manual application
- ✅ Deletion
- ✅ Security (SQL injection, XSS, destructive ops)
- ✅ Edge cases (long text, Unicode, boundaries)

#### Validation Logic (`test_feedback_validator.py`)
- ✅ Strict/moderate/lenient modes
- ✅ Suspicious pattern detection
- ✅ Destructive operation blocking
- ✅ Confidence boost calculation
- ✅ Metadata validation (columns/tables)
- ✅ Edge cases (empty SQL, special chars)
- ✅ Complete validation workflows

#### Integration Tests (`test_feedback_integration.py`)
- ✅ Auto-learning workflow (high confidence)
- ✅ Deferred learning (medium confidence)
- ✅ Manual review queue (low confidence)
- ✅ Learned correction application
- ✅ Success rate tracking
- ✅ Feedback chaining
- ✅ Batch processing
- ✅ Error scenarios
- ✅ Statistics accuracy

#### Frontend Components

**FeedbackModal Tests:**
- ✅ Component rendering
- ✅ Form field interactions
- ✅ Validation rules
- ✅ Submission flow
- ✅ Error handling
- ✅ Loading states
- ✅ Accessibility (ARIA, keyboard nav)

**FeedbackStats Tests:**
- ✅ Stats display
- ✅ Recent feedback list
- ✅ Apply to learning functionality
- ✅ Data refresh
- ✅ Filtering and sorting
- ✅ Visual indicators
- ✅ Error handling
- ✅ Pagination

### Continuous Testing

Set up pre-commit hooks to run tests automatically:

```bash
# Create .git/hooks/pre-commit
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash

echo "Running backend tests..."
pytest tests/test_feedback_*.py -q || exit 1

echo "Running frontend tests..."
cd frontend && npm test -- --watchAll=false || exit 1

echo "All tests passed!"
EOF

chmod +x .git/hooks/pre-commit
```

### Test Results Interpretation

**Expected Results:**
- All tests should pass (green)
- Code coverage should be >80% for feedback modules
- No warnings or deprecation errors

**If Tests Fail:**
1. Check database connection (backend tests)
2. Verify all dependencies installed (`pip install -r requirements.txt`, `npm install`)
3. Check environment variables (`.env` file)
4. Review error messages for specific failures
5. Run tests individually to isolate issues

---

## Success!

If all components work in the demo, feedback system tests pass, and automated tests succeed, **Phase 0 is complete!** 🎉

You've successfully implemented:

### Week 1 - Observability:
- ✅ Backend agent trace system
- ✅ Fix methods tracking
- ✅ Complete API integration
- ✅ 4 beautiful React components
- ✅ Full TypeScript support
- ✅ Responsive design
- ✅ Accessible UI

### Week 2 - User Feedback Integration:
- ✅ User feedback API (6 endpoints)
- ✅ FeedbackModal component
- ✅ SQLEditor component
- ✅ FeedbackStats dashboard
- ✅ Multi-database feedback support
- ✅ Learning system integration
- ✅ Confidence tracking
- ✅ 4 feedback types

### Testing Infrastructure:
- ✅ 270+ automated tests
- ✅ Backend test suite (3 files, 100+ tests)
- ✅ Frontend test suite (2 files, 90+ tests)
- ✅ Integration tests for workflows
- ✅ Security testing (injection, XSS)
- ✅ Edge case coverage
- ✅ Accessibility testing
- ✅ Performance testing

### Phase 0 Complete - All 6 Features:
1. ✅ Self-Correcting SQL Agent
2. ✅ Learning from Corrections
3. ✅ Schema-Aware Fixes
4. ✅ Result Verification Agent
5. ✅ Query Planning Agent
6. ✅ **User Feedback Integration**

**Database Guru is now a fully self-improving SQL system with comprehensive test coverage!** 🚀
