"""Format Neo4j query results into ``table`` + ``graph_viz`` payloads.

Phase 25.3, spec §5.6.

The Bolt driver returns records whose values can be:

* Scalars (str/int/float/bool/None)
* Lists / dicts of the above
* ``neo4j.graph.Node`` instances (identity, labels, properties)
* ``neo4j.graph.Relationship`` instances (identity, type, start/end, properties)
* ``neo4j.graph.Path`` instances (sequence of nodes + relationships)
* ``neo4j.time.Date / DateTime / Duration`` etc.

We walk each record and build two complementary views:

* ``table_columns + table_rows`` — every record becomes one row; node /
  relationship cells are rendered as their primitive ``{labels, props}``
  dict so the UI can show them with the JSON viewer.
* ``graph_viz`` — collect distinct nodes + relationships into Cytoscape-
  flavoured ``{nodes, edges}`` arrays, capped at
  ``GRAPH_MAX_VIZ_NODES`` / ``GRAPH_MAX_VIZ_EDGES``.

If the result is purely scalar (e.g. ``RETURN count(n)``) the
``graph_viz`` field is empty and ``has_graph`` is False so the UI can
collapse the Graph tab.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ── Output dataclasses ────────────────────────────────────────────────────


@dataclass
class GraphVizNode:
    id: str
    labels: List[str]
    properties: Dict[str, Any]
    display_name: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "labels": self.labels,
            "properties": self.properties,
            "displayName": self.display_name,
        }


@dataclass
class GraphVizEdge:
    id: str
    source: str
    target: str
    type: str
    properties: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "type": self.type,
            "properties": self.properties,
        }


@dataclass
class FormattedResult:
    """Combined table + graph view of a Cypher result set."""

    table_columns: List[str]
    table_rows: List[List[Any]]
    nodes: List[GraphVizNode] = field(default_factory=list)
    edges: List[GraphVizEdge] = field(default_factory=list)
    truncated: bool = False
    warnings: List[str] = field(default_factory=list)

    @property
    def has_graph(self) -> bool:
        return bool(self.nodes)

    def to_payload(self) -> Dict[str, Any]:
        return {
            "table": {
                "columns": self.table_columns,
                "rows": self.table_rows,
            },
            "graph_viz": {
                "nodes": [n.to_dict() for n in self.nodes],
                "edges": [e.to_dict() for e in self.edges],
                "has_graph": self.has_graph,
            },
            "truncated": self.truncated,
            "warnings": list(self.warnings),
        }


# ── Identification helpers ────────────────────────────────────────────────

# We don't import from ``neo4j.graph`` so this module is testable without
# spinning up a driver. Duck-typing matches the attributes the driver
# exposes on Node / Relationship / Path.


def _is_node(obj: Any) -> bool:
    return (
        hasattr(obj, "labels")
        and hasattr(obj, "element_id")
        and hasattr(obj, "items")
    )


def _is_relationship(obj: Any) -> bool:
    return (
        hasattr(obj, "type")
        and hasattr(obj, "element_id")
        and hasattr(obj, "start_node")
        and hasattr(obj, "end_node")
    )


def _is_path(obj: Any) -> bool:
    return hasattr(obj, "nodes") and hasattr(obj, "relationships") and not _is_node(obj)


def _node_id(node: Any) -> str:
    eid = getattr(node, "element_id", None)
    if eid is not None:
        return str(eid)
    # Older drivers expose ``id`` (integer); use it as a string for stable keys.
    return f"node-{getattr(node, 'id', id(node))}"


def _rel_id(rel: Any) -> str:
    eid = getattr(rel, "element_id", None)
    if eid is not None:
        return str(eid)
    return f"rel-{getattr(rel, 'id', id(rel))}"


def _node_props(node: Any) -> Dict[str, Any]:
    try:
        return {k: _to_jsonable(v) for k, v in dict(node).items()}
    except Exception:  # noqa: BLE001
        return {}


def _node_display(node: Any) -> str:
    """Pick a human-readable label for a node — ``name`` > ``title`` >
    first short string property > first label + id."""
    props = _node_props(node)
    for candidate in ("name", "title", "label", "id"):
        val = props.get(candidate)
        if isinstance(val, str) and val:
            return val
    # First short string property.
    for k, v in props.items():
        if isinstance(v, str) and 0 < len(v) <= 80:
            return v
    labels = list(getattr(node, "labels", []))
    if labels:
        return f"{labels[0]}#{_node_id(node)[-6:]}"
    return _node_id(node)


def _to_jsonable(value: Any) -> Any:
    """Convert driver-native types into JSON-friendly primitives.

    The neo4j driver returns its own temporal types (``Date``, ``DateTime``,
    ``Duration``) that JSON can't serialise directly. ``str()`` works for
    all of them and the UI just needs to display them.
    """
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, dict):
        return {k: _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_to_jsonable(v) for v in value]
    if _is_node(value):
        return {
            "_kind": "node",
            "id": _node_id(value),
            "labels": list(getattr(value, "labels", [])),
            "properties": _node_props(value),
        }
    if _is_relationship(value):
        return {
            "_kind": "relationship",
            "id": _rel_id(value),
            "type": getattr(value, "type", None),
            "source": _node_id(getattr(value, "start_node", None)) if getattr(value, "start_node", None) else None,
            "target": _node_id(getattr(value, "end_node", None)) if getattr(value, "end_node", None) else None,
            "properties": _node_props(value),
        }
    if _is_path(value):
        return {
            "_kind": "path",
            "nodes": [_to_jsonable(n) for n in getattr(value, "nodes", [])],
            "relationships": [_to_jsonable(r) for r in getattr(value, "relationships", [])],
        }
    # Last resort — let str() handle it (temporal types).
    return str(value)


# ── Walker ────────────────────────────────────────────────────────────────


class _GraphAccumulator:
    """Collect distinct nodes/edges across many records, respecting caps."""

    def __init__(self, *, max_nodes: int, max_edges: int):
        self.max_nodes = max(0, max_nodes)
        self.max_edges = max(0, max_edges)
        self._nodes: Dict[str, GraphVizNode] = {}
        self._edges: Dict[str, GraphVizEdge] = {}
        self.truncated = False

    def add_node(self, node: Any) -> Optional[str]:
        nid = _node_id(node)
        if nid in self._nodes:
            return nid
        if len(self._nodes) >= self.max_nodes:
            self.truncated = True
            return None
        self._nodes[nid] = GraphVizNode(
            id=nid,
            labels=list(getattr(node, "labels", [])),
            properties=_node_props(node),
            display_name=_node_display(node),
        )
        return nid

    def add_relationship(self, rel: Any) -> None:
        rid = _rel_id(rel)
        if rid in self._edges:
            return
        # Pull endpoints. The driver embeds Node objects on Relationship
        # so we can add them lazily — important because some MATCH
        # patterns return only the relationship.
        start = getattr(rel, "start_node", None)
        end = getattr(rel, "end_node", None)
        source_id = self.add_node(start) if start is not None else None
        target_id = self.add_node(end) if end is not None else None
        if not source_id or not target_id:
            # Endpoints didn't fit under the cap — drop the edge but
            # keep ``truncated`` already flipped by add_node.
            return
        if len(self._edges) >= self.max_edges:
            self.truncated = True
            return
        self._edges[rid] = GraphVizEdge(
            id=rid,
            source=source_id,
            target=target_id,
            type=getattr(rel, "type", "") or "",
            properties=_node_props(rel),
        )

    def nodes_list(self) -> List[GraphVizNode]:
        return list(self._nodes.values())

    def edges_list(self) -> List[GraphVizEdge]:
        return list(self._edges.values())


def _walk_value(value: Any, acc: _GraphAccumulator) -> Any:
    """Recursively walk a record cell, registering graph elements with
    the accumulator. Returns the cell's table-serialised form."""
    if _is_node(value):
        acc.add_node(value)
        return _to_jsonable(value)
    if _is_relationship(value):
        acc.add_relationship(value)
        return _to_jsonable(value)
    if _is_path(value):
        for n in getattr(value, "nodes", []):
            acc.add_node(n)
        for r in getattr(value, "relationships", []):
            acc.add_relationship(r)
        return _to_jsonable(value)
    if isinstance(value, dict):
        return {k: _walk_value(v, acc) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_walk_value(v, acc) for v in value]
    return _to_jsonable(value)


