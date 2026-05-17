"""Unit tests for the Cypher safety classifier (Phase 25.3).

The classifier is text-based — we don't need a live Neo4j to test it.
We assert one safety level per representative snippet and pin the
reasoning strings for the ones the UI surfaces verbatim.
"""

from __future__ import annotations

import pytest

from src.graph.safety.classifier import (
    GraphQuerySafetyLevel,
    classify,
    explain_blocked,
)


# ── Read-only happy paths ─────────────────────────────────────────────────


@pytest.mark.parametrize(
    "cypher",
    [
        "MATCH (n:User) RETURN n LIMIT 10",
        "MATCH (u:User)-[:PURCHASED]->(o:Order) RETURN u, o",
        "MATCH (n) WHERE n.email = 'alice@example.com' RETURN n",
        "MATCH (n) WITH n LIMIT 5 RETURN n",
        "UNWIND [1,2,3] AS x RETURN x",
        "RETURN 1 AS one",
        "SHOW INDEXES",
        "SHOW CONSTRAINTS",
        "CALL db.labels() YIELD label RETURN label",
        "CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType",
        "CALL db.schema.nodeTypeProperties()",
        "MATCH p=(a)-[*1..3]-(b) RETURN p LIMIT 50",
        # String literal contains a keyword that should be stripped.
        "MATCH (n:User {note: 'CREATE THIS'}) RETURN n",
        # Comment contains keyword.
        "MATCH (n) RETURN n // CREATE was here",
        "/* DELETE in comment */ MATCH (n) RETURN n",
        # Back-ticked identifier named after a keyword shouldn't trip.
        "MATCH (n:`CREATE`) RETURN n",
    ],
)
def test_classify_read_only(cypher: str):
    result = classify(cypher)
    assert result.level == GraphQuerySafetyLevel.READ_ONLY, (
        f"Expected READ_ONLY for: {cypher!r} — got {result.level} ({result.reasons})"
    )


# ── Write classifications ────────────────────────────────────────────────


@pytest.mark.parametrize(
    "cypher",
    [
        "CREATE (n:User {name: 'Alice'})",
        "MERGE (u:User {email: 'a@b.com'})",
        "MATCH (n:User) DELETE n",
        "MATCH (n:User) DETACH DELETE n",
        "MATCH (n) SET n.flag = true",
        "MATCH (n) REMOVE n.flag",
    ],
)
def test_classify_write(cypher: str):
    result = classify(cypher)
    assert result.level == GraphQuerySafetyLevel.WRITE
    assert result.is_blocked_for_read_only is True


# ── Dangerous classifications ────────────────────────────────────────────


@pytest.mark.parametrize(
    "cypher",
    [
        "DROP INDEX user_email_idx",
        "DROP CONSTRAINT user_email_unique",
        "CREATE INDEX user_email FOR (u:User) ON (u.email)",
        "CREATE CONSTRAINT user_email IF NOT EXISTS FOR (u:User) REQUIRE u.email IS UNIQUE",
        "LOAD CSV WITH HEADERS FROM 'file:///users.csv' AS row CREATE (:User {email: row.email})",
        "USING PERIODIC COMMIT 500 LOAD CSV FROM 'file:///x.csv' AS row CREATE (:X {a: row[0]})",
        "CREATE DATABASE newdb",
        "DROP DATABASE olddb",
    ],
)
def test_classify_dangerous(cypher: str):
    result = classify(cypher)
    assert result.level == GraphQuerySafetyLevel.DANGEROUS


# ── Admin classifications (procedures) ───────────────────────────────────


@pytest.mark.parametrize(
    "cypher",
    [
        "CALL dbms.components()",
        "CALL dbms.killTransaction('tx-42')",
        "CALL apoc.cypher.runWrite('CREATE (n) RETURN n', {})",
        # Unrecognized procedure when APOC is disabled.
        "CALL apoc.meta.schema()",
        # Non-allowed non-APOC procedure.
        "CALL custom.something()",
    ],
)
def test_classify_admin(cypher: str):
    result = classify(cypher)
    assert result.level == GraphQuerySafetyLevel.ADMIN


