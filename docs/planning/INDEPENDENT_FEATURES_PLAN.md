# Independent Features Plan: Streaming, Preprocessing & Pattern Learning

**Last Updated**: January 25, 2026
**Status**: Planning
**Priority**: Medium (can start anytime - no dependencies)

---

## Overview

This document consolidates three independent features that can be implemented in any order without blocking dependencies. These features enhance different aspects of Database Guru:

| Feature | Category | Impact | Est. Effort |
|---------|----------|--------|-------------|
| **Streaming Results** | Performance/UX | Large dataset handling | 1-2 weeks |
| **Advanced Preprocessing** | SQL Accuracy | Better first-attempt success | 2-3 days |
| **Pattern Learning** | Intelligence | Continuous improvement | 4-5 days |

---

## Feature 1: Streaming Results (SSE)

### Problem Statement

Current behavior: Query execution blocks until all results are fetched, then renders the entire table at once. For large datasets (10K+ rows), users see a loading spinner for extended periods with no feedback.

**User Pain Points:**
- No progress indication for long-running queries
- Memory pressure when loading 100K+ rows at once
- Poor UX - users don't know if query is running or hung

### Solution: Server-Sent Events (SSE)

Implement real-time streaming of query results with progressive rendering.

### Backend Implementation

**File:** `src/api/endpoints/query_stream.py`

```python
from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse
import json

router = APIRouter(prefix="/api/query", tags=["query-stream"])

@router.get("/stream/{query_id}")
async def stream_query_results(query_id: str):
    """Stream query results using Server-Sent Events."""

    async def event_generator():
        # 1. Send metadata first (columns, estimated rows)
        yield {
            "event": "metadata",
            "data": json.dumps({
                "columns": ["id", "name", "created_at"],
                "estimated_rows": 50000,
                "query_id": query_id
            })
        }

        # 2. Stream rows in batches
        async for batch in execute_streaming_query(query_id, batch_size=100):
            yield {
                "event": "rows",
                "data": json.dumps({
                    "rows": batch,
                    "count": len(batch)
                })
            }

            # 3. Send progress updates
            yield {
                "event": "progress",
                "data": json.dumps({
                    "rows_sent": current_count,
                    "percentage": (current_count / total) * 100
                })
            }

        # 4. Send completion
        yield {
            "event": "complete",
            "data": json.dumps({
                "total_rows": final_count,
                "elapsed_ms": elapsed,
                "success": True
            })
        }

    return EventSourceResponse(event_generator())
```

**Streaming Query Executor:**

```python
# src/core/streaming_executor.py
from typing import AsyncIterator, List, Dict, Any

class StreamingQueryExecutor:
    """Executes queries with row-by-row streaming."""

    def __init__(self, batch_size: int = 100):
        self.batch_size = batch_size

    async def execute_streaming(
        self,
        connection_id: int,
        sql: str
    ) -> AsyncIterator[List[Dict[str, Any]]]:
        """
        Execute query and yield results in batches.

        Uses server-side cursors where supported:
        - PostgreSQL: DECLARE CURSOR
        - MySQL: mysql.connector with buffered=False
        - SQLite: fetchmany with arraysize
        - DuckDB: Arrow batched reads
        """
        session = await get_session(connection_id)

        # Execute query
        result = await session.execute(text(sql))

        # Stream in batches
        while True:
            batch = result.fetchmany(self.batch_size)
            if not batch:
                break
            yield [dict(row._mapping) for row in batch]
```

### Frontend Implementation

**File:** `frontend/src/hooks/useStreamingQuery.ts`

```typescript
import { useState, useCallback, useRef } from 'react';

interface StreamingState {
  status: 'idle' | 'connecting' | 'streaming' | 'complete' | 'error';
  rows: any[];
  columns: string[];
  progress: number;
  totalRows: number | null;
  error: string | null;
}

export function useStreamingQuery() {
  const [state, setState] = useState<StreamingState>({
    status: 'idle',
    rows: [],
    columns: [],
    progress: 0,
    totalRows: null,
    error: null,
  });

  const eventSourceRef = useRef<EventSource | null>(null);

  const startStreaming = useCallback((queryId: string) => {
    setState(prev => ({ ...prev, status: 'connecting', rows: [] }));

    const eventSource = new EventSource(`/api/query/stream/${queryId}`);
    eventSourceRef.current = eventSource;

    eventSource.addEventListener('metadata', (e) => {
      const data = JSON.parse(e.data);
      setState(prev => ({
        ...prev,
        status: 'streaming',
        columns: data.columns,
        totalRows: data.estimated_rows,
      }));
    });

    eventSource.addEventListener('rows', (e) => {
      const data = JSON.parse(e.data);
      setState(prev => ({
        ...prev,
        rows: [...prev.rows, ...data.rows], // Append new rows
      }));
    });

    eventSource.addEventListener('progress', (e) => {
      const data = JSON.parse(e.data);
      setState(prev => ({
        ...prev,
        progress: data.percentage,
      }));
    });

    eventSource.addEventListener('complete', (e) => {
      const data = JSON.parse(e.data);
      setState(prev => ({
        ...prev,
        status: 'complete',
        totalRows: data.total_rows,
      }));
      eventSource.close();
    });

    eventSource.addEventListener('error', (e) => {
      setState(prev => ({
        ...prev,
        status: 'error',
        error: 'Stream connection failed',
      }));
      eventSource.close();
    });
  }, []);

  const stopStreaming = useCallback(() => {
    eventSourceRef.current?.close();
    setState(prev => ({ ...prev, status: 'idle' }));
  }, []);

  return { ...state, startStreaming, stopStreaming };
}
```

