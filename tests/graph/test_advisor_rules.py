"""Tests for graph modeling advisor rules (Phase 25.6)."""

import pytest

from src.graph.schema.advisor_rules import (
    AdvisorFinding,
    RuleId,
    Severity,
    check_high_degree_node,
    check_inconsistent_direction,
    check_missing_index_on_lookup,
    check_orphan_nodes,
    check_overloaded_label,
    check_relationship_too_many_props,
    run_all_rules,
)
from src.graph.schema.normalizer import (
    GraphConstraint,
    GraphIndex,
    GraphNodeLabel,
    GraphProperty,
    GraphRelationshipPattern,
    GraphRelationshipType,
    GraphSchema,
)


def _make_schema(**kwargs) -> GraphSchema:
    defaults = dict(
        provider="neo4j",
        database_name="test",
        labels=[],
        relationships=[],
        patterns=[],
        indexes=[],
        constraints=[],
    )
    defaults.update(kwargs)
    return GraphSchema(**defaults)


def _make_label(name: str, props: list[str] | None = None, count: int | None = None) -> GraphNodeLabel:
    properties = [GraphProperty(name=p) for p in (props or [])]
    return GraphNodeLabel(name=name, properties=properties, estimated_count=count)


def _make_rel(name: str, props: list[str] | None = None) -> GraphRelationshipType:
    properties = [GraphProperty(name=p) for p in (props or [])]
    return GraphRelationshipType(name=name, properties=properties)


def _make_pattern(src: str, rt: str, tgt: str, count: int | None = None) -> GraphRelationshipPattern:
    return GraphRelationshipPattern(
        source_labels=[src], relationship_type=rt,
        target_labels=[tgt], estimated_count=count,
    )


def _make_index(name: str, label: str, props: list[str]) -> GraphIndex:
    return GraphIndex(
        name=name, entity_type="NODE",
        labels_or_types=[label], properties=props,
        type="RANGE",
    )


# ── Missing Index ────────────────────────────────────────────────────────


class TestMissingIndexOnLookup:
    def test_flags_unindexed_email(self):
        schema = _make_schema(
            labels=[_make_label("User", ["email", "name"])],
        )
        findings = check_missing_index_on_lookup(schema)
        assert len(findings) == 1
        assert findings[0].rule_id == RuleId.MISSING_INDEX_ON_LOOKUP
        assert findings[0].severity == Severity.HIGH
        assert "email" in findings[0].title

    def test_skips_indexed_email(self):
        schema = _make_schema(
            labels=[_make_label("User", ["email", "name"])],
            indexes=[_make_index("idx_email", "User", ["email"])],
        )
        findings = check_missing_index_on_lookup(schema)
        assert len(findings) == 0

    def test_flags_multiple_lookup_props(self):
        schema = _make_schema(
            labels=[_make_label("Product", ["sku", "slug", "price"])],
        )
        findings = check_missing_index_on_lookup(schema)
        assert len(findings) == 2
        rule_ids = {f.details["property"] for f in findings}
        assert rule_ids == {"sku", "slug"}

    def test_case_insensitive_match(self):
        label = _make_label("User", ["Email"])
        schema = _make_schema(labels=[label])
        findings = check_missing_index_on_lookup(schema)
        assert len(findings) == 1

    def test_no_false_positive_on_regular_prop(self):
        schema = _make_schema(
            labels=[_make_label("User", ["name", "age", "city"])],
        )
        findings = check_missing_index_on_lookup(schema)
        assert len(findings) == 0


# ── Overloaded Label ─────────────────────────────────────────────────────


class TestOverloadedLabel:
    def test_flags_over_threshold(self):
        props = [f"prop_{i}" for i in range(16)]
        schema = _make_schema(labels=[_make_label("BigNode", props)])
        findings = check_overloaded_label(schema)
        assert len(findings) == 1
        assert findings[0].rule_id == RuleId.OVERLOADED_LABEL

    def test_passes_at_threshold(self):
        props = [f"prop_{i}" for i in range(15)]
        schema = _make_schema(labels=[_make_label("OkNode", props)])
        findings = check_overloaded_label(schema)
        assert len(findings) == 0


# ── Relationship Too Many Props ──────────────────────────────────────────


