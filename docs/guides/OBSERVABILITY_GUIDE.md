# Observability Guide (Phase 24 + Phase 24.7)

Database Guru ships with three production-grade observability primitives that
are **off by default** and turned on through environment variables, plus an
in-app admin surface that exposes them to operators:

1. Structured JSON logging with request-id propagation (24.1)
2. Prometheus metrics with a `/metrics` scrape endpoint (24.2)
3. OpenTelemetry tracing with OTLP HTTP export (24.3)
4. A Docker `observability` profile that bundles Jaeger, Prometheus, and
   Grafana (24.4)
5. **Admin & Observability UI (24.7)** — Last-request badge, audit log viewer,
   user management, Health sub-tab, and deep-links to Prometheus/Jaeger/Grafana
   from the Settings panel

All three pillars share the same design rules:

- **Opt-in.** When the relevant flag is `false`, the call sites pay essentially
  nothing — metric helpers are no-ops, span helpers return null spans, log
  format defaults to console.
- **Never block startup.** A missing OTLP endpoint, a refused Prometheus
  scrape, or a Grafana outage cannot prevent the backend from serving traffic.
- **Bounded labels.** Metric labels never use raw URL paths, query text,
  user_id, connection_id, or anything else that grows with usage.
- **No secrets in logs/spans/metrics.** Authorization headers, API keys,
  cookies, prompt text, SQL text, and result rows are redacted before they hit
  any sink.

---

## 1. Structured Logging

### Settings

| Setting | Default | Description |
|---|---|---|
| `LOG_FORMAT` | `console` | `json` for production, `console` for dev |
| `LOG_LEVEL` | `INFO` | Standard Python log levels |
| `LOG_INCLUDE_REQUEST_ID` | `true` | Attach a `request_id` to every record |
| `LOG_INCLUDE_USER_ID` | `false` | Attach `user_id` once auth has resolved |

### Behavior

- Every HTTP request gets a `request_id` — taken from the `X-Request-ID`
  header if the client supplies one (sanitised to alphanumeric/`-`/`_`,
  ≤ 128 chars), otherwise a fresh `uuid4().hex`.
- The same id is reflected back on the response as `X-Request-ID` so clients
  can correlate.
- Every log line emitted during the request — whether through `structlog` or
  the legacy `logging` module — automatically carries `request_id` (and
  `user_id` if enabled and authenticated).
- A single terse `http_request` access log line is emitted per request with
  `method`, `route` (template, never the raw path), `status_code`, and
  `duration_ms`.

### Redaction

Sensitive keys are stripped to `[REDACTED]` before serialization. The full
list (matched case-insensitively, kept in sync with `_SENSITIVE_KEYS` in
`src/observability/logging_config.py`):

```
authorization, cookie, cookies, set-cookie, api_key, apikey, api-key,
x-api-key, bearer, password, secret, token, access_token, refresh_token,
prompt, sql, query, response_text, result, result_rows, rows
```

Redaction runs both at the structlog processor layer and through the stdlib
adapter, so it covers `logger.info(...)`, `log.info(prompt=...)`, and bound
contextvars. It also recurses into nested dicts/lists/tuples up to 6 levels
deep.

**Limits — do not rely on redaction for the following:**

- **Free-form text.** Event messages, formatted strings, raw exception
  messages from the DB driver / LLM provider are **not** scrubbed. If a
  PostgreSQL error string contains the offending SQL, or an LLM provider
  echoes the prompt into an error body, that text will appear in logs.
  Scrub at the call site (or avoid logging raw `str(exc)` from external
  systems) when secrets may be embedded in the message.
- **Unknown keys.** Redaction is key-based only. Custom field names like
  `oauth_jwt` or `ssn` are not scrubbed unless added to `_SENSITIVE_KEYS`.

When you find a developer-facing surprise — `logger.info("...", sql=...)`
showing `[REDACTED]` — that is intentional. Use a different key name (e.g.
`sql_template`) only if the value is provably safe to log.

### Example log line (JSON)

```json
{
  "timestamp": "2026-04-23T12:00:00.123456Z",
  "level": "info",
  "logger": "src.api.endpoints.chat",
  "event": "http_request",
  "request_id": "8b1c5e09f1c34d8da9f9d3a7c6b1e6f0",
  "method": "POST",
  "route": "/api/chat/{session_id}",
  "status_code": 200,
  "duration_ms": 312.41
}
```

