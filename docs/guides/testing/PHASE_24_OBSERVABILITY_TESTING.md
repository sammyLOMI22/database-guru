# Phase 24: Observability & Monitoring — Manual Testing Guide

**Date**: April 2026
**Scope**: Structured JSON logging with request_id propagation, Prometheus
metrics with `/metrics` gating, OpenTelemetry tracing (LLM + self-correcting
spans), and the Docker observability profile (Jaeger / Prometheus / Grafana).

---

## Prerequisites

```bash
source venv/bin/activate
pip install -r requirements.txt   # picks up the new opentelemetry-* pins
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Optional Docker observability stack:

```bash
docker compose --profile observability up -d
# Jaeger:     http://localhost:16686
# Prometheus: http://localhost:9090
# Grafana:    http://localhost:3001  (admin / admin on first launch)
```

---

## 1. Automated test suite

Run only the new Phase 24 tests:

```bash
python -m pytest tests/observability -q
```

| Check | Expected |
|---|---|
| Total | `17 passed` |
| Logging tests | 7 |
| Metrics tests | 6 |
| Tracing tests | 4 |

Run with the broader suite:

```bash
./run_tests.sh
```

---

## 2. Structured logging (24.1)

### 2.1 JSON format

```bash
LOG_FORMAT=json LOG_LEVEL=INFO \
  python -m uvicorn src.main:app --port 8000
```

Hit any endpoint:

```bash
curl -s http://localhost:8000/health -o /dev/null
```

| Check | Expected |
|---|---|
| Each log line is parseable as JSON | yes |
| Each line has `timestamp`, `level`, `event`, `request_id` | yes |
| The `http_request` line includes `method`, `route`, `status_code`, `duration_ms` | yes |
| `route` is a template like `/health`, never `/health?foo=bar` | yes |

### 2.2 Console format

```bash
LOG_FORMAT=console python -m uvicorn src.main:app --port 8000
```

| Check | Expected |
|---|---|
| Lines are human-readable, not JSON | yes |
| First column is timestamp | yes |
| Color codes appear in a real terminal (TTY) | yes (optional) |

### 2.3 Request ID propagation

```bash
curl -i -H 'X-Request-ID: my-trace-1234' http://localhost:8000/health
```

| Check | Expected |
|---|---|
| Response header `X-Request-ID` echoes `my-trace-1234` | yes |
| The matching log line carries `request_id=my-trace-1234` | yes |
| Without the header, the response still carries a fresh hex id | yes |
| A header containing `<script>` or 1KB of garbage is rejected | yes (a fresh uuid is used) |

### 2.4 Redaction

```bash
curl -H 'Authorization: Bearer secret' http://localhost:8000/health
```

| Check | Expected |
|---|---|
| No log line contains `Bearer secret` | yes |
| No log line contains the literal API key for any provider | yes |
| Prompt text and SQL never appear in logs (even at DEBUG level for the http_request access line) | yes |

---

## 3. Metrics (24.2)

### 3.1 Disabled by default

```bash
curl -i http://localhost:8000/metrics
```

| Check | Expected |
|---|---|
| HTTP status | 404 |

### 3.2 Collectors only

```bash
METRICS_ENABLED=true METRICS_EXPOSE_ENDPOINT=false \
  python -m uvicorn src.main:app --port 8000

curl -s -o /dev/null http://localhost:8000/health
curl -i http://localhost:8000/metrics
```

| Check | Expected |
|---|---|
| `/metrics` | 404 |
| Application logs show no errors from metric helpers | yes |

### 3.3 Metrics exposed

```bash
METRICS_ENABLED=true METRICS_EXPOSE_ENDPOINT=true \
  python -m uvicorn src.main:app --port 8000

curl -s http://localhost:8000/health > /dev/null
curl -s http://localhost:8000/metrics | grep dbguru_
```

| Check | Expected |
|---|---|
| `/metrics` returns 200 | yes |
| `dbguru_http_requests_total{...status="200"...}` is present | yes |
| Body shows `dbguru_*` HELP/TYPE blocks | yes |
| Hitting `/metrics` repeatedly does not double-register collectors | yes |

### 3.4 Bounded label cardinality

```bash
for i in $(seq 1 5); do
  curl -s -o /dev/null http://localhost:8000/no-such/path-$i;
