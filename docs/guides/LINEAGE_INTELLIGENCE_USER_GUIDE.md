# Lineage Intelligence User Guide

This guide covers the LLM-powered Lineage Intelligence features in Database Guru (Phase 12), which transform technical data lineage into actionable insights.

## Overview

Lineage Intelligence adds five powerful capabilities on top of the core Data Lineage system:

| Phase | Feature | Purpose |
|-------|---------|---------|
| 12.1 | **Lineage Narrator** | Natural language explanations of data flow |
| 12.2 | **Impact Advisor** | Migration plans and SQL patches for schema changes |
| 12.3 | **Schema Health Analyzer** | Database design quality grading (A-F) |
| 12.4 | **Pattern Intelligence** | Bottleneck analysis and optimization suggestions |
| 12.5 | **Conversational Lineage** | Natural language Q&A about your schema |

## Getting Started

### Prerequisites

- Database Guru running with Ollama
- At least one database connection configured
- Some query history (for pattern analysis)

### Accessing Lineage Intelligence

Navigate to the **Lineage** tab in the main navigation. You'll find these panels:

- **Explore** - Parse SQL and view lineage (with optional narrative)
- **Health** - Schema health dashboard
- **Patterns** - Enhanced pattern analytics
- **Chat** - Natural language Q&A

## Feature Guide

### 1. Lineage Narrator (Phase 12.1)

Transform technical lineage graphs into business-friendly explanations.

#### How to Use

1. Go to **Lineage > Explore**
2. Enter your SQL query
3. Check the **"Generate Explanation"** checkbox
4. Click **Parse**
5. View the narrative panel alongside the graph

#### What You Get

- **Summary**: 2-3 sentence business overview
- **Data Flow Description**: Step-by-step data movement
- **Column Explanations**: What each output column means
- **Transformation Details**: Business meaning of aggregations, joins, etc.
- **Potential Issues**: Data quality concerns detected

#### Example

```sql
SELECT
  c.name,
  SUM(o.total) as lifetime_value
FROM customers c
JOIN orders o ON c.id = o.customer_id
WHERE o.status = 'completed'
GROUP BY c.name
```

**Generated Narrative:**
> "This query calculates customer lifetime value by summing all completed order totals per customer.
> Data flows from the customers table (providing customer names) and the orders table (providing purchase amounts),
> joined on customer_id. The SUM aggregation groups orders by customer to produce total spending.
> This metric is useful for identifying high-value customers and prioritizing retention efforts."

#### API Usage

```bash
curl -X POST "http://localhost:8000/api/lineage/parse?explain=true" \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "SELECT c.name, SUM(o.total) FROM customers c JOIN orders o...",
    "question": "Show me customer lifetime values"
  }'
```

---

### 2. Impact Advisor (Phase 12.2)

Get LLM-enhanced recommendations before making schema changes.

#### How to Use

1. Go to **Lineage > Impact**
2. Select change type (rename column, drop column, etc.)
3. Enter table name and column name
4. Optionally enter new value (for renames)
5. Check **"Include SQL Patches"** for auto-generated fixes
6. Click **Analyze Impact**

#### What You Get

- **Risk Explanation**: Why this change is risky in business terms
- **Migration Plan**: Step-by-step guide with SQL
- **SQL Patches**: Corrected queries for all affected queries
- **Rollback Strategy**: How to undo if needed

#### Supported Change Types

| Change Type | Description |
|-------------|-------------|
| `rename_column` | Rename a column in a table |
| `drop_column` | Remove a column from a table |
| `rename_table` | Rename an entire table |
| `change_type` | Change column data type |

#### Example

**Change**: Rename `customers.state` to `customers.region`

**Impact Advice:**
```
Risk Level: MEDIUM (15 queries affected)

Migration Plan:
1. Add new column 'region' (reversible)
2. Copy data: UPDATE customers SET region = state
3. Update application queries (see patches below)
4. Verify application works
5. Drop old column 'state' (after validation period)

SQL Patches:
- Query #123: SELECT * FROM customers WHERE state = 'CA'
  -> SELECT * FROM customers WHERE region = 'CA'
- Query #456: SELECT state, COUNT(*) FROM customers GROUP BY state
  -> SELECT region, COUNT(*) FROM customers GROUP BY region
```

#### API Usage

```bash
curl -X POST http://localhost:8000/api/lineage/impact/advise \
  -H "Content-Type: application/json" \
  -d '{
    "change_type": "rename_column",
    "table_name": "customers",
    "column_name": "state",
    "new_value": "region",
    "include_patches": true
  }'
```

