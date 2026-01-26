"""One-time migration: Add connection_id column to query_history."""
import sqlite3
import sys


def migrate(db_path: str = "database_guru.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if column exists
    cursor.execute("PRAGMA table_info(query_history)")
    columns = [row[1] for row in cursor.fetchall()]

    if "connection_id" not in columns:
        cursor.execute(
            "ALTER TABLE query_history ADD COLUMN connection_id INTEGER "
            "REFERENCES database_connections(id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_connection_created "
            "ON query_history (connection_id, created_at)"
        )
        conn.commit()
        print("Migration successful: added connection_id to query_history")
    else:
        print("Column already exists, skipping migration")

    conn.close()


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "database_guru.db"
    migrate(path)
