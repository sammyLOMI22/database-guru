# Phase 17: Multi-Provider Monitoring - Manual Testing Guide

**Date**: April 2026
**Scope**: Native token extraction for 6 provider formats, user-managed model pricing (CRUD), cost summary with daily breakdown, provider performance comparison, unpriced model detection, ModelPricingManager UI.

---

## Prerequisites

```bash
source venv/bin/activate
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
cd frontend && npm run dev
```

Swagger UI: http://localhost:8000/api/docs
Frontend: http://localhost:3000 (Usage tab)

---

## 1. Model Pricing Configuration (CRUD)

### 1.1 List Configs - Empty State

```bash
curl http://localhost:8000/api/llm/usage/model-configs
```

| Check | Expected |
|-------|----------|
| Empty DB | `[]` (no error) |
| HTTP status | 200 |

### 1.2 Create Model Config

```bash
# Ollama (free local model)
curl -X POST http://localhost:8000/api/llm/usage/model-configs \
  -H "Content-Type: application/json" \
  -d '{"model_name":"llama3","provider":"ollama","cost_per_1m_input_tokens":0.0,"cost_per_1m_output_tokens":0.0,"display_name":"Llama 3 (Local)"}'

# OpenAI
curl -X POST http://localhost:8000/api/llm/usage/model-configs \
  -H "Content-Type: application/json" \
  -d '{"model_name":"gpt-4o","provider":"openai","cost_per_1m_input_tokens":2.50,"cost_per_1m_output_tokens":10.00,"display_name":"GPT-4o"}'

# Anthropic
curl -X POST http://localhost:8000/api/llm/usage/model-configs \
  -H "Content-Type: application/json" \
  -d '{"model_name":"claude-3-5-sonnet","provider":"anthropic","cost_per_1m_input_tokens":3.00,"cost_per_1m_output_tokens":15.00}'
```

| Check | Expected |
|-------|----------|
| Returns created config with `id` | `id` is an integer |
| `is_active` field | `true` |
| `display_name` when omitted | Falls back to `model_name` |
| List configs after creates | All 3 present, sorted by provider then model_name |

### 1.3 Update (Upsert) Existing Config

```bash
# Update gpt-4o pricing (same model_name = update)
curl -X POST http://localhost:8000/api/llm/usage/model-configs \
  -H "Content-Type: application/json" \
  -d '{"model_name":"gpt-4o","provider":"openai","cost_per_1m_input_tokens":5.00,"cost_per_1m_output_tokens":15.00}'
```

| Check | Expected |
|-------|----------|
| Costs updated | input=5.00, output=15.00 |
| `display_name` preserved | Still "GPT-4o" (not overwritten when omitted) |
| `id` unchanged | Same id as original create |
| No duplicate created | Still only 1 gpt-4o entry in list |

### 1.4 Delete Config

```bash
curl -X DELETE http://localhost:8000/api/llm/usage/model-configs/llama3
```

| Check | Expected |
|-------|----------|
| Delete existing | 200 with `{"message": "Model config 'llama3' deleted"}` |
| List after delete | llama3 gone |

```bash
curl -X DELETE http://localhost:8000/api/llm/usage/model-configs/nonexistent-model
```

| Check | Expected |
|-------|----------|
| Delete non-existent | 404 with `"not found"` message |

### 1.5 Validation Edge Cases

```bash
# Missing required field (no provider)
curl -X POST http://localhost:8000/api/llm/usage/model-configs \
  -H "Content-Type: application/json" \
  -d '{"model_name":"test"}'
```

| Check | Expected |
|-------|----------|
| Missing `provider` | 422 validation error |
| Missing `cost_per_1m_input_tokens` | 422 validation error |
| Missing `cost_per_1m_output_tokens` | 422 validation error |
| Missing `model_name` | 422 validation error |

### 1.6 Special Characters in Model Names

```bash
# Colon in model name (common with Ollama tags)
curl -X POST http://localhost:8000/api/llm/usage/model-configs \
  -H "Content-Type: application/json" \
  -d '{"model_name":"llama3:latest","provider":"ollama","cost_per_1m_input_tokens":0,"cost_per_1m_output_tokens":0}'

# Delete with colon (URL encoding)
curl -X DELETE "http://localhost:8000/api/llm/usage/model-configs/llama3%3Alatest"
```

