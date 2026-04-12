# Phase 15: LLM Provider Expansion — Testing Guide

**Last Updated**: April 11, 2026
**Branch**: `phase-15-llm-provider-expansion`
**Scope**: Multi-provider LLM support (8 providers), data security, provider routing, frontend UI

---

## Prerequisites

### 1. Start the Backend

```bash
source venv/bin/activate
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Start the Frontend

```bash
cd frontend
npm run dev
```

### 3. Run Alembic Migrations

The branch adds 1 new migration for provider tables:

```bash
alembic upgrade head
```

Verify the new tables exist:
- `llm_provider_configs` — stores provider configurations with encrypted API keys
- `llm_task_routing` — per-task provider routing overrides

### 4. Ensure Ollama is Running

```bash
ollama serve
```

Ollama must be running for default local LLM behavior.

### 5. (Optional) Set Up Cloud Provider Keys

To test cloud providers, set environment variables in `.env`:

```env
# OpenAI
OPENAI_ENABLED=true
OPENAI_API_KEY=sk-...

# Azure OpenAI
AZURE_OPENAI_ENABLED=true
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o

# Anthropic
ANTHROPIC_ENABLED=true
ANTHROPIC_API_KEY=sk-ant-...

# Google Vertex AI
GOOGLE_VERTEX_ENABLED=true
GOOGLE_VERTEX_PROJECT_ID=your-project

# AWS Bedrock
AWS_BEDROCK_ENABLED=true
AWS_BEDROCK_REGION=us-east-1

# Data security level (must be changed to allow cloud providers)
DATA_SECURITY_LEVEL=unrestricted
```

> **Important**: Without changing `DATA_SECURITY_LEVEL` from `local_only`, cloud providers will be registered but blocked from use. This is intentional — data never leaves your machine by default.

---

## Automated Tests

### Run All Phase 15 Tests

```bash
source venv/bin/activate
python -m pytest tests/llm/ -v
```

Expected: **184 tests pass** (0 failures).

### Test Breakdown by File

| Test File | Tests | What It Covers |
|-----------|-------|----------------|
| `tests/llm/test_provider_base.py` | 36 | BaseLLMProvider ABC, DataLocality, LLMResponse, ModelInfo, ProviderHealth |
| `tests/llm/test_tracked_client.py` | 24 | TrackedLLMClient wrapper, generate/chat with tracking, legacy dict conversion, backward compat |
| `tests/llm/test_openai_compat.py` | 46 | OpenAI, LM Studio, vLLM providers, httpx mocking, token extraction, registry auto-registration |
| `tests/llm/test_azure_anthropic.py` | 44 | Azure OpenAI (deployment URLs, API versioning), Anthropic (Messages API, content blocks) |
| `tests/llm/test_vertex_bedrock.py` | 36 | Google Vertex AI (REST + ADC), AWS Bedrock (boto3 Converse API, SigV4) |
| `tests/llm/test_phase15_4.py` | 36 | ModelRouter provider routing, execute_with_fallback, ProviderConfigService (encryption, CRUD) |

### Run Full Test Suite (Regression Check)

```bash
python -m pytest tests/ --ignore=tests/test_api.py --ignore=tests/test_end_to_end.py -q
```

Expected: **2177+ pass**, 0 new failures (pre-existing failures in server-dependent tests are expected).

### Frontend Build Check

```bash
cd frontend && npm run build
```

Expected: builds successfully with no TypeScript errors.

---

## Manual Testing: Backend API

Use Swagger UI at `http://localhost:8000/api/docs` or curl.

### Test 1: List Providers (Registry State)

```bash
curl http://localhost:8000/api/llm-providers/registry
```

**Expected**: JSON with `providers` array (at least `ollama`), `security_level: "local_only"`.

**Edge cases**:
- With no providers enabled in `.env`, only `ollama` should appear
- The `security_level` should match the `DATA_SECURITY_LEVEL` setting

### Test 2: List Provider Configs

