"""Database models for Database Guru"""
from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, JSON, ForeignKey, Index, Date, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import relationship
from src.database.connection import Base


class LLMUsage(Base):
    """Track individual LLM API calls across all agents."""
    __tablename__ = "llm_usage"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Linking
    query_history_id = Column(Integer, ForeignKey("query_history.id", ondelete="SET NULL"), nullable=True)
    chat_session_id = Column(String(36), ForeignKey("chat_sessions.id", ondelete="SET NULL"), nullable=True, index=True)
    chat_message_id = Column(Integer, ForeignKey("chat_messages.id", ondelete="SET NULL"), nullable=True)

    # Agent & Model Info
    agent_type = Column(String(50), nullable=False, index=True)
    agent_name = Column(String(100))
    provider = Column(String(50), default="ollama", index=True)
    data_locality = Column(String(20), nullable=True)  # local, cloud_private, cloud_public
    model_name = Column(String(100), nullable=False, index=True)
    llm_method = Column(String(20), nullable=False)  # 'generate', 'chat', 'embeddings'

    # Token Counts
    input_tokens = Column(Integer, nullable=False, default=0)
    output_tokens = Column(Integer, nullable=False, default=0)
    token_estimation_method = Column(String(20), default='estimated')

    # Timing
    request_timestamp = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    response_time_ms = Column(Float)
    time_to_first_token_ms = Column(Float)

    # Context (for debugging)
    prompt_summary = Column(String(500))
    response_summary = Column(String(500))

    # Status
    success = Column(Boolean, nullable=False, default=True)
    error_message = Column(Text)

    # Cost
    estimated_cost_usd = Column(Float)

    # Metadata
    metadata_json = Column(JSON, name="metadata")  # Avoid collision with Base.metadata
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)

    # Relationships
    query_history = relationship("QueryHistory", back_populates="llm_usage_records")
    chat_session = relationship("ChatSession", back_populates="llm_usage_records")
    chat_message = relationship("ChatMessage", back_populates="llm_usage_records")

    @property
    def total_tokens(self):
        return self.input_tokens + self.output_tokens


class LLMUsageAggregate(Base):
    """Pre-computed daily/hourly statistics for dashboard performance."""
    __tablename__ = "llm_usage_aggregate"

    id = Column(Integer, primary_key=True, autoincrement=True)

    date = Column(Date, nullable=False, index=True)
    hour = Column(Integer)  # 0-23, NULL for daily
    agent_type = Column(String(50), index=True)
    provider = Column(String(50), index=True)
    model_name = Column(String(100))

    total_calls = Column(Integer, nullable=False, default=0)
    successful_calls = Column(Integer, nullable=False, default=0)
    failed_calls = Column(Integer, nullable=False, default=0)

    total_input_tokens = Column(Integer, nullable=False, default=0)
    total_output_tokens = Column(Integer, nullable=False, default=0)
    total_tokens = Column(Integer, nullable=False, default=0)

    avg_response_time_ms = Column(Float)
    max_response_time_ms = Column(Float)
    min_response_time_ms = Column(Float)

    total_estimated_cost_usd = Column(Float)

    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint('date', 'hour', 'agent_type', 'provider', 'model_name', name='uq_llm_agg_dimensions'),
    )


class LLMModelConfig(Base):
    """Model metadata and configuration."""
    __tablename__ = "llm_model_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_name = Column(String(100), nullable=False)
    display_name = Column(String(100))
    provider = Column(String(50), nullable=False, default="ollama")

    # Capabilities
    context_window_size = Column(Integer, default=4096)
    max_output_tokens = Column(Integer, default=2048)
    supports_streaming = Column(Boolean, default=True)

    # Cost (per 1M tokens, for reference)
    cost_per_1m_input_tokens = Column(Float)
    cost_per_1m_output_tokens = Column(Float)
    token_calibration_factor = Column(Float, default=1.0)

    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)

    notes = Column(Text)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint('model_name', 'provider', name='uq_model_provider'),
    )


