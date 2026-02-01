"""
Impact Advisor - Phase 12.2

Extends ImpactAnalyzer with LLM-powered recommendations:
- Risk explanations (why the change is risky)
- Migration plans (step-by-step migration guide)
- SQL patches (corrected query versions)

Follows the LineageNarrator pattern for LLM integration.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

from src.lineage.impact_analyzer import (
    ImpactAnalyzer,
    ImpactAnalysis,
    ImpactedQuery,
    RiskLevel,
)
from src.lineage.llm_utils import extract_json_object

logger = logging.getLogger(__name__)


class ChangeType(Enum):
    """Type of schema change being analyzed."""
    RENAME_COLUMN = "rename_column"
    RENAME_TABLE = "rename_table"
    DROP_COLUMN = "drop_column"
    DROP_TABLE = "drop_table"
    CHANGE_TYPE = "change_type"
    ADD_CONSTRAINT = "add_constraint"
    REMOVE_CONSTRAINT = "remove_constraint"


@dataclass
class SQLPatch:
    """A suggested SQL modification for an impacted query."""
    query_id: int
    original_sql: str
    patched_sql: str
    change_description: str
    confidence: float = 0.8
    requires_review: bool = False

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class MigrationStep:
    """A single step in a migration plan."""
    step_number: int
    action: str  # e.g., "backup", "alter_table", "update_queries", "verify"
    description: str
    sql: Optional[str] = None  # SQL to execute, if applicable
    reversible: bool = True
    risk_level: str = "low"

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class MigrationPlan:
    """Complete migration plan for a schema change."""
    change_type: str
    target_object: str
    new_value: Optional[str] = None
    steps: List[MigrationStep] = field(default_factory=list)
    estimated_downtime: str = "none"  # none, minimal, moderate, significant
    rollback_possible: bool = True
    warnings: List[str] = field(default_factory=list)
    generated_at: Optional[str] = None

    def __post_init__(self):
        if self.generated_at is None:
            self.generated_at = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict:
        result = asdict(self)
        result["steps"] = [s.to_dict() if isinstance(s, MigrationStep) else s for s in self.steps]
        return result


@dataclass
class RiskExplanation:
    """LLM-generated explanation of why a change is risky."""
    risk_level: str
    summary: str  # One-line risk summary
    detailed_explanation: str  # Full explanation
    affected_areas: List[str] = field(default_factory=list)  # ["reporting", "ETL", "API"]
    recommendations: List[str] = field(default_factory=list)
    confidence: float = 0.8

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ImpactAdvice:
    """Complete LLM-enhanced impact analysis with recommendations."""
    # Base impact analysis
    impact: ImpactAnalysis
    change_type: str
    new_value: Optional[str] = None

    # LLM-generated content
    risk_explanation: Optional[RiskExplanation] = None
    migration_plan: Optional[MigrationPlan] = None
    sql_patches: List[SQLPatch] = field(default_factory=list)

    # Metadata
    generated_at: Optional[str] = None
    llm_used: bool = False

    def __post_init__(self):
        if self.generated_at is None:
            self.generated_at = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict:
        result = {
            "impact": self.impact.to_dict(),
            "change_type": self.change_type,
            "new_value": self.new_value,
            "risk_explanation": self.risk_explanation.to_dict() if self.risk_explanation else None,
            "migration_plan": self.migration_plan.to_dict() if self.migration_plan else None,
            "sql_patches": [p.to_dict() for p in self.sql_patches],
            "generated_at": self.generated_at,
            "llm_used": self.llm_used,
        }
        return result


# Prompt templates
RISK_EXPLANATION_PROMPT = """Analyze the risk of this database schema change.

## Change Details
Change Type: {change_type}
Target Object: {target_object}
New Value: {new_value}

## Impact Summary
- Total affected queries: {total_affected}
- Current risk level: {risk_level}
- Risk breakdown: {risk_counts}

## Sample Affected Queries
{sample_queries}

## Task
Explain why this change is risky (or not) and what areas might be affected.

