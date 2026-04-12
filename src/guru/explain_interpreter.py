"""
Explain Interpreter - Phase 22.2

LLM-powered execution plan interpreter. Takes a parsed ExecutionPlan
and generates actionable performance insights using Ollama.

Follows the LineageNarrator/ImpactAdvisor agent pattern:
- Wrap LLM calls with asyncio.wait_for() for timeout
- Parse JSON with balanced brace matching (extract_json_object)
- Always have fallback response on timeout/error
- SQLite plans use deterministic-only analysis (no LLM)
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.guru.explain_analyzer import ExecutionPlan
from src.lineage.llm_utils import extract_json_object
from src.guru.prompts.explain_prompts import get_explain_prompt, EXPLAIN_TOKEN_BUDGETS

logger = logging.getLogger(__name__)


# ============================================================================
# Dataclasses
# ============================================================================

@dataclass
class Bottleneck:
    """A performance bottleneck identified in the execution plan."""
    node_type: str
    table_or_index: str
    severity: str  # "low", "medium", "high", "critical"
    description: str
    impact_estimate: str

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class IndexSuggestion:
    """A suggested index to improve query performance."""
    table: str
    columns: List[str]
    reason: str
    create_sql: str
    estimated_speedup: str

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class QueryRewrite:
    """A suggested query rewrite for better performance."""
    original_pattern: str
    rewritten_sql: str
    reason: str
    expected_improvement: str

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class PerformanceInsights:
    """LLM-generated performance analysis results."""
    summary: str
    overall_severity: str = "warning"  # "good", "warning", "critical"
    bottlenecks: List[Bottleneck] = field(default_factory=list)
    index_suggestions: List[IndexSuggestion] = field(default_factory=list)
    query_rewrites: List[QueryRewrite] = field(default_factory=list)
    before_after_estimate: Optional[str] = None
    general_recommendations: List[str] = field(default_factory=list)
    confidence: float = 0.5
    llm_used: bool = False
    generated_at: Optional[str] = None

    def __post_init__(self):
        if self.generated_at is None:
            self.generated_at = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict:
        result = asdict(self)
        result["bottlenecks"] = [
            b.to_dict() if isinstance(b, Bottleneck) else b
            for b in self.bottlenecks
        ]
        result["index_suggestions"] = [
            s.to_dict() if isinstance(s, IndexSuggestion) else s
            for s in self.index_suggestions
        ]
        result["query_rewrites"] = [
            r.to_dict() if isinstance(r, QueryRewrite) else r
            for r in self.query_rewrites
        ]
        return result


# ============================================================================
# Interpreter Agent
# ============================================================================

class ExplainInterpreter:
    """LLM-powered execution plan interpreter."""

    def __init__(
        self,
        ollama_client,
        model_router=None,
        timeout_seconds: float = 25.0,
        model: Optional[str] = None,
    ):
        self.client = ollama_client
        self.router = model_router
        self.timeout_seconds = timeout_seconds
        self.model = model

    async def interpret(
        self,
        plan: ExecutionPlan,
        schema_context: Optional[Dict] = None,
        db=None,
        query_history_id: Optional[int] = None,
        chat_session_id: Optional[str] = None,
        chat_message_id: Optional[int] = None,
    ) -> PerformanceInsights:
        """
        Interpret an execution plan and generate performance insights.

        For SQLite, returns deterministic-only analysis (no LLM call).
        For other dialects, uses LLM with tiered prompts.
        """
        # SQLite short-circuit: plan output is too simple for LLM
        if plan.dialect == "sqlite":
            return self._sqlite_deterministic_insights(plan)

        # Build prompt
        prompt = self._build_prompt(plan, schema_context)

        # Get model
        model_to_use = self._get_model()

        # LLM call with timeout
        try:
            response_text = await asyncio.wait_for(
                self.client.generate(
                    prompt=prompt,
                    temperature=0.2,
                    model=model_to_use,
                    db=db,
                    agent_type="explain_interpreter",
                    query_history_id=query_history_id,
                    chat_session_id=chat_session_id,
                    chat_message_id=chat_message_id,
                ),
                timeout=self.timeout_seconds,
            )
        except asyncio.TimeoutError:
            logger.warning(f"EXPLAIN interpretation timeout after {self.timeout_seconds}s")
            return self._fallback_insights(plan)
        except Exception as e:
            logger.error(f"EXPLAIN interpretation LLM call failed: {e}")
            return self._fallback_insights(plan)

        return self._parse_response(response_text, plan)

    def _build_prompt(self, plan: ExecutionPlan, schema_context: Optional[Dict] = None) -> str:
        """Build the LLM prompt from the execution plan."""
        # Get model size for tiered prompt selection
        model_size = self._get_model_size()
        template = get_explain_prompt(model_size)

        # Format plan nodes as text
        explain_text = "\n".join(plan.raw_plan) if plan.raw_plan else "No plan data available"

        # Format warnings
        warnings_text = "\n".join(f"- {w}" for w in plan.warnings) if plan.warnings else "None"

        # Format schema context
        schema_text = ""
        if schema_context:
            schema_text = "SCHEMA CONTEXT:\n"
            for table, cols in schema_context.items():
                if isinstance(cols, list):
                    schema_text += f"  {table}: {', '.join(str(c) for c in cols)}\n"
                else:
                    schema_text += f"  {table}: {cols}\n"

        return template.format(
            database_type=plan.dialect,
            sql=plan.sql,
            explain_plan=explain_text,
            warnings=warnings_text,
            schema_context=schema_text,
        )

    def _parse_response(self, response_text: str, plan: ExecutionPlan) -> PerformanceInsights:
        """Parse the LLM JSON response into PerformanceInsights."""
        try:
            json_str = extract_json_object(response_text)
            if not json_str:
                logger.warning("No JSON found in EXPLAIN interpretation response")
                return self._fallback_insights(plan)

            data = json.loads(json_str)

            summary = data.get("summary", "")
            if not isinstance(summary, str) or len(summary) < 5:
                return self._fallback_insights(plan)

            # Parse bottlenecks
            bottlenecks = []
            for b in data.get("bottlenecks", []):
                if isinstance(b, dict):
                    bottlenecks.append(Bottleneck(
                        node_type=b.get("node_type", "Unknown"),
                        table_or_index=b.get("table_or_index", "unknown"),
                        severity=b.get("severity", "medium"),
                        description=b.get("description", ""),
                        impact_estimate=b.get("impact_estimate", ""),
                    ))

            # Parse index suggestions
            index_suggestions = []
            for s in data.get("index_suggestions", []):
                if isinstance(s, dict):
                    index_suggestions.append(IndexSuggestion(
                        table=s.get("table", ""),
                        columns=s.get("columns", []),
                        reason=s.get("reason", ""),
                        create_sql=s.get("create_sql", ""),
                        estimated_speedup=s.get("estimated_speedup", ""),
                    ))

            # Parse query rewrites
            query_rewrites = []
            for r in data.get("query_rewrites", []):
                if isinstance(r, dict):
                    query_rewrites.append(QueryRewrite(
                        original_pattern=r.get("original_pattern", ""),
                        rewritten_sql=r.get("rewritten_sql", ""),
                        reason=r.get("reason", ""),
                        expected_improvement=r.get("expected_improvement", ""),
                    ))

            return PerformanceInsights(
                summary=summary,
                overall_severity=data.get("overall_severity", "warning"),
                bottlenecks=bottlenecks,
                index_suggestions=index_suggestions,
                query_rewrites=query_rewrites,
                before_after_estimate=data.get("before_after_estimate"),
                general_recommendations=data.get("general_recommendations", []),
                confidence=float(data.get("confidence", 0.7)),
                llm_used=True,
            )

        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"EXPLAIN interpretation response parse error: {e}")
            return self._fallback_insights(plan)

    def _fallback_insights(self, plan: ExecutionPlan) -> PerformanceInsights:
        """Generate deterministic-only insights when LLM fails."""
        # Build bottlenecks from deterministic warnings
        bottlenecks = []
        for table in plan.seq_scan_tables:
            bottlenecks.append(Bottleneck(
                node_type="Seq Scan",
                table_or_index=table,
                severity="medium",
                description=f"Sequential scan on '{table}'",
                impact_estimate="May be slow on large tables",
            ))

        summary = "Query analysis based on execution plan structure."
        if plan.has_seq_scans:
            summary = f"Query performs sequential scans on: {', '.join(plan.seq_scan_tables)}. Consider adding indexes."
        if plan.has_disk_spill:
            summary += " Disk spill detected — consider increasing work_mem."

        severity = "good"
        if plan.has_seq_scans:
            severity = "warning"
        if plan.has_disk_spill:
            severity = "critical"

        return PerformanceInsights(
            summary=summary,
            overall_severity=severity,
            bottlenecks=bottlenecks,
            general_recommendations=plan.warnings,
            confidence=0.4,
            llm_used=False,
        )

    def _sqlite_deterministic_insights(self, plan: ExecutionPlan) -> PerformanceInsights:
        """SQLite-specific deterministic analysis (no LLM needed)."""
        bottlenecks = []
        for node in plan.all_nodes:
            if node.node_type == "SCAN" and node.relation:
                bottlenecks.append(Bottleneck(
                    node_type="Full Table Scan",
                    table_or_index=node.relation,
                    severity="medium",
                    description=f"Full table scan on '{node.relation}' — no index used",
                    impact_estimate="Reads every row in the table",
                ))
            elif node.node_type == "TEMP B-TREE":
                bottlenecks.append(Bottleneck(
                    node_type="Temp B-Tree Sort",
                    table_or_index="(temporary)",
                    severity="low",
                    description="Temporary B-tree created for sorting",
                    impact_estimate="Extra memory/CPU for sort operation",
                ))

        has_issues = bool(bottlenecks)
        summary = "SQLite execution plan analysis (deterministic)."
        if has_issues:
            tables = [b.table_or_index for b in bottlenecks if b.table_or_index != "(temporary)"]
            if tables:
                summary = f"Full table scans detected on: {', '.join(tables)}. Consider adding indexes."

        return PerformanceInsights(
            summary=summary,
            overall_severity="warning" if has_issues else "good",
            bottlenecks=bottlenecks,
            general_recommendations=plan.warnings,
            confidence=0.6,
            llm_used=False,
        )

    def _get_model(self) -> Optional[str]:
        """Get the model to use for this task."""
        if self.model:
            return self.model
        if self.router:
            from src.llm.model_router import TaskType
            return self.router.get_model_for_task(TaskType.EXPLAIN_ANALYSIS)
        return None

    def _get_model_size(self):
        """Get the model size for prompt tier selection."""
        from src.llm.prompt_optimizer import ModelSize
        if self.router:
            from src.llm.model_router import TaskType
            return self.router.get_model_size(TaskType.EXPLAIN_ANALYSIS)
        return ModelSize.MEDIUM


# ============================================================================
# Factory function
# ============================================================================

async def get_explain_interpreter(db=None, model: Optional[str] = None) -> ExplainInterpreter:
    """Create an ExplainInterpreter with the standard agent setup."""
    from src.llm import get_llm_client
    from src.llm.model_router import get_model_router, TaskType

    router = await get_model_router(db) if db else None

    provider_name = router.get_provider_for_task(TaskType.EXPLAIN_ANALYSIS) if router else None
    client = get_llm_client(provider_name)

    timeout = 25.0
    if router:
        timeout = router.get_timeout_for_task(TaskType.EXPLAIN_ANALYSIS)

    effective_model = model
    if not effective_model and router:
        effective_model = router.get_model_for_task(TaskType.EXPLAIN_ANALYSIS)

    return ExplainInterpreter(
        ollama_client=client,
        model_router=router,
        timeout_seconds=timeout,
        model=effective_model,
    )
