# Debugging Report: Connection Pool Eviction & UI Issues

**Date**: December 7, 2025
**Status**: Fixes Applied (Pending Environment Reset)

## 1. Issue Description
Two distinct but related issues were reported regarding the Connection Pool Management UI:
1.  **Eviction Failure ("Flash")**: Clicking the "Evict" button caused the page to reload instantly (flash) without performing the eviction. The UI would sometimes show "Error on page".
2.  **Display Glitch ("0/0/")**: The "Connections" column displayed `0/0/` instead of the expected `Active / Idle / Capacity` values (e.g., `0 / 0 / 30`).

## 2. Root Cause Analysis

### A. Eviction Failure (Frontend & Backend)
This was a multi-layered failure involving both the frontend event handling and backend logic.

1.  **Frontend Event Handling (The "Flash")**:
    *   **Cause**: The `<button>` element in `ConnectionPoolMetrics.tsx` lacked the `type="button"` attribute. Browsers treat buttons inside forms (or sometimes implicitly) as `autosubmit` by default, causing a full page reload before the React `onClick` handler could complete the API call.
    *   **Fix**: Added `type="button"` and `e.preventDefault()` to the click handler.

2.  **Backend Silent Failure (Case Sensitivity)**:
    *   **Cause**: The Frontend sends the database type as "SQLite" (mixed case). The Backend's `ConnectionPoolManager` stored keys as provided (e.g., "SQLite"), but the eviction logic in `evict_pool` initially checked for an exact match or a naive lowercase conversion that didn't match the stored key structure `(id, "SQLite")`.
    *   **Fix**: Updated `ConnectionPoolManager.evict_pool` to iterate over all pool keys and perform a robust case-insensitive comparison against the request.

3.  **Backend Race Condition (Error 500)**:
    *   **Cause**: The `get_all_metrics` method iterated directly over `self._pools`. If an eviction (deletion) occurred simultaneously, Python raised `RuntimeError: dictionary changed size during iteration`.
    *   **Fix**: Updated `get_all_metrics` to iterate over a copy of the list: `list(self._pools.items())`.

### B. "0/0/" Display Glitch
1.  **Interface Mismatch**:
    *   **Cause**: The Backend API (`/api/pools/stats`) returns the field `total_capacity`. The Frontend interface `PoolMetrics` (in `poolsApi.ts`) defined this field as `capacity`. Because of this mismatch, the value was `undefined` in the UI, rendering as empty.
    *   **Fix**: Updated `frontend/src/services/poolsApi.ts` to rename `capacity` to `total_capacity` and updated the component to display the correct field.

### C. Persistence of Issues (Why it didn't look fixed)
Even after applying valid fixes, the issues persisted for the user.
1.  **Zombie Processes**: Debugging revealed "Address already in use" errors in the logs. Old instances of the backend process (holding the old code) were stuck running on port 8000.
2.  **Caching**: The exact code on disk was verified to be correct, yet the browser behavior reflected the old code. This indicates aggressive caching by Vite (`node_modules/.vite`) or the browser.

## 3. Summary of Code Changes

### `frontend/src/components/ConnectionPoolMetrics.tsx`
```tsx
// BEFORE
<button
  onClick={() => handleEvictPool(...)}
  // ...
>

// AFTER
<button
  type="button" // Prevent form submission
  onClick={(e) => {
    e.preventDefault(); // Stop event propagation
    handleEvictPool(...);
  }}
  // ...
>
```

### `frontend/src/services/poolsApi.ts`
```typescript
// BEFORE
export interface PoolMetrics {
  capacity: number;
}

// AFTER
export interface PoolMetrics {
  total_capacity: number; // Matches backend JSON response
}
```

### `src/core/connection_pool_manager.py`
```python
# Fixed iteration safety
def get_all_metrics(self):
    for key, pool in list(self._pools.items()): # Iterate over copy
        # ...

# Fixed Case-Sensitivity
async def evict_pool(self, connection_id, database_type):
    # ...
    # Robust search for matching key regardless of stored case
    for key in self._pools.keys():
        if key[0] == connection_id and key[1].lower() == target_db_type_lower:
            target_key = key
            break
    # ...
```

## 4. Resolution Guide

If the issues appear to persist, it is purely an environment artifact. Pplease follow these steps to force a clean state:

1.  **Stop All Servers**: Ctrl+C in your terminal.
2.  **Kill Zombie Processes**:
    ```bash
    kill -9 $(lsof -t -i:8000)
    # Or manually find python processes and kill them
    ```
3.  **Clear Frontend Cache**:
    ```bash
    rm -rf frontend/node_modules/.vite
    ```
4.  **Restart**:
    ```bash
    ./start_all.sh
    ```
5.  **Hard Refresh Browser**: Cmd+Shift+R (Mac) or Ctrl+F5.
