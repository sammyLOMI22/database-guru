# Data Insights Enhancement Plan (Phase 19)

**Date**: February 1, 2026
**Status**: PROPOSED
**Priority**: MEDIUM
**Est. Effort**: ~1,800 lines | 2-3 weeks
**Dependencies**: None (Independent)

---

## Overview

Enhance data insights quality for multi-database scenarios and charts through small model optimizations similar to what was done for SQL generation. This includes prompt compression, adaptive analysis, analytics caching, and smarter chart recommendations.

### Goals
1. **Small Model Optimization**: Reduce prompt sizes by 40% for <7B models
2. **Analytics Caching**: Cache computed statistics to eliminate redundant analysis
3. **Multi-Source Insights**: Better cross-database comparisons and quality metrics
4. **Chart Quality**: Adaptive scoring and smarter column selection
5. **Performance**: Parallel analysis for 30-40% speedup

---

## Current State Assessment

### What Works Well
- Statistical analysis (outliers, correlations, trends) is comprehensive
- Multi-database parallel execution functional
- Chart recommendation scores 11 chart types
- Pattern detection (time-series, hierarchy, geo) working

### Key Gaps
| Gap | Impact | Current Behavior |
|-----|--------|------------------|
| No model-aware prompts | Large prompts fail on small models | Fixed 700+ token prompt always |
| No statistics caching | Redundant computation | Same stats recalculated each query |
| Limited cross-DB insights | Missing quality comparisons | Only numeric column averages |
| Sequential analysis | Slow response times | 5 serial passes through data |
| Fixed chart weights | Suboptimal for some domains | Same weights regardless of context |

---

## Implementation Phases

### Phase 19.1: Small Model Narrative Optimization
**Est: ~400 lines | 3-4 days**

Add model-aware prompt templates and token budgeting for Result Narrator.

#### 19.1.1 Model-Aware Prompt Templates

**File**: `src/llm/prompts.py`

Add tiered narrative prompts:

```python
# Compact prompt for small models (<7B parameters)
NARRATIVE_PROMPT_COMPACT = """Data analyst. Query results for: {question}

Data ({row_count} rows):
{sample_data}

Stats: {statistics_compact}

Return JSON:
{{"summary": "1-2 sentences", "insights": ["insight1", "insight2"], "answer": "direct value", "confidence": 0.0-1.0}}"""

# Standard prompt for medium models (7B-13B)
NARRATIVE_PROMPT_STANDARD = """..."""  # Current prompt

# Enhanced prompt for large models (13B+)
NARRATIVE_PROMPT_ENHANCED = """..."""  # Richer context, more insights
```

**Token Budget by Model Tier**:
| Tier | Models | Max Prompt Tokens | Max Insights |
|------|--------|-------------------|--------------|
| Compact | Llama 3.2 3B, Gemma 2B, Phi-3 | 800 | 2-3 |
| Standard | Qwen2.5-7B, Mistral 7B | 1,500 | 4-5 |
| Enhanced | Qwen2.5-32B, Llama 3 70B | 2,500 | 5-7 |

#### 19.1.2 Statistics Compression

**File**: `src/llm/result_narrator.py`

Add method to compress statistics for small models:

```python
def _compress_statistics(self, statistics: Dict, model_tier: str) -> str:
    """Compress statistics based on model tier."""
    if model_tier == "compact":
        # Only essential stats: count, avg for top 3 numeric columns
        return self._format_essential_stats(statistics)
    elif model_tier == "standard":
        # Current level
        return json.dumps(statistics)
    else:
        # Full stats + additional context
        return self._format_enhanced_stats(statistics)
```

#### 19.1.3 Model Router Integration

**File**: `src/llm/result_narrator.py`

Integrate with existing model router:

```python
async def generate_narrative(self, ...):
    # Get model tier from router
    model_info = self.model_router.get_model_for_task(TaskType.NARRATIVES)
    model_tier = self._get_model_tier(model_info.model_name)

    # Select appropriate prompt template
    prompt_template = self._get_prompt_template(model_tier)

    # Compress statistics for tier
    stats_str = self._compress_statistics(statistics, model_tier)

    # Apply token budget
    prompt = self.prompt_optimizer.optimize(
        prompt_template.format(...),
        max_tokens=MODEL_TIER_BUDGETS[model_tier]
    )
```

