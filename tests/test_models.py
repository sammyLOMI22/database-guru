"""Test script for model management"""
import asyncio
import httpx
import pytest


BASE_URL = "http://localhost:8000"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_models():
    """Test model management features"""
    print("=" * 80)
    print("🤖 DATABASE GURU - MODEL MANAGEMENT TEST")
    print("=" * 80)
    print()

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Test 1: List Available Models
        print("1️⃣  Listing Available Models")
        print("-" * 80)
        response = await client.get(f"{BASE_URL}/api/models/")

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Found {data['count']} models:")
            for model in data['models']:
                marker = "⭐" if model == data['default_model'] else "  "
                print(f"   {marker} {model}")
            print(f"\n   Default model: {data['default_model']}")
        else:
            print(f"❌ Error: {response.text}")
            return
        print()

        # Test 2: Get Model Details
        print("2️⃣  Model Details")
        print("-" * 80)
        response = await client.get(f"{BASE_URL}/api/models/details")

        if response.status_code == 200:
            data = response.json()
            print(f"Ollama URL: {data['ollama_url']}")
            print(f"\nDetailed model info:")
            for model in data['models']:
                print(f"   • {model['name']}")
                print(f"     Size: {model['size']}")
                print(f"     Available: {model['available']}")
        print()

        # Test 3: Recommended Models
        print("3️⃣  Recommended Models")
        print("-" * 80)
        response = await client.get(f"{BASE_URL}/api/models/recommended")

        if response.status_code == 200:
            data = response.json()
            print("Top recommendations for SQL generation:\n")
            for model in data['recommended_models']:
                if model.get('recommended'):
                    print(f"   ✅ {model['name']} ({model['size']})")
                    print(f"      {model['description']}")
                    print(f"      Install: {model['command']}")
                    print()
        print()

        # Test 4: Query with Different Models
        print("4️⃣  Testing Queries with Different Models")
        print("-" * 80)

        test_question = "Show me all customers from California"

        # Get list of available models
        models_resp = await client.get(f"{BASE_URL}/api/models/")
        if models_resp.status_code == 200:
            available_models = models_resp.json()['models'][:2]  # Test first 2 models

            for model_name in available_models:
                print(f"\n   Testing with model: {model_name}")
                query_data = {
                    "question": test_question,
                    "model": model_name,
                    "use_cache": False,
                }

                response = await client.post(f"{BASE_URL}/api/query/", json=query_data)

                if response.status_code == 200:
                    result = response.json()
                    print(f"   ✓ SQL: {result['sql'][:60]}...")
                    if result.get('execution_time_ms'):
                        print(f"   ✓ Execution: {result['execution_time_ms']:.2f}ms")
                else:
                    print(f"   ❌ Error: {response.status_code}")
        print()

        # Test 5: Test a Specific Model
        print("5️⃣  Quick Model Test")
        print("-" * 80)

        # Get default model
        models_resp = await client.get(f"{BASE_URL}/api/models/")
        if models_resp.status_code == 200:
            default_model = models_resp.json()['default_model']

            response = await client.get(f"{BASE_URL}/api/models/test/{default_model}")

            if response.status_code == 200:
                result = response.json()
                print(f"Model: {result['model']}")
                print(f"Test passed: {result['test_passed']}")
                if result.get('sample_output'):
                    print(f"Sample output: {result['sample_output'][:100]}...")
            else:
                print(f"❌ Error: {response.text}")
        print()

    print("=" * 80)
    print("✨ MODEL TEST COMPLETE!")
    print("=" * 80)
    print()
    print("You can now:")
    print("  • Use any installed Ollama model")
    print("  • Specify model per query: {\"question\": \"...\", \"model\": \"mistral\"}")
    print("  • Install new models: ollama pull <model-name>")
    print("  • Check available models at: /api/models/")
    print()


if __name__ == "__main__":
    print("\n🤖 Database Guru - Model Management Test\n")
    print("Prerequisites:")
    print("  1. API is running (python src/main.py)")
    print("  2. Ollama is running (ollama serve)")
    print("  3. At least one model is installed\n")

    try:
        asyncio.run(test_models())
    except httpx.ConnectError:
        print("\n❌ Error: Could not connect to API")
        print("   Make sure the server is running: python src/main.py")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
