#!/usr/bin/env python
"""
Demonstration of Smart Insight Generation
Shows how fallback narratives now generate meaningful business insights
instead of just raw statistics.
"""

from src.llm.result_narrator import ResultNarrator
from unittest.mock import AsyncMock


def demo_smart_insights():
    """Demonstrate the smart insight generation"""

    print("\n" + "="*80)
    print("SMART INSIGHT GENERATION - BEFORE vs AFTER")
    print("="*80)

    mock_ollama = AsyncMock()
    narrator = ResultNarrator(ollama_client=mock_ollama)

    # Example 1: Product inventory data
    print("\n" + "-"*80)
    print("EXAMPLE 1: Product Inventory Analysis")
    print("-"*80)

    product_stats = {
        "row_count": 25,
        "price": {
            "type": "numeric",
            "min": 15.99,
            "max": 299.99,
            "avg": 150.45,
            "median": 145.00,
            "stdev": 87.23
        },
        "product_name": {
            "type": "string",
            "unique_count": 10,
            "total_count": 25,
            "most_common": "Laptop Pro 15",
            "most_common_count": 5,
            "most_common_percent": 20.0
        },
        "category": {
            "type": "string",
            "unique_count": 3,
            "total_count": 25,
            "most_common": "Electronics",
            "most_common_count": 15,
            "most_common_percent": 60.0
        }
    }

    insights = narrator._generate_smart_insights(product_stats, 25)

    print("\nBEFORE (Raw Statistics):")
    print("  • Price: ranges from $15.99 to $299.99 (avg: $150.45)")
    print("  • Product Name: 10 unique values, with 'Laptop Pro 15' being most common")
    print("  • Category: 3 unique values, with 'Electronics' being most common")

    print("\nAFTER (Smart Insights):")
    for i, insight in enumerate(insights, 1):
        print(f"  {i}. {insight}")

    # Example 2: Customer segmentation data
    print("\n" + "-"*80)
    print("EXAMPLE 2: Customer Segmentation Analysis")
    print("-"*80)

    customer_stats = {
        "row_count": 500,
        "order_value": {
            "type": "numeric",
            "min": 10.0,
            "max": 5000.0,
            "avg": 450.00,
            "median": 250.00,
            "stdev": 1200.00
        },
        "customer_region": {
            "type": "string",
            "unique_count": 1,
            "total_count": 500,
            "most_common": "North America",
            "most_common_count": 500,
            "most_common_percent": 100.0
        },
        "account_status": {
            "type": "string",
            "unique_count": 4,
            "total_count": 500,
            "most_common": "Active",
            "most_common_count": 350,
            "most_common_percent": 70.0
        }
    }

    insights = narrator._generate_smart_insights(customer_stats, 500)

    print("\nBEFORE (Raw Statistics):")
    print("  • Order Value: ranges from $10.00 to $5000.00 (avg: $450.00)")
    print("  • Customer Region: 1 unique value, with 'North America' being most common")
    print("  • Account Status: 4 unique values, with 'Active' being most common")

    print("\nAFTER (Smart Insights):")
    for i, insight in enumerate(insights, 1):
        print(f"  {i}. {insight}")

    # Example 3: Sales performance data with low variance
    print("\n" + "-"*80)
    print("EXAMPLE 3: Consistent Performance Metrics")
    print("-"*80)

    sales_stats = {
        "row_count": 100,
        "conversion_rate": {
            "type": "numeric",
            "min": 0.18,
            "max": 0.22,
            "avg": 0.20,
            "median": 0.20,
            "stdev": 0.01
        },
        "sales_rep": {
            "type": "string",
            "unique_count": 5,
            "total_count": 100,
            "most_common": "Alice Johnson",
            "most_common_count": 25,
            "most_common_percent": 25.0
        }
    }

    insights = narrator._generate_smart_insights(sales_stats, 100)

    print("\nBEFORE (Raw Statistics):")
    print("  • Conversion Rate: ranges from 0.18 to 0.22 (avg: 0.20)")
    print("  • Sales Rep: 5 unique values, with 'Alice Johnson' being most common")

    print("\nAFTER (Smart Insights):")
    for i, insight in enumerate(insights, 1):
        print(f"  {i}. {insight}")

    # Example 4: Highly diverse product catalog
    print("\n" + "-"*80)
    print("EXAMPLE 4: Diverse Product Catalog")
    print("-"*80)

    catalog_stats = {
        "row_count": 250,
        "sku": {
            "type": "string",
            "unique_count": 248,
            "total_count": 250,
            "most_common": "SKU-12345",
            "most_common_count": 2,
            "most_common_percent": 0.8
        },
        "stock_quantity": {
            "type": "numeric",
            "min": 0,
            "max": 10000,
            "avg": 2500,
            "median": 1500,
            "stdev": 3200
        }
    }

    insights = narrator._generate_smart_insights(catalog_stats, 250)

    print("\nBEFORE (Raw Statistics):")
    print("  • SKU: 248 unique values, with 'SKU-12345' being most common")
    print("  • Stock Quantity: ranges from 0 to 10,000 (avg: 2500)")

    print("\nAFTER (Smart Insights):")
    for i, insight in enumerate(insights, 1):
        print(f"  {i}. {insight}")

    print("\n" + "="*80)
    print("KEY IMPROVEMENTS")
    print("="*80)
    print("""
✓ CONTEXTUAL: Insights explain WHAT the data means, not just the numbers
✓ ACTIONABLE: Suggestions for next steps (filters, aggregations, segmentation)
✓ COMPARATIVE: Highlights dominance, concentration, and diversity
✓ BUSINESS-FOCUSED: Uses business language instead of statistical jargon
✓ PATTERN-AWARE: Detects and calls out interesting patterns
✓ SAMPLE-AWARE: Notes when data size might affect reliability

EXAMPLES OF IMPROVEMENTS:

BEFORE: "Price: ranges from $15.99 to $299.99 (avg: $150.45)"
AFTER:  "Price spans a wide range ($15.99 to $299.99), suggesting diverse product tiers"

BEFORE: "Product Name: 10 unique values, with 'Laptop Pro 15' being most common"
AFTER:  "Product Name is dominated by 'Laptop Pro 15' (20% of records)"

BEFORE: "Category: 3 unique values, with 'Electronics' being most common"
AFTER:  "Data is concentrated in a single Electronics segment - consider applying filters for targeted analysis"

BEFORE: "Order Value: ranges from $10.00 to $5000.00"
AFTER:  "Order Value shows wide variation: from $10 to $5000, with median at $250 (high variability suggests multiple customer tiers)"

BEFORE: "Conversion Rate: ranges from 0.18 to 0.22"
AFTER:  "Conversion Rate values are consistent, mostly around 0.20 (range: 0.18-0.22) - stable performance"
    """)


if __name__ == "__main__":
    demo_smart_insights()