#### 19.1.4 Multi-DB Narrative Compression

Same tiering for `MULTI_DATABASE_NARRATIVE_PROMPT`:

- **Compact**: Top 2 differences only, no per-DB breakdown
- **Standard**: Current format with 3-4 comparisons
- **Enhanced**: Full breakdown + quality metrics + recommendations

#### Tests
- `test_narrative_prompt_selection_by_model()`
- `test_statistics_compression_compact()`
- `test_statistics_compression_standard()`
- `test_model_tier_detection()`
- `test_token_budget_enforcement()`

---

### Phase 19.2: Analytics Caching Layer
**Est: ~350 lines | 2-3 days**

Cache computed statistics and patterns to avoid redundant analysis.

#### 19.2.1 Statistics Cache Service

**New File**: `src/services/analytics_cache.py`

```python
class AnalyticsCache:
    """Cache for computed statistics and patterns."""

    def __init__(self, redis_client: Optional[Redis] = None):
        self.redis = redis_client
        self.local_cache = TTLCache(maxsize=100, ttl=3600)  # 1hr local

    async def get_statistics(
        self,
        result_hash: str,
        database_type: str
    ) -> Optional[Dict]:
        """Get cached statistics for result set."""
        key = f"stats:{database_type}:{result_hash}"

        # Check local first
        if key in self.local_cache:
            return self.local_cache[key]

        # Check Redis
        if self.redis:
            cached = await self.redis.get(key)
            if cached:
                stats = json.loads(cached)
                self.local_cache[key] = stats
                return stats

        return None

    async def cache_statistics(
        self,
        result_hash: str,
        database_type: str,
        statistics: Dict,
        ttl: int = 86400  # 24 hours
    ):
        """Cache computed statistics."""
        key = f"stats:{database_type}:{result_hash}"
        self.local_cache[key] = statistics

        if self.redis:
            await self.redis.setex(key, ttl, json.dumps(statistics))

    def compute_result_hash(self, results: List[Dict]) -> str:
        """Compute hash of result set for cache key."""
        # Hash based on column names + first/last rows + row count
        if not results:
            return "empty"

        fingerprint = {
            "columns": sorted(results[0].keys()),
            "count": len(results),
            "first": self._row_fingerprint(results[0]),
            "last": self._row_fingerprint(results[-1]) if len(results) > 1 else None
        }
        return hashlib.md5(json.dumps(fingerprint).encode()).hexdigest()[:16]
```

#### 19.2.2 Pattern Cache

Cache detected patterns (time-series, hierarchy, geo):

```python
async def get_patterns(self, result_hash: str) -> Optional[DetectedPatterns]:
    """Get cached pattern detection results."""
    key = f"patterns:{result_hash}"
    ...

async def cache_patterns(
    self,
    result_hash: str,
    patterns: DetectedPatterns,
    ttl: int = 86400
):
    """Cache pattern detection results."""
    ...
```

#### 19.2.3 Integration with Result Narrator

**File**: `src/llm/result_narrator.py`

```python
class ResultNarrator:
    def __init__(self, ..., analytics_cache: Optional[AnalyticsCache] = None):
        self.analytics_cache = analytics_cache or AnalyticsCache()

    async def _get_or_compute_statistics(
        self,
        results: List[Dict],
        database_type: str
    ) -> Dict:
        """Get statistics from cache or compute them."""
        result_hash = self.analytics_cache.compute_result_hash(results)

        # Try cache first
        cached = await self.analytics_cache.get_statistics(result_hash, database_type)
        if cached:
            logger.info(f"Analytics cache hit for {result_hash}")
            return cached

        # Compute and cache
        statistics = self._extract_statistics(results)
        await self.analytics_cache.cache_statistics(
            result_hash, database_type, statistics
        )
        return statistics
```

#### Tests
- `test_statistics_cache_hit()`
- `test_statistics_cache_miss_and_store()`
- `test_result_hash_consistency()`
- `test_pattern_cache()`
- `test_cache_expiration()`

