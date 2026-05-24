"""Pydantic schemas for API requests and responses

Note on schema location: most request/response models live here, but a few
endpoint-local schemas are intentionally co-located with their routers when
they're a private contract for that one endpoint:

- Auth (`UserCreate`, `UserLogin`, `UserResponse`, `TokenResponse`) →
  `src/auth/schemas.py` — kept next to the auth service so the password
  complexity validator and the User model travel together.
- Admin user CRUD (`AdminUserCreate`, `AdminUserUpdate`, `AdminUserResponse`,
  `AdminUserListResponse`, `AdminPasswordResetResponse`) →
  `src/api/endpoints/admin_users.py` — only used by the Phase 24.7 admin
  router and gated by `ADMIN_UI_ENABLED`.
"""
from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field, validator, field_validator, model_validator

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

    # Server-level auth configuration (read-only, from environment)
    require_auth: bool = False

    # Server-level observability configuration (read-only, from environment).
    # Phase 24 admin UI uses these to render deep-links and feature gates.
    metrics_enabled: bool = False
    metrics_endpoint_exposed: bool = False
    metrics_public_url: Optional[str] = None
    otel_enabled: bool = False
    otel_service_name: Optional[str] = None
    otel_traces_sampler_ratio: Optional[float] = None
    jaeger_ui_url: Optional[str] = None
    grafana_url: Optional[str] = None

    # Hard kill-switch for the Phase 24 admin UI as a whole.
    admin_ui_enabled: bool = True

    # Auth hardening flags (read-only mirror of Settings; Admin UI surfaces
    # these so an operator can tell at a glance which protections are live).
    # Only populated for admin callers — leaking lockout thresholds /
    # rate-limit windows to anonymous visitors helps an attacker tune
    # credential-stuffing under the threshold. See PASSWORD_AUTH_HARDENING_PLAN.md.
    auth_token_versioning_enabled: Optional[bool] = None
    auth_invalidate_tokens_on_deactivate: Optional[bool] = None
    auth_invalidate_tokens_on_logout: Optional[bool] = None
    auth_rate_limit_change_password: Optional[bool] = None
    auth_change_password_per_user_per_minute: Optional[int] = None
    auth_rate_limit_login_lockout_enabled: Optional[bool] = None
    auth_login_lockout_threshold: Optional[int] = None
    auth_login_lockout_window_seconds: Optional[int] = None
    auth_password_reset_mode: Optional[str] = None
    auth_password_reset_token_ttl_minutes: Optional[int] = None
    auth_password_reset_base_url: Optional[str] = None
    auth_password_history_depth: Optional[int] = None
    auth_require_admin_quorum: Optional[bool] = None

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
# LLM Usage Monitoring Schemas (Phase 16)
# ============================================================================

class LLMUsageResponse(BaseModel):
    """Single LLM usage record."""
    id: int
    agent_type: str
    agent_name: Optional[str] = None
    provider: str = "ollama"
    model_name: str
    llm_method: str
    input_tokens: int
    output_tokens: int
    total_tokens: int = 0
    token_estimation_method: str
    response_time_ms: Optional[float] = None
    estimated_cost_usd: Optional[float] = None
    success: bool
    error_message: Optional[str] = None
    created_at: datetime

    def model_post_init(self, __context: Any) -> None:
        if not self.total_tokens:
            self.total_tokens = self.input_tokens + self.output_tokens

    class Config:
        from_attributes = True


class LLMUsageStatsResponse(BaseModel):
    """Overall usage statistics."""
    period_days: int
    total_calls: int
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    avg_response_time_ms: Optional[float] = None
    unique_sessions: int
    models_used: int
    total_cost_usd: float = 0.0


class LLMUsageByAgentResponse(BaseModel):
    """Usage breakdown by agent type."""
    agent_type: str
    total_calls: int
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    avg_response_time_ms: Optional[float] = None


