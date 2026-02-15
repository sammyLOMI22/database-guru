"""Self-Correcting SQL Agent with automatic error recovery"""
import logging
from typing import Optional, Dict, Any, List, TYPE_CHECKING
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from src.llm.sql_generator import SQLGenerator

# Avoid circular import
if TYPE_CHECKING:
    from src.llm.quality_profile import QualityProfile
from sqlalchemy.ext.asyncio import AsyncSession
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

# Import Semantic Validator (Phase 3)
try:
    from src.llm.sql_semantic_validator import SQLSemanticValidator, SemanticMismatchType
    SEMANTIC_VALIDATION_AVAILABLE = True
except ImportError:
    SEMANTIC_VALIDATION_AVAILABLE = False
    logger.warning("Semantic validator not available - semantic validation disabled")

# Import Query Template Engine (Phase: Small Model Optimization)
try:
    from src.llm.query_templates import TemplateEngine, TemplateMatch
    TEMPLATE_ENGINE_AVAILABLE = True
except ImportError:
    TEMPLATE_ENGINE_AVAILABLE = False
    logger.debug("Query template engine not available")

# Import Query Preprocessor (Phase: Small Model Optimization)
try:
    from src.llm.query_preprocessor import QueryPreprocessor, PreprocessedQuery
    PREPROCESSOR_AVAILABLE = True
