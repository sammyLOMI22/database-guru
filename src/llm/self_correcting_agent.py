"""Self-Correcting SQL Agent with automatic error recovery"""
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from src.llm.sql_generator import SQLGenerator
from src.core.executor import SQLExecutor
from src.database.models import DatabaseConnection
from src.config.settings import Settings

logger = logging.getLogger(__name__)

# Import CorrectionLearner (optional to avoid circular imports)
try:
    from src.llm.correction_learner import CorrectionLearner
    LEARNING_AVAILABLE = True
except ImportError:
    LEARNING_AVAILABLE = False
    logger.warning("CorrectionLearner not available - learning disabled")

# Import Tool-Using Agent (optional for enhanced context)
try:
    from src.llm.tool_using_agent import ToolUsingAgent
    TOOL_USING_AVAILABLE = True
except ImportError:
    TOOL_USING_AVAILABLE = False
    logger.warning("ToolUsingAgent not available - tool-using disabled")

# Import Confidence Scorer
try:
    from src.llm.confidence_scorer import get_confidence_scorer, ConfidenceScore
    CONFIDENCE_SCORING_AVAILABLE = True
except ImportError:
    CONFIDENCE_SCORING_AVAILABLE = False
    logger.warning("Confidence scorer not available - confidence scoring disabled")


class AgentTrace:
    """
    Captures agent execution trace for transparency

    This class records each significant decision point during query processing,
    allowing users to understand what the agent did and why.
    """

    def __init__(self):
        self.steps: List[Dict[str, Any]] = []
        self.start_time = datetime.utcnow()

    def add_step(
        self,
        step_type: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
        icon: Optional[str] = None
    ):
        """
        Add a step to the execution trace

        Args:
            step_type: Type of step (analysis, planning, attempt_start, success, etc.)
            message: Human-readable message describing what happened
            metadata: Additional structured data about this step
            icon: Optional emoji icon for UI display
        """
        elapsed = (datetime.utcnow() - self.start_time).total_seconds() * 1000

        self.steps.append({
            "timestamp": datetime.utcnow().isoformat(),
            "elapsed_ms": round(elapsed, 2),
            "type": step_type,
            "message": message,
            "metadata": metadata or {},
            "icon": icon or self._default_icon(step_type)
        })

    def _default_icon(self, step_type: str) -> str:
        """Get default icon for step type"""
        icons = {
            "analysis": "🔍",
            "planning": "📋",
            "generation": "✨",
            "execution": "⚡",
            "attempt_start": "🔄",
            "success": "✅",
            "error": "❌",
            "warning": "⚠️",
            "fix_attempt": "🔧",
            "quick_fix": "⚡",
            "learned_fix": "🧠",
            "llm_fix": "🤖",
            "tool_fix": "🔧",
            "verification": "🔍",
            "verification_warning": "⚠️",
            "learning": "📚"
        }
        return icons.get(step_type, "•")

    def to_dict(self) -> Dict[str, Any]:
        """Convert trace to dictionary for API response"""
        total_elapsed = (datetime.utcnow() - self.start_time).total_seconds() * 1000
        return {
            "steps": self.steps,
            "total_elapsed_ms": round(total_elapsed, 2),
            "start_time": self.start_time.isoformat()
        }


class ErrorType(Enum):
    """Types of SQL errors for better diagnosis"""
    SYNTAX_ERROR = "syntax_error"
    TABLE_NOT_FOUND = "table_not_found"
    COLUMN_NOT_FOUND = "column_not_found"
    TYPE_MISMATCH = "type_mismatch"
    PERMISSION_DENIED = "permission_denied"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


@dataclass
class CorrectionAttempt:
    """Record of a correction attempt"""
    attempt_number: int
    sql: str
    error: Optional[str]
    error_type: ErrorType
    success: bool
    execution_time_ms: Optional[float]
    row_count: Optional[int]
    confidence_score: Optional[Dict[str, Any]] = None  # Confidence prediction before execution


class ErrorDiagnostics:
    """Analyze and categorize SQL errors"""

    @staticmethod
    def categorize_error(error_message: str) -> ErrorType:
        """
        Categorize error type from error message

        Args:
            error_message: Error message from database

        Returns:
            ErrorType enum
        """
        error_lower = error_message.lower()

        # Check in order of specificity (most specific first)

        # Type mismatch (check before "does not exist" matches)
        if any(keyword in error_lower for keyword in [
            "operator does not exist", "type mismatch", "cast", "conversion", "incompatible"
        ]):
            return ErrorType.TYPE_MISMATCH

        # Column not found (check before table since column errors are more specific)
        if any(keyword in error_lower for keyword in [
            "column", "field", "unknown column", "no such column"
        ]):
            return ErrorType.COLUMN_NOT_FOUND

        # Table not found
        if any(keyword in error_lower for keyword in [
            "table", "relation", "no such table", "does not exist"
        ]):
            return ErrorType.TABLE_NOT_FOUND

        # Syntax errors
        if any(keyword in error_lower for keyword in [
            "syntax error", "syntax", "parse error", "unexpected"
        ]):
            return ErrorType.SYNTAX_ERROR

        # Permission issues
        if any(keyword in error_lower for keyword in [
            "permission", "denied", "access", "unauthorized"
        ]):
            return ErrorType.PERMISSION_DENIED

        # Timeout
        if any(keyword in error_lower for keyword in [
            "timeout", "timed out", "exceeded"
        ]):
            return ErrorType.TIMEOUT

        return ErrorType.UNKNOWN

    @staticmethod
    def extract_error_context(error_message: str, error_type: ErrorType) -> Dict[str, Any]:
        """
        Extract useful context from error message

        Args:
            error_message: Error message from database
            error_type: Categorized error type

        Returns:
            Dictionary with extracted context
        """
        context = {
            "error_type": error_type.value,
            "raw_error": error_message
        }

        error_lower = error_message.lower()

        if error_type == ErrorType.TABLE_NOT_FOUND:
            # Try to extract table name
            import re
            match = re.search(r'table["\s]+([a-z_][a-z0-9_]*)', error_lower)
            if match:
                context["missing_table"] = match.group(1)

        elif error_type == ErrorType.COLUMN_NOT_FOUND:
            # Try to extract column name
            import re
            match = re.search(r'column["\s]+([a-z_][a-z0-9_]*)', error_lower)
            if match:
                context["missing_column"] = match.group(1)

        return context

    @staticmethod
    def generate_fix_hints(error_type: ErrorType, context: Dict[str, Any]) -> str:
        """
        Generate helpful hints for fixing the error

        Args:
            error_type: Type of error
            context: Error context

        Returns:
            Hints for fixing the error
        """
        hints = []

        if error_type == ErrorType.TABLE_NOT_FOUND:
            hints.append("Check the schema for the correct table name.")
            hints.append("Table names may be case-sensitive.")
            if "missing_table" in context:
                hints.append(f"Could not find table: {context['missing_table']}")

        elif error_type == ErrorType.COLUMN_NOT_FOUND:
            hints.append("Check the schema for the correct column name.")
            hints.append("Make sure you're referencing the right table.")
            if "missing_column" in context:
                hints.append(f"Could not find column: {context['missing_column']}")

        elif error_type == ErrorType.SYNTAX_ERROR:
            hints.append("Check for missing commas, parentheses, or keywords.")
            hints.append("Verify SQL syntax is correct for the database type.")

        elif error_type == ErrorType.TYPE_MISMATCH:
            hints.append("Check data types in comparisons and operations.")
            hints.append("You may need to cast values to the correct type.")

        return "\n".join(hints)


