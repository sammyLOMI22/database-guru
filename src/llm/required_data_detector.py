"""Required Data Detection - Extracts what data is needed before SQL generation.

This module analyzes questions to identify required tables, columns, and values,
then validates against the schema to detect CANNOT_ANSWER cases early.

Key Features:
- Fast regex-based extraction (no LLM calls)
- Fuzzy matching for table/column names
- Singular/plural normalization
- Location detection integration
- Helpful suggestions for impossible queries

Usage:
    detector = RequiredDataDetector(schema_dict)
    result = detector.detect_required_data("Show products from California")

    if not result.can_satisfy:
        print(f"Cannot answer: {result.impossible_reason}")
        print(f"Suggestions: {result.suggestions}")
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set, Tuple
from difflib import SequenceMatcher
import re
import logging

logger = logging.getLogger(__name__)


@dataclass
class SchemaMatch:
    """Result of matching an entity to schema.

    Attributes:
        entity_text: The original text being matched
        matched: Whether a match was found
        match_type: Type of match ("exact", "fuzzy", "plural", "none")
        similarity: Similarity score for fuzzy matches (0.0-1.0)
        matched_name: The actual schema element name
        suggestions: Alternative names if no match
    """
    entity_text: str
    matched: bool
    match_type: str
    similarity: float = 0.0
    matched_name: Optional[str] = None
    suggestions: List[str] = field(default_factory=list)


@dataclass
class RequiredDataResult:
    """What data is required to answer the query.

    Attributes:
        tables_required: Set of validated table names
        columns_required: Columns needed, grouped by table
        values_required: Filter values (column -> value mapping)
        locations_detected: Location references with normalization
        can_satisfy: Whether the schema can satisfy the query
        missing_tables: Table names that weren't found
        missing_columns: Column names that weren't found (by context)
        suggestions: Helpful suggestions for the user
        impossible_reason: Explanation if can_satisfy is False
    """
    tables_required: Set[str] = field(default_factory=set)
    columns_required: Dict[str, Set[str]] = field(default_factory=dict)
    values_required: Dict[str, Any] = field(default_factory=dict)
    locations_detected: List[Dict[str, str]] = field(default_factory=list)
    can_satisfy: bool = True
    missing_tables: List[str] = field(default_factory=list)
    missing_columns: Dict[str, List[str]] = field(default_factory=dict)
    suggestions: List[str] = field(default_factory=list)
    impossible_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "tables_required": list(self.tables_required),
            "columns_required": {k: list(v) for k, v in self.columns_required.items()},
            "values_required": self.values_required,
            "locations_detected": self.locations_detected,
            "can_satisfy": self.can_satisfy,
            "missing_tables": self.missing_tables,
            "missing_columns": self.missing_columns,
            "suggestions": self.suggestions,
            "impossible_reason": self.impossible_reason
        }


class RequiredDataDetector:
    """Detects what data is needed and validates against schema.

    This class is designed for fast, pre-generation validation to catch
    impossible queries before wasting an LLM call.

    Performance target: <20ms for validation
    """

    # Patterns for extracting table references
    TABLE_PATTERNS = [
        r'\b(all|show|list|get|find|display)\s+(\w+)',
        r'\bfrom\s+(\w+)',
        r'(\w+)\s+table',
        r'(\w+)\s+data',
        r'(\w+)\s+records',
        r'(\w+)\s+information',
    ]

    # Patterns for extracting column references
    COLUMN_PATTERNS = [
        r'\b(by|group\s+by|order\s+by|sort\s+by)\s+(\w+)',
        r'(\w+)\s+(is|equals?|=|>|<|>=|<=|!=)',
        r'\b(where|filter|with)\s+(\w+)',
        r'\b(\w+)\s+(greater|less|more|fewer)\s+than',
    ]

    # Words to ignore when extracting entities
    STOP_WORDS = {
        # Verbs and question words
        'show', 'list', 'find', 'get', 'all', 'from', 'where', 'with',
        'the', 'and', 'how', 'many', 'what', 'which', 'their', 'that',
        'this', 'have', 'has', 'been', 'were', 'was', 'are', 'total',
        'count', 'number', 'give', 'display', 'select', 'each', 'every',
        'some', 'any', 'more', 'less', 'than', 'over', 'under', 'above',
        'below', 'between', 'before', 'after', 'during', 'since', 'until',
        'only', 'also', 'just', 'even', 'still', 'already', 'data',
        'table', 'information', 'records', 'entries', 'items', 'results',
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
        'value', 'values', 'is', 'on', 'in', 'to', 'for', 'by', 'at',
        'of', 'an', 'a',
    }

    def __init__(self, schema_dict: Dict[str, Any]):
        """Initialize with schema for validation.

        Args:
            schema_dict: Parsed schema dictionary from SchemaInspector
        """
        self.schema = schema_dict
        self.tables = set(schema_dict.get("tables", {}).keys())
        self.tables_lower = {t.lower(): t for t in self.tables}
        self.columns_by_table = self._build_column_index()
        self.all_columns = self._build_all_columns()
        self.all_columns_lower = {c.lower(): c for c in self.all_columns}

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

    def detect_required_data(self, question: str) -> RequiredDataResult:
        """Main entry point: detect what data is needed.

        Analyzes the question to extract:
        1. Location mentions (FIRST - to exclude from table/column matching)
        2. Table references
        3. Column references
        4. Filter values

        Then validates all against the schema.

        Args:
            question: Natural language question

        Returns:
            RequiredDataResult with validation status and suggestions
        """
        question_lower = question.lower()

        # Step 1: Detect locations FIRST (uses LocationMapper)
        # This ensures multi-word locations like "New York" are detected before
        # individual words get filtered as table/column candidates
        locations = self._detect_locations(question)

        # Build set of words that are part of detected locations
        # These should NOT be treated as table or column names
        location_words = set()
        for loc in locations:
            # Split multi-word locations (e.g., "New York" -> {"new", "york"})
            original = loc.get('original', '')
            if original:
                location_words.update(original.lower().split())

        # Step 2: Extract potential table references, excluding location words
        table_candidates = self._extract_table_references(question_lower, exclude_words=location_words)

        # Step 3: Extract potential column references, excluding location words
        column_candidates = self._extract_column_references(question_lower, exclude_words=location_words)

        # Step 4: Extract values (for filters)
        values = self._extract_values(question)

        # Step 5: Validate against schema
        result = self._validate_against_schema(
            table_candidates,
            column_candidates,
            locations
        )

        # Step 6: Add extracted values
        result.values_required = values
        result.locations_detected = locations

        return result

    def _extract_table_references(self, question: str, exclude_words: Set[str] = None) -> List[str]:
        """Extract potential table names from question.

        Uses regex patterns to find words that might be table names,
        then filters out common stop words.

        Args:
            question: The question text (lowercase)
            exclude_words: Words to exclude (e.g., detected location words like "new", "york")
        """
        candidates = []
        seen = set()
        exclude = exclude_words or set()

        # Apply patterns
        for pattern in self.TABLE_PATTERNS:
            matches = re.findall(pattern, question, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    # Add non-stop-word groups
                    for m in match:
                        if m and m.lower() not in self.STOP_WORDS and m.lower() not in exclude and m.lower() not in seen:
                            candidates.append(m)
                            seen.add(m.lower())
                elif match and match.lower() not in self.STOP_WORDS and match.lower() not in exclude and match.lower() not in seen:
                    candidates.append(match)
                    seen.add(match.lower())

        # Also check individual words that look like table names
        words = re.findall(r'\b([a-z][a-z0-9_]*)\b', question)
        for word in words:
            word_lower = word.lower()
            if (len(word) > 3 and
                word_lower not in self.STOP_WORDS and
                word_lower not in exclude and
                word_lower not in seen and
                self._looks_like_entity_name(word)):
                candidates.append(word)
                seen.add(word_lower)

        return candidates

    def _extract_column_references(self, question: str, exclude_words: Set[str] = None) -> List[str]:
        """Extract potential column names from question.

        Args:
            question: The question text (lowercase)
            exclude_words: Words to exclude (e.g., detected location words like "new", "york")
        """
        candidates = []
        seen = set()
        exclude = exclude_words or set()

        for pattern in self.COLUMN_PATTERNS:
            matches = re.findall(pattern, question, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    for m in match:
                        if m and m.lower() not in self.STOP_WORDS and m.lower() not in exclude and m.lower() not in seen:
                            candidates.append(m)
                            seen.add(m.lower())
                elif match and match.lower() not in self.STOP_WORDS and match.lower() not in exclude and match.lower() not in seen:
                    candidates.append(match)
                    seen.add(match.lower())

        return candidates

    def _detect_locations(self, question: str) -> List[Dict[str, str]]:
        """Detect location references (reuses LocationMapper).

        Returns:
            List of location dictionaries with 'original', 'normalized', 'type'
        """
        try:
            from src.core.location_mapper import LocationMapper
            return LocationMapper.detect_location_in_query(question)
        except ImportError:
            logger.debug("LocationMapper not available")
            return []

    def _extract_values(self, question: str) -> Dict[str, Any]:
        """Extract filter values from question.

        Extracts:
        - Numeric values
        - Quoted strings
        - Date-like patterns
        """
        values = {}

        # Extract numbers
        numbers = re.findall(r'\b(\d+(?:\.\d+)?)\b', question)
        if numbers:
            values["_numeric_values"] = [float(n) for n in numbers]

        # Extract quoted strings
        quoted = re.findall(r'"([^"]+)"|\'([^\']+)\'', question)
        if quoted:
            values["_quoted_values"] = [q[0] or q[1] for q in quoted]

        # Extract date patterns (YYYY-MM-DD, MM/DD/YYYY, etc.)
        dates = re.findall(r'\b(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{4})\b', question)
        if dates:
            values["_date_values"] = dates

        return values

    def _validate_against_schema(
        self,
        table_candidates: List[str],
        column_candidates: List[str],
        locations: List[Dict]
    ) -> RequiredDataResult:
        """Validate extracted entities against actual schema.

        Performs fuzzy matching and generates suggestions for missing entities.
        """
        result = RequiredDataResult()

        # Match tables
        for candidate in table_candidates:
            match = self._match_table(candidate)
            if match.matched:
                result.tables_required.add(match.matched_name)
            else:
                # Only add to missing if it looks like a real table reference
                if self._looks_like_entity_name(candidate) and len(candidate) > 3:
                    result.missing_tables.append(candidate)
                    if match.suggestions:
                        result.suggestions.append(
                            f"'{candidate}' not found. Did you mean: {', '.join(match.suggestions)}?"
                        )

        # Match columns
        for candidate in column_candidates:
            match = self._match_column(candidate)
            if match.matched and match.matched_name:
                # Find which table(s) have this column
                tables_with_col = self._find_tables_with_column(match.matched_name)
                for table in tables_with_col:
                    if table not in result.columns_required:
                        result.columns_required[table] = set()
                    result.columns_required[table].add(match.matched_name)
            elif len(candidate) > 2 and self._looks_like_entity_name(candidate):
                # Track missing columns
                if "unknown" not in result.missing_columns:
                    result.missing_columns["unknown"] = []
                result.missing_columns["unknown"].append(candidate)

        # Check if locations can be satisfied
        if locations:
            has_location_column = self._has_location_column()
            if not has_location_column:
                result.can_satisfy = False
                if "location" not in result.missing_columns:
                    result.missing_columns["location"] = []
                result.missing_columns["location"].append("state/city/location column required")

        # Determine overall satisfaction
        if result.missing_tables:
            result.can_satisfy = False
            result.impossible_reason = f"Tables not found: {', '.join(result.missing_tables)}"

        if result.missing_columns and not result.can_satisfy:
            missing_desc = []
            for context, cols in result.missing_columns.items():
                missing_desc.append(f"{context}: {', '.join(cols)}")
            if result.impossible_reason:
                result.impossible_reason += f"; Columns issue: {'; '.join(missing_desc)}"
            else:
                result.can_satisfy = False
                result.impossible_reason = f"Columns issue: {'; '.join(missing_desc)}"

        # Add available tables as suggestion if query is impossible
        if not result.can_satisfy and self.tables:
            sorted_tables = sorted(self.tables)[:10]  # Limit to 10 for readability
            result.suggestions.append(f"Available tables: {', '.join(sorted_tables)}")

        return result

    def _match_table(self, candidate: str, threshold: float = 0.7) -> SchemaMatch:
        """Match a table name candidate against schema.

        Tries:
        1. Exact match (case-insensitive)
        2. Singular/plural variants
        3. Fuzzy matching

        Args:
            candidate: The table name to match
            threshold: Minimum similarity for fuzzy match

        Returns:
            SchemaMatch with match details
        """
        candidate_lower = candidate.lower()

        # Exact match
        if candidate_lower in self.tables_lower:
            return SchemaMatch(
                entity_text=candidate,
                matched=True,
                match_type="exact",
                similarity=1.0,
                matched_name=self.tables_lower[candidate_lower]
            )

        # Singular/plural handling
        if candidate_lower.endswith('s'):
            singular = candidate_lower[:-1]
            if singular in self.tables_lower:
                return SchemaMatch(
                    entity_text=candidate,
                    matched=True,
                    match_type="plural",
                    similarity=0.95,
                    matched_name=self.tables_lower[singular]
                )
        else:
            plural = candidate_lower + 's'
            if plural in self.tables_lower:
                return SchemaMatch(
                    entity_text=candidate,
                    matched=True,
                    match_type="singular",
                    similarity=0.95,
                    matched_name=self.tables_lower[plural]
                )

        # Fuzzy match
        best_match = None
        best_score = 0.0
        for table_lower, table_actual in self.tables_lower.items():
            score = SequenceMatcher(None, candidate_lower, table_lower).ratio()
            if score > best_score:
                best_score = score
                best_match = table_actual

        if best_score >= threshold:
            return SchemaMatch(
                entity_text=candidate,
                matched=True,
                match_type="fuzzy",
                similarity=best_score,
                matched_name=best_match
            )

        # No match - find suggestions
        suggestions = self._find_similar_names(candidate_lower, list(self.tables), limit=3)
        return SchemaMatch(
            entity_text=candidate,
            matched=False,
            match_type="none",
            similarity=best_score,
            suggestions=suggestions
        )

    def _match_column(self, candidate: str, threshold: float = 0.75) -> SchemaMatch:
        """Match a column name candidate against schema.

        Searches all tables for matching columns.
        """
        candidate_lower = candidate.lower()

        # Exact match
        if candidate_lower in self.all_columns_lower:
            return SchemaMatch(
                entity_text=candidate,
                matched=True,
                match_type="exact",
                similarity=1.0,
                matched_name=self.all_columns_lower[candidate_lower]
            )

        # Fuzzy match
        best_match = None
        best_score = 0.0
        for col_lower, col_actual in self.all_columns_lower.items():
            score = SequenceMatcher(None, candidate_lower, col_lower).ratio()
            if score > best_score:
                best_score = score
                best_match = col_actual

        if best_score >= threshold:
            return SchemaMatch(
                entity_text=candidate,
                matched=True,
                match_type="fuzzy",
                similarity=best_score,
                matched_name=best_match
            )

        # No match
        suggestions = self._find_similar_names(candidate_lower, list(self.all_columns), limit=3)
        return SchemaMatch(
            entity_text=candidate,
            matched=False,
            match_type="none",
            similarity=best_score,
            suggestions=suggestions
        )

    def _find_tables_with_column(self, column_name: str) -> List[str]:
        """Find which tables contain a given column."""
        tables = []
        column_lower = column_name.lower()
        for table, columns in self.columns_by_table.items():
            if any(c.lower() == column_lower for c in columns):
                tables.append(table)
        return tables

    def _find_similar_names(
        self,
        candidate: str,
        options: List[str],
        limit: int = 3,
        threshold: float = 0.4
    ) -> List[str]:
        """Find similar names for suggestions.

        Returns:
            List of similar names sorted by similarity
        """
        scores = []
        for opt in options:
            score = SequenceMatcher(None, candidate.lower(), opt.lower()).ratio()
            if score >= threshold:
                scores.append((opt, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return [name for name, _ in scores[:limit]]

    def _has_location_column(self) -> bool:
        """Check if schema has location-related columns."""
        location_keywords = ['state', 'city', 'country', 'location', 'address', 'region', 'province']
        for columns in self.columns_by_table.values():
            for col in columns:
                if any(kw in col.lower() for kw in location_keywords):
                    return True
        return False

    def _looks_like_entity_name(self, word: str) -> bool:
        """Heuristic: does this word look like a table/column name?

        Filters out words that are clearly not entity names:
        - Stop words
        - Very short words
        - Words with verb/adjective endings
        """
        if word.lower() in self.STOP_WORDS:
            return False

        if len(word) <= 2:
            return False

        # Avoid words that are clearly verbs or adjectives
        verb_endings = ['ing', 'ed', 'ize', 'ify', 'ate']
        adj_endings = ['ly', 'ful', 'less', 'able', 'ible', 'ous', 'ive']

        for ending in verb_endings + adj_endings:
            if word.lower().endswith(ending) and len(word) > len(ending) + 2:
                return False

        return True

    def get_column_info(self, table_name: str, column_name: str) -> Optional[Dict[str, Any]]:
        """Get column metadata from schema.

        Useful for understanding column type, sample values, etc.
        """
        table_info = self.schema.get("tables", {}).get(table_name)
        if not table_info:
            return None

        for col in table_info.get("columns", []):
            if col["name"].lower() == column_name.lower():
                return col

        return None

    def get_sample_values(self, table_name: str, column_name: str) -> List[Any]:
        """Get sample values for a column if available in schema."""
        col_info = self.get_column_info(table_name, column_name)
        if col_info:
            return col_info.get("sample_values", [])
        return []
