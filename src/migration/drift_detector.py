"""Schema Drift Detection (Phase 20.1)

Compares a database connection's current live schema against a saved baseline
to detect schema drift over time.
"""

import logging
from typing import Dict, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.schema_cache import SchemaCache
from src.core.user_db_connector import UserDatabaseConnector
from src.database.models import DatabaseConnection
from src.migration.schema_comparator import SchemaComparator, SchemaDiff

logger = logging.getLogger(__name__)


class DriftDetector:
    """Detect schema drift for a single database connection.

    Compares the current live schema against a saved baseline fingerprint
    and full schema snapshot.
    """

    def __init__(self):
        self._comparator = SchemaComparator()

    async def detect_drift(
        self,
        connection: DatabaseConnection,
        baseline_schema: Dict[str, Any],
        baseline_fingerprint: str,
        db: Optional[AsyncSession] = None,
    ) -> SchemaDiff:
        """Compare a connection's current schema against a baseline.

        Args:
            connection: The database connection to introspect.
            baseline_schema: Previously saved schema dict.
            baseline_fingerprint: Previously saved fingerprint.
            db: Metadata DB session (for SchemaCache).

        Returns:
            SchemaDiff showing what changed since baseline.
        """
        # Quick check: get current fingerprint
        current_schema = await self._get_current_schema(connection)
        current_fingerprint = SchemaCache.create_fingerprint_from_schema_dict(current_schema)

        if current_fingerprint == baseline_fingerprint:
            logger.info(f"No drift detected for connection {connection.id} ({connection.name})")
            return SchemaDiff(
                source_connection_id=connection.id,
                target_connection_id=connection.id,
                source_fingerprint=baseline_fingerprint,
                target_fingerprint=current_fingerprint,
                diff_summary="No differences found",
                overall_risk="none",
            )

        logger.info(
            f"Drift detected for connection {connection.id}: "
            f"fingerprint {baseline_fingerprint[:8]}... -> {current_fingerprint[:8]}..."
        )

        return self._comparator.compare(
            source_schema=baseline_schema,
            target_schema=current_schema,
            source_connection_id=connection.id,
            target_connection_id=connection.id,
            source_fingerprint=baseline_fingerprint,
            target_fingerprint=current_fingerprint,
        )

    async def _get_current_schema(
        self, connection: DatabaseConnection,
    ) -> Dict[str, Any]:
        """Fetch the current live schema for a connection."""
        async with UserDatabaseConnector.get_user_db_session(connection) as session:
            schema = await SchemaCache.get_schema(
                connection_id=connection.id,
                connection_name=connection.name,
                user_db_session=session,
                force_refresh=True,
                include_samples=False,
            )
        return schema
