"""
Lineage Narrator - Phase 12.1

Generates natural language explanations of data lineage graphs,
transforming technical SQL analysis into business-friendly narratives.

Follows the ResultNarrator pattern for LLM integration:
- Extract deterministic data first
- Wrap LLM calls with asyncio.wait_for() for timeout
- Parse JSON with balanced brace matching
- Always have fallback response on timeout/error
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional, Any

from src.lineage.sql_lineage_parser import (
    LineageGraph,
    LineageNode,
    LineageNodeType,
    TransformationType,
)
from src.lineage.llm_utils import extract_json_object

logger = logging.getLogger(__name__)


@dataclass
class TransformationExplanation:
    """Explanation of a single transformation in the lineage graph."""
    node_id: str
    transformation_type: str
    input_columns: List[str]
    output_column: str
    explanation: str  # "Sums all order totals for each customer"
    business_meaning: Optional[str] = None  # "Calculates customer lifetime value"

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class LineageNarrative:
    """LLM-generated narrative explanation of data lineage."""
    summary: str  # 2-3 sentence overview
    data_flow_description: str  # Detailed flow explanation
    column_explanations: Dict[str, str] = field(default_factory=dict)  # output_col -> explanation
    transformations_explained: List[TransformationExplanation] = field(default_factory=list)
    business_context: Dict[str, str] = field(default_factory=dict)  # technical_name -> business_term
    potential_issues: List[str] = field(default_factory=list)  # Detected quality/logic issues
    confidence: float = 0.5  # 0.0-1.0
    generated_at: Optional[str] = None

    def __post_init__(self):
        if self.generated_at is None:
            self.generated_at = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict:
        result = asdict(self)
        # Convert TransformationExplanation objects to dicts
        result["transformations_explained"] = [
            t.to_dict() if isinstance(t, TransformationExplanation) else t
            for t in self.transformations_explained
        ]
        return result


# Prompt template for lineage narrative generation
LINEAGE_NARRATIVE_PROMPT = """Analyze this SQL data lineage and explain it in business terms.

## Original Question
{question}

## SQL Query
{sql}

## Data Flow Graph
Source Tables: {source_tables}
Output Columns: {output_columns}

Transformations:
{transformations_formatted}

## Column Lineage
{column_lineage_formatted}

## Task
Provide:
1. SUMMARY: 2-3 sentences explaining what this query does in business terms
2. DATA FLOW: Step-by-step explanation of how data flows from sources to results
3. COLUMN MEANINGS: For each output column, explain what it represents
4. TRANSFORMATIONS: Explain each transformation (SUM, JOIN, CASE, etc.) in business terms
5. POTENTIAL ISSUES: Any data quality or logic concerns you notice

