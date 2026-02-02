# Lineage Intelligence - LLM-Powered Data Understanding

**Feature**: LLM-Powered Schema Analysis, Lineage Interpretation & Design Recommendations
**Branch**: data-lineage (extension)
**Priority**: HIGH
**Estimated Effort**: ~4,500 lines | 8-10 days
**Prerequisites**: Phase 11.1-11.5 Data Lineage (COMPLETE)

---

## 1. Vision

Transform Database Guru from a **query tool** into a **database intelligence platform** that helps users:

1. **Understand** - What does this data flow actually mean in business terms?
2. **Optimize** - How can I make my queries and schema faster?
3. **Evolve** - What's the safest way to change my schema?
4. **Design** - Is my database well-designed? What's missing?

**Key Principle**: Deterministic analysis (Phase 11) remains the foundation. LLM adds interpretation, explanation, and recommendations on top.

---

## 2. Feature Overview

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                        LINEAGE INTELLIGENCE FEATURE SET                                  │
└─────────────────────────────────────────────────────────────────────────────────────────┘

┌───────────────────────┐    ┌───────────────────────┐    ┌───────────────────────┐
│  Phase 12.1           │    │  Phase 12.2           │    │  Phase 12.3           │
│  LINEAGE NARRATOR     │───▶│  IMPACT ADVISOR       │───▶│  SCHEMA HEALTH        │
│                       │    │                       │    │  ANALYZER             │
│  • Data flow explain  │    │  • Migration guides   │    │                       │
│  • Transform meaning  │    │  • Risk explanations  │    │  • Normalization      │
│  • Business context   │    │  • SQL patch generate │    │  • Index suggestions  │
│  • Column semantics   │    │  • Dependency mapping │    │  • FK detection       │
│                       │    │                       │    │  • Type suggestions   │
│  ~800 lines           │    │  ~900 lines           │    │  ~1,000 lines         │
└───────────────────────┘    └───────────────────────┘    └───────────────────────┘
         │                            │                            │
         └────────────────────────────┼────────────────────────────┘
                                      │
                                      ▼
                    ┌───────────────────────────────────┐
                    │  Phase 12.4                       │
                    │  QUERY PATTERN INTELLIGENCE       │
                    │                                   │
                    │  • Bottleneck root cause          │
                    │  • Optimization recommendations   │
                    │  • Anti-pattern detection         │
                    │  • Trend analysis                 │
                    │                                   │
                    │  ~800 lines                       │
                    └───────────────────────────────────┘
                                      │
                                      ▼
                    ┌───────────────────────────────────┐
                    │  Phase 12.5                       │
                    │  CONVERSATIONAL LINEAGE           │
                    │                                   │
                    │  • "What columns feed revenue?"   │
                    │  • "What breaks if I rename X?"   │
                    │  • "Suggest next optimization"    │
                    │  • Multi-turn context             │
                    │                                   │
                    │  ~1,000 lines                     │
                    └───────────────────────────────────┘
```

---

## 3. Phase 12.1: Lineage Narrator

### Purpose
Generate human-readable explanations of data lineage graphs, transforming technical SQL analysis into business-friendly narratives.

### User Stories
1. As a business analyst, I want to understand what a complex SQL query does in plain English
2. As a data engineer, I want documentation generated from my query lineage
3. As a new team member, I want context about what transformations mean for the business

### Implementation

#### 3.1.1 LineageNarrator Class (`src/lineage/lineage_narrator.py`)

```python
class LineageNarrator:
    """Generates natural language explanations of data lineage."""

    def __init__(
        self,
        ollama_client: OllamaClient,
        model_router: Optional[ModelRouter] = None
    ):
        self.client = ollama_client
        self.router = model_router or ModelRouter()

    async def generate_narrative(
        self,
        lineage_graph: LineageGraph,
        question: Optional[str] = None,
        schema_context: Optional[Dict] = None,
        timeout: float = 15.0
    ) -> LineageNarrative:
        """
        Generate narrative explanation of lineage.

        Args:
            lineage_graph: Parsed lineage from SQLLineageParser
            question: Original natural language query (for context)
            schema_context: Table/column descriptions if available
            timeout: Max seconds for LLM call

        Returns:
            LineageNarrative with summary, column explanations, recommendations
        """

    async def explain_transformation(
        self,
        node: LineageNode,
        context: Dict
    ) -> str:
        """Explain what a specific transformation does."""

    async def infer_business_context(
        self,
        lineage_graph: LineageGraph,
        schema_context: Dict
    ) -> Dict[str, str]:
        """Map technical columns to business terminology."""

    def _build_lineage_prompt(
        self,
        lineage_graph: LineageGraph,
        question: Optional[str]
    ) -> str:
        """Build prompt for lineage explanation."""
```

#### 3.1.2 Data Models

```python
@dataclass
class LineageNarrative:
    summary: str  # 2-3 sentence overview
    data_flow_description: str  # Detailed flow explanation
    column_explanations: Dict[str, str]  # output_col -> explanation
    transformations_explained: List[TransformationExplanation]
    business_context: Dict[str, str]  # technical_name -> business_term
    potential_issues: List[str]  # Detected quality/logic issues
    confidence: float  # 0.0-1.0
    generated_at: datetime

@dataclass
class TransformationExplanation:
    node_id: str
    transformation_type: str
    input_columns: List[str]
    output_column: str
    explanation: str  # "Sums all order totals for each customer"
    business_meaning: Optional[str]  # "Calculates customer lifetime value"