---

## 2. Metrics

### Settings

| Setting | Default | Description |
|---|---|---|
| `METRICS_ENABLED` | `false` | Register collectors and start recording |
| `METRICS_EXPOSE_ENDPOINT` | `false` | Mount `GET /metrics` |

The two flags are independent. You can collect in-process metrics without
exposing them, or skip both for zero overhead. When the endpoint is mounted
it is **exempt from rate limiting** so Prometheus scrapes never trip the
limiter.

> Security note: `/metrics` is unauthenticated, exempt from rate limiting,
> and intended for an internal Docker network only. **In production, protect
> it at the reverse proxy / firewall layer** (e.g. allowlist your Prometheus
> scraper IP, or terminate behind an internal-only listener). It exposes
> route templates, model names, provider/cost rates, latency, and error
> rates — most teams do not want this public. The endpoint is gated by
> `METRICS_EXPOSE_ENDPOINT`; keep it `false` until the network boundary is
> in place.
>
> Example nginx allowlist (production):
>
> ```nginx
> location /metrics {
>     allow 10.0.0.0/8;        # internal network
>     allow 192.168.0.0/16;
>     deny all;
>     proxy_pass http://backend:8000;
> }
> ```

### Collectors

All collectors are prefixed with `dbguru_`:

| Metric | Type | Labels |
|---|---|---|
| `dbguru_http_requests_total` | counter | method, route, status |
| `dbguru_http_request_duration_seconds` | histogram | method, route |
| `dbguru_llm_calls_total` | counter | provider, model, agent_type, success |
| `dbguru_llm_latency_seconds` | histogram | provider, model, agent_type |
| `dbguru_llm_tokens_total` | counter | provider, model, direction |
| `dbguru_llm_cost_usd_total` | counter | provider, model |
| `dbguru_sql_query_duration_seconds` | histogram | dialect, success |
| `dbguru_connection_pool_checkouts_total` | counter | dialect |
| `dbguru_connection_pool_size` | gauge | dialect |
| `dbguru_connection_pool_max_size` | gauge | dialect |
| `dbguru_cache_hits_total` | counter | cache |
| `dbguru_cache_misses_total` | counter | cache |

LLM token, cost, and success values are **read straight from
`LLMUsageTracker`** so we never recompute or re-tokenise solely for metrics.
Pool size and max-size gauges are populated at scrape time via
`ConnectionPoolManager.get_pool_metrics_snapshot()` (under the manager's
lock, so the gauge values cannot be torn during pool churn).

### Bounded labels

The middleware records HTTP metrics under the **matched FastAPI route
template**, never `request.url.path`. Unmatched paths are bucketed into
`route="unmatched"`. An attacker cannot blow up cardinality by hitting random
URLs.

---

## 3. Tracing (OpenTelemetry)

### Settings

| Setting | Default | Description |
|---|---|---|
| `OTEL_ENABLED` | `false` | Initialise the SDK + auto-instrumentation |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://jaeger:4318` | OTLP HTTP endpoint |
| `OTEL_SERVICE_NAME` | `database-guru` | `service.name` resource attribute |
| `OTEL_TRACES_SAMPLER_RATIO` | `0.1` | `ParentBased(TraceIdRatioBased)` |

### Auto-instrumentation

When enabled, the following are wired up at startup:

- `FastAPIInstrumentor` — every HTTP request gets a server span
- `SQLAlchemyInstrumentor` — every query becomes a span
- `HTTPXClientInstrumentor` — outbound HTTP calls (LLM providers)
- `RedisInstrumentor` — Redis cache calls

Each instrumentation is wrapped in its own `try/except` — a missing optional
dependency disables that one but does not affect the rest.

### Manual spans

- **`llm.call`** — opened by `TrackedLLMClient.generate()` and `chat()`.
  Attributes: `llm.provider`, `llm.model`, `llm.agent_type`,
  `llm.prompt_tokens`, `llm.completion_tokens`, `llm.cost_usd`,
  `llm.success`, `llm.duration_ms`.