**Progressive Table Rendering:**

```typescript
// frontend/src/components/StreamingResultsTable.tsx
import { useVirtualizer } from '@tanstack/react-virtual';

export function StreamingResultsTable({
  rows,
  columns,
  progress,
  status
}: StreamingTableProps) {
  const parentRef = useRef<HTMLDivElement>(null);

  // Virtualize for performance with large datasets
  const rowVirtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 35, // row height
    overscan: 20,
  });

  return (
    <div className="streaming-table">
      {/* Progress indicator */}
      {status === 'streaming' && (
        <div className="progress-bar">
          <div
            className="progress-fill bg-blue-500"
            style={{ width: `${progress}%` }}
          />
          <span className="progress-text">
            {rows.length.toLocaleString()} rows loaded ({progress.toFixed(1)}%)
          </span>
        </div>
      )}

      {/* Virtualized table */}
      <div ref={parentRef} className="table-container h-[600px] overflow-auto">
        <table className="min-w-full">
          <thead className="sticky top-0 bg-gray-800">
            <tr>
              {columns.map(col => (
                <th key={col} className="px-4 py-2">{col}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rowVirtualizer.getVirtualItems().map(virtualRow => {
              const row = rows[virtualRow.index];
              return (
                <tr
                  key={virtualRow.index}
                  style={{
                    height: `${virtualRow.size}px`,
                    transform: `translateY(${virtualRow.start}px)`,
                  }}
                >
                  {columns.map(col => (
                    <td key={col} className="px-4 py-2">{row[col]}</td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

### SSE Message Types

| Event | Description | Data Fields |
|-------|-------------|-------------|
| `metadata` | Query info, column names | `columns`, `estimated_rows`, `query_id` |
| `rows` | Batch of result rows | `rows[]`, `count` |
| `progress` | Progress update | `rows_sent`, `percentage` |
| `complete` | Query finished | `total_rows`, `elapsed_ms`, `success` |
| `error` | Error occurred | `message`, `code`, `sql_state` |

### Implementation Tasks

1. **Backend SSE Endpoint** (1-2 days)
   - [ ] Add `sse-starlette` dependency
   - [ ] Create `/api/query/stream/{query_id}` endpoint
   - [ ] Implement `StreamingQueryExecutor` with database-specific cursors
   - [ ] Add streaming support to `SQLExecutor`
   - [ ] Handle connection timeouts and cleanup

2. **Frontend Streaming Hook** (1 day)
   - [ ] Create `useStreamingQuery` hook
   - [ ] Handle all SSE event types
   - [ ] Implement connection retry logic
   - [ ] Add cleanup on unmount

3. **Progressive Table Rendering** (2 days)
   - [ ] Integrate `@tanstack/react-virtual` for virtualization
   - [ ] Create `StreamingResultsTable` component
   - [ ] Add progress bar with row count
   - [ ] Implement smooth scroll during streaming

4. **Integration & Polish** (2 days)
   - [ ] Add streaming toggle in settings
   - [ ] Fallback to batch mode for small results
   - [ ] Handle streaming cancellation
   - [ ] Add streaming indicator to QueryResults

5. **Testing** (2 days)
   - [ ] Unit tests for streaming executor
   - [ ] Integration tests for SSE endpoint
   - [ ] Frontend tests for streaming hook
   - [ ] Performance tests with 100K+ rows

### Success Criteria

- [ ] SSE endpoint streams rows in real-time
- [ ] Frontend receives and renders rows progressively
- [ ] Progress indicator shows accurate percentage
- [ ] Large datasets (100K+ rows) render smoothly
- [ ] Memory usage stays stable during streaming
- [ ] Error handling preserves user context

---

## Feature 2: Advanced Preprocessing (Phase 2.3)

### Problem Statement

Current preprocessing only handles location normalization ("California" → "CA"). Users frequently ask queries involving dates, booleans, and status values that fail because the LLM doesn't know the exact database format.

**Common Failures:**
- "orders from last week" → LLM generates generic date syntax
- "active users" → LLM doesn't know if `status = 'active'` or `is_active = 1`
- "paid orders" → LLM doesn't know `payment_status = 'PAID'` vs `'paid'`

### Solution: Multi-Entity Preprocessing

Extend `QueryPreprocessor` to normalize dates, booleans, status values, and detect column formats.

### Implementation

**File:** `src/llm/advanced_preprocessor.py`

```python
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import re

