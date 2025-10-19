# Debugging Multi-Database Query Issues

## Issues Observed

1. **DuckDB Query Failed** - Shows "Unknown error"
2. **No Observability Components** - Agent trace, corrections not showing

---

## Debugging Steps

### Step 1: Check Browser DevTools

1. Open browser DevTools (F12)
2. Go to **Network** tab
3. Find the request to `/api/multi-query/`
4. Click on it and check the **Response** tab

**Look for:**
```json
{
  "database_results": [
    {
      "connection_name": "ECommerceTestDB",
      "agent_trace": { ... },  // ← Should be here
      "attempts": [ ... ],      // ← Should be here
      "self_corrected": false,  // ← Should be here
      ...
    },
    {
      "connection_name": "Duck db eCommerce",
      "error": "...",           // ← Check actual error
      "agent_trace": { ... },  // ← Should be here even on error
      ...
    }
  ]
}
```

### Step 2: Check Backend Console

Look at your backend terminal for error messages. Should show:
```
ERROR - Failed to execute query on database 'Duck db eCommerce': [actual error]
```

---

## Known Issues & Fixes

### Issue 1: State Value Mismatch

**Problem:** DuckDB using `'New York'` but data might have `'NY'`

**Evidence:**
- SQLite: `WHERE c.state = 'NY'` ✅ Works
- DuckDB: `WHERE c.state = 'New York'` ❌ Fails

**Why:** The LLM generates different SQL for each database, and it might be making different assumptions about the state format.

**Solution:** The self-correcting agent should catch this and retry, BUT we need to see the actual error first.

### Issue 2: Observability Data Not Showing

**Possible Causes:**

1. **Backend not returning data:**
   - Check if `agent_trace`, `attempts`, etc. are in the API response
   - They should be there even if the query fails

2. **Frontend not receiving data:**
   - Check Network tab response
   - Check for TypeScript errors in console

3. **Components not rendering:**
   - Check browser console for React errors
   - Verify imports are correct

---

## Quick Fixes to Try

### Fix 1: Check Actual Error

Add console.log to see what we're getting:

**In browser console, run:**
```javascript
// After query completes, check the last response
fetch('/api/multi-query/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    question: "what products went to New York",
    chat_session_id: "your_session_id"  // Replace with actual
  })
}).then(r => r.json()).then(data => {
  console.log('Full Response:', data);
  console.log('Database Results:', data.database_results);
  data.database_results.forEach(db => {
    console.log(`${db.connection_name}:`, {
      success: db.success,
      error: db.error,
      has_trace: !!db.agent_trace,
      has_attempts: !!db.attempts,
      self_corrected: db.self_corrected
    });
  });
});
```

### Fix 2: Verify Backend is Running Latest Code

Restart the backend to ensure it has the latest changes:
```bash
# Stop backend (Ctrl+C)
# Restart:
source venv/bin/activate
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### Fix 3: Hard Refresh Frontend

Clear cache and reload:
- Chrome/Edge: Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)
- Firefox: Ctrl+F5 (Windows) or Cmd+Shift+R (Mac)

---

## Expected Behavior

### When Query Succeeds

Each database result should have:
```json
{
  "connection_name": "ECommerceTestDB",
  "success": true,
  "sql": "SELECT ...",
  "results": [...],
  "agent_trace": {
    "steps": [...],
    "total_elapsed_ms": 123.45
  },
  "self_corrected": false,
  "total_attempts": 1
}
```

### When Query Fails Then Corrects

```json
{
  "connection_name": "Duck db eCommerce",
  "success": true,
  "sql": "SELECT ... WHERE state = 'NY'",  // Corrected!
  "agent_trace": {
    "steps": [
      {"type": "generation", "message": "Generated SQL"},
      {"type": "error", "message": "Attempt 1 failed"},
      {"type": "quick_fix", "message": "Applied quick fix"},
      {"type": "success", "message": "Query succeeded"}
    ]
  },
  "attempts": [
    {"attempt_number": 1, "success": false, "error": "..."},
    {"attempt_number": 2, "success": true, "fix_method": "quick_fix"}
  ],
  "self_corrected": true,
  "total_attempts": 2
}
```

### When Query Completely Fails

```json
{
  "connection_name": "Duck db eCommerce",
  "success": false,
  "error": "relation 'products' does not exist",
  "agent_trace": {
    "steps": [
      {"type": "generation", "message": "Generated SQL"},
      {"type": "error", "message": "All 3 attempts exhausted"}
    ]
  },
  "attempts": [
    {"attempt_number": 1, "success": false},
    {"attempt_number": 2, "success": false},
    {"attempt_number": 3, "success": false}
  ],
  "self_corrected": false,
  "total_attempts": 3
}
```

---

## Checklist

- [ ] Check Network tab for `/api/multi-query/` response
- [ ] Verify `agent_trace` exists in response
- [ ] Verify `attempts` exists in response
- [ ] Check browser console for errors
- [ ] Check backend console for actual error
- [ ] Restart backend with latest code
- [ ] Hard refresh frontend
- [ ] Check if components show after refresh

---

## If Still Not Working

### Temporary Workaround

Visit the demo page to verify components work:
```
http://localhost:3000/?demo=true
```

This shows the observability components with mock data. If they show there but not in the real app, the issue is with the data flow, not the components.

### Report Back

Please share:
1. Full JSON response from Network tab
2. Any errors from browser console
3. Any errors from backend console
4. Screenshot of what you see

This will help me identify the exact issue!

---

*Debugging Guide Created: 2025-10-19*