```bash
curl http://localhost:8000/api/llm-providers/
```

**Expected**: Array of provider config objects with `registered` boolean indicating whether the provider is active in the registry.

### Test 3: Test Provider Connectivity

```bash
curl -X POST http://localhost:8000/api/llm-providers/ollama/test
```

**Expected**: `{ "provider": "ollama", "healthy": true, "message": "...", "data_locality": "local" }`

**Edge cases**:
- Test a non-registered provider → should return `healthy: false` with appropriate message
- Stop Ollama and test → should return `healthy: false`
- The test endpoint uses a synthetic prompt ("Hello, respond with OK") — verify no real schema data is sent

### Test 4: List Available Models

```bash
curl http://localhost:8000/api/llm-providers/ollama/models
```

**Expected**: Array of model objects with `name` field matching your pulled Ollama models.

**Edge cases**:
- Provider with no models → should return empty array, not error
- Non-existent provider → should return 404 or empty list

### Test 5: Configure a Provider via API

```bash
curl -X PUT http://localhost:8000/api/llm-providers/openai/config \
  -H "Content-Type: application/json" \
  -d '{"enabled": true, "api_key": "sk-test-key-123", "default_model": "gpt-4o"}'
```

**Expected**: Config saved. API key stored encrypted (not plaintext).

**Verify encryption**:
```bash
curl http://localhost:8000/api/llm-providers/openai/config
```
- `api_key_masked` should show something like `sk-t...123` (first 4 + last 3 chars)
- `api_key_encrypted` should be a Fernet-encrypted string, not the raw key

**Edge cases**:
- Configure without `LLM_ENCRYPTION_KEY` set → should auto-generate a key and log a warning
- Update config with new API key → should re-encrypt
- Update config without API key field → should preserve existing encrypted key
- Delete config → `DELETE /api/llm-providers/openai/config`

### Test 6: Task Routing CRUD

```bash
# Create a routing rule
curl -X PUT http://localhost:8000/api/llm-providers/routing/tasks \
  -H "Content-Type: application/json" \
  -d '{"task_type": "sql_generation", "primary_provider": "openai"}'

# List all routing rules
curl http://localhost:8000/api/llm-providers/routing/tasks

# Delete a routing rule
curl -X DELETE http://localhost:8000/api/llm-providers/routing/tasks/sql_generation
```

**Expected**: CRUD operations succeed. After delete, the task reverts to default provider.

**Edge cases**:
- Route to a non-registered provider → should save but provider won't be found at runtime
- Route to a provider blocked by security level → should save but execution will skip it and use fallback
- Duplicate upsert → should update, not create duplicate

### Test 7: Health Check All Providers

```bash
curl http://localhost:8000/api/llm-providers/health/all
```

**Expected**: Array of health results for each registered provider.

### Test 8: Data Security Level Enforcement

With `DATA_SECURITY_LEVEL=local_only`:

```bash
# Register OpenAI (cloud_public) — should succeed
curl -X PUT http://localhost:8000/api/llm-providers/openai/config \
  -H "Content-Type: application/json" \
  -d '{"enabled": true, "api_key": "sk-test", "data_locality": "cloud_public"}'

# Test OpenAI — should fail at test time or show blocked
curl -X POST http://localhost:8000/api/llm-providers/openai/test
```

**Expected**: Provider registers but is blocked from actual LLM calls. Test might show connectivity (it only sends a synthetic prompt) but the registry's `get()` with `enforce_security=True` should raise `DataSecurityError` when code tries to use it for real queries.

---

## Manual Testing: Frontend UI

### Test 9: Settings Panel — LLM Provider Section

1. Navigate to **Settings** (gear icon)
2. Scroll to the **LLM Providers** section at the top

**Expected**: 
- A **Local/Frontier** toggle is visible
- "Local" is selected by default with emerald accent
- Info text: "Your data stays on this machine"
- Provider cards for local providers (Ollama, optionally LM Studio/vLLM) are shown