- **`agent.self_correcting`** — opened around
  `SelfCorrectingAgent.generate_and_execute_with_retry`. Attributes:
  `agent.type`, `agent.attempts`, `agent.self_corrected`, `db.dialect`,
  `execution.success`.

Token/cost/success values reuse what `LLMUsageTracker` already computes.

### Failure isolation

If `init_tracing` cannot import `opentelemetry.sdk`, cannot construct an
exporter, or the OTLP endpoint is unreachable, it logs a warning and disables
itself. Span helpers always return a no-op span so call sites are safe.

---

## 4. Docker observability profile

The compose file ships an `observability` profile with three services:

```bash
# Default stack (no observability):
docker compose up -d

# Recommended: add the monitoring stack AND auto-enable backend flags so
# Prometheus has something to scrape and Jaeger receives spans:
docker compose -f docker-compose.yml -f docker-compose.observability.yml \
    --profile observability up -d

# Bare profile (monitoring containers only — backend flags stay off):
docker compose --profile observability up -d
```

> ⚠ Using `--profile observability` on its own brings up Jaeger, Prometheus,
> and Grafana but does **not** flip the backend's observability flags.
> Prometheus will scrape `backend:8000/metrics` immediately, but until
> `METRICS_ENABLED=true`, `METRICS_EXPOSE_ENDPOINT=true`, and `OTEL_ENABLED=true`
> are set on the backend, `/metrics` returns 404 and no spans are exported.
>
> The `docker-compose.observability.yml` override sets those flags (plus the
> Jaeger/Grafana deep-link URLs and `ADMIN_UI_ENABLED`) automatically. If you
> prefer to keep observability config in `.env.docker`, uncomment the Phase 24
> block in that file and use the bare profile command — values you set there
> override the compose override.

| Service | Image | Port |
|---|---|---|
| Jaeger | `jaegertracing/all-in-one:1.56` | UI 16686, OTLP 4318 |
| Prometheus | `prom/prometheus:v2.51.2` | UI 9090 |
| Grafana | `grafana/grafana:10.4.5` | UI 3001 |

> ⚠ **Grafana credentials.** The compose file falls back to `admin/admin`
> when `GRAFANA_USER`/`GRAFANA_PASSWORD` are not set. This is acceptable for
> a laptop bound to `127.0.0.1` only. **For any non-local deployment** —
> shared dev hosts, remote tunnels, or copied prod compose files — set
> `GRAFANA_PASSWORD` to a generated secret before bringing the stack up.

Grafana is provisioned with:

- A Prometheus datasource pointing to the in-network Prometheus
- A "Database Guru — Overview" dashboard with 9 panels (request volume,
  latency p50/p95/p99, error rate, LLM calls, LLM latency, LLM cost/h, SQL
  latency, cache hit ratio, pool size)

Prometheus scrapes `backend:8000/metrics` every 15 seconds and ships three
starter alert rules:

- `DbGuruHighErrorRate` — error rate > 5% for 5 min
- `DbGuruLLMLatencyP99High` — LLM p99 > 30s for 10 min
- `DbGuruConnectionPoolSaturation` — pool > 90% for 10 min

To enable observability inside the backend container, set:

```env
LOG_FORMAT=json
METRICS_ENABLED=true
METRICS_EXPOSE_ENDPOINT=true
OTEL_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4318
OTEL_TRACES_SAMPLER_RATIO=0.1
```

Sample values are in `.env.docker` (commented out by default).

---

## 5. Operational checklist

Before turning observability on in production:

- [ ] Set `LOG_FORMAT=json` and review one request's worth of logs.
- [ ] Enable `METRICS_ENABLED` first; only flip `METRICS_EXPOSE_ENDPOINT`
      after confirming the network boundary.
- [ ] Pick an `OTEL_TRACES_SAMPLER_RATIO` that matches traffic (1.0 is fine
      for low-traffic workloads; reduce it as request volume grows).
- [ ] Confirm `/metrics` is reachable only from your scraper, not the
      internet.
- [ ] Verify alert thresholds match your SLOs and silence them during
      planned LLM provider outages.

---

## 6. Out of scope for Phase 24

These are intentionally deferred:

- Loki / ELK / any log aggregator (we ship JSON to stdout only)
- Long-term metrics retention tuning
- PagerDuty / Slack / email notification routing

---

## 7. Admin & Observability UI (Phase 24.7)

