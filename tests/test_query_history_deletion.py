#!/usr/bin/env python3
"""
Test script for query history deletion bug fix

This tests the fix for the bug where deleting query history records
would fail with a foreign key constraint error when chat messages
reference them.

Usage:
    python test_query_history_deletion.py
"""
import requests
import json

BASE_URL = "http://localhost:8000"


def test_query_history_deletion():
    """Test that query history records can be deleted properly"""
    print("="*70)
    print("Testing Query History Deletion")
    print("="*70)

    # Step 1: Create a chat session
    print("\n1. Creating a test chat session...")
    session_response = requests.post(
        f"{BASE_URL}/api/chat/sessions",
        json={
            "name": "Test Session for Query Deletion",
            "connection_ids": [1]
        }
    )

    if session_response.status_code not in [200, 201]:
        print(f"❌ Failed to create session: {session_response.status_code}")
        return False

    session_id = session_response.json()["id"]
    print(f"✅ Created session: {session_id}")

    # Step 2: Execute a query to create a QueryHistory record
    print("\n2. Executing a query...")
    query_response = requests.post(
        f"{BASE_URL}/api/query/",
        json={
            "question": "Show me all products",
            "session_id": session_id,
            "use_cache": False
        }
    )

    if query_response.status_code != 200:
        print(f"❌ Failed to execute query: {query_response.status_code}")
        print(query_response.text)
        return False

    query_data = query_response.json()
    query_id = query_data.get("query_id")
    print(f"✅ Query executed, ID: {query_id}")

    # Step 3: Verify chat messages reference the query
    print("\n3. Verifying chat messages reference the query...")
    messages_response = requests.get(f"{BASE_URL}/api/chat/sessions/{session_id}/messages")

    if messages_response.status_code != 200:
        print(f"❌ Failed to get messages: {messages_response.status_code}")
        return False

    messages = messages_response.json()
    messages_with_query = [m for m in messages if m.get("query_history_id") == query_id]

    if not messages_with_query:
        print(f"⚠️  No messages reference query {query_id}")
    else:
        print(f"✅ Found {len(messages_with_query)} message(s) referencing query {query_id}")

    # Step 4: Delete the query history record (this is where the bug would occur)
    print(f"\n4. Deleting query history {query_id}...")
    delete_response = requests.delete(f"{BASE_URL}/api/query/history/{query_id}")

    if delete_response.status_code != 204:
        print(f"❌ Failed to delete query: {delete_response.status_code}")
        print(delete_response.text)
        return False

    print(f"✅ Successfully deleted query")

    # Step 5: Verify the query is deleted
    print("\n5. Verifying query is deleted...")
    verify_response = requests.get(f"{BASE_URL}/api/query/history/{query_id}")

    if verify_response.status_code != 404:
        print(f"❌ Query still exists! Status: {verify_response.status_code}")
        return False

    print(f"✅ Confirmed query is deleted (404)")

    # Step 6: Verify chat messages were updated (query_history_id set to NULL)
    print("\n6. Verifying chat messages were updated...")
    messages_response = requests.get(f"{BASE_URL}/api/chat/sessions/{session_id}/messages")

    if messages_response.status_code != 200:
        print(f"❌ Failed to get messages: {messages_response.status_code}")
        return False

    messages = messages_response.json()
    messages_with_null = [m for m in messages if m.get("query_history_id") is None]

    if len(messages_with_null) > 0:
        print(f"✅ Confirmed {len(messages_with_null)} message(s) have NULL query_history_id")
    else:
        print(f"⚠️  No messages with NULL query_history_id found")

    # Step 7: Clean up - delete the session
    print("\n7. Cleaning up test session...")
    cleanup_response = requests.delete(f"{BASE_URL}/api/chat/sessions/{session_id}")

    if cleanup_response.status_code != 204:
        print(f"⚠️  Failed to delete session: {cleanup_response.status_code}")
    else:
        print(f"✅ Test session deleted")

    print("\n" + "="*70)
    print("✅ ALL TESTS PASSED! Query history deletion works correctly!")
    print("="*70)
    return True


def test_delete_nonexistent_query():
    """Test deleting a non-existent query returns 404"""
    print("\n" + "="*70)
    print("Testing Deletion of Non-Existent Query")
    print("="*70)

    # Try to delete a query that doesn't exist
    print("\nDeleting non-existent query ID 999999...")
    delete_response = requests.delete(f"{BASE_URL}/api/query/history/999999")

    if delete_response.status_code == 404:
        print("✅ Correctly returned 404 for non-existent query")
        return True
    else:
        print(f"❌ Expected 404, got {delete_response.status_code}")
        return False


if __name__ == "__main__":
    # Check if backend is running
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print("❌ Backend not responding")
            exit(1)
    except requests.exceptions.ConnectionError:
        print("❌ Backend is not running. Start it with: ./start.sh")
        exit(1)

    # Run the tests
    test1_success = test_query_history_deletion()
    test2_success = test_delete_nonexistent_query()

    if test1_success and test2_success:
        print("\n🎉 All tests passed!")
        exit(0)
    else:
        print("\n❌ Some tests failed")
        exit(1)
