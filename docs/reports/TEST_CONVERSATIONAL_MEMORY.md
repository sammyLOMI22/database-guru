# Testing Conversational Memory Feature

## Quick Start

1. **Start the system:**
```bash
./start.sh
```

2. **Open your browser:**
```
http://localhost:3000
```

3. **Follow the test scenarios below!**

---

## Test Scenario 1: Basic Conversation Flow

### Steps:
1. **Create a new chat session:**
   - Click "New Session" in the left sidebar
   - Name it: "Product Queries Test"
   - Select your active database connection

2. **Ask Query 1:**
   ```
   Show me all products
   ```
   - Should return all products from your database
   - Context panel should show: "No conversation history yet"

3. **Ask Query 2 (with context):**
   ```
   Filter by electronics
   ```
   - Should automatically filter the previous products query
   - Context panel should now show Query 1
   - Blue badge should appear: "💡 Conversational memory active"

4. **Ask Query 3 (with context):**
   ```
   Sort by price
   ```
   - Should sort the filtered electronics by price
   - Context panel should show Query 1 and Query 2

### Expected Results:
- ✅ Query 1: `SELECT * FROM products`
- ✅ Query 2: `SELECT * FROM products WHERE category = 'electronics'`
- ✅ Query 3: `SELECT * FROM products WHERE category = 'electronics' ORDER BY price`

---

## Test Scenario 2: Context Panel Interaction

### Steps:
1. **Expand/Collapse Context Panel:**
   - Click the arrow icon next to "💬 Conversation Context"
   - Should expand/collapse smoothly

2. **View Context Details:**
   - Each query should show:
     - ✓ Question asked
     - ✓ SQL generated
     - ✓ Success/Error status
     - ✓ Row count (if available)

3. **Refresh Context:**
   - Click the refresh icon
   - Should reload context from server

4. **Clear Context:**
   - Click the trash icon
   - Confirm the dialog
   - Context should clear
   - Badge should disappear
   - Next query starts fresh

---

## Test Scenario 3: Smart Context Detection

### Test Different Question Types:

**Should Use Context (contextual questions):**
- "filter that" ✓
- "sort it" ✓
- "also show" ✓
- "by category" ✓
- "add limit" ✓

**Should NOT Use Context (standalone questions):**
- "Show me all customers from California" ✗
- "Get products ordered today" ✗
- "List all databases" ✗

### How to Test:
1. Ask "Show me all products"
2. Then ask contextual questions from the list above
3. Check the generated SQL - should build on previous query

---

## Test Scenario 4: Error Handling

### Test Error Recovery:

1. **Query with Error:**
   ```
   Show me invalid_table
   ```
   - Should fail with error
   - Should still save to context
   - Context panel should show ✗ Error status

2. **Follow-up Query:**
   ```
   Show me products instead
   ```
   - Should work
   - Should include failed query in context (for learning)

3. **Context After Error:**
   - Click expand context panel
   - Failed query should be visible
   - Error status should be clear

---

## Test Scenario 5: Multiple Sessions

### Steps:
1. **Session 1:**
   - Ask: "Show me products"
   - Ask: "Filter by electronics"
   - Context: 2 queries

2. **Switch to Session 2:**
   - Create new session
   - Ask: "Show me customers"
   - Context: Should be empty (separate from Session 1)

3. **Switch Back to Session 1:**
   - Select first session
   - Context: Should still have 2 queries
   - Ask: "Sort by price"
   - Context: Now has 3 queries

### Expected:
- ✅ Context is session-specific
- ✅ Context persists across session switches
- ✅ Each session maintains independent context

---

## API Testing (Using curl)

### 1. Create a Chat Session:
```bash
curl -X POST http://localhost:8000/api/chat/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Session",
    "connection_ids": [1]
  }'
```

**Note the session_id from response!**

### 2. Send Query with Context:
```bash
SESSION_ID="your-session-id-here"

# Query 1
curl -X POST http://localhost:8000/api/query/ \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Show me all products",
    "session_id": "'$SESSION_ID'"
  }'

# Query 2 (with context)
curl -X POST http://localhost:8000/api/query/ \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Filter by electronics",
    "session_id": "'$SESSION_ID'"
  }'
```

### 3. Get Conversation Context:
```bash
curl http://localhost:8000/api/chat/sessions/$SESSION_ID/context
```

**Expected Response:**
```json
{
  "session_id": "...",
  "context": {
    "has_context": true,
    "window_size": 2,
    "messages": [
      {
        "question": "Show me all products",
        "sql": "SELECT * FROM products",
        "success": true
      },
      {
        "question": "Filter by electronics",
        "sql": "SELECT * FROM products WHERE category = 'electronics'",
        "success": true
      }
    ]
  }
}
```

### 4. Clear Context:
```bash
curl -X DELETE http://localhost:8000/api/chat/sessions/$SESSION_ID/context
```

---

## Verification Checklist

### Backend:
- [ ] Backend starts without errors
- [ ] Query endpoint accepts session_id
- [ ] Context endpoint returns data
- [ ] Clear context endpoint works
- [ ] Context saved to database correctly

### Frontend:
- [ ] Context panel renders correctly
- [ ] Context updates after each query
- [ ] Expand/collapse works
- [ ] Refresh button works
- [ ] Clear button works with confirmation
- [ ] Context awareness badge appears
- [ ] No console errors

### Functionality:
- [ ] Context retrieved correctly
- [ ] Context-aware prompts generated
- [ ] Smart detection works
- [ ] Window size limits applied (3 queries default)
- [ ] Oldest queries removed when limit exceeded
- [ ] Context persists across session switches
- [ ] Clear context empties correctly

### Performance:
- [ ] Context loads quickly (< 100ms)
- [ ] No lag when switching sessions
- [ ] UI remains responsive
- [ ] No memory leaks

---

## Common Issues & Solutions

### Issue: Context panel shows "No conversation history"
**Solution:** Make sure you selected a chat session (not "Default Mode")

### Issue: Context not updating after queries
**Solution:**
1. Check that session_id is being sent in API calls
2. Click refresh button
3. Check browser console for errors

### Issue: "Session not found" error
**Solution:**
1. Create a new chat session
2. Make sure the session exists in database

### Issue: Frontend not loading
**Solution:**
```bash
cd frontend
npm install
npm run dev
```

### Issue: Backend errors
**Solution:**
```bash
source venv/bin/activate
pip install -r requirements.txt
python -m uvicorn src.main:app --reload
```

---

## Success Criteria

✅ **Phase 1 is working correctly if:**
1. You can create a chat session
2. Queries save to context automatically
3. Follow-up questions use context
4. Context panel displays correctly
5. Clear context resets properly
6. Multiple sessions maintain separate contexts
7. No errors in console or logs

---

## Performance Benchmarks

Expected performance:
- Context retrieval: < 10ms
- Query with context: +50ms vs no context
- Context panel render: < 100ms
- Clear context: < 50ms

Check logs for timing information.

---

## Next Steps After Testing

Once you've verified Phase 1 works:
1. Document any bugs found
2. Adjust context window size if needed
3. Customize UI styling if desired
4. Move on to Phase 2: Streaming Results!

---

## Need Help?

If you encounter issues:
1. Check backend logs: `backend.log`
2. Check frontend console
3. Check database: `database_guru.db`
4. Review test output: `pytest tests/test_conversational_memory.py -v`

**Have fun testing!** 🎉
