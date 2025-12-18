"""Test script to verify narratives with multiple databases"""
import asyncio
import httpx
import json

async def test_multi_db_query_multiple_databases():
    """Test multi-database query with multiple databases for combined analysis"""

    # Create a test request with narratives enabled and multiple connections
    request_data = {
        "question": "What are the top products?",
        "connection_ids": [1, 2],  # Query two databases if both exist
        "enable_narratives": True,
        "use_cache": False
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://localhost:8000/api/multi-query/",
                json=request_data,
                timeout=45.0
            )

            print(f"Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()

                print(f"\nTotal databases queried: {data.get('total_databases_queried')}")

                # Check for combined analysis
                combined_analysis = data.get("combined_analysis")
                if combined_analysis:
                    print(f"\n✓ COMBINED ANALYSIS FOUND:")
                    print(f"  Summary: {combined_analysis.get('summary')}")
                    print(f"  Databases included: {combined_analysis.get('databases_included')}")
                    print(f"  Confidence: {combined_analysis.get('confidence')}")
                    print(f"  Total rows analyzed: {combined_analysis.get('total_rows_analyzed')}")
                else:
                    print(f"\n✗ COMBINED ANALYSIS NOT FOUND (null)")

                # Check per-database analyses
                if data.get("database_results"):
                    for i, result in enumerate(data["database_results"]):
                        result_analysis = result.get("result_analysis")
                        print(f"\n--- Database {i}: {result.get('connection_name')} ---")

                        if result_analysis:
                            print(f"  ✓ Summary: {result_analysis.get('summary')}")
                            print(f"  ✓ Confidence: {result_analysis.get('confidence')}")
                        else:
                            print(f"  ✗ NO NARRATIVE")

            elif response.status_code == 422:
                print(f"Validation Error: {response.json()}")
            else:
                print(f"Error {response.status_code}: {response.text}")

        except Exception as e:
            print(f"Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_multi_db_query_multiple_databases())