# ── Public API ────────────────────────────────────────────────────────────


def format_records(
    records: List[Dict[str, Any]],
    *,
    max_nodes: int = 200,
    max_edges: int = 500,
    truncated_records: bool = False,
) -> FormattedResult:
    """Render ``records`` (list of cypher result dicts) into a
    :class:`FormattedResult`.

    Args:
        records: List of dicts as returned by ``await result.data()`` on
            the neo4j driver.
        max_nodes / max_edges: Cytoscape sanity caps. Mirror the
            ``GRAPH_MAX_VIZ_*`` settings.
        truncated_records: Pass ``True`` when the caller hit its
            ``GRAPH_MAX_RECORDS`` cap so the formatter can carry that
            warning through.
    """
    acc = _GraphAccumulator(max_nodes=max_nodes, max_edges=max_edges)
    warnings: List[str] = []

    if not records:
        return FormattedResult(
            table_columns=[],
            table_rows=[],
            warnings=warnings,
        )

    # Column order: preserve insertion order of the first record's keys
    # (Python dicts preserve order; the driver returns dicts in the
    # ``RETURN`` clause order).
    columns: List[str] = list(records[0].keys())
    rows: List[List[Any]] = []
    for record in records:
        row: List[Any] = []
        for col in columns:
            row.append(_walk_value(record.get(col), acc))
        rows.append(row)

    if acc.truncated:
        warnings.append(
            f"Visualization truncated — only the first {max_nodes} node(s) "
            f"and {max_edges} edge(s) are shown."
        )
    if truncated_records:
        warnings.append(
            "Result truncated — some Neo4j records were not returned because "
            "GRAPH_MAX_RECORDS was reached."
        )

    return FormattedResult(
        table_columns=columns,
        table_rows=rows,
        nodes=acc.nodes_list(),
        edges=acc.edges_list(),
        truncated=acc.truncated or truncated_records,
        warnings=warnings,
    )


__all__ = [
    "FormattedResult",
    "GraphVizEdge",
    "GraphVizNode",
    "format_records",
]
