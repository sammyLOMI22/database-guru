# LLM Usage Monitoring & Analytics Dashboard

## Overview

This document outlines the plan for implementing comprehensive LLM token usage monitoring and analytics for Database Guru. The feature will track token consumption across all 23+ agents, link usage to chat sessions, and provide both a dedicated dashboard and inline chat statistics.

## Goals

1. **Track Token Usage** - Record input/output tokens for every LLM call
2. **Per-Agent Analytics** - Understand which agents consume the most resources
3. **Session Linking** - Associate costs with specific chat conversations
4. **Real-time Visibility** - Show usage in the chat interface as queries run
5. **Historical Analytics** - Dashboard for trends, budgets, and optimization insights
6. **Cost Awareness** - Help users understand the "cost" of different query types

---

## Architecture Design

### High-Level Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           LLM USAGE TRACKING FLOW                           │
└─────────────────────────────────────────────────────────────────────────────┘

  User Query                                              Frontend Dashboard
      │                                                         ▲
      ▼                                                         │
┌──────────────┐    ┌──────────────┐    ┌──────────────┐   ┌────┴────────┐
│  Chat API    │───▶│ Agent System │───▶│ OllamaClient │   │ Stats API   │
│  Endpoint    │    │ (23+ agents) │    │  (wrapped)   │   │ /llm/usage  │
└──────────────┘    └──────────────┘    └──────┬───────┘   └─────────────┘
      │                                        │                  ▲
      │ session_id                             │ LLMUsageRecord   │
      ▼                                        ▼                  │
┌──────────────┐                        ┌──────────────┐          │
│ ChatSession  │◀───────────────────────│  LLMUsage    │──────────┘
│ ChatMessage  │     query_history_id   │    Table     │
└──────────────┘                        └──────────────┘
                                               │
                                               ▼
                                        ┌──────────────┐
                                        │ LLMUsage     │
                                        │  Aggregate   │
                                        └──────────────┘
```

### Token Estimation Strategy

Since Ollama doesn't always return token counts, we'll implement a hybrid approach:

1. **Ollama Native Tokens** (when available)
   - Ollama API returns `eval_count`, `prompt_eval_count` in responses
   - Extract these when present in the response metadata

2. **Token Estimation Fallback**
   - Use tiktoken library with cl100k_base encoding (GPT-4 approximation)
   - Works well for most LLMs as a reasonable estimate
   - Formula: `tokens ≈ len(text) / 4` as rough backup

3. **Model-Specific Calibration**
   - Store calibration factors per model in database
   - Allow adjustment based on observed patterns

---

## Database Schema

### New Tables

#### 1. LLMUsage (Core Tracking Table)

```sql
CREATE TABLE llm_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Linking
    query_history_id INTEGER REFERENCES query_history(id) ON DELETE SET NULL,
    chat_session_id VARCHAR(36) REFERENCES chat_sessions(id) ON DELETE SET NULL,
    chat_message_id INTEGER REFERENCES chat_messages(id) ON DELETE SET NULL,

    -- Agent & Model Info
    agent_type VARCHAR(50) NOT NULL,  -- 'sql_generator', 'result_narrator', etc.
    agent_name VARCHAR(100),          -- Human-readable name
    model_name VARCHAR(100) NOT NULL, -- 'qwen2.5-coder:32b', 'llama3.2:latest'
    llm_method VARCHAR(20) NOT NULL,  -- 'generate', 'chat', 'embeddings'

    -- Token Counts
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER GENERATED ALWAYS AS (input_tokens + output_tokens) STORED,
    token_estimation_method VARCHAR(20) DEFAULT 'estimated', -- 'ollama_native', 'tiktoken', 'estimated'

    -- Timing
    request_timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    response_time_ms FLOAT,
    time_to_first_token_ms FLOAT,  -- For streaming responses

    -- Context
    prompt_summary VARCHAR(500),    -- Truncated prompt for debugging
    response_summary VARCHAR(500),  -- Truncated response for debugging

    -- Status
    success BOOLEAN NOT NULL DEFAULT TRUE,
    error_message TEXT,

    -- Cost (optional, for future use)
    estimated_cost_usd FLOAT,

    -- Metadata
    metadata JSON,  -- Extensible for future fields
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for common queries
CREATE INDEX idx_llm_usage_session ON llm_usage(chat_session_id);
CREATE INDEX idx_llm_usage_query ON llm_usage(query_history_id);
CREATE INDEX idx_llm_usage_agent ON llm_usage(agent_type);
CREATE INDEX idx_llm_usage_model ON llm_usage(model_name);
CREATE INDEX idx_llm_usage_timestamp ON llm_usage(request_timestamp);
CREATE INDEX idx_llm_usage_created ON llm_usage(created_at);
```

#### 2. LLMUsageAggregate (Pre-computed Statistics)

```sql
CREATE TABLE llm_usage_aggregate (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Aggregation Dimensions
    date DATE NOT NULL,
    hour INTEGER,  -- 0-23, NULL for daily aggregates
    agent_type VARCHAR(50),
    model_name VARCHAR(100),

    -- Metrics
    total_calls INTEGER NOT NULL DEFAULT 0,
    successful_calls INTEGER NOT NULL DEFAULT 0,
    failed_calls INTEGER NOT NULL DEFAULT 0,

    total_input_tokens INTEGER NOT NULL DEFAULT 0,
    total_output_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER NOT NULL DEFAULT 0,

    avg_response_time_ms FLOAT,
    max_response_time_ms FLOAT,
    min_response_time_ms FLOAT,
    p95_response_time_ms FLOAT,

    total_estimated_cost_usd FLOAT,

    -- Metadata
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(date, hour, agent_type, model_name)
);

