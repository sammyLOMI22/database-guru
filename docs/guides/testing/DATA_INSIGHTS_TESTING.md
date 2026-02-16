# Data Insights Enhancement Testing Guide (Phase 19)

This guide covers how to verify that all Phase 19 features work correctly.

## Overview

Phase 19 adds 5 sub-features with comprehensive test coverage:

| Sub-phase | Feature | Test File | Tests |
|-----------|---------|-----------|-------|
| 19.1 | Tiered Narrative Prompts | `tests/test_narrative_tiers.py` | 31 |
| 19.2 | Analytics Caching | `tests/test_analytics_cache.py` | 21 |
| 19.3 | Multi-Source Quality Insights | `tests/test_multi_source_insights.py` | 24 |
| 19.4 | Chart Intelligence Enhancements | `frontend/tests/chartIntelligenceEnhancements.test.ts` | 16 |
| 19.5 | Parallel Analysis Pipeline | `tests/test_parallel_analysis.py` | 16 |
| **Total** | | | **108** |

## Running Tests

### Run All Phase 19 Backend Tests

```bash
source venv/bin/activate

python -m pytest tests/test_narrative_tiers.py \
  tests/test_analytics_cache.py \
  tests/test_multi_source_insights.py \
  tests/test_parallel_analysis.py -v
```

### Run All Phase 19 Frontend Tests

```bash
cd frontend
npx vitest run tests/chartIntelligenceEnhancements.test.ts
```

### Run Individual Sub-phase Tests

```bash
# 19.1 Tiered Narrative Prompts
python -m pytest tests/test_narrative_tiers.py -v

# 19.2 Analytics Caching
python -m pytest tests/test_analytics_cache.py -v

# 19.3 Multi-Source Quality Insights
python -m pytest tests/test_multi_source_insights.py -v

# 19.5 Parallel Analysis Pipeline
python -m pytest tests/test_parallel_analysis.py -v

# 19.4 Chart Intelligence (frontend)
cd frontend && npx vitest run tests/chartIntelligenceEnhancements.test.ts
```

### Run with Coverage

```bash
python -m pytest tests/test_narrative_tiers.py \
  tests/test_analytics_cache.py \
  tests/test_multi_source_insights.py \
  tests/test_parallel_analysis.py \
  --cov=src/llm/result_narrator \
  --cov=src/llm/prompts \
  --cov=src/services/analytics_cache \
  --cov-report=html
```

---

## Phase 19.1: Tiered Narrative Prompts

### What It Does
Selects different prompt templates based on LLM model size (SMALL/MEDIUM/LARGE) to optimize token usage and narrative quality. Small models get compact prompts; large models get enhanced prompts with quality analysis.

### Key Files
- `src/llm/prompts/narrative_tiers.py` — prompt templates, token budgets, row limits
- `src/llm/result_narrator.py` — `_get_model_tier()`, `_compress_statistics()`, `_build_prompt()`

### What the Tests Verify

| Test Class | What It Checks |
|------------|----------------|
| `TestModelTierDetection` | Model names correctly map to SMALL/MEDIUM/LARGE tiers (phi3 → SMALL, mistral:7b → MEDIUM, qwen2.5:32b → LARGE, unknown → MEDIUM) |
| `TestPromptSelection` | `get_narrative_prompt()` returns correct template per tier, for both single-DB and multi-DB |
| `TestStatisticsCompression` | SMALL tier limits to 3 numeric columns with count/avg only; MEDIUM preserves all; LARGE adds range and coefficient of variation |
| `TestBuildPromptIntegration` | `_build_prompt()` uses the correct template and limits sample rows by tier |
| `TestTokenBudgets` | Token budgets and insight limits increase monotonically with tier |

### Manual Verification

