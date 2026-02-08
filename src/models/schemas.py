"""Pydantic schemas for API requests and responses"""
from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field, validator, field_validator

from src.security.prompt_sanitizer import sanitize_user_input, detect_injection_attempt


class QueryRequest(BaseModel):
    """Request model for natural language query"""
    question: str = Field(
        ...,
        description="Natural language question",
        min_length=3,
        max_length=500,
        example="Show me all customers from California"
    )
    database_type: str = Field(
        default="postgresql",
        description="Type of database",
        example="postgresql"
    )
    schema: Optional[str] = Field(
        default=None,
        description="Database schema information (optional)",
    )
    model: Optional[str] = Field(
        default=None,
        description="Ollama model to use (e.g., 'llama3', 'mistral', 'codellama'). Uses default if not specified.",
        example="llama3"
    )
    allow_write: bool = Field(
        default=False,
        description="Allow write operations (INSERT, UPDATE, DELETE)",
    )
    use_cache: bool = Field(
        default=True,
        description="Use cached results if available",
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Chat session ID for conversational context (optional)",
        example="550e8400-e29b-41d4-a716-446655440000"
    )
    force_schema_refresh: bool = Field(
        default=False,
        description="Force re-introspection of database schema (bypasses cache)",
    )
    enable_narratives: bool = Field(
        default=True,
        description="Enable natural language narrative generation from query results",
    )
    preferred_chart_type: Optional[str] = Field(
        default=None,
        description="User-requested chart type from natural language parsing (bar, line, pie, scatter, table)",
    )
    row_limit: int = Field(
        default=100,
        ge=1,
        le=10000,
        description="Maximum number of rows to return (1-10000, default: 100)",
    )

    @validator('question')
    def question_not_empty(cls, v):
        """Validate and sanitize user question to prevent prompt injection"""
        if not v or not v.strip():
            raise ValueError('Question cannot be empty')

        # Sanitize input (removes control characters, normalizes whitespace)
        sanitized = sanitize_user_input(v)

        if not sanitized:
            raise ValueError('Question cannot be empty after sanitization')

        # Detect potential injection attempts
        is_suspicious, reason = detect_injection_attempt(sanitized)
        if is_suspicious:
            # Log but don't block - the sanitizer will clean it up
            # We log for security monitoring
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Suspicious input detected in question: {reason}")

        return sanitized


class AgentTraceStep(BaseModel):
    """Individual step in agent execution trace"""
    timestamp: str = Field(..., description="ISO timestamp when step occurred")
    elapsed_ms: float = Field(..., description="Milliseconds elapsed since trace start")
    type: str = Field(..., description="Type of step (analysis, planning, generation, etc.)")
    message: str = Field(..., description="Human-readable message describing the step")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata for this step")
    icon: str = Field(..., description="Emoji icon for UI display")


class AgentTrace(BaseModel):
    """Agent execution trace for observability"""
    steps: List[AgentTraceStep] = Field(
        default_factory=list,
        description="Sequence of steps in agent execution"
    )
    total_elapsed_ms: float = Field(..., description="Total execution time in milliseconds")
    start_time: str = Field(..., description="ISO timestamp when trace started")


class ResultAnalysis(BaseModel):
    """Natural language analysis of query results"""
    summary: str = Field(
        ...,
        description="1-2 sentence overview of the query results"
    )
    key_insights: List[str] = Field(
        default_factory=list,
        description="3-5 key findings, patterns, or observations from the results"
    )
    direct_answer: Optional[str] = Field(
        default=None,
        description="Direct answer to the user's question if applicable (e.g., for 'How many...' questions)"
    )
    confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Confidence score (0.0-1.0) indicating how confident the analysis is"
    )
    statistics: Dict[str, Any] = Field(
        default_factory=dict,
        description="Extracted statistics from the query results"
    )
    generated_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="ISO timestamp when the analysis was generated"
    )


