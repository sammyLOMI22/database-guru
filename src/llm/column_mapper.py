"""
Column name mapping and learning system

Handles column name corrections from user feedback, storing mappings
and applying them to future queries for better schema matching.

Part of Phase 2: Non-SQL Feedback Implementation
"""
import logging
import re
from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime
from difflib import SequenceMatcher

from sqlalchemy import select, and_, or_, func, text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class ColumnMapping:
    """Represents a column name mapping"""
    def __init__(
        self,
        id: int,
        source_column: str,
        target_column: str,
        table_name: Optional[str],
        connection_name: Optional[str],
        database_type: str,
        confidence_score: float,
        times_applied: int = 0,
        description: Optional[str] = None
    ):
        self.id = id
        self.source_column = source_column
        self.target_column = target_column
        self.table_name = table_name
        self.connection_name = connection_name
        self.database_type = database_type
        self.confidence_score = confidence_score
        self.times_applied = times_applied
        self.description = description

    def __repr__(self):
        table_info = f" in {self.table_name}" if self.table_name else ""
        conn_info = f" ({self.connection_name})" if self.connection_name else ""
        return f"<ColumnMapping: {self.source_column} → {self.target_column}{table_info}{conn_info}>"


class ColumnMapper:
    """
    Manages column name mappings and aliases

    Features:
    - Learn from user feedback about column name corrections
    - Apply mappings during query planning and execution
    - Suggest correct column names with fuzzy matching
    - Track mapping success rates and usage statistics
    - Support both table-specific and global mappings

    Example:
        mapper = ColumnMapper(db_session=db)

        # Learn from feedback
        mapping_id = await mapper.learn_from_feedback(
            source_column="price",
            target_column="unit_price",
            table_name="products",
            database_type="postgres",
            feedback_id=123
        )

        # Apply mappings to SQL
        corrected_sql, applied = await mapper.apply_mappings(
            sql="SELECT price FROM products",
            table_name="products",
            database_type="postgres"
        )
        # Result: "SELECT unit_price FROM products"

        # Suggest correct column name
        suggestion = await mapper.suggest_correct_column(
            incorrect_column="customer_name",
            table_name="customers",
            database_type="postgres"
        )
    """

    def __init__(self, db_session: AsyncSession):
        """
        Initialize the column mapper

        Args:
            db_session: Async database session for persistence
        """
        self.db_session = db_session

    async def learn_from_feedback(
        self,
        source_column: str,
        target_column: str,
        table_name: Optional[str],
        connection_name: str,
        database_type: str,
        feedback_id: int,
        description: Optional[str] = None,
        confidence_score: float = 1.0
    ) -> int:
        """
        Create a new column mapping from user feedback

        Args:
            source_column: The incorrect column name user tried to use
            target_column: The correct column name in the schema
            table_name: Specific table (None = applies to all tables in this connection)
            connection_name: Database connection name (e.g., "sales_db", "inventory_db")
            database_type: Database type (postgres, mysql, sqlite, etc.)
            feedback_id: ID of the user feedback that taught us this
            description: Human-readable description of the mapping
            confidence_score: Confidence in this mapping (0.0-1.0)

        Returns:
            The ID of the created column mapping

        Raises:
            ValueError: If mapping already exists
        """
        try:
            logger.info(
                f"📚 Learning column mapping: {source_column} → {target_column}"
                f"{' in ' + table_name if table_name else ''} "
                f"(conn={connection_name}, db={database_type}, confidence={confidence_score})"
            )

            # Check if mapping already exists
            existing_mapping = await self._get_mapping(
                source_column=source_column,
                target_column=target_column,
                table_name=table_name,
                connection_name=connection_name,
                database_type=database_type
            )

            if existing_mapping:
                logger.warning(
                    f"⚠️  Column mapping already exists: {existing_mapping}"
                )
                # Update the existing mapping with new metadata
                await self.db_session.execute(
                    text("""
                        UPDATE column_mappings
                        SET confidence_score = :confidence,
                            description = COALESCE(:description, description),
                            learned_from_feedback_id = :feedback_id
                        WHERE id = :mapping_id
                    """),
                    {
                        "confidence": confidence_score,
                        "description": description,
                        "feedback_id": feedback_id,
                        "mapping_id": existing_mapping.id
                    }
                )
                await self.db_session.commit()
                return existing_mapping.id

            # Create new mapping
            result = await self.db_session.execute(
                text("""
                    INSERT INTO column_mappings (
                        source_column,
                        target_column,
                        table_name,
                        connection_name,
                        database_type,
                        description,
                        confidence_score,
                        learned_from_feedback_id,
                        created_by,
                        created_at
                    ) VALUES (
                        :source_column,
                        :target_column,
                        :table_name,
                        :connection_name,
                        :database_type,
                        :description,
                        :confidence_score,
                        :feedback_id,
                        'user',
                        CURRENT_TIMESTAMP
                    )
                """),
                {
                    "source_column": source_column.lower(),
                    "target_column": target_column.lower(),
                    "table_name": table_name.lower() if table_name else None,
                    "connection_name": connection_name,
                    "database_type": database_type.lower(),
                    "description": description,
                    "confidence_score": confidence_score,
                    "feedback_id": feedback_id
                }
            )

            await self.db_session.commit()
            mapping_id = result.lastrowid

            logger.info(
                f"✅ Column mapping created: id={mapping_id}, "
                f"{source_column} → {target_column}"
            )

            return mapping_id

        except Exception as e:
            await self.db_session.rollback()
            logger.error(
                f"❌ Failed to learn column mapping: {e}",
                exc_info=True
            )
            raise

    async def apply_mappings(
        self,
        sql: str,
        table_name: Optional[str],
        connection_name: str,
        database_type: str
    ) -> Tuple[str, List[str]]:
        """
        Apply learned column mappings to SQL query

        Args:
            sql: The SQL query to modify
            table_name: The table being queried (for table-specific mappings)
            connection_name: Database connection name
            database_type: Database type

        Returns:
            Tuple of (modified_sql, list_of_applied_mappings)

        Example:
            >>> sql = "SELECT price FROM products WHERE category = 'electronics'"
            >>> corrected, applied = await mapper.apply_mappings(
            ...     sql=sql,
            ...     table_name="products",
            ...     connection_name="sales_db",
            ...     database_type="postgres"
            ... )
            >>> print(corrected)
            "SELECT unit_price FROM products WHERE category = 'electronics'"
            >>> print(applied)
            ["price → unit_price"]
        """
        try:
            # Get applicable mappings
            mappings = await self._get_applicable_mappings(
                table_name=table_name,
                connection_name=connection_name,
                database_type=database_type
            )

            if not mappings:
                logger.debug("No column mappings found for this query")
                return sql, []

            modified_sql = sql
            applied_mappings = []

            # Apply each mapping
            for mapping in mappings:
                # Use word boundary regex to avoid partial matches
                # e.g., "price" shouldn't match "total_price"
                pattern = r'\b' + re.escape(mapping.source_column) + r'\b'

                if re.search(pattern, modified_sql, re.IGNORECASE):
                    # Replace with target column
                    modified_sql = re.sub(
                        pattern,
                        mapping.target_column,
                        modified_sql,
                        flags=re.IGNORECASE
                    )

                    applied_mappings.append(
                        f"{mapping.source_column} → {mapping.target_column}"
                    )

                    # Update usage statistics
                    await self._record_mapping_usage(mapping.id)

                    logger.info(
                        f"✨ Applied column mapping: {mapping.source_column} → "
                        f"{mapping.target_column}"
                    )

            if applied_mappings:
                await self.db_session.commit()

            return modified_sql, applied_mappings

        except Exception as e:
            logger.error(f"❌ Failed to apply column mappings: {e}", exc_info=True)
            # Return original SQL on error
            return sql, []

    async def suggest_correct_column(
        self,
        incorrect_column: str,
        table_name: Optional[str],
        connection_name: str,
        database_type: str,
        min_confidence: float = 0.6
    ) -> Optional[str]:
        """
        Suggest correct column name based on learned mappings

        Args:
            incorrect_column: The column name that failed
            table_name: The table context
            connection_name: Database connection name
            database_type: Database type
            min_confidence: Minimum confidence threshold for suggestions

        Returns:
            Suggested correct column name, or None if no good match

        Example:
            >>> suggestion = await mapper.suggest_correct_column(
            ...     incorrect_column="customer_name",
            ...     table_name="customers",
            ...     connection_name="sales_db",
            ...     database_type="postgres"
            ... )
            >>> print(suggestion)
            "customer_full_name"  # If this mapping was learned
        """
        try:
            # First, check for exact mapping
            mappings = await self._get_applicable_mappings(
                table_name=table_name,
                connection_name=connection_name,
                database_type=database_type
            )

            for mapping in mappings:
                if mapping.source_column.lower() == incorrect_column.lower():
                    if mapping.confidence_score >= min_confidence:
                        logger.info(
                            f"💡 Found learned mapping: {incorrect_column} → "
                            f"{mapping.target_column} (confidence={mapping.confidence_score})"
                        )
                        return mapping.target_column

            # No exact match found
            logger.debug(
                f"No column mapping found for '{incorrect_column}' in "
                f"table '{table_name}' (db={database_type})"
            )
            return None

        except Exception as e:
            logger.error(f"❌ Failed to suggest column: {e}", exc_info=True)
            return None

    async def get_mapping_stats(self, database_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistics about column mappings

        Args:
            database_type: Filter by database type (optional)

        Returns:
            Dictionary with mapping statistics
        """
        try:
            where_clause = "WHERE database_type = :db_type" if database_type else ""
            params = {"db_type": database_type} if database_type else {}

            result = await self.db_session.execute(
                text(f"""
                    SELECT
                        COUNT(*) as total_mappings,
                        SUM(times_applied) as total_applications,
                        AVG(confidence_score) as avg_confidence,
                        COUNT(CASE WHEN table_name IS NULL THEN 1 END) as global_mappings,
                        COUNT(CASE WHEN table_name IS NOT NULL THEN 1 END) as table_specific_mappings
                    FROM column_mappings
                    {where_clause}
                """),
                params
            )

            row = result.fetchone()

            return {
                "total_mappings": row[0] or 0,
                "total_applications": row[1] or 0,
                "average_confidence": round(row[2] or 0.0, 2),
                "global_mappings": row[3] or 0,
                "table_specific_mappings": row[4] or 0,
                "database_type": database_type or "all"
            }

        except Exception as e:
            logger.error(f"Failed to get mapping stats: {e}", exc_info=True)
            return {}

    async def delete_mapping(self, mapping_id: int) -> bool:
        """
        Delete a column mapping

        Args:
            mapping_id: ID of the mapping to delete

        Returns:
            True if deleted, False if not found
        """
        try:
            result = await self.db_session.execute(
                text("DELETE FROM column_mappings WHERE id = :mapping_id"),
                {"mapping_id": mapping_id}
            )
            await self.db_session.commit()

            deleted = result.rowcount > 0
            if deleted:
                logger.info(f"🗑️  Deleted column mapping: id={mapping_id}")
            else:
                logger.warning(f"⚠️  Column mapping not found: id={mapping_id}")

            return deleted

        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Failed to delete mapping: {e}", exc_info=True)
            return False

    # Private helper methods

    async def _get_mapping(
        self,
        source_column: str,
        target_column: str,
        table_name: Optional[str],
        connection_name: str,
        database_type: str
    ) -> Optional[ColumnMapping]:
        """Get a specific mapping if it exists"""
        result = await self.db_session.execute(
            text("""
                SELECT
                    id, source_column, target_column, table_name, connection_name,
                    database_type, confidence_score, times_applied, description
                FROM column_mappings
                WHERE source_column = :source
                  AND target_column = :target
                  AND COALESCE(table_name, '') = :table
                  AND connection_name = :conn_name
                  AND database_type = :db_type
                LIMIT 1
            """),
            {
                "source": source_column.lower(),
                "target": target_column.lower(),
                "table": (table_name or "").lower(),
                "conn_name": connection_name,
                "db_type": database_type.lower()
            }
        )

        row = result.fetchone()
        if row:
            return ColumnMapping(
                id=row[0],
                source_column=row[1],
                target_column=row[2],
                table_name=row[3],
                connection_name=row[4],
                database_type=row[5],
                confidence_score=row[6],
                times_applied=row[7],
                description=row[8]
            )

        return None

    async def _get_applicable_mappings(
        self,
        table_name: Optional[str],
        connection_name: str,
        database_type: str
    ) -> List[ColumnMapping]:
        """
        Get all mappings applicable to this table, connection, and database

        Priority:
        1. Table-specific mappings for this table in this connection
        2. Global mappings (table_name IS NULL) for this connection
        """
        result = await self.db_session.execute(
            text("""
                SELECT
                    id, source_column, target_column, table_name, connection_name,
                    database_type, confidence_score, times_applied, description
                FROM column_mappings
                WHERE connection_name = :conn_name
                  AND database_type = :db_type
                  AND (table_name = :table OR table_name IS NULL)
                ORDER BY
                    CASE WHEN table_name IS NOT NULL THEN 1 ELSE 2 END,
                    confidence_score DESC,
                    times_applied DESC
            """),
            {
                "conn_name": connection_name,
                "db_type": database_type.lower(),
                "table": table_name.lower() if table_name else None
            }
        )

        mappings = []
        for row in result.fetchall():
            mappings.append(ColumnMapping(
                id=row[0],
                source_column=row[1],
                target_column=row[2],
                table_name=row[3],
                connection_name=row[4],
                database_type=row[5],
                confidence_score=row[6],
                times_applied=row[7],
                description=row[8]
            ))

        return mappings

    async def _record_mapping_usage(self, mapping_id: int):
        """Record that a mapping was successfully applied"""
        await self.db_session.execute(
            text("""
                UPDATE column_mappings
                SET times_applied = times_applied + 1,
                    last_applied_at = CURRENT_TIMESTAMP
                WHERE id = :mapping_id
            """),
            {"mapping_id": mapping_id}
        )


# Utility functions for column name similarity

def column_similarity(col1: str, col2: str) -> float:
    """
    Calculate similarity between two column names (0.0 to 1.0)

    Uses SequenceMatcher for fuzzy string matching.
    """
    return SequenceMatcher(None, col1.lower(), col2.lower()).ratio()


def find_similar_columns(
    target_column: str,
    available_columns: List[str],
    threshold: float = 0.6
) -> List[Tuple[str, float]]:
    """
    Find columns similar to the target

    Args:
        target_column: The column to match
        available_columns: List of available column names
        threshold: Minimum similarity score (0.0-1.0)

    Returns:
        List of (column_name, similarity_score) tuples, sorted by score
    """
    matches = []

    for col in available_columns:
        similarity = column_similarity(target_column, col)
        if similarity >= threshold:
            matches.append((col, similarity))

    # Sort by similarity score (descending)
    matches.sort(key=lambda x: x[1], reverse=True)

    return matches
