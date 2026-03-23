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