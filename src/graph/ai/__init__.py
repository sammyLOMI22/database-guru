"""AI-assisted graph features (Phase 25.2+).

25.2 ships the schema summarizer. 25.4 adds Cypher generation /
explanation. 25.6 adds modeling-advice prose.
"""

from src.graph.ai.schema_summarizer import (  # noqa: F401
    GraphSchemaSummarizer,
    get_graph_schema_summarizer,
)

__all__ = ["GraphSchemaSummarizer", "get_graph_schema_summarizer"]
