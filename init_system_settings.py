"""Initialize system settings table"""
import asyncio
from src.database.connection import DatabaseManager
from src.database.models import Base, SystemSettings
from src.config.settings import Settings
from sqlalchemy import text, select

async def init_settings():
    """Create system_settings table and initialize default settings"""
    settings = Settings()
    db_manager = DatabaseManager(settings)
    await db_manager.initialize_async()

    async with db_manager.async_engine.begin() as conn:
        # Create the table if it doesn't exist
        print("Creating system_settings table if not exists...")
        await conn.run_sync(Base.metadata.create_all, tables=[SystemSettings.__table__])
        print("✅ system_settings table created")

    # Initialize default settings if not exists
    async with db_manager.get_async_session() as session:
        result = await session.execute(select(SystemSettings).limit(1))
        existing = result.scalar_one_or_none()

        if not existing:
            print("Initializing default system settings...")
            default_settings = SystemSettings(
                # Auto-Learning Settings
                auto_learning_enabled=False,
                confidence_threshold=0.80,
                apply_mode="immediate",
                test_before_learning=True,
                validation_mode="strict",
                require_result_comparison=True,
                # Security Settings
                allow_destructive_auto_learn=False,
                require_admin_approval=True,
                # Audit Settings
                enable_audit_log=True,
                max_audit_log_days=90,
            )
            session.add(default_settings)
            await session.commit()
            print("✅ Default settings initialized")
            print(f"\n   🤖 Auto-Learning:")
            print(f"   - Enabled: {default_settings.auto_learning_enabled}")
            print(f"   - Confidence threshold: {default_settings.confidence_threshold * 100}%")
            print(f"   - Apply mode: {default_settings.apply_mode}")
            print(f"   - Test before learning: {default_settings.test_before_learning}")
            print(f"   - Validation mode: {default_settings.validation_mode}")
            print(f"\n   🛡️  Security:")
            print(f"   - Allow destructive auto-learn: {default_settings.allow_destructive_auto_learn}")
            print(f"   - Require admin approval: {default_settings.require_admin_approval}")
            print(f"\n   📋 Audit:")
            print(f"   - Enable audit log: {default_settings.enable_audit_log}")
            print(f"   - Max audit log days: {default_settings.max_audit_log_days}")
        else:
            print("✅ System settings already exist")
            print(f"\n   🤖 Auto-Learning:")
            print(f"   - Enabled: {existing.auto_learning_enabled}")
            print(f"   - Confidence threshold: {existing.confidence_threshold * 100}%")
            print(f"   - Validation mode: {getattr(existing, 'validation_mode', 'N/A')}")
            print(f"\n   🛡️  Security:")
            print(f"   - Allow destructive: {getattr(existing, 'allow_destructive_auto_learn', 'N/A')}")
            print(f"   - Require admin: {getattr(existing, 'require_admin_approval', 'N/A')}")

    await db_manager.close_async()
    print("\n✅ System settings initialized successfully!")

if __name__ == "__main__":
    asyncio.run(init_settings())
