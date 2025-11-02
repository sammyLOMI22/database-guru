#!/usr/bin/env python3
"""
Test script for Multi-Database Streaming Results API

Usage:
    python test_multi_db_streaming_api.py
"""
import requests
import json
import time
from typing import Dict, List

BASE_URL = "http://localhost:8000"


def print_section(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def print_event(event_type: str, data: Dict, indent: int = 0):
    """Pretty print an SSE event"""
    prefix = "  " * indent

    if event_type == "status":
        status = data.get("status", "")
        message = data.get("message", "")
        print(f"{prefix}📊 Status: {status} - {message}")

    elif event_type == "database_start":
        conn_name = data.get("connection_name", "Unknown")
        db_type = data.get("database_type", "")
        print(f"\n{prefix}🚀 Starting: {conn_name} ({db_type})")

    elif event_type == "database_metadata":
        conn_name = data.get("connection_name", "Unknown")
        columns = data.get("columns", [])
        print(f"{prefix}📋 Columns from {conn_name}: {', '.join(columns)}")

    elif event_type == "database_data":
        conn_name = data.get("connection_name", "Unknown")
        rows = data.get("data", [])
        batch_num = data.get("batch_number", 0)
        rows_sent = data.get("rows_sent", 0)
        print(f"{prefix}📦 Batch #{batch_num} from {conn_name}: {len(rows)} rows (total: {rows_sent})")

        # Show first row if available
        if rows and len(rows) > 0:
            first_row = rows[0]
            print(f"{prefix}   Sample: {json.dumps(first_row, indent=2)[:100]}...")

    elif event_type == "database_complete":
        conn_name = data.get("connection_name", "Unknown")
        total_rows = data.get("total_rows", 0)
        exec_time = data.get("execution_time_ms", 0)
        print(f"{prefix}✅ Complete: {conn_name} - {total_rows} rows in {exec_time:.2f}ms")

    elif event_type == "database_error":
        conn_name = data.get("connection_name", "Unknown")
        error = data.get("error", "Unknown error")
        print(f"{prefix}❌ Error in {conn_name}: {error}")

    elif event_type == "all_complete":
        total_dbs = data.get("total_databases", 0)
        successful = data.get("successful_databases", 0)
        total_rows = data.get("total_rows", 0)
        total_time = data.get("total_execution_time_ms", 0)
        print(f"\n{prefix}🎉 All Complete!")
        print(f"{prefix}   Databases: {successful}/{total_dbs}")
        print(f"{prefix}   Total Rows: {total_rows}")
        print(f"{prefix}   Total Time: {total_time:.2f}ms")

    elif event_type == "error":
        error = data.get("error", "Unknown error")
        print(f"{prefix}❌ Critical Error: {error}")


def test_multi_db_streaming():
    """Test multi-database streaming"""
    print_section("Multi-Database Streaming Results API Test")

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

    # Get database connections
    conn_response = requests.get(f"{BASE_URL}/api/connections/")
    if conn_response.status_code != 200:
        print("❌ Failed to get database connections")
        return

    conn_data = conn_response.json()
    connections = conn_data.get('connections', conn_data) if isinstance(conn_data, dict) else conn_data

    if not connections:
        print("❌ No database connections found")
        return

    print(f"✅ Found {len(connections)} connection(s)")
    for conn in connections:
        print(f"   - {conn['name']} ({conn['database_type']})")

    # Test 1: Stream from all connections
    print_section("Test 1: Stream from Multiple Databases")

    connection_ids = [conn['id'] for conn in connections[:2]]  # Use first 2 connections

    print(f"Querying {len(connection_ids)} database(s)...\n")

    stream_url = f"{BASE_URL}/api/multi-query/stream"

    request_data = {
        "question": "Show me the first 10 rows",
        "connection_ids": connection_ids,
        "model": "qwen2.5-coder:32b"
    }

    # Start streaming
    start_time = time.time()
    print("📡 Starting multi-database stream...\n")

    response = requests.post(
        stream_url,
        json=request_data,
        stream=True,
        timeout=120  # Longer timeout for multiple databases
    )

    if response.status_code != 200:
        print(f"❌ Stream failed: {response.status_code}")
        print(response.text)
        return

    # Process SSE events
    current_event = None
    current_data = None

    stats = {
        "databases_started": 0,
        "databases_completed": 0,
        "databases_errored": 0,
        "total_batches": 0,
        "total_rows": 0,
    }

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

                    # Print event
                    print_event(current_event, parsed_data)

                    # Update stats
                    if current_event == "database_start":
                        stats["databases_started"] += 1
                    elif current_event == "database_data":
                        stats["total_batches"] += 1
                        stats["total_rows"] += len(parsed_data.get("data", []))
                    elif current_event == "database_complete":
                        stats["databases_completed"] += 1
                    elif current_event == "database_error":
                        stats["databases_errored"] += 1

                except json.JSONDecodeError as e:
                    print(f"❌ Failed to parse event data: {e}")

                # Reset for next event
                current_event = None
                current_data = None

    elapsed = time.time() - start_time

    print_section("Test Results")
    print(f"⏱️  Total Time: {elapsed:.2f}s")
    print(f"📊 Statistics:")
    print(f"   - Databases Started: {stats['databases_started']}")
    print(f"   - Databases Completed: {stats['databases_completed']}")
    print(f"   - Databases Errored: {stats['databases_errored']}")
    print(f"   - Total Batches: {stats['total_batches']}")
    print(f"   - Total Rows: {stats['total_rows']}")

    # Test 2: Stream with conversational memory
    print_section("Test 2: Stream with Conversational Memory")

    # Create a chat session first
    session_response = requests.post(
        f"{BASE_URL}/api/chat/sessions",
        json={
            "name": "Multi-DB Streaming Test Session",
            "database_connection_ids": connection_ids
        }
    )

    if session_response.status_code not in [200, 201]:
        print(f"⚠️  Could not create session: {session_response.status_code}")
        print("Skipping conversational memory test")
    else:
        session_data = session_response.json()
        session_id = session_data.get("id")
        print(f"✅ Created session: {session_id}")

        # First query
        print("\n📝 Query 1: 'Show me all products'")
        request_data = {
            "question": "Show me all products",
            "chat_session_id": session_id,
            "model": "qwen2.5-coder:32b"
        }

        response = requests.post(stream_url, json=request_data, stream=True, timeout=120)

        # Process events (simplified)
        for line in response.iter_lines(decode_unicode=True):
            if line.startswith('event:') and 'all_complete' in line:
                print("✅ Query 1 completed")
                break

        # Second query with context
        print("\n📝 Query 2: 'Filter by electronics' (should use context)")
        request_data["question"] = "Filter by electronics"

        response = requests.post(stream_url, json=request_data, stream=True, timeout=120)

        used_context = False
        for line in response.iter_lines(decode_unicode=True):
            if line.startswith('data:') and 'used_context' in line:
                data = json.loads(line[5:].strip())
                used_context = data.get("used_context", False)
            if line.startswith('event:') and 'all_complete' in line:
                break

        if used_context:
            print("✅ Query 2 completed with conversational context!")
        else:
            print("⚠️  Query 2 completed but may not have used context")

    print_section("All Tests Complete! 🎉")


if __name__ == "__main__":
    test_multi_db_streaming()
