PR Review: NoSQL DML Support (Latest Commit)                                                                                          
                                                                                                                                        
  Overall Assessment                                                                                                                    
                                                                                                                                        
  Solid extension of the Phase 18 edit mode to all 5 NoSQL databases. The architecture mirrors the existing SQL DML pipeline well —     
  separate generator, executor, and validator paths with a clean dispatch pattern. Good test coverage (36 new tests). A few issues worth
   addressing before merge:                                                                                                             
                  
  ---
  Bugs / Correctness Issues
                                                                                                                                        
  1. CQL injection via _cql_val — nosql_dml_generator.py:164
  The _cql_val helper does naive string interpolation (f"'{v}'") for display strings, but the same display string is also used as       
  parameterized_sql. While the actual execution uses parameterized queries (%s placeholders + params list), a single quote inside a     
  string value will break the display SQL and could confuse preview consumers. Consider escaping single quotes in the display path      
  (v.replace("'", "''")).                                                                                                               
                  
  2. DynamoDB PartiQL injection risk — nosql_dml_generator.py:181,191,198                                                               
  DynamoDB's native dict stores the raw PartiQL string with values interpolated inline (_partiql_val). The executor passes this directly
   to client.execute_statement(Statement=partiql) at nosql_dml_executor.py:193 with no parameterization. PartiQL supports ? placeholders
   via the Parameters field — you should use those instead of string interpolation. This is the most significant issue in this PR.
                                                                                                                                        
  3. Elasticsearch doc.pop("_id") mutates input — nosql_dml_generator.py:237                                                            
  doc.pop("_id") mutates change.new_row_data in place, which could cause unexpected behavior if the same change object is used again
  (e.g., in preview then execute). Copy the dict first:                                                                                 
  body = {k: v for k, v in doc.items() if k != "_id"}
  native = {"method": "index", "index": index, "body": body}                                                                            
  if doc.get("_id"):                                        
      native["id"] = str(doc["_id"])                                                                                                    
                                    
  4. update_write_permissions crashes when current_user is None — dml.py:231                                                            
  Line 231 accesses current_user.id without first checking current_user is not None. When REQUIRE_AUTH=False and get_optional_user      
  returns None, this line will raise AttributeError:                                                                                    
  if connection.owner_id is not None and connection.owner_id != current_user.id and not current_user.is_admin:                          
  The guard at line 226 only covers owner_id is None + auth active. Add a current_user is not None guard to line 231.                   
                                                                                                                                        
  5. MongoDB transaction assumes replica set — nosql_dml_executor.py:109-110                                                            
  client.start_session() + session.start_transaction() requires a MongoDB replica set. Standalone MongoDB instances will throw          
  ConfigurationError. Consider catching this and falling back to non-transactional execution, or at minimum surfacing a clear error     
  message.                                                                                                                              
                                                                                                                                        
  ---             
  Design Concerns
                 
  6. Redis pipeline error handling — nosql_dml_executor.py:248-266
  pipe.execute() returns a list of results (one per command). If any command in the MULTI/EXEC pipeline fails, Redis raises the error   
  only for that command. Currently the code doesn't inspect individual results — a partial failure would silently succeed. Check the    
  return values or catch redis.exceptions.ResponseError per result.                                                                     
                                                                                                                                        
  7. Cassandra BatchStatement with mixed tables — nosql_dml_executor.py:161-172                                                         
  Cassandra logged batches spanning multiple partitions/tables are an anti-pattern that degrades performance. The code unconditionally
  batches all statements. Consider warning or splitting by table/partition, or at minimum using BatchType.UNLOGGED when statements span 
  tables.         
                                                                                                                                        
  8. DMLStatement.parameterized_sql is always identical to display_sql for NoSQL — nosql_dml_generator.py:96                            
  This field name is misleading since NoSQL statements aren't parameterized SQL. Not blocking, but consider setting it to None or an
  empty string to avoid confusion downstream.                                                                                           
                  
  ---                                                                                                                                   
  Frontend        
          
  9. WritePermissionsModal — no allowed_tables UI
  The backend supports allowed_tables whitelist, and the modal saves permissions without it (sending undefined). This means existing    
  table restrictions get silently cleared on save. Either preserve the current allowed_tables value when saving, or add UI for it.      
                                                                                                                                        
  10. WritePermissionsModal — missing keyboard handling                                                                                 
  No Escape key handler to close the modal, and no focus trap. Minor UX issue.
                                                                                                                                        
  ---
  Testing                                                                                                                               
                  
  11. NoSQL executor tests mock everything — no integration path
  The 14 executor tests use mocked dispatch functions, which is fine for unit tests but doesn't verify that the actual _execute_*       
  functions work with real client pool imports. Consider at least an import-level smoke test.                                           
                                                                                                                                        
  12. Missing test: _get_nosql_table_info — dml.py:342-416                                                                              
  The NoSQL table-info endpoint helper has nontrivial branching logic for DynamoDB/Cassandra PK extraction but no test coverage.
                                                                                                                                        
  ---             
  Nits                                                                                                                                  
                  
  - nosql_dml_generator.py:184 — " SET ".join(...) for DynamoDB UPDATE produces SET col1 = v1 SET col2 = v2 instead of SET col1 = v1, 
  col2 = v2. Should be ", ".join(...) wrapped in a single SET.                                                                          
  - Commit message has a typo: ests/dml/test_dml_validator.py (missing t).
  - frontend/src/hooks/useEditMode.ts is 67 lines of new code but never imported anywhere visible in this diff — verify it's wired up.  
                                                                                                                                        
  ---                                                                                                                                   
  Summary                                                                                                                               
                  
  Must fix before merge: Items 2 (DynamoDB PartiQL injection), 3 (mutating input), 4 (None crash on permissions endpoint), and 14
  (DynamoDB SET join bug).                                                                                                              
   
  Should fix: Items 1, 5, 6, 9.                                                                                                         
                  
  Nice to have: Items 7, 8, 10, 11, 12.

  Codex:
  1. High: src/api/endpoints/dml.py:342 is written against the wrong schema shape. It treats schema["tables"][name] as a {field_name:
     field_info} map and iterates fields.items() (src/api/endpoints/dml.py:368-399), but every real inspector returns {"columns": [...],
     "row_count": ...} instead (src/nosql/mongodb/schema_inspector.py:95-98, src/nosql/dynamodb/schema_inspector.py:104-108, src/nosql/
     cassandra/schema_inspector.py:40-48, src/nosql/elasticsearch/schema_inspector.py:42-49, src/nosql/redis/schema_inspector.py:67-88).
     In production this will produce bogus columns like columns/row_count, and DynamoDB/Cassandra PK extraction will never see kind/
     key_type, so NoSQL edit mode cannot build correct PK metadata.
  2. High: Redis DML is blocked by the identifier regex. The NoSQL regex only allows letters, digits, _, ., and - (src/dml/
     constants.py:8-9), and both validation and table-info enforce it (src/dml/dml_validator.py:102-116, src/api/endpoints/dml.py:295-
     300). Real Redis keys/patterns here are colon-delimited and may contain * (src/nosql/redis/schema_inspector.py:90-107), so requests
     like user:1 or user:* will be rejected before execution. That makes the Redis DML path effectively unusable.
  3. High: the frontend never enables edit mode for MongoDB, Redis, or Elasticsearch results. extractTableName() only understands
     SELECT ... FROM ... SQL (frontend/src/components/edit/EditModeWrapper.tsx:21-38), and edit mode is gated on that parse succeeding
     (frontend/src/components/edit/EditModeWrapper.tsx:55-78). But the displayed NoSQL queries are db.collection.find(...), raw Redis
     commands, and GET /index/_search (src/nosql/mongodb/mql_generator.py:196-230, src/nosql/redis/command_generator.py:182-184, src/
     nosql/elasticsearch/query_dsl_generator.py:118-122). So the branch adds backend NoSQL DML support that the UI cannot reach for 3/5
     NoSQL backends.
  4. Medium: the NoSQL table-info tests validate a schema format that production never returns, so they would not catch finding #1. The
     tests mock {"tables": {"users": {"name": "string", ...}}} and similar flat field maps (tests/dml/test_nosql_dml_executor.py:212-
     306), while the real inspectors all return a columns array. The current coverage therefore gives false confidence around the most
     fragile part of the NoSQL DML integration.

  Assumptions:

  - I focused on reviewable correctness issues and did not inspect every frontend component outside the edit-mode path.
  - I could not run the test suite locally because pytest is not installed in this environment (python3 -m pytest --version failed with
    No module named pytest).