class LLMUsageByModelResponse(BaseModel):
    """Usage breakdown by model."""
    model_name: str
    total_calls: int
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    avg_response_time_ms: Optional[float] = None


class LLMUsageByProviderResponse(BaseModel):
    """Usage breakdown by provider."""
    provider: str
    total_calls: int
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    avg_response_time_ms: Optional[float] = None
    total_cost_usd: float = 0.0


class LLMUsageTimeSeriesResponse(BaseModel):
    """Time series data point."""
    period: str
    total_calls: int
    total_tokens: int


class SessionUsageSummaryResponse(BaseModel):
    """Usage summary for a chat session."""
    session_id: str
    total_calls: int
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    avg_response_time_ms: Optional[float] = None
    first_call: Optional[str] = None
    last_call: Optional[str] = None
    total_cost_usd: float = 0.0
    by_agent: Dict[str, int] = Field(default_factory=dict)


class InlineUsageStats(BaseModel):
    """Lightweight stats for inline display in chat."""
    tokens_used: int
    llm_calls: int
    response_time_ms: float
    agents_involved: List[str]


# ============================================================================
# Multi-Provider Monitoring Schemas (Phase 17)
# ============================================================================

class ModelConfigResponse(BaseModel):
    """Model pricing configuration."""
    id: int
    model_name: str
    display_name: Optional[str] = None
    provider: str
    cost_per_1m_input_tokens: Optional[float] = None
    cost_per_1m_output_tokens: Optional[float] = None
    is_active: bool = True

    class Config:
        from_attributes = True


class ModelConfigCreateRequest(BaseModel):
    """Request to create/update a model pricing config."""
    model_name: str = Field(..., min_length=1, max_length=100)
    provider: str = Field(..., min_length=1, max_length=50)
    cost_per_1m_input_tokens: float = Field(..., ge=0)
    cost_per_1m_output_tokens: float = Field(..., ge=0)
    display_name: Optional[str] = Field(default=None, max_length=100)


class UnpricedModelResponse(BaseModel):
    """A model seen in usage but missing pricing config."""
    model_name: str
    provider: str
    call_count: int
    total_tokens: int


class DailyCostEntry(BaseModel):
    """A single day's cost data."""
    date: str
    cost_usd: float
    calls: int
    tokens: int


class CostSummaryResponse(BaseModel):
    """Cost summary across all providers."""
    period_days: int
    total_cost_usd: float
    total_tokens: int
    total_calls: int
    avg_cost_per_call: float
    daily_costs: List[DailyCostEntry]
    by_provider: Dict[str, float]


class ProviderAgentStats(BaseModel):
    """Stats for one provider within one agent type."""
    calls: int
    avg_latency_ms: Optional[float] = None
    total_cost_usd: float
    avg_tokens_per_call: Optional[float] = None
    success_rate: float


class ProviderComparisonResponse(BaseModel):
    """Provider comparison grouped by agent type."""
    period_days: int
    by_agent_type: Dict[str, Dict[str, ProviderAgentStats]]


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


# ============================================================================
# Phase 20: Migration Toolkit Schemas
# ============================================================================

class SchemaDiffRequest(BaseModel):
    """Request to compare two database schemas."""
    source_connection_id: int = Field(..., description="Source database connection ID")
    target_connection_id: int = Field(..., description="Target database connection ID")
    name: Optional[str] = Field(None, description="Project name (required if saving)")
    save: bool = Field(False, description="Whether to save as a MigrationProject")
    include_views: bool = Field(False, description="Include views in comparison")
    include_sequences: bool = Field(False, description="Include sequences in comparison")
    include_check_constraints: bool = Field(False, description="Include check constraints in comparison")
    include_routines: bool = Field(False, description="Include stored procedures/functions in comparison")
    include_triggers: bool = Field(False, description="Include triggers in comparison")
    include_enums: bool = Field(False, description="Include enum types in comparison")

    @model_validator(mode="after")
    def source_and_target_must_differ(self) -> "SchemaDiffRequest":
        if self.source_connection_id == self.target_connection_id:
            raise ValueError("source_connection_id and target_connection_id must be different")
        return self