| Check | Expected |
|-------|----------|
| Create with colon | Succeeds |
| Delete with URL-encoded colon | Succeeds |
| Create with slash in name | Succeeds (test `model/v2`) |
| Delete with URL-encoded slash | Succeeds |

---

## 2. Unpriced Model Detection

### 2.1 Empty State

```bash
curl http://localhost:8000/api/llm/usage/unpriced-models
```

| Check | Expected |
|-------|----------|
| No usage records at all | `[]` |
| All models have pricing | `[]` |

### 2.2 With Usage but No Pricing

Generate some usage records first (run a few queries through the app with different models), then:

```bash
curl http://localhost:8000/api/llm/usage/unpriced-models
```

| Check | Expected |
|-------|----------|
| Models without config appear | Listed with `call_count` and `total_tokens` |
| Ordered by call_count | Most-used unpriced model first |
| After adding pricing for top model | That model disappears from list |
| `total_tokens` calculation | Sum of input + output tokens for that model |

### 2.3 Fuzzy Matching Does NOT Apply

The unpriced models endpoint uses exact model_name matching against the config table. It does NOT use fuzzy matching:

| Check | Expected |
|-------|----------|
| Config exists for "llama3" but usage has "llama3:latest" | "llama3:latest" shows as unpriced |
| Add explicit config for "llama3:latest" | Disappears from unpriced list |

> **Note**: Cost calculation uses fuzzy matching ("llama3:latest" -> "llama3" config), but the unpriced models endpoint does not. This means a model can be listed as "unpriced" while still having costs calculated via fuzzy match. This is by design -- it surfaces models that should have explicit pricing configured.

---

## 3. Cost Summary

### 3.1 Basic Query

```bash
curl "http://localhost:8000/api/llm/usage/cost-summary?days=30"
```

| Check | Expected |
|-------|----------|
| `period_days` | 30 |
| `total_cost_usd` | Sum of all `estimated_cost_usd` in range |
| `total_tokens` | Sum of input + output tokens |
| `total_calls` | Count of LLMUsage records in range |
| `avg_cost_per_call` | `total_cost_usd / total_calls` |
| `daily_costs` | Array of `{date, cost_usd, calls, tokens}` sorted by date |
| `by_provider` | Dict of `{provider_name: total_cost}` |

### 3.2 Empty Period

```bash
curl "http://localhost:8000/api/llm/usage/cost-summary?days=1"
```

(If no usage in last 24h)

| Check | Expected |
|-------|----------|
| `total_cost_usd` | 0.0 |
| `total_calls` | 0 |
| `avg_cost_per_call` | 0.0 (no division by zero) |
| `daily_costs` | `[]` |
| `by_provider` | `{}` |

### 3.3 Boundary Validation

```bash
curl "http://localhost:8000/api/llm/usage/cost-summary?days=0"    # Should fail
curl "http://localhost:8000/api/llm/usage/cost-summary?days=366"  # Should fail
curl "http://localhost:8000/api/llm/usage/cost-summary?days=1"    # Min valid
curl "http://localhost:8000/api/llm/usage/cost-summary?days=365"  # Max valid
```

| Check | Expected |
|-------|----------|
| days=0 | 422 validation error (`ge=1`) |
| days=366 | 422 validation error (`le=365`) |
| days=1 | 200, data from last 24h |
| days=365 | 200, data from last year |

### 3.4 Multi-Provider Cost Breakdown

After running queries against multiple providers:

| Check | Expected |
|-------|----------|
| Free provider (Ollama, $0 config) | Shows as `"ollama": 0.0` in by_provider |
| Paid provider (OpenAI, $5/$15 config) | Shows calculated cost |
| Provider with NULL estimated_cost_usd | Defaults to 0.0 |
| Sum of by_provider values | Equals total_cost_usd |

### 3.5 Daily Breakdown Accuracy

| Check | Expected |
|-------|----------|
| Dates are in chronological order | Ascending by date |
| Each day's `calls` | Matches count of records for that day |
| Each day's `tokens` | Sum of (input + output) for that day |
| Each day's `cost_usd` | Sum of estimated_cost_usd for that day |
| Days with no activity | Not included (gaps in list are expected) |

---

## 4. Provider Comparison

### 4.1 Basic Query

```bash
curl "http://localhost:8000/api/llm/usage/provider-comparison?days=7"
```

