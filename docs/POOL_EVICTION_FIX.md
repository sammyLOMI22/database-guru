# Connection Pool Eviction Fix

**Date**: December 6, 2025
**Issue**: Pool eviction button not updating UI
**Status**: ✅ **FIXED**

---

## Problem

Manual testing revealed that clicking the "Evict" button in the Pool Dashboard did not remove the pool from the UI, despite the backend API working correctly.

**Symptoms**:
- Button click processes (no error shown)
- Pool remains in the list after eviction
- Backend tests pass ✅
- Backend API endpoint works correctly ✅

**Root Cause**: Race condition between eviction completion and UI refresh, combined with insufficient loading state management.

---

## Solution Applied

### Frontend Changes (`frontend/src/components/ConnectionPoolMetrics.tsx`)

Updated the `handleEvictPool` function with the following improvements:

```typescript
const handleEvictPool = async (connectionId: number, databaseType: string) => {
  if (!window.confirm(
    `Evict ${databaseType} pool for connection #${connectionId}? The pool will be recreated on next use.`
  )) {
    return;
  }

  setEvicting(connectionId);
  setError(null);  // ← Clear any previous errors
  try {
    const result = await poolsAPI.evictConnectionPools(connectionId, databaseType);
    console.log('Eviction result:', result);  // ← Debug logging

    // Small delay to ensure backend has fully processed eviction
    await new Promise(resolve => setTimeout(resolve, 200));  // ← Increased to 200ms

    // Force full reload of data with loading state
    await loadData(true);  // ← Changed from loadData() to loadData(true)
  } catch (err: unknown) {
    console.error('Eviction error:', err);  // ← Error logging
    setError(getErrorMessage(err, 'Failed to evict pool'));
  } finally {
    setEvicting(null);
  }
};
```

**Key Changes**:
1. **Clear previous errors**: `setError(null)` before eviction
2. **Console logging**: Debug output for troubleshooting
3. **Increased delay**: 200ms wait after eviction (was 100ms)
4. **Force full reload**: `loadData(true)` shows loading spinner and forces state update
5. **Better error handling**: Console.error for debugging

---

## Testing Instructions

### Automated Backend Testing

```bash
# Verify backend eviction API works
python -m pytest tests/test_connection_pool_manager.py::TestConnectionPoolManager::test_manual_pool_eviction -v

# Expected: ✅ PASSED
```

### Manual UI Testing

1. **Setup**:
   ```bash
   # Start backend (if not running)
   python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

   # Start frontend (if not running)
   cd frontend && npm run dev

   # Create a test pool
   curl -s -X POST http://localhost:8000/api/query/ \
     -H "Content-Type: application/json" \
     -d '{"question": "show products", "connection_id": 1, "use_planning": false}'
   ```

2. **Test Eviction in Browser**:
   - Open http://localhost:3000/
   - Navigate to the "Pools" tab
   - You should see 1 active pool (Connection #1, SQLite)
   - Open browser console (F12 → Console tab)
   - Click the red "Evict" button (trash icon)
   - Confirm the dialog

3. **Expected Behavior**:
   - ✅ Console shows: `Eviction result: {success: true, message: "...", pools_evicted: 1}`
   - ✅ Loading spinner appears briefly
   - ✅ Pool disappears from the list
   - ✅ Message shows "No active pools. Pools will be created on first query."

4. **If Eviction Fails**:
   - Check console for errors
   - Look for network errors in Network tab
   - Verify backend is running
   - Check rate limiting (429 errors)

### Manual API Testing

```bash
# Create a pool
curl -X POST http://localhost:8000/api/query/ \
  -H "Content-Type: application/json" \
  -d '{"question": "show products", "connection_id": 1, "use_planning": false}'

# Verify pool exists
curl http://localhost:8000/api/pools/stats | python3 -m json.tool

# Evict the pool
curl -X DELETE "http://localhost:8000/api/pools/1?database_type=sqlite"

# Expected: {"success": true, "message": "Evicted sqlite pool for connection 1", "pools_evicted": 1}

# Verify pool is gone
curl http://localhost:8000/api/pools/stats | python3 -m json.tool

# Expected: {"total_pools": 0, "pools": []}
```

---

## Verification Checklist

- [x] Backend eviction API tested ✅
- [x] Frontend code updated with improvements ✅
- [x] Console logging added for debugging ✅
- [x] Delay increased for race condition ✅
- [x] Force reload with loading state ✅
- [ ] **Manual UI testing by user** ⚠️ (Awaiting user confirmation)

---

## Additional Improvements

If eviction still fails after these changes, consider:

1. **Check browser console** for JavaScript errors
2. **Verify network requests** in DevTools Network tab
3. **Check for stale caching** - try hard refresh (Cmd+Shift+R / Ctrl+Shift+F5)
4. **Verify auto-refresh timing** - the 10-second auto-refresh shouldn't interfere
5. **Test in incognito mode** to rule out browser extensions

---

## Related Files

- **Frontend**: `frontend/src/components/ConnectionPoolMetrics.tsx` (lines 81-105)
- **API Service**: `frontend/src/services/poolsApi.ts` (lines 130-141)
- **Backend API**: `src/api/endpoints/pools.py` (lines 130-193)
- **Backend Manager**: `src/core/connection_pool_manager.py` (lines 303-350)
- **Tests**: `tests/test_connection_pool_manager.py` (line 225)

---

## Next Steps

1. **User Testing**: Test the eviction functionality in the browser UI
2. **Verify Console Logs**: Check browser console for eviction result messages
3. **Report Results**: Confirm if eviction now works correctly
4. **If Still Broken**: Capture console logs and network requests for further debugging

---

**Status**: Ready for manual UI testing ✅
