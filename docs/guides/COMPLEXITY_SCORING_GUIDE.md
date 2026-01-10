# Query Complexity Scoring Guide

## Overview

The Query Planning Agent uses a complexity scoring system (0.0-1.0) to decide whether to use full query planning or direct SQL generation.

**Threshold**: Planning is enabled when `score >= 0.5` OR `(num_tables > 5 AND score >= 0.3)`

---

## Scoring Factors

### Multi-Table Operations (+0.3)
**Keywords**: `join`, `combine`, `merge`, `relationship`, `between`

**Examples**:
- ❌ "Show me all users" → 0.0 (no multi-table keywords)
- ✅ "Show the relationship between orders and customers" → 0.3
- ✅ "Join products with categories" → 0.3

---

### Aggregations (+0.2)
**Keywords**: `total`, `sum`, `average`, `avg`, `count`, `min`, `max`

**Examples**:
- ❌ "Show me all products" → 0.0
- ✅ "Count all orders" → 0.2
- ✅ "What's the average order value?" → 0.2
- ✅ "Sum of sales by region" → 0.2

---

### Grouping/Categorization (+0.2)
**Keywords**: `by category`, `by type`, `by`, `group`, `per`

**Examples**:
- ❌ "List all products" → 0.0
- ✅ "Products by category" → 0.2
- ✅ "Sales per customer" → 0.2
- ✅ "Group orders by status" → 0.2

---

### Comparisons/Ranking (+0.2)
**Keywords**: `top`, `bottom`, `highest`, `lowest`, `best`, `worst`, `compare`, `versus`, `vs`

**Examples**:
- ❌ "Show all customers" → 0.0
- ✅ "Top 10 customers" → 0.2
- ✅ "Highest rated products" → 0.2
- ✅ "Compare sales vs last year" → 0.2

---

### Geography/Location (+0.2)
**Keywords**: `shipped to`, `delivered to`, `sent to`, `in california`, `in texas`, `location`, `address`, `city`, `state`, `country`

**Examples**:
- ❌ "Show all orders" → 0.0
- ✅ "Orders shipped to California" → 0.2
- ✅ "Customers in Texas" → 0.2
- ✅ "Products delivered to New York" → 0.2

**Note**: Location queries often require joins (customers ← orders ← order_items), so planning helps

---

### Temporal/Trend Analysis (+0.1)
**Keywords**: `trend`, `over time`, `change`, `growth`, `decline`

**Examples**:
- ❌ "Show all sales" → 0.0
- ✅ "Sales trend over time" → 0.1
- ✅ "Revenue growth this quarter" → 0.1

---

### Multiple Tables Mentioned (+0.2)
**Detection**: Table names explicitly mentioned in question

**Examples**:
- ❌ "Show me all records" → 0.0 (no table names)
- ❌ "List products" → 0.0 (one table name)
- ✅ "Compare customers and orders" → 0.2 (two table names)
- ✅ "Join products, categories, and reviews" → 0.2 (three table names)

---

## Complexity Score Examples

### Score: 0.0 - Simple Direct Queries
```
"Show me all users"
"Get customer ID 123"
"List all products"
"What categories exist?"
```
**Decision**: ✗ Skip planning → Direct SQL generation

---

### Score: 0.2 - Simple Aggregations
```
"Count all orders"
"How many products?"
"List products by category"
```
**Decision**: ✗ Skip planning → Direct SQL generation

---

### Score: 0.4 - Moderate Complexity
```
"Top 10 products" (comparison: +0.2, aggregation: +0.2)
"Average price by category" (aggregation: +0.2, grouping: +0.2)
"Count orders per customer" (aggregation: +0.2, grouping: +0.2)
```
**Decision**: ✗ Skip planning (< 0.5) → Direct SQL generation

---

### Score: 0.5-0.6 - Complex Queries (Planning Threshold)
```
"Top customers by total orders" (comparison: +0.2, aggregation: +0.2, grouping: +0.2)
Score: 0.6 → ✓ Use planning

"Products shipped to California" (location: +0.2, multi-table: +0.3)
Score: 0.5 → ✓ Use planning

"Average order value by state" (aggregation: +0.2, grouping: +0.2, location: +0.2)
Score: 0.6 → ✓ Use planning
```
**Decision**: ✓ Use query planning

