# Semantic Type Intelligence Plan

## Overview

This document outlines the roadmap for implementing additional query intelligence features beyond the existing location detection. These features will enhance the system's ability to understand natural language queries and automatically normalize values, detect patterns, and generate more accurate SQL.

**Current State:** Location Intelligence is implemented in `query_preprocessor.py` with bidirectional normalization (e.g., "California" ↔ "CA").

**Goal:** Create a pluggable semantic type detection system that handles multiple data types intelligently.

---

## Priority Ranking Summary

| Priority | Feature | Impact | Effort | ROI Score |
|----------|---------|--------|--------|-----------|
| **P0** | Date/Time Intelligence | High | 3-4 days | ⭐⭐⭐⭐⭐ |
| **P1** | Status/Enum Intelligence | High | 2-3 days | ⭐⭐⭐⭐⭐ |
| **P2** | Boolean Intelligence | Medium | 1-2 days | ⭐⭐⭐⭐ |
| **P3** | Numeric Range Intelligence | Medium | 2 days | ⭐⭐⭐ |
| **P4** | ID/Reference Intelligence | Medium | 2-3 days | ⭐⭐⭐ |
| **P5** | Null/Empty Intelligence | Low-Medium | 1-2 days | ⭐⭐⭐ |
| **P6** | Currency Intelligence | Low | 2 days | ⭐⭐ |
| **P7** | Unit Conversion Intelligence | Low | 3 days | ⭐⭐ |
| **P8** | Contact Pattern Intelligence | Low | 2 days | ⭐⭐ |

---

## Architecture Design

### Proposed Class Hierarchy

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum

class SemanticType(Enum):
    LOCATION = "location"
    DATETIME = "datetime"
    STATUS_ENUM = "status_enum"
    BOOLEAN = "boolean"
    NUMERIC_RANGE = "numeric_range"
    ID_REFERENCE = "id_reference"
    NULL_EMPTY = "null_empty"
    CURRENCY = "currency"
    UNIT = "unit"
    CONTACT = "contact"

@dataclass
class SemanticDetection:
    """Result of semantic type detection."""
    semantic_type: SemanticType
    original_value: str           # What user typed
    normalized_value: str         # What DB expects
    confidence: float             # 0.0-1.0
    column_hint: Optional[str]    # Suggested column
    table_hint: Optional[str]     # Suggested table
    dialect_specific: bool        # Needs DB-specific handling
    metadata: Dict                # Type-specific extra data

class SemanticTypeDetector(ABC):
    """Base class for all semantic type detectors."""

    @abstractmethod
    def detect(self, question: str, schema: Dict) -> List[SemanticDetection]:
        """Detect semantic values in the question."""
        pass

    @abstractmethod
    def normalize(self, value: str, target_format: str) -> str:
        """Normalize a value to the target format."""
        pass

    @abstractmethod
    def get_column_patterns(self) -> List[str]:
        """Return column name patterns this detector handles."""
        pass

class SemanticTypeRegistry:
    """Central registry managing all semantic type detectors."""

    def __init__(self, schema: Dict, dialect: str):
        self.schema = schema
        self.dialect = dialect
        self.detectors: List[SemanticTypeDetector] = []
        self._register_default_detectors()

    def _register_default_detectors(self):
        """Register all available detectors."""
        self.detectors = [
            LocationDetector(self.schema),           # Existing
            DateTimeDetector(self.schema, self.dialect),  # P0
            StatusEnumDetector(self.schema),         # P1
            BooleanDetector(self.schema, self.dialect),   # P2
            NumericRangeDetector(self.schema),       # P3
            IDReferenceDetector(self.schema),        # P4
            NullEmptyDetector(self.schema),          # P5
        ]

    def detect_all(self, question: str) -> List[SemanticDetection]:
        """Run all detectors and return combined results."""
        results = []
        for detector in self.detectors:
            results.extend(detector.detect(question, self.schema))
        return sorted(results, key=lambda x: -x.confidence)
