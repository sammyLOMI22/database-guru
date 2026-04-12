# PR Review: `phase-15-llm-provider-expansion`

Base: `origin/main`
Head: `phase-15-llm-provider-expansion`
Review date: `2026-04-12`

## Findings

### 1. High: Provider configs are stored in the database but never applied to the runtime registry

The new admin surface writes provider settings into `llm_provider_configs`, but the live registry is still built only from environment settings at startup. That means saving a provider in the UI/API does not actually make it usable for routing, model listing, or health checks unless the same values are also present in `.env` and the app restarts.

References:
- [src/services/provider_config_service.py](/Users/sam/database-guru/src/services/provider_config_service.py:93)
- [src/main.py](/Users/sam/database-guru/src/main.py:83)
- [src/api/endpoints/llm_providers.py](/Users/sam/database-guru/src/api/endpoints/llm_providers.py:138)
- [src/api/endpoints/llm_providers.py](/Users/sam/database-guru/src/api/endpoints/llm_providers.py:198)

Why this matters:
- `PUT /api/llm-providers/{provider}/config` succeeds and returns stored config.
- `POST /api/llm-providers/{provider}/test` and `GET /api/llm-providers/{provider}/models` still read from the env-backed registry.
- `enabled`, `endpoint`, `default_model`, and encrypted API keys in the DB never drive runtime behavior.

Code suggestion:
```python
# After a successful provider config write/delete:
await db.commit()
await rebuild_provider_registry_from_db(db, settings)
invalidate_model_router()
```

Suggested direction:
- Add a DB-backed registry loader that hydrates providers from `LLMProviderConfig`.
- Rebuild or hot-swap the registry after provider config mutations.
- Treat env values as bootstrap defaults, not the only source of truth.

### 2. High: Per-task provider routing is effectively a no-op in real call paths

`ModelRouter` now loads `primary_provider` and even implements `execute_with_fallback()`, but the actual agent factories still create clients with `get_llm_client()` and never pass the routed provider name. In practice the branch changes the model string, but not the provider instance used for the call.

References:
- [src/llm/model_router.py](/Users/sam/database-guru/src/llm/model_router.py:257)
- [src/llm/model_router.py](/Users/sam/database-guru/src/llm/model_router.py:447)
- [src/llm/__init__.py](/Users/sam/database-guru/src/llm/__init__.py:14)
- [src/llm/sql_generator.py](/Users/sam/database-guru/src/llm/sql_generator.py:239)
- [src/lineage/lineage_narrator.py](/Users/sam/database-guru/src/lineage/lineage_narrator.py:498)

Why this matters:
- A routing rule like `sql_generation -> openai / gpt-4o` can still execute through the default client.
- The default client path currently picks the first allowed provider, which is usually still Ollama.
- The UI exposes routing as if it is active, but most production paths will ignore it.

Code suggestion:
```python
router = await get_model_router(db)
provider = router.get_provider_for_task(TaskType.SQL_GENERATION)
model = router.get_model_for_task(TaskType.SQL_GENERATION)
client = get_llm_client(provider)
```

Better long-term option:
```python
response = await router.execute_with_fallback(
    TaskType.SQL_GENERATION,
    messages=messages,
    temperature=temperature,
)
```

### 3. Medium: Several provider-management read endpoints are unauthenticated

The write endpoints require `require_admin`, but multiple read and introspection endpoints do not. Anonymous callers can enumerate configured providers, security level, routing rules, and in some cases trigger outbound provider calls.

References:
- [src/api/endpoints/llm_providers.py](/Users/sam/database-guru/src/api/endpoints/llm_providers.py:68)
- [src/api/endpoints/llm_providers.py](/Users/sam/database-guru/src/api/endpoints/llm_providers.py:94)
- [src/api/endpoints/llm_providers.py](/Users/sam/database-guru/src/api/endpoints/llm_providers.py:115)
- [src/api/endpoints/llm_providers.py](/Users/sam/database-guru/src/api/endpoints/llm_providers.py:222)
- [src/api/endpoints/llm_providers.py](/Users/sam/database-guru/src/api/endpoints/llm_providers.py:267)
- [src/api/endpoints/llm_providers.py](/Users/sam/database-guru/src/api/endpoints/llm_providers.py:326)

