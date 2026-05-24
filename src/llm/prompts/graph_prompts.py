"""LLM prompt templates for Graph Mode (Phase 25).

Only the templates required by Phase 25.2 ship here. Cypher generation /
explanation / modeling-advice templates land in 25.4 / 25.6 alongside their
agents.
"""

from __future__ import annotations

from textwrap import dedent
from typing import Any, Dict, List, Optional


def build_graph_schema_summary_prompt(
    schema: Dict[str, Any],
    *,
    max_labels: int = 25,
    max_relationships: int = 25,
    max_patterns: int = 10,
) -> str:
    """Compact summary prompt for the GraphOverview AI card.

    Designed for the small-model tier (≤ 800 tokens of context) so local
    Ollama instances can render the card without provider escalation.
    Returns a single prompt string — the agent layer wraps it with the
    appropriate system message per provider.
    """
    name = schema.get("database_name") or "graph"
    labels: List[Dict[str, Any]] = list(schema.get("labels") or [])[:max_labels]
    rels: List[Dict[str, Any]] = list(schema.get("relationships") or [])[:max_relationships]
    patterns: List[Dict[str, Any]] = list(schema.get("patterns") or [])[:max_patterns]

    label_lines: List[str] = []
    for lbl in labels:
        count = lbl.get("estimated_count")
        suffix = f" (~{count:,} nodes)" if isinstance(count, int) else ""
        label_lines.append(f"- {lbl.get('name')}{suffix}")
    if len(schema.get("labels") or []) > max_labels:
        label_lines.append(f"- ... and {len(schema['labels']) - max_labels} more labels")

    rel_lines: List[str] = []
    for rel in rels:
        rel_lines.append(f"- {rel.get('name')}")
    if len(schema.get("relationships") or []) > max_relationships:
        rel_lines.append(
            f"- ... and {len(schema['relationships']) - max_relationships} more relationship types"
        )

    pattern_lines: List[str] = []
    for pat in patterns:
        sa = ",".join(pat.get("source_labels") or []) or "?"
        tb = ",".join(pat.get("target_labels") or []) or "?"
        cnt = pat.get("estimated_count")
        suffix = f" (count {cnt:,})" if isinstance(cnt, int) else ""
        pattern_lines.append(f"- (:{sa})-[:{pat.get('relationship_type')}]->(:{tb}){suffix}")

    indexes = schema.get("indexes") or []
    constraints = schema.get("constraints") or []

    return dedent(
        f"""
        You are a senior graph-database engineer describing a Neo4j database to
        a teammate who has never seen it before. Write 2-3 short sentences (no
        more than 70 words total) that capture:

        1. What the graph appears to model — infer the domain from the labels
           and relationship types (e.g. "social graph of users and posts",
           "supply-chain network", "code-dependency graph").
        2. The scale and shape — total node labels, relationship types, and
           anything notable like a hub label or sparse area.
        3. One concrete observation a user could act on (e.g. "no indexes on
           User.email — lookups will scan", "graph is mostly trees, not cycles").

        Plain prose only. No bullet lists, no markdown headings, no preamble
        like "Here is a summary". Do not invent labels or relationships that
        aren't listed below.

        Database name: {name}
        Node labels ({len(schema.get('labels') or [])}):
        {chr(10).join(label_lines) or '- (none)'}

        Relationship types ({len(schema.get('relationships') or [])}):
        {chr(10).join(rel_lines) or '- (none)'}

        Top relationship patterns ({len(schema.get('patterns') or [])}):
        {chr(10).join(pattern_lines) or '- (none)'}

        Indexes: {len(indexes)} total
        Constraints: {len(constraints)} total
        """
    ).strip()


def fallback_schema_summary(schema: Dict[str, Any]) -> str:
    """Deterministic fallback when the LLM is unavailable or fails.

    Used by :class:`GraphSchemaSummarizer` when the provider call raises or
    times out — guarantees the Overview card always renders something useful.
    """
    name = schema.get("database_name") or "graph"
    label_count = len(schema.get("labels") or [])
    rel_count = len(schema.get("relationships") or [])
    pattern_count = len(schema.get("patterns") or [])
    index_count = len(schema.get("indexes") or [])

    parts = [
        f"Neo4j database {name!r} has {label_count} node label"
        f"{'s' if label_count != 1 else ''} and {rel_count} relationship type"
        f"{'s' if rel_count != 1 else ''}."
    ]
    if pattern_count:
        parts.append(
            f"Introspection sampled {pattern_count} relationship pattern"
            f"{'s' if pattern_count != 1 else ''}."
        )
    if index_count == 0 and label_count > 0:
        parts.append(
            "No indexes are defined — consider adding indexes on lookup properties "
            "before running production queries."
        )
    return " ".join(parts)


