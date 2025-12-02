"""
Tool-Using Agent - Uses tools to gather context before generating SQL

This agent enhances SQL generation by:
1. Analyzing the question to identify what information is needed
2. Using tools to explore schema and sample data
3. Building enriched context for the SQL generator
4. Providing better first-attempt accuracy

Integrates with:
- ToolRegistry for tool execution
- MappingCache for caching (from feedback-system-update)
- SchemaCache for schema access (from feedback-system-update)

Part of Phase 3.1: Tool-Using Agent Implementation
"""
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from src.tools.tool_registry import ToolRegistry, get_tool_registry
from src.tools.base import ToolResult, ToolCategory
from src.llm.mapping_cache import get_mapping_cache

logger = logging.getLogger(__name__)


@dataclass
class ToolUsingResult:
    """Result from tool-using agent processing"""
    success: bool
    sql: Optional[str] = None
    explanation: str = ""
    tools_used: List[str] = field(default_factory=list)
    tool_results: List[Dict[str, Any]] = field(default_factory=list)
    enriched_context: str = ""
    confidence: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "sql": self.sql,
            "explanation": self.explanation,
            "tools_used": self.tools_used,
            "tool_results": self.tool_results,
            "enriched_context": self.enriched_context,
            "confidence": self.confidence,
            "error": self.error,
        }