---

### Phase 19.3: Enhanced Multi-Source Insights
**Est: ~450 lines | 3-4 days**

Add richer cross-database analysis with quality metrics and gap detection.

#### 19.3.1 Data Quality Metrics

**File**: `src/llm/result_narrator.py`

Add new analysis methods:

```python
def _calculate_quality_metrics(
    self,
    results: List[Dict],
    database_name: str
) -> DataQualityMetrics:
    """Calculate data quality metrics for a result set."""
    metrics = DataQualityMetrics(
        database=database_name,
        row_count=len(results),
        null_rates={},      # Percentage of NULLs per column
        duplicate_rate=0.0, # Percentage of duplicate rows
        freshness=None,     # Most recent timestamp if temporal
        completeness=0.0    # Percentage of non-NULL values overall
    )

    if not results:
        return metrics

    columns = list(results[0].keys())

    # Calculate NULL rates per column
    for col in columns:
        null_count = sum(1 for r in results if r.get(col) is None)
        metrics.null_rates[col] = null_count / len(results)

    # Overall completeness
    total_cells = len(results) * len(columns)
    null_cells = sum(
        1 for r in results for v in r.values() if v is None
    )
    metrics.completeness = 1 - (null_cells / total_cells) if total_cells > 0 else 0

    # Duplicate detection (based on all columns)
    seen = set()
    duplicates = 0
    for r in results:
        row_tuple = tuple(sorted(r.items()))
        if row_tuple in seen:
            duplicates += 1
        seen.add(row_tuple)
    metrics.duplicate_rate = duplicates / len(results) if results else 0

    # Freshness (newest timestamp)
    temporal_cols = self._detect_temporal_columns(results)
    if temporal_cols:
        dates = [r.get(temporal_cols[0]) for r in results if r.get(temporal_cols[0])]
        if dates:
            metrics.freshness = max(dates)

    return metrics
```

#### 19.3.2 Cross-Database Gap Analysis

```python
def _analyze_cross_database_gaps(
    self,
    db_results: Dict[str, List[Dict]]  # {db_name: results}
) -> List[GapInsight]:
    """Identify data gaps between databases."""
    insights = []

    # Compare categorical value coverage
    categorical_cols = self._get_common_categorical_columns(db_results)
    for col in categorical_cols:
        value_sets = {
            db: set(r.get(col) for r in results if r.get(col))
            for db, results in db_results.items()
        }

        # Find values missing in some DBs
        all_values = set.union(*value_sets.values())
        for db, values in value_sets.items():
            missing = all_values - values
            if missing and len(missing) <= 10:
                insights.append(GapInsight(
                    column=col,
                    database=db,
                    missing_values=list(missing),
                    coverage_pct=len(values) / len(all_values) * 100
                ))

    return insights
```

#### 19.3.3 Quality Comparison in Narrative Prompt

Add quality metrics to multi-database prompt:

```python
MULTI_DATABASE_NARRATIVE_PROMPT_ENHANCED = """
...
DATA QUALITY COMPARISON:
{quality_comparison}

COVERAGE GAPS:
{gap_analysis}

INCLUDE in your response:
1. Which database has better data quality (fewer NULLs, more complete)
2. Data freshness comparison (which is more up-to-date)
3. Coverage gaps (what's missing where)
4. Recommendations for data consolidation
...
"""
```

#### 19.3.4 Quality Metrics Response Schema

```python
@dataclass
class DataQualityMetrics:
    database: str
    row_count: int
    null_rates: Dict[str, float]
    duplicate_rate: float
    freshness: Optional[datetime]
    completeness: float

@dataclass
class GapInsight:
    column: str
    database: str
    missing_values: List[Any]
    coverage_pct: float

@dataclass
class MultiSourceQualityReport:
    metrics_by_db: Dict[str, DataQualityMetrics]
    gaps: List[GapInsight]
    quality_winner: str  # DB with best overall quality
    freshness_winner: str  # DB with most recent data
    recommendations: List[str]
```

#### Tests
- `test_null_rate_calculation()`
- `test_duplicate_detection()`
- `test_freshness_detection()`
- `test_cross_database_gap_analysis()`
- `test_quality_comparison_narrative()`

