# Password & Session Hardening Plan

**Status:** Proposed
**Owner:** Auth / Phase 24.7 follow-up
**Last updated:** 2026-04-26

## 1. Goals & Non-Goals

### Goals
Tighten the post-reset and password-change flow for a **single-tenant, locally-deployed** Database Guru install. Each item below should be:

- **Shippable in isolation** — no item depends on a later one.
- **Operator-toggleable** — every behavior must be enable/disable-able via `Settings`. Defaults preserve existing behavior; nothing turns on without explicit opt-in unless flagged below.
- **Local-friendly** — no third-party IdP, no SMTP server, no internet access required.

### Non-Goals
- TOTP / 2FA via third-party authenticator services.
- Email-based reset links (no SMTP assumed). Phase C uses an in-app token URL the operator hands off out-of-band.
- Argon2 migration (bcrypt is fine for this scale).
- SSO / OIDC / SAML.

---

## 2. Configuration Surface

All new behaviors are gated by additions to `src/config/settings.py`. Operators flip them in `.env` (local dev) or `.env.docker` (containers).

```python
# Phase A — Token invalidation on password change
AUTH_TOKEN_VERSIONING_ENABLED: bool = False        # add `pv` claim and reject stale tokens
AUTH_INVALIDATE_TOKENS_ON_DEACTIVATE: bool = False # bump pv when is_active flips to False
AUTH_INVALIDATE_TOKENS_ON_LOGOUT: bool = False     # bump pv on /api/auth/logout (kicks other devices)

# Phase B — Rate limiting
AUTH_RATE_LIMIT_CHANGE_PASSWORD: bool = False
AUTH_CHANGE_PASSWORD_PER_USER_PER_MINUTE: int = 5
AUTH_RATE_LIMIT_LOGIN_LOCKOUT_ENABLED: bool = False
AUTH_LOGIN_LOCKOUT_THRESHOLD: int = 5              # failures before temp lock
AUTH_LOGIN_LOCKOUT_WINDOW_SECONDS: int = 900       # 15 minutes

# Phase C — One-shot reset tokens (replaces temp-password return)
AUTH_PASSWORD_RESET_MODE: str = "temp_password"    # temp_password | reset_token | both
AUTH_PASSWORD_RESET_TOKEN_TTL_MINUTES: int = 15
AUTH_PASSWORD_RESET_BASE_URL: str = ""             # e.g. http://localhost:3000 — used to build the redemption link

# Phase D — Optional hardening
AUTH_PASSWORD_HISTORY_DEPTH: int = 0               # 0 = disabled. e.g. 5 = block last 5 hashes
AUTH_REQUIRE_ADMIN_QUORUM: bool = False            # block deactivating/demoting the last admin
```

**Surfacing in the UI.** `/api/settings` returns the relevant flags so the Admin tab can:
- Hide the "reveal temp password" view when `AUTH_PASSWORD_RESET_MODE=reset_token`.
- Show "session invalidation: on/off" under Health → Security.
- Render an inline note when an operator picks a setting that affects logged-in users (e.g. flipping `AUTH_INVALIDATE_TOKENS_ON_LOGOUT` warns: "this will sign users out on every device when they log out").

---

## 3. Phases

Each phase is a separate PR. Tests, docs, and migrations ship with the phase that introduces them.

### Phase A — Token Invalidation on Password Change

**Why:** today, an attacker holding a stolen JWT keeps access for up to 24h after the user rotates their password. "Force a password change" doesn't actually evict them.

**Changes:**
- **Migration:** add `users.password_version INTEGER NOT NULL DEFAULT 1`.
- `AuthService.create_access_token` includes `pv: user.password_version` in the JWT claims **only when** `AUTH_TOKEN_VERSIONING_ENABLED=True`.
- `get_current_user` rejects the token with 401 ("Session invalidated, please sign in again") when `payload["pv"] != user.password_version`. Tokens issued before the feature was enabled don't carry `pv`; treat missing-claim as "valid" so flipping the flag doesn't kick everyone out instantly. Operator who *wants* a kill-switch logout can call a new `POST /api/admin/users/{id}/invalidate-sessions` endpoint instead.
- `change_password` and `admin_users.reset_user_password` bump `password_version` when versioning is enabled.
- Conditional bumps:
  - `update_user` bumps when `AUTH_INVALIDATE_TOKENS_ON_DEACTIVATE=True` and `is_active` flips False.
  - `logout` bumps when `AUTH_INVALIDATE_TOKENS_ON_LOGOUT=True`. (Off by default — most operators don't want a logout to kick the user's other devices.)

**Tests:**
- Token issued before bump rejected (versioning on).
- Token issued after bump accepted.
- Reset bumps `password_version`; change-password bumps it.
- Versioning **off**: no `pv` in token, mismatch is impossible, behavior identical to today.

**Files:** `src/auth/models.py`, `src/auth/service.py`, `src/auth/dependencies.py`, `src/api/endpoints/auth.py`, `src/api/endpoints/admin_users.py`, new alembic migration, `tests/test_auth_token_versioning.py`.

