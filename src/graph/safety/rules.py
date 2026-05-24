"""Safety rule tables for the Cypher classifier (Phase 25.3, spec §12).

Kept separate from :mod:`src.graph.safety.classifier` so the rule sets are
easy to audit / extend without touching the algorithm.

Two important design points:

* ``WRITE_KEYWORDS`` matches the *uppercased token stream* after literal
  and comment stripping. Multi-word phrases (``DETACH DELETE``) are
  spelled with a single internal space — the classifier rejoins tokens
  with single spaces before substring-matching so this works.
* ``DANGEROUS_KEYWORDS`` represent constructs that can move data,
  read/write the filesystem, or affect the cluster. These escalate
  past plain ``WRITE`` so the executor can render a stronger blocked
  reason in the UI.
"""

from __future__ import annotations

from typing import FrozenSet

# Plain DML-style writes. Detected via whole-word match on the uppercased
# token stream.
WRITE_KEYWORDS: FrozenSet[str] = frozenset(
    {
        "CREATE",
        "MERGE",
        "DELETE",
        "DETACH DELETE",
        "REMOVE",
        "SET",
    }
)

# Things that are not plain writes — they touch DDL, the filesystem,
# replication, or cluster state. Always classified above WRITE so the
# blocked-reason payload can flag them distinctly.
DANGEROUS_KEYWORDS: FrozenSet[str] = frozenset(
    {
        "DROP",
        "LOAD CSV",
        "USING PERIODIC COMMIT",
        "CREATE INDEX",
        "CREATE CONSTRAINT",
        "DROP INDEX",
        "DROP CONSTRAINT",
        "CREATE DATABASE",
        "DROP DATABASE",
        "ALTER DATABASE",
        "START DATABASE",
        "STOP DATABASE",
    }
)

# Procedure calls that we permit even though they start with ``CALL``.
# Anything outside this set requires an explicit opt-in (e.g.
# ``GRAPH_ALLOW_APOC=True`` for ``apoc.*``). The schema-introspection set
# is read-only by definition.
#
# Note: ``dbms.components`` is intentionally absent — the ``dbms.`` prefix
# in ADMIN_PROCEDURE_PREFIXES catches it first, and we want user-facing
# Cypher to treat all ``dbms.*`` as admin. The introspection pipeline calls
# it internally without going through the classifier.
ALLOWED_READ_PROCEDURES: FrozenSet[str] = frozenset(
    {
        "db.labels",
        "db.relationshiptypes",
        "db.schema.nodetypeproperties",
        "db.schema.reltypeproperties",
        "db.indexes",
        "db.constraints",
        "db.schema.visualization",
    }
)

# Procedures that always require admin/operator privileges. If we see one
# of these, the query is ``ADMIN`` regardless of the rest.
ADMIN_PROCEDURE_PREFIXES: FrozenSet[str] = frozenset(
    {
        "dbms.",
        "db.checkpoint",
        "db.killtransaction",
        "db.killqueries",
    }
)

# APOC sub-namespaces that are known-write. When APOC is permitted we
# still surface these as WRITE/DANGEROUS so the executor can refuse them
# in MVP.
APOC_WRITE_PREFIXES: FrozenSet[str] = frozenset(
    {
        "apoc.create.",
        "apoc.merge.",
        "apoc.refactor.",
        "apoc.periodic.",
        "apoc.cypher.runwrite",
        "apoc.import.",
        "apoc.export.",
        "apoc.load.",
    }
)

__all__ = [
    "ADMIN_PROCEDURE_PREFIXES",
    "ALLOWED_READ_PROCEDURES",
    "APOC_WRITE_PREFIXES",
    "DANGEROUS_KEYWORDS",
    "WRITE_KEYWORDS",
]
