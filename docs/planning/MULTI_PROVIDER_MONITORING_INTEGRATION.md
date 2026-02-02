# Multi-Provider Monitoring Integration

## Overview

This document outlines the plan for extending LLM usage monitoring capabilities to all supported providers after both the base monitoring system (Ollama) and the provider expansion are complete.

**Prerequisites:**
- ✅ LLM Usage Monitoring (Ollama) - Must be implemented first
- ✅ LLM Provider Expansion (Phase 14) - Must be implemented first

**This Feature:** Integrates monitoring across all providers with provider-specific enhancements.

---

## Dependencies

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FEATURE DEPENDENCY CHAIN                          │
└─────────────────────────────────────────────────────────────────────────────┘

  ┌────────────────────────┐     ┌────────────────────────┐
  │  LLM Usage Monitoring  │     │  LLM Provider Expansion │
  │  (Ollama-based)        │     │  (Phase 14)             │
  │                        │     │                         │
  │  • LLMUsage table      │     │  • BaseLLMProvider      │
  │  • LLMUsageTracker     │     │  • Provider registry    │
  │  • Dashboard UI        │     │  • OpenAI, Anthropic... │
  │  • Inline stats        │     │  • Enhanced router      │
  └───────────┬────────────┘     └───────────┬─────────────┘
              │                              │
              └──────────────┬───────────────┘
                             │
                             ▼
              ┌────────────────────────────┐
              │  MULTI-PROVIDER MONITORING │  ← This Feature
              │  INTEGRATION               │
              │                            │
              │  • Provider-specific costs │
              │  • Native token counts     │
              │  • Cost comparison         │
              │  • Provider analytics      │
              └────────────────────────────┘
```

---

## Goals

1. **Unified Tracking** - All providers report to the same monitoring system
2. **Native Token Counts** - Use each provider's native token reporting (not estimates)
3. **Accurate Cost Tracking** - Real pricing per provider/model
4. **Provider Comparison** - Compare costs and performance across providers
5. **Seamless Integration** - Minimal changes to existing provider implementations

---

## Architecture

### Integration Points

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        MONITORING INTEGRATION FLOW                          │
└─────────────────────────────────────────────────────────────────────────────┘

  Provider Response (varies by provider)
  ┌─────────────────────────────────────────────────────────────────────────┐
  │                                                                         │
  │  OpenAI Response:          Anthropic Response:      Ollama Response:    │
  │  {                         {                        {                   │
  │    usage: {                  usage: {                 eval_count: 150,  │
  │      prompt_tokens: 100,       input_tokens: 100,     prompt_eval_count:│
  │      completion_tokens: 50,    output_tokens: 50      100               │
  │      total_tokens: 150       }                      }                   │
  │    }                       }                                            │
  │  }                                                                      │
  │                                                                         │
  └─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │                      PROVIDER TOKEN EXTRACTOR                           │
  │                                                                         │
  │   Normalizes all provider responses to unified UsageMetrics format      │
  │                                                                         │
  │   class UsageMetrics:                                                   │
  │       input_tokens: int                                                 │
  │       output_tokens: int                                                │
  │       total_tokens: int                                                 │
  │       cost_usd: float                                                   │
  │       token_source: str  # "native" | "estimated"                       │
  │                                                                         │
  └─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │                         LLM USAGE TRACKER                               │
  │                      (from base monitoring)                             │
  │                                                                         │
  │   Records to llm_usage table with provider-specific data                │
  │                                                                         │
  └─────────────────────────────────────────────────────────────────────────┘
```

---

## Provider-Specific Token Extraction

### Token Response Formats by Provider

| Provider | Input Tokens Field | Output Tokens Field | Native Counting |
|----------|-------------------|---------------------|-----------------|
| Ollama | `prompt_eval_count` | `eval_count` | ✅ Yes |
| OpenAI | `usage.prompt_tokens` | `usage.completion_tokens` | ✅ Yes |
| Anthropic | `usage.input_tokens` | `usage.output_tokens` | ✅ Yes |
| Google | `usage_metadata.prompt_token_count` | `usage_metadata.candidates_token_count` | ✅ Yes |
| Azure OpenAI | `usage.prompt_tokens` | `usage.completion_tokens` | ✅ Yes |
| Groq | `usage.prompt_tokens` | `usage.completion_tokens` | ✅ Yes |
| Together | `usage.prompt_tokens` | `usage.completion_tokens` | ✅ Yes |

### Token Extractor Implementation

