"""Direct test of the improved ResultNarrator"""
import asyncio
from src.llm.result_narrator import ResultNarrator
from src.llm.ollama_client import OllamaClient
from src.config.settings import Settings

async def test_narrator_directly():
    """Test the narrator directly with sample data"""

    # Sample product data
    results = [
        {"name": "Laptop Pro 15", "stock_quantity": 45, "price": 1200},
        {"name": "Wireless Mouse", "stock_quantity": 234, "price": 25},
        {"name": "USB-C Cable", "stock_quantity": 500, "price": 12},
        {"name": "Monitor 4K", "stock_quantity": 8, "price": 450},
        {"name": "Keyboard Mechanical", "stock_quantity": 67, "price": 120},
    ]

    settings = Settings()
    ollama_client = OllamaClient(settings=settings)
    await ollama_client.connect()

    narrator = ResultNarrator(
        ollama_client=ollama_client,
        enable_statistics=True,
        timeout_seconds=5
    )

    print("🚀 Testing improved narrative generation...\n")

    # Generate narrative
    narrative = await narrator.generate_narrative(
        question="What products do we have in stock and how much inventory?",
        sql="SELECT name, stock_quantity, price FROM products",
        results=results,
        row_count=len(results),
        execution_time_ms=45.2
    )

    print("=" * 70)
    print("📊 NARRATIVE RESULT")
    print("=" * 70)
    print(f"\n📍 SUMMARY:\n{narrative.summary}\n")

    print(f"💡 KEY INSIGHTS:")
    for i, insight in enumerate(narrative.key_insights, 1):
        print(f"  {i}. {insight}")

    if narrative.direct_answer:
        print(f"\n✓ DIRECT ANSWER:\n{narrative.direct_answer}")

    print(f"\n📈 CONFIDENCE: {narrative.confidence}")
    print("\n" + "=" * 70)

    await ollama_client.disconnect()

if __name__ == "__main__":
    asyncio.run(test_narrator_directly())