```

### Integration Point

```python
# In query_preprocessor.py or new semantic_preprocessor.py
class SemanticPreprocessor:
    def __init__(self, schema: Dict, dialect: str):
        self.registry = SemanticTypeRegistry(schema, dialect)

    def preprocess(self, question: str) -> PreprocessedQuery:
        detections = self.registry.detect_all(question)

        normalized_question = question
        llm_hints = []

        for detection in detections:
            if detection.confidence > 0.7:
                normalized_question = normalized_question.replace(
                    detection.original_value,
                    detection.normalized_value
                )
                llm_hints.append(self._build_hint(detection))

        return PreprocessedQuery(
            original_question=question,
            normalized_question=normalized_question,
            llm_hints=llm_hints,
            semantic_detections=detections
        )
```

---

## Feature Details

### P0: Date/Time Intelligence (3-4 days)

**Impact:** HIGH - Date/time queries are extremely common and error-prone.

**Problem Solved:**
- "orders from last week" → `WHERE order_date >= '2026-01-01'`
- "sales in Q4 2025" → `WHERE sale_date BETWEEN '2025-10-01' AND '2025-12-31'`
- "created yesterday" → `WHERE created_at >= '2026-01-07'`

**Implementation:**

```python
class DateTimeDetector(SemanticTypeDetector):
    """Detects and normalizes date/time references."""

    RELATIVE_PATTERNS = {
        r'\btoday\b': lambda: date.today(),
        r'\byesterday\b': lambda: date.today() - timedelta(days=1),
        r'\blast week\b': lambda: (date.today() - timedelta(weeks=1), date.today()),
        r'\blast month\b': lambda: (date.today().replace(day=1) - timedelta(days=1)).replace(day=1),
        r'\blast year\b': lambda: date.today().replace(year=date.today().year - 1),
        r'\bthis week\b': lambda: date.today() - timedelta(days=date.today().weekday()),
        r'\bthis month\b': lambda: date.today().replace(day=1),
        r'\bthis year\b': lambda: date.today().replace(month=1, day=1),
    }

    QUARTER_PATTERNS = {
        r'Q1\s*(\d{4})': lambda y: (f"{y}-01-01", f"{y}-03-31"),
        r'Q2\s*(\d{4})': lambda y: (f"{y}-04-01", f"{y}-06-30"),
        r'Q3\s*(\d{4})': lambda y: (f"{y}-07-01", f"{y}-09-30"),
        r'Q4\s*(\d{4})': lambda y: (f"{y}-10-01", f"{y}-12-31"),
    }

    COLUMN_PATTERNS = [
        r'.*_date$', r'.*_at$', r'.*_time$', r'^date_.*',
        r'^created', r'^updated', r'^modified', r'^timestamp',
        r'^order_date', r'^sale_date', r'^birth_date', r'^due_date'
    ]

    DIALECT_FORMATS = {
        'postgresql': "DATE '{}'",
        'mysql': "'{}'",
        'sqlite': "'{}'",
        'duckdb': "DATE '{}'",
    }
```

**Success Metrics:**
- 80%+ accuracy on relative date queries
- <50ms processing time
- Support for 15+ relative date patterns

---

### P1: Status/Enum Intelligence (2-3 days)

**Impact:** HIGH - Status fields are ubiquitous and have inconsistent naming.

**Problem Solved:**
- "active customers" → `WHERE status = 'active'` OR `WHERE is_active = true`
- "pending orders" → `WHERE order_status = 'pending'`
- "completed tasks" → `WHERE state = 'completed'` OR `WHERE status = 'done'`

**Implementation:**

```python
class StatusEnumDetector(SemanticTypeDetector):
    """Detects status/enum values and maps to schema."""

    # Common status synonyms
    STATUS_SYNONYMS = {
        'active': ['active', 'enabled', 'live', 'open', 'current'],
        'inactive': ['inactive', 'disabled', 'closed', 'archived'],
        'pending': ['pending', 'waiting', 'queued', 'processing'],
        'completed': ['completed', 'done', 'finished', 'closed', 'resolved'],
        'cancelled': ['cancelled', 'canceled', 'aborted', 'terminated'],
        'failed': ['failed', 'error', 'rejected', 'declined'],
    }

    COLUMN_PATTERNS = [
        r'^status$', r'.*_status$', r'^state$', r'.*_state$',
        r'^type$', r'.*_type$', r'^category$', r'^priority$'
    ]

    def detect(self, question: str, schema: Dict) -> List[SemanticDetection]:
        detections = []

        # Find status columns in schema
        status_columns = self._find_status_columns(schema)

        for canonical, synonyms in self.STATUS_SYNONYMS.items():
            for synonym in synonyms:
                if synonym.lower() in question.lower():
                    # Check if any status column has this value
                    for col_info in status_columns:
                        if canonical in col_info['values'] or synonym in col_info['values']:
                            detections.append(SemanticDetection(
                                semantic_type=SemanticType.STATUS_ENUM,
                                original_value=synonym,
                                normalized_value=col_info['actual_value'],
                                confidence=0.85,
                                column_hint=col_info['column'],
                                table_hint=col_info['table'],
                            ))

        return detections