class ColumnDiffSchema(BaseModel):
    table_name: str
    column_name: str
    diff_type: str
    source_state: Optional[Dict[str, Any]] = None
    target_state: Optional[Dict[str, Any]] = None
    is_breaking: bool = False
    risk_level: str = "low"


class ConstraintDiffSchema(BaseModel):
    table_name: str
    constraint_type: str
    diff_type: str
    source_state: Optional[Any] = None
    target_state: Optional[Any] = None
    risk_level: str = "low"


class TableDiffSchema(BaseModel):
    table_name: str
    diff_type: str
    column_diffs: List[ColumnDiffSchema] = Field(default_factory=list)
    constraint_diffs: List[ConstraintDiffSchema] = Field(default_factory=list)
    risk_level: str = "low"


class ViewDiffSchema(BaseModel):
    view_name: str
    diff_type: str
    source_definition: Optional[str] = None
    target_definition: Optional[str] = None
    risk_level: str = "low"


class SequenceDiffSchema(BaseModel):
    sequence_name: str
    diff_type: str
    source_state: Optional[Dict[str, Any]] = None
    target_state: Optional[Dict[str, Any]] = None
    risk_level: str = "low"


class CheckConstraintDiffSchema(BaseModel):
    table_name: str
    constraint_name: str
    diff_type: str
    source_definition: Optional[str] = None
    target_definition: Optional[str] = None
    risk_level: str = "low"


class RoutineDiffSchema(BaseModel):
    routine_name: str
    routine_type: str
    diff_type: str
    source_definition: Optional[str] = None
    target_definition: Optional[str] = None
    risk_level: str = "medium"


class TriggerDiffSchema(BaseModel):
    trigger_name: str
    table_name: str
    diff_type: str
    source_definition: Optional[str] = None
    target_definition: Optional[str] = None
    risk_level: str = "medium"


class EnumDiffSchema(BaseModel):
    enum_name: str
    diff_type: str
    source_values: Optional[List[str]] = None
    target_values: Optional[List[str]] = None
    risk_level: str = "low"


class SchemaDiffResponse(BaseModel):
    source_connection_id: Optional[int] = None
    target_connection_id: Optional[int] = None
    source_fingerprint: str = ""
    target_fingerprint: str = ""
    table_diffs: List[TableDiffSchema] = Field(default_factory=list)
    view_diffs: List[ViewDiffSchema] = Field(default_factory=list)
    sequence_diffs: List[SequenceDiffSchema] = Field(default_factory=list)
    check_constraint_diffs: List[CheckConstraintDiffSchema] = Field(default_factory=list)
    routine_diffs: List[RoutineDiffSchema] = Field(default_factory=list)
    trigger_diffs: List[TriggerDiffSchema] = Field(default_factory=list)
    enum_diffs: List[EnumDiffSchema] = Field(default_factory=list)
    total_breaking_changes: int = 0
    total_safe_changes: int = 0
    overall_risk: str = "none"
    diff_summary: str = ""
    compared_at: str = ""
    project_id: Optional[int] = None


class MigrationProjectSummary(BaseModel):
    id: int
    name: str
    source_connection_id: Optional[int] = None
    target_connection_id: Optional[int] = None
    source_connection_name: Optional[str] = None
    target_connection_name: Optional[str] = None
    overall_risk: Optional[str] = None
    status: str = "draft"
    target_dialect: Optional[str] = None
    created_at: str
    updated_at: str


class MigrationProjectDetail(MigrationProjectSummary):
    diff_snapshot: Optional[Dict[str, Any]] = None
    migration_plan: Optional[Dict[str, Any]] = None
    data_migration_plan: Optional[Dict[str, Any]] = None
    up_sql: Optional[str] = None
    down_sql: Optional[str] = None
    verify_sql: Optional[str] = None
    notes: Optional[str] = None


