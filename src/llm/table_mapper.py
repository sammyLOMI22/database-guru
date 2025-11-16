"""
Table name mapping and learning system

Handles table name corrections from user feedback, storing mappings
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


class TableMapping:
    """Represents a table name mapping"""
    def __init__(
        self,
        id: int,
        source_table: str,
        target_table: str,
        connection_name: str,
        database_type: str,
        mapping_type: str,
        confidence_score: float,
        times_applied: int = 0,
        description: Optional[str] = None
    ):
        self.id = id
        self.source_table = source_table
        self.target_table = target_table
        self.connection_name = connection_name
        self.database_type = database_type
        self.mapping_type = mapping_type
        self.confidence_score = confidence_score
        self.times_applied = times_applied
        self.description = description

    def __repr__(self):
        conn_info = f" ({self.connection_name})" if self.connection_name else ""
        return f"<TableMapping: {self.source_table} → {self.target_table}{conn_info}>"


class TableMapper:
    """
    Manages table name mappings and aliases

    Features:
    - Learn from user feedback about table name corrections
    - Apply mappings during query planning and execution
    - Suggest correct table names with fuzzy matching
    - Track mapping success rates and usage statistics
    - Support for connection-specific mappings

    Example:
        mapper = TableMapper(db_session=db)

        # Learn from feedback
        mapping_id = await mapper.learn_from_feedback(
            source_table="users",
            target_table="customers",
            connection_name="sales_db",
            database_type="postgres",
            feedback_id=123
        )

        # Apply mappings to SQL
        corrected_sql, applied = await mapper.apply_mappings(
            sql="SELECT * FROM users WHERE active = true",
            connection_name="sales_db",
            database_type="postgres"
        )
        # Result: "SELECT * FROM customers WHERE active = true"

        # Suggest correct table name
        suggestion = await mapper.suggest_correct_table(
            incorrect_table="user",
            connection_name="sales_db",
            database_type="postgres"
        )
    """

    def __init__(self, db_session: AsyncSession):
        """
        Initialize the table mapper

        Args:
            db_session: Async database session for persistence
        """
        self.db_session = db_session

    async def learn_from_feedback(
        self,
        source_table: str,
        target_table: str,
        connection_name: str,
        database_type: str,
        feedback_id: int,
        description: Optional[str] = None,
        mapping_type: str = "alias",
        confidence_score: float = 1.0
    ) -> int:
        """
        Create a new table mapping from user feedback

        Args:
            source_table: The incorrect table name user tried to use
            target_table: The correct table name in the schema
            connection_name: Database connection name (e.g., "sales_db", "inventory_db")
            database_type: Database type (postgres, mysql, sqlite, etc.)
            feedback_id: ID of the user feedback that taught us this
            description: Human-readable description of the mapping
            mapping_type: Type of mapping (alias, typo, synonym, etc.)
            confidence_score: Confidence in this mapping (0.0-1.0)

        Returns:
            The ID of the created table mapping

        Raises:
            ValueError: If mapping already exists
        """
        try:
            logger.info(
                f"📚 Learning table mapping: {source_table} → {target_table} "
                f"(conn={connection_name}, db={database_type}, type={mapping_type}, "
                f"confidence={confidence_score})"
            )

            # Check if mapping already exists
            existing_mapping = await self._get_mapping(
                source_table=source_table,
                target_table=target_table,
                connection_name=connection_name,
                database_type=database_type
            )

            if existing_mapping:
                logger.warning(
                    f"⚠️  Table mapping already exists: {existing_mapping}"
                )
                # Update the existing mapping with new metadata
                await self.db_session.execute(
                    text("""
                        UPDATE table_mappings
                        SET confidence_score = :confidence,
                            description = COALESCE(:description, description),
                            mapping_type = :mapping_type,
                            learned_from_feedback_id = :feedback_id
                        WHERE id = :mapping_id
                    """),
                    {
                        "confidence": confidence_score,
                        "description": description,
                        "mapping_type": mapping_type,
                        "feedback_id": feedback_id,
                        "mapping_id": existing_mapping.id
                    }
                )
                await self.db_session.commit()
                return existing_mapping.id

            # Create new mapping
            result = await self.db_session.execute(
                text("""
                    INSERT INTO table_mappings (
                        source_table,
                        target_table,
                        connection_name,
                        database_type,
                        description,
                        mapping_type,
                        confidence_score,
                        learned_from_feedback_id,
                        created_by,
                        created_at
                    ) VALUES (
                        :source_table,
                        :target_table,
                        :connection_name,
                        :database_type,
                        :description,
                        :mapping_type,
                        :confidence_score,
                        :feedback_id,
                        'user',
                        CURRENT_TIMESTAMP
                    )
                """),
                {
                    "source_table": source_table.lower(),
                    "target_table": target_table.lower(),
                    "connection_name": connection_name,
                    "database_type": database_type.lower(),
                    "description": description,
                    "mapping_type": mapping_type,
                    "confidence_score": confidence_score,
                    "feedback_id": feedback_id
                }
            )

            await self.db_session.commit()
            mapping_id = result.lastrowid

            logger.info(
                f"✅ Table mapping created: id={mapping_id}, "
                f"{source_table} → {target_table}"
            )

            return mapping_id

        except Exception as e:
            await self.db_session.rollback()
            logger.error(
                f"❌ Failed to learn table mapping: {e}",
                exc_info=True
            )
            raise

    async def apply_mappings(
        self,
        sql: str,
        connection_name: str,
        database_type: str
    ) -> Tuple[str, List[str]]:
        """
        Apply learned table mappings to SQL query

        Args:
            sql: The SQL query to modify
            connection_name: Database connection name
            database_type: Database type

        Returns:
            Tuple of (modified_sql, list_of_applied_mappings)

        Example:
            >>> sql = "SELECT name FROM users JOIN orders ON users.id = orders.user_id"
            >>> corrected, applied = await mapper.apply_mappings(
            ...     sql=sql,
            ...     connection_name="sales_db",
            ...     database_type="postgres"
            ... )
            >>> print(corrected)
            "SELECT name FROM customers JOIN orders ON customers.id = orders.user_id"
            >>> print(applied)
            ["users → customers"]
        """
        try:
            # Get applicable mappings
            mappings = await self._get_applicable_mappings(
                connection_name=connection_name,
                database_type=database_type
            )

            if not mappings:
                logger.debug("No table mappings found for this query")
                return sql, []

            modified_sql = sql
            applied_mappings = []

            # Apply each mapping
            for mapping in mappings:
                # Use word boundary regex to avoid partial matches
                # e.g., "user" shouldn't match "users_archive"
                pattern = r'\b' + re.escape(mapping.source_table) + r'\b'

                if re.search(pattern, modified_sql, re.IGNORECASE):
                    # Replace with target table
                    modified_sql = re.sub(
                        pattern,
                        mapping.target_table,
                        modified_sql,
                        flags=re.IGNORECASE
                    )

                    applied_mappings.append(
                        f"{mapping.source_table} → {mapping.target_table}"
                    )

                    # Update usage statistics
                    await self._record_mapping_usage(mapping.id)

                    logger.info(
                        f"✨ Applied table mapping: {mapping.source_table} → "
                        f"{mapping.target_table}"
                    )

            if applied_mappings:
                await self.db_session.commit()

            return modified_sql, applied_mappings

        except Exception as e:
            logger.error(f"❌ Failed to apply table mappings: {e}", exc_info=True)
            # Return original SQL on error
            return sql, []

    async def suggest_correct_table(
        self,
        incorrect_table: str,
        connection_name: str,
        database_type: str,
        min_confidence: float = 0.6
    ) -> Optional[str]:
        """
        Suggest correct table name based on learned mappings

        Args:
            incorrect_table: The table name that failed
            connection_name: Database connection name
            database_type: Database type
            min_confidence: Minimum confidence threshold for suggestions

        Returns:
            Suggested correct table name, or None if no good match

        Example:
            >>> suggestion = await mapper.suggest_correct_table(
            ...     incorrect_table="user",
            ...     connection_name="sales_db",
            ...     database_type="postgres"
            ... )
            >>> print(suggestion)
            "users"  # If this mapping was learned
        """
        try:
            # Check for exact mapping
            mappings = await self._get_applicable_mappings(
                connection_name=connection_name,
                database_type=database_type
            )

            for mapping in mappings:
                if mapping.source_table.lower() == incorrect_table.lower():
                    if mapping.confidence_score >= min_confidence:
                        logger.info(
                            f"💡 Found learned mapping: {incorrect_table} → "
                            f"{mapping.target_table} (confidence={mapping.confidence_score})"
                        )
                        return mapping.target_table

            # No exact match found
            logger.debug(
                f"No table mapping found for '{incorrect_table}' "
                f"(connection={connection_name}, db={database_type})"
            )
            return None

        except Exception as e:
            logger.error(f"❌ Failed to suggest table: {e}", exc_info=True)
            return None

    async def get_mapping_stats(self, database_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistics about table mappings

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
                        COUNT(CASE WHEN mapping_type = 'alias' THEN 1 END) as alias_mappings,
                        COUNT(CASE WHEN mapping_type = 'typo' THEN 1 END) as typo_mappings
                    FROM table_mappings
                    {where_clause}
                """),
                params
            )

            row = result.fetchone()

            return {
                "total_mappings": row[0] or 0,
                "total_applications": row[1] or 0,
                "average_confidence": round(row[2] or 0.0, 2),
                "alias_mappings": row[3] or 0,
                "typo_mappings": row[4] or 0,
                "database_type": database_type or "all"
            }

        except Exception as e:
            logger.error(f"Failed to get mapping stats: {e}", exc_info=True)
            return {}

    async def delete_mapping(self, mapping_id: int) -> bool:
        """
        Delete a table mapping

        Args:
            mapping_id: ID of the mapping to delete

        Returns:
            True if deleted, False if not found
        """
        try:
            result = await self.db_session.execute(
                text("DELETE FROM table_mappings WHERE id = :mapping_id"),
                {"mapping_id": mapping_id}
            )
            await self.db_session.commit()

            deleted = result.rowcount > 0
            if deleted:
                logger.info(f"🗑️  Deleted table mapping: id={mapping_id}")
            else:
                logger.warning(f"⚠️  Table mapping not found: id={mapping_id}")

            return deleted

        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Failed to delete mapping: {e}", exc_info=True)
            return False

    # Private helper methods

    async def _get_mapping(
        self,
        source_table: str,
        target_table: str,
        connection_name: str,
        database_type: str
    ) -> Optional[TableMapping]:
        """Get a specific mapping if it exists"""
        result = await self.db_session.execute(
            text("""
                SELECT
                    id, source_table, target_table, connection_name,
                    database_type, mapping_type, confidence_score,
                    times_applied, description
                FROM table_mappings
                WHERE source_table = :source
                  AND target_table = :target
                  AND connection_name = :conn_name
                  AND database_type = :db_type
                LIMIT 1
            """),
            {
                "source": source_table.lower(),
                "target": target_table.lower(),
                "conn_name": connection_name,
                "db_type": database_type.lower()
            }
        )

        row = result.fetchone()
        if row:
            return TableMapping(
                id=row[0],
                source_table=row[1],
                target_table=row[2],
                connection_name=row[3],
                database_type=row[4],
                mapping_type=row[5],
                confidence_score=row[6],
                times_applied=row[7],
                description=row[8]
            )

        return None

    async def _get_applicable_mappings(
        self,
        connection_name: str,
        database_type: str
    ) -> List[TableMapping]:
        """
        Get all mappings applicable to this connection and database
        """
        result = await self.db_session.execute(
            text("""
                SELECT
                    id, source_table, target_table, connection_name,
                    database_type, mapping_type, confidence_score,
                    times_applied, description
                FROM table_mappings
                WHERE connection_name = :conn_name
                  AND database_type = :db_type
                ORDER BY
                    confidence_score DESC,
                    times_applied DESC
            """),
            {
                "conn_name": connection_name,
                "db_type": database_type.lower()
            }
        )

        mappings = []
        for row in result.fetchall():
            mappings.append(TableMapping(
                id=row[0],
                source_table=row[1],
                target_table=row[2],
                connection_name=row[3],
                database_type=row[4],
                mapping_type=row[5],
                confidence_score=row[6],
                times_applied=row[7],
                description=row[8]
            ))

        return mappings

    async def _record_mapping_usage(self, mapping_id: int):
        """Record that a mapping was successfully applied"""
        await self.db_session.execute(
            text("""
                UPDATE table_mappings
                SET times_applied = times_applied + 1,
                    last_applied_at = CURRENT_TIMESTAMP
                WHERE id = :mapping_id
            """),
            {"mapping_id": mapping_id}
        )


# Utility functions for table name similarity

def table_similarity(table1: str, table2: str) -> float:
    """
    Calculate similarity between two table names (0.0 to 1.0)

    Uses SequenceMatcher for fuzzy string matching.
    """
    return SequenceMatcher(None, table1.lower(), table2.lower()).ratio()


def find_similar_tables(
    target_table: str,
    available_tables: List[str],
    threshold: float = 0.6
) -> List[Tuple[str, float]]:
    """
    Find tables similar to the target

    Args:
        target_table: The table to match
        available_tables: List of available table names
        threshold: Minimum similarity score (0.0-1.0)

    Returns:
        List of (table_name, similarity_score) tuples, sorted by score
    """
    matches = []

    for table in available_tables:
        similarity = table_similarity(target_table, table)
        if similarity >= threshold:
            matches.append((table, similarity))

    # Sort by similarity score (descending)
    matches.sort(key=lambda x: x[1], reverse=True)

    return matches
