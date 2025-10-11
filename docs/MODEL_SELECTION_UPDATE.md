# 🤖 Model Selection Feature - Update

## What's New

Database Guru now supports **using your local Ollama installation** and **choosing any model** for SQL generation!

---

## Key Features

### ✅ Local Ollama Support
- Use your existing Ollama installation
- No Docker required (optional)
- Automatically connects to `localhost:11434`
- Works with all your installed models

### ✅ Model Selection Per Query
- Choose different models for different queries
- Compare model performance
- Optimal model for each task

### ✅ Model Management API
- List available models
- Get model details (size, etc.)
- Install new models via API
- Test models before using

### ✅ Automatic Fallback
- If specified model not found, uses default
- Attempts to pull missing models
- Graceful error handling

---

## Quick Examples

### 1. Use Your Local Ollama

```bash
# Start local Ollama (if not running)
ollama serve

# Database Guru automatically connects!
python src/main.py
```

### 2. List Your Models

```bash
curl http://localhost:8000/api/models/
```

Response:
```json
{
  "models": ["llama3", "mistral", "codellama", "phi3"],
  "default_model": "llama3",
  "count": 4
}
```

### 3. Use Different Models

**Use Mistral:**
```bash
curl -X POST http://localhost:8000/api/query/ \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Show me all customers",
    "model": "mistral"
  }'
```

**Use CodeLlama:**
```bash
curl -X POST http://localhost:8000/api/query/ \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Complex join query",
    "model": "codellama"
  }'
```

**Use Default (Llama 3):**
```bash
curl -X POST http://localhost:8000/api/query/ \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Show me all orders"
  }'
```

---

## New API Endpoints

### Model Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/models/` | List all available models |
| GET | `/api/models/details` | Detailed model information |
| GET | `/api/models/recommended` | Get recommended models for SQL |
| POST | `/api/models/pull/{name}` | Download a new model |
| GET | `/api/models/test/{name}` | Test a model |

### Updated Query Endpoint

**New Parameter:**
```json
{
  "question": "your question",
  "model": "llama3"  // ← NEW: Optional model selection
}
```

---

## Configuration

### Environment Variables

```env
# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434  # Local Ollama
OLLAMA_MODEL=llama3                     # Default model
OLLAMA_ALLOW_MODEL_SELECTION=true      # Enable per-query selection
```

### Recommended Models

| Model | Size | Best For | Command |
|-------|------|----------|---------|
| llama3 | 4.7GB | General SQL | `ollama pull llama3` |
| codellama | 3.8GB | Complex queries | `ollama pull codellama` |
| mistral | 4.1GB | Speed | `ollama pull mistral` |
| phi3 | 2.3GB | Lightweight | `ollama pull phi3` |

---

## Implementation Details

### Files Changed

**New Files:**
- `src/api/endpoints/models.py` - Model management endpoints
- `LOCAL_OLLAMA_GUIDE.md` - Comprehensive guide
- `test_models.py` - Model testing script

**Updated Files:**
- `src/config/settings.py` - Added model selection settings
- `src/models/schemas.py` - Added `model` field to QueryRequest
- `src/llm/sql_generator.py` - Added `model` parameter to generate_sql()
- `src/api/endpoints/query.py` - Pass model to SQL generator
- `src/main.py` - Added models router
- `src/EXAMPLE.ENV` - Updated configuration examples

### Database Schema

The `query_history` table now stores which model was used:
```sql
model_used VARCHAR(100)  -- e.g., "llama3", "mistral"
```

---

## Usage Patterns

### Pattern 1: Default Model for Everything

```env
OLLAMA_MODEL=llama3
```

All queries use llama3 unless specified.

### Pattern 2: Model Per Task

```python
# Simple queries - use fast model
{"question": "Count users", "model": "mistral"}

# Complex queries - use powerful model
{"question": "Complex multi-join", "model": "codellama"}

# Default for everything else
{"question": "Regular query"}  # Uses OLLAMA_MODEL
```

### Pattern 3: A/B Testing

Compare different models:
```bash
for model in llama3 mistral codellama; do
  curl -X POST http://localhost:8000/api/query/ \
    -d "{\"question\": \"test query\", \"model\": \"$model\"}"
done
```

---

## Benefits

### 🚀 Performance
- Use faster models for simple queries
- Use accurate models for complex queries
- Optimize based on your needs

### 💰 Cost Savings
- No cloud API costs
- Use local models
- Full control over resources

### 🔒 Privacy
- All processing local
- No data sent to cloud
- Complete data privacy

### 🎯 Flexibility
- Try any Ollama model
- Switch models anytime
- A/B test different models

---

## Testing

### Test Available Models

```bash
python test_models.py
```

### Compare Models

```bash
# Test all installed models with same query
curl http://localhost:8000/api/models/ | \
  jq -r '.models[]' | \
  while read model; do
    echo "Testing $model..."
    curl -X POST http://localhost:8000/api/query/ \
      -d "{\"question\": \"Show top 5 customers\", \"model\": \"$model\"}"
  done
```

---

## Migration Guide

### If You Were Using Docker Ollama

**Before:**
```yaml
# docker-compose.yml had ollama service
OLLAMA_BASE_URL=http://ollama:11434
```

**After:**
```bash
# Option 1: Use local Ollama (recommended)
ollama serve
OLLAMA_BASE_URL=http://localhost:11434

# Option 2: Keep using Docker
docker-compose up ollama
OLLAMA_BASE_URL=http://localhost:11434  # Same!
```

### If You Were Using Fixed Model

**Before:**
```python
# Always used llama3
await generate_sql(question, schema)
```

**After:**
```python
# Can choose per query
await generate_sql(question, schema, model="mistral")

# Or use default
await generate_sql(question, schema)
```

---

## Troubleshooting

### Models Not Listed

```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Install models
ollama pull llama3
```

### Model Not Found Error

```bash
# Pull the model
ollama pull mistral

# Or use installed model
curl http://localhost:8000/api/models/
```

### Ollama Connection Failed

```bash
# Start Ollama
ollama serve

# Verify running
curl http://localhost:11434/api/tags
```

---

## Next Steps

1. **Install recommended models:**
   ```bash
   ollama pull llama3
   ollama pull mistral
   ollama pull codellama
   ```

2. **Test model management:**
   ```bash
   python test_models.py
   ```

3. **Try different models:**
   - Use interactive docs: http://localhost:8000/docs
   - Compare model performance
   - Find optimal model for your use case

4. **Read full guide:**
   - [LOCAL_OLLAMA_GUIDE.md](LOCAL_OLLAMA_GUIDE.md)

---

## Summary

✅ **Use Local Ollama** - No Docker required
✅ **All Models Supported** - Any Ollama model works
✅ **Model Selection** - Choose model per query
✅ **Model Management** - Install/test via API
✅ **Backward Compatible** - Existing code still works

**Your models, your choice!** 🤖