1. **Tier detection**: Create a `ResultNarrator` with `model="phi3"` and confirm `_get_model_tier()` returns `ModelSize.SMALL`
2. **Prompt selection**: Call `get_narrative_prompt(ModelSize.SMALL)` and verify the prompt starts with `"Data analyst."` (compact template)
3. **Stats compression**: Pass full statistics to `_format_essential_stats()` and confirm only 3 numeric columns appear, with no `stdev`/`median`/`sum` keys

---

## Phase 19.2: Analytics Caching

### What It Does
Two-tier cache (in-memory TTLCache + optional Redis) that caches computed statistics and pattern detection results. Eliminates redundant computation when the same result set is analyzed multiple times.

### Key Files
- `src/services/analytics_cache.py` — `AnalyticsCache`, `get_analytics_cache()`
- `src/config/settings.py` — `ANALYTICS_CACHE_TTL`, `ANALYTICS_CACHE_REDIS_TTL`, `ANALYTICS_CACHE_MAXSIZE`

### What the Tests Verify

| Test Class | What It Checks |
|------------|----------------|
| `TestResultHash` | `compute_result_hash()` is deterministic, differs for different data, returns 16-char hex, handles edge cases (empty, single row, non-serializable) |
| `TestLocalCache` | Cache miss returns `None`, set-then-get works, different DB types use different keys, `get_cache_stats()` reports size |
| `TestRedisFallback` | Local cache works when Redis is unavailable, Redis errors fall back silently, Redis hits populate local cache |
| `TestNarratorIntegration` | `ResultNarrator` skips `_extract_statistics()` on cache hit, computes and caches on miss, works with `analytics_cache=None` |
| `TestSingleton` | `get_analytics_cache()` returns the same instance on repeated calls |

### Manual Verification

1. **Cache round-trip**:
   ```python
   from src.services.analytics_cache import AnalyticsCache
   cache = AnalyticsCache()
   await cache.set_statistics("abc123", "postgresql", {"row_count": 42})
   result = await cache.get_statistics("abc123", "postgresql")
   assert result == {"row_count": 42}
   ```

2. **Result hashing**:
   ```python
   h1 = AnalyticsCache.compute_result_hash([{"a": 1}])
   h2 = AnalyticsCache.compute_result_hash([{"a": 1}])
   assert h1 == h2 and len(h1) == 16
   ```

3. **Configuration**: Set `ANALYTICS_CACHE_MAXSIZE=5` in `.env` and confirm `get_analytics_cache().get_cache_stats()["local_maxsize"] == 5`

---

## Phase 19.3: Multi-Source Data Quality Insights

### What It Does
When querying multiple databases, computes per-database quality metrics (null rates, completeness, duplicates, freshness) and detects coverage gaps across databases. For large models, injects a quality summary into the LLM prompt.

### Key Files
- `src/llm/result_narrator.py` — `DataQualityMetrics`, `GapInsight`, `MultiSourceQualityReport`, `_calculate_quality_metrics()`, `_build_multi_source_quality_report()`

### What the Tests Verify

| Test Class | What It Checks |
|------------|----------------|
| `TestCalculateQualityMetrics` | Empty results, null rate calculation, completeness (non-null percentage), duplicate detection, freshness (max temporal value), `_source_database` column excluded |
| `TestGapDetection` | No gaps when all DBs have data; gap detected when a column is 100% NULL in one DB but present in another; multi-DB gap detection |
| `TestMultiSourceQualityReport` | Freshest DB detected, most complete DB detected, `format_summary()` includes DB names and gap details |
| `TestQualityInPrompt` | Large model multi-DB prompt includes `DATA QUALITY COMPARISON`; medium and small model prompts do not |
| `TestCachedQualityReport` | Quality report is cached after computation; cached data is returned on subsequent calls |

### Manual Verification

