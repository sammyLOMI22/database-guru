# Intelligent Data Narratives & Human Insights - Complete Guide

## Overview

The "Intelligent Data Narratives & Human Insights" feature transforms raw SQL query results into human-readable natural language summaries with advanced statistical analysis. Instead of showing only data tables, Database Guru generates contextual narratives that highlight patterns, anomalies, trends, and correlations.

**Example**:
```
Query: "Show me sales by region"
Raw Result: [{"region": "CA", "sales": 250000}, {"region": "NY", "sales": 180000}, ...]

Generated Narrative:
"California leads with the highest sales at $250K, followed by New York at $180K.
California sales are 39% higher than NY. Note: This is the highest California
sales figure in 6 months, showing consistent upward momentum."

Key Insights:
• California generates 28% of total regional sales
• Sales vary widely across regions ($150K-$450K range)
• Top 3 regions account for 62% of total revenue
```

## Feature Components

### 1. Core Narrative Generation

The system generates structured narratives with:

- **Summary**: 1-2 sentence overview answering the user's question
- **Key Insights**: 3-5 bullet points highlighting notable patterns
- **Direct Answer**: Specific value when question asks for a metric
- **Confidence Score**: 0.0-1.0 rating of interpretation quality
- **Statistics**: Extracted metrics (min, max, avg, counts, distributions)

### 2. Advanced Analysis Features

#### Anomaly Detection
- **Method**: Z-score statistical outlier detection (threshold: |z| ≥ 1.95)
- **Use Case**: Identifies unusual values that deviate significantly from normal data
- **Example**: "Found 1 extreme outlier: value 9999 is 15+ standard deviations above the mean"
- **Display**: Red alert box in ResultSummary component

#### Comparative Analysis
- **Method**: Queries historical results and compares to current data
- **Use Case**: Shows percentage changes vs. recent similar queries
- **Example**: "Revenue is up 20% compared to last month's query"
- **Requirement**: Database session with access to query_history table

#### Trend Detection
- **Method**: Linear regression on time-series data (R² threshold: 0.3)
- **Use Case**: Identifies temporal patterns in date-based columns
- **Example**: "Sales trending upward by 2.5% per day over 30 days (R²=0.92)"
- **Display**: Blue alert box showing trend direction and slope

#### Correlation Analysis
- **Method**: Pearson correlation coefficient (threshold: |r| > 0.7)
- **Use Case**: Detects relationships between numeric columns
- **Example**: "Marketing spend and sales revenue strongly correlated (r=0.88)"
- **Display**: Purple alert box with correlation insights

## Architecture

### Backend Components

#### ResultNarrator Agent (`src/llm/result_narrator.py`)
**Primary**: Orchestrates narrative generation and advanced analysis

**Key Methods**:
```python
# Main entry point
async def generate_narrative(
    question: str,
    sql: str,
    results: List[Dict],
    row_count: int,
    execution_time_ms: int
) -> NarrativeResult

# Advanced analysis methods
def _detect_anomalies(results) -> Dict  # Z-score outlier detection
def _compare_to_history(results) -> Dict  # Historical comparison
def _detect_trends(results, temporal_cols) -> Dict  # Linear regression
def _calculate_correlations(results) -> Dict  # Pearson correlation
def _get_historical_context() -> List[Dict]  # Query history lookup
def _detect_temporal_columns(results) -> List[str]  # Date column detection
```

**Performance Characteristics**:
- Small datasets (5 rows): < 1.0 second
- Medium datasets (20 rows): < 1.5 seconds
- Large datasets (100 rows, sampled): < 2.0 seconds
- All advanced features combined: < 3.0 seconds (99th percentile)

#### LLM Integration
- **Model**: Configured via Ollama (default: qwen2.5-coder:32b)
- **Temperature**: 0.3 (factual, less creative)
- **Timeout**: 5 seconds per LLM call
- **Response Format**: JSON with summary, insights, answer, confidence

### Frontend Components

#### ResultSummary Component (`frontend/src/components/ResultSummary.tsx`)
**Primary**: Displays generated narratives with advanced analysis findings

**Sections**:
1. **Header**: Title with sparkles icon + confidence badge (green/amber/red)
2. **Direct Answer**: Highlighted box when question asks for specific value
3. **Summary**: Main narrative paragraph
4. **Key Insights**: Bulleted list of notable findings
5. **Advanced Findings**:
   - Anomalies section (red background) - outliers and unusual values
   - Trends section (blue background) - temporal patterns
   - Correlations section (purple background) - column relationships
6. **Statistics**: Expandable `<details>` element with raw metrics
7. **Timestamp**: Generation time in user's local time

#### ChatInterface Toggle (`frontend/src/components/ChatInterface.tsx`)
**Purpose**: User control for enabling/disabling narrative generation

