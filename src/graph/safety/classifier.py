"""Cypher safety classifier (Phase 25.3, spec §12).

Static analysis only — no parser dependency. We strip string literals
and comments, uppercase-tokenize, then match against the rule sets in
:mod:`src.graph.safety.rules`.

MVP policy:

* ``READ_ONLY`` → executor allows it.
* Everything else → executor returns HTTP 400 with a ``blocked_reason``
  payload. The frontend renders the reason + a short plain-English
  explanation.

The classifier is intentionally conservative: when in doubt we return
``UNKNOWN`` (which is treated as blocked by the executor). False
positives are tolerable; false negatives — letting a write through —
are not.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from src.graph.safety.rules import (
    ADMIN_PROCEDURE_PREFIXES,
    ALLOWED_READ_PROCEDURES,
    APOC_WRITE_PREFIXES,
    DANGEROUS_KEYWORDS,
    WRITE_KEYWORDS,
)


class GraphQuerySafetyLevel(str, Enum):
    READ_ONLY = "read_only"
    WRITE = "write"
    ADMIN = "admin"
    DANGEROUS = "dangerous"
    UNKNOWN = "unknown"


@dataclass
class SafetyClassification:
    """Structured classifier output.

    ``level`` is the canonical decision; ``reasons`` is a list of
    human-readable strings the executor can splice into the
    ``blocked_reason`` payload so operators can see exactly what
    triggered the block.
    """

    level: GraphQuerySafetyLevel
    reasons: List[str] = field(default_factory=list)
    procedures: List[str] = field(default_factory=list)

    @property
    def is_blocked_for_read_only(self) -> bool:
        return self.level != GraphQuerySafetyLevel.READ_ONLY


# ── Tokenization helpers ──────────────────────────────────────────────────

# Match double-quoted, single-quoted, and back-ticked literals. Triple
# quotes are not part of Cypher, so we don't bother with them. Patterns
# allow escaped quotes inside the string.
_STRING_LITERAL = re.compile(
    r"""
    (?:'(?:\\.|[^'\\])*')    # single-quoted
    |
    (?:"(?:\\.|[^"\\])*")    # double-quoted
    |
    (?:`(?:\\.|[^`\\])*`)    # back-tick identifier — also stripped so a
                              # label named ``CREATE`` doesn't trip us
    """,
    re.VERBOSE | re.DOTALL,
)
_LINE_COMMENT = re.compile(r"//[^\n]*")
_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)


def _normalize(cypher: str) -> str:
    """Strip comments + string literals, collapse whitespace, uppercase."""
    no_block = _BLOCK_COMMENT.sub(" ", cypher)
    no_line = _LINE_COMMENT.sub(" ", no_block)
    no_strings = _STRING_LITERAL.sub(" ", no_line)
    # Whitespace normalization makes multi-word phrases (``DETACH DELETE``)
    # match cleanly with a substring check.
    collapsed = re.sub(r"\s+", " ", no_strings).strip()
    return collapsed.upper()


_PROCEDURE_CALL = re.compile(
    r"\bCALL\s+([A-Za-z_][A-Za-z0-9_.]*)", re.IGNORECASE
)


def _extract_procedures(cypher: str) -> List[str]:
    """Return the lowercased FQNs of every ``CALL <ns.proc>`` we find."""
    return [m.group(1).lower() for m in _PROCEDURE_CALL.finditer(cypher)]


def _has_whole_word(haystack: str, needle: str) -> bool:
    """Whole-word substring match, supporting multi-token needles.

    Operates on the already-uppercased, whitespace-normalized text.
    Uses ``\\b`` boundaries so ``SET`` doesn't match ``ASSET``.
    """
    pattern = r"\b" + re.escape(needle) + r"\b"
    return re.search(pattern, haystack) is not None


# ── Public API ────────────────────────────────────────────────────────────


def classify(cypher: str, *, allow_apoc: bool = False) -> SafetyClassification:
    """Classify ``cypher`` into one of the five safety levels.

    Args:
        cypher: Raw Cypher source (may include strings, comments, line
            breaks). Treated read-only — never mutated.
        allow_apoc: When ``True``, ``apoc.*`` procedure calls escape the
            ADMIN classification and are evaluated by their sub-namespace
            (read APOC stays READ_ONLY; ``apoc.create.*`` etc. fall into
            WRITE). Mirrors the ``GRAPH_ALLOW_APOC`` setting.

    Returns:
        :class:`SafetyClassification` with the chosen level + the list of
        rules that fired (so the API layer can surface a meaningful
        reason).
    """
    if not cypher or not cypher.strip():
        return SafetyClassification(
            level=GraphQuerySafetyLevel.UNKNOWN,
            reasons=["Empty query."],
        )

    text = _normalize(cypher)

    if not text:
        return SafetyClassification(
            level=GraphQuerySafetyLevel.UNKNOWN,
            reasons=["Query reduces to whitespace after stripping comments and literals."],
        )

    reasons: List[str] = []

    # Cheap structural sanity check — wildly unbalanced parens almost
    # always indicate a paste error, and our classifier is text-based so
    # we'd otherwise happily classify ``CREATE (n`` as WRITE despite the
    # query being unrunnable.
    if abs(cypher.count("(") - cypher.count(")")) > 4:
        return SafetyClassification(
            level=GraphQuerySafetyLevel.UNKNOWN,
            reasons=["Unbalanced parentheses — query is likely incomplete."],
        )

    procedures = _extract_procedures(cypher)

    # 1) Dangerous wins outright — those keywords are never recoverable
    #    in MVP.
    for keyword in DANGEROUS_KEYWORDS:
        if _has_whole_word(text, keyword):
            reasons.append(f"Contains dangerous construct: {keyword}.")
            return SafetyClassification(
                level=GraphQuerySafetyLevel.DANGEROUS,
                reasons=reasons,
                procedures=procedures,
            )

    # 2) Admin procedures — anything in dbms.* or db.kill* lives here.
    for proc in procedures:
        if any(proc.startswith(prefix) for prefix in ADMIN_PROCEDURE_PREFIXES):
            reasons.append(f"Calls admin procedure: {proc}.")
            return SafetyClassification(
                level=GraphQuerySafetyLevel.ADMIN,
                reasons=reasons,
                procedures=procedures,
            )

    # 3) Procedure handling for non-admin namespaces.
    for proc in procedures:
        if proc in ALLOWED_READ_PROCEDURES:
            continue  # read-only, OK
        if proc.startswith("apoc."):
            if not allow_apoc:
                reasons.append(
                    f"Calls APOC procedure: {proc} (GRAPH_ALLOW_APOC is False)."
                )
                return SafetyClassification(
                    level=GraphQuerySafetyLevel.ADMIN,
                    reasons=reasons,
                    procedures=procedures,
                )
            # When APOC is permitted, treat known write APOCs as WRITE.
            if any(proc.startswith(p) for p in APOC_WRITE_PREFIXES):
                reasons.append(f"Calls APOC write procedure: {proc}.")
                return SafetyClassification(
                    level=GraphQuerySafetyLevel.WRITE,
                    reasons=reasons,
                    procedures=procedures,
                )
            # Other APOC procs (meta, text, etc.) — treat as read.
            continue
        # Unknown non-allowed procedure — classify as ADMIN so the user
        # gets a clear "we don't recognize this" message rather than a
        # silent pass.
        reasons.append(f"Calls unrecognised procedure: {proc}.")
        return SafetyClassification(
            level=GraphQuerySafetyLevel.ADMIN,
            reasons=reasons,
            procedures=procedures,
        )

    # 4) Plain writes.
    for keyword in WRITE_KEYWORDS:
        if _has_whole_word(text, keyword):
            reasons.append(f"Contains write keyword: {keyword}.")
            return SafetyClassification(
                level=GraphQuerySafetyLevel.WRITE,
                reasons=reasons,
                procedures=procedures,
            )

    # 5) If we got this far there's no recognised mutator. Sanity-check
    #    that we actually saw a Cypher verb — otherwise return UNKNOWN.
    if not _has_whole_word(text, "MATCH") \
            and not _has_whole_word(text, "RETURN") \
            and not _has_whole_word(text, "CALL") \
            and not _has_whole_word(text, "WITH") \
            and not _has_whole_word(text, "UNWIND") \
            and not _has_whole_word(text, "SHOW"):
        return SafetyClassification(
            level=GraphQuerySafetyLevel.UNKNOWN,
            reasons=["No recognised Cypher read clause (MATCH/RETURN/CALL/WITH/UNWIND/SHOW)."],
            procedures=procedures,
        )

    return SafetyClassification(
        level=GraphQuerySafetyLevel.READ_ONLY,
        reasons=[],
        procedures=procedures,
    )


def explain_blocked(level: GraphQuerySafetyLevel, reasons: List[str]) -> str:
    """Compose a user-facing message for a blocked query."""
    base = {
        GraphQuerySafetyLevel.WRITE: (
            "This query would modify data and was blocked because the "
            "Cypher Query Lab is read-only in this release."
        ),
        GraphQuerySafetyLevel.DANGEROUS: (
            "This query contains a destructive or filesystem-level "
            "construct and was blocked."
        ),
        GraphQuerySafetyLevel.ADMIN: (
            "This query calls an administrative procedure that the "
            "Cypher Query Lab does not permit."
        ),
        GraphQuerySafetyLevel.UNKNOWN: (
            "We couldn't safely classify this query, so it was blocked. "
            "Try simplifying or rewriting it."
        ),
    }
    msg = base.get(level, "Query blocked.")
    if reasons:
        msg += " Reason(s): " + "; ".join(reasons)
    return msg


__all__ = [
    "GraphQuerySafetyLevel",
    "SafetyClassification",
    "classify",
    "explain_blocked",
]
