"""Query Intent Classification for pre-generation validation.

This module analyzes natural language questions to classify intent and extract
requirements BEFORE SQL generation, enabling early CANNOT_ANSWER detection.

Key Features:
- Fast regex-based classification (no LLM calls, <50ms)
- Entity extraction for tables, columns, locations, values
- Schema validation to detect impossible queries
- Helpful suggestions when queries cannot be answered

Usage:
    classifier = QueryIntentClassifier(schema_dict)
    result = classifier.classify("Show all products from California")

    if not result.can_answer():
        return f"Cannot answer: {result.impossible_reason}"
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Tuple
from difflib import SequenceMatcher
import re
import logging

logger = logging.getLogger(__name__)


class QueryIntent(Enum):
    """Classification of query intent.

    Each intent maps to a typical SQL pattern:
    - LOOKUP: Simple SELECT without aggregation
    - AGGREGATION: COUNT, SUM, AVG, etc.
    - COMPARISON: WHERE with comparison operators
    - RELATIONSHIP: JOIN required (multiple tables)
    - TEMPORAL: Date/time filtering
    - RANKING: TOP N / ORDER BY LIMIT
    - IMPOSSIBLE: Cannot answer with available schema
    """
    LOOKUP = "lookup"
    AGGREGATION = "aggregation"
    COMPARISON = "comparison"
    RELATIONSHIP = "relationship"
    TEMPORAL = "temporal"
    RANKING = "ranking"
    IMPOSSIBLE = "impossible"


@dataclass
class ExtractedEntity:
    """An entity extracted from the user's question.

    Attributes:
        original_text: The raw text from the question (e.g., "California")
        entity_type: Category of entity ("table", "column", "value", "location", "aggregation")
        normalized_value: Processed value if applicable (e.g., "CA" for California)
        confidence: Extraction confidence score (0.0-1.0)
        mapped_to_schema: Whether this entity was found in the schema
        schema_match: The actual schema element name if matched
    """
    original_text: str
    entity_type: str
    normalized_value: Optional[str] = None
    confidence: float = 0.0
    mapped_to_schema: bool = False
    schema_match: Optional[str] = None


@dataclass
class QueryIntentResult:
    """Complete result of query intent classification.

    Attributes:
        intent: The classified query intent
        confidence: Classification confidence (0.0-1.0)
        extracted_entities: All entities found in the question
        required_tables: Tables needed to answer the query
        required_columns: Columns needed, grouped by table
        required_values: Filter values detected (column -> value mapping)
        aggregations: Aggregation functions needed (COUNT, SUM, etc.)
        filters: Filter conditions extracted
        impossible_reason: Why the query cannot be answered (if IMPOSSIBLE)
        suggestions: Helpful suggestions for impossible queries
    """
    intent: QueryIntent
    confidence: float
    extracted_entities: List[ExtractedEntity] = field(default_factory=list)
    required_tables: Set[str] = field(default_factory=set)
    required_columns: Dict[str, Set[str]] = field(default_factory=dict)
    required_values: Dict[str, Any] = field(default_factory=dict)
    aggregations: List[str] = field(default_factory=list)
    filters: List[Dict[str, Any]] = field(default_factory=list)
    impossible_reason: Optional[str] = None
    suggestions: List[str] = field(default_factory=list)

    def can_answer(self) -> bool:
        """Check if the query can be answered with available schema."""
        return self.intent != QueryIntent.IMPOSSIBLE

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization and AgentTrace."""
        return {
            "intent": self.intent.value,
            "confidence": self.confidence,
            "extracted_entities": [
                {
                    "text": e.original_text,
                    "type": e.entity_type,
                    "normalized": e.normalized_value,
                    "confidence": e.confidence,
                    "mapped": e.mapped_to_schema,
                    "schema_match": e.schema_match
                }
                for e in self.extracted_entities
            ],
            "required_tables": list(self.required_tables),
            "required_columns": {k: list(v) for k, v in self.required_columns.items()},
            "aggregations": self.aggregations,
            "filters": self.filters,
            "can_answer": self.can_answer(),
            "impossible_reason": self.impossible_reason,
            "suggestions": self.suggestions
        }


