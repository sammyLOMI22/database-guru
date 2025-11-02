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
