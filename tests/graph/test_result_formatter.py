"""Unit tests for the Cypher result formatter (Phase 25.3).

We don't import from ``neo4j.graph`` here — the formatter is duck-typed
and the tests use small stand-in classes so the suite runs without the
driver.
"""

from __future__ import annotations

from src.graph.result_formatter import format_records


# ── Stub neo4j types ─────────────────────────────────────────────────────


class _StubNode:
    def __init__(self, eid: str, labels, props):
        self.element_id = eid
        self.labels = labels
        self._props = props

    def __iter__(self):
        return iter(self._props)

    def keys(self):
        return self._props.keys()

    def items(self):
        return self._props.items()

    def __getitem__(self, key):
        return self._props[key]


class _StubRel:
    def __init__(self, eid: str, rtype: str, start, end, props=None):
        self.element_id = eid
        self.type = rtype
        self.start_node = start
        self.end_node = end
        self._props = props or {}

    def keys(self):
        return self._props.keys()

    def items(self):
        return self._props.items()

    def __getitem__(self, key):
        return self._props[key]


class _StubPath:
    def __init__(self, nodes, relationships):
        self.nodes = nodes
        self.relationships = relationships


# ── Scalar-only results ──────────────────────────────────────────────────


def test_scalar_only_no_graph():
    records = [{"c": 42}]
    result = format_records(records)
    assert result.table_columns == ["c"]
    assert result.table_rows == [[42]]
    assert result.has_graph is False
    assert result.nodes == []
    assert result.edges == []


def test_empty_records():
    result = format_records([])
    assert result.table_columns == []
    assert result.table_rows == []
    assert result.has_graph is False


def test_multiple_scalar_columns():
    records = [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]
    result = format_records(records)
    assert result.table_columns == ["name", "age"]
    assert result.table_rows == [["Alice", 30], ["Bob", 25]]


# ── Node-only results ────────────────────────────────────────────────────


def test_single_node_populates_graph_viz():
    alice = _StubNode("n1", ["User"], {"name": "Alice"})
    result = format_records([{"u": alice}])
    assert result.has_graph is True
    assert len(result.nodes) == 1
    node = result.nodes[0]
    assert node.id == "n1"
    assert node.labels == ["User"]
    assert node.properties == {"name": "Alice"}
    assert node.display_name == "Alice"
    # Table cell renders the node as a dict with _kind sentinel.
    assert result.table_rows[0][0]["_kind"] == "node"
    assert result.table_rows[0][0]["labels"] == ["User"]


def test_duplicate_nodes_dedup():
    alice = _StubNode("n1", ["User"], {"name": "Alice"})
    records = [{"u": alice}, {"u": alice}, {"u": alice}]
    result = format_records(records)
    assert len(result.nodes) == 1
    assert len(result.table_rows) == 3


def test_display_name_falls_back_to_first_short_string():
    n = _StubNode("n2", ["X"], {"description": "Hello world"})
    result = format_records([{"u": n}])
    assert result.nodes[0].display_name == "Hello world"


def test_display_name_falls_back_to_label_when_no_string_props():
    n = _StubNode("n3", ["Order"], {"qty": 5})
    result = format_records([{"u": n}])
    # Label#shortid form.
    name = result.nodes[0].display_name
    assert name.startswith("Order#") or name == "n3"


# ── Relationship + Path results ──────────────────────────────────────────


def test_relationship_pulls_in_endpoints():
    alice = _StubNode("a", ["User"], {"name": "Alice"})
    order = _StubNode("o", ["Order"], {"id": "ord-1"})
    rel = _StubRel("r1", "PURCHASED", alice, order, {"qty": 2})
    result = format_records([{"r": rel}])
    assert len(result.nodes) == 2
    assert len(result.edges) == 1
    edge = result.edges[0]
    assert edge.source == "a"
    assert edge.target == "o"
    assert edge.type == "PURCHASED"
    assert edge.properties == {"qty": 2}


def test_path_collects_all_nodes_and_rels():
    a = _StubNode("a", ["User"], {"name": "A"})
    b = _StubNode("b", ["User"], {"name": "B"})
    c = _StubNode("c", ["User"], {"name": "C"})
    r1 = _StubRel("r1", "KNOWS", a, b)
    r2 = _StubRel("r2", "KNOWS", b, c)
    path = _StubPath([a, b, c], [r1, r2])
    result = format_records([{"p": path}])
    assert len(result.nodes) == 3
    assert len(result.edges) == 2


# ── Truncation caps ──────────────────────────────────────────────────────


def test_node_cap_truncates_and_warns():
    nodes = [_StubNode(f"n{i}", ["X"], {"i": i}) for i in range(10)]
    records = [{"u": n} for n in nodes]
    result = format_records(records, max_nodes=5, max_edges=10)
    assert len(result.nodes) == 5
    assert result.truncated is True
    assert any("truncated" in w.lower() for w in result.warnings)


def test_edge_cap_truncates():
    nodes = [_StubNode(f"n{i}", ["X"], {"i": i}) for i in range(6)]
    rels = [_StubRel(f"r{i}", "T", nodes[0], nodes[i]) for i in range(1, 6)]
    records = [{"r": r} for r in rels]
    result = format_records(records, max_nodes=10, max_edges=2)
    assert len(result.edges) == 2
    assert result.truncated is True


def test_truncated_records_warning_passed_through():
    result = format_records([{"c": 1}], truncated_records=True)
    assert result.truncated is True
    assert any("GRAPH_MAX_RECORDS" in w for w in result.warnings)


# ── Nested structures ────────────────────────────────────────────────────


def test_list_of_nodes_collects_them_all():
    a = _StubNode("a", ["X"], {})
    b = _StubNode("b", ["X"], {})
    result = format_records([{"all": [a, b]}])
    assert len(result.nodes) == 2


def test_dict_value_recursed():
    a = _StubNode("a", ["X"], {})
    result = format_records([{"wrapper": {"inner": a}}])
    assert len(result.nodes) == 1


# ── Payload shape ────────────────────────────────────────────────────────


def test_to_payload_shape():
    alice = _StubNode("a", ["User"], {"name": "Alice"})
    result = format_records([{"u": alice}])
    payload = result.to_payload()
    assert "table" in payload
    assert "graph_viz" in payload
    assert payload["graph_viz"]["has_graph"] is True
    assert payload["table"]["columns"] == ["u"]
    assert payload["truncated"] is False