Respond in JSON format:
{{
  "risk_level": "low|medium|high",
  "summary": "One-line risk summary",
  "detailed_explanation": "2-3 paragraphs explaining the risk",
  "affected_areas": ["reporting", "ETL", "user-facing queries"],
  "recommendations": ["Test in staging first", "Update query X"],
  "confidence": 0.85
}}"""


MIGRATION_PLAN_PROMPT = """Generate a step-by-step migration plan for this schema change.

## Change Details
Change Type: {change_type}
Target Object: {target_object}
New Value: {new_value}
Database Type: {db_type}

## Impact Assessment
Total affected queries: {total_affected}
Risk level: {risk_level}

## Affected Queries (sample)
{sample_queries}

## Task
Create a safe migration plan with:
1. Pre-migration steps (backup, validation)
2. The schema change itself
3. Query updates
4. Verification steps
5. Rollback plan

Respond in JSON format:
{{
  "estimated_downtime": "none|minimal|moderate|significant",
  "rollback_possible": true,
  "warnings": ["Warning 1", "Warning 2"],
  "steps": [
    {{
      "step_number": 1,
      "action": "backup",
      "description": "Create backup of affected table",
      "sql": "-- Optional SQL command",
      "reversible": true,
      "risk_level": "low"
    }}
  ]
}}"""


SQL_PATCH_PROMPT = """Generate patched SQL queries to accommodate this schema change.

## Change Details
Change Type: {change_type}
Old Value: {old_value}
New Value: {new_value}

## Original Queries to Patch
{queries_to_patch}

## Task
For each query, generate the patched version that works with the new schema.

