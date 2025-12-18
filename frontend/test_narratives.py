"""Test script to verify narratives are being generated"""
import asyncio
import httpx
import json

async def test_multi_db_query_with_narratives():
    """Test multi-database query with narratives enabled"""
    
    # Create a test request with narratives enabled
    request_data = {
        "question": "What are the top 5 results?",
        "connection_ids": [1],  # Assumes at least one connection exists
        "enable_narratives": True,
        "use_cache": False
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://localhost:8000/api/multi-query/",
                json=request_data,
                timeout=30.0
            )
            
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Check for narratives
                combined_analysis = data.get("combined_analysis")
                print(f"\nCombined Analysis: {combined_analysis}")
                
                if data.get("database_results"):
                    for i, result in enumerate(data["database_results"]):
                        result_analysis = result.get("result_analysis")
                        print(f"\nDatabase {i} Analysis: {result_analysis}")
                        
                        if result_analysis:
                            print(f"  Summary: {result_analysis.get('summary')}")
                            print(f"  Confidence: {result_analysis.get('confidence')}")
                        else:
                            print(f"  NO NARRATIVE FOUND")
            else:
                print(f"Error: {response.text}")
                
        except Exception as e:
            print(f"Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_multi_db_query_with_narratives())
