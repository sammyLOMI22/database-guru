"""Tests for the correction learning system"""
import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.models import Base, LearnedCorrection
from src.llm.correction_learner import CorrectionLearner
from src.llm.self_correcting_agent import ErrorType


@pytest.fixture
def db_session():
    """Create a test database session"""
    # Use in-memory SQLite for testing
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    yield session

    session.close()


@pytest.fixture
def learner(db_session):
    """Create a CorrectionLearner instance"""
    return CorrectionLearner(db_session=db_session, enable_learning=True)


@pytest.mark.asyncio
async def test_learn_from_correction(learner, db_session):
    """Test learning from a successful correction"""
    correction_id = await learner.learn_from_correction(
        error_type=ErrorType.TABLE_NOT_FOUND,
        original_sql="SELECT * FROM prodcuts LIMIT 10",
        original_error='relation "prodcuts" does not exist',
        corrected_sql="SELECT * FROM products LIMIT 10",
        database_type="postgresql",
        was_successful=True
    )

    assert correction_id is not None

    # Verify it was stored
    correction = db_session.query(LearnedCorrection).filter(
        LearnedCorrection.id == correction_id
    ).first()

    assert correction is not None
    assert correction.error_type == ErrorType.TABLE_NOT_FOUND.value
    assert correction.database_type == "postgresql"
    assert correction.times_applied == 1
    assert correction.confidence_score == 0.7


@pytest.mark.asyncio
async def test_learn_duplicate_correction(learner, db_session):
    """Test that duplicate corrections update the existing one"""
    # Learn first time
    correction_id_1 = await learner.learn_from_correction(
        error_type=ErrorType.COLUMN_NOT_FOUND,
        original_sql="SELECT pric FROM products",
        original_error='column "pric" does not exist',
        corrected_sql="SELECT price FROM products",
        database_type="postgresql",
        was_successful=True
    )

    # Learn same correction again
    correction_id_2 = await learner.learn_from_correction(
        error_type=ErrorType.COLUMN_NOT_FOUND,
        original_sql="SELECT pric FROM orders",
        original_error='column "pric" does not exist',
        corrected_sql="SELECT price FROM orders",
        database_type="postgresql",
        was_successful=True
    )

    # Should update the same correction
    assert correction_id_1 == correction_id_2

    # Verify times_applied was incremented
    correction = db_session.query(LearnedCorrection).filter(
        LearnedCorrection.id == correction_id_1
    ).first()

    assert correction.times_applied == 2
    assert correction.confidence_score > 0.7  # Increased confidence


@pytest.mark.asyncio
async def test_find_applicable_corrections_exact_match(learner, db_session):
    """Test finding applicable corrections with exact match"""
    # Learn a correction
    await learner.learn_from_correction(
        error_type=ErrorType.TABLE_NOT_FOUND,
        original_sql="SELECT * FROM prodcuts",
        original_error='table "prodcuts" does not exist',
        corrected_sql="SELECT * FROM products",
        database_type="postgresql",
        was_successful=True
    )

    # Search for similar error
    corrections = await learner.find_applicable_corrections(
        error_type=ErrorType.TABLE_NOT_FOUND,
        error_message='table "prodcuts" does not exist',
        database_type="postgresql"
    )

    assert len(corrections) > 0
    assert corrections[0]["error_type"] == ErrorType.TABLE_NOT_FOUND.value


@pytest.mark.asyncio
async def test_find_applicable_corrections_different_database(learner, db_session):
    """Test that corrections are database-specific"""
    # Learn a correction for PostgreSQL
    await learner.learn_from_correction(
        error_type=ErrorType.SYNTAX_ERROR,
        original_sql="SELECT * FROM products",
        original_error='syntax error near "FROM"',
        corrected_sql="SELECT * FROM products LIMIT 10",
        database_type="postgresql",
        was_successful=True
    )

    # Search for MySQL - should not find the PostgreSQL correction
    corrections = await learner.find_applicable_corrections(
        error_type=ErrorType.SYNTAX_ERROR,
        error_message='syntax error near "FROM"',
        database_type="mysql"
    )

    assert len(corrections) == 0


@pytest.mark.asyncio
async def test_find_applicable_corrections_confidence_threshold(learner, db_session):
    """Test that low-confidence corrections are filtered out"""
    # Create a low-confidence correction manually
    low_confidence = LearnedCorrection(
        error_type=ErrorType.UNKNOWN.value,
        error_pattern="some error",
        database_type="postgresql",
        original_sql="SELECT * FROM test",
        original_error="some error",
        corrected_sql="SELECT * FROM test2",
        confidence_score=0.3,  # Below threshold
        times_applied=0
    )
    db_session.add(low_confidence)
    db_session.commit()

    # Search should not return low-confidence corrections
    corrections = await learner.find_applicable_corrections(
        error_type=ErrorType.UNKNOWN,
        error_message="some error",
        database_type="postgresql"
    )

    assert len(corrections) == 0