---

### 3. Schema Health Analyzer (Phase 12.3)

Get a comprehensive assessment of your database design quality.

#### How to Use

1. Go to **Lineage > Health**
2. Select a database connection
3. View the health dashboard automatically

#### Health Grades

| Grade | Score | Meaning |
|-------|-------|---------|
| **A** | 90-100 | Excellent - Well-designed schema |
| **B** | 80-89 | Good - Minor improvements possible |
| **C** | 70-79 | Fair - Several issues detected |
| **D** | 60-69 | Poor - Significant problems |
| **F** | <60 | Critical - Requires immediate attention |

#### What You Get

**Index Suggestions:**
- Missing indexes based on query patterns
- CREATE INDEX SQL ready to copy
- Estimated impact (low/medium/high)
- Number of queries that would benefit

**Normalization Issues:**
- 1NF violations (repeating groups)
- 2NF violations (partial dependencies)
- 3NF violations (transitive dependencies)
- Recommendations for fixing

**Anti-Patterns Detected:**
- Tables without primary keys
- Wide tables (too many columns)
- Poor naming conventions
- Missing foreign key constraints
- God tables (does too much)

**Per-Table Summary:**
- Column count, index count
- Primary key status
- Foreign key relationships
- Table-specific issues

#### Example Dashboard

```
Schema Health: B (Score: 84/100)
Database: sample_ecommerce.db

Issues Found: 7 (2 Critical, 3 Warning, 2 Info)

Index Suggestions (3):
- orders(customer_id) - 45 queries would benefit
- order_items(product_id) - 32 queries would benefit
- products(category_id) - 18 queries would benefit

Anti-Patterns (2):
- reviews table has no primary key [CRITICAL]
- orders table has 25 columns (consider splitting) [WARNING]
```

#### API Usage

```bash
curl http://localhost:8000/api/lineage/schema/health/1?include_patterns=true
```

---

### 4. Pattern Intelligence (Phase 12.4)

Get LLM-enhanced insights into your query patterns.

#### How to Use

1. Go to **Lineage > Patterns**
2. Select connection and time range
3. Switch between views:
   - **Analysis** - Full pattern intelligence report
   - **Bottlenecks** - Detailed bottleneck analysis
   - **Trends** - Usage trends over time

#### What You Get

**Bottleneck Analysis:**
- Root cause identification (why is it slow?)
- Contributing factors
- Specific optimization suggestions
- Estimated improvement potential

**Anti-Pattern Detection:**
- SELECT * usage (fetching unnecessary columns)
- N+1 queries (multiple queries in loops)
- Cartesian joins (missing JOIN conditions)
- Missing WHERE clauses
- Occurrence counts and sample queries

**Optimization Suggestions:**
- Prioritized list (1 = highest priority)
- Category (index, query_rewrite, caching, schema)
- Implementation SQL
- Estimated impact

**Usage Trends:**
- Table usage over time (daily/weekly)
- Trend direction (increasing/decreasing/stable)
- Change percentage
- Emerging and declining tables

#### Example Analysis

```
Pattern Intelligence Report
Connection: Production DB | Last 30 Days

Bottlenecks (2):
- orders table
  Score: 0.85 (HIGH)
  Root Causes:
  - No index on created_at (used in 67% of queries)
  - Full table scans for date range queries
  Suggestion: CREATE INDEX idx_orders_created ON orders(created_at)
  Estimated Improvement: HIGH (2-3x faster queries)

Anti-Patterns (3):
- SELECT * (15 occurrences)
  Affected: 15 queries
  Recommendation: Select only needed columns
- N+1 Query Pattern (8 occurrences)
  Sample: SELECT * FROM orders WHERE customer_id = ?
  Recommendation: Use JOIN or batch queries
```

#### API Usage

```bash
# Full pattern analysis
curl http://localhost:8000/api/lineage/patterns/1/analyze?time_range=30

# Specific bottleneck analysis
curl http://localhost:8000/api/lineage/patterns/1/bottlenecks/orders
```

---

### 5. Conversational Lineage (Phase 12.5)

Ask questions about your schema in natural language.

#### How to Use

1. Go to **Lineage > Chat**
2. Type your question
3. View the answer with supporting data
4. Ask follow-up questions (context is maintained)

#### Question Types

| Type | Example Questions |
|------|------------------|
| **Lineage** | "What feeds into the revenue column?" |
| **Impact** | "What breaks if I rename customers.state?" |
| **Pattern** | "What are the most used tables?" |
| **Schema** | "What columns does the orders table have?" |
| **Recommendation** | "How can I speed up my queries?" |
| **General** | "Describe the database structure" |

