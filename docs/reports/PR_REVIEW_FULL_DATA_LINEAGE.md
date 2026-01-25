  PR Review: Data Lineage System                                                                                                                      
                                                                                                                                                      
  Summary                                                                                                                                             
                                                                                                                                                      
  This PR introduces a comprehensive Data Lineage system with column-level tracking, schema change impact analysis, and query pattern analytics. The  
  implementation spans ~7,000 lines of new code across 47 files.                                                                                      
                                                                                                                                                      
  ---                                                                                                                                                 
  What Works Well ✅                                                                                                                                  
                                                                                                                                                      
  1. Solid Architecture                                                                                                                               
                                                                                                                                                      
  - Clean separation of concerns: sql_lineage_parser.py (parsing), impact_analyzer.py (analysis), query_pattern_analyzer.py (analytics)               
  - Follows existing codebase patterns (dataclasses, async/await, SQLAlchemy)                                                                         
  - Good use of enums for type safety (LineageNodeType, TransformationType, RiskLevel)                                                                
                                                                                                                                                      
  2. Robust SQL Parsing (sql_lineage_parser.py)                                                                                                       
                                                                                                                                                      
  - Leverages sqlparse library for production-grade SQL parsing                                                                                       
  - Handles complex scenarios well:                                                                                                                   
    - Multi-table JOINs with aliases                                                                                                                  
    - Subqueries in WHERE clauses (lines 287-331)                                                                                                     
    - Aggregations (COUNT, SUM, AVG, etc.)                                                                                                            
    - CASE expressions and function calls                                                                                                             
    - Schema-qualified names (public.orders → orders)                                                                                                 
  - Smart orphan table handling - tables used only in JOINs/WHERE get appropriate edges (lines 176-204)                                               
                                                                                                                                                      
  3. False Positive Prevention (impact_analyzer.py)                                                                                                   
                                                                                                                                                      
  - Word-boundary regex matching prevents substring false positives (line 217-225)                                                                    
  - _is_identifier_match() correctly handles: orders ≠ customer_orders ≠ orders_archive                                                               
  - ILIKE pre-filter + regex post-filter for performance + accuracy                                                                                   
                                                                                                                                                      
  4. Excellent Test Coverage                                                                                                                          
                                                                                                                                                      
  - 609 lines of parser tests with organized test classes                                                                                             
  - Tests for edge cases: empty SQL, malformed SQL, non-SELECT statements                                                                             
  - Dedicated TestFalsePositivePrevention class with substring trap tests                                                                             
  - Frontend tests with proper React Flow mocking                                                                                                     
                                                                                                                                                      
  5. Well-Designed Frontend                                                                                                                           
                                                                                                                                                      
  - 4-tab panel organization (Explore, History, Impact, Patterns)                                                                                     
  - React Flow integration with custom nodes/edges                                                                                                    
  - Node click highlighting for path tracing                                                                                                          
  - Responsive heatmap with 3 view modes (Frequency, Joins, Performance)                                                                              
  - Dark mode support throughout                                                                                                                      
                                                                                                                                                      
  6. Query Pattern Analytics (query_pattern_analyzer.py)                                                                                              
                                                                                                                                                      
  - Bottleneck scoring formula is sensible: (frequency / max_freq) * (avg_time / max_time)                                                            
  - Time range filtering (7/30/90 days)                                                                                                               
  - Per-connection scoping for multi-database setups                                                                                                  
  - Performance cap at 2000 queries                                                                                                                   
                                                                                                                                                      
  ---                                                                                                                                                 
  Issues & Improvements 🔧                                                                                                                            
                                                                                                                                                      
  High Priority                                                                                                                                       
                                                                                                                                                      
  1. Missing Index on connection_id                                                                                                                   
                                                                                                                                                      
  query_pattern_analyzer.py:327 filters by connection_id, but there's no database index:                                                              
  stmt = stmt.where(QueryHistory.connection_id == connection_id)                                                                                      
  Impact: Slow queries on large query_history tables.                                                                                                 
  Fix: Add migration to create index on QueryHistory.connection_id.                                                                                   
                                                                                                                                                      
  2. Module-Level Singleton Instances (lineage.py:47-49)                                                                                              
                                                                                                                                                      
  _parser = SQLLineageParser()                                                                                                                        
  _analyzer = ImpactAnalyzer()                                                                                                                        
  _pattern_analyzer = QueryPatternAnalyzer()                                                                                                          
  These are created at module import time, not request time. The SQLLineageParser has internal state (_node_counter) that gets reset per parse() call,
   so it's safe. However, this pattern prevents dependency injection for testing the API layer directly.                                              
                                                                                                                                                      
  Recommendation: Consider using FastAPI dependency injection like other endpoints.                                                                   
                                                                                                                                                      
  3. No Rate Limiting on Parse Endpoint                                                                                                               
                                                                                                                                                      
  POST /api/lineage/parse accepts arbitrary SQL and performs CPU-intensive parsing. A malicious user could DoS with complex queries.                  
                                                                                                                                                      
  Fix: Add request rate limiting or SQL size limits.                                                                                                  
                                                                                                                                                      
  Medium Priority                                                                                                                                     
                                                                                                                                                      
  4. UTC Datetime Issue (query_pattern_analyzer.py:330)                                                                                               
                                                                                                                                                      
  cutoff = datetime.utcnow() - timedelta(days=time_range_days)                                                                                        
  datetime.utcnow() is deprecated. Use datetime.now(timezone.utc) instead.                                                                            
                                                                                                                                                      
  5. Hardcoded Limit in Stats (impact_analyzer.py:214)                                                                                                
                                                                                                                                                      
  return {..., "tables": sorted(tables_referenced)[:50]}                                                                                              
  The 50-table limit should be configurable or documented.                                                                                            
                                                                                                                                                      
  6. Missing Error Boundary in Frontend                                                                                                               
                                                                                                                                                      
  LineageGraph.tsx catches parse errors but if the graph rendering fails (e.g., malformed node data), the entire component crashes.                   
                                                                                                                                                      
  Fix: Wrap React Flow in an error boundary.                                                                                                          
                                                                                                                                                      
  7. Potential Memory Issue with Large Graphs                                                                                                         
                                                                                                                                                      
  layoutLineageGraph (in lineageLayoutUtils.ts) creates full graph copies. For queries with 100+ columns, this could be expensive.                    
                                                                                                                                                      
  Low Priority                                                                                                                                        
                                                                                                                                                      
  8. Magic Numbers (impact_analyzer.py:303-308)                                                                                                       
                                                                                                                                                      
  if affected_count > 20:                                                                                                                             
      return RiskLevel.HIGH.value                                                                                                                     
  elif affected_count >= 5:                                                                                                                           
      return RiskLevel.MEDIUM.value                                                                                                                   
  These thresholds should be constants or configurable.                                                                                               
                                                                                                                                                      
  9. Inconsistent Limit Handling                                                                                                                      
                                                                                                                                                      
  - impact_analyzer.py:248 over-fetches with limit * 2                                                                                                
  - query_pattern_analyzer.py:333 uses MAX_QUERIES = 2000                                                                                             
                                                                                                                                                      
  Consider a unified configuration for limits.                                                                                                        
                                                                                                                                                      
  10. TypeScript Type Assertion (QueryPatternHeatmap.tsx:78)                                                                                          
                                                                                                                                                      
  const isDark = document.documentElement.classList.contains('dark');                                                                                 
  This doesn't react to dark mode changes. Should use the useDarkMode hook like LineageGraph.tsx.                                                     
                                                                                                                                                      
  ---                                                                                                                                                 
  Code Quality Notes                                                                                                                                  
                                                                                                                                                      
  Positives                                                                                                                                           
                                                                                                                                                      
  - Good docstrings throughout                                                                                                                        
  - Consistent error handling with logging                                                                                                            
  - Type hints used consistently in Python                                                                                                            
  - TypeScript interfaces match backend schemas exactly                                                                                               
                                                                                                                                                      
  Minor Style Issues                                                                                                                                  
                                                                                                                                                      
  - Some methods are quite long (_process_select_item is 120+ lines) - could be broken up                                                             
  - Mix of single and double quotes in SQL strings (cosmetic)                                                                                         
                                                                                                                                                      
  ---                                                                                                                                                 
  Future Directions 🚀                                                                                                                                
                                                                                                                                                      
  1. Lineage Persistence                                                                                                                              
                                                                                                                                                      
  Currently lineage is computed on-demand. For frequently accessed queries, consider:                                                                 
  - Caching lineage graphs in Redis                                                                                                                   
  - Storing lineage in a dedicated query_lineage table                                                                                                
                                                                                                                                                      
  2. Cross-Query Lineage                                                                                                                              
                                                                                                                                                      
  Track data flow across multiple queries in a session:                                                                                               
  - Query A creates temp table → Query B reads it                                                                                                     
  - Track ETL-style workflows                                                                                                                         
                                                                                                                                                      
  3. Schema Change Simulation                                                                                                                         
                                                                                                                                                      
  Before impact analysis, let users simulate:                                                                                                         
  - "What if I rename email to email_address?"                                                                                                        
  - Auto-generate migration scripts                                                                                                                   
                                                                                                                                                      
  4. Visual Diff for Schema Changes                                                                                                                   
                                                                                                                                                      
  Highlight what would break in the lineage graph when a column is modified.                                                                          
                                                                                                                                                      
  5. Integration with ER Diagram                                                                                                                      
                                                                                                                                                      
  The codebase has ERDiagram.tsx - could overlay lineage paths on the ER diagram for visual schema exploration.                                       
                                                                                                                                                      
  6. Export Capabilities                                                                                                                              
                                                                                                                                                      
  - Export lineage graph as PNG/SVG                                                                                                                   
  - Export impact analysis as CSV for documentation                                                                                                   
                                                                                                                                                      
  7. Real-Time Lineage Tracking                                                                                                                       
                                                                                                                                                      
  Hook into query execution to automatically build lineage graphs as queries run.                                                                     
                                                                                                                                                      
  ---                                                                                                                                                 
  Testing Recommendations                                                                                                                             
                                                                                                                                                      
  The test coverage is good, but consider adding:                                                                                                     
  1. Integration tests - API → Parser → Database round-trip                                                                                           
  2. Performance tests - Parse time for complex 50-table JOINs                                                                                        
  3. Concurrency tests - Multiple simultaneous parse requests                                                                                         
                                                                                                                                                      
  ---                                                                                                                                                 
  Verdict                                                                                                                                             
                                                                                                                                                      
  Approve with minor changes. This is a well-implemented feature with solid architecture and good test coverage. The identified issues are mostly     
  performance optimizations and code hygiene rather than correctness problems. The false-positive prevention in impact analysis is particularly well  
  done.                                                                                                                                               
                                                                                                                                                      
  Suggested merge checklist:                                                                                                                          
  - Add database index on QueryHistory.connection_id                                                                                                  
  - Fix datetime.utcnow() deprecation                                                                                                                 
  - Add SQL size limit to parse endpoint                                                                                                              
  - Use useDarkMode hook in QueryPatternHeatmap.tsx  