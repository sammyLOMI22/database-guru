# Connection Pooling - Manual Testing Guide

**Date**: December 6, 2025
**Feature**: Connection Pooling Dashboard
**Component**: `frontend/src/components/ConnectionPoolMetrics.tsx`
**Status**: Ready for Manual Testing

---

## Prerequisites

Before starting the manual tests, ensure:

1. ✅ **Backend Running**: http://0.0.0.0:8000
   ```bash
   source venv/bin/activate
   python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. ✅ **Frontend Running**: http://localhost:3000
   ```bash
   cd frontend
   npm run dev
   ```

3. ✅ **Connection Pooling Enabled**: Check `.env` file
   ```bash
   ENABLE_CONNECTION_POOLING=True
   USER_DB_POOL_SIZE=10
   USER_DB_MAX_OVERFLOW=20
   ```

4. ✅ **Database Connections Available**: At least one test database connection configured
   - ECommerceTestDB (SQLite)
   - Duck db eCommerce (DuckDB)

---

## Quick Verification

Before detailed testing, verify the system is ready:

```bash
# Check backend health
curl http://localhost:8000/health

# Check pool stats (should show pooling_enabled: true)
curl http://localhost:8000/api/pools/stats

# Check available connections
curl http://localhost:8000/api/connections/
```

**Expected Response**:
```json
{
  "total_pools": 0,
  "global_metrics": {
    "total_active_connections": 0,
    "total_idle_connections": 0,
    "avg_utilization_percent": 0.0
  },
  "pools": [],
  "pooling_enabled": true
}
```

---

## Manual Testing Checklist

### **TEST 1: Navigate to Dashboard** ✅

**Objective**: Verify the dashboard loads correctly

**Steps**:
1. Open http://localhost:3000/ in your browser
2. Click on the **"Pools"** tab in the main navigation
   - Should be the 6th tab after: Query, Connections, Chat, Tools, Cache

**Expected Results**:
- ✅ Dashboard loads successfully without errors
- ✅ Shows one of:
  - "Connection Pooling Disabled" message (if pooling is off), OR
  - "No Active Pools" message (if no queries have been run yet)
- ✅ Global metrics cards display:
  - **Total Pools**: 0
  - **Active Connections**: 0
  - **Idle Connections**: 0
  - **Avg Utilization**: 0%
- ✅ Empty pool table with message: "No pools currently active"

**Visual Check**:
- Clean layout with gradient header
- Stats cards with icons
- Empty state is user-friendly

---

### **TEST 2: Execute Query to Create Pool** ✅

**Objective**: Create a connection pool by executing a query

**Steps**:
1. Navigate to **"Query"** tab
2. Select **"ECommerceTestDB"** (SQLite) from the connection dropdown
3. Enter question: `Show me all products`
4. Click **"Execute Query"** button
5. Wait for query to complete (should show results table)
6. Navigate back to **"Pools"** tab

**Expected Results**:
- ✅ **Total Pools**: 1
- ✅ **Active Connections**: 0 (after query completes, pool is idle)
- ✅ **Idle Connections**: 10 (default pool size)
- ✅ **Avg Utilization**: Low % (depends on pool size)
- ✅ Pool table shows one row:
  - **Connection Name**: "ECommerceTestDB"
  - **Database Type**: "sqlite" (blue badge)
  - **Pool Size**: 10
  - **Max Overflow**: 20
  - **Active**: 0
  - **Idle**: 10
  - **Utilization**: Green progress bar (low %)
  - **Total Checkouts**: 1+
  - **Total Checkins**: Matches checkouts
  - **Checkout Failures**: 0
  - **Avg Wait Time**: Low (< 1ms typical)
  - **Max Wait Time**: Low
  - **Age**: "0m 5s" or similar
  - **Actions**: "Evict" button

**Visual Check**:
- Stats cards update from 0 to actual values
- Pool table renders with proper formatting
- Utilization bar is green (healthy)

---

### **TEST 3: Auto-Refresh Functionality** ✅

**Objective**: Verify dashboard auto-refreshes every 10 seconds

**Steps**:
1. Stay on the **"Pools"** dashboard
2. Watch the dashboard for 30 seconds
3. Observe the **Age** column in the pool table

**Expected Results**:
- ✅ Dashboard refreshes every 10 seconds automatically
- ✅ Brief skeleton loader appears during refresh (flash of gray boxes)
- ✅ **Age** column increments:
  - First refresh: "0m 10s"
  - Second refresh: "0m 20s"
  - Third refresh: "0m 30s"
- ✅ Metrics remain consistent (no flickering or data loss)
- ✅ No console errors during refresh

**Visual Check**:
- Smooth refresh without jarring UI changes
- Loading skeleton is brief and non-intrusive

---

### **TEST 4: Manual Refresh** ✅

**Objective**: Test manual refresh button

**Steps**:
1. On the **"Pools"** dashboard, locate the **"Refresh"** button (circular arrow icon, top right)
2. Click the **"Refresh"** button

**Expected Results**:
- ✅ Dashboard refreshes immediately (doesn't wait for 10s auto-refresh)
- ✅ Brief loading state appears
- ✅ Updated metrics displayed
- ✅ Age counters may not change much (depends on timing)

**Visual Check**:
- Button shows active state when clicked
- Refresh is instantaneous

---

### **TEST 5: Pool Utilization (Execute Multiple Queries)** ✅

**Objective**: Observe active connections and utilization during query execution

**Steps**:
1. Navigate to **"Query"** tab
2. Keep the **"Pools"** tab open in a second browser window or tab
3. Execute multiple queries in **quick succession** (within a few seconds):
   - `Show me all customers`
   - `Show me all orders`
   - `Count total products`
   - `List order items`
4. **Quickly** switch to the **"Pools"** tab (or watch the second window)

**Expected Results**:
- ✅ **Active Connections**: Shows non-zero value while queries execute (e.g., 1-4)
- ✅ **Idle Connections**: Decreases as connections become active
- ✅ **Utilization %**: Increases temporarily
- ✅ **Utilization Bar**: Color changes:
  - Green (< 50%)
  - Yellow (50-70%)
  - Red (> 70%)
- ✅ Pool table shows real-time active/idle changes
- ✅ **Total Checkouts** increments with each query
- ✅ After queries complete:
  - Active → 0
  - Idle → 10
  - Utilization returns to low %

**Visual Check**:
- Real-time updates show pool activity
- Utilization bar animates smoothly
- No UI lag or freezing

---

### **TEST 6: Health Status** ✅

**Objective**: Verify health warnings appear based on utilization

**Steps**:
1. Check the **Health Status** section at the top of the dashboard
2. Execute queries to increase utilization (see TEST 5)
3. Observe health status changes

**Expected Results**:

**Scenario A: Low Utilization (< 70%)**
- ✅ Status: **"Healthy"** (green badge)
- ✅ No warnings displayed
- ✅ Icon: Green checkmark

**Scenario B: Medium Utilization (70-90%)**
- ✅ Status: **"Degraded"** (yellow badge)
- ✅ Warnings displayed:
  - "Pool utilization is high (XX%)"
  - "Consider increasing pool size or max overflow"
- ✅ Icon: Yellow warning triangle

**Scenario C: High Utilization (> 90%)**
- ✅ Status: **"Unhealthy"** (red badge)
- ✅ Warnings displayed:
  - "Pool is at critical utilization (XX%)"
  - "Immediate action recommended"
- ✅ Icon: Red alert circle

**Visual Check**:
- Health badge color matches status
- Warnings are clear and actionable

---

### **TEST 7: Pool Details Table** ✅

**Objective**: Verify all pool table columns display correctly

**Steps**:
1. Execute a query to create at least one pool (see TEST 2)
2. Review all columns in the pool details table

**Expected Results**:

**Table Columns**:
- ✅ **Connection Name**: Displays database connection name
- ✅ **Database Type**: Shows badge with database type
  - SQLite: Blue badge
  - PostgreSQL: Purple badge
  - MySQL: Orange badge
  - DuckDB: Green badge
- ✅ **Pool Size / Max Overflow**: Displays "10 / 20"
- ✅ **Active / Idle**: Shows current active and idle counts
- ✅ **Utilization**:
  - Percentage displayed
  - Colored progress bar (green/yellow/red)
  - Bar width matches percentage
- ✅ **Checkout Stats**: Shows "Total / Failures" (e.g., "15 / 0")
- ✅ **Wait Times**: Shows "Avg / Max" in milliseconds (e.g., "0.5ms / 10.0ms")
- ✅ **Age**: Formatted as "Xm Ys" (e.g., "5m 32s")
- ✅ **Actions**: "Evict" button (red/danger style)

**Data Accuracy**:
- ✅ Active + Idle ≤ Pool Size + Max Overflow
- ✅ Utilization % = (Active / (Pool Size + Max Overflow)) * 100
- ✅ Age increments with each refresh

**Visual Check**:
- Table is responsive and readable
- Columns align properly
- Progress bars render correctly

---

### **TEST 8: Manual Pool Eviction** ⚠️

**Objective**: Test manual eviction of a single pool

**Steps**:
1. Ensure at least one pool is active (see TEST 2)
2. Click the **"Evict"** button for one pool in the table
3. Confirm the browser prompt that appears

**Expected Results**:
- ✅ Browser confirmation dialog appears:
  - Message: "Are you sure you want to evict this pool?"
  - Buttons: "OK" and "Cancel"
- ✅ After clicking "OK":
  - Pool row disappears from table
  - **Total Pools** count decreases by 1
  - **Active Connections** and **Idle Connections** update
  - Global metrics recalculate
- ✅ If "Cancel" clicked:
  - Pool remains in table
  - No changes to metrics

**Side Effect**:
- ✅ Next query on that connection will create a new pool
- ✅ Age will reset to "0m 0s"

**Visual Check**:
- Smooth removal animation
- Metrics update instantly

---

### **TEST 9: Evict All Pools** ⚠️

**Objective**: Test clearing all connection pools at once

**Steps**:
1. Create multiple pools by executing queries on different connections:
   - Query on "ECommerceTestDB" (SQLite)
   - Query on "Duck db eCommerce" (DuckDB)
2. Verify **Total Pools** ≥ 2
3. Click the **"Evict All"** button (red button at top right)
4. Confirm the browser prompt

**Expected Results**:
- ✅ Browser confirmation dialog appears:
  - Message: "Are you sure you want to evict all connection pools?"
  - Buttons: "OK" and "Cancel"
- ✅ After clicking "OK":
  - **All pools** disappear from table
  - **Total Pools**: 0
  - **Active Connections**: 0
  - **Idle Connections**: 0
  - **Avg Utilization**: 0%
  - Table shows: "No pools currently active"
- ✅ If "Cancel" clicked:
  - All pools remain
  - No changes to metrics

**Visual Check**:
- Clean transition to empty state
- No orphaned UI elements

---

### **TEST 10: Pool Recreation** ✅

**Objective**: Verify pools recreate automatically after eviction

**Steps**:
1. Evict all pools (see TEST 9)
2. Navigate to **"Query"** tab
3. Execute a new query on any connection
4. Navigate back to **"Pools"** tab

**Expected Results**:
- ✅ New pool appears in table
- ✅ **Total Pools**: 1
- ✅ Pool starts with:
  - **Utilization**: 0% (idle)
  - **Age**: "0m Xs" (new pool)
  - **Checkouts**: 1+
  - **Wait Times**: Low
- ✅ Identical pool configuration to before eviction

**Visual Check**:
- Pool recreation is seamless
- No errors or delays

---

### **TEST 11: Multiple Database Pools** ✅

**Objective**: Verify multiple pools display simultaneously

**Steps**:
1. Execute queries on **different** database connections:
   - Query on "ECommerceTestDB" (SQLite)
   - Query on "Duck db eCommerce" (DuckDB)
2. Navigate to **"Pools"** tab

**Expected Results**:
- ✅ **Total Pools**: 2 (or more)
- ✅ Pool table shows **2 separate rows**:
  - Row 1: ECommerceTestDB (sqlite, blue badge)
  - Row 2: Duck db eCommerce (duckdb, green badge)
- ✅ Each pool has **independent metrics**:
  - Different checkout counts
  - Different ages (if created at different times)
  - Different utilization %
- ✅ **Global Metrics** aggregate across all pools:
  - Total Active = Sum of all active connections
  - Total Idle = Sum of all idle connections
  - Avg Utilization = Weighted average

**Visual Check**:
- Multiple pools render without overlap
- Database type badges are distinct colors
- Table scrolls if many pools (> 5)

---

### **TEST 12: Pool Age Tracking** ✅

**Objective**: Verify pool age increments over time

**Steps**:
1. Create a pool (see TEST 2)
2. Note the initial age (e.g., "0m 5s")
3. Wait for **1 minute** (watch the auto-refresh)
4. Observe the **Age** column

**Expected Results**:
- ✅ Age increments with each 10-second refresh:
  - Refresh 1: "0m 10s"
  - Refresh 2: "0m 20s"
  - Refresh 3: "0m 30s"
  - ...
  - After 1 min: "1m 0s"
  - After 5 min: "5m 0s"
- ✅ Format is consistent: "Xm Ys"
- ✅ Age continues to increment until pool is evicted

**Long-Term Behavior** (optional):
- After 30 minutes: Pool may be auto-evicted (if idle timeout is enabled)
- After 2 hours: Pool may be auto-evicted (if max age is enabled)

**Visual Check**:
- Age updates smoothly
- No time discrepancies

---

### **TEST 13: Checkout/Checkin Stats** ✅

**Objective**: Verify checkout and checkin counters are accurate

**Steps**:
1. Create a pool (see TEST 2)
2. Note the initial **Total Checkouts** (e.g., 1)
3. Execute **5 more queries** on the same connection
4. Navigate back to **"Pools"** tab

**Expected Results**:
- ✅ **Total Checkouts** increments by 5 (now 6 total)
- ✅ **Total Checkins** matches checkouts when queries complete
- ✅ **Checkout Failures**: Remains 0 (unless errors occurred)
- ✅ **Active Connections**: 0 (after all queries complete)

**With Errors** (optional):
- Execute a query that fails (e.g., invalid SQL)
- ✅ **Checkout Failures** increments by 1
- ✅ **Total Checkouts** still increments

**Visual Check**:
- Counters update reliably
- No negative values or overflows

---

### **TEST 14: Wait Time Metrics** ✅

**Objective**: Observe wait time statistics under load

**Steps**:
1. Create a pool (see TEST 2)
2. Execute **many concurrent queries** to stress the pool:
   - Open multiple browser tabs
   - Execute queries simultaneously on the same connection
   - Try to exceed pool size (10 concurrent queries)
3. Navigate to **"Pools"** tab

**Expected Results**:

**Low Load (< 10 concurrent queries)**:
- ✅ **Avg Wait Time**: Very low (< 1ms)
- ✅ **Max Wait Time**: Low (< 5ms)
- ✅ No queueing occurs

**High Load (> 10 concurrent queries, exceeding pool size)**:
- ✅ **Avg Wait Time**: Increases (may be 10-100ms)
- ✅ **Max Wait Time**: Shows highest wait observed
- ✅ Some queries may queue if pool is exhausted
- ✅ Overflow connections are created (up to max overflow = 20)

**Visual Check**:
- Wait times displayed in milliseconds
- Values are reasonable (not negative or extreme)

---

### **TEST 15: Settings Display** ✅

**Objective**: Verify pool configuration is visible (if displayed)

**Steps**:
1. Check for a settings section or info panel on the dashboard
2. If present, review the displayed configuration

**Expected Results** (if settings section exists):
- ✅ **Pool Size**: 10 (default from USER_DB_POOL_SIZE)
- ✅ **Max Overflow**: 20 (default from USER_DB_MAX_OVERFLOW)
- ✅ **Pool Timeout**: 30s (default from USER_DB_POOL_TIMEOUT)
- ✅ **Pool Recycle**: 3600s / 1 hour (from USER_DB_POOL_RECYCLE)
- ✅ **Pre-ping Enabled**: True (health check enabled)
- ✅ **Idle Timeout**: 1800s / 30 min
- ✅ **Max Age**: 7200s / 2 hours

**Note**: If settings aren't displayed on the dashboard, check via API:
```bash
curl http://localhost:8000/api/pools/settings
```

**Visual Check**:
- Settings are clearly labeled
- Values match .env configuration

---

### **TEST 16: Error Handling** ✅

**Objective**: Verify dashboard handles API failures gracefully

**Steps**:
1. (Optional) Temporarily stop the backend server:
   ```bash
   # In the backend terminal, press Ctrl+C
   ```
2. Navigate to **"Pools"** tab or wait for auto-refresh
3. Observe the error state

**Expected Results**:
- ✅ Dashboard shows **error state**:
  - Red error message: "Failed to load pool statistics"
  - Or: "Error loading pool data"
  - Reason displayed (e.g., "Network error")
- ✅ **Retry button** appears
- ✅ No JavaScript console errors that crash the app
- ✅ Clicking "Retry" attempts to reload data

**After Restarting Backend**:
- ✅ Click "Retry" or wait for auto-refresh
- ✅ Dashboard recovers and displays data normally

**Visual Check**:
- Error message is user-friendly
- Retry mechanism works

---

### **TEST 17: Disabled State** ✅

**Objective**: Verify dashboard shows disabled state when pooling is off

**Steps** (requires configuration change):
1. Edit `.env` file:
   ```bash
   ENABLE_CONNECTION_POOLING=False
   ```
2. Restart the backend server
3. Navigate to **"Pools"** tab

**Expected Results**:
- ✅ Dashboard shows **"Connection Pooling Disabled"** message
- ✅ No pool table or metrics displayed
- ✅ Information about how to enable pooling:
  - "Set ENABLE_CONNECTION_POOLING=True in .env"
  - "Restart the server to enable"

**After Re-enabling**:
1. Edit `.env` file:
   ```bash
   ENABLE_CONNECTION_POOLING=True
   ```
2. Restart backend
3. ✅ Dashboard returns to normal operation

**Visual Check**:
- Disabled state is clear and informative
- No confusing empty states

---

## Visual Validation

### **Color Coding Checks**

**Utilization Progress Bars**:
- ✅ **< 50% utilization**: Green bar
- ✅ **50-70% utilization**: Yellow bar
- ✅ **> 70% utilization**: Red bar

**Database Type Badges**:
- ✅ **SQLite**: Blue badge (`bg-blue-100 text-blue-800`)
- ✅ **PostgreSQL**: Purple badge (`bg-purple-100 text-purple-800`)
- ✅ **MySQL**: Orange badge (`bg-orange-100 text-orange-800`)
- ✅ **DuckDB**: Green badge (`bg-green-100 text-green-800`)

**Health Status Badges**:
- ✅ **Healthy**: Green badge with checkmark icon
- ✅ **Degraded**: Yellow badge with warning icon
- ✅ **Unhealthy**: Red badge with alert icon
- ✅ **Disabled**: Gray badge

**Icons**:
- ✅ **Database icon** in stats cards
- ✅ **Activity icon** for connections
- ✅ **Zap icon** for utilization
- ✅ **Refresh icon** for manual refresh button
- ✅ **Trash icon** for evict buttons

---

## Performance Checks

### **Auto-Refresh Performance**:
- ✅ Auto-refresh interval: 10 seconds (configurable)
- ✅ No memory leaks (check browser DevTools → Performance)
- ✅ No excessive re-renders (check React DevTools)

### **API Response Times**:
```bash
# Test API performance
time curl http://localhost:8000/api/pools/stats
# Should be < 50ms