class TestRelationshipTooManyProps:
    def test_flags_heavy_relationship(self):
        props = [f"prop_{i}" for i in range(7)]
        schema = _make_schema(relationships=[_make_rel("TRANSACTION", props)])
        findings = check_relationship_too_many_props(schema)
        assert len(findings) == 1
        assert findings[0].rule_id == RuleId.RELATIONSHIP_TOO_MANY_PROPS

    def test_passes_at_threshold(self):
        props = [f"prop_{i}" for i in range(6)]
        schema = _make_schema(relationships=[_make_rel("SENT", props)])
        findings = check_relationship_too_many_props(schema)
        assert len(findings) == 0


# ── Inconsistent Direction ───────────────────────────────────────────────


class TestInconsistentDirection:
    def test_flags_bidirectional(self):
        schema = _make_schema(patterns=[
            _make_pattern("User", "FOLLOWS", "User"),
            _make_pattern("User", "FOLLOWS", "User"),
        ])
        # Same direction, same labels — no finding
        findings = check_inconsistent_direction(schema)
        assert len(findings) == 0

    def test_flags_reversed_pair(self):
        schema = _make_schema(patterns=[
            _make_pattern("User", "KNOWS", "Company"),
            _make_pattern("Company", "KNOWS", "User"),
        ])
        findings = check_inconsistent_direction(schema)
        assert len(findings) == 1
        assert findings[0].rule_id == RuleId.INCONSISTENT_DIRECTION

    def test_different_rel_types_no_flag(self):
        schema = _make_schema(patterns=[
            _make_pattern("User", "MANAGES", "Team"),
            _make_pattern("Team", "BELONGS_TO", "User"),
        ])
        findings = check_inconsistent_direction(schema)
        assert len(findings) == 0


# ── Orphan Nodes ─────────────────────────────────────────────────────────


class TestOrphanNodes:
    def test_flags_disconnected_label(self):
        schema = _make_schema(
            labels=[
                _make_label("User", count=100),
                _make_label("Orphan", count=50),
            ],
            patterns=[_make_pattern("User", "KNOWS", "User")],
        )
        findings = check_orphan_nodes(schema)
        assert len(findings) == 1
        assert findings[0].entity_name == "Orphan"

    def test_skips_zero_count_orphan(self):
        schema = _make_schema(
            labels=[_make_label("Empty", count=0)],
            patterns=[],
        )
        findings = check_orphan_nodes(schema)
        assert len(findings) == 0

    def test_connected_label_no_flag(self):
        schema = _make_schema(
            labels=[_make_label("User", count=100)],
            patterns=[_make_pattern("User", "KNOWS", "User")],
        )
        findings = check_orphan_nodes(schema)
        assert len(findings) == 0


# ── High Degree Node ────────────────────────────────────────────────────


class TestHighDegreeNode:
    def test_flags_hub_label(self):
        patterns = [
            _make_pattern("Hub", f"R{i}", f"Target{i}", count=5000)
            for i in range(6)
        ]
        schema = _make_schema(
            labels=[_make_label("Hub", count=100)],
            patterns=patterns,
        )
        findings = check_high_degree_node(schema)
        assert len(findings) == 1
        assert findings[0].rule_id == RuleId.HIGH_DEGREE_NODE
        assert findings[0].entity_name == "Hub"

    def test_skips_low_pattern_count(self):
        patterns = [_make_pattern("Node", "R1", "Other", count=50000)]
        schema = _make_schema(
            labels=[_make_label("Node", count=100)],
            patterns=patterns,
        )
        findings = check_high_degree_node(schema)
        assert len(findings) == 0


# ── run_all_rules ────────────────────────────────────────────────────────


class TestRunAllRules:
    def test_returns_sorted_by_severity(self):
        schema = _make_schema(
            labels=[
                _make_label("User", ["email"], count=100),
                _make_label("Orphan", count=50),
            ],
            patterns=[_make_pattern("User", "KNOWS", "User")],
        )
        findings = run_all_rules(schema)
        assert len(findings) >= 2
        severities = [f.severity for f in findings]
        order = {Severity.HIGH: 0, Severity.MEDIUM: 1, Severity.LOW: 2, Severity.INFO: 3}
        assert severities == sorted(severities, key=lambda s: order.get(s, 99))

    def test_empty_schema_no_findings(self):
        schema = _make_schema()
        findings = run_all_rules(schema)
        assert findings == []

    def test_finding_to_dict(self):
        schema = _make_schema(
            labels=[_make_label("User", ["email"])],
        )
        findings = run_all_rules(schema)
        assert len(findings) >= 1
        d = findings[0].to_dict()
        assert "rule_id" in d
        assert "severity" in d
        assert "title" in d
        assert "why" in d
        assert "suggested_fix" in d