CREATE INDEX idx_llm_agg_date ON llm_usage_aggregate(date);
CREATE INDEX idx_llm_agg_agent ON llm_usage_aggregate(agent_type);
```

#### 3. LLMModelConfig (Model Metadata)

```sql
CREATE TABLE llm_model_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    model_name VARCHAR(100) NOT NULL UNIQUE,
    display_name VARCHAR(100),

    -- Capabilities
    context_window_size INTEGER DEFAULT 4096,
    max_output_tokens INTEGER DEFAULT 2048,
    supports_streaming BOOLEAN DEFAULT TRUE,

    -- Cost (per 1M tokens, for reference)
    cost_per_1m_input_tokens FLOAT,
    cost_per_1m_output_tokens FLOAT,

    -- Token Estimation
    token_calibration_factor FLOAT DEFAULT 1.0,  -- Multiplier for estimates

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_default BOOLEAN DEFAULT FALSE,

    -- Metadata
    notes TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

#### 4. LLMUsageBudget (Optional Budget Controls)

```sql
CREATE TABLE llm_usage_budget (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Scope
    scope VARCHAR(20) NOT NULL DEFAULT 'global',  -- 'global', 'user', 'session'
    scope_id VARCHAR(100),  -- user_id or session_id if scoped

    -- Budget Settings
    daily_token_limit INTEGER,
    monthly_token_limit INTEGER,
    daily_cost_limit_usd FLOAT,
    monthly_cost_limit_usd FLOAT,

    -- Alert Thresholds (percentage)
    warning_threshold_pct INTEGER DEFAULT 80,
    critical_threshold_pct INTEGER DEFAULT 95,

    -- Current Period Tracking
    current_daily_tokens INTEGER DEFAULT 0,
    current_monthly_tokens INTEGER DEFAULT 0,
    last_reset_date DATE,

    -- Actions
    action_on_exceed VARCHAR(20) DEFAULT 'warn',  -- 'warn', 'throttle', 'block'

    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### SQLAlchemy Models

```python
# src/database/models.py additions

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
    model_name = Column(String(100), nullable=False, index=True)
    llm_method = Column(String(20), nullable=False)  # 'generate', 'chat', 'embeddings'

    # Token Counts
    input_tokens = Column(Integer, nullable=False, default=0)
    output_tokens = Column(Integer, nullable=False, default=0)
    token_estimation_method = Column(String(20), default='estimated')

    # Timing
    request_timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
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
    metadata = Column(JSON)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    query_history = relationship("QueryHistory", backref="llm_usage_records")
    chat_session = relationship("ChatSession", backref="llm_usage_records")
    chat_message = relationship("ChatMessage", backref="llm_usage_records")

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

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('date', 'hour', 'agent_type', 'model_name', name='uq_llm_agg_dimensions'),
    )


class LLMModelConfig(Base):
    """Model metadata and configuration."""
    __tablename__ = "llm_model_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(100))

    context_window_size = Column(Integer, default=4096)
    max_output_tokens = Column(Integer, default=2048)
    supports_streaming = Column(Boolean, default=True)

    cost_per_1m_input_tokens = Column(Float)
    cost_per_1m_output_tokens = Column(Float)
    token_calibration_factor = Column(Float, default=1.0)

    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)

    notes = Column(Text)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
```

---

## Backend Implementation

### 1. LLM Usage Tracker Service

Create a centralized service to track all LLM calls:

```python
# src/services/llm_usage_tracker.py

import time
from datetime import datetime
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager
import tiktoken
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import LLMUsage


