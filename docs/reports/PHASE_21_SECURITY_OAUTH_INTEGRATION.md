PR Review: Phase 21 — Security & Auth Foundation                                                                                                    
                                                                                                                                                      
  Overall Assessment: Solid implementation, a few issues to address                                                                                   
                                                                                                                                                      
  The PR adds JWT authentication, resource ownership, per-user rate limiting, and audit logging with a well-thought-out backwards-compatible approach
  (REQUIRE_AUTH=False by default). Good test coverage (57 tests). The code is clean and well-organized.

  ---
  Issues

  1. SECURITY: JWT secret defaults are insecure (High)

  src/config/settings.py:19-20 — Both SECRET_KEY and JWT_SECRET have hardcoded defaults:
  SECRET_KEY: str = "change-this-secret-key"
  JWT_SECRET: str = "change-this-jwt-secret"

  If someone deploys without setting env vars, every JWT is signed with a known key. Consider raising an error on startup when REQUIRE_AUTH=True and
  the secret is still the default, or at minimum logging a loud warning.

  2. SECURITY: Rate limit uses unverified JWT claims (Medium)

  src/middleware/rate_limit.py:24-27 — _extract_user_id_from_token calls jwt.get_unverified_claims():
  payload = jwt.get_unverified_claims(token)
  return f"user:{payload.get('sub', '')}"

  An attacker can craft a JWT with sub: "admin_user_id" and consume that user's rate limit quota without knowing the secret. This is a
  denial-of-service vector against specific users. Consider either:
  - Verifying the signature (perf impact), or
  - Using a hash of the full token as the rate limit key (so forged tokens get their own bucket)

  3. BUG: list_chat_sessions hides unowned sessions from authenticated users

  src/api/endpoints/chat.py:228-230:
  if current_user:
      query = query.where(ChatSession.owner_id == current_user.id)

  Unlike list_connections which uses or_(owner_id == user.id, owner_id.is_(None)), the chat sessions endpoint filters strictly by owner_id == user.id,
   hiding pre-existing sessions with owner_id=None. This is inconsistent — connections show unowned resources but sessions don't.

  4. BUG: log_action flushes but register endpoint commits twice

  src/api/endpoints/auth.py:33-42:
  user = await auth_service.register(db, ...)  # commits internally (line 95 of service.py)
  await log_action(db, ...)  # flushes
  await db.commit()  # second commit

  register() already calls db.commit() on line 95 of service.py. Then the endpoint commits again after log_action. If the log_action flush fails
  (which is swallowed), the second commit is a no-op. But if there's a DB error between the register commit and the audit log, the user is created but
   the audit entry is lost. Consider moving the commit in register() out to the endpoint so everything is in one transaction.

  5. Hardcoded migration revision IDs (Low)

  alembic/versions/a1b2c3d4e5f6_*.py — Revision IDs like a1b2c3d4e5f6, b2c3d4e5f6a7, c3d4e5f6a7b8 are clearly hand-written rather than auto-generated.
   This risks collision if someone else generates a migration with the same ID. Consider using alembic revision --autogenerate to get proper random
  IDs. (Given memory notes about Alembic autogenerate noise, at least use random hex rather than sequential patterns.)

  6. Duplicate _get_auth_service factory

  Both src/auth/dependencies.py:20 and src/api/endpoints/auth.py:20 define the same _get_auth_service function. Extract to a single location (e.g.,
  dependencies.py since it's already there).

  7. email index defined twice on User model

  src/auth/models.py:12 — email column has index=True in the column definition AND there's an explicit Index('idx_user_email', 'email') in
  __table_args__. Same for username. This creates duplicate indexes. Remove either the column-level index=True or the __table_args__ Index.

  8. Missing is_active check in get_current_user

  src/auth/dependencies.py:24-61 — get_current_user returns the user without checking is_active. get_current_active_user adds that check, but
  get_current_user is used directly in some places. This means deactivated users could still access endpoints that use get_current_user directly
  (currently only test code, but worth noting as a footgun).

  9. UserUpdate schema defined but unused

  src/auth/schemas.py:41-45 — UserUpdate is defined but there's no update-user endpoint. Dead code.

  ---
  Nits

  - src/auth/audit.py:6 — Text is imported but unused
  - src/middleware/rate_limit.py:23 — from jose import jwt is imported inside the function on every call. Since jose is now a hard dependency for
  auth, consider moving to top-level
  - test_rate_limit_user.py:50 — test_jwt_without_sub_returns_user_empty — returning "user:" (empty sub) as a rate limit key means all tokens without
  sub share a single bucket. This is fine but worth a comment

  ---
  What's done well

  - Backwards compatibility — REQUIRE_AUTH=False default, get_optional_user pattern is clean
  - Never-raising audit logger — Good resilience pattern
  - Ownership model — owner_id nullable FK with SET NULL on delete is the right choice for gradual adoption
  - Test coverage — 57 tests covering auth, ownership, rate limiting, and audit edge cases
  - Documentation — Thorough testing guide, updated architecture docs, code location index

  Recommendation

  Address items 1-4 before merging. The rest can be follow-ups.

CHANGES
1. JWT secret safety — settings.check_jwt_secret() now raises on startup if REQUIRE_AUTH=True with the default secret, and warns otherwise          
  2. Rate limit DoS vector — Replaced jwt.get_unverified_claims() with a SHA-256 hash of the raw token, so forged JWTs get their own bucket instead of
   exhausting a real user's quota                                                                                                                     
  3. Hidden unowned sessions — list_chat_sessions now includes owner_id IS NULL sessions for authenticated users, consistent with list_connections    
  4. Double-commit in register — register() now uses flush() instead of commit(), so the endpoint controls the transaction boundary (user creation +  
  audit log in one commit)                                                                                                                            
  5. Duplicate _get_auth_service — Removed from auth.py endpoint, imports from dependencies.py                                                        
  6. Duplicate indexes — Removed column-level index=True from User model's email and username (kept the explicit __table_args__ indexes)              
  7. get_current_user missing is_active check — Now raises 401 for deactivated users
  8. Unused UserUpdate schema — Removed along with unused Optional import
  9. Unused Text import — Removed from audit.py