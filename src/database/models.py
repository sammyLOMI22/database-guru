"""Database models for Database Guru"""
from datetime import datetime
import uuid
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship
from src.database.connection import Base


class QueryHistory(Base):
    """Store history of natural language queries and generated SQL

    Extended with query compilation metrics (Phase 4.2)
    """
    __tablename__ = "query_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), index=True, nullable=True)  # Optional user tracking

    # Input
    natural_language_query = Column(Text, nullable=False)

    # Generated SQL
    generated_sql = Column(Text, nullable=False)
    sql_validated = Column(Boolean, default=False)

    # Execution
    executed = Column(Boolean, default=False)
    execution_time_ms = Column(Float, nullable=True)
    result_count = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)

    # Metadata
    database_type = Column(String(50))  # postgres, mysql, sqlite, etc.
    model_used = Column(String(100))  # llama3, gpt-4, etc.

    # Query Compilation Metrics (Phase 4.2)
    normalized_hash = Column(String(64), nullable=True, index=True)  # Hash of normalized query template
    used_prepared_statement = Column(Boolean, default=False)  # Whether prepared statement was used
    plan_cache_hit = Column(Boolean, default=False)  # Whether plan was cached
    compilation_speedup_ms = Column(Float, nullable=True)  # Estimated speedup from compilation

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    feedbacks = relationship("UserFeedback", back_populates="query", cascade="all, delete-orphan")

    # Indexes for common queries
    __table_args__ = (
        Index('idx_user_created', 'user_id', 'created_at'),
        Index('idx_created', 'created_at'),
        Index('idx_normalized_hash', 'normalized_hash'),  # For compilation lookups
    )


class DatabaseConnection(Base):
    """Store configured database connections"""
    __tablename__ = "database_connections"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)

    # Connection details (encrypted in practice)
    database_type = Column(String(50), nullable=False)  # postgres, mysql, etc.
    host = Column(String(255))
    port = Column(Integer)
    database_name = Column(String(255))
    username = Column(String(255))
    # password should be encrypted - handled by security layer
    password_encrypted = Column(Text)

    # Schema information cache
    schema_cache = Column(JSON, nullable=True)  # Store table/column metadata
    schema_updated_at = Column(DateTime, nullable=True)

    # Status
    is_active = Column(Boolean, default=True)
    last_tested_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class QueryCache(Base):
    """Cache frequently used queries"""
    __tablename__ = "query_cache"

    id = Column(Integer, primary_key=True, index=True)

    # Cache key (hash of natural language query)
    cache_key = Column(String(64), unique=True, index=True, nullable=False)

    # Cached data
    natural_language_query = Column(Text, nullable=False)
    generated_sql = Column(Text, nullable=False)
    result_data = Column(JSON, nullable=True)  # Optional: cache results too

    # Cache metadata
    hit_count = Column(Integer, default=0)
    last_accessed_at = Column(DateTime, default=datetime.utcnow)

    # Expiration
    expires_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class UserFeedback(Base):
    """
    User corrections and feedback on queries

    Stores user-provided corrections to enable continuous learning.
    Feedback can be SQL corrections, column/table name fixes, or result issues.
    """
    __tablename__ = "user_feedback"

    id = Column(Integer, primary_key=True, index=True)

    # Link to original query
    query_id = Column(Integer, ForeignKey("query_history.id"), nullable=False, index=True)

    # Feedback type
    feedback_type = Column(String(50), nullable=False, index=True)
    # Types: "sql_correction", "column_name", "table_name", "result_issue"

    # Original and corrected content
    original_sql = Column(Text, nullable=False)
    corrected_sql = Column(Text, nullable=True)
    correction_description = Column(Text, nullable=True)

    # Specific corrections (structured data)
    # Example: {"from": "category", "to": "category_name", "table": "products"}
    correction_details = Column(JSON, nullable=True)

    # Quality indicators
    user_confidence = Column(Float, default=1.0)  # 0.0 to 1.0
    applied_successfully = Column(Boolean, default=False, index=True)

    # Learning integration
    learned_correction_id = Column(
        Integer,
        ForeignKey("learned_corrections.id"),
        nullable=True
    )

    # Metadata
    user_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    applied_at = Column(DateTime, nullable=True)

    # Relationships
    query = relationship("QueryHistory", back_populates="feedbacks")
    learned_correction = relationship("LearnedCorrection")

    def __repr__(self):
        return f"<UserFeedback(id={self.id}, type={self.feedback_type}, query_id={self.query_id})>"