```python
# src/llm/monitoring/token_extractors.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any

from src.llm.providers.base import ProviderType


@dataclass
class UsageMetrics:
    """Normalized usage metrics from any provider."""
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float
    token_source: str  # "native" or "estimated"
    raw_usage: Optional[Dict[str, Any]] = None


class TokenExtractor(ABC):
    """Base class for extracting tokens from provider responses."""

    @abstractmethod
    def extract(self, response: Dict[str, Any]) -> UsageMetrics:
        """Extract usage metrics from provider response."""
        pass

    @abstractmethod
    def calculate_cost(self, input_tokens: int, output_tokens: int, model: str) -> float:
        """Calculate cost based on provider pricing."""
        pass


class OllamaTokenExtractor(TokenExtractor):
    """Extract tokens from Ollama responses."""

    def extract(self, response: Dict[str, Any]) -> UsageMetrics:
        input_tokens = response.get("prompt_eval_count", 0)
        output_tokens = response.get("eval_count", 0)

        return UsageMetrics(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost_usd=0.0,  # Ollama is free
            token_source="native" if input_tokens or output_tokens else "estimated",
            raw_usage=response,
        )

    def calculate_cost(self, input_tokens: int, output_tokens: int, model: str) -> float:
        return 0.0  # Local, no cost


class OpenAITokenExtractor(TokenExtractor):
    """Extract tokens from OpenAI responses."""

    # Pricing per 1M tokens (as of 2024)
    PRICING = {
        "gpt-4o": {"input": 2.50, "output": 10.00},
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "gpt-4-turbo": {"input": 10.00, "output": 30.00},
        "gpt-4": {"input": 30.00, "output": 60.00},
        "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    }

    def extract(self, response: Dict[str, Any]) -> UsageMetrics:
        usage = response.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)

        model = response.get("model", "gpt-4o-mini")
        cost = self.calculate_cost(input_tokens, output_tokens, model)

        return UsageMetrics(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost_usd=cost,
            token_source="native",
            raw_usage=usage,
        )

    def calculate_cost(self, input_tokens: int, output_tokens: int, model: str) -> float:
        # Find base model (handle versioned names)
        base_model = model.split("-202")[0] if "-202" in model else model
        pricing = self.PRICING.get(base_model, {"input": 0.0, "output": 0.0})

        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return input_cost + output_cost


class AnthropicTokenExtractor(TokenExtractor):
    """Extract tokens from Anthropic responses."""

    PRICING = {
        "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
        "claude-3-5-haiku": {"input": 0.80, "output": 4.00},
        "claude-3-opus": {"input": 15.00, "output": 75.00},
        "claude-3-sonnet": {"input": 3.00, "output": 15.00},
        "claude-3-haiku": {"input": 0.25, "output": 1.25},
    }

    def extract(self, response: Dict[str, Any]) -> UsageMetrics:
        usage = response.get("usage", {})
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)

        model = response.get("model", "claude-3-5-sonnet")
        cost = self.calculate_cost(input_tokens, output_tokens, model)

        return UsageMetrics(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost_usd=cost,
            token_source="native",
            raw_usage=usage,
        )

    def calculate_cost(self, input_tokens: int, output_tokens: int, model: str) -> float:
        # Normalize model name
        base_model = model.split("-2024")[0].split("-2025")[0]
        pricing = self.PRICING.get(base_model, {"input": 0.0, "output": 0.0})

        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return input_cost + output_cost


class GoogleTokenExtractor(TokenExtractor):
    """Extract tokens from Google Gemini responses."""

    PRICING = {
        "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
        "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
        "gemini-1.0-pro": {"input": 0.50, "output": 1.50},
    }

    def extract(self, response: Dict[str, Any]) -> UsageMetrics:
        usage = response.get("usage_metadata", {})
        input_tokens = usage.get("prompt_token_count", 0)
        output_tokens = usage.get("candidates_token_count", 0)

        model = response.get("model", "gemini-1.5-flash")
        cost = self.calculate_cost(input_tokens, output_tokens, model)

        return UsageMetrics(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost_usd=cost,
            token_source="native" if usage else "estimated",
            raw_usage=usage,
        )

    def calculate_cost(self, input_tokens: int, output_tokens: int, model: str) -> float:
        pricing = self.PRICING.get(model, {"input": 0.0, "output": 0.0})
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return input_cost + output_cost


class AzureOpenAITokenExtractor(OpenAITokenExtractor):
    """Extract tokens from Azure OpenAI (same format as OpenAI)."""

    # Azure pricing may differ slightly, override if needed
    pass


# Registry
TOKEN_EXTRACTORS: Dict[ProviderType, TokenExtractor] = {
    ProviderType.OLLAMA: OllamaTokenExtractor(),
    ProviderType.OPENAI: OpenAITokenExtractor(),
    ProviderType.ANTHROPIC: AnthropicTokenExtractor(),
    ProviderType.GOOGLE: GoogleTokenExtractor(),
    ProviderType.AZURE_OPENAI: AzureOpenAITokenExtractor(),
}


def get_token_extractor(provider: ProviderType) -> TokenExtractor:
    """Get the appropriate token extractor for a provider."""
    return TOKEN_EXTRACTORS.get(provider, OllamaTokenExtractor())
```