class QueryResponse(BaseModel):
    """Response model for query results"""
    query_id: Optional[int] = Field(
        None,
        description="Query history ID"
    )
    question: str = Field(
        ...,
        description="Original natural language question"
    )
    sql: str = Field(
        ...,
        description="Generated SQL query"
    )
    is_valid: bool = Field(
        ...,
        description="Whether the SQL is valid"
    )
    is_read_only: bool = Field(
        ...,
        description="Whether the query is read-only"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Any warnings about the query"
    )
    results: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Query results (if executed)"
    )
    row_count: Optional[int] = Field(
        default=None,
        description="Number of rows returned"
    )
    execution_time_ms: Optional[float] = Field(
        default=None,
        description="Query execution time in milliseconds"
    )
    cached: bool = Field(
        default=False,
        description="Whether result was from cache"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Response timestamp"
    )
    # Option 2 Enhancement: Agent trace for observability
    agent_trace: Optional[AgentTrace] = Field(
        default=None,
        description="Agent execution trace showing decision-making process"
    )
    # Option 2 Enhancement: Query plan and correction attempts
    query_plan: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Query plan details (for complex queries)"
    )
    attempts: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Correction attempts with fix methods"
    )
    self_corrected: bool = Field(
        default=False,
        description="Whether the query was auto-corrected"
    )
    total_attempts: int = Field(
        default=1,
        description="Total number of execution attempts"
    )
    verification_warnings: List[str] = Field(
        default_factory=list,
        description="Warnings from result verification"
    )
    used_planning: bool = Field(
        default=False,
        description="Whether query planning was used"
    )
    conversation_context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Conversation context used for this query"
    )
    used_context: bool = Field(
        default=False,
        description="Whether conversational memory was used"
    )
    # Semantic caching fields
    cache_type: Optional[str] = Field(
        default=None,
        description="Type of cache hit: 'exact' or 'semantic'"
    )
    semantic_similarity: Optional[float] = Field(
        default=None,
        description="Similarity score for semantic cache hits (0.0-1.0)"
    )
    matched_question: Optional[str] = Field(
        default=None,
        description="Original question that matched in semantic cache"
    )
    # Intelligent Data Narratives
    result_analysis: Optional[ResultAnalysis] = Field(
        default=None,
        description="Natural language analysis and insights from query results"
    )
    # Chart Intent (Phase 8: Chart Intelligence)
    preferred_chart_type: Optional[str] = Field(
        default=None,
        description="User-requested chart type passed through from request (bar, line, pie, scatter, table)"
    )
    # Model tracking (Phase: Small Model Optimization)
    model_used: Optional[str] = Field(
        default=None,
        description="The LLM model that was actually used for SQL generation (may differ from default if per-task routing is enabled)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "query_id": 123,
                "question": "Show me all customers from California",
                "sql": "SELECT * FROM customers WHERE state = 'CA'",
                "is_valid": True,
                "is_read_only": True,
                "warnings": [],
                "results": [
                    {"id": 1, "name": "John Doe", "state": "CA"},
                    {"id": 2, "name": "Jane Smith", "state": "CA"}
                ],
                "row_count": 2,
                "execution_time_ms": 45.2,
                "cached": False,
                "timestamp": "2024-01-01T12:00:00"
            }
        }


class ExplainRequest(BaseModel):
    """Request model for SQL explanation"""
    sql: str = Field(
        ...,
        description="SQL query to explain",
        min_length=5,
    )
    schema: Optional[str] = Field(
        default=None,
        description="Database schema context"
    )


class ExplainResponse(BaseModel):
    """Response model for SQL explanation"""
    sql: str = Field(..., description="Original SQL query")
    explanation: str = Field(..., description="Natural language explanation")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class QueryHistoryResponse(BaseModel):
    """Response model for query history"""
    id: int
    natural_language_query: str
    generated_sql: str
    sql_validated: bool
    executed: bool
    execution_time_ms: Optional[float]
    result_count: Optional[int]
    error_message: Optional[str]
    database_type: Optional[str]
    model_used: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class HealthCheckResponse(BaseModel):
    """Response model for health check"""
    status: str = Field(..., description="Overall status")
    version: str = Field(..., description="API version")
    services: Dict[str, bool] = Field(
        ...,
        description="Status of individual services"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "services": {
                    "database": True,
                    "cache": True,
                    "llm": True
                },
                "timestamp": "2024-01-01T12:00:00"
            }
        }


class ErrorResponse(BaseModel):
    """Response model for errors"""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    class Config:
        json_schema_extra = {
            "example": {
                "error": "Invalid query",
                "detail": "Question cannot be empty",
                "timestamp": "2024-01-01T12:00:00"
            }
        }