@dataclass
class EntityNormalization:
    """Normalized entity with original and database-compatible forms."""
    original: str
    normalized: str
    entity_type: str  # "date", "boolean", "status", "currency"
    confidence: float
    sql_fragment: Optional[str] = None  # Ready-to-use SQL condition
    column_hint: Optional[str] = None

class AdvancedPreprocessor:
    """Extended preprocessor with multi-entity normalization."""

    def __init__(self, schema_inspector):
        self.schema = schema_inspector
        self._status_cache: Dict[str, List[str]] = {}

    def preprocess(self, question: str, connection_id: int) -> Dict:
        """
        Preprocess question with all normalizations.

        Returns enhanced context for SQL generation.
        """
        result = {
            "original_question": question,
            "normalized_question": question,
            "entities": [],
            "sql_hints": [],
            "warnings": []
        }

        # Apply normalizations in order
        result = self._normalize_dates(result)
        result = self._normalize_booleans(result, connection_id)
        result = self._normalize_status_values(result, connection_id)
        result = self._normalize_currency(result)

        return result

    def _normalize_dates(self, result: Dict) -> Dict:
        """Normalize date expressions to SQL-compatible forms."""

        patterns = [
            # Relative dates
            (r"last (\d+) days?", self._handle_relative_days),
            (r"last (\d+) weeks?", self._handle_relative_weeks),
            (r"last (\d+) months?", self._handle_relative_months),
            (r"past (\d+) days?", self._handle_relative_days),

            # Named periods
            (r"\btoday\b", lambda m: ("date(created_at) = date('now')", "today")),
            (r"\byesterday\b", lambda m: ("date(created_at) = date('now', '-1 day')", "yesterday")),
            (r"\bthis week\b", lambda m: self._this_period("week")),
            (r"\bthis month\b", lambda m: self._this_period("month")),
            (r"\bthis year\b", lambda m: self._this_period("year")),
            (r"\blast week\b", lambda m: self._last_period("week")),
            (r"\blast month\b", lambda m: self._last_period("month")),
            (r"\blast year\b", lambda m: self._last_period("year")),

            # Absolute dates (US format)
            (r"(\d{1,2})/(\d{1,2})/(\d{4})", self._handle_us_date),
            # ISO format
            (r"(\d{4})-(\d{2})-(\d{2})", self._handle_iso_date),
        ]

        question = result["normalized_question"]

        for pattern, handler in patterns:
            match = re.search(pattern, question, re.IGNORECASE)
            if match:
                sql_fragment, normalized = handler(match)
                result["entities"].append(EntityNormalization(
                    original=match.group(0),
                    normalized=normalized,
                    entity_type="date",
                    confidence=0.95,
                    sql_fragment=sql_fragment
                ))
                result["sql_hints"].append({
                    "type": "date_filter",
                    "original": match.group(0),
                    "sql": sql_fragment,
                    "note": f"'{match.group(0)}' interpreted as: {sql_fragment}"
                })

        return result

    def _handle_relative_days(self, match) -> Tuple[str, str]:
        n = match.group(1)
        return (
            f"created_at > datetime('now', '-{n} days')",
            f"last {n} days"
        )

    def _normalize_booleans(self, result: Dict, connection_id: int) -> Dict:
        """Normalize boolean expressions based on schema inspection."""

        # Common boolean column patterns
        boolean_columns = [
            "is_active", "is_enabled", "is_deleted", "is_verified",
            "active", "enabled", "deleted", "verified", "visible"
        ]

        # Detect actual boolean columns in schema
        schema = self.schema.get_schema(connection_id)
        detected_bool_cols = self._detect_boolean_columns(schema)

        # Boolean term mappings
        true_terms = ["active", "enabled", "verified", "visible", "yes", "on"]
        false_terms = ["inactive", "disabled", "unverified", "hidden", "no", "off"]

        question = result["normalized_question"].lower()

        for term in true_terms:
            if term in question:
                # Find matching column
                col = self._find_boolean_column(term, detected_bool_cols, schema)
                if col:
                    value = self._get_boolean_true_value(col, schema)
                    result["entities"].append(EntityNormalization(
                        original=term,
                        normalized=f"{col['name']} = {value}",
                        entity_type="boolean",
                        confidence=0.9,
                        sql_fragment=f"{col['name']} = {value}",
                        column_hint=col['name']
                    ))

        return result

    def _normalize_status_values(self, result: Dict, connection_id: int) -> Dict:
        """Normalize status-related terms to actual database values."""

        # Get cached status values or fetch from DB
        if connection_id not in self._status_cache:
            self._status_cache[connection_id] = self._sample_status_columns(connection_id)

        status_values = self._status_cache[connection_id]

        # Common status terms to look for
        status_terms = {
            "pending": ["pending", "wait", "queued"],
            "completed": ["completed", "complete", "done", "finished"],
            "shipped": ["shipped", "dispatched", "sent"],
            "cancelled": ["cancelled", "canceled", "voided"],
            "paid": ["paid", "settled", "cleared"],
            "failed": ["failed", "error", "rejected"],
        }

        question = result["normalized_question"].lower()

        for canonical, synonyms in status_terms.items():
            for term in synonyms:
                if term in question:
                    # Find actual value in database
                    actual_value = self._find_status_value(canonical, status_values)
                    if actual_value:
                        result["entities"].append(EntityNormalization(
                            original=term,
                            normalized=actual_value["value"],
                            entity_type="status",
                            confidence=0.85,
                            sql_fragment=f"{actual_value['column']} = '{actual_value['value']}'",
                            column_hint=actual_value['column']
                        ))
                        result["sql_hints"].append({
                            "type": "status_filter",
                            "original": term,
                            "column": actual_value['column'],
                            "value": actual_value['value'],
                            "note": f"'{term}' maps to {actual_value['column']} = '{actual_value['value']}'"
                        })
                    break

        return result

    def _sample_status_columns(self, connection_id: int) -> Dict:
        """Sample status/enum columns to discover actual values."""
        schema = self.schema.get_schema(connection_id)
        status_columns = {}

        for table_name, table in schema.get("tables", {}).items():
            for col in table.get("columns", []):
                # Heuristics for status columns
                if any(keyword in col["name"].lower()
                       for keyword in ["status", "state", "type", "category"]):
                    # Sample distinct values
                    values = self.schema.get_distinct_values(
                        connection_id, table_name, col["name"], limit=20
                    )
                    status_columns[f"{table_name}.{col['name']}"] = values

        return status_columns
