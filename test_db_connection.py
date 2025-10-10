"""Quick test script for database connection"""
import asyncio
from src.config.settings import Settings
from src.database.connection import get_db_manager


async def test_connection():
    """Test database connection"""
    print("🧪 Testing Database Connection...\n")

    # Load settings
    settings = Settings()
    print(f"Database URL: {settings.DATABASE_URL}")

    # Get database manager
    db_manager = get_db_manager(settings)

    # Initialize async engine
    print("\n📡 Initializing async database engine...")
    await db_manager.initialize_async()

    # Health check
    print("\n💚 Running health check...")
    is_healthy = await db_manager.health_check()

    if is_healthy:
        print("✅ Database connection successful!")
    else:
        print("❌ Database connection failed!")

    # Create tables
    print("\n📋 Creating database tables...")
    await db_manager.create_tables_async()
    print("✅ Tables created!")

    # Clean up
    await db_manager.close_async()
    print("\n✨ Test complete!")


if __name__ == "__main__":
    asyncio.run(test_connection())