class StatsResponse(BaseModel):
    """Response model for statistics"""
    total_queries: int = Field(..., description="Total number of queries")
    cached_queries: int = Field(..., description="Number of cached queries")
    average_execution_time_ms: Optional[float] = Field(
        None,
        description="Average query execution time"
    )
    top_queries: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Most frequent queries"
    )


# ============================================================================
# User Feedback Schemas
# ============================================================================

class FeedbackCreate(BaseModel):
    """Create user feedback on a query"""
    query_id: int = Field(..., description="ID of the query being corrected")
    feedback_type: str = Field(
        ...,
        description="Type of feedback: sql_correction, column_name, table_name, result_issue"
    )
    corrected_sql: Optional[str] = Field(None, description="Corrected SQL query")
    correction_description: Optional[str] = Field(
        None,
        description="Description of what was wrong and how it was fixed"
    )
    correction_details: Optional[Dict[str, Any]] = Field(
        None,
        description="Structured correction data (e.g., {'from': 'category', 'to': 'category_name'})"
    )
    user_notes: Optional[str] = Field(None, description="Additional user notes")
    user_confidence: float = Field(
        1.0,
        ge=0.0,
        le=1.0,
        description="User's confidence in the correction (0.0 to 1.0)"
    )

    @field_validator('feedback_type')
    @classmethod
    def validate_feedback_type(cls, v):
        valid_types = ['sql_correction', 'column_name', 'table_name', 'result_issue']
        if v not in valid_types:
            raise ValueError(f'feedback_type must be one of {valid_types}')
        return v


class FeedbackResponse(BaseModel):
    """User feedback response"""
    id: int
    query_id: int
    feedback_type: str
    original_sql: str
    corrected_sql: Optional[str]
    correction_description: Optional[str]
    correction_details: Optional[Dict[str, Any]]
    user_confidence: float
    applied_successfully: bool
    learned_correction_id: Optional[int]
    user_notes: Optional[str]
    created_at: datetime
    applied_at: Optional[datetime]

    class Config:
        from_attributes = True


class FeedbackApplyRequest(BaseModel):
    """Apply user feedback to learning system"""
    feedback_id: int = Field(..., description="ID of the feedback to apply")
    test_before_learning: bool = Field(
        True,
        description="Test the correction before adding to learning system"
    )


class FeedbackStatsResponse(BaseModel):
    """Feedback statistics"""
    total_feedback: int
    applied_to_learning: int
    pending: int
    by_type: Dict[str, int]


# ============================================================================
# System Settings Schemas
# ============================================================================