```

#### 3.1.3 LLM Prompt Template

```python
LINEAGE_NARRATIVE_PROMPT = """
Analyze this SQL data lineage and explain it in business terms.

## Original Question
{question}

## SQL Query
{sql}

## Data Flow Graph
Source Tables: {source_tables}
Output Columns: {output_columns}

Transformations:
{transformations_formatted}

## Column Lineage
{column_lineage_formatted}

## Task
Provide:
1. SUMMARY: 2-3 sentences explaining what this query does in business terms
2. DATA FLOW: Step-by-step explanation of how data flows from sources to results
3. COLUMN MEANINGS: For each output column, explain what it represents
4. TRANSFORMATIONS: Explain each transformation (SUM, JOIN, CASE, etc.) in business terms
5. POTENTIAL ISSUES: Any data quality or logic concerns you notice

Respond in JSON format:
{
  "summary": "...",
  "data_flow_description": "...",
  "column_explanations": {"col1": "...", "col2": "..."},
  "transformations_explained": [
    {"node_id": "...", "explanation": "...", "business_meaning": "..."}
  ],
  "potential_issues": ["...", "..."]
}
"""
```

#### 3.1.4 API Endpoint Updates

```python
# src/api/endpoints/lineage.py - Update existing endpoint

@router.post("/parse")
async def parse_sql_lineage(
    request: LineageParseRequest,
    explain: bool = Query(False, description="Generate LLM narrative"),
    db: AsyncSession = Depends(get_db)
) -> LineageParseResponse:
    """Parse SQL and optionally explain lineage."""

    # Existing deterministic parsing
    graph = parser.parse(request.sql)

    # Optional LLM narrative
    narrative = None
    if explain and request.enable_llm:
        narrator = LineageNarrator(ollama_client)
        narrative = await narrator.generate_narrative(
            lineage_graph=graph,
            question=request.question,
            timeout=15.0
        )

    return LineageParseResponse(
        lineage_graph=graph,
        narrative=narrative  # Optional
    )
```

#### 3.1.5 Frontend Integration

```typescript
// frontend/src/components/lineage/LineageNarrative.tsx

interface LineageNarrativeProps {
  narrative: LineageNarrative | null;
  isLoading: boolean;
}