class MigrationToolkitStepSchema(BaseModel):
    """A single step in a Phase 20 migration toolkit plan.

    Distinct from MigrationStepSchema (used by ImpactAdvisor).
    """
    step_number: int
    action: str
    description: str
    sql_hint: Optional[str] = None
    table_name: Optional[str] = None
    object_type: str = "table"
    lock_type: str = "none"
    estimated_duration: str = "instant"
    risk_level: str = "low"
    is_reversible: bool = True
    depends_on: List[int] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class MigrationPlanResponse(BaseModel):
    project_id: int
    steps: List[MigrationToolkitStepSchema] = Field(default_factory=list)
    execution_order: List[str] = Field(default_factory=list)
    total_estimated_downtime: str = "unknown"
    recommended_maintenance_window: bool = False
    pre_migration_checklist: List[str] = Field(default_factory=list)
    post_migration_checklist: List[str] = Field(default_factory=list)
    rollback_strategy: str = ""
    overall_complexity: str = "simple"
    llm_used: bool = False
    generated_at: str = ""


class GenerateScriptsRequest(BaseModel):
    target_dialect: str = Field(
        ...,
        description="Target SQL dialect",
        pattern=r"^(postgresql|mysql|sqlite|mssql|oracle|duckdb)$",
    )
    include_views: bool = Field(False, description="Include views in scripts")
    include_sequences: bool = Field(False, description="Include sequences in scripts")
    include_check_constraints: bool = Field(False, description="Include check constraints in scripts")
    include_routines: bool = Field(False, description="Include stored procedures/functions in scripts")
    include_triggers: bool = Field(False, description="Include triggers in scripts")
    include_enums: bool = Field(False, description="Include enum types in scripts")


class GeneratedScriptsResponse(BaseModel):
    project_id: int
    target_dialect: str
    up_sql: str = ""
    down_sql: str = ""
    verify_sql: str = ""
    warnings: List[str] = Field(default_factory=list)
    generated_at: str = ""


class BackupScriptRequest(BaseModel):
    """Request to generate backup/restore scripts for a single database."""
    connection_id: int = Field(..., description="Database connection ID")
    dialect: Optional[str] = Field(
        None,
        description="Target dialect (defaults to the connection's database_type)",
        pattern=r"^(postgresql|mysql|sqlite|mssql|oracle|duckdb)?$",
    )
    include_views: bool = Field(False, description="Include views in backup")
    include_sequences: bool = Field(False, description="Include sequences in backup")
    include_check_constraints: bool = Field(False, description="Include check constraints in backup")
    include_routines: bool = Field(False, description="Include stored procedures/functions in backup")
    include_triggers: bool = Field(False, description="Include triggers in backup")
    include_enums: bool = Field(False, description="Include enum types in backup")


class BackupScriptResponse(BaseModel):
    connection_id: int
    connection_name: str = ""
    dialect: str = ""
    backup_sql: str = ""
    restore_sql: str = ""
    verify_sql: str = ""
    table_count: int = 0
    warnings: List[str] = Field(default_factory=list)
    generated_at: str = ""


class ColumnMappingSchema(BaseModel):
    source_col: Optional[str] = None
    target_col: str
    transform_expression: str = ""
    requires_llm: bool = False


class TableDataMigrationSchema(BaseModel):
    source_table: str
    target_table: str
    column_mappings: List[ColumnMappingSchema] = Field(default_factory=list)
    insert_sql: str = ""
    batched_insert_sql: str = ""
    count_verify_sql: str = ""
    warnings: List[str] = Field(default_factory=list)


