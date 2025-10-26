"""Test script for Redis cache layer"""
import asyncio
from src.config.settings import Settings
from src.cache.redis_client import get_redis_cache
from src.cache.decorators import cached, cache_query_result, CacheNamespace


async def test_basic_operations():
    """Test basic Redis cache operations"""
    print("🧪 Testing Redis Cache...\n")

    settings = Settings()
    cache = get_redis_cache(settings)

    # Connect
    print("📡 Connecting to Redis...")
    await cache.connect()

    # Health check
    print("💚 Running health check...")
    is_healthy = await cache.health_check()
    print(f"✅ Health check: {'PASSED' if is_healthy else 'FAILED'}\n")

    # Test set/get
    print("🔧 Testing set/get operations...")
    await cache.set("test:key1", {"message": "Hello from Redis!"}, ttl=60)
    value = await cache.get("test:key1")
    print(f"  ✓ Set/Get: {value}")

    # Test exists
    exists = await cache.exists("test:key1")
    print(f"  ✓ Exists: {exists}")

    # Test increment
    await cache.increment("test:counter")
    await cache.increment("test:counter")
    counter = await cache.get("test:counter")
    print(f"  ✓ Counter: {counter}")

    # Test delete
    await cache.delete("test:key1")
    deleted_value = await cache.get("test:key1")
    print(f"  ✓ Delete: {deleted_value is None}\n")

    # Test pattern clear
    print("🧹 Testing pattern clear...")
    await cache.set("test:pattern:1", "value1")
    await cache.set("test:pattern:2", "value2")
    await cache.set("test:pattern:3", "value3")
    deleted = await cache.clear_pattern("test:pattern:*")
    print(f"  ✓ Cleared {deleted} keys\n")

    # Clean up
    await cache.clear_pattern("test:*")
    await cache.disconnect()
    print("✨ Test complete!")


async def test_decorators():
    """Test cache decorators"""
    print("\n🎨 Testing Cache Decorators...\n")

    settings = Settings()
    cache = get_redis_cache(settings)
    await cache.connect()

    # Define a cached function
    call_count = 0

    @cached(ttl=60, key_prefix="demo")
    async def expensive_operation(param: str):
        nonlocal call_count
        call_count += 1
        print(f"  💻 Executing expensive operation (call #{call_count})...")
        await asyncio.sleep(0.1)  # Simulate work
        return f"Result for {param}"

    # First call - cache miss
    print("📞 First call (cache miss)...")
    result1 = await expensive_operation("test")
    print(f"  Result: {result1}")

    # Second call - cache hit
    print("\n📞 Second call (cache hit)...")
    result2 = await expensive_operation("test")
    print(f"  Result: {result2}")
    print(f"  ✓ Function called {call_count} time(s) (should be 1)\n")

    # Test namespace
    print("📦 Testing cache namespace...")
    async with CacheNamespace("user:123") as ns:
        await ns.set("profile", {"name": "John Doe", "email": "john@example.com"})
        profile = await ns.get("profile")
        if profile:
            print(f"  ✓ Namespaced get: {profile['name']}")
        else:
            print(f"  ⚠️  Namespaced get returned None (Redis not available)")

    # Clean up
    await cache.clear_pattern("demo:*")
    await cache.clear_pattern("user:*")
    await cache.disconnect()
    print("\n✨ Decorator test complete!")


if __name__ == "__main__":
    asyncio.run(test_basic_operations())
    asyncio.run(test_decorators())