```

**Success Metrics:**
- 90%+ accuracy mapping common status terms
- Auto-discover enum values from schema sampling
- Support 20+ common status synonyms

---

### P2: Boolean Intelligence (1-2 days)

**Impact:** MEDIUM - Boolean columns have many naming variations.

**Problem Solved:**
- "verified users" → `WHERE is_verified = true` OR `WHERE verified = 1`
- "unsubscribed customers" → `WHERE subscribed = false`
- "featured products" → `WHERE is_featured = true`

**Implementation:**

```python
class BooleanDetector(SemanticTypeDetector):
    """Detects boolean intent and maps to schema columns."""

    POSITIVE_INDICATORS = [
        'is', 'are', 'has', 'have', 'verified', 'active', 'enabled',
        'featured', 'published', 'approved', 'confirmed', 'valid'
    ]

    NEGATIVE_PREFIXES = ['un', 'non', 'not', 'in', 'dis']

    COLUMN_PATTERNS = [
        r'^is_.*', r'^has_.*', r'^can_.*', r'^should_.*',
        r'.*_flag$', r'.*_ind$', r'^active$', r'^enabled$',
        r'^verified$', r'^published$', r'^deleted$'
    ]

    DIALECT_TRUE = {
        'postgresql': 'true',
        'mysql': '1',
        'sqlite': '1',
        'duckdb': 'true',
    }
```

**Success Metrics:**
- 95%+ accuracy on boolean column detection
- Dialect-aware true/false generation
- Handle negation prefixes correctly

---

### P3: Numeric Range Intelligence (2 days)

**Impact:** MEDIUM - Range queries are common but require careful parsing.

**Problem Solved:**
- "products under $50" → `WHERE price < 50`
- "orders between 100 and 500" → `WHERE amount BETWEEN 100 AND 500`
- "customers with more than 10 orders" → `WHERE order_count > 10`
- "items over 1000 in stock" → `WHERE quantity > 1000`

**Implementation:**

```python
class NumericRangeDetector(SemanticTypeDetector):
    """Detects numeric range expressions."""

    RANGE_PATTERNS = [
        (r'under\s+\$?(\d+(?:\.\d+)?)', 'lt'),
        (r'below\s+\$?(\d+(?:\.\d+)?)', 'lt'),
        (r'less than\s+\$?(\d+(?:\.\d+)?)', 'lt'),
        (r'over\s+\$?(\d+(?:\.\d+)?)', 'gt'),
        (r'above\s+\$?(\d+(?:\.\d+)?)', 'gt'),
        (r'more than\s+\$?(\d+(?:\.\d+)?)', 'gt'),
        (r'greater than\s+\$?(\d+(?:\.\d+)?)', 'gt'),
        (r'at least\s+\$?(\d+(?:\.\d+)?)', 'gte'),
        (r'at most\s+\$?(\d+(?:\.\d+)?)', 'lte'),
        (r'between\s+\$?(\d+(?:\.\d+)?)\s+and\s+\$?(\d+(?:\.\d+)?)', 'between'),
        (r'from\s+\$?(\d+(?:\.\d+)?)\s+to\s+\$?(\d+(?:\.\d+)?)', 'between'),
    ]

    OPERATOR_MAP = {
        'lt': '<',
        'lte': '<=',
        'gt': '>',
        'gte': '>=',
        'between': 'BETWEEN',
    }
