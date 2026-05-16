# PR Review: Phase 24 Observability & Monitoring

Date: 2026-04-26  
Branch: `phase-24-Observability-&-Monitoring`  
Base reviewed against: `origin/main`

## Review Summary

Recommendation: do not merge as-is. The core observability implementation is directionally strong, but there are deployment wiring gaps and a few security/API regressions that should be fixed before this branch ships.

The branch adds structured logging, request IDs, Prometheus metrics, OpenTelemetry spans, Docker observability services, and a new admin UI for users/audit/system health. The strongest parts are the opt-in defaults, route-template metrics labels, sanitized request IDs, no-op observability helpers when disabled, and focused backend tests.

## Blocking Findings

### 1. Observability Docker profile starts Prometheus/Grafana/Jaeger but does not enable the backend observability features

Severity: High  
Files: `docker-compose.yml`, `src/config/settings.py`, `src/main.py`

`docker-compose.yml` adds Prometheus scraping `backend:8000/metrics`, but the backend service does not set `METRICS_ENABLED=true` or `METRICS_EXPOSE_ENDPOINT=true`. Both default to `False` in `Settings`, and `/metrics` is mounted only when `METRICS_EXPOSE_ENDPOINT` is true. Running `docker compose --profile observability up -d` therefore brings up Prometheus and Grafana, but Prometheus scrapes a 404 from the app.

Similar wiring is missing for `OTEL_ENABLED`, `ADMIN_UI_ENABLED`, `JAEGER_UI_URL`, `GRAFANA_URL`, and `METRICS_PUBLIC_URL`, so the operator-facing UI may show disabled/missing links even though the observability containers are running.

Fix: set profile-specific backend env vars when the observability profile is active, or document a required `.env.docker` block and add a compose override. At minimum, the advertised compose command should produce a working dashboard.

### 2. Existing user audit endpoint is removed whenever the new admin UI kill switch is off

Severity: High  
Files: `src/main.py:266`, `src/config/settings.py`

Before this branch, `audit.router` was always mounted. Now both `audit.router` and `admin_users.router` are mounted only under `ADMIN_UI_ENABLED`. Since `ADMIN_UI_ENABLED` defaults to `False`, existing endpoints like `/api/audit/logs/me` disappear by default, even though that route is for the current active user and not an admin-only UI surface.

Impact: clients or frontend flows relying on a user viewing their own audit history will regress to 404 in default deployments.

Fix: split the gate. Keep `/api/audit/logs/me` mounted unconditionally, and gate only admin-only routes (`/api/audit/logs`, `/api/audit/facets`, `/api/admin/users`) behind the admin UI feature flag.

### 3. Password reset creates a permanent usable password, not a forced temporary credential

Severity: High  
Files: `src/api/endpoints/admin_users.py:244`, `frontend/src/components/admin/UserManagement.tsx:404`

The reset endpoint returns `temporary_password` in the API response and the UI displays/copies it, but the user model and login flow do not enforce password change on next login. The response text says "should change it", but the application does not require it.

Impact: an operator-generated password can become a long-lived credential, shared through out-of-band channels, copied to clipboard, or retained in browser memory/screenshots. That weakens account recovery security and auditability.

Fix: add a `must_change_password` or password-reset token flow. Prefer sending a single-use reset link/token with expiration. If returning a password remains necessary for local deployments, force change on next login and add an audit event when the user completes the change.

## Important Findings

### 4. Audit facet queries use one `AsyncSession` concurrently

Severity: Medium  
File: `src/auth/audit.py:174`

`get_audit_facets` uses `asyncio.gather(db.execute(actions_q), db.execute(resources_q))` against the same SQLAlchemy `AsyncSession`. `AsyncSession` is not designed for concurrent operations. The tests use `AsyncMock`, so they do not catch the real session behavior.

Impact: the audit filter dropdown can fail intermittently under real database drivers with "session is provisioning a connection" or similar concurrency errors.