---

## Enhanced LLMResponse

Update the base `LLMResponse` to include usage metrics:

```python
# src/llm/providers/base.py (updates)

@dataclass
class LLMResponse:
    """Provider-agnostic response format with usage metrics."""
    content: str
    model: str
    provider: ProviderType

    # Timing
    response_time_ms: Optional[float] = None

    # Usage metrics (populated by token extractor)
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    cost_usd: Optional[float] = None
    token_source: str = "estimated"  # "native" or "estimated"

    # Raw response
    raw_response: Optional[Dict[str, Any]] = None
    finish_reason: Optional[str] = None

    def has_native_tokens(self) -> bool:
        """Check if tokens were natively reported by provider."""
        return self.token_source == "native"
```

---

## Provider Base Class Updates

Update `BaseLLMProvider` to automatically extract usage:

```python
# src/llm/providers/base.py (updates)

from src.llm.monitoring.token_extractors import get_token_extractor, UsageMetrics


class LLMClient(ABC):
    """Abstract base class for all LLM providers."""

    provider_type: ProviderType

    def __init__(self, config: LLMConfig):
        self.config = config
        self.model = config.model
        self._token_extractor = get_token_extractor(self.provider_type)

    def _enrich_response(self, response: LLMResponse, raw: Dict[str, Any]) -> LLMResponse:
        """Enrich response with usage metrics from raw provider response."""
        try:
            metrics = self._token_extractor.extract(raw)
            response.input_tokens = metrics.input_tokens
            response.output_tokens = metrics.output_tokens
            response.total_tokens = metrics.total_tokens
            response.cost_usd = metrics.cost_usd
            response.token_source = metrics.token_source
        except Exception:
            # If extraction fails, leave as estimated
            pass
        return response
```

---

## Enhanced Usage Tracker

Update the usage tracker to handle multi-provider data:

```python
# src/services/llm_usage_tracker.py (updates)

class LLMUsageTracker:
    """Centralized LLM usage tracking service - multi-provider support."""

    async def track_from_response(
        self,
        db: AsyncSession,
        response: LLMResponse,
        agent_type: str,
        query_history_id: Optional[int] = None,
        chat_session_id: Optional[str] = None,
        chat_message_id: Optional[int] = None,
        agent_name: Optional[str] = None,
        prompt_text: Optional[str] = None,
    ) -> LLMUsage:
        """
        Track usage directly from an LLMResponse object.
        Uses native token counts when available.
        """
        usage_record = LLMUsage(
            query_history_id=query_history_id,
            chat_session_id=chat_session_id,
            chat_message_id=chat_message_id,
            agent_type=agent_type,
            agent_name=agent_name,
            model_name=response.model,
            provider=response.provider.value,  # NEW: Track provider
            llm_method="chat",
            input_tokens=response.input_tokens or 0,
            output_tokens=response.output_tokens or 0,
            token_estimation_method=response.token_source,
            request_timestamp=datetime.utcnow(),
            response_time_ms=response.response_time_ms,
            prompt_summary=prompt_text[:500] if prompt_text else None,
            response_summary=response.content[:500] if response.content else None,
            success=True,
            estimated_cost_usd=response.cost_usd,
        )

        db.add(usage_record)
        await db.commit()
        return usage_record
```

---

## Database Schema Updates

Add provider field to usage table:

```sql
-- Migration: Add provider column to llm_usage
ALTER TABLE llm_usage ADD COLUMN provider VARCHAR(50) DEFAULT 'ollama';
CREATE INDEX idx_llm_usage_provider ON llm_usage(provider);

-- Add cost tracking columns if not present
ALTER TABLE llm_usage ADD COLUMN estimated_cost_usd FLOAT DEFAULT 0.0;
```