```

**Success Metrics:**
- 90%+ accuracy on range expression parsing
- Handle currency symbols ($, €, £)
- Support various range phrasings

---

### P4: ID/Reference Intelligence (2-3 days)

**Impact:** MEDIUM - Helps with foreign key relationships and ID lookups.

**Problem Solved:**
- "order #12345" → `WHERE order_id = 12345`
- "customer ID ABC-123" → `WHERE customer_id = 'ABC-123'`
- "invoice number INV-2025-001" → `WHERE invoice_number = 'INV-2025-001'`

**Implementation:**

```python
class IDReferenceDetector(SemanticTypeDetector):
    """Detects ID/reference patterns in queries."""

    ID_PATTERNS = [
        (r'(?:order|invoice|ticket|case)\s*#?\s*(\d+)', 'numeric_id'),
        (r'(?:id|ID)\s*[:#]?\s*([A-Za-z0-9-]+)', 'alphanumeric_id'),
        (r'(?:customer|user|employee)\s+(\d+)', 'entity_id'),
        (r'([A-Z]{2,4}-\d{4}-\d{3,6})', 'formatted_id'),  # INV-2025-001
        (r'(?:reference|ref)\s*[:#]?\s*([A-Za-z0-9-]+)', 'reference'),
    ]

    COLUMN_PATTERNS = [
        r'.*_id$', r'^id$', r'.*_number$', r'.*_code$',
        r'.*_ref$', r'^sku$', r'^uuid$', r'^guid$'
    ]
```

**Success Metrics:**
- 85%+ accuracy on ID pattern detection
- Support common ID formats (numeric, alphanumeric, formatted)
- Auto-detect primary key columns

---

### P5: Null/Empty Intelligence (1-2 days)

**Impact:** LOW-MEDIUM - Helpful for data quality queries.

**Problem Solved:**
- "customers without email" → `WHERE email IS NULL OR email = ''`
- "products missing description" → `WHERE description IS NULL`
- "orders with no shipping address" → `WHERE shipping_address IS NULL`

**Implementation:**

```python
class NullEmptyDetector(SemanticTypeDetector):
    """Detects null/empty value queries."""

    NULL_INDICATORS = [
        (r'without\s+(\w+)', 'null'),
        (r'missing\s+(\w+)', 'null'),
        (r'no\s+(\w+)', 'null'),
        (r'empty\s+(\w+)', 'empty'),
        (r'blank\s+(\w+)', 'empty'),
        (r'(\w+)\s+is\s+(?:not\s+)?(?:null|empty|blank|missing)', 'null'),
    ]

    def generate_condition(self, column: str, check_type: str) -> str:
        if check_type == 'null':
            return f"{column} IS NULL"
        elif check_type == 'empty':
            return f"({column} IS NULL OR {column} = '')"
        elif check_type == 'not_null':
            return f"{column} IS NOT NULL"
```

**Success Metrics:**
- 90%+ accuracy on null/empty detection
- Handle both NULL and empty string checks
- Support negation ("with email" vs "without email")

---

### P6: Currency Intelligence (2 days)

**Impact:** LOW - Useful for financial applications.

**Problem Solved:**
- "sales over $1,000" → `WHERE amount > 1000`
- "prices in euros" → Filter/convert currency columns
- "$1.5M revenue" → `WHERE revenue > 1500000`

**Implementation:**

```python
class CurrencyDetector(SemanticTypeDetector):
    """Detects and normalizes currency values."""

    CURRENCY_PATTERNS = [
        (r'\$\s*([\d,]+(?:\.\d{2})?)\s*(k|m|b)?', 'USD'),
        (r'€\s*([\d,]+(?:\.\d{2})?)\s*(k|m|b)?', 'EUR'),
        (r'£\s*([\d,]+(?:\.\d{2})?)\s*(k|m|b)?', 'GBP'),
        (r'([\d,]+(?:\.\d{2})?)\s*(?:dollars?|usd)', 'USD'),
    ]

    MULTIPLIERS = {'k': 1000, 'm': 1000000, 'b': 1000000000}