class DataMigrationPlanResponse(BaseModel):
    project_id: int
    table_migrations: List[TableDataMigrationSchema] = Field(default_factory=list)
    batch_size: int = 1000
    recommended_order: List[str] = Field(default_factory=list)
    total_tables_with_data: int = 0
    llm_used: bool = False
    generated_at: str = ""


# ============================================================================
# Performance Guru Schemas (Phase 22)
# ============================================================================

def _validate_explain_sql(v: str) -> str:
    """Shared validator: block DDL/DML and multi-statement queries for EXPLAIN endpoints."""
    stripped = v.strip()
    upper = stripped.upper()
    for keyword in ("DROP ", "TRUNCATE ", "DELETE ", "UPDATE ", "INSERT ", "ALTER ", "CREATE "):
        if upper.startswith(keyword):
            raise ValueError("Performance analysis only supports SELECT queries")
    if ";" in stripped:
        raise ValueError("Multi-statement queries are not allowed")
    return v


class PerformanceAnalysisRequest(BaseModel):
    """Request to analyze query performance via EXPLAIN."""
    sql: str = Field(..., min_length=1, max_length=20000, description="SQL query to analyze")
    connection_id: int = Field(..., description="Database connection to run EXPLAIN on")
    run_analyze: bool = Field(
        default=False,
        description="Run EXPLAIN ANALYZE (actually executes the query). Requires explicit opt-in.",
    )
    include_schema_context: bool = Field(default=True, description="Include schema context for LLM")
    model: Optional[str] = Field(default=None, description="Override LLM model for analysis")

    @field_validator("sql")
    @classmethod
    def validate_sql_is_select(cls, v: str) -> str:
        return _validate_explain_sql(v)


class ExplainOnlyRequest(BaseModel):
    """Request for raw EXPLAIN plan without LLM interpretation."""
    sql: str = Field(..., min_length=1, max_length=20000, description="SQL query to explain")
    connection_id: int = Field(..., description="Database connection to run EXPLAIN on")
    run_analyze: bool = Field(default=False, description="Run EXPLAIN ANALYZE")

    @field_validator("sql")
    @classmethod
    def validate_sql_is_select(cls, v: str) -> str:
        return _validate_explain_sql(v)


class PlanNodeSchema(BaseModel):
    node_type: str
    relation: Optional[str] = None
    cost_startup: Optional[float] = None
    cost_total: Optional[float] = None
    rows_estimated: Optional[int] = None
    rows_actual: Optional[int] = None
    loops: Optional[int] = None
    actual_time_ms: Optional[float] = None
    filter: Optional[str] = None
    index_name: Optional[str] = None
    join_type: Optional[str] = None
    disk_spill: bool = False
    children: List["PlanNodeSchema"] = Field(default_factory=list)
    raw_text: str = ""
    depth: int = 0


PlanNodeSchema.model_rebuild()


class ExecutionPlanSchema(BaseModel):
    dialect: str
    sql: str
    analyzed: bool
    root_node: Optional[PlanNodeSchema] = None
    all_nodes: List[PlanNodeSchema] = Field(default_factory=list)
    total_cost: Optional[float] = None
    total_actual_time_ms: Optional[float] = None
    has_seq_scans: bool = False
    has_disk_spill: bool = False
    has_hash_batches: bool = False
    node_count: int = 0
    seq_scan_tables: List[str] = Field(default_factory=list)
    missing_index_hints: List[str] = Field(default_factory=list)
    raw_plan: List[str] = Field(default_factory=list)
    parsed_at: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)


class BottleneckSchema(BaseModel):
    node_type: str
    table_or_index: str
    severity: str
    description: str
    impact_estimate: str


class IndexSuggestionSchema(BaseModel):
    table: str
    columns: List[str] = Field(default_factory=list)
    reason: str
    create_sql: str
    estimated_speedup: str


class QueryRewriteSchema(BaseModel):
    original_pattern: str
    rewritten_sql: str
    reason: str
    expected_improvement: str


