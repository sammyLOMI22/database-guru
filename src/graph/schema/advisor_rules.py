"""Rule-based graph modeling advisor (Phase 25.6).

Analyzes a :class:`GraphSchema` and produces a list of ranked
:class:`AdvisorFinding` objects. Each finding describes a potential
modeling or performance issue with a ``why`` explanation and a
concrete ``suggested_fix``.

Rules implemented (per spec §11):

* ``MissingIndexOnLookupProperty`` — id / email / slug / sku / externalId
  without an index → full-label scans.
* ``OverloadedNodeLabel`` — >15 unique properties on a single label
  suggests the label conflates multiple domain concepts.
* ``RelationshipWithTooManyProperties`` — >6 properties on a
  relationship type hints that data belongs on a separate node.
* ``InconsistentRelationshipDirection`` — same two labels appear as
  both (A)-[R]->(B) and (B)-[R]->(A).
* ``OrphanNodes`` — labels with >0 estimated nodes but zero
  relationships in any sampled pattern.
* ``HighDegreeNode`` — a label appears in many patterns with high
  estimated counts, suggesting hub nodes that may cause traversal
  hotspots.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from src.graph.schema.normalizer import GraphSchema


class RuleId(str, Enum):
    MISSING_INDEX_ON_LOOKUP = "missing_index_on_lookup"
    OVERLOADED_LABEL = "overloaded_label"
    RELATIONSHIP_TOO_MANY_PROPS = "relationship_too_many_props"
    INCONSISTENT_DIRECTION = "inconsistent_direction"
    ORPHAN_NODES = "orphan_nodes"
    HIGH_DEGREE_NODE = "high_degree_node"


class Severity(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class AdvisorFinding:
    rule_id: RuleId
    severity: Severity
    title: str
    description: str
    why: str
    suggested_fix: str
    entity_name: Optional[str] = None
    entity_type: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id.value,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "why": self.why,
            "suggested_fix": self.suggested_fix,
            "entity_name": self.entity_name,
            "entity_type": self.entity_type,
            "details": self.details,
        }


LOOKUP_PROPERTY_NAMES: Set[str] = {
    "id", "uid", "uuid", "email", "slug", "sku",
    "external_id", "externalId", "external_key", "externalKey",
    "code", "username", "login", "handle",
}

OVERLOADED_PROPERTY_THRESHOLD = 15
RELATIONSHIP_PROPERTY_THRESHOLD = 6
HIGH_DEGREE_PATTERN_THRESHOLD = 5
HIGH_DEGREE_COUNT_THRESHOLD = 10_000


def check_missing_index_on_lookup(schema: GraphSchema) -> List[AdvisorFinding]:
    findings: List[AdvisorFinding] = []
    indexed_props: Dict[str, Set[str]] = {}
    for idx in schema.indexes:
        if (idx.type or "").upper() == "LOOKUP":
            continue
        for label in idx.labels_or_types:
            indexed_props.setdefault(label, set()).update(idx.properties)

    for label in schema.labels:
        label_indexed = indexed_props.get(label.name, set())
        for prop in label.properties:
            if prop.name.lower() in {n.lower() for n in LOOKUP_PROPERTY_NAMES}:
                if prop.name not in label_indexed:
                    findings.append(AdvisorFinding(
                        rule_id=RuleId.MISSING_INDEX_ON_LOOKUP,
                        severity=Severity.HIGH,
                        title=f"No index on {label.name}.{prop.name}",
                        description=(
                            f"Property '{prop.name}' on label '{label.name}' looks like a "
                            f"lookup key but has no index."
                        ),
                        why=(
                            "Without an index, queries filtering on this property "
                            "will scan every node with this label. This becomes "
                            "increasingly expensive as the graph grows."
                        ),
                        suggested_fix=(
                            f"CREATE INDEX FOR (n:{label.name}) ON (n.{prop.name})"
                        ),
                        entity_name=label.name,
                        entity_type="NODE",
                        details={"property": prop.name},
                    ))
    return findings


def check_overloaded_label(schema: GraphSchema) -> List[AdvisorFinding]:
    findings: List[AdvisorFinding] = []
    for label in schema.labels:
        if len(label.properties) > OVERLOADED_PROPERTY_THRESHOLD:
            findings.append(AdvisorFinding(
                rule_id=RuleId.OVERLOADED_LABEL,
                severity=Severity.MEDIUM,
                title=f"Overloaded label: {label.name}",
                description=(
                    f"Label '{label.name}' has {len(label.properties)} properties, "
                    f"which exceeds the recommended threshold of "
                    f"{OVERLOADED_PROPERTY_THRESHOLD}."
                ),
                why=(
                    "A label with too many properties often conflates multiple "
                    "domain concepts. This leads to sparse property storage, "
                    "confusing queries, and makes schema evolution harder."
                ),
                suggested_fix=(
                    f"Consider splitting '{label.name}' into two or more labels "
                    f"that represent distinct domain concepts, connected by "
                    f"relationships."
                ),
                entity_name=label.name,
                entity_type="NODE",
                details={"property_count": len(label.properties)},
            ))
    return findings


def check_relationship_too_many_props(schema: GraphSchema) -> List[AdvisorFinding]:
    findings: List[AdvisorFinding] = []
    for rel in schema.relationships:
        if len(rel.properties) > RELATIONSHIP_PROPERTY_THRESHOLD:
            findings.append(AdvisorFinding(
                rule_id=RuleId.RELATIONSHIP_TOO_MANY_PROPS,
                severity=Severity.MEDIUM,
                title=f"Heavy relationship: {rel.name}",
                description=(
                    f"Relationship type '{rel.name}' has {len(rel.properties)} "
                    f"properties (threshold: {RELATIONSHIP_PROPERTY_THRESHOLD})."
                ),
                why=(
                    "Relationships with many properties suggest the relationship "
                    "itself represents a domain entity. Moving those properties "
                    "to an intermediate node improves query clarity and allows "
                    "indexing on the intermediate node's properties."
                ),
                suggested_fix=(
                    f"Consider extracting '{rel.name}' into an intermediate node "
                    f"(e.g., (:A)-[:HAS_{rel.name}]->(:{rel.name}Node)-[:TO]->(:B))."
                ),
                entity_name=rel.name,
                entity_type="RELATIONSHIP",
                details={"property_count": len(rel.properties)},
            ))
    return findings


def check_inconsistent_direction(schema: GraphSchema) -> List[AdvisorFinding]:
    findings: List[AdvisorFinding] = []
    seen: Dict[str, Set[tuple]] = {}

    for pat in schema.patterns:
        rt = pat.relationship_type
        src = tuple(sorted(pat.source_labels))
        tgt = tuple(sorted(pat.target_labels))
        seen.setdefault(rt, set()).add((src, tgt))

    for rt, directions in seen.items():
        pairs = list(directions)
        for i, (src_a, tgt_a) in enumerate(pairs):
            for src_b, tgt_b in pairs[i + 1:]:
                if src_a == tgt_b and tgt_a == src_b:
                    label_a = ",".join(src_a) or "?"
                    label_b = ",".join(tgt_a) or "?"
                    findings.append(AdvisorFinding(
                        rule_id=RuleId.INCONSISTENT_DIRECTION,
                        severity=Severity.LOW,
                        title=f"Bidirectional {rt} between {label_a} and {label_b}",
                        description=(
                            f"Relationship type '{rt}' appears in both directions "
                            f"between {label_a} and {label_b}."
                        ),
                        why=(
                            "Bidirectional relationships of the same type between "
                            "the same labels can confuse traversal queries and "
                            "double storage. If the relationship is truly "
                            "symmetric, consider using a single direction and "
                            "querying with undirected match patterns."
                        ),
                        suggested_fix=(
                            f"Standardize on one direction for :{rt} between "
                            f"{label_a} and {label_b}, or use distinct relationship "
                            f"types for each direction."
                        ),
                        entity_name=rt,
                        entity_type="RELATIONSHIP",
                        details={
                            "source_labels": list(src_a),
                            "target_labels": list(tgt_a),
                        },
                    ))
    return findings


def check_orphan_nodes(schema: GraphSchema) -> List[AdvisorFinding]:
    findings: List[AdvisorFinding] = []

    labels_in_patterns: Set[str] = set()
    for pat in schema.patterns:
        labels_in_patterns.update(pat.source_labels)
        labels_in_patterns.update(pat.target_labels)

    for label in schema.labels:
        if label.name not in labels_in_patterns:
            count = label.estimated_count
            if count is not None and count > 0:
                findings.append(AdvisorFinding(
                    rule_id=RuleId.ORPHAN_NODES,
                    severity=Severity.LOW,
                    title=f"Orphan label: {label.name}",
                    description=(
                        f"Label '{label.name}' has ~{count:,} nodes but no "
                        f"relationships in any sampled pattern."
                    ),
                    why=(
                        "Disconnected nodes in a graph database can indicate "
                        "incomplete data loads, leftover test data, or a "
                        "modeling issue where the data would be better stored "
                        "in a relational database."
                    ),
                    suggested_fix=(
                        f"Verify whether '{label.name}' nodes should be connected "
                        f"to other nodes. If they are standalone reference data, "
                        f"consider whether they belong in the graph or in a "
                        f"separate store."
                    ),
                    entity_name=label.name,
                    entity_type="NODE",
                    details={"estimated_count": count},
                ))
    return findings


def check_high_degree_node(schema: GraphSchema) -> List[AdvisorFinding]:
    findings: List[AdvisorFinding] = []

    label_pattern_counts: Dict[str, int] = {}
    label_total_edges: Dict[str, int] = {}
    for pat in schema.patterns:
        for lbl in pat.source_labels:
            label_pattern_counts[lbl] = label_pattern_counts.get(lbl, 0) + 1
            if pat.estimated_count:
                label_total_edges[lbl] = (
                    label_total_edges.get(lbl, 0) + pat.estimated_count
                )
        for lbl in pat.target_labels:
            label_pattern_counts[lbl] = label_pattern_counts.get(lbl, 0) + 1
            if pat.estimated_count:
                label_total_edges[lbl] = (
                    label_total_edges.get(lbl, 0) + pat.estimated_count
                )

    for label in schema.labels:
        pattern_count = label_pattern_counts.get(label.name, 0)
        total_edges = label_total_edges.get(label.name, 0)
        node_count = label.estimated_count or 0

        if (
            pattern_count >= HIGH_DEGREE_PATTERN_THRESHOLD
            and total_edges >= HIGH_DEGREE_COUNT_THRESHOLD
        ):
            avg_degree = (
                round(total_edges / node_count) if node_count > 0 else "unknown"
            )
            findings.append(AdvisorFinding(
                rule_id=RuleId.HIGH_DEGREE_NODE,
                severity=Severity.MEDIUM,
                title=f"High-degree hub: {label.name}",
                description=(
                    f"Label '{label.name}' participates in {pattern_count} "
                    f"relationship patterns with ~{total_edges:,} total edges."
                ),
                why=(
                    "Hub nodes with many relationships can cause expensive "
                    "traversals. Queries that touch these nodes without "
                    "relationship-type filters will expand explosively."
                ),
                suggested_fix=(
                    f"When querying '{label.name}', always filter by "
                    f"relationship type and direction. Consider adding "
                    f"relationship-type indexes or introducing intermediate "
                    f"nodes to reduce fan-out."
                ),
                entity_name=label.name,
                entity_type="NODE",
                details={
                    "pattern_count": pattern_count,
                    "total_edges": total_edges,
                    "estimated_node_count": node_count,
                    "avg_degree": avg_degree,
                },
            ))
    return findings


ALL_RULES = [
    check_missing_index_on_lookup,
    check_overloaded_label,
    check_relationship_too_many_props,
    check_inconsistent_direction,
    check_orphan_nodes,
    check_high_degree_node,
]

SEVERITY_ORDER = {
    Severity.HIGH: 0,
    Severity.MEDIUM: 1,
    Severity.LOW: 2,
    Severity.INFO: 3,
}


def run_all_rules(schema: GraphSchema) -> List[AdvisorFinding]:
    """Execute every rule against the schema and return findings sorted by severity."""
    findings: List[AdvisorFinding] = []
    for rule_fn in ALL_RULES:
        findings.extend(rule_fn(schema))
    findings.sort(key=lambda f: SEVERITY_ORDER.get(f.severity, 99))
    return findings


__all__ = [
    "AdvisorFinding",
    "RuleId",
    "Severity",
    "run_all_rules",
    "check_missing_index_on_lookup",
    "check_overloaded_label",
    "check_relationship_too_many_props",
    "check_inconsistent_direction",
    "check_orphan_nodes",
    "check_high_degree_node",
]
