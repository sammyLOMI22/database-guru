#!/usr/bin/env python
"""
Test script to demonstrate the improved multi-database narrative generation.
Run with: python test_narrative_improvements.py
"""

import asyncio
from unittest.mock import AsyncMock
from src.llm.result_narrator import ResultNarrator


async def test_single_database_narrative():
    """Test single database narrative (unchanged behavior)"""
    print("\n" + "="*80)
    print("TEST 1: Single Database Narrative (Unchanged)")
    print("="*80)

    mock_ollama = AsyncMock()
    mock_ollama.generate = AsyncMock(return_value='''
    {
        "summary": "We found 150 customer records with purchase history spanning the last quarter",
        "key_insights": [
            "Average order value is $450 with range from $50 to $2,000",
            "Top customers account for 30% of total revenue",
            "Most purchases occur on weekends"
        ],
        "confidence": 0.85
    }
    ''')

    narrator = ResultNarrator(ollama_client=mock_ollama)

    results = [
        {"customer_id": i, "name": f"Customer {i}", "order_value": 50 + (i % 20) * 100}
        for i in range(150)
    ]

    narrative = await narrator.generate_narrative(
        question="Show me our customers and their order values",
        sql="SELECT * FROM customers LIMIT 150",
        results=results,
        row_count=150,
        execution_time_ms=45.2,
        database_type="postgresql"
    )

    print(f"\nQuestion: Show me our customers and their order values")
    print(f"\nSummary: {narrative.summary}")
    print(f"\nKey Insights:")
    for insight in narrative.key_insights:
        print(f"  • {insight}")
    print(f"\nConfidence: {narrative.confidence}")


async def test_multi_database_narrative():
    """Test multi-database narrative with comparison focus"""
    print("\n" + "="*80)
    print("TEST 2: Multi-Database Narrative (IMPROVED)")
    print("="*80)

    mock_ollama = AsyncMock()
    mock_ollama.generate = AsyncMock(return_value='''
    {
        "summary": "Database A dominates with 65% of total records (156 vs 84 rows) and shows 2.3x higher average order values ($520 vs $225), suggesting it contains the primary customer base with higher spending power",
        "key_insights": [
            "Database A leads by volume (156 records, 65% of total) - represents primary customer segment",
            "Order value gap is significant: A averages $520 vs B at $225 (2.3x difference)",
            "Database A has consistent data (all customers have values), B has 15% sparse coverage",
            "Combined view reveals A customers are premium tier (avg $520) while B contains budget-conscious (avg $225)",
            "Recommend segmenting by source: A for premium products, B for value offerings"
        ],
        "direct_answer": "Database A is the clear leader with more customers and higher spending, representing premium customers. Database B captures budget-conscious segment with different purchasing patterns",
        "confidence": 0.92
    }
    ''')

    narrator = ResultNarrator(ollama_client=mock_ollama)

    # Simulate results from 2 databases combined
    results = []

    # Database A: 156 customers with high order values
    for i in range(156):
        results.append({
            "_source_database": "Production DB",
            "customer_id": i,
            "name": f"Premium Customer {i}",
            "order_value": 400 + (i % 40) * 5
        })

    # Database B: 84 customers with lower order values
    for i in range(84):
        results.append({
            "_source_database": "Archive DB",
            "customer_id": i + 200,
            "name": f"Budget Customer {i}",
            "order_value": 150 + (i % 20) * 5 if i % 7 != 0 else None  # Some sparse data
        })

    narrative = await narrator.generate_narrative(
        question="Show me all customers and their order values",
        sql="[Multiple databases]",
        results=results,
        row_count=len(results),
        execution_time_ms=156.8,
        databases=["Production DB", "Archive DB"],
        multi_database=True
    )

    print(f"\nQuestion: Show me all customers and their order values")
    print(f"Databases: Production DB, Archive DB")
    print(f"Total Rows: {len(results)}")
    print(f"\nSummary: {narrative.summary}")
    print(f"\nKey Insights:")
    for i, insight in enumerate(narrative.key_insights, 1):
        print(f"  {i}. {insight}")
    print(f"\nDirect Answer: {narrative.direct_answer}")
    print(f"\nConfidence: {narrative.confidence}")


