"""Migration Planner Agent (Phase 20.2)

Takes a SchemaDiff and produces an ordered MigrationPlan with:
- Topological sorting of tables by FK dependencies
- Deterministic step generation (pre-check, backup, DDL, verify)
- Optional LLM enrichment (annotations, checklists, complexity)

Follows the ImpactAdvisor pattern: deterministic first, LLM enrichment second.
"""

import asyncio
import json
import logging
from collections import defaultdict, deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

from src.migration.schema_comparator import SchemaDiff, TableDiff

logger = logging.getLogger(__name__)


@dataclass
class MigrationStep:
    """A single step in the migration plan."""
    step_number: int = 0
    action: str = "ddl"  # "pre_check" | "backup" | "ddl" | "verify" | "rollback_point"
    description: str = ""
    sql_hint: Optional[str] = None
    table_name: Optional[str] = None
    lock_type: str = "none"  # "none" | "row" | "table" | "exclusive"
    estimated_duration: str = "instant"  # "instant" | "seconds" | "minutes" | "hours"
    risk_level: str = "low"
    is_reversible: bool = True
    depends_on: List[int] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MigrationPlan:
    """Complete migration plan for a project."""
    project_id: int = 0
    steps: List[MigrationStep] = field(default_factory=list)
    execution_order: List[str] = field(default_factory=list)
    total_estimated_downtime: str = "unknown"
    recommended_maintenance_window: bool = False
    pre_migration_checklist: List[str] = field(default_factory=list)
    post_migration_checklist: List[str] = field(default_factory=list)
    rollback_strategy: str = ""
    overall_complexity: str = "simple"  # "simple" | "moderate" | "complex" | "high-risk"
    llm_used: bool = False
    generated_at: str = ""

    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "steps": [s.to_dict() for s in self.steps],
            "execution_order": self.execution_order,
            "total_estimated_downtime": self.total_estimated_downtime,
            "recommended_maintenance_window": self.recommended_maintenance_window,
            "pre_migration_checklist": self.pre_migration_checklist,
            "post_migration_checklist": self.post_migration_checklist,
            "rollback_strategy": self.rollback_strategy,
            "overall_complexity": self.overall_complexity,
            "llm_used": self.llm_used,
            "generated_at": self.generated_at,
        }