The backend stack is hardened, but operators still need a way to *use* it
without leaving the app. Phase 24.7 ships that surface, fully gated by a single
kill-switch.

### Kill-switch

```
ADMIN_UI_ENABLED=true   # opt-in (default: false); set true to mount the admin surface
```

The flag defaults to `false` so a fresh deployment never accidentally exposes
user CRUD or audit logs — matching the opt-in posture of `METRICS_ENABLED`,
`OTEL_ENABLED`, and `METRICS_EXPOSE_ENDPOINT`. Operators must set it
explicitly in their `.env` to use the Admin tab.

When `ADMIN_UI_ENABLED=false` (the default):

- The `audit` and `admin_users` routers are **not mounted** (they don't appear
  in `/api/docs` either)
- `/api/settings/` returns `admin_ui_enabled: false`
- The frontend hides the **Admin** tab and the Settings → **Observability**
  section entirely

### Last-request badge (header)

Every API response carries `X-Request-ID` (set by `RequestContextMiddleware`,
exposed via CORS `expose_headers`). The frontend axios response interceptor
captures `x-request-id` + `traceparent` into a Zustand `useLastRequestStore`,
and the header `LastRequestBadge` shows a short id and copies the full id +
traceparent to the clipboard on click. Drop the id into your log aggregator or
Jaeger to jump straight to the trace for the last action you took.

### Admin tab (admin-only)

Sub-tabs, all wrapped in a `RequireAdmin` guard:

- **Users** — list with search/filter, inline admin role toggle, enable/disable,
  one-time temporary password reset. Self-lockout protection is enforced
  server-side: an admin cannot demote or deactivate themselves through the API.
- **Audit Log** — paginated viewer over `GET /api/audit/logs` with server-side
  filters (action, resource_type, user_id, date range), JSON detail drawer per
  row, dropdowns populated from `GET /api/audit/facets`.
- **Health** — replaces the old `?demo=true` mock. Live `/health` cards
  (API/Database/Cache/LLM), observability gate matrix
  (Prometheus/OpenTelemetry/Jaeger/Grafana), last-request widget with
  traceparent, semantic + LLM cache hit rates, recent queries, recent audit
  feed.

### Observability deep-links (Settings → Observability)

Optional environment variables, surfaced via `/api/settings/`:

| Setting | Default | Purpose |
|---|---|---|
| `JAEGER_UI_URL` | unset | Browser URL for Jaeger UI (e.g. `http://localhost:16686`) |
| `GRAFANA_URL` | unset | Browser URL for Grafana (e.g. `http://localhost:3001`) |
| `METRICS_PUBLIC_URL` | unset | Browser-reachable URL for `/metrics` (falls back to relative `/metrics` when `METRICS_EXPOSE_ENDPOINT=true`) |

The Settings panel renders one card per link. Each card is **disabled with a
tooltip** when the corresponding feature flag is off — e.g. clicking the
Prometheus link with `METRICS_ENABLED=false` shows "Set `METRICS_ENABLED=true`
in your `.env` to collect metrics." This keeps the surface honest even in
partially-configured deployments.

### Endpoints exposed to the UI

```
# Audit (admin)
GET  /api/audit/logs         # filters + pagination
GET  /api/audit/logs/me      # current user's own actions
GET  /api/audit/facets       # distinct actions / resource_types

# Admin users
GET    /api/admin/users
POST   /api/admin/users
PATCH  /api/admin/users/{id}
POST   /api/admin/users/{id}/reset-password
DELETE /api/admin/users/{id}
```

All admin mutations call `log_action()` so they show up in the Audit Log
viewer immediately.

### Tests

| File | LOC | Coverage |
|---|---|---|
| `tests/test_admin_users_endpoints.py` | 320 | full CRUD, self-lockout, password complexity, audit side-effects |
| `tests/test_audit_endpoints.py` | 237 | filters, pagination, facets, admin-vs-user 403 |
| `tests/test_admin_ui_toggle.py` | 35 | `ADMIN_UI_ENABLED=false` removes routers from the OpenAPI schema |
| `tests/test_settings_observability.py` | 163 | `/api/settings/` surfaces `metrics_*`, `otel_*`, deep-link URLs |
- A user-facing observability UI in the main app
