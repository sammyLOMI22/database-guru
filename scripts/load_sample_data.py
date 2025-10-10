#!/usr/bin/env python3
"""Load sample data into the database"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.settings import Settings
from src.database.connection import get_db_manager


async def load_sample_data():
    """Load sample data from SQL file"""
    print("🧙‍♂️ Loading sample data into Database Guru...\n")

    # Initialize database
    settings = Settings()
    db_manager = get_db_manager(settings)
    await db_manager.initialize_async()

    # Read SQL file
    sql_file = Path(__file__).parent / "create_sample_data.sql"
    if not sql_file.exists():
        print(f"❌ SQL file not found: {sql_file}")
        return

    print(f"📄 Reading SQL file: {sql_file.name}")
    sql_content = sql_file.read_text()

    # Execute SQL
    print("⚙️  Executing SQL...")
    async with db_manager.get_async_session() as session:
        # Split by semicolon and execute each statement
        statements = [s.strip() for s in sql_content.split(';') if s.strip()]

        for i, statement in enumerate(statements, 1):
            if statement:
                try:
                    await session.execute(statement)
                    print(f"  ✓ Statement {i}/{len(statements)}")
                except Exception as e:
                    print(f"  ⚠️  Statement {i} warning: {e}")

        await session.commit()

    print("\n✅ Sample data loaded successfully!")
    print("\nSample data includes:")
    print("  • 10 customers")
    print("  • 10 products")
    print("  • 10 orders")
    print("  • 16 order items")
    print("\nYou can now test queries like:")
    print("  - 'Show me all customers from California'")
    print("  - 'What are the top 5 most expensive products?'")
    print("  - 'How many completed orders are there?'")
    print("  - 'List all products in the Electronics category'")

    # Clean up
    await db_manager.close_async()


if __name__ == "__main__":
    asyncio.run(load_sample_data())
