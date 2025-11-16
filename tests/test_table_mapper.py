"""
Tests for Table Mapper

Tests the table name mapping and learning system for handling
user feedback about table name corrections.

Part of Phase 2: Non-SQL Feedback Implementation
"""
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from src.database.models import Base
from src.llm.table_mapper import (
    TableMapper,
    TableMapping,
    table_similarity,
    find_similar_tables
)


@pytest.fixture
async def db_session():
    """Create a test async database session with table_mappings table"""
    # Use in-memory SQLite for testing (async version)
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    # Create all tables including table_mappings
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Create table_mappings table (since it's not in Base.metadata yet)
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS table_mappings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_table VARCHAR(255) NOT NULL,
                target_table VARCHAR(255) NOT NULL,
                connection_name VARCHAR(255) NOT NULL,
                database_type VARCHAR(50) NOT NULL,
                description TEXT NULL,
                example_query TEXT NULL,
                mapping_type VARCHAR(50) DEFAULT 'alias',
                times_applied INTEGER DEFAULT 0,
                success_rate REAL DEFAULT 1.0,
                confidence_score REAL DEFAULT 1.0,
                learned_from_feedback_id INTEGER NULL,
                created_by VARCHAR(50) DEFAULT 'system',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_applied_at TIMESTAMP NULL
            )
        """))

    # Create session factory
    AsyncSessionLocal = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    # Create and yield session
    async with AsyncSessionLocal() as session:
        yield session

    # Cleanup
    await engine.dispose()


@pytest.fixture
async def table_mapper(db_session: AsyncSession) -> TableMapper:
    """Create a TableMapper instance for testing"""
    return TableMapper(db_session=db_session)


class TestTableMapperLearning:
    """Test learning table mappings from feedback"""

    @pytest.mark.asyncio
    async def test_learn_basic_mapping(self, table_mapper: TableMapper, db_session: AsyncSession):
        """Test learning a basic table mapping"""
        mapping_id = await table_mapper.learn_from_feedback(
            source_table="users",
            target_table="customers",
            connection_name="test_db",
            database_type="postgres",
            feedback_id=1,
            description="User correction: users → customers",
            mapping_type="alias",
            confidence_score=0.95
        )

        assert mapping_id > 0

        # Verify mapping was created
        result = await db_session.execute(
            text("SELECT * FROM table_mappings WHERE id = :id"),
            {"id": mapping_id}
        )
        row = result.fetchone()

        assert row is not None
        assert row[1] == "users"  # source_table
        assert row[2] == "customers"  # target_table
        assert row[3] == "test_db"  # connection_name
        assert row[4] == "postgres"  # database_type
        assert row[7] == "alias"  # mapping_type
        assert row[10] == 0.95  # confidence_score

    @pytest.mark.asyncio
    async def test_learn_duplicate_mapping_updates(self, table_mapper: TableMapper, db_session: AsyncSession):
        """Test that learning a duplicate mapping updates the existing one"""
        # Create first mapping
        mapping_id1 = await table_mapper.learn_from_feedback(
            source_table="orders",
            target_table="sales",
            connection_name="test_db",
            database_type="postgres",
            feedback_id=3,
            confidence_score=0.80
        )

        # Try to create duplicate
        mapping_id2 = await table_mapper.learn_from_feedback(
            source_table="orders",
            target_table="sales",
            connection_name="test_db",
            database_type="postgres",
            feedback_id=4,
            confidence_score=0.95  # Higher confidence
        )

        # Should return same ID
        assert mapping_id1 == mapping_id2

        # Verify confidence was updated
        result = await db_session.execute(
            text("SELECT confidence_score FROM table_mappings WHERE id = :id"),
            {"id": mapping_id1}
        )
        row = result.fetchone()
        assert row[0] == 0.95

    @pytest.mark.asyncio
    async def test_learn_case_insensitive(self, table_mapper: TableMapper, db_session: AsyncSession):
        """Test that table names are stored in lowercase"""
        mapping_id = await table_mapper.learn_from_feedback(
            source_table="Users",  # Mixed case
            target_table="Customers",
            connection_name="test_db",
            database_type="PostgreSQL",  # Mixed case
            feedback_id=5
        )

        result = await db_session.execute(
            text("SELECT source_table, target_table, database_type FROM table_mappings WHERE id = :id"),
            {"id": mapping_id}
        )
        row = result.fetchone()

        assert row[0] == "users"  # Lowercase
        assert row[1] == "customers"  # Lowercase
        assert row[2] == "postgresql"  # Lowercase

    @pytest.mark.asyncio
    async def test_learn_different_mapping_types(self, table_mapper: TableMapper, db_session: AsyncSession):
        """Test learning mappings with different types"""
        # Alias mapping
        alias_id = await table_mapper.learn_from_feedback(
            source_table="usr",
            target_table="users",
            connection_name="test_db",
            database_type="postgres",
            feedback_id=6,
            mapping_type="alias"
        )

        # Typo mapping
        typo_id = await table_mapper.learn_from_feedback(
            source_table="prodcuts",
            target_table="products",
            connection_name="test_db",
            database_type="postgres",
            feedback_id=7,
            mapping_type="typo"
        )

        # Verify both were created
        result = await db_session.execute(
            text("SELECT id, mapping_type FROM table_mappings WHERE id IN (:id1, :id2)"),
            {"id1": alias_id, "id2": typo_id}
        )
        rows = result.fetchall()
        assert len(rows) == 2

        types = {row[1] for row in rows}
        assert "alias" in types
        assert "typo" in types


class TestTableMapperApplication:
    """Test applying table mappings to SQL"""

    @pytest.mark.asyncio
    async def test_apply_simple_mapping(self, table_mapper: TableMapper, db_session: AsyncSession):
        """Test applying a single table mapping"""
        # Create mapping
        await table_mapper.learn_from_feedback(
            source_table="users",
            target_table="customers",
            connection_name="test_db",
            database_type="postgres",
            feedback_id=10
        )

        # Apply to SQL
        sql = "SELECT * FROM users WHERE active = true"
        corrected_sql, applied = await table_mapper.apply_mappings(
            sql=sql,
            connection_name="test_db",
            database_type="postgres"
        )

        assert "customers" in corrected_sql
        assert corrected_sql == "SELECT * FROM customers WHERE active = true"
        assert len(applied) == 1
        assert "users → customers" in applied[0]

    @pytest.mark.asyncio
    async def test_apply_multiple_mappings(self, table_mapper: TableMapper, db_session: AsyncSession):
        """Test applying multiple table mappings in one query"""
        # Create mappings
        await table_mapper.learn_from_feedback(
            source_table="users",
            target_table="customers",
            connection_name="test_db",
            database_type="postgres",
            feedback_id=11
        )
        await table_mapper.learn_from_feedback(
            source_table="orders",
            target_table="sales",
            connection_name="test_db",
            database_type="postgres",
            feedback_id=12
        )

        # Apply to SQL with JOIN
        sql = "SELECT * FROM users JOIN orders ON users.id = orders.user_id"
        corrected_sql, applied = await table_mapper.apply_mappings(
            sql=sql,
            connection_name="test_db",
            database_type="postgres"
        )

        assert "customers" in corrected_sql
        assert "sales" in corrected_sql
        assert len(applied) == 2

    @pytest.mark.asyncio
    async def test_apply_word_boundary_matching(self, table_mapper: TableMapper, db_session: AsyncSession):
        """Test that mappings respect word boundaries (no partial matches)"""
        # Create mapping for "user"
        await table_mapper.learn_from_feedback(
            source_table="user",
            target_table="customer",
            connection_name="test_db",
            database_type="postgres",
            feedback_id=13
        )

        # SQL with "users" (should NOT be replaced because it's a different word)
        sql = "SELECT * FROM user, users"
        corrected_sql, applied = await table_mapper.apply_mappings(
            sql=sql,
            connection_name="test_db",
            database_type="postgres"
        )

        # "user" should be replaced, but "users" should remain
        assert "customer" in corrected_sql
        assert "users" in corrected_sql  # Unchanged
        assert len(applied) == 1

    @pytest.mark.asyncio
    async def test_apply_no_mappings(self, table_mapper: TableMapper, db_session: AsyncSession):
        """Test that SQL is unchanged when no mappings apply"""
        sql = "SELECT * FROM products WHERE category = 'electronics'"
        corrected_sql, applied = await table_mapper.apply_mappings(
            sql=sql,
            connection_name="test_db",
            database_type="postgres"
        )

        assert corrected_sql == sql
        assert len(applied) == 0

    @pytest.mark.asyncio
    async def test_apply_updates_usage_statistics(self, table_mapper: TableMapper, db_session: AsyncSession):
        """Test that applying a mapping updates times_applied counter"""
        # Create mapping
        mapping_id = await table_mapper.learn_from_feedback(
            source_table="orders",
            target_table="sales",
            connection_name="test_db",
            database_type="postgres",
            feedback_id=14
        )

        # Apply once
        await table_mapper.apply_mappings(
            sql="SELECT * FROM orders",
            connection_name="test_db",
            database_type="postgres"
        )

        # Check times_applied
        result = await db_session.execute(
            text("SELECT times_applied FROM table_mappings WHERE id = :id"),
            {"id": mapping_id}
        )
        row = result.fetchone()
        assert row[0] == 1

        # Apply again
        await table_mapper.apply_mappings(
            sql="SELECT COUNT(*) FROM orders WHERE status = 'pending'",
            connection_name="test_db",
            database_type="postgres"
        )

        # Check times_applied again
        result = await db_session.execute(
            text("SELECT times_applied FROM table_mappings WHERE id = :id"),
            {"id": mapping_id}
        )
        row = result.fetchone()
        assert row[0] == 2

    @pytest.mark.asyncio
    async def test_apply_case_insensitive(self, table_mapper: TableMapper, db_session: AsyncSession):
        """Test that mappings work case-insensitively"""
        # Create mapping
        await table_mapper.learn_from_feedback(
            source_table="users",
            target_table="customers",
            connection_name="test_db",
            database_type="postgres",
            feedback_id=15
        )

        # Apply to SQL with different case
        sql = "SELECT * FROM Users WHERE active = true"
        corrected_sql, applied = await table_mapper.apply_mappings(
            sql=sql,
            connection_name="test_db",
            database_type="postgres"
        )

        assert "customers" in corrected_sql
        assert len(applied) == 1


class TestTableMapperSuggestions:
    """Test table name suggestions"""

    @pytest.mark.asyncio
    async def test_suggest_exact_match(self, table_mapper: TableMapper, db_session: AsyncSession):
        """Test suggesting table name with exact match"""
        # Create mapping
        await table_mapper.learn_from_feedback(
            source_table="usr",
            target_table="users",
            connection_name="test_db",
            database_type="postgres",
            feedback_id=20,
            confidence_score=0.95
        )

        # Get suggestion
        suggestion = await table_mapper.suggest_correct_table(
            incorrect_table="usr",
            connection_name="test_db",
            database_type="postgres"
        )

        assert suggestion == "users"

    @pytest.mark.asyncio
    async def test_suggest_no_match(self, table_mapper: TableMapper, db_session: AsyncSession):
        """Test that None is returned when no mapping exists"""
        suggestion = await table_mapper.suggest_correct_table(
            incorrect_table="nonexistent_table",
            connection_name="test_db",
            database_type="postgres"
        )

        assert suggestion is None

    @pytest.mark.asyncio
    async def test_suggest_low_confidence_filtered(self, table_mapper: TableMapper, db_session: AsyncSession):
        """Test that low-confidence mappings are filtered out"""
        # Create low-confidence mapping
        await table_mapper.learn_from_feedback(
            source_table="ord",
            target_table="orders",
            connection_name="test_db",
            database_type="postgres",
            feedback_id=21,
            confidence_score=0.50  # Low confidence
        )

        # Should not suggest (default min_confidence=0.6)
        suggestion = await table_mapper.suggest_correct_table(
            incorrect_table="ord",
            connection_name="test_db",
            database_type="postgres"
        )

        assert suggestion is None

        # Should suggest with lower threshold
        suggestion = await table_mapper.suggest_correct_table(
            incorrect_table="ord",
            connection_name="test_db",
            database_type="postgres",
            min_confidence=0.4
        )

        assert suggestion == "orders"


class TestTableMapperStats:
    """Test mapping statistics"""

    @pytest.mark.asyncio
    async def test_get_stats_empty(self, table_mapper: TableMapper):
        """Test stats when no mappings exist"""
        stats = await table_mapper.get_mapping_stats()

        assert stats["total_mappings"] == 0
        assert stats["total_applications"] == 0
        assert stats["alias_mappings"] == 0
        assert stats["typo_mappings"] == 0

    @pytest.mark.asyncio
    async def test_get_stats_with_mappings(self, table_mapper: TableMapper, db_session: AsyncSession):
        """Test stats with multiple mappings"""
        # Create alias mapping
        await table_mapper.learn_from_feedback(
            source_table="usr",
            target_table="users",
            connection_name="test_db",
            database_type="postgres",
            feedback_id=30,
            mapping_type="alias"
        )

        # Create typo mappings
        await table_mapper.learn_from_feedback(
            source_table="prodcuts",
            target_table="products",
            connection_name="test_db",
            database_type="postgres",
            feedback_id=31,
            mapping_type="typo"
        )
        await table_mapper.learn_from_feedback(
            source_table="ordr",
            target_table="orders",
            connection_name="test_db",
            database_type="postgres",
            feedback_id=32,
            mapping_type="typo"
        )

        stats = await table_mapper.get_mapping_stats(database_type="postgres")

        assert stats["total_mappings"] == 3
        assert stats["alias_mappings"] == 1
        assert stats["typo_mappings"] == 2
        assert stats["database_type"] == "postgres"


class TestTableMapperDeletion:
    """Test deleting table mappings"""

    @pytest.mark.asyncio
    async def test_delete_mapping(self, table_mapper: TableMapper, db_session: AsyncSession):
        """Test deleting a mapping"""
        # Create mapping
        mapping_id = await table_mapper.learn_from_feedback(
            source_table="old_table",
            target_table="new_table",
            connection_name="test_db",
            database_type="postgres",
            feedback_id=40
        )

        # Delete it
        deleted = await table_mapper.delete_mapping(mapping_id)
        assert deleted is True

        # Verify it's gone
        result = await db_session.execute(
            text("SELECT COUNT(*) FROM table_mappings WHERE id = :id"),
            {"id": mapping_id}
        )
        count = result.scalar()
        assert count == 0

    @pytest.mark.asyncio
    async def test_delete_nonexistent_mapping(self, table_mapper: TableMapper):
        """Test deleting a mapping that doesn't exist"""
        deleted = await table_mapper.delete_mapping(99999)
        assert deleted is False