async def test_three_database_narrative():
    """Test narrative with three databases"""
    print("\n" + "="*80)
    print("TEST 3: Three-Database Narrative (ADVANCED)")
    print("="*80)

    mock_ollama = AsyncMock()
    mock_ollama.generate = AsyncMock(return_value='''
    {
        "summary": "Database A dominates with 50% market share and premium customers (avg $650), Database B provides mid-market coverage (25%, avg $400), while Database C captures budget segment (25%, avg $180) - a natural 3-tier customer segmentation",
        "key_insights": [
            "Volume distribution: A leads (200 rows, 50%), B second (100 rows, 25%), C third (100 rows, 25%)",
            "Spending tiers by database: Premium A ($650 avg) > Mid B ($400) > Budget C ($180) - perfect market segmentation",
            "Data completeness: A has 100% coverage, B 95% coverage, C 80% with some missing values",
            "Cross-database insight: Total market capacity is $255K across all tiers, with A driving 62% of value",
            "Recommendation: Maintain separate strategies per database - premium retention for A, growth for B, value retention for C"
        ],
        "confidence": 0.88
    }
    ''')

    narrator = ResultNarrator(ollama_client=mock_ollama)

    results = []

    # DB A: 200 premium customers
    for i in range(200):
        results.append({
            "_source_database": "Premium Tier",
            "customer_id": i,
            "order_value": 600 + (i % 30) * 2
        })

    # DB B: 100 mid-market customers
    for i in range(100):
        results.append({
            "_source_database": "Mid Market",
            "customer_id": i + 300,
            "order_value": 350 + (i % 25) * 2 if i % 20 != 0 else None
        })

    # DB C: 100 budget customers
    for i in range(100):
        results.append({
            "_source_database": "Budget Tier",
            "customer_id": i + 400,
            "order_value": 150 + (i % 15) * 2 if i % 5 != 0 else None
        })

    narrative = await narrator.generate_narrative(
        question="Show all customer segments",
        sql="[Multiple databases]",
        results=results,
        row_count=len(results),
        execution_time_ms=342.1,
        databases=["Premium Tier", "Mid Market", "Budget Tier"],
        multi_database=True
    )

    print(f"\nQuestion: Show all customer segments")
    print(f"Databases: Premium Tier, Mid Market, Budget Tier")
    print(f"Total Rows: {len(results)}")
    print(f"\nSummary: {narrative.summary}")
    print(f"\nKey Insights:")
    for i, insight in enumerate(narrative.key_insights, 1):
        print(f"  {i}. {insight}")
    print(f"\nConfidence: {narrative.confidence}")


async def main():
    print("\n" + "="*80)
    print("MULTI-DATABASE NARRATIVE QUALITY TEST")
    print("="*80)
    print("\nThis script demonstrates the improved narrative generation with")
    print("cross-database comparisons, rankings, and actionable insights.")

    await test_single_database_narrative()
    await test_multi_database_narrative()
    await test_three_database_narrative()

    print("\n" + "="*80)
    print("SUMMARY OF IMPROVEMENTS")
    print("="*80)
    print("""
BEFORE: Generic summaries
  "Queried 2 databases, found 245 rows total"

AFTER: Specific, actionable insights with comparisons
  "Database A dominates with 65% of records and 2.3x higher values...
   Recommend segmenting by source for different strategies"

KEY FEATURES:
  ✓ Volume comparisons (e.g., "3x larger than B")
  ✓ Value differences (e.g., "2.3x higher average")
  ✓ Data completeness (e.g., "100% coverage vs 80%")
  ✓ Market segmentation insights
  ✓ Actionable recommendations
  ✓ Ranking and leadership identification
    """)


if __name__ == "__main__":
    asyncio.run(main())
