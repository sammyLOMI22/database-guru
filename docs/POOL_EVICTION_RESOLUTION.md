# Pool Eviction Issue - Resolution Steps

**Status**: All code fixes applied ✅ | Environment cleanup required ⚠️

---

## Issue Summary

The pool eviction button was not working due to a combination of:
1. **Code Issues** (ALL FIXED ✅):
   - Missing `type="button"` attribute causing page flash
   - Backend case sensitivity in pool key matching
   - Race condition in `get_all_metrics` iteration
   - Frontend/backend field name mismatch (`capacity` vs `total_capacity`)
   - Auto-refresh interfering with manual eviction

2. **Environment Issue** (REQUIRES ACTION ⚠️):
   - Zombie processes running old code (2 PIDs found on port 8000)
   - Vite cache holding old frontend code
   - Python cache potentially stale

---

## Verification: All Code Fixes Are In Place

✅ **Button has proper event handling** (`frontend/src/components/ConnectionPoolMetrics.tsx:406-420`):
```typescript
<button
  type="button"  // Prevents form submission
  onClick={(e) => {
    e.preventDefault();  // Stops propagation
    handleEvictPool(pool.connection_id, pool.database_type);
  }}
```

✅ **Backend has case-insensitive matching** (`src/core/connection_pool_manager.py:314-340`):
```python
# Check for direct match first
direct_key = (connection_id, database_type)
if direct_key in self._pools:
    target_key = direct_key
else:
    # Search for case-insensitive match
    for key in self._pools.keys():
        if key[0] == connection_id and key[1].lower() == target_db_type_lower:
            target_key = key
            break
```

✅ **Thread-safe iteration** (`src/core/connection_pool_manager.py:438`):
```python
for key, pool in list(self._pools.items()):  # Iterate over copy
```

✅ **Field name fixed** (`frontend/src/services/poolsApi.ts:44`):
```typescript
total_capacity: number;  // Matches backend response
```

✅ **Auto-refresh pause/resume** (`frontend/src/components/ConnectionPoolMetrics.tsx:95-129`):
```typescript
// Pause auto-refresh before eviction
if (intervalRef.current) {
    clearInterval(intervalRef.current);
    intervalRef.current = null;
}
// ... eviction logic ...
// Restart in finally block
finally {
    setEvicting(null);
    startAutoRefresh();
}
```

---

## Resolution Steps

### Step 1: Kill Zombie Processes and Clear Caches

Run the cleanup script:

```bash
chmod +x scripts/clean_restart.sh
./scripts/clean_restart.sh
```

**Expected Output**:
```
🧹 Starting complete cleanup...
1️⃣ Killing all processes on port 8000...
   Found processes: 54613 64732
   ✅ Killed zombie processes
2️⃣ Killing all processes on port 3000...
   ✅ Killed frontend processes
3️⃣ Clearing Vite cache...
   ✅ Cleared Vite cache
4️⃣ Clearing Python cache...
   ✅ Cleared Python cache
5️⃣ Waiting for ports to be free...
   ✅ Port 8000 is free
   ✅ Port 3000 is free

✅ Cleanup complete!
```

### Step 2: Restart Servers

**Terminal 1 - Backend**:
```bash
source venv/bin/activate
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend**:
```bash
cd frontend
npm run dev
```

### Step 3: Hard Refresh Browser

- **Mac**: `Cmd + Shift + R`
- **Windows/Linux**: `Ctrl + F5` or `Ctrl + Shift + R`

This ensures the browser loads the new JavaScript code, not cached versions.

### Step 4: Test Eviction

1. Open browser console (F12 → Console tab)
2. Navigate to http://localhost:3000/
3. Go to "Pools" tab
4. If no pools exist, create one by running a query
5. Click the red "Evict" button (trash icon)
6. **Watch console output**:

**Expected Console Logs**:
```
✅ Eviction successful: {success: true, message: "...", pools_evicted: 1}
🔄 Reloading pool data...
✅ Data reloaded. Total pools: 0
```

**Expected UI Behavior**:
- Loading spinner appears briefly
- Pool disappears from the list
- Message shows "No active pools. Pools will be created on first query."

---

## Troubleshooting

### If Port 8000 Still In Use

Find and kill manually:
```bash
lsof -t -i:8000
# Note the PIDs
kill -9 <PID1> <PID2> ...
```

### If Eviction Still Fails After Cleanup

1. **Check Console for Errors**: Look for red error messages
2. **Check Network Tab**:
   - Open DevTools → Network
   - Click evict button
   - Look for DELETE request to `/api/pools/1?database_type=sqlite`
   - Check response status (should be 200)
3. **Verify Backend Logs**: Check terminal running backend for error messages
4. **Check Auto-Refresh**: Console should show auto-refresh is paused during eviction

### If Browser Shows Old UI

1. Clear browser cache completely:
   - Chrome: Settings → Privacy → Clear browsing data → Cached images and files
   - Firefox: Settings → Privacy → Clear Data → Cached Web Content
2. Try incognito/private mode
3. Try different browser

---

## Success Criteria

- ✅ Clicking "Evict" button does NOT cause page flash/reload
- ✅ Console shows eviction success message
- ✅ Pool disappears from UI within 1 second
- ✅ No errors in console or backend logs
- ✅ "Connections" column shows proper format (e.g., "0 / 0 / 30")
- ✅ Age column shows proper format (e.g., "30.4s", "2.1h")

---

## Files Changed (For Reference)

**Backend**:
- `src/core/connection_pool_manager.py` - 4 fixes (connection_name, eviction case-sensitivity, thread-safe iteration, top-level fields)

**Frontend**:
- `frontend/src/components/ConnectionPoolMetrics.tsx` - 3 fixes (button type, auto-refresh pause/resume, enhanced logging)
- `frontend/src/services/poolsApi.ts` - 1 fix (capacity → total_capacity)

**Tests**:
- `tests/test_connection_pool_manager.py` - 3 updates (verify connection_name, age_seconds, top-level fields)

**Scripts**:
- `scripts/clean_restart.sh` - New cleanup script

**Documentation**:
- `docs/DEBUGGING_POOL_EVICTION_REPORT.md` - Complete issue analysis
- `docs/POOL_EVICTION_FIX.md` - Fix documentation with testing guide
- `docs/POOL_EVICTION_RESOLUTION.md` - This file (resolution steps)

---

## Next Steps After Successful Test

1. ✅ Run backend tests to ensure no regressions
2. ✅ Update `PR_REVIEW.md` to mark issues as RESOLVED
3. ✅ Commit all changes
4. ✅ Merge PR to main branch

---

**Last Updated**: December 7, 2025
**Status**: Ready for user to execute cleanup and retest
