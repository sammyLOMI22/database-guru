PR Review: NoSQL Database Expansion (Phase 14)                                                                                                                       
                                                                                                                                                                       
  Branch: no-sql-database-expansion (4 commits, +7843/-321 lines, 65 files)                                                                                            
                  
  Overall Assessment

  Well-structured feature addition. The architecture follows good patterns — abstract base classes, shared retry logic, per-DB handlers, result normalization to a
  common contract. The code integrates cleanly into the existing SQL pipeline without breaking it.

  ---
  Positives

  1. Clean routing — is_nosql() check in query.py and multi_db_handler.py creates a clean branch before the SQL pipeline, avoiding any changes to the SQL path
  2. Shared base classes — NoSQLHandler, NoSQLClientPoolMixin, NoSQLSchemaInspector, NoSQLQueryGenerator in base.py eliminate duplication across 5 DB handlers
  3. Same result contract — normalize_nosql_result() ensures NoSQL results match SQLExecutor.execute_query() shape, so downstream narration/history/frontend works
  unchanged
  4. Security-conscious — Redis has command allowlists blocking dangerous ops (FLUSHALL, CONFIG, EVAL). DynamoDB validates PartiQL against injection. MongoDB blocks
  writes unless allow_write=True
  5. Agent integration — Retry loop integrates CorrectionLearner, ConfidenceScorer, and ResultVerificationAgent with proper try/except wrappers (non-fatal)
  6. Good test coverage — 127 tests across 6 files

  ---
  Issues

  High Priority

  1. datetime.utcnow() deprecation — Used in base.py:961, base.py:982, router.py:136, router.py:147. This is deprecated in Python 3.12+ and returns naive datetimes.
  The NoSQLClientPoolMixin already uses datetime.now(timezone.utc) — these should be consistent:
  # base.py:961, 982 and router.py:136, 147
  datetime.utcnow()  →  datetime.now(timezone.utc)
  1. Note: this will only work if connection.schema_updated_at is also timezone-aware, so verify that first.
  2. password_encrypted used as raw password — mongodb/client_pool.py:79 reads connection.password_encrypted and URL-encodes it directly into the MongoDB URI. If this
  is actually an encrypted value (as the name suggests), it would need decryption first. The other connection testers in connection_tester.py use connection.password —
   check which is correct.
  3. Missing evict() on some pools — router.py:evict_nosql_pool() calls pool.evict() on all 5 pools, but not all pool classes implement evict(). Verify
  DynamoDBClientPool and ElasticsearchClientPool have this method.

  Medium Priority

  4. Handler instantiation per request — router.py:execute_nosql_query() creates a new handler instance on every query (e.g., MongoDBHandler()). Since handlers are
  stateless, this is fine functionally, but a singleton or module-level instance would avoid repeated allocation.
  5. _DB_NAME_OPTIONAL_TYPES as class variable with underscore — In ConnectionCreate (connections.py), _DB_NAME_OPTIONAL_TYPES uses a leading underscore which Pydantic
   may treat specially (as a private attribute). Consider using model_config or a plain ClassVar annotation to be explicit.
  6. DynamoDB PartiQL injection mitigation is incomplete — _validate_partiql() strips single-quoted strings before checking for semicolons, but doesn't handle escaped
  quotes within strings ('it''s'). This could allow a crafted string to bypass the check. Consider using parameterized statements instead.
  7. No write protection in Elasticsearch executor — Unlike MongoDB, Redis, Cassandra, and DynamoDB executors, ElasticsearchQueryExecutor has an allow_write param but
  never checks it. The _execute_search method would need to block index/update/delete operations.
  8. (fixed)Cassandra sync driver in async context — cassandra/client_pool.py mentions "queries are run in a thread pool executor" but the handler doesn't wrap
  session.execute() in asyncio.run_in_executor(). Verify the Cassandra query executor actually does this.

  Low Priority

  9. Duplicated schema caching logic — NoSQLHandler._get_schema() and router.get_cached_or_fresh_schema() do nearly the same thing. Consider having _get_schema()
  delegate to get_cached_or_fresh_schema().
  10. _close_entry_sync for async clients — The base mixin calls _close_entry_sync() for cleanup, but Redis and Elasticsearch clients need async close
  (aclose()/close()). The comment says "schedule via fire-and-forget" but the implementations use pass or sync close, which may leak connections on eviction.
  11. Empty __init__.py in tests/nosql/ — Fine, just noting it.
  12. Frontend DatabaseConnectionModal.tsx — The refactoring to extract inputClass/labelClass constants and add conditional form layouts is clean. The DynamoDB field
  mapping (host→region, username→access_key, password→secret_key) has good label overrides.

  ---
  Suggestions

  - Add an integration test that exercises the full query.py → is_nosql() → handler flow with a mocked NoSQL backend
  - Consider adding a NoSQLClientPool abstract base with evict() and close_all() as required methods
  - The KEYS command in Redis allowlist (query_executor.py:33) can be dangerous on production databases with many keys — consider using only SCAN

  ---
  Verdict

  Approve with minor changes. The architecture is solid and well-integrated. Fix the password_encrypted issue (#2) and the Elasticsearch write protection gap (#7)
  before merging. The datetime.utcnow() deprecation (#1) should also be addressed for consistency.
  Summary of fixes:                                                                                                                                                    
                                                                                                                                                                     
  - Issue #1 fixed — Replaced all 4 datetime.utcnow() calls in src/nosql/base.py and src/nosql/router.py with datetime.now(timezone.utc). Used .replace(tzinfo=None)   
  for age comparisons to stay compatible with the naive DateTime DB column, and timezone-aware for writes (matching file_source_handler.py pattern).                   
  - Issue #2 (false positive) — password_encrypted is the actual DB column name; there's no encryption layer yet. The SQL connectors use it the same way (# TODO:      
  decrypt). NoSQL code is consistent.                                                                                                                                  
  - Issue #3 (false positive) — All 5 pools (MongoDB, Redis, Cassandra, DynamoDB, Elasticsearch) implement evict().    
   #5 — Pydantic private attribute (connections.py): Changed _DB_NAME_OPTIONAL_TYPES to DB_NAME_OPTIONAL_TYPES: ClassVar[Set[str]]. Leading-underscore 
  attributes are treated as private by Pydantic and excluded from the model schema. ClassVar annotation explicitly marks it as a class-level constant.
                                                                                                                                                      
  #6 — PartiQL escaped quote bypass (dynamodb/query_executor.py): Changed the regex from '[^']*' to '(?:[^']|'')*' which correctly handles SQL-style  
  escaped quotes ('') inside string literals, preventing semicolons hidden inside 'it''s;DROP' from being exposed.                                    
                                                                                                                                                      
  #7 — Elasticsearch write protection (elasticsearch/query_executor.py): Added a write-intent check that blocks DSL dicts containing write keys       
  (script, update, delete, upsert, doc, doc_as_upsert) unless allow_write=True. This matches the pattern used by all other executors.                 
                                                                                                                                                      
  #4 (handler instantiation) and #8 (Cassandra async) were non-issues — handlers are stateless, and Cassandra already uses run_in_executor.
                                                
                                                                              