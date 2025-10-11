"""Database models for Database Guru"""
from datetime import datetime
import uuid
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship
from src.database.connection import Base


class QueryHistory(Base):
    """Store history of natural language queries and generated SQL"""
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

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Indexes for common queries
    __table_args__ = (
        Index('idx_user_created', 'user_id', 'created_at'),
        Index('idx_created', 'created_at'),
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
    """Store user feedback on query results"""
    __tablename__ = "user_feedback"

    id = Column(Integer, primary_key=True, index=True)
    query_history_id = Column(Integer, ForeignKey("query_history.id"), nullable=False)

    # Feedback
    rating = Column(Integer)  # 1-5 stars
    was_helpful = Column(Boolean)
    corrected_sql = Column(Text, nullable=True)  # User-provided correction
    comments = Column(Text, nullable=True)

    # User info
    user_id = Column(String(255), index=True, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    query_history = relationship("QueryHistory", backref="feedback")


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