class ChatSession(Base):
    """Store chat sessions with their associated database connections"""
    __tablename__ = "chat_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    user_id = Column(String(255), index=True, nullable=True)  # Optional user tracking

    # Multi-database support - stores array of connection IDs
    active_connection_ids = Column(JSON, nullable=False, default=list)  # [1, 2, 3]

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_active_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Indexes
    __table_args__ = (
        Index('idx_user_last_active', 'user_id', 'last_active_at'),
    )


class ChatMessage(Base):
    """Store individual messages in a chat session"""
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    chat_session_id = Column(String(36), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)

    # Message content
    role = Column(String(20), nullable=False)  # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)

    # Query metadata (for assistant messages)
    query_history_id = Column(Integer, ForeignKey("query_history.id"), nullable=True)
    databases_used = Column(JSON, nullable=True)  # [{"conn_id": 1, "name": "ecommerce", "tables": ["products"]}]

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    chat_session = relationship("ChatSession", backref="messages")
    query_history = relationship("QueryHistory", backref="chat_messages")


class LearnedCorrection(Base):
    """Store successful corrections that the system learned from"""
    __tablename__ = "learned_corrections"

    id = Column(Integer, primary_key=True, index=True)

    # Error pattern matching
    error_type = Column(String(50), nullable=False, index=True)  # From ErrorType enum
    error_pattern = Column(Text, nullable=False)  # Pattern to match against errors
    database_type = Column(String(50), nullable=False, index=True)  # postgres, mysql, duckdb, etc.

    # Original error details
    original_sql = Column(Text, nullable=False)
    original_error = Column(Text, nullable=False)

    # Successful correction
    corrected_sql = Column(Text, nullable=False)
    correction_description = Column(Text, nullable=True)  # Human-readable description

    # Pattern metadata
    table_pattern = Column(String(255), nullable=True, index=True)  # e.g., "products" -> table-specific
    column_pattern = Column(String(255), nullable=True, index=True)  # e.g., "price" -> column-specific

    # Learning metadata
    times_applied = Column(Integer, default=0)  # How many times this correction was successfully reused
    success_rate = Column(Float, default=1.0)  # Success rate when applied
    confidence_score = Column(Float, default=1.0)  # Confidence in this correction (0-1)

    # Timestamps
    learned_at = Column(DateTime, default=datetime.utcnow, index=True)
    last_applied_at = Column(DateTime, nullable=True)

    # Indexes for efficient lookups
    __table_args__ = (
        Index('idx_error_type_db', 'error_type', 'database_type'),
        Index('idx_table_pattern', 'table_pattern'),
        Index('idx_column_pattern', 'column_pattern'),
        Index('idx_confidence', 'confidence_score'),
    )


