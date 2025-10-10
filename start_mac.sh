#!/bin/bash
# Start script for Mac

echo "🍎 Starting DB Q&A System on Mac..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Start services in background
echo "Starting services..."

# Start Redis if installed
if command -v redis-server &> /dev/null; then
    echo "Starting Redis..."
    redis-server --daemonize yes
else
    echo "⚠️  Redis not found. Some features may not work."
fi

# Start PostgreSQL if installed
if command -v pg_ctl &> /dev/null; then
    echo "Starting PostgreSQL..."
    brew services start postgresql@15 2>/dev/null || true
else
    echo "⚠️  PostgreSQL not found. Using SQLite instead."
fi

# Start Ollama
if command -v ollama &> /dev/null; then
    echo "Starting Ollama..."
    ollama serve > logs/ollama.log 2>&1 &
    OLLAMA_PID=$!
    sleep 2
    
    # Pull model if not exists
    ollama list | grep -q "llama3" || ollama pull llama3
else
    echo "⚠️  Ollama not found. LLM features will not work."
fi

# Create .env from example if it doesn't exist
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "📝 Created .env file. Please update with your settings."
fi

# Start the application
echo "🚀 Starting application..."
echo "📱 Opening http://localhost:8000/docs in 3 seconds..."
sleep 3 && open http://localhost:8000/docs &

# Run the application
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Cleanup on exit
trap "kill $OLLAMA_PID 2>/dev/null; redis-cli shutdown 2>/dev/null" EXIT