class LLMUsageTracker:
    """Centralized LLM usage tracking service."""

    def __init__(self):
        self._encoder = None  # Lazy-loaded tiktoken encoder

    @property
    def encoder(self):
        if self._encoder is None:
            try:
                self._encoder = tiktoken.get_encoding("cl100k_base")
            except Exception:
                self._encoder = None
        return self._encoder

    def estimate_tokens(self, text: str) -> tuple[int, str]:
        """Estimate token count for text. Returns (count, method)."""
        if not text:
            return 0, "empty"

        if self.encoder:
            try:
                return len(self.encoder.encode(text)), "tiktoken"
            except Exception:
                pass

        # Fallback: rough estimate (4 chars per token average)
        return len(text) // 4, "estimated"

    def extract_ollama_tokens(self, response: dict) -> tuple[Optional[int], Optional[int]]:
        """Extract token counts from Ollama response if available."""
        input_tokens = response.get("prompt_eval_count")
        output_tokens = response.get("eval_count")
        return input_tokens, output_tokens

    @asynccontextmanager
    async def track_call(
        self,
        db: AsyncSession,
        agent_type: str,
        model_name: str,
        llm_method: str,
        prompt: str,
        query_history_id: Optional[int] = None,
        chat_session_id: Optional[str] = None,
        chat_message_id: Optional[int] = None,
        agent_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Context manager to track an LLM call.

        Usage:
            async with tracker.track_call(db, "sql_generator", model, "generate", prompt) as tracking:
                response = await ollama.generate(...)
                tracking.set_response(response_text, ollama_response_dict)
        """
        start_time = time.time()
        tracking = _TrackingContext(
            tracker=self,
            db=db,
            agent_type=agent_type,
            model_name=model_name,
            llm_method=llm_method,
            prompt=prompt,
            query_history_id=query_history_id,
            chat_session_id=chat_session_id,
            chat_message_id=chat_message_id,
            agent_name=agent_name,
            metadata=metadata,
            start_time=start_time,
        )

        try:
            yield tracking
        except Exception as e:
            tracking.set_error(str(e))
            raise
        finally:
            await tracking.save()


class _TrackingContext:
    """Internal context for a single LLM call being tracked."""

    def __init__(self, tracker, db, agent_type, model_name, llm_method, prompt,
                 query_history_id, chat_session_id, chat_message_id, agent_name,
                 metadata, start_time):
        self.tracker = tracker
        self.db = db
        self.agent_type = agent_type
        self.model_name = model_name
        self.llm_method = llm_method
        self.prompt = prompt
        self.query_history_id = query_history_id
        self.chat_session_id = chat_session_id
        self.chat_message_id = chat_message_id
        self.agent_name = agent_name
        self.metadata = metadata or {}
        self.start_time = start_time

        self.response_text: Optional[str] = None
        self.ollama_response: Optional[dict] = None
        self.error_message: Optional[str] = None
        self.success = True

    def set_response(self, response_text: str, ollama_response: Optional[dict] = None):
        """Set the response from the LLM call."""
        self.response_text = response_text
        self.ollama_response = ollama_response

    def set_error(self, error_message: str):
        """Mark the call as failed."""
        self.success = False
        self.error_message = error_message

    async def save(self):
        """Save the usage record to the database."""
        end_time = time.time()
        response_time_ms = (end_time - self.start_time) * 1000

        # Calculate tokens
        input_tokens, input_method = self.tracker.estimate_tokens(self.prompt)
        output_tokens, output_method = 0, "empty"
        token_method = input_method

        if self.response_text:
            output_tokens, output_method = self.tracker.estimate_tokens(self.response_text)

        # Try to get native Ollama token counts
        if self.ollama_response:
            ollama_input, ollama_output = self.tracker.extract_ollama_tokens(self.ollama_response)
            if ollama_input is not None:
                input_tokens = ollama_input
                token_method = "ollama_native"
            if ollama_output is not None:
                output_tokens = ollama_output
                token_method = "ollama_native"

        # Create record
        usage_record = LLMUsage(
            query_history_id=self.query_history_id,
            chat_session_id=self.chat_session_id,
            chat_message_id=self.chat_message_id,
            agent_type=self.agent_type,
            agent_name=self.agent_name,
            model_name=self.model_name,
            llm_method=self.llm_method,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            token_estimation_method=token_method,
            request_timestamp=datetime.utcnow(),
            response_time_ms=response_time_ms,
            prompt_summary=self.prompt[:500] if self.prompt else None,
            response_summary=self.response_text[:500] if self.response_text else None,
            success=self.success,
            error_message=self.error_message,
            metadata=self.metadata,
        )

        self.db.add(usage_record)
        await self.db.commit()

        return usage_record


# Global instance
llm_usage_tracker = LLMUsageTracker()
```

### 2. OllamaClient Wrapper Integration

Modify the existing OllamaClient to integrate tracking:

```python
# src/llm/ollama_client.py additions

from src.services.llm_usage_tracker import llm_usage_tracker

class OllamaClient:
    # ... existing code ...

    async def generate_tracked(
        self,
        prompt: str,
        db: AsyncSession,
        agent_type: str,
        query_history_id: Optional[int] = None,
        chat_session_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """Generate with automatic usage tracking."""
        async with llm_usage_tracker.track_call(
            db=db,
            agent_type=agent_type,
            model_name=self.model,
            llm_method="generate",
            prompt=prompt,
            query_history_id=query_history_id,
            chat_session_id=chat_session_id,
        ) as tracking:
            result = await self.generate(prompt, **kwargs)
            tracking.set_response(result)
            return result

    async def chat_tracked(
        self,
        messages: list,
        db: AsyncSession,
        agent_type: str,
        query_history_id: Optional[int] = None,
        chat_session_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """Chat with automatic usage tracking."""
        # Convert messages to prompt string for token estimation
        prompt_text = "\n".join(f"{m['role']}: {m['content']}" for m in messages)

        async with llm_usage_tracker.track_call(
            db=db,
            agent_type=agent_type,
            model_name=self.model,
            llm_method="chat",
            prompt=prompt_text,
            query_history_id=query_history_id,
            chat_session_id=chat_session_id,
        ) as tracking:
            result = await self.chat(messages, **kwargs)
            tracking.set_response(result)
            return result
```

### 3. API Endpoints

```python
# src/api/endpoints/llm_usage.py

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta
from typing import Optional, List

from src.database.session import get_session
from src.database.models import LLMUsage, LLMUsageAggregate
from src.models.schemas import (
    LLMUsageResponse,
    LLMUsageStatsResponse,
    LLMUsageByAgentResponse,
    LLMUsageTimeSeriesResponse,
    SessionUsageSummaryResponse,
)

router = APIRouter(prefix="/llm/usage", tags=["LLM Usage"])


@router.get("/stats", response_model=LLMUsageStatsResponse)
async def get_usage_stats(
    days: int = Query(default=7, ge=1, le=90),
    db: AsyncSession = Depends(get_session),
):
    """Get overall LLM usage statistics for the past N days."""
    since = datetime.utcnow() - timedelta(days=days)

    result = await db.execute(
        select(
            func.count(LLMUsage.id).label("total_calls"),
            func.sum(LLMUsage.input_tokens).label("total_input_tokens"),
            func.sum(LLMUsage.output_tokens).label("total_output_tokens"),
            func.avg(LLMUsage.response_time_ms).label("avg_response_time_ms"),
            func.count(func.distinct(LLMUsage.chat_session_id)).label("unique_sessions"),
            func.count(func.distinct(LLMUsage.model_name)).label("models_used"),
        ).where(LLMUsage.created_at >= since)
    )

    row = result.one()
    return {
        "period_days": days,
        "total_calls": row.total_calls or 0,
        "total_input_tokens": row.total_input_tokens or 0,
        "total_output_tokens": row.total_output_tokens or 0,
        "total_tokens": (row.total_input_tokens or 0) + (row.total_output_tokens or 0),
        "avg_response_time_ms": row.avg_response_time_ms,
        "unique_sessions": row.unique_sessions or 0,
        "models_used": row.models_used or 0,
    }


@router.get("/by-agent", response_model=List[LLMUsageByAgentResponse])
async def get_usage_by_agent(
    days: int = Query(default=7, ge=1, le=90),
    db: AsyncSession = Depends(get_session),
):
    """Get LLM usage breakdown by agent type."""
    since = datetime.utcnow() - timedelta(days=days)

    result = await db.execute(
        select(
            LLMUsage.agent_type,
            func.count(LLMUsage.id).label("total_calls"),
            func.sum(LLMUsage.input_tokens).label("total_input_tokens"),
            func.sum(LLMUsage.output_tokens).label("total_output_tokens"),
            func.avg(LLMUsage.response_time_ms).label("avg_response_time_ms"),
        )
        .where(LLMUsage.created_at >= since)
        .group_by(LLMUsage.agent_type)
        .order_by(func.sum(LLMUsage.input_tokens + LLMUsage.output_tokens).desc())
    )

    return [
        {
            "agent_type": row.agent_type,
            "total_calls": row.total_calls,
            "total_input_tokens": row.total_input_tokens or 0,
            "total_output_tokens": row.total_output_tokens or 0,
            "total_tokens": (row.total_input_tokens or 0) + (row.total_output_tokens or 0),
            "avg_response_time_ms": row.avg_response_time_ms,
        }
        for row in result.all()
    ]


@router.get("/by-model", response_model=List[dict])
async def get_usage_by_model(
    days: int = Query(default=7, ge=1, le=90),
    db: AsyncSession = Depends(get_session),
):
    """Get LLM usage breakdown by model."""
    since = datetime.utcnow() - timedelta(days=days)

    result = await db.execute(
        select(
            LLMUsage.model_name,
            func.count(LLMUsage.id).label("total_calls"),
            func.sum(LLMUsage.input_tokens).label("total_input_tokens"),
            func.sum(LLMUsage.output_tokens).label("total_output_tokens"),
            func.avg(LLMUsage.response_time_ms).label("avg_response_time_ms"),
        )
        .where(LLMUsage.created_at >= since)
        .group_by(LLMUsage.model_name)
        .order_by(func.sum(LLMUsage.input_tokens + LLMUsage.output_tokens).desc())
    )

    return [
        {
            "model_name": row.model_name,
            "total_calls": row.total_calls,
            "total_input_tokens": row.total_input_tokens or 0,
            "total_output_tokens": row.total_output_tokens or 0,
            "total_tokens": (row.total_input_tokens or 0) + (row.total_output_tokens or 0),
            "avg_response_time_ms": row.avg_response_time_ms,
        }
        for row in result.all()
    ]


@router.get("/timeseries", response_model=List[LLMUsageTimeSeriesResponse])
async def get_usage_timeseries(
    days: int = Query(default=7, ge=1, le=30),
    granularity: str = Query(default="hour", enum=["hour", "day"]),
    db: AsyncSession = Depends(get_session),
):
    """Get LLM usage over time for charting."""
    since = datetime.utcnow() - timedelta(days=days)

    # Use pre-aggregated data if available, otherwise query raw
    if granularity == "day":
        result = await db.execute(
            select(
                func.date(LLMUsage.created_at).label("period"),
                func.count(LLMUsage.id).label("total_calls"),
                func.sum(LLMUsage.input_tokens).label("total_input_tokens"),
                func.sum(LLMUsage.output_tokens).label("total_output_tokens"),
            )
            .where(LLMUsage.created_at >= since)
            .group_by(func.date(LLMUsage.created_at))
            .order_by(func.date(LLMUsage.created_at))
        )
    else:
        result = await db.execute(
            select(
                func.strftime('%Y-%m-%d %H:00', LLMUsage.created_at).label("period"),
                func.count(LLMUsage.id).label("total_calls"),
                func.sum(LLMUsage.input_tokens).label("total_input_tokens"),
                func.sum(LLMUsage.output_tokens).label("total_output_tokens"),
            )
            .where(LLMUsage.created_at >= since)
            .group_by(func.strftime('%Y-%m-%d %H:00', LLMUsage.created_at))
            .order_by(func.strftime('%Y-%m-%d %H:00', LLMUsage.created_at))
        )

    return [
        {
            "period": str(row.period),
            "total_calls": row.total_calls,
            "total_tokens": (row.total_input_tokens or 0) + (row.total_output_tokens or 0),
        }
        for row in result.all()
    ]


@router.get("/session/{session_id}", response_model=SessionUsageSummaryResponse)
async def get_session_usage(
    session_id: str,
    db: AsyncSession = Depends(get_session),
):
    """Get LLM usage for a specific chat session."""
    result = await db.execute(
        select(
            func.count(LLMUsage.id).label("total_calls"),
            func.sum(LLMUsage.input_tokens).label("total_input_tokens"),
            func.sum(LLMUsage.output_tokens).label("total_output_tokens"),
            func.avg(LLMUsage.response_time_ms).label("avg_response_time_ms"),
            func.min(LLMUsage.created_at).label("first_call"),
            func.max(LLMUsage.created_at).label("last_call"),
        ).where(LLMUsage.chat_session_id == session_id)
    )

    row = result.one()

    # Get breakdown by agent
    agent_result = await db.execute(
        select(
            LLMUsage.agent_type,
            func.sum(LLMUsage.input_tokens + LLMUsage.output_tokens).label("tokens"),
        )
        .where(LLMUsage.chat_session_id == session_id)
        .group_by(LLMUsage.agent_type)
    )

    return {
        "session_id": session_id,
        "total_calls": row.total_calls or 0,
        "total_input_tokens": row.total_input_tokens or 0,
        "total_output_tokens": row.total_output_tokens or 0,
        "total_tokens": (row.total_input_tokens or 0) + (row.total_output_tokens or 0),
        "avg_response_time_ms": row.avg_response_time_ms,
        "first_call": row.first_call.isoformat() if row.first_call else None,
        "last_call": row.last_call.isoformat() if row.last_call else None,
        "by_agent": {r.agent_type: r.tokens for r in agent_result.all()},
    }


@router.get("/recent", response_model=List[LLMUsageResponse])
async def get_recent_usage(
    limit: int = Query(default=50, ge=1, le=500),
    agent_type: Optional[str] = None,
    model_name: Optional[str] = None,
    db: AsyncSession = Depends(get_session),
):
    """Get recent LLM usage records for debugging/monitoring."""
    query = select(LLMUsage).order_by(LLMUsage.created_at.desc()).limit(limit)

    if agent_type:
        query = query.where(LLMUsage.agent_type == agent_type)
    if model_name:
        query = query.where(LLMUsage.model_name == model_name)

    result = await db.execute(query)
    return result.scalars().all()
```

### 4. Pydantic Schemas

```python
# src/models/schemas.py additions

class LLMUsageResponse(BaseModel):
    """Single LLM usage record."""
    id: int
    agent_type: str
    agent_name: Optional[str]
    model_name: str
    llm_method: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    token_estimation_method: str
    response_time_ms: Optional[float]
    success: bool
    error_message: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class LLMUsageStatsResponse(BaseModel):
    """Overall usage statistics."""
    period_days: int
    total_calls: int
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    avg_response_time_ms: Optional[float]
    unique_sessions: int
    models_used: int


class LLMUsageByAgentResponse(BaseModel):
    """Usage breakdown by agent type."""
    agent_type: str
    total_calls: int
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    avg_response_time_ms: Optional[float]
    percentage_of_total: Optional[float] = None


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
    avg_response_time_ms: Optional[float]
    first_call: Optional[str]
    last_call: Optional[str]
    by_agent: Dict[str, int]


class InlineUsageStats(BaseModel):
    """Lightweight stats for inline display in chat."""
    tokens_used: int
    llm_calls: int
    response_time_ms: float
    agents_involved: List[str]
```

---

## Frontend Implementation

### 1. Dashboard Page (`/dashboard/llm-usage`)

#### Layout Components

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  LLM Usage Dashboard                                      [7d] [30d] [90d]  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ Total Tokens│  │ Total Calls │  │ Avg Response│  │ Active      │        │
│  │   1.2M      │  │   4,521     │  │   342ms     │  │ Sessions: 89│        │
│  │  ↑12% week  │  │  ↑8% week   │  │  ↓5% week   │  │             │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Token Usage Over Time                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │     ▄▄                                                               │   │
│  │    ████  ▄▄   ▄▄                      ▄▄                             │   │
│  │   █████ ████ ████  ▄▄      ▄▄   ▄▄   ████                           │   │
│  │  ██████ █████████ ████    ████ ████ ██████  ▄▄                       │   │
│  │ ███████████████████████  ████████████████████████                    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│   Mon    Tue    Wed    Thu    Fri    Sat    Sun                            │
│                                                                             │
├──────────────────────────────────┬──────────────────────────────────────────┤
│                                  │                                          │
│  Usage by Agent                  │  Usage by Model                          │
│  ┌────────────────────────────┐  │  ┌────────────────────────────────────┐  │
│  │ ████████████ SQL Generator │  │  │ ████████████████ qwen2.5-coder:32b │  │
│  │ ████████  Result Narrator  │  │  │ ████████ llama3.2:latest           │  │
│  │ ██████    Query Planning   │  │  │ ███ mistral:7b                     │  │
│  │ █████     Lineage Agents   │  │  │                                    │  │
│  │ ███       Confidence Score │  │  │                                    │  │
│  └────────────────────────────┘  │  └────────────────────────────────────┘  │
│                                  │                                          │
├──────────────────────────────────┴──────────────────────────────────────────┤
│                                                                             │
│  Recent LLM Calls                                          [Filter: All ▼]  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Time       Agent              Model           In/Out    Response    │   │
│  │ 10:23:45   sql_generator     qwen2.5:32b     1.2k/340   234ms      │   │
│  │ 10:23:44   result_narrator   qwen2.5:32b     890/520    456ms      │   │
│  │ 10:22:12   query_planning    llama3.2        450/180    123ms      │   │
│  │ 10:22:10   sql_generator     qwen2.5:32b     1.1k/280   198ms      │   │
│  │ ...                                                                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### React Components

```typescript
// frontend/src/components/dashboard/LLMUsageDashboard.tsx

interface LLMUsageDashboardProps {}

export const LLMUsageDashboard: React.FC<LLMUsageDashboardProps> = () => {
  const [timeRange, setTimeRange] = useState<7 | 30 | 90>(7);
  const { data: stats, isLoading: statsLoading } = useLLMUsageStats(timeRange);
  const { data: byAgent } = useLLMUsageByAgent(timeRange);
  const { data: byModel } = useLLMUsageByModel(timeRange);
  const { data: timeseries } = useLLMUsageTimeseries(timeRange);
  const { data: recentCalls } = useRecentLLMCalls(50);

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">LLM Usage Dashboard</h1>
        <TimeRangeSelector value={timeRange} onChange={setTimeRange} />
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard
          title="Total Tokens"
          value={formatNumber(stats?.total_tokens)}
          trend={stats?.token_trend}
        />
        <StatCard
          title="Total Calls"
          value={formatNumber(stats?.total_calls)}
          trend={stats?.calls_trend}
        />
        <StatCard
          title="Avg Response"
          value={`${stats?.avg_response_time_ms?.toFixed(0)}ms`}
        />
        <StatCard
          title="Active Sessions"
          value={stats?.unique_sessions}
        />
      </div>

      {/* Time Series Chart */}
      <Card>
        <CardHeader>Token Usage Over Time</CardHeader>
        <CardContent>
          <TokenUsageChart data={timeseries} />
        </CardContent>
      </Card>

      {/* Agent & Model Breakdown */}
      <div className="grid grid-cols-2 gap-4">
        <Card>
          <CardHeader>Usage by Agent</CardHeader>
          <CardContent>
            <HorizontalBarChart data={byAgent} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>Usage by Model</CardHeader>
          <CardContent>
            <HorizontalBarChart data={byModel} />
          </CardContent>
        </Card>
      </div>

      {/* Recent Calls Table */}
      <Card>
        <CardHeader>Recent LLM Calls</CardHeader>
        <CardContent>
          <RecentCallsTable data={recentCalls} />
        </CardContent>
      </Card>
    </div>
  );
};
```

### 2. Inline Chat Usage Display

Add a collapsible usage summary to each chat message response:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ User: What are the top 10 customers by revenue?                            │
├─────────────────────────────────────────────────────────────────────────────┤
│ Assistant:                                                                  │
│                                                                             │
│ SELECT c.name, SUM(o.total) as revenue                                     │
│ FROM customers c JOIN orders o ON c.id = o.customer_id                     │
│ GROUP BY c.id ORDER BY revenue DESC LIMIT 10;                              │
│                                                                             │
│ [Results Table: 10 rows]                                                    │
│                                                                             │
│ ┌───────────────────────────────────────────────────────────────────────┐  │
│ │ 📊 Usage: 1,847 tokens | 3 LLM calls | 892ms                    [▼]  │  │
│ └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│ Expanded view:                                                              │
│ ┌───────────────────────────────────────────────────────────────────────┐  │
│ │ Agent Breakdown:                                                      │  │
│ │   • sql_generator: 1,203 tokens (65%)                                │  │
│ │   • query_planning: 384 tokens (21%)                                  │  │
│ │   • result_narrator: 260 tokens (14%)                                │  │
│ │                                                                       │  │
│ │ Model: qwen2.5-coder:32b                                             │  │
│ │ Total Response Time: 892ms                                            │  │
│ └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### React Component

```typescript
// frontend/src/components/chat/UsageSummary.tsx

interface UsageSummaryProps {
  sessionId: string;
  messageId: number;
  compact?: boolean;
}

export const UsageSummary: React.FC<UsageSummaryProps> = ({
  sessionId,
  messageId,
  compact = true,
}) => {
  const [expanded, setExpanded] = useState(false);
  const { data: usage } = useMessageUsage(sessionId, messageId);

  if (!usage) return null;

  if (compact && !expanded) {
    return (
      <button
        onClick={() => setExpanded(true)}
        className="flex items-center gap-2 text-xs text-gray-500 hover:text-gray-700"
      >
        <BarChart2 className="w-3 h-3" />
        <span>
          {formatNumber(usage.tokens_used)} tokens | {usage.llm_calls} calls |{' '}
          {usage.response_time_ms.toFixed(0)}ms
        </span>
        <ChevronDown className="w-3 h-3" />
      </button>
    );
  }

  return (
    <div className="mt-2 p-3 bg-gray-50 rounded-lg text-sm">
      <div className="flex justify-between items-start">
        <div className="space-y-2">
          <div className="font-medium">Agent Breakdown:</div>
          {usage.by_agent.map(({ agent, tokens, percentage }) => (
            <div key={agent} className="flex items-center gap-2">
              <div
                className="h-2 bg-blue-500 rounded"
                style={{ width: `${percentage}%`, maxWidth: '150px' }}
              />
              <span>
                {agent}: {formatNumber(tokens)} ({percentage.toFixed(0)}%)
              </span>
            </div>
          ))}
        </div>
        <button onClick={() => setExpanded(false)} className="text-gray-400">
          <ChevronUp className="w-4 h-4" />
        </button>
      </div>
      <div className="mt-2 text-gray-500">
        Model: {usage.model_name} | Total: {usage.response_time_ms.toFixed(0)}ms
      </div>
    </div>
  );
};
```

### 3. Session Usage Summary (Sidebar or Header)

Show running totals for the current chat session:

```typescript
// frontend/src/components/chat/SessionUsageBadge.tsx

interface SessionUsageBadgeProps {
  sessionId: string;
}

export const SessionUsageBadge: React.FC<SessionUsageBadgeProps> = ({
  sessionId,
}) => {
  const { data: usage } = useSessionUsage(sessionId);

  if (!usage) return null;

  return (
    <div className="flex items-center gap-4 text-xs text-gray-500">
      <div className="flex items-center gap-1">
        <Zap className="w-3 h-3" />
        <span>{formatNumber(usage.total_tokens)} tokens</span>
      </div>
      <div className="flex items-center gap-1">
        <MessageSquare className="w-3 h-3" />
        <span>{usage.total_calls} calls</span>
      </div>
    </div>
  );
};
```

---

## Agent Integration Map

The following agents need to be updated to call the tracked LLM methods:

| Agent | File | Method to Update | Priority |
|-------|------|------------------|----------|
| SQL Generator | `src/llm/sql_generator.py` | `generate()` | High |
| Self-Correcting | `src/llm/self_correcting_agent.py` | Multiple calls | High |
| Query Planning | `src/llm/query_planning_agent.py` | `generate()` | High |
| Result Narrator | `src/llm/result_narrator.py` | `generate()` | High |
| Lineage Narrator | `src/lineage/lineage_narrator.py` | `generate()` | Medium |
| Impact Advisor | `src/lineage/impact_advisor.py` | `generate()` | Medium |
| Schema Health | `src/lineage/schema_health_analyzer.py` | `generate()` | Medium |
| Pattern Intel | `src/lineage/pattern_intelligence.py` | `generate()` | Medium |
| Lineage Convo | `src/lineage/lineage_conversation_agent.py` | `chat()` | Medium |
| Tool-Using | `src/llm/tool_using_agent.py` | Multiple | Low |

---

## Implementation Phases

### Phase 1: Core Infrastructure (Foundation)
- [ ] Create database migrations for new tables
- [ ] Implement `LLMUsageTracker` service
- [ ] Add `generate_tracked()` and `chat_tracked()` to OllamaClient
- [ ] Create basic API endpoints (`/llm/usage/stats`, `/llm/usage/by-agent`)
- [ ] Add unit tests for tracker service

### Phase 2: Agent Integration
- [ ] Update SQL Generator to use tracked methods
- [ ] Update Self-Correcting Agent
- [ ] Update Query Planning Agent
- [ ] Update Result Narrator
- [ ] Pass `chat_session_id` through the call chain
- [ ] Integration tests for tracking flow

### Phase 3: Dashboard Frontend
- [ ] Create dashboard page route
- [ ] Implement stat cards component
- [ ] Implement time series chart (use Recharts or Chart.js)
- [ ] Implement agent/model breakdown charts
- [ ] Implement recent calls table
- [ ] Add navigation link to dashboard

### Phase 4: Inline Chat Integration
- [ ] Add `UsageSummary` component to chat messages
- [ ] Implement `SessionUsageBadge` in chat header
- [ ] Create API endpoint for message-specific usage
- [ ] Style and polish the inline displays

### Phase 5: Lineage Agent Integration
- [ ] Update Lineage Narrator
- [ ] Update Impact Advisor
- [ ] Update Schema Health Analyzer
- [ ] Update Pattern Intelligence
- [ ] Update Lineage Conversation Agent

### Phase 6: Advanced Features (Optional)
- [ ] Implement usage aggregation background job
- [ ] Add budget/limit controls
- [ ] Add cost estimation (if relevant)
- [ ] Export usage reports (CSV/JSON)
- [ ] Usage alerts and notifications

---

## API Summary

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/llm/usage/stats` | GET | Overall statistics for time period |
| `/llm/usage/by-agent` | GET | Breakdown by agent type |
| `/llm/usage/by-model` | GET | Breakdown by model |
| `/llm/usage/timeseries` | GET | Time series for charts |
| `/llm/usage/session/{id}` | GET | Usage for specific session |
| `/llm/usage/recent` | GET | Recent LLM calls (debugging) |
| `/llm/usage/message/{id}` | GET | Usage for specific message |

---

## Configuration Additions

```python
# src/config/settings.py additions

class Settings(BaseSettings):
    # ... existing settings ...

    # LLM Usage Tracking
    LLM_USAGE_TRACKING_ENABLED: bool = True
    LLM_USAGE_STORE_PROMPTS: bool = True  # Store prompt summaries (privacy consideration)
    LLM_USAGE_PROMPT_MAX_LENGTH: int = 500  # Truncate stored prompts
    LLM_USAGE_AGGREGATION_ENABLED: bool = True

    # Token Estimation
    LLM_TOKEN_ESTIMATION_METHOD: str = "tiktoken"  # 'tiktoken', 'chars', 'ollama_native'

    # Optional: Cost Tracking
    LLM_COST_TRACKING_ENABLED: bool = False
    LLM_DEFAULT_COST_PER_1M_INPUT: float = 0.0
    LLM_DEFAULT_COST_PER_1M_OUTPUT: float = 0.0
```

---

## Privacy Considerations

1. **Prompt Storage**: Consider making prompt summary storage optional (can be disabled in settings)
2. **User Data**: Don't store actual query results in usage records
3. **Retention**: Consider adding a data retention policy for old usage records
4. **Access Control**: Dashboard should respect user permissions when implemented

---

## Testing Strategy

1. **Unit Tests**
   - Token estimation accuracy
   - Usage tracker context manager behavior
   - API endpoint response formats

2. **Integration Tests**
   - Full flow: query → LLM call → usage recorded → API returns data
   - Session linking verification
   - Agent tracking across the full request lifecycle

3. **Performance Tests**
   - Ensure tracking adds minimal latency (<5ms per call)
   - Dashboard queries remain fast with large datasets

---

## Future Enhancements

1. **Real-time Dashboard**: WebSocket updates for live usage monitoring
2. **Anomaly Detection**: Alert when usage patterns change significantly
3. **Cost Optimization**: Suggest model routing changes to reduce costs
4. **Comparative Analysis**: Compare efficiency across different query types
5. **User-level Tracking**: Per-user usage limits and dashboards
6. **Export & Billing**: Generate usage reports for cost allocation

---

## Dependencies

### Backend
```
tiktoken>=0.5.0  # Token estimation
```

### Frontend
```
recharts  # Charts (already may be installed)
# or
chart.js + react-chartjs-2
```

---

## Related Documentation

- [AGENTS.md](/.claude/AGENTS.md) - Agent architecture reference
- [ARCHITECTURE.md](/.claude/ARCHITECTURE.md) - System architecture
- [API.md](/.claude/API.md) - Existing API documentation

---

*Document Version: 1.0*
*Created: 2026-02-01*
*Status: Planning*