Respond in JSON format:
{{
  "summary": "...",
  "data_flow_description": "...",
  "column_explanations": {{"col1": "...", "col2": "..."}},
  "transformations_explained": [
    {{"node_id": "...", "transformation_type": "...", "input_columns": [], "output_column": "...", "explanation": "...", "business_meaning": "..."}}
  ],
  "business_context": {{"technical_name": "business_term"}},
  "potential_issues": ["...", "..."],
  "confidence": 0.85
}}"""


class LineageNarrator:
    """
    Generates natural language explanations of data lineage graphs.

    This agent:
    1. Extracts deterministic summary from lineage graph
    2. Builds an LLM prompt with lineage context
    3. Generates business-friendly narrative
    4. Returns structured narrative with confidence score
    5. Falls back to deterministic narrative on timeout/error
    """

    def __init__(
        self,
        ollama_client,
        model_router=None,
        timeout_seconds: float = 15.0,
        model: Optional[str] = None,
    ):
        """
        Initialize the lineage narrator.

        Args:
            ollama_client: OllamaClient instance for LLM calls
            model_router: Optional ModelRouter for per-task model selection
            timeout_seconds: Timeout for LLM calls
            model: Optional model override for narrative generation
        """
        self.client = ollama_client
        self.router = model_router
        self.timeout_seconds = timeout_seconds
        self.model = model

    async def generate_narrative(
        self,
        lineage_graph: LineageGraph,
        question: Optional[str] = None,
        schema_context: Optional[Dict] = None,
        timeout: Optional[float] = None,
    ) -> LineageNarrative:
        """
        Generate narrative explanation of lineage.

        Args:
            lineage_graph: Parsed lineage from SQLLineageParser
            question: Original natural language query (for context)
            schema_context: Table/column descriptions if available
            timeout: Override default timeout

        Returns:
            LineageNarrative with summary, column explanations, recommendations
        """
        effective_timeout = timeout or self.timeout_seconds

        try:
            # Handle empty lineage
            if not lineage_graph.nodes:
                return self._fallback_narrative(lineage_graph, "No lineage data available for analysis.")

            # Extract deterministic summary first
            deterministic_summary = self._extract_deterministic_summary(lineage_graph)

            # Build prompt for LLM
            prompt = self._build_lineage_prompt(lineage_graph, question)

            # Determine model to use
            model_to_use = self.model
            if not model_to_use and self.router:
                try:
                    from src.llm.model_router import TaskType
                    model_to_use = self.router.get_model_for_task(TaskType.LINEAGE_NARRATIVE)
                except (ImportError, AttributeError):
                    pass  # Fall back to default model

            # Call LLM with timeout
            try:
                logger.debug(f"🔍 Generating lineage narrative for {len(lineage_graph.nodes)} nodes")
                response_text = await asyncio.wait_for(
                    self.client.generate(
                        prompt=prompt,
                        temperature=0.2,  # Low temperature for analytical task
                        model=model_to_use,
                    ),
                    timeout=effective_timeout
                )
            except asyncio.TimeoutError:
                logger.warning(f"⏱️ Lineage narrative generation timeout after {effective_timeout}s")
                return self._fallback_narrative(lineage_graph, deterministic_summary)
            except Exception as e:
                logger.error(f"❌ LLM call failed: {e}")
                return self._fallback_narrative(lineage_graph, deterministic_summary)

            # Parse response
            narrative = self._parse_response(response_text, lineage_graph, deterministic_summary)
            logger.info(f"✅ Generated lineage narrative with confidence {narrative.confidence:.2f}")
            return narrative

        except Exception as e:
            logger.error(f"❌ Error generating narrative: {e}", exc_info=True)
            return self._fallback_narrative(lineage_graph, "Error analyzing lineage.")

    async def explain_transformation(
        self,
        node: LineageNode,
        context: Dict,
    ) -> str:
        """Explain what a specific transformation does."""
        if node.node_type != LineageNodeType.TRANSFORMATION:
            return f"Node {node.label} is not a transformation."

        transformation_type = node.transformation_type.value if node.transformation_type else "unknown"
        expression = node.expression or node.label

        # Build simple prompt for single transformation
        prompt = f"""Explain this SQL transformation in one sentence:

Type: {transformation_type}
Expression: {expression}

Explain what this does in plain English for a business user."""

        try:
            response = await asyncio.wait_for(
                self.client.generate(prompt=prompt, temperature=0.2),
                timeout=5.0
            )
            return response.strip()
        except Exception as e:
            logger.warning(f"Failed to explain transformation: {e}")
            return f"{transformation_type.title()} operation on {expression}"

    async def infer_business_context(
        self,
        lineage_graph: LineageGraph,
        schema_context: Optional[Dict] = None,
    ) -> Dict[str, str]:
        """Map technical columns to business terminology."""
        if not lineage_graph.columns_used and not lineage_graph.output_columns:
            return {}

        columns = list(set(lineage_graph.columns_used + lineage_graph.output_columns))

        prompt = f"""Map these database columns to business-friendly names:

Columns: {', '.join(columns[:20])}
Tables: {', '.join(lineage_graph.tables_used[:10])}