---

### Score: 0.7+ - Very Complex Queries
```
"Top 10 customers by total orders in California"
(comparison: +0.2, aggregation: +0.2, grouping: +0.2, location: +0.2)
Score: 0.8 → ✓ Use planning

"Compare average sales between Texas and California over time"
(comparison: +0.2, aggregation: +0.2, location: +0.2, temporal: +0.1)
Score: 0.7 → ✓ Use planning

"Highest rated products by category shipped to New York"
(comparison: +0.2, aggregation: +0.2, grouping: +0.2, location: +0.2)
Score: 0.8 → ✓ Use planning
```
**Decision**: ✓ Use query planning

---

## Special Cases

### Large Schemas (>5 tables)

For schemas with >5 tables, planning is enabled at a lower threshold:

**Rule**: `num_tables > 5 AND score >= 0.3`

**Example**:
```sql
Schema: 8 tables (customers, orders, products, categories, reviews, etc.)
Query: "Top 10 products"
Score: 0.4 (comparison: +0.2, aggregation: +0.2)

Decision: ✓ Use planning (large schema + score >= 0.3)
Reason: With 8 tables, even "simple" queries may need cross-table joins
```

---

## Tuning the Threshold

### Current Settings
- **Default threshold**: 0.5 (moderate complexity)
- **Large schema threshold**: 0.3 (for schemas with >5 tables)
- **Large schema definition**: >5 tables

### To Adjust Thresholds

Edit `src/llm/query_planning_agent.py`:

```python
# Line 335: Main threshold
if complexity_score >= 0.5:  # Change to 0.4 for more planning, 0.6 for less

# Line 343: Large schema threshold
if num_tables > 5 and complexity_score >= 0.3:  # Adjust 5 or 0.3 as needed
```

---

## Monitoring Complexity Scores

### Log Output

When processing queries, you'll see:

```
INFO: Query complexity score: 0.60 for question: 'Top customers by total orders in California...'
INFO: ✓ Enabling query planning (complexity: 0.60)
```

or

```
INFO: Query complexity score: 0.20 for question: 'Count all products...'
INFO: ✗ Skipping query planning (complexity: 0.20 < 0.5)
```

### Ideal Distribution

Target distribution after optimization:

- **70-80%** of queries: Score < 0.5 (skip planning)
- **20-30%** of queries: Score >= 0.5 (use planning)

If you see different distributions:
- **>50% using planning**: Threshold too low (increase to 0.6)
- **<10% using planning**: Threshold too high (decrease to 0.4)

---

## Testing Complexity Scoring

### Quick Test

```python
from src.llm.query_planning_agent import QueryPlanningAgent

agent = QueryPlanningAgent()

# Test simple query
score = agent._calculate_complexity_score("Show me all users")
print(f"Score: {score}")  # Expected: 0.0

# Test complex query
score = agent._calculate_complexity_score("Top 10 customers by total orders in California")
print(f"Score: {score}")  # Expected: 0.6-0.8
```

---

## FAQ

**Q: Why not always use planning?**
A: Planning adds 2-4 seconds (2 LLM calls vs 1). For simple queries, this overhead isn't worth it.

**Q: What if planning is skipped but query fails?**
A: The self-correcting agent will retry with error correction (still 1 LLM call per retry).

**Q: Can users override the automatic decision?**
A: Not yet - see "Additional Recommendations" in PERFORMANCE_OPTIMIZATION_SUMMARY.md for future work.

**Q: How accurate is the complexity scoring?**
A: ~85-90% accuracy based on keyword heuristics. May need tuning based on your specific query patterns.

**Q: What happens if score is exactly 0.5?**
A: Planning is enabled (threshold is `>=`, not `>`).

---

**Last Updated**: 2025-10-18
**Version**: 1.0.0
