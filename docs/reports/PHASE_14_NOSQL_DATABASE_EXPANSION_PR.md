PR Review: NoSQL Database Expansion (Phase 14)                                                                                                      
                                                                                                                                                      
  Branch: no-sql-database-expansion | 63 files, +7,471 / -312 lines | 2 commits                                                                       
                  
  Overall Assessment

  Well-structured feature addition that adds 5 NoSQL databases (MongoDB, Redis, Cassandra, DynamoDB, Elasticsearch) via a clean router pattern. The
  architecture correctly branches NoSQL queries away from the SQL pipeline early, and each database follows a consistent handler pattern. Good test
  coverage with 127+ tests.

  ---
  Issues Found

  Critical / Security(ALL 3 Fixed)

  1. Password leakage in MongoDB URI (src/nosql/mongodb/client_pool.py:70-74)
  password = connection.password_encrypted  # TODO: decrypt
  1. The password_encrypted field is being used raw in the URI. If it's actually encrypted (as the name suggests), the connection will fail. If it's
  stored plaintext despite the name, you're fine — but the TODO: decrypt comment suggests this isn't resolved. Also, the username/password are
  interpolated directly into the URI string without URL-encoding, which will break if either contains special characters (@, :, /, %).

  1. Same issue exists in all other client pools — check Redis, Cassandra, DynamoDB, Elasticsearch for consistent password handling.
  2. Redis execute_command accepts arbitrary commands (src/nosql/redis/query_executor.py:82)
  result = await self.client.execute_command(cmd, *args)
  2. The only guard is is_write on the RedisCommand object, which is set by the LLM-generated command. A hallucinated or adversarial prompt could
  generate dangerous commands like FLUSHALL, FLUSHDB, CONFIG SET, DEBUG, SHUTDOWN, SCRIPT, EVAL. Consider allowlisting safe commands rather than
  relying on the LLM's is_write flag.
  3. DynamoDB PartiQL injection surface (src/nosql/dynamodb/query_executor.py:70-71)
  response = await client.execute_statement(Statement=partiql, ...)
  3. The write check only looks at the first word (INSERT, UPDATE, DELETE). An LLM-generated query like SELECT ... ; DELETE FROM ... or other PartiQL
  injection vectors aren't blocked. The SQL pipeline has semicolon stripping — consider equivalent protection here.

  Moderate

  4. Massive code duplication across all 5 handlers
  Every handler has near-identical _get_schema(), _generate_and_execute_with_retry(), and _build_error_result() methods. The NoSQLHandler base class
  defines the interface but doesn't provide shared implementation. Consider extracting the retry/schema-caching logic into the base class to reduce
  ~400 lines of duplication and ensure bug fixes apply everywhere.
  5. _introspect_nosql_database duplicates handler schema caching (src/core/multi_db_handler.py:462-539)
  The multi-DB handler has its own 80-line schema caching block that duplicates the logic in each handler's _get_schema(). Schema caching should live
  in one place.
  6. NoSQL path in query.py skips several SQL-path features (src/api/endpoints/query.py:270-279)
  The NoSQL branch doesn't call:
    - format_attempts_for_ui() — raw attempts are passed through instead
    - Result narration / data insights
    - LLM usage tracking
    - Learned pattern caching

  Some of these may be intentional for Phase 14, but it's worth documenting which features are deferred.
  7. is_read_only logic change (src/api/endpoints/query.py:119)
  # Old (SQL path): is_read_only = True  # Determine from SQL if needed
  # New (NoSQL path): is_read_only = not request.allow_write
  7. The NoSQL path changed the semantics — is_read_only is now based on the request flag rather than the actual query. If someone sends
  allow_write=False but the generated query is read-only (which it should be), this is fine. But it's inconsistent with the SQL path which always
  returns True.
  8.(fixed) Client pools have no eviction/cleanup strategy
  All 5 singleton client pools (MongoClientPool, RedisClientPool, etc.) store clients forever keyed by connection_id. There's no TTL, no max-size
  limit, and no cleanup when connections are soft-deleted. The evict() methods exist but are never called.
  9. (ISSUE is Fixed)Cassandra session is synchronous (src/nosql/cassandra/client_pool.py)
  The cassandra-driver Cluster.connect() is synchronous and could block the event loop. Consider running it via asyncio.to_thread().

  Minor

  10.(add to tech debt) datetime.utcnow() is deprecated (all handlers)
  Python 3.12+ deprecates datetime.utcnow(). Use datetime.now(timezone.utc) instead. This appears in every handler's _get_schema() and in
  multi_db_handler.py.
  11. Mutable default argument (src/nosql/mongodb/handler.py:268)
  def _build_error_result(self, ..., attempts: list = None):
  11. Should be Optional[List] = None for type correctness (functionally fine since you don't mutate the default).
  12.(fixed) ConnectionCreate schema allows database_name min_length=1 for all types (src/api/endpoints/connections.py:13)
  But DynamoDB doesn't need a database_name (it's table-based), and Elasticsearch uses index names at query time. The frontend sets database_name=''
  for DynamoDB which will fail the Pydantic validation.
  13.(fixed) Elasticsearch connection test uses HTTP, not HTTPS (src/core/connection_tester.py:432)
  url = f"http://{host or 'localhost'}:{port or 9200}"
  13. Production Elasticsearch typically uses HTTPS. Should support both schemes.
  14. Missing __init__.py test for tests/nosql/ — tests may not be discovered depending on pytest configuration (the empty __init__.py is present, so
  this is fine).

  Positives

  - Clean router pattern (is_nosql() + execute_nosql_query()) makes the branch point simple and clear
  - Consistent result contract via normalize_nosql_result() — downstream code works unchanged
  - Write protection on all executors with allow_write flag
  - Timeout protection on all query executions via asyncio.wait_for()
  - Error classifiers per database enable targeted self-correction hints
  - Good test coverage across all 5 databases with error classification, schema inspection, and executor tests
  - Frontend modal cleanly handles 11 database types with type-specific form layouts
  - Dialect registry properly skips SQL rules for NoSQL types

  Recommendation

  The PR is close to merge-ready but I'd want issues #1 (password handling), #2 (Redis command allowlisting), and #3 (PartiQL injection) addressed
  before merging. The duplication (#4-5) is worth tracking as tech debt but doesn't block the PR.
   
   Changesmade                                                                                                                                                                                                                                                                        
  1. MongoDB URI credential encoding (src/nosql/mongodb/client_pool.py)                                                                               
  - Added urllib.parse.quote_plus import                                                                                                              
  - URL-encode both username and password in _build_uri() to handle special characters (@, :, /, %)                                                 
  - Removed stale # TODO: decrypt comment

  2. Redis command allowlist (src/nosql/redis/query_executor.py)
  - Added ALLOWED_READ_COMMANDS (45 safe read commands) and ALLOWED_WRITE_COMMANDS (30 safe write commands) as frozen sets
  - Commands not on the allowlist are blocked before execution — this prevents dangerous commands like FLUSHALL, FLUSHDB, CONFIG SET, DEBUG, SHUTDOWN,
   SCRIPT, EVAL, CLUSTER
  - Write detection now also checks the command against ALLOWED_WRITE_COMMANDS (not just the LLM's is_write flag), so even if the LLM marks DEL as
  is_write: false, it's still blocked when allow_write=False

  3. PartiQL injection protection (src/nosql/dynamodb/query_executor.py)
  - Added _validate_partiql() method that runs before execution
  - Blocks multi-statement injection via semicolons (strips string literals first to avoid false positives)
  - Allowlists only SELECT/INSERT/UPDATE/DELETE as first keywords — blocks CREATE, DROP, or any exotic PartiQL extensions
13. Fixed the Elasticsearch HTTP/HTTPS issue in three places:                                                                                           
  - src/core/connection_tester.py — test connection uses HTTPS when credentials are provided                                                        
  - src/nosql/elasticsearch/client_pool.py — client pool uses HTTPS when credentials are provided                                                     
  - frontend/src/components/DatabaseConnectionModal.tsx — connection string preview matches the same logic                                            
                                                                                                                                                      
  The heuristic is: credentials present → HTTPS (production/cloud clusters like Elastic Cloud always require auth + TLS), no credentials → HTTP (local
   dev).    
8. Here's what was done:                                                                                                                               
                                                                                                                                                      
  src/nosql/base.py — Added NoSQLClientPoolMixin with:                                                                                                
  - MAX_POOL_SIZE = 20 — LRU eviction when exceeded                                                                                                   
  - IDLE_TTL_SECONDS = 1800 — prune clients idle >30 min                                                                                              
  - _cleanup_stale() — lazy TTL sweep called on each get_client()                                                                                     
  - _enforce_max_size() — LRU eviction called after inserting new entries                                                                             
  - _close_entry_sync() — override point for DB-specific cleanup
                                                                                                                                                      
  All 5 client pools — Inherit NoSQLClientPoolMixin, call _cleanup_stale() at the top of get_client()/get_session(), call _enforce_max_size() after
  inserting new entries. Each overrides _close_entry_sync() for proper cleanup (Motor close(), Redis aclose() via fire-and-forget, Cassandra
  session.shutdown()/cluster.shutdown(), ES close() via fire-and-forget).

  src/nosql/router.py — Added evict_nosql_pool(connection_id, database_type) dispatch function.   
12. Fixed: database_name is now optional (empty string allowed) for DynamoDB, Elasticsearch, and Redis via a @model_validator. All other database types 
  still require it. This matches the frontend behavior where DynamoDB sends no database name and Redis sends a db number (which can be "0").        
   Issue 4: Extracted shared handler logic into NoSQLHandler base class                                                                                
                                                                                                                                                      
  - src/nosql/base.py: Added _get_schema(), _generate_and_execute_with_retry(), and _build_error_result() as concrete methods on NoSQLHandler. Added  
  generate_with_error_context() to NoSQLQueryGenerator ABC. The retry loop accepts an error_classifier callable to keep DB-specific error             
  classification.                                                                                                                                     
  - src/nosql/redis/command_generator.py: Renamed previous_command → previous_query (kept previous_command as optional backward-compat kwarg).        
  - 5 handler files: Removed ~400 lines of duplicated _get_schema, _generate_and_execute_with_retry, and _build_error_result methods. Each handler now
   just wires up its pool/inspector/generator/executor in handle() and delegates to the base class.                                                   
                                                                                                                                                      
  Issue 5: Deduplicated schema caching in multi_db_handler
                                                                                                                                                      
  - src/nosql/router.py: Added get_nosql_inspector() (pool→client→inspector factory) and get_cached_or_fresh_schema() (TTL cache check + fresh inspect
   + persist).                                                                                                                                        
  - src/core/multi_db_handler.py: Replaced the 65-line _introspect_nosql_database() body with a 3-line call to the new router helpers.                
                                                                                                                                                      
  Issue 6: NoSQL attempts formatting

  - src/api/endpoints/query.py: Added a comment clarifying that NoSQL handler attempts are already UI-formatted dicts (unlike the SQL path which
  converts CorrectionAttempt objects).  
                                                                     