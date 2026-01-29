# LLM Provider Expansion Plan (Phase 14)

**Created**: January 28, 2026
**Status**: PLANNING
**Priority**: HIGH
**Estimated Effort**: ~3,000 lines of code

---

## Overview

Expand Database Guru's LLM support beyond Ollama to include cloud providers (Azure OpenAI, OpenAI, Anthropic, Google Vertex AI, AWS Bedrock) and additional local options (LM Studio, vLLM). This enables users to leverage their existing cloud infrastructure, use more powerful models, and maintain flexibility in their LLM deployment strategy.

### Why This Feature?

| Current State | Target State |
|--------------|--------------|
| Only Ollama supported | 7+ LLM providers |
| Local-only deployment | Cloud + Local hybrid |
| Single model config | Per-provider configuration |
| No enterprise integration | Azure/AWS enterprise support |

### Key Use Cases

1. **Enterprise Integration**: Companies already using Azure OpenAI can connect Database Guru to their existing infrastructure
2. **Model Flexibility**: Use GPT-4, Claude, or Gemini for complex queries while using local models for simple ones
3. **Cost Optimization**: Route different task types to cost-appropriate providers
4. **Fallback/Redundancy**: Automatic failover between providers for reliability

---

## Visual Architecture

```
                              LLM PROVIDER ARCHITECTURE
                              =========================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                           LLM PROVIDER REGISTRY                          │
    │                                                                          │
    │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
    │  │    Ollama    │  │ Azure OpenAI │  │    OpenAI    │  │  Anthropic   │ │
    │  │   (Local)    │  │   (Cloud)    │  │   (Cloud)    │  │   (Cloud)    │ │
    │  │              │  │              │  │              │  │              │ │
    │  │ ✅ Existing  │  │  ⭐ Priority │  │   Planned    │  │   Planned    │ │
    │  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘ │
    │                                                                          │
    │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
    │  │ Google Vertex│  │ AWS Bedrock  │  │  LM Studio   │  │    vLLM      │ │
    │  │   (Cloud)    │  │   (Cloud)    │  │   (Local)    │  │   (Local)    │ │
    │  │              │  │              │  │              │  │              │ │
    │  │   Planned    │  │   Planned    │  │   Planned    │  │   Planned    │ │
    │  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘ │
    └─────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
    ┌─────────────────────────────────────────────────────────────────────────┐
    │                          UNIFIED LLM INTERFACE                           │
    │                                                                          │
    │  class BaseLLMProvider(ABC):                                             │
    │      async def generate(prompt, **kwargs) -> str                         │
    │      async def chat(messages, **kwargs) -> str                           │
    │      async def embeddings(text, **kwargs) -> List[float]                 │
    │      async def health_check() -> bool                                    │
    │      async def list_models() -> List[str]                                │
    │                                                                          │
    └─────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
    ┌─────────────────────────────────────────────────────────────────────────┐
    │                     ENHANCED MODEL ROUTER (Phase 2.4)                    │
    │                                                                          │
    │  • Route tasks to providers based on:                                    │
    │    - Task type (SQL, Narratives, Planning, Corrections)                  │
    │    - Provider availability                                               │
    │    - Cost optimization rules                                             │
    │    - User preferences                                                    │
    │                                                                          │
    │  • Fallback chains:                                                      │
    │    Azure OpenAI → OpenAI → Ollama (configurable)                         │
    │                                                                          │
    └─────────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Phases

### Phase 14.1: Provider Abstraction Layer (~600 lines)
**Create unified interface for all LLM providers**

```
src/llm/providers/
├── __init__.py
├── base.py              # BaseLLMProvider abstract class
├── registry.py          # Provider registry & factory
├── ollama.py            # Refactored OllamaProvider
└── types.py             # Shared types (LLMResponse, etc.)
```

**Key Components:**

```python
# base.py
class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    provider_name: str
    supports_streaming: bool = True
    supports_embeddings: bool = True
    supports_function_calling: bool = False

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse: ...

    @abstractmethod
    async def chat(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        **kwargs
    ) -> LLMResponse: ...

    @abstractmethod
    async def health_check(self) -> ProviderHealth: ...

    @abstractmethod
    async def list_models(self) -> List[ModelInfo]: ...


# registry.py
class ProviderRegistry:
    """Central registry for LLM providers."""

    def register(self, name: str, provider_class: Type[BaseLLMProvider]): ...
    def get(self, name: str) -> BaseLLMProvider: ...
    def list_available(self) -> List[str]: ...
    def get_configured(self) -> List[BaseLLMProvider]: ...
