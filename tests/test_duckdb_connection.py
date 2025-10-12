#!/usr/bin/env python3
"""
Test DuckDB connection functionality
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.connection_tester import ConnectionTester
from src.core.user_db_connector import UserDatabaseConnector
from src.database.models import DatabaseConnection


async def test_duckdb_connection():
    """Test DuckDB connection"""
    print("Testing DuckDB Connection...")
    print("=" * 50)

    # Path to sample database
    db_path = Path(__file__).parent.parent / "sample_ecommerce.duckdb"

    if not db_path.exists():
        print(f"Error: Sample database not found at {db_path}")
        print("Please run: python scripts/create_sample_duckdb.py")
        return False

    print(f"\n1. Testing connection to: {db_path}")

    # Test connection
    tester = ConnectionTester()
    result = await tester.test_connection(
        database_type="duckdb",
        host="",
        port=0,
        database_name=str(db_path),
        username="",
        password="",
    )

    print(f"\nConnection test result:")
    print(f"  Success: {result['success']}")
    print(f"  Message: {result['message']}")

    if not result["success"]:
        return False

    # Test building connection URL
    print(f"\n2. Testing connection URL building...")
    mock_connection = DatabaseConnection(
        id=1,
        name="Test DuckDB",
        database_type="duckdb",
        database_name=str(db_path),
    )

    url = UserDatabaseConnector.build_connection_url(mock_connection)
    print(f"  Connection URL: {url}")

    # Test querying
    print(f"\n3. Testing database query...")
    try:
        async with UserDatabaseConnector.get_user_db_session(mock_connection) as session:
            from sqlalchemy import text
            from sqlalchemy.orm import Session

            # Check if it's a sync session (DuckDB)
            is_sync = isinstance(session, Session)

            # Test simple query
            if is_sync:
                result = session.execute(text("SELECT COUNT(*) as count FROM products"))
            else:
                result = await session.execute(text("SELECT COUNT(*) as count FROM products"))

            row = result.fetchone()
            print(f"  Products count: {row[0]}")

            # Test table listing
            if is_sync:
                result = session.execute(
                    text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'")
                )
            else:
                result = await session.execute(
                    text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'")
                )
            tables = [row[0] for row in result.fetchall()]
            print(f"  Tables found: {', '.join(tables)}")

            # Test sample query
            if is_sync:
                result = session.execute(
                    text("SELECT name, price FROM products LIMIT 5")
                )
            else:
                result = await session.execute(
                    text("SELECT name, price FROM products LIMIT 5")
                )
            print(f"\n  Sample products:")
            for row in result.fetchall():
                print(f"    - {row[0]}: ${row[1]}")

        print(f"\n✅ All DuckDB tests passed!")
        return True

    except Exception as e:
        print(f"\n❌ Error querying database: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_duckdb_connection())
    sys.exit(0 if success else 1)