```python
# src/database/models.py (updates to LLMUsage)

class LLMUsage(Base):
    __tablename__ = "llm_usage"

    # ... existing fields ...

    # Provider tracking (NEW)
    provider = Column(String(50), nullable=False, default="ollama", index=True)

    # Cost tracking
    estimated_cost_usd = Column(Float, default=0.0)
```

---

## New API Endpoints

### Provider-Specific Stats

```python
# src/api/endpoints/llm_usage.py (additions)

@router.get("/by-provider", response_model=List[ProviderUsageStats])
async def get_usage_by_provider(
    days: int = Query(default=7, ge=1, le=90),
    db: AsyncSession = Depends(get_session),
):
    """Get LLM usage breakdown by provider."""
    since = datetime.utcnow() - timedelta(days=days)

    result = await db.execute(
        select(
            LLMUsage.provider,
            func.count(LLMUsage.id).label("total_calls"),
            func.sum(LLMUsage.input_tokens).label("total_input_tokens"),
            func.sum(LLMUsage.output_tokens).label("total_output_tokens"),
            func.sum(LLMUsage.estimated_cost_usd).label("total_cost"),
            func.avg(LLMUsage.response_time_ms).label("avg_response_time_ms"),
        )
        .where(LLMUsage.created_at >= since)
        .group_by(LLMUsage.provider)
        .order_by(func.sum(LLMUsage.estimated_cost_usd).desc())
    )

    return [
        {
            "provider": row.provider,
            "total_calls": row.total_calls,
            "total_input_tokens": row.total_input_tokens or 0,
            "total_output_tokens": row.total_output_tokens or 0,
            "total_tokens": (row.total_input_tokens or 0) + (row.total_output_tokens or 0),
            "total_cost_usd": row.total_cost or 0.0,
            "avg_response_time_ms": row.avg_response_time_ms,
        }
        for row in result.all()
    ]


@router.get("/cost-summary", response_model=CostSummaryResponse)
async def get_cost_summary(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_session),
):
    """Get cost summary across all providers."""
    since = datetime.utcnow() - timedelta(days=days)

    result = await db.execute(
        select(
            func.sum(LLMUsage.estimated_cost_usd).label("total_cost"),
            func.sum(LLMUsage.input_tokens).label("total_input_tokens"),
            func.sum(LLMUsage.output_tokens).label("total_output_tokens"),
            func.count(LLMUsage.id).label("total_calls"),
        )
        .where(LLMUsage.created_at >= since)
    )

    row = result.one()

    # Get daily breakdown
    daily_result = await db.execute(
        select(
            func.date(LLMUsage.created_at).label("date"),
            func.sum(LLMUsage.estimated_cost_usd).label("cost"),
        )
        .where(LLMUsage.created_at >= since)
        .group_by(func.date(LLMUsage.created_at))
        .order_by(func.date(LLMUsage.created_at))
    )

    return {
        "period_days": days,
        "total_cost_usd": row.total_cost or 0.0,
        "total_tokens": (row.total_input_tokens or 0) + (row.total_output_tokens or 0),
        "total_calls": row.total_calls or 0,
        "avg_cost_per_call": (row.total_cost or 0) / (row.total_calls or 1),
        "daily_costs": [
            {"date": str(r.date), "cost_usd": r.cost or 0.0}
            for r in daily_result.all()
        ],
    }


@router.get("/provider-comparison", response_model=ProviderComparisonResponse)
async def get_provider_comparison(
    days: int = Query(default=7, ge=1, le=90),
    db: AsyncSession = Depends(get_session),
):
    """Compare performance and cost across providers."""
    since = datetime.utcnow() - timedelta(days=days)

    result = await db.execute(
        select(
            LLMUsage.provider,
            LLMUsage.agent_type,
            func.count(LLMUsage.id).label("calls"),
            func.avg(LLMUsage.response_time_ms).label("avg_latency"),
            func.sum(LLMUsage.estimated_cost_usd).label("total_cost"),
            func.avg(
                (LLMUsage.input_tokens + LLMUsage.output_tokens)
            ).label("avg_tokens_per_call"),
        )
        .where(LLMUsage.created_at >= since)
        .group_by(LLMUsage.provider, LLMUsage.agent_type)
    )

    # Organize by agent type for comparison
    comparison = {}
    for row in result.all():
        agent = row.agent_type
        if agent not in comparison:
            comparison[agent] = {}
        comparison[agent][row.provider] = {
            "calls": row.calls,
            "avg_latency_ms": row.avg_latency,
            "total_cost_usd": row.total_cost or 0.0,
            "avg_tokens_per_call": row.avg_tokens_per_call,
        }

    return {"period_days": days, "by_agent_type": comparison}
```