```

**Column Format Detector:**

```python
# src/llm/column_format_detector.py

class ColumnFormatDetector:
    """Detects data format patterns in columns from sample values."""

    def detect_format(self, column_name: str, sample_values: List) -> Dict:
        """
        Analyze sample values to determine format.

        Returns:
            {
                "format": "location_code" | "date_iso" | "boolean_numeric" | ...,
                "confidence": 0.0-1.0,
                "sample_values": [...],
                "recommendation": "Use 'CA' instead of 'California'"
            }
        """
        if not sample_values:
            return {"format": "unknown", "confidence": 0.0}

        # Test each format detector
        detectors = [
            ("location_code", self._is_location_code),
            ("location_full", self._is_location_full),
            ("date_iso", self._is_date_iso),
            ("date_us", self._is_date_us),
            ("boolean_numeric", self._is_boolean_numeric),
            ("boolean_text", self._is_boolean_text),
            ("status_upper", self._is_status_upper),
            ("status_lower", self._is_status_lower),
            ("currency_symbol", self._is_currency_with_symbol),
            ("currency_numeric", self._is_currency_numeric),
            ("uuid", self._is_uuid),
            ("email", self._is_email),
        ]

        results = []
        for format_name, detector in detectors:
            confidence = detector(sample_values)
            if confidence > 0.7:
                results.append((format_name, confidence))

        if not results:
            return {"format": "unknown", "confidence": 0.0}

        # Return highest confidence format
        results.sort(key=lambda x: x[1], reverse=True)
        best_format, confidence = results[0]

        return {
            "format": best_format,
            "confidence": confidence,
            "sample_values": sample_values[:5],
            "recommendation": self._get_recommendation(best_format, sample_values)
        }

    def _is_location_code(self, values: List) -> float:
        """Check if values are 2-letter state/country codes."""
        if not values:
            return 0.0
        matches = sum(1 for v in values if isinstance(v, str) and len(v) == 2 and v.isupper())
        return matches / len(values)

    def _is_boolean_numeric(self, values: List) -> float:
        """Check if values are 0/1 booleans."""
        valid = {0, 1, '0', '1'}
        matches = sum(1 for v in values if v in valid)
        return matches / len(values) if values else 0.0

    def _is_status_upper(self, values: List) -> float:
        """Check if values are UPPERCASE status strings."""
        if not values:
            return 0.0
        matches = sum(1 for v in values
                     if isinstance(v, str) and v.isupper() and len(v) < 20)
        return matches / len(values)