class PerformanceInsightsSchema(BaseModel):
    summary: str
    overall_severity: str = "warning"
    bottlenecks: List[BottleneckSchema] = Field(default_factory=list)
    index_suggestions: List[IndexSuggestionSchema] = Field(default_factory=list)
    query_rewrites: List[QueryRewriteSchema] = Field(default_factory=list)
    before_after_estimate: Optional[str] = None
    general_recommendations: List[str] = Field(default_factory=list)
    confidence: float = 0.5
    llm_used: bool = False
    generated_at: Optional[str] = None


class PerformanceAnalysisResponse(BaseModel):
    """Response with execution plan and LLM-powered insights."""
    plan: ExecutionPlanSchema
    insights: PerformanceInsightsSchema
    connection_id: int
    sql: str
    analyzed: bool
    dialect: str


class ExplainOnlyResponse(BaseModel):
    """Response with raw execution plan only (no LLM)."""
    plan: ExecutionPlanSchema
    dialect: str
    analyzed: bool
    warnings: List[str] = Field(default_factory=list)


# ── Phase 25: Graph Mode (Neo4j) ──────────────────────────────────────────


class GraphPropertySchema(BaseModel):
    name: str
    types: List[str] = Field(default_factory=list)
    indexed: bool = False
    nullable: Optional[bool] = None
    sample_values: Optional[List[Any]] = None


class GraphNodeLabelSchema(BaseModel):
    name: str
    estimated_count: Optional[int] = None
    properties: List[GraphPropertySchema] = Field(default_factory=list)


class GraphRelationshipTypeSchema(BaseModel):
    name: str
    estimated_count: Optional[int] = None
    properties: List[GraphPropertySchema] = Field(default_factory=list)


class GraphRelationshipPatternSchema(BaseModel):
    source_labels: List[str] = Field(default_factory=list)
    relationship_type: str
    target_labels: List[str] = Field(default_factory=list)
    estimated_count: Optional[int] = None


class GraphIndexSchema(BaseModel):
    name: str
    entity_type: str
    labels_or_types: List[str] = Field(default_factory=list)
    properties: List[str] = Field(default_factory=list)
    type: Optional[str] = None
    state: Optional[str] = None


class GraphConstraintSchema(BaseModel):
    name: str
    entity_type: str
    labels_or_types: List[str] = Field(default_factory=list)
    properties: List[str] = Field(default_factory=list)
    type: str


class GraphSchemaResponse(BaseModel):
    """Cached or fresh schema for a graph connection (Phase 25.2)."""

    connection_id: int
    provider: str
    database_name: str
    labels: List[GraphNodeLabelSchema] = Field(default_factory=list)
    relationships: List[GraphRelationshipTypeSchema] = Field(default_factory=list)
    patterns: List[GraphRelationshipPatternSchema] = Field(default_factory=list)
    indexes: List[GraphIndexSchema] = Field(default_factory=list)
    constraints: List[GraphConstraintSchema] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    collected_at: Optional[str] = None
    schema_updated_at: Optional[str] = None
    server_version: Optional[str] = None
    edition: Optional[str] = None
    label_count: int = 0
    relationship_type_count: int = 0
    pattern_count: int = 0
    index_count: int = 0
    constraint_count: int = 0
    # True when the response is served from DatabaseConnection.schema_cache,
    # False when this request triggered a fresh introspection.
    cached: bool = False


class GraphIntrospectRequest(BaseModel):
    """Force-refresh introspection request payload."""

    overall_timeout_ms: Optional[int] = Field(
        default=None,
        ge=1000,
        le=600_000,
        description="Override server-wide GRAPH_INTROSPECTION_TIMEOUT_MS for this call.",
    )
    query_timeout_ms: Optional[int] = Field(
        default=None,
        ge=500,
        le=120_000,
        description="Override per-statement query timeout for this introspection only.",
    )