time curl http://localhost:8000/api/pools/health
# Should be < 50ms
```

### **Frontend Rendering**:
- ✅ Initial load: < 500ms
- ✅ Refresh load: < 200ms
- ✅ No UI jank or stuttering
- ✅ Smooth animations

---

## Browser Compatibility

Test the dashboard on multiple browsers:

- ✅ **Chrome** (v120+)
- ✅ **Firefox** (v120+)
- ✅ **Safari** (v17+)
- ✅ **Edge** (v120+)

**Expected**: All features work consistently across browsers.

---

## Accessibility Checks

### **Keyboard Navigation**:
- ✅ Tab through buttons (Refresh, Evict, Evict All)
- ✅ Enter key activates buttons
- ✅ Focus indicators visible

### **Screen Reader** (optional):
- ✅ Table headers announced
- ✅ Button labels clear
- ✅ Status messages readable

### **Contrast**:
- ✅ Text meets WCAG AA standards
- ✅ Color-blind friendly (not relying solely on color)

---

## Quick Test Summary

Use this checklist for rapid verification:

### **Basic Functionality** (Must Pass):
- [ ] Dashboard loads without errors
- [ ] Pool created after executing a query
- [ ] Auto-refresh works (every 10s)
- [ ] Manual refresh button works
- [ ] Pool metrics display correctly
- [ ] Pool eviction works
- [ ] Multiple pools display correctly

### **Advanced Features** (Should Pass):
- [ ] Health status changes with utilization
- [ ] Age tracking increments over time
- [ ] Checkout/checkin stats are accurate
- [ ] Wait time metrics display
- [ ] Utilization bar colors change appropriately
- [ ] Database type badges are correct

### **Edge Cases** (Nice to Have):
- [ ] Error handling when backend is down
- [ ] Disabled state when pooling is off
- [ ] Pool recreation after eviction
- [ ] High load (concurrent queries) handled

---

## Known Issues

**None identified at this time.**

If you encounter any issues during testing, please document:
1. Browser and version
2. Steps to reproduce
3. Expected vs actual behavior
4. Screenshots (if visual issue)
5. Console errors (if any)

---

## Test Results Template

Use this template to record your test results:

```markdown
## Test Results