export const LineageNarrative: React.FC<LineageNarrativeProps> = ({
  narrative,
  isLoading
}) => {
  if (isLoading) return <NarrativeLoading />;
  if (!narrative) return null;

  return (
    <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
      <h3 className="font-semibold text-blue-800 dark:text-blue-200 mb-2">
        Data Flow Explanation
      </h3>

      {/* Summary */}
      <p className="text-gray-700 dark:text-gray-300 mb-4">
        {narrative.summary}
      </p>

      {/* Column Meanings */}
      <div className="space-y-2">
        <h4 className="font-medium">Output Columns</h4>
        {Object.entries(narrative.column_explanations).map(([col, explanation]) => (
          <div key={col} className="flex items-start gap-2">
            <code className="text-sm bg-gray-100 px-1">{col}</code>
            <span className="text-sm text-gray-600">{explanation}</span>
          </div>
        ))}
      </div>

      {/* Potential Issues */}
      {narrative.potential_issues.length > 0 && (
        <div className="mt-4 p-3 bg-yellow-50 rounded">
          <h4 className="font-medium text-yellow-800">Potential Issues</h4>
          <ul className="list-disc list-inside text-sm text-yellow-700">
            {narrative.potential_issues.map((issue, i) => (
              <li key={i}>{issue}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};
```

#### 3.1.6 Test Coverage

```python
# tests/test_lineage_narrator.py

class TestLineageNarrator:
    """Tests for LineageNarrator LLM integration."""

    async def test_generate_narrative_simple_select(self):
        """Test narrative for simple SELECT query."""

    async def test_generate_narrative_with_aggregation(self):
        """Test narrative explains SUM/COUNT/AVG correctly."""

    async def test_generate_narrative_with_joins(self):
        """Test narrative explains multi-table joins."""

    async def test_generate_narrative_complex_case(self):
        """Test narrative handles CASE expressions."""

    async def test_timeout_graceful_degradation(self):
        """Test returns partial result on timeout."""

    async def test_invalid_lineage_handling(self):
        """Test handles malformed lineage gracefully."""

    async def test_business_context_inference(self):
        """Test technical-to-business term mapping."""
```

**Lines**: ~800 (backend: 400, frontend: 250, tests: 150)

---

## 4. Phase 12.2: Impact Advisor

### Purpose
Transform impact analysis from "here's what's affected" to "here's what to do about it" with migration guides, risk explanations, and SQL patches.

### User Stories
1. As a DBA, I want to know WHY a schema change is risky, not just that it is
2. As a developer, I want SQL patches to fix affected queries after a schema change
3. As a team lead, I want a migration plan I can share with stakeholders

### Implementation

#### 4.2.1 ImpactAdvisor Class (`src/lineage/impact_advisor.py`)

```python
class ImpactAdvisor:
    """Provides intelligent recommendations for schema changes."""

    def __init__(
        self,
        ollama_client: OllamaClient,
        impact_analyzer: ImpactAnalyzer,
        model_router: Optional[ModelRouter] = None
    ):
        self.client = ollama_client
        self.analyzer = impact_analyzer
        self.router = model_router or ModelRouter()

    async def analyze_with_recommendations(
        self,
        change_type: SchemaChangeType,  # RENAME, DROP, MODIFY_TYPE, ADD
        target_table: str,
        target_column: Optional[str],
        new_value: Optional[str],  # New name for RENAME, new type for MODIFY
        db_session: AsyncSession,
        connection_id: Optional[int] = None
    ) -> ImpactAdvice:
        """
        Analyze impact and provide actionable recommendations.

        Returns:
            ImpactAdvice with risk analysis, migration steps, SQL patches
        """

    async def generate_migration_plan(
        self,
        impact: ImpactAnalysis,
        change_type: SchemaChangeType,
        new_value: Optional[str]
    ) -> MigrationPlan:
        """Generate step-by-step migration plan."""

    async def generate_sql_patches(
        self,
        impacted_queries: List[ImpactedQuery],
        change_type: SchemaChangeType,
        old_value: str,
        new_value: str
    ) -> List[SQLPatch]:
        """Generate SQL fixes for affected queries."""

    async def explain_risk(
        self,
        impact: ImpactAnalysis
    ) -> RiskExplanation:
        """Explain why this change is risky in business terms."""
```

#### 4.2.2 Data Models

```python
class SchemaChangeType(Enum):
    RENAME_COLUMN = "rename_column"
    RENAME_TABLE = "rename_table"
    DROP_COLUMN = "drop_column"
    DROP_TABLE = "drop_table"
    MODIFY_TYPE = "modify_type"
    ADD_COLUMN = "add_column"
    ADD_INDEX = "add_index"

@dataclass
class ImpactAdvice:
    original_impact: ImpactAnalysis  # From deterministic analyzer
    risk_explanation: RiskExplanation
    migration_plan: MigrationPlan
    sql_patches: List[SQLPatch]
    recommendations: List[str]
    estimated_effort: str  # "Low", "Medium", "High"
    confidence: float

@dataclass
class RiskExplanation:
    summary: str  # "Removing status column affects 47 queries..."
    risk_factors: List[RiskFactor]  # Breakdown of risk sources
    business_impact: str  # Business-level explanation
    mitigation_options: List[str]

@dataclass
class RiskFactor:
    factor: str  # "JOIN dependency", "WHERE clause filter", etc.
    severity: str  # "high", "medium", "low"
    affected_count: int
    explanation: str

@dataclass
class MigrationPlan:
    steps: List[MigrationStep]
    rollback_steps: List[MigrationStep]
    prerequisites: List[str]
    estimated_downtime: str  # "None", "Brief (<1min)", "Extended"
    testing_notes: List[str]

@dataclass
class MigrationStep:
    order: int
    description: str
    sql: Optional[str]
    is_destructive: bool
    requires_downtime: bool

@dataclass
class SQLPatch:
    query_id: int
    original_sql: str
    patched_sql: str
    change_description: str
    confidence: float  # How confident is the patch
    manual_review_needed: bool
```

#### 4.2.3 LLM Prompt Templates

```python
RISK_EXPLANATION_PROMPT = """
Analyze this schema change impact and explain the risks.

## Proposed Change
Type: {change_type}
Target: {table}.{column}
{new_value_info}

## Impact Summary
Total affected queries: {total_affected}
By type:
- SELECT clauses: {select_count}
- WHERE filters: {filter_count}
- JOIN conditions: {join_count}
- GROUP BY: {group_count}
- ORDER BY: {order_count}

## Sample Affected Queries
{sample_queries}

## Task
Explain:
1. WHY this change is {risk_level} risk
2. What BUSINESS PROCESSES might be affected
3. What could GO WRONG if done incorrectly
4. MITIGATION options to reduce risk

Respond in JSON format with: summary, risk_factors[], business_impact, mitigation_options[]
"""

MIGRATION_PLAN_PROMPT = """
Generate a safe migration plan for this schema change.

## Change Details
{change_details}

## Affected Queries
{affected_queries_summary}

## Database Type
{database_type}

## Task
Create a step-by-step migration plan including:
1. Pre-migration checks
2. Migration steps with SQL (in order)
3. Post-migration verification
4. Rollback steps if something goes wrong
5. Testing recommendations

Consider:
- Minimize downtime
- Backwards compatibility during transition
- Data integrity preservation

Respond in JSON with: steps[], rollback_steps[], prerequisites[], testing_notes[]
"""

SQL_PATCH_PROMPT = """
Generate SQL patches for these affected queries.

## Schema Change
{change_description}

## Affected Query
Original SQL:
{original_sql}

Original Question: {original_question}

## Task
Generate the corrected SQL that:
1. Maintains the same functionality
2. Uses the new schema (e.g., new column name)
3. Preserves query intent

Respond in JSON: patched_sql, change_description, confidence, manual_review_needed
"""
```

#### 4.2.4 API Endpoints

```python
# src/api/endpoints/lineage.py - New endpoint

@router.post("/impact/advise")
async def get_impact_advice(
    request: ImpactAdviceRequest,
    db: AsyncSession = Depends(get_db)
) -> ImpactAdviceResponse:
    """
    Analyze schema change impact with LLM recommendations.

    Returns deterministic impact analysis PLUS:
    - Risk explanation in business terms
    - Migration plan with SQL steps
    - SQL patches for affected queries
    - Effort estimation
    """

    advisor = ImpactAdvisor(ollama_client, impact_analyzer)
    advice = await advisor.analyze_with_recommendations(
        change_type=request.change_type,
        target_table=request.table,
        target_column=request.column,
        new_value=request.new_value,
        db_session=db,
        connection_id=request.connection_id
    )

    return ImpactAdviceResponse(
        impact=advice.original_impact,
        risk_explanation=advice.risk_explanation,
        migration_plan=advice.migration_plan,
        sql_patches=advice.sql_patches,
        recommendations=advice.recommendations
    )
```

#### 4.2.5 Frontend Integration

```typescript
// frontend/src/components/lineage/ImpactAdvisorPanel.tsx

export const ImpactAdvisorPanel: React.FC<ImpactAdvisorProps> = ({
  advice,
  isLoading
}) => {
  return (
    <div className="space-y-4">
      {/* Risk Explanation Card */}
      <Card className="border-l-4 border-l-red-500">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="text-red-500" />
            Risk Assessment
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="mb-4">{advice.risk_explanation.summary}</p>

          {/* Risk Factors */}
          <div className="space-y-2">
            {advice.risk_explanation.risk_factors.map((factor, i) => (
              <RiskFactorBadge key={i} factor={factor} />
            ))}
          </div>

          {/* Business Impact */}
          <div className="mt-4 p-3 bg-gray-50 rounded">
            <h4 className="font-medium">Business Impact</h4>
            <p className="text-sm">{advice.risk_explanation.business_impact}</p>
          </div>
        </CardContent>
      </Card>

      {/* Migration Plan Card */}
      <Card>
        <CardHeader>
          <CardTitle>Migration Plan</CardTitle>
        </CardHeader>
        <CardContent>
          <MigrationSteps steps={advice.migration_plan.steps} />

          <Collapsible title="Rollback Plan">
            <MigrationSteps steps={advice.migration_plan.rollback_steps} />
          </Collapsible>
        </CardContent>
      </Card>

      {/* SQL Patches Card */}
      <Card>
        <CardHeader>
          <CardTitle>Suggested SQL Patches</CardTitle>
        </CardHeader>
        <CardContent>
          {advice.sql_patches.map((patch, i) => (
            <SQLPatchCard key={i} patch={patch} />
          ))}
        </CardContent>
      </Card>
    </div>
  );
};
```

**Lines**: ~900 (backend: 500, frontend: 250, tests: 150)

---

## 5. Phase 12.3: Schema Health Analyzer

### Purpose
Analyze database schema design and provide intelligent recommendations for normalization, indexing, type optimization, and structural improvements.

### User Stories
1. As a DBA, I want to know if my schema follows best practices
2. As a developer, I want index suggestions based on my actual query patterns
3. As a data architect, I want normalization recommendations with trade-off analysis

### Implementation

#### 5.3.1 SchemaHealthAnalyzer Class (`src/lineage/schema_health_analyzer.py`)

```python
class SchemaHealthAnalyzer:
    """Analyzes schema design and provides improvement recommendations."""

    def __init__(
        self,
        ollama_client: OllamaClient,
        schema_inspector: SchemaInspector,
        query_pattern_analyzer: QueryPatternAnalyzer,
        model_router: Optional[ModelRouter] = None
    ):
        self.client = ollama_client
        self.inspector = schema_inspector
        self.pattern_analyzer = query_pattern_analyzer
        self.router = model_router or ModelRouter()

    async def analyze_schema_health(
        self,
        connection_id: int,
        db_session: AsyncSession,
        include_query_patterns: bool = True
    ) -> SchemaHealthReport:
        """
        Comprehensive schema health analysis.

        Combines:
        - Structural analysis (PKs, FKs, types)
        - Query pattern analysis (actual usage)
        - LLM reasoning for recommendations
        """

    async def suggest_indexes(
        self,
        connection_id: int,
        db_session: AsyncSession
    ) -> List[IndexSuggestion]:
        """
        Suggest indexes based on query patterns.

        Analyzes:
        - WHERE clause columns
        - JOIN columns
        - ORDER BY columns
        - Query frequency
        """

    async def analyze_normalization(
        self,
        connection_id: int,
        db_session: AsyncSession
    ) -> NormalizationAnalysis:
        """
        Analyze normalization level and suggest improvements.

        Detects:
        - Repeated column patterns (denormalization)
        - Missing junction tables
        - Redundant data storage
        """

    async def suggest_type_improvements(
        self,
        connection_id: int,
        db_session: AsyncSession
    ) -> List[TypeSuggestion]:
        """
        Suggest column type improvements based on actual data.

        Detects:
        - VARCHAR storing only integers
        - TEXT storing short strings
        - Inconsistent date formats
        """

    async def detect_anti_patterns(
        self,
        connection_id: int,
        db_session: AsyncSession
    ) -> List[AntiPattern]:
        """
        Detect common schema anti-patterns.

        Patterns:
        - God tables (too many columns)
        - EAV abuse (entity-attribute-value)
        - Polymorphic associations
        - Missing audit columns
        """
```

#### 5.3.2 Data Models

```python
@dataclass
class SchemaHealthReport:
    connection_id: int
    overall_score: float  # 0-100 health score
    grade: str  # A, B, C, D, F

    structural_issues: List[StructuralIssue]
    index_suggestions: List[IndexSuggestion]
    normalization_analysis: NormalizationAnalysis
    type_suggestions: List[TypeSuggestion]
    anti_patterns: List[AntiPattern]

    summary: str  # LLM-generated summary
    top_recommendations: List[str]  # Prioritized action items

    generated_at: datetime

@dataclass
class StructuralIssue:
    issue_type: str  # "missing_pk", "orphan_fk", "circular_ref", "missing_fk"
    severity: str  # "critical", "warning", "info"
    table: str
    column: Optional[str]
    description: str
    fix_sql: Optional[str]

@dataclass
class IndexSuggestion:
    table: str
    columns: List[str]
    index_type: str  # "btree", "hash", "gin", "composite"
    reason: str  # "Used in WHERE clause in 85% of queries"
    estimated_improvement: str  # "High", "Medium", "Low"
    create_sql: str
    query_count_affected: int

@dataclass
class NormalizationAnalysis:
    current_level: str  # "1NF", "2NF", "3NF", "BCNF", "Denormalized"
    issues: List[NormalizationIssue]
    recommendations: List[str]
    trade_offs: Dict[str, str]  # recommendation -> trade-off explanation

@dataclass
class NormalizationIssue:
    issue_type: str  # "repeating_groups", "partial_dependency", "transitive_dependency"
    tables_involved: List[str]
    columns_involved: List[str]
    description: str
    suggested_fix: str
    fix_sql: List[str]  # DDL statements to fix

@dataclass
class TypeSuggestion:
    table: str
    column: str
    current_type: str
    suggested_type: str
    reason: str
    sample_values: List[str]
    alter_sql: str

@dataclass
class AntiPattern:
    pattern_name: str
    severity: str
    tables_involved: List[str]
    description: str
    why_problematic: str
    suggested_fix: str
    examples: List[str]
```

#### 5.3.3 Analysis Components

```python
# Deterministic structural analysis (no LLM)
class StructuralAnalyzer:
    """Detect structural issues without LLM."""

    def find_missing_primary_keys(self, schema: Dict) -> List[str]:
        """Find tables without primary keys."""

    def find_orphaned_foreign_keys(self, schema: Dict) -> List[Dict]:
        """Find FKs referencing non-existent tables/columns."""

    def find_missing_foreign_keys(self, schema: Dict) -> List[Dict]:
        """Detect columns that look like FKs but aren't declared."""
        # Pattern: *_id columns without FK constraints

    def detect_circular_references(self, schema: Dict) -> List[List[str]]:
        """Find circular FK chains."""

# Query-pattern-based index analysis (no LLM)
class IndexAnalyzer:
    """Suggest indexes based on query patterns."""

    def analyze_where_clauses(
        self,
        queries: List[QueryHistory]
    ) -> Dict[str, int]:
        """Count column usage in WHERE clauses."""

    def analyze_join_columns(
        self,
        queries: List[QueryHistory]
    ) -> Dict[str, int]:
        """Count column usage in JOIN conditions."""

    def suggest_composite_indexes(
        self,
        where_usage: Dict,
        join_usage: Dict
    ) -> List[IndexSuggestion]:
        """Suggest multi-column indexes for common patterns."""
```

#### 5.3.4 LLM Prompt Templates

```python
SCHEMA_HEALTH_SUMMARY_PROMPT = """
Analyze this database schema and provide a health assessment.

## Schema Overview
Tables: {table_count}
Total Columns: {column_count}
Foreign Keys: {fk_count}

## Structural Issues Found
{structural_issues}

## Query Pattern Data
Most queried tables: {top_tables}
Most common JOINs: {common_joins}
Slow queries involving: {slow_tables}

## Missing Indexes Detected
{missing_indexes}

## Task
Provide:
1. OVERALL ASSESSMENT: Rate this schema A-F with explanation
2. TOP 3 RECOMMENDATIONS: Most impactful improvements
3. TRADE-OFFS: For each recommendation, explain pros/cons
4. PRIORITY ORDER: What to fix first and why

Respond in JSON with: overall_score, grade, summary, top_recommendations[]
"""

NORMALIZATION_ANALYSIS_PROMPT = """
Analyze this schema for normalization issues.

## Schema Details
{schema_details}

## Patterns Detected
- Repeating column groups: {repeating_groups}
- Potential partial dependencies: {partial_deps}
- Redundant data patterns: {redundant_patterns}

## Task
1. Identify the current normalization level (1NF, 2NF, 3NF, BCNF, or Denormalized)
2. List specific normalization violations
3. Provide DDL to fix issues (if recommended)
4. Explain trade-offs (sometimes denormalization is intentional)

Respond in JSON with: current_level, issues[], recommendations[], trade_offs{}
"""

INDEX_RECOMMENDATION_PROMPT = """
Recommend indexes for this database based on query patterns.

## Query Patterns
{query_pattern_summary}

## Current Indexes
{existing_indexes}

## Column Usage Statistics
WHERE clauses: {where_usage}
JOIN conditions: {join_usage}
ORDER BY: {order_usage}
GROUP BY: {group_usage}

## Task
Suggest indexes that will:
1. Speed up the most frequent queries
2. Support common JOIN patterns
3. Avoid over-indexing (too many indexes slow writes)

For each suggestion, explain:
- Which queries benefit
- Estimated performance improvement
- Any trade-offs (write performance, storage)

Respond in JSON with: suggestions[{table, columns, reason, estimated_improvement}]
"""
```

#### 5.3.5 API Endpoints

```python
@router.get("/schema/health/{connection_id}")
async def get_schema_health(
    connection_id: int,
    include_patterns: bool = Query(True),
    db: AsyncSession = Depends(get_db)
) -> SchemaHealthResponse:
    """
    Get comprehensive schema health analysis.

    Returns:
    - Overall health score and grade
    - Structural issues (missing PKs, orphan FKs)
    - Index suggestions based on query patterns
    - Normalization analysis
    - Type improvement suggestions
    - Detected anti-patterns
    - Prioritized recommendations
    """

@router.get("/schema/suggest-indexes/{connection_id}")
async def suggest_indexes(
    connection_id: int,
    db: AsyncSession = Depends(get_db)
) -> List[IndexSuggestion]:
    """Get index suggestions based on query patterns."""

@router.get("/schema/normalization/{connection_id}")
async def analyze_normalization(
    connection_id: int,
    db: AsyncSession = Depends(get_db)
) -> NormalizationAnalysis:
    """Get normalization analysis with fix suggestions."""
```

#### 5.3.6 Frontend Integration

```typescript
// frontend/src/components/schema/SchemaHealthDashboard.tsx

export const SchemaHealthDashboard: React.FC<Props> = ({ connectionId }) => {
  const { data: health, isLoading } = useSchemaHealth(connectionId);

  return (
    <div className="space-y-6">
      {/* Overall Score Card */}
      <Card className="p-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold">Schema Health</h2>
            <p className="text-gray-500">{health?.summary}</p>
          </div>
          <HealthGradeBadge
            score={health?.overall_score}
            grade={health?.grade}
          />
        </div>
      </Card>

      {/* Top Recommendations */}
      <Card>
        <CardHeader>
          <CardTitle>Top Recommendations</CardTitle>
        </CardHeader>
        <CardContent>
          <ol className="list-decimal list-inside space-y-2">
            {health?.top_recommendations.map((rec, i) => (
              <li key={i} className="text-gray-700">{rec}</li>
            ))}
          </ol>
        </CardContent>
      </Card>

      {/* Tabbed Detail View */}
      <Tabs defaultValue="indexes">
        <TabsList>
          <TabsTrigger value="indexes">Index Suggestions</TabsTrigger>
          <TabsTrigger value="structure">Structural Issues</TabsTrigger>
          <TabsTrigger value="normalization">Normalization</TabsTrigger>
          <TabsTrigger value="types">Type Suggestions</TabsTrigger>
        </TabsList>

        <TabsContent value="indexes">
          <IndexSuggestionsPanel suggestions={health?.index_suggestions} />
        </TabsContent>

        <TabsContent value="structure">
          <StructuralIssuesPanel issues={health?.structural_issues} />
        </TabsContent>

        <TabsContent value="normalization">
          <NormalizationPanel analysis={health?.normalization_analysis} />
        </TabsContent>

        <TabsContent value="types">
          <TypeSuggestionsPanel suggestions={health?.type_suggestions} />
        </TabsContent>
      </Tabs>
    </div>
  );
};
```

**Lines**: ~1,000 (backend: 550, frontend: 300, tests: 150)

---

## 6. Phase 12.4: Query Pattern Intelligence

### Purpose
Transform raw query pattern data into actionable insights: root cause analysis for bottlenecks, optimization recommendations, and anti-pattern detection.

### User Stories
1. As a DBA, I want to know WHY certain queries are slow, not just that they are
2. As a developer, I want specific optimization suggestions for my query patterns
3. As a team lead, I want to identify training opportunities (common mistakes)

### Implementation

#### 6.4.1 PatternIntelligenceAgent Class (`src/lineage/pattern_intelligence.py`)

```python
class PatternIntelligenceAgent:
    """Provides intelligent insights on query patterns."""

    async def analyze_bottleneck(
        self,
        bottleneck: PerformanceBottleneck,
        schema: Dict,
        sample_queries: List[str]
    ) -> BottleneckAnalysis:
        """
        Analyze why a table is a bottleneck.

        Returns root causes and specific fix recommendations.
        """

    async def suggest_optimizations(
        self,
        patterns: HeatmapData,
        schema: Dict
    ) -> List[OptimizationSuggestion]:
        """
        Suggest query and schema optimizations.

        Based on:
        - Frequently joined tables → suggest materialized views
        - Repeated patterns → suggest query templates
        - High-latency patterns → suggest indexes or rewrites
        """

    async def detect_anti_patterns(
        self,
        queries: List[QueryHistory]
    ) -> List[QueryAntiPattern]:
        """
        Detect common query anti-patterns.

        Patterns:
        - N+1 queries (many similar queries)
        - SELECT * on large tables
        - Missing LIMIT clauses
        - Cartesian joins
        - OR conditions that prevent index use
        """

    async def analyze_trends(
        self,
        patterns: HeatmapData,
        time_range: str
    ) -> TrendAnalysis:
        """
        Analyze pattern changes over time.

        Detects:
        - Usage growth/decline
        - New query patterns
        - Performance degradation trends
        """
```

#### 6.4.2 Data Models

```python
@dataclass
class BottleneckAnalysis:
    table: str
    bottleneck_score: float
    root_causes: List[RootCause]
    recommendations: List[OptimizationSuggestion]
    quick_wins: List[str]  # Easy fixes
    long_term_fixes: List[str]  # Requires more effort

@dataclass
class RootCause:
    cause_type: str  # "missing_index", "table_scan", "complex_join", "data_volume"
    confidence: float
    evidence: str
    impact: str  # "high", "medium", "low"

@dataclass
class OptimizationSuggestion:
    suggestion_type: str  # "add_index", "rewrite_query", "create_view", "partition_table"
    description: str
    expected_improvement: str
    implementation: str  # SQL or instructions
    effort: str  # "low", "medium", "high"
    risk: str

@dataclass
class QueryAntiPattern:
    pattern_name: str
    severity: str
    occurrences: int
    example_queries: List[str]
    why_problematic: str
    how_to_fix: str

@dataclass
class TrendAnalysis:
    time_range: str
    key_trends: List[Trend]
    alerts: List[str]  # Things that need attention
    predictions: List[str]  # What might happen if trends continue
```

**Lines**: ~800 (backend: 450, frontend: 200, tests: 150)

---

## 7. Phase 12.5: Conversational Lineage

### Purpose
Enable natural language interaction with lineage data, allowing users to ask questions and get intelligent responses.

### User Stories
1. As a developer, I want to ask "What columns feed into revenue?" in plain English
2. As a DBA, I want to ask "What breaks if I drop the status column?"
3. As a data analyst, I want to have a conversation about my data model

### Implementation

#### 7.5.1 LineageConversationAgent Class (`src/lineage/lineage_conversation_agent.py`)

```python
class LineageConversationAgent:
    """Handles conversational queries about lineage and schema."""

    def __init__(
        self,
        ollama_client: OllamaClient,
        lineage_parser: SQLLineageParser,
        impact_analyzer: ImpactAnalyzer,
        pattern_analyzer: QueryPatternAnalyzer,
        schema_inspector: SchemaInspector,
        conversational_memory: ConversationalMemoryAgent
    ):
        self.client = ollama_client
        self.parser = lineage_parser
        self.impact = impact_analyzer
        self.patterns = pattern_analyzer
        self.schema = schema_inspector
        self.memory = conversational_memory

    async def ask(
        self,
        question: str,
        connection_id: int,
        session_id: Optional[str],
        db_session: AsyncSession
    ) -> LineageAnswer:
        """
        Answer a natural language question about lineage.

        Question types:
        - Lineage queries: "What columns feed into X?"
        - Impact queries: "What breaks if I change Y?"
        - Pattern queries: "What are the most used tables?"
        - Recommendation queries: "How can I optimize Z?"
        """

    async def _classify_question(
        self,
        question: str
    ) -> QuestionType:
        """Classify question to route to appropriate analyzer."""

    async def _answer_lineage_question(
        self,
        question: str,
        connection_id: int,
        db_session: AsyncSession
    ) -> LineageAnswer:
        """Handle questions about data flow."""

    async def _answer_impact_question(
        self,
        question: str,
        connection_id: int,
        db_session: AsyncSession
    ) -> LineageAnswer:
        """Handle questions about schema change impact."""

    async def _answer_pattern_question(
        self,
        question: str,
        connection_id: int,
        db_session: AsyncSession
    ) -> LineageAnswer:
        """Handle questions about query patterns."""
```

#### 7.5.2 Question Types and Routing

```python
class QuestionType(Enum):
    LINEAGE = "lineage"  # "What feeds into X?"
    IMPACT = "impact"  # "What breaks if I change Y?"
    PATTERN = "pattern"  # "What's most used?"
    RECOMMENDATION = "recommendation"  # "How to optimize?"
    SCHEMA = "schema"  # "What's in table X?"
    GENERAL = "general"  # Anything else

QUESTION_PATTERNS = {
    QuestionType.LINEAGE: [
        r"what.*feeds.*into",
        r"where.*comes.*from",
        r"source.*of",
        r"lineage.*of",
        r"depends.*on",
    ],
    QuestionType.IMPACT: [
        r"what.*breaks.*if",
        r"affected.*by",
        r"impact.*of",
        r"change.*what.*happens",
        r"remove.*affect",
        r"rename.*affect",
    ],
    QuestionType.PATTERN: [
        r"most.*used",
        r"frequently.*queried",
        r"common.*joins",
        r"bottleneck",
        r"slow.*queries",
    ],
    QuestionType.RECOMMENDATION: [
        r"how.*optimize",
        r"improve.*performance",
        r"suggest.*index",
        r"should.*change",
        r"best.*practice",
    ],
}
```

#### 7.5.3 API Endpoint

```python
@router.post("/lineage/ask")
async def ask_lineage_question(
    request: LineageQuestionRequest,
    db: AsyncSession = Depends(get_db)
) -> LineageAnswerResponse:
    """
    Ask a natural language question about data lineage.

    Examples:
    - "What columns feed into total_revenue?"
    - "What queries would break if I rename customer_id?"
    - "What are the most frequently joined tables?"
    - "How can I optimize queries on the orders table?"
    """

    agent = LineageConversationAgent(...)
    answer = await agent.ask(
        question=request.question,
        connection_id=request.connection_id,
        session_id=request.session_id,
        db_session=db
    )

    return LineageAnswerResponse(
        answer=answer.text,
        supporting_data=answer.supporting_data,
        visualizations=answer.visualizations,  # Graphs to render
        follow_up_questions=answer.suggested_follow_ups
    )
```

#### 7.5.4 Frontend Integration

```typescript
// frontend/src/components/lineage/LineageChat.tsx

export const LineageChat: React.FC<Props> = ({ connectionId }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');

  const askQuestion = useMutation({
    mutationFn: (question: string) => lineageApi.ask({
      question,
      connection_id: connectionId,
      session_id: sessionId
    }),
    onSuccess: (response) => {
      setMessages(prev => [
        ...prev,
        { role: 'user', content: input },
        {
          role: 'assistant',
          content: response.answer,
          visualizations: response.visualizations,
          followUps: response.follow_up_questions
        }
      ]);
    }
  });

  return (
    <div className="flex flex-col h-full">
      {/* Message List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg, i) => (
          <ChatMessage key={i} message={msg} />
        ))}
      </div>

      {/* Suggested Questions */}
      {messages.length === 0 && (
        <div className="p-4 grid grid-cols-2 gap-2">
          {SUGGESTED_QUESTIONS.map((q, i) => (
            <button
              key={i}
              onClick={() => askQuestion.mutate(q)}
              className="p-2 text-left text-sm border rounded hover:bg-gray-50"
            >
              {q}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div className="border-t p-4">
        <div className="flex gap-2">
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder="Ask about your data lineage..."
            className="flex-1 border rounded px-3 py-2"
            onKeyDown={e => e.key === 'Enter' && askQuestion.mutate(input)}
          />
          <button
            onClick={() => askQuestion.mutate(input)}
            className="px-4 py-2 bg-indigo-600 text-white rounded"
          >
            Ask
          </button>
        </div>
      </div>
    </div>
  );
};

const SUGGESTED_QUESTIONS = [
  "What are the most frequently used tables?",
  "Which tables would be affected if I modify the orders table?",
  "What columns feed into total_revenue calculations?",
  "How can I optimize slow queries?",
];
```

**Lines**: ~1,000 (backend: 550, frontend: 300, tests: 150)

---

## 8. Implementation Schedule

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                        LINEAGE INTELLIGENCE IMPLEMENTATION                           │
└─────────────────────────────────────────────────────────────────────────────────────┘

Week 1
├── Day 1-2: Phase 12.1 - Lineage Narrator
│   ├── LineageNarrator class
│   ├── Data models
│   ├── API endpoint update
│   └── Basic tests
│
├── Day 3-4: Phase 12.1 - Frontend + Polish
│   ├── LineageNarrative component
│   ├── Integration with LineagePanel
│   └── Comprehensive tests

Week 2
├── Day 1-2: Phase 12.2 - Impact Advisor
│   ├── ImpactAdvisor class
│   ├── Migration plan generation
│   ├── SQL patch generation
│   └── Tests
│
├── Day 3-4: Phase 12.2 - Frontend
│   ├── ImpactAdvisorPanel component
│   ├── MigrationSteps component
│   └── SQLPatchCard component

Week 3
├── Day 1-3: Phase 12.3 - Schema Health Analyzer
│   ├── Structural analyzer (no LLM)
│   ├── Index analyzer (no LLM)
│   ├── LLM-powered recommendations
│   └── Tests
│
├── Day 4-5: Phase 12.3 - Frontend
│   ├── SchemaHealthDashboard
│   ├── Component panels (indexes, normalization, types)
│   └── ER Diagram integration

Week 4
├── Day 1-2: Phase 12.4 - Pattern Intelligence
│   ├── PatternIntelligenceAgent
│   ├── Bottleneck analysis
│   ├── Anti-pattern detection
│   └── Tests
│
├── Day 3-5: Phase 12.5 - Conversational Lineage
│   ├── LineageConversationAgent
│   ├── Question routing
│   ├── LineageChat component
│   └── E2E tests
```

---

## 9. Dependencies

### Backend
- Existing: `ollama`, `sqlparse`, `sqlalchemy`
- No new dependencies required

### Frontend
- Existing: `@tanstack/react-query`, `recharts`, `reactflow`
- No new dependencies required

---

## 10. Integration with Existing Systems

### Model Router Integration
```python
# Add new task types to ModelRouter
TASK_LINEAGE_NARRATIVE = "lineage_narrative"
TASK_IMPACT_ANALYSIS = "impact_analysis"
TASK_SCHEMA_HEALTH = "schema_health"
TASK_LINEAGE_CONVERSATION = "lineage_conversation"

# Default timeouts
TASK_TIMEOUTS = {
    TASK_LINEAGE_NARRATIVE: 15.0,
    TASK_IMPACT_ANALYSIS: 20.0,
    TASK_SCHEMA_HEALTH: 30.0,
    TASK_LINEAGE_CONVERSATION: 15.0,
}
```

### System Settings Extension
```python
# New settings for lineage intelligence
enable_lineage_narrator: bool = True
enable_impact_advisor: bool = True
enable_schema_health: bool = True
enable_lineage_chat: bool = True
model_lineage_intelligence: Optional[str] = None  # Per-task model
```

### ConversationalMemoryAgent Integration
```python
# Extend to track lineage conversation context
class LineageConversationContext:
    recent_queries: List[str]
    discussed_tables: List[str]
    discussed_columns: List[str]
    current_topic: str  # "lineage", "impact", "patterns", "health"
```

---

## 11. Success Criteria

| Feature | Success Metric |
|---------|----------------|
| Lineage Narrator | Generates coherent explanation for 95% of valid queries |
| Impact Advisor | Provides actionable migration plan for all change types |
| Schema Health | Detects 90%+ of missing PKs, orphan FKs |
| Pattern Intelligence | Identifies top 3 bottlenecks correctly |
| Conversational Lineage | Correctly routes 90%+ of questions |

### Performance Targets
- Lineage narrative: <5 seconds
- Impact advice: <10 seconds
- Schema health: <15 seconds
- Conversational response: <5 seconds

---

## 12. Risk Mitigation

| Risk | Mitigation |
|------|------------|
| LLM hallucination | All recommendations based on deterministic analysis first |
| Slow responses | Aggressive timeouts + graceful degradation |
| Complex schemas | Limit analysis to 50 tables by default |
| Cost (LLM calls) | Cache narratives, optional features |

---

## 13. Future Extensions

After Phase 12:
- **Auto-documentation**: Generate data dictionary from lineage + LLM
- **Change monitoring**: Alert when query patterns change significantly
- **Team insights**: Compare query patterns across team members
- **Cost analysis**: Estimate query costs across cloud databases
- **Compliance checking**: Detect PII in lineage paths

---

## 14. Files Summary

### New Files

| File | Purpose | Lines |
|------|---------|-------|
| `src/lineage/lineage_narrator.py` | Lineage explanation generation | ~400 |
| `src/lineage/impact_advisor.py` | Migration recommendations | ~500 |
| `src/lineage/schema_health_analyzer.py` | Schema design analysis | ~550 |
| `src/lineage/pattern_intelligence.py` | Query pattern insights | ~450 |
| `src/lineage/lineage_conversation_agent.py` | Conversational interface | ~550 |
| `frontend/src/components/lineage/LineageNarrative.tsx` | Narrative display | ~150 |
| `frontend/src/components/lineage/ImpactAdvisorPanel.tsx` | Impact recommendations UI | ~250 |
| `frontend/src/components/schema/SchemaHealthDashboard.tsx` | Health dashboard | ~300 |
| `frontend/src/components/lineage/LineageChat.tsx` | Conversational UI | ~300 |
| `tests/test_lineage_narrator.py` | Narrator tests | ~150 |
| `tests/test_impact_advisor.py` | Impact advisor tests | ~150 |
| `tests/test_schema_health.py` | Schema health tests | ~150 |
| `tests/test_pattern_intelligence.py` | Pattern tests | ~150 |
| `tests/test_lineage_conversation.py` | Conversation tests | ~150 |

**Total**: ~4,200 lines

### Modified Files

| File | Changes |
|------|---------|
| `src/api/endpoints/lineage.py` | Add explain parameter, new endpoints |
| `src/llm/model_router.py` | Add lineage task types |
| `src/database/models.py` | Add lineage settings |
| `frontend/src/components/lineage/LineagePanel.tsx` | Add Chat tab |
| `frontend/src/services/lineageApi.ts` | Add new API methods |

---

**Document Version**: 1.1
**Created**: January 24, 2026
**Completed**: January 31, 2026
**Author**: Claude Code
**Status**: ✅ COMPLETE (151 tests, ~11,266 lines across 27 files)
