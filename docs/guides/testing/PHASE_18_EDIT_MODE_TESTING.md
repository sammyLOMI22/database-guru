# Phase 18: Edit Mode & DML Operations — Testing Guide

**Last Updated**: March 21, 2026
**Branch**: `phase-18-edit-mode`
**Scope**: Security & Auth (Phase 21) + Edit Mode & DML (Phase 18)

---

## Prerequisites

### 1. Start the Backend

```bash
source venv/bin/activate

# Set the environment variable to enable write operations
export ALLOW_WRITE_OPERATIONS=true

python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

> **Without `ALLOW_WRITE_OPERATIONS=true`**, all DML execute requests will be rejected with a 403 error. This is intentional — writes are off by default for safety.

### 2. Start the Frontend

```bash
cd frontend
npm run dev
```

### 3. Run Alembic Migrations

The branch adds 4 new migrations. Apply them:

```bash
alembic upgrade head
```

Verify the new tables exist:
- `users`
- `audit_logs`
- `connection_write_permissions`
- `owner_id` columns on `database_connections`, `chat_sessions`, `file_sources`, `query_history`, `migration_projects`

### 4. Create a Test Database

Use the sample SQLite database or any SQL database with known data:

```bash
python scripts/create_sample_db.py
```

### 5. Ensure Ollama is Running

```bash
ollama serve
```

---

## Part 1: Authentication (Phase 21)

### 1.1 Register a User

**Via Swagger UI** (`http://localhost:8000/api/docs`):

```
POST /api/auth/register
{
  "email": "testuser@example.com",
  "username": "testuser",
  "password": "SecurePass123!"
}
```

**Expected**: 200 with `{ "access_token": "...", "token_type": "bearer" }`

**Edge Cases**:
- Register with same email again → 400 "Email already registered"
- Register with same username → 400 "Username already taken"
- Empty password → 422 validation error
- Invalid email format → 422 validation error

### 1.2 Login

```
POST /api/auth/login
{
  "email": "testuser@example.com",
  "password": "SecurePass123!"
}
```

**Expected**: 200 with a new JWT token

**Edge Cases**:
- Wrong password → 401 "Invalid credentials"
- Non-existent email → 401 "Invalid credentials" (same message — no user enumeration)
- Empty fields → 422

### 1.3 Get Current User

```
GET /api/auth/me
Authorization: Bearer <token>
```

**Expected**: 200 with user info (id, email, username, is_admin)

**Edge Cases**:
- No Authorization header → 401
- Expired/invalid token → 401
- Malformed token (random string) → 401

### 1.4 Frontend Auth Flow

1. Open `http://localhost:3000`
2. If `REQUIRE_AUTH=true`, you should see the login/register page
3. Register a new account
4. Verify the JWT token is stored (check browser DevTools → Application → Local Storage)
5. Verify the header shows the username and a logout button
6. Click logout → token cleared, redirected to auth page

**Edge Case**: If `REQUIRE_AUTH=false` (default), the app should work without login — auth is optional.

---

## Part 2: Resource Ownership (Phase 21)

### 2.1 Connection Ownership

1. **Log in as User A** and create a database connection
2. **Log in as User B** (register a second user)
3. As User B, try to access User A's connection → **Expected**: 403 Forbidden
4. As User B, try to list connections → should only see User B's connections (and unowned ones)

### 2.2 Session Ownership

1. As User A, create a chat session and send a query
2. As User B, try to access User A's session → 403
3. As User B, list sessions → should not see User A's sessions

### 2.3 Unowned Resources (REQUIRE_AUTH=false)

When `REQUIRE_AUTH=false`:
- Connections/sessions created without auth have `owner_id=NULL`
- Any user (authenticated or not) can access unowned resources
- Authenticated users' new resources get `owner_id` set

---

## Part 3: Rate Limiting (Phase 21)

### 3.1 Per-User Rate Limits

1. Log in and note the user ID from the JWT
2. Send many rapid requests to `/api/query/` (default limit: 200/min)
3. After exceeding the limit → **Expected**: 429 Too Many Requests
4. Verify the rate limit key is per-user (not per-IP) when authenticated

### 3.2 LLM-Specific Rate Limits

The LLM endpoint limit is 30/min per user. This is harder to hit manually but can be tested with:

