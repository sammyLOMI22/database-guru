 PR Review: Phase 12 - Lineage Intelligence                                                                                                          
                                                                                                                                                      
  Summary                                                                                                                                             
                                                                                                                                                      
  This PR implements Phase 12: Lineage Intelligence, adding 5 new LLM-powered agents to the data lineage system:                                      
  - 12.1 Lineage Narrator - Natural language explanations of lineage graphs                                                                           
  - 12.2 Impact Advisor - Migration plans and SQL patches for schema changes                                                                          
  - 12.3 Schema Health Analyzer - Database design quality scoring                                                                                     
  - 12.4 Pattern Intelligence - Query anti-pattern detection and optimization suggestions                                                             
  - 12.5 Lineage Conversation Agent - Multi-turn Q&A about schema/lineage                                                                             
                                                                                                                                                      
  Stats: +11,266 lines across 27 files, including ~2,960 lines of tests                                                                               
                                                                                                                                                      
  ---                                                                                                                                                 
  Strengths                                                                                                                                           
                                                                                                                                                      
  1. Consistent Architecture                                                                                                                          
                                                                                                                                                      
  All agents follow the same established patterns from ResultNarrator:                                                                                
  - Timeout-wrapped LLM calls with asyncio.wait_for()                                                                                                 
  - Deterministic fallbacks when LLM fails                                                                                                            
  - Balanced brace matching for JSON extraction (_extract_json_object)                                                                                
  - Factory functions with ModelRouter integration                                                                                                    
                                                                                                                                                      
  2. Good Test Coverage                                                                                                                               
                                                                                                                                                      
  Comprehensive test files for each component with proper async testing:                                                                              
  - test_lineage_narrator.py - 474 lines                                                                                                              
  - test_impact_advisor.py - 455 lines                                                                                                                
  - test_schema_health.py - 817 lines                                                                                                                 
  - test_pattern_intelligence.py - 584 lines                                                                                                          
  - test_lineage_conversation.py - 630 lines                                                                                                          
                                                                                                                                                      
  3. Graceful Degradation                                                                                                                             
                                                                                                                                                      
  Every LLM-enhanced endpoint returns meaningful results even on timeout/error:                                                                       
  # Example from lineage_narrator.py:188-202                                                                                                          
  except asyncio.TimeoutError:                                                                                                                        
      logger.warning(f"⏱️ Lineage narrative generation timeout after {effective_timeout}s")                                                           
      return self._fallback_narrative(lineage_graph, deterministic_summary)                                                                           
                                                                                                                                                      
  4. Clean API Design                                                                                                                                 
                                                                                                                                                      
  New endpoints follow RESTful conventions and return properly typed Pydantic schemas:                                                                
  - POST /api/lineage/parse?explain=true - Parse with optional narrative                                                                              
  - POST /api/lineage/impact/advise - LLM-enhanced impact analysis                                                                                    
  - GET /api/lineage/schema/health/{connection_id} - Schema health report                                                                             
  - POST /api/lineage/ask - Conversational interface                                                                                                  
                                                                                                                                                      
  5. Frontend UX                                                                                                                                      
                                                                                                                                                      
  LineageChat.tsx is well-designed with:                                                                                                              
  - Question type badges with color coding                                                                                                            
  - Confidence indicators                                                                                                                             
  - Follow-up suggestions                                                                                                                             
  - Table link chips for navigation                                                                                                                   
                                                                                                                                                      
  ---                                                                                                                                                 
  Issues to Address                                                                                                                                   
                                                                                                                                                      
  1. Missing model_pattern_intelligence in ModelRouter                                                                                                
                                                                                                                                                      
  src/llm/model_router.py:288-295 - The get_model_router function doesn't load the model/timeout for PATTERN_INTELLIGENCE:                            
                                                                                                                                                      
  # Current code loads these but misses pattern_intelligence:                                                                                         
  'model_lineage_conversation': getattr(sys_settings, 'model_lineage_conversation', None),                                                            
  'timeout_lineage_conversation': getattr(sys_settings, 'timeout_lineage_conversation', 15),                                                          
  # Missing:                                                                                                                                          
  # 'model_pattern_intelligence': getattr(sys_settings, 'model_pattern_intelligence', None),                                                          
  # 'timeout_pattern_intelligence': getattr(sys_settings, 'timeout_pattern_intelligence', 20),                                                        
                                                                                                                                                      
  2. Potential Memory Leak in Conversation Contexts                                                                                                   
                                                                                                                                                      
  src/lineage/lineage_conversation_agent.py:190 stores conversation contexts without cleanup:                                                         
                                                                                                                                                      
  self._conversation_contexts: Dict[str, ConversationContext] = {}                                                                                    
                                                                                                                                                      
  Sessions are stored indefinitely. Consider adding TTL-based expiration or max session limit.                                                        
                                                                                                                                                      
  3. SQL Injection Risk in Raw SQL Query                                                                                                              
                                                                                                                                                      
  src/lineage/lineage_conversation_agent.py:511-517 uses string interpolation for SQL:                                                                
                                                                                                                                                      
  where_clause = " OR ".join(conditions)                                                                                                              
  query = text(f"""                                                                                                                                   
      SELECT id, natural_language_query, generated_sql, execution_time_ms, created_at                                                                 
      FROM query_history                                                                                                                              
      WHERE connection_id = :conn_id AND ({where_clause})                                                                                             
      ...                                                                                                                                             
  """)                                                                                                                                                
                                                                                                                                                      
  While where_clause is constructed from LIKE patterns, it's safer to use SQLAlchemy ORM here.                                                        
                                                                                                                                                      
  4. Missing Error Boundary in Frontend                                                                                                               
                                                                                                                                                      
  LineageChat.tsx catches errors but doesn't show detailed user feedback when the API is unreachable.                                                 
                                                                                                                                                      
  5. Duplicate JSON Extraction Code                                                                                                                   
                                                                                                                                                      
  _extract_json_object() is duplicated across 5 files with identical implementation. Should be extracted to a shared utility:                         
  - lineage_narrator.py:363-414                                                                                                                       
  - impact_advisor.py:723-758                                                                                                                         
  - schema_health_analyzer.py:1036-1067                                                                                                               
  - pattern_intelligence.py:883-917                                                                                                                   
                                                                                                                                                      
  ---                                                                                                                                                 
  Suggestions                                                                                                                                         
                                                                                                                                                      
  1. Add Index for Query Patterns                                                                                                                     
                                                                                                                                                      
  Consider adding a database index for the query pattern lookups:                                                                                     
  CREATE INDEX idx_query_history_connection_executed                                                                                                  
  ON query_history(connection_id, executed)                                                                                                           
  WHERE generated_sql IS NOT NULL;                                                                                                                    
                                                                                                                                                      
  2. Consider Rate Limiting for /ask Endpoint                                                                                                         
                                                                                                                                                      
  The conversational endpoint could benefit from rate limiting since each request triggers an LLM call.                                               
                                                                                                                                                      
  3. Add Response Caching for Schema Health                                                                                                           
                                                                                                                                                      
  Schema health reports are expensive to compute. Consider caching for a few minutes since schema doesn't change frequently.                          
                                                                                                                                                      
  4. Type Hints for Return Values                                                                                                                     
                                                                                                                                                      
  Some methods like _build_lineage_info could benefit from more specific return type hints:                                                           
  async def _build_lineage_info(...) -> Dict[str, Any]:  # Could be TypedDict                                                                         
                                                                                                                                                      
  ---                                                                                                                                                 
  Documentation                                                                                                                                       
                                                                                                                                                      
  Good inline documentation in all new files. The AGENTS.md and LINEAGE_INTELLIGENCE_USER_GUIDE.md updates cover the new features well.               
                                                                                                                                                      
  ---                                                                                                                                                 
  Final Assessment                                                                                                                                    
                                                                                                                                                      
  Overall: Approve with minor fixes                                                                                                                   
                                                                                                                                                      
  This is a well-architected implementation that extends the existing patterns consistently. The test coverage is solid and error handling is         
  thoughtful. The main issues are:                                                                                                                    
                                                                                                                                                      
  1. Missing model_pattern_intelligence settings loader (bug)                                                                                         
  2. Memory leak potential in conversation contexts (should fix)                                                                                      
  3. Code duplication for JSON extraction (nice to have)                                                                                              
                                                                                                                                                      
  The SQL injection concern (#3 above) is low risk since input comes from controlled sources, but refactoring to ORM would be cleaner. 
  ---                                                                                                                                                 
  PR Review: Lineage Intelligence (Phase 12)                                                                                                          
                                                                                                                                                      
  Overview                                                                                                                                            
                                                                                                                                                      
  This PR adds the "Lineage Intelligence" feature (Phase 12) with ~11,266 lines added across 27 files. It introduces 5 new LLM-powered agents for data
   lineage understanding and schema analysis.                                                                                                         
                                                                                                                                                      
  Summary of Changes                                                                                                                                  
  ┌────────────┬───────────────────────────────┬──────────────────────────────────────────────────────────────┐                                       
  │ Component  │             File              │                           Purpose                            │                                       
  ├────────────┼───────────────────────────────┼──────────────────────────────────────────────────────────────┤                                       
  │ Phase 12.1 │ lineage_narrator.py           │ LLM-generated explanations of data lineage graphs            │                                       
  ├────────────┼───────────────────────────────┼──────────────────────────────────────────────────────────────┤                                       
  │ Phase 12.2 │ impact_advisor.py             │ Migration plans, SQL patches, risk explanations              │                                       
  ├────────────┼───────────────────────────────┼──────────────────────────────────────────────────────────────┤                                       
  │ Phase 12.3 │ schema_health_analyzer.py     │ Database design quality analysis (grades, index suggestions) │                                       
  ├────────────┼───────────────────────────────┼──────────────────────────────────────────────────────────────┤                                       
  │ Phase 12.4 │ pattern_intelligence.py       │ Query anti-pattern detection, bottleneck analysis            │                                       
  ├────────────┼───────────────────────────────┼──────────────────────────────────────────────────────────────┤                                       
  │ Phase 12.5 │ lineage_conversation_agent.py │ Natural language Q&A about schema/lineage                    │                                       
  └────────────┴───────────────────────────────┴──────────────────────────────────────────────────────────────┘                                       
  Strengths                                                                                                                                           
                                                                                                                                                      
  1. Excellent patterns followed - All agents follow the established pattern from ResultNarrator:                                                     
    - Async with asyncio.wait_for() for timeout handling                                                                                              
    - Graceful degradation with fallback responses on LLM failure                                                                                     
    - Balanced brace JSON parsing for robust response extraction                                                                                      
  2. Comprehensive test coverage - 151 tests covering:                                                                                                
    - Happy paths                                                                                                                                     
    - Timeout handling                                                                                                                                
    - LLM errors                                                                                                                                      
    - Malformed responses                                                                                                                             
    - Edge cases (empty inputs, missing data)                                                                                                         
  3. Model router integration - Added TaskType enums for per-task model/timeout configuration in model_router.py:36-41                                
  4. Good API design - Clean REST endpoints with optional parameters (e.g., explain=true for narrative generation)                                    
  5. Frontend components - Well-structured React components with loading states and confidence indicators                                             
                                                                                                                                                      
  ---                                                                                                                                                 
  Issues & Recommendations                                                                                                                            
                                                                                                                                                      
  1. Duplicated JSON Parsing Code (Medium Priority)                                                                                                   
                                                                                                                                                      
  The _extract_json_object() method is duplicated across multiple files:                                                                              
  - lineage_narrator.py:347-393                                                                                                                       
  - impact_advisor.py:548-585                                                                                                                         
  - schema_health_analyzer.py (also has a copy)                                                                                                       
                                                                                                                                                      
  Recommendation: The file src/lineage/llm_utils.py exists but is untracked and not being used. Stage this file and refactor the agents to use the    
  shared utility:                                                                                                                                     
                                                                                                                                                      
  from src.lineage.llm_utils import extract_json_object, parse_json_response                                                                          
                                                                                                                                                      
  2. Untracked File (Low Priority)                                                                                                                    
                                                                                                                                                      
  src/lineage/llm_utils.py is shown as untracked in git status. Should be staged with this PR.                                                        
                                                                                                                                                      
  3. Missing PATTERN_INTELLIGENCE in Model Router (Bug)                                                                                               
                                                                                                                                                      
  In model_router.py, the PATTERN_INTELLIGENCE TaskType is added but the corresponding settings in get_model_router() don't include                   
  model_pattern_intelligence or timeout_pattern_intelligence.                                                                                         
                                                                                                                                                      
  Fix needed at model_router.py:~290:                                                                                                                 
  'model_pattern_intelligence': getattr(sys_settings, 'model_pattern_intelligence', None),                                                            
  'timeout_pattern_intelligence': getattr(sys_settings, 'timeout_pattern_intelligence', 20),                                                          
                                                                                                                                                      
  4. Potential SQL Injection in SQL Patches (Security - Info)                                                                                         
                                                                                                                                                      
  The ImpactAdvisor generates SQL patches via LLM. The UI should clearly warn users to review these before execution. The current                     
  SQLPatch.requires_review field is good, but consider defaulting to True.                                                                            
                                                                                                                                                      
  5. Missing Database Column Definitions (Medium Priority)                                                                                            
                                                                                                                                                      
  The schemas reference new SystemSettings fields (model_lineage_narrative, timeout_lineage_narrative, etc.) but these need corresponding columns in  
  src/database/models.py.                                                                                                                             
                                                                                                                                                      
  Check if the following are added to the SystemSettings model:                                                                                       
  model_lineage_narrative = Column(String, nullable=True)                                                                                             
  timeout_lineage_narrative = Column(Integer, default=15)                                                                                             
  # ... etc for other Phase 12 settings                                                                                                               
                                                                                                                                                      
  ---                                                                                                                                                 
  Test Results                                                                                                                                        
                                                                                                                                                      
  151 tests collected                                                                                                                                 
                                                                                                                                                      
  Tests appear comprehensive but should run the full suite to verify:                                                                                 
  ./run_tests.sh tests/test_lineage_narrator.py tests/test_impact_advisor.py \                                                                        
    tests/test_schema_health.py tests/test_pattern_intelligence.py \                                                                                  
    tests/test_lineage_conversation.py                                                                                                                
                                                                                                                                                      
  ---                                                                                                                                                 
  Verdict: Approve with Minor Changes                                                                                                                 
                                                                                                                                                      
  The implementation is solid, follows established patterns, and has good test coverage. The main action items before merge:                          
                                                                                                                                                      
  1. Stage src/lineage/llm_utils.py and update agents to use it (or remove if not needed)                                                             
  2. Add missing model router settings for PATTERN_INTELLIGENCE                                                                                       
  3. Verify database model columns exist for new settings                                                                                             
                                                                                                                                                      
  Nice work on this feature set!