@pytest.mark.asyncio
async def test_apply_learned_correction_success(learner, db_session):
    """Test applying a learned correction and updating stats"""
    # Learn a correction
    correction_id = await learner.learn_from_correction(
        error_type=ErrorType.TABLE_NOT_FOUND,
        original_sql="SELECT * FROM users",
        original_error='table "users" does not exist',
        corrected_sql="SELECT * FROM user_table",
        database_type="postgresql",
        was_successful=True
    )

    # Apply it successfully
    await learner.apply_learned_correction(
        correction_id=correction_id,
        current_sql="SELECT * FROM users WHERE id = 1",
        was_successful=True
    )

    # Verify stats were updated
    correction = db_session.query(LearnedCorrection).filter(
        LearnedCorrection.id == correction_id
    ).first()

    assert correction.times_applied == 2  # Initial + this application
    assert correction.confidence_score > 0.7  # Increased
    assert correction.last_applied_at is not None


@pytest.mark.asyncio
async def test_apply_learned_correction_failure(learner, db_session):
    """Test that failed applications decrease confidence"""
    # Learn a correction
    correction_id = await learner.learn_from_correction(
        error_type=ErrorType.COLUMN_NOT_FOUND,
        original_sql="SELECT name FROM products",
        original_error='column "name" does not exist',
        corrected_sql="SELECT product_name FROM products",
        database_type="postgresql",
        was_successful=True
    )

    initial_confidence = 0.7

    # Apply it unsuccessfully
    await learner.apply_learned_correction(
        correction_id=correction_id,
        current_sql="SELECT name FROM orders",
        was_successful=False
    )

    # Verify confidence decreased
    correction = db_session.query(LearnedCorrection).filter(
        LearnedCorrection.id == correction_id
    ).first()

    assert correction.confidence_score < initial_confidence


@pytest.mark.asyncio
async def test_get_learning_stats(learner, db_session):
    """Test getting learning statistics"""
    # Learn several corrections
    await learner.learn_from_correction(
        error_type=ErrorType.TABLE_NOT_FOUND,
        original_sql="SELECT * FROM test1",
        original_error='table "test1" does not exist',
        corrected_sql="SELECT * FROM test_table1",
        database_type="postgresql",
        was_successful=True
    )

    await learner.learn_from_correction(
        error_type=ErrorType.COLUMN_NOT_FOUND,
        original_sql="SELECT col FROM test",
        original_error='column "col" does not exist',
        corrected_sql="SELECT column_name FROM test",
        database_type="postgresql",
        was_successful=True
    )

    # Get stats
    stats = await learner.get_learning_stats()

    assert stats["total_corrections"] == 2
    assert stats["learning_enabled"] is True
    assert ErrorType.TABLE_NOT_FOUND.value in stats["by_error_type"]
    assert ErrorType.COLUMN_NOT_FOUND.value in stats["by_error_type"]


@pytest.mark.asyncio
async def test_extract_table_name(learner):
    """Test extracting table name from error message"""
    error = 'relation "products" does not exist'
    table_name = learner._extract_table_name(error)
    assert table_name == "products"

    error2 = 'no such table: user_data'
    table_name2 = learner._extract_table_name(error2)
    assert table_name2 == "user_data"


@pytest.mark.asyncio
async def test_extract_column_name(learner):
    """Test extracting column name from error message"""
    error = 'column "price" does not exist'
    column_name = learner._extract_column_name(error)
    assert column_name == "price"

    error2 = 'no such column: user_id'
    column_name2 = learner._extract_column_name(error2)
    assert column_name2 == "user_id"


@pytest.mark.asyncio
async def test_normalize_error(learner):
    """Test error normalization for pattern matching"""
    error1 = 'table "products" does not exist'
    error2 = 'table "users" does not exist'

    normalized1 = learner._normalize_error(error1)
    normalized2 = learner._normalize_error(error2)

    # Both should normalize to the same pattern
    assert normalized1 == normalized2
    assert "<name>" in normalized1


@pytest.mark.asyncio
async def test_learning_disabled(db_session):
    """Test that learning can be disabled"""
    learner = CorrectionLearner(db_session=db_session, enable_learning=False)

    correction_id = await learner.learn_from_correction(
        error_type=ErrorType.TABLE_NOT_FOUND,
        original_sql="SELECT * FROM test",
        original_error="table does not exist",
        corrected_sql="SELECT * FROM test_table",
        database_type="postgresql",
        was_successful=True
    )

    # Should not learn when disabled
    assert correction_id is None

    # Should not find any corrections
    corrections = await learner.find_applicable_corrections(
        error_type=ErrorType.TABLE_NOT_FOUND,
        error_message="table does not exist",
        database_type="postgresql"
    )

    assert len(corrections) == 0


@pytest.mark.asyncio
async def test_table_pattern_matching(learner, db_session):
    """Test that corrections are matched by table pattern"""
    # Learn a correction for a specific table
    await learner.learn_from_correction(
        error_type=ErrorType.TABLE_NOT_FOUND,
        original_sql="SELECT * FROM products",
        original_error='table "products" does not exist',
        corrected_sql="SELECT * FROM product_table",
        database_type="postgresql",
        was_successful=True
    )

    # Search with same table name
    corrections = await learner.find_applicable_corrections(
        error_type=ErrorType.TABLE_NOT_FOUND,
        error_message='table "products" does not exist',
        database_type="postgresql"
    )

    assert len(corrections) > 0
    assert corrections[0]["table_pattern"] == "products"
