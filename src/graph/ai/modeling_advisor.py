"""LLM-enhanced graph modeling advisor (Phase 25.6).

Combines rule-based :func:`run_all_rules` findings with an optional LLM
pass that enriches the ``why`` and ``suggested_fix`` prose. Falls back
gracefully to the rule-only findings when the LLM is unavailable.

Mirrors the pattern of :mod:`src.graph.ai.schema_summarizer`.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.graph.schema.advisor_rules import AdvisorFinding, run_all_rules
from src.graph.schema.normalizer import GraphSchema, graph_schema_from_dict

logger = logging.getLogger(__name__)


@dataclass
class ModelingAdviceResult:
    findings: List[AdvisorFinding]
    ai_summary: Optional[str]
    model: Optional[str]
    provider: Optional[str]
    used_fallback: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "findings": [f.to_dict() for f in self.findings],
            "ai_summary": self.ai_summary,
            "model": self.model,
            "provider": self.provider,
            "used_fallback": self.used_fallback,
        }


class GraphModelingAdvisor:
    """Run rule-based checks and optionally enrich with LLM commentary."""

    def __init__(
        self,
        llm_client: Any,
        *,
        model: Optional[str] = None,
        timeout_seconds: float = 20.0,
        max_output_chars: int = 1500,
    ):
        self.client = llm_client
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_output_chars = max_output_chars

    async def advise(
        self,
        schema_dict: Dict[str, Any],
        *,
        db: Optional[AsyncSession] = None,
    ) -> ModelingAdviceResult:
        schema = graph_schema_from_dict(schema_dict)
        findings = run_all_rules(schema)

        if not findings or self.client is None:
            return ModelingAdviceResult(
                findings=findings,
                ai_summary=None,
                model=self.model,
                provider=getattr(self.client, "provider_name", None),
                used_fallback=self.client is None,
            )

        from src.llm.prompts.graph_prompts import build_modeling_advice_prompt

        prompt = build_modeling_advice_prompt(schema_dict, findings)

        try:
            text = await asyncio.wait_for(
                self.client.generate(
                    prompt=prompt,
                    model=self.model,
                    temperature=0.3,
                    db=db,
                    agent_type="graph_modeling_advisor",
                    agent_name="GraphModelingAdvisor",
                ),
                timeout=self.timeout_seconds,
            )
        except asyncio.TimeoutError:
            logger.info(
                "Graph modeling advice LLM timed out after %ss",
                self.timeout_seconds,
            )
            return ModelingAdviceResult(
                findings=findings,
                ai_summary=None,
                model=self.model,
                provider=getattr(self.client, "provider_name", None),
                used_fallback=True,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Graph modeling advice LLM failed: %s", exc)
            return ModelingAdviceResult(
                findings=findings,
                ai_summary=None,
                model=self.model,
                provider=getattr(self.client, "provider_name", None),
                used_fallback=True,
            )

        text = (text or "").strip()
        if not text:
            ai_summary = None
            used_fallback = True
        else:
            if len(text) > self.max_output_chars:
                text = text[: self.max_output_chars].rstrip() + "…"
            ai_summary = text
            used_fallback = False

        return ModelingAdviceResult(
            findings=findings,
            ai_summary=ai_summary,
            model=self.model,
            provider=getattr(self.client, "provider_name", None),
            used_fallback=used_fallback,
        )


async def get_modeling_advisor(
    db_session: Optional[AsyncSession] = None,
) -> GraphModelingAdvisor:
    """Build an advisor wired to the configured ModelRouter + LLM client."""
    from src.llm import get_llm_client

    model: Optional[str] = None
    timeout = 20.0
    provider_name: Optional[str] = None

    if db_session is not None:
        try:
            from src.llm.model_router import TaskType, get_model_router

            router = await get_model_router(db_session)
            model = router.get_model_for_task(TaskType.GRAPH_MODELING_ADVICE)
            timeout = float(
                router.get_timeout_for_task(TaskType.GRAPH_MODELING_ADVICE)
            )
            provider_name = router.get_provider_for_task(
                TaskType.GRAPH_MODELING_ADVICE
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("ModelRouter lookup for modeling advice failed: %s", exc)

    client = get_llm_client(provider_name)
    return GraphModelingAdvisor(
        llm_client=client,
        model=model,
        timeout_seconds=timeout,
    )


__all__ = [
    "GraphModelingAdvisor",
    "ModelingAdviceResult",
    "get_modeling_advisor",
]