```

---

### P7: Unit Conversion Intelligence (3 days)

**Impact:** LOW - Specialized for measurement-heavy domains.

**Problem Solved:**
- "products weighing over 5 lbs" → `WHERE weight_kg > 2.27`
- "distances under 100 miles" → `WHERE distance_km < 160.9`
- "temperatures above 100°F" → `WHERE temp_celsius > 37.8`

---

### P8: Contact Pattern Intelligence (2 days)

**Impact:** LOW - Specialized for CRM/contact databases.

**Problem Solved:**
- "customers with gmail" → `WHERE email LIKE '%@gmail.com'`
- "phone numbers starting with 555" → `WHERE phone LIKE '555%'`
- "addresses in zip code 90210" → `WHERE zip_code = '90210'`

---

## Implementation Phases

### Phase A: Foundation (Week 1)
- [ ] Create `SemanticTypeDetector` base class
- [ ] Create `SemanticTypeRegistry` manager
- [ ] Refactor existing `LocationDetector` to use new pattern
- [ ] Add unit tests for base classes

### Phase B: High Priority Features (Weeks 2-3)
- [ ] **P0:** Date/Time Intelligence
  - [ ] Relative date parsing (today, yesterday, last week)
  - [ ] Quarter/fiscal period support
  - [ ] Dialect-aware date formatting
  - [ ] 15+ unit tests
- [ ] **P1:** Status/Enum Intelligence
  - [ ] Status synonym mapping
  - [ ] Auto-discovery from schema sampling
  - [ ] 10+ unit tests
- [ ] **P2:** Boolean Intelligence
  - [ ] Boolean column detection
  - [ ] Negation handling
  - [ ] Dialect-aware true/false
  - [ ] 8+ unit tests

### Phase C: Medium Priority Features (Weeks 4-5)
- [ ] **P3:** Numeric Range Intelligence
- [ ] **P4:** ID/Reference Intelligence
- [ ] **P5:** Null/Empty Intelligence

### Phase D: Low Priority Features (Future)
- [ ] **P6:** Currency Intelligence
- [ ] **P7:** Unit Conversion Intelligence
- [ ] **P8:** Contact Pattern Intelligence

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Query accuracy improvement | +15% | A/B test with/without semantic detection |
| First-attempt success rate | +20% | Track queries needing correction |
| Processing latency | <100ms | Total semantic detection time |
| Coverage | 80%+ | % of queries with at least one detection |
| False positive rate | <5% | Incorrect normalizations |

---

## Testing Strategy

1. **Unit Tests:** Each detector has dedicated tests
   - Pattern matching accuracy
   - Normalization correctness
   - Edge cases (empty input, malformed values)

2. **Integration Tests:** End-to-end query processing
   - Full pipeline with all detectors enabled
   - Multi-detection scenarios (date + status + location)
   - Conflict resolution testing

3. **Regression Tests:** Known query patterns
   - Golden set of 100+ queries with expected SQL
   - Automated comparison on each PR

4. **Performance Tests:** Latency benchmarks
   - Single detector: <10ms
   - All detectors: <100ms
   - 1000 queries/second throughput

---

## File Locations

| Component | File Path |
|-----------|-----------|
| Base Classes | `src/llm/semantic_types/base.py` |
| Registry | `src/llm/semantic_types/registry.py` |
| Location Detector | `src/llm/semantic_types/location.py` |
| DateTime Detector | `src/llm/semantic_types/datetime.py` |
| Status/Enum Detector | `src/llm/semantic_types/status_enum.py` |
| Boolean Detector | `src/llm/semantic_types/boolean.py` |
| Numeric Range Detector | `src/llm/semantic_types/numeric_range.py` |
| ID/Reference Detector | `src/llm/semantic_types/id_reference.py` |
| Null/Empty Detector | `src/llm/semantic_types/null_empty.py` |
| Tests | `tests/test_semantic_types/` |

---

## Dependencies

- **dateutil** - For robust date parsing (P0)
- **pytz** - For timezone handling (P0)
- No additional dependencies for P1-P5

---

## Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2026-01-08 | 0.1 | Initial plan created |

---

## Related Documents

- [Small Model Optimization Phase 2](SMALL_MODEL_OPTIMIZATION_PHASE2.md)
- [SQL Generation Pipeline](SQL_GENERATION_PIPELINE.md)
- [Query Preprocessor](../src/llm/query_preprocessor.py)
- [Multi-Database Validation Guide](MULTI_DB_VALIDATION_GUIDE.md)
