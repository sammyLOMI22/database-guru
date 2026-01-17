Data Lineage & Impact Analysis - Phase 11 Implementation Plan

 Feature: Data Lineage & Impact Analysis + ER Extensions
 Branch: data-lineage
 Priority: MEDIUM
 Estimated Effort: ~3,500 lines | 6-8 days
 Prerequisite: Phase 7 ER Diagrams Core (COMPLETE)

 Note: This implementation includes relevant ER Diagram extensions (Query Path Overlay, Table Statistics) that integrate naturally with Data 
 Lineage.

 ---
 1. Overview

 Purpose

 Visualize how data flows through queries and transformations, enabling impact analysis before schema changes. Users can understand:
 - Query Lineage: Which source tables/columns flow to which result columns
 - Column-Level Tracking: Trace individual columns through JOINs, aggregations, transformations
 - Impact Analysis: "What breaks if I rename/drop this column?"
 - Query Pattern Analytics: Usage heatmaps, common JOINs, performance bottlenecks

 User Stories

 1. As a DBA, I want to see which queries use a specific column before I modify it
 2. As a developer, I want to visualize how data flows from source tables to my query results
 3. As a data engineer, I want to identify frequently-joined tables for optimization
 4. As a team lead, I want to understand query patterns across my team's usage

 ---
 2. Architecture

 Data Flow

 User selects a query or asks "What uses orders.total?"
     │
     ▼
 LineageAPI (new endpoint)
     │
     ├──► SQLLineageParser (parse SQL → lineage graph)
     │              │
     │              ▼
     │    Extract: source_tables, columns, transformations
     │
     ├──► ImpactAnalyzer (scan query_history for usage)
     │              │
     │              ▼
     │    Find queries referencing target table/column
     │
     └──► QueryPatternAnalyzer (aggregate usage stats)
                │
                ▼
          Heatmap data, common JOINs, bottlenecks
                │
                ▼
 Frontend (React Flow-based visualization)
     │
     ├──► LineageGraph (directed graph view)
     ├──► ColumnLineage (column-level tracing)
     ├──► ImpactAnalysisPanel (affected queries list)
     └──► QueryPatternHeatmap (usage visualization)

 Reusable Infrastructure

 - React Flow - Already used in ER Diagrams (Phase 7)
 - Dagre Layout - Already in erDiagramUtils.ts
 - sqlparse - Already used in multi_db_query_validator.py
 - QueryHistory model - Stores all executed queries
 - ChatMessage.databases_used - Tracks tables used per query

 ---
 3. Backend Implementation

 3.1 SQL Lineage Parser (src/core/sql_lineage_parser.py)

 Purpose: Parse SQL and extract lineage information (source tables → transformations → result columns)

 Key Functions:
 class SQLLineageParser:
     def parse_query(self, sql: str) -> QueryLineage:
         """Parse SQL and return lineage graph."""

     def extract_source_columns(self, sql: str) -> Dict[str, List[str]]:
         """Extract {table: [columns]} from SELECT/JOIN/WHERE."""

     def extract_transformations(self, sql: str) -> List[ColumnTransformation]:
         """Detect SUM(), CONCAT(), CASE, aliases, etc."""

     def build_lineage_graph(self, sql: str) -> LineageGraph:
         """Build full lineage from sources to results."""

 Reuse Pattern: Extend _extract_tables_from_statement() and _extract_columns_from_statement() from multi_db_query_validator.py.

 Lines: ~350

 3.2 Impact Analyzer (src/core/impact_analyzer.py)

 Purpose: Scan query history to find queries affected by schema changes

 Key Functions:
 class ImpactAnalyzer:
     async def analyze_column_impact(
         self,
         table: str,
         column: str,
         db_session: AsyncSession
     ) -> ImpactReport:
         """Find all queries using this column."""

     async def analyze_table_impact(
         self,
         table: str,
         db_session: AsyncSession
     ) -> ImpactReport:
         """Find all queries referencing this table."""

     def calculate_risk_level(self, affected_queries: int) -> RiskLevel:
         """Determine risk: LOW (<5), MEDIUM (5-20), HIGH (>20)."""

 Lines: ~250

 3.3 Query Pattern Analyzer (src/core/query_pattern_analyzer.py)

 Purpose: Aggregate query patterns for heatmaps and insights

 Key Functions:
 class QueryPatternAnalyzer:
     async def get_table_usage_frequency(
         self,
         connection_id: int,
         db_session: AsyncSession
     ) -> Dict[str, int]:
         """Count queries per table."""

     async def get_common_join_patterns(
         self,
         connection_id: int,
         db_session: AsyncSession
     ) -> List[JoinPattern]:
         """Find most common table JOIN combinations."""

     async def identify_bottlenecks(
         self,
         connection_id: int,
         db_session: AsyncSession
     ) -> List[PerformanceBottleneck]:
         """Find large tables frequently joined."""

 Lines: ~200

 3.4 Lineage API Endpoint (src/api/endpoints/lineage.py)

 Purpose: REST API for lineage and impact analysis

 Endpoints:
 ┌────────┬───────────────────────────────────────┬────────────────────────────────────┐
 │ Method │                 Path                  │            Description             │
 ├────────┼───────────────────────────────────────┼────────────────────────────────────┤
 │ GET    │ /api/lineage/query/{query_id}         │ Get lineage for a specific query   │
 ├────────┼───────────────────────────────────────┼────────────────────────────────────┤
 │ POST   │ /api/lineage/parse                    │ Parse SQL and return lineage graph │
 ├────────┼───────────────────────────────────────┼────────────────────────────────────┤
 │ POST   │ /api/lineage/impact                   │ Analyze impact of schema change    │
 ├────────┼───────────────────────────────────────┼────────────────────────────────────┤
 │ GET    │ /api/lineage/patterns/{connection_id} │ Get query pattern analytics        │
 ├────────┼───────────────────────────────────────┼────────────────────────────────────┤
 │ GET    │ /api/lineage/heatmap/{connection_id}  │ Get table usage heatmap data       │
 └────────┴───────────────────────────────────────┴────────────────────────────────────┘
 Lines: ~200

 ---
 4. Frontend Implementation

 4.1 Types (frontend/src/types/lineage.ts)

 // Lineage node types
 interface LineageNodeData {
   type: 'source_table' | 'result_column' | 'transformation';
   name: string;
   columns?: string[];
   transformation?: string; // e.g., "SUM", "CONCAT"
   tableName?: string;
   connectionId?: number;
 }

 // Lineage edge for column flow
 interface LineageEdgeData {
   sourceColumn: string;
   targetColumn: string;
   transformationType?: string;
 }

 // Impact analysis result
 interface ImpactReport {
   affectedQueries: QuerySummary[];
   riskLevel: 'low' | 'medium' | 'high';
   queryTypes: { select: number; aggregate: number; join: number };
   sampleQueries: string[];
 }

 // Query pattern data
 interface TableUsage {
   tableName: string;
   queryCount: number;
   lastUsed: string;
 }

 Lines: ~120

 4.2 LineageGraph Component (frontend/src/components/lineage/LineageGraph.tsx)

 Purpose: Main visualization showing data flow from sources to results

 Features:
 - Source table nodes (left) → Transformation nodes (middle) → Result columns (right)
 - Animated edges showing data flow direction
 - Click node to highlight connected paths
 - Zoom/pan controls (reuse from ER Diagram)
 - Layout: Left-to-right Dagre

 Reuse: calculateDagreLayout(), useDarkMode, React Flow setup from ERDiagram.tsx

 Lines: ~300

 4.3 ColumnLineage Component (frontend/src/components/lineage/ColumnLineage.tsx)

 Purpose: Detailed column-level tracing view

 Features:
 - Table showing: Source Column → Transformation → Result Column
 - Expandable rows for complex transformations
 - Filter by table or column name
 - Export as CSV

 Lines: ~250

 4.4 ImpactAnalysisPanel Component (frontend/src/components/lineage/ImpactAnalysisPanel.tsx)

 Purpose: Show queries affected by a schema change

 Features:
 - Input: Table/column name to analyze
 - Risk level badge (LOW/MEDIUM/HIGH with color)
 - List of affected queries with SQL preview
 - Group by query type (SELECT, aggregations, JOINs)
 - "Export Report" button

 Lines: ~200

 4.5 QueryPatternHeatmap Component (frontend/src/components/lineage/QueryPatternHeatmap.tsx)

 Purpose: Visual heatmap of table usage frequency

 Features:
 - Grid of tables colored by usage frequency
 - Click table to see query list
 - Toggle: by query count, by JOIN frequency, by performance
 - Time range filter (7d, 30d, 90d, all)
 - Scope toggle: "Per Connection" (default) vs "All Connections" dropdown
 - Cross-connection view shows which tables are queried across multiple DBs

 Lines: ~220

 4.6 SQL Lineage Parser Utility (frontend/src/utils/sqlLineageParser.ts)

 Purpose: Client-side SQL parsing for instant lineage preview

 Features:
 - Parse SQL using sql-parser-cst library
 - Extract source tables and columns
 - Identify transformations (SUM, COUNT, CASE, etc.)
 - Build lineage graph data structure

 Lines: ~350

 4.7 Lineage API Service (frontend/src/services/lineageApi.ts)

 Purpose: API client for lineage endpoints

 Lines: ~100

 ---
 5. ER Diagram Extensions (Parallel Implementation)

 These extensions integrate naturally with Data Lineage and will be built alongside:

 5.1 Query Path Overlay (frontend/src/components/schema/QueryPathOverlay.tsx)

 Purpose: Highlight tables/relationships used by the current query on ER diagram

 Features:
 - Parse SQL to identify referenced tables
 - Highlight used tables with glow effect
 - Animate JOIN edges with data flow direction
 - Dim unused tables for context
 - Toggle on/off in ERDiagram controls

 Integration: Shares SQL parsing logic with sqlLineageParser.ts

 Lines: ~150

 5.2 Table Statistics Overlay (frontend/src/components/schema/TableStatsNode.tsx)

 Purpose: Show row counts and size on table nodes

 Features:
 - Fetch row counts via new GET /api/schema/stats/{connection_id} endpoint
 - Display: row count, estimated size, last query time
 - Badge on table header with expandable details
 - Cache stats with 5-minute TTL

 Backend: New src/api/endpoints/table_stats.py (~100 lines)

 Lines: ~180

 5.3 Schema Health Indicators (Optional - Time Permitting)

 - Missing PK detection
 - Orphaned FK warnings
 - Circular reference detection

 ---
 6. Integration Points

 6.1 App.tsx Changes

 - Add "Lineage" as new main tab (6th tab)
 - Route: /lineage
 - Color scheme: Indigo (#6366F1)

 6.2 QueryResults Integration

 - Add "View Lineage" button to query results
 - Opens LineageGraph for current query

 6.3 ERDiagram Integration

 - Add "Impact Analysis" context menu on table right-click
 - Opens ImpactAnalysisPanel for selected table
 - Query Path Overlay toggle in controls

 6.4 Schema Tab Integration

 - Add "Analyze Impact" button in Schema explorer
 - Opens panel for column-level impact analysis
 - Table Statistics toggle in controls

 ---
 7. Database Changes

 7.1 New Indexes (Performance)

 Add indexes to query_history for impact analysis queries:

 CREATE INDEX idx_query_history_generated_sql_gin
 ON query_history USING gin (to_tsvector('english', generated_sql));

 CREATE INDEX idx_query_history_connection_created
 ON query_history (database_type, created_at);

 7.2 Lineage Cache Table (Hybrid LRU)

 Cache parsed lineage after second access:

 class QueryLineageCache(Base):
     __tablename__ = "query_lineage_cache"

     id = Column(Integer, primary_key=True)
     query_history_id = Column(Integer, ForeignKey("query_history.id"), unique=True)
     lineage_data = Column(JSON)  # Cached lineage graph
     access_count = Column(Integer, default=1)  # Track access frequency
     created_at = Column(DateTime, default=datetime.utcnow)
     last_accessed_at = Column(DateTime, default=datetime.utcnow)

     # Auto-evict entries not accessed in 7 days
     __table_args__ = (
         Index('idx_lineage_last_accessed', 'last_accessed_at'),
     )

 Cache Strategy:
 - First access: Parse on-demand, increment counter
 - Second access: Parse and cache, return result
 - Subsequent: Return cached, update last_accessed_at
 - Background job: Evict entries older than 7 days

 ---
 8. Implementation Phases

 Phase 11.1: Backend Core (Day 1-2)

 - Create sql_lineage_parser.py with basic parsing
 - Create impact_analyzer.py with query scanning
 - Create lineage.py API endpoints
 - Create table_stats.py API endpoint
 - Add backend tests

 Phase 11.2: Frontend Core (Day 2-3)

 - Create types/lineage.ts
 - Create LineageGraph.tsx with React Flow
 - Create lineageApi.ts service
 - Add "Lineage" tab to App.tsx

 Phase 11.3: Column Lineage & Impact (Day 3-4)

 - Create ColumnLineage.tsx component
 - Create ImpactAnalysisPanel.tsx component
 - Integrate with QueryResults and Schema tabs
 - Add frontend tests

 Phase 11.4: ER Extensions (Day 4-5)

 - Create QueryPathOverlay.tsx component
 - Create TableStatsNode.tsx extended node
 - Integrate overlay toggle in ERDiagramControls
 - Share SQL parsing between lineage and overlay

 Phase 11.5: Query Analytics (Day 5-6)

 - Create query_pattern_analyzer.py
 - Create QueryPatternHeatmap.tsx
 - Add time range filtering
 - Add scope toggle (per-connection/cross-connection)

 Phase 11.6: Polish & Testing (Day 6-8)

 - End-to-end testing
 - Performance testing with large query history
 - UI/UX refinement
 - Documentation

 ---
 9. Files Summary

 New Files
 ┌─────────────────────────────────────────────────────────┬──────────────────────────────────┬────────────┐
 │                          File                           │             Purpose              │ Est. Lines │
 ├─────────────────────────────────────────────────────────┼──────────────────────────────────┼────────────┤
 │ src/core/sql_lineage_parser.py                          │ Parse SQL for lineage extraction │ ~350       │
 ├─────────────────────────────────────────────────────────┼──────────────────────────────────┼────────────┤
 │ src/core/impact_analyzer.py                             │ Scan history for impact analysis │ ~250       │
 ├─────────────────────────────────────────────────────────┼──────────────────────────────────┼────────────┤
 │ src/core/query_pattern_analyzer.py                      │ Aggregate query patterns         │ ~200       │
 ├─────────────────────────────────────────────────────────┼──────────────────────────────────┼────────────┤
 │ src/api/endpoints/lineage.py                            │ REST API endpoints               │ ~200       │
 ├─────────────────────────────────────────────────────────┼──────────────────────────────────┼────────────┤
 │ frontend/src/types/lineage.ts                           │ TypeScript types                 │ ~120       │
 ├─────────────────────────────────────────────────────────┼──────────────────────────────────┼────────────┤
 │ frontend/src/components/lineage/LineageGraph.tsx        │ Main lineage visualization       │ ~300       │
 ├─────────────────────────────────────────────────────────┼──────────────────────────────────┼────────────┤
 │ frontend/src/components/lineage/ColumnLineage.tsx       │ Column-level tracing             │ ~250       │
 ├─────────────────────────────────────────────────────────┼──────────────────────────────────┼────────────┤
 │ frontend/src/components/lineage/ImpactAnalysisPanel.tsx │ Impact preview panel             │ ~200       │
 ├─────────────────────────────────────────────────────────┼──────────────────────────────────┼────────────┤
 │ frontend/src/components/lineage/QueryPatternHeatmap.tsx │ Usage heatmap with scope toggle  │ ~220       │
 ├─────────────────────────────────────────────────────────┼──────────────────────────────────┼────────────┤
 │ frontend/src/utils/sqlLineageParser.ts                  │ Client-side SQL parsing          │ ~350       │
 ├─────────────────────────────────────────────────────────┼──────────────────────────────────┼────────────┤
 │ frontend/src/services/lineageApi.ts                     │ API client                       │ ~100       │
 ├─────────────────────────────────────────────────────────┼──────────────────────────────────┼────────────┤
 │ tests/test_sql_lineage_parser.py                        │ Backend lineage tests            │ ~200       │
 ├─────────────────────────────────────────────────────────┼──────────────────────────────────┼────────────┤
 │ tests/test_impact_analyzer.py                           │ Backend impact tests             │ ~150       │
 ├─────────────────────────────────────────────────────────┼──────────────────────────────────┼────────────┤
 │ frontend/tests/LineageGraph.test.tsx                    │ Frontend tests                   │ ~250       │
 ├─────────────────────────────────────────────────────────┼──────────────────────────────────┼────────────┤
 │ ER Extensions                                           │                                  │            │
 ├─────────────────────────────────────────────────────────┼──────────────────────────────────┼────────────┤
 │ frontend/src/components/schema/QueryPathOverlay.tsx     │ Table highlighting               │ ~150       │
 ├─────────────────────────────────────────────────────────┼──────────────────────────────────┼────────────┤
 │ frontend/src/components/schema/TableStatsNode.tsx       │ Stats display                    │ ~180       │
 ├─────────────────────────────────────────────────────────┼──────────────────────────────────┼────────────┤
 │ src/api/endpoints/table_stats.py                        │ Stats API                        │ ~100       │
 ├─────────────────────────────────────────────────────────┼──────────────────────────────────┼────────────┤
 │ frontend/tests/QueryPathOverlay.test.tsx                │ Overlay tests                    │ ~80        │
 └─────────────────────────────────────────────────────────┴──────────────────────────────────┴────────────┘
 Total: ~3,650 lines

 Modified Files
 ┌──────────────────────────────────────────────────────┬──────────────────────────────────────────────────┐
 │                         File                         │                     Changes                      │
 ├──────────────────────────────────────────────────────┼──────────────────────────────────────────────────┤
 │ frontend/src/App.tsx                                 │ Add Lineage tab                                  │
 ├──────────────────────────────────────────────────────┼──────────────────────────────────────────────────┤
 │ frontend/package.json                                │ Add sql-parser-cst dependency                    │
 ├──────────────────────────────────────────────────────┼──────────────────────────────────────────────────┤
 │ src/api/router.py                                    │ Register lineage and table_stats routers         │
 ├──────────────────────────────────────────────────────┼──────────────────────────────────────────────────┤
 │ frontend/src/components/QueryResults.tsx             │ Add "View Lineage" button                        │
 ├──────────────────────────────────────────────────────┼──────────────────────────────────────────────────┤
 │ frontend/src/components/schema/ERDiagram.tsx         │ Add right-click context menu, integrate overlays │
 ├──────────────────────────────────────────────────────┼──────────────────────────────────────────────────┤
 │ frontend/src/components/schema/ERDiagramControls.tsx │ Add overlay toggles                              │
 ├──────────────────────────────────────────────────────┼──────────────────────────────────────────────────┤
 │ frontend/src/components/schema/TableNode.tsx         │ Support extended stats display                   │
 └──────────────────────────────────────────────────────┴──────────────────────────────────────────────────┘
 ---
 10. Dependencies

 Backend

 - sqlparse - Already installed (used in multi_db_query_validator.py)

 Frontend

 {
   "sql-parser-cst": "^0.25.0"
 }

 ---
 11. Verification Plan

 Backend Tests

 # Run lineage parser tests
 ./run_tests.sh tests/test_sql_lineage_parser.py

 # Run impact analyzer tests
 ./run_tests.sh tests/test_impact_analyzer.py

 # Run API endpoint tests
 ./run_tests.sh tests/test_lineage_endpoints.py

 Frontend Tests

 cd frontend
 npm test -- LineageGraph
 npm test -- ImpactAnalysis

 Manual E2E Testing

 1. Execute several queries across databases
 2. Navigate to Lineage tab
 3. Select a query → verify lineage graph displays correctly
 4. Click "Impact Analysis" on a table → verify affected queries listed
 5. Check Query Pattern Heatmap shows usage data
 6. Verify dark mode styling

 ---
 12. Design Decisions (Confirmed)

 1. Lineage Caching: Hybrid LRU - Cache lineage after second access. First request parses on-demand, subsequent accesses use cache. Auto-evict
 after 7 days of no access.
 2. Analytics Scope: Both options - Toggle between per-connection and cross-connection views. Default to per-connection, with "All Connections"
 option in dropdown.
 3. Implementation: Full feature - Implement all 4 components in single PR: Lineage Graph, Column Tracking, Impact Analysis, Query Pattern
 Heatmap.

 ---
 13. Success Criteria

 - LineageGraph renders for any valid SQL query
 - Column-level transformations correctly identified (SUM, JOIN, CASE)
 - Impact Analysis finds all queries using a given column
 - Query Pattern Heatmap displays for each connection
 - Query Path Overlay highlights tables in ER Diagram
 - Table Statistics display row counts
 - All 35+ new tests passing
 - Performance: <2s lineage parsing for complex queries
 - Dark mode fully supported