Respond in JSON format:
{{
  "patches": [
    {{
      "query_id": 1,
      "original_sql": "SELECT old_column FROM table",
      "patched_sql": "SELECT new_column FROM table",
      "change_description": "Renamed old_column to new_column",
      "confidence": 0.95,
      "requires_review": false
    }}
  ]
}}"""


class ImpactAdvisor:
    """
    LLM-enhanced impact analysis advisor.

    Extends ImpactAnalyzer with:
    - Risk explanations (business-friendly risk assessment)
    - Migration plans (step-by-step guides)
    - SQL patches (updated query suggestions)
    """

    def __init__(
        self,
        ollama_client,
        model_router=None,
        timeout_seconds: float = 20.0,
        model: Optional[str] = None,
    ):
        """
        Initialize the impact advisor.

        Args:
            ollama_client: OllamaClient instance for LLM calls
            model_router: Optional ModelRouter for per-task model selection
            timeout_seconds: Timeout for LLM calls
            model: Optional model override
        """
        self.client = ollama_client
        self.router = model_router
        self.timeout_seconds = timeout_seconds
        self.model = model
        self.impact_analyzer = ImpactAnalyzer()

    async def analyze_with_recommendations(
        self,
        db,
        change_type: str,
        table_name: str,
        column_name: Optional[str] = None,
        new_value: Optional[str] = None,
        include_patches: bool = True,
        timeout: Optional[float] = None,
    ) -> ImpactAdvice:
        """
        Perform complete impact analysis with LLM-generated recommendations.

        Args:
            db: Database session
            change_type: Type of change (rename_column, drop_table, etc.)
            table_name: Table being modified
            column_name: Column being modified (if applicable)
            new_value: New name/type (for renames/type changes)
            include_patches: Whether to generate SQL patches
            timeout: Optional timeout override

        Returns:
            ImpactAdvice with complete analysis and recommendations
        """
        effective_timeout = timeout or self.timeout_seconds

        # Step 1: Run base impact analysis
        if column_name:
            impact = await self.impact_analyzer.analyze_column_impact(
                db, table_name, column_name
            )
            target_object = f"{table_name}.{column_name}"
        else:
            impact = await self.impact_analyzer.analyze_table_impact(db, table_name)
            target_object = table_name

        # Step 2: Build advice with LLM enhancements
        advice = ImpactAdvice(
            impact=impact,
            change_type=change_type,
            new_value=new_value,
        )

        # Step 3: Generate LLM content in parallel
        try:
            tasks = [
                self._generate_risk_explanation(
                    impact, change_type, target_object, new_value, effective_timeout
                ),
                self._generate_migration_plan(
                    impact, change_type, target_object, new_value, effective_timeout
                ),
            ]

            if include_patches and impact.impacted_queries and new_value:
                tasks.append(
                    self._generate_sql_patches(
                        impact.impacted_queries[:10],  # Limit to 10 queries
                        change_type,
                        target_object,
                        new_value,
                        effective_timeout,
                    )
                )

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            if not isinstance(results[0], Exception):
                advice.risk_explanation = results[0]
                advice.llm_used = True

            if not isinstance(results[1], Exception):
                advice.migration_plan = results[1]
                advice.llm_used = True

            if len(results) > 2 and not isinstance(results[2], Exception):
                advice.sql_patches = results[2]

        except Exception as e:
            logger.warning(f"LLM enhancement failed: {e}")
            # Fallback to deterministic advice
            advice.risk_explanation = self._fallback_risk_explanation(impact)
            advice.migration_plan = self._fallback_migration_plan(
                change_type, target_object, new_value
            )

        return advice

    async def explain_risk(
        self,
        impact: ImpactAnalysis,
        change_type: str,
        new_value: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> RiskExplanation:
        """Generate a detailed risk explanation for an impact analysis."""
        target_object = impact.changed_object
        effective_timeout = timeout or self.timeout_seconds

        try:
            return await self._generate_risk_explanation(
                impact, change_type, target_object, new_value, effective_timeout
            )
        except Exception as e:
            logger.warning(f"Risk explanation failed: {e}")
            return self._fallback_risk_explanation(impact)

    async def generate_migration_plan(
        self,
        impact: ImpactAnalysis,
        change_type: str,
        new_value: Optional[str] = None,
        db_type: str = "postgresql",
        timeout: Optional[float] = None,
    ) -> MigrationPlan:
        """Generate a migration plan for a schema change."""
        target_object = impact.changed_object
        effective_timeout = timeout or self.timeout_seconds

        try:
            return await self._generate_migration_plan(
                impact, change_type, target_object, new_value, effective_timeout, db_type
            )
        except Exception as e:
            logger.warning(f"Migration plan generation failed: {e}")
            return self._fallback_migration_plan(change_type, target_object, new_value)

    async def generate_sql_patches(
        self,
        impacted_queries: List[ImpactedQuery],
        change_type: str,
        old_value: str,
        new_value: str,
        timeout: Optional[float] = None,
    ) -> List[SQLPatch]:
        """Generate SQL patches for affected queries."""
        effective_timeout = timeout or self.timeout_seconds

        try:
            return await self._generate_sql_patches(
                impacted_queries, change_type, old_value, new_value, effective_timeout
            )
        except Exception as e:
            logger.warning(f"SQL patch generation failed: {e}")
            return []

    async def _generate_risk_explanation(
        self,
        impact: ImpactAnalysis,
        change_type: str,
        target_object: str,
        new_value: Optional[str],
        timeout: float,
    ) -> RiskExplanation:
        """Generate risk explanation using LLM."""
        # Format sample queries
        sample_queries = self._format_sample_queries(impact.impacted_queries[:5])

        prompt = RISK_EXPLANATION_PROMPT.format(
            change_type=change_type,
            target_object=target_object,
            new_value=new_value or "N/A",
            total_affected=impact.total_affected,
            risk_level=impact.risk_level,
            risk_counts=json.dumps(impact.risk_counts),
            sample_queries=sample_queries,
        )

        model = self._get_model()
        response = await asyncio.wait_for(
            self.client.generate(prompt=prompt, model=model, temperature=0.2),
            timeout=timeout,
        )

        # Parse response
        json_str = extract_json_object(response)
        if not json_str:
            raise ValueError("No valid JSON in response")

        data = json.loads(json_str)
        return RiskExplanation(
            risk_level=data.get("risk_level", impact.risk_level),
            summary=data.get("summary", ""),
            detailed_explanation=data.get("detailed_explanation", ""),
            affected_areas=data.get("affected_areas", []),
            recommendations=data.get("recommendations", []),
            confidence=data.get("confidence", 0.8),
        )

    async def _generate_migration_plan(
        self,
        impact: ImpactAnalysis,
        change_type: str,
        target_object: str,
        new_value: Optional[str],
        timeout: float,
        db_type: str = "postgresql",
    ) -> MigrationPlan:
        """Generate migration plan using LLM."""
        sample_queries = self._format_sample_queries(impact.impacted_queries[:5])

        prompt = MIGRATION_PLAN_PROMPT.format(
            change_type=change_type,
            target_object=target_object,
            new_value=new_value or "N/A",
            db_type=db_type,
            total_affected=impact.total_affected,
            risk_level=impact.risk_level,
            sample_queries=sample_queries,
        )

        model = self._get_model()
        response = await asyncio.wait_for(
            self.client.generate(prompt=prompt, model=model, temperature=0.2),
            timeout=timeout,
        )

        # Parse response
        json_str = extract_json_object(response)
        if not json_str:
            raise ValueError("No valid JSON in response")

        data = json.loads(json_str)

        # Build migration steps
        steps = []
        for step_data in data.get("steps", []):
            steps.append(MigrationStep(
                step_number=step_data.get("step_number", len(steps) + 1),
                action=step_data.get("action", "unknown"),
                description=step_data.get("description", ""),
                sql=step_data.get("sql"),
                reversible=step_data.get("reversible", True),
                risk_level=step_data.get("risk_level", "low"),
            ))

        return MigrationPlan(
            change_type=change_type,
            target_object=target_object,
            new_value=new_value,
            steps=steps,
            estimated_downtime=data.get("estimated_downtime", "minimal"),
            rollback_possible=data.get("rollback_possible", True),
            warnings=data.get("warnings", []),
        )

    async def _generate_sql_patches(
        self,
        impacted_queries: List[ImpactedQuery],
        change_type: str,
        old_value: str,
        new_value: str,
        timeout: float,
    ) -> List[SQLPatch]:
        """Generate SQL patches for affected queries."""
        # Format queries for prompt
        queries_formatted = "\n\n".join([
            f"Query ID: {q.query_id}\n"
            f"Original Question: {q.natural_language_query}\n"
            f"SQL: {q.generated_sql}"
            for q in impacted_queries
        ])

        prompt = SQL_PATCH_PROMPT.format(
            change_type=change_type,
            old_value=old_value,
            new_value=new_value,
            queries_to_patch=queries_formatted,
        )

        model = self._get_model()
        response = await asyncio.wait_for(
            self.client.generate(prompt=prompt, model=model, temperature=0.2),
            timeout=timeout,
        )

        # Parse response
        json_str = extract_json_object(response)
        if not json_str:
            return []

        data = json.loads(json_str)
        patches = []

        for patch_data in data.get("patches", []):
            patches.append(SQLPatch(
                query_id=patch_data.get("query_id", 0),
                original_sql=patch_data.get("original_sql", ""),
                patched_sql=patch_data.get("patched_sql", ""),
                change_description=patch_data.get("change_description", ""),
                confidence=patch_data.get("confidence", 0.8),
                requires_review=patch_data.get("requires_review", False),
            ))

        return patches

    def _fallback_risk_explanation(self, impact: ImpactAnalysis) -> RiskExplanation:
        """Generate deterministic risk explanation when LLM fails."""
        if impact.total_affected == 0:
            return RiskExplanation(
                risk_level="low",
                summary="No queries currently reference this object.",
                detailed_explanation=(
                    "Based on query history analysis, no existing queries reference "
                    f"{impact.changed_object}. This change can likely be made safely, "
                    "but consider checking for any queries not captured in history."
                ),
                affected_areas=[],
                recommendations=["Verify no external systems depend on this object"],
                confidence=0.6,
            )

        risk_descriptions = {
            "low": "Minor impact expected",
            "medium": "Moderate impact - careful testing recommended",
            "high": "Significant impact - thorough review required",
        }

        return RiskExplanation(
            risk_level=impact.risk_level,
            summary=f"{impact.total_affected} queries affected. {risk_descriptions.get(impact.risk_level, '')}",
            detailed_explanation=(
                f"This change will affect {impact.total_affected} existing queries. "
                f"Risk breakdown: {impact.risk_counts['high']} high, "
                f"{impact.risk_counts['medium']} medium, {impact.risk_counts['low']} low risk queries. "
                "Review affected queries and plan for necessary updates."
            ),
            affected_areas=["query_history"],
            recommendations=[
                "Review all affected queries before making changes",
                "Test in a non-production environment first",
                "Prepare updated versions of affected queries",
            ],
            confidence=0.4,  # Lower confidence for fallback
        )

    def _fallback_migration_plan(
        self,
        change_type: str,
        target_object: str,
        new_value: Optional[str],
    ) -> MigrationPlan:
        """Generate deterministic migration plan when LLM fails."""
        steps = [
            MigrationStep(
                step_number=1,
                action="backup",
                description=f"Create backup of {target_object} and related data",
                reversible=True,
                risk_level="low",
            ),
            MigrationStep(
                step_number=2,
                action="validate",
                description="Verify all affected queries have been identified",
                reversible=True,
                risk_level="low",
            ),
        ]

        # Add change-specific steps
        if change_type == ChangeType.RENAME_COLUMN.value and new_value:
            steps.append(MigrationStep(
                step_number=3,
                action="alter_table",
                description=f"Rename column to {new_value}",
                sql=f"ALTER TABLE ... RENAME COLUMN ... TO {new_value};",
                reversible=True,
                risk_level="medium",
            ))
        elif change_type == ChangeType.DROP_COLUMN.value:
            steps.append(MigrationStep(
                step_number=3,
                action="alter_table",
                description="Drop column (ensure data backup exists)",
                sql="ALTER TABLE ... DROP COLUMN ...;",
                reversible=False,
                risk_level="high",
            ))
        elif change_type == ChangeType.DROP_TABLE.value:
            steps.append(MigrationStep(
                step_number=3,
                action="drop_table",
                description="Drop table (ensure full backup exists)",
                sql="DROP TABLE ...;",
                reversible=False,
                risk_level="high",
            ))
        else:
            steps.append(MigrationStep(
                step_number=3,
                action="execute_change",
                description=f"Execute {change_type} change",
                reversible=True,
                risk_level="medium",
            ))

        steps.extend([
            MigrationStep(
                step_number=4,
                action="update_queries",
                description="Update affected queries to use new schema",
                reversible=True,
                risk_level="medium",
            ),
            MigrationStep(
                step_number=5,
                action="verify",
                description="Verify all updated queries work correctly",
                reversible=True,
                risk_level="low",
            ),
        ])

        return MigrationPlan(
            change_type=change_type,
            target_object=target_object,
            new_value=new_value,
            steps=steps,
            estimated_downtime="minimal",
            rollback_possible=change_type not in [
                ChangeType.DROP_COLUMN.value,
                ChangeType.DROP_TABLE.value,
            ],
            warnings=["This is a basic plan. Review carefully before execution."],
        )

    def _format_sample_queries(self, queries: List[ImpactedQuery]) -> str:
        """Format sample queries for LLM prompt."""
        if not queries:
            return "No affected queries found."

        lines = []
        for q in queries:
            lines.append(
                f"- Query {q.query_id}: {q.natural_language_query}\n"
                f"  SQL: {q.generated_sql[:200]}{'...' if len(q.generated_sql) > 200 else ''}\n"
                f"  Impact Type: {q.impact_type}, Risk: {q.risk_level}"
            )
        return "\n".join(lines)

    def _get_model(self) -> Optional[str]:
        """Get model to use for generation."""
        if self.model:
            return self.model
        if self.router:
            from src.llm.model_router import TaskType
            return self.router.get_model_for_task(TaskType.IMPACT_ANALYSIS)
        return None

async def get_impact_advisor(
    db=None,
    model: Optional[str] = None,
) -> ImpactAdvisor:
    """
    Factory function to create an ImpactAdvisor instance.

    Args:
        db: Optional database session (for loading settings)
        model: Optional model override

    Returns:
        Configured ImpactAdvisor instance
    """
    from src.llm.ollama_client import get_ollama_client
    from src.llm.model_router import get_model_router, TaskType

    client = get_ollama_client()
    router = await get_model_router(db) if db else None

    # Get timeout from router or use default
    timeout = 20.0
    if router:
        timeout = router.get_timeout_for_task(TaskType.IMPACT_ANALYSIS)

    # Use provided model or get from router
    effective_model = model
    if not effective_model and router:
        effective_model = router.get_model_for_task(TaskType.IMPACT_ANALYSIS)

    return ImpactAdvisor(
        ollama_client=client,
        model_router=router,
        timeout_seconds=timeout,
        model=effective_model,
    )