---

### Phase 19.4: Chart Intelligence Enhancements
**Est: ~350 lines | 2-3 days**

Improve chart recommendations with adaptive scoring and smarter column selection.

#### 19.4.1 Adaptive Scoring Weights

**File**: `frontend/src/utils/chartIntelligence.ts`

Replace hardcoded weights with configurable scoring:

```typescript
interface ScoringWeights {
  timeSeries: { line: number; area: number; bar: number };
  categorical: { bar: number; pie: number; treemap: number };
  numeric: { scatter: number; histogram: number; boxplot: number };
  // ... more
}

// Default weights (can be overridden per workspace)
const DEFAULT_WEIGHTS: ScoringWeights = {
  timeSeries: { line: 40, area: 35, bar: 15 },
  categorical: { bar: 45, pie: 40, treemap: 35 },
  numeric: { scatter: 40, histogram: 30, boxplot: 35 }
};

// Business data preset (favors bar charts)
const BUSINESS_WEIGHTS: ScoringWeights = {
  timeSeries: { line: 45, area: 30, bar: 25 },
  categorical: { bar: 55, pie: 35, treemap: 30 },  // Higher bar preference
  numeric: { scatter: 35, histogram: 25, boxplot: 30 }
};

// Scientific data preset (favors distributions)
const SCIENTIFIC_WEIGHTS: ScoringWeights = {
  timeSeries: { line: 50, area: 25, bar: 10 },
  categorical: { bar: 30, pie: 25, treemap: 20 },
  numeric: { scatter: 50, histogram: 45, boxplot: 40 }  // Higher distribution preference
};
```

#### 19.4.2 Smart Column Selection

Score columns by "interestingness" for better X/Y selection:

```typescript
interface ColumnScore {
  column: string;
  type: 'numeric' | 'categorical' | 'temporal';
  variance: number;      // Normalized variance (0-1)
  uniqueness: number;    // Unique values / total rows
  nullRate: number;      // Percentage of nulls
  interestScore: number; // Combined score
}

function scoreColumnsForChart(
  data: any[],
  statistics: Statistics
): ColumnScore[] {
  const scores: ColumnScore[] = [];

  for (const col of Object.keys(data[0] || {})) {
    // Skip ID columns
    if (isIdColumn(col)) continue;

    const colStats = statistics.columns[col];
    const score: ColumnScore = {
      column: col,
      type: detectColumnType(col, data),
      variance: colStats?.stdev ? colStats.stdev / (colStats.max - colStats.min || 1) : 0,
      uniqueness: (colStats?.unique_count || 0) / data.length,
      nullRate: (colStats?.null_count || 0) / data.length,
      interestScore: 0
    };

    // Calculate interest score
    // Higher variance = more interesting for numeric
    // Moderate uniqueness = more interesting for categorical
    // Low null rate = better quality
    score.interestScore = calculateInterestScore(score);
    scores.push(score);
  }

  return scores.sort((a, b) => b.interestScore - a.interestScore);
}

function selectBestColumns(
  scores: ColumnScore[],
  chartType: ChartType
): { x: string; y: string } {
  // For scatter: pick two most interesting numeric columns
  if (chartType === 'scatter') {
    const numerics = scores.filter(s => s.type === 'numeric');
    return { x: numerics[0]?.column, y: numerics[1]?.column };
  }

  // For bar/line: temporal/categorical for X, most interesting numeric for Y
  if (['bar', 'line', 'area'].includes(chartType)) {
    const xCol = scores.find(s => s.type === 'temporal')
               || scores.find(s => s.type === 'categorical');
    const yCol = scores.find(s => s.type === 'numeric');
    return { x: xCol?.column, y: yCol?.column };
  }

  // ... other chart types
}
```

#### 19.4.3 Context-Aware Insights

Generate insights based on question context:

