"""Graph schema dataclasses + normalization helpers (Phase 25.2).

Maps raw Neo4j introspection rows (``CALL db.labels()``,
``db.schema.nodeTypeProperties``, ``SHOW INDEXES``, etc.) into a
provider-agnostic :class:`GraphSchema` shape that mirrors the TypeScript
interface defined in the spec §5.3.

Design notes:

* Dataclasses are intentionally JSON-serializable via :meth:`to_dict`.
  The dict shape is what we persist to ``DatabaseConnection.schema_cache``
  and what we serve back to the frontend (camelCase aliases applied at the
  Pydantic layer).
* ``graph_schema_from_dict`` is the inverse — used when re-hydrating a
  cached schema from the DB, and when tests construct fixtures.
* Helpers like :func:`normalize_node_type_properties` accept the *raw shape
  returned by the Neo4j driver* (post-``record.data()``) so the schema
  inspector stays as a thin orchestration layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Literal, Optional

EntityType = Literal["NODE", "RELATIONSHIP"]


# ── Property / label / relationship dataclasses ───────────────────────────


@dataclass
class GraphProperty:
    """A single property observed on a node label or relationship type."""

    name: str
    types: List[str] = field(default_factory=list)
    indexed: bool = False
    nullable: Optional[bool] = None
    sample_values: Optional[List[Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "types": list(self.types),
            "indexed": self.indexed,
            "nullable": self.nullable,
            "sample_values": list(self.sample_values) if self.sample_values is not None else None,
        }


@dataclass
class GraphNodeLabel:
    """A node label (e.g. ``Person``)."""

    name: str
    estimated_count: Optional[int] = None
    properties: List[GraphProperty] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "estimated_count": self.estimated_count,
            "properties": [p.to_dict() for p in self.properties],
        }


@dataclass
class GraphRelationshipType:
    """A relationship type (e.g. ``KNOWS``)."""

    name: str
    estimated_count: Optional[int] = None
    properties: List[GraphProperty] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "estimated_count": self.estimated_count,
            "properties": [p.to_dict() for p in self.properties],
        }


@dataclass
class GraphRelationshipPattern:
    """Sampled ``(:A)-[:R]->(:B)`` pattern with observed count."""

    source_labels: List[str]
    relationship_type: str
    target_labels: List[str]
    estimated_count: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_labels": list(self.source_labels),
            "relationship_type": self.relationship_type,
            "target_labels": list(self.target_labels),
            "estimated_count": self.estimated_count,
        }


@dataclass
class GraphIndex:
    """A Neo4j index (BTREE / RANGE / TEXT / POINT / FULLTEXT / LOOKUP)."""

    name: str
    entity_type: EntityType
    labels_or_types: List[str]
    properties: List[str]
    type: Optional[str] = None
    state: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "entity_type": self.entity_type,
            "labels_or_types": list(self.labels_or_types),
            "properties": list(self.properties),
            "type": self.type,
            "state": self.state,
        }


@dataclass
class GraphConstraint:
    """A Neo4j constraint (UNIQUENESS / NODE_KEY / EXISTENCE)."""

    name: str
    entity_type: EntityType
    labels_or_types: List[str]
    properties: List[str]
    type: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "entity_type": self.entity_type,
            "labels_or_types": list(self.labels_or_types),
            "properties": list(self.properties),
            "type": self.type,
        }


@dataclass
class GraphSchema:
    """Provider-agnostic graph schema (spec §5.3)."""

    provider: str
    database_name: str
    labels: List[GraphNodeLabel] = field(default_factory=list)
    relationships: List[GraphRelationshipType] = field(default_factory=list)
    patterns: List[GraphRelationshipPattern] = field(default_factory=list)
    indexes: List[GraphIndex] = field(default_factory=list)
    constraints: List[GraphConstraint] = field(default_factory=list)
    collected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    warnings: List[str] = field(default_factory=list)
    server_version: Optional[str] = None
    edition: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "database_name": self.database_name,
            "labels": [lbl.to_dict() for lbl in self.labels],
            "relationships": [r.to_dict() for r in self.relationships],
            "patterns": [p.to_dict() for p in self.patterns],
            "indexes": [i.to_dict() for i in self.indexes],
            "constraints": [c.to_dict() for c in self.constraints],
            "collected_at": self.collected_at.isoformat(),
            "warnings": list(self.warnings),
            "server_version": self.server_version,
            "edition": self.edition,
            "label_count": len(self.labels),
            "relationship_type_count": len(self.relationships),
            "pattern_count": len(self.patterns),
            "index_count": len(self.indexes),
            "constraint_count": len(self.constraints),
        }

    def to_response_payload(
        self,
        *,
        connection_id: int,
        schema_updated_at: Optional[str],
        cached: bool,
    ) -> Dict[str, Any]:
        """Shape this schema for the GraphSchemaResponse wire model.

        Lives on the dataclass (not on the endpoint module) so adding a
        schema field only requires touching one file. Callers pass the
        connection-scoped bits (``connection_id`` and
        ``schema_updated_at``) that the dataclass itself doesn't know
        about.
        """
        return {
            "connection_id": connection_id,
            "schema_updated_at": schema_updated_at,
            "cached": cached,
            **self.to_dict(),
        }


# ── Inverse: re-hydrate from cache dict ───────────────────────────────────


def _parse_collected_at(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str) and value:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return datetime.now(timezone.utc)


def graph_schema_from_dict(data: Dict[str, Any]) -> GraphSchema:
    """Re-hydrate a :class:`GraphSchema` from its serialized form.

    Tolerant of missing keys so cached payloads from older shipping versions
    don't blow up on read.
    """

    def _prop(d: Dict[str, Any]) -> GraphProperty:
        return GraphProperty(
            name=d["name"],
            types=list(d.get("types") or []),
            indexed=bool(d.get("indexed", False)),
            nullable=d.get("nullable"),
            sample_values=d.get("sample_values"),
        )

    labels = [
        GraphNodeLabel(
            name=row["name"],
            estimated_count=row.get("estimated_count"),
            properties=[_prop(p) for p in (row.get("properties") or [])],
        )
        for row in data.get("labels") or []
    ]
    rels = [
        GraphRelationshipType(
            name=row["name"],
            estimated_count=row.get("estimated_count"),
            properties=[_prop(p) for p in (row.get("properties") or [])],
        )
        for row in data.get("relationships") or []
    ]
    patterns = [
        GraphRelationshipPattern(
            source_labels=list(row.get("source_labels") or []),
            relationship_type=row["relationship_type"],
            target_labels=list(row.get("target_labels") or []),
            estimated_count=row.get("estimated_count"),
        )
        for row in data.get("patterns") or []
    ]
    indexes = [
        GraphIndex(
            name=row["name"],
            entity_type=row.get("entity_type") or "NODE",
            labels_or_types=list(row.get("labels_or_types") or []),
            properties=list(row.get("properties") or []),
            type=row.get("type"),
            state=row.get("state"),
        )
        for row in data.get("indexes") or []
    ]
    constraints = [
        GraphConstraint(
            name=row["name"],
            entity_type=row.get("entity_type") or "NODE",
            labels_or_types=list(row.get("labels_or_types") or []),
            properties=list(row.get("properties") or []),
            type=row.get("type") or "UNKNOWN",
        )
        for row in data.get("constraints") or []
    ]

    return GraphSchema(
        provider=data.get("provider", "neo4j"),
        database_name=data.get("database_name", "neo4j"),
        labels=labels,
        relationships=rels,
        patterns=patterns,
        indexes=indexes,
        constraints=constraints,
        collected_at=_parse_collected_at(data.get("collected_at")),
        warnings=list(data.get("warnings") or []),
        server_version=data.get("server_version"),
        edition=data.get("edition"),
    )


# ── Normalization from raw Neo4j rows ─────────────────────────────────────


def _parse_node_type_label(node_type: str) -> List[str]:
    """``CALL db.schema.nodeTypeProperties`` returns ``nodeType`` as
    ``":`Label1`:`Label2`"`` (Neo4j 5.x). Extract the label names.

    Falls back to a naive split when the input doesn't look like the
    documented shape — protects against driver-version drift.
    """
    if not node_type:
        return []
    parts = []
    for raw in node_type.split(":"):
        cleaned = raw.strip().strip("`").strip()
        if cleaned:
            parts.append(cleaned)
    return parts


def normalize_node_type_properties(
    rows: Iterable[Dict[str, Any]],
    indexed_property_lookup: Optional[Dict[str, set]] = None,
) -> Dict[str, List[GraphProperty]]:
    """Convert ``db.schema.nodeTypeProperties`` rows into label → properties.

    Args:
        rows: Iterable of dicts with ``nodeType`` / ``propertyName`` /
            ``propertyTypes`` / ``mandatory`` keys.
        indexed_property_lookup: Optional ``{label_name → set(property_name)}``
            used to mark indexed properties. When None, ``indexed`` is False
            for every property.

    Returns:
        ``{label_name: [GraphProperty, ...]}``. Properties are deduped per
        label by name; types from multiple rows are merged.
    """
    indexed_property_lookup = indexed_property_lookup or {}
    result: Dict[str, Dict[str, GraphProperty]] = {}

    for row in rows:
        labels = _parse_node_type_label(row.get("nodeType") or "")
        prop_name = row.get("propertyName")
        if not labels or not prop_name:
            continue

        types = row.get("propertyTypes") or []
        if isinstance(types, str):
            types = [types]
        mandatory = row.get("mandatory")
        nullable = (not mandatory) if isinstance(mandatory, bool) else None

        for label in labels:
            bucket = result.setdefault(label, {})
            existing = bucket.get(prop_name)
            indexed = prop_name in indexed_property_lookup.get(label, set())
            if existing is None:
                bucket[prop_name] = GraphProperty(
                    name=prop_name,
                    types=sorted(set(types)),
                    indexed=indexed,
                    nullable=nullable,
                )
            else:
                # Merge types — same property observed in multiple node types.
                merged = sorted(set(existing.types) | set(types))
                existing.types = merged
                existing.indexed = existing.indexed or indexed
                # Nullable becomes True if ever observed nullable.
                if nullable is True:
                    existing.nullable = True
                elif existing.nullable is None and nullable is False:
                    existing.nullable = False

    return {label: list(props.values()) for label, props in result.items()}


def normalize_rel_type_properties(
    rows: Iterable[Dict[str, Any]],
    indexed_property_lookup: Optional[Dict[str, set]] = None,
) -> Dict[str, List[GraphProperty]]:
    """Convert ``db.schema.relTypeProperties`` rows into rel_type → properties.

    ``relType`` arrives as ``":\\`KNOWS\\`"`` in Neo4j 5.x — strip the colon
    and backticks. Same merge semantics as :func:`normalize_node_type_properties`.
    """
    indexed_property_lookup = indexed_property_lookup or {}
    result: Dict[str, Dict[str, GraphProperty]] = {}

    for row in rows:
        raw = row.get("relType") or ""
        rel_type = raw.strip(":").strip("`").strip()
        prop_name = row.get("propertyName")
        if not rel_type or not prop_name:
            continue

        types = row.get("propertyTypes") or []
        if isinstance(types, str):
            types = [types]
        mandatory = row.get("mandatory")
        nullable = (not mandatory) if isinstance(mandatory, bool) else None

        bucket = result.setdefault(rel_type, {})
        existing = bucket.get(prop_name)
        indexed = prop_name in indexed_property_lookup.get(rel_type, set())
        if existing is None:
            bucket[prop_name] = GraphProperty(
                name=prop_name,
                types=sorted(set(types)),
                indexed=indexed,
                nullable=nullable,
            )
        else:
            existing.types = sorted(set(existing.types) | set(types))
            existing.indexed = existing.indexed or indexed
            if nullable is True:
                existing.nullable = True
            elif existing.nullable is None and nullable is False:
                existing.nullable = False

    return {rel: list(props.values()) for rel, props in result.items()}


def normalize_indexes(rows: Iterable[Dict[str, Any]]) -> List[GraphIndex]:
    """Convert ``SHOW INDEXES`` rows into :class:`GraphIndex` instances.

    Filters out ``LOOKUP`` indexes that are auto-created and rarely useful
    in the schema explorer? — No, we keep them (operators want full picture).
    """
    out: List[GraphIndex] = []
    for row in rows:
        name = row.get("name")
        if not name:
            continue
        out.append(
            GraphIndex(
                name=name,
                entity_type=(row.get("entityType") or "NODE").upper(),  # type: ignore[arg-type]
                labels_or_types=list(row.get("labelsOrTypes") or []),
                properties=list(row.get("properties") or []),
                type=row.get("type"),
                state=row.get("state"),
            )
        )
    return out


def normalize_constraints(rows: Iterable[Dict[str, Any]]) -> List[GraphConstraint]:
    """Convert ``SHOW CONSTRAINTS`` rows into :class:`GraphConstraint`."""
    out: List[GraphConstraint] = []
    for row in rows:
        name = row.get("name")
        if not name:
            continue
        out.append(
            GraphConstraint(
                name=name,
                entity_type=(row.get("entityType") or "NODE").upper(),  # type: ignore[arg-type]
                labels_or_types=list(row.get("labelsOrTypes") or []),
                properties=list(row.get("properties") or []),
                type=(row.get("type") or "UNKNOWN").upper(),
            )
        )
    return out


def build_indexed_property_lookup(
    indexes: Iterable[GraphIndex],
    entity_type: EntityType,
) -> Dict[str, set]:
    """Build ``{label_or_type: {prop_name, ...}}`` for fast indexed-flag lookup.

    Combines all indexes whose ``entity_type`` matches; ``LOOKUP`` indexes
    (which match all labels) are skipped to avoid false positives.
    """
    lookup: Dict[str, set] = {}
    for idx in indexes:
        if idx.entity_type != entity_type:
            continue
        if (idx.type or "").upper() == "LOOKUP":
            continue
        for label in idx.labels_or_types:
            lookup.setdefault(label, set()).update(idx.properties)
    return lookup


def normalize_patterns(
    rows: Iterable[Dict[str, Any]],
) -> List[GraphRelationshipPattern]:
    """Convert ``MATCH (a)-[r]->(b)`` sample rows into :class:`GraphRelationshipPattern`.

    Expects each row to expose ``sa`` (list[str] source labels), ``rt`` (rel type),
    ``tb`` (list[str] target labels), and optional ``c`` (count).
    """
    out: List[GraphRelationshipPattern] = []
    for row in rows:
        rt = row.get("rt") or row.get("relationship_type")
        if not rt:
            continue
        out.append(
            GraphRelationshipPattern(
                source_labels=list(row.get("sa") or row.get("source_labels") or []),
                relationship_type=rt,
                target_labels=list(row.get("tb") or row.get("target_labels") or []),
                estimated_count=row.get("c") or row.get("estimated_count"),
            )
        )
    return out


__all__ = [
    "EntityType",
    "GraphConstraint",
    "GraphIndex",
    "GraphNodeLabel",
    "GraphProperty",
    "GraphRelationshipPattern",
    "GraphRelationshipType",
    "GraphSchema",
    "build_indexed_property_lookup",
    "graph_schema_from_dict",
    "normalize_constraints",
    "normalize_indexes",
    "normalize_node_type_properties",
    "normalize_patterns",
    "normalize_rel_type_properties",
]