class SystemSettingsResponse(BaseModel):
    """System settings response"""
    id: int
    auto_learning_enabled: bool
    confidence_threshold: float
    apply_mode: str  # "immediate" or "deferred"
    test_before_learning: bool
    validation_mode: str  # "strict", "moderate", "lenient"
    require_result_comparison: bool
    enable_audit_log: bool
    max_audit_log_days: int
    query_quality_level: int  # 0-100 scale
    # Semantic Understanding Settings
    enable_intent_classification: bool  # Phase 1: Detect impossible queries
    enable_dynamic_examples: bool  # Phase 2: Schema-specific examples
    enable_semantic_validation: bool  # Phase 3: Post-generation validation

    # Per-Task Model Configuration (Small Model Optimization)
    model_sql_generation: Optional[str] = None  # Model for SQL generation
    model_narratives: Optional[str] = None  # Model for result narratives
    model_query_planning: Optional[str] = None  # Model for query planning
    model_error_correction: Optional[str] = None  # Model for error correction

    # Per-Task Timeout Configuration (seconds)
    timeout_sql_generation: int = 30
    timeout_narratives: int = 15
    timeout_query_planning: int = 20
    timeout_error_correction: int = 15

    # Small Model Optimization Feature Flags
    enable_query_templates: bool = True  # Bypass LLM for simple patterns
    enable_location_preprocessing: bool = True  # Normalize locations before LLM

    # Prompt Optimization (Phase 2.2)
    enable_prompt_optimization: bool = False  # OFF by default, user opt-in
    prompt_model_size: Optional[str] = "auto"  # auto|small|medium|large
    enable_schema_compression: bool = True  # Compress schema to relevant tables
    max_schema_tables: int = 10  # Max tables before compression
    enable_example_selection: bool = True  # Select relevant few-shot examples
    max_few_shot_examples: int = 3  # Max examples to include

    @field_validator('prompt_model_size', mode='before')
    @classmethod
    def default_prompt_model_size(cls, v):
        """Handle NULL values from database by providing default"""
        return v if v is not None else "auto"

    # Multi-Database Query Intelligence (Phase 2.4)
    enable_multi_db_validation: bool = True  # Pre-flight schema validation
    multi_db_validation_threshold: float = 0.6  # Fuzzy match threshold for alternatives

    # Phase 12: Lineage Intelligence Model Configuration
    model_lineage_narrative: Optional[str] = None  # Model for lineage explanations
    model_impact_analysis: Optional[str] = None  # Model for impact advisor
    model_schema_health: Optional[str] = None  # Model for schema health analysis
    model_lineage_conversation: Optional[str] = None  # Model for lineage chat
    model_pattern_intelligence: Optional[str] = None  # Model for pattern analysis

    # Phase 12: Lineage Intelligence Timeout Configuration
    timeout_lineage_narrative: int = 15
    timeout_impact_analysis: int = 20
    timeout_schema_health: int = 30
    timeout_lineage_conversation: int = 15
    timeout_pattern_intelligence: int = 20

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SystemSettingsUpdateRequest(BaseModel):
    """Update system settings"""
    auto_learning_enabled: Optional[bool] = None
    confidence_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    apply_mode: Optional[str] = Field(None, pattern="^(immediate|deferred)$")
    test_before_learning: Optional[bool] = None
    validation_mode: Optional[str] = Field(None, pattern="^(strict|moderate|lenient)$")
    require_result_comparison: Optional[bool] = None
    enable_audit_log: Optional[bool] = None
    max_audit_log_days: Optional[int] = Field(None, ge=1, le=365)
    query_quality_level: Optional[int] = Field(None, ge=0, le=100)
    # Semantic Understanding Settings
    enable_intent_classification: Optional[bool] = None  # Phase 1
    enable_dynamic_examples: Optional[bool] = None  # Phase 2
    enable_semantic_validation: Optional[bool] = None  # Phase 3

    # Per-Task Model Configuration (Small Model Optimization)
    model_sql_generation: Optional[str] = None  # Model for SQL generation
    model_narratives: Optional[str] = None  # Model for result narratives
    model_query_planning: Optional[str] = None  # Model for query planning
    model_error_correction: Optional[str] = None  # Model for error correction

    # Per-Task Timeout Configuration (seconds)
    timeout_sql_generation: Optional[int] = Field(None, ge=1, le=300)
    timeout_narratives: Optional[int] = Field(None, ge=1, le=300)
    timeout_query_planning: Optional[int] = Field(None, ge=1, le=300)
    timeout_error_correction: Optional[int] = Field(None, ge=1, le=300)

    # Small Model Optimization Feature Flags
    enable_query_templates: Optional[bool] = None  # Bypass LLM for simple patterns
    enable_location_preprocessing: Optional[bool] = None  # Normalize locations before LLM

    # Prompt Optimization (Phase 2.2)
    enable_prompt_optimization: Optional[bool] = None  # Toggle for prompt optimization
    prompt_model_size: Optional[str] = Field(None, pattern="^(auto|small|medium|large)$")
    enable_schema_compression: Optional[bool] = None  # Compress schema to relevant tables
    max_schema_tables: Optional[int] = Field(None, ge=1, le=50)  # Max tables before compression
    enable_example_selection: Optional[bool] = None  # Select relevant few-shot examples
    max_few_shot_examples: Optional[int] = Field(None, ge=0, le=10)  # Max examples to include

    # Multi-Database Query Intelligence (Phase 2.4)
    enable_multi_db_validation: Optional[bool] = None  # Pre-flight schema validation
    multi_db_validation_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)  # Fuzzy match threshold

    # Phase 12: Lineage Intelligence Model Configuration
    model_lineage_narrative: Optional[str] = None  # Model for lineage explanations
    model_impact_analysis: Optional[str] = None  # Model for impact advisor
    model_schema_health: Optional[str] = None  # Model for schema health analysis
    model_lineage_conversation: Optional[str] = None  # Model for lineage chat
    model_pattern_intelligence: Optional[str] = None  # Model for pattern analysis

    # Phase 12: Lineage Intelligence Timeout Configuration
    timeout_lineage_narrative: Optional[int] = Field(None, ge=1, le=300)
    timeout_impact_analysis: Optional[int] = Field(None, ge=1, le=300)
    timeout_schema_health: Optional[int] = Field(None, ge=1, le=300)
    timeout_lineage_conversation: Optional[int] = Field(None, ge=1, le=300)
    timeout_pattern_intelligence: Optional[int] = Field(None, ge=1, le=300)