```typescript
function generateContextualInsights(
  question: string,
  data: any[],
  patterns: DetectedPatterns
): DataInsight[] {
  const insights: DataInsight[] = [];
  const questionLower = question.toLowerCase();

  // Trend context
  if (questionLower.includes('trend') || questionLower.includes('over time')) {
    if (patterns.trend) {
      insights.push({
        type: 'trend',
        message: `${patterns.trend.direction} trend detected with ${patterns.trend.confidence}% confidence`,
        priority: 'high'
      });
    }
  }

  // Comparison context
  if (questionLower.includes('compare') || questionLower.includes('difference')) {
    const maxMin = findMaxMinCategories(data);
    insights.push({
      type: 'comparison',
      message: `${maxMin.max.category} leads at ${maxMin.max.value}, ${maxMin.min.category} trails at ${maxMin.min.value}`,
      priority: 'high'
    });
  }

  // Distribution context
  if (questionLower.includes('distribution') || questionLower.includes('spread')) {
    if (patterns.outliers.length > 0) {
      insights.push({
        type: 'outlier',
        message: `${patterns.outliers.length} outliers detected that may skew the distribution`,
        priority: 'medium'
      });
    }
  }

  return insights;
}
```

#### Tests
- `test_adaptive_scoring_weights()`
- `test_column_interest_scoring()`
- `test_smart_column_selection_scatter()`
- `test_smart_column_selection_bar()`
- `test_contextual_insights_trend()`
- `test_contextual_insights_comparison()`

---

### Phase 19.5: Parallel Analysis Pipeline
**Est: ~250 lines | 1-2 days**

Parallelize independent analysis steps for 30-40% speedup.

#### 19.5.1 Async Analysis Methods

**File**: `src/llm/result_narrator.py`

Convert analysis methods to async:

```python
async def _extract_statistics_async(self, results: List[Dict]) -> Dict:
    """Async version of statistics extraction."""
    return await asyncio.to_thread(self._extract_statistics, results)

async def _detect_anomalies_async(self, results: List[Dict]) -> List[Dict]:
    """Async version of anomaly detection."""
    return await asyncio.to_thread(self._detect_anomalies, results)

async def _detect_temporal_columns_async(self, results: List[Dict]) -> List[str]:
    """Async version of temporal detection."""
    return await asyncio.to_thread(self._detect_temporal_columns, results)
```

#### 19.5.2 Parallel Execution

```python
async def _analyze_results_parallel(
    self,
    results: List[Dict],
    database_type: str
) -> AnalysisBundle:
    """Run independent analyses in parallel."""

    # Phase 1: Independent analyses (parallel)
    stats_task = self._extract_statistics_async(results)
    anomalies_task = self._detect_anomalies_async(results)
    temporal_task = self._detect_temporal_columns_async(results)
    quality_task = self._calculate_quality_metrics_async(results, database_type)

    stats, anomalies, temporal_cols, quality = await asyncio.gather(
        stats_task,
        anomalies_task,
        temporal_task,
        quality_task
    )

    # Phase 2: Dependent analyses (parallel where possible)
    trends_task = self._detect_trends_async(results, temporal_cols)
    correlations_task = self._calculate_correlations_async(results)

    trends, correlations = await asyncio.gather(
        trends_task,
        correlations_task
    )

    return AnalysisBundle(
        statistics=stats,
        anomalies=anomalies,
        temporal_columns=temporal_cols,
        trends=trends,
        correlations=correlations,
        quality_metrics=quality
    )
```

#### 19.5.3 Early Exit Optimization

Stop analysis when confidence is sufficient:

```python
async def generate_narrative(self, ...):
    """Generate narrative with early exit optimization."""

    # Quick analysis for small datasets
    if len(results) < 10:
        # Use simplified analysis path
        return await self._generate_simple_narrative(results, question, sql)

    # Check cache first
    cached_stats = await self.analytics_cache.get_statistics(result_hash, db_type)
    if cached_stats and cached_stats.get('confidence', 0) > 0.8:
        # High-confidence cached analysis, skip redundant computation
        return await self._generate_from_cached(cached_stats, question)

    # Full parallel analysis
    analysis = await self._analyze_results_parallel(results, db_type)
    ...
```

#### Tests
- `test_parallel_analysis_speedup()`
- `test_early_exit_small_dataset()`
- `test_early_exit_cached_high_confidence()`
- `test_analysis_bundle_completeness()`

---

## API Changes

### New Endpoints