### Test 10: Local/Frontier Toggle

1. Click the **Frontier** toggle button
2. A confirmation dialog should appear

**Expected**:
- Dialog warns about data leaving the network
- "Cancel" returns to Local mode
- "Enable Frontier" switches to Frontier mode with blue/indigo gradient accent
- Frontier provider cards (OpenAI, Azure, Anthropic, Vertex AI, Bedrock) appear

**Edge cases**:
- Toggle back to Local → no confirmation needed, just switches
- Toggle to Frontier with no cloud providers configured → cards show "Not registered" status

### Test 11: Provider Card Display

For each provider card, verify:
- **Name** and **locality badge** (`LOCAL` green, `PRIVATE CLOUD` blue, `FRONTIER` amber)
- **Status dot**: emerald (connected), red (unreachable), gray (unknown/not registered)
- **API Key display**: masked by default (`••••••••`), show/hide eye toggle works
- **Model**: shows configured default model
- **Endpoint**: shows configured URL (truncated if long)

### Test 12: Test Connection Button

1. Click **Test** on the Ollama card

**Expected**: 
- Button shows spinner during test
- Status updates to "Connected" (green) or "Unreachable" (red)
- Result message displayed below card details

**Edge cases**:
- Click Test while already testing → button should be disabled
- Test a not-registered provider → button should be disabled
- Network timeout → should show failure message, not hang

### Test 13: Configure Provider Modal

1. Click **Configure** on any provider card

**Expected**: 
- Modal opens with current provider settings
- Fields: Enabled toggle, API Key input, Endpoint URL, Default Model, Extra Config (JSON)
- Save persists to backend
- API key shows as masked if previously set

**Edge cases**:
- Enter empty API key and save → should clear/not overwrite existing
- Enter invalid JSON in Extra Config → should show validation error
- Save with provider disabled → should save config but unregister from registry

### Test 14: Per-Task Routing (Advanced Section)

1. Scroll to **Advanced: Per-Task Provider Routing** 
2. Click the chevron to expand

**Expected**:
- Table with 11 task types (SQL Generation, Data Narratives, etc.)
- Each row has a provider dropdown defaulting to "Default (Ollama)"
- Available providers listed in dropdown

**Test routing**:
1. Change "SQL Generation" to a different provider
2. Spinner shows while saving
3. Row gets amber left-border if routed to a frontier provider

**Edge cases**:
- Set to "Default" → should delete the routing rule (revert to default)
- Change provider while saving another → should queue or handle gracefully
- Expanded section loads routing rules on first expand (lazy loading)

### Test 15: Model Selection with Locality Badges

1. Go to **Settings** > **Model Configuration** section
2. Open any model dropdown

**Expected**:
- Models grouped by provider
- Each model has a color-coded locality dot:
  - `● LOCAL` (emerald) — Ollama, LM Studio, vLLM models
  - `◐ PRIVATE CLOUD` (blue) — Azure, Vertex AI, Bedrock models
  - `○ CLOUD` (amber) — OpenAI, Anthropic models
- Provider name shown as group header
- Selecting a model from a different provider updates the selection

**Edge cases**:
- Only one provider registered → should show flat list without group headers
- Provider with no models (e.g., not connected) → should not appear in dropdown
- Long model names → should truncate or wrap gracefully

---

## Edge Cases & Security Scenarios

### EC-1: Backward Compatibility (Critical)

All existing functionality must work identically without any provider configuration:

1. Start fresh with default settings (no `.env` changes)
2. Connect to a database
3. Ask a natural language question
4. Verify SQL is generated and executed via Ollama (default)

**Why**: The `get_llm_client()` function falls back to `get_ollama_client()` if the registry is empty. All 16 migrated callers must behave identically to before.

### EC-2: Security Level Cascade

Test that the security level blocks appropriately:

| Security Level | LOCAL providers | CLOUD_PRIVATE | CLOUD_PUBLIC |
|----------------|----------------|---------------|--------------|
| `local_only` | Allowed | Blocked | Blocked |
| `cloud_private` | Allowed | Allowed | Blocked |
| `unrestricted` | Allowed | Allowed | Allowed |

Verify by setting `DATA_SECURITY_LEVEL` and checking which providers appear in `list_allowed()`.

### EC-3: Fallback Chain Respects Security

1. Configure a task with primary provider = `openai` (cloud_public)
2. Add fallback chain: `[{"provider": "ollama"}]`
3. Set `DATA_SECURITY_LEVEL=local_only`

**Expected**: OpenAI is skipped (security blocked), Ollama fallback is used. No error raised.

### EC-4: Fallback Never "Falls Up"

1. Configure primary = `ollama` (local), fallback = `openai` (cloud_public)
2. Set `DATA_SECURITY_LEVEL=local_only`

**Expected**: If Ollama fails, OpenAI fallback is skipped because it's a higher security tier. Error raised rather than using blocked provider.

### EC-5: API Key Never in Plaintext

1. Configure a provider with an API key via the API
2. Query the config back: `GET /api/llm-providers/{name}/config`
3. Check the database directly: `SELECT * FROM llm_provider_configs`

**Expected**: 
- API response shows `api_key_masked` (e.g., `sk-t...123`), never the full key
- Database stores `api_key_encrypted` as a Fernet token, never plaintext
- Frontend never receives the decrypted key

### EC-6: Provider Test Never Sends Real Data

Review the test endpoint implementation:
- It sends a hardcoded synthetic prompt (e.g., "Hello, respond with OK")
- No schema names, table structures, or user data are included

### EC-7: Circular Import Prevention

The `get_llm_client()` function is defined in `src/llm/__init__.py`. Files within the `src/llm/` package (like `sql_generator.py` and `query_planning_agent.py`) use lazy imports to avoid circular dependencies:

```python
# Inside __init__ method, NOT at module level
from src.llm import get_llm_client
self.ollama = get_llm_client()
```

Verify by running:
```bash
python -c "from src.llm import get_llm_client; print('OK')"
python -c "from src.llm.sql_generator import SQLGenerator; print('OK')"
```

### EC-8: Concurrent Provider Configuration

1. Open two browser tabs on the Settings page
2. Configure different providers simultaneously
3. Verify both saves succeed without data corruption

### EC-9: Provider Registration at Startup

1. Set `OPENAI_ENABLED=true` and `OPENAI_API_KEY=sk-test` in `.env`
2. Restart the backend
3. Check `GET /api/llm-providers/registry`

**Expected**: OpenAI appears in the registered providers list. If `DATA_SECURITY_LEVEL=local_only`, it's registered but listed in `available` only (not in `allowed`).

### EC-10: Empty/Missing Settings Gracefully Handled

Test various partial configurations:

| Scenario | Expected Behavior |
|----------|-------------------|
| `OPENAI_ENABLED=true` but no `OPENAI_API_KEY` | OpenAI not registered (key required) |
| `AZURE_OPENAI_ENABLED=true` but missing `AZURE_OPENAI_ENDPOINT` | Azure not registered (endpoint required) |
| `GOOGLE_VERTEX_ENABLED=true` but no `GOOGLE_VERTEX_PROJECT_ID` | Vertex not registered (project ID required) |
| `AWS_BEDROCK_ENABLED=true` with no AWS credentials | Bedrock registered but health check fails |
| `LM_STUDIO_ENABLED=true` with no LM Studio running | LM Studio registered but health check fails |
| No `.env` changes at all | Only Ollama registered, everything works as before |

### EC-11: Model Router with Provider Routing

1. Set up a task routing rule: `sql_generation → openai`
2. Ask a SQL question
3. Check `LLMUsage` table

**Expected**: The `provider` column shows `openai` (or the configured provider), not `ollama`.

### EC-12: TrackedLLMClient Property Compatibility