---

## Dashboard Updates

### Provider Cost Breakdown Widget

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Cost by Provider (Last 30 Days)                              Total: $12.47 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ OpenAI        ████████████████████████████████████  $8.23  (66%)      │ │
│  │ Anthropic     ████████████                          $3.15  (25%)      │ │
│  │ Google        ████                                  $1.09  (9%)       │ │
│  │ Ollama        (free)                                $0.00  (0%)       │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Provider Performance Comparison

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Provider Performance Comparison                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  SQL Generation Task                                                        │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ Provider      │ Avg Latency │ Avg Tokens │ Cost/Call │ Calls          │ │
│  │ ─────────────────────────────────────────────────────────────────────  │ │
│  │ OpenAI        │    342ms    │    1,247   │  $0.0019  │   523          │ │
│  │ Anthropic     │    456ms    │    1,389   │  $0.0042  │   234          │ │
│  │ Ollama        │    892ms    │    1,156   │  $0.0000  │  1,847         │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  Result Narratives Task                                                     │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ Provider      │ Avg Latency │ Avg Tokens │ Cost/Call │ Calls          │ │
│  │ ─────────────────────────────────────────────────────────────────────  │ │
│  │ Anthropic     │    234ms    │      892   │  $0.0027  │   456          │ │
│  │ OpenAI        │    298ms    │      756   │  $0.0011  │   312          │ │
│  │ Ollama        │    567ms    │      834   │  $0.0000  │   923          │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Daily Cost Trend

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Daily Cost Trend                                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  $2.00 ┤                                                                    │
│        │                    ▄▄                                              │
│  $1.50 ┤              ▄▄   ████                                             │
│        │        ▄▄   ████ ██████  ▄▄                                        │
│  $1.00 ┤   ▄▄  ████ █████████████████  ▄▄                                   │
│        │  ████ █████████████████████████████                                │
│  $0.50 ┤ ██████████████████████████████████████                             │
│        │████████████████████████████████████████                            │
│  $0.00 ┼────────────────────────────────────────                            │
│         Mon  Tue  Wed  Thu  Fri  Sat  Sun                                   │
│                                                                             │
│  Legend: ■ OpenAI  ■ Anthropic  ■ Google  ■ Ollama (free)                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Pydantic Schemas

```python
# src/models/schemas.py (additions)

class ProviderUsageStats(BaseModel):
    """Usage statistics for a single provider."""
    provider: str
    total_calls: int
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    total_cost_usd: float
    avg_response_time_ms: Optional[float]


class CostSummaryResponse(BaseModel):
    """Overall cost summary."""
    period_days: int
    total_cost_usd: float
    total_tokens: int
    total_calls: int
    avg_cost_per_call: float
    daily_costs: List[Dict[str, Any]]


class ProviderComparisonResponse(BaseModel):
    """Provider comparison by task type."""
    period_days: int
    by_agent_type: Dict[str, Dict[str, Dict[str, Any]]]
```

---

## Frontend Components

### Provider Cost Widget

```typescript
// frontend/src/components/dashboard/ProviderCostWidget.tsx

interface ProviderCostWidgetProps {
  days?: number;
}

export const ProviderCostWidget: React.FC<ProviderCostWidgetProps> = ({ days = 30 }) => {
  const { data } = useProviderUsageStats(days);

  const totalCost = data?.reduce((sum, p) => sum + p.total_cost_usd, 0) || 0;

  return (
    <Card>
      <CardHeader className="flex justify-between">
        <span>Cost by Provider</span>
        <span className="font-bold">${totalCost.toFixed(2)}</span>
      </CardHeader>
      <CardContent>
        {data?.map((provider) => (
          <div key={provider.provider} className="flex items-center gap-2 mb-2">
            <div className="w-24">{provider.provider}</div>
            <div className="flex-1">
              <div
                className="h-4 bg-blue-500 rounded"
                style={{ width: `${(provider.total_cost_usd / totalCost) * 100}%` }}
              />
            </div>
            <div className="w-20 text-right">
              ${provider.total_cost_usd.toFixed(2)}
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
};
```

### Provider Comparison Table