class QueryIntentClassifier:
    """Classifies query intent before SQL generation.

    This classifier uses a hybrid approach:
    1. Fast regex-based classification for common patterns
    2. Entity extraction to identify tables, columns, values
    3. Schema validation to detect impossible queries early

    Performance target: <50ms for simple cases (regex only, no LLM calls)
    """

    # Intent classification patterns (scored by weight)
    LOOKUP_PATTERNS = [
        (r'^show\s+(me\s+)?(all\s+)?', 1.0),
        (r'^list\s+(all\s+)?', 1.0),
        (r'^get\s+(all\s+)?', 1.0),
        (r'^display\s+', 0.9),
        (r'^what\s+(are|is)\s+', 0.8),
        (r'^find\s+(all\s+)?', 0.9),
        (r'^select\s+', 0.7),
    ]

    AGGREGATION_PATTERNS = [
        (r'\bhow\s+many\b', 2.0),
        (r'\bnumber\s+of\b', 1.8),
        (r'\bcount\s+(of|the)?\b', 2.0),
        (r'\btotal\s+(number|amount|count|sales|revenue|sum)\b', 2.0),
        (r'\bsum\s+of\b', 2.0),
        (r'\baverage\s+(of)?\b', 2.0),
        (r'\bavg\b', 2.0),
        (r'\bmean\b', 1.8),
        (r'\bmaximum\b', 1.5),
        (r'\bminimum\b', 1.5),
        (r'\bmax\s+(of)?\b', 1.5),
        (r'\bmin\s+(of)?\b', 1.5),
    ]

    COMPARISON_PATTERNS = [
        (r'\b(more|greater|higher)\s+than\b', 1.5),
        (r'\b(less|fewer|lower)\s+than\b', 1.5),
        (r'\bunder\s+\$?\d+', 1.5),
        (r'\bover\s+\$?\d+', 1.5),
        (r'\babove\s+\$?\d+', 1.5),
        (r'\bbelow\s+\$?\d+', 1.5),
        (r'\bbetween\s+\d+\s+and\s+\d+', 1.8),
        (r'\b(cheaper|expensive|oldest|newest)\b', 1.3),
        (r'\bwhere\s+\w+\s*(=|>|<|>=|<=|!=)', 1.5),
    ]

    RELATIONSHIP_PATTERNS = [
        (r'\bwith\s+(their|its|the)\b', 2.0),
        (r'\band\s+(their|its|the)\b', 1.5),
        (r'\balongside\b', 1.8),
        (r'\brelated\s+to\b', 2.0),
        (r'\bfor\s+each\b', 1.8),
        (r'\bjoin(ed)?\s+(with|to)\b', 2.0),
        (r'\bincluding\s+(their|its)\b', 1.5),
        (r'\bbelonging\s+to\b', 1.5),
    ]

    TEMPORAL_PATTERNS = [
        (r'\b(last|past|previous)\s+(week|month|year|day|quarter)\b', 2.0),
        (r'\b(this)\s+(week|month|year|day|quarter)\b', 1.8),
        (r'\b(since|before|after|during)\s+', 1.5),
        (r'\brecent(ly)?\b', 1.3),
        (r'\b(today|yesterday|tomorrow)\b', 1.5),
        (r'\bin\s+\d{4}\b', 1.3),  # Year like "in 2024"
        (r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\b', 1.3),
        (r'\bdate\s*(=|>|<|between)', 1.5),
    ]

    RANKING_PATTERNS = [
        (r'\btop\s+\d+\b', 2.0),
        (r'\bbottom\s+\d+\b', 2.0),
        (r'\bfirst\s+\d+\b', 1.8),
        (r'\blast\s+\d+\b', 1.8),
        (r'\b(highest|lowest)\s+\d*\b', 1.5),
        (r'\bbest\s+\d*\b', 1.3),
        (r'\bworst\s+\d*\b', 1.3),
        (r'\bmost\s+\w+\b', 1.5),
        (r'\bleast\s+\w+\b', 1.5),
    ]

    # Entity extraction patterns
    TABLE_PATTERNS = [
        r'\b(all|show|list|get|find|display)\s+(\w+)',
        r'\bfrom\s+(\w+)',
        r'(\w+)\s+table',
        r'(\w+)\s+data',
        r'(\w+)\s+records',
    ]

    COLUMN_PATTERNS = [
        r'\b(by|group\s+by|order\s+by)\s+(\w+)',
        r'(\w+)\s+(is|equals?|=|>|<)',
        r'\b(where|filter)\s+(\w+)',
        r'\bsort\s+by\s+(\w+)',
    ]

    # Aggregation keyword mapping
    AGGREGATION_KEYWORDS = {
        "count": "COUNT",
        "total": "SUM",
        "sum": "SUM",
        "average": "AVG",
        "avg": "AVG",
        "mean": "AVG",
        "maximum": "MAX",
        "max": "MAX",
        "highest": "MAX",
        "minimum": "MIN",
        "min": "MIN",
        "lowest": "MIN"
    }

    # Common words that are NOT table/column names
    STOP_WORDS = {
        # Verbs and question words
        'show', 'list', 'find', 'get', 'all', 'from', 'where', 'with',
        'the', 'and', 'how', 'many', 'what', 'which', 'their', 'that',
        'this', 'have', 'has', 'been', 'were', 'was', 'are', 'total',
        'count', 'number', 'give', 'display', 'select', 'each', 'every',
        'some', 'any', 'more', 'less', 'than', 'over', 'under', 'above',
        'below', 'between', 'before', 'after', 'during', 'since', 'until',
        # Temporal words
        'last', 'week', 'month', 'year', 'day', 'today', 'yesterday',
        'tomorrow', 'recent', 'recently', 'past', 'previous', 'next',
        'first', 'second', 'third', 'quarter', 'hours', 'minutes',
        # Ranking/comparison words
        'top', 'bottom', 'highest', 'lowest', 'best', 'worst', 'most',
        'least', 'maximum', 'minimum', 'average', 'mean', 'median',
        # NOTE: Location words (california, texas, new york, etc.) are NOT in STOP_WORDS
        # They are detected separately by LocationMapper and excluded dynamically
        # to avoid breaking multi-word locations like "New York"
        'state', 'city', 'country', 'region', 'location', 'address',
        # Other common words
        'there', 'here', 'dollars', 'price', 'revenue', 'cost', 'sales',
        'priced', 'order', 'ordered', 'product', 'item', 'record',
        'data', 'information', 'result', 'results', 'value', 'values',
        'is', 'on', 'in', 'to', 'for', 'by', 'at', 'of', 'an', 'a',
    }

    def __init__(
        self,
        schema_dict: Dict[str, Any],
        use_llm_for_complex: bool = False,
        ollama_client=None
    ):
        """Initialize classifier with schema.

        Args:
            schema_dict: Parsed schema dictionary from SchemaInspector
            use_llm_for_complex: If True, use LLM for ambiguous queries (not implemented)
            ollama_client: OllamaClient instance (for future LLM-based classification)
        """
        self.schema = schema_dict
        self.use_llm = use_llm_for_complex
        self.ollama = ollama_client

        # Build schema indices for fast lookup
        self.tables = set(schema_dict.get("tables", {}).keys())
        self.tables_lower = {t.lower(): t for t in self.tables}
        self.columns_by_table = self._build_column_index()
        self.all_columns = self._build_all_columns()

    def _build_column_index(self) -> Dict[str, Set[str]]:
        """Build table -> columns mapping."""
        result = {}
        for table_name, table_info in self.schema.get("tables", {}).items():
            columns = {col["name"] for col in table_info.get("columns", [])}
            result[table_name] = columns
        return result

    def _build_all_columns(self) -> Set[str]:
        """Get all column names across all tables."""
        all_cols = set()
        for cols in self.columns_by_table.values():
            all_cols.update(cols)
        return all_cols

    def classify(self, question: str) -> QueryIntentResult:
        """Classify query intent and extract requirements.

        This is the main entry point for pre-generation validation.

        Args:
            question: Natural language question

        Returns:
            QueryIntentResult with intent, entities, and validation results
        """
        question_lower = question.lower().strip()

        # Step 1: Fast pattern-based intent classification
        intent, confidence = self._classify_by_patterns(question_lower)

        # Step 2: Extract entities (tables, columns, locations, values)
        entities = self._extract_entities(question)

        # Step 3: Identify required tables from entities
        required_tables = self._identify_required_tables(entities, question_lower)

        # Step 4: Identify required columns
        required_columns = self._identify_required_columns(entities, required_tables)

        # Step 5: Extract aggregations
        aggregations = self._extract_aggregations(question_lower)

        # Step 6: Extract filter conditions
        filters = self._extract_filters(question)

        # Step 7: Validate against schema - detect impossible queries
        validation = self._validate_requirements(
            required_tables, required_columns, entities
        )

        # Step 8: Merge tables found from question text into matched_tables
        # _identify_required_tables may find tables not captured as entities
        final_tables = validation.get("matched_tables", set()) | required_tables

        # Step 9: Determine final intent based on validation
        if not validation["can_satisfy"]:
            intent = QueryIntent.IMPOSSIBLE
            confidence = 0.9

        return QueryIntentResult(
            intent=intent,
            confidence=confidence,
            extracted_entities=entities,
            required_tables=final_tables,
            required_columns=required_columns,
            required_values={},
            aggregations=aggregations,
            filters=filters,
            impossible_reason=validation.get("reason"),
            suggestions=validation.get("suggestions", [])
        )

    def _classify_by_patterns(self, question: str) -> Tuple[QueryIntent, float]:
        """Fast pattern-based intent classification.

        Scores each intent type based on matching patterns and their weights.
        Returns the highest scoring intent with a confidence value.
        """
        scores = {
            QueryIntent.LOOKUP: 0.0,
            QueryIntent.AGGREGATION: 0.0,
            QueryIntent.COMPARISON: 0.0,
            QueryIntent.RELATIONSHIP: 0.0,
            QueryIntent.TEMPORAL: 0.0,
            QueryIntent.RANKING: 0.0,
        }

        # Score each pattern type
        for pattern, weight in self.LOOKUP_PATTERNS:
            if re.search(pattern, question, re.IGNORECASE):
                scores[QueryIntent.LOOKUP] += weight

        for pattern, weight in self.AGGREGATION_PATTERNS:
            if re.search(pattern, question, re.IGNORECASE):
                scores[QueryIntent.AGGREGATION] += weight

        for pattern, weight in self.COMPARISON_PATTERNS:
            if re.search(pattern, question, re.IGNORECASE):
                scores[QueryIntent.COMPARISON] += weight

        for pattern, weight in self.RELATIONSHIP_PATTERNS:
            if re.search(pattern, question, re.IGNORECASE):
                scores[QueryIntent.RELATIONSHIP] += weight

        for pattern, weight in self.TEMPORAL_PATTERNS:
            if re.search(pattern, question, re.IGNORECASE):
                scores[QueryIntent.TEMPORAL] += weight

        for pattern, weight in self.RANKING_PATTERNS:
            if re.search(pattern, question, re.IGNORECASE):
                scores[QueryIntent.RANKING] += weight

        # Find winner
        max_score = max(scores.values())
        if max_score == 0:
            # Default to simple lookup
            return QueryIntent.LOOKUP, 0.5

        winner = max(scores, key=scores.get)

        # Calculate confidence based on score magnitude and separation from second place
        sorted_scores = sorted(scores.values(), reverse=True)
        separation = sorted_scores[0] - sorted_scores[1] if len(sorted_scores) > 1 else sorted_scores[0]
        confidence = min(0.95, 0.5 + (max_score * 0.1) + (separation * 0.1))

        return winner, confidence

    def _extract_entities(self, question: str) -> List[ExtractedEntity]:
        """Extract entities from the question."""
        entities = []
        question_lower = question.lower()

        # Step 1: Extract location entities FIRST (reuse LocationMapper)
        # This ensures multi-word locations like "New York" are detected before
        # individual words get filtered as table/column candidates
        location_entities = self._extract_locations(question)
        entities.extend(location_entities)

        # Build set of words that are part of detected locations
        # These should NOT be treated as table or column names
        location_words = set()
        for loc_entity in location_entities:
            # Split multi-word locations (e.g., "New York" -> {"new", "york"})
            location_words.update(loc_entity.original_text.lower().split())

        # Step 2: Extract table-like words, excluding location words
        entities.extend(self._extract_table_entities(question_lower, exclude_words=location_words))

        # Step 3: Extract column-like words, excluding location words
        entities.extend(self._extract_column_entities(question_lower, exclude_words=location_words))

        # Step 4: Extract numeric values
        entities.extend(self._extract_value_entities(question))

        return entities

    def _extract_locations(self, question: str) -> List[ExtractedEntity]:
        """Extract location references from question."""
        entities = []
        try:
            from src.core.location_mapper import LocationMapper
            locations = LocationMapper.detect_location_in_query(question)
            for loc in locations:
                entities.append(ExtractedEntity(
                    original_text=loc.get('original', ''),
                    entity_type='location',
                    normalized_value=loc.get('normalized'),
                    confidence=0.9,
                    mapped_to_schema=self._has_location_column(),
                    schema_match='state' if self._has_location_column() else None
                ))
        except ImportError:
            logger.debug("LocationMapper not available")
        return entities

    def _extract_table_entities(self, question: str, exclude_words: Set[str] = None) -> List[ExtractedEntity]:
        """Extract potential table references.

        Args:
            question: The question text (lowercase)
            exclude_words: Words to exclude (e.g., detected location words like "new", "york")
        """
        entities = []
        seen = set()
        exclude = exclude_words or set()

        # Use table patterns
        for pattern in self.TABLE_PATTERNS:
            matches = re.findall(pattern, question, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    # Take the capturing group that looks like a table name
                    for m in match:
                        if m and m.lower() not in self.STOP_WORDS and m.lower() not in exclude and m not in seen:
                            self._add_table_entity(entities, m, seen)
                elif match and match.lower() not in self.STOP_WORDS and match.lower() not in exclude and match not in seen:
                    self._add_table_entity(entities, match, seen)

        # Also check individual words that look like table names
        words = re.findall(r'\b([a-z_][a-z0-9_]*)\b', question)
        for word in words:
            if (len(word) > 3 and
                word not in self.STOP_WORDS and
                word not in exclude and
                word not in seen and
                self._looks_like_table(word)):
                self._add_table_entity(entities, word, seen)

        return entities

    def _add_table_entity(self, entities: List[ExtractedEntity], word: str, seen: Set[str]):
        """Add a table entity with schema matching."""
        seen.add(word)
        match = self._fuzzy_match_table(word)
        entities.append(ExtractedEntity(
            original_text=word,
            entity_type='table',
            normalized_value=match if match else word,
            confidence=0.85 if match else 0.4,
            mapped_to_schema=match is not None,
            schema_match=match
        ))

    def _extract_column_entities(self, question: str, exclude_words: Set[str] = None) -> List[ExtractedEntity]:
        """Extract potential column references.

        Args:
            question: The question text (lowercase)
            exclude_words: Words to exclude (e.g., detected location words like "new", "york")
        """
        entities = []
        seen = set()
        exclude = exclude_words or set()

        for pattern in self.COLUMN_PATTERNS:
            matches = re.findall(pattern, question, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    for m in match:
                        if m and m.lower() not in self.STOP_WORDS and m.lower() not in exclude and m not in seen:
                            self._add_column_entity(entities, m, seen)
                elif match and match.lower() not in self.STOP_WORDS and match.lower() not in exclude and match not in seen:
                    self._add_column_entity(entities, match, seen)

        return entities

    def _add_column_entity(self, entities: List[ExtractedEntity], word: str, seen: Set[str]):
        """Add a column entity with schema matching."""
        seen.add(word)
        match_table, match_col = self._find_column_in_schema(word)
        entities.append(ExtractedEntity(
            original_text=word,
            entity_type='column',
            normalized_value=match_col if match_col else word,
            confidence=0.8 if match_col else 0.4,
            mapped_to_schema=match_col is not None,
            schema_match=f"{match_table}.{match_col}" if match_table else None
        ))

    def _extract_value_entities(self, question: str) -> List[ExtractedEntity]:
        """Extract filter values from question."""
        entities = []

        # Extract numeric values
        numbers = re.findall(r'\b(\d+(?:\.\d+)?)\b', question)
        for num in numbers:
            entities.append(ExtractedEntity(
                original_text=num,
                entity_type='value',
                normalized_value=float(num),
                confidence=0.9,
                mapped_to_schema=True,
                schema_match=None
            ))

        # Extract quoted strings
        quoted = re.findall(r'"([^"]+)"|\'([^\']+)\'', question)
        for q in quoted:
            value = q[0] or q[1]
            entities.append(ExtractedEntity(
                original_text=value,
                entity_type='value',
                normalized_value=value,
                confidence=0.95,
                mapped_to_schema=True,
                schema_match=None
            ))

        return entities

    def _identify_required_tables(
        self,
        entities: List[ExtractedEntity],
        question: str
    ) -> Set[str]:
        """Identify which tables are needed for this query."""
        tables = set()

        # From matched entities
        for entity in entities:
            if entity.entity_type == 'table' and entity.mapped_to_schema:
                tables.add(entity.schema_match)

        # If no tables found, try to infer from the question
        if not tables:
            # Look for table names directly in question
            for table in self.tables:
                if table.lower() in question or table.lower() + 's' in question:
                    tables.add(table)
                # Check singular form
                if table.lower().endswith('s'):
                    singular = table.lower()[:-1]
                    if singular in question:
                        tables.add(table)

        return tables

    def _identify_required_columns(
        self,
        entities: List[ExtractedEntity],
        tables: Set[str]
    ) -> Dict[str, Set[str]]:
        """Identify which columns are needed per table."""
        columns = {}

        for entity in entities:
            if entity.entity_type == 'column' and entity.mapped_to_schema:
                if entity.schema_match and '.' in entity.schema_match:
                    table, col = entity.schema_match.split('.', 1)
                    if table not in columns:
                        columns[table] = set()
                    columns[table].add(col)

        return columns

    def _extract_aggregations(self, question: str) -> List[str]:
        """Extract aggregation functions needed."""
        aggregations = []

        for keyword, func in self.AGGREGATION_KEYWORDS.items():
            if keyword in question:
                if func not in aggregations:
                    aggregations.append(func)

        # Special patterns
        if 'how many' in question or 'number of' in question:
            if 'COUNT' not in aggregations:
                aggregations.append('COUNT')

        return aggregations

    def _extract_filters(self, question: str) -> List[Dict[str, Any]]:
        """Extract filter conditions from question."""
        filters = []

        # Numeric comparison patterns
        patterns = [
            (r'(under|less\s+than|below|<)\s*\$?(\d+(?:\.\d+)?)', '<'),
            (r'(over|more\s+than|above|>)\s*\$?(\d+(?:\.\d+)?)', '>'),
            (r'(at\s+least|>=)\s*\$?(\d+(?:\.\d+)?)', '>='),
            (r'(at\s+most|<=)\s*\$?(\d+(?:\.\d+)?)', '<='),
            (r'\$?(\d+(?:\.\d+)?)\s*(or\s+more|and\s+up|\+)', '>='),
            (r'between\s+\$?(\d+(?:\.\d+)?)\s+and\s+\$?(\d+(?:\.\d+)?)', 'BETWEEN'),
        ]

        for pattern, operator in patterns:
            match = re.search(pattern, question, re.IGNORECASE)
            if match:
                groups = match.groups()
                if operator == 'BETWEEN' and len(groups) >= 2:
                    filters.append({
                        'operator': 'BETWEEN',
                        'value': (float(groups[0]), float(groups[1])),
                        'type': 'numeric'
                    })
                else:
                    # Find the numeric value in groups
                    for g in groups:
                        try:
                            value = float(g)
                            filters.append({
                                'operator': operator,
                                'value': value,
                                'type': 'numeric'
                            })
                            break
                        except (ValueError, TypeError):
                            continue

        return filters

    def _validate_requirements(
        self,
        required_tables: Set[str],
        required_columns: Dict[str, Set[str]],
        entities: List[ExtractedEntity]
    ) -> Dict[str, Any]:
        """Validate extracted requirements against schema.

        Returns:
            Dictionary with:
            - can_satisfy: bool
            - matched_tables: Set of validated table names
            - reason: Why query is impossible (if applicable)
            - suggestions: Helpful suggestions
        """
        result = {
            "can_satisfy": True,
            "matched_tables": set(),
            "missing_tables": [],
            "missing_columns": [],
            "reason": None,
            "suggestions": []
        }

        # Check unmatched table entities
        for entity in entities:
            if entity.entity_type == 'table':
                if entity.mapped_to_schema:
                    result["matched_tables"].add(entity.schema_match)
                else:
                    # Only flag as missing if it really looks like a table reference
                    if len(entity.original_text) > 3 and self._looks_like_table(entity.original_text):
                        result["missing_tables"].append(entity.original_text)

        # Check location entities without location columns
        location_entities = [e for e in entities if e.entity_type == 'location']
        if location_entities and not self._has_location_column():
            result["can_satisfy"] = False
            result["missing_columns"].append("state/city/location column")

        # Build failure reason
        if result["missing_tables"] or result["missing_columns"]:
            if result["missing_tables"]:
                result["can_satisfy"] = False
                result["reason"] = f"Tables not found: {', '.join(result['missing_tables'])}"
                # Add suggestions for similar tables
                for mt in result["missing_tables"]:
                    similar = self._find_similar_tables(mt)
                    if similar:
                        result["suggestions"].append(f"Did you mean: {', '.join(similar)}?")

            if result["missing_columns"]:
                if result["reason"]:
                    result["reason"] += f"; Columns not found: {', '.join(result['missing_columns'])}"
                else:
                    result["can_satisfy"] = False
                    result["reason"] = f"Columns not found: {', '.join(result['missing_columns'])}"

        # Add available tables as suggestion
        if not result["can_satisfy"] and self.tables:
            result["suggestions"].append(f"Available tables: {', '.join(sorted(self.tables))}")

        return result

    def _fuzzy_match_table(self, candidate: str, threshold: float = 0.7) -> Optional[str]:
        """Fuzzy match table name against schema."""
        candidate_lower = candidate.lower()

        # Exact match
        if candidate_lower in self.tables_lower:
            return self.tables_lower[candidate_lower]

        # Singular/plural handling
        if candidate_lower.endswith('s'):
            singular = candidate_lower[:-1]
            if singular in self.tables_lower:
                return self.tables_lower[singular]
        else:
            plural = candidate_lower + 's'
            if plural in self.tables_lower:
                return self.tables_lower[plural]

        # Fuzzy match
        best_match = None
        best_score = 0.0
        for table in self.tables:
            score = SequenceMatcher(None, candidate_lower, table.lower()).ratio()
            if score > best_score and score >= threshold:
                best_score = score
                best_match = table

        return best_match

    def _find_column_in_schema(self, candidate: str) -> Tuple[Optional[str], Optional[str]]:
        """Find which table contains this column.

        Returns:
            Tuple of (table_name, column_name) or (None, None)
        """
        candidate_lower = candidate.lower()

        for table, columns in self.columns_by_table.items():
            for col in columns:
                if col.lower() == candidate_lower:
                    return table, col
                # Fuzzy match
                if SequenceMatcher(None, candidate_lower, col.lower()).ratio() >= 0.8:
                    return table, col

        return None, None

    def _find_similar_tables(self, candidate: str, limit: int = 3) -> List[str]:
        """Find similar table names for suggestions."""
        scores = []
        candidate_lower = candidate.lower()

        for table in self.tables:
            score = SequenceMatcher(None, candidate_lower, table.lower()).ratio()
            if score > 0.4:
                scores.append((table, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return [t for t, _ in scores[:limit]]

    def _has_location_column(self) -> bool:
        """Check if schema has location-related columns."""
        location_keywords = ['state', 'city', 'country', 'location', 'address', 'region']
        for columns in self.columns_by_table.values():
            for col in columns:
                if any(kw in col.lower() for kw in location_keywords):
                    return True
        return False

    def _looks_like_table(self, word: str) -> bool:
        """Heuristic: does this word look like a table name?"""
        if word.lower() in self.STOP_WORDS:
            return False
        # Tables are typically nouns, often plural
        # Avoid words that are clearly verbs or adjectives
        verb_endings = ['ing', 'ed', 'ize', 'ify']
        adj_endings = ['ly', 'ful', 'less', 'able', 'ible']
        for ending in verb_endings + adj_endings:
            if word.endswith(ending):
                return False
        return True