```

**Deliverables:**
- [ ] Abstract base class with full interface
- [ ] Provider registry with lazy initialization
- [ ] Refactor existing OllamaClient to OllamaProvider
- [ ] Shared types for responses, errors, model info
- [ ] Unit tests for abstraction layer

---

### Phase 14.2: Azure OpenAI Provider (~500 lines)
**Priority cloud provider for enterprise users**

```
src/llm/providers/
└── azure_openai.py      # Azure OpenAI implementation
```

**Configuration:**

```python
# settings.py additions
class Settings(BaseSettings):
    # Azure OpenAI
    AZURE_OPENAI_ENABLED: bool = False
    AZURE_OPENAI_ENDPOINT: Optional[str] = None  # https://<resource>.openai.azure.com
    AZURE_OPENAI_API_KEY: Optional[str] = None
    AZURE_OPENAI_API_VERSION: str = "2024-02-15-preview"
    AZURE_OPENAI_DEPLOYMENT_NAME: Optional[str] = None  # Deployment name for default model
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT: Optional[str] = None  # For embeddings
```

**Provider Implementation:**

```python
class AzureOpenAIProvider(BaseLLMProvider):
    provider_name = "azure_openai"
    supports_function_calling = True

    def __init__(self, settings: Settings):
        self.endpoint = settings.AZURE_OPENAI_ENDPOINT
        self.api_key = settings.AZURE_OPENAI_API_KEY
        self.api_version = settings.AZURE_OPENAI_API_VERSION
        self.deployment = settings.AZURE_OPENAI_DEPLOYMENT_NAME

    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        # Use Azure OpenAI SDK or httpx
        ...

    async def list_models(self) -> List[ModelInfo]:
        # List deployments in Azure resource
        ...
```

**Deliverables:**
- [ ] Azure OpenAI provider with full API support
- [ ] Deployment-based model selection
- [ ] Azure-specific error handling (rate limits, quotas)
- [ ] Integration tests with mock Azure responses
- [ ] Documentation for Azure setup

---

### Phase 14.3: OpenAI Provider (~400 lines)
**Direct OpenAI API support**

```
src/llm/providers/
└── openai.py            # OpenAI implementation
```

**Configuration:**

```python
# settings.py additions
OPENAI_ENABLED: bool = False
OPENAI_API_KEY: Optional[str] = None
OPENAI_ORG_ID: Optional[str] = None
OPENAI_DEFAULT_MODEL: str = "gpt-4-turbo"
```

**Deliverables:**
- [ ] OpenAI provider using official SDK
- [ ] Support for GPT-4, GPT-4 Turbo, GPT-3.5
- [ ] Function calling support
- [ ] Token counting and cost tracking
- [ ] Rate limit handling with exponential backoff

---

### Phase 14.4: Anthropic Provider (~400 lines)
**Claude API support**

```
src/llm/providers/
└── anthropic.py         # Anthropic implementation
```

**Configuration:**

```python
ANTHROPIC_ENABLED: bool = False
ANTHROPIC_API_KEY: Optional[str] = None
ANTHROPIC_DEFAULT_MODEL: str = "claude-3-5-sonnet-20241022"
```

**Deliverables:**
- [ ] Anthropic provider using official SDK
- [ ] Support for Claude 3.5 Sonnet, Opus, Haiku
- [ ] Tool use support (Anthropic's function calling)
- [ ] Long context handling (200K tokens)

---

### Phase 14.5: Additional Cloud Providers (~600 lines)
**Google Vertex AI and AWS Bedrock**

```
src/llm/providers/
├── google_vertex.py     # Google Vertex AI
└── aws_bedrock.py       # AWS Bedrock
```

**Google Vertex AI:**
```python
GOOGLE_VERTEX_ENABLED: bool = False
GOOGLE_PROJECT_ID: Optional[str] = None
GOOGLE_LOCATION: str = "us-central1"
GOOGLE_DEFAULT_MODEL: str = "gemini-1.5-pro"
```

**AWS Bedrock:**
```python
AWS_BEDROCK_ENABLED: bool = False
AWS_REGION: str = "us-east-1"
AWS_BEDROCK_MODEL_ID: str = "anthropic.claude-3-sonnet-20240229-v1:0"
# Uses AWS credential chain (env vars, IAM role, etc.)
```

**Deliverables:**
- [ ] Google Vertex AI provider (Gemini models)
- [ ] AWS Bedrock provider (multi-model)
- [ ] Cloud-specific authentication handling
- [ ] Regional endpoint support

---

### Phase 14.6: Local Provider Alternatives (~300 lines)
**LM Studio and vLLM support**

```
src/llm/providers/
├── lm_studio.py         # LM Studio (OpenAI-compatible API)
└── vllm.py              # vLLM server
```

**LM Studio:**
```python
LM_STUDIO_ENABLED: bool = False
LM_STUDIO_BASE_URL: str = "http://localhost:1234"  # Default LM Studio port
```

**vLLM:**
```python
VLLM_ENABLED: bool = False
VLLM_BASE_URL: str = "http://localhost:8000"
```

Both use OpenAI-compatible API, so can share base implementation.

**Deliverables:**
- [ ] LM Studio provider (OpenAI-compatible)
- [ ] vLLM provider (OpenAI-compatible)
- [ ] Shared OpenAI-compatible base class

---

### Phase 14.7: Enhanced Model Router (~400 lines)
**Upgrade model router for multi-provider support**

**New Routing Capabilities:**

```python
class EnhancedModelRouter:
    """Routes tasks to appropriate providers and models."""

    def __init__(self, settings: Settings, provider_registry: ProviderRegistry):
        self.registry = provider_registry

    def get_provider_for_task(self, task: TaskType) -> BaseLLMProvider:
        """Get the best provider for a task based on configuration."""
        ...

    def get_fallback_chain(self, task: TaskType) -> List[BaseLLMProvider]:
        """Get ordered list of providers to try for a task."""
        ...

    async def execute_with_fallback(
        self,
        task: TaskType,
        prompt: str,
        **kwargs
    ) -> LLMResponse:
        """Execute prompt with automatic fallback on failure."""
        ...
