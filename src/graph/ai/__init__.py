"""AI-assisted graph features (Phase 25.2+).

25.2 ships the schema summarizer. 25.4 adds Cypher generation /
explanation. 25.6 adds modeling-advice prose.

This module intentionally does **not** re-export the summarizer at package
level. ``src.graph.ai.schema_summarizer`` transitively imports the LLM
client + ModelRouter stack, which is expensive at import time and pulls in
the global usage tracker. Endpoint code (and tests) import the symbols
directly from the submodule so unrelated callers — e.g. test collection
for ``tests/graph/test_schema_normalizer.py`` — don't pay for the LLM
import graph just by touching ``src.graph.ai``.

If you find yourself wanting a shortcut import here, prefer fixing the
submodule's import cost instead.
"""