```

### Implementation Tasks

1. **Advanced Preprocessor** (1.5 days)
   - [ ] Create `AdvancedPreprocessor` class extending current preprocessor
   - [ ] Implement date normalization with 10+ patterns
   - [ ] Implement boolean detection and normalization
   - [ ] Implement status value normalization with caching
   - [ ] Add currency handling ($100 → 100.00)

2. **Column Format Detector** (1 day)
   - [ ] Create `ColumnFormatDetector` class
   - [ ] Implement format detection for 12+ patterns
   - [ ] Add sample value caching per connection
   - [ ] Generate recommendations for LLM context

3. **Integration** (0.5 days)
   - [ ] Integrate with `SQLGenerator`
   - [ ] Add preprocessing hints to LLM prompt
   - [ ] Update API response to include normalizations
   - [ ] Add preprocessing toggle in settings

4. **UI Feedback** (0.5 days)
   - [ ] Show detected normalizations in query input
   - [ ] Add "understood as" tooltip for interpreted values
   - [ ] Display warnings for ambiguous terms

5. **Testing** (0.5 days)
   - [ ] Unit tests for each normalization type
   - [ ] Integration tests with real schemas
   - [ ] Edge case tests (ambiguous dates, mixed formats)

### Success Criteria

- [ ] Date expressions normalize correctly for all dialects
- [ ] Boolean terms map to correct column values
- [ ] Status values auto-detect from sample data
- [ ] Column formats detected with >80% accuracy
- [ ] SQL generation success rate improves by 10-15%

---

## Feature 3: Pattern Learning (Phase 2.6)

### Problem Statement

Each query starts fresh, even if similar queries have succeeded before. Successful query patterns aren't learned or reused, missing opportunities for faster and more accurate SQL generation.

**Opportunities Missed:**
- "Show sales by region" succeeded → similar queries should use same pattern
- User corrections create implicit training data
- Model performance varies by query type but isn't tracked

### Solution: Query Pattern Learning System

Learn from successful queries, track model performance, and reuse patterns for similar questions.

### Implementation

**Database Schema:**

```sql
-- src/database/models.py (additions)