```typescript
// frontend/src/components/dashboard/ProviderComparisonTable.tsx

export const ProviderComparisonTable: React.FC = () => {
  const { data } = useProviderComparison(7);

  return (
    <Card>
      <CardHeader>Provider Performance Comparison</CardHeader>
      <CardContent>
        {Object.entries(data?.by_agent_type || {}).map(([agentType, providers]) => (
          <div key={agentType} className="mb-6">
            <h4 className="font-medium mb-2">{formatAgentType(agentType)}</h4>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500">
                  <th>Provider</th>
                  <th>Avg Latency</th>
                  <th>Avg Tokens</th>
                  <th>Cost/Call</th>
                  <th>Calls</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(providers).map(([provider, stats]) => (
                  <tr key={provider}>
                    <td>{provider}</td>
                    <td>{stats.avg_latency_ms?.toFixed(0)}ms</td>
                    <td>{stats.avg_tokens_per_call?.toFixed(0)}</td>
                    <td>${stats.total_cost_usd.toFixed(4)}</td>
                    <td>{stats.calls}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}
      </CardContent>
    </Card>
  );
};
```

---

## Implementation Phases

### Phase 1: Token Extractor Framework
- [ ] Create `TokenExtractor` base class
- [ ] Implement extractors for each provider (Ollama, OpenAI, Anthropic, Google)
- [ ] Add provider pricing data
- [ ] Unit tests for each extractor

### Phase 2: Base Provider Integration
- [ ] Update `LLMResponse` with usage fields
- [ ] Add `_enrich_response()` to `LLMClient` base
- [ ] Update each provider to call `_enrich_response()`
- [ ] Integration tests

### Phase 3: Database & Tracker Updates
- [ ] Add `provider` column to `llm_usage` table
- [ ] Create migration
- [ ] Update `LLMUsageTracker.track_from_response()`
- [ ] Update existing tracking code

### Phase 4: API Endpoints
- [ ] `/llm/usage/by-provider` endpoint
- [ ] `/llm/usage/cost-summary` endpoint
- [ ] `/llm/usage/provider-comparison` endpoint
- [ ] Add provider filter to existing endpoints

### Phase 5: Dashboard Updates
- [ ] Provider cost breakdown widget
- [ ] Provider comparison table
- [ ] Daily cost trend chart (stacked by provider)
- [ ] Add provider filter to existing charts

### Phase 6: Inline Chat Updates
- [ ] Show provider in usage summary
- [ ] Show cost per message (for paid providers)
- [ ] Provider indicator badge

---

## API Summary

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/llm/usage/by-provider` | GET | Usage breakdown by provider |
| `/llm/usage/cost-summary` | GET | Total cost summary with daily breakdown |
| `/llm/usage/provider-comparison` | GET | Performance comparison across providers |

---

## Pricing Configuration

Allow updating pricing without code changes:

```python
# src/llm/monitoring/pricing.py

from typing import Dict
from src.database.models import LLMModelPricing

# Default pricing (fallback if not in database)
DEFAULT_PRICING = {
    "openai": {
        "gpt-4o": {"input": 2.50, "output": 10.00},
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    },
    "anthropic": {
        "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
        "claude-3-5-haiku": {"input": 0.80, "output": 4.00},
    },
    # ... etc
}


async def get_model_pricing(
    db: AsyncSession,
    provider: str,
    model: str
) -> Dict[str, float]:
    """Get pricing for a model, checking database first."""
    # Check database for custom pricing
    result = await db.execute(
        select(LLMModelPricing)
        .where(LLMModelPricing.provider == provider)
        .where(LLMModelPricing.model == model)
    )
    pricing = result.scalar_one_or_none()

    if pricing:
        return {
            "input": pricing.cost_per_1m_input,
            "output": pricing.cost_per_1m_output,
        }

    # Fall back to defaults
    return DEFAULT_PRICING.get(provider, {}).get(model, {"input": 0.0, "output": 0.0})
```

---

## Related Documentation

- [LLM Usage Monitoring Plan](./LLM_USAGE_MONITORING_PLAN.md) - Base monitoring system
- [LLM Provider Expansion Plan](./LLM_PROVIDER_EXPANSION_PLAN.md) - Provider abstraction layer

---

*Document Version: 1.0*
*Created: 2026-02-01*
*Status: Planning*
*Dependencies: LLM_USAGE_MONITORING_PLAN.md, LLM_PROVIDER_EXPANSION_PLAN.md*