done
curl -s http://localhost:8000/metrics | grep no-such
```

| Check | Expected |
|---|---|
| **No** metric line contains `no-such` or `path-N` | yes |
| Unmatched paths are bucketed under `route="unmatched"` | yes |
| Pool/cache/LLM labels stay bounded after a real query workload | yes |

### 3.5 Rate-limit exemption

```bash
# Simulate a Prometheus scrape loop
for i in $(seq 1 300); do curl -s -o /dev/null http://localhost:8000/metrics; done
```

| Check | Expected |
|---|---|
| All 300 calls return 200 (no 429) | yes |
| `/metrics` is in the rate-limit middleware's exempt list | yes |

---

## 4. Tracing (24.3)

### 4.1 Disabled by default

```bash
python -m uvicorn src.main:app --port 8000
# Generate traffic
curl -s -o /dev/null http://localhost:8000/health
```

| Check | Expected |
|---|---|
| Startup logs do not reference OTel | yes |
| No outbound traffic to port 4318 | yes |

### 4.2 Enabled with unreachable exporter

```bash
OTEL_ENABLED=true OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:1 \
  python -m uvicorn src.main:app --port 8000
```

| Check | Expected |
|---|---|
| Backend starts cleanly (no crash, no traceback) | yes |
| A warning logs that the exporter is unreachable, not an error | yes |
| `curl /health` still works | yes |

### 4.3 Enabled with Jaeger

```bash
docker compose --profile observability up -d
OTEL_ENABLED=true \
  OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318 \
  OTEL_TRACES_SAMPLER_RATIO=1.0 \
  python -m uvicorn src.main:app --port 8000

# Issue an LLM-touching request, e.g. a chat:
curl -X POST http://localhost:8000/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"how many users are there?"}'
```

Open http://localhost:16686 → service `database-guru`:

| Check | Expected |
|---|---|
| HTTP server span for the FastAPI route | yes |
| `llm.call` span as a child, with attributes: `llm.provider`, `llm.model`, `llm.agent_type`, `llm.prompt_tokens`, `llm.completion_tokens`, `llm.cost_usd`, `llm.success` | yes |
| `agent.self_correcting` span with `db.dialect`, `agent.attempts`, `agent.self_corrected`, `execution.success` | yes |
| SQLAlchemy spans nested under the agent span | yes |
| No span attribute contains prompt/SQL/result text | yes |

### 4.4 Sampler

```bash
OTEL_TRACES_SAMPLER_RATIO=0.0 ...   # disable sampling
```

| Check | Expected |
|---|---|
| Traffic still serves normally | yes |
| Jaeger receives zero spans for that run | yes |

---

## 5. Docker observability profile (24.4)

### 5.1 Profile boots

```bash
docker compose --profile observability up -d
docker compose ps | grep -E 'jaeger|prometheus|grafana'
```

| Check | Expected |
|---|---|
| All three containers report `Up` | yes |
| Jaeger UI reachable at :16686 | yes |
| Prometheus UI reachable at :9090 | yes |
| Grafana UI reachable at :3001 | yes |

### 5.2 Prometheus scrape

In Prometheus → **Status → Targets**:

| Check | Expected |
|---|---|
| `backend:8000/metrics` target | `UP` |
| Last scrape duration | < 1s |

Run a query like `dbguru_http_requests_total`:

| Check | Expected |
|---|---|
| Time series appears | yes |

### 5.3 Grafana provisioning

In Grafana → **Connections → Data sources**:

| Check | Expected |
|---|---|
| `Prometheus` datasource auto-provisioned | yes |
| Health: `Successfully queried` | yes |

Open dashboards:

| Check | Expected |
|---|---|
| "Database Guru — Overview" dashboard appears in the list | yes |
| All 9 panels render without errors (some may be empty until traffic flows) | yes |

### 5.4 Alerts

In Prometheus → **Alerts**:

| Check | Expected |
|---|---|
| Three rules listed: `DbGuruHighErrorRate`, `DbGuruLLMLatencyP99High`, `DbGuruConnectionPoolSaturation` | yes |
| All `OK` (green) under healthy conditions | yes |

---

## 6. Acceptance criteria recap

- [ ] Every HTTP request has a `request_id` in logs and on the response
      header.
- [ ] Enabling logs does not change endpoint behavior or break legacy
      `logging.getLogger(...)` calls.
- [ ] When `METRICS_ENABLED=true` and `METRICS_EXPOSE_ENDPOINT=true`,
      `/metrics` is scrapeable and exempt from rate limiting.
- [ ] Metric labels are bounded — no raw paths, user IDs, connection IDs,
      or query text.
- [ ] When `OTEL_ENABLED=true`, LLM calls and self-correcting agent runs
      emit spans with the agreed attributes.
- [ ] If Prometheus, Grafana, Jaeger, or the OTLP endpoint are unavailable,
      the backend still starts and serves requests.
- [ ] When all observability flags are `false`, runtime behavior matches
      pre-Phase-24 behavior.