**Behavior**:
- Toggle button: "✨ Narratives" (enabled) vs "📊 Data Only" (disabled)
- Preference persisted to localStorage
- Passed to QueryRequest as `enable_narratives: boolean`

### Data Integration

#### API Endpoint
**Endpoint**: `POST /api/query/`
**Parameter**: `enable_narratives: bool = True`
**Response**: Includes `result_analysis: ResultAnalysis | null`

**Request Example**:
```python
{
    "question": "Show sales by region",
    "sql": "SELECT region, SUM(sales) as sales FROM sales GROUP BY region",
    "enable_narratives": true  # Enable narrative generation
}
```

**Response Example**:
```python
{
    "sql": "...",
    "success": true,
    "result_analysis": {
        "summary": "California leads with highest sales...",
        "key_insights": ["Insight 1", "Insight 2", ...],
        "direct_answer": None,
        "confidence": 0.88,
        "statistics": {
            "region_count": 5,
            "sales": {"min": 150000, "max": 450000, "avg": 320000},
            "anomalies": {
                "found": true,
                "count": 1,
                "patterns": ["One outlier value..."]
            },
            "trends": {...},
            "correlations": {...}
        },
        "generated_at": "2024-12-13T18:30:45.123456"
    }
}
```

## Usage

### For End Users

#### Enable/Disable Narratives
1. Look for the "✨ Narratives" / "📊 Data Only" toggle in the ChatInterface
2. Click to toggle narrative generation
3. Preference is saved automatically (localStorage)

#### Reading Narratives
1. **Look at the Summary first**: Gets the gist of the data
2. **Review Key Insights**: Highlights important findings
3. **Check Advanced Findings**: Red/blue/purple boxes show anomalies/trends/correlations
4. **Expand Statistics**: Click "Detailed Statistics" for raw metrics

#### Query Examples That Trigger Advanced Features

**Anomaly Detection**:
```sql
SELECT product, sales FROM sales WHERE date = '2024-12-01'
-- Will detect if any product has unusually high/low sales
```

**Trend Detection**:
```sql
SELECT date, daily_revenue FROM revenue_daily WHERE date >= '2024-11-01'
-- Will detect if revenue is trending up/down
```

**Correlation Analysis**:
```sql
SELECT marketing_spend, sales_revenue FROM weekly_metrics
-- Will find relationship between marketing and sales
```

**Comparative Analysis**:
```sql
SELECT region, total_sales FROM sales GROUP BY region
-- Will compare to similar past queries (if available in history)
```

### For Developers

#### Enable Narratives in Your Integration
```python
# API call with narratives enabled
response = requests.post("http://localhost:8000/api/query/", json={
    "connection_id": "my_db",
    "question": "What is our total revenue?",
    "sql": "SELECT SUM(amount) as revenue FROM orders",
    "enable_narratives": True  # Enable feature
})

narrative = response.json()["result_analysis"]
print(f"Summary: {narrative['summary']}")
print(f"Confidence: {narrative['confidence']}")
```

#### Customize Narrative Generation
```python
from src.llm.result_narrator import ResultNarrator

narrator = ResultNarrator(
    ollama_client=my_ollama_client,
    db_session=my_db_session,
    enable_statistics=True,
    max_sample_rows=20,  # Sample first 20 rows for large datasets
    timeout_seconds=5    # 5 second LLM timeout
)

narrative = await narrator.generate_narrative(
    question="Analyze the data",
    sql="SELECT * FROM my_table",
    results=query_results,
    row_count=len(query_results),
    execution_time_ms=50
)
```

## Performance Characteristics

### Latency Breakdown

| Component | Typical Time | Max Time |
|-----------|---|---|
| Statistics Extraction | 20-30ms | 50ms |
| Anomaly Detection | 10-20ms | 50ms |
| Temporal Detection | 5-10ms | 20ms |
| Trend Calculation | 30-50ms | 100ms |
| Correlation Calc | 15-30ms | 50ms |
| LLM Call | 800-1500ms | 5000ms (timeout) |
| Response Parsing | 5-10ms | 20ms |
| **Total (all features)** | **900-1700ms** | **5300ms (99th %)** |

### Optimization Strategies

1. **Result Sampling**: First 20 rows analyzed for large datasets (>20 rows)
2. **Parallel Analysis**: Anomaly/trend/correlation detection runs in sequence but LLM call doesn't block
3. **Statistical Caching**: Results statistics extracted once, reused
4. **Graceful Degradation**: All advanced features wrapped in try-except (never blocks narrative)

### Scaling Considerations

- **Small queries (1-20 rows)**: Analyze all rows - full precision
- **Medium queries (21-1000 rows)**: Sample first 20 rows - high accuracy with speed
- **Large queries (>1000 rows)**: Skipped - narratives disabled (configured via NARRATIVE_MAX_ROWS)
- **Empty results**: Instant fallback narrative

## Configuration

### Environment Variables