```

**Configuration:**

```python
# New settings for routing
LLM_PROVIDER_PRIORITY: List[str] = ["azure_openai", "openai", "ollama"]
LLM_FALLBACK_ENABLED: bool = True
LLM_COST_OPTIMIZATION: bool = False  # Route cheaper queries to cheaper providers

# Per-task provider override
PROVIDER_SQL_GENERATION: Optional[str] = None  # e.g., "azure_openai"
PROVIDER_NARRATIVES: Optional[str] = None
PROVIDER_QUERY_PLANNING: Optional[str] = None
PROVIDER_ERROR_CORRECTION: Optional[str] = None
```

**Deliverables:**
- [ ] Multi-provider routing logic
- [ ] Fallback chain execution
- [ ] Provider health monitoring
- [ ] Per-task provider configuration
- [ ] Cost-based routing (optional)

---

### Phase 14.8: Frontend UI (~500 lines)
**Provider configuration interface**

```
frontend/src/components/settings/
├── LLMProviderSettings.tsx     # Main provider settings panel
├── ProviderCard.tsx            # Individual provider config card
├── ProviderConnectionTest.tsx  # Test connection button/status
└── ProviderSelector.tsx        # Dropdown for task→provider mapping
```

**UI Components:**

1. **Provider Configuration Panel**
   - Enable/disable providers
   - API key input (masked)
   - Endpoint configuration
   - Test connection button

2. **Task Routing Configuration**
   - Per-task provider selection
   - Fallback chain configuration
   - Priority ordering (drag-and-drop)

3. **Provider Status Dashboard**
   - Health status for each provider
   - Response times
   - Error rates

**Deliverables:**
- [ ] Provider configuration cards
- [ ] Secure API key input (never displayed after save)
- [ ] Connection testing UI
- [ ] Task routing configuration
- [ ] Provider health dashboard

---

### Phase 14.9: Backend API (~300 lines)
**API endpoints for provider management**

```python
# New endpoints in src/api/endpoints/llm_providers.py

@router.get("/providers")
async def list_providers() -> List[ProviderInfo]:
    """List all available LLM providers and their status."""

@router.post("/providers/{provider_name}/test")
async def test_provider(provider_name: str) -> ProviderTestResult:
    """Test connection to a specific provider."""

@router.get("/providers/{provider_name}/models")
async def list_provider_models(provider_name: str) -> List[ModelInfo]:
    """List available models for a provider."""

@router.put("/providers/config")
async def update_provider_config(config: ProviderConfig) -> ProviderConfig:
    """Update provider configuration."""

@router.get("/providers/routing")
async def get_routing_config() -> RoutingConfig:
    """Get current task→provider routing configuration."""

@router.put("/providers/routing")
async def update_routing_config(config: RoutingConfig) -> RoutingConfig:
    """Update task→provider routing."""
