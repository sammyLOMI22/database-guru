"""Natural-language → Cypher query generation (Phase 25.4).

Wraps :class:`TrackedLLMClient` with the graph schema context to convert a
user's plain-English question into a valid read-only Cypher query. Follows
the same factory pattern as :mod:`src.graph.ai.schema_summarizer`.

Post-processing:
* Strips markdown fences if the LLM wraps the output.
* Injects ``LIMIT`` when the model forgets.
* Detects labels/types not present in the schema (``unknown_labels``).
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.llm.prompts.graph_prompts import build_cypher_generation_prompt

logger = logging.getLogger(__name__)

_FENCE_RE = re.compile(
    r"^```(?:cypher|cql)?\s*\n?(.*?)\n?\s*```$",
    re.DOTALL | re.IGNORECASE,
)
_LIMIT_RE = re.compile(r"\bLIMIT\s+\d+", re.IGNORECASE)


@dataclass
class CypherGenerationResult:
    """Structured output from the generator."""

    cypher: str
    question: str
    model: Optional[str]
    provider: Optional[str]
    unknown_labels: List[str] = field(default_factory=list)
    used_fallback: bool = False
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cypher": self.cypher,
            "question": self.question,
            "model": self.model,
            "provider": self.provider,
            "unknown_labels": self.unknown_labels,
            "used_fallback": self.used_fallback,
            "error": self.error,
        }


class CypherGenerator:
    """Convert a natural-language question into a Cypher READ query."""

    def __init__(
        self,
        llm_client: Any,
        *,
        model: Optional[str] = None,
        timeout_seconds: float = 25.0,
        default_limit: int = 25,
    ):
        self.client = llm_client
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.default_limit = default_limit

    async def generate(
        self,
        question: str,
        schema: Dict[str, Any],
        *,
        db: Optional[AsyncSession] = None,
        chat_session_id: Optional[str] = None,
    ) -> CypherGenerationResult:
        """Generate a Cypher query from a natural-language question."""
        if self.client is None:
            return CypherGenerationResult(
                cypher="",
                question=question,
                model=None,
                provider=None,
                used_fallback=True,
                error="No LLM client configured",
            )

        prompt = build_cypher_generation_prompt(
            question, schema, default_limit=self.default_limit,
        )

        try:
            text = await asyncio.wait_for(
                self.client.generate(
                    prompt=prompt,
                    model=self.model,
                    temperature=0.1,
                    db=db,
                    agent_type="cypher_generator",
                    agent_name="CypherGenerator",
                    chat_session_id=chat_session_id,
                ),
                timeout=self.timeout_seconds,
            )
        except asyncio.TimeoutError:
            logger.info("Cypher generation timed out after %ss", self.timeout_seconds)
            return CypherGenerationResult(
                cypher="",
                question=question,
                model=self.model,
                provider=getattr(self.client, "provider_name", None),
                used_fallback=True,
                error="Generation timed out",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Cypher generation failed: %s", exc)
            return CypherGenerationResult(
                cypher="",
                question=question,
                model=self.model,
                provider=getattr(self.client, "provider_name", None),
                used_fallback=True,
                error=str(exc),
            )

        cypher = _clean_cypher(text or "")

        if not cypher:
            return CypherGenerationResult(
                cypher="",
                question=question,
                model=self.model,
                provider=getattr(self.client, "provider_name", None),
                used_fallback=True,
                error="LLM returned empty or unparseable output",
            )

        cypher = _inject_limit(cypher, self.default_limit)
        unknown = _detect_unknown_labels(cypher, schema)

        return CypherGenerationResult(
            cypher=cypher,
            question=question,
            model=self.model,
            provider=getattr(self.client, "provider_name", None),
            unknown_labels=unknown,
        )


# ── Post-processing helpers ──────────────────────────────────────────────


def _clean_cypher(raw: str) -> str:
    """Strip markdown fences and leading/trailing whitespace."""
    text = raw.strip()
    m = _FENCE_RE.match(text)
    if m:
        text = m.group(1).strip()
    for prefix in ("cypher\n", "Cypher\n", "CYPHER\n"):
        if text.startswith(prefix):
            text = text[len(prefix):].strip()
    return text


def _inject_limit(cypher: str, default_limit: int) -> str:
    """Append ``LIMIT`` if the query doesn't already have one."""
    if _LIMIT_RE.search(cypher):
        return cypher
    return cypher.rstrip().rstrip(";") + f"\nLIMIT {default_limit}"


def _detect_unknown_labels(cypher: str, schema: Dict[str, Any]) -> List[str]:
    """Find node labels or relationship types in the Cypher that are not in the schema."""
    known_labels = {
        (lbl.get("name") or "").lower()
        for lbl in (schema.get("labels") or [])
    }
    known_rels = {
        (rel.get("name") or "").lower()
        for rel in (schema.get("relationships") or [])
    }
    known = known_labels | known_rels

    label_pattern = re.compile(r"[:]\s*([A-Za-z_]\w*)")
    found = set(label_pattern.findall(cypher))

    unknown = sorted(name for name in found if name.lower() not in known)
    return unknown


# ── Factory ──────────────────────────────────────────────────────────────


async def get_cypher_generator(
    db_session: Optional[AsyncSession] = None,
) -> CypherGenerator:
    """Build a generator wired to the configured ModelRouter + LLM client."""
    from src.llm import get_llm_client

    model: Optional[str] = None
    timeout = 25.0
    provider_name: Optional[str] = None

    if db_session is not None:
        try:
            from src.llm.model_router import TaskType, get_model_router

            router = await get_model_router(db_session)
            model = router.get_model_for_task(TaskType.CYPHER_GENERATION)
            timeout = float(router.get_timeout_for_task(TaskType.CYPHER_GENERATION))
            provider_name = router.get_provider_for_task(TaskType.CYPHER_GENERATION)
        except Exception as exc:  # noqa: BLE001
            logger.debug("ModelRouter lookup for cypher generation failed: %s", exc)

    client = get_llm_client(provider_name)
    return CypherGenerator(
        llm_client=client,
        model=model,
        timeout_seconds=timeout,
    )


__all__ = [
    "CypherGenerationResult",
    "CypherGenerator",
    "get_cypher_generator",
]
