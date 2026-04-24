Phase 24 - Observability & Monitoring Plan

Goal: production-grade observability via structured JSON logs, Prometheus metrics, and OpenTelemetry tracing, delivered in a safe rollout order and fully opt-in through settings and a Docker profile.

Why this phase:
- Phase 23 established Dockerized deployment, which makes a bundled observability profile practical.
- The product already has cost tracking, connection pooling, Redis caching, provider routing, and retrying agents; Phase 24 should expose those behaviors operationally without changing user-facing behavior.

Core design principles:
1. Everything is opt-in. Existing users should see no behavior change until observability flags or the Docker monitoring profile are enabled.
2. Observability must never block application startup or request handling. Exporter or collector failures degrade to warnings, not hard failures.
3. Reuse existing data where available. Token counts, costs, and success flags should come from existing tracking paths rather than being recomputed.
4. Keep scope production-useful but bounded. Ship logs to stdout and omit Loki/ELK from this phase.
5. Treat privacy and label cardinality as first-class requirements, not cleanup work.

Non-functional requirements:
- Logging, metrics, and tracing initialization must be idempotent under reload and repeated startup paths.
- If OTLP, Prometheus scraping, or Grafana are unavailable, the backend continues serving traffic.
- No prompts, SQL text, result rows, auth headers, cookies, API keys, or raw secrets may be emitted in logs, spans, or metrics.
- User identity in observability data must be bounded and explicit. request_id is allowed by default; user_id is only attached when already authenticated and only where the implementation already has that value safely available.
- Metric labels must remain bounded. Avoid labels that grow with traffic volume, user count, connection count, or arbitrary paths.

Implementation order:
1. Structured logging + request context
2. Metrics + /metrics endpoint
3. Docker monitoring profile + dashboards + alerts
4. OpenTelemetry tracing

This order is intentional: logs and metrics deliver immediate operational value and lower integration risk. Tracing comes last because it has the highest instrumentation surface area.

24.1 Structured Logging (~300 lines)

- New: src/observability/logging_config.py
  - Configure structlog with JSON renderer in production and key-value console output in development.
  - Preserve compatibility with existing logging.getLogger(...).info(...) calls.
  - Centralize redaction helpers for sensitive fields.
- New: src/middleware/request_context.py
  - ASGI middleware that assigns request_id from X-Request-ID or uuid4.
  - Bind request_id into a contextvars-backed structlog context for the full request lifecycle.
  - Optionally bind authenticated user_id when already available from validated JWT context.
- Update src/main.py
  - Replace both basicConfig bootstrap calls with configure_logging(settings).
  - Ensure logging is re-applied safely after Alembic startup behavior resets logging state.
- Update /health endpoint behavior
  - Return request_id in the response header to make request correlation easy during smoke testing and incidents.
- Settings:
  - LOG_FORMAT = json | console
  - LOG_LEVEL
  - LOG_INCLUDE_REQUEST_ID = true by default
  - LOG_INCLUDE_USER_ID = false by default

Logging policy:
- Required fields in every request-scoped log: timestamp, level, logger, event/message, request_id, environment.
- Recommended fields where available: user_id, route, method, status_code, duration_ms.
- Redact or omit:
  - Authorization, cookies, API keys, bearer tokens
  - Prompt text
  - SQL text
  - Query results / row payloads
  - Full exception payloads containing secrets

24.2 Metrics & Dashboards (~400 lines)

- New: src/observability/metrics.py
  - Define Prometheus collectors:
    - dbguru_http_requests_total{method,route,status}
    - dbguru_http_request_duration_seconds{method,route}
    - dbguru_llm_calls_total{provider,model,agent_type,success}
    - dbguru_llm_latency_seconds{provider,model,agent_type}
    - dbguru_llm_tokens_total{provider,model,direction}
    - dbguru_llm_cost_usd_total{provider,model}
    - dbguru_sql_query_duration_seconds{dialect,success}
    - dbguru_connection_pool_checkouts_total{dialect}
    - dbguru_connection_pool_size{dialect}
    - dbguru_cache_hits_total{cache}
    - dbguru_cache_misses_total{cache}
- New endpoint: GET /metrics exposed by prometheus-client.
- Hook existing completion points:
  - LLMUsageTracker / TrackedLLMClient for LLM counters and histograms.
  - SQLExecutor for query duration and success/failure.
  - Cache services for hit/miss counters where practical.
  - Connection pool manager for pool checkout and pool size gauges.

Metrics label policy:
- Use route templates, not raw URL paths.
- Do not use connection_id, request_id, query text, user_id, or model deployment IDs as metric labels.
- Prefer bounded dimensions only: provider, model, agent_type, dialect, success, cache, method, route, status.
- If a label set risks unbounded growth, drop the label before implementation.

Metrics exposure policy:
- Metrics collection and metrics endpoint exposure are separate controls.
- Settings:
  - METRICS_ENABLED = false by default
  - METRICS_EXPOSE_ENDPOINT = false by default
- If endpoint exposure is disabled, collectors may still exist for future in-process use but /metrics should not be mounted.
- If endpoint exposure is enabled, add /metrics to rate-limit exemptions.
- Keep /metrics unauthenticated only for internal Docker-network scraping. Document that direct public exposure is not recommended.

Dashboards and alerts:
- New: docker/grafana/dashboards/dbguru-overview.json
  - Panels:
    - request volume
    - request latency p50/p95/p99
    - error rate
    - LLM calls by provider/model
    - LLM latency
    - LLM cost per hour
    - SQL latency by dialect
    - cache hit ratio
    - connection pool saturation
