"""
Cleanup test/dummy data from the feedback system

This script identifies and removes test entries from:
- user_feedback table
- learned_corrections table (if orphaned)

SAFETY FEATURES:
- Dry-run mode by default (preview changes)
- Detailed logging of what will be deleted
- Rollback on any errors
- Preserves legitimate user feedback
"""
import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, and_, or_, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_db_manager
from src.database.models import UserFeedback, LearnedCorrection, QueryHistory
from src.config.settings import Settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def identify_test_feedback(db: AsyncSession) -> list[int]:
    """
    Identify feedback entries that appear to be test data

    Test data patterns:
    - Descriptions containing 'test', 'dummy', 'example', 'sample'
    - User notes with 'test' or 'debug'
    - Corrected SQL containing obvious test patterns
    - Feedback for non-existent queries
    """
    test_patterns = [
        '%test%',
        '%dummy%',
        '%example%',
        '%sample%',
        '%debug%',
        '%TODO%',
        '%FIXME%'
    ]

    # Find feedback matching test patterns
    conditions = []
    for pattern in test_patterns:
        conditions.extend([
            UserFeedback.correction_description.ilike(pattern),
            UserFeedback.user_notes.ilike(pattern),
            UserFeedback.corrected_sql.ilike(pattern)
        ])

    stmt = select(UserFeedback.id).where(or_(*conditions))
    result = await db.execute(stmt)
    test_feedback_ids = [row[0] for row in result.all()]

    logger.info(f"Found {len(test_feedback_ids)} feedback entries matching test patterns")

    # Find feedback for non-existent queries (orphaned)
    orphan_stmt = select(UserFeedback.id).where(
        ~UserFeedback.query_id.in_(
            select(QueryHistory.id)
        )
    )
    orphan_result = await db.execute(orphan_stmt)
    orphan_feedback_ids = [row[0] for row in orphan_result.all()]

    logger.info(f"Found {len(orphan_feedback_ids)} orphaned feedback entries (query no longer exists)")

    # Combine and deduplicate
    all_test_ids = list(set(test_feedback_ids + orphan_feedback_ids))

    return all_test_ids


async def preview_deletions(db: AsyncSession, feedback_ids: list[int]):
    """Show what will be deleted"""
    if not feedback_ids:
        logger.info("No test feedback to delete")
        return

    logger.info(f"\n{'='*80}")
    logger.info(f"PREVIEW: {len(feedback_ids)} feedback entries will be deleted:")
    logger.info(f"{'='*80}\n")

    stmt = select(UserFeedback).where(UserFeedback.id.in_(feedback_ids)).limit(10)
    result = await db.execute(stmt)
    sample_feedback = result.scalars().all()

    for i, feedback in enumerate(sample_feedback, 1):
        logger.info(f"\n--- Entry {i} (ID: {feedback.id}) ---")
        logger.info(f"Type: {feedback.feedback_type}")
        logger.info(f"Description: {feedback.correction_description[:100] if feedback.correction_description else 'N/A'}")
        logger.info(f"User Notes: {feedback.user_notes[:100] if feedback.user_notes else 'N/A'}")
        logger.info(f"Created: {feedback.created_at}")
        logger.info(f"Applied: {feedback.applied_successfully}")

    if len(feedback_ids) > 10:
        logger.info(f"\n... and {len(feedback_ids) - 10} more entries")

    logger.info(f"\n{'='*80}\n")


async def cleanup_test_data(dry_run: bool = True):
    """
    Clean up test/dummy feedback data

    Args:
        dry_run: If True, only preview changes without deleting
    """
    # Initialize database manager
    db_manager = get_db_manager(Settings())
    await db_manager.initialize_async()

    async with db_manager.get_async_session() as db:
        try:
            logger.info("🧹 Starting test data cleanup...")
            logger.info(f"Mode: {'DRY RUN (no changes)' if dry_run else 'ACTUAL DELETION'}")

            # Get current counts
            total_feedback = await db.scalar(select(func.count(UserFeedback.id)))
            total_corrections = await db.scalar(select(func.count(LearnedCorrection.id)))

            logger.info(f"\nCurrent database state:")
            logger.info(f"  Total feedback entries: {total_feedback}")
            logger.info(f"  Total learned corrections: {total_corrections}")

            # Identify test data
            test_feedback_ids = await identify_test_feedback(db)

            if not test_feedback_ids:
                logger.info("✅ No test data found. Database is clean!")
                return

            # Preview what will be deleted
            await preview_deletions(db, test_feedback_ids)

            if dry_run:
                logger.info("🔍 DRY RUN MODE: No changes made")
                logger.info(f"Run with dry_run=False to actually delete {len(test_feedback_ids)} entries")
                return

            # Actual deletion
            logger.info(f"⚠️  Deleting {len(test_feedback_ids)} test feedback entries...")

            # Delete feedback entries
            delete_stmt = delete(UserFeedback).where(UserFeedback.id.in_(test_feedback_ids))
            result = await db.execute(delete_stmt)
            deleted_count = result.rowcount

            await db.commit()

            logger.info(f"✅ Successfully deleted {deleted_count} test feedback entries")

            # Check for orphaned learned corrections (no longer referenced by any feedback)
            orphan_corrections_stmt = select(LearnedCorrection.id).where(
                ~LearnedCorrection.id.in_(
                    select(UserFeedback.learned_correction_id).where(
                        UserFeedback.learned_correction_id.isnot(None)
                    )
                )
            )
            orphan_result = await db.execute(orphan_corrections_stmt)
            orphan_correction_ids = [row[0] for row in orphan_result.all()]

            if orphan_correction_ids:
                logger.info(f"\n📋 Found {len(orphan_correction_ids)} orphaned learned corrections")
                logger.info("These corrections are not referenced by any feedback and could be cleaned up")
                logger.info("(Keeping them for now - they may still be useful)")

            # Final counts
            final_feedback = await db.scalar(select(func.count(UserFeedback.id)))
            final_corrections = await db.scalar(select(func.count(LearnedCorrection.id)))

            logger.info(f"\nFinal database state:")
            logger.info(f"  Total feedback entries: {final_feedback} (was {total_feedback})")
            logger.info(f"  Total learned corrections: {final_corrections} (unchanged)")
            logger.info(f"\n🎉 Cleanup complete!")

        except Exception as e:
            await db.rollback()
            logger.error(f"❌ Cleanup failed: {e}", exc_info=True)
            raise


async def main():
    """Run cleanup with user confirmation"""
    logger.info("="*80)
    logger.info("TEST DATA CLEANUP TOOL")
    logger.info("="*80)

    # First, run in dry-run mode
    await cleanup_test_data(dry_run=True)

    # Prompt for actual deletion
    print("\n" + "="*80)
    response = input("\nDo you want to proceed with ACTUAL DELETION? (yes/no): ")
    print("="*80 + "\n")

    if response.lower() == 'yes':
        await cleanup_test_data(dry_run=False)
    else:
        logger.info("Cleanup cancelled by user")


if __name__ == "__main__":
    asyncio.run(main())