class GraphSchemaSummaryResponse(BaseModel):
    """LLM-rendered (or fallback) overview blurb for the GraphOverview card."""

    connection_id: int
    summary: str
    model: Optional[str] = None
    provider: Optional[str] = None
    used_fallback: bool = False


# ── Phase 25.3 — Cypher Query Lab ────────────────────────────────────────


class GraphQueryRequest(BaseModel):
    """Request body for ``POST /graph/connections/{id}/query``.

    ``parameters`` carries Cypher parameters so the caller doesn't have
    to interpolate values into the query (which would defeat the safety
    classifier's string-stripping step).
    """

    cypher: str = Field(..., min_length=1, max_length=20_000)
    parameters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Cypher parameters dict (passed to the driver verbatim).",
    )
    query_timeout_ms: Optional[int] = Field(
        default=None,
        ge=500,
        le=120_000,
        description="Override server-wide GRAPH_QUERY_TIMEOUT_MS for this call.",
    )
    max_records: Optional[int] = Field(
        default=None,
        ge=1,
        le=10_000,
        description="Override server-wide GRAPH_MAX_RECORDS for this call.",
    )
    source: Optional[str] = Field(
        default="manual",
        description="Where the query came from — 'manual', 'ai', or 'chat'.",
    )
    prompt: Optional[str] = Field(
        default=None,
        max_length=5_000,
        description="Original NL prompt when source='ai'; logged to history only.",
    )


class GraphVizNodePayload(BaseModel):
    id: str
    labels: List[str]
    properties: Dict[str, Any] = Field(default_factory=dict)
    displayName: str  # Stays camelCase to match the Cytoscape data shape on the frontend.


class GraphVizEdgePayload(BaseModel):
    id: str
    source: str
    target: str
    type: str
    properties: Dict[str, Any] = Field(default_factory=dict)


class GraphVizPayload(BaseModel):
    nodes: List[GraphVizNodePayload] = Field(default_factory=list)
    edges: List[GraphVizEdgePayload] = Field(default_factory=list)
    has_graph: bool = False


class GraphTablePayload(BaseModel):
    columns: List[str] = Field(default_factory=list)
    rows: List[List[Any]] = Field(default_factory=list)


class GraphQueryResult(BaseModel):
    """Response for a successful Cypher execution."""

    connection_id: int
    cypher: str
    safety_level: str
    success: bool
    record_count: int
    execution_time_ms: float
    truncated: bool
    table: GraphTablePayload
    graph_viz: GraphVizPayload
    warnings: List[str] = Field(default_factory=list)
    server_warnings: List[str] = Field(default_factory=list)


class GraphQueryBlocked(BaseModel):
    """Response body for a query blocked by the safety classifier (HTTP 400)."""

    connection_id: int
    safety_level: str
    blocked_reason: str
    reasons: List[str] = Field(default_factory=list)
    procedures: List[str] = Field(default_factory=list)


class GraphQueryError(BaseModel):
    """Response body for a query that ran but errored at the driver layer."""

    connection_id: int
    safety_level: str
    success: bool = False
    error_category: str
    error_message: str
    error_hint: Optional[str] = None
    error_code: Optional[str] = None
    execution_time_ms: float = 0.0


class GraphHistoryItem(BaseModel):
    """A single ``graph_query_history`` row in the listing endpoint."""

    id: int
    connection_id: int
    source: str
    cypher: str
    prompt: Optional[str] = None
    safety_level: str
    success: bool
    execution_time_ms: Optional[float] = None
    record_count: Optional[int] = None
    truncated: bool = False
    blocked_reason: Optional[str] = None
    error_category: Optional[str] = None
    error_message: Optional[str] = None
    created_at: str


class GraphHistoryResponse(BaseModel):
    """Paginated graph query history."""

    connection_id: int
    items: List[GraphHistoryItem]
    total: int
    limit: int
    offset: int


# ── Phase 25.4: AI Cypher Generation + Explanation ─────────────────────────