class SystemSettings(Base):
    """System-wide settings for Database Guru

    Stores configuration for auto-learning, confidence thresholds, etc.
    Only one row should exist in this table (singleton pattern).
    """
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)

    # Auto-Learning Settings
    auto_learning_enabled = Column(Boolean, default=False, nullable=False)
    confidence_threshold = Column(Float, default=0.75, nullable=False)  # 0.0-1.0 (lowered from 0.80 to increase auto-approval rate)
    apply_mode = Column(String(20), default="immediate", nullable=False)  # "immediate" or "deferred"
    test_before_learning = Column(Boolean, default=True, nullable=False)
    validation_mode = Column(String(20), default="strict", nullable=False)  # "strict", "moderate", "lenient"
    require_result_comparison = Column(Boolean, default=True, nullable=False)  # Compare original vs corrected results

    # Security Settings (Future: Admin Mode)
    allow_destructive_auto_learn = Column(Boolean, default=False, nullable=False)  # NEVER enable in production!
    require_admin_approval = Column(Boolean, default=True, nullable=False)  # Require admin for destructive ops

    # Audit Settings
    enable_audit_log = Column(Boolean, default=True, nullable=False)
    max_audit_log_days = Column(Integer, default=90, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return (
            f"<SystemSettings(auto_learning={self.auto_learning_enabled}, "
            f"threshold={self.confidence_threshold}, mode={self.apply_mode})>"
        )


class CompiledQueryMetrics(Base):
    """Track performance and compilation status of queries (Phase 4.2)

    Stores metrics for compiled queries including execution counts,
    plan cache hits, and prepared statement usage.
    """
    __tablename__ = "compiled_query_metrics"

    id = Column(Integer, primary_key=True, index=True)

    # Query identification
    normalized_hash = Column(String(64), unique=True, index=True, nullable=False)
    connection_id = Column(Integer, ForeignKey("database_connections.id"), nullable=False, index=True)
    template_sql = Column(Text, nullable=False)

    # Compilation status
    is_prepared = Column(Boolean, default=False, index=True)
    is_plan_cached = Column(Boolean, default=False, index=True)

    # Execution metrics
    total_executions = Column(Integer, default=0)
    total_execution_ms = Column(Float, default=0.0)
    avg_execution_ms = Column(Float, default=0.0)
    min_execution_ms = Column(Float, nullable=True)
    max_execution_ms = Column(Float, nullable=True)

    # Cache hit metrics
    plan_cache_hits = Column(Integer, default=0)
    plan_cache_misses = Column(Integer, default=0)
    prepared_statement_hits = Column(Integer, default=0)

    # Timestamps
    first_executed_at = Column(DateTime, default=datetime.utcnow, index=True)
    last_executed_at = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Indexes for common queries
    __table_args__ = (
        Index('idx_connection_hash', 'connection_id', 'normalized_hash'),
        Index('idx_last_executed', 'last_executed_at'),
        Index('idx_is_prepared', 'is_prepared'),
    )

    def __repr__(self):
        return (
            f"<CompiledQueryMetrics(hash={self.normalized_hash[:8]}, "
            f"executions={self.total_executions}, prepared={self.is_prepared})>"
        )


class CompilationInvalidationLog(Base):
    """Log schema changes and cache invalidations (Phase 4.2)

    Tracks when and why cached plans and prepared statements are invalidated
    due to schema changes or manual invalidation.
    """
    __tablename__ = "compilation_invalidation_log"

    id = Column(Integer, primary_key=True, index=True)

    # Connection and table information
    connection_id = Column(Integer, ForeignKey("database_connections.id"), nullable=False, index=True)
    table_name = Column(String(255), nullable=True, index=True)  # NULL for connection-wide invalidation

    # Schema fingerprints
    old_fingerprint = Column(String(32), nullable=True)
    new_fingerprint = Column(String(32), nullable=True)

    # Invalidation details
    invalidation_reason = Column(String(50), nullable=False)  # 'schema_change', 'manual', 'ttl_expired'
    plans_invalidated = Column(Integer, default=0)
    statements_invalidated = Column(Integer, default=0)

    # Optional details
    affected_queries = Column(JSON, nullable=True)  # List of affected query hashes
    details = Column(Text, nullable=True)  # Additional context

    # Timestamps
    invalidated_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Indexes
    __table_args__ = (
        Index('idx_connection_reason', 'connection_id', 'invalidation_reason'),
        Index('idx_table_invalidation', 'table_name', 'invalidated_at'),
    )

    def __repr__(self):
        return (
            f"<CompilationInvalidationLog(connection={self.connection_id}, "
            f"reason={self.invalidation_reason}, table={self.table_name})>"
        )