```bash
# src/config/settings.py
ENABLE_NARRATIVES=true                    # Feature flag
NARRATIVE_TIMEOUT_SECONDS=5               # LLM timeout
NARRATIVE_MAX_SAMPLE_ROWS=20              # Sample size for large datasets
NARRATIVE_MAX_ROWS=1000                   # Max rows to generate narratives for
NARRATIVE_ANOMALY_THRESHOLD=1.95          # Z-score threshold
NARRATIVE_CORRELATION_THRESHOLD=0.7       # Correlation coefficient threshold
NARRATIVE_TREND_MIN_R_SQUARED=0.3        # Minimum R² for reporting trends
NARRATIVE_HISTORY_DAYS=30                 # Historical query lookback window
```

### Disabling Features

```python
# Via code
narrator = ResultNarrator(
    ollama_client=client,
    enable_statistics=True,  # Can set to False to skip statistics extraction
)

# Via API request (future enhancement)
# POST /api/query/ with enable_narratives=False
```

## Testing

### Test Coverage

**Unit Tests** (40 tests): `tests/test_result_narrator.py`
- Core narrative generation (6 tests)
- Statistics extraction (5 tests)
- JSON response parsing (6 tests)
- Fallback handling (3 tests)
- Prompt building (2 tests)
- Anomaly detection (4 tests)
- Comparative analysis (4 tests)
- Trend detection (4 tests)
- Correlation analysis (4 tests)

**Performance Tests** (11 tests): `tests/test_performance_narratives.py`
- Small/medium/large dataset latency
- Individual component performance
- Latency breakdown verification
- Large result sampling
- NULL value handling

**End-to-End Tests** (12 tests): `tests/test_e2e_narratives.py`
- Sales aggregation queries
- Time-series analysis
- Outlier detection
- Correlation analysis
- Customer segmentation
- Geographic analysis
- Product performance
- Edge cases (empty, single row, large datasets)

**Frontend Tests** (13 tests): `frontend/tests/ResultSummary.test.tsx`
- Component rendering
- Confidence badge colors
- Key insights display
- Statistics expandable section
- Advanced findings display (anomalies, trends, correlations)

**Total Test Coverage**: 76 comprehensive tests, all passing ✅

### Running Tests

```bash
# Run all narrative tests
./run_tests.sh tests/test_result_narrator.py tests/test_performance_narratives.py tests/test_e2e_narratives.py

# Run specific test class
./run_tests.sh tests/test_result_narrator.py::TestAnomalyDetection

# Run with coverage report
python -m pytest tests/test_*.py --cov=src.llm.result_narrator --cov-report=html
```

## Troubleshooting

### Narratives Not Appearing
**Problem**: Feature enabled but no narratives shown
**Solutions**:
1. Check `enable_narratives: true` in API request
2. Verify ChatInterface toggle is set to "✨ Narratives"
3. Check browser console for errors
4. Ensure Ollama is running: `ollama serve`

### Slow Narrative Generation
**Problem**: Taking >3 seconds for narrative generation
**Solutions**:
1. Check Ollama performance (high CPU usage?)
2. Reduce NARRATIVE_MAX_SAMPLE_ROWS (default: 20)
3. Increase NARRATIVE_TIMEOUT_SECONDS if network is slow
4. Profile with `tests/test_performance_narratives.py`

### Generic/Unhelpful Narratives
**Problem**: Getting generic narratives like "returned X rows"
**Solutions**:
1. Verify advanced features are enabled in ResultNarrator constructor
2. Check that generate_narrative() is calling _detect_anomalies, _detect_trends, etc.
3. Run E2E tests to verify advanced feature detection works
4. Check LLM response parsing doesn't have errors in logs

### LLM Timeout
**Problem**: "Narrative generation timeout after 5s" warning
**Solutions**:
1. Increase NARRATIVE_TIMEOUT_SECONDS in settings
2. Check Ollama model performance (`ollama ps`)
3. Consider switching to faster model
4. Reduce NARRATIVE_MAX_SAMPLE_ROWS

## Future Enhancements

### Planned Improvements
1. **Business Context Integration**: Reference business glossary for domain-specific insights
2. **Multi-Query Narratives**: Synthesize insights across multiple related queries
3. **Predictive Insights**: ML-based forecasting for trend extrapolation
4. **Custom Metrics**: User-defined KPIs for domain-specific analysis
5. **Narrative Personalization**: Adjust detail level based on user preferences

### Architecture Extensibility
The system is designed for easy extension:
- Add new analysis methods to ResultNarrator (follow _detect_anomalies pattern)
- Register new findings in generate_narrative() and return via statistics
- Update ResultSummary.tsx to display new finding types
- Add corresponding tests following existing test patterns

## See Also
- **CLAUDE.md**: Project-wide architecture and development guide
- **PARALLEL_EXECUTION.md**: Parallel query execution (related system)
- **SEMANTIC_CACHING.md**: Query result caching system
- **../**: Additional documentation
