# Learning from Corrections - Quick Start Guide

## Getting Started in 5 Minutes

This guide will get you up and running with the Learning from Corrections feature.

---

## Step 1: Initialize Database

Create the new `learned_corrections` table:

```bash
# Make sure you're in the database-guru directory
cd /Users/sam/database-guru

# Activate virtual environment (if not already active)
source venv/bin/activate

# Initialize/update database
python -m src.database.init_db
```

Expected output:
```
INFO - Initializing database...
INFO - ✅ Database initialized successfully!
```

---

## Step 2: Start the Application

```bash
python -m src.main
```

The learning feature is **enabled by default** - no configuration needed!

---

## Step 3: Test the Learning System

### Option A: Using the API

**1. Check that learning is enabled:**
```bash
curl http://localhost:8000/api/learned-corrections/stats/summary
```

Expected response:
```json
{
  "total_corrections": 0,
  "by_error_type": {},
  "top_corrections": [],
  "learning_enabled": true
}
```

**2. Make a query that will generate an error (then get corrected):**
```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Show me all products",
    "connection_id": 1
  }'
```

**3. If a correction was made, check learned corrections:**
```bash
curl http://localhost:8000/api/learned-corrections/
```

### Option B: Using Python

Create a test script `test_learning.py`:

```python
import asyncio
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from src.config.settings import Settings
from src.llm.sql_generator import SQLGenerator
from src.llm.self_correcting_agent import SelfCorrectingSQLAgent
from src.database.connection import get_db_manager

async def test_learning():
    # Setup
    settings = Settings()
    db_manager = get_db_manager(settings)
    await db_manager.initialize_async()

    # Get database session
    SessionLocal = sessionmaker(bind=db_manager.engine)
    db_session = SessionLocal()

    # Create test database with a typo
    test_conn = create_engine("sqlite:///:memory:")
    test_conn.execute(text("CREATE TABLE products (id INTEGER, name TEXT, price REAL)"))
    test_conn.execute(text("INSERT INTO products VALUES (1, 'Widget', 9.99)"))

    # Create agent with learning
    generator = SQLGenerator(settings)
    agent = SelfCorrectingSQLAgent(
        sql_generator=generator,
        max_retries=3,
        enable_learning=True,
        learner_session=db_session  # Database for storing learned corrections
    )

    # Create session for query execution
    TestSession = sessionmaker(bind=test_conn)
    test_session = TestSession()

    # Simulate a query that will fail then get corrected
    # (This would normally happen through the API)
    print("🧪 Testing learning system...")

    # First, let's check if we have any corrections
    from src.llm.correction_learner import CorrectionLearner
    learner = CorrectionLearner(db_session=db_session, enable_learning=True)

    stats = await learner.get_learning_stats()
    print(f"\n📊 Initial stats: {stats['total_corrections']} corrections")

    # Manually add a test correction
    from src.llm.self_correcting_agent import ErrorType

    correction_id = await learner.learn_from_correction(
        error_type=ErrorType.TABLE_NOT_FOUND,
        original_sql="SELECT * FROM prodcuts",
        original_error='no such table: prodcuts',
        corrected_sql="SELECT * FROM products",
        database_type="sqlite",
        was_successful=True
    )

    print(f"✅ Learned correction ID: {correction_id}")

    # Get updated stats
    stats = await learner.get_learning_stats()
    print(f"\n📊 Updated stats:")
    print(f"  Total corrections: {stats['total_corrections']}")
    print(f"  By error type: {stats['by_error_type']}")

    # Find applicable corrections
    corrections = await learner.find_applicable_corrections(
        error_type=ErrorType.TABLE_NOT_FOUND,
        error_message='no such table: prodcuts',
        database_type="sqlite"
    )

    print(f"\n🔍 Found {len(corrections)} applicable corrections:")
    for correction in corrections:
        print(f"  - ID {correction['id']}: {correction['correction_description']}")
        print(f"    Confidence: {correction['confidence_score']:.2f}")
        print(f"    Times applied: {correction['times_applied']}")

    print("\n✨ Learning system is working!")

    # Cleanup
    test_session.close()
    db_session.close()
    await db_manager.close_async()

if __name__ == "__main__":
    asyncio.run(test_learning())
```

Run it:
```bash
python test_learning.py
```

