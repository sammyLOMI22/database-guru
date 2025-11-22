"""
Add connection_name field to mapping tables

This updates the non-SQL feedback tables to include connection_name
to support multiple database instances of the same type.

Run with: python scripts/add_connection_name_to_mappings.py

Part of Phase 2: Non-SQL Feedback Implementation - Bugfix
"""
import asyncio
import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.config.settings import Settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = Settings()


ALTER_COLUMN_MAPPINGS = """
ALTER TABLE column_mappings ADD COLUMN connection_name VARCHAR(255) NULL;
"""

ALTER_TABLE_MAPPINGS = """
ALTER TABLE table_mappings ADD COLUMN connection_name VARCHAR(255) NULL;
"""

# Update unique index to include connection_name
DROP_COLUMN_MAPPINGS_INDEX = """
DROP INDEX IF EXISTS idx_column_mappings_unique;
"""

CREATE_COLUMN_MAPPINGS_INDEX = """
CREATE UNIQUE INDEX IF NOT EXISTS idx_column_mappings_unique
    ON column_mappings(
        source_column,
        target_column,
        COALESCE(table_name, ''),
        COALESCE(connection_name, ''),
        database_type
    );
"""

DROP_TABLE_MAPPINGS_INDEX = """
DROP INDEX IF EXISTS idx_table_mappings_unique;
"""

CREATE_TABLE_MAPPINGS_INDEX = """
CREATE UNIQUE INDEX IF NOT EXISTS idx_table_mappings_unique
    ON table_mappings(
        source_table,
        target_table,
        COALESCE(connection_name, ''),
        database_type
    );
"""

# Add index on connection_name
CREATE_COLUMN_MAPPINGS_CONNECTION_INDEX = """
CREATE INDEX IF NOT EXISTS idx_column_mappings_connection ON column_mappings(connection_name);
"""

CREATE_TABLE_MAPPINGS_CONNECTION_INDEX = """
CREATE INDEX IF NOT EXISTS idx_table_mappings_connection ON table_mappings(connection_name);
"""


async def run_migration():
    """Run the migration to add connection_name"""
    try:
        logger.info("🚀 Starting connection_name migration...")

        engine = create_async_engine(
            settings.DATABASE_URL,
            echo=False
        )

        async with engine.begin() as conn:
            # Add connection_name column to column_mappings
            logger.info("Adding connection_name to column_mappings...")
            await conn.execute(text(ALTER_COLUMN_MAPPINGS))

            # Add connection_name column to table_mappings
            logger.info("Adding connection_name to table_mappings...")
            await conn.execute(text(ALTER_TABLE_MAPPINGS))

            # Update unique indexes
            logger.info("Updating unique indexes...")
            await conn.execute(text(DROP_COLUMN_MAPPINGS_INDEX))
            await conn.execute(text(CREATE_COLUMN_MAPPINGS_INDEX))
            await conn.execute(text(DROP_TABLE_MAPPINGS_INDEX))
            await conn.execute(text(CREATE_TABLE_MAPPINGS_INDEX))

            # Add connection_name indexes
            logger.info("Adding connection_name indexes...")
            await conn.execute(text(CREATE_COLUMN_MAPPINGS_CONNECTION_INDEX))
            await conn.execute(text(CREATE_TABLE_MAPPINGS_CONNECTION_INDEX))

        logger.info("✅ Migration completed successfully!")

        # Verify
        async with engine.connect() as conn:
            result = await conn.execute(text("PRAGMA table_info(column_mappings)"))
            columns = result.fetchall()
            connection_name_exists = any(col[1] == 'connection_name' for col in columns)

            if connection_name_exists:
                logger.info("✅ Verified: connection_name column added to column_mappings")
            else:
                logger.error("❌ Verification failed: connection_name column not found")
                return False

        await engine.dispose()
        return True

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}", exc_info=True)
        return False


async def rollback_migration():
    """Rollback the migration (remove connection_name)"""
    logger.warning("🔄 Rolling back migration...")

    try:
        engine = create_async_engine(
            settings.DATABASE_URL,
            echo=False
        )

        async with engine.begin() as conn:
            # SQLite doesn't support DROP COLUMN directly, so we need to recreate tables
            logger.info("⚠️  SQLite doesn't support DROP COLUMN.")
            logger.info("   To rollback, you need to manually recreate the tables")
            logger.info("   or restore from backup.")

        await engine.dispose()

    except Exception as e:
        logger.error(f"❌ Rollback failed: {e}", exc_info=True)


async def main():
    """Main entry point"""
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--rollback":
        await rollback_migration()
        return

    # Run migration
    success = await run_migration()

    if success:
        logger.info("\n✨ Migration complete!")
        logger.info("\n📝 Key changes:")
        logger.info("   - Added connection_name to column_mappings")
        logger.info("   - Added connection_name to table_mappings")
        logger.info("   - Updated unique indexes to include connection_name")
        logger.info("   - Added indexes on connection_name for performance")
        logger.info("\n⚠️  IMPORTANT: Update all code to pass connection_name parameter!")
        logger.info("   - ColumnMapper.learn_from_feedback(connection_name=...)")
        logger.info("   - ColumnMapper.apply_mappings(connection_name=...)")
        logger.info("   - TableMapper methods (when implemented)")
    else:
        logger.error("\n❌ Migration failed. Check logs for details.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
