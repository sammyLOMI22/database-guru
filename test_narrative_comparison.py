"""Compare narratives before and after improvements"""
import asyncio
import httpx
import json

async def test_narrative():
    request_data = {
        "question": "What are the products in stock?",
        "connection_ids": [1],
        "enable_narratives": True,
        "use_cache": False
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/multi-query/",
            json=request_data,
            timeout=30.0
        )

        if response.status_code == 200:
            data = response.json()
            result = data["database_results"][0]

            if result.get("result_analysis"):
                analysis = result["result_analysis"]
                print("📊 NARRATIVE ANALYSIS")
                print("=" * 60)
                print(f"\nSummary:\n  {analysis['summary']}")
                print(f"\nKey Insights:")
                for insight in analysis['key_insights']:
                    print(f"  • {insight}")
                print(f"\nConfidence: {analysis['confidence']}")
                print(f"\nColumns Analyzed:")
                if analysis['statistics']:
                    for col, stats in analysis['statistics'].items():
                        if col != 'row_count':
                            col_type = stats.get('type', 'unknown')
                            if col_type == 'numeric':
                                print(f"  • {col}: min={stats['min']}, max={stats['max']}, avg={stats['avg']}")
                            elif col_type == 'string':
                                print(f"  • {col}: {stats['unique_count']} unique values")

if __name__ == "__main__":
    asyncio.run(test_narrative())