class LLMProviderConfig(Base):
    """Stored configuration for LLM providers (API keys encrypted)."""
    __tablename__ = "llm_provider_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    provider_name = Column(String(50), nullable=False, unique=True)
    enabled = Column(Boolean, default=False)
    data_locality = Column(String(20), nullable=False)  # local, cloud_private, cloud_public
    api_key_encrypted = Column(Text)  # Fernet-encrypted API key
    endpoint = Column(Text)
    default_model = Column(String(100))
    extra_config = Column(JSON)  # Provider-specific settings

    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class LLMTaskRouting(Base):
    """Per-task provider and model routing configuration."""
    __tablename__ = "llm_task_routing"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_type = Column(String(50), nullable=False, unique=True)  # sql_generation, narratives, etc.
    primary_provider = Column(String(50), nullable=False)
    primary_model = Column(String(100))
    fallback_chain = Column(JSON)  # Ordered list: [{"provider": "ollama", "model": "llama3.2"}]

    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class QueryHistory(Base):
    """Store history of natural language queries and generated SQL"""
    __tablename__ = "query_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), index=True, nullable=True)  # Legacy optional user tracking
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

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
    connection_id = Column(Integer, ForeignKey("database_connections.id"), nullable=True, index=True)
    status = Column(String(20), default="pending")  # pending, processing, completed, failed

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    # Relationships
    feedbacks = relationship("UserFeedback", back_populates="query", cascade="all, delete-orphan")
    llm_usage_records = relationship("LLMUsage", back_populates="query_history", cascade="save-update, merge", passive_deletes=True)
    chat_messages = relationship("ChatMessage", back_populates="query_history")

    # Indexes for common queries
    __table_args__ = (
        Index('idx_user_created', 'user_id', 'created_at'),
        Index('idx_created', 'created_at'),
        Index('idx_connection_created', 'connection_id', 'created_at'),
    )


class DatabaseConnection(Base):
    """Store configured database connections"""
    __tablename__ = "database_connections"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

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
    is_deleted = Column(Boolean, default=False, index=True)
    last_tested_at = Column(DateTime, nullable=True)

    # Graph-specific (Phase 25 — Neo4j) — NULL/no-op for non-graph databases
    encrypted = Column(Boolean, nullable=True)
    read_only = Column(Boolean, nullable=False, default=True, server_default="1")

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


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
    last_accessed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Expiration
    expires_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


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
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
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
    user_id = Column(String(255), index=True, nullable=True)  # Legacy optional user tracking
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Multi-database support - stores array of connection IDs
    active_connection_ids = Column(JSON, nullable=False, default=list)  # [1, 2, 3]

    # File sources support - stores array of file source IDs (Phase 13)
    active_file_source_ids = Column(JSON, nullable=False, default=list)  # [1, 2, 3]

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    last_active_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    # Relationships
    messages = relationship("ChatMessage", back_populates="chat_session", cascade="all, delete-orphan")
    llm_usage_records = relationship("LLMUsage", back_populates="chat_session", cascade="save-update, merge", passive_deletes=True)

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
    response_data = Column(JSON, nullable=True)  # Full API response for history replay (capped rows, no traces)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    # Relationships
    chat_session = relationship("ChatSession", back_populates="messages")
    query_history = relationship("QueryHistory", back_populates="chat_messages")
    llm_usage_records = relationship("LLMUsage", back_populates="chat_message", cascade="save-update, merge", passive_deletes=True)


