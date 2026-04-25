Code Review — Phase 24 Observability & Monitoring

  Branch: phase-24-Observability-&-Monitoring (6 commits, 31 files, +2687/-84)
  Scope: Structured logging (24.1), Prometheus metrics (24.2), OpenTelemetry tracing (24.3), Docker observability profile (24.4), tests (24.5), docs
  (24.6).

  Overview

  Adds an opt-in observability stack: structlog JSON/console logs with request_id propagation, Prometheus metrics with bounded-cardinality labels, OTel
  tracing with auto-instrumentation for FastAPI/SQLAlchemy/HTTPX/Redis, plus a Docker observability profile bundling Jaeger + Prometheus + Grafana with a
  starter dashboard and alert rules.

  Strengths

  - Off-by-default everywhere. METRICS_ENABLED, OTEL_ENABLED both false; helpers are real no-ops (the _Noop collector class, _NullSpan) so call-site
  overhead is one boolean check.
  - Cardinality discipline. HTTP route label is the matched template, with an "unmatched" fallback so attackers can't blow up the TSDB by hitting
  /no-such/<random>. Test test_route_label_uses_template_not_raw_path enforces this.
  - Fault-tolerant init. Every OTel/instrumentation step is independently wrapped in try/except with a warning — backend stays up if the OTLP endpoint is
  down or an instrumentation package is missing.
  - Idempotent. configure_logging, init_metrics, init_tracing all guard against double-init and support force=True for tests.
  - Single source of truth for LLM telemetry. LLMUsageTracker._save_usage emits the same numbers it persists to llm_usage, so DB rows and Prom counters
  cannot diverge.
  - Sanitized request-id intake. Only [A-Za-z0-9_-]{1,128} accepted from clients; otherwise a fresh uuid4. Reflected on response as X-Request-ID.
  - Local-only Docker bindings (127.0.0.1:…) and no-new-privileges on each container.

  Issues

  🔴 Real bug — broken alert rule

  docker/prometheus/alerts.yml:32-37 (DbGuruConnectionPoolSaturation):

  expr: |
    max by (dialect) (dbguru_connection_pool_size) /
    on(dialect) group_left()                                                                                                                              
    max by (dialect) (dbguru_connection_pool_size) >= 0.9
                                                                                                                                                          
  This divides pool_size by itself — it's always 1.0 ≥ 0.9, so this alert always fires (after for: 10m). There's no pool_max_size metric exported to      
  compare against. Either expose pool max size as a gauge (e.g., dbguru_connection_pool_max_size{dialect}) and divide by it, or convert this to an        
  absolute-threshold alert until that metric exists.                                                                                                      
                  
  🟠 Aggressive global logger reset                                                                                                                       
   
  src/observability/logging_config.py:437-442 strips handlers from every logger in Logger.manager.loggerDict and forces propagate=True. This intentionally
   rehomes SQLAlchemy/uvicorn handlers, but it also means any third-party library that legitimately attaches a handler (e.g., a vendor SDK with its own
  log destination) will silently lose it. Consider scoping to a known list (sqlalchemy, uvicorn, alembic) instead of the kitchen sink.                    
                  
  🟠 metrics_endpoint reaches into private state                                                                                                          
   
  src/observability/metrics.py:761-774 walks manager._pools.items() without holding manager._lock. The list(...) snapshot prevents a                      
  mutation-during-iteration error, but the dialect aggregation can still see torn state during pool churn. Either expose a public
  get_pool_metrics_snapshot() on ConnectionPoolManager and use it, or async with manager._lock.                                                           
                  
  🟠 Test-isolation hazard                                                                                                                                
   
  tests/observability/test_metrics.py reloads src.main with importlib.reload(_m) inside each test (test_metrics_endpoint_*). Reload re-runs the module    
  body, which calls Settings() and re-mounts middleware/routers on a new app object — but it leaves the previously imported app and any registered
  Prometheus collectors behind. With pytest running in a single process, the _reset_metrics fixture clears dbguru_* collectors, but other module-level    
  state (rate limiter, lifespan) is not reset. This will be flaky once these tests are run in a session with other src.main-importing tests. Consider
  building each test's app via a small factory rather than reloading.

  🟡 Settings instantiated 4× in src/main.py                                                                                                              
   
  Lines 48, 56, 93, 106 each call Settings(). It's cheap but clearly unintended duplication. The lifespan-scope settings could be lifted to module level  
  (or use a cached get_settings() dependency).
                                                                                                                                                          
  🟡 _session_dialect per query                                                                                                                           
   
  src/core/executor.py:_session_dialect runs on every execute(). For AsyncSession, get_bind() can do work. Consider caching dialect on the executor or on 
  the session via session.info to keep the hot path cheap.
                                                                                                                                                          
  🟡 record_llm_call skips zero counts                                                                                                                    
   
  metrics.py:710-715 uses if input_tokens: — falsy on 0. Harmless today (no-op increment), but worth changing to is not None to avoid silently dropping a 
  legitimately-zero observation if behavior changes later.
                                                                                                                                                          
  🟡 Cache instrumentation only on get()                                                                                                                  
   
  src/cache/redis_client.py records hit/miss only in get(). Other read paths (get_pattern, multi-key fetches if any) won't show up. If the dashboard's    
  "Cache hit ratio" is meant to be representative, instrument all read entry points.
                                                                                                                                                          
  Test coverage gaps

  - RequestContextMiddleware has no direct tests — header sanitization, missing-header path, response header round-trip, contextvar leak prevention. Worth
   adding given the middleware writes a globally-shared contextvar.
  - SQL metrics on error (the _session_dialect failure paths) have no assertions.                                                                         
  - LLMUsageTracker._save_usage → record_llm_call integration is only verified by reading the code; no test asserts that a tracked call produces a Prom   
  counter increment.                                                                                                                                      
  - init_tracing with a real exporter and instrumentations is not exercised — test_llm_span_records_required_attributes_when_enabled bypasses init_tracing
   and pokes module globals directly.                                                                                                                     
                  
  Security / operational                                                                                                                                  
                  
  - Grafana defaults admin/admin (${GRAFANA_USER:-admin} / ${GRAFANA_PASSWORD:-admin}). Fine for local dev. Confirm OBSERVABILITY_GUIDE.md calls out a    
  MUST-change for any non-local deploy.
  - /metrics is unauthenticated and exempt from rate limiting (src/middleware/rate_limit.py:189). Acceptable when the endpoint is reachable only via the  
  cluster network, but the doc should explicitly say "protect at the reverse proxy in production" — leaking pool sizes, LLM costs, and traffic shape is   
  more than most teams want public.
  - Redaction list includes prompt, sql, query, result_rows. Good safety default but it will surprise developers who try to log these fields and see      
  [REDACTED]. Make sure this is documented prominently.                                                                                                   
   
  Minor / cosmetic                                                                                                                                        
                  
  - Branch name and the file docs/planning/Phase 24_Observability_&_Monitoring.md contain & and a space — works on macOS/Linux but is awkward to handle in
   shell scripts and CI artifacts. Worth renaming on the next branch.
  - src/observability/tracing.py:899 imports trace inside the try block but only uses it later via trace.set_tracer_provider — fine, just noting.         
                                                                                                                                                          
  Recommendation
                                                                                                                                                          
  Approve once the alert-rule division-by-self bug is fixed (or removed); everything else is non-blocking polish. The architecture (off-by-default,       
  cardinality-bounded, fault-tolerant) is solid and the call-site instrumentation is in the right places.

  Summary                                                                                                                                              
                                                                                                                                                     
  Reviewed both PR review files and addressed all real issues plus high-value polish. All 83 tests across observability, auth, ownership, and          
  rate-limit pass. The remaining test failures (test_feedback_api, test_query_history_deletion, test_result_narrator, test_schema_cache,               
  test_llm_usage_extended, plus test_api/test_models/test_e2e_*) are pre-existing on baseline (verified by stashing and re-running).                   
                                                                                                                                                       
  Real bugs fixed                                                                                                                                      

  1. Pool saturation alert (both reviews — high) — docker/prometheus/alerts.yml: replaced pool_size / pool_size with pool_size / pool_max_size, with   
  clamp_min + an and max_size > 0 guard so partial registrations don't divide-by-zero. Added a new dbguru_connection_pool_max_size gauge and
  set_pool_max_size helper.                                                                                                                            
  2. LOG_INCLUDE_USER_ID non-functional (codex — high) — auth deps (get_current_user/get_optional_user) now call set_user_id() directly into the     
  structlog contextvar, so user_id flows through every in-handler log line, not just the trailing access log. Rate-limit middleware also sets it for   
  token-bearing requests that don't go through an auth dep.
  3. CORS missing X-Request-ID (codex — medium) — added to both allow_headers and expose_headers in src/main.py so browser clients can send and read   
  it.                                                                                                                                                  
  4. Aggressive global logger reset (review #1 — medium) — scoped the handler-strip-and-propagate logic to a known prefix list (sqlalchemy, uvicorn,
  alembic, fastapi, starlette) so third-party SDK loggers are left alone.                                                                              
  5. _refresh_pool_gauges torn-state read (review #1 — medium) — added public ConnectionPoolManager.get_pool_metrics_snapshot() that copies under    
  self._lock; metrics now uses it instead of walking _pools directly. Also feeds set_pool_max_size.                                                    
  6. OTel spans don't record exceptions (codex — medium) — added _record_exception() helper and wrapped both llm_call_span and self_correcting_span to
  call record_exception() + set_status(ERROR) and propagate exc_info into the underlying span's __exit__.                                              
  7. record_llm_call zero-drop (review #1 — minor) — switched truthy checks to is not None with safe coercion.                                       
  8. Settings instantiated 4× in main.py (review #1 — minor) — single module-level _settings instance; lifespan still re-reads in case env was mutated 
  post-import.                                                                                                                                         
  9. Redaction key list out of sync (codex — medium) — added x-api-key, result, rows; added recursive redaction (capped at depth 6) for nested         
  dicts/lists/tuples.                                                                                                                                  
                                                                                                                                                     
  Documentation hardened                                                                                                                               
                                                                                                                                                     
  10. docs/guides/OBSERVABILITY_GUIDE.md: documented /metrics proxy/firewall protection (with nginx allowlist example), Grafana admin/admin warning for
   non-local deployments, redaction limits (key-only, no exception-message scrubbing), Docker observability profile caveat (tooling-only — backend
  flags must also be enabled), and the new dbguru_connection_pool_max_size metric.                                                                     
                                                                                                                                                     
  Intentionally deferred

  - Test-isolation hazard with importlib.reload — flagged but tests pass; rewriting to a factory is bigger scope.                                      
  - _session_dialect per-query micro-opt — defer until shown hot in a profile.
  - mget() cache instrumentation — niche path; follow-up.                                                                                              
  - Branch name with & — cosmetic, only affects this branch.  