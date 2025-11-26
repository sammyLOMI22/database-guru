# Changelog

All notable changes to Database Guru are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Cache Trace Integration** - Cache operations now appear in Agent Execution Trace
  - Cache lookup, hit/miss, and store steps visible in trace timeline
  - Per-database cache status in multi-query results
  - Visual cache indicators with custom icons (⚡ hit, 🔍 miss, 💾 store, 🗄️ lookup)
  - Cache info banner in multi-database results showing hit/miss summary
- **Enhanced Connection Management UI**
  - Edit button for modifying existing database connections
  - Loading spinner overlay during connection save operations
  - Selected connection highlighting with blue border
  - Database icon in header status indicator
- **Conversational Memory Toggle**
  - Show/hide button for conversation context panel
  - Active context indicator with toggle control
  - Improved UX for multi-turn conversations
- **Cache Setup Documentation** - Comprehensive guide for Redis and Ollama setup
  - Local installation instructions (Homebrew)
  - Docker setup with examples
  - Docker Compose configuration
  - Troubleshooting guide
  - Recommended models table
- **Automated Setup Scripts** - Helper scripts for easy cache setup
  - `./scripts/setup_cache.sh` - Complete automated setup (Redis + Ollama + Models)
  - `./scripts/setup_redis.sh` - Interactive Redis setup and startup
  - `./scripts/setup_ollama.sh` - Interactive Ollama + model installation
  - Auto-detection of installed components
  - Service management (background vs foreground)
- **Complete Stack Startup Scripts** - One-command startup for entire stack
  - `./start_all.sh` - Start Redis + Ollama + Backend + Frontend with one command
  - `./stop_all.sh` - Stop all services gracefully
  - Smart service tracking (only stops services started by script)
  - Existing `./start.sh` remains for application-only startup

### Fixed
- **Agent Execution Trace Crashes** - Added defensive rendering to prevent blank pages
  - Null checks for trace data and steps
  - Fallback values for missing properties
  - Support for alternative property names (`total_elapsed_ms` vs `total_duration_ms`)
  - Graceful handling of missing metadata
- **TypeScript Build Warnings** - Resolved all unused variable warnings
  - Implemented unused code (edit connections, context toggle, loading states)
  - Removed commented-out imports
  - Clean TypeScript compilation
- **Backend Cache Trace Data** - Ensured consistent trace structure
  - Added `elapsed_ms` to all cache trace steps
  - Standardized on `total_elapsed_ms` property name
  - Fixed cache miss step metadata

### Changed
- **Multi-Database Query Results** - Enhanced cache visibility
  - Added `CacheInfo` to response payload
  - Cache info banner shows semantic hits, misses, and stored counts
  - Per-database cache status in agent trace
- **Agent Trace Component** - Improved cache step styling
  - Amber badges for cache hits
  - Slate badges for cache misses
  - Teal badges for cache stores
  - Custom icons for each cache operation type
- **README.md** - Updated with recent changes
  - Added cache trace integration documentation
  - Updated prerequisites to mention Redis (optional)
  - Enhanced configuration section with Redis and cache settings
  - Added cache setup guide link
  - Documented recent UI improvements

## [2.0.0] - 2025-11-25

### Major Features
- **Semantic Caching** - 30-50% higher cache hit rates with similarity matching
- **Semantic Cache Dashboard** - Full UI for cache monitoring and management
- **Tool-Using Agent** - 10 specialized tools for schema exploration
- **Parallel Multi-Database Execution** - 3x speedup with intelligent throttling
- **Parallel Correction Strategies** - 1.6x faster error recovery
- **Production-Grade Security** - Multi-layer prompt injection protection

### Backend Improvements
- Embedding service with Ollama or TF-IDF fallback
- Schema fingerprinting for cache invalidation
- Conditional result verification for performance
- Dual timeout protection for parallel operations
- Comprehensive metrics tracking

### Frontend Enhancements
- Tools tab with overview, directory, and usage stats
- Cache tab with overview, statistics, and recent queries
- Parallel execution metrics visualization
- Inline cache hit badges in query results

See individual feature guides in `docs/` for complete documentation.

---

## Version History

### Phase 3.3 - Semantic Cache UI (November 22, 2025)
- Semantic Cache Dashboard with 3 tabs
- Cache statistics visualization
- Recent cached queries browser
- Inline cache badges in results
- 34 frontend tests, 9 backend tests

### Phase 3.2 - Semantic Caching Backend (November 22, 2025)
- Embedding service implementation
- Semantic cache with similarity matching
- LLM response caching
- Schema fingerprinting
- 20 comprehensive backend tests

### Phase 3.1 - Tool-Using Agent (November 21, 2025)
- 10 specialized tools (schema, data, query, validation)
- Tool registry with caching
- Tools UI dashboard
- 26 backend tests, 30 frontend tests

### Phase 2 - Production Features (November 8, 2025)
- Parallel multi-database execution (3x speedup)
- Parallel correction strategies (1.6x speedup)
- 71 tests verifying production readiness
- Comprehensive metrics and observability

### Phase 1 - Conversational Memory (November 2, 2025)
- Multi-turn conversation support
- Context-aware query generation
- Prompt injection protection
- 44 tests including 29 security tests

---

## Upgrade Notes

### Upgrading to Latest
No breaking changes. New features are opt-in or have sensible defaults.

**Optional: Enable Redis for persistent caching**
```bash
brew services start redis
```
Without Redis, semantic cache uses in-memory fallback.

**Optional: Pull embedding model for better similarity**
```bash
ollama pull nomic-embed-text
```
Without embedding model, semantic cache uses TF-IDF fallback.

See [Cache Setup Guide](docs/CACHE_SETUP.md) for detailed instructions.
