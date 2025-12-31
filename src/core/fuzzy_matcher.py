"""Centralized Fuzzy Matching Utility.

This module provides fast, consistent fuzzy matching for schema elements (tables, columns).
It addresses the PR review feedback about O(N*M) performance with SequenceMatcher
by using optimized algorithms with early cutoffs.

Key optimizations:
1. Fast pre-filtering using set intersection before expensive comparisons
2. Early cutoff on exact/plural matches (most common cases)
3. Caching of lowercase/normalized forms
4. Optional use of rapidfuzz if available (10x faster)

Usage:
    matcher = FuzzyMatcher(tables=['customers', 'orders', 'products'])
    result = matcher.find_table('custmer')  # Returns 'customers' with score 0.85
"""
from dataclasses import dataclass
from typing import List, Optional, Set, Dict, Tuple
import logging

logger = logging.getLogger(__name__)

# Try to use rapidfuzz if available (10x faster than difflib)
try:
    from rapidfuzz import fuzz
    from rapidfuzz.distance import Levenshtein
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False
    from difflib import SequenceMatcher


@dataclass
class FuzzyMatchResult:
    """Result of a fuzzy match operation.

    Attributes:
        match: The matched string (None if no match found)
        score: Similarity score (0.0-1.0)
        original: The original search term
        match_type: How the match was found ('exact', 'plural', 'fuzzy')
    """
    match: Optional[str]
    score: float
    original: str
    match_type: str  # 'exact', 'plural', 'fuzzy', 'none'

    def is_match(self, threshold: float = 0.7) -> bool:
        """Check if this result is a valid match above threshold."""
        return self.match is not None and self.score >= threshold