None required - enhancements are internal to existing endpoints.

### Modified Response Fields

Add quality metrics to multi-database responses:

```python
class DatabaseQueryResult(BaseModel):
    # ... existing fields ...
    quality_metrics: Optional[DataQualityMetrics] = None  # NEW

class MultiDatabaseQueryResponse(BaseModel):
    # ... existing fields ...
    cross_database_analysis: Optional[MultiSourceQualityReport] = None  # NEW
```

---

## Configuration

### New Settings

**File**: `src/config/settings.py`

```python
class Settings(BaseSettings):
    # ... existing ...

    # Analytics Cache
    ANALYTICS_CACHE_TTL: int = 86400  # 24 hours
    ANALYTICS_CACHE_ENABLED: bool = True

    # Narrative Optimization
    NARRATIVE_MODEL_TIER_AUTO: bool = True  # Auto-detect model tier
    NARRATIVE_MAX_INSIGHTS_COMPACT: int = 3
    NARRATIVE_MAX_INSIGHTS_STANDARD: int = 5
    NARRATIVE_MAX_INSIGHTS_ENHANCED: int = 7

    # Chart Intelligence
    CHART_SCORING_PRESET: str = "default"  # default, business, scientific
    CHART_COLUMN_SELECTION_SMART: bool = True
```

---

## Testing Strategy

### Unit Tests (~40 tests)
- Prompt template selection by model tier
- Statistics compression accuracy
- Cache hit/miss behavior
- Quality metrics calculations
- Gap analysis correctness
- Column scoring logic
- Parallel analysis correctness

### Integration Tests (~15 tests)
- End-to-end narrative with small model
- Multi-database quality comparison
- Chart recommendation with adaptive weights
- Cache integration with Redis

### Performance Tests (~5 tests)
- Parallel vs sequential speedup measurement
- Cache hit rate under load
- Memory usage with large datasets

---

## Rollout Plan

### Week 1: Foundation
- [ ] 19.1 Small Model Narrative Optimization
- [ ] 19.2 Analytics Caching Layer

### Week 2: Multi-Source & Charts
- [ ] 19.3 Enhanced Multi-Source Insights
- [ ] 19.4 Chart Intelligence Enhancements

### Week 3: Performance & Polish
- [ ] 19.5 Parallel Analysis Pipeline
- [ ] Integration testing
- [ ] Documentation updates

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Narrative generation time (avg) | ~3s | <2s |
| Small model narrative success rate | ~60% | >90% |
| Analytics cache hit rate | 0% | >40% |
| Chart recommendation accuracy | ~75% | >85% |
| Multi-DB insight quality (subjective) | Basic | Rich quality metrics |

---

## Dependencies

- Redis (optional, for distributed caching)
- Existing model router (`src/llm/model_router.py`)
- Existing prompt optimizer (`src/llm/prompt_optimizer.py`)

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Cache invalidation complexity | Stale insights | TTL-based expiry, result hash includes schema |
| Small model quality degradation | Poor insights | Fallback to larger model on low confidence |
| Parallel analysis race conditions | Incorrect results | Use asyncio.gather, no shared mutable state |
| Scoring weight tuning | Suboptimal charts | A/B testing, user feedback loop |

---

## File Summary

| Phase | New Files | Modified Files |
|-------|-----------|----------------|
| 19.1 | - | `src/llm/prompts.py`, `src/llm/result_narrator.py` |
| 19.2 | `src/services/analytics_cache.py` | `src/llm/result_narrator.py` |
| 19.3 | - | `src/llm/result_narrator.py`, `src/llm/prompts.py` |
| 19.4 | - | `frontend/src/utils/chartIntelligence.ts` |
| 19.5 | - | `src/llm/result_narrator.py` |

---

## References

- [SMALL_MODEL_OPTIMIZATION_PHASE2.md](SMALL_MODEL_OPTIMIZATION_PHASE2.md) - Similar optimization approach
- [Result Narrator](../../src/llm/result_narrator.py) - Current implementation
- [Chart Intelligence](../../frontend/src/utils/chartIntelligence.ts) - Current chart logic
- [Model Router](../../src/llm/model_router.py) - Model selection logic