class TestTableSimilarity:
    """Test utility functions for table name similarity"""

    def test_table_similarity_exact_match(self):
        """Test similarity with exact match"""
        similarity = table_similarity("users", "users")
        assert similarity == 1.0

    def test_table_similarity_case_insensitive(self):
        """Test similarity is case-insensitive"""
        similarity = table_similarity("Users", "users")
        assert similarity == 1.0

    def test_table_similarity_partial_match(self):
        """Test similarity with partial match"""
        similarity = table_similarity("usr", "users")
        assert 0.5 < similarity < 0.9  # Similar but not identical

    def test_table_similarity_no_match(self):
        """Test similarity with completely different tables"""
        similarity = table_similarity("users", "products")
        assert similarity < 0.4

    def test_find_similar_tables(self):
        """Test finding similar tables from a list"""
        available = ["users", "customers", "products", "orders"]
        matches = find_similar_tables("usr", available, threshold=0.6)

        # Should find users as most similar
        assert len(matches) > 0
        assert matches[0][0] == "users"
        assert matches[0][1] > 0.6

    def test_find_similar_tables_no_matches(self):
        """Test finding similar tables when none meet threshold"""
        available = ["products", "orders", "categories"]
        matches = find_similar_tables("customer", available, threshold=0.8)

        assert len(matches) == 0