#### Example Conversation

```
User: What are the most used tables?
AI: Based on query patterns from the last 30 days, your most used tables are:
    1. orders (45% of queries) - Primary transaction table
    2. customers (30%) - Frequently joined with orders
    3. products (25%) - Used in catalog queries

    The orders table shows signs of being a bottleneck.
    Would you like optimization suggestions?

User: Yes, how can I optimize the orders table?

AI: Here are my recommendations for optimizing the orders table:

    1. Add index on created_at (HIGH priority)
       - 67% of queries filter by date
       - SQL: CREATE INDEX idx_orders_created ON orders(created_at)

    2. Add composite index on (customer_id, status)
       - Common filter combination
       - Estimated 2-3x speedup

    3. Consider partitioning by month
       - Large table (>1M rows)
       - Historical queries rarely access old data
```

#### API Usage

```bash
curl -X POST http://localhost:8000/api/lineage/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What tables are used most frequently?",
    "connection_id": 1,
    "session_id": "optional-for-context"
  }'
```

#### Follow-Up Suggestions

After each answer, the system suggests related questions:
- "Would you like more details about X?"
- "Should I analyze the impact of Y?"
- "Want to see the lineage for Z?"

---

## Best Practices

### For Lineage Narratives
1. Include the original question for better context
2. Use for complex queries with multiple joins/aggregations
3. Share narratives with non-technical stakeholders

### For Impact Analysis
1. Always run before schema migrations
2. Review all HIGH risk queries manually
3. Test SQL patches in development first
4. Keep rollback strategies documented

### For Schema Health
1. Run weekly health checks
2. Address CRITICAL issues immediately
3. Plan sprints around index suggestions
4. Track score improvement over time

### For Pattern Intelligence
1. Review bottlenecks after performance issues
2. Address anti-patterns in code reviews
3. Monitor trends for capacity planning
4. Use insights for database optimization

### For Conversational Q&A
1. Start broad, then drill down
2. Use session_id for related questions
3. Follow up on suggestions
4. Save important answers for documentation

---

## Troubleshooting

### LLM Timeouts
- Ensure Ollama is running: `ollama serve`
- Check model is loaded: `ollama list`
- Increase timeout in settings if needed

### Empty Narratives
- Verify SQL is valid
- Check lineage graph has nodes
- Try simpler queries first

### Health Analysis Fails
- Ensure connection is active
- Check database permissions
- Verify schema is accessible

### Pattern Analysis Empty
- Need query history (run some queries first)
- Check time range includes queries
- Verify connection ID is correct

### Chat Not Responding
- Check Ollama connection
- Verify connection_id is valid
- Try simpler questions first

---

## Architecture

### Backend Components

```
src/lineage/
├── lineage_narrator.py           # Phase 12.1 (553 lines)
├── impact_advisor.py             # Phase 12.2 (796 lines)
├── schema_health_analyzer.py     # Phase 12.3 (1105 lines)
├── pattern_intelligence.py       # Phase 12.4 (959 lines)
└── lineage_conversation_agent.py # Phase 12.5 (1055 lines)
```

### Frontend Components

```
frontend/src/components/lineage/
├── LineageNarrative.tsx      # Narrative display
├── ImpactAdvisorPanel.tsx    # Impact analysis UI
├── LineageChat.tsx           # Conversational interface
└── QueryPatternHeatmap.tsx   # Enhanced patterns

frontend/src/components/schema/
└── SchemaHealthDashboard.tsx # Health dashboard
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/lineage/parse?explain=true` | POST | Parse with narrative |
| `/api/lineage/impact/advise` | POST | Impact advice |
| `/api/lineage/schema/health/{id}` | GET | Schema health |
| `/api/lineage/patterns/{id}/analyze` | GET | Pattern intelligence |
| `/api/lineage/patterns/{id}/bottlenecks/{table}` | GET | Bottleneck detail |
| `/api/lineage/ask` | POST | Conversational Q&A |

---

## Related Documentation

- [Data Lineage Guide](DATA_LINEAGE_GUIDE.md) - Core lineage features
- [Lineage Intelligence Testing Guide](testing/LINEAGE_INTELLIGENCE_TESTING.md) - How to test
- [Multi-Database Validation Guide](MULTI_DB_VALIDATION_GUIDE.md) - Query validation
- [Query Planning Agent](../modules/QUERY_PLANNING_AGENT.md) - Query planning