```

**Deliverables:**
- [ ] Provider listing endpoint
- [ ] Connection testing endpoint
- [ ] Model listing per provider
- [ ] Configuration CRUD endpoints
- [ ] Routing configuration endpoints

---

## Database Schema Changes

```sql
-- New table for provider configurations
CREATE TABLE llm_provider_configs (
    id INTEGER PRIMARY KEY,
    provider_name VARCHAR(50) NOT NULL UNIQUE,
    enabled BOOLEAN DEFAULT FALSE,
    api_key_encrypted TEXT,  -- Encrypted API key
    endpoint TEXT,
    default_model VARCHAR(100),
    extra_config JSON,  -- Provider-specific settings
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- New table for task→provider routing
CREATE TABLE llm_task_routing (
    id INTEGER PRIMARY KEY,
    task_type VARCHAR(50) NOT NULL,  -- sql_generation, narratives, etc.
    primary_provider VARCHAR(50) NOT NULL,
    fallback_providers JSON,  -- Ordered list of fallback providers
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add columns to system_settings for global LLM config
ALTER TABLE system_settings ADD COLUMN llm_fallback_enabled BOOLEAN DEFAULT TRUE;
ALTER TABLE system_settings ADD COLUMN llm_cost_optimization BOOLEAN DEFAULT FALSE;
```

---

## Security Considerations

### API Key Storage
- **Never store plaintext API keys** in database or logs
- Use Fernet symmetric encryption for API keys at rest
- Decrypt only when making API calls
- Never return API keys in API responses (mask with `***`)

### Key Rotation
- Support API key rotation without downtime
- Log key usage for audit (without exposing keys)

### Environment Variables
- Support loading keys from environment variables (preferred for production)
- `.env` file for local development

```python
# Priority: env var > database > settings file
def get_api_key(provider: str) -> Optional[str]:
    env_key = os.getenv(f"{provider.upper()}_API_KEY")
    if env_key:
        return env_key
    return decrypt_from_database(provider)
```

---

## Testing Strategy

### Unit Tests (~200 tests)
- Provider interface compliance
- Response parsing
- Error handling
- Mock API responses

### Integration Tests (~50 tests)
- Real provider connections (with test keys)
- Fallback chain execution
- Routing logic
- Rate limit handling

### E2E Tests (~20 tests)
- Full query flow with different providers
- Provider switching
- Configuration persistence

---

## Migration Path

### For Existing Users
1. Existing Ollama configuration continues to work unchanged
2. New providers are opt-in (disabled by default)
3. No breaking changes to current API

### For New Users
1. Setup wizard prompts for provider selection
2. Ollama remains recommended for local/free usage
3. Cloud providers for enterprise features

---

## Dependencies

### New Python Packages
```
openai>=1.0.0          # OpenAI + Azure OpenAI SDK
anthropic>=0.18.0      # Anthropic SDK
google-cloud-aiplatform>=1.40.0  # Vertex AI
boto3>=1.34.0          # AWS Bedrock
cryptography>=42.0.0   # API key encryption
```

### Optional Dependencies
- `tiktoken` for OpenAI token counting
- `google-auth` for GCP authentication

---

## Recommended Implementation Order

```
Phase 14.1 ──▶ Phase 14.2 ──▶ Phase 14.7 ──▶ Phase 14.8/14.9
   │              │
   │              └── (Azure OpenAI - Primary Cloud Target)
   │
   └── (Foundation: Must complete first)

Parallel tracks after 14.2:
├── Phase 14.3 (OpenAI) - Can run in parallel
├── Phase 14.4 (Anthropic) - Can run in parallel
├── Phase 14.5 (Vertex/Bedrock) - Lower priority
└── Phase 14.6 (LM Studio/vLLM) - Lower priority
```

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Providers Supported | 7+ |
| Provider Switch Time | < 100ms |
| Fallback Success Rate | > 99% |
| API Key Security | Zero plaintext exposure |
| Test Coverage | > 85% |

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| API key exposure | Encryption at rest, no logging, masked responses |
| Provider API changes | Abstract interface, provider-specific adapters |
| Rate limiting | Exponential backoff, queue management |
| Cost overruns | Usage tracking, configurable limits |
| Latency variance | Health monitoring, smart routing |

---

## Related Documents

- [Model Router](../modules/MODEL_ROUTER.md) - Existing per-task routing
- [Prompt Optimizer](../technical/PROMPT_OPTIMIZATION.md) - Token optimization
- [Settings Guide](../guides/SETTINGS_GUIDE.md) - Configuration patterns

---

**Next Steps:**
1. Review and approve this plan
2. Begin Phase 14.1 (Provider Abstraction)
3. Obtain Azure OpenAI test credentials for development
