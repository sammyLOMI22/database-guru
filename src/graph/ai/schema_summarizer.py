"""Graph schema → 2-3 sentence AI overview blurb (Phase 25.2).

Tiny agent layered over :class:`TrackedLLMClient` + :class:`ModelRouter`,
mirroring the pattern of :mod:`src.lineage.lineage_narrator`. Falls back to
a deterministic summary string when the LLM is unavailable so the frontend
Overview card always renders.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.llm.prompts.graph_prompts import (
    build_graph_schema_summary_prompt,
    fallback_schema_summary,
)

logger = logging.getLogger(__name__)


@dataclass
class GraphSchemaSummary:
    """LLM-rendered (or fallback) blurb about a graph schema."""

    summary: str
    model: Optional[str]
    provider: Optional[str]
    used_fallback: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": self.summary,
            "model": self.model,
            "provider": self.provider,
            "used_fallback": self.used_fallback,
        }


class GraphSchemaSummarizer:
    """Generate a short prose overview of a :class:`GraphSchema` dict."""

    def __init__(
        self,
        llm_client: Any,
        *,
        model: Optional[str] = None,
        timeout_seconds: float = 15.0,
        max_output_chars: int = 500,
    ):
        self.client = llm_client
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_output_chars = max_output_chars

    async def summarize(
        self,
        schema: Dict[str, Any],
        *,
        db: Optional[AsyncSession] = None,
        chat_session_id: Optional[str] = None,
    ) -> GraphSchemaSummary:
        """Return a 2-3 sentence summary; falls back deterministically on error."""
        prompt = build_graph_schema_summary_prompt(schema)
        fallback = fallback_schema_summary(schema)

        if self.client is None:
            return GraphSchemaSummary(
                summary=fallback,
                model=None,
                provider=None,
                used_fallback=True,
            )

        try:
            text = await asyncio.wait_for(
                self.client.generate(
                    prompt=prompt,
                    model=self.model,
                    temperature=0.2,
                    db=db,
                    agent_type="graph_schema_summarizer",
                    agent_name="GraphSchemaSummarizer",
                    chat_session_id=chat_session_id,
                ),
                timeout=self.timeout_seconds,
            )
        except asyncio.TimeoutError:
            logger.info("Graph schema summary timed out after %ss", self.timeout_seconds)
            return GraphSchemaSummary(
                summary=fallback,
                model=self.model,
                provider=getattr(self.client, "provider_name", None),
                used_fallback=True,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Graph schema summary failed: %s", exc)
            return GraphSchemaSummary(
                summary=fallback,
                model=self.model,
                provider=getattr(self.client, "provider_name", None),
                used_fallback=True,
            )

        text = (text or "").strip()
        if not text:
            text = fallback
            used_fallback = True
        else:
            used_fallback = False
            if len(text) > self.max_output_chars:
                text = text[: self.max_output_chars].rstrip() + "…"

        return GraphSchemaSummary(
            summary=text,
            model=self.model,
            provider=getattr(self.client, "provider_name", None),
            used_fallback=used_fallback,
        )


# ── Factory ───────────────────────────────────────────────────────────────


async def get_graph_schema_summarizer(
    db_session: Optional[AsyncSession] = None,
) -> GraphSchemaSummarizer:
    """Build a summarizer wired up to the configured ModelRouter + LLM client.

    Mirrors :func:`src.lineage.lineage_narrator.get_lineage_narrator` so the
    callsite shape is familiar to maintainers.
    """
    from src.llm import get_llm_client

    model: Optional[str] = None
    timeout = 15.0
    provider_name: Optional[str] = None

    if db_session is not None:
        try:
            from src.llm.model_router import TaskType, get_model_router

            router = await get_model_router(db_session)
            model = router.get_model_for_task(TaskType.GRAPH_SCHEMA_SUMMARY)
            timeout = float(router.get_timeout_for_task(TaskType.GRAPH_SCHEMA_SUMMARY))
            provider_name = router.get_provider_for_task(TaskType.GRAPH_SCHEMA_SUMMARY)
        except Exception as exc:  # noqa: BLE001
            logger.debug("ModelRouter lookup for graph summary failed: %s", exc)

    client = get_llm_client(provider_name)
    return GraphSchemaSummarizer(
        llm_client=client,
        model=model,
        timeout_seconds=timeout,
    )


__all__ = [
    "GraphSchemaSummarizer",
    "GraphSchemaSummary",
    "get_graph_schema_summarizer",
]
