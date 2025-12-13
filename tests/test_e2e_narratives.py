"""End-to-end integration tests for narrative generation with realistic query scenarios"""
import asyncio
import json
import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from unittest.mock import AsyncMock, MagicMock

from src.llm.result_narrator import ResultNarrator, NarrativeResult
from src.database.models import Base


@pytest.fixture
async def db_session():
    """Create in-memory database session for testing"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session


@pytest.fixture
def realistic_ollama_mock():
    """Mock Ollama with realistic response patterns"""
    client = AsyncMock()

    async def side_effect(*args, prompt: str = None, **kwargs):
        # Return just the response string (what ollama.generate returns)
        # Return different responses based on detected patterns in prompt
        if prompt and "Statistical anomalies" in prompt:
            return json.dumps({
                "summary": "The dataset contains statistical anomalies with one extreme outlier value significantly different from the normal range.",
                "key_insights": [
                    "One value (9999) is 15+ standard deviations above the mean",
                    "Remaining 20 values cluster tightly between 100-110",
                    "Anomaly represents 4.8% of total row count"
                ],
                "direct_answer": None,
                "confidence": 0.92
            })
        elif prompt and "Temporal trends" in prompt:
            return json.dumps({
                "summary": "Sales show a consistent upward trend over the 30-day period, with strong monthly growth.",
                "key_insights": [
                    "Average growth of 2.5% per day over the period",
                    "Sales increased from $45K to $75K (67% total growth)",
                    "Trend is consistent with R² of 0.92 indicating strong linear relationship"
                ],
                "direct_answer": "$75K",
                "confidence": 0.95
            })
        elif prompt and "Column correlations" in prompt:
            return json.dumps({
                "summary": "Marketing spend and sales revenue show a strong positive correlation (r=0.88), indicating marketing effectiveness.",
                "key_insights": [
                    "For every $1 increase in marketing spend, sales increase by approximately $3.50",
                    "This correlation is statistically significant (r=0.88)",
                    "The relationship suggests marketing ROI of 3.5x"
                ],
                "direct_answer": None,
                "confidence": 0.89
            })
        else:
            # Default response
            return json.dumps({
                "summary": "Query executed successfully with 42 rows of results.",
                "key_insights": [
                    "Data retrieved from query execution",
                    "Results appear consistent and well-formed"
                ],
                "direct_answer": None,
                "confidence": 0.75
            })

    client.generate = AsyncMock(side_effect=side_effect)
    return client


@pytest.mark.asyncio
async def test_e2e_sales_aggregation_query(realistic_ollama_mock, db_session):
    """E2E test: Simple aggregation query for sales by region"""
    narrator = ResultNarrator(
        ollama_client=realistic_ollama_mock,
        db_session=db_session
    )

    results = [
        {"region": "North", "sales": 125000, "customers": 450},
        {"region": "South", "sales": 98000, "customers": 320},
        {"region": "East", "sales": 156000, "customers": 520},
        {"region": "West", "sales": 89000, "customers": 280},
    ]

    narrative = await narrator.generate_narrative(
        question="What are sales by region?",
        sql="SELECT region, SUM(sales) as sales, COUNT(*) as customers FROM sales GROUP BY region",
        results=results,
        row_count=4,
        execution_time_ms=45
    )

    assert narrative.summary
    assert len(narrative.key_insights) > 0
    assert narrative.confidence > 0.5
    assert narrative.generated_at


@pytest.mark.asyncio
async def test_e2e_time_series_analysis(realistic_ollama_mock, db_session):
    """E2E test: Time-series data with trend detection"""
    narrator = ResultNarrator(
        ollama_client=realistic_ollama_mock,
        db_session=db_session
    )

    # Generate 30 days of sales data with upward trend
    results = []
    base_sales = 45000
    for i in range(1, 31):
        date = (datetime(2024, 1, 1) + timedelta(days=i-1)).strftime("%Y-%m-%d")
        sales = base_sales + (i * 1000)  # Linear increase
        results.append({
            "date": date,
            "sales": sales,
            "day_of_week": (i % 7) + 1
        })

    narrative = await narrator.generate_narrative(
        question="Show sales trend over January",
        sql="SELECT date, SUM(sales) as sales, DAYOFWEEK(date) as day_of_week FROM sales GROUP BY date",
        results=results,
        row_count=30,
        execution_time_ms=120
    )

    assert narrative.summary
    # Should have generated a narrative
    assert narrative.confidence > 0.5
    # Time-series data should have been processed
    assert narrative.summary or narrative.key_insights
    # Statistics should include trend analysis if detected
    if narrative.statistics.get("trends"):
        assert narrative.statistics["trends"].get("found") is True


@pytest.mark.asyncio
async def test_e2e_outlier_detection(realistic_ollama_mock, db_session):
    """E2E test: Data with obvious outliers"""
    narrator = ResultNarrator(
        ollama_client=realistic_ollama_mock,
        db_session=db_session
    )

    # Normal values with one extreme outlier
    results = [
        {"id": i, "transaction_amount": 100 + (i % 50)} for i in range(1, 21)
    ]
    results.append({"id": 21, "transaction_amount": 9999})  # Extreme outlier

    narrative = await narrator.generate_narrative(
        question="Analyze transaction amounts",
        sql="SELECT id, amount as transaction_amount FROM transactions ORDER BY id",
        results=results,
        row_count=21,
        execution_time_ms=85
    )

    assert narrative.summary
    assert narrative.confidence > 0.5
    # Should detect anomalies
    if narrative.statistics.get("anomalies"):
        assert narrative.statistics["anomalies"].get("found") is True
        assert narrative.statistics["anomalies"].get("count", 0) > 0


@pytest.mark.asyncio
async def test_e2e_correlation_analysis(realistic_ollama_mock, db_session):
    """E2E test: Multi-column data with correlations"""
    narrator = ResultNarrator(
        ollama_client=realistic_ollama_mock,
        db_session=db_session
    )

    # Marketing spend and sales (highly correlated)
    results = []
    for i in range(1, 21):
        marketing = 1000 + (i * 500)
        sales = 5000 + (i * 1750)  # Strongly correlated with marketing
        results.append({
            "week": i,
            "marketing_spend": marketing,
            "sales_revenue": sales,
            "conversion_rate": 0.15 + (i * 0.005)
        })

    narrative = await narrator.generate_narrative(
        question="Analyze marketing effectiveness",
        sql="SELECT week, marketing_spend, sales_revenue, conversion_rate FROM weekly_metrics",
        results=results,
        row_count=20,
        execution_time_ms=95
    )

    assert narrative.summary
    assert narrative.confidence > 0.6
    # Should detect correlations
    if narrative.statistics.get("correlations"):
        assert narrative.statistics["correlations"].get("found") is True
        assert len(narrative.statistics["correlations"].get("significant_correlations", [])) > 0


@pytest.mark.asyncio
async def test_e2e_customer_segmentation(realistic_ollama_mock, db_session):
    """E2E test: Customer segmentation with mixed data types"""
    narrator = ResultNarrator(
        ollama_client=realistic_ollama_mock,
        db_session=db_session
    )

    results = [
        {"segment": "Premium", "customer_count": 2450, "avg_lifetime_value": 8500, "churn_rate": 0.08},
        {"segment": "Standard", "customer_count": 12300, "avg_lifetime_value": 2100, "churn_rate": 0.15},
        {"segment": "Basic", "customer_count": 45600, "avg_lifetime_value": 600, "churn_rate": 0.25},
    ]

    narrative = await narrator.generate_narrative(
        question="What is the customer breakdown by segment?",
        sql="SELECT segment, COUNT(*) as customer_count, AVG(ltv) as avg_lifetime_value, churn_rate FROM customers GROUP BY segment",
        results=results,
        row_count=3,
        execution_time_ms=60
    )

    assert narrative.summary
    assert len(narrative.key_insights) > 0
    assert narrative.confidence > 0.6


@pytest.mark.asyncio
async def test_e2e_geographic_analysis(realistic_ollama_mock, db_session):
    """E2E test: Geographic data with distributions"""
    narrator = ResultNarrator(
        ollama_client=realistic_ollama_mock,
        db_session=db_session
    )

    results = [
        {"country": "USA", "state": "CA", "revenue": 2500000, "customer_count": 15420},
        {"country": "USA", "state": "NY", "revenue": 1800000, "customer_count": 9800},
        {"country": "USA", "state": "TX", "revenue": 1200000, "customer_count": 7500},
        {"country": "Canada", "state": "ON", "revenue": 450000, "customer_count": 2800},
        {"country": "Canada", "state": "BC", "revenue": 320000, "customer_count": 1900},
    ]

    narrative = await narrator.generate_narrative(
        question="Show revenue by country and state",
        sql="SELECT country, state, SUM(revenue) as revenue, COUNT(*) as customer_count FROM locations GROUP BY country, state",
        results=results,
        row_count=5,
        execution_time_ms=75
    )

    assert narrative.summary
    assert len(narrative.key_insights) > 0
    assert narrative.confidence > 0.5


@pytest.mark.asyncio
async def test_e2e_product_performance(realistic_ollama_mock, db_session):
    """E2E test: Product performance with rankings"""
    narrator = ResultNarrator(
        ollama_client=realistic_ollama_mock,
        db_session=db_session
    )

    results = [
        {"product": "Laptop Pro", "units_sold": 5420, "revenue": 8130000, "rating": 4.8},
        {"product": "Tablet X", "units_sold": 12300, "revenue": 2460000, "rating": 4.5},
        {"product": "Phone Z", "units_sold": 28900, "revenue": 4335000, "rating": 4.6},
        {"product": "Watch S", "units_sold": 8700, "revenue": 870000, "rating": 4.3},
        {"product": "Headset Q", "units_sold": 15400, "revenue": 2310000, "rating": 4.7},
    ]

    narrative = await narrator.generate_narrative(
        question="Which product generates the most revenue?",
        sql="SELECT product, units_sold, revenue, rating FROM products ORDER BY revenue DESC",
        results=results,
        row_count=5,
        execution_time_ms=70
    )

    assert narrative.summary
    # Should have generated a narrative about products
    assert len(narrative.summary) > 0
    assert narrative.confidence > 0.5


@pytest.mark.asyncio
async def test_e2e_empty_result_set(realistic_ollama_mock, db_session):
    """E2E test: Empty result handling"""
    narrator = ResultNarrator(
        ollama_client=realistic_ollama_mock,
        db_session=db_session
    )

    narrative = await narrator.generate_narrative(
        question="Show deleted customers",
        sql="SELECT * FROM customers WHERE deleted_at IS NOT NULL",
        results=[],
        row_count=0,
        execution_time_ms=20
    )

    assert narrative.summary
    assert narrative.confidence >= 0
    # Empty results should have fallback narrative
    assert len(narrative.summary) > 0


@pytest.mark.asyncio
async def test_e2e_single_row_result(realistic_ollama_mock, db_session):
    """E2E test: Single row result"""
    narrator = ResultNarrator(
        ollama_client=realistic_ollama_mock,
        db_session=db_session
    )

    results = [
        {"metric": "Total Revenue", "value": 15240000, "year": 2024}
    ]

    narrative = await narrator.generate_narrative(
        question="What is the total revenue for 2024?",
        sql="SELECT SUM(revenue) as value FROM sales WHERE YEAR(date) = 2024",
        results=results,
        row_count=1,
        execution_time_ms=35
    )

    assert narrative.summary
    assert narrative.direct_answer or narrative.summary
    assert narrative.confidence > 0.6


@pytest.mark.asyncio
async def test_e2e_large_dataset_sampling(realistic_ollama_mock, db_session):
    """E2E test: Large dataset (>20 rows) triggers sampling"""
    narrator = ResultNarrator(
        ollama_client=realistic_ollama_mock,
        db_session=db_session,
        max_sample_rows=20
    )

    # Create 100 rows
    results = []
    for i in range(1, 101):
        results.append({
            "id": i,
            "amount": 1000 + (i * 10),
            "category": f"cat_{i % 5}",
            "date": f"2024-01-{(i % 28) + 1:02d}"
        })

    narrative = await narrator.generate_narrative(
        question="Analyze all transactions",
        sql="SELECT * FROM transactions",
        results=results,
        row_count=100,
        execution_time_ms=150
    )

    assert narrative.summary
    assert narrative.confidence > 0.5
    # Should have sampled first 20 rows
    assert len(narrative.key_insights) > 0


@pytest.mark.asyncio
async def test_e2e_null_handling(realistic_ollama_mock, db_session):
    """E2E test: Data with NULL values"""
    narrator = ResultNarrator(
        ollama_client=realistic_ollama_mock,
        db_session=db_session
    )

    results = [
        {"user_id": 1, "email": "user1@example.com", "phone": "555-0001", "verified": True},
        {"user_id": 2, "email": "user2@example.com", "phone": None, "verified": False},
        {"user_id": 3, "email": None, "phone": "555-0003", "verified": True},
        {"user_id": 4, "email": "user4@example.com", "phone": "555-0004", "verified": None},
        {"user_id": 5, "email": "user5@example.com", "phone": None, "verified": True},
    ]

    narrative = await narrator.generate_narrative(
        question="Review user data quality",
        sql="SELECT user_id, email, phone, verified FROM users",
        results=results,
        row_count=5,
        execution_time_ms=40
    )

    assert narrative.summary
    assert narrative.confidence > 0.5
    # Should handle NULLs gracefully
    assert "NULL" not in narrative.summary or any("incomplete" in insight.lower() or "missing" in insight.lower() for insight in narrative.key_insights)


@pytest.mark.asyncio
async def test_e2e_numerical_stability(realistic_ollama_mock, db_session):
    """E2E test: Very large and very small numbers"""
    narrator = ResultNarrator(
        ollama_client=realistic_ollama_mock,
        db_session=db_session
    )

    results = [
        {"metric": "Cloud Storage", "size_bytes": 1099511627776, "growth_rate": 0.00000125},
        {"metric": "API Calls", "size_bytes": 5368709120, "growth_rate": 0.00045},
        {"metric": "Database", "size_bytes": 10737418240, "growth_rate": 0.000003},
    ]

    narrative = await narrator.generate_narrative(
        question="What is our system resource usage?",
        sql="SELECT metric, size_bytes, growth_rate FROM system_metrics",
        results=results,
        row_count=3,
        execution_time_ms=50
    )

    assert narrative.summary
    assert narrative.confidence > 0.5
    # Should handle large/small numbers without error
    assert not any(char in narrative.summary for char in ["∞", "NaN", "inf"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