class FileSource(Base):
    """Store uploaded file data sources (CSV, Excel) for querying via DuckDB

    Phase 13: CSV & Excel File Support
    Files are uploaded, schema is inferred via DuckDB, and they become
    queryable data sources alongside traditional database connections.
    """
    __tablename__ = "file_sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)  # Display name
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # File metadata
    original_filename = Column(String(255), nullable=False)
    file_type = Column(String(20), nullable=False)  # 'csv', 'xlsx', 'xls'
    file_size_bytes = Column(Integer, nullable=False)
    file_path = Column(String(512), nullable=False)
    file_hash = Column(String(64), nullable=True)  # SHA-256 for deduplication

    # Excel sheet handling
    sheet_name = Column(String(255), nullable=True)

    # Schema information (cached from DuckDB inference)
    schema_cache = Column(JSON, nullable=True)  # {columns: [...], row_count: N, sample_values: {...}}
    schema_updated_at = Column(DateTime, nullable=True)
    row_count = Column(Integer, nullable=True)

    # DuckDB integration
    duckdb_table_name = Column(String(255), nullable=False, unique=True)  # e.g., "file_1_q4_sales"

    # Ownership and scope
    user_id = Column(String(255), index=True, nullable=True)
    chat_session_id = Column(String(36), ForeignKey("chat_sessions.id", ondelete="SET NULL"), nullable=True)
    is_global = Column(Boolean, default=False)  # Available across all sessions

    # Status
    is_active = Column(Boolean, default=True)
    processing_status = Column(String(20), default='pending')  # pending, processing, ready, error
    processing_error = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime, nullable=True, index=True)  # Auto-cleanup after N days

    # Relationships
    chat_session = relationship("ChatSession", backref="file_sources")

    # Indexes for common queries
    __table_args__ = (
        Index('idx_file_user_session', 'user_id', 'chat_session_id'),
        Index('idx_file_hash', 'file_hash'),
        Index('idx_file_status', 'processing_status'),
        Index('idx_file_global', 'is_global', 'is_active'),
    )

    def __repr__(self):
        return f"<FileSource(id={self.id}, name='{self.name}', type='{self.file_type}', status='{self.processing_status}')>"


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
    learned_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
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

    # Query Quality Settings
    query_quality_level = Column(Integer, default=50, nullable=False)  # 0-100 scale

    # Semantic Understanding Settings (Phase 1, 2, 3)
    enable_intent_classification = Column(Boolean, default=True, nullable=False)  # Phase 1: Detect impossible queries
    enable_dynamic_examples = Column(Boolean, default=True, nullable=False)  # Phase 2: Schema-specific examples
    enable_semantic_validation = Column(Boolean, default=True, nullable=False)  # Phase 3: Post-generation validation

    # Per-Task Model Configuration (Phase: Small Model Optimization)
    # If None, uses the default OLLAMA_MODEL from settings
    model_sql_generation = Column(String(100), nullable=True)  # Model for SQL generation
    model_narratives = Column(String(100), nullable=True)  # Model for result narratives
    model_query_planning = Column(String(100), nullable=True)  # Model for query planning
    model_error_correction = Column(String(100), nullable=True)  # Model for error correction

    # Per-Task Timeout Configuration (seconds)
    timeout_sql_generation = Column(Integer, default=30, nullable=False)
    timeout_narratives = Column(Integer, default=15, nullable=False)
    timeout_query_planning = Column(Integer, default=20, nullable=False)
    timeout_error_correction = Column(Integer, default=15, nullable=False)

    # Phase 12: Lineage Intelligence Model Overrides
    model_lineage_narrative = Column(String(100), nullable=True)  # Model for lineage explanations
    model_impact_analysis = Column(String(100), nullable=True)  # Model for impact/migration advice
    model_schema_health = Column(String(100), nullable=True)  # Model for schema analysis
    model_lineage_conversation = Column(String(100), nullable=True)  # Model for lineage Q&A
    model_pattern_intelligence = Column(String(100), nullable=True)  # Model for pattern analysis

    # Phase 12: Lineage Intelligence Timeouts (seconds)
    timeout_lineage_narrative = Column(Integer, default=15, nullable=False)
    timeout_impact_analysis = Column(Integer, default=20, nullable=False)
    timeout_schema_health = Column(Integer, default=30, nullable=False)
    timeout_lineage_conversation = Column(Integer, default=15, nullable=False)
    timeout_pattern_intelligence = Column(Integer, default=20, nullable=False)

    # Small Model Optimization Feature Flags
    enable_query_templates = Column(Boolean, default=True, nullable=False)  # Bypass LLM for simple patterns
    enable_location_preprocessing = Column(Boolean, default=True, nullable=False)  # Normalize locations before LLM

    # Prompt Optimization (Phase 2.2) - USER TOGGLE
    enable_prompt_optimization = Column(Boolean, default=False, nullable=False)  # OFF by default, user opt-in
    prompt_model_size = Column(String(20), default="auto", nullable=False)  # auto|small|medium|large
    enable_schema_compression = Column(Boolean, default=True, nullable=False)  # Compress schema to relevant tables
    max_schema_tables = Column(Integer, default=10, nullable=False)  # Max tables before compression
    enable_example_selection = Column(Boolean, default=True, nullable=False)  # Select relevant few-shot examples
    max_few_shot_examples = Column(Integer, default=3, nullable=False)  # Max examples to include

    # Multi-Database Query Intelligence (Phase 2.4)
    enable_multi_db_validation = Column(Boolean, default=True, nullable=False)  # Pre-flight schema validation
    multi_db_validation_threshold = Column(Float, default=0.6, nullable=False)  # Fuzzy match threshold for alternatives

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Phase 20: Migration Toolkit
    model_migration_planner = Column(String(100), nullable=True)
    timeout_migration_planner = Column(Integer, default=30, nullable=False)

    def __repr__(self):
        return (
            f"<SystemSettings(auto_learning={self.auto_learning_enabled}, "
            f"threshold={self.confidence_threshold}, mode={self.apply_mode})>"
        )


