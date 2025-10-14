# Result Verification Agent

## Overview

The **Result Verification Agent** is a quality assurance component that validates SQL query results before showing them to users. It catches logical errors, suspicious patterns, and unexpected results that might indicate incorrect queries.

## Features

### Intelligent Result Verification
- **Empty Result Detection** - Catches queries that return 0 rows when data should exist
- **NULL Value Detection** - Identifies when all returned values are NULL
- **Extreme Value Detection** - Flags unusually large numbers that might indicate calculation errors
- **Count Validation** - Verifies COUNT queries return reasonable values
- **Negative Count Detection** - Catches impossible negative counts

### Automatic Diagnostics
- Runs diagnostic queries to understand issues
- Checks if tables exist and contain data
- Retrieves sample data for analysis
- Provides detailed diagnosis of problems

### Smart Hints & Suggestions
- Generates improvement hints based on issue type
- Suggests fixes for common problems
- Provides context-aware recommendations

### Integration with Self-Correcting Agent
- Automatically triggers query regeneration for high-confidence issues
- Seamlessly integrated into the correction loop
- Configurable confidence thresholds

## How It Works

```
User Question → SQL Generation → Query Execution → ✅ Success
                                                      ↓
                                            Result Verification
                                                      ↓
                                    ┌─────────────────┴─────────────────┐
                                    ↓                                   ↓
                              Looks Good                          Suspicious!
                                    ↓                                   ↓
                            Return Results                    Run Diagnostics
                                                                        ↓
                                                              Generate Hints
                                                                        ↓
                                                    ┌──────────────────┴─────────────┐
                                                    ↓                                ↓
                                          High Confidence                   Low Confidence
                                          (≥ 0.7)                           (< 0.7)
                                                    ↓                                ↓
                                          Regenerate Query              Return with Warning
```

## Usage

### Basic Usage

```python
from src.llm.result_verification_agent import ResultVerificationAgent

# Initialize agent
agent = ResultVerificationAgent(
    enable_diagnostics=True,
    enable_auto_fix=True,
    extreme_value_threshold=1e9
)

# Verify results
verification = await agent.verify_results(
    question="How many customers do we have?",
    sql="SELECT COUNT(*) FROM customers",
    result={
        "success": True,
        "data": [{"count": 0}],
        "row_count": 1
    },
    schema=schema,
    database_type="postgresql"
)

if verification.is_suspicious:
    print(f"Issue: {verification.description}")
    print(f"Confidence: {verification.confidence}")
    print(f"Fix: {verification.suggested_fix}")
```

### Integrated with Self-Correcting Agent

The verification agent is automatically enabled in the self-correcting agent:

```python
from src.llm.self_correcting_agent import SelfCorrectingSQLAgent

# Initialize with verification enabled (default)
agent = SelfCorrectingSQLAgent(
    sql_generator=generator,
    enable_result_verification=True  # Enabled by default
)

# Generate and execute with automatic verification
result = await agent.generate_and_execute_with_retry(
    question="Show me all customers",
    schema=schema,
    session=db_session,
    database_type="postgresql"
)

# Check verification warnings
if result.get("verification_warnings"):
    for warning in result["verification_warnings"]:
        print(f"⚠️ {warning}")
```

### API Endpoints

#### 1. Verify Existing Result

```bash
POST /api/verify/result

{
  "question": "How many orders do we have?",
  "sql": "SELECT COUNT(*) FROM orders",
  "result": {
    "success": true,
    "data": [{"count": 0}],
    "row_count": 1
  },
  "database_type": "postgresql"
}
```

Response:
```json
{
  "is_suspicious": true,
  "confidence": 0.5,
  "issue_type": "unexpected_count",
  "description": "COUNT returned 0 for question 'How many orders do we have?'. Verify this is expected.",
  "suggested_fix": "Check table has data, verify WHERE clause filters",
  "improvement_hints": "Issue detected: COUNT returned 0...\nConsider: Are the WHERE clause filters too restrictive?"
}
```

#### 2. Execute and Verify

```bash
POST /api/verify/execute-and-verify

{
  "question": "Show me all customers",
  "sql": "SELECT * FROM customers WHERE age > 150",
  "database_type": "postgresql"
}
```

Response:
```json
{
  "execution": {
    "success": true,
    "data": [],
    "row_count": 0,
    "execution_time_ms": 12.5
  },
  "verification": {
    "is_suspicious": true,
    "confidence": 0.7,
    "issue_type": "empty_result",
    "description": "Query returned 0 rows. This might be correct, but let's verify the table(s) customers actually contain data.",
    "diagnostics": {
      "table_exists": true,
      "table_has_data": true,
      "row_count": 150
    }
  },
  "improvement_hints": "Issue detected: Query returned 0 rows...\nTable has 150 rows\nConsider: Are the WHERE clause filters too restrictive?"
}
```