Expected output:
```
🧪 Testing learning system...

📊 Initial stats: 0 corrections
✅ Learned correction ID: 1

📊 Updated stats:
  Total corrections: 1
  By error type: {'table_not_found': 1}

🔍 Found 1 applicable corrections:
  - ID 1: Fix for missing table: prodcuts
    Confidence: 0.70
    Times applied: 1

✨ Learning system is working!
```

---

## Step 4: Verify Learning in Action

### Create a Scenario

1. **Set up a test database with a typo-prone table name**
2. **Make a query that generates an error**
3. **Watch the self-correcting agent fix it**
4. **Make a similar query** - it should fix it faster!

### Monitor Learning

**View all learned corrections:**
```bash
curl http://localhost:8000/api/learned-corrections/ | jq
```

**View learning statistics:**
```bash
curl http://localhost:8000/api/learned-corrections/stats/summary | jq
```

**Search for corrections:**
```bash
curl "http://localhost:8000/api/learned-corrections/search/similar?\
error_type=table_not_found&\
database_type=postgresql&\
error_message=table%20products%20does%20not%20exist" | jq
```

---

## Step 5: Run Tests (Optional)

Install test dependencies:
```bash
pip install -r requirements-dev.txt
```

Run the tests:
```bash
pytest tests/test_correction_learner.py -v
```

Expected output:
```
tests/test_correction_learner.py::test_learn_from_correction PASSED
tests/test_correction_learner.py::test_learn_duplicate_correction PASSED
tests/test_correction_learner.py::test_find_applicable_corrections_exact_match PASSED
...
```

---

## Common Use Cases

### Use Case 1: Check Learning Status

```bash
curl http://localhost:8000/api/learned-corrections/stats/summary
```

### Use Case 2: View Top Corrections

```bash
curl "http://localhost:8000/api/learned-corrections/?limit=10" | jq
```

### Use Case 3: Search for Similar Corrections

```bash
curl "http://localhost:8000/api/learned-corrections/search/similar?\
error_type=column_not_found&\
database_type=postgresql&\
error_message=column%20price%20does%20not%20exist" | jq
```

### Use Case 4: Delete a Bad Correction

```bash
curl -X DELETE http://localhost:8000/api/learned-corrections/42
```

### Use Case 5: Reset All Corrections

```bash
curl -X POST "http://localhost:8000/api/learned-corrections/reset?confirm=true"
```

---

## Troubleshooting

### Issue: Learning not enabled

**Check:**
```bash
curl http://localhost:8000/api/learned-corrections/stats/summary
```

If `learning_enabled: false`, check that:
1. Database is initialized
2. Application has database write permissions
3. No errors in application logs

### Issue: No corrections being learned

**Check application logs** for:
- `"✨ Learned from successful correction"`
- Any errors from `CorrectionLearner`

**Verify** self-correcting agent is working:
```bash
# Check query history
curl http://localhost:8000/api/query/history | jq
```

### Issue: Tests failing

**Make sure you have test dependencies:**
```bash
pip install -r requirements-dev.txt
```

**Run with verbose output:**
```bash
pytest tests/test_correction_learner.py -v -s
```

---

## Next Steps

1. **Read the full documentation**: [LEARNING_FROM_CORRECTIONS.md](LEARNING_FROM_CORRECTIONS.md)
2. **Monitor learning progress** in production
3. **Review learned corrections** periodically
4. **Adjust confidence thresholds** based on your needs
5. **Share feedback** on what works and what doesn't

---

## Quick Reference

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/learned-corrections/` | GET | List all corrections |
| `/api/learned-corrections/{id}` | GET | Get specific correction |
| `/api/learned-corrections/stats/summary` | GET | Learning statistics |
| `/api/learned-corrections/search/similar` | GET | Search similar corrections |
| `/api/learned-corrections/{id}` | DELETE | Delete correction |
| `/api/learned-corrections/reset` | POST | Reset all corrections |

### Configuration

```python
# Enable learning (default)
agent = SelfCorrectingSQLAgent(
    sql_generator=generator,
    enable_learning=True,
    learner_session=db_session
)

# Disable learning
agent = SelfCorrectingSQLAgent(
    sql_generator=generator,
    enable_learning=False
)
```

---

## Success Indicators

You'll know the learning system is working when you see:

✅ `learning_enabled: true` in stats
✅ Growing number of corrections over time
✅ Faster error recovery on repeated errors
✅ Corrections being applied (check `times_applied`)
✅ High confidence scores (>= 0.7)

---

**That's it! You're ready to use Learning from Corrections.**

For more details, see the [full documentation](LEARNING_FROM_CORRECTIONS.md).
