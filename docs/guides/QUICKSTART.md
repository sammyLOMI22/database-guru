# 🧙‍♂️ Database Guru - Quick Start Guide

## Prerequisites

- Docker Desktop installed and running
- Python 3.11+
- 8GB RAM minimum (16GB recommended for LLMs)

## Step 1: Start Docker Services

Start PostgreSQL, Redis, and Ollama:

```bash
docker-compose up -d postgres redis ollama
```

Check services are running:

```bash
docker-compose ps
```

## Step 2: Pull the LLM Model

Wait a moment for Ollama to start, then pull the Llama3 model:

```bash
docker exec -it db-qa-ollama ollama pull llama3
```

This may take a few minutes depending on your internet connection.

## Step 3: Install Python Dependencies

Create a virtual environment and install dependencies:

```bash
python -m venv venv
source venv/bin/activate  # On macOS/Linux
pip install -r requirements.txt
```

## Step 4: Configure Environment

Create a `.env` file in the project root:

```bash
cp src/EXAMPLE.ENV .env
```

Update the `.env` file with your settings (defaults should work for local development):

```env
# Application
APP_NAME="Database Guru"
ENVIRONMENT=development
DEBUG=true

# Database (Docker defaults)
DATABASE_URL=postgresql://dbuser:dbpass@localhost:5432/dbqa

# Ollama (Docker defaults)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3

# Redis (Docker defaults)
REDIS_URL=redis://localhost:6379
CACHE_TTL=3600

# Security (generate new keys for production!)
SECRET_KEY=change-this-secret-key
JWT_SECRET=change-this-jwt-secret
```

## Step 5: Initialize Database

Create the database tables:

```bash
python src/database/init_db.py
```

You should see:
```
✅ Database initialized successfully!
```

## Step 6: Start the API

Run the FastAPI application:

```bash
python src/main.py
```

Or using uvicorn directly:

```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
🚀 Starting Database Guru...
📊 Initializing database...
✅ Database ready
💾 Initializing Redis cache...
✅ Cache ready
🧙‍♂️ Database Guru is ready!
```

## Step 7: Test the API

### Option 1: Interactive API Docs

Open your browser and visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Option 2: Run Test Script

In a new terminal (with venv activated):

```bash
python test_api.py
```

### Option 3: cURL Commands

**Health Check:**
```bash
curl http://localhost:8000/health
```

**Process a Query:**
```bash
curl -X POST http://localhost:8000/api/query/ \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Show me all customers from California",
    "database_type": "postgresql"
  }'
```

**Get Query History:**
```bash
curl http://localhost:8000/api/query/history
```

**Explain SQL:**
```bash
curl -X POST http://localhost:8000/api/query/explain \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "SELECT * FROM customers WHERE state = '\''CA'\''"
  }'
```

## API Endpoints

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Root endpoint with API info |
| GET | `/health` | Health check for all services |
| POST | `/api/query/` | Process natural language query |
| POST | `/api/query/explain` | Explain a SQL query |
| GET | `/api/query/history` | Get query history |
| GET | `/api/query/history/{id}` | Get specific query |
| GET | `/api/query/stats` | Get usage statistics |

### Example Request/Response

**Request:**
```json
{
  "question": "What are the top 5 products by price?",
  "database_type": "postgresql",
  "use_cache": true
}
```

**Response:**
```json
{
  "query_id": 123,
  "question": "What are the top 5 products by price?",
  "sql": "SELECT * FROM products ORDER BY price DESC LIMIT 5",
  "is_valid": true,
  "is_read_only": true,
  "warnings": [],
  "cached": false,
  "timestamp": "2024-01-01T12:00:00"
}
```

## Running Tests

### Test Individual Components

```bash
# Test database connection
python test_db_connection.py

# Test Redis cache
python test_redis_cache.py

# Test LLM layer
python test_llm.py

# Test full pipeline
python examples/full_pipeline.py

# Test API
python test_api.py
```

## Troubleshooting

### Ollama Connection Issues

Check if Ollama is running:
```bash
curl http://localhost:11434/api/tags
```

Check Ollama logs:
```bash
docker logs db-qa-ollama
```

### Database Connection Issues

Check if PostgreSQL is running:
```bash
docker logs db-qa-postgres
```

Test connection:
```bash
docker exec -it db-qa-postgres psql -U dbuser -d dbqa
```

### Redis Connection Issues

Check if Redis is running:
```bash
docker logs db-qa-redis
```

Test connection:
```bash
docker exec -it db-qa-redis redis-cli ping
```

### Port Already in Use

If port 8000 is already in use:
```bash
# Find process using port 8000
lsof -i :8000

# Change port in src/main.py or use:
uvicorn src.main:app --port 8001
```

## Stopping the Application

### Stop API
Press `Ctrl+C` in the terminal running the API

### Stop Docker Services
```bash
docker-compose down
```

### Stop and Remove All Data
```bash
docker-compose down -v
```

## Next Steps

- Explore the interactive API docs at http://localhost:8000/docs
- Try different natural language queries
- Check out the examples in `examples/` directory
- Review the architecture in the main README.md

## Need Help?

- Check the main README.md for architecture details
- Review the code documentation
- Open an issue on GitHub