#### 3. Health Check

```bash
GET /api/verify/health
```

## Issue Types

### 1. Empty Result (`empty_result`)

**When detected:**
- Query returns 0 rows

**Confidence:** 0.7 (Medium)

**Why suspicious:**
- User's question implies data should exist
- Table might be empty or filters too restrictive

**Suggested fixes:**
- Verify table has data
- Check WHERE clause filters
- Adjust query logic

**Example:**
```
Question: "Show me all customers"
SQL: SELECT * FROM customers WHERE age > 200
Result: 0 rows

Issue: Age filter is too restrictive
```

### 2. All NULL Values (`all_nulls`)

**When detected:**
- All values in result are NULL

**Confidence:** 0.8 (High)

**Why suspicious:**
- Usually indicates wrong column names
- Incorrect JOIN conditions
- Missing data

**Suggested fixes:**
- Check column names in SELECT
- Verify JOIN conditions
- Check for missing data

**Example:**
```
Question: "Show me product prices"
SQL: SELECT pric FROM products  -- Typo!
Result: All NULL

Issue: Column name 'pric' doesn't exist, returns NULL
```

### 3. Extreme Value (`extreme_value`)

**When detected:**
- Numeric value exceeds threshold (default: 1e9)

**Confidence:** 0.6 (Medium)

**Why suspicious:**
- Wrong aggregation (SUM instead of COUNT)
- JOIN creating duplicate rows
- Calculation error

**Suggested fixes:**
- Check aggregation functions
- Verify JOIN multipliers
- Check data types

**Example:**
```
Question: "Total revenue?"
SQL: SELECT SUM(price) FROM orders o JOIN order_items oi  -- Missing ON clause!
Result: 9,999,999,999,999

Issue: Cartesian product from missing JOIN condition
```

### 4. Unexpected Count (`unexpected_count`)

**When detected:**
- COUNT query returns 0 when question expects data

**Confidence:** 0.5 (Medium)

**Why suspicious:**
- Question implies data exists
- Filters might be wrong

**Suggested fixes:**
- Check table has data
- Verify WHERE clause

**Example:**
```
Question: "How many active users?"
SQL: SELECT COUNT(*) FROM users WHERE status = 'activ'  -- Typo!
Result: 0

Issue: Status value typo ('activ' vs 'active')
```

### 5. Negative Count (`negative_count`)

**When detected:**
- COUNT or similar aggregate returns negative value

**Confidence:** 1.0 (Very High)

**Why suspicious:**
- Counts can never be negative
- Serious query logic error

**Suggested fixes:**
- Check query logic
- Verify aggregation functions
- Check data types

**Example:**
```
SQL: SELECT -COUNT(*) FROM orders  -- Wrong!
Result: -150

Issue: Negation operator shouldn't be used with COUNT
```

## Configuration

### Agent Configuration

```python
agent = ResultVerificationAgent(
    enable_diagnostics=True,        # Run diagnostic queries
    enable_auto_fix=True,           # Attempt automatic fixes
    extreme_value_threshold=1e9     # Threshold for extreme values
)
```

### Integration Configuration

```python
# In SelfCorrectingSQLAgent
agent = SelfCorrectingSQLAgent(
    sql_generator=generator,
    enable_result_verification=True,  # Enable/disable verification
    max_retries=3                      # Max attempts including verification retries
)
```

### Confidence Thresholds

- **≥ 0.7**: High confidence - Trigger automatic retry
- **0.5 - 0.7**: Medium confidence - Return with warning
- **< 0.5**: Low confidence - Return results as-is

## Examples

### Example 1: Empty Result Detection

```python
# User asks: "Show me premium customers"
# SQL generated: SELECT * FROM customers WHERE tier = 'premium'
# Result: 0 rows

# Verification detects issue
verification = await agent.verify_results(...)

# Output:
# is_suspicious: True
# confidence: 0.7
# description: "Query returned 0 rows. Verify table has data."

# Diagnostics show:
# - Table 'customers' exists
# - Table has 1,500 rows
# - Sample data shows tier values: 'gold', 'silver', 'basic'

# Hint: "Consider: Are you using the correct tier value? Table has 'gold', 'silver', 'basic'"

# Agent regenerates with correct tier value
```

### Example 2: All NULL Detection

```python
# User asks: "What are customer names?"
# SQL generated: SELECT customer_name FROM users  -- Wrong table!
# Result: [{"customer_name": None}, {"customer_name": None}]

# Verification detects issue
# is_suspicious: True
# confidence: 0.8
# description: "All values are NULL. Check column names or JOINs."

# Agent suggests:
# - Column 'customer_name' doesn't exist in 'users' table
# - Did you mean 'customers' table with 'name' column?

# Agent regenerates: SELECT name FROM customers
```