# ============================================================================
# Data Lineage Schemas (Phase 11)
# ============================================================================

class LineageNodeSchema(BaseModel):
    """A node in the lineage graph."""
    id: str
    node_type: str  # source_table, source_column, transformation, output_column
    label: str
    table_name: Optional[str] = None
    column_name: Optional[str] = None
    expression: Optional[str] = None
    transformation_type: Optional[str] = None  # direct, aggregation, expression, function


class LineageEdgeSchema(BaseModel):
    """An edge in the lineage graph."""
    source_id: str
    target_id: str
    edge_type: str = "data_flow"
    label: Optional[str] = None


class LineageParseRequest(BaseModel):
    """Request to parse SQL for lineage."""
    sql: str = Field(
        ...,
        description="SQL query to parse for lineage",
        min_length=1,
        max_length=10000,
    )
    connection_id: Optional[int] = Field(
        default=None,
        description="Optional connection ID for context",
    )
    question: Optional[str] = Field(
        default=None,
        description="Original natural language question (for narrative context)",
        max_length=1000,
    )


class TransformationExplanationSchema(BaseModel):
    """Explanation of a transformation in the lineage graph."""
    node_id: str
    transformation_type: str
    input_columns: List[str] = Field(default_factory=list)
    output_column: str
    explanation: str
    business_meaning: Optional[str] = None


class LineageNarrativeSchema(BaseModel):
    """LLM-generated narrative explanation of lineage (Phase 12.1)."""
    summary: str
    data_flow_description: str = ""
    column_explanations: Dict[str, str] = Field(default_factory=dict)
    transformations_explained: List[TransformationExplanationSchema] = Field(default_factory=list)
    business_context: Dict[str, str] = Field(default_factory=dict)
    potential_issues: List[str] = Field(default_factory=list)
    confidence: float = 0.5
    generated_at: Optional[str] = None


class LineageGraphResponse(BaseModel):
    """Response with the parsed lineage graph."""
    nodes: List[LineageNodeSchema] = Field(default_factory=list)
    edges: List[LineageEdgeSchema] = Field(default_factory=list)
    sql: str = ""
    tables_used: List[str] = Field(default_factory=list)
    columns_used: List[str] = Field(default_factory=list)
    output_columns: List[str] = Field(default_factory=list)
    narrative: Optional[LineageNarrativeSchema] = None  # Phase 12.1: LLM narrative


class ImpactedQuerySchema(BaseModel):
    """A query affected by a schema change."""
    query_id: int
    natural_language_query: str
    generated_sql: str
    impact_type: str
    risk_level: str


class ImpactAnalysisRequest(BaseModel):
    """Request to analyze impact of a schema change."""
    table_name: str = Field(
        ...,
        description="Table being changed",
        min_length=1,
        max_length=255,
    )
    column_name: Optional[str] = Field(
        default=None,
        description="Column being changed (optional - if omitted, analyzes table-level impact)",
        max_length=255,
    )


class ImpactAnalysisResponse(BaseModel):
    """Response with impact analysis results."""
    changed_object: str
    object_type: str  # "table" or "column"
    impacted_queries: List[ImpactedQuerySchema] = Field(default_factory=list)
    total_affected: int = 0
    risk_level: str = "low"
    risk_counts: Dict[str, int] = Field(default_factory=lambda: {"low": 0, "medium": 0, "high": 0})
    summary: str = ""


class LineageStatsResponse(BaseModel):
    """Basic lineage statistics."""
    total_queries: int = 0
    unique_tables_referenced: int = 0
    tables: List[str] = Field(default_factory=list)


