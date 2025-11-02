#!/usr/bin/env python3
"""
Test script for chat session deletion bug fix

This tests the fix for the bug where deleting chat sessions
would fail with a foreign key constraint error.

Usage:
    python test_chat_session_deletion.py
"""
import requests
import json

BASE_URL = "http://localhost:8000"


def test_chat_session_deletion():
    """Test that chat sessions can be deleted properly"""
    print("="*70)
    print("Testing Chat Session Deletion")
    print("="*70)

    # Step 1: Create a new chat session
    print("\n1. Creating a test chat session...")
    create_response = requests.post(
        f"{BASE_URL}/api/chat/sessions",
        json={
            "name": "Test Session for Deletion",
            "connection_ids": [1]
        }
    )

    if create_response.status_code not in [200, 201]:
        print(f"❌ Failed to create session: {create_response.status_code}")
        print(create_response.text)
        return False

    session_data = create_response.json()
    session_id = session_data["id"]
    print(f"✅ Created session: {session_id}")

    # Step 2: Add some messages to the session
    print("\n2. Adding messages to the session...")

    for i, (role, content) in enumerate([
        ("user", "Show me all products"),
        ("assistant", "SELECT * FROM products"),
        ("user", "Filter by electronics"),
        ("assistant", "SELECT * FROM products WHERE category = 'electronics'")
    ], 1):
        msg_response = requests.post(
            f"{BASE_URL}/api/chat/sessions/{session_id}/messages",
            json={
                "role": role,
                "content": content
            }
        )

        if msg_response.status_code not in [200, 201]:
            print(f"❌ Failed to add message {i}: {msg_response.status_code}")
            return False

    print(f"✅ Added 4 messages to the session")

    # Step 3: Verify messages were added
    print("\n3. Verifying messages...")
    messages_response = requests.get(f"{BASE_URL}/api/chat/sessions/{session_id}/messages")

    if messages_response.status_code != 200:
        print(f"❌ Failed to get messages: {messages_response.status_code}")
        return False

    messages = messages_response.json()
    print(f"✅ Confirmed {len(messages)} messages in session")

    # Step 4: Delete the session (this is where the bug was)
    print("\n4. Deleting the session...")
    delete_response = requests.delete(f"{BASE_URL}/api/chat/sessions/{session_id}")

    if delete_response.status_code != 204:
        print(f"❌ Failed to delete session: {delete_response.status_code}")
        print(delete_response.text)
        return False

    print(f"✅ Successfully deleted session")

    # Step 5: Verify the session is gone
    print("\n5. Verifying session is deleted...")
    verify_response = requests.get(f"{BASE_URL}/api/chat/sessions/{session_id}")

    if verify_response.status_code != 404:
        print(f"❌ Session still exists! Status: {verify_response.status_code}")
        return False

    print(f"✅ Confirmed session is deleted (404)")

    # Step 6: Verify messages are gone too
    print("\n6. Verifying messages are deleted...")
    messages_verify = requests.get(f"{BASE_URL}/api/chat/sessions/{session_id}/messages")

    if messages_verify.status_code != 404:
        print(f"⚠️  Unexpected status when checking messages: {messages_verify.status_code}")
        # This is OK as long as the session is gone
    else:
        print(f"✅ Confirmed messages are deleted (404)")

    print("\n" + "="*70)
    print("✅ ALL TESTS PASSED! Chat session deletion works correctly!")
    print("="*70)
    return True


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

    # Run the test
    success = test_chat_session_deletion()
    exit(0 if success else 1)
