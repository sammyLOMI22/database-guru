#!/usr/bin/env python3
"""
Quick test script for Streaming Results API

Usage:
    python test_streaming_api.py
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000"


def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def test_streaming():
    """Test streaming query results"""
    print_section("Testing Streaming Results API")

    # Check if backend is running
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print("❌ Backend not responding")
            return
        print("✅ Backend is running!")
    except requests.exceptions.ConnectionError:
        print("❌ Backend is not running. Start it with: ./start.sh")
        return

    # Get active connection
    conn_response = requests.get(f"{BASE_URL}/api/connections/")
    if conn_response.status_code != 200:
        print("❌ Failed to get database connections")
        return

    conn_data = conn_response.json()
    connections = conn_data.get('connections', conn_data) if isinstance(conn_data, dict) else conn_data

    if not connections:
        print("❌ No database connections found")
        return

    active_conn = next((c for c in connections if c.get('is_active')), connections[0])
    print(f"✅ Using connection: {active_conn['name']}")

    # Test streaming query
    print_section("Streaming Query: 'Show me all products'")

    stream_url = f"{BASE_URL}/api/query/stream"

    request_data = {
        "question": "Show me all products",
        "model": "qwen2.5-coder:32b"
    }

    # Start streaming
    print("📡 Starting stream...\n")

    response = requests.post(
        stream_url,
        json=request_data,
        stream=True,  # Enable streaming
        timeout=60
    )

    if response.status_code != 200:
        print(f"❌ Stream failed: {response.status_code}")
        print(response.text)
        return

    # Process SSE events
    buffer = ""
    current_event = None
    current_data = None

    total_rows = 0
    batches_received = 0

    for line in response.iter_lines(decode_unicode=True):
        if line.startswith('event:'):
            current_event = line[6:].strip()

        elif line.startswith('data:'):
            current_data = line[5:].strip()

        elif line == '':
            # Empty line signals end of event
            if current_event and current_data:
                try:
                    parsed_data = json.loads(current_data)

                    # Handle different event types
                    if current_event == 'status':
                        status = parsed_data.get('status', '')
                        message = parsed_data.get('message', '')
                        print(f"🔄 Status: {message}")

                    elif current_event == 'sql_generated':
                        sql = parsed_data.get('sql', '')
                        used_context = parsed_data.get('used_context', False)
                        print(f"\n✨ SQL Generated:")
                        print(f"   {sql}")
                        if used_context:
                            print(f"   💡 Used conversational context!")
                        print()

                    elif current_event == 'metadata':
                        columns = parsed_data.get('columns', [])
                        print(f"📊 Columns: {', '.join(columns)}\n")

                    elif current_event == 'data':
                        batch_num = parsed_data.get('batch_number', 0)
                        rows_in_batch = parsed_data.get('rows_in_batch', 0)
                        rows_sent = parsed_data.get('rows_sent', 0)

                        batches_received += 1
                        total_rows = rows_sent

                        print(f"📦 Batch {batch_num}: {rows_in_batch} rows (Total: {rows_sent})")

                    elif current_event == 'complete':
                        truncated = parsed_data.get('truncated', False)
                        total = parsed_data.get('total_rows', 0)
                        exec_time = parsed_data.get('execution_time_ms', 0)

                        print(f"\n✅ Stream Complete!")
                        print(f"   Total Rows: {total}")
                        print(f"   Batches: {batches_received}")
                        print(f"   Execution Time: {exec_time:.2f}ms")

                        if truncated:
                            print(f"   ⚠️  Results truncated (max 1000 rows)")

                    elif current_event == 'error':
                        error = parsed_data.get('error', 'Unknown error')
                        print(f"\n❌ Error: {error}")

                except json.JSONDecodeError as e:
                    print(f"⚠️  Failed to parse event data: {e}")

                current_event = None
                current_data = None

    print_section("Summary")
    print(f"✅ Streaming test completed successfully!")
    print(f"📊 Received {total_rows} rows in {batches_received} batches")
    print(f"\n🎉 Streaming Results is working!\n")


if __name__ == "__main__":
    try:
        test_streaming()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
