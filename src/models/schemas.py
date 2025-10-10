"""Pydantic schemas for API requests and responses"""
from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field, validator


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

    @validator('question')
    def question_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Question cannot be empty')
        return v.strip()


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