1. **Quality metrics**: Create results with known nulls and confirm `completeness` matches expected value:
   ```python
   narrator = ResultNarrator(ollama_client=mock, model="qwen2.5:32b")
   metrics = narrator._calculate_quality_metrics(
       [{"a": 1, "b": None}, {"a": None, "b": None}], "testdb"
   )
   assert metrics.completeness == 0.25  # 1 non-null out of 4 cells
   ```

2. **Gap detection**: Supply two databases where column `y` is NULL in one:
   ```python
   report = narrator._build_multi_source_quality_report({
       "db1": [{"x": 1, "y": 10}],
       "db2": [{"x": 2, "y": None}],
   })
   assert len(report.gap_insights) == 1
   assert report.gap_insights[0].column == "y"
   ```

3. **Prompt injection**: Confirm the enhanced multi-DB prompt for a large model contains `"DATA QUALITY COMPARISON"`, and the same prompt for a small model does not.

---

## Phase 19.4: Chart Intelligence Enhancements

### What It Does
Frontend improvements to chart type selection: adaptive scoring presets (default/business/scientific), column interest scoring for Y-axis selection, and context-aware insight ordering based on user question.

### Key Files
- `frontend/src/utils/chartIntelligence.ts` — `analyzeData()`, `scoreColumnInterest()`, `ScoringPreset`

### What the Tests Verify

| Test Group | What It Checks |
|------------|----------------|
| Adaptive Scoring Presets | Default preset matches no-preset behavior; business preset boosts bar charts for categorical data; scientific preset boosts scatter/histogram; business reduces scatter prominence |
| Column Interest Scoring | Revenue-like columns score higher than ID columns; high-variance columns score higher; non-numeric columns return 0; columns with many nulls are penalized; `total_sales` is picked over `id` for Y-axis |
| Context-Aware Insights | Trend insight surfaced first for trend questions; outlier insight highlighted for anomaly questions; distribution insight appears for comparison questions; base insights returned without question |
| Backward Compatibility | `analyzeData(data)` works with only results; works with results + statistics; empty data returns `table` chart type |

### Manual Verification

1. **Preset behavior**: In browser console or test, call `analyzeData(categoricalData, {}, '', 'business')` and confirm bar chart ranks higher than with `'default'` preset.

2. **Y-axis selection**: Call `analyzeData([{id: 1, total_sales: 1000}, ...])` and confirm `result.yColumn === 'total_sales'` (not `id`).

3. **Visual check**: Query a dataset in the app and observe that the auto-selected chart type makes sense for the data shape. Toggle between chart types to confirm alternatives are reasonable.

---

## Phase 19.5: Parallel Analysis Pipeline

### What It Does
Runs statistics extraction, anomaly detection, and correlation calculation in parallel using `asyncio.gather` for datasets with >= 10 rows. Applies early exit for tiny datasets (<= 3 rows) to skip the LLM entirely.

### Key Files
- `src/llm/result_narrator.py` — `generate_narrative()` lines 188-227

### What the Tests Verify

| Test Class | What It Checks |
|------------|----------------|
| `TestEarlyExitSmallDataset` | 0 rows → "No results found" (no LLM call); >1000 rows → "too large" (no LLM call); <=3 rows → fallback narrative (no LLM call); 4 rows → LLM is called |
| `TestParallelExecution` | >=10 rows triggers `asyncio.gather`; <10 rows (but >3) does NOT use `asyncio.gather` |
| `TestParallelExceptionHandling` | Anomaly detection failure → narrative still generated; correlation failure → fallback narrative; statistics failure → empty dict fallback; LLM timeout → fallback narrative |
| `TestAnalysisCompleteness` | Anomalies (outlier data) appear in `result.statistics["anomalies"]`; trends (temporal data) appear in `result.statistics["trends"]`; correlations (correlated columns) appear in `result.statistics["correlations"]`; token info captured from LLM response |
| `TestMultiDatabaseParallel` | Large model multi-DB computes quality report; small model multi-DB skips quality report |

### Manual Verification

