# Semantic Cache UI Components

**Created**: November 22, 2025
**Phase**: 3.3 - Semantic Caching UI Components
**Status**: Complete

---

## Overview

The Semantic Cache UI provides comprehensive visibility and control over Database Guru's intelligent caching system. Users can monitor cache performance, view cached queries, and manage cache lifecycle through an intuitive dashboard.

### Key Features

- **Real-time Statistics** - Monitor hit rates, lookup counts, and cache entries
- **Cache Management** - Clear semantic, LLM, or all caches with one click
- **Query Browser** - View and explore cached queries with expandable SQL
- **Inline Indicators** - See cache hit badges directly on query results
- **Performance Insights** - Track estimated time savings and efficiency

---

## Component Architecture

```
App.tsx
└── SemanticCachePanel (5th tab - amber theme)
    ├── Tab Navigation
    │   ├── Overview (default)
    │   ├── Statistics
    │   └── Recent Queries
    ├── CacheOverview
    │   ├── Stats Cards (4)
    │   ├── Cache Breakdown (2 panels)
    │   ├── Embedding Service Status
    │   ├── How It Works Section
    │   └── Quick Actions
    ├── CacheStatistics
    │   ├── Hit Type Distribution
    │   ├── LLM Cache Stats
    │   ├── Embedding Efficiency
    │   └── Performance Impact
    └── RecentCachedQueries
        ├── Query List
        ├── Expandable SQL
        ├── Pagination
        └── Page Size Selector

QueryResults.tsx
└── Cache Badge (inline indicator)
    ├── Exact Hit (green)
    └── Semantic Hit (amber + similarity %)
```

---

## Components

### 1. SemanticCachePanel

**File**: `frontend/src/components/SemanticCachePanel.tsx`
**Lines**: ~110

Main container component with tabbed navigation.

```typescript
import { SemanticCachePanel } from './components/SemanticCachePanel';

// Usage in App.tsx
{activeTab === 'cache' && <SemanticCachePanel />}
```

**Features**:
- Three-tab navigation (Overview, Statistics, Recent)
- Amber border indicator for active tab
- Lazy loads child components based on active tab

**Props**: None (self-contained)

---

### 2. CacheOverview

**File**: `frontend/src/components/CacheOverview.tsx`
**Lines**: ~370

Summary dashboard with stats, breakdown, and quick actions.

```typescript
import { CacheOverview } from './components/CacheOverview';

<CacheOverview />
```

**Sections**:

| Section | Description |
|---------|-------------|
| **Stats Cards** | 4 gradient cards: Total Lookups, Hit Rate, Semantic Hits, Cached Entries |
| **Cache Breakdown** | Side-by-side panels for Semantic Cache and LLM Cache details |
| **Embedding Service** | Status grid showing requests, hits, rate, Ollama calls, online status |
| **How It Works** | 3-step explanation of the caching flow |
| **Quick Actions** | Clear cache buttons with confirmation dialogs |

**State**:
- `stats`: Cache statistics from API
- `loading`: Loading state
- `error`: Error message
- `clearing`: Which cache is being cleared

**API Calls**:
- `cacheAPI.getStats()` - Load statistics
- `cacheAPI.clearSemanticCache()` - Clear semantic cache
- `cacheAPI.clearLLMCache()` - Clear LLM cache
- `cacheAPI.clearAllCaches()` - Clear all caches

---

### 3. CacheStatistics

**File**: `frontend/src/components/CacheStatistics.tsx`
**Lines**: ~270

Detailed statistics with distribution charts and metrics.

```typescript
import { CacheStatistics } from './components/CacheStatistics';

<CacheStatistics />
```

**Sections**:

| Section | Description |
|---------|-------------|
| **Hit Type Distribution** | Progress bars showing exact hits, semantic hits, and misses |
| **LLM Response Cache** | Lookups, hits, hit rate, misses with progress bar |
| **Embedding Service Efficiency** | Requests, cache hits, Ollama calls, TF-IDF fallbacks |
| **Performance Impact** | Estimated queries accelerated and time saved |

**Visual Elements**:
- Horizontal progress bars with percentage labels
- Color-coded sections (green for hits, blue for semantic, gray for misses)
- Refresh button for manual data reload

---

### 4. RecentCachedQueries

**File**: `frontend/src/components/RecentCachedQueries.tsx`
**Lines**: ~230

Browsable list of cached queries with expandable SQL.

```typescript
import { RecentCachedQueries } from './components/RecentCachedQueries';

<RecentCachedQueries />
```

**Features**:

| Feature | Description |
|---------|-------------|
| **Query List** | Cards showing question, database type, connection, timestamp |
| **Database Badges** | Color-coded badges (PostgreSQL=blue, MySQL=orange, SQLite=green, DuckDB=yellow) |
| **Hit Counter** | Shows how many times each cached query was hit |
| **Expandable SQL** | Click "View SQL" to expand and see the cached SQL |
| **Pagination** | Page size selector (10/25/50 per page) |
| **Refresh** | Manual refresh button |

