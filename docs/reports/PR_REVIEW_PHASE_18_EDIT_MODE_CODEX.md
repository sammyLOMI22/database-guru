# PR Review: `phase-18-edit-mode`

## Verdict
**Status**: REQUEST CHANGES

## Findings

### 1. Saved edits are not reflected in the UI after a successful execute
- Evidence: `frontend/src/components/edit/ChangesSummaryBar.tsx:34-42` clears local changes with `onDiscard()` and closes the modal, but does not refresh or patch the rendered data. `frontend/src/components/edit/EditModeWrapper.tsx:98-115` keeps rendering the original `results` prop it received from the query response.
- Impact: After a successful `UPDATE` / `INSERT` / `DELETE`, the table falls back to stale pre-edit data. For inserts and deletes this can look like the save failed, and for updates it can invite duplicate or conflicting edits.
- Recommendation: Rehydrate the visible rows from the execute result, or trigger a query refresh / parent invalidation before clearing the local change tracker.

### 2. Disabling `require_where_clause` produces invalid SQL for `UPDATE` and `DELETE`
- Evidence: `src/dml/dml_validator.py:84-92` allows empty `primary_key` values whenever `require_where_clause` is `False`. But `src/dml/dml_generator.py:150-164` and `src/dml/dml_generator.py:178-190` always emit `WHERE {where_clause}`, while `src/dml/dml_generator.py:202-220` returns an empty string for an empty primary key.
- Impact: Any connection configured with `require_where_clause = false` will generate statements like `UPDATE ... WHERE` or `DELETE ... WHERE`, which are invalid SQL. The flag cannot work as implemented.
- Recommendation: Either reject empty primary keys unconditionally, or explicitly support full-table DML when that guardrail is disabled.

### 3. “Per-user” rate limiting is actually keyed per token
- Evidence: `src/middleware/rate_limit.py:18-42` validates the JWT and then hashes the entire token, returning `tok:<hash>` as the bucket key.
- Impact: The same account can mint multiple valid JWTs by logging in again and get a fresh rate-limit bucket each time. That defeats the intended `RATE_LIMIT_PER_USER` / `RATE_LIMIT_LLM_PER_USER` controls.
- Recommendation: Key authenticated traffic by a stable identity from the validated token payload, such as `sub`, and fall back to IP only for unauthenticated requests.

## Open Questions / Assumptions
- Review scope is the diff from `main` merge-base `ef8c1886d728345473ee0f9629a448d1a5275d63` to `phase-18-edit-mode`.
- I did not run the test suite in this environment; findings are based on code review of the branch delta.

## Summary
This branch adds substantial edit-mode functionality and auth/audit work. The main blockers are the stale post-save UI state, the broken `require_where_clause=false` path, and a rate-limit key that does not match the intended per-user behavior.

\Fix 1: Stale UI after DML execute                                                                           
  - EditModeWrapper now manages a local displayResults state (synced from props via useEffect)              
  - After successful save, handleSaveSuccess applies changes optimistically: UPDATEs patch row values,      
  DELETEs remove rows, INSERTs append new rows                                                              
  - Callback flows: ChangesSummaryBar → EditableQueryResults → EditModeWrapper via onSaveSuccess            
                                                                                                            
  Fix 2: Invalid SQL with empty WHERE clause                                                                  
  - Validator now always requires a primary key for UPDATE/DELETE, regardless of require_where_clause       
  setting                                                                                         
  - Generator adds defensive guards — raises ValueError if primary_key is empty for UPDATE/DELETE           
  - This prevents WHERE  (empty clause) from ever being emitted                                             
                                                                                                            
  Fix 3: Rate limit keyed per-token → per-user                                                                   
  - _extract_rate_limit_key now extracts sub from the decoded JWT payload                                   
  - Returns user:<sub> instead of tok:<hash>, so multiple tokens for the same user share one rate-limit   
  bucket                                                                                                    
  - Removed unused hashlib import 