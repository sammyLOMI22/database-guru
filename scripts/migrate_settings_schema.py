import asyncio
import sqlite3
import os
from src.database.connection import DatabaseManager
from src.config.settings import Settings

async def migrate():
    print("🚀 Starting SystemSettings schema migration...")
    settings = Settings()
    db_path = "database_guru.db"
    
    if not os.path.exists(db_path):
        print(f"❌ Database file not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Define missing columns with their types and defaults
    new_columns = [
        # Small Model Optimization / Task Routing
        ("model_sql_generation", "VARCHAR(100)", "NULL"),
        ("model_narratives", "VARCHAR(100)", "NULL"),
        ("model_query_planning", "VARCHAR(100)", "NULL"),
        ("model_error_correction", "VARCHAR(100)", "NULL"),
        
        # Timeouts
        ("timeout_sql_generation", "INTEGER", "30"),
        ("timeout_narratives", "INTEGER", "15"),
        ("timeout_query_planning", "INTEGER", "20"),
        ("timeout_error_correction", "INTEGER", "15"),
        
        # Optimization Flags
        ("enable_query_templates", "BOOLEAN", "1"),
        ("enable_location_preprocessing", "BOOLEAN", "1"),
        
        # Prompt Optimization
        ("enable_prompt_optimization", "BOOLEAN", "0"),
        ("prompt_model_size", "VARCHAR(20)", "'auto'"),
        ("enable_schema_compression", "BOOLEAN", "1"),
        ("max_schema_tables", "INTEGER", "10"),
        ("enable_example_selection", "BOOLEAN", "1"),
        ("max_few_shot_examples", "INTEGER", "3"),
        
        # Semantic Understanding (Phases 1-3)
        ("enable_intent_classification", "BOOLEAN", "1"),
        ("enable_dynamic_examples", "BOOLEAN", "1"),
        ("enable_semantic_validation", "BOOLEAN", "1"),
        
        # Multi-DB
        ("enable_multi_db_validation", "BOOLEAN", "1"),
        ("multi_db_validation_threshold", "FLOAT", "0.6"),
        
        # Query Quality
        ("query_quality_level", "INTEGER", "50")
    ]

    # Get existing columns
    cursor.execute("PRAGMA table_info(system_settings)")
    existing_columns = [row[1] for row in cursor.fetchall()]

    migrated = 0
    for col_name, col_type, default_val in new_columns:
        if col_name not in existing_columns:
            print(f"➕ Adding column: {col_name} ({col_type})")
            try:
                # SQLite ALTER TABLE only supports adding one column at a time
                cursor.execute(f"ALTER TABLE system_settings ADD COLUMN {col_name} {col_type} DEFAULT {default_val}")
                migrated += 1
            except sqlite3.OperationalError as e:
                print(f"⚠️ Error adding {col_name}: {e}")

    conn.commit()
    conn.close()
    print(f"✅ Migration complete. {migrated} columns added.")

if __name__ == "__main__":
    asyncio.run(migrate())