**State**:
- `data`: Recent queries response
- `loading`: Loading state
- `error`: Error message
- `expandedQuery`: Currently expanded query (by question)
- `limit`: Page size (10/25/50)

**Helper Functions**:
- `formatDate(dateString)` - Format ISO date to locale string
- `formatTimeAgo(dateString)` - Convert to relative time (e.g., "2h ago")

---

### 5. QueryResults Cache Badge

**File**: `frontend/src/components/QueryResults.tsx`
**Lines**: ~45 (badge section)

Inline cache hit indicator displayed above query results.

```typescript
interface QueryResultsProps {
  // ... existing props
  cacheType?: 'exact' | 'semantic' | null;
  semanticSimilarity?: number | null;
  matchedQuestion?: string | null;
}
```

**Badge Variants**:

| Type | Color | Content |
|------|-------|---------|
| **Exact Hit** | Green (`bg-green-50`) | "Exact Cache Hit" + "Instant Response" badge |
| **Semantic Hit** | Amber (`bg-amber-50`) | "Semantic Cache Hit" + "(X% match)" + matched question |

**Visual Design**:
```
┌─────────────────────────────────────────────────────────┐
│ [Database Icon] Exact Cache Hit          Instant Response│
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ [Zap Icon] Semantic Cache Hit (92% match) Instant Response│
│ Matched: "Show customers in California"                  │
└─────────────────────────────────────────────────────────┘
```

---

## API Service

**File**: `frontend/src/services/cacheApi.ts`
**Lines**: ~150

TypeScript API client for cache endpoints.

### Types

```typescript
// Cache statistics response
interface CacheStatsResponse {
  semantic_cache: {
    total_lookups: number;
    total_hits: number;
    exact_hits: number;
    semantic_hits: number;
    misses: number;
    hit_rate_percent: number;
    semantic_hit_rate_percent: number;
    total_stores: number;
    similarity_threshold: number;
    ttl_seconds: number;
    memory_entries: number;
  };
  llm_cache: {
    total_lookups: number;
    hits: number;
    misses: number;
    hit_rate_percent: number;
    total_stores: number;
    similarity_threshold: number;
    ttl_seconds: number;
  };
  embedding_service: {
    total_requests: number;
    cache_hits: number;
    cache_hit_rate_percent: number;
    ollama_calls: number;
    tfidf_fallbacks: number;
    ollama_available: boolean;
  };
}

// Recent queries response
interface RecentQueriesResponse {
  queries: CachedQueryResponse[];
  total: number;
}

interface CachedQueryResponse {
  question: string;
  sql: string;
  connection_id: number;
  database_type: string;
  created_at: string;
  hits: number;
  last_hit_at: string | null;
}

// Clear cache response
interface ClearCacheResponse {
  message: string;
  entries_cleared: number;
}
```

### Methods

```typescript
const cacheAPI = {
  // Get combined cache statistics
  async getStats(): Promise<CacheStatsResponse>

  // Get recent cached queries
  async getRecentQueries(filters?: {
    limit?: number;
    offset?: number;
    connection_id?: number;
  }): Promise<RecentQueriesResponse>

  // Clear semantic query cache
  async clearSemanticCache(): Promise<ClearCacheResponse>

  // Clear LLM response cache
  async clearLLMCache(): Promise<ClearCacheResponse>

  // Clear all caches
  async clearAllCaches(): Promise<ClearCacheResponse>

  // Clear cache for specific connection
  async clearConnectionCache(connectionId: number): Promise<ClearCacheResponse>
};
```

---

## Backend API Endpoints

**File**: `src/api/endpoints/cache.py`
**Lines**: ~260

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/cache/stats` | GET | Get combined statistics for all caches |
| `/api/cache/recent` | GET | Get recent cached queries with pagination |
| `/api/cache/semantic` | DELETE | Clear semantic query cache |
| `/api/cache/llm` | DELETE | Clear LLM response cache |
| `/api/cache/all` | DELETE | Clear all caches |
| `/api/cache/connection/{id}` | DELETE | Clear cache for specific connection |

### Example Requests

```bash
# Get cache statistics
curl http://localhost:8000/api/cache/stats

# Get recent queries (with pagination)
curl "http://localhost:8000/api/cache/recent?limit=20&offset=0"

# Get recent queries for specific connection
curl "http://localhost:8000/api/cache/recent?connection_id=1"

# Clear semantic cache
curl -X DELETE http://localhost:8000/api/cache/semantic

# Clear LLM cache
curl -X DELETE http://localhost:8000/api/cache/llm

# Clear all caches
curl -X DELETE http://localhost:8000/api/cache/all

