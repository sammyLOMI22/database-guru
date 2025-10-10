# 🤖 Using Local Ollama with Database Guru

Database Guru now supports using **your local Ollama installation** with all your existing models!

---

## Quick Setup

### Option 1: Use Local Ollama (Recommended)

If you already have Ollama installed on your Mac:

```bash
# 1. Make sure Ollama is running
ollama serve

# 2. Database Guru will automatically connect to localhost:11434
python src/main.py
```

That's it! Database Guru will use your local Ollama and all installed models.

### Option 2: Use Docker Ollama

```bash
# Use Docker Compose
docker-compose up -d ollama
```

---

## Managing Models

### List Available Models

**Via API:**
```bash
curl http://localhost:8000/api/models/
```

**Response:**
```json
{
  "models": ["llama3", "mistral", "codellama", "phi3"],
  "default_model": "llama3",
  "count": 4
}
```

### Get Model Details

```bash
curl http://localhost:8000/api/models/details
```

**Response:**
```json
{
  "models": [
    {
      "name": "llama3",
      "size": "4.7 GB",
      "modified": "2024-01-05T10:30:00",
      "available": true
    },
    ...
  ],
  "ollama_url": "http://localhost:11434"
}
```

### Install New Models

**Via Ollama CLI:**
```bash
# Install recommended models
ollama pull llama3
ollama pull mistral
ollama pull codellama
ollama pull phi3
```

**Via Database Guru API:**
```bash
curl -X POST http://localhost:8000/api/models/pull/mistral
```

### See Recommended Models

```bash
curl http://localhost:8000/api/models/recommended
```

---

## Using Different Models

### Method 1: Specify Model Per Query

```bash
curl -X POST http://localhost:8000/api/query/ \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Show me all customers from California",
    "model": "mistral"
  }'
```

### Method 2: Change Default Model

Edit `.env`:
```env
OLLAMA_MODEL=mistral  # or codellama, phi3, etc.
```

### Method 3: Test Different Models

```bash
# Test a model
curl http://localhost:8000/api/models/test/codellama
```

---

## Recommended Models for SQL

### Best Overall: Llama 3
```bash
ollama pull llama3
```
- **Size:** ~4.7GB
- **Speed:** Fast
- **Quality:** Excellent SQL generation
- **Best for:** General use

### Best for Code: CodeLlama
```bash
ollama pull codellama
```
- **Size:** ~3.8GB
- **Speed:** Very fast
- **Quality:** Great for SQL
- **Best for:** Technical queries

### Fastest: Mistral
```bash
ollama pull mistral
```
- **Size:** ~4.1GB
- **Speed:** Fastest
- **Quality:** Good
- **Best for:** Quick responses

### Lightweight: Phi-3
```bash
ollama pull phi3
```
- **Size:** ~2.3GB
- **Speed:** Very fast
- **Quality:** Good for simple queries
- **Best for:** Resource-constrained systems

### Most Accurate: Llama 3 70B (Requires GPU)
```bash
ollama pull llama3:70b
```
- **Size:** ~40GB
- **Speed:** Slower (needs good GPU)
- **Quality:** Best accuracy
- **Best for:** Complex queries, production

---

## Configuration

### Environment Variables

```env
# Ollama Connection
OLLAMA_BASE_URL=http://localhost:11434  # Local Ollama
OLLAMA_MODEL=llama3                      # Default model

# Model Selection
OLLAMA_ALLOW_MODEL_SELECTION=true       # Allow per-query model choice
```

### Using Docker Ollama vs Local

**Local Ollama (Default):**
```env
OLLAMA_BASE_URL=http://localhost:11434
```

**Docker Ollama:**
```env
OLLAMA_BASE_URL=http://localhost:11434  # Same, docker-compose maps the port
```

---

## Example Workflows

### Compare Models for Same Query

```bash
# Try with Llama 3
curl -X POST http://localhost:8000/api/query/ \
  -d '{"question": "Top 5 expensive products", "model": "llama3"}'

# Try with Mistral
curl -X POST http://localhost:8000/api/query/ \
  -d '{"question": "Top 5 expensive products", "model": "mistral"}'

# Try with CodeLlama
curl -X POST http://localhost:8000/api/query/ \
  -d '{"question": "Top 5 expensive products", "model": "codellama"}'
```

### Automatic Model Fallback

Database Guru will:
1. Try your specified model
2. Fall back to default model if specified model not found
3. Attempt to pull default model if not available

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/models/` | List all available models |
| GET | `/api/models/details` | Get detailed model info |
| GET | `/api/models/recommended` | Get recommended models |
| POST | `/api/models/pull/{name}` | Pull/download a model |
| GET | `/api/models/test/{name}` | Test a model |

---

## Tips & Best Practices

### 1. **Start with Llama 3**
```bash
ollama pull llama3
```
Best balance of speed, quality, and resource usage.

### 2. **Use CodeLlama for Complex Joins**
CodeLlama excels at generating complex SQL with multiple joins.

### 3. **Use Mistral for Quick Queries**
For simple SELECT queries, Mistral is fastest.

### 4. **Test Before Production**
```bash
curl http://localhost:8000/api/models/test/your-model
```

### 5. **Monitor Model Performance**
Check query history to see which models work best:
```bash
curl http://localhost:8000/api/query/history
```

---

## Troubleshooting

### Ollama Not Found

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not, start it
ollama serve
```

### Model Not Available

```bash
# List available models
ollama list

# Pull missing model
ollama pull llama3
```

### Using Too Much RAM

Try lighter models:
```bash
ollama pull phi3       # 2.3GB
ollama pull mistral    # 4.1GB
```

### Slow Generation

1. Use a smaller model (phi3, mistral)
2. Use GPU acceleration if available
3. Reduce context with simpler schema

---

## Advanced: Custom Models

You can use ANY Ollama model:

```bash
# Pull any model from Ollama library
ollama pull deepseek-coder

# Use it in Database Guru
curl -X POST http://localhost:8000/api/query/ \
  -d '{"question": "...", "model": "deepseek-coder"}'
```

Browse models: https://ollama.com/library

---

## Performance Comparison

| Model | Size | Speed | SQL Quality | RAM Usage |
|-------|------|-------|-------------|-----------|
| phi3 | 2.3GB | ⚡⚡⚡⚡⚡ | ⭐⭐⭐ | 4GB |
| mistral | 4.1GB | ⚡⚡⚡⚡ | ⭐⭐⭐⭐ | 6GB |
| codellama | 3.8GB | ⚡⚡⚡⚡ | ⭐⭐⭐⭐⭐ | 6GB |
| llama3 | 4.7GB | ⚡⚡⚡⚡ | ⭐⭐⭐⭐⭐ | 8GB |
| llama3:70b | 40GB | ⚡⚡ | ⭐⭐⭐⭐⭐ | 48GB+ |

---

## Summary

✅ **No Docker Required** - Use your local Ollama
✅ **All Models Supported** - Use any model you have
✅ **Per-Query Selection** - Choose model for each query
✅ **Automatic Detection** - Works out of the box
✅ **Model Management** - Install/test via API

**Database Guru now uses YOUR models, YOUR way!** 🚀
