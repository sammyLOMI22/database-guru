PR Review: Phase 13 CSV/Excel Data Source Support                                                                                                                    
                                                                                                                                                                       
  Summary                                                                                                                                                              
                                                                                                                                                                       
  This PR adds the ability to upload CSV and Excel files as queryable data sources via DuckDB. Files can be attached to chat sessions or made globally available, with 
  lazy-loading table management and automatic schema inference.                                                                                                        
                                                                                                                                                                       
  Changes Overview                                                                                                                                                     
                                                                                                                                                                       
  - 31 files changed (+5,214 lines)                                                                                                                                    
  - New files: 7 Python modules, 3 frontend components, tests, docs                                                                                                    
  - Key additions: File upload API, DuckDB session manager, multi-db integration, React components                                                                     
                                                                                                                                                                       
  ---                                                                                                                                                                  
  ✅ Strengths                                                                                                                                                         
                                                                                                                                                                       
  1. Well-structured architecture                                                                                                                                      
  - Clean separation: FileSourceHandler (upload/validation), FileSourceDuckDBSession (query engine)                                                                    
  - Singleton DuckDB session with lazy table loading is memory-efficient                                                                                               
  - Good integration with existing MultiDatabaseHandler                                                                                                                
                                                                                                                                                                       
  2. Solid security practices                                                                                                                                          
  - File validation with magic byte checking (src/core/file_source_handler.py:174-193)                                                                                 
  - Filename sanitization blocking path traversal (_sanitize_filename method)                                                                                          
  - Size limits enforced (100MB default)                                                                                                                               
  - Extension allowlist approach                                                                                                                                       
                                                                                                                                                                       
  3. Comprehensive test coverage                                                                                                                                       
  - ~460 lines of tests covering validation, sanitization, schema inference                                                                                            
  - Tests for edge cases (empty files, invalid extensions, path traversal)                                                                                             
                                                                                                                                                                       
  4. Good async patterns                                                                                                                                               
  - Proper use of run_in_executor for sync DuckDB operations                                                                                                           
  - asyncio.Lock protecting concurrent table creation                                                                                                                  
                                                                                                                                                                       
  ---                                                                                                                                                                  
  ⚠️ Issues to Address                                                                                                                                                 
                                                                                                                                                                       
  High Priority                                                                                                                                                        
                                                                                                                                                                       
  1. SQL Injection in DuckDB queries (src/core/file_source_session.py:127-132)                                                                                         
  session.execute(f"""                                                                                                                                                 
      CREATE OR REPLACE TABLE "{table_name}" AS                                                                                                                        
      SELECT * FROM read_csv_auto('{file_path}', header=true, all_varchar=false)                                                                                       
  """)                                                                                                                                                                 
  The file_path is user-influenced via the original filename. While sanitization exists, the SQL string interpolation is risky. Consider using DuckDB's parameterized  
  queries or additional path validation.                                                                                                                               
                                                                                                                                                                       
  2. Missing authorization checks (src/api/endpoints/files.py)                                                                                                         
  - No user authentication/authorization on file endpoints                                                                                                             
  - Any user can delete any file by ID                                                                                                                                 
  - user_id field exists but isn't enforced                                                                                                                            
  @router.delete("/{file_id}", ...)                                                                                                                                    
  async def delete_file(file_id: int, ...):                                                                                                                            
      # No check if user owns the file                                                                                                                                 
                                                                                                                                                                       
  3. Race condition in session cleanup (src/core/file_source_session.py:73-89)                                                                                         
  The lock is held during table load but _loaded_tables is a class variable shared across async contexts. If a table load fails mid-way, the set might be left         
  inconsistent.                                                                                                                                                        
                                                                                                                                                                       
  Medium Priority                                                                                                                                                      
                                                                                                                                                                       
  4. Missing input validation on sheet_name (src/core/file_source_session.py:131)                                                                                      
  sheet = sheet_name or 'Sheet1'                                                                                                                                       
  read_query = f"SELECT * FROM read_excel('{file_path}', sheet='{sheet}')"                                                                                             
  Sheet names should be sanitized to prevent injection.                                                                                                                
                                                                                                                                                                       
  5. No rate limiting on file uploads                                                                                                                                  
  Large file uploads could DOS the server. Consider adding rate limits or queuing.                                                                                     
                                                                                                                                                                       
  6. Migration downgrade loses data (alembic/versions/c22b240bc731_...py:67)                                                                                           
  The downgrade drops active_file_source_ids column, potentially losing data without warning.                                                                          
                                                                                                                                                                       
  Low Priority                                                                                                                                                         
                                                                                                                                                                       
  7. Duplicate code in response conversion (src/api/endpoints/files.py:32-56)                                                                                          
  _file_source_to_response duplicates schema conversion logic. Consider moving to the model.                                                                           
                                                                                                                                                                       
  8. Hardcoded 'Sheet1' fallback (src/core/file_source_session.py:131)                                                                                                 
  May fail for Excel files where first sheet has different name.                                                                                                       
                                                                                                                                                                       
  ---                                                                                                                                                                  
  🔍 Suggestions                                                                                                                                                       
                                                                                                                                                                       
  1. Add authorization middleware to file endpoints, checking user_id ownership                                                                                        
  2. Use parameterized paths where possible or add explicit path canonicalization:                                                                                     
  file_path = os.path.realpath(file_path)                                                                                                                              
  if not file_path.startswith(self.upload_dir):                                                                                                                        
      raise ValueError("Invalid file path")                                                                                                                            
                                                                                                                                                                       
  3. Add cleanup for failed uploads - partial files should be removed if processing fails                                                                              
  4. Consider background processing for large files instead of blocking the upload request                                                                             
  5. Add file source to API response types in frontend/src/types/api.ts for type safety                                                                                
                                                                                                                                                                       
  ---                                                                                                                                                                  
  📋 Checklist                                                                                                                                                         
  ┌───────────────────────┬───────────────────────────┐                                                                                                                
  │         Item          │          Status           │                                                                                                                
  ├───────────────────────┼───────────────────────────┤                                                                                                                
  │ Tests pass            │ ⏳ Not verified           │                                                                                                                
  ├───────────────────────┼───────────────────────────┤                                                                                                                
  │ Documentation updated │ ✅                        │                                                                                                                
  ├───────────────────────┼───────────────────────────┤                                                                                                                
  │ Migration reversible  │ ⚠️ Data loss on downgrade │                                                                                                                
  ├───────────────────────┼───────────────────────────┤                                                                                                                
  │ Security review       │ ⚠️ Injection concerns     │                                                                                                                
  ├───────────────────────┼───────────────────────────┤                                                                                                                
  │ Type hints            │ ✅                        │                                                                                                                
  └───────────────────────┴───────────────────────────┘                                                                                                                
  ---                                                                                                                                                                  
  Verdict                                                                                                                                                              
                                                                                                                                                                       
  Needs changes before merge. The feature is well-designed but has security gaps in SQL string building and missing authorization. Address the high-priority items     
  before merging.
  All 36 tests pass. Here's a summary of the fixes made:                                                                                                               
                                                                                                                                      
  Fixes Applied                                                                                                                                                                                                                                                                       
  1. SQL Injection Prevention (High Priority) ✅                                                                                                                       
                                                                                                                                   
  - src/core/file_source_session.py: Added _validate_file_path() and _sanitize_sheet_name() functions                                                                  
  - src/core/file_source_handler.py: Added same validation functions                                                                                                   
  - All DuckDB queries now use validated paths and sanitized sheet names                                                                                               
  - Path traversal attacks are blocked by checking paths stay within upload directory                                                                                  
                                                                                                                                                                       
  2. Race Condition Fix (High Priority) ✅                                                                                                                             
                                                                                                                          
  - src/core/file_source_session.py:ensure_table_loaded(): Now properly cleans up state if table loading fails                                                         
  - Partial tables are dropped, metadata is cleared before re-raising exception                                                                                        
  - Lock is held during entire operation to prevent concurrent issues                                                                                                  
                                                                                                                                                                       
  3. Failed Upload Cleanup (Medium Priority) ✅                                                                                                                        
                                                                                                                         
  - src/core/file_source_handler.py:process_upload(): Now deletes partial files when processing fails after file was saved                                             
                                                                                                                                                                       
  4. Migration Downgrade Warning (Low Priority) ✅                                                                                                                                                 
  - alembic/versions/c22b240bc731_...py: Added warning comment about data loss on downgrade                                                                                                   
  5. New Security Tests ✅                                                                                                                                                                  
  - tests/test_file_sources.py: Added 9 new tests for path validation and sheet name sanitization                                                                      
  - Tests verify path traversal blocking, SQL injection prevention, edge cases  

  Skipped                                        
  - Authorization checks on file endpoints - not implemented yet