def build_cypher_generation_prompt(
    question: str,
    schema: Dict[str, Any],
    *,
    max_labels: int = 30,
    max_relationships: int = 30,
    max_patterns: int = 15,
    default_limit: int = 25,
) -> str:
    """Build a prompt that converts a natural-language question to Cypher.

    The prompt embeds a compact schema context so the LLM can reference real
    labels, relationship types, and properties. A ``LIMIT`` hint is baked in
    to prevent unbounded result sets from models that forget.
    """
    labels: List[Dict[str, Any]] = list(schema.get("labels") or [])[:max_labels]
    rels: List[Dict[str, Any]] = list(schema.get("relationships") or [])[:max_relationships]
    patterns: List[Dict[str, Any]] = list(schema.get("patterns") or [])[:max_patterns]
    indexes: List[Dict[str, Any]] = list(schema.get("indexes") or [])

    label_lines: List[str] = []
    for lbl in labels:
        props = lbl.get("properties") or []
        prop_names = ", ".join(p.get("name", "?") for p in props[:12])
        count = lbl.get("estimated_count")
        suffix = f" (~{count:,})" if isinstance(count, int) else ""
        label_lines.append(f"  :{lbl.get('name')}{suffix}  {{ {prop_names} }}")

    rel_lines: List[str] = []
    for rel in rels:
        props = rel.get("properties") or []
        prop_names = ", ".join(p.get("name", "?") for p in props[:8])
        bracket = f" {{ {prop_names} }}" if prop_names else ""
        rel_lines.append(f"  [:{rel.get('name')}{bracket}]")

    pattern_lines: List[str] = []
    for pat in patterns:
        sa = ",".join(pat.get("source_labels") or []) or "?"
        tb = ",".join(pat.get("target_labels") or []) or "?"
        pattern_lines.append(
            f"  (:{sa})-[:{pat.get('relationship_type')}]->(:{tb})"
        )

    index_lines: List[str] = []
    for idx in indexes[:10]:
        lts = ", ".join(idx.get("labels_or_types") or [])
        ps = ", ".join(idx.get("properties") or [])
        index_lines.append(f"  {idx.get('name', '?')} ON :{lts}({ps})")

    return dedent(
        f"""
        You are a Cypher query expert. Convert the user's natural-language
        question into a single, valid Cypher READ query for a Neo4j database.

        Rules:
        1. Return ONLY the Cypher query — no explanation, no markdown fences.
        2. Use ONLY labels, relationship types, and properties listed below.
        3. ALWAYS include a LIMIT clause (default {default_limit}) to prevent
           unbounded result sets. The user may specify a different limit.
        4. NEVER generate write operations (CREATE, MERGE, DELETE, SET,
           REMOVE, DETACH DELETE, DROP, CALL … YIELD with side effects).
        5. Prefer indexed properties for lookups when an index exists.
        6. Use parameterized values ($param) when the question contains
           specific literal values that should be parameterized.

        === Graph Schema ===

        Node labels ({len(labels)}):
{chr(10).join(label_lines) or '  (none)'}

        Relationship types ({len(rels)}):
{chr(10).join(rel_lines) or '  (none)'}

        Patterns:
{chr(10).join(pattern_lines) or '  (none)'}

        Indexes:
{chr(10).join(index_lines) or '  (none)'}

        === User Question ===
        {question}
        """
    ).strip()


def build_cypher_explanation_prompt(
    cypher: str,
    schema: Optional[Dict[str, Any]] = None,
) -> str:
    """Build a prompt that explains a Cypher query in plain English.

    Optionally includes schema context so the LLM can reference the domain
    model when describing what the query does.
    """
    schema_section = ""
    if schema:
        labels = [lbl.get("name", "?") for lbl in (schema.get("labels") or [])[:20]]
        rels = [rel.get("name", "?") for rel in (schema.get("relationships") or [])[:20]]
        if labels or rels:
            schema_section = dedent(
                f"""
                === Graph Context ===
                Node labels: {", ".join(labels) or "(none)"}
                Relationship types: {", ".join(rels) or "(none)"}
                """
            ).strip() + "\n\n"

    return dedent(
        f"""
        You are a graph database expert explaining Cypher queries to a
        colleague who knows SQL but is new to Neo4j.

        Explain the following Cypher query in plain English. Include:
        1. What the query does in one clear sentence.
        2. Step-by-step breakdown of each clause (MATCH, WHERE, RETURN, etc.).
        3. Performance notes — mention if the query scans all nodes of a
           label (no index), uses variable-length paths, or could be expensive.
        4. If the query uses aggregation or list operations, explain the
           output shape.

        Keep the explanation concise — under 200 words. No markdown headings.
        Use plain prose with numbered steps.

        {schema_section}=== Cypher Query ===
        {cypher}
        """
    ).strip()


__all__ = [
    "build_graph_schema_summary_prompt",
    "fallback_schema_summary",
    "build_cypher_generation_prompt",
    "build_cypher_explanation_prompt",
]