# ============================================================================
# Query Pattern Analytics Schemas (Phase 11.5)
# ============================================================================

class TableUsageEntrySchema(BaseModel):
    """Usage details for a single table."""
    table_name: str
    query_count: int
    join_count: int = 0
    avg_execution_time_ms: Optional[float] = None
    last_used_at: Optional[datetime] = None


class JoinPatternSchema(BaseModel):
    """A frequently observed JOIN pattern."""
    table_a: str
    table_b: str
    join_count: int
    sample_sql: str = ""
    avg_execution_time_ms: Optional[float] = None


class PerformanceBottleneckSchema(BaseModel):
    """A performance bottleneck table."""
    table_name: str
    query_count: int
    avg_execution_time_ms: float
    max_execution_time_ms: float
    bottleneck_score: float


class HeatmapDataResponse(BaseModel):
    """Complete heatmap response for query pattern visualization."""
    table_usage: List[TableUsageEntrySchema] = Field(default_factory=list)
    join_patterns: List[JoinPatternSchema] = Field(default_factory=list)
    bottlenecks: List[PerformanceBottleneckSchema] = Field(default_factory=list)
    time_range_days: Optional[int] = None
    total_queries_analyzed: int = 0
    connection_id: Optional[int] = None


# ============================================================================
# Impact Advisor Schemas (Phase 12.2)
# ============================================================================

class SQLPatchSchema(BaseModel):
    """A suggested SQL modification for an impacted query."""
    query_id: int
    original_sql: str
    patched_sql: str
    change_description: str
    confidence: float = 0.8
    requires_review: bool = False


class MigrationStepSchema(BaseModel):
    """A single step in a migration plan."""
    step_number: int
    action: str
    description: str
    sql: Optional[str] = None
    reversible: bool = True
    risk_level: str = "low"


class MigrationPlanSchema(BaseModel):
    """Complete migration plan for a schema change."""
    change_type: str
    target_object: str
    new_value: Optional[str] = None
    steps: List[MigrationStepSchema] = Field(default_factory=list)
    estimated_downtime: str = "none"
    rollback_possible: bool = True
    warnings: List[str] = Field(default_factory=list)
    generated_at: Optional[str] = None


class RiskExplanationSchema(BaseModel):
    """LLM-generated explanation of why a change is risky."""
    risk_level: str
    summary: str
    detailed_explanation: str
    affected_areas: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    confidence: float = 0.8


class ImpactAdviceRequest(BaseModel):
    """Request for LLM-enhanced impact analysis."""
    change_type: str = Field(
        ...,
        description="Type of change: rename_column, rename_table, drop_column, drop_table, change_type",
    )
    table_name: str = Field(
        ...,
        description="Table being modified",
        min_length=1,
        max_length=255,
    )
    column_name: Optional[str] = Field(
        default=None,
        description="Column being modified (for column-level changes)",
        max_length=255,
    )
    new_value: Optional[str] = Field(
        default=None,
        description="New name or type (for renames/type changes)",
        max_length=255,
    )
    include_patches: bool = Field(
        default=True,
        description="Whether to generate SQL patches for affected queries",
    )


class ImpactAdviceResponse(BaseModel):
    """Complete LLM-enhanced impact analysis with recommendations."""
    # Base impact
    impact: ImpactAnalysisResponse
    change_type: str
    new_value: Optional[str] = None

    # LLM-generated content
    risk_explanation: Optional[RiskExplanationSchema] = None
    migration_plan: Optional[MigrationPlanSchema] = None
    sql_patches: List[SQLPatchSchema] = Field(default_factory=list)

    # Metadata
    generated_at: Optional[str] = None
    llm_used: bool = False


# ============================================================================
# Schema Health Analyzer Schemas (Phase 12.3)
# ============================================================================

class IndexSuggestionSchema(BaseModel):
    """A suggested index to improve query performance."""
    table_name: str
    columns: List[str]
    index_type: str = "btree"
    reason: str = ""
    estimated_impact: str = "medium"
    create_sql: str = ""
    query_count_benefiting: int = 0


class SchemaIssueSchema(BaseModel):
    """A detected schema issue or anti-pattern."""
    category: str
    severity: str
    title: str
    description: str
    affected_objects: List[str] = Field(default_factory=list)
    recommendation: str = ""
    fix_sql: Optional[str] = None