class FuzzyMatcher:
    """Fast fuzzy matching for schema elements.

    This class provides consistent fuzzy matching across the codebase,
    replacing duplicated logic in QueryIntentClassifier and SQLSemanticValidator.

    Performance optimizations:
    - Exact/plural matching first (O(1) with hash lookups)
    - Character set pre-filtering before expensive comparisons
    - Uses rapidfuzz if available (10x faster than difflib)
    - Caches normalized forms to avoid repeated lowercase operations
    """

    def __init__(
        self,
        tables: Optional[List[str]] = None,
        columns: Optional[Dict[str, Set[str]]] = None,
        default_threshold: float = 0.7
    ):
        """Initialize the fuzzy matcher.

        Args:
            tables: List of table names to match against
            columns: Dict mapping table names to sets of column names
            default_threshold: Default similarity threshold (0.0-1.0)
        """
        self.default_threshold = default_threshold

        # Table name indexes
        self.tables: Set[str] = set(tables or [])
        self.tables_lower: Dict[str, str] = {t.lower(): t for t in self.tables}

        # Column indexes by table
        self.columns_by_table: Dict[str, Set[str]] = columns or {}
        self.all_columns: Set[str] = set()
        self.column_to_tables: Dict[str, List[str]] = {}  # column -> list of tables

        # Build column indexes
        for table, cols in self.columns_by_table.items():
            for col in cols:
                self.all_columns.add(col)
                if col.lower() not in self.column_to_tables:
                    self.column_to_tables[col.lower()] = []
                self.column_to_tables[col.lower()].append(table)

    @staticmethod
    def similarity(s1: str, s2: str) -> float:
        """Calculate similarity between two strings.

        Uses rapidfuzz if available (10x faster), falls back to difflib.

        Args:
            s1: First string
            s2: Second string

        Returns:
            Similarity score (0.0-1.0)
        """
        if RAPIDFUZZ_AVAILABLE:
            # rapidfuzz returns 0-100, normalize to 0-1
            return fuzz.ratio(s1.lower(), s2.lower()) / 100.0
        else:
            return SequenceMatcher(None, s1.lower(), s2.lower()).ratio()

    @staticmethod
    def _char_overlap(s1: str, s2: str) -> float:
        """Fast character set overlap check for pre-filtering.

        This is O(n+m) and can quickly reject very dissimilar strings
        before running expensive similarity algorithms.
        """
        set1 = set(s1.lower())
        set2 = set(s2.lower())
        if not set1 or not set2:
            return 0.0
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union  # Jaccard similarity

    def find_table(
        self,
        candidate: str,
        threshold: Optional[float] = None
    ) -> FuzzyMatchResult:
        """Find the best matching table name.

        Args:
            candidate: Search term (e.g., 'custmer', 'customer', 'customers')
            threshold: Minimum similarity score (default: self.default_threshold)

        Returns:
            FuzzyMatchResult with match details
        """
        threshold = threshold or self.default_threshold
        candidate_lower = candidate.lower()

        # Step 1: Exact match (O(1))
        if candidate_lower in self.tables_lower:
            return FuzzyMatchResult(
                match=self.tables_lower[candidate_lower],
                score=1.0,
                original=candidate,
                match_type='exact'
            )

        # Step 2: Singular/plural match (O(1))
        # Check if adding/removing 's' gives exact match
        if candidate_lower.endswith('s'):
            singular = candidate_lower[:-1]
            if singular in self.tables_lower:
                return FuzzyMatchResult(
                    match=self.tables_lower[singular],
                    score=0.95,
                    original=candidate,
                    match_type='plural'
                )
        else:
            plural = candidate_lower + 's'
            if plural in self.tables_lower:
                return FuzzyMatchResult(
                    match=self.tables_lower[plural],
                    score=0.95,
                    original=candidate,
                    match_type='plural'
                )

        # Step 3: Fuzzy match with pre-filtering
        best_match = None
        best_score = 0.0

        for table in self.tables:
            # Fast pre-filter: skip if character overlap is too low
            char_overlap = self._char_overlap(candidate_lower, table.lower())
            if char_overlap < 0.3:  # Very different character sets
                continue

            # Full similarity check
            score = self.similarity(candidate, table)
            if score > best_score and score >= threshold:
                best_score = score
                best_match = table

        if best_match:
            return FuzzyMatchResult(
                match=best_match,
                score=best_score,
                original=candidate,
                match_type='fuzzy'
            )

        return FuzzyMatchResult(
            match=None,
            score=0.0,
            original=candidate,
            match_type='none'
        )

    def find_column(
        self,
        candidate: str,
        table: Optional[str] = None,
        threshold: Optional[float] = None
    ) -> Tuple[Optional[str], Optional[str], float]:
        """Find the best matching column, optionally within a specific table.

        Args:
            candidate: Column name to search for
            table: Optional table to search within (if None, searches all)
            threshold: Minimum similarity score

        Returns:
            Tuple of (table_name, column_name, score) or (None, None, 0.0)
        """
        threshold = threshold if threshold is not None else 0.8
        candidate_lower = candidate.lower()

        # Determine which columns to search
        if table:
            columns_to_search = [(table, col) for col in self.columns_by_table.get(table, [])]
        else:
            columns_to_search = [
                (t, col)
                for t, cols in self.columns_by_table.items()
                for col in cols
            ]

        # Exact match first (O(1) if searching within table)
        if candidate_lower in self.column_to_tables:
            tables_with_col = self.column_to_tables[candidate_lower]
            if table is None or table in tables_with_col:
                matched_table = table if table else tables_with_col[0]
                # Find the actual cased column name
                for col in self.columns_by_table.get(matched_table, []):
                    if col.lower() == candidate_lower:
                        return (matched_table, col, 1.0)

        # Fuzzy match
        best_match = (None, None, 0.0)

        for tbl, col in columns_to_search:
            # Pre-filter
            char_overlap = self._char_overlap(candidate_lower, col.lower())
            if char_overlap < 0.3:
                continue

            score = self.similarity(candidate, col)
            if score > best_match[2] and score >= threshold:
                best_match = (tbl, col, score)

        return best_match

    def find_similar(
        self,
        candidate: str,
        candidates: Set[str],
        max_results: int = 3,
        threshold: float = 0.4
    ) -> List[Tuple[str, float]]:
        """Find similar strings from a set of candidates.

        Used for generating "Did you mean...?" suggestions.

        Args:
            candidate: Search term
            candidates: Set of possible matches
            max_results: Maximum number of results to return
            threshold: Minimum similarity threshold

        Returns:
            List of (match, score) tuples, sorted by score descending
        """
        scored = []
        candidate_lower = candidate.lower()

        for c in candidates:
            # Pre-filter
            char_overlap = self._char_overlap(candidate_lower, c.lower())
            if char_overlap < 0.2:
                continue

            score = self.similarity(candidate, c)
            if score >= threshold:
                scored.append((c, score))

        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:max_results]

    def update_tables(self, tables: List[str]) -> None:
        """Update the table list (for schema changes)."""
        self.tables = set(tables)
        self.tables_lower = {t.lower(): t for t in self.tables}

    def update_columns(self, columns_by_table: Dict[str, Set[str]]) -> None:
        """Update the column mapping (for schema changes)."""
        self.columns_by_table = columns_by_table
        self.all_columns.clear()
        self.column_to_tables.clear()

        for table, cols in columns_by_table.items():
            for col in cols:
                self.all_columns.add(col)
                if col.lower() not in self.column_to_tables:
                    self.column_to_tables[col.lower()] = []
                self.column_to_tables[col.lower()].append(table)


# Convenience functions for one-off matching
def fuzzy_match_table(
    candidate: str,
    tables: List[str],
    threshold: float = 0.7
) -> Optional[str]:
    """Quick fuzzy match for a table name.

    For repeated matching, prefer creating a FuzzyMatcher instance.
    """
    matcher = FuzzyMatcher(tables=tables, default_threshold=threshold)
    result = matcher.find_table(candidate)
    return result.match if result.is_match(threshold) else None


def fuzzy_match_column(
    candidate: str,
    columns_by_table: Dict[str, Set[str]],
    table: Optional[str] = None,
    threshold: float = 0.8
) -> Tuple[Optional[str], Optional[str]]:
    """Quick fuzzy match for a column name.

    For repeated matching, prefer creating a FuzzyMatcher instance.
    """
    matcher = FuzzyMatcher(columns=columns_by_table)
    tbl, col, score = matcher.find_column(candidate, table, threshold)
    return (tbl, col) if score >= threshold else (None, None)
