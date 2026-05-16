"""Unit tests for Phase 25.2 — Neo4j schema normalizer (src.graph.schema.normalizer).

Pure data-shape tests with no Neo4j driver dependency; takes the documented
row format returned by the driver and asserts that we collapse it into
:class:`GraphSchema` correctly. Locks down the public contract that the
inspector + API endpoints rely on.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.graph.schema.normalizer import (
    GraphConstraint,
    GraphIndex,
    GraphNodeLabel,
    GraphProperty,
    GraphRelationshipPattern,
    GraphRelationshipType,
    GraphSchema,
    build_indexed_property_lookup,
    graph_schema_from_dict,
    normalize_constraints,
    normalize_indexes,
    normalize_node_type_properties,
    normalize_patterns,
    normalize_rel_type_properties,
)


# ── normalize_node_type_properties ────────────────────────────────────────


class TestNodePropertyNormalization:
    def test_single_label_single_property(self):
        rows = [
            {
                "nodeType": ":`Person`",
                "propertyName": "email",
                "propertyTypes": ["String"],
                "mandatory": True,
            },
        ]
        result = normalize_node_type_properties(rows)
        assert list(result.keys()) == ["Person"]
        prop = result["Person"][0]
        assert prop.name == "email"
        assert prop.types == ["String"]
        assert prop.nullable is False  # mandatory=True → not nullable

    def test_multi_label_node_type(self):
        # Neo4j 5.x labels a node with multiple labels as ":`A`:`B`"
        rows = [
            {
                "nodeType": ":`Customer`:`Person`",
                "propertyName": "id",
                "propertyTypes": ["Integer"],
                "mandatory": True,
            },
        ]
        result = normalize_node_type_properties(rows)
        assert set(result.keys()) == {"Customer", "Person"}
        for label in ("Customer", "Person"):
            assert result[label][0].name == "id"

    def test_merge_types_across_rows(self):
        rows = [
            {
                "nodeType": ":`Order`",
                "propertyName": "shipped_at",
                "propertyTypes": ["DateTime"],
                "mandatory": False,
            },
            {
                "nodeType": ":`Order`",
                "propertyName": "shipped_at",
                "propertyTypes": ["Null"],
                "mandatory": False,
            },
        ]
        result = normalize_node_type_properties(rows)
        prop = result["Order"][0]
        assert set(prop.types) == {"DateTime", "Null"}
        assert prop.nullable is True

    def test_indexed_lookup_marks_property(self):
        rows = [
            {
                "nodeType": ":`User`",
                "propertyName": "email",
                "propertyTypes": ["String"],
                "mandatory": True,
            },
            {
                "nodeType": ":`User`",
                "propertyName": "name",
                "propertyTypes": ["String"],
                "mandatory": False,
            },
        ]
        lookup = {"User": {"email"}}
        result = normalize_node_type_properties(rows, lookup)
        props = {p.name: p for p in result["User"]}
        assert props["email"].indexed is True
        assert props["name"].indexed is False

    def test_missing_node_type_or_property_is_skipped(self):
        rows = [
            {"nodeType": "", "propertyName": "x", "propertyTypes": ["String"]},
            {"nodeType": ":`A`", "propertyName": None, "propertyTypes": ["String"]},
        ]
        assert normalize_node_type_properties(rows) == {}

    def test_mandatory_unknown_keeps_nullable_none(self):
        rows = [
            {
                "nodeType": ":`X`",
                "propertyName": "k",
                "propertyTypes": ["String"],
                # no "mandatory" key
            }
        ]
        prop = normalize_node_type_properties(rows)["X"][0]
        assert prop.nullable is None


# ── normalize_rel_type_properties ─────────────────────────────────────────


class TestRelationshipPropertyNormalization:
    def test_rel_type_strip_colon_and_backticks(self):
        rows = [
            {
                "relType": ":`KNOWS`",
                "propertyName": "since",
                "propertyTypes": ["DateTime"],
                "mandatory": False,
            }
        ]
        result = normalize_rel_type_properties(rows)
        assert list(result.keys()) == ["KNOWS"]
        prop = result["KNOWS"][0]
        assert prop.types == ["DateTime"]
        assert prop.nullable is True

    def test_indexed_lookup_marks_rel_property(self):
        rows = [
            {
                "relType": ":`PURCHASED`",
                "propertyName": "order_id",
                "propertyTypes": ["String"],
                "mandatory": True,
            }
        ]
        lookup = {"PURCHASED": {"order_id"}}
        result = normalize_rel_type_properties(rows, lookup)
        assert result["PURCHASED"][0].indexed is True


# ── normalize_indexes / normalize_constraints ─────────────────────────────


class TestIndexConstraintNormalization:
    def test_normalize_indexes_basic(self):
        rows = [
            {
                "name": "user_email_idx",
                "entityType": "node",  # lowercase normalised to upper
                "labelsOrTypes": ["User"],
                "properties": ["email"],
                "type": "RANGE",
                "state": "ONLINE",
            },
            {
                # malformed row — no name; should be dropped, not raise
                "entityType": "NODE",
                "labelsOrTypes": [],
                "properties": [],
            },
        ]
        idx = normalize_indexes(rows)
        assert len(idx) == 1
        only = idx[0]
        assert only.name == "user_email_idx"
        assert only.entity_type == "NODE"
        assert only.labels_or_types == ["User"]
        assert only.type == "RANGE"

    def test_normalize_constraints_uppercases_type(self):
        rows = [
            {
                "name": "user_email_unique",
                "entityType": "NODE",
                "labelsOrTypes": ["User"],
                "properties": ["email"],
                "type": "uniqueness",
            }
        ]
        c = normalize_constraints(rows)[0]
        assert isinstance(c, GraphConstraint)
        assert c.type == "UNIQUENESS"


# ── build_indexed_property_lookup ─────────────────────────────────────────


class TestIndexedPropertyLookup:
    def test_node_indexes_only(self):
        indexes = [
            GraphIndex(
                name="i1",
                entity_type="NODE",
                labels_or_types=["User"],
                properties=["email"],
                type="RANGE",
            ),
            GraphIndex(
                name="i2",
                entity_type="RELATIONSHIP",
                labels_or_types=["KNOWS"],
                properties=["since"],
                type="RANGE",
            ),
        ]
        node_lookup = build_indexed_property_lookup(indexes, "NODE")
        assert node_lookup == {"User": {"email"}}
        rel_lookup = build_indexed_property_lookup(indexes, "RELATIONSHIP")
        assert rel_lookup == {"KNOWS": {"since"}}

    def test_lookup_index_skipped(self):
        # LOOKUP indexes match every label and should never make a property
        # look "indexed" in the schema explorer.
        indexes = [
            GraphIndex(
                name="lookup",
                entity_type="NODE",
                labels_or_types=["__ANY__"],
                properties=["__id__"],
                type="LOOKUP",
            ),
        ]
        assert build_indexed_property_lookup(indexes, "NODE") == {}


# ── normalize_patterns ────────────────────────────────────────────────────


class TestPatternNormalization:
    def test_sample_rows_to_patterns(self):
        rows = [
            {"sa": ["User"], "rt": "PURCHASED", "tb": ["Product"], "c": 1500},
            {"sa": ["Order"], "rt": "CONTAINS", "tb": ["Product"], "c": 50},
            # malformed row — no rt; dropped
            {"sa": ["X"], "rt": None, "tb": ["Y"], "c": 1},
        ]
        patterns = normalize_patterns(rows)
        assert len(patterns) == 2
        first = patterns[0]
        assert isinstance(first, GraphRelationshipPattern)
        assert first.relationship_type == "PURCHASED"
        assert first.estimated_count == 1500


# ── GraphSchema.to_dict + graph_schema_from_dict round-trip ───────────────


class TestRoundTrip:
    def _schema(self) -> GraphSchema:
        return GraphSchema(
            provider="neo4j",
            database_name="neo4j",
            labels=[
                GraphNodeLabel(
                    name="User",
                    estimated_count=500,
                    properties=[
                        GraphProperty(
                            name="email",
                            types=["String"],
                            indexed=True,
                            nullable=False,
                        )
                    ],
                )
            ],
            relationships=[
                GraphRelationshipType(
                    name="KNOWS",
                    properties=[GraphProperty(name="since", types=["DateTime"])],
                )
            ],
            patterns=[
                GraphRelationshipPattern(
                    source_labels=["User"],
                    relationship_type="KNOWS",
                    target_labels=["User"],
                    estimated_count=42,
                )
            ],
            indexes=[
                GraphIndex(
                    name="user_email",
                    entity_type="NODE",
                    labels_or_types=["User"],
                    properties=["email"],
                    type="RANGE",
                    state="ONLINE",
                )
            ],
            constraints=[
                GraphConstraint(
                    name="user_email_unique",
                    entity_type="NODE",
                    labels_or_types=["User"],
                    properties=["email"],
                    type="UNIQUENESS",
                )
            ],
            warnings=["sampled counts incomplete"],
            collected_at=datetime(2026, 5, 16, 12, 0, tzinfo=timezone.utc),
            server_version="5.18.0",
            edition="enterprise",
        )

    def test_to_dict_shape(self):
        d = self._schema().to_dict()
        assert d["provider"] == "neo4j"
        assert d["label_count"] == 1
        assert d["relationship_type_count"] == 1
        assert d["pattern_count"] == 1
        assert d["index_count"] == 1
        assert d["constraint_count"] == 1
        assert d["warnings"] == ["sampled counts incomplete"]
        assert d["labels"][0]["properties"][0]["indexed"] is True

    def test_round_trip(self):
        original = self._schema()
        rehydrated = graph_schema_from_dict(original.to_dict())
        assert rehydrated.provider == original.provider
        assert rehydrated.database_name == original.database_name
        assert len(rehydrated.labels) == 1
        assert rehydrated.labels[0].name == "User"
        assert rehydrated.labels[0].properties[0].indexed is True
        assert rehydrated.indexes[0].type == "RANGE"
        assert rehydrated.collected_at == original.collected_at

    def test_round_trip_empty(self):
        empty = GraphSchema(provider="neo4j", database_name="neo4j")
        rehydrated = graph_schema_from_dict(empty.to_dict())
        assert rehydrated.labels == []
        assert rehydrated.relationships == []

    def test_from_dict_tolerates_missing_keys(self):
        rehydrated = graph_schema_from_dict(
            {"provider": "neo4j", "database_name": "neo4j"}
        )
        assert rehydrated.labels == []
        assert rehydrated.warnings == []