class NormalizationIssueSchema(BaseModel):
    """A normalization violation."""
    table_name: str
    issue_type: str
    description: str
    affected_columns: List[str] = Field(default_factory=list)
    recommendation: str = ""


class TableHealthSummarySchema(BaseModel):
    """Health summary for a single table."""
    table_name: str
    column_count: int
    has_primary_key: bool
    foreign_key_count: int
    index_count: int
    issues: List[SchemaIssueSchema] = Field(default_factory=list)
    suggestions: List[IndexSuggestionSchema] = Field(default_factory=list)


class SchemaHealthReportSchema(BaseModel):
    """Complete schema health analysis report."""
    connection_id: int
    database_name: str
    grade: str = "B"
    score: int = 75
    table_count: int = 0
    total_issues: int = 0
    critical_issues: int = 0

    # Detailed findings
    index_suggestions: List[IndexSuggestionSchema] = Field(default_factory=list)
    normalization_issues: List[NormalizationIssueSchema] = Field(default_factory=list)
    anti_patterns: List[SchemaIssueSchema] = Field(default_factory=list)
    table_summaries: List[TableHealthSummarySchema] = Field(default_factory=list)

    # LLM-generated summary
    summary: str = ""
    recommendations: List[str] = Field(default_factory=list)

    # Metadata
    analyzed_at: Optional[str] = None
    llm_used: bool = False


# ============================================================================
# Pattern Intelligence Schemas (Phase 12.4)
# ============================================================================

class BottleneckAnalysisSchema(BaseModel):
    """LLM-enhanced analysis of a performance bottleneck."""
    table_name: str
    bottleneck_score: float
    root_causes: List[str] = Field(default_factory=list)
    contributing_factors: List[str] = Field(default_factory=list)
    optimization_suggestions: List[str] = Field(default_factory=list)
    estimated_improvement: str = "medium"
    sample_slow_queries: List[str] = Field(default_factory=list)
    confidence: float = 0.0


class OptimizationSuggestionSchema(BaseModel):
    """A suggested optimization for query patterns."""
    category: str  # "index", "query_rewrite", "caching", "schema"
    title: str
    description: str
    affected_tables: List[str] = Field(default_factory=list)
    estimated_impact: str = "medium"
    implementation_sql: Optional[str] = None
    priority: int = 0


class QueryAntiPatternSchema(BaseModel):
    """A detected query anti-pattern."""
    pattern_type: str
    severity: str
    title: str
    description: str
    affected_queries: List[int] = Field(default_factory=list)
    sample_sql: str = ""
    recommendation: str = ""
    occurrence_count: int = 0


class UsageTrendSchema(BaseModel):
    """Trend data for a table's usage over time."""
    table_name: str
    period: str = "daily"
    data_points: List[Dict[str, Any]] = Field(default_factory=list)
    trend_direction: str = "stable"
    change_percentage: float = 0.0


class TrendAnalysisSchema(BaseModel):
    """Complete trend analysis for a connection."""
    connection_id: int
    time_range_days: int
    table_trends: List[UsageTrendSchema] = Field(default_factory=list)
    busiest_tables: List[str] = Field(default_factory=list)
    emerging_tables: List[str] = Field(default_factory=list)
    declining_tables: List[str] = Field(default_factory=list)
    summary: str = ""


class PatternIntelligenceReportSchema(BaseModel):
    """Complete pattern intelligence report."""
    connection_id: int
    bottleneck_analyses: List[BottleneckAnalysisSchema] = Field(default_factory=list)
    optimization_suggestions: List[OptimizationSuggestionSchema] = Field(default_factory=list)
    anti_patterns: List[QueryAntiPatternSchema] = Field(default_factory=list)
    trend_analysis: Optional[TrendAnalysisSchema] = None
    summary: str = ""
    recommendations: List[str] = Field(default_factory=list)
    analyzed_at: Optional[str] = None
    llm_used: bool = False


# =============================================================================
# Phase 12.5: Conversational Lineage Schemas
# =============================================================================