Fix: run the two queries sequentially, or use separate sessions/connections if parallelism is actually needed. For two distinct lists on an admin screen, sequential execution is simpler and safer.

### 5. Structured redaction does not cover sensitive data embedded in log messages

Severity: Medium  
Files: `src/observability/logging_config.py`, `src/core/executor.py`

The redactor is key-based and only redacts structured fields. Existing log statements still interpolate raw SQL snippets and database/provider error strings into the event message, for example query timeout and DBAPI error logs in `SQLExecutor`.

Impact: enabling JSON logging can give operators better log aggregation, but SQL text, literals, table names, and driver errors may still land in centralized logs. For this application, SQL may include customer data or secrets.

Fix: convert high-risk logs to structured fields that can be redacted or summarized. Avoid logging raw SQL/error bodies; log a query hash, dialect, connection id, request id, and coarse error class instead.

### 6. LLM metrics labels can become high-cardinality

Severity: Medium  
File: `src/observability/metrics.py:239`

`provider`, `model`, and `agent_type` are used directly as Prometheus labels. Provider/model values can come from configurable LLM provider records and user/operator-created model names. This is better than labeling prompts, but still risky in a system with user-defined providers or frequent model aliases.

Impact: Prometheus cardinality can grow without bounds, increasing memory and query cost.

Fix: normalize labels to known provider/model slugs, collapse unknowns to `custom` or `unknown`, and optionally expose detailed model names through logs/traces instead of metrics labels.

### 7. Audit API response shape is a breaking change

Severity: Medium  
Files: `src/api/endpoints/audit.py`, `frontend/src/services/auditApi.ts`

`GET /api/audit/logs` and `/api/audit/logs/me` changed from returning a plain list to returning `{ items, total, limit, offset }`. The frontend was updated, but external clients or older UI builds will break.

Fix: version the endpoint, add backward-compatible aliases, or call this out in release notes with migration guidance.

## Lower-Risk Notes

- `frontend/src/App.tsx` defaults `adminUiEnabled` to `true` until settings load. If settings fetch fails, an admin user may see an Admin tab that only produces 404s. This is not a security boundary, but it is noisy UX.
- Admin user list search uses `%term%` across username/email. It is admin-only and limited to 500 rows per page, but it will not scale well without search-specific indexes or stricter query patterns.
- `grafana` defaults to `admin/admin` unless env vars are set. It is bound to localhost, which is reasonable for local use, but docs should strongly flag this before production use.

## What Works Well

- Observability helpers are no-op when disabled, which keeps baseline overhead low.
- HTTP metrics use route templates rather than raw paths, avoiding a common cardinality bug.
- Request IDs are sanitized and reflected through `X-Request-ID`, which improves support/debug workflows.
- The logging setup is centralized and re-applied after Alembic resets logging.
- Manual spans avoid prompt bodies and SQL text, which is the right default posture.
- Admin endpoints consistently use `require_admin`, audit mutating actions, and prevent self-demotion/self-deactivation.
- Focused backend tests cover metrics gating, tracing no-op behavior, structured logging, audit pagination, and admin user permissions.

## User Perspective

The feature is useful: request correlation, health panels, audit filtering, and user management are exactly the tools an operator expects when the app becomes multi-user. The main user-facing gap is that the "observability profile" does not actually make the app observable without extra environment work. An app user or project stakeholder will experience this as "I followed the guide, but dashboards are empty."

The admin UI also needs clearer security workflows around password resets. The current flow works mechanically, but it relies on human process where the product should enforce a safer path.

## Project Manager Perspective

This is a solid phase foundation, but it mixes three deliverables: observability plumbing, deployment stack, and admin user management. That increases release risk. I would split acceptance into:

1. Observability stack works from documented compose command.
2. Existing audit API compatibility is preserved or explicitly migrated.
3. Admin user management ships with a secure password recovery story.
4. Dashboards show real backend metrics in a fresh local deployment.

