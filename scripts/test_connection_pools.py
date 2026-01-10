#!/usr/bin/env python3
"""
Test script to create connection pools by executing queries
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def execute_query(question, connection_id, connection_name):
    """Execute a query via the API"""
    url = f"{BASE_URL}/api/query/"
    payload = {
        "question": question,
        "connection_id": connection_id,
        "use_planning": False
    }

    print(f"\n{'='*60}")
    print(f"🔍 Executing query on {connection_name}")
    print(f"Question: {question}")
    print(f"{'='*60}")

    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()

        print(f"✅ Success: {data.get('success')}")
        print(f"📊 SQL: {data.get('sql', 'N/A')[:100]}...")
        print(f"📈 Rows returned: {len(data.get('results', []))}")

        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")
        return False

def get_pool_stats():
    """Get current pool statistics"""
    url = f"{BASE_URL}/api/pools/stats"

    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()

        print(f"\n{'='*60}")
        print(f"📊 CURRENT POOL STATISTICS")
        print(f"{'='*60}")
        print(f"Total Pools: {data['total_pools']}")
        print(f"Total Active Connections: {data['global_metrics']['total_active_connections']}")
        print(f"Total Idle Connections: {data['global_metrics']['total_idle_connections']}")
        print(f"Avg Utilization: {data['global_metrics']['avg_utilization_percent']:.1f}%")
        print(f"Pooling Enabled: {data['pooling_enabled']}")

        if data['pools']:
            print(f"\n📋 Active Pools:")
            for pool in data['pools']:
                print(f"\n  Connection ID: {pool['connection_id']} ({pool['database_type'].upper()})")
                metrics = pool['metrics']
                print(f"    Active/Idle: {metrics['active_connections']}/{metrics['idle_connections']}")
                print(f"    Total Capacity: {metrics['total_capacity']}")
                print(f"    Utilization: {metrics['utilization_percent']:.1f}%")
                print(f"    Total Checkouts: {metrics['total_checkouts']}")
                print(f"    Total Checkins: {metrics['total_checkins']}")
                print(f"    Failed Checkouts: {metrics['failed_checkouts']}")
                print(f"    Avg Wait Time: {metrics.get('avg_wait_time_ms', 0):.2f}ms")
                print(f"    Age: {metrics.get('total_age_seconds', 0):.1f}s")
                print(f"    Health: {metrics.get('health_status', 'unknown').upper()}")
        else:
            print("\n  No active pools")

        return data
    except requests.exceptions.RequestException as e:
        print(f"❌ Error getting pool stats: {e}")
        return None

def get_pool_health():
    """Get pool health status"""
    url = f"{BASE_URL}/api/pools/health"

    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()

        print(f"\n{'='*60}")
        print(f"🏥 POOL HEALTH STATUS")
        print(f"{'='*60}")
        print(f"Status: {data['status'].upper()}")
        print(f"Total Pools: {data['total_pools']}")

        if data.get('warnings'):
            print(f"\n⚠️  Warnings:")
            for warning in data['warnings']:
                print(f"  - {warning}")
        else:
            print(f"\n✅ No warnings - All pools healthy!")

        return data
    except requests.exceptions.RequestException as e:
        print(f"❌ Error getting pool health: {e}")
        return None

def main():
    """Main test function"""
    print("\n" + "="*60)
    print("🏊 CONNECTION POOLING TEST SCRIPT")
    print("="*60)

    # Check backend is running
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        response.raise_for_status()
        print("✅ Backend is running")
    except requests.exceptions.RequestException:
        print("❌ Backend is not running. Please start it with:")
        print("   python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000")
        return

    # Get initial pool stats
    print("\n📊 INITIAL STATE:")
    get_pool_stats()

    # Test queries
    test_queries = [
        {
            "question": "Show me all products",
            "connection_id": 1,
            "connection_name": "ECommerceTestDB (SQLite)"
        },
        {
            "question": "Show me all customers",
            "connection_id": 1,
            "connection_name": "ECommerceTestDB (SQLite)"
        },
        {
            "question": "Count total orders",
            "connection_id": 1,
            "connection_name": "ECommerceTestDB (SQLite)"
        },
        {
            "question": "List all categories",
            "connection_id": 2,
            "connection_name": "Duck db eCommerce (DuckDB)"
        },
        {
            "question": "Show recent orders",
            "connection_id": 2,
            "connection_name": "Duck db eCommerce (DuckDB)"
        },
    ]

    print("\n\n🚀 EXECUTING TEST QUERIES...")

    successful = 0
    for query in test_queries:
        if execute_query(
            query["question"],
            query["connection_id"],
            query["connection_name"]
        ):
            successful += 1

        # Small delay between queries
        time.sleep(1)

    print(f"\n\n{'='*60}")
    print(f"📈 EXECUTION SUMMARY")
    print(f"{'='*60}")
    print(f"Total Queries: {len(test_queries)}")
    print(f"Successful: {successful}")
    print(f"Failed: {len(test_queries) - successful}")

    # Get final pool stats
    print("\n\n📊 FINAL STATE:")
    get_pool_stats()
    get_pool_health()

    # Instructions
    print("\n\n" + "="*60)
    print("🎯 NEXT STEPS")
    print("="*60)
    print("1. Open http://localhost:3000/ in your browser")
    print("2. Navigate to the 'Pools' tab")
    print("3. You should see active connection pools!")
    print("4. Observe the auto-refresh (every 10 seconds)")
    print("5. Try the manual refresh button")
    print("6. Try evicting a pool")
    print("\n📖 Full testing guide: docs/reports/CONNECTION_POOLING_MANUAL_TESTING.md")
    print("="*60)

if __name__ == "__main__":
    main()