| Check | Expected |
|-------|----------|
| `period_days` | 7 |
| `by_agent_type` | Nested dict: agent_type -> provider -> stats |
| Each stat has `calls` | Integer count |
| Each stat has `avg_latency_ms` | Float or null |
| Each stat has `total_cost_usd` | Float (0.0 for free providers) |
| Each stat has `avg_tokens_per_call` | Float or null |
| Each stat has `success_rate` | 0.0-100.0 percentage |

### 4.2 Success Rate Calculation

| Scenario | Expected |
|----------|----------|
| 50 calls, 48 successful | `success_rate: 96.0` |
| 100 calls, 100 successful | `success_rate: 100.0` |
| 10 calls, 0 successful | `success_rate: 0.0` |
| 0 calls (shouldn't appear) | Not in results |

### 4.3 Boundary Validation

```bash
curl "http://localhost:8000/api/llm/usage/provider-comparison?days=0"   # Should fail
curl "http://localhost:8000/api/llm/usage/provider-comparison?days=91"  # Should fail
curl "http://localhost:8000/api/llm/usage/provider-comparison?days=1"   # Min valid
curl "http://localhost:8000/api/llm/usage/provider-comparison?days=90"  # Max valid
```

| Check | Expected |
|-------|----------|
| days=0 | 422 validation error (`ge=1`) |
| days=91 | 422 validation error (`le=90`) |

### 4.4 Empty Period

| Check | Expected |
|-------|----------|
| No usage in range | `by_agent_type: {}` |
| HTTP status | 200 (not error) |

---

## 5. By-Provider Endpoint (Updated)

### 5.1 Cost Field Added

```bash
curl "http://localhost:8000/api/llm/usage/by-provider?days=7"
```

| Check | Expected |
|-------|----------|
| Each provider entry includes `total_cost_usd` | Float value |
| Provider with $0 cost config | `total_cost_usd: 0.0` |
| Provider with no pricing config | `total_cost_usd: 0.0` |

---

## 6. Token Extraction (Per-Provider)

These are best tested by actually running queries through each configured provider. If you have access to multiple providers, run a simple query through each and verify tokens are extracted correctly.

### 6.1 Provider-Specific Token Formats

| Provider | Where to Check | Expected Token Fields |
|----------|---------------|----------------------|
| Ollama | Usage records | `input_tokens`, `output_tokens` from `prompt_eval_count`/`eval_count` |
| OpenAI | Usage records | From `usage.prompt_tokens`/`completion_tokens` |
| Azure OpenAI | Usage records | Same as OpenAI format |
| LM Studio | Usage records | Same as OpenAI format |
| vLLM | Usage records | Same as OpenAI format |
| Anthropic | Usage records | From `usage.input_tokens`/`output_tokens` |
| Google Vertex AI | Usage records | From `usageMetadata.promptTokenCount`/`candidatesTokenCount` |
| AWS Bedrock | Usage records | From `usage.inputTokens`/`outputTokens` |

### 6.2 Verification

After running a query through a provider:

```bash
curl "http://localhost:8000/api/llm/usage/recent?limit=1"
```

| Check | Expected |
|-------|----------|
| `input_tokens` | Non-null integer (native extraction worked) |
| `output_tokens` | Non-null integer (native extraction worked) |
| `estimated_cost_usd` | Calculated from token count * model pricing |
| `provider` field | Correct provider name |

### 6.3 Fallback Behavior

If native token extraction fails (missing fields in provider response), the tracker falls back to tiktoken estimation:

| Check | Expected |
|-------|----------|
| Tokens still recorded | Estimated values used |
| Cost still calculated | Based on estimated tokens |
| No error logged for normal fallback | Clean fallback |

---

## 7. Frontend Testing

### 7.1 Usage Dashboard - Cost Sections

Navigate to the **Usage** tab.

#### Cost by Provider Chart

| Check | Expected |
|-------|----------|
| Chart visible when cost data exists | Bar chart with provider names |
| Total cost displayed in header | `$X.XX` format |
| Empty state (no cost data) | "No provider cost data available" message |
| Hover tooltip on bars | Shows `$X.XXXX` (4 decimal places) |
| Multiple providers | All shown, bars proportional to cost |

#### Daily Cost Trend

| Check | Expected |
|-------|----------|
| Only shown when total_cost_usd > 0 | Hidden when no costs |
| Line chart with date axis | Dates formatted as MM/DD |
| Avg Cost per Call card | Shows `$X.XXXX` |
| Single day of data | Single point on chart |
| Many days of data | Smooth trend line |

#### Provider Performance Comparison Table

| Check | Expected |
|-------|----------|
| Only shown when data exists | Hidden when empty |
| Grouped by agent type | Section per agent type |
| Per-provider columns | Avg Latency, Avg Tokens, Cost/Call, Calls, Success |
| Success rate color coding | Green (>=95%), Yellow (>=80%), Red (<80%) |
| Null avg_latency | Shows "-" not "NaN" or "null" |
| Null avg_tokens_per_call | Shows "-" |
| Cost/call calculation | `total_cost / calls`, displayed as `$X.XXXX` |

### 7.2 Model Pricing Manager

Navigate to Usage tab, scroll to Model Pricing section.

#### Empty State

| Check | Expected |
|-------|----------|
| No configs | Empty table, no error |
| "Add Model" button visible | Always present |

#### Adding a New Config

1. Click "Add Model"
2. Fill in form fields

| Check | Expected |
|-------|----------|
| model_name field | Editable text input |
| provider field | Editable text input |
| cost fields | Editable number inputs |
| display_name field | Optional text input |
| Click Save | Config appears in table |
| Click Cancel (X) | Form dismissed, no change |

#### Validation

| Input | Expected |
|-------|----------|
| Cost = "abc" | Error: "Costs must be valid non-negative numbers" |
| Cost = "-5" | Error: "Costs must be valid non-negative numbers" |
| Cost = "0" | Valid (saves successfully) |
| Cost = "2.50" | Valid |
| Cost = "" (empty) | Error (NaN) |
| Cost = "2,500" (with comma) | Error (parseFloat returns NaN at comma) |
| Both costs valid | Saves successfully, error cleared |

#### Editing Existing Config

1. Click edit icon on a row

| Check | Expected |
|-------|----------|
| model_name | Disabled (cannot change) |
| provider | Disabled (cannot change) |
| Costs pre-filled | Current values shown |
| display_name pre-filled | Current value shown |
| Save with new costs | Updated in table |
| display_name left empty | Not overwritten if was previously set |

#### Deleting a Config

| Check | Expected |
|-------|----------|
| Click trash icon | Config removed immediately (no confirmation dialog) |
| Config disappears from table | After refresh |
| Network error on delete | Error message shown |

#### Unpriced Models Alert

| Check | Expected |
|-------|----------|
| Models in usage without pricing | Amber alert banner shown |
| Alert lists model names | With call count |
| Click "Set Pricing" on unpriced | Form opens with model_name/provider pre-filled and disabled |
| Save pricing for unpriced | Model disappears from alert, appears in table |
| All models priced | Alert hidden |

### 7.3 Time Range Interaction

| Check | Expected |
|-------|----------|
| Change from 7d to 30d | All charts refresh, including cost and comparison data |
| Change from 7d to 1d | Granularity stays "hour" |
| Change to 90d | All data loads (may be slow) |

### 7.4 Error Handling

| Check | Expected |
|-------|----------|
| Stop backend, load dashboard | Charts empty, errors in console |
| Stop backend, try to save config | "Failed to save pricing config" error shown |
| Stop backend, try to delete config | "Failed to delete pricing config" error shown |
| Restart backend, retry | Should work normally |

---

## 8. Integration Scenarios

### 8.1 End-to-End: New Model Discovery to Cost Tracking

1. Start with no model configs
2. Run several queries (generates LLM usage records)
3. Check `/unpriced-models` -- your model appears
4. Open frontend, see unpriced alert in Model Pricing Manager
5. Click "Set Pricing", enter costs, save
6. Model disappears from unpriced alert
7. Run more queries
8. Check `/cost-summary` -- new costs appear
9. Check dashboard -- Cost by Provider shows values

### 8.2 Cost Accuracy Verification

1. Configure "test-model" with $10.00/1M input, $20.00/1M output
2. Run query generating exactly 1000 input tokens and 500 output tokens
3. Expected cost: (1000/1M * $10) + (500/1M * $20) = $0.01 + $0.01 = $0.02
4. Verify in `/recent?limit=1`: `estimated_cost_usd` close to $0.02
5. Verify in `/cost-summary`: total includes this amount

### 8.3 Provider Switching

1. Configure two providers (e.g., Ollama + OpenAI)
2. Run 5 queries with Ollama, 5 with OpenAI
3. Check `/provider-comparison`:
   - Both providers listed under relevant agent types
   - Latency, cost, success rate accurate per provider
4. Check `/cost-summary`:
   - `by_provider` shows both with correct costs

### 8.4 Fuzzy Matching vs Explicit Config

1. Add config for "llama3" (no tag)
2. Run query with model "llama3:latest"
3. Verify: cost is calculated (fuzzy match works for cost calculation)
4. Check `/unpriced-models`: "llama3:latest" still listed (exact match only)
5. Add explicit config for "llama3:latest"
6. Check `/unpriced-models`: "llama3:latest" disappears
7. Verify: cost now uses explicit config (not fuzzy)

---

## 9. Edge Cases & Regression Checks

### 9.1 Configs/Seed Endpoint (Regression)

```bash
curl -X POST http://localhost:8000/api/llm/usage/configs/seed
```

| Check | Expected |
|-------|----------|
| Response | `{"message": "Model pricing is user-managed. Use POST /llm/usage/model-configs to configure."}` |
| DB unchanged | No new configs created |

### 9.2 Concurrent Updates

1. Open two browser tabs with Usage dashboard
2. Tab 1: Edit model cost to $5.00
3. Tab 2: Edit same model cost to $3.00, save
4. Tab 1: Save $5.00
5. Check: last write wins ($5.00)
6. Refresh Tab 2: shows $5.00

### 9.3 Large Dataset Performance

| Check | Expected |
|-------|----------|
| `/cost-summary?days=365` | Responds within 5 seconds |
| `/provider-comparison?days=90` | Responds within 5 seconds |
| 100+ model configs | List loads quickly |
| 1000+ usage records | Dashboard renders without lag |

### 9.4 Null/Zero Cost Handling

| Check | Expected |
|-------|----------|
| Model with $0/$0 costs (Ollama) | Cost = $0.00, NOT treated as "unpriced" |
| Model with no config at all | Cost = $0.00, listed as "unpriced" |
| `estimated_cost_usd` = NULL in DB | Defaults to 0.0 in summaries |

### 9.5 Provider Names Consistency

| Check | Expected |
|-------|----------|
| Provider name in usage vs config | Must match for cost calculation |
| "azure" vs "azure_openai" | Token extraction treats both as OpenAI-compatible |
| Unknown provider string | Token extraction returns (None, None), falls back to estimation |

---

## 10. Checklist Summary

### API Endpoints
- [ ] GET `/model-configs` - empty, populated, sorted order
- [ ] POST `/model-configs` - create, update, validation errors, special chars
- [ ] DELETE `/model-configs/{name}` - existing, non-existent, URL encoding
- [ ] GET `/unpriced-models` - empty, with unpriced, after pricing added
- [ ] GET `/cost-summary` - empty, populated, boundary days, daily accuracy
- [ ] GET `/provider-comparison` - empty, multi-provider, success rate math
- [ ] GET `/by-provider` - now includes `total_cost_usd`

### Frontend
- [ ] Cost by Provider chart renders with data
- [ ] Cost by Provider shows empty state message
- [ ] Daily Cost Trend hidden when no costs
- [ ] Daily Cost Trend shows correct data
- [ ] Provider Comparison table renders grouped by agent
- [ ] Success rate color coding works (green/yellow/red)
- [ ] Model Pricing Manager - add new config
- [ ] Model Pricing Manager - edit existing config
- [ ] Model Pricing Manager - delete config
- [ ] Model Pricing Manager - validation errors shown
- [ ] Unpriced models alert appears and disappears correctly
- [ ] Set Pricing from unpriced pre-fills form correctly
- [ ] Time range changes refresh all data

### Token Extraction
- [ ] Ollama tokens extracted natively
- [ ] OpenAI-compatible tokens extracted (OpenAI/Azure/LM Studio/vLLM)
- [ ] Anthropic tokens extracted natively
- [ ] Google Vertex AI tokens extracted natively
- [ ] AWS Bedrock tokens extracted natively
- [ ] Fallback to tiktoken estimation when native fails

### Integration
- [ ] End-to-end: unpriced -> add pricing -> costs appear
- [ ] Fuzzy matching works for cost calculation
- [ ] Explicit config overrides fuzzy match
- [ ] configs/seed is now a no-op