class ToolUsingAgent:
    """
    Agent that uses tools to gather schema information before generating SQL.

    The agent analyzes the user's question, determines what information would
    help generate accurate SQL, uses appropriate tools to gather that info,
    and provides enriched context to the SQL generator.

    Example:
        agent = ToolUsingAgent(sql_generator=generator)
        result = await agent.process(
            question="Show me orders from California",
            schema=schema_str,
            session=db_session,
            schema_inspector=inspector
        )
        # Agent will:
        # 1. search_schema("order") - find orders table
        # 2. find_columns("state") - find state column
        # 3. get_column_values("customers", "state") - see format (CA vs California)
        # 4. Generate SQL with correct format
    """

    def __init__(
        self,
        sql_generator=None,
        tool_registry: Optional[ToolRegistry] = None,
        max_tool_calls: int = 5,
        enable_auto_explore: bool = True,
    ):
        """
        Initialize the tool-using agent.

        Args:
            sql_generator: SQLGenerator instance for generating SQL
            tool_registry: ToolRegistry instance (uses global if not provided)
            max_tool_calls: Maximum number of tool calls per request
            enable_auto_explore: Whether to automatically explore schema
        """
        self.generator = sql_generator
        self.registry = tool_registry or get_tool_registry()
        self.max_tool_calls = max_tool_calls
        self.enable_auto_explore = enable_auto_explore
        self._cache = get_mapping_cache()

    async def process(
        self,
        question: str,
        schema: str,
        database_type: str = "postgresql",
        session=None,
        schema_inspector=None,
        schema_cache=None,
        connection_id: Optional[int] = None,
        use_tools: bool = True,
        trace=None,  # Optional AgentTrace for UI visibility
        context_only: bool = False,  # If True, skip SQL generation and only return enriched context
    ) -> ToolUsingResult:
        """
        Process a question using tools to gather context.

        Args:
            question: Natural language question
            schema: Database schema string (for fallback)
            database_type: Type of database
            session: Database session
            schema_inspector: SchemaInspector instance
            schema_cache: SchemaCache instance
            connection_id: Database connection ID
            use_tools: Whether to use tools (can skip for simple queries)
            trace: Optional AgentTrace to add steps for UI visibility
            context_only: If True, skip SQL generation and only return enriched context (faster for error correction)

        Returns:
            ToolUsingResult with enriched context and optionally SQL
        """
        tools_used = []
        tool_results = []
        enriched_context = ""

        try:
            if use_tools and self.enable_auto_explore:
                # Step 1: Analyze question and plan tool calls
                planned_calls = self._plan_tool_calls(question, schema)

                if planned_calls:
                    logger.info(f"Planning {len(planned_calls)} tool calls for: {question[:50]}...")
                    if trace:
                        trace.add_step(
                            "tool_planning",
                            f"Planning {len(planned_calls)} tool calls to gather schema context",
                            metadata={"planned_tools": [c[0] for c in planned_calls[:self.max_tool_calls]]}
                        )

                # Step 2: Execute tools (up to max_tool_calls)
                context_parts = []
                for tool_name, kwargs in planned_calls[:self.max_tool_calls]:
                    result = await self.registry.execute_tool(
                        tool_name=tool_name,
                        session=session,
                        schema_inspector=schema_inspector,
                        schema_cache=schema_cache,
                        connection_id=connection_id,
                        **kwargs
                    )

                    tools_used.append(tool_name)
                    tool_result_info = {
                        "tool": tool_name,
                        "args": kwargs,
                        "success": result.success,
                        "cache_hit": result.cache_hit,
                        "time_ms": result.execution_time_ms,
                        "data": result.data if result.success else None,
                        "error": result.error,
                    }
                    tool_results.append(tool_result_info)

                    # Add trace step for each tool execution
                    if trace:
                        if result.success:
                            trace.add_step(
                                "tool_success",
                                f"Tool '{tool_name}' executed successfully ({result.execution_time_ms:.1f}ms){' (cached)' if result.cache_hit else ''}",
                                metadata=tool_result_info
                            )
                        else:
                            trace.add_step(
                                "tool_error",
                                f"Tool '{tool_name}' failed: {result.error}",
                                metadata=tool_result_info
                            )

                    if result.success and result.data:
                        context_part = self._format_tool_result(tool_name, result.data)
                        if context_part:
                            context_parts.append(context_part)

                # Step 3: Build enriched context
                if context_parts:
                    enriched_context = self._build_enriched_context(context_parts)
                    if trace:
                        trace.add_step(
                            "tool_context",
                            f"Built enriched context from {len(tools_used)} tools",
                            metadata={"tools_used": tools_used, "context_length": len(enriched_context)}
                        )

            # Step 4: Generate SQL if generator is available (skip if context_only=True)
            sql = None
            explanation = ""

            if self.generator and not context_only:
                # Combine original schema with enriched context
                enhanced_schema = schema
                if enriched_context:
                    enhanced_schema = f"{schema}\n\n{enriched_context}"

                sql_result = await self.generator.generate_sql(
                    question=question,
                    schema=enhanced_schema,
                    database_type=database_type,
                )

                sql = sql_result.get("sql")
                explanation = sql_result.get("explanation", "")

            # Calculate confidence based on tool usage
            confidence = self._calculate_confidence(tools_used, tool_results)

            return ToolUsingResult(
                success=True,
                sql=sql,
                explanation=explanation,
                tools_used=tools_used,
                tool_results=tool_results,
                enriched_context=enriched_context,
                confidence=confidence,
            )

        except Exception as e:
            logger.error(f"Tool-using agent failed: {e}")
            return ToolUsingResult(
                success=False,
                error=str(e),
                tools_used=tools_used,
                tool_results=tool_results,
            )

    async def explore_for_question(
        self,
        question: str,
        session=None,
        schema_inspector=None,
        schema_cache=None,
        connection_id: Optional[int] = None,
        max_depth: int = 2,
    ) -> Dict[str, Any]:
        """
        Deep exploration for a question - gathers comprehensive context.

        This can be called standalone to explore schema before query generation.
        Useful for complex queries that need thorough understanding.

        Args:
            question: Natural language question
            session: Database session
            schema_inspector: SchemaInspector instance
            schema_cache: SchemaCache instance
            connection_id: Database connection ID
            max_depth: How deep to explore (1=basic, 2=moderate, 3=thorough)

        Returns:
            Exploration results dictionary
        """
        exploration = {
            "question": question,
            "discovered_tables": [],
            "discovered_columns": [],
            "value_samples": {},
            "relationships": [],
            "tools_used": [],
        }

        # Extract keywords from question
        keywords = self._extract_keywords(question)

        # First pass: find relevant tables/columns
        for keyword in keywords[:3]:
            result = await self.registry.execute_tool(
                tool_name="search_schema",
                session=session,
                schema_inspector=schema_inspector,
                schema_cache=schema_cache,
                connection_id=connection_id,
                keyword=keyword
            )

            exploration["tools_used"].append("search_schema")

            if result.success and result.data:
                for table in result.data.get("tables", []):
                    if table["name"] not in exploration["discovered_tables"]:
                        exploration["discovered_tables"].append(table["name"])
                for col in result.data.get("columns", []):
                    exploration["discovered_columns"].append(col)

        if max_depth < 2:
            return exploration

        # Second pass: get details on discovered tables
        for table in exploration["discovered_tables"][:3]:
            info_result = await self.registry.execute_tool(
                tool_name="get_table_info",
                session=session,
                schema_inspector=schema_inspector,
                schema_cache=schema_cache,
                connection_id=connection_id,
                table_name=table
            )

            exploration["tools_used"].append("get_table_info")

            if info_result.success and info_result.data:
                exploration["relationships"].extend(
                    info_result.data.get("relationships", [])
                )

        if max_depth < 3:
            return exploration

        # Third pass: sample values for key columns
        value_columns = ["state", "status", "type", "category", "country"]
        for col_info in exploration["discovered_columns"]:
            col_name = col_info.get("column", "").lower()
            if any(vc in col_name for vc in value_columns):
                values_result = await self.registry.execute_tool(
                    tool_name="get_column_values",
                    session=session,
                    schema_inspector=schema_inspector,
                    schema_cache=schema_cache,
                    connection_id=connection_id,
                    table_name=col_info["table"],
                    column_name=col_info["column"],
                    limit=10
                )

                exploration["tools_used"].append("get_column_values")

                if values_result.success and values_result.data:
                    key = f"{col_info['table']}.{col_info['column']}"
                    exploration["value_samples"][key] = values_result.data.get(
                        "distinct_values", []
                    )

        return exploration

    def _plan_tool_calls(
        self,
        question: str,
        schema: str
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Analyze question and plan which tools to call.

        Enhanced heuristics to use more tools proactively:
        - search_schema: Find relevant tables/columns
        - get_table_info: Get detailed table structure
        - get_column_values: Discover actual values for filtering (CA vs California)
        - get_sample_data: Understand data patterns
        - get_relationships: Find foreign keys for joins
        - find_columns: Locate specific column types
        """
        calls = []
        question_lower = question.lower()

        # Extract keywords for searching
        keywords = self._extract_keywords(question)

        # Track tables found for follow-up tool calls
        potential_tables = set()

        # Pattern 1: Search for relevant tables/columns (always do this first)
        if keywords:
            # Search for the most relevant keyword
            calls.append(("search_schema", {"keyword": keywords[0]}))
            potential_tables.add(keywords[0])

            # If multiple keywords, search for a second one
            if len(keywords) > 1:
                calls.append(("search_schema", {"keyword": keywords[1]}))
                potential_tables.add(keywords[1])

        # Pattern 2: Location-based queries - get actual column values!
        location_words = [
            "california", "new york", "texas", "florida", "ny", "ca", "tx",
            "state", "city", "country", "region", "location"
        ]
        location_match = any(loc in question_lower for loc in location_words)
        if location_match:
            calls.append(("find_columns", {"column_name": "state"}))
            # CRITICAL: Get actual values to know if it's "CA" or "California"
            calls.append(("get_column_values", {"table_name": "customers", "column_name": "state", "limit": 10}))
            calls.append(("get_column_values", {"table_name": "orders", "column_name": "state", "limit": 10}))

        # Pattern 3: Status/category queries - get actual values!
        status_words = ["status", "pending", "active", "completed", "shipped", "type", "category"]
        status_match = any(sw in question_lower for sw in status_words)
        if status_match:
            calls.append(("find_columns", {"column_name": "status"}))
            # Get actual status values to know exact enum values
            calls.append(("get_column_values", {"table_name": "orders", "column_name": "status", "limit": 10}))

        # Pattern 4: Get table info for main keywords (detailed structure)
        if keywords and len(keywords) >= 1:
            # Get detailed info for the primary table mentioned
            calls.append(("get_table_info", {"table_name": keywords[0]}))

        # Pattern 5: Get sample data to understand data patterns
        # Useful for understanding date formats, naming conventions, etc.
        if keywords and len(keywords) >= 1:
            calls.append(("get_sample_data", {"table_name": keywords[0], "limit": 5}))

        # Pattern 6: Join queries - get relationships
        join_indicators = ["with", "along with", "and their", "related", "join", "between"]
        if any(ji in question_lower for ji in join_indicators):
            if keywords:
                calls.append(("get_relationships", {"table_name": keywords[0]}))
                # Also get info on the second table if present
                if len(keywords) > 1:
                    calls.append(("get_table_info", {"table_name": keywords[1]}))
                    calls.append(("get_relationships", {"table_name": keywords[1]}))

        # Pattern 7: Count/aggregate queries - sample data helps understand scale
        if any(w in question_lower for w in ["how many", "count", "total", "sum", "average", "max", "min"]):
            if keywords:
                calls.append(("count_rows", {"table_name": keywords[0]}))

        # Pattern 8: Date/time queries - sample data shows date format
        date_words = ["date", "time", "year", "month", "day", "recent", "latest", "oldest", "last"]
        if any(dw in question_lower for dw in date_words):
            if keywords:
                calls.append(("find_columns", {"column_name": "date"}))
                calls.append(("find_columns", {"column_name": "created"}))

        return calls

    def _extract_keywords(self, question: str) -> List[str]:
        """Extract searchable keywords from question."""
        # Common stop words to filter out
        stop_words = {
            "show", "me", "get", "find", "list", "all", "the", "a", "an",
            "from", "where", "with", "by", "in", "on", "and", "or", "to",
            "how", "many", "much", "what", "which", "who", "that", "is",
            "are", "was", "were", "be", "been", "being", "have", "has", "had",
            "do", "does", "did", "will", "would", "could", "should", "may",
            "might", "must", "shall", "can", "need", "dare", "ought", "used",
            "give", "gave", "given", "take", "took", "taken", "make", "made",
            "for", "of", "at", "as", "if", "so", "but", "not", "no", "yes",
            "this", "that", "these", "those", "it", "its", "my", "your",
            "his", "her", "their", "our", "we", "they", "i", "you", "he", "she",
            "select", "query", "display", "fetch", "retrieve",
        }

        # Extract words
        words = re.findall(r'\b[a-z_]+\b', question.lower())

        # Filter and deduplicate
        keywords = []
        seen = set()
        for word in words:
            if word not in stop_words and len(word) > 2 and word not in seen:
                keywords.append(word)
                seen.add(word)

        return keywords

    def _format_tool_result(self, tool_name: str, data: Dict[str, Any]) -> str:
        """Format a tool result for inclusion in context."""
        if tool_name == "search_schema":
            parts = []
            if data.get("tables"):
                table_names = [t["name"] for t in data["tables"][:5]]
                parts.append(f"Found tables: {', '.join(table_names)}")
            if data.get("columns"):
                cols = data["columns"][:5]
                col_info = [f"{c['table']}.{c['column']}" for c in cols]
                parts.append(f"Found columns: {', '.join(col_info)}")
            return "; ".join(parts) if parts else ""

        elif tool_name == "get_table_info":
            table = data.get("table_name", "")
            cols = [c.get("name") for c in data.get("columns", [])][:8]
            return f"Table {table} has columns: {', '.join(cols)}"

        elif tool_name == "find_columns":
            found = data.get("found_in", [])[:5]
            if found:
                locations = [f"{f['table']}.{f['column']}" for f in found]
                return f"Column '{data.get('column_name')}' found in: {', '.join(locations)}"
            return ""

        elif tool_name == "get_column_values":
            values = data.get("distinct_values", [])[:10]
            if values:
                table = data.get("table", "")
                column = data.get("column", "")
                return f"Sample values in {table}.{column}: {values}"
            return ""

        elif tool_name == "get_relationships":
            suggestions = data.get("join_suggestions", [])[:3]
            if suggestions:
                hints = [s.get("sql_hint", "") for s in suggestions]
                return f"Join hints: {'; '.join(hints)}"
            return ""

        return ""

    def _build_enriched_context(self, context_parts: List[str]) -> str:
        """Build the enriched context string for the SQL generator with explicit constraints."""
        if not context_parts:
            return ""

        # Separate positive findings from negative findings
        available = []
        not_available = []

        for part in context_parts:
            if not part:
                continue
            # Check for "not found" or "doesn't exist" patterns
            if any(phrase in part.lower() for phrase in ["not found", "no ", "doesn't exist", "found in: []"]):
                not_available.append(part)
            else:
                available.append(part)

        lines = [
            "=== IMPORTANT: Tool-Discovered Schema Constraints ===",
            "",
        ]

        # List what DOESN'T exist first (critical to avoid errors)
        if not_available:
            lines.append("⚠️  DO NOT USE (these don't exist in the schema):")
            for item in not_available:
                lines.append(f"   ✗ {item}")
            lines.append("")

        # Then list what DOES exist
        if available:
            lines.append("✓  AVAILABLE (use these for your query):")
            for item in available:
                lines.append(f"   • {item}")
            lines.append("")

        lines.append("IMPORTANT: Only use columns/tables marked as AVAILABLE above.")
        lines.append("Attempting to use items marked with ✗ will cause errors.")

        return "\n".join(lines)

    def _calculate_confidence(
        self,
        tools_used: List[str],
        tool_results: List[Dict[str, Any]]
    ) -> float:
        """Calculate confidence score based on tool usage and results."""
        if not tools_used:
            return 0.5  # Default confidence without tools

        # Count successful tools
        successful = sum(1 for r in tool_results if r.get("success", False))
        total = len(tool_results)

        if total == 0:
            return 0.5

        # Base confidence from tool success rate
        success_rate = successful / total
        confidence = 0.5 + (success_rate * 0.3)  # 0.5 to 0.8

        # Bonus for cache hits (indicates repeated successful patterns)
        cache_hits = sum(1 for r in tool_results if r.get("cache_hit", False))
        if cache_hits > 0:
            confidence += 0.05

        # Bonus for finding relevant data
        has_data = any(r.get("data") for r in tool_results)
        if has_data:
            confidence += 0.1

        return min(confidence, 0.95)  # Cap at 0.95

    def get_tools_prompt(self, category: Optional[ToolCategory] = None) -> str:
        """Get formatted tools for LLM prompt."""
        return self.registry.format_tools_for_prompt(category=category)
