"""
IndexAdvisor Service

Core service for database index recommendations.
Analyzes slow queries and generates passive recommendations.

Features:
- Automatic slow query detection (>500ms threshold)
- EXPLAIN plan analysis for PostgreSQL, MySQL, SQLite
- Index recommendation generation with confidence scoring
- Duplicate and conflicting index detection
- Impact estimation and validation
- Integration with Tool-Using Agent

Part of Phase 4: Database Index Recommendations
"""
import logging
import re
from typing import List, Dict, Optional, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_

from src.database.models import IndexRecommendation, DatabaseConnection, QueryHistory
from src.models.schemas import IndexRecommendationCreate
from src.tools.index_tools import (
    AnalyzeSlowQueryTool,
    CheckExistingIndexesTool,
    RecommendIndexTool,
    ValidateIndexImpactTool,
)
from src.core.user_db_connector import UserDatabaseConnector

logger = logging.getLogger(__name__)


class IndexAdvisor:
    """
    Service for analyzing queries and generating index recommendations.

    This is a passive recommendation system - it suggests indexes but
    never automatically creates them for security reasons.
    """

    # Slow query threshold in milliseconds
    SLOW_QUERY_THRESHOLD_MS = 500.0

    # Confidence thresholds for priority assignment
    HIGH_PRIORITY_CONFIDENCE = 0.85
    MEDIUM_PRIORITY_CONFIDENCE = 0.70

    def __init__(self, db_session: AsyncSession):
        """
        Initialize IndexAdvisor.

        Args:
            db_session: Async database session for metadata storage
        """
        self.db_session = db_session

        # Initialize tools
        self.analyze_tool = AnalyzeSlowQueryTool()
        self.check_indexes_tool = CheckExistingIndexesTool()
        self.recommend_tool = RecommendIndexTool()
        self.validate_tool = ValidateIndexImpactTool()

    async def analyze_query(
        self,
        connection_id: int,
        query_sql: str,
        execution_time_ms: float,
        query_id: Optional[int] = None
    ) -> Optional[IndexRecommendation]:
        """
        Analyze a query and generate index recommendation if needed.

        Args:
            connection_id: Database connection ID
            query_sql: SQL query to analyze
            execution_time_ms: Actual query execution time
            query_id: Query history ID if available

        Returns:
            IndexRecommendation if recommendation generated, None otherwise
        """
        try:
            # Check if query is slow enough to warrant analysis
            if execution_time_ms < self.SLOW_QUERY_THRESHOLD_MS:
                logger.debug(f"Query execution time {execution_time_ms}ms below threshold")
                return None

            # Get database connection details
            connection = await self._get_connection(connection_id)
            if not connection:
                logger.error(f"Connection {connection_id} not found")
                return None

            # Extract table name from query
            table_name = self._extract_primary_table(query_sql)
            if not table_name:
                logger.warning("Could not extract table name from query")
                return None

            # Setup database context for tools
            db_handler = await self._create_db_handler(connection)
            if not db_handler:
                logger.error("Failed to create database handler")
                return None

            try:
                context = {"db_handler": db_handler}

                # Set context for all tools
                self.analyze_tool.context = context
                self.check_indexes_tool.context = context
                self.recommend_tool.context = context

                # Step 1: Analyze query with EXPLAIN
                analysis_result = await self.analyze_tool.execute(
                    query_sql=query_sql,
                    database_type=connection.database_type
                )

                if not analysis_result.success:
                    logger.warning(f"Query analysis failed: {analysis_result.error_message}")
                    # Continue with recommendation anyway using static analysis
                    analysis_data = {"is_slow": True, "recommendations": []}
                else:
                    analysis_data = analysis_result.data

                # Step 2: Check existing indexes
                existing_indexes_result = await self.check_indexes_tool.execute(
                    table_name=table_name,
                    database_type=connection.database_type
                )

                existing_indexes = []
                if existing_indexes_result.success:
                    existing_indexes = existing_indexes_result.data.get("indexes", [])

                # Step 3: Generate index recommendation
                recommendation_result = await self.recommend_tool.execute(
                    query_sql=query_sql,
                    table_name=table_name,
                    database_type=connection.database_type
                )

                if not recommendation_result.success or not recommendation_result.data.get("index_name"):
                    logger.info("No suitable index recommendation found")
                    return None

                recommendation_data = recommendation_result.data

                # Step 4: Check for conflicts with existing indexes
                similar_exists, conflicting = self._check_index_conflicts(
                    recommendation_data["columns"],
                    existing_indexes
                )

                # Step 5: Validate impact
                validation_result = await self.validate_tool.execute(
                    query_sql=query_sql,
                    proposed_index_sql=recommendation_data["create_sql"],
                    database_type=connection.database_type
                )

                estimated_improvement_pct = None
                current_cost = None
                projected_cost = None
                confidence_score = 0.8  # Default

                if validation_result.success:
                    validation_data = validation_result.data
                    estimated_improvement_pct = validation_data.get("improvement_pct")
                    current_cost = validation_data.get("current_cost")
                    projected_cost = validation_data.get("projected_cost")
                    confidence_score = validation_data.get("confidence", 0.8)

                # Calculate priority based on execution time and confidence
                priority = self._calculate_priority(
                    execution_time_ms,
                    confidence_score,
                    estimated_improvement_pct
                )

                # Generate reason
                reason = self._generate_reason(
                    execution_time_ms,
                    table_name,
                    recommendation_data["columns"],
                    estimated_improvement_pct,
                    similar_exists
                )

                # Create recommendation record
                index_recommendation = IndexRecommendation(
                    connection_id=connection_id,
                    database_name=connection.database_name,
                    database_type=connection.database_type,
                    query_id=query_id,
                    slow_query_sql=query_sql,
                    execution_time_ms=execution_time_ms,
                    query_frequency=1,
                    table_name=table_name,
                    column_names=recommendation_data["columns"],
                    index_type="btree",
                    index_name=recommendation_data["index_name"],
                    estimated_improvement_pct=estimated_improvement_pct,
                    estimated_rows_scanned=analysis_data.get("estimated_rows_scanned"),
                    current_cost=current_cost,
                    projected_cost=projected_cost,
                    similar_indexes_exist=similar_exists,
                    conflicting_indexes=conflicting if conflicting else None,
                    confidence_score=confidence_score,
                    priority=priority,
                    reason=reason,
                    status="pending",
                    create_index_sql=recommendation_data["create_sql"],
                    drop_index_sql=recommendation_data.get("drop_sql"),
                    analysis_method="explain_plan",
                    validated=validation_result.success
                )

                # Save to database
                self.db_session.add(index_recommendation)
                await self.db_session.commit()
                await self.db_session.refresh(index_recommendation)

                logger.info(
                    f"Generated index recommendation {index_recommendation.id} "
                    f"for table {table_name} with priority {priority}"
                )

                return index_recommendation

            finally:
                # Clean up database handler resources
                if db_handler and hasattr(db_handler, 'cleanup'):
                    try:
                        db_handler.cleanup()
                    except Exception as cleanup_error:
                        logger.warning(f"Error cleaning up database handler: {cleanup_error}")

        except Exception as e:
            logger.error(f"Error analyzing query for index recommendation: {str(e)}")
            return None

    async def get_recommendations(
        self,
        connection_id: Optional[int] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[IndexRecommendation]:
        """
        Get index recommendations with optional filters.

        Args:
            connection_id: Filter by connection ID
            status: Filter by status (pending, accepted, rejected, applied, failed)
            priority: Filter by priority (high, medium, low)
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of IndexRecommendation objects
        """
        try:
            query = select(IndexRecommendation)

            # Apply filters
            filters = []
            if connection_id is not None:
                filters.append(IndexRecommendation.connection_id == connection_id)
            if status:
                filters.append(IndexRecommendation.status == status)
            if priority:
                filters.append(IndexRecommendation.priority == priority)

            if filters:
                query = query.where(and_(*filters))

            # Order by priority and creation date
            query = query.order_by(
                IndexRecommendation.priority.desc(),
                IndexRecommendation.created_at.desc()
            ).limit(limit).offset(offset)

            result = await self.db_session.execute(query)
            recommendations = result.scalars().all()

            return list(recommendations)

        except Exception as e:
            logger.error(f"Error getting recommendations: {str(e)}")
            return []

    async def get_recommendation_stats(
        self,
        connection_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get statistics about index recommendations.

        Args:
            connection_id: Optional filter by connection

        Returns:
            Dictionary with statistics
        """
        try:
            base_query = select(IndexRecommendation)
            if connection_id is not None:
                base_query = base_query.where(IndexRecommendation.connection_id == connection_id)

            # Total count
            count_query = select(func.count()).select_from(IndexRecommendation)
            if connection_id is not None:
                count_query = count_query.where(IndexRecommendation.connection_id == connection_id)

            total_result = await self.db_session.execute(count_query)
            total = total_result.scalar() or 0

            # Count by status
            status_counts = {}
            for status in ["pending", "accepted", "rejected", "applied", "failed"]:
                status_query = select(func.count()).select_from(IndexRecommendation).where(
                    IndexRecommendation.status == status
                )
                if connection_id is not None:
                    status_query = status_query.where(IndexRecommendation.connection_id == connection_id)

                result = await self.db_session.execute(status_query)
                status_counts[status] = result.scalar() or 0

            # Count by priority
            priority_counts = {}
            for priority in ["high", "medium", "low"]:
                priority_query = select(func.count()).select_from(IndexRecommendation).where(
                    IndexRecommendation.priority == priority
                )
                if connection_id is not None:
                    priority_query = priority_query.where(IndexRecommendation.connection_id == connection_id)

                result = await self.db_session.execute(priority_query)
                priority_counts[priority] = result.scalar() or 0

            # Count by database type
            db_type_query = select(
                IndexRecommendation.database_type,
                func.count()
            ).group_by(IndexRecommendation.database_type)

            if connection_id is not None:
                db_type_query = db_type_query.where(IndexRecommendation.connection_id == connection_id)

            db_type_result = await self.db_session.execute(db_type_query)
            db_type_counts = {row[0]: row[1] for row in db_type_result}

            # Average execution time
            avg_exec_query = select(func.avg(IndexRecommendation.execution_time_ms))
            if connection_id is not None:
                avg_exec_query = avg_exec_query.where(IndexRecommendation.connection_id == connection_id)

            avg_exec_result = await self.db_session.execute(avg_exec_query)
            avg_execution_time = avg_exec_result.scalar() or 0.0

            # Average improvement
            avg_improvement_query = select(
                func.avg(IndexRecommendation.estimated_improvement_pct)
            ).where(IndexRecommendation.estimated_improvement_pct.isnot(None))

            if connection_id is not None:
                avg_improvement_query = avg_improvement_query.where(
                    IndexRecommendation.connection_id == connection_id
                )

            avg_improvement_result = await self.db_session.execute(avg_improvement_query)
            avg_improvement = avg_improvement_result.scalar()

            return {
                "total_recommendations": total,
                "by_status": status_counts,
                "by_priority": priority_counts,
                "by_database_type": db_type_counts,
                "avg_execution_time_ms": float(avg_execution_time),
                "avg_improvement_pct": float(avg_improvement) if avg_improvement else None,
                "total_applied": status_counts.get("applied", 0),
                "total_pending": status_counts.get("pending", 0)
            }

        except Exception as e:
            logger.error(f"Error getting recommendation stats: {str(e)}")
            return {
                "total_recommendations": 0,
                "by_status": {},
                "by_priority": {},
                "by_database_type": {},
                "avg_execution_time_ms": 0.0,
                "avg_improvement_pct": None,
                "total_applied": 0,
                "total_pending": 0
            }

    async def update_recommendation_status(
        self,
        recommendation_id: int,
        status: str,
        applied_by: Optional[str] = None,
        validation_notes: Optional[str] = None
    ) -> Optional[IndexRecommendation]:
        """
        Update recommendation status.

        Args:
            recommendation_id: Recommendation ID
            status: New status
            applied_by: User who applied (for 'applied' status)
            validation_notes: Optional validation notes

        Returns:
            Updated IndexRecommendation or None
        """
        try:
            query = select(IndexRecommendation).where(IndexRecommendation.id == recommendation_id)
            result = await self.db_session.execute(query)
            recommendation = result.scalar_one_or_none()

            if not recommendation:
                logger.error(f"Recommendation {recommendation_id} not found")
                return None

            recommendation.status = status

            if status == "applied":
                recommendation.applied_at = datetime.utcnow()
                if applied_by:
                    recommendation.applied_by = applied_by

            if validation_notes:
                recommendation.validation_notes = validation_notes

            await self.db_session.commit()
            await self.db_session.refresh(recommendation)

            return recommendation

        except Exception as e:
            logger.error(f"Error updating recommendation status: {str(e)}")
            return None

    # ========================================================================
    # Private Helper Methods
    # ========================================================================

    async def _get_connection(self, connection_id: int) -> Optional[DatabaseConnection]:
        """Get database connection by ID"""
        query = select(DatabaseConnection).where(DatabaseConnection.id == connection_id)
        result = await self.db_session.execute(query)
        return result.scalar_one_or_none()

    async def _create_db_handler(self, connection: DatabaseConnection):
        """Create database handler for executing queries"""
        from src.core.multi_db_handler import MultiDatabaseHandler

        connector = UserDatabaseConnector()

        # Create database session for the specific connection
        try:
            session, engine, is_sync = await connector.create_session(
                database_type=connection.database_type,
                host=connection.host,
                port=connection.port,
                database_name=connection.database_name,
                username=connection.username,
                password=connection.password,
            )
        except Exception as e:
            logger.error(f"Failed to create session for connection {connection.id}: {e}")
            return None

        if not session:
            logger.warning(f"Failed to create session for connection {connection.id}")
            return None

        # Create a minimal handler wrapper for tool execution
        class ToolDatabaseHandler:
            """Minimal database handler for index analysis tools"""
            def __init__(self, session, engine, is_sync):
                self.session = session
                self.engine = engine
                self.is_sync = is_sync

            async def execute_raw_sql(self, sql: str):
                """Execute raw SQL and return results (required by index_tools)"""
                from sqlalchemy import text

                try:
                    if self.is_sync:
                        # DuckDB uses sync session
                        result = self.session.execute(text(sql))
                        rows = result.fetchall() if hasattr(result, 'fetchall') else []
                        # Convert Row objects to dicts for tool compatibility
                        return [dict(row._mapping) if hasattr(row, '_mapping') else dict(row) for row in rows]
                    else:
                        # Async databases
                        result = await self.session.execute(text(sql))
                        rows = result.fetchall() if hasattr(result, 'fetchall') else []
                        # Convert Row objects to dicts for tool compatibility
                        return [dict(row._mapping) if hasattr(row, '_mapping') else dict(row) for row in rows]
                except Exception as e:
                    logger.error(f"Query execution failed in index analysis: {e}")
                    raise  # Re-raise so tools can handle it

            def cleanup(self):
                """Clean up database resources"""
                try:
                    if self.is_sync:
                        self.session.close()
                        self.engine.dispose()
                    else:
                        # Note: async cleanup should be awaited, but this is called from sync context
                        # For now, just close the session - engine disposal happens in garbage collection
                        import asyncio
                        if asyncio.iscoroutinefunction(self.session.close):
                            # Schedule async cleanup
                            loop = asyncio.get_event_loop()
                            if loop.is_running():
                                loop.create_task(self._async_cleanup())
                            else:
                                asyncio.run(self._async_cleanup())
                        else:
                            self.session.close()
                except Exception as e:
                    logger.error(f"Error during database handler cleanup: {e}")

            async def _async_cleanup(self):
                """Async cleanup for async sessions"""
                try:
                    await self.session.close()
                    await self.engine.dispose()
                except Exception as e:
                    logger.error(f"Error during async cleanup: {e}")

        return ToolDatabaseHandler(session, engine, is_sync)

    def _extract_primary_table(self, query_sql: str) -> Optional[str]:
        """Extract the primary table from SQL query"""
        # Match FROM clause
        from_match = re.search(r"FROM\s+(\w+)", query_sql, re.IGNORECASE)
        if from_match:
            return from_match.group(1)

        # Match JOIN clauses
        join_match = re.search(r"JOIN\s+(\w+)", query_sql, re.IGNORECASE)
        if join_match:
            return join_match.group(1)

        return None

    def _check_index_conflicts(
        self,
        proposed_columns: List[str],
        existing_indexes: List[Dict[str, Any]]
    ) -> tuple[bool, Optional[List[str]]]:
        """
        Check if proposed index conflicts with existing indexes.

        Returns:
            (similar_exists, conflicting_names)
        """
        conflicting = []

        for idx in existing_indexes:
            idx_columns = idx.get("columns", [])

            # Exact match (order matters - different order = different performance!)
            if proposed_columns == idx_columns:
                conflicting.append(idx["name"])

            # Subset match (proposed columns are prefix of existing)
            elif len(proposed_columns) <= len(idx_columns):
                if all(
                    p == idx_columns[i] for i, p in enumerate(proposed_columns)
                ):
                    conflicting.append(idx["name"])

        similar_exists = len(conflicting) > 0
        return similar_exists, conflicting if conflicting else None

    def _calculate_priority(
        self,
        execution_time_ms: float,
        confidence_score: float,
        estimated_improvement_pct: Optional[float]
    ) -> str:
        """Calculate recommendation priority"""
        # High priority: very slow query + high confidence
        if execution_time_ms > 2000 and confidence_score >= self.HIGH_PRIORITY_CONFIDENCE:
            return "high"

        # High priority: moderate speed but excellent improvement potential
        if estimated_improvement_pct and estimated_improvement_pct > 60:
            return "high"

        # Medium priority: moderate slowness or moderate confidence
        if execution_time_ms > 1000 or confidence_score >= self.MEDIUM_PRIORITY_CONFIDENCE:
            return "medium"

        # Low priority: everything else
        return "low"

    def _generate_reason(
        self,
        execution_time_ms: float,
        table_name: str,
        columns: List[str],
        estimated_improvement_pct: Optional[float],
        similar_exists: bool
    ) -> str:
        """Generate human-readable reason for recommendation"""
        reasons = []

        # Slow query reason
        if execution_time_ms > 2000:
            reasons.append(f"Query is very slow ({execution_time_ms:.0f}ms)")
        elif execution_time_ms > 1000:
            reasons.append(f"Query is slow ({execution_time_ms:.0f}ms)")
        else:
            reasons.append(f"Query execution time: {execution_time_ms:.0f}ms")

        # Index benefit
        columns_str = ", ".join(columns)
        reasons.append(f"Index on {columns_str} would improve WHERE/ORDER BY performance")

        # Improvement estimate
        if estimated_improvement_pct:
            reasons.append(f"Estimated {estimated_improvement_pct:.0f}% improvement")

        # Similar index warning
        if similar_exists:
            reasons.append("Similar index may already exist - review before applying")

        return ". ".join(reasons)