Why this matters:
- `GET /api/llm-providers/registry` exposes current security posture.
- `GET /api/llm-providers/routing/tasks` exposes internal task-to-provider mappings.
- `GET /api/llm-providers/{provider}/models` can enumerate cloud model/deployment inventory.
- `GET /api/llm-providers/health/all` can drive external requests without admin auth.

Code suggestion:
```python
@router.get("/registry")
async def list_registry_providers(
    _: User = Depends(require_admin),
) -> dict[str, Any]:
    ...
```

Minimum recommendation:
- Make every provider-management endpoint admin-only unless there is a clear product reason not to.

### 4. Medium: `GET /{provider_name}/models` serializes `ModelInfo` as if it were a dict

The endpoint iterates the provider result with `m.get(...)`, but `BaseLLMProvider.list_models()` is defined to return `list[ModelInfo]`, and the concrete providers do exactly that. This should raise an attribute error once the endpoint gets a non-empty result.

References:
- [src/api/endpoints/llm_providers.py](/Users/sam/database-guru/src/api/endpoints/llm_providers.py:246)
- [src/llm/providers/base.py](/Users/sam/database-guru/src/llm/providers/base.py:113)
- [src/llm/providers/ollama.py](/Users/sam/database-guru/src/llm/providers/ollama.py:202)

Why this matters:
- The endpoint appears shipped, but the happy path likely 500s.
- Current tests do not appear to cover this API path end-to-end.

Code suggestion:
```python
return [
    ProviderModelInfo(
        name=m.name,
        size=m.size,
        modified_at=None,
    )
    for m in models
]
```

If `modified_at` is needed, add it to `ModelInfo` first and keep one response type end-to-end.

### 5. Low: The new `llm_usage.data_locality` audit column is never populated

The migration and ORM model add `data_locality` to `llm_usage`, but the tracker never writes it. The branch advertises stronger provider auditability, yet this specific field will remain `NULL` for all new records.

References:
- [alembic/versions/e5f6a7b8c9d0_add_llm_provider_tables.py](/Users/sam/database-guru/alembic/versions/e5f6a7b8c9d0_add_llm_provider_tables.py:44)
- [src/database/models.py](/Users/sam/database-guru/src/database/models.py:23)
- [src/services/llm_usage_tracker.py](/Users/sam/database-guru/src/services/llm_usage_tracker.py:181)

Why this matters:
- Compliance and reporting cannot distinguish local vs private-cloud vs public-cloud calls.
- The schema change adds storage and migration cost without delivering the intended audit value.

Code suggestion:
```python
usage_record = LLMUsage(
    ...,
    provider=self.provider,
    data_locality=self.metadata.get("data_locality"),
    ...
)
```

Suggested implementation:
- Pass `provider.data_locality.value` into the tracker from `TrackedLLMClient`.

## What Works Well

- The provider abstraction is clean. `BaseLLMProvider`, `ProviderRegistry`, and the locality enum make the expansion path straightforward.
- The data-locality model is a good product boundary. Explicit `local`, `cloud_private`, and `cloud_public` tiers are easy to reason about.
- Mutating provider and routing actions are audited, which is the right default for this surface.
- Test investment is strong at the provider/unit level, especially around fallback logic and provider-specific clients.

## Future Directions

- Make provider enablement and `DATA_SECURITY_LEVEL` first-class runtime settings instead of env-only startup state. Right now the frontend “Local / Frontier” toggle is UI state only and does not change backend policy.
  References:
  [frontend/src/components/LLMProviderSettings.tsx](/Users/sam/database-guru/frontend/src/components/LLMProviderSettings.tsx:66)
  [src/main.py](/Users/sam/database-guru/src/main.py:83)
- Add end-to-end API tests for:
  - provider config activation
  - model listing
  - health checks
  - admin auth on all management routes
  - actual routed execution through non-default providers
- Add registry refresh and circuit-breaker behavior so unhealthy providers are temporarily avoided instead of retried blindly.

## New Feature Opportunities

- Cost-aware routing: choose provider/model by latency budget, token cost, and locality policy.
- Secret-manager support: store API keys in Vault/AWS Secrets Manager/Azure Key Vault instead of the app database when available.
- Health-based automatic failover: rank fallbacks by recent success rate and latency instead of a static chain.
- Per-task policy controls: for example, allow cloud for narratives but force local-only for SQL generation and schema-heavy tasks.