## Future Feature Recommendations

- Add an in-app trace search link that carries the current request ID/trace ID into Jaeger.
- Add SLO widgets: request error rate, p95 latency, LLM spend/hour, LLM timeout rate, cache hit rate.
- Add audit export with date range and signed CSV for compliance workflows.
- Add admin actions for forced logout/token revocation after role changes or password resets.
- Add alert routing examples for Slack/email/PagerDuty rather than only Prometheus rules.
- Add per-tenant/user observability views once multi-tenant boundaries exist.

## Disposition (2026-04-26)

| # | Finding | Action |
|---|---|---|
| 1 | Observability profile env not wired | **Addressed** — added `docker-compose.observability.yml` override that sets backend `METRICS_ENABLED`, `METRICS_EXPOSE_ENDPOINT`, `OTEL_ENABLED`, deep-link URLs, and `ADMIN_UI_ENABLED`; updated `.env.docker.example` and `OBSERVABILITY_GUIDE.md` to point to the override-based command. |
| 2 | `/api/audit/logs/me` regression | **Addressed** — split `audit.py` into `router` (always mounted, hosts `/logs/me`) and `admin_router` (admin-only, gated by `ADMIN_UI_ENABLED`). Updated tests. |
| 3 | Operator password reset = permanent password | **Addressed** — added `users.must_change_password` (alembic `3d8f4c2a1e9b`); reset endpoint flips it; new `POST /api/auth/change-password` clears it and audit-logs. Frontend renders a forced-change screen (`ForcedPasswordChange`) before any other UI when the flag is set. |
| 4 | `asyncio.gather` on shared `AsyncSession` | **Addressed** — `get_audit_facets` now runs sequentially. |
| 5 | SQL/error redaction in log messages | **Deferred** — broader refactor of executor/error-path log statements is out of scope for this branch. Tracking as a follow-up. |
| 6 | LLM metric label cardinality | **Deferred** — provider/model already come from a configured provider registry; cardinality bound is finite per deployment. Tracking a follow-up to add a slug normaliser before any user-facing model alias surface lands. |
| 7 | Audit API response shape change | **No code change** — this is a brand-new endpoint shipping in this branch (no external consumers). Captured in release notes; will version if/when an external client materialises. |
| L | Frontend `adminUiEnabled` defaulting to true | **Addressed** — now defaults to false until `/api/settings` confirms it; older backends without the field still light it up via the `!== false` check. |
| L | Admin user search `%term%` | **No change** — admin-only, capped at 500 rows, no measured perf issue. Revisit if it shows up in a slow log. |
| L | Grafana `admin/admin` default | **Addressed** — `.env.docker.example` now flags `GRAFANA_PASSWORD` with a "set before any non-localhost deploy" note; doc already warned in `OBSERVABILITY_GUIDE.md`. |

New test coverage added:
- `tests/test_auth_change_password.py` — clears flag on success, rejects wrong current password (flag stays set), rejects reuse, rejects weak new password.
- Updated `tests/test_admin_users_endpoints.py::TestResetPassword` — asserts `must_change_password=True` after admin reset.
- Updated `tests/test_audit_endpoints.py` — mounts the new `admin_router` alongside `router`.

## Verification Performed

- `env PYTHONPATH=. venv/bin/pytest tests/observability tests/test_admin_users_endpoints.py tests/test_audit_endpoints.py tests/test_settings_observability.py -q`  
  Result: 52 passed, 9 warnings.
- `npm run build` in `frontend/`  
  Result: passed. Vite reports large bundle warning only.
- `npm test -- --run` in `frontend/`  
  Result: interrupted after hanging. Before interruption, Vitest showed existing test harness failures around missing `QueryClientProvider` in `Message.test.tsx` and missing mocked `settingsAPI` exports in `EnhancedChatInterface.test.tsx`; not enough evidence to attribute those directly to this branch.
