"""Cypher → plain-English explanation (Phase 25.4).

Given a Cypher query (and optionally the graph schema for domain context),
produces a concise plain-English explanation. Follows the same factory
pattern as :mod:`src.graph.ai.schema_summarizer`.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.llm.prompts.graph_prompts import build_cypher_explanation_prompt

logger = logging.getLogger(__name__)


@dataclass
class CypherExplanationResult:
    """Structured output from the explainer."""

    explanation: str
    cypher: str
    model: Optional[str]
    provider: Optional[str]
    used_fallback: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "explanation": self.explanation,
            "cypher": self.cypher,
            "model": self.model,
            "provider": self.provider,
            "used_fallback": self.used_fallback,
        }


def _fallback_explanation(cypher: str) -> str:
    """Deterministic fallback when the LLM is unavailable."""
    import re

    upper = cypher.upper()
    keywords = [
        "OPTIONAL MATCH", "MATCH", "WHERE", "WITH", "RETURN",
        "ORDER BY", "LIMIT", "SKIP", "UNWIND", "CALL",
    ]
    clauses = []
    for kw in keywords:
        if re.search(rf"\b{kw}\b", upper):
            clauses.append(kw)
    if not clauses:
        return "This Cypher query could not be analyzed without an LLM."
    return (
        f"This query uses the following Cypher clauses: {', '.join(clauses)}. "
        "Connect an LLM provider for a detailed plain-English explanation."
    )


class CypherExplainer:
    """Explain a Cypher query in plain English."""

    def __init__(
        self,
        llm_client: Any,
        *,
        model: Optional[str] = None,
        timeout_seconds: float = 15.0,
        max_output_chars: int = 1500,
    ):
        self.client = llm_client
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_output_chars = max_output_chars

    async def explain(
        self,
        cypher: str,
        schema: Optional[Dict[str, Any]] = None,
        *,
        db: Optional[AsyncSession] = None,
        chat_session_id: Optional[str] = None,
    ) -> CypherExplanationResult:
        """Return a plain-English explanation of the Cypher query."""
        fallback = _fallback_explanation(cypher)

        if self.client is None:
            return CypherExplanationResult(
                explanation=fallback,
                cypher=cypher,
                model=None,
                provider=None,
                used_fallback=True,
            )

        prompt = build_cypher_explanation_prompt(cypher, schema)

        try:
            text = await asyncio.wait_for(
                self.client.generate(
                    prompt=prompt,
                    model=self.model,
                    temperature=0.2,
                    db=db,
                    agent_type="cypher_explainer",
                    agent_name="CypherExplainer",
                    chat_session_id=chat_session_id,
                ),
                timeout=self.timeout_seconds,
            )
        except asyncio.TimeoutError:
            logger.info("Cypher explanation timed out after %ss", self.timeout_seconds)
            return CypherExplanationResult(
                explanation=fallback,
                cypher=cypher,
                model=self.model,
                provider=getattr(self.client, "provider_name", None),
                used_fallback=True,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Cypher explanation failed: %s", exc)
            return CypherExplanationResult(
                explanation=fallback,
                cypher=cypher,
                model=self.model,
                provider=getattr(self.client, "provider_name", None),
                used_fallback=True,
            )

        text = (text or "").strip()
        if not text:
            return CypherExplanationResult(
                explanation=fallback,
                cypher=cypher,
                model=self.model,
                provider=getattr(self.client, "provider_name", None),
                used_fallback=True,
            )

        if len(text) > self.max_output_chars:
            text = text[: self.max_output_chars].rstrip() + "…"

        return CypherExplanationResult(
            explanation=text,
            cypher=cypher,
            model=self.model,
            provider=getattr(self.client, "provider_name", None),
        )


# ── Factory ──────────────────────────────────────────────────────────────


async def get_cypher_explainer(
    db_session: Optional[AsyncSession] = None,
) -> CypherExplainer:
    """Build an explainer wired to the configured ModelRouter + LLM client."""
    from src.llm import get_llm_client

    model: Optional[str] = None
    timeout = 15.0
    provider_name: Optional[str] = None

    if db_session is not None:
        try:
            from src.llm.model_router import TaskType, get_model_router

            router = await get_model_router(db_session)
            model = router.get_model_for_task(TaskType.CYPHER_EXPLANATION)
            timeout = float(router.get_timeout_for_task(TaskType.CYPHER_EXPLANATION))
            provider_name = router.get_provider_for_task(TaskType.CYPHER_EXPLANATION)
        except Exception as exc:  # noqa: BLE001
            logger.debug("ModelRouter lookup for cypher explanation failed: %s", exc)

    client = get_llm_client(provider_name)
    return CypherExplainer(
        llm_client=client,
        model=model,
        timeout_seconds=timeout,
    )


__all__ = [
    "CypherExplanationResult",
    "CypherExplainer",
    "get_cypher_explainer",
]
