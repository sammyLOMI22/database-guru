#!/usr/bin/env python3
"""
Script to fix active_connection_ids in chat_sessions table.
Ensures all values are proper JSON arrays, not integers.
"""
import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select
from src.config.settings import Settings
from src.database.connection import get_db_manager
from src.database.models import ChatSession

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def fix_connection_ids():
    """Fix any malformed active_connection_ids in the database."""
    print("🔧 Checking chat sessions for malformed connection IDs...\n")

    # Initialize database
    settings = Settings()
    db_manager = get_db_manager(settings)
    await db_manager.initialize_async()

    async with db_manager.get_async_session() as db:
        # Get all chat sessions
        result = await db.execute(select(ChatSession))
        sessions = result.scalars().all()

        if not sessions:
            print("ℹ️  No chat sessions found in database")
            return

        fixed_count = 0
        ok_count = 0

        for session in sessions:
            conn_ids = session.active_connection_ids

            # Check if it's already a list
            if isinstance(conn_ids, list):
                print(f"✓ Session '{session.name}' ({session.id[:8]}...) - OK: {conn_ids}")
                ok_count += 1
                continue

            # Fix if it's an integer
            if isinstance(conn_ids, int):
                print(f"⚠️  Session '{session.name}' ({session.id[:8]}...) - FIXING: {conn_ids} -> [{conn_ids}]")
                session.active_connection_ids = [conn_ids]
                fixed_count += 1
            # Fix if it's something else
            elif conn_ids is not None:
                print(f"⚠️  Session '{session.name}' ({session.id[:8]}...) - CONVERTING: {conn_ids!r} (type: {type(conn_ids).__name__})")
                try:
                    session.active_connection_ids = list(conn_ids)
                    fixed_count += 1
                except Exception as e:
                    print(f"❌ Failed to convert {conn_ids!r}: {e}")

        if fixed_count > 0:
            await db.commit()
            print(f"\n✅ Fixed {fixed_count} chat session(s)")
        else:
            print(f"\n✅ All {ok_count} session(s) already have correct format")


if __name__ == "__main__":
    asyncio.run(fix_connection_ids())
