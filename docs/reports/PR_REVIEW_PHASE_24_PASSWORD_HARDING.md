PR Review — phase-24-Observability-&-Monitoring                                                                                     
                                                                                                                                      
  Overview
                                                                                                                                      
  Bundles three large initiatives:                                                                                                    
  1. Phase 24 (Observability) — structlog + request_id contextvars, Prometheus /metrics, OpenTelemetry tracing, Grafana/Prometheus
  Docker stack, request-id badge in the UI.                                                                                           
  2. Phase 24.7 (Admin UI) — /admin/users CRUD endpoints, audit-log viewer, system-health panel, ADMIN_UI_ENABLED kill-switch.      
  3. Phase 24.8 (Password Auth Hardening) — token versioning (JWT pv claim), per-username login lockout, change-password rate limit,  
  one-shot reset tokens, password history, admin quorum guard.                                                                        
                                                                                                                                      
  22 commits, 90 files, +11459/-1364. New tables: audit_logs (already), password_reset_tokens, password_history. New column:          
  users.password_version. All Phase 24.8 behavior gated on AUTH_* flags that default to off.                                          
                                                                                                                                    
  ---                                                                                                                                 
  Strengths                                                                                                                         
           
  - Feature-flag discipline. Every hardening surface is opt-in (AUTH_TOKEN_VERSIONING_ENABLED, AUTH_RATE_LIMIT_*,
  AUTH_PASSWORD_RESET_MODE, etc.) with a single Settings.check_auth_hardening() validator at startup. Legacy JWTs without a pv claim  
  are explicitly accepted (dependencies.py:76-82) so flipping the flag doesn't boot every signed-in user.
  - Crypto primitives are correct. secrets.SystemRandom() for temp passwords, secrets.token_urlsafe(32) for reset tokens (256 bits),  
  bcrypt for token hashes (plaintext never stored), constant-time auth via _DUMMY_HASH (service.py:106-218).                          
  - Defense in depth. Self-demote/self-deactivate guard + admin-quorum overlay (admin_users.py:271-289, _enforce_admin_quorum);
  change-password and reset-redeem both run reuse-history check; reset-redeem returns generic 401 to avoid leaking which token state  
  was wrong.                                                                                                                        
  - Observability hygiene. _route_template (request_context.py:118-129) caps cardinality by using the matched route, never            
  request.url.path. Sensitive-key redaction in the structlog processor (logging_config.py:34-58) catches authorization, password,     
  token, sql, prompt, etc., recursively.
  - Migrations are idempotent. All three Phase 24.8 migrations inspect for existing tables/columns before mutating.                   
  - Strong test coverage. 9 new test files (test_auth_token_versioning.py, test_auth_reset_tokens.py, test_auth_history_and_quorum.py,
   test_auth_rate_limit.py, test_admin_users_endpoints.py, etc.) plus observability tests. Each phase has end-to-end coverage.        
                                                                                                                                      
  ---                                                                                                                                 
  Issues                                                                                                                            
        
  High priority
                                                                                                                                      
  1. GET /api/settings/ is unauthenticated and now leaks the entire auth-hardening posture. src/api/endpoints/settings.py:69-115      
  mounts at /api/settings/ with no auth dependency, and the response now includes auth_login_lockout_threshold,                       
  auth_login_lockout_window_seconds, auth_password_history_depth, auth_change_password_per_user_per_minute, auth_password_reset_mode, 
  etc. An unauthenticated visitor can fingerprint the lockout window (helping them tune sub-threshold credential stuffing) and      
  enumerate which mitigations are on. Gate this behind require_admin (or split into a public subset + admin subset).
  2. LoginAttemptTracker has unbounded memory growth from unknown usernames. rate_limit.py:236-296 keys by username.lower() with no
  eviction. An attacker spraying random usernames at /api/auth/login grows _failures without bound — each entry is a list of          
  timestamps and at least one timestamp is appended on every failure. Even with the timestamp-trim on read, the dict keys persist.
  This is a slow DoS and turns the lockout feature itself into the attack surface. Add a max-keys cap with LRU eviction, or run a     
  periodic GC pass that drops keys whose latest timestamp is outside the window.                                                    
  3. Module-level _settings = Settings() in rate_limit.py:15 snapshots JWT_SECRET at import. Anywhere _extract_rate_limit_key reads
  this, it will use the import-time value even if the lifespan-scoped Settings() later differs (e.g. test patching). The              
  create_app(settings) factory exists specifically to avoid this; the rate-limit module is the one place that ignores it. Pass
  settings in via BaseHTTPMiddleware.__init__ or read from request.app.state.                                                         
                                                                                                                                    
  Medium priority

  4. In-memory rate-limit/lockout state breaks under multi-worker. _UserKeyedRateLimiter, LoginAttemptTracker, and the global         
  RateLimitMiddleware all keep state per-process. Worker A locks alice; worker B doesn't see it; effective threshold = threshold × 
  workers. The plan acknowledges this in §8 of PASSWORD_AUTH_HARDENING_PLAN.md, but the README/Phase 24.8 docs should warn explicitly:
   do not enable lockout on multi-worker uvicorn without Redis-backed state.                                                        
  5. /api/auth/redeem-reset walks every outstanding token with bcrypt. auth.py:296-307 selects all (used_at IS NULL AND expires_at > 
  now) rows and bcrypt-compares the candidate token against each. With 15-min TTL and low volume that's fine; with a noisy admin (or a
   small attack on the endpoint) bcrypt-per-row is O(N) and a slow-DoS vector. Two options: (a) include a short, lookup-only prefix in
   the plaintext token and store it as an indexed column, narrowing the candidate set; (b) require the user identifier on redeem so   
  the index lookup is user_id=?.                                                                                                    
  6. reset_token mode leaves the old password working. admin_users.py:393-395: when AUTH_PASSWORD_RESET_MODE=reset_token, the user's
  existing password is intentionally not invalidated — only password_version is bumped and must_change_password is set. If the        
  operator reset the password to lock out a compromised account, the attacker's stolen credential still works (they'll just hit the
  forced-change screen and pick a new password they control). The semantic intent here is "user lost access, here's a link" — but the 
  endpoint is also the obvious tool for "compromised account, kick them now," and the doc/UI should either make that ambiguity      
  explicit or null the password unconditionally.
  7. /api/auth/change-password has no rate-limit when AUTH_RATE_LIMIT_CHANGE_PASSWORD=False. Default is off. A caller with a valid
  token can hammer it (cheap attack: enumerating common-password reuse via the history-check 400 vs. the success 200 response code).  
  Either flip the default to true or always apply a low ceiling.
  8. History-block path on /redeem-reset is silently un-audited. auth.py:335-348: on history reuse, db.rollback() then 400. No        
  log_action precedes the rollback, so an operator can't see "user attempted reuse on token X." Worth a log_action before the rollback
   (it'll roll back too — that's fine, but at least the attempt at the change-password endpoint is logged for the symmetric path;
  redeem should match).                                                                                                               
                                                                                                                                    
  Low priority                                                                                                                        
   
  9. Branch is too large to review in one shot. Phase 24 / 24.7 / 24.8 should have shipped as three PRs. If this can be split now     
  (even cosmetically into stacked PRs) reviewers and rollback both benefit.                                                         
  10. _UserKeyedRateLimiter also has no cleanup (rate_limit.py:180-216). Smaller blast radius than the login tracker because it's     
  keyed by user.id (only authenticated users), but the same pattern.                                                                  
  11. Reset token in URL query string (?token=…). Industry-standard but leaks via referer/server logs/browser history. If you control
  the redemption page, prefer extracting the token from the URL fragment (#token=) and POSTing it.                                    
  12. docs/reports/ ships PR-review markdown files (PR_REVIEW_PHASE_24_OBSERVABILITY_*.md, ~625 lines). These look like prior-review
  artifacts; consider whether they belong in the tree or should be .gitignored.                                                       
  13. Branch name contains & — likely fine for git, but some CI runners and shell tooling escape it inconsistently. Cosmetic.       
  14. Tracing wrapper hand-rolls __enter__ / __exit__ (tracing.py:217-274). Functional, but with span_cm as span: would handle the    
  entire lifecycle including exception path. Would simplify.                                                                          
                                                                                                                                      
  ---                                                                                                                                 
  Suggestions                                                                                                                       
                                                                                                                                      
  - For #1 (settings leak), add a SystemSettingsPublicResponse (the small public subset: require_auth, observability deep-link URLs 
  only) and keep the full payload behind require_admin. The frontend already calls this on every page load — splitting it is cheap.   
  - For #2 (memory growth), the simplest fix is a per-instance cap: drop the oldest key when len(self._failures) > 10_000. Pair with a
   comment that says "Redis backend is the supported answer for >1 worker."                                                           
  - For #5 (O(N) bcrypt redeem), if you don't want a schema change, log a warning when the active-token count exceeds 50 and run a  
  cleanup job that purges expires_at < now.                                                                                           
  - The modified field on AdminUserResponse (admin_users.py:46) is a nice UX touch but isn't read anywhere in the frontend yet —    
  confirmed no \.modified references in UserManagement.tsx. Either wire it up or drop it.                                             
                                                                                                                                    
  ---                                                                                                                                 
  Verdict                                                                                                                           
         
  Don't ship as-is. Issues #1 (unauthenticated leak of hardening posture) and #2 (memory DoS) are both touched directly by this branch
   and should land before merge. #3, #4, #7 can land as follow-ups but should be documented as known limitations. The rest are        
  quality/cleanup. The crypto and migration design is solid; the bundling and the new attack surface around /api/settings/ are the
  headline concerns.

Findings

  1. High: must_change_password is enforced only in the React shell, not by backend auth dependencies.
     src/api/endpoints/admin_users.py:366 sets must_change_password=True and tells the operator the user is forced to change before
     using the app, but src/api/endpoints/auth.py:142 still returns a normal JWT and src/auth/dependencies.py:71 only checks token
     validity/version and is_active. A direct API client can use the temporary password token against any protected endpoint without
     changing it. Add backend enforcement in the auth dependency, allowing only /api/auth/change-password, /api/auth/logout, and
     maybe /api/auth/me while the flag is set.
  2. Medium: reset-token redemption can “rotate” to the existing password when history is disabled.
     src/api/endpoints/auth.py:335 relies solely on check_password_history, but src/auth/service.py:40 returns False immediately when
     AUTH_PASSWORD_HISTORY_DEPTH=0. In reset_token mode the current password is intentionally left unchanged until redemption, so a
     user can redeem the link with their current password, clear must_change_password, consume the token, and avoid rotation. Add an
     explicit current-password comparison in /redeem-reset, independent of password-history depth.

  FIXED issues 1-7 first review +1+2 second review