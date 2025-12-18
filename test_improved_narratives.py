"""Test the improved narrative generation"""
import asyncio
import httpx
import time

async def test_improved_narrative():
    """Test with a unique question to avoid cache"""

    timestamp = int(time.time())
    request_data = {
        "question": f"Tell me about products inventory status {timestamp}",
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
                print("=" * 70)
                print("📊 IMPROVED NARRATIVE ANALYSIS")
                print("=" * 70)
                print(f"\n📍 SUMMARY:\n{analysis['summary']}\n")

                print(f"💡 KEY INSIGHTS:")
                for i, insight in enumerate(analysis['key_insights'], 1):
                    print(f"  {i}. {insight}")

                if analysis.get('direct_answer'):
                    print(f"\n✓ DIRECT ANSWER:\n{analysis['direct_answer']}")

                print(f"\n📈 CONFIDENCE: {analysis['confidence']}")
                print("\n" + "=" * 70)
            else:
                print("No narrative generated")
        else:
            print(f"Error {response.status_code}: {response.text}")

if __name__ == "__main__":
    asyncio.run(test_improved_narrative())
