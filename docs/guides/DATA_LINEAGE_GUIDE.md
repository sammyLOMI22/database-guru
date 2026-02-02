# Data Lineage & Impact Analysis Guide

This guide covers the Data Lineage feature in Database Guru, which provides column-level lineage visualization, schema change impact analysis, and query pattern analytics.

## Overview

The Data Lineage system helps you understand:
- **Data Flow**: How data moves from source tables through transformations to output columns
- **Schema Impact**: Which queries will be affected by schema changes
- **Query Patterns**: Which tables are heavily queried and potential bottlenecks

## Features

### 1. SQL Lineage Visualization

Parse any SQL query and visualize the complete data flow:

```sql
SELECT c.name, SUM(o.total) as revenue
FROM customers c
JOIN orders o ON c.id = o.customer_id
WHERE o.status = 'completed'
GROUP BY c.name
```

This generates a lineage graph showing:
- Source tables: `customers`, `orders`
- Source columns: `c.name`, `o.total`, `o.customer_id`, `o.status`
- Transformations: JOIN, SUM aggregation, GROUP BY
- Output columns: `name`, `revenue`

#### Node Types

| Type | Description | Color |
|------|-------------|-------|
| SOURCE_TABLE | Database table | Blue |
| SOURCE_COLUMN | Column from source table | Indigo |
| TRANSFORMATION | SQL operation (JOIN, SUM, etc.) | Purple |
| OUTPUT_COLUMN | Result column | Green |

#### Edge Types

| Type | Description | Color |
|------|-------------|-------|
| direct | Direct column mapping | Indigo |
| contains | Table contains column | Blue |
| feeds | Column feeds transformation | Purple |
| produces | Transformation produces output | Green |
| join | JOIN relationship | Amber |
| filter | WHERE/HAVING filter | Red |
| data_flow | General data flow | Gray |

### 2. Schema Change Impact Analysis

Before modifying your database schema, understand which queries will be affected:

#### Risk Levels

| Level | Affected Queries | Recommendation |
|-------|------------------|----------------|
| LOW | < 5 queries | Safe to proceed |
| MEDIUM | 5-20 queries | Review carefully |
| HIGH | > 20 queries | Plan migration strategy |

#### Impact Types

- **SELECT**: Column used in output (SELECT clause)
- **FILTER**: Column used in WHERE/HAVING conditions
- **JOIN**: Table/column used in JOIN conditions
- **GROUP**: Column used in GROUP BY clause
- **ORDER**: Column used in ORDER BY clause

### 3. Query Pattern Analytics

Analyze query patterns to identify optimization opportunities:

#### Table Usage Frequency
Shows which tables are queried most frequently. Use this to:
- Prioritize index optimization
- Consider caching strategies
- Plan for scaling

#### Common Join Patterns
Shows frequently joined table pairs with sample SQL. Use this to:
- Add indexes on join columns
- Consider denormalization
- Optimize join order

#### Performance Bottlenecks
Identifies tables with high query frequency AND high average latency.
Bottleneck score = normalized_frequency × normalized_latency (0-1 scale)

## UI Guide

### Accessing Lineage

Navigate to the **Lineage** tab in the main navigation.

### Explore Tab

1. Enter SQL in the text area
2. Click "Parse" or press Ctrl+Enter
3. View the interactive lineage graph
4. Click nodes to highlight connected paths

**Features:**
- Auto-layout with Dagre engine
- MiniMap for navigation
- Zoom and pan controls
- Node selection highlighting

### History Tab

View lineage for previously executed queries:
1. Select a query from history
2. View its lineage graph
3. Track column-level data flow

### Impact Tab

Analyze schema change impact:
1. Enter table name (required)
2. Optionally enter column name
3. Click "Analyze Impact"
4. Review affected queries with risk levels

### Patterns Tab

View query pattern heatmap:
1. Select connection (or "All connections")
2. Select time range (7d, 30d, 90d, All)
3. Switch between views:
   - **Frequency**: Table usage counts
   - **Joins**: Common join patterns
   - **Performance**: Bottleneck identification

## API Reference

### Parse SQL

```bash
POST /api/lineage/parse
Content-Type: application/json

{
  "sql": "SELECT * FROM customers JOIN orders ON ...",
  "connection_id": 1
}
```

**Response:**
```json
{
  "nodes": [
    {"id": "table_customers", "type": "source_table", "label": "customers"},
    {"id": "col_name", "type": "output_column", "label": "name"}
  ],
  "edges": [
    {"source": "table_customers", "target": "col_name", "edge_type": "direct"}
  ],
  "tables_used": ["customers", "orders"],
  "columns_used": ["name", "id"],
  "output_columns": ["name", "total"]
}
```

### Analyze Impact

```bash
POST /api/lineage/impact
Content-Type: application/json

{
  "table_name": "customers",
  "column_name": "state"
}
```

**Response:**
```json
{
  "risk_level": "MEDIUM",
  "affected_count": 15,
  "risk_counts": {"LOW": 5, "MEDIUM": 8, "HIGH": 2},
  "summary": "15 queries affected by change to customers.state",
  "affected_queries": [
    {
      "query_id": 123,
      "question": "Show customers in California",
      "sql": "SELECT * FROM customers WHERE state = 'CA'",
      "risk_level": "MEDIUM",
      "impact_type": "FILTER"
    }
  ]
}
```

### Get Query Pattern Heatmap

```bash
GET /api/lineage/patterns/{connection_id}?time_range=30
```