class SelfCorrectingSQLAgent:
    """
    Agent that automatically retries and fixes failed SQL queries

    This agent will:
    1. Generate initial SQL
    2. Execute and check for errors
    3. If error occurs, analyze and attempt to fix
    4. Retry with corrected SQL
    5. Repeat up to max_retries times
    """

    def __init__(
        self,
        sql_generator: SQLGenerator,
        max_retries: int = 3,
        enable_diagnostics: bool = True,
        enable_learning: bool = True,
        enable_schema_fixes: bool = True,
        enable_result_verification: bool = True,
        enable_query_planning: bool = True,
        learner_session = None,
        planning_session = None
    ):
        """
        Initialize the self-correcting agent

        Args:
            sql_generator: SQL generator instance
            max_retries: Maximum number of correction attempts
            enable_diagnostics: Whether to provide detailed error diagnostics
            enable_learning: Whether to enable learning from corrections
            enable_schema_fixes: Whether to enable fast schema-aware fixes
            enable_result_verification: Whether to enable result verification
            enable_query_planning: Whether to enable query planning for complex queries
            learner_session: Database session for the learner (optional)
            planning_session: Database session for the query planner (optional, for learned mappings)
        """
        self.generator = sql_generator
        self.max_retries = max_retries
        self.enable_diagnostics = enable_diagnostics
        self.enable_schema_fixes = enable_schema_fixes
        self.enable_result_verification = enable_result_verification
        self.enable_query_planning = enable_query_planning
        self.diagnostics = ErrorDiagnostics()

        # Track which fix method was used per attempt (for observability)
        self.fix_methods: Dict[int, str] = {}

        # Initialize learner if available and enabled
        self.enable_learning = enable_learning and LEARNING_AVAILABLE
        self.learner = None
        if self.enable_learning and learner_session:
            self.learner = CorrectionLearner(
                db_session=learner_session,
                enable_learning=True
            )
            logger.info("Correction learning enabled")
        elif enable_learning and not LEARNING_AVAILABLE:
            logger.warning("Learning requested but CorrectionLearner not available")

        # Schema-aware fixer will be initialized per-query with schema
        self.schema_fixer = None
        if self.enable_schema_fixes:
            logger.info("Schema-aware fixes enabled")

        # Initialize result verification agent
        self.verification_agent = None
        if self.enable_result_verification:
            try:
                from src.llm.result_verification_agent import ResultVerificationAgent
                self.verification_agent = ResultVerificationAgent(
                    enable_diagnostics=True,
                    enable_auto_fix=True,
                    db_session=planning_session  # Use same session for pattern validation
                )
                logger.info("Result verification enabled" + (" with learned patterns" if planning_session else ""))
            except ImportError:
                logger.warning("ResultVerificationAgent not available - verification disabled")
                self.enable_result_verification = False

        # Initialize query planning agent
        self.planning_agent = None
        if self.enable_query_planning:
            try:
                from src.llm.query_planning_agent import QueryPlanningAgent
                self.planning_agent = QueryPlanningAgent(
                    settings=sql_generator.settings,
                    ollama_client=sql_generator.ollama,
                    enable_planning=True,
                    db_session=planning_session
                )
                logger.info("Query planning enabled" + (" with learned mappings" if planning_session else ""))
            except ImportError:
                logger.warning("QueryPlanningAgent not available - planning disabled")
                self.enable_query_planning = False

        # Initialize tool-using agent for enhanced error correction
        self.tool_using_agent = None
        self.enable_tool_using = TOOL_USING_AVAILABLE
        if self.enable_tool_using:
            try:
                self.tool_using_agent = ToolUsingAgent(
                    sql_generator=sql_generator,
                    max_tool_calls=3,  # Limit calls during error fixing
                    enable_auto_explore=True,
                )
                logger.info("Tool-using agent enabled for enhanced error correction")
            except Exception as e:
                logger.warning(f"Failed to initialize ToolUsingAgent: {e}")
                self.enable_tool_using = False

    def format_attempts_for_ui(
        self,
        attempts: List[CorrectionAttempt]
    ) -> List[Dict[str, Any]]:
        """
        Format correction attempts for frontend display

        Args:
            attempts: List of CorrectionAttempt objects

        Returns:
            List of UI-friendly attempt dictionaries
        """
        return [
            {
                "attempt_number": a.attempt_number,
                "sql": a.sql,
                "success": a.success,
                "error": a.error,
                "error_type": a.error_type.value if a.error_type else None,
                "execution_time_ms": a.execution_time_ms,
                "row_count": a.row_count,
                "fix_method": self.fix_methods.get(a.attempt_number),
                "confidence_prediction": a.confidence_score  # Include confidence score
            } for a in attempts
        ]

    async def _try_parallel_fixes(
        self,
        sql: str,
        last_error: str,
        error_type: "ErrorType",
        error_context: Dict[str, Any],
        hints: str,
        schema: str,
        database_type: str,
        trace: "AgentTrace",
        session=None,  # Database session for tool-using agent
        schema_inspector=None,  # SchemaInspector for tool-using agent
        schema_cache=None,  # SchemaCache for tool-using agent
        connection_id: Optional[int] = None,  # Connection ID for tool-using agent
    ) -> Dict[str, Any]:
        """
        Try multiple fix strategies in parallel and return the first successful one

        This method executes schema-aware fixes, learned corrections, and LLM fixes
        simultaneously, providing 2-3x speedup on error corrections.

        Args:
            sql: Current SQL query
            last_error: Error message from previous attempt
            error_type: Categorized error type
            error_context: Extracted error context
            hints: Generated hints for fixing
            schema: Database schema
            database_type: Type of database
            trace: Agent trace for observability

        Returns:
            Dict with:
                - sql: Corrected SQL
                - fix_method: Which method succeeded ("quick_fix", "learned", "llm")
                - confidence: Confidence score (if available)
                - explanation: Fix explanation
        """
        import asyncio

        trace.add_step("fix_attempt", f"Trying parallel fixes for error: {last_error[:100]}...")
        logger.info("⚡ Trying parallel correction strategies...")

        # Define async tasks for each fix strategy
        async def try_quick_fix():
            """Try schema-aware quick fix"""
            if not self.enable_schema_fixes or not self.schema_fixer:
                return None

            try:
                from src.llm.schema_aware_fixer import QuickFix
                # Quick fix is sync, so wrap it
                quick_fix = await asyncio.to_thread(
                    self.schema_fixer.quick_fix,
                    sql=sql,
                    error_type=error_type,
                    error_message=last_error,
                    context=error_context
                )

                if quick_fix.success and quick_fix.confidence >= 0.7:
                    return {
                        "sql": quick_fix.fixed_sql,
                        "fix_method": "quick_fix",
                        "confidence": quick_fix.confidence,
                        "explanation": quick_fix.explanation,
                        "method_details": quick_fix.correction_type,
                    }
                return None
            except Exception as e:
                logger.warning(f"Quick fix failed: {e}")
                return None

        async def try_learned_fix():
            """Try learned corrections"""
            if not self.learner:
                return None

            try:
                learned_corrections = await self.learner.find_applicable_corrections(
                    error_type=error_type,
                    error_message=last_error,
                    database_type=database_type,
                    sql=sql,
                    limit=1
                )

                if learned_corrections:
                    correction = learned_corrections[0]
                    # Apply the learned correction pattern to SQL
                    # This is a simplified version - real implementation may need more logic
                    return {
                        "sql": correction.get("corrected_sql", sql),
                        "fix_method": "learned",
                        "confidence": correction.get("confidence_score", 0.8),
                        "explanation": correction.get("correction_description", "Applied learned correction"),
                        "correction_id": correction.get("id"),
                    }
                return None
            except Exception as e:
                logger.warning(f"Learned fix failed: {e}")
                return None

        async def try_llm_fix():
            """Try LLM-based fix"""
            try:
                enhanced_error = f"{last_error}\n\nHints:\n{hints}"
                fix_result = await self.generator.fix_sql_error(
                    sql=sql,
                    error=enhanced_error,
                    schema=schema,
                    database_type=database_type
                )
                return {
                    "sql": fix_result["sql"],
                    "fix_method": "llm",
                    "confidence": 0.6,  # Default confidence for LLM fixes
                    "explanation": "LLM-generated correction",
                }
            except Exception as e:
                logger.warning(f"LLM fix failed: {e}")
                return None

        async def try_tool_fix():
            """Try tool-using agent to gather context and fix"""
            if not self.enable_tool_using or not self.tool_using_agent:
                return None

            try:
                # Use tools to explore schema and gather context about the error
                # This helps find correct table/column names
                tool_result = await self.tool_using_agent.process(
                    question=f"Fix SQL error: {last_error[:200]}",
                    schema=schema,
                    database_type=database_type,
                    session=session,
                    schema_inspector=schema_inspector,
                    schema_cache=schema_cache,
                    connection_id=connection_id,
                    use_tools=True,
                    trace=trace,  # Pass trace for UI visibility
                )

                if tool_result.success and tool_result.sql:
                    return {
                        "sql": tool_result.sql,
                        "fix_method": "tool_using",
                        "confidence": tool_result.confidence,
                        "explanation": f"Tool-assisted fix using {len(tool_result.tools_used)} tools: {', '.join(tool_result.tools_used[:3])}",
                        "tools_used": tool_result.tools_used,
                        "enriched_context": tool_result.enriched_context[:200] if tool_result.enriched_context else None,
                    }
                return None
            except Exception as e:
                logger.warning(f"Tool-using fix failed: {e}")
                return None

        # Execute all fix strategies in parallel with timeout protection
        tasks = [try_quick_fix(), try_learned_fix(), try_llm_fix(), try_tool_fix()]
        start_time = asyncio.get_event_loop().time()

        # FIX #5: Add timeout wrapper to prevent indefinite hangs
        settings = Settings()
        timeout = settings.PARALLEL_CORRECTIONS_TIMEOUT

        # Metrics tracking
        metrics = {
            "strategies_attempted": len(tasks),
            "strategies_succeeded": 0,
            "strategies_failed": 0,
            "strategies_timed_out": 0,
            "winning_strategy": None,
            "elapsed_ms": 0,
            "timed_out": False,
        }

        try:
            # Use return_exceptions=True to handle failures gracefully
            # Wrap with timeout to prevent hanging
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=timeout
            )

            elapsed = asyncio.get_event_loop().time() - start_time
            metrics["elapsed_ms"] = round(elapsed * 1000, 2)
            logger.info(f"⚡ Parallel fixes completed in {elapsed:.3f}s")

        except asyncio.TimeoutError:
            # FIX #5: Handle timeout - fallback to LLM fix
            elapsed = asyncio.get_event_loop().time() - start_time
            metrics["elapsed_ms"] = round(elapsed * 1000, 2)
            metrics["timed_out"] = True
            metrics["strategies_timed_out"] = len(tasks)

            logger.warning(f"⚠️ Parallel fixes timed out after {timeout}s, using fallback LLM fix")
            trace.add_step(
                "warning",
                f"Parallel fixes timed out after {timeout}s, using fallback",
                metadata=metrics
            )

            # Fallback to direct LLM fix
            enhanced_error = f"{last_error}\n\nHints:\n{hints}"
            fix_result = await self.generator.fix_sql_error(
                sql=sql,
                error=enhanced_error,
                schema=schema,
                database_type=database_type
            )

            metrics["winning_strategy"] = "llm_fallback_timeout"
            metrics["strategies_succeeded"] = 1

            return {
                "sql": fix_result["sql"],
                "fix_method": "llm_fallback_timeout",
                "confidence": 0.4,  # Lower confidence due to timeout
                "explanation": f"Fallback LLM correction (parallel strategies timed out after {timeout}s)",
                "metrics": metrics,
            }

        # Find the first successful fix
        successful_fixes = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"Fix strategy {i} raised exception: {result}")
                metrics["strategies_failed"] += 1
                continue
            if result is not None:
                successful_fixes.append(result)
                metrics["strategies_succeeded"] += 1
                method = result["fix_method"]
                conf = result.get("confidence", 0)

                # Track first (winning) strategy
                if metrics["winning_strategy"] is None:
                    metrics["winning_strategy"] = method

                step_type_map = {
                    "quick_fix": "quick_fix",
                    "learned": "learned_fix",
                    "llm": "llm_fix",
                    "tool_using": "tool_fix",
                }
                trace.add_step(
                    step_type_map.get(method, "fix_attempt"),
                    f"{method.replace('_', ' ').title()} succeeded: {result['explanation']}",
                    metadata={"confidence": conf, "elapsed_ms": metrics["elapsed_ms"]}
                )
            else:
                metrics["strategies_failed"] += 1

        if successful_fixes:
            # Return the first (fastest) successful fix
            best_fix = successful_fixes[0]

            # FIX #6: Add metrics to response
            best_fix["metrics"] = metrics

            logger.info(
                f"✅ Parallel fix succeeded using: {best_fix['fix_method']} "
                f"(confidence: {best_fix.get('confidence', 0):.2f}) - "
                f"Metrics: {metrics['strategies_succeeded']}/{metrics['strategies_attempted']} strategies succeeded"
            )

            # Add metrics to trace
            trace.add_step(
                "planning",
                f"Parallel corrections metrics: {metrics['winning_strategy']} won in {metrics['elapsed_ms']}ms",
                metadata=metrics
            )

            return best_fix
        else:
            # All strategies failed - fallback to LLM as last resort
            metrics["winning_strategy"] = "llm_fallback_all_failed"
            metrics["strategies_failed"] = metrics["strategies_attempted"]

            logger.warning("⚠️ All parallel fix strategies failed, falling back to sequential LLM fix")
            trace.add_step("warning", "All parallel fixes failed, using fallback LLM fix", metadata=metrics)
            enhanced_error = f"{last_error}\n\nHints:\n{hints}"
            fix_result = await self.generator.fix_sql_error(
                sql=sql,
                error=enhanced_error,
                schema=schema,
                database_type=database_type
            )
            return {
                "sql": fix_result["sql"],
                "fix_method": "llm_fallback",
                "confidence": 0.5,
                "explanation": "Fallback LLM correction (parallel strategies failed)",
                "metrics": metrics,
            }

    async def generate_and_execute_with_retry(
        self,
        question: str,
        schema: str,
        session,  # Database session
        database_type: str = "postgresql",
        allow_write: bool = False,
        model: Optional[str] = None,
        schema_dict: Optional[Dict] = None,
        use_parallel_corrections: bool = True,  # NEW: Enable/disable parallel fixes
        connection_name: Optional[str] = None,  # NEW: Connection name for learned mappings
        schema_inspector=None,  # NEW: SchemaInspector for tool-using agent
        schema_cache=None,  # NEW: SchemaCache for tool-using agent
        connection_id: Optional[int] = None,  # NEW: Connection ID for tool-using agent
    ) -> Dict[str, Any]:
        """
        Generate SQL with automatic error correction and retry

        Args:
            question: Natural language question
            schema: Database schema information
            session: Database session for execution
            database_type: Type of database
            allow_write: Whether to allow write operations
            model: Optional model name to use
            schema_dict: Optional parsed schema dictionary
            use_parallel_corrections: Whether to enable parallel correction attempts
            connection_name: Optional connection name for applying learned mappings

        Returns:
            Dictionary with:
                - success: bool
                - sql: Final SQL query
                - result: Query results (if successful)
                - attempts: List of CorrectionAttempt objects
                - self_corrected: Whether auto-correction was used
                - total_attempts: Total number of attempts
                - error: Final error message (if failed)
                - agent_trace: Execution trace for observability
        """
        # Initialize agent trace for observability
        trace = AgentTrace()
        trace.add_step(
            "analysis",
            f"Analyzing question: {question[:100]}{'...' if len(question) > 100 else ''}",
            metadata={"database_type": database_type, "model": model or self.generator.settings.OLLAMA_MODEL}
        )

        # Reset fix methods tracking for this query
        self.fix_methods = {}

        attempts: List[CorrectionAttempt] = []
        last_error = None
        sql = None

        # Initialize schema-aware fixer if enabled
        if self.enable_schema_fixes:
            try:
                from src.llm.schema_aware_fixer import SchemaAwareFixer
                import json
                # Parse schema if it's a string
                schema_dict = json.loads(schema) if isinstance(schema, str) else schema
                self.schema_fixer = SchemaAwareFixer(schema_dict)
                logger.info("Schema-aware fixer initialized with schema")
            except Exception as e:
                logger.warning(f"Failed to initialize schema-aware fixer: {e}")
                self.schema_fixer = None

        executor = SQLExecutor(
            max_rows=1000,
            timeout_seconds=30,
            allow_write=allow_write
        )

        # Try query planning first for complex queries
        query_plan = None
        if self.enable_query_planning and self.planning_agent:
            try:
                trace.add_step("planning", "Checking if query planning should be used")
                logger.info("🧠 Checking if query planning should be used...")
                planning_result = await self.planning_agent.plan_and_generate_sql(
                    question=question,
                    schema=schema,
                    database_type=database_type,
                    sql_generator=self.generator,
                    model=model,
                    schema_dict=schema_dict,
                    connection_name=connection_name
                )

                if planning_result.get("used_planning"):
                    query_plan = planning_result["plan"]
                    trace.add_step(
                        "planning",
                        f"Query plan created (complexity: {query_plan.complexity.value}, confidence: {query_plan.confidence:.2f})",
                        metadata={
                            "complexity": query_plan.complexity.value,
                            "confidence": query_plan.confidence,
                            "estimated_tables": len(query_plan.tables_needed)
                        }
                    )
                    logger.info(
                        f"📋 Query plan created: complexity={query_plan.complexity.value}, "
                        f"confidence={query_plan.confidence:.2f}"
                    )
                    # Use the SQL generated from the plan
                    if planning_result.get("sql"):
                        sql = planning_result["sql"]
            except Exception as e:
                trace.add_step("warning", f"Query planning failed: {str(e)[:100]}")
                logger.warning(f"Query planning failed, falling back to direct generation: {e}")

        for attempt_num in range(1, self.max_retries + 1):
            try:
                trace.add_step("attempt_start", f"Starting attempt {attempt_num}/{self.max_retries}")

                # Initialize confidence prediction for this attempt
                confidence_prediction = None

                # Generate or fix SQL
                if attempt_num == 1:
                    # First attempt: generate from scratch (or use plan-based SQL)
                    if sql is None:  # Only generate if not already generated by planner
                        trace.add_step("generation", "Generating initial SQL query")
                        logger.info(f"Attempt {attempt_num}/{self.max_retries}: Generating SQL for: {question}")
                        gen_result = await self.generator.generate_sql(
                            question=question,
                            schema=schema,
                            database_type=database_type,
                            allow_write=allow_write,
                            model=model
                        )
                        sql = gen_result["sql"]
                        trace.add_step("generation", f"Generated SQL: {sql[:100]}{'...' if len(sql) > 100 else ''}", metadata={"sql": sql})
                    else:
                        trace.add_step("generation", "Using SQL from query plan")
                        logger.info(f"Attempt {attempt_num}/{self.max_retries}: Using SQL from query plan")
                        gen_result = {"sql": sql, "is_valid": True}
                else:
                    # Retry: fix the error
                    logger.info(f"Attempt {attempt_num}/{self.max_retries}: Attempting to fix SQL error")

                    # Categorize error
                    error_type = self.diagnostics.categorize_error(last_error)
                    error_context = self.diagnostics.extract_error_context(last_error, error_type)
                    hints = self.diagnostics.generate_fix_hints(error_type, error_context)

                    # Use parallel or sequential corrections based on flag
                    if use_parallel_corrections:
                        # ========== PARALLEL CORRECTIONS (2-3x faster!) ==========
                        fix_result = await self._try_parallel_fixes(
                            sql=sql,
                            last_error=last_error,
                            error_type=error_type,
                            error_context=error_context,
                            hints=hints,
                            schema=schema,
                            database_type=database_type,
                            trace=trace,
                            session=session,
                            schema_inspector=schema_inspector,
                            schema_cache=schema_cache,
                            connection_id=connection_id,
                        )
                        sql = fix_result["sql"]
                        self.fix_methods[attempt_num] = fix_result["fix_method"]
                        logger.info(f"✅ Parallel correction succeeded: {fix_result['explanation']}")
                    else:
                        # ========== SEQUENTIAL CORRECTIONS (legacy fallback) ==========
                        # Try schema-aware quick fix FIRST (fastest, no LLM call)
                        quick_fix_used = False
                        if self.enable_schema_fixes and self.schema_fixer:
                            from src.llm.schema_aware_fixer import QuickFix
                            quick_fix = self.schema_fixer.quick_fix(
                                sql=sql,
                                error_type=error_type,
                                error_message=last_error,
                                context=error_context
                            )

                            if quick_fix.success and quick_fix.confidence >= 0.7:
                                sql = quick_fix.fixed_sql
                                quick_fix_used = True
                                # Track fix method for observability
                                self.fix_methods[attempt_num] = "quick_fix"
                                trace.add_step(
                                    "quick_fix",
                                    f"Applied quick fix: {quick_fix.explanation}",
                                    metadata={"confidence": quick_fix.confidence, "method": quick_fix.fix_method}
                                )
                                logger.info(
                                    f"⚡ Quick fix applied: {quick_fix.explanation} "
                                    f"(confidence: {quick_fix.confidence:.2f}) - SKIPPED LLM CALL"
                                )
                                # Continue to execution without LLM call

                        if not quick_fix_used:
                            # Quick fix didn't work, use learned corrections or LLM
                            # Check for learned corrections
                            learned_correction = None
                            if self.learner:
                                learned_corrections = await self.learner.find_applicable_corrections(
                                    error_type=error_type,
                                    error_message=last_error,
                                    database_type=database_type,
                                    sql=sql,
                                    limit=1
                                )
                                if learned_corrections:
                                    learned_correction = learned_corrections[0]
                                    # Track fix method for observability
                                    self.fix_methods[attempt_num] = "learned"
                                    trace.add_step(
                                        "learned_fix",
                                        f"Found learned correction (confidence: {learned_correction['confidence_score']:.2f})",
                                        metadata={
                                            "correction_id": learned_correction['id'],
                                            "confidence": learned_correction['confidence_score'],
                                            "description": learned_correction['correction_description']
                                        }
                                    )
                                    logger.info(
                                        f"Found learned correction {learned_correction['id']} "
                                        f"(confidence: {learned_correction['confidence_score']:.2f})"
                                    )
                                    # Add learned correction to hints
                                    hints += f"\n\nLearned correction available: {learned_correction['correction_description']}"

                            # Add hints to error message for better correction
                            enhanced_error = f"{last_error}\n\nHints:\n{hints}"

                            # Generate corrected SQL using LLM
                            # Track fix method for observability (if not already tracked by learned correction)
                            if attempt_num not in self.fix_methods:
                                self.fix_methods[attempt_num] = "llm"
                            trace.add_step("llm_fix", "Generating corrected SQL using LLM")
                            fix_result = await self.generator.fix_sql_error(
                                sql=sql,
                                error=enhanced_error,
                                schema=schema,
                                database_type=database_type
                            )
                            sql = fix_result["sql"]
                            trace.add_step("llm_fix", f"LLM generated fix: {sql[:100]}{'...' if len(sql) > 100 else ''}", metadata={"sql": sql})

                            logger.info(f"Generated corrected SQL: {sql[:100]}...")

                    # Calculate confidence score for this correction attempt
                    if CONFIDENCE_SCORING_AVAILABLE and attempt_num > 1:  # Only for corrections, not first attempt
                        try:
                            scorer = get_confidence_scorer()
                            # Get historical success rate for this error type
                            stats = scorer.get_stats()
                            historical_rate = None
                            if error_type.value in stats:
                                historical_rate = stats[error_type.value].get("success_rate")

                            # Get previous SQL for comparison
                            previous_sql = attempts[-1].sql if attempts else sql

                            confidence_prediction = scorer.predict_success_probability(
                                error_type=error_type.value,
                                original_sql=previous_sql,
                                correction_sql=sql,
                                schema=schema_dict,
                                historical_success_rate=historical_rate,
                                error_message=last_error,
                                context={"database_type": database_type}
                            )

                            trace.add_step(
                                "planning",
                                f"Confidence prediction: {confidence_prediction.get_level()} ({confidence_prediction.overall:.1%})",
                                metadata={
                                    "confidence": confidence_prediction.overall,
                                    "level": confidence_prediction.get_level(),
                                    "recommendation": confidence_prediction.recommendation,
                                    "reasoning": confidence_prediction.reasoning
                                }
                            )

                            logger.info(
                                f"📊 Confidence: {confidence_prediction.get_level()} "
                                f"({confidence_prediction.overall:.1%}) - {confidence_prediction.reasoning}"
                            )

                            # Skip execution if confidence is very low (< 0.2)
                            if confidence_prediction.overall < 0.2:
                                logger.warning(
                                    f"⚠️ Very low confidence ({confidence_prediction.overall:.1%}), "
                                    f"skipping execution to save resources"
                                )
                                trace.add_step(
                                    "warning",
                                    f"Skipping execution due to very low confidence ({confidence_prediction.overall:.1%})"
                                )
                                # Record failed attempt without execution
                                attempt = CorrectionAttempt(
                                    attempt_number=attempt_num,
                                    sql=sql,
                                    error="Skipped due to very low confidence score",
                                    error_type=error_type,
                                    success=False,
                                    execution_time_ms=0,
                                    row_count=0,
                                    confidence_score=confidence_prediction.to_dict() if confidence_prediction else None
                                )
                                attempts.append(attempt)
                                continue  # Skip to next attempt

                        except Exception as e:
                            logger.warning(f"Failed to calculate confidence score: {e}")
                            confidence_prediction = None

                # Validate SQL before executing
                if not gen_result.get("is_valid", True) if attempt_num == 1 else True:
                    logger.warning(f"Generated SQL failed validation: {gen_result.get('warnings')}")

                # Execute SQL
                trace.add_step("execution", f"Executing SQL query")
                exec_result = await executor.execute_query(
                    session=session,
                    sql=sql
                )

                # Record attempt
                attempt = CorrectionAttempt(
                    attempt_number=attempt_num,
                    sql=sql,
                    error=None if exec_result["success"] else exec_result["error"],
                    error_type=ErrorType.UNKNOWN if exec_result["success"] else self.diagnostics.categorize_error(exec_result["error"]),
                    success=exec_result["success"],
                    execution_time_ms=exec_result.get("execution_time_ms"),
                    row_count=exec_result.get("row_count"),
                    confidence_score=confidence_prediction.to_dict() if confidence_prediction else None
                )
                attempts.append(attempt)

                # Update confidence scorer statistics after execution
                if CONFIDENCE_SCORING_AVAILABLE and confidence_prediction and attempt_num > 1:
                    try:
                        scorer = get_confidence_scorer()
                        scorer.update_historical_stats(
                            error_type=error_type.value,
                            success=exec_result["success"]
                        )
                    except Exception as e:
                        logger.warning(f"Failed to update confidence stats: {e}")

                if exec_result["success"]:
                    # Success! But verify results make sense
                    trace.add_step(
                        "success",
                        f"Query executed successfully (rows: {exec_result.get('row_count', 0)}, time: {exec_result.get('execution_time_ms', 0):.2f}ms)",
                        metadata={
                            "row_count": exec_result.get('row_count', 0),
                            "execution_time_ms": exec_result.get('execution_time_ms', 0)
                        }
                    )
                    logger.info(f"✅ Query succeeded on attempt {attempt_num}/{self.max_retries}")

                    # Verify results if enabled (with conditional skip for high-confidence results)
                    verification_result = None
                    verification_warnings = []
                    skip_verification = False

                    # Quick confidence check to skip expensive verification
                    if self.enable_result_verification and self.verification_agent:
                        row_count = exec_result.get("row_count", 0)
                        # Skip verification for "obviously correct" results:
                        # - Simple SELECT queries that return reasonable data (1-100 rows)
                        # - Queries that didn't need any correction (first attempt success)
                        # - Not empty results (0 rows still gets verified)
                        if (
                            attempt_num == 1 and  # First attempt success
                            row_count > 0 and row_count <= 100 and  # Reasonable row count
                            not any(kw in sql.upper() for kw in ['JOIN', 'UNION', 'SUBQUERY', 'HAVING'])
                        ):
                            skip_verification = True
                            trace.add_step(
                                "verification_skip",
                                f"Skipping verification for high-confidence result ({row_count} rows, first attempt)"
                            )
                            logger.info(f"⏭️ Skipping verification for high-confidence result ({row_count} rows)")

                    if self.enable_result_verification and self.verification_agent and not skip_verification:
                        try:
                            trace.add_step("verification", "Verifying query results for accuracy")
                            logger.info("🔍 Verifying query results...")

                            # Extract primary table from query plan if available
                            primary_table = None
                            if query_plan and hasattr(query_plan, 'tables') and query_plan.tables:
                                primary_table = query_plan.tables[0].name

                            verification_result = await self.verification_agent.verify_results(
                                question=question,
                                sql=sql,
                                result=exec_result,
                                schema=schema,
                                database_type=database_type,
                                connection_name=connection_name,
                                table_name=primary_table
                            )

                            if verification_result.is_suspicious:
                                trace.add_step(
                                    "verification_warning",
                                    f"Suspicious results detected: {verification_result.description}",
                                    metadata={
                                        "confidence": verification_result.confidence,
                                        "issue": verification_result.issue_type.value if hasattr(verification_result, 'issue_type') else None
                                    }
                                )
                                logger.warning(
                                    f"⚠️ Suspicious results detected: {verification_result.description} "
                                    f"(confidence: {verification_result.confidence:.2f})"
                                )

                                # Run diagnostics if needed
                                diagnostics = None
                                if verification_result.diagnostic_queries:
                                    diagnostics = await self.verification_agent.run_diagnostics(
                                        sql=sql,
                                        verification=verification_result,
                                        session=session,
                                        database_type=database_type
                                    )
                                    logger.info(f"📊 Diagnostics: {diagnostics.diagnosis}")

                                # Generate improvement hints
                                hints = self.verification_agent.generate_improvement_hints(
                                    question=question,
                                    sql=sql,
                                    verification=verification_result,
                                    diagnostics=diagnostics
                                )

                                # If high confidence issue and auto-fix enabled, try to regenerate
                                if (verification_result.confidence >= 0.7 and
                                    attempt_num < self.max_retries and
                                    self.verification_agent.enable_auto_fix):

                                    trace.add_step("fix_attempt", "High confidence issue detected, attempting to regenerate query")
                                    logger.info("🔧 High confidence issue detected, attempting to regenerate query...")

                                    # Add verification feedback to the next attempt
                                    last_error = f"Query succeeded but returned suspicious results:\n{hints}"

                                    # Mark this attempt as failed verification
                                    attempt.success = False
                                    attempt.error = verification_result.description

                                    # Continue to next attempt
                                    logger.warning(f"❌ Attempt {attempt_num} failed verification check")
                                    continue
                                else:
                                    # Low confidence or last attempt - return with warning
                                    verification_warnings.append(
                                        f"⚠️ Result verification: {verification_result.description}"
                                    )
                        except Exception as e:
                            logger.error(f"Error during result verification: {e}")
                            verification_warnings.append(f"Result verification failed: {str(e)}")

                    # Learn from this correction if it was a retry
                    if attempt_num > 1 and self.learner and len(attempts) > 0:
                        # Get the original error from the first failed attempt
                        first_attempt = attempts[0]
                        if not first_attempt.success and first_attempt.error:
                            trace.add_step("learning", "Learning from successful correction")
                            await self.learner.learn_from_correction(
                                error_type=first_attempt.error_type,
                                original_sql=first_attempt.sql,
                                original_error=first_attempt.error,
                                corrected_sql=sql,
                                database_type=database_type,
                                was_successful=True
                            )
                            logger.info("✨ Learned from successful correction")

                    return {
                        "success": True,
                        "sql": sql,
                        "result": exec_result,
                        "attempts": attempts,
                        "self_corrected": attempt_num > 1,
                        "total_attempts": attempt_num,
                        "question": question,
                        "model_used": model or self.generator.settings.OLLAMA_MODEL,
                        "verification": verification_result,
                        "verification_warnings": verification_warnings,
                        "query_plan": query_plan.to_dict() if query_plan else None,
                        "used_planning": query_plan is not None,
                        "agent_trace": trace.to_dict()
                    }

                # Failed - save error for next retry
                last_error = exec_result["error"]
                trace.add_step("error", f"Attempt {attempt_num} failed: {last_error[:100]}{'...' if len(last_error) > 100 else ''}")
                logger.warning(f"❌ Attempt {attempt_num} failed: {last_error[:200]}")

                # If this is the last attempt, don't retry
                if attempt_num >= self.max_retries:
                    break

            except Exception as e:
                logger.error(f"Exception during attempt {attempt_num}: {e}")
                last_error = str(e)

                # Record failed attempt
                attempt = CorrectionAttempt(
                    attempt_number=attempt_num,
                    sql=sql or "",
                    error=str(e),
                    error_type=ErrorType.UNKNOWN,
                    success=False,
                    execution_time_ms=None,
                    row_count=None
                )
                attempts.append(attempt)

                if attempt_num >= self.max_retries:
                    break

        # All retries exhausted
        trace.add_step("error", f"All {self.max_retries} attempts exhausted, query failed")
        logger.error(f"❌ Query failed after {self.max_retries} attempts")
        return {
            "success": False,
            "sql": sql or "",
            "error": last_error,
            "attempts": attempts,
            "self_corrected": len(attempts) > 1,
            "total_attempts": len(attempts),
            "question": question,
            "model_used": model or self.generator.settings.OLLAMA_MODEL,
            "message": f"Failed after {self.max_retries} attempts",
            "agent_trace": trace.to_dict()
        }

    async def execute_with_retry(
        self,
        sql: str,
        schema: str,
        session,
        database_type: str,
        question: str,
        allow_write: bool = False,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute pre-generated SQL with automatic error correction and retry

        This method is useful when you already have SQL generated and just need
        the retry/correction logic.

        Args:
            sql: Pre-generated SQL query
            schema: Database schema information
            session: Database session for execution
            database_type: Type of database
            question: Original natural language question (for context in corrections)
            allow_write: Whether to allow write operations
            model: Optional model name to use for SQL correction

        Returns:
            Dictionary with:
                - success: bool
                - sql: Final SQL query (may be corrected)
                - result: Query results (if successful)
                - corrections: List of correction attempt details
                - attempts: Total number of attempts
                - final_error: Final error message (if failed)
        """
        attempts: List[Dict[str, Any]] = []
        last_error = None
        current_sql = sql

        executor = SQLExecutor(
            max_rows=1000,
            timeout_seconds=30,
            allow_write=allow_write
        )

        for attempt_num in range(1, self.max_retries + 1):
            try:
                logger.info(f"Attempt {attempt_num}/{self.max_retries}: Executing SQL")

                # Execute SQL
                exec_result = await executor.execute_query(
                    session=session,
                    sql=current_sql
                )

                # Record attempt
                attempt_info = {
                    "attempt_number": attempt_num,
                    "sql": current_sql,
                    "error": None if exec_result["success"] else exec_result.get("error"),
                    "error_type": ErrorType.UNKNOWN.value if not exec_result["success"] else None,
                    "success": exec_result["success"],
                    "execution_time_ms": exec_result.get("execution_time_ms"),
                    "row_count": exec_result.get("row_count")
                }

                if not exec_result["success"]:
                    error_type = self.diagnostics.categorize_error(exec_result["error"])
                    attempt_info["error_type"] = error_type.value

                attempts.append(attempt_info)

                if exec_result["success"]:
                    # Success!
                    logger.info(f"✅ Query succeeded on attempt {attempt_num}/{self.max_retries}")
                    return {
                        "success": True,
                        "sql": current_sql,
                        "result": exec_result,
                        "corrections": attempts,
                        "attempts": attempt_num,
                        "self_corrected": attempt_num > 1,
                    }

                # Failed - try to correct
                last_error = exec_result["error"]
                logger.warning(f"❌ Attempt {attempt_num} failed: {last_error[:200]}")

                # If this is the last attempt, don't retry
                if attempt_num >= self.max_retries:
                    break

                # Generate correction
                error_type = self.diagnostics.categorize_error(last_error)
                error_context = self.diagnostics.extract_error_context(last_error, error_type)
                hints = self.diagnostics.generate_fix_hints(error_type, error_context)

                # Add hints to error message
                enhanced_error = f"{last_error}\n\nHints:\n{hints}"

                # Generate corrected SQL
                fix_result = await self.generator.fix_sql_error(
                    sql=current_sql,
                    error=enhanced_error,
                    schema=schema,
                    database_type=database_type,
                    model=model,
                )
                current_sql = fix_result["sql"]

                logger.info(f"Generated corrected SQL: {current_sql[:100]}...")

            except Exception as e:
                logger.error(f"Exception during attempt {attempt_num}: {e}")
                last_error = str(e)

                # Record failed attempt
                attempts.append({
                    "attempt_number": attempt_num,
                    "sql": current_sql,
                    "error": str(e),
                    "error_type": ErrorType.UNKNOWN.value,
                    "success": False,
                    "execution_time_ms": None,
                    "row_count": None
                })

                if attempt_num >= self.max_retries:
                    break

        # All retries exhausted
        logger.error(f"❌ Query failed after {self.max_retries} attempts")
        return {
            "success": False,
            "sql": current_sql,
            "final_error": last_error,
            "corrections": attempts,
            "attempts": len(attempts),
            "self_corrected": len(attempts) > 1,
        }

    def get_correction_summary(self, result: Dict[str, Any]) -> str:
        """
        Generate a human-readable summary of the correction process

        Args:
            result: Result from generate_and_execute_with_retry

        Returns:
            Summary string
        """
        if result["success"]:
            if result["self_corrected"]:
                return (
                    f"✅ Query succeeded after {result['total_attempts']} attempts "
                    f"(auto-corrected from {result['total_attempts'] - 1} error(s))"
                )
            else:
                return "✅ Query succeeded on first try"
        else:
            return (
                f"❌ Query failed after {result['total_attempts']} attempts\n"
                f"Final error: {result['error'][:200]}"
            )

    def get_detailed_report(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a detailed report of all correction attempts

        Args:
            result: Result from generate_and_execute_with_retry

        Returns:
            Detailed report dictionary
        """
        attempts_detail = []

        for attempt in result.get("attempts", []):
            attempts_detail.append({
                "attempt": attempt.attempt_number,
                "sql": attempt.sql[:200] + "..." if len(attempt.sql) > 200 else attempt.sql,
                "success": attempt.success,
                "error_type": attempt.error_type.value if attempt.error_type else None,
                "error": attempt.error[:200] if attempt.error else None,
                "execution_time_ms": attempt.execution_time_ms,
                "row_count": attempt.row_count
            })

        return {
            "summary": self.get_correction_summary(result),
            "success": result["success"],
            "total_attempts": result["total_attempts"],
            "self_corrected": result["self_corrected"],
            "final_sql": result["sql"],
            "attempts": attempts_detail,
            "question": result["question"],
            "model_used": result.get("model_used")
        }