class LineageQuestionRequest(BaseModel):
    """Request model for asking lineage questions."""
    question: str = Field(
        ...,
        description="Natural language question about lineage, schema, or patterns",
        min_length=3,
        max_length=500,
    )
    connection_id: int = Field(
        ...,
        description="Database connection ID",
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Session ID for multi-turn conversation context",
    )

    @validator('question')
    def question_not_empty(cls, v):
        """Validate and sanitize user question."""
        if not v or not v.strip():
            raise ValueError('Question cannot be empty')
        sanitized = sanitize_user_input(v)
        if not sanitized:
            raise ValueError('Question cannot be empty after sanitization')
        return sanitized


class LineageAnswerSchema(BaseModel):
    """Response model for lineage questions."""
    question: str
    question_type: str = Field(
        ...,
        description="Classified question type (lineage, impact, pattern, schema, recommendation, general)",
    )
    answer: str = Field(
        ...,
        description="Natural language answer to the question",
    )
    supporting_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Supporting data that informed the answer",
    )
    related_tables: List[str] = Field(
        default_factory=list,
        description="Tables related to the answer",
    )
    related_queries: List[int] = Field(
        default_factory=list,
        description="Query IDs related to the answer",
    )
    confidence: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Confidence score for the answer",
    )
    follow_up_suggestions: List[str] = Field(
        default_factory=list,
        description="Suggested follow-up questions",
    )
    generated_at: Optional[str] = None
    llm_used: bool = False


# =============================================================================
# Phase 13: File Source Schemas (CSV & Excel Support)
# =============================================================================

class FileSourceCreate(BaseModel):
    """Request model for file upload metadata."""
    name: Optional[str] = Field(
        default=None,
        description="Display name for the file source (defaults to filename)",
        max_length=255,
    )
    sheet_name: Optional[str] = Field(
        default=None,
        description="For Excel files, the sheet to use (defaults to first sheet)",
        max_length=255,
    )
    chat_session_id: Optional[str] = Field(
        default=None,
        description="Chat session to associate file with (optional)",
    )
    is_global: bool = Field(
        default=False,
        description="Make file available across all sessions",
    )


class FileColumnInfo(BaseModel):
    """Column information from file schema inference."""
    name: str = Field(..., description="Column name")
    type: str = Field(..., description="Inferred SQL type (e.g., VARCHAR, INTEGER, DOUBLE, DATE)")
    nullable: bool = Field(default=True, description="Whether the column allows NULL values")
    sample_values: List[Any] = Field(
        default_factory=list,
        description="Sample values from this column (up to 5)",
    )


class FileSchemaResponse(BaseModel):
    """Response with inferred file schema."""
    columns: List[FileColumnInfo] = Field(
        default_factory=list,
        description="Column definitions inferred from file",
    )
    row_count: int = Field(
        default=0,
        description="Total number of rows in the file",
    )
    sample_values: Dict[str, List[Any]] = Field(
        default_factory=dict,
        description="Sample values per column",
    )


class FileSourceResponse(BaseModel):
    """Response model for file source details."""
    id: int
    name: str
    original_filename: str
    file_type: str  # 'csv', 'xlsx', 'xls'
    file_size_bytes: int
    processing_status: str  # 'pending', 'processing', 'ready', 'error'
    processing_error: Optional[str] = None
    schema: Optional[FileSchemaResponse] = None
    row_count: Optional[int] = None
    sheet_name: Optional[str] = None
    duckdb_table_name: Optional[str] = None
    is_global: bool = False
    chat_session_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class FilePreviewResponse(BaseModel):
    """Response for file data preview."""
    file_id: int
    file_name: str
    columns: List[str] = Field(
        default_factory=list,
        description="Column names in order",
    )
    data: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Preview rows as list of dicts",
    )
    row_count: int = Field(
        default=0,
        description="Number of rows in preview",
    )
    total_rows: int = Field(
        default=0,
        description="Total rows in file",
    )
    truncated: bool = Field(
        default=False,
        description="Whether preview was truncated",
    )


class ExcelSheetsResponse(BaseModel):
    """Response for Excel sheet listing."""
    file_name: str
    sheets: List[str] = Field(
        default_factory=list,
        description="List of sheet names in the Excel file",
    )


class FileSourceListResponse(BaseModel):
    """Response for listing file sources."""
    files: List[FileSourceResponse] = Field(
        default_factory=list,
        description="List of file sources",
    )
    total: int = Field(
        default=0,
        description="Total number of files",
    )