def test_apoc_read_passes_when_allowed():
    """``apoc.meta.schema`` is read-only — should pass when allow_apoc=True."""
    result = classify("CALL apoc.meta.schema()", allow_apoc=True)
    assert result.level == GraphQuerySafetyLevel.READ_ONLY


def test_apoc_write_still_blocked_when_apoc_allowed():
    """Even with GRAPH_ALLOW_APOC, writes through APOC should be WRITE."""
    result = classify(
        "CALL apoc.create.node(['User'], {name: 'A'})", allow_apoc=True
    )
    assert result.level == GraphQuerySafetyLevel.WRITE


def test_apoc_periodic_blocked_when_apoc_allowed():
    """``apoc.periodic.*`` orchestrates writes — must be flagged."""
    result = classify(
        "CALL apoc.periodic.iterate('MATCH (n) RETURN n', 'SET n.x=1', {})",
        allow_apoc=True,
    )
    assert result.level == GraphQuerySafetyLevel.WRITE


# ── Unknown / degenerate ─────────────────────────────────────────────────


@pytest.mark.parametrize(
    "cypher",
    [
        "",
        "   ",
        "// just a comment",
        "/* nothing useful */",
        # No recognisable verb.
        "FOOBAR baz qux",
        # Wildly unbalanced parens.
        "MATCH (((((((n RETURN n",
    ],
)
def test_classify_unknown(cypher: str):
    result = classify(cypher)
    assert result.level == GraphQuerySafetyLevel.UNKNOWN


# ── Reasoning + explain helpers ──────────────────────────────────────────


def test_reasons_surface_offending_keyword():
    result = classify("MATCH (n) DELETE n")
    assert any("DELETE" in r for r in result.reasons)


def test_explain_blocked_includes_reasons():
    result = classify("CREATE (n:X)")
    msg = explain_blocked(result.level, result.reasons)
    assert "read-only" in msg.lower()
    assert "CREATE" in msg


def test_explain_blocked_dangerous():
    result = classify("DROP DATABASE x")
    msg = explain_blocked(result.level, result.reasons)
    assert "destructive" in msg.lower() or "filesystem-level" in msg.lower()


def test_procedures_field_populated():
    result = classify(
        "CALL db.labels() YIELD label CALL db.indexes() YIELD name RETURN label, name"
    )
    assert "db.labels" in result.procedures
    assert "db.indexes" in result.procedures


def test_string_literal_keyword_is_ignored():
    """``CREATE`` inside a string must not flip the classification."""
    result = classify("MATCH (n) WHERE n.script = 'CREATE TABLE' RETURN n")
    assert result.level == GraphQuerySafetyLevel.READ_ONLY


def test_block_comment_keyword_is_ignored():
    result = classify("MATCH (n) /* CREATE */ RETURN n")
    assert result.level == GraphQuerySafetyLevel.READ_ONLY


def test_set_substring_not_matched():
    """``SET`` must not match inside ``ASSET`` (whole-word safety)."""
    result = classify("MATCH (a:Asset) RETURN a")
    assert result.level == GraphQuerySafetyLevel.READ_ONLY


def test_multiple_writes_returns_first_match():
    """The classifier returns at the first WRITE — reasons reflect that."""
    result = classify("MATCH (n) DELETE n SET n.x = 1")
    assert result.level == GraphQuerySafetyLevel.WRITE
    # We just need *some* reason that explains the block.
    assert result.reasons


def test_is_blocked_for_read_only_true_when_unknown():
    result = classify("")
    assert result.is_blocked_for_read_only is True


def test_is_blocked_for_read_only_false_when_read_only():
    result = classify("MATCH (n) RETURN n")
    assert result.is_blocked_for_read_only is False