except ImportError:
    PREPROCESSOR_AVAILABLE = False
    logger.debug("Query preprocessor not available")


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
    def generate_fix_hints(
        error_type: ErrorType,
        context: Dict[str, Any],
        schema_dict: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate helpful hints for fixing the error

        Args:
            error_type: Type of error
            context: Error context
            schema_dict: Optional schema dictionary for schema-aware hints

        Returns:
            Hints for fixing the error
        """
        hints = []

        if error_type == ErrorType.TABLE_NOT_FOUND:
            hints.append("Check the schema for the correct table name.")
            hints.append("Table names may be case-sensitive.")
            if "missing_table" in context:
                hints.append(f"Could not find table: {context['missing_table']}")
            if schema_dict and "tables" in schema_dict:
                available = ", ".join(schema_dict["tables"].keys())
                hints.append(f"Available tables: {available}")

        elif error_type == ErrorType.COLUMN_NOT_FOUND:
            missing_col = context.get("missing_column", "")
            hints.append("The column may be on a DIFFERENT table than you're using.")
            hints.append("Check which table actually has this column in the schema.")

            if missing_col:
                hints.append(f"Could not find column: {missing_col}")

            # Schema-aware: find which tables actually have this column
            if schema_dict and "tables" in schema_dict and missing_col:
                tables_with_col = []
                for table_name, table_info in schema_dict["tables"].items():
                    for col in table_info.get("columns", []):
                        if col.get("name", "").lower() == missing_col.lower():
                            tables_with_col.append(table_name)
                if tables_with_col:
                    hints.append(f"IMPORTANT: '{missing_col}' column is on table(s): {', '.join(tables_with_col)}")
                    hints.append(f"You need to JOIN to {tables_with_col[0]} to use this column!")
                else:
                    # Column doesn't exist at all
                    hints.append(f"Column '{missing_col}' does not exist in any table.")

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
        planning_session = None,
        quality_profile: Optional["QualityProfile"] = None,
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
            quality_profile: Optional quality profile for controlling agent behavior
        """
        self.generator = sql_generator
        self.quality_profile = quality_profile

        # Apply quality profile settings if provided
        if quality_profile:
            self.max_retries = quality_profile.max_retries
            enable_result_verification = quality_profile.enable_result_verification
            logger.info(
                f"Applied quality profile: {quality_profile.level.value} "
                f"(retries={self.max_retries}, verification={enable_result_verification})"
            )
        else:
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
        # Respect quality profile's enable_tool_exploration if provided
        self.tool_using_agent = None
        tool_exploration_enabled = TOOL_USING_AVAILABLE
        if quality_profile:
            tool_exploration_enabled = quality_profile.enable_tool_exploration and TOOL_USING_AVAILABLE
        self.enable_tool_using = tool_exploration_enabled
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
        schema_dict: Optional[Dict] = None,  # For WHERE column validation
        db: Optional[AsyncSession] = None,
        query_history_id: Optional[int] = None,
        chat_session_id: Optional[str] = None,
        chat_message_id: Optional[int] = None,
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
                # Pass correction hints as separate parameter (addresses PR review)
                fix_result = await self.generator.fix_sql_error(
                    sql=sql,
                    error=last_error,
                    schema=schema,
                    database_type=database_type,
                    correction_hints=hints,  # Explicit hints forwarding
                    schema_dict=schema_dict,  # Pass for WHERE column validation
                    db=db,
                    query_history_id=query_history_id,
                    chat_session_id=chat_session_id,
                    chat_message_id=chat_message_id,
                )
                fix_token_info = fix_result.get("token_info", {})
                return {
                    "sql": fix_result["sql"],
                    "fix_method": "llm",
                    "confidence": 0.6,  # Default confidence for LLM fixes
                    "explanation": "LLM-generated correction",
                    "token_info": fix_token_info,
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
                    schema_dict=schema_dict,  # Pass for WHERE column validation
                )

                if tool_result.success and tool_result.sql:
                    return {
                        "sql": tool_result.sql,
                        "fix_method": "tool_using",
                        "confidence": tool_result.confidence,
                        "explanation": f"Tool-assisted fix using {len(tool_result.tools_used)} tools: {', '.join(tool_result.tools_used[:3])}",
                        "tools_used": tool_result.tools_used,
                        "enriched_context": tool_result.enriched_context[:200] if tool_result.enriched_context else None,
                        "token_info": tool_result.token_info or {},
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
            fix_result = await self.generator.fix_sql_error(
                sql=sql,
                error=last_error,
                schema=schema,
                database_type=database_type,
                correction_hints=hints,  # Explicit hints forwarding (addresses PR review)
                schema_dict=schema_dict,  # Pass for WHERE column validation
                db=db,
                query_history_id=query_history_id,
                chat_session_id=chat_session_id,
                chat_message_id=chat_message_id,
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
                step_metadata = {"confidence": conf, "elapsed_ms": metrics["elapsed_ms"]}
                if result.get("token_info"):
                    step_metadata.update(result["token_info"])
                trace.add_step(
                    step_type_map.get(method, "fix_attempt"),
                    f"{method.replace('_', ' ').title()} succeeded: {result['explanation']}",
                    metadata=step_metadata
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
            fix_result = await self.generator.fix_sql_error(
                sql=sql,
                error=last_error,
                schema=schema,
                database_type=database_type,
                correction_hints=hints,  # Explicit hints forwarding (addresses PR review)
                schema_dict=schema_dict,  # Pass for WHERE column validation
                db=db,
                query_history_id=query_history_id,
                chat_session_id=chat_session_id,
                chat_message_id=chat_message_id,
            )
            return {
                "sql": fix_result["sql"],
                "fix_method": "llm_fallback",
                "confidence": 0.5,
                "explanation": "Fallback LLM correction (parallel strategies failed)",
                "metrics": metrics,
                "token_info": fix_result.get("token_info", {}),
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
        row_limit: int = 100,  # NEW: Maximum rows to return
        db: Optional[AsyncSession] = None,
        query_history_id: Optional[int] = None,
        chat_session_id: Optional[str] = None,
        chat_message_id: Optional[int] = None,
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
            row_limit: Maximum rows to return (default: 100)

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

        # === TEMPLATE MATCHING: Bypass LLM for simple query patterns ===
        # Check if the question matches a known template (e.g., "show all customers", "count products")
        # This is part of Small Model Optimization to reduce LLM calls for simple queries
        if TEMPLATE_ENGINE_AVAILABLE and schema_dict:
            # Check if template matching is enabled via quality profile
            enable_templates = True
            if self.quality_profile:
                enable_templates = getattr(self.quality_profile, 'enable_query_templates', True)

            if enable_templates:
                try:
                    template_engine = TemplateEngine(
                        schema_dict,
                        default_limit=row_limit,
                        database_type=database_type
                    )
                    template_match = template_engine.try_match(question)

                    if template_match:
                        trace.add_step(
                            "template_match",
                            f"Matched template: {template_match.template_type.value} (confidence: {template_match.confidence:.2f})",
                            metadata={
                                "template": template_match.template_type.value,
                                "confidence": template_match.confidence,
                                "table": template_match.matched_table,
                                "sql": template_match.sql,
                            },
                            icon="⚡"
                        )
                        logger.info(
                            f"⚡ Template matched: {template_match.template_type.value} "
                            f"-> {template_match.sql[:80]}... (bypassing LLM)"
                        )

                        # Execute the template SQL directly
                        executor = SQLExecutor(
                            max_rows=row_limit,
                            timeout_seconds=30,
                            allow_write=allow_write
                        )
                        exec_result = await executor.execute(session, template_match.sql)

                        if exec_result["success"]:
                            trace.add_step(
                                "success",
                                f"Template query executed successfully ({exec_result.get('row_count', 0)} rows)",
                                icon="✅"
                            )
                            logger.info(
                                f"✅ Template query succeeded: {exec_result.get('row_count', 0)} rows "
                                f"(bypassed LLM entirely)"
                            )
                            return {
                                "success": True,
                                "sql": template_match.sql,
                                "result": exec_result,
                                "attempts": [],
                                "self_corrected": False,
                                "total_attempts": 0,
                                "question": question,
                                "model_used": "template",  # Indicate no LLM was used
                                "template_matched": True,
                                "template_type": template_match.template_type.value,
                                "template_confidence": template_match.confidence,
                                "agent_trace": trace.to_dict(),
                                "verification_warnings": [],
                                "used_planning": False,
                                "query_plan": None,
                            }
                        else:
                            # Template SQL failed - log and fall through to normal processing
                            trace.add_step(
                                "warning",
                                f"Template SQL failed: {exec_result.get('error', 'Unknown error')[:100]}",
                                icon="⚠️"
                            )
                            logger.warning(
                                f"Template SQL failed, falling back to LLM: {exec_result.get('error', '')[:100]}"
                            )
                            # Continue with normal flow

                except Exception as e:
                    logger.debug(f"Template matching failed (continuing with LLM): {e}")

        # Reset fix methods tracking for this query
        self.fix_methods = {}

        attempts: List[CorrectionAttempt] = []
        last_error = None
        sql = None

        # Initialize schema-aware fixer if enabled
        if self.enable_schema_fixes:
            try:
                from src.llm.schema_aware_fixer import SchemaAwareFixer
                # Use passed schema_dict if available, otherwise it stays None
                # (we don't try to parse formatted schema text as JSON)
                if schema_dict:
                    self.schema_fixer = SchemaAwareFixer(schema_dict)
                    logger.info("Schema-aware fixer initialized with schema_dict")
                else:
                    logger.debug("No schema_dict available, schema-aware fixer not initialized")
                    self.schema_fixer = None
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
                    connection_name=connection_name,
                    quality_profile=self.quality_profile,
                    db=db,
                    query_history_id=query_history_id,
                    chat_session_id=chat_session_id,
                    chat_message_id=chat_message_id,
                )

                if planning_result.get("used_planning"):
                    query_plan = planning_result["plan"]
                    planning_token_info = planning_result.get("token_info", {})
                    trace.add_step(
                        "planning",
                        f"Query plan created (complexity: {query_plan.complexity.value}, confidence: {query_plan.confidence:.2f})",
                        metadata={
                            "complexity": query_plan.complexity.value,
                            "confidence": query_plan.confidence,
                            "estimated_tables": len(query_plan.tables),
                            **planning_token_info,
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

        # === PRE-GENERATION: Query Intent Classification ===
        # Detect impossible queries BEFORE wasting an LLM call
        intent_result = None
        if schema_dict and self.quality_profile and self.quality_profile.enable_intent_classification:
            try:
                from src.llm.query_intent_classifier import QueryIntentClassifier, QueryIntent

                classifier = QueryIntentClassifier(schema_dict)
                intent_result = classifier.classify(question)

                trace.add_step(
                    "intent_classification",
                    f"Query intent: {intent_result.intent.value} (confidence: {intent_result.confidence:.2f})",
                    metadata={
                        "intent": intent_result.intent.value,
                        "confidence": intent_result.confidence,
                        "entities_found": len(intent_result.extracted_entities),
                        "tables_required": list(intent_result.required_tables),
                        "can_answer": intent_result.can_answer(),
                    }
                )
                logger.info(
                    f"🎯 Query intent: {intent_result.intent.value} "
                    f"(confidence: {intent_result.confidence:.2f}, "
                    f"entities: {len(intent_result.extracted_entities)})"
                )

                # Early exit for IMPOSSIBLE queries
                if not intent_result.can_answer():
                    logger.info(f"❌ Query cannot be answered: {intent_result.impossible_reason}")
                    trace.add_step(
                        "cannot_answer",
                        f"Pre-generation validation: {intent_result.impossible_reason}",
                        metadata={"suggestions": intent_result.suggestions}
                    )
                    return {
                        "success": False,
                        "sql": "",
                        "result": None,
                        "error": f"Cannot answer this query. {intent_result.impossible_reason}",
                        "attempts": [],
                        "self_corrected": False,
                        "total_attempts": 0,
                        "agent_trace": trace.to_dict(),
                        "cannot_answer": True,
                        "cannot_answer_reason": intent_result.impossible_reason,
                        "suggestions": intent_result.suggestions,
                        "intent_classification": intent_result.to_dict(),
                    }

            except Exception as e:
                logger.warning(f"Intent classification failed (continuing): {e}")
                trace.add_step("warning", f"Intent classification skipped: {str(e)[:100]}")

        # === SCHEMA FILTERING: Reduce schema to relevant tables only ===
        # This addresses PR review: "For large databases, passing full schema hits context limits"
        # Only filter if we have a schema_dict and more than 10 tables
        filtered_schema = schema
        if schema_dict and len(schema_dict.get("tables", {})) > 10:
            try:
                from src.core.schema_inspector import SchemaInspector
                inspector = SchemaInspector()
                filtered_schema_dict = inspector.filter_schema_for_query(
                    schema_dict, question, include_neighbors=True, max_neighbor_hops=1
                )
                # Only use filtered schema if it's smaller but still has tables
                if (0 < len(filtered_schema_dict.get("tables", {})) < len(schema_dict.get("tables", {}))):
                    filtered_schema = inspector.format_schema_for_llm(filtered_schema_dict)
                    trace.add_step(
                        "schema_filtering",
                        f"Filtered schema: {len(filtered_schema_dict['tables'])} tables "
                        f"(from {len(schema_dict['tables'])} total)",
                        metadata={
                            "filtered_tables": list(filtered_schema_dict["tables"].keys()),
                            "original_count": len(schema_dict["tables"]),
                            "filtered_count": len(filtered_schema_dict["tables"]),
                        }
                    )
                    logger.info(
                        f"📉 Schema filtered: {len(filtered_schema_dict['tables'])} tables "
                        f"from {len(schema_dict['tables'])} total"
                    )
                    # Update schema for generation
                    schema = filtered_schema
            except Exception as e:
                logger.debug(f"Schema filtering skipped: {e}")

        for attempt_num in range(1, self.max_retries + 1):
            try:
                trace.add_step("attempt_start", f"Starting attempt {attempt_num}/{self.max_retries}")

                # Initialize confidence prediction for this attempt
                confidence_prediction = None

                # Generate or fix SQL
                if attempt_num == 1:
                    # First attempt: generate from scratch (or use plan-based SQL)
                    if sql is None:  # Only generate if not already generated by planner
                        # === LOCATION PREPROCESSING: Normalize locations before LLM ===
                        # This is part of Small Model Optimization to help smaller models
                        # handle location queries correctly (e.g., "California" -> "CA")
                        question_for_llm = question
                        preprocessed_context = ""
                        if PREPROCESSOR_AVAILABLE and schema_dict:
                            enable_preprocessing = True
                            if self.quality_profile:
                                enable_preprocessing = getattr(
                                    self.quality_profile, 'enable_location_preprocessing', True
                                )

                            if enable_preprocessing:
                                try:
                                    preprocessor = QueryPreprocessor(schema_dict)
                                    preprocessed = preprocessor.preprocess(question)

                                    if preprocessed.detected_locations:
                                        question_for_llm = preprocessed.normalized
                                        preprocessed_context = preprocessed.enhanced_context
                                        trace.add_step(
                                            "preprocessing",
                                            f"Normalized locations: {', '.join(f'{l.original}→{l.normalized}' for l in preprocessed.detected_locations)}",
                                            metadata={
                                                "original": question,
                                                "normalized": question_for_llm,
                                                "locations": [l.original for l in preprocessed.detected_locations],
                                                "db_format": preprocessed.location_format_hint,
                                            },
                                            icon="🗺️"
                                        )
                                        logger.info(
                                            f"🗺️ Preprocessed query: {len(preprocessed.detected_locations)} locations normalized "
                                            f"(format: {preprocessed.location_format_hint})"
                                        )
                                except Exception as e:
                                    logger.debug(f"Query preprocessing failed (continuing): {e}")

                        # NEW: Use tool-using agent to gather schema context BEFORE generation
                        enhanced_schema = schema
                        if self.enable_tool_using and self.tool_using_agent:
                            try:
                                trace.add_step("tool_exploration", "Using tools to explore schema before SQL generation")
                                logger.info("🔧 Using tool-using agent to gather schema context...")
                                tool_result = await self.tool_using_agent.process(
                                    question=question,
                                    schema=schema,
                                    database_type=database_type,
                                    session=session,
                                    schema_inspector=schema_inspector,
                                    schema_cache=schema_cache,
                                    connection_id=connection_id,
                                    use_tools=True,
                                    trace=trace,
                                    schema_dict=schema_dict,  # Pass for WHERE column validation
                                )
                                if tool_result.success and tool_result.enriched_context:
                                    enhanced_schema = f"{schema}\n\n{tool_result.enriched_context}"
                                    tool_ctx_meta = {
                                        "tools_used": tool_result.tools_used,
                                        "context_length": len(tool_result.enriched_context),
                                        "confidence": tool_result.confidence,
                                    }
                                    if tool_result.token_info:
                                        tool_ctx_meta.update(tool_result.token_info)
                                    trace.add_step(
                                        "tool_context",
                                        f"Gathered context using {len(tool_result.tools_used)} tools: {', '.join(tool_result.tools_used[:5])}",
                                        metadata=tool_ctx_meta
                                    )
                                    logger.info(f"✅ Tool exploration complete: {len(tool_result.tools_used)} tools used")
                            except Exception as e:
                                logger.warning(f"Tool exploration failed (continuing without): {e}")
                                trace.add_step("warning", f"Tool exploration failed: {str(e)[:100]}")

                        # Add preprocessed context to enhanced schema if available
                        if preprocessed_context:
                            enhanced_schema = f"{enhanced_schema}\n\n{preprocessed_context}"

                        trace.add_step("generation", "Generating initial SQL query")
                        logger.info(f"Attempt {attempt_num}/{self.max_retries}: Generating SQL for: {question_for_llm}")
                        gen_result = await self.generator.generate_sql(
                            question=question_for_llm,  # Use preprocessed question with normalized locations
                            schema=enhanced_schema,  # Use enhanced schema with tool context + preprocessing hints
                            database_type=database_type,
                            allow_write=allow_write,
                            model=model,
                            quality_profile=self.quality_profile,
                            schema_dict=schema_dict,  # Pass for LocationMapper
                            row_limit=row_limit,  # Pass row limit to LLM
                            intent_result=intent_result,  # Phase 1: Intent-driven prompting
                            db=db,
                            query_history_id=query_history_id,
                            chat_session_id=chat_session_id,
                            chat_message_id=chat_message_id,
                        )

                        # Check if LLM says query cannot be answered
                        if gen_result.get("cannot_answer"):
                            reason = gen_result.get("cannot_answer_reason", "Query cannot be answered with current schema")
                            trace.add_step("cannot_answer", f"Schema limitation: {reason}")
                            logger.info(f"Query cannot be answered: {reason}")
                            return {
                                "success": False,
                                "sql": "",
                                "result": None,
                                "error": f"This query cannot be answered with the current database schema. {reason}",
                                "attempts": attempts,
                                "self_corrected": False,
                                "total_attempts": attempt_num,
                                "agent_trace": trace.to_dict(),
                                "cannot_answer": True,
                                "cannot_answer_reason": reason,
                            }

                        sql = gen_result["sql"]
                        gen_token_info = gen_result.get("token_info", {})
                        trace.add_step("generation", f"Generated SQL: {sql[:100]}{'...' if len(sql) > 100 else ''}", metadata={"sql": sql, **gen_token_info})

                        # Validate that all tables in SQL exist in schema
                        if schema_dict and 'tables' in schema_dict:
                            from src.llm.sql_generator import SQLValidator
                            schema_tables = list(schema_dict['tables'].keys())
                            tables_valid, missing_tables = SQLValidator.validate_tables_exist(sql, schema_tables)
                            if not tables_valid:
                                # Tables don't exist - treat as error for retry
                                last_error = (
                                    f"SQL references non-existent tables: {', '.join(missing_tables)}. "
                                    f"Available tables are: {', '.join(schema_tables)}. "
                                    f"Regenerate using ONLY these tables."
                                )
                                logger.warning(f"Table validation failed: {last_error}")
                                trace.add_step("validation", f"Table validation failed: {missing_tables}")
                                continue  # Skip to next attempt

                            # NEW: Validate column qualification in multi-table queries
                            # This catches ambiguous column references before execution
                            try:
                                from src.llm.sql_semantic_validator import SQLSemanticValidator
                                semantic_validator = SQLSemanticValidator()
                                qual_result = semantic_validator.validate_column_qualification(sql, schema_dict)
                                if not qual_result.is_valid:
                                    # Ambiguous columns detected - provide hints for regeneration
                                    hints_text = qual_result.get_regeneration_hints()
                                    last_error = (
                                        f"Ambiguous column references in multi-table query. "
                                        f"{hints_text}"
                                    )
                                    logger.warning(f"Column qualification validation failed: {qual_result.mismatch_details}")
                                    trace.add_step(
                                        "validation",
                                        f"Column qualification failed: {qual_result.mismatch_details}",
                                        metadata={"suggestions": qual_result.suggestions}
                                    )
                                    continue  # Skip to next attempt for regeneration

                                # NEW: Validate WHERE clause columns exist in queried tables
                                # This catches: SELECT * FROM orders WHERE state = 'NY'
                                # when state is in customers table, not orders
                                where_result = semantic_validator.validate_where_columns_exist(sql, schema_dict)
                                if not where_result.is_valid:
                                    hints_text = where_result.get_regeneration_hints()
                                    last_error = (
                                        f"WHERE clause references column not in queried tables. "
                                        f"{hints_text}"
                                    )
                                    logger.warning(f"WHERE column validation failed: {where_result.mismatch_details}")
                                    trace.add_step(
                                        "validation",
                                        f"WHERE column validation failed: {where_result.mismatch_details}",
                                        metadata={"suggestions": where_result.suggestions}
                                    )
                                    continue  # Skip to next attempt for regeneration
                            except Exception as e:
                                logger.debug(f"Column validation check skipped: {e}")
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
                    # Pass schema_dict for schema-aware hints (addresses PR review)
                    hints = self.diagnostics.generate_fix_hints(error_type, error_context, schema_dict)

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
                            schema_dict=schema_dict,  # Pass for WHERE column validation
                            db=db,
                            query_history_id=query_history_id,
                            chat_session_id=chat_session_id,
                            chat_message_id=chat_message_id,
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

                            # Generate corrected SQL using LLM
                            # Track fix method for observability (if not already tracked by learned correction)
                            if attempt_num not in self.fix_methods:
                                self.fix_methods[attempt_num] = "llm"
                            trace.add_step("llm_fix", "Generating corrected SQL using LLM")
                            fix_result = await self.generator.fix_sql_error(
                                sql=sql,
                                error=last_error,
                                schema=schema,
                                database_type=database_type,
                                correction_hints=hints,  # Explicit hints forwarding (addresses PR review)
                                schema_dict=schema_dict,  # Pass for WHERE column validation
                                db=db,
                                query_history_id=query_history_id,
                                chat_session_id=chat_session_id,
                                chat_message_id=chat_message_id,
                            )
                            sql = fix_result["sql"]
                            fix_token_info = fix_result.get("token_info", {})
                            trace.add_step("llm_fix", f"LLM generated fix: {sql[:100]}{'...' if len(sql) > 100 else ''}", metadata={"sql": sql, **fix_token_info})

                            logger.info(f"Generated corrected SQL: {sql[:100]}...")

                # Validate fixed SQL before execution (applies to all retry paths)
                if schema_dict and attempt_num > 1:
                    # First validate that all tables exist (same as first attempt)
                    from src.llm.sql_generator import SQLValidator
                    schema_tables = list(schema_dict['tables'].keys())
                    tables_valid, missing_tables = SQLValidator.validate_tables_exist(sql, schema_tables)
                    if not tables_valid:
                        last_error = (
                            f"SQL still references non-existent tables: {', '.join(missing_tables)}. "
                            f"Available tables are: {', '.join(schema_tables)}. "
                            f"Regenerate using ONLY these tables."
                        )
                        logger.warning(f"Retry table validation failed: {missing_tables}")
                        trace.add_step("validation", f"Retry table validation failed: {missing_tables}")
                        continue  # Skip to next attempt

                    # Then validate WHERE columns
                    try:
                        from src.llm.sql_semantic_validator import SQLSemanticValidator
                        retry_validator = SQLSemanticValidator()
                        retry_where_result = retry_validator.validate_where_columns_exist(sql, schema_dict)
                        if not retry_where_result.is_valid:
                            # Fixed SQL still has invalid WHERE columns - build hints for next retry
                            hints_text = retry_where_result.get_regeneration_hints()
                            last_error = (
                                f"Fixed SQL still references columns not in queried tables. "
                                f"{hints_text}"
                            )
                            logger.warning(f"Retry WHERE validation failed: {retry_where_result.mismatch_details}")
                            trace.add_step(
                                "validation",
                                f"Retry WHERE validation failed: {retry_where_result.mismatch_details}",
                                metadata={"suggestions": retry_where_result.suggestions}
                            )
                            continue  # Skip to next attempt
                    except Exception as e:
                        logger.debug(f"Retry WHERE validation skipped: {e}")

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

                # Validate SQL before executing - CRITICAL: must prevent execution if invalid!
                # Check for ALL attempts, not just first (Phase 1-4 fix)
                if not gen_result.get("is_valid", True):
                    validation_warnings = gen_result.get('warnings', [])
                    logger.warning(f"🚫 [ATTEMPT {attempt_num}] Generated SQL failed validation: {validation_warnings}")

                    # Build error message with hints for regeneration
                    last_error = f"SQL validation failed: {'; '.join(validation_warnings)}"

                    # Include WHERE validation hints if available (for location column issues)
                    if gen_result.get("where_validation_hints"):
                        last_error += f" {gen_result['where_validation_hints']}"

                    trace.add_step(
                        "validation",
                        f"SQL failed pre-execution validation: {validation_warnings}",
                        metadata={"hints": gen_result.get("where_validation_hints")}
                    )

                    # Record as failed attempt and retry with hints
                    attempt = CorrectionAttempt(
                        attempt_number=attempt_num,
                        sql=sql,
                        error=last_error,
                        error_type=ErrorType.SEMANTIC_ERROR if hasattr(ErrorType, 'SEMANTIC_ERROR') else ErrorType.UNKNOWN,
                        success=False,
                        execution_time_ms=0.0,
                        row_count=0,
                        confidence_score=None
                    )
                    attempts.append(attempt)
                    continue  # Skip to next attempt for regeneration with hints

                # === POST-GENERATION: Semantic Validation (Phase 3) ===
                # Validate that SQL matches the detected intent BEFORE execution
                if (SEMANTIC_VALIDATION_AVAILABLE and
                    intent_result is not None and
                    self.quality_profile and
                    self.quality_profile.enable_semantic_validation and
                    attempt_num == 1):  # Only validate on first attempt
                    try:
                        semantic_validator = SQLSemanticValidator()
                        validation_result = semantic_validator.validate(
                            sql=sql,
                            intent_result=intent_result,
                            question=question
                        )

                        trace.add_step(
                            "semantic_validation",
                            f"Semantic validation: {'passed' if validation_result.is_valid else 'failed'} "
                            f"(confidence: {validation_result.confidence:.2f})",
                            metadata={
                                "is_valid": validation_result.is_valid,
                                "confidence": validation_result.confidence,
                                "mismatch_type": validation_result.mismatch_type.value,
                                "details": validation_result.mismatch_details[:3],
                                "validation_time_ms": validation_result.validation_time_ms,
                            }
                        )

                        if not validation_result.is_valid:
                            # SQL doesn't match intent - use hints for regeneration
                            logger.warning(
                                f"❌ Semantic validation failed: {validation_result.mismatch_type.value} - "
                                f"{', '.join(validation_result.mismatch_details[:2])}"
                            )

                            # Build regeneration context
                            regen_hints = validation_result.get_regeneration_hints()
                            last_error = f"Semantic validation: {regen_hints}"

                            # Record as failed attempt and continue to retry
                            attempt = CorrectionAttempt(
                                attempt_number=attempt_num,
                                sql=sql,
                                error=last_error,
                                error_type=ErrorType.SEMANTIC_ERROR if hasattr(ErrorType, 'SEMANTIC_ERROR') else ErrorType.UNKNOWN,
                                success=False,
                                execution_time_ms=0.0,
                                row_count=0,
                                confidence_score=None
                            )
                            attempts.append(attempt)
                            continue  # Skip to next attempt with hints

                        logger.info(
                            f"✅ Semantic validation passed (confidence: {validation_result.confidence:.2f})"
                        )

                    except Exception as e:
                        logger.warning(f"Semantic validation failed (continuing): {e}")
                        trace.add_step("warning", f"Semantic validation skipped: {str(e)[:100]}")

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
        schema_dict: Optional[Dict] = None,  # For WHERE column validation
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

                # Generate corrected SQL with explicit hints (addresses PR review)
                fix_result = await self.generator.fix_sql_error(
                    sql=current_sql,
                    error=last_error,
                    schema=schema,
                    database_type=database_type,
                    model=model,
                    correction_hints=hints,  # Explicit hints forwarding
                    schema_dict=schema_dict,  # Pass for WHERE column validation
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