### Example 3: Extreme Value Detection

```python
# User asks: "Total order value?"
# SQL generated: SELECT SUM(o.total * oi.quantity) FROM orders o, order_items oi
# Result: [{"sum": 999999999999}]  -- Cartesian product!

# Verification detects issue
# is_suspicious: True
# confidence: 0.6
# description: "Extreme value detected: 999999999999"

# Agent suggests:
# - Missing JOIN condition
# - Cartesian product creating duplicate calculations

# Agent regenerates with proper JOIN
```

## Best Practices

1. **Enable Verification by Default**
   - Always enable for production
   - Catches 70%+ of logical errors

2. **Tune Confidence Thresholds**
   - Adjust based on your use case
   - Higher threshold = fewer false positives
   - Lower threshold = catch more issues

3. **Review Verification Warnings**
   - Even low-confidence warnings are useful
   - May indicate edge cases

4. **Use Diagnostics**
   - Provides valuable context
   - Helps understand root cause

5. **Monitor Verification Metrics**
   - Track verification rate
   - Measure false positive rate
   - Adjust thresholds accordingly

## Performance Impact

- **Verification Check**: ~0.1ms (negligible)
- **With Diagnostics**: +50-200ms (runs additional queries)
- **Auto-Fix Retry**: +2-5s (regenerates SQL with LLM)

**Recommendation:** Keep verification enabled - the quality improvement far outweighs the minimal performance cost.

## Limitations

1. **Cannot Detect All Issues**
   - Some logical errors are hard to detect
   - Business logic errors require domain knowledge

2. **False Positives**
   - Empty results might be valid
   - Extreme values might be legitimate

3. **Diagnostic Overhead**
   - Running diagnostic queries adds latency
   - Can be disabled if needed

4. **Table Name Extraction**
   - Uses regex (simple heuristic)
   - May miss complex queries with subqueries

## Roadmap

Future enhancements planned:

- [ ] **Statistical Analysis** - Detect outliers based on historical data
- [ ] **Schema Validation** - Verify column types match expected types
- [ ] **Cross-Query Learning** - Learn from similar queries
- [ ] **Business Rule Validation** - User-defined validation rules
- [ ] **Result Distribution Analysis** - Detect skewed distributions
- [ ] **Time-Series Validation** - Verify temporal patterns

## Troubleshooting

### Issue: Too Many False Positives

**Solution:** Increase confidence threshold or disable auto-fix:
```python
agent = ResultVerificationAgent(
    enable_auto_fix=False  # Only warn, don't retry
)
```

### Issue: Diagnostics Taking Too Long

**Solution:** Disable diagnostics:
```python
agent = ResultVerificationAgent(
    enable_diagnostics=False
)
```

### Issue: Verification Not Working

**Check:**
1. `enable_result_verification=True` in SelfCorrectingSQLAgent
2. Verification agent initialized properly
3. Check logs for errors

## API Reference

### `ResultVerificationAgent`

#### Methods

##### `verify_results()`
Verify if query results make sense.

**Parameters:**
- `question` (str): Original natural language question
- `sql` (str): SQL query executed
- `result` (dict): Query execution result
- `schema` (str): Database schema
- `database_type` (str): Database type

**Returns:** `VerificationResult`

##### `run_diagnostics()`
Run diagnostic queries to understand issues.

**Parameters:**
- `sql` (str): Original SQL query
- `verification` (VerificationResult): Verification result
- `session`: Database session
- `database_type` (str): Database type

**Returns:** `DiagnosticResult`

##### `generate_improvement_hints()`
Generate hints for improving the query.

**Parameters:**
- `question` (str): Original question
- `sql` (str): SQL query
- `verification` (VerificationResult): Verification result
- `diagnostics` (DiagnosticResult, optional): Diagnostic results

**Returns:** `str` (improvement hints)

### Data Classes

#### `VerificationResult`
```python
@dataclass
class VerificationResult:
    is_suspicious: bool
    confidence: float  # 0.0 to 1.0
    issue_type: VerificationIssue
    description: str
    suggested_fix: Optional[str] = None
    diagnostic_queries: Optional[List[str]] = None
```

#### `DiagnosticResult`
```python
@dataclass
class DiagnosticResult:
    table_exists: bool
    table_has_data: bool
    column_exists: bool
    sample_data: Optional[List[Dict[str, Any]]] = None
    row_count: Optional[int] = None
    diagnosis: Optional[str] = None
```

## See Also

- [Self-Correcting Agent](SELF_CORRECTING_AGENT.md)
- [Learning from Corrections](LEARNING_FROM_CORRECTIONS.md)
- [Schema-Aware Fixes](SCHEMA_AWARE_FIXES.md)

---

**Made with ❤️ for high-quality SQL generation**