Some callers access properties like `.model`, `.base_url`, `.client`, `.settings`:

```python
client = get_llm_client()
print(client.model)      # Should return default model string
print(client.base_url)   # Should return provider's base URL
print(client.client)     # Should return truthy value (backward compat)
```

Verify these don't raise AttributeError.

---

## Database Migration Verification

### New Tables

```sql
-- Check llm_provider_configs
SELECT name FROM sqlite_master WHERE type='table' AND name='llm_provider_configs';

-- Verify columns
PRAGMA table_info(llm_provider_configs);
-- Expected: id, provider_name (unique), enabled, data_locality, api_key_encrypted,
--           endpoint, default_model, extra_config, created_at, updated_at

-- Check llm_task_routing  
PRAGMA table_info(llm_task_routing);
-- Expected: id, task_type (unique), primary_provider, primary_model,
--           fallback_chain, created_at, updated_at
```

### Migration Rollback

```bash
alembic downgrade -1
```

Verify the `llm_provider_configs` and `llm_task_routing` tables are dropped cleanly.

---

## Performance Considerations

- **Registry initialization** happens once at startup (in `lifespan` handler). No per-request overhead.
- **`get_llm_client()`** is a lightweight factory — creates a new `TrackedLLMClient` wrapper per call. The underlying provider instance is shared via the registry singleton.
- **Health checks** (`/health/all`) call each provider sequentially — could be slow with many providers. Consider timeout limits if using in monitoring.
- **Fernet encryption** adds ~1ms overhead per encrypt/decrypt — negligible for config operations.

---

## Files Changed (Phase 15 Only)

### New Files (21)
| Category | Files |
|----------|-------|
| Provider Abstraction | `src/llm/providers/base.py`, `types.py`, `registry.py`, `__init__.py` |
| Provider Implementations | `ollama.py`, `openai_compat.py`, `openai_provider.py`, `azure_openai.py`, `anthropic.py`, `google_vertex.py`, `aws_bedrock.py`, `lm_studio.py`, `vllm.py` |
| Infrastructure | `src/llm/tracked_client.py`, `src/services/provider_config_service.py`, `src/api/endpoints/llm_providers.py` |
| Migration | `alembic/versions/e5f6a7b8c9d0_add_llm_provider_tables.py` |
| Frontend | `LLMProviderSettings.tsx`, `ProviderCard.tsx`, `TaskRoutingConfig.tsx`, `llmProviderApi.ts` |

### Modified Files (31)
| Category | Files |
|----------|-------|
| Core Shim | `src/llm/ollama_client.py` (rewritten as backward-compat alias), `src/llm/__init__.py` |
| Model Router | `src/llm/model_router.py` (provider routing + fallback) |
| Settings | `src/config/settings.py` (12 new provider settings) |
| Startup | `src/main.py` (registry init + route registration) |
| DB Models | `src/database/models.py` (LLMProviderConfig, LLMTaskRouting) |
| Caller Migration (16 files) | `sql_generator.py`, `query_planning_agent.py`, `lineage_conversation_agent.py`, `impact_advisor.py`, `lineage_narrator.py`, `schema_health_analyzer.py`, `pattern_intelligence.py`, `migration_planner.py`, `explain_interpreter.py`, `multi_db_query.py`, 5 NoSQL handlers |
| Frontend | `ModelConfigPanel.tsx` (locality badges), `SettingsPanel.tsx` (provider section) |
| Tests | 7 test files updated (mock patch targets) |

### Test Files (6 new, 7 modified)
- `tests/llm/test_provider_base.py` — 36 tests
- `tests/llm/test_tracked_client.py` — 24 tests
- `tests/llm/test_openai_compat.py` — 46 tests
- `tests/llm/test_azure_anthropic.py` — 44 tests
- `tests/llm/test_vertex_bedrock.py` — 36 tests
- `tests/llm/test_phase15_4.py` — 36 tests
- **Total**: 220+ new tests, 184 LLM tests passing