class MigrationPlanner:
    """Plans safe migration steps from a SchemaDiff.

    Deterministic layer: topological sort + step generation.
    LLM layer: annotations, checklists, complexity assessment.
    """

    def __init__(self, ollama_client=None, model_router=None, timeout_seconds=30.0, model=None):
        self.client = ollama_client
        self.router = model_router
        self.timeout_seconds = timeout_seconds
        self.model = model

    async def plan(
        self,
        project_id: int,
        diff: SchemaDiff,
        db=None,
        source_schema: Optional[Dict[str, Any]] = None,
        target_schema: Optional[Dict[str, Any]] = None,
    ) -> MigrationPlan:
        """Generate a migration plan from a schema diff."""
        plan = MigrationPlan(project_id=project_id)

        # Step 1: Deterministic analysis
        plan.execution_order = self._topological_sort_tables(diff, source_schema, target_schema)
        plan.steps = self._generate_deterministic_steps(diff, plan.execution_order)
        plan.rollback_strategy = self._determine_rollback_strategy(diff)
        plan.overall_complexity = self._assess_complexity_deterministic(diff)
        plan.pre_migration_checklist = self._default_pre_checklist(diff)
        plan.post_migration_checklist = self._default_post_checklist(diff)
        plan.total_estimated_downtime = self._estimate_downtime(plan.steps)
        plan.recommended_maintenance_window = diff.overall_risk in ("high", "critical")

        # Step 2: LLM enrichment (optional)
        if self.client:
            try:
                model = self._get_model()
                results = await asyncio.gather(
                    self._llm_annotate_steps(plan, diff, model, db),
                    self._llm_generate_checklists(diff, model, db),
                    self._llm_assess_complexity(diff, model, db),
                    return_exceptions=True,
                )

                if not isinstance(results[0], Exception) and results[0]:
                    # Merge LLM annotations into steps
                    annotations = results[0]
                    for step in plan.steps:
                        if step.step_number in annotations:
                            ann = annotations[step.step_number]
                            step.warnings.extend(ann.get("warnings", []))
                            if ann.get("lock_type"):
                                step.lock_type = ann["lock_type"]
                            if ann.get("estimated_duration"):
                                step.estimated_duration = ann["estimated_duration"]

                if not isinstance(results[1], Exception) and results[1]:
                    checklists = results[1]
                    if checklists.get("pre"):
                        plan.pre_migration_checklist = checklists["pre"]
                    if checklists.get("post"):
                        plan.post_migration_checklist = checklists["post"]

                if not isinstance(results[2], Exception) and results[2]:
                    complexity = results[2]
                    if complexity.get("overall_complexity"):
                        plan.overall_complexity = complexity["overall_complexity"]
                    if complexity.get("rollback_strategy"):
                        plan.rollback_strategy = complexity["rollback_strategy"]

                llm_enriched = any(
                    not isinstance(r, Exception) and r for r in results
                )
                if llm_enriched:
                    plan.llm_used = True
                    logger.info("LLM enrichment applied to migration plan")
                else:
                    logger.warning("LLM enrichment produced no usable results, using deterministic plan")
            except Exception as e:
                logger.warning(f"LLM enrichment failed, using deterministic plan: {e}")

        return plan

    def _topological_sort_tables(
        self,
        diff: SchemaDiff,
        source_schema: Optional[Dict[str, Any]] = None,
        target_schema: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """Sort tables respecting FK dependencies using Kahn's algorithm.

        Parent tables (referenced by FK) come before child tables.
        Uses both constraint diffs AND existing FK relationships from
        the full schemas (so unchanged FKs are also respected).
        """
        # Build adjacency: parent -> [children]
        graph: Dict[str, set] = defaultdict(set)
        in_degree: Dict[str, int] = defaultdict(int)

        all_tables = set()
        for td in diff.table_diffs:
            all_tables.add(td.table_name)

            # Process FK constraints from diffs
            for cd in td.constraint_diffs:
                if cd.constraint_type == "foreign_key":
                    state = cd.target_state or cd.source_state
                    if state and isinstance(state, (list, tuple)) and len(state) >= 2:
                        referred_table = state[1]
                        if referred_table != td.table_name:
                            graph[referred_table].add(td.table_name)
                            in_degree[td.table_name] = in_degree.get(td.table_name, 0) + 1

        # Also consider existing FK relationships from the full target schema
        # (these won't appear in constraint_diffs if they haven't changed)
        schema_tables = (target_schema or source_schema or {}).get("tables", {})
        for table_name in all_tables:
            table_info = schema_tables.get(table_name, {})
            for fk in table_info.get("foreign_keys", []):
                referred_table = fk.get("referred_table", "")
                if referred_table and referred_table != table_name and referred_table in all_tables:
                    if table_name not in graph.get(referred_table, set()):
                        graph[referred_table].add(table_name)
                        in_degree[table_name] = in_degree.get(table_name, 0) + 1

        # Initialize nodes with 0 in-degree
        for table in all_tables:
            if table not in in_degree:
                in_degree[table] = 0

        # Kahn's algorithm
        queue = deque(t for t in sorted(all_tables) if in_degree[t] == 0)
        result = []

        while queue:
            node = queue.popleft()
            result.append(node)
            for child in sorted(graph.get(node, [])):
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)

        # Add any remaining tables (circular deps)
        remaining = [t for t in sorted(all_tables) if t not in result]
        if remaining:
            logger.warning(f"Circular FK dependencies detected for tables: {remaining}")
            result.extend(remaining)

        return result

    def _generate_deterministic_steps(
        self, diff: SchemaDiff, execution_order: List[str],
    ) -> List[MigrationStep]:
        """Generate ordered migration steps without LLM."""
        steps: List[MigrationStep] = []
        step_num = 1

        # Pre-check step
        steps.append(MigrationStep(
            step_number=step_num,
            action="pre_check",
            description="Verify database connectivity and current schema state",
            risk_level="low",
        ))
        step_num += 1

        # Build a lookup for table diffs
        diff_by_table = {td.table_name: td for td in diff.table_diffs}

        # Backup step for critical changes
        critical_tables = [
            td.table_name for td in diff.table_diffs
            if td.risk_level in ("high", "critical")
        ]
        if critical_tables:
            steps.append(MigrationStep(
                step_number=step_num,
                action="backup",
                description=f"Backup affected tables: {', '.join(critical_tables)}",
                risk_level="low",
                is_reversible=True,
            ))
            step_num += 1

        # Process tables in topological order
        for table_name in execution_order:
            td = diff_by_table.get(table_name)
            if not td:
                continue

            if td.diff_type == "added":
                steps.append(MigrationStep(
                    step_number=step_num,
                    action="ddl",
                    description=f"Create table '{table_name}'",
                    table_name=table_name,
                    risk_level="low",
                    lock_type="none",
                    is_reversible=True,
                ))
                step_num += 1

            elif td.diff_type == "removed":
                steps.append(MigrationStep(
                    step_number=step_num,
                    action="ddl",
                    description=f"Drop table '{table_name}'",
                    table_name=table_name,
                    risk_level="critical",
                    lock_type="exclusive",
                    is_reversible=False,
                    warnings=["DATA LOSS: All data in this table will be permanently deleted"],
                ))
                step_num += 1

            elif td.diff_type == "modified":
                for cd in td.column_diffs:
                    desc = self._describe_column_change(cd)
                    warnings = []
                    if cd.is_breaking:
                        warnings.append(f"Breaking change: {cd.diff_type} on {table_name}.{cd.column_name}")
                    steps.append(MigrationStep(
                        step_number=step_num,
                        action="ddl",
                        description=desc,
                        table_name=table_name,
                        risk_level=cd.risk_level,
                        lock_type="table" if cd.diff_type in ("type_changed", "nullability_changed") else "none",
                        is_reversible=cd.diff_type != "removed",
                        warnings=warnings,
                    ))
                    step_num += 1

                for cd in td.constraint_diffs:
                    steps.append(MigrationStep(
                        step_number=step_num,
                        action="ddl",
                        description=f"{cd.diff_type.title()} {cd.constraint_type} on '{table_name}'",
                        table_name=table_name,
                        risk_level=cd.risk_level,
                        lock_type="table" if cd.constraint_type == "primary_key" else "none",
                    ))
                    step_num += 1

        # Final verify step
        steps.append(MigrationStep(
            step_number=step_num,
            action="verify",
            description="Run verification queries to confirm migration success",
            risk_level="low",
        ))

        return steps

    def _describe_column_change(self, cd) -> str:
        """Generate a human-readable description for a column diff."""
        if cd.diff_type == "added":
            tgt = cd.target_state or {}
            return f"Add column '{cd.column_name}' ({tgt.get('type', '?')}) to '{cd.table_name}'"
        elif cd.diff_type == "removed":
            return f"Drop column '{cd.column_name}' from '{cd.table_name}'"
        elif cd.diff_type == "type_changed":
            src = cd.source_state or {}
            tgt = cd.target_state or {}
            return f"Change '{cd.table_name}'.'{cd.column_name}' type: {src.get('type', '?')} -> {tgt.get('type', '?')}"
        elif cd.diff_type == "nullability_changed":
            tgt = cd.target_state or {}
            nullable = "nullable" if tgt.get("nullable", True) else "NOT NULL"
            return f"Change '{cd.table_name}'.'{cd.column_name}' to {nullable}"
        elif cd.diff_type == "default_changed":
            tgt = cd.target_state or {}
            return f"Change default for '{cd.table_name}'.'{cd.column_name}' to {tgt.get('default', 'NULL')}"
        return f"Modify '{cd.table_name}'.'{cd.column_name}' ({cd.diff_type})"

    def _determine_rollback_strategy(self, diff: SchemaDiff) -> str:
        has_critical = any(td.risk_level == "critical" for td in diff.table_diffs)
        if has_critical:
            return "Execute down.sql rollback script. Restore from backup for dropped tables/columns."
        return "Execute down.sql rollback script to reverse all changes."

    def _assess_complexity_deterministic(self, diff: SchemaDiff) -> str:
        total_changes = sum(
            len(td.column_diffs) + len(td.constraint_diffs)
            for td in diff.table_diffs
        )
        if diff.overall_risk == "critical" or total_changes > 20:
            return "high-risk"
        if diff.overall_risk == "high" or total_changes > 10:
            return "complex"
        if total_changes > 3:
            return "moderate"
        return "simple"

    def _default_pre_checklist(self, diff: SchemaDiff) -> List[str]:
        items = [
            "Verify database backup is current",
            "Confirm no active long-running queries",
            "Review generated scripts for correctness",
        ]
        if diff.overall_risk in ("high", "critical"):
            items.append("Schedule maintenance window")
            items.append("Notify affected teams")
        return items

    def _default_post_checklist(self, diff: SchemaDiff) -> List[str]:
        return [
            "Run verify.sql to confirm migration success",
            "Check application connectivity",
            "Monitor error logs for 15 minutes",
            "Update schema documentation",
        ]

    def _estimate_downtime(self, steps: List[MigrationStep]) -> str:
        ddl_count = sum(1 for s in steps if s.action == "ddl")
        has_critical = any(s.risk_level == "critical" for s in steps)
        if has_critical:
            return "minutes to hours (depends on table sizes)"
        if ddl_count > 10:
            return "minutes"
        if ddl_count > 3:
            return "seconds to minutes"
        return "seconds"

    def _get_model(self) -> str:
        if self.model:
            return self.model
        if self.router:
            from src.llm.model_router import TaskType
            return self.router.get_model_for_task(TaskType.MIGRATION_PLANNER)
        return "llama3.2:latest"

    async def _llm_annotate_steps(
        self, plan: MigrationPlan, diff: SchemaDiff, model: str, db=None,
    ) -> Optional[Dict[int, Dict]]:
        """Use LLM to add warnings and lock guidance per step."""
        if not self.client:
            return None

        steps_text = "\n".join(
            f"Step {s.step_number}: [{s.action}] {s.description} (risk: {s.risk_level})"
            for s in plan.steps if s.action == "ddl"
        )

        prompt = f"""You are a database migration expert. Annotate each DDL step with practical warnings.

Migration steps:
{steps_text}

For each step, return a JSON object where keys are step numbers (as integers) and values have:
- "warnings": list of practical warnings (empty list if none)
- "lock_type": "none"|"row"|"table"|"exclusive"
- "estimated_duration": "instant"|"seconds"|"minutes"|"hours"

Return ONLY the JSON object, no explanation."""

        try:
            from src.lineage.llm_utils import extract_json_object

            response = await asyncio.wait_for(
                self.client.generate(
                    prompt=prompt,
                    model=model,
                    temperature=0.2,
                    db=db,
                    agent_type="migration_planner",
                ),
                timeout=self.timeout_seconds,
            )
            json_str = extract_json_object(response)
            if json_str:
                data = json.loads(json_str)
                return {int(k): v for k, v in data.items()}
        except Exception as e:
            logger.warning(f"LLM step annotation failed: {e}")
        return None

    async def _llm_generate_checklists(
        self, diff: SchemaDiff, model: str, db=None,
    ) -> Optional[Dict[str, List[str]]]:
        """Use LLM to generate pre/post migration checklists."""
        if not self.client:
            return None

        prompt = f"""You are a database migration expert. Generate pre and post migration checklists.

Schema changes summary: {diff.diff_summary}
Overall risk: {diff.overall_risk}
Breaking changes: {diff.total_breaking_changes}

Return a JSON object with:
- "pre": list of 3-5 pre-migration checklist items
- "post": list of 3-5 post-migration checklist items

Return ONLY the JSON object."""

        try:
            from src.lineage.llm_utils import extract_json_object

            response = await asyncio.wait_for(
                self.client.generate(
                    prompt=prompt,
                    model=model,
                    temperature=0.2,
                    db=db,
                    agent_type="migration_planner",
                ),
                timeout=self.timeout_seconds,
            )
            json_str = extract_json_object(response)
            if json_str:
                return json.loads(json_str)
        except Exception as e:
            logger.warning(f"LLM checklist generation failed: {e}")
        return None

    async def _llm_assess_complexity(
        self, diff: SchemaDiff, model: str, db=None,
    ) -> Optional[Dict[str, str]]:
        """Use LLM to assess overall complexity."""
        if not self.client:
            return None

        prompt = f"""You are a database migration expert. Assess the complexity of this migration.

Changes: {diff.diff_summary}
Risk level: {diff.overall_risk}
Breaking changes: {diff.total_breaking_changes}
Safe changes: {diff.total_safe_changes}

Return a JSON object with:
- "overall_complexity": "simple"|"moderate"|"complex"|"high-risk"
- "rollback_strategy": a brief rollback strategy description

Return ONLY the JSON object."""

        try:
            from src.lineage.llm_utils import extract_json_object

            response = await asyncio.wait_for(
                self.client.generate(
                    prompt=prompt,
                    model=model,
                    temperature=0.2,
                    db=db,
                    agent_type="migration_planner",
                ),
                timeout=self.timeout_seconds,
            )
            json_str = extract_json_object(response)
            if json_str:
                return json.loads(json_str)
        except Exception as e:
            logger.warning(f"LLM complexity assessment failed: {e}")
        return None


async def get_migration_planner(db=None, model=None) -> MigrationPlanner:
    """Factory function to create a MigrationPlanner instance."""
    from src.llm.ollama_client import get_ollama_client
    from src.llm.model_router import get_model_router, TaskType

    client = get_ollama_client()
    router = await get_model_router(db) if db else None

    timeout = router.get_timeout_for_task(TaskType.MIGRATION_PLANNER) if router else 30.0
    resolved_model = model or (router.get_model_for_task(TaskType.MIGRATION_PLANNER) if router else None)

    return MigrationPlanner(
        ollama_client=client,
        model_router=router,
        timeout_seconds=timeout,
        model=resolved_model,
    )


async def plan_migration(
    project,
    db=None,
    source_schema: Optional[Dict[str, Any]] = None,
    target_schema: Optional[Dict[str, Any]] = None,
) -> MigrationPlan:
    """High-level function to plan migration for a project."""
    planner = await get_migration_planner(db)

    diff_data = project.diff_snapshot
    if not diff_data:
        raise ValueError("Project has no diff snapshot")

    diff = SchemaDiff.from_dict(diff_data)
    return await planner.plan(project.id, diff, db, source_schema, target_schema)
