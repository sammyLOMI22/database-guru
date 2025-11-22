"""
Add database tables for non-SQL feedback handling

This script creates three new tables:
1. column_mappings - Store column name aliases and corrections
2. table_mappings - Store table name aliases and corrections
3. result_validation_patterns - Store learned result validation patterns

Run with: python scripts/add_non_sql_feedback_tables.py

Part of Phase 2: Non-SQL Feedback Implementation
"""
import asyncio
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.config.settings import Settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = Settings()


# SQL for creating the new tables
CREATE_COLUMN_MAPPINGS_TABLE = """
CREATE TABLE IF NOT EXISTS column_mappings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Mapping details
    source_column VARCHAR(255) NOT NULL,
    target_column VARCHAR(255) NOT NULL,
    table_name VARCHAR(255) NULL,
    database_type VARCHAR(50) NOT NULL,

    -- Context
    description TEXT NULL,
    example_query TEXT NULL,

    -- Learning metadata
    times_applied INTEGER DEFAULT 0,
    success_rate REAL DEFAULT 1.0,
    confidence_score REAL DEFAULT 1.0,

    -- Source tracking
    learned_from_feedback_id INTEGER NULL,
    created_by VARCHAR(50) DEFAULT 'system',

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_applied_at TIMESTAMP NULL,

    -- Foreign key
    FOREIGN KEY (learned_from_feedback_id) REFERENCES user_feedback(id) ON DELETE SET NULL
);
"""

CREATE_COLUMN_MAPPINGS_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_column_mappings_source ON column_mappings(source_column)",
    "CREATE INDEX IF NOT EXISTS idx_column_mappings_target ON column_mappings(target_column)",
    "CREATE INDEX IF NOT EXISTS idx_column_mappings_table ON column_mappings(table_name)",
    "CREATE INDEX IF NOT EXISTS idx_column_mappings_database ON column_mappings(database_type)",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_column_mappings_unique ON column_mappings(source_column, target_column, COALESCE(table_name, ''), database_type)"
]

CREATE_TABLE_MAPPINGS_TABLE = """
CREATE TABLE IF NOT EXISTS table_mappings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Mapping details
    source_table VARCHAR(255) NOT NULL,
    target_table VARCHAR(255) NOT NULL,
    database_type VARCHAR(50) NOT NULL,

    -- Context
    description TEXT NULL,
    example_query TEXT NULL,
    mapping_type VARCHAR(50) DEFAULT 'alias',

    -- Learning metadata
    times_applied INTEGER DEFAULT 0,
    success_rate REAL DEFAULT 1.0,
    confidence_score REAL DEFAULT 1.0,

    -- Source tracking
    learned_from_feedback_id INTEGER NULL,
    created_by VARCHAR(50) DEFAULT 'system',

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_applied_at TIMESTAMP NULL,

    -- Foreign key
    FOREIGN KEY (learned_from_feedback_id) REFERENCES user_feedback(id) ON DELETE SET NULL
);
"""

CREATE_TABLE_MAPPINGS_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_table_mappings_source ON table_mappings(source_table)",
    "CREATE INDEX IF NOT EXISTS idx_table_mappings_target ON table_mappings(target_table)",
    "CREATE INDEX IF NOT EXISTS idx_table_mappings_database ON table_mappings(database_type)",
    "CREATE INDEX IF NOT EXISTS idx_table_mappings_type ON table_mappings(mapping_type)",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_table_mappings_unique ON table_mappings(source_table, target_table, database_type)"
]

CREATE_RESULT_VALIDATION_PATTERNS_TABLE = """
CREATE TABLE IF NOT EXISTS result_validation_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Pattern details
    pattern_type VARCHAR(50) NOT NULL,
    pattern_description TEXT NOT NULL,

    -- Matching criteria (JSON)
    matching_criteria TEXT NOT NULL,

    -- Action to take
    action VARCHAR(50) NOT NULL,
    suggestion TEXT NULL,

    -- Learning metadata
    times_triggered INTEGER DEFAULT 0,
    times_helpful INTEGER DEFAULT 0,
    confidence_score REAL DEFAULT 1.0,

    -- Source tracking
    learned_from_feedback_id INTEGER NULL,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_triggered_at TIMESTAMP NULL,

    -- Foreign key
    FOREIGN KEY (learned_from_feedback_id) REFERENCES user_feedback(id) ON DELETE SET NULL
);
"""

CREATE_RESULT_VALIDATION_PATTERNS_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_result_patterns_type ON result_validation_patterns(pattern_type)",
    "CREATE INDEX IF NOT EXISTS idx_result_patterns_confidence ON result_validation_patterns(confidence_score)",
    "CREATE INDEX IF NOT EXISTS idx_result_patterns_action ON result_validation_patterns(action)"
]