- New: docker/prometheus/prometheus.yml
  - Scrape backend:8000/metrics every 15s.
- New: docker/prometheus/alerts.yml
  - Starter rules:
    - error rate > 5% for 5m
    - LLM latency p99 > 30s for 10m
    - connection pool saturation > 90% for 10m

24.3 OpenTelemetry Tracing (~500 lines)

- New: src/observability/tracing.py
  - Initialize TracerProvider with OTLP HTTP exporter.
  - Ensure exporter failures log warnings and do not fail startup.
- Auto-instrument at startup:
  - FastAPIInstrumentor
  - SQLAlchemyInstrumentor
  - HTTPXClientInstrumentor
  - RedisInstrumentor
- Manual spans in high-value paths only:
  - TrackedLLMClient.generate/chat
    - Attributes:
      - llm.provider
      - llm.model
      - llm.agent_type
      - llm.prompt_tokens
      - llm.completion_tokens
      - llm.cost_usd
      - llm.success
  - SelfCorrectingAgent.generate_and_execute_with_retry
    - Attributes:
      - agent.type
      - agent.attempts
      - agent.self_corrected
      - db.dialect
      - execution.success
- Reuse LLMUsageTracker-derived values for span attributes. Do not trigger extra tokenization or cost computation solely for tracing.
- Settings:
  - OTEL_ENABLED = false by default
  - OTEL_EXPORTER_OTLP_ENDPOINT = http://jaeger:4318
  - OTEL_SERVICE_NAME = database-guru
  - OTEL_TRACES_SAMPLER_RATIO = 0.1

Tracing policy:
- No prompt bodies, SQL statements, result data, or request/response bodies in span attributes.
- Only instrument hot paths and service boundaries; do not add spans to low-value helpers.
- Verify instrumentation is applied once and does not duplicate spans during reload/startup.

24.4 Docker Integration (~100 lines)

Add an observability profile to docker-compose.yml:
- jaeger
  - image: jaegertracing/all-in-one:1.56
  - UI: :16686
  - OTLP HTTP: :4318
- prometheus
  - image: prom/prometheus:v2.51
  - UI: :9090
- grafana
  - image: grafana/grafana:10.4
  - UI: :3001 to avoid conflict with frontend on :3000
  - pre-provision Prometheus datasource and dashboard

Backend wiring:
- Add observability env vars to .env.docker example values.
- Mount Prometheus and Grafana config from docker/prometheus and docker/grafana.
- Keep observability services on the internal Docker network by default.

Testing (~25 tests)

- tests/observability/test_logging_config.py
  - JSON logging renders correctly
  - console logging renders correctly
  - request_id propagates across a request
  - sensitive fields are redacted or omitted
- tests/observability/test_metrics.py
  - counters/histograms increment at expected completion points
  - /metrics scraping works when exposed
  - /metrics is absent or disabled when not exposed
  - label cardinality remains bounded for route and pool metrics
- tests/observability/test_tracing.py
  - tracer initialization is safe when OTEL is disabled
  - exporter failure does not crash startup
  - LLM span contains required attributes
  - self-correcting agent span contains required attributes
- Integration smoke tests:
  - Docker observability profile starts successfully
  - Prometheus scrapes backend
  - Grafana dashboard loads provisioned datasource

Acceptance criteria:
- Each handled HTTP request has a request_id available in logs and in the /health response header.
- Enabling logs does not change endpoint behavior and does not break existing logger calls.
- When METRICS_ENABLED=true and METRICS_EXPOSE_ENDPOINT=true, /metrics is scrapeable and exempt from rate limiting.
- Metrics use bounded labels only.
- When OTEL_ENABLED=true, LLM calls and self-correcting agent runs emit spans with the agreed attributes.
- If Prometheus, Grafana, Jaeger, or the OTLP endpoint are unavailable, the backend still starts and serves requests.
- When all observability flags are false, runtime behavior remains effectively the same as pre-Phase-24 behavior.

Deliverables:
- Code:
  - src/observability/logging_config.py
  - src/observability/metrics.py
  - src/observability/tracing.py
  - src/middleware/request_context.py
- Docker/config:
  - docker/prometheus/prometheus.yml
  - docker/prometheus/alerts.yml
  - docker/grafana/provisioning/...
  - docker/grafana/dashboards/dbguru-overview.json
- Docs:
  - docs/planning/Phase 24_Observability_&_Monitoring.md
  - docs/guides/OBSERVABILITY_GUIDE.md
  - docs/guides/testing/PHASE_24_OBSERVABILITY_TESTING.md
- Roadmap/docs follow-up:
  - Update MASTER_ROADMAP.md to remove the implied in-phase log aggregator if Phase 24 intentionally ships stdout JSON only.
  - Update CHANGELOG.md
  - Update CLAUDE.md if it references startup or monitoring workflows

Dependencies / requirements additions:
- opentelemetry-api==1.26.0
- opentelemetry-sdk==1.26.0
- opentelemetry-exporter-otlp-proto-http==1.26.0
- opentelemetry-instrumentation-fastapi
- opentelemetry-instrumentation-sqlalchemy
- opentelemetry-instrumentation-httpx
- opentelemetry-instrumentation-redis
- structlog and prometheus-client are already pinned

Out of scope for Phase 24:
- Loki, Elasticsearch, or any bundled log aggregation pipeline
- Long-term metrics retention tuning
- PagerDuty, Slack, or email notification integrations
- User-facing observability UI inside the main frontend app

Recommended implementation note:
- Build logs and metrics first, land Docker profile second, and add tracing last. If schedule pressure appears, tracing is the cleanest sub-scope to defer without undercutting the usefulness of the phase.