# Clear cache for connection #1
curl -X DELETE http://localhost:8000/api/cache/connection/1
```

### Example Response

```json
// GET /api/cache/stats
{
  "semantic_cache": {
    "total_lookups": 100,
    "total_hits": 50,
    "exact_hits": 20,
    "semantic_hits": 30,
    "misses": 50,
    "hit_rate_percent": 50.0,
    "semantic_hit_rate_percent": 30.0,
    "total_stores": 60,
    "similarity_threshold": 0.85,
    "ttl_seconds": 86400,
    "memory_entries": 25
  },
  "llm_cache": {
    "total_lookups": 80,
    "hits": 45,
    "misses": 35,
    "hit_rate_percent": 56.25,
    "total_stores": 50,
    "similarity_threshold": 0.88,
    "ttl_seconds": 43200
  },
  "embedding_service": {
    "total_requests": 200,
    "cache_hits": 150,
    "cache_hit_rate_percent": 75.0,
    "ollama_calls": 40,
    "tfidf_fallbacks": 10,
    "ollama_available": true
  }
}
```

---

## Color Scheme

The Cache UI uses an **amber/gold** color scheme to distinguish it from other features:

| Element | Color Class | Hex |
|---------|-------------|-----|
| Tab border (active) | `border-amber-500` | #f59e0b |
| Tab text (active) | `text-amber-600` | #d97706 |
| Primary buttons | `bg-amber-500` | #f59e0b |
| Stat card gradient | `from-amber-50 to-amber-100` | - |
| Semantic hit badge | `bg-amber-50 border-amber-200` | - |
| Exact hit badge | `bg-green-50 border-green-200` | - |

---

## Testing

### Frontend Tests

**File**: `frontend/tests/SemanticCachePanel.test.tsx`
**Tests**: 34 passing

| Test Suite | Tests | Coverage |
|------------|-------|----------|
| SemanticCachePanel | 6 | Tab rendering, navigation, default state |
| CacheOverview | 9 | Stats display, loading, error, clear actions |
| CacheStatistics | 6 | Distribution, LLM stats, embedding efficiency |
| RecentCachedQueries | 8 | Query list, expand SQL, pagination, empty state |
| QueryResults Cache Badge | 5 | Exact/semantic badges, styling, similarity display |

### Backend Tests

**File**: `tests/test_cache_endpoints.py`
**Tests**: 9 passing

| Test | Description |
|------|-------------|
| `test_get_cache_stats` | Returns combined statistics |
| `test_get_recent_queries` | Returns paginated query list |
| `test_get_recent_queries_with_limit` | Pagination works correctly |
| `test_clear_semantic_cache` | Clears semantic cache |
| `test_clear_llm_cache` | Clears LLM cache |
| `test_clear_all_caches` | Clears all caches |
| `test_clear_connection_cache` | Clears specific connection |
| `test_stats_empty_cache` | Handles empty cache gracefully |
| `test_recent_empty` | Returns empty list when no queries |

### Running Tests

```bash
# Frontend tests
cd frontend
npm test -- --run tests/SemanticCachePanel.test.tsx

# Backend tests
cd ..
source venv/bin/activate
python -m pytest tests/test_cache_endpoints.py -v
```

---

## Integration with Query Flow

The cache badge integrates with the query execution flow:

```
1. User submits question
   ↓
2. Backend checks caches (exact → semantic → LLM)
   ↓
3. If cache hit, response includes:
   - cache_type: "exact" | "semantic"
   - semantic_similarity: 0.85-1.0 (if semantic)
   - matched_question: "original cached question" (if semantic)
   ↓
4. Frontend QueryResults renders badge:
   - Green badge for exact hits
   - Amber badge for semantic hits with similarity %
   ↓
5. User sees instant response with cache indicator
```

---

## Files Summary

| File | Type | Lines | Description |
|------|------|-------|-------------|
| `src/api/endpoints/cache.py` | Backend | ~260 | API endpoints |
| `frontend/src/components/SemanticCachePanel.tsx` | Frontend | ~110 | Main container |
| `frontend/src/components/CacheOverview.tsx` | Frontend | ~370 | Stats dashboard |
| `frontend/src/components/CacheStatistics.tsx` | Frontend | ~270 | Distribution charts |
| `frontend/src/components/RecentCachedQueries.tsx` | Frontend | ~230 | Query browser |
| `frontend/src/components/QueryResults.tsx` | Frontend | +45 | Cache badge addition |
| `frontend/src/services/cacheApi.ts` | Frontend | ~150 | API service |
| `tests/test_cache_endpoints.py` | Backend Test | ~280 | 9 tests |
| `frontend/tests/SemanticCachePanel.test.tsx` | Frontend Test | ~430 | 34 tests |

**Total**: ~2,100 lines of new code

---

## Related Documentation

- [Semantic Caching Guide](SEMANTIC_CACHING.md) - Backend caching implementation
- [Tool-Using Agent Guide](TOOL_USING_AGENT.md) - Similar UI pattern reference
- [Future Plans](FUTURE_PLANS.md) - Phase 3.3 completion details

---

## Changelog

### November 22, 2025 - Initial Release
- Created SemanticCachePanel with 3 tabs
- Implemented CacheOverview with stats and actions
- Implemented CacheStatistics with distribution charts
- Implemented RecentCachedQueries with SQL expand
- Added inline cache badge to QueryResults
- Created cacheApi.ts service layer
- Added Cache tab to App.tsx (5th tab)
- 6 backend API endpoints
- 43 tests (9 backend + 34 frontend)