class CypherGenerateRequest(BaseModel):
    """Request body for POST /api/graph/connections/:id/ai/generate-cypher."""

    question: str = Field(..., min_length=1, max_length=2000)


class CypherGenerateResponse(BaseModel):
    """Response from the Cypher generation endpoint."""

    connection_id: int
    cypher: str
    question: str
    model: Optional[str] = None
    provider: Optional[str] = None
    unknown_labels: List[str] = Field(default_factory=list)
    used_fallback: bool = False
    error: Optional[str] = None


class CypherExplainRequest(BaseModel):
    """Request body for POST /api/graph/connections/:id/ai/explain-cypher."""

    cypher: str = Field(..., min_length=1, max_length=10000)
    include_schema: bool = Field(
        default=True,
        description="Include graph schema context for domain-aware explanations.",
    )


class CypherExplainResponse(BaseModel):
    """Response from the Cypher explanation endpoint."""

    connection_id: int
    explanation: str
    cypher: str
    model: Optional[str] = None
    provider: Optional[str] = None
    used_fallback: bool = False


# ── Phase 25.5: Visual Graph Explorer ───────────────────────────────────────


class GraphExploreRequest(BaseModel):
    """Request body for ``POST /api/graph/connections/{id}/explore``.

    Identifies a starting node by label + property = value, then expands
    1–3 hops, optionally filtering relationships by type.

    The depth/cap/types fields are echoed back in the response so the UI
    can render the "expanded N nodes (cap M)" banner without re-tracking
    its own request state.
    """

    start_label: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Cypher label of the starting node (plain identifier).",
    )
    start_property: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Property name used to locate the starting node.",
    )
    start_value: Any = Field(
        ...,
        description="Value to match against ``start_property`` (parameterized).",
    )
    depth: int = Field(
        default=1,
        ge=1,
        le=3,
        description="Hops to expand (1-3).",
    )
    rel_types: Optional[List[str]] = Field(
        default=None,
        description="Optional whitelist of relationship type names.",
    )
    direction: str = Field(
        default="any",
        pattern="^(out|in|any)$",
        description="Traversal direction: 'out', 'in', or 'any'.",
    )
    node_cap: Optional[int] = Field(
        default=None,
        ge=1,
        le=1000,
        description="Override server-wide GRAPH_MAX_VIZ_NODES (clamped to it).",
    )
    query_timeout_ms: Optional[int] = Field(
        default=None,
        ge=500,
        le=120_000,
        description="Override server-wide GRAPH_QUERY_TIMEOUT_MS.",
    )


class GraphExploreResponse(BaseModel):
    """Response body for a successful expand.

    Reuses the same ``graph_viz`` shape as the Cypher Query Lab so the
    GraphCanvas component can render either source without branching.
    """

    connection_id: int
    start_label: str
    depth: int
    direction: str
    rel_types: List[str] = Field(default_factory=list)
    safety_level: str
    success: bool
    record_count: int
    execution_time_ms: float
    truncated: bool
    table: GraphTablePayload
    graph_viz: GraphVizPayload
    warnings: List[str] = Field(default_factory=list)
    server_warnings: List[str] = Field(default_factory=list)


# ── Phase 25.6: Guru Advice ─────────────────────────────────────────────


class GraphAdvisorFinding(BaseModel):
    """A single rule-based modeling finding."""
    rule_id: str
    severity: str
    title: str
    description: str
    why: str
    suggested_fix: str
    entity_name: Optional[str] = None
    entity_type: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class GraphModelingAdviceResponse(BaseModel):
    """Response for POST /api/graph/connections/{id}/ai/modeling-advice."""
    connection_id: int
    findings: List[GraphAdvisorFinding] = Field(default_factory=list)
    finding_count: int = 0
    ai_summary: Optional[str] = None
    model: Optional[str] = None
    provider: Optional[str] = None
    used_fallback: bool = False