**Effort:** ~1 day.
**Default:** `AUTH_TOKEN_VERSIONING_ENABLED=False` to preserve backwards compatibility on upgrade.

---

### Phase B — Rate-Limit Change-Password and Login Lockout

**Why:** `current_password` is still a guessable secret. A compromised token plus brute force on the change-password endpoint shouldn't be free. Login itself is rate-limited globally per-IP today, but a per-user lockout adds defence against slow distributed attacks.

**Changes:**
- Add `change_password_rate_limiter` keyed by `user.id` (not IP — the user is authenticated). Default 5/min when enabled.
- Add `LoginAttemptTracker` (in-process or Redis-backed depending on `REDIS_URL`):
  - On `login_failed`, increment counter for the username.
  - When counter >= `AUTH_LOGIN_LOCKOUT_THRESHOLD` within `AUTH_LOGIN_LOCKOUT_WINDOW_SECONDS`, return 429 ("Account temporarily locked, try again in N minutes") on subsequent attempts until the window elapses or a successful login resets the counter.
  - Counter cleared on successful login.
  - Audit-log `account_locked` and `account_unlocked`.

**Tests:**
- 6th change-password attempt within 60s returns 429 when limiter enabled.
- Limiter disabled → unlimited attempts (matches today's behavior).
- 5 failed logins → 6th returns 429; window expiry unlocks; successful login resets the counter.

**Files:** `src/middleware/rate_limit.py`, `src/auth/service.py`, `src/api/endpoints/auth.py`, `tests/test_auth_rate_limit.py`.

**Effort:** ~2 hours for change-password limiter; +half day for login lockout.
**Default:** both flags `False`.

---

### Phase C — One-Shot Password Reset Tokens

**Why:** the operator-generated temp password lives in clipboard, screenshots, and operator memory. A single-use, short-TTL reset token avoids exposing a real password and gives the user a normal "set your own password" first-run experience.

**Changes:**
- **Migration:** new table `password_reset_tokens(id, user_id, token_hash, expires_at, used_at, created_by_admin_id, created_at)`. `token_hash` is bcrypt-hashed; the plaintext token never lands in the DB.
- `admin_users.reset_user_password` behavior keyed off `AUTH_PASSWORD_RESET_MODE`:
  - `temp_password` (default, current behavior).
  - `reset_token` — generates a 32-byte URL-safe token, stores its hash, returns `{redemption_url}` built from `AUTH_PASSWORD_RESET_BASE_URL`. `temporary_password` field absent.
  - `both` — returns both for transition periods.
- New endpoint `POST /api/auth/redeem-reset { token, new_password }`:
  - Looks up the token by hash, rejects if expired or `used_at` already set.
  - Validates new password complexity.
  - Sets the password, marks `used_at`, bumps `password_version` (if Phase A enabled), audit-logs `password_reset_redeemed`.
  - Returns a fresh access token so the user lands logged in.
- Frontend:
  - New route `/reset?token=…` → `PasswordReset` component (password form).
  - Admin "reset password" UI conditionally shows password OR redemption URL OR both, driven by the settings flag.
- Background cleanup: drop expired/used tokens older than 7 days on the existing `cleanup_expired_files`-style scheduler (or a sibling task).

**Tests:**
- Token redemption succeeds → password updated, `used_at` set, password_version bumped.
- Reused token rejected with 410 Gone.
- Expired token rejected with 410 Gone.
- Wrong token rejected with 401 (without leaking which user it belonged to).
- `AUTH_PASSWORD_RESET_MODE=temp_password` (default) keeps existing API shape unchanged.

**Files:** new alembic migration, `src/auth/models.py`, `src/auth/service.py`, `src/api/endpoints/admin_users.py`, `src/api/endpoints/auth.py`, `frontend/src/components/admin/UserManagement.tsx`, new `frontend/src/components/PasswordReset.tsx`, frontend route table, `tests/test_auth_reset_tokens.py`.

**Effort:** ~2 days.
**Default:** `AUTH_PASSWORD_RESET_MODE=temp_password` — operators opt in to the safer flow when their UX is ready.

---

### Phase D — Optional Hardening

Ship only if motivated by a specific need.

#### D1. Password history
- Migration: `password_history(user_id, hashed_password, replaced_at)`.
- On `change_password` / `redeem-reset`: hash check the new password against the last `AUTH_PASSWORD_HISTORY_DEPTH` entries; reject reuse.
- Default `0` = disabled (no history kept).
- Effort: ~3 hours.

#### D2. JWT denylist on logout
- Adds JTI claim + Redis denylist. Heavy; only do if multi-device hygiene matters and Phase A's `AUTH_INVALIDATE_TOKENS_ON_LOGOUT` (which kicks all devices) is too coarse.
- Effort: ~1 day, requires Redis profile.

#### D3. Admin quorum safeguard
- Block deactivating or demoting the last active admin (`AUTH_REQUIRE_ADMIN_QUORUM=True`). Already partially in place for self-edit.
- Returns 400 with "at least one admin must remain active" instead of letting the operation succeed.
- Effort: ~2 hours.

#### D4. Auto-logout on deactivation
- Already covered by `AUTH_INVALIDATE_TOKENS_ON_DEACTIVATE` in Phase A. Listed here for completeness — operators turn it on when they want deactivation to be immediate rather than waiting for token expiry.

---

## 4. Suggested Rollout Order

| Order | Phase | Effort | User-visible? |
|---|---|---|---|
| 1 | A — token invalidation | ~1 day | No (silent security improvement) |
| 2 | B — change-password rate limit | ~2 hrs | Only on abuse |
| 3 | B — login lockout | ~½ day | On lockout |
| 4 | C — reset tokens | ~2 days | Yes (admin UI changes) |
| 5 | D1 — password history | ~3 hrs | On reuse attempt |
| 6 | D3 — admin quorum | ~2 hrs | On last-admin edit |
| 7 | D2 — JTI denylist | ~1 day | No (requires Redis) |

---

## 5. Defaults Summary

For a fresh install upgrading from today's branch, **nothing changes** unless the operator opts in. This matches the rest of the security/observability surface (`METRICS_ENABLED`, `OTEL_ENABLED`, `ADMIN_UI_ENABLED`).

| Setting | Default | Recommendation |
|---|---|---|
| `AUTH_TOKEN_VERSIONING_ENABLED` | `False` | Turn **on** for any multi-user deployment. |
| `AUTH_INVALIDATE_TOKENS_ON_DEACTIVATE` | `False` | Turn **on** if you actually use deactivation as a kick. |
| `AUTH_INVALIDATE_TOKENS_ON_LOGOUT` | `False` | Leave off unless you want a logout to evict every device. |
| `AUTH_RATE_LIMIT_CHANGE_PASSWORD` | `False` | Turn **on** in any internet-reachable deployment. |
| `AUTH_RATE_LIMIT_LOGIN_LOCKOUT_ENABLED` | `False` | Turn **on** for any internet-reachable deployment. |
| `AUTH_PASSWORD_RESET_MODE` | `temp_password` | Move to `reset_token` once the frontend is in place. |
| `AUTH_PASSWORD_HISTORY_DEPTH` | `0` | Set to `5` only for compliance scenarios. |
| `AUTH_REQUIRE_ADMIN_QUORUM` | `False` | Turn **on** for any deployment with >1 admin. |

---

## 6. Documentation Deliverables Per Phase

Each phase ships with:
- Updated `.env.docker.example` block for the new flags.
- A "Hardening" section appended to `docs/guides/SECURITY_GUIDE.md` (or a new `docs/guides/AUTH_HARDENING_GUIDE.md`) describing what each flag does, what it costs, and what scenarios it protects against.
- Migration runbook entry in `docs/guides/DOCKER_DEPLOYMENT_GUIDE.md` calling out the alembic upgrade.
- Settings panel entry in the Admin → Health sub-tab showing each flag's current state.

---

## 7. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Flipping `AUTH_TOKEN_VERSIONING_ENABLED` mid-flight could lock everyone out | Tokens without a `pv` claim are accepted; only stale `pv` is rejected. Existing tokens keep working until they expire naturally. |
| Login lockout amplifies a password-spray DoS | Tracker keyed by username, not IP; threshold and window configurable; success resets counter. |
| Reset-token URL is shared insecurely | TTL ≤ 15 minutes; single-use; admin can revoke before redemption by issuing a second reset (which invalidates the first by hashed-token replacement). |
| Password history table grows unbounded | Trim to last N hashes per user on insert. |
| Admin quorum check blocks legitimate workflows (e.g. transferring admin between accounts) | Endpoint accepts a `force=True` query param plus an audit reason when the operator explicitly accepts the lockout risk. |

---

## 8. Open Questions

- Should we collapse `AUTH_INVALIDATE_TOKENS_ON_DEACTIVATE` and `AUTH_INVALIDATE_TOKENS_ON_LOGOUT` into a single `AUTH_TOKEN_INVALIDATION_TRIGGERS` list? Easier to extend later, slightly noisier today.
- For Phase C, do we want the redemption URL to point at the frontend (`/reset?token=…`) or the API directly? Frontend is friendlier; API works without the SPA loaded.
- Phase B login lockout: in-process (simple, doesn't survive restart) vs Redis-backed (consistent across workers, requires the `full` profile). Default to in-process and document the limitation.

---

## 9. Linkage

- Implements follow-ups from `docs/reports/PR_REVIEW_PHASE_24_OBSERVABILITY_MONITORING_SENIOR_REVIEW.md` Finding #3.
- Builds on `must_change_password` flow added in alembic `3d8f4c2a1e9b`.
- Touches surfaces owned by Phase 21 (auth) and Phase 24.7 (admin UI).