**Date**: YYYY-MM-DD
**Tester**: [Your Name]
**Browser**: Chrome 120.0
**OS**: macOS 14.1

### Results:

| Test # | Test Name | Status | Notes |
|--------|-----------|--------|-------|
| 1 | Navigate to Dashboard | ✅ PASS | Loaded successfully |
| 2 | Execute Query to Create Pool | ✅ PASS | Pool created, metrics correct |
| 3 | Auto-Refresh | ✅ PASS | Refreshes every 10s |
| 4 | Manual Refresh | ✅ PASS | Immediate update |
| 5 | Pool Utilization | ✅ PASS | Real-time active/idle tracking |
| 6 | Health Status | ✅ PASS | Status badges correct |
| 7 | Pool Details Table | ✅ PASS | All columns display |
| 8 | Manual Eviction | ✅ PASS | Pool removed successfully |
| 9 | Evict All | ✅ PASS | All pools cleared |
| 10 | Pool Recreation | ✅ PASS | New pool created |
| 11 | Multiple Pools | ✅ PASS | 2 pools displayed |
| 12 | Age Tracking | ✅ PASS | Age increments |
| 13 | Checkout/Checkin Stats | ✅ PASS | Accurate counters |
| 14 | Wait Time Metrics | ✅ PASS | Low wait times |
| 15 | Settings Display | ⏭️ SKIP | Not implemented |
| 16 | Error Handling | ✅ PASS | Error state works |
| 17 | Disabled State | ⏭️ SKIP | Not tested |

### Overall Status: ✅ **PASS** (15/15 core tests passed)

### Issues Found: None

### Recommendations: None - ready for production
```

---

## Conclusion

This manual testing guide covers:
- **17 functional tests** covering all major features
- **Visual validation** of colors, badges, and icons
- **Performance checks** for API and frontend
- **Error handling** verification
- **Browser compatibility** testing
- **Accessibility** checks

After completing these tests, the Connection Pooling Dashboard should be:
- ✅ Fully functional
- ✅ Visually polished
- ✅ Performant under load
- ✅ Error-resilient
- ✅ Production-ready

---

**Testing Status**: ⏳ **Awaiting Manual Testing**
**Last Updated**: December 6, 2025
**Next Steps**: Execute tests and document results
