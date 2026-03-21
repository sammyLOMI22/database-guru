# Phase 21: Security & Auth Foundation — Testing Guide

This guide covers how to verify Phase 21 (JWT authentication, resource ownership, per-user rate limiting, and audit logging) via automated tests and manual walkthroughs.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Running Automated Tests](#running-automated-tests)
3. [Test Coverage Summary](#test-coverage-summary)
4. [Creating a User](#creating-a-user)
5. [Manual Testing: Authentication](#manual-testing-authentication)
6. [Manual Testing: Resource Ownership](#manual-testing-resource-ownership)
7. [Manual Testing: Rate Limiting](#manual-testing-rate-limiting)
8. [Manual Testing: Audit Logging](#manual-testing-audit-logging)
9. [Configuration Reference](#configuration-reference)
10. [Known Limitations & Edge Cases](#known-limitations--edge-cases)

---

## Prerequisites

```bash
# 1. Activate virtualenv
source venv/bin/activate

# 2. Ensure auth dependencies are installed
pip install "python-jose[cryptography]" bcrypt email-validator

# 3. Run Alembic migrations (creates users, audit_logs tables + owner_id columns)
alembic upgrade head

# 4. Start the backend
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

> **Automated tests don't require a running server.** All tests use mocks.

---

## Running Automated Tests

### Run all Phase 21 tests

```bash
python -m pytest tests/test_auth.py tests/test_ownership.py tests/test_rate_limit_user.py tests/test_audit.py -v
```

### Run individual test files

```bash
# Authentication (password hashing, JWT, user CRUD, schemas)
python -m pytest tests/test_auth.py -v

# Resource ownership (session access, optional user, admin checks)
python -m pytest tests/test_ownership.py -v

# Per-user rate limiting (JWT extraction, user-based limits)
python -m pytest tests/test_rate_limit_user.py -v

# Audit logging (log creation, filtering, never-raises behavior)
python -m pytest tests/test_audit.py -v

# Connection soft-delete (updated with auth params)
python -m pytest tests/test_connection_soft_delete.py -v
```

### Run with coverage

```bash
python -m pytest tests/test_auth.py tests/test_ownership.py tests/test_rate_limit_user.py tests/test_audit.py --cov=src/auth --cov-report=term-missing
```

---

## Test Coverage Summary

| Test File | Tests | What It Covers |
|-----------|-------|----------------|
| `test_auth.py` | 25 | Password hashing (bcrypt), JWT create/decode/expiry/wrong-secret, user registration (with duplicate check), authentication (correct/wrong/inactive/nonexistent), Pydantic schema validation |
| `test_ownership.py` | 13 | Session ownership checks, `get_optional_user` with/without REQUIRE_AUTH, `get_current_user` 401 cases, `require_admin` 403, model attribute verification |
| `test_rate_limit_user.py` | 8 | JWT extraction from Authorization header, user-based rate limiting, independent limits per user, IP fallback for unauthenticated |
| `test_audit.py` | 8 | Audit entry creation, details JSON, never-raises on DB error, nullable fields, query with filters |
| `test_connection_soft_delete.py` | 3 | Delete with auth params, idempotent delete, 410 on activate-deleted |
| **Total** | **57** | |

---

## Creating a User

### Option 1: curl (recommended for quick testing)

```bash
# Register a new user
curl -s -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "alice@example.com",
    "username": "alice",
    "password": "securepass123"
  }' | python -m json.tool
```

**Response:**
```json
{
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 86400,
    "user": {
        "id": 1,
        "email": "alice@example.com",
        "username": "alice",
        "is_active": true,
        "is_admin": false,
        "created_at": "2026-03-13T10:00:00"
    }
}
```

Save the token for subsequent requests:

```bash
export TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### Option 2: Swagger UI

1. Open http://localhost:8000/api/docs
2. Find **POST /api/auth/register** and click "Try it out"
3. Fill in the request body:
   ```json
   {
     "email": "alice@example.com",
     "username": "alice",
     "password": "securepass123"
   }
   ```
4. Click "Execute"
5. Copy the `access_token` from the response
6. Click the "Authorize" button at the top of the page
7. Paste the token (without "Bearer " prefix) and click "Authorize"

### Option 3: Python script

```python
import asyncio
from src.auth.service import AuthService
from src.config.settings import Settings
from src.database.session import async_session_maker

async def create_user():
    settings = Settings()
    auth = AuthService(settings)
    async with async_session_maker() as db:
        user = await auth.register(db, "alice@example.com", "alice", "securepass123")
        print(f"Created user: {user.username} (id={user.id})")
        token, expires = auth.create_access_token(user.id, user.username)
        print(f"Token: {token}")

asyncio.run(create_user())
```

### Creating an Admin User

There is no admin registration endpoint — admin users are created by updating an existing user in the database:

```bash
# After registering a normal user, promote to admin via sqlite3
sqlite3 database_guru.db "UPDATE users SET is_admin = 1 WHERE username = 'alice';"
```

Or via Python:

```python
import asyncio
from sqlalchemy import update
from src.auth.models import User
from src.database.session import async_session_maker

async def make_admin(username: str):
    async with async_session_maker() as db:
        await db.execute(update(User).where(User.username == username).values(is_admin=True))
        await db.commit()
        print(f"{username} is now an admin")

asyncio.run(make_admin("alice"))
```

### User Registration Requirements

| Field | Requirement |
|-------|-------------|
| `email` | Valid email address (validated by `EmailStr`) |
| `username` | 3-100 chars, alphanumeric + underscore + hyphen only (`^[a-zA-Z0-9_-]+$`) |
| `password` | 8-128 characters |

---

## Manual Testing: Authentication

### Register a user

```bash
curl -s -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "bob@example.com", "username": "bob", "password": "mypassword123"}' \
  | python -m json.tool
```

### Register with duplicate email (expect 409)

```bash
curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "bob@example.com", "username": "bob2", "password": "mypassword123"}'
# Expected: 409
```

### Register with invalid input (expect 422)

```bash
# Short password
curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "x@x.com", "username": "test", "password": "short"}'
# Expected: 422

# Invalid username (spaces)
curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "x@x.com", "username": "bad name!", "password": "password123"}'
# Expected: 422

# Invalid email
curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "not-an-email", "username": "test2", "password": "password123"}'
# Expected: 422
```

### Login

```bash
curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "bob", "password": "mypassword123"}' \
  | python -m json.tool
# Expected: 200 with access_token
```

### Login with wrong password (expect 401)

```bash
curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "bob", "password": "wrongpassword"}'
# Expected: 401
```

### Get current user (/me)

```bash
curl -s http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer $TOKEN" \
  | python -m json.tool
# Expected: 200 with user info
```

### Access /me without token (expect 401)

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/auth/me
# Expected: 401
```

---

## Manual Testing: Resource Ownership

> **Important**: By default `REQUIRE_AUTH=False`, so endpoints allow unauthenticated access. However, ownership is **always enforced**: guests can only see unowned (legacy/guest) sessions, never sessions created by logged-in users. To require authentication on all endpoints, set `REQUIRE_AUTH=True` in your `.env`.

### Create a session as an authenticated user

```bash
curl -s -X POST http://localhost:8000/api/sessions/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name": "My session"}' \
  | python -m json.tool
# Expected: session created with owner_id set to your user ID
```

### List sessions (shows only owned sessions when authenticated)

```bash
curl -s http://localhost:8000/api/sessions/ \
  -H "Authorization: Bearer $TOKEN" \
  | python -m json.tool
# Expected: only sessions owned by this user (+ unowned sessions)
```

### Guest cannot see owned sessions

```bash
# Without a token, list sessions — should only show unowned (legacy/guest) sessions
curl -s http://localhost:8000/api/chat/sessions/ | python -m json.tool
# Expected: no sessions with owner_id set

# Try to access an owned session by ID without a token — expect 403
curl -s http://localhost:8000/api/chat/sessions/<owned-session-id>
# Expected: 403 "You do not have access to this session"

# Try to read messages from an owned session without a token — expect 403
curl -s http://localhost:8000/api/chat/sessions/<owned-session-id>/messages
# Expected: 403
```

### Access another user's session (expect 403)

```bash
# Register a second user, create a session with them, then try to access it
# with the first user's token — should return 403
```

### Create a connection with ownership

```bash
curl -s -X POST http://localhost:8000/api/connections/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "My PostgreSQL",
    "database_type": "postgresql",
    "host": "localhost",
    "port": 5432,
    "database_name": "mydb",
    "username": "pguser",
    "password": "pgpass"
  }' | python -m json.tool
# Expected: connection created with owner_id
```

---

## Manual Testing: Rate Limiting

### Verify per-user rate limiting

Rate limiting uses JWT user ID when available, falling back to IP address:

```bash
# Rapid-fire requests as authenticated user
for i in $(seq 1 10); do
  curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/api/sessions/ \
    -H "Authorization: Bearer $TOKEN"
done
# All should return 200 (well within 200/min limit)
```

### Verify unauthenticated falls back to IP

```bash
for i in $(seq 1 5); do
  curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/api/sessions/
done
# Uses IP-based rate limiting
```

---

## Manual Testing: Audit Logging

### View your own audit logs

```bash
curl -s http://localhost:8000/api/audit/logs/me \
  -H "Authorization: Bearer $TOKEN" \
  | python -m json.tool
# Expected: list of your register, login, create, delete actions
```

### Filter audit logs

```bash
# Only login events
curl -s "http://localhost:8000/api/audit/logs/me?action=login" \
  -H "Authorization: Bearer $TOKEN" \
  | python -m json.tool

# Only connection-related events
curl -s "http://localhost:8000/api/audit/logs/me?resource_type=connection" \
  -H "Authorization: Bearer $TOKEN" \
  | python -m json.tool
```

### View all audit logs (admin only)

```bash
# First promote your user to admin (see "Creating an Admin User" above)
curl -s http://localhost:8000/api/audit/logs \
  -H "Authorization: Bearer $TOKEN" \
  | python -m json.tool
# Expected: all audit logs across all users
```

### Access admin logs as non-admin (expect 403)

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/audit/logs \
  -H "Authorization: Bearer $TOKEN"
# Expected: 403 (if user is not admin)
```

---

## Configuration Reference

All settings are in `src/config/settings.py` and can be overridden via environment variables or `.env`:

| Setting | Default | Description |
|---------|---------|-------------|
| `JWT_SECRET` | `"change-this-jwt-secret"` | Secret key for signing JWT tokens. **Change in production!** |
| `JWT_ALGORITHM` | `"HS256"` | JWT signing algorithm |
| `JWT_EXPIRATION_MINUTES` | `1440` (24 hours) | Token expiration time |
| `REQUIRE_AUTH` | `False` | When `True`, all endpoints require a valid JWT token. When `False`, endpoints work without auth (backwards compatible) |
| `RATE_LIMIT_PER_USER` | `200` | Max requests per minute per authenticated user |
| `RATE_LIMIT_LLM_PER_USER` | `30` | Max LLM calls per minute per authenticated user |

### Enabling Mandatory Authentication

To require authentication on all endpoints:

```bash
# In .env
REQUIRE_AUTH=true
JWT_SECRET=your-production-secret-here
```

When `REQUIRE_AUTH=True`:
- All endpoints that use `get_optional_user` will require a valid token (401 if missing)
- Existing resources without an `owner_id` remain accessible to all authenticated users
- New resources are automatically assigned to the creating user

---

## Known Limitations & Edge Cases

1. **No password reset flow** — users cannot reset forgotten passwords (future work)
2. **No refresh tokens** — tokens expire after `JWT_EXPIRATION_MINUTES` and users must re-login
3. **Admin creation is manual** — no self-service admin registration; must update DB directly
4. **`owner_id` is nullable** — existing resources created before Phase 21 have `owner_id=NULL` and are accessible to all users (both guests and authenticated). Owned sessions (`owner_id` set) are only visible to their owner; guests receive 403
5. **SQLite FK enforcement** — SQLite does not enforce foreign keys by default, so `owner_id` referential integrity is enforced at the application level
6. **Audit log is append-only** — there is no endpoint to delete audit log entries
7. **Rate limit window** — per-user rate limiting uses the same sliding window as IP-based limiting (configured in `RATE_LIMIT_REQUESTS` / `RATE_LIMIT_WINDOW_SECONDS`)
8. **Feature flag scope** — `REQUIRE_AUTH=False` disables auth checks globally; there is no per-endpoint auth toggle
