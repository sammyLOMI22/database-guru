"""Test script with fresh narratives (bypassing cache)"""
import asyncio
import httpx
import json

async def test_fresh_narratives():
    """Test with fresh narratives, not from cache"""

    # Use a unique timestamp to avoid cache hits
    import time
    timestamp = int(time.time())

    request_data = {
        "question": f"Show me the products {timestamp}",  # Unique question
        "connection_ids": [1, 2],
        "enable_narratives": True,
        "use_cache": False  # Disable cache for this test
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://localhost:8000/api/multi-query/",
                json=request_data,
                timeout=45.0
            )

            print(f"Status: {response.status_code}\n")

            if response.status_code == 200:
                data = response.json()

                print(f"Total databases queried: {data.get('total_databases_queried')}\n")

                # Check for combined analysis
                combined_analysis = data.get("combined_analysis")
                if combined_analysis:
                    print(f"✓ COMBINED ANALYSIS:")
                    print(f"  Summary: {combined_analysis.get('summary')}")
                    print(f"  Key Insights:")
                    for insight in combined_analysis.get('key_insights', []):
                        print(f"    • {insight}")
                    print(f"  Confidence: {combined_analysis.get('confidence')}")
                    print()

                # Check per-database analyses
                if data.get("database_results"):
                    for i, result in enumerate(data["database_results"]):
                        result_analysis = result.get("result_analysis")
                        print(f"--- Database {i+1}: {result.get('connection_name')} ---")

                        if result_analysis:
                            print(f"Summary: {result_analysis.get('summary')}")
                            print(f"Key Insights:")
                            for insight in result_analysis.get('key_insights', []):
                                print(f"  • {insight}")
                            print(f"Confidence: {result_analysis.get('confidence')}\n")
                        else:
                            print(f"NO NARRATIVE\n")

            else:
                print(f"Error {response.status_code}: {response.text}")

        except Exception as e:
            print(f"Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_fresh_narratives())