Return JSON mapping technical names to business terms:
{{"customer_id": "Customer ID", "total_amt": "Total Amount", "created_at": "Creation Date"}}"""

        try:
            response = await asyncio.wait_for(
                self.client.generate(prompt=prompt, temperature=0.2),
                timeout=5.0
            )
            json_str = extract_json_object(response)
            if json_str:
                return json.loads(json_str)
        except Exception as e:
            logger.debug(f"Failed to infer business context: {e}")

        return {}

    def _extract_deterministic_summary(self, lineage_graph: LineageGraph) -> str:
        """Extract a basic summary from lineage graph without LLM."""
        tables = lineage_graph.tables_used
        outputs = lineage_graph.output_columns

        # Count transformation types
        transformations = [n for n in lineage_graph.nodes if n.node_type == LineageNodeType.TRANSFORMATION]
        aggregations = [t for t in transformations if t.transformation_type == TransformationType.AGGREGATION]
        expressions = [t for t in transformations if t.transformation_type == TransformationType.EXPRESSION]

        parts = []

        if len(tables) == 1:
            parts.append(f"Queries the {tables[0]} table")
        elif len(tables) > 1:
            parts.append(f"Joins {len(tables)} tables ({', '.join(tables[:3])}{'...' if len(tables) > 3 else ''})")

        if aggregations:
            agg_types = set(t.label.split('(')[0].upper() for t in aggregations if '(' in t.label)
            if agg_types:
                parts.append(f"applies {', '.join(agg_types)} aggregation{'s' if len(agg_types) > 1 else ''}")

        if len(outputs) > 0:
            parts.append(f"returns {len(outputs)} column{'s' if len(outputs) > 1 else ''}")

        return ". ".join(parts) + "." if parts else "Extracts data from database."

    def _build_lineage_prompt(
        self,
        lineage_graph: LineageGraph,
        question: Optional[str],
    ) -> str:
        """Build prompt for lineage explanation."""
        # Format transformations
        transformations = []
        for node in lineage_graph.nodes:
            if node.node_type == LineageNodeType.TRANSFORMATION:
                trans_type = node.transformation_type.value if node.transformation_type else "unknown"
                transformations.append(f"  - {node.label} ({trans_type})")

        transformations_formatted = "\n".join(transformations) if transformations else "  (none)"

        # Format column lineage
        column_lineage = []
        for node in lineage_graph.nodes:
            if node.node_type == LineageNodeType.OUTPUT_COLUMN:
                # Find source columns by tracing edges
                sources = self._trace_sources(node.id, lineage_graph)
                if sources:
                    column_lineage.append(f"  - {node.label}: from {', '.join(sources)}")
                else:
                    column_lineage.append(f"  - {node.label}: (computed)")

        column_lineage_formatted = "\n".join(column_lineage) if column_lineage else "  (no output columns)"

        return LINEAGE_NARRATIVE_PROMPT.format(
            question=question or "(not provided)",
            sql=lineage_graph.sql[:500] if len(lineage_graph.sql) > 500 else lineage_graph.sql,
            source_tables=", ".join(lineage_graph.tables_used) or "(none)",
            output_columns=", ".join(lineage_graph.output_columns) or "(none)",
            transformations_formatted=transformations_formatted,
            column_lineage_formatted=column_lineage_formatted,
        )

    def _trace_sources(
        self, node_id: str, graph: LineageGraph, max_depth: int = 50
    ) -> List[str]:
        """Trace back to find source columns for a given node.

        Args:
            node_id: The node ID to trace sources for.
            graph: The lineage graph to traverse.
            max_depth: Maximum recursion depth to prevent stack overflow on deep graphs.
        """
        sources = []
        visited = set()

        def trace(current_id: str, depth: int = 0):
            # Guard against deep recursion and cycles
            if depth > max_depth or current_id in visited:
                return
            visited.add(current_id)

            for edge in graph.edges:
                if edge.target_id == current_id:
                    source_node = next((n for n in graph.nodes if n.id == edge.source_id), None)
                    if source_node:
                        if source_node.node_type == LineageNodeType.SOURCE_COLUMN:
                            table = source_node.table_name or ""
                            col = source_node.column_name or source_node.label
                            sources.append(f"{table}.{col}" if table else col)
                        else:
                            trace(source_node.id, depth + 1)

        trace(node_id)
        return sources[:5]  # Limit to 5 sources

    def _parse_response(
        self,
        response_text: str,
        lineage_graph: LineageGraph,
        deterministic_summary: str,
    ) -> LineageNarrative:
        """Parse LLM response and extract narrative components."""
        try:
            # Try to extract JSON from response using balanced brace matching
            json_str = extract_json_object(response_text)

            if not json_str:
                # No valid JSON found, return fallback
                logger.warning("No valid JSON found in LLM response")
                return self._fallback_narrative(lineage_graph, deterministic_summary)

            data = json.loads(json_str)

            # Validate that we got the expected structure
            summary = data.get("summary", "")
            if not isinstance(summary, str) or len(summary) < 10:
                logger.warning(f"Invalid summary: '{summary[:30] if summary else '(empty)'}...'")
                return self._fallback_narrative(lineage_graph, deterministic_summary)

            # Parse transformations_explained
            transformations_raw = data.get("transformations_explained", [])
            transformations = []
            for t in transformations_raw:
                if isinstance(t, dict):
                    transformations.append(TransformationExplanation(
                        node_id=t.get("node_id", ""),
                        transformation_type=t.get("transformation_type", "unknown"),
                        input_columns=t.get("input_columns", []),
                        output_column=t.get("output_column", ""),
                        explanation=t.get("explanation", ""),
                        business_meaning=t.get("business_meaning"),
                    ))

            # Clean potential_issues
            issues = data.get("potential_issues", [])
            if isinstance(issues, str):
                issues = [issues]
            elif not isinstance(issues, list):
                issues = []
            issues = [i for i in issues if isinstance(i, str) and len(i) > 5]

            return LineageNarrative(
                summary=summary,
                data_flow_description=data.get("data_flow_description", ""),
                column_explanations=data.get("column_explanations", {}),
                transformations_explained=transformations,
                business_context=data.get("business_context", {}),
                potential_issues=issues,
                confidence=float(data.get("confidence", 0.7)),
            )

        except json.JSONDecodeError as e:
            logger.warning(f"JSON decode error: {e}")
            return self._fallback_narrative(lineage_graph, deterministic_summary)
        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")
            return self._fallback_narrative(lineage_graph, deterministic_summary)

    def _fallback_narrative(
        self,
        lineage_graph: LineageGraph,
        summary: str,
    ) -> LineageNarrative:
        """Generate deterministic fallback narrative when LLM fails."""
        # Build column explanations from output columns
        column_explanations = {}
        for node in lineage_graph.nodes:
            if node.node_type == LineageNodeType.OUTPUT_COLUMN:
                sources = self._trace_sources(node.id, lineage_graph)
                if sources:
                    column_explanations[node.label] = f"Derived from {', '.join(sources[:3])}"
                else:
                    column_explanations[node.label] = "Computed value"

        # Build basic data flow description
        flow_parts = []
        if lineage_graph.tables_used:
            flow_parts.append(f"Data flows from {', '.join(lineage_graph.tables_used)}")

        transformations = [n for n in lineage_graph.nodes if n.node_type == LineageNodeType.TRANSFORMATION]
        if transformations:
            trans_types = set(
                n.transformation_type.value if n.transformation_type else "unknown"
                for n in transformations
            )
            flow_parts.append(f"through {', '.join(trans_types)} transformations")

        if lineage_graph.output_columns:
            flow_parts.append(f"to produce {len(lineage_graph.output_columns)} output columns")

        data_flow = " ".join(flow_parts) + "." if flow_parts else "Query processes data."

        return LineageNarrative(
            summary=summary,
            data_flow_description=data_flow,
            column_explanations=column_explanations,
            transformations_explained=[],
            business_context={},
            potential_issues=[],
            confidence=0.4,  # Lower confidence for fallback
        )


# Convenience function for getting narrator instance
async def get_lineage_narrator(
    db_session=None,
    model: Optional[str] = None,
) -> LineageNarrator:
    """Get a configured LineageNarrator instance."""
    from src.llm.ollama_client import get_ollama_client

    client = get_ollama_client()

    # Try to get model router
    model_router = None
    timeout = 15.0

    if db_session:
        try:
            from src.llm.model_router import get_model_router, TaskType
            model_router = await get_model_router(db_session)
            timeout = model_router.get_timeout_for_task(TaskType.LINEAGE_NARRATIVE)
            if not model:
                model = model_router.get_model_for_task(TaskType.LINEAGE_NARRATIVE)
        except (ImportError, AttributeError):
            pass  # Model router not available or missing task type

    return LineageNarrator(
        ollama_client=client,
        model_router=model_router,
        timeout_seconds=timeout,
        model=model,
    )