async def run_migration():
    """Run the database migration"""
    try:
        logger.info("🚀 Starting non-SQL feedback tables migration...")

        # Create async engine
        engine = create_async_engine(
            settings.DATABASE_URL,
            echo=False
        )

        async with engine.begin() as conn:
            # Create column_mappings table
            logger.info("Creating column_mappings table...")
            await conn.execute(text(CREATE_COLUMN_MAPPINGS_TABLE))
            for index_sql in CREATE_COLUMN_MAPPINGS_INDEXES:
                await conn.execute(text(index_sql))
            logger.info("✅ column_mappings table created")

            # Create table_mappings table
            logger.info("Creating table_mappings table...")
            await conn.execute(text(CREATE_TABLE_MAPPINGS_TABLE))
            for index_sql in CREATE_TABLE_MAPPINGS_INDEXES:
                await conn.execute(text(index_sql))
            logger.info("✅ table_mappings table created")

            # Create result_validation_patterns table
            logger.info("Creating result_validation_patterns table...")
            await conn.execute(text(CREATE_RESULT_VALIDATION_PATTERNS_TABLE))
            for index_sql in CREATE_RESULT_VALIDATION_PATTERNS_INDEXES:
                await conn.execute(text(index_sql))
            logger.info("✅ result_validation_patterns table created")

        # Verify tables were created
        async with engine.connect() as conn:
            result = await conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('column_mappings', 'table_mappings', 'result_validation_patterns')"
            ))
            tables = [row[0] for row in result.fetchall()]

            logger.info(f"\n📊 Verification:")
            logger.info(f"   Tables created: {', '.join(tables)}")

            if len(tables) == 3:
                logger.info("\n🎉 Migration completed successfully!")
                logger.info("\n📝 Summary:")
                logger.info("   - column_mappings: Ready for column name corrections")
                logger.info("   - table_mappings: Ready for table name corrections")
                logger.info("   - result_validation_patterns: Ready for result issue learning")
            else:
                logger.error(f"\n❌ Migration incomplete! Only {len(tables)}/3 tables created")
                return False

        await engine.dispose()
        return True

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}", exc_info=True)
        return False


async def verify_tables():
    """Verify the new tables exist and show sample structure"""
    try:
        engine = create_async_engine(
            settings.DATABASE_URL,
            echo=False
        )

        async with engine.connect() as conn:
            logger.info("\n🔍 Verifying table structures...")

            # Check column_mappings
            result = await conn.execute(text("PRAGMA table_info(column_mappings)"))
            columns = result.fetchall()
            logger.info(f"\n📊 column_mappings ({len(columns)} columns):")
            for col in columns:
                logger.info(f"   - {col[1]}: {col[2]}")

            # Check table_mappings
            result = await conn.execute(text("PRAGMA table_info(table_mappings)"))
            columns = result.fetchall()
            logger.info(f"\n📊 table_mappings ({len(columns)} columns):")
            for col in columns:
                logger.info(f"   - {col[1]}: {col[2]}")

            # Check result_validation_patterns
            result = await conn.execute(text("PRAGMA table_info(result_validation_patterns)"))
            columns = result.fetchall()
            logger.info(f"\n📊 result_validation_patterns ({len(columns)} columns):")
            for col in columns:
                logger.info(f"   - {col[1]}: {col[2]}")

        await engine.dispose()

    except Exception as e:
        logger.error(f"Verification failed: {e}", exc_info=True)


async def rollback_migration():
    """Rollback the migration (drop the new tables)"""
    logger.warning("🔄 Rolling back migration...")

    try:
        engine = create_async_engine(
            settings.DATABASE_URL,
            echo=False
        )

        async with engine.begin() as conn:
            await conn.execute(text("DROP TABLE IF EXISTS column_mappings"))
            await conn.execute(text("DROP TABLE IF EXISTS table_mappings"))
            await conn.execute(text("DROP TABLE IF EXISTS result_validation_patterns"))

        logger.info("✅ Migration rolled back successfully")
        await engine.dispose()

    except Exception as e:
        logger.error(f"❌ Rollback failed: {e}", exc_info=True)


async def main():
    """Main entry point"""
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--rollback":
        await rollback_migration()
        return

    if len(sys.argv) > 1 and sys.argv[1] == "--verify":
        await verify_tables()
        return

    # Run migration
    success = await run_migration()

    if success:
        # Show table structures
        await verify_tables()

        logger.info("\n✨ Next steps:")
        logger.info("   1. Implement ColumnMapper class (src/llm/column_mapper.py)")
        logger.info("   2. Implement TableMapper class (src/llm/table_mapper.py)")
        logger.info("   3. Implement ResultPatternLearner class (src/llm/result_pattern_learner.py)")
        logger.info("   4. Update feedback.py endpoint to handle non-SQL feedback types")
        logger.info("\n📖 See docs/NON_SQL_FEEDBACK_DESIGN.md for full implementation plan")
    else:
        logger.error("\n❌ Migration failed. Check logs for details.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