**Response:**
```json
{
  "table_usage": [
    {"table_name": "orders", "query_count": 150, "join_count": 45, "avg_execution_time_ms": 120}
  ],
  "join_patterns": [
    {"table1": "orders", "table2": "customers", "join_count": 45, "sample_sql": "..."}
  ],
  "bottlenecks": [
    {"table_name": "orders", "query_count": 150, "avg_execution_time_ms": 120, "bottleneck_score": 0.85}
  ],
  "time_range_days": 30,
  "total_queries_analyzed": 500
}
```

### Get Query Lineage

```bash
GET /api/lineage/query/{query_id}
```

### Get Table Queries

```bash
GET /api/lineage/table/{table_name}/queries
```

### Get Statistics

```bash
GET /api/lineage/stats
```

## SQL Parsing Capabilities

The lineage parser supports:

### Queries
- Simple SELECT statements
- Multi-table JOINs (INNER, LEFT, RIGHT, FULL)
- Subqueries in WHERE/HAVING clauses
- UNION/INTERSECT/EXCEPT

### Columns
- Direct column references (`name`, `t.name`)
- Aliased columns (`name AS customer_name`)
- SELECT * expansion
- Schema-qualified names (`public.orders`)

### Transformations
- Aggregations: COUNT, SUM, AVG, MIN, MAX, GROUP_CONCAT, STRING_AGG
- Functions: COALESCE, UPPER, LOWER, TRIM, ROUND, etc.
- CASE expressions
- Arithmetic expressions
- Date functions

### Clauses
- FROM with multiple tables
- JOIN with ON conditions
- WHERE with complex predicates
- GROUP BY
- HAVING
- ORDER BY

## Best Practices

### Impact Analysis
1. Run impact analysis before any schema migration
2. Review HIGH risk queries first
3. Update application code before schema changes
4. Test affected queries after migration

### Query Optimization
1. Check bottlenecks regularly (weekly)
2. Add indexes for frequently joined columns
3. Consider query caching for hot tables
4. Monitor pattern changes over time

### Lineage Tracking
1. Parse critical queries to understand data flow
2. Document lineage for compliance requirements
3. Use lineage to trace data quality issues
4. Share lineage graphs with stakeholders

## Troubleshooting

### Parser Errors
- Ensure SQL is syntactically valid
- Check for database-specific syntax (parser uses standard SQL)
- Complex CTEs may not fully parse

### Empty Results
- Verify the query has been executed (history queries only)
- Check connection ID is correct
- Ensure time range includes relevant queries

### Performance
- Pattern analysis limited to 2,000 queries for performance
- Use time range filters to reduce dataset
- Connection filtering improves response time

## Architecture

### Backend Components

```
src/lineage/
├── __init__.py
├── sql_lineage_parser.py   # SQL parsing (835 lines)
├── impact_analyzer.py      # Impact analysis (341 lines)
└── query_pattern_analyzer.py # Pattern analytics (399 lines)

src/api/endpoints/
└── lineage.py              # REST API (227 lines)
```

### Frontend Components

```
frontend/src/components/lineage/
├── LineagePanel.tsx        # Main container
├── LineageGraph.tsx        # React Flow visualization
├── LineageNode.tsx         # Custom node component
├── LineageEdge.tsx         # Custom edge component
├── ColumnLineage.tsx       # Table view
├── ImpactAnalysisPanel.tsx # Impact analysis
├── ImpactedQueryCard.tsx   # Query card
└── QueryPatternHeatmap.tsx # Heatmap view

frontend/src/
├── types/lineage.ts        # TypeScript types
├── services/lineageApi.ts  # API client
└── utils/lineageLayoutUtils.ts # Layout engine
```

### Data Flow

```
User SQL → SQLLineageParser → LineageGraph (nodes, edges)
                                    ↓
                              LineageGraph.tsx (React Flow)
                                    ↓
                              Interactive Visualization
```

## Phase 12: Lineage Intelligence

The Data Lineage system has been enhanced with LLM-powered intelligence features:

| Phase | Feature | Description |
|-------|---------|-------------|
| 12.1 | **Lineage Narrator** | Natural language explanations of data flow |
| 12.2 | **Impact Advisor** | Migration plans and SQL patches for schema changes |
| 12.3 | **Schema Health Analyzer** | Database design quality grading (A-F) |
| 12.4 | **Pattern Intelligence** | Bottleneck analysis and optimization suggestions |
| 12.5 | **Conversational Lineage** | Natural language Q&A about your schema |

### Quick Start with Phase 12

**Enable Narrative Generation:**
```bash
# Add explain=true to get LLM-generated narrative
curl -X POST "http://localhost:8000/api/lineage/parse?explain=true" \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT * FROM customers JOIN orders ON ..."}'
```

**Get Schema Health:**
```bash
curl http://localhost:8000/api/lineage/schema/health/1
```

**Ask Questions:**
```bash
curl -X POST http://localhost:8000/api/lineage/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What tables are used most?", "connection_id": 1}'
```

See [Lineage Intelligence User Guide](LINEAGE_INTELLIGENCE_USER_GUIDE.md) for complete Phase 12 documentation.

## Related Documentation

- [Lineage Intelligence User Guide](LINEAGE_INTELLIGENCE_USER_GUIDE.md) - LLM-powered lineage features (Phase 12)
- [Lineage Intelligence Testing Guide](testing/LINEAGE_INTELLIGENCE_TESTING.md) - How to test Phase 12
- [Multi-Database Validation Guide](MULTI_DB_VALIDATION_GUIDE.md) - Pre-flight query validation
- [SQL Generation Pipeline](../technical/SQL_GENERATION_PIPELINE.md) - Query processing flow
- [Query Planning Agent](../modules/QUERY_PLANNING_AGENT.md) - Query planning system
