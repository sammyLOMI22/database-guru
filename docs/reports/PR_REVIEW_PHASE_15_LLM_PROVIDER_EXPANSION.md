PR Review: phase-15-llm-provider-expansion                                                                                  
                                                                                          
  Recommendation: REQUEST CHANGES | Vibe Score: 6.2/10                                                                                                 
                                                                                                                                                       
  The provider abstraction, DML pipeline, and auth internals are well-designed. The issues are mostly security gaps from missing wiring rather than    
  fundamental design flaws.                                                                                                                            
                                                                                                                                                       
  ---                                                                                                                                                  
  CRITICAL (3 — must fix before merge)                                                                                                                 
                                                                                                                                                       
  1. Unauthenticated LLM provider endpoints (src/api/endpoints/llm_providers.py) — All mutation endpoints (PUT/DELETE config, routing) have zero auth. 
  Anyone can overwrite API keys and provider configs. Add Depends(require_admin).                                                                      
  2. Default JWT secret accepted when auth is "off" (src/config/settings.py:20) — JWT_SECRET defaults to "change-this-jwt-secret" and the guard only   
  fires when REQUIRE_AUTH=True. Since login/register are always available and get_optional_user decodes tokens, an attacker can forge tokens to bypass 
  DML ownership checks.                                                                                                                                
  3. No login-specific rate limiting (src/api/endpoints/auth.py) — Login/register share the general 100-req/min limit. No account lockout, no          
  progressive delay. Brute-force credential stuffing is trivially easy.                                                                                
                                                                                                                                                       
  HIGH (5)                                                                                                                                             
                                                                                                                                                       
  4. Plaintext API key fallback (src/services/provider_config_service.py:33-37) — Missing LLM_ENCRYPTION_KEY silently stores keys as plaintext. Should 
  refuse to write keys without encryption.                                                                                                             
  5. Security bypass on unauthenticated endpoints — test_provider and list_provider_models use enforce_security=False, letting anyone probe cloud      
  providers even under local_only security.                                                                                                            
  6. result.rowcount = -1 not handled (src/dml/dml_executor.py:116) — SQLite/ODBC can return -1, breaking affected-row counts.                         
  7. Cassandra batch type inverted (src/dml/nosql_dml_executor.py) — LOGGED used for single-table (should be UNLOGGED), UNLOGGED for multi-table       
  (should be LOGGED or avoided entirely).                                                                                                              
  8. request.client can be None in RateLimitMiddleware.dispatch — will crash instead of rate-limiting.                                                 
                                                                                                                                                       
  MEDIUM (7)                                                                                                                                           
                                                                                                                                                       
  9. CORS uses wildcard methods/headers with allow_credentials=True                                                                                    
  10. Password policy: only 8-char minimum, no complexity/blocklist                                                                                    
  11. No token revocation/logout mechanism                                                                                                             
  12. Provider config changes not audit-logged                                                                                                         
  13. Duplicate ownership checks between validator and endpoint                                                                                        
  14. display_sql field named sql — invites unsafe execution                                                                                           
  15. SAFE_IDENT_RE rejects schema-qualified names like public.users                                                                                   
                                                                                                                                                       
  LOW (4)                                                                                                                                              
                                                                                                                                                       
  16. DateTime columns missing timezone=True in User model                                                                                             
  17. request.client.host doesn't extract X-Forwarded-For                                                                                              
  18. Provider registry singleton not thread-safe                                                                                                      
  19. Rate limiter cleanup has dictionary-mutation race condition                                                                                      
                                                                                                                                                       
  ---                                                                                                                                                  
  What's Good                                                                                                                                          
                                                                                                                                                       
  - Provider abstraction (BaseLLMProvider → TrackedLLMClient → ProviderRegistry) is clean and extensible                                               
  - DML pipeline's two-form approach (display SQL vs parameterized) is a solid pattern                                                                 
  - Auth service timing-attack mitigation with _DUMMY_HASH shows security awareness                                                                    
  - log_action() never-raises contract is pragmatic                                                                                                    
  - Good test coverage on auth service and DML operations                                                                                              
                                                                                                                                                       
  Fixing the 3 critical + 5 high items would bring this to ~8.5/10. The core architecture is production-quality; the gaps are wiring omissions, not    
  design flaws.

  Fixed all critical, high, medium and low issues