```bash
for i in $(seq 1 35); do
  curl -s -o /dev/null -w "%{http_code}\n" \
    -H "Authorization: Bearer <token>" \
    -X POST http://localhost:8000/api/query/ \
    -H "Content-Type: application/json" \
    -d '{"question":"test","connection_ids":[1]}'
done
```

**Expected**: First ~30 return 200, then 429

### 3.3 Unauthenticated Rate Limiting

Without a token, rate limiting falls back to IP-based limiting. Verify the same IP gets rate-limited after exceeding the global limit.

---

## Part 4: Audit Logging (Phase 21)

### 4.1 View Audit Logs (Admin)

```
GET /api/audit/logs
Authorization: Bearer <admin-token>
```

**Edge Cases**:
- Non-admin user → 403 Forbidden
- Filter by action: `?action=login`
- Filter by resource type: `?resource_type=connection`

### 4.2 View My Logs

```
GET /api/audit/logs/me
Authorization: Bearer <token>
```

Should return only the current user's actions.

### 4.3 Verify Actions are Logged

After performing these actions, check audit logs for entries:
- Register → `action=register`
- Login → `action=login`
- Create connection → `action=create`
- Delete connection → `action=delete`
- DML execute → `action=dml_execute` (tested in Part 5)

---

## Part 5: Write Permissions Setup (Phase 18)

### 5.1 Check Default Permissions

```
GET /api/dml/permissions/1
Authorization: Bearer <token>
```

**Expected**: `{ "connection_id": 1, "write_enabled": false }` (no permissions configured yet)

### 5.2 Enable Write Permissions

```
PUT /api/dml/permissions/1
Authorization: Bearer <token>
{
  "allow_insert": true,
  "allow_update": true,
  "allow_delete": true,
  "require_where_clause": true,
  "max_rows_per_operation": 100
}
```

**Expected**: 200 with `write_enabled: true` and all flags set

**Edge Cases**:
- Unauthenticated request → 401 (write permissions always require auth)
- User B trying to set permissions on User A's connection → 403
- Setting `allowed_tables: ["products", "orders"]` → only those tables are editable
- Setting `max_rows_per_operation: 1` → limits batch size to 1

### 5.3 Partial Permissions

```
PUT /api/dml/permissions/1
{
  "allow_insert": true,
  "allow_update": false,
  "allow_delete": false
}
```

Then try to execute an UPDATE → **Expected**: 403 "UPDATE operations are not allowed on this connection."

---

## Part 6: Table Info (Phase 18)

### 6.1 Get Table Info

```
GET /api/dml/table-info/1/products
Authorization: Bearer <token>
```

**Expected**:
```json
{
  "table_name": "products",
  "primary_key_columns": ["id"],
  "columns": [
    { "name": "id", "type": "INTEGER", "nullable": false, "is_primary_key": true, "is_autoincrement": true },
    { "name": "name", "type": "VARCHAR", "nullable": false, "is_primary_key": false },
    ...
  ]
}
```

**Edge Cases**:
- Non-existent table → 500 or empty response (depends on DB driver)
- Table name with SQL injection attempt (e.g., `products; DROP TABLE users`) → 400 "Invalid table name"
- Table name with spaces or special chars → 400 "Invalid table name"

---

## Part 7: DML Preview (Phase 18)

### 7.1 Preview an UPDATE

```
POST /api/dml/preview
{
  "connection_id": 1,
  "changes": [
    {
      "change_type": "UPDATE",
      "table_name": "products",
      "primary_key": { "id": 1 },
      "changes": [
        { "column": "name", "old_value": "Widget A", "new_value": "Widget A Pro" }
      ]
    }
  ]
}
```

**Expected**:
```json
{
  "sql": "-- Generated DML Script\n-- Dialect: sqlite\n-- Changes: 1\n\nBEGIN;\n\n-- UPDATE on products\nUPDATE \"products\"\nSET \"name\" = 'Widget A Pro'\nWHERE \"id\" = 1;\n\nCOMMIT;",
  "change_count": 1,
  "summary": { "INSERT": 0, "UPDATE": 1, "DELETE": 0 },
  "statements": [...]
}
```

### 7.2 Preview an INSERT

```
POST /api/dml/preview
{
  "connection_id": 1,
  "changes": [
    {
      "change_type": "INSERT",
      "table_name": "products",
      "primary_key": {},
      "changes": [],
      "new_row_data": {
        "name": "New Product",
        "price": 29.99,
        "category_id": 1,
        "stock_quantity": 100
      }
    }
  ]
}
```

### 7.3 Preview a DELETE

```
POST /api/dml/preview
{
  "connection_id": 1,
  "changes": [
    {
      "change_type": "DELETE",
      "table_name": "products",
      "primary_key": { "id": 99 },
      "changes": []
    }
  ]
}
```

### 7.4 Preview Mixed Changes

Send INSERT + UPDATE + DELETE in one request. Verify the output orders them: DELETEs first, UPDATEs second, INSERTs last.

### 7.5 Edge Cases

- **Empty changes list** → 200 with `change_count: 0`
- **NULL value in update**: `"new_value": null` → display SQL shows `NULL`
- **Boolean value**: `"new_value": true` → display SQL shows `TRUE`
- **String with single quote**: `"new_value": "O'Brien"` → display SQL escapes as `'O''Brien'`
- **Numeric value**: `"new_value": 42.5` → display SQL shows `42.5` (no quotes)

---

## Part 8: DML Execution (Phase 18)

> **WARNING**: Execution modifies real data. Use the sample database or a test database.

### 8.1 Execute an UPDATE

```
POST /api/dml/execute
Authorization: Bearer <token>
{
  "connection_id": 1,
  "changes": [
    {
      "change_type": "UPDATE",
      "table_name": "products",
      "primary_key": { "id": 1 },
      "changes": [
        { "column": "name", "old_value": "Laptop", "new_value": "Laptop Pro" }
      ]
    }
  ]
}
```

**Expected**: `{ "success": true, "rows_affected": 1 }`

**Verify**: Query the product and confirm the name changed.

### 8.2 Execute an INSERT

```
POST /api/dml/execute
Authorization: Bearer <token>
{
  "connection_id": 1,
  "changes": [
    {
      "change_type": "INSERT",
      "table_name": "products",
      "primary_key": {},
      "changes": [],
      "new_row_data": {
        "name": "Test Product",
        "price": 9.99,
        "category_id": 1,
        "stock_quantity": 50
      }
    }
  ]
}
```

**Verify**: Query the products table and confirm the new row exists.

### 8.3 Execute a DELETE

```
POST /api/dml/execute
Authorization: Bearer <token>
{
  "connection_id": 1,
  "changes": [
    {
      "change_type": "DELETE",
      "table_name": "products",
      "primary_key": { "id": 99 },
      "changes": []
    }
  ]
}
```

**Expected**: `rows_affected: 0` if id=99 doesn't exist (no error — DELETE WHERE non-existent is valid SQL).

### 8.4 Transaction Rollback on Error

Send a batch with one valid and one invalid statement:

```
POST /api/dml/execute
Authorization: Bearer <token>
{
  "connection_id": 1,
  "changes": [
    {
      "change_type": "UPDATE",
      "table_name": "products",
      "primary_key": { "id": 1 },
      "changes": [
        { "column": "name", "old_value": "Laptop Pro", "new_value": "Updated Name" }
      ]
    },
    {
      "change_type": "INSERT",
      "table_name": "products",
      "primary_key": {},
      "changes": [],
      "new_row_data": {
        "nonexistent_column": "value"
      }
    }
  ]
}
```

**Expected**: 400 error. The first UPDATE should be **rolled back** — product name should remain unchanged.

### 8.5 Audit Trail

After executing DML, check audit logs:

```
GET /api/audit/logs/me
Authorization: Bearer <token>
```

Should contain `dml_execute` entries with details including table_name, change_type, and SQL.

---

## Part 9: Validation Edge Cases (Phase 18)

### 9.1 Global Write Disabled

Stop the backend and restart **without** `ALLOW_WRITE_OPERATIONS=true`:

```bash
unset ALLOW_WRITE_OPERATIONS
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Try to execute → **Expected**: 403 "Write operations are disabled globally."

### 9.2 No Write Permissions Configured

Delete the permission record (or use a connection that was never configured):

```
POST /api/dml/execute
Authorization: Bearer <token>
{
  "connection_id": 2,
  "changes": [{ "change_type": "UPDATE", "table_name": "test", "primary_key": { "id": 1 }, "changes": [{ "column": "x", "new_value": "y" }] }]
}
```

**Expected**: 403 "Write permissions have not been configured for this connection."

### 9.3 Operation Type Not Allowed

Configure permissions with `allow_update: false`, then try an UPDATE → 403 "UPDATE operations are not allowed."

### 9.4 Table Not in Whitelist

Configure `allowed_tables: ["products"]`, then try to edit `orders` → 403 "Table 'orders' is not in the allowed tables list."

### 9.5 Missing Primary Key (WHERE clause required)

With `require_where_clause: true` (default), send an UPDATE with empty `primary_key: {}`:

**Expected**: 403 "UPDATE requires a WHERE clause (primary key must be specified)."

### 9.6 Row Count Exceeded

Configure `max_rows_per_operation: 2`, then send 3 UPDATEs:

**Expected**: 403 "Too many UPDATE operations (3). Maximum allowed: 2 per operation type."

### 9.7 Unsafe Identifier

```json
{
  "change_type": "UPDATE",
  "table_name": "products; DROP TABLE users",
  "primary_key": { "id": 1 },
  "changes": [{ "column": "name", "new_value": "test" }]
}
```

**Expected**: 403 "Invalid table name" (caught by `SAFE_IDENT_RE`)

### 9.8 NoSQL Connection

Try to execute DML on a MongoDB/Redis connection:

**Expected**: 403 "Edit mode is not supported for NoSQL databases."

### 9.9 Unauthenticated Execute

Try `/api/dml/execute` without an Authorization header:

**Expected**: 401 (execute always requires authentication)

### 9.10 Preview Without Auth

Try `/api/dml/preview` without auth (should work if `REQUIRE_AUTH=false` and connection is unowned):

**Expected**: 200 — preview does not require authentication by default

---

## Part 10: Frontend Edit Mode (Phase 18)

### 10.1 Enable Edit Mode

1. Connect to the sample SQLite database
2. Run a query: "show all products"
3. Look for the Edit Mode toggle in the query results area
4. Click the toggle to enter edit mode

**Prerequisites**: Write permissions must be configured for the connection (see Part 5).

### 10.2 Edit a Cell

1. In edit mode, click on a cell value (non-PK column)
2. Type a new value
3. Click away or press Enter to confirm
4. The cell should highlight (indicating a pending change)
5. The changes summary bar should show "1 UPDATE"

**Edge Cases**:
- Click a primary key column → should NOT be editable
- Edit a cell then revert to original value → change should be removed from tracker
- Edit multiple cells in the same row → should merge into a single UPDATE

### 10.3 Add a Row

1. Click the "Add Row" button (+ icon)
2. Fill in the form fields (PK fields with autoincrement should be optional)
3. Submit the form
4. The new row should appear in the table
5. Changes summary should show "1 INSERT"

**Edge Cases**:
- Submit with required fields empty → form validation error
- Add multiple rows → each gets a separate INSERT

### 10.4 Delete a Row

1. Select a row using the checkbox
2. Click the delete button (trash icon)
3. Confirm in the confirmation dialog
4. The row should be struck through or marked
5. Changes summary should show "1 DELETE"

**Edge Cases**:
- Delete then undo (if supported) → change removed from tracker
- Delete a row that was just added (pending INSERT) → both changes cancel out

### 10.5 Preview DML

1. Make several changes (edit, add, delete)
2. Click "Preview" in the changes summary bar
3. The DML Preview Panel should open showing:
   - Generated SQL script
   - Dialect-appropriate quoting
   - Transaction wrapping (BEGIN/COMMIT)
   - Correct ordering (DELETEs → UPDATEs → INSERTs)

### 10.6 Execute Changes

1. After reviewing the preview, click "Execute" / "Apply Changes"
2. Confirm the execution
3. **Expected**: Success message with rows_affected count
4. Re-run the original query to verify changes persisted

### 10.7 Discard Changes

1. Make some edits
2. Toggle edit mode OFF
3. All pending changes should be discarded
4. Re-entering edit mode starts fresh

---

## Part 11: Multi-Dialect Testing (Phase 18)

If you have multiple database types available, test that DML generates correct quoting:

| Dialect | Identifier Quoting | BEGIN Statement |
|---------|-------------------|-----------------|
| **PostgreSQL** | `"column_name"` | `BEGIN;` |
| **MySQL** | `` `column_name` `` | `BEGIN;` |
| **SQLite** | `"column_name"` | `BEGIN;` |
| **DuckDB** | `"column_name"` | `BEGIN;` |
| **MSSQL** | `[column_name]` | `BEGIN TRANSACTION;` |
| **Oracle** | `"column_name"` | `BEGIN;` |

Test via the preview endpoint by connecting to each database type.

---

## Part 12: Automated Tests

### Run All DML Tests

```bash
source venv/bin/activate
python -m pytest tests/dml/ -v
```

**Expected**: 40 tests passing across:
- `test_dml_generator.py` — Statement generation for all dialects and change types
- `test_dml_validator.py` — All 10 validation checks
- `test_dml_executor.py` — Async/sync execution, transaction rollback

### Run Auth Tests

```bash
python -m pytest tests/test_auth.py tests/test_ownership.py tests/test_rate_limit_user.py tests/test_audit.py -v
```

**Expected**: ~61 tests passing

### Run All Tests

```bash
./run_tests.sh
```

---

## Checklist

### Phase 21: Security & Auth
- [ ] User registration (happy path + duplicate email/username)
- [ ] User login (happy path + wrong password + non-existent user)
- [ ] JWT token in Authorization header
- [ ] GET /api/auth/me returns user info
- [ ] Connection ownership isolation (User A can't see User B's)
- [ ] Session ownership isolation
- [ ] Unowned resources accessible to all (when REQUIRE_AUTH=false)
- [ ] Per-user rate limiting kicks in at threshold
- [ ] Audit logs record login/register/create/delete events
- [ ] Admin-only audit log endpoint (403 for non-admin)
- [ ] Frontend auth flow (login/register/logout)

### Phase 18: Write Permissions
- [ ] Default permissions: write_enabled=false
- [ ] Enable write permissions (PUT /api/dml/permissions/{id})
- [ ] Partial permissions (allow_insert=true, allow_update=false)
- [ ] Allowed tables whitelist
- [ ] Max rows per operation limit
- [ ] Require WHERE clause enforcement

### Phase 18: DML Preview
- [ ] Preview UPDATE generates correct SQL
- [ ] Preview INSERT generates correct SQL
- [ ] Preview DELETE generates correct SQL
- [ ] Mixed changes ordered correctly (DELETE → UPDATE → INSERT)
- [ ] NULL, boolean, numeric, string with quotes all format correctly
- [ ] Transaction wrapping (BEGIN/COMMIT)
- [ ] Dialect-appropriate identifier quoting

### Phase 18: DML Execution
- [ ] Execute UPDATE changes data
- [ ] Execute INSERT adds row
- [ ] Execute DELETE removes row
- [ ] Transaction rollback on error (no partial changes)
- [ ] Audit log records dml_execute entries
- [ ] Audit log records dml_failed on error
- [ ] rows_affected count is accurate

### Phase 18: Validation
- [ ] ALLOW_WRITE_OPERATIONS=false blocks execution
- [ ] No permission record → blocked
- [ ] Wrong operation type → blocked
- [ ] Table not in whitelist → blocked
- [ ] Missing primary key → blocked (when require_where_clause=true)
- [ ] Row count exceeds max → blocked
- [ ] Unsafe table/column names → blocked
- [ ] NoSQL connection → blocked
- [ ] Unauthenticated execute → 401

### Phase 18: Frontend Edit Mode
- [ ] Edit mode toggle visible on query results
- [ ] Cell editing (click → edit → blur)
- [ ] PK columns not editable
- [ ] Revert edit removes change from tracker
- [ ] Add row form with schema-aware fields
- [ ] Delete row with confirmation
- [ ] Changes summary bar shows counts
- [ ] DML preview panel shows generated SQL
- [ ] Execute applies changes
- [ ] Discard changes on toggle off

### Cross-Feature
- [ ] Auth + DML: unauthenticated user cannot execute DML
- [ ] Auth + DML: User A cannot execute DML on User B's connection
- [ ] Audit: DML executions appear in audit logs with full details
- [ ] Soft-deleted connections: DML endpoints return 404 for deleted connections