1. **Early exit**: Call `generate_narrative()` with 2 rows and confirm the LLM mock is never called:
   ```python
   narrator = ResultNarrator(ollama_client=mock, model="mistral:7b")
   result = await narrator.generate_narrative(
       question="items?", sql="SELECT *",
       results=[{"a": 1}, {"a": 2}], row_count=2, execution_time_ms=5.0
   )
   assert "Found 2 record" in result.summary
   mock.generate.assert_not_called()
   ```

2. **Parallel path**: Call with 15+ rows and observe (via logging or debugger) that `asyncio.gather` is used.

3. **Graceful degradation**: Patch `_detect_anomalies` to raise an exception and confirm the narrative is still generated (falls back gracefully).

---

## End-to-End Verification Checklist

Use this checklist to verify Phase 19 features work together in the running application.

### Prerequisites
- Backend running (`python -m uvicorn src.main:app --reload`)
- Frontend running (`cd frontend && npm run dev`)
- At least one database connection configured
- Ollama running with a model pulled

### Checklist

| # | Test | Expected Result | Pass? |
|---|------|-----------------|-------|
| 1 | Run a simple query (e.g., "show all products") | Narrative generated with summary, insights, and statistics | |
| 2 | Run same query again | Second response should be faster (analytics cache hit — check backend logs for `"Analytics cache hit"`) | |
| 3 | Query with small model configured (e.g., phi3) | Narrative should be shorter/more compact. Check prompt in logs starts with `"Data analyst."` | |
| 4 | Query with large model (e.g., qwen2.5:32b) | Narrative should be richer. Prompt should contain `"senior data analyst"` | |
| 5 | Query returning <= 3 rows | Fallback narrative ("Found N records") without LLM call. Should be near-instant | |
| 6 | Query returning 0 rows | "No results found." response | |
| 7 | Query returning > 1000 rows | "too large for detailed analysis" response | |
| 8 | Multi-database query (2+ connections active) | Narrative compares databases. Check for cross-DB insights | |
| 9 | Multi-database query with large model | Logs should show quality report generation. Prompt includes `"DATA QUALITY COMPARISON"` | |
| 10 | Chart auto-detection on categorical data | Bar chart should be primary recommendation | |
| 11 | Chart auto-detection on time series data | Line chart should be primary recommendation | |
| 12 | Dataset with clear outlier | `result.statistics` should contain `anomalies.found: true` | |
| 13 | Dataset with correlated numeric columns (20+ rows) | `result.statistics` should contain `correlations.found: true` | |
| 14 | Run `get_analytics_cache().get_cache_stats()` | Should show non-zero `local_size` after queries | |

### Logging Verification

Enable debug logging to verify cache behavior:

```python
# In .env or environment
LOG_LEVEL=DEBUG
```

Look for these log messages:
- `"Analytics cache hit for statistics"` — cache is working
- `"Analytics cache hit for quality report"` — quality report cache is working
- `"Correlation calculation failed: ..."` — graceful degradation working
- `"Narrative generation timeout after Xs"` — timeout fallback working

---

## Troubleshooting

| Issue | Likely Cause | Fix |
|-------|-------------|-----|
| Tier detection always returns MEDIUM | Model name doesn't match any size pattern | Check `get_model_size_for_model()` in `src/llm/prompt_optimizer.py` |
| Cache never hits | Different result sets produce different hashes | Verify `compute_result_hash()` with identical data returns same hash |
| Quality report missing from prompt | Model tier is not LARGE | Quality summary only injected for `ModelSize.LARGE` |
| `asyncio.gather` not called | Dataset < 10 rows | Parallel path only activates for >= 10 rows |
| `ImportError: cachetools` | Missing dependency | `pip install cachetools` |
| Redis cache not working | Redis not running or not configured | Analytics cache falls back to local-only silently. Check `REDIS_URL` in `.env` |
| Frontend chart tests fail | Missing vitest | `cd frontend && npm install` |
