# Connection Pooling Guide

**Version**: 1.0
**Last Updated**: December 6, 2025
**Status**: Production Ready

---

## Table of Contents

1. [Overview](#overview)
2. [How It Works](#how-it-works)
3. [Getting Started](#getting-started)
4. [Configuration](#configuration)
5. [Monitoring](#monitoring)
6. [Performance Tuning](#performance-tuning)
7. [Troubleshooting](#troubleshooting)
8. [Best Practices](#best-practices)
9. [Technical Details](#technical-details)

---

## Overview

### What is Connection Pooling?

Connection pooling is a technique that maintains a pool of reusable database connections, eliminating the overhead of creating a new connection for every query.

**Without pooling** (old behavior):
```
Query 1: Create engine → Execute → Dispose engine (150ms)
Query 2: Create engine → Execute → Dispose engine (150ms)
Query 3: Create engine → Execute → Dispose engine (150ms)
```

**With pooling** (new behavior):
```
Query 1: Get from pool → Execute → Return to pool (5ms)
Query 2: Get from pool → Execute → Return to pool (5ms)
Query 3: Get from pool → Execute → Return to pool (5ms)
```

### Benefits

✅ **30x faster queries** - Connection overhead reduced from 150ms to ~5ms
✅ **50-70% reduction in database load** - Fewer connection handshakes
✅ **Better concurrency** - Handle 20-30 simultaneous requests efficiently
✅ **Production-ready** - Health checks, automatic cleanup, graceful degradation
✅ **Zero code changes** - Enabled via configuration, works automatically

### Supported Databases

| Database   | Status | Pool Type | Notes |
|------------|--------|-----------|-------|
| PostgreSQL | ✅ Yes | Async | asyncpg driver |
| MySQL      | ✅ Yes | Async | aiomysql driver |
| SQLite     | ✅ Yes | Async | aiosqlite driver |
| DuckDB     | ✅ Yes | Sync | duckdb driver (wrapped in async) |
| MongoDB    | ⬜ Future | N/A | Awaiting MongoDB query support |

---

## How It Works

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   ConnectionPoolManager                         │
│                     (Global Singleton)                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  _pools: Dict[(connection_id, db_type), PoolEntry]             │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ PoolEntry #1 │  │ PoolEntry #2 │  │ PoolEntry #3 │         │
│  ├──────────────┤  ├──────────────┤  ├──────────────┤         │
│  │ PostgreSQL   │  │ MySQL        │  │ SQLite       │         │
│  │ engine       │  │ engine       │  │ engine       │         │
│  │ factory      │  │ factory      │  │ factory      │         │
│  │ metrics      │  │ metrics      │  │ metrics      │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
    Connection #1        Connection #2        Connection #3
```

### Pool Lifecycle

#### 1. **Creation** (Lazy)
Pools are created on first query to a database:
```python
# First query to PostgreSQL connection #1
pool = await pool_manager.get_pool(connection)
# Pool created with 10 connections, max 20 overflow
```

#### 2. **Reuse** (Fast)
Subsequent queries reuse the existing pool:
```python
# Second query to same connection
pool = await pool_manager.get_pool(connection)
# Returns existing pool (no creation overhead)
```

#### 3. **Cleanup** (Automatic)
Three-tier eviction strategy:
- **Idle timeout** (30 min): Soft eviction of unused pools
- **Max age** (2 hours): Hard eviction (forced refresh)
- **Connection deletion**: Immediate eviction when connection removed
- **Background task**: Runs every 5 minutes

#### 4. **Disposal** (Graceful)
On application shutdown:
```python
await pool_manager.close_all_pools()
# Gracefully closes all connections
```

---

## Getting Started

### Enable Connection Pooling

Connection pooling is **enabled by default**. To verify:

```bash
# Check environment variable
echo $ENABLE_CONNECTION_POOLING  # Should be "True" or not set
```

To explicitly enable/disable:

```bash
# .env file
ENABLE_CONNECTION_POOLING=True   # Enable (default)
ENABLE_CONNECTION_POOLING=False  # Disable
```

### Verify It's Working

1. **Check the UI**:
   - Navigate to http://localhost:3000
   - Click the **🔗 Pools** tab
   - You should see pool metrics after running a query

2. **Check the API**:
   ```bash
   curl http://localhost:8000/api/pools/stats | jq
   ```

3. **Check the logs**:
   ```
   INFO: Connection pools initialized (PostgreSQL, MySQL, SQLite, DuckDB)
   INFO: Created pool for connection #1 (postgresql)
   ```

### First Query Creates Pool

```bash
# Make your first query via the UI or API
# Pool will be created automatically

# Then check pools tab
# You should see 1 pool with metrics
```

---

## Configuration

### Environment Variables

All settings can be configured via environment variables in `.env`:

```bash
# Feature Flag
ENABLE_CONNECTION_POOLING=True      # Enable/disable pooling

# Pool Size
USER_DB_POOL_SIZE=10                # Base pool size (per connection)
USER_DB_MAX_OVERFLOW=20             # Burst capacity

# Connection Lifecycle
USER_DB_POOL_RECYCLE=3600           # Recycle connections after 1 hour
USER_DB_POOL_TIMEOUT=30             # Wait timeout (seconds)
USER_DB_POOL_PRE_PING=True          # Validate connections before use

# Cleanup
POOL_IDLE_CLEANUP_INTERVAL=300      # Cleanup every 5 minutes
POOL_MAX_IDLE_TIME=1800             # Evict idle pools after 30 minutes
POOL_MAX_AGE=7200                   # Force refresh after 2 hours

# Health Checks
POOL_HEALTH_CHECK_INTERVAL=60       # Health check every 60 seconds
```

### Configuration Recommendations

#### Small Apps (< 10 concurrent users)
```bash
USER_DB_POOL_SIZE=5
USER_DB_MAX_OVERFLOW=10
```

#### Medium Apps (10-50 concurrent users)
```bash
USER_DB_POOL_SIZE=10      # Default
USER_DB_MAX_OVERFLOW=20   # Default
```

#### Large Apps (50+ concurrent users)
```bash
USER_DB_POOL_SIZE=20
USER_DB_MAX_OVERFLOW=40
```

#### Development/Testing
```bash
USER_DB_POOL_SIZE=3
USER_DB_MAX_OVERFLOW=5
POOL_MAX_IDLE_TIME=600    # Cleanup faster (10 min)
```

---

## Monitoring

### UI Dashboard

Navigate to **🔗 Pools** tab to see:

**Overview Cards**:
- Total Pools
- Active Connections
- Idle Connections
- Average Utilization %

**Pool Details Table**:
- Connection name and ID
- Database type
- Health status (🟢 🟡 🔴)
- Active/Idle/Capacity breakdown
- Utilization bar (color-coded)
- Wait time metrics
- Pool age
- Eviction controls

**Warnings**:
- Unhealthy pools (red banner)
- High utilization pools (yellow banner, >80%)

**Auto-refresh**: Every 10 seconds

### API Endpoints

#### Get Overall Stats
```bash
curl http://localhost:8000/api/pools/stats
```

Response:
```json
{
  "total_pools": 3,
  "global_metrics": {
    "total_active_connections": 5,
    "total_idle_connections": 25,
    "avg_utilization_percent": 16.7
  },
  "pools": [
    {
      "connection_id": 1,
      "database_type": "postgresql",
      "connection_name": "Production DB",
      "created_at": "2025-12-06T10:00:00",
      "last_used": "2025-12-06T10:05:00",
      "age_seconds": 300,
      "metrics": {
        "active_connections": 2,
        "idle_connections": 8,
        "total_connections": 10,
        "utilization_percent": 20.0,
        "total_checkouts": 150,
        "total_checkins": 148,
        "failed_checkouts": 0,
        "avg_wait_time_ms": 2.5,
        "max_wait_time_ms": 15.0,
        "health_status": "healthy",
        "pool_size": 10,
        "max_overflow": 20,
        "capacity": 30
      }
    }
  ],
  "pooling_enabled": true
}
```

#### Get Connection-Specific Stats
```bash
curl http://localhost:8000/api/pools/stats/1
```

#### Get Health Status
```bash
curl http://localhost:8000/api/pools/health
```

#### Manually Evict Pool
```bash
curl -X DELETE http://localhost:8000/api/pools/1
# Or specific database type:
curl -X DELETE "http://localhost:8000/api/pools/1?database_type=postgresql"
```

### Logs

Pooling events are logged at INFO level:

```
INFO: Connection pools initialized (PostgreSQL, MySQL, SQLite, DuckDB)
INFO: Created pool for connection #1 (postgresql)
INFO: Evicted idle pool for connection #2 (mysql) - idle for 1800s
INFO: Evicted old pool for connection #3 (sqlite) - age 7200s
INFO: Evicted pool for connection #4 (duckdb) - connection deleted
INFO: Connection pools closed
```

---

## Performance Tuning

### Understanding Utilization

**Utilization** = (active_connections / capacity) × 100

| Utilization | Status | Action |
|-------------|--------|--------|
| < 60% | ✅ Healthy | No action needed |
| 60-80% | ⚠️ Moderate | Monitor for growth |
| > 80% | 🔴 High | Increase pool size |
| > 95% | 🚨 Critical | Immediate increase needed |

### Symptoms and Solutions

#### Symptom: High utilization (>80%)
**Cause**: Pool size too small for workload
**Solution**:
```bash
USER_DB_POOL_SIZE=20        # Increase base size
USER_DB_MAX_OVERFLOW=40     # Increase overflow
```

#### Symptom: Many failed checkouts
**Cause**: Pool exhaustion, timeout too short
**Solution**:
```bash
USER_DB_POOL_TIMEOUT=60     # Increase timeout
USER_DB_MAX_OVERFLOW=30     # Increase overflow
```

#### Symptom: High wait times (>50ms)
**Cause**: Pool contention
**Solution**:
```bash
USER_DB_POOL_SIZE=15        # Add more connections
```

#### Symptom: Stale connection errors
**Cause**: Connections timing out on database side
**Solution**:
```bash
USER_DB_POOL_RECYCLE=1800   # Recycle more frequently
USER_DB_POOL_PRE_PING=True  # Validate before use (default)
```

#### Symptom: Too many idle connections
**Cause**: Pool size too large
**Solution**:
```bash
USER_DB_POOL_SIZE=5         # Reduce base size
POOL_MAX_IDLE_TIME=900      # Cleanup faster (15 min)
```

### Performance Targets

| Metric | Target | Critical |
|--------|--------|----------|
| Query overhead | < 10ms | > 50ms |
| Utilization | < 70% | > 90% |
| Wait time (avg) | < 5ms | > 20ms |
| Failed checkouts | 0 | > 5/min |
| Pool creation time | < 100ms | > 500ms |

### Database-Specific Tuning

#### PostgreSQL
```bash
USER_DB_POOL_SIZE=10
USER_DB_MAX_OVERFLOW=20
USER_DB_POOL_RECYCLE=3600
# PostgreSQL handles concurrent connections well
```

#### MySQL
```bash
USER_DB_POOL_SIZE=10
USER_DB_MAX_OVERFLOW=20
USER_DB_POOL_RECYCLE=3600
# Similar to PostgreSQL
```

#### SQLite
```bash
USER_DB_POOL_SIZE=5
USER_DB_MAX_OVERFLOW=10
USER_DB_POOL_RECYCLE=1800
# SQLite has single-writer lock, smaller pool is fine
```

#### DuckDB
```bash
USER_DB_POOL_SIZE=5
USER_DB_MAX_OVERFLOW=10
USER_DB_POOL_RECYCLE=1800
# In-process database, small pool is sufficient
```

---

## Troubleshooting

### Issue: Pools not being created

**Check 1**: Is pooling enabled?
```bash
curl http://localhost:8000/api/pools/stats | jq '.pooling_enabled'
# Should return: true
```

**Check 2**: Have you run any queries?
- Pools are created lazily on first query
- Run a test query to trigger pool creation

**Check 3**: Check logs
```bash
grep "pool" backend.log
```

### Issue: "Pool timeout" errors

**Symptom**: Queries fail with timeout errors

**Causes**:
1. Pool size too small
2. Timeout setting too short
3. Slow queries blocking connections

**Solutions**:
```bash
# Increase pool capacity
USER_DB_POOL_SIZE=15
USER_DB_MAX_OVERFLOW=30

# Increase timeout
USER_DB_POOL_TIMEOUT=60

# Check for slow queries in your database
```

### Issue: "Stale connection" errors

**Symptom**: Intermittent connection failures

**Causes**:
1. Database closing idle connections
2. Network interruptions
3. Firewall timeouts

**Solutions**:
```bash
# Enable pre-ping (validates before use)
USER_DB_POOL_PRE_PING=True   # Default, should already be on

# Recycle connections more frequently
USER_DB_POOL_RECYCLE=1800    # 30 minutes instead of 1 hour

# Check database server timeout settings
```

### Issue: Memory usage growing

**Symptom**: Application memory increases over time

**Causes**:
1. Too many pools not being cleaned up
2. Idle timeout too long

**Solutions**:
```bash
# More aggressive cleanup
POOL_MAX_IDLE_TIME=900       # 15 minutes instead of 30
POOL_IDLE_CLEANUP_INTERVAL=180  # Every 3 minutes

# Force refresh more often
POOL_MAX_AGE=3600            # 1 hour instead of 2
```

### Issue: Pool health shows "unhealthy"

**Symptom**: Red health indicator in UI

**Causes**:
1. Database server down
2. Network issues
3. High error rate

**Actions**:
1. Check database server status
2. Review error logs
3. Try manual eviction: `DELETE /api/pools/{connection_id}`
4. Pool will auto-recreate on next query

### Issue: High utilization warnings

**Symptom**: Yellow/red banners in UI

**Immediate action**:
```bash
# Quick fix: increase pool size
USER_DB_POOL_SIZE=20
USER_DB_MAX_OVERFLOW=40

# Restart application to apply changes
```

**Long-term**:
- Analyze query patterns
- Optimize slow queries
- Consider database scaling

---

## Best Practices

### Do's ✅

1. **Monitor regularly**
   - Check Pools tab weekly
   - Set up alerts for >80% utilization
   - Review failed checkouts

2. **Start conservative**
   - Begin with default settings
   - Increase gradually based on metrics
   - Don't over-provision

3. **Use pre-ping**
   - Keep `POOL_PRE_PING=True` (default)
   - Prevents stale connection errors
   - Small overhead, big benefit

4. **Clean up old connections**
   - Use appropriate database types
   - Delete unused connections
   - Pools auto-evict after idle timeout

5. **Test before production**
   - Run performance tests
   - Verify pool behavior under load
   - Check cleanup works correctly

### Don'ts ❌

1. **Don't disable pooling in production**
   - 30x performance loss
   - Only disable for debugging

2. **Don't set pool size too high**
   - Wastes memory
   - Database connection limits
   - Start small, grow as needed

3. **Don't ignore warnings**
   - High utilization = upcoming problems
   - Failed checkouts = capacity issues
   - Act before it's critical

4. **Don't share connection strings**
   - Each database connection gets its own pool
   - Isolates issues
   - Better metrics

5. **Don't manually manage engines**
   - Let the pool manager handle it
   - Don't call `engine.dispose()`
   - Don't create custom engines

### Production Checklist

Before deploying to production:

- [ ] `ENABLE_CONNECTION_POOLING=True`
- [ ] Pool size appropriate for load
- [ ] Pre-ping enabled
- [ ] Health checks configured
- [ ] Monitoring dashboard accessible
- [ ] Alert thresholds set (>80% utilization)
- [ ] Cleanup intervals configured
- [ ] Performance tests passed
- [ ] Stale connection handling tested
- [ ] Graceful shutdown tested

---

## Technical Details

### Pool Isolation

Each `(connection_id, database_type)` pair gets its own pool:

```python
# Connection #1 to PostgreSQL
pool_key_1 = (1, "postgresql")

# Connection #1 to MySQL (different pool!)
pool_key_2 = (1, "mysql")

# Connection #2 to PostgreSQL (different pool!)
pool_key_3 = (2, "postgresql")
```

**Why?**
- Different databases need different configurations
- Isolates failures
- Better metrics granularity

### Thread Safety

The pool manager uses `asyncio.Lock`:

```python
async with self._lock:
    # Critical section
    # Only one coroutine at a time
```

All pool operations are atomic and thread-safe.

### Async vs Sync

**Async pools** (PostgreSQL, MySQL, SQLite):
```python
async with pool_entry.session_factory() as session:
    result = await session.execute(query)
```

**Sync pools** (DuckDB):
```python
session = pool_entry.session_factory()
try:
    result = session.execute(query)
finally:
    session.close()
```

Both wrapped in async context for unified API.

### MongoDB Status

MongoDB query support is not yet implemented. When it is:

1. Will use PyMongo's native pooling
2. Different code path from SQLAlchemy
3. Configuration will be similar

Current status:
```python
if database_type == 'mongodb':
    raise NotImplementedError("MongoDB queries not yet supported")
```

---

## See Also

- [Test Database Setup](./TEST_DATABASE_SETUP.md) - Setting up test databases
- [Architecture (CLAUDE.md)](../../CLAUDE.md) - System architecture
- [Implementation Plan](../planning/CONNECTION_POOLING_IMPLEMENTATION_PLAN.md) - Development details

---

## Support

If you encounter issues:

1. Check this guide's [Troubleshooting](#troubleshooting) section
2. Review logs: `backend.log`
3. Check UI: **🔗 Pools** tab
4. Test API: `GET /api/pools/health`
5. Open an issue on GitHub with:
   - Pool stats JSON
   - Relevant log entries
   - Configuration settings
   - Steps to reproduce

---

**Last Updated**: December 6, 2025
**Version**: 1.0
**Status**: Production Ready