class LearnedPattern(Base):
    """Stores learned SQL generation patterns."""
    __tablename__ = "learned_patterns"

    id = Column(Integer, primary_key=True)
    question_pattern = Column(String, index=True)  # Generalized question regex
    sql_template = Column(String)                   # Templatized SQL
    tables_pattern = Column(String)                 # Required tables (JSON)
    dialect = Column(String, index=True)            # postgresql, sqlite, etc.

    success_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)
    last_used = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    @property
    def confidence(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.5


class ModelPerformance(Base):
    """Tracks model performance by task type."""
    __tablename__ = "model_performance"

    id = Column(Integer, primary_key=True)
    model_name = Column(String, index=True)
    task_type = Column(String, index=True)  # sql_generation, correction, narrative

    total_attempts = Column(Integer, default=0)
    successful_attempts = Column(Integer, default=0)
    total_latency_ms = Column(BigInteger, default=0)
    total_tokens = Column(BigInteger, default=0)

    last_updated = Column(DateTime, default=datetime.utcnow)

    @property
    def success_rate(self) -> float:
        return self.successful_attempts / self.total_attempts if self.total_attempts > 0 else 0.0

    @property
    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / self.total_attempts if self.total_attempts > 0 else 0.0
```

**Pattern Learner:**

```python
# src/llm/pattern_learner.py

from dataclasses import dataclass
from typing import Optional, List, Dict
import re
from rapidfuzz import fuzz

@dataclass
class PatternMatch:
    """Result of pattern matching."""
    pattern_id: int
    sql_template: str
    confidence: float
    original_question: str
    applied_sql: str

class PatternLearner:
    """Learns and applies SQL patterns from successful queries."""

    def __init__(self, db_session, min_confidence: float = 0.8):
        self.db = db_session
        self.min_confidence = min_confidence
        self._pattern_cache: Dict[str, List] = {}

    async def learn_from_success(
        self,
        question: str,
        sql: str,
        schema: Dict,
        dialect: str
    ) -> Optional[int]:
        """
        Extract and store pattern from successful query.

        Returns pattern_id if new pattern created, None if existing updated.
        """
        # 1. Generalize the question into a pattern
        pattern = self._generalize_question(question)

        # 2. Templatize the SQL (replace literals with placeholders)
        template = self._templatize_sql(sql, schema)

        # 3. Extract required tables
        tables = self._extract_tables(sql)

        # 4. Check for existing similar pattern
        existing = await self._find_similar_pattern(pattern, dialect)

        if existing:
            # Update existing pattern
            existing.success_count += 1
            existing.last_used = datetime.utcnow()
            await self.db.commit()
            return None
        else:
            # Create new pattern
            new_pattern = LearnedPattern(
                question_pattern=pattern,
                sql_template=template,
                tables_pattern=json.dumps(tables),
                dialect=dialect,
                success_count=1
            )
            self.db.add(new_pattern)
            await self.db.commit()
            return new_pattern.id

    async def try_apply_pattern(
        self,
        question: str,
        schema: Dict,
        dialect: str
    ) -> Optional[PatternMatch]:
        """
        Try to apply a learned pattern to a new question.

        Returns PatternMatch if high-confidence match found.
        """
        # Find matching patterns
        patterns = await self._get_patterns_for_dialect(dialect)

        best_match = None
        best_score = 0.0

        for pattern in patterns:
            if pattern.confidence < self.min_confidence:
                continue

            # Check if question matches pattern
            score = self._match_score(question, pattern.question_pattern)

            if score > best_score and score > 0.85:
                # Try to apply template
                applied_sql = self._apply_template(
                    pattern.sql_template,
                    question,
                    schema
                )
                if applied_sql:
                    best_match = PatternMatch(
                        pattern_id=pattern.id,
                        sql_template=pattern.sql_template,
                        confidence=pattern.confidence * score,
                        original_question=question,
                        applied_sql=applied_sql
                    )
                    best_score = score

        return best_match

    def _generalize_question(self, question: str) -> str:
        """
        Convert specific question to generalizable pattern.

        "Show sales in California for 2024"
        → "Show {metric} in {location} for {time_period}"
        """
        pattern = question.lower()

        # Replace specific values with placeholders
        replacements = [
            # Locations (states)
            (r'\b(california|texas|new york|florida|etc)\b', '{location}'),
            # Numbers
            (r'\b\d+\b', '{number}'),
            # Dates/years
            (r'\b(20\d{2}|19\d{2})\b', '{year}'),
            (r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\b', '{month}'),
            # Common metrics
            (r'\b(sales|orders|revenue|customers|products|users)\b', '{entity}'),
        ]

        for regex, placeholder in replacements:
            pattern = re.sub(regex, placeholder, pattern, flags=re.IGNORECASE)

        return pattern

    def _templatize_sql(self, sql: str, schema: Dict) -> str:
        """
        Convert specific SQL to template with placeholders.

        "SELECT * FROM orders WHERE state = 'CA'"
        → "SELECT * FROM orders WHERE state = '{filter_value}'"
        """
        template = sql

        # Replace string literals
        template = re.sub(r"'[^']+?'", "'{value}'", template)

        # Replace numeric literals (but not in column names)
        template = re.sub(r"(?<![a-zA-Z_])\d+(?![a-zA-Z_])", "{number}", template)

        return template

    def _match_score(self, question: str, pattern: str) -> float:
        """Calculate similarity between question and pattern."""
        # Use fuzzy matching
        return fuzz.ratio(
            self._generalize_question(question),
            pattern
        ) / 100.0
```

**Model Performance Tracker:**

```python
# src/llm/model_performance_tracker.py

class ModelPerformanceTracker:
    """Tracks and analyzes model performance by task."""

    def __init__(self, db_session):
        self.db = db_session

    async def record_attempt(
        self,
        model: str,
        task: str,
        success: bool,
        latency_ms: float,
        tokens: int
    ):
        """Record a model attempt with outcome."""
        perf = await self._get_or_create(model, task)

        perf.total_attempts += 1
        if success:
            perf.successful_attempts += 1
        perf.total_latency_ms += int(latency_ms)
        perf.total_tokens += tokens
        perf.last_updated = datetime.utcnow()

        await self.db.commit()

    async def get_best_model(
        self,
        task: str,
        min_attempts: int = 10,
        min_success_rate: float = 0.7
    ) -> Optional[str]:
        """
        Get the best performing model for a task.

        Considers success rate and latency.
        """
        perfs = await self.db.execute(
            select(ModelPerformance)
            .where(ModelPerformance.task_type == task)
            .where(ModelPerformance.total_attempts >= min_attempts)
        )

        candidates = []
        for perf in perfs.scalars():
            if perf.success_rate >= min_success_rate:
                # Score = success_rate * (1 / normalized_latency)
                score = perf.success_rate * (1000 / max(perf.avg_latency_ms, 100))
                candidates.append((perf.model_name, score))

        if not candidates:
            return None

        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]

    async def get_performance_report(self) -> Dict:
        """Generate comprehensive performance report."""
        perfs = await self.db.execute(select(ModelPerformance))

        report = {
            "by_model": {},
            "by_task": {},
            "recommendations": []
        }

        for perf in perfs.scalars():
            # Aggregate by model
            if perf.model_name not in report["by_model"]:
                report["by_model"][perf.model_name] = []
            report["by_model"][perf.model_name].append({
                "task": perf.task_type,
                "success_rate": perf.success_rate,
                "avg_latency_ms": perf.avg_latency_ms,
                "attempts": perf.total_attempts
            })

            # Aggregate by task
            if perf.task_type not in report["by_task"]:
                report["by_task"][perf.task_type] = []
            report["by_task"][perf.task_type].append({
                "model": perf.model_name,
                "success_rate": perf.success_rate,
                "avg_latency_ms": perf.avg_latency_ms
            })

        # Generate recommendations
        for task, models in report["by_task"].items():
            if models:
                best = max(models, key=lambda x: x["success_rate"])
                report["recommendations"].append({
                    "task": task,
                    "recommended_model": best["model"],
                    "success_rate": best["success_rate"]
                })

        return report
```

### API Endpoints

```python
# src/api/endpoints/patterns.py

router = APIRouter(prefix="/api/patterns", tags=["patterns"])

@router.get("/")
async def list_patterns(
    dialect: Optional[str] = None,
    min_confidence: float = 0.5,
    limit: int = 50
):
    """List learned patterns with statistics."""
    pass

@router.get("/stats")
async def pattern_stats():
    """Get pattern learning statistics."""
    return {
        "total_patterns": 150,
        "patterns_by_dialect": {"postgresql": 80, "sqlite": 70},
        "avg_confidence": 0.87,
        "pattern_hit_rate": 0.23,  # 23% of queries use learned patterns
        "top_patterns": [...]
    }

@router.delete("/{pattern_id}")
async def delete_pattern(pattern_id: int):
    """Delete a learned pattern."""
    pass

# Model performance endpoints
@router.get("/models/performance")
async def model_performance():
    """Get model performance report."""
    pass

@router.get("/models/recommend/{task}")
async def recommend_model(task: str):
    """Get recommended model for task."""
    pass
```

### Frontend Analytics Dashboard

```typescript
// frontend/src/components/PatternAnalytics.tsx

export function PatternAnalytics() {
  const { data: stats } = useQuery(['patternStats'], fetchPatternStats);
  const { data: modelPerf } = useQuery(['modelPerformance'], fetchModelPerformance);

  return (
    <div className="pattern-analytics grid grid-cols-2 gap-6">
      {/* Pattern Statistics */}
      <Card>
        <CardHeader>
          <CardTitle>Learned Patterns</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="stat-grid">
            <StatCard label="Total Patterns" value={stats?.total_patterns} />
            <StatCard label="Pattern Hit Rate" value={`${stats?.pattern_hit_rate}%`} />
            <StatCard label="Avg Confidence" value={stats?.avg_confidence?.toFixed(2)} />
          </div>

          {/* Pattern distribution by dialect */}
          <PieChart data={stats?.patterns_by_dialect} />
        </CardContent>
      </Card>

      {/* Model Performance */}
      <Card>
        <CardHeader>
          <CardTitle>Model Performance</CardTitle>
        </CardHeader>
        <CardContent>
          <table className="w-full">
            <thead>
              <tr>
                <th>Model</th>
                <th>Task</th>
                <th>Success Rate</th>
                <th>Avg Latency</th>
              </tr>
            </thead>
            <tbody>
              {modelPerf?.recommendations.map(rec => (
                <tr key={`${rec.model}-${rec.task}`}>
                  <td>{rec.recommended_model}</td>
                  <td>{rec.task}</td>
                  <td>{(rec.success_rate * 100).toFixed(1)}%</td>
                  <td>{rec.avg_latency_ms}ms</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}
```

### Implementation Tasks

1. **Database Schema** (0.5 days)
   - [ ] Add `LearnedPattern` model
   - [ ] Add `ModelPerformance` model
   - [ ] Create database migration
   - [ ] Add indexes for query performance

2. **Pattern Learner** (2 days)
   - [ ] Implement question generalization
   - [ ] Implement SQL templatization
   - [ ] Implement pattern matching with fuzzy search
   - [ ] Implement template application
   - [ ] Add pattern caching

3. **Model Performance Tracker** (1 day)
   - [ ] Implement attempt recording
   - [ ] Implement best model selection
   - [ ] Implement performance report generation
   - [ ] Integrate with SQLGenerator and SelfCorrectingAgent

4. **Integration** (1 day)
   - [ ] Add pattern learning to successful query flow
   - [ ] Add pattern matching before LLM generation
   - [ ] Record model performance on every attempt
   - [ ] Add toggle in settings

5. **API & Frontend** (1 day)
   - [ ] Create patterns API endpoints
   - [ ] Create PatternAnalytics dashboard component
   - [ ] Add patterns tab to settings/analytics

6. **Testing** (0.5 days)
   - [ ] Unit tests for pattern generalization
   - [ ] Integration tests for pattern matching
   - [ ] Performance tests with 1000+ patterns

### Success Criteria

- [ ] Successful queries create learned patterns
- [ ] Pattern matching works with >85% accuracy
- [ ] Model performance tracked across all tasks
- [ ] Best model recommendations are accurate
- [ ] Analytics dashboard shows meaningful insights
- [ ] Template match rate increases by 10-15%

---

## Implementation Order Recommendation

These features are independent but have natural synergies:

```
Week 1-2: Streaming Results
├─ Immediate UX improvement
├─ No dependencies on other features
└─ Most user-visible impact

Week 3: Advanced Preprocessing
├─ Improves SQL accuracy
├─ Benefits from existing schema infrastructure
└─ Medium complexity

Week 4-5: Pattern Learning
├─ Requires successful query data (benefits from preprocessing)
├─ Longest learning curve
└─ Compound improvements over time
```

### Alternative: Parallel Implementation

If multiple developers are available:

| Developer A | Developer B |
|------------|-------------|
| Streaming Results (Backend) | Advanced Preprocessing |
| Streaming Results (Frontend) | Pattern Learning (Core) |
| Integration & Testing | Analytics Dashboard |

---

## Dependencies

### External Packages

| Feature | Package | Purpose |
|---------|---------|---------|
| Streaming | `sse-starlette` | Server-Sent Events for FastAPI |
| Streaming | `@tanstack/react-virtual` | Table virtualization |
| Preprocessing | (none) | Uses existing schema inspector |
| Pattern Learning | `rapidfuzz` | Fuzzy string matching |

### Internal Dependencies

| Feature | Depends On |
|---------|------------|
| Streaming | `SQLExecutor`, connection pools |
| Preprocessing | `SchemaInspector`, `ToolUsingAgent` |
| Pattern Learning | Database session, model router |

---

## Configuration

```bash
# Streaming
STREAMING_ENABLED=true
STREAMING_BATCH_SIZE=100
STREAMING_THRESHOLD_ROWS=1000  # Use streaming for results > N rows

# Advanced Preprocessing
ADVANCED_PREPROCESSING_ENABLED=true
STATUS_VALUE_CACHE_TTL=3600  # Cache status values for 1 hour
DATE_NORMALIZATION_ENABLED=true

# Pattern Learning
PATTERN_LEARNING_ENABLED=true
MIN_PATTERN_CONFIDENCE=0.8
MAX_PATTERNS_PER_DIALECT=1000
PATTERN_MATCH_THRESHOLD=0.85
MODEL_TRACKING_ENABLED=true
```

---

## Success Metrics

| Feature | Metric | Target |
|---------|--------|--------|
| **Streaming** | Time to first row | < 500ms |
| **Streaming** | Memory usage (100K rows) | < 500MB |
| **Preprocessing** | Date query accuracy | > 90% |
| **Preprocessing** | Boolean detection | > 85% |
| **Pattern Learning** | Pattern hit rate | > 20% |
| **Pattern Learning** | Model recommendation accuracy | > 80% |

---

## Related Documentation

- [FUTURE_PLANS.md](FUTURE_PLANS.md) - Original streaming proposal
- [SMALL_MODEL_OPTIMIZATION_PHASE2.md](SMALL_MODEL_OPTIMIZATION_PHASE2.md) - Preprocessing and learning specs
- [MASTER_ROADMAP.md](MASTER_ROADMAP.md) - Overall project roadmap
- [SQL_GENERATION_PIPELINE.md](../technical/SQL_GENERATION_PIPELINE.md) - Current pipeline architecture

---

**Document Version**: 1.0
**Created**: January 25, 2026
