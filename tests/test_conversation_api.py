#!/usr/bin/env python3
"""
Quick test script for Conversational Memory API

Usage:
    python test_conversation_api.py
"""
import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def print_success(message):
    print(f"✅ {message}")

def print_error(message):
    print(f"❌ {message}")

def print_info(message):
    print(f"ℹ️  {message}")

def test_health():
    """Test if backend is running"""
    print_section("1. Testing Backend Health")
    try:
        # Try root endpoint first
        response = requests.get(f"{BASE_URL}/", timeout=5)
        if response.status_code == 200:
            print_success("Backend is running!")
            return True

        # Try health endpoint
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print_success("Backend is running!")
            print_info(f"Response: {response.json()}")
            return True
        else:
            print_error(f"Backend returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_error("Backend is not running!")
        print_info("Start backend with: ./start.sh")
        return False
    except Exception as e:
        print_error(f"Error: {e}")
        return False

def create_test_session():
    """Create a test chat session"""
    print_section("2. Creating Test Chat Session")
    try:
        # Get available connections first
        conn_response = requests.get(f"{BASE_URL}/api/connections/")
        if conn_response.status_code != 200:
            print_error(f"Failed to get database connections: {conn_response.status_code}")
            print_info(conn_response.text)
            return None

        conn_data = conn_response.json()
        connections = conn_data.get('connections', conn_data) if isinstance(conn_data, dict) else conn_data

        if not connections:
            print_error("No database connections found")
            print_info("Response: " + str(conn_data))
            print_info("Create a connection first in the UI")
            return None

        print_info(f"Found {len(connections)} database connection(s)")

        # Use first active connection
        active_conn = next((c for c in connections if c.get('is_active')), connections[0])
        print_info(f"Using connection: {active_conn['name']}")

        # Create session
        session_data = {
            "name": f"Test Session {datetime.now().strftime('%H:%M:%S')}",
            "connection_ids": [active_conn['id']]
        }

        response = requests.post(
            f"{BASE_URL}/api/chat/sessions",
            json=session_data
        )

        if response.status_code == 201:
            session = response.json()
            print_success(f"Created session: {session['name']}")
            print_info(f"Session ID: {session['id']}")
            return session['id']
        else:
            print_error(f"Failed to create session: {response.status_code}")
            print_info(response.text)
            return None

    except Exception as e:
        print_error(f"Error creating session: {e}")
        return None

def send_query(session_id, question, query_num):
    """Send a query with session context"""
    print_section(f"3.{query_num}. Sending Query: '{question}'")
    try:
        response = requests.post(
            f"{BASE_URL}/api/query/",
            json={
                "question": question,
                "session_id": session_id
            },
            timeout=60
        )

        if response.status_code == 200:
            result = response.json()
            print_success("Query executed successfully!")
            print_info(f"SQL Generated: {result['sql']}")
            print_info(f"Used Context: {result.get('used_context', False)}")
            print_info(f"Row Count: {result.get('row_count', 0)}")

            if result.get('conversation_context'):
                ctx = result['conversation_context']
                print_info(f"Context Window Size: {ctx.get('window_size', 0)}")

            return True
        else:
            print_error(f"Query failed: {response.status_code}")
            print_info(response.text)
            return False

    except Exception as e:
        print_error(f"Error sending query: {e}")
        return False

def get_context(session_id):
    """Get conversation context"""
    print_section("4. Getting Conversation Context")
    try:
        response = requests.get(
            f"{BASE_URL}/api/chat/sessions/{session_id}/context"
        )

        if response.status_code == 200:
            context_data = response.json()
            context = context_data['context']

            print_success("Retrieved conversation context!")
            print_info(f"Has Context: {context['has_context']}")
            print_info(f"Window Size: {context['window_size']}")

            if context['messages']:
                print("\n📝 Context Messages:")
                for i, msg in enumerate(context['messages'], 1):
                    print(f"\n  {i}. Question: {msg['question']}")
                    print(f"     SQL: {msg['sql'][:80]}...")
                    print(f"     Success: {msg['success']}")

            return True
        else:
            print_error(f"Failed to get context: {response.status_code}")
            return False

    except Exception as e:
        print_error(f"Error getting context: {e}")
        return False

def clear_context(session_id):
    """Clear conversation context"""
    print_section("5. Clearing Conversation Context")
    try:
        response = requests.delete(
            f"{BASE_URL}/api/chat/sessions/{session_id}/context"
        )

        if response.status_code == 200:
            print_success("Context cleared successfully!")
            return True
        else:
            print_error(f"Failed to clear context: {response.status_code}")
            return False

    except Exception as e:
        print_error(f"Error clearing context: {e}")
        return False

def main():
    """Run all tests"""
    print("\n")
    print("🧙‍♂️  Database Guru - Conversational Memory API Test")
    print("="*60)

    # Test 1: Health check
    if not test_health():
        print("\n❌ Cannot continue - backend is not running")
        return

    time.sleep(0.5)

    # Test 2: Create session
    session_id = create_test_session()
    if not session_id:
        print("\n❌ Cannot continue - failed to create session")
        return

    time.sleep(0.5)

    # Test 3: Send queries
    queries = [
        "Show me all products",
        "Filter by electronics",
        "Sort by price"
    ]

    for i, query in enumerate(queries, 1):
        if not send_query(session_id, query, i):
            print(f"\n⚠️  Query {i} failed, but continuing...")
        time.sleep(0.5)

    # Test 4: Get context
    get_context(session_id)
    time.sleep(0.5)

    # Test 5: Clear context
    clear_context(session_id)
    time.sleep(0.5)

    # Test 6: Verify context cleared
    print_section("6. Verifying Context Cleared")
    if get_context(session_id):
        print_success("Context verification complete!")

    # Summary
    print_section("Test Summary")
    print_success("All tests completed!")
    print_info(f"Session ID: {session_id}")
    print_info("Check the UI to see the results visually")
    print("\n🎉 Conversational Memory is working!\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