class MigrationProject(Base):
    """Store migration projects: schema diffs, plans, and generated scripts.

    Phase 20: Migration Toolkit
    A single project record carries state through the full workflow:
    diff → plan → script generation → data migration.
    """
    __tablename__ = "migration_projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Connection references
    source_connection_id = Column(
        Integer,
        ForeignKey("database_connections.id", ondelete="SET NULL"),
        nullable=True,
    )
    target_connection_id = Column(
        Integer,
        ForeignKey("database_connections.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Diff snapshot (SchemaDiff.to_dict())
    diff_snapshot = Column(JSON, nullable=True)
    source_fingerprint = Column(String(64), nullable=True)
    target_fingerprint = Column(String(64), nullable=True)

    # LLM-generated migration plan (MigrationPlan.to_dict())
    migration_plan = Column(JSON, nullable=True)

    # Generated scripts
    up_sql = Column(Text, nullable=True)
    down_sql = Column(Text, nullable=True)
    verify_sql = Column(Text, nullable=True)

    # Data migration queries (DataMigrationPlan.to_dict())
    data_migration_plan = Column(JSON, nullable=True)

    # Metadata
    target_dialect = Column(String(50), nullable=True)  # postgresql|mysql|sqlite
    status = Column(String(20), default="draft")  # draft|planned|scripted
    notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    source_connection = relationship(
        "DatabaseConnection", foreign_keys=[source_connection_id]
    )
    target_connection = relationship(
        "DatabaseConnection", foreign_keys=[target_connection_id]
    )

    __table_args__ = (
        Index('idx_migration_source', 'source_connection_id'),
        Index('idx_migration_target', 'target_connection_id'),
        Index('idx_migration_status', 'status'),
        CheckConstraint("status IN ('draft', 'planned', 'scripted')", name='ck_migration_status'),
    )


class ConnectionWritePermission(Base):
    """Per-connection write permissions for Edit Mode (Phase 18)."""
    __tablename__ = "connection_write_permissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    connection_id = Column(
        Integer,
        ForeignKey("database_connections.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    # Granular DML permissions
    allow_insert = Column(Boolean, default=False)
    allow_update = Column(Boolean, default=False)
    allow_delete = Column(Boolean, default=False)

    # Safety settings
    require_where_clause = Column(Boolean, default=True)
    max_rows_per_operation = Column(Integer, default=100)
    allowed_tables = Column(JSON, nullable=True)  # null = all tables

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    # Relationship
    connection = relationship("DatabaseConnection", backref="write_permission")
