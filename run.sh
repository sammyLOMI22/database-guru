#!/bin/bash

# Database Guru - Easy Start Script

echo "🧙‍♂️ Database Guru - Starting..."
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop."
    exit 1
fi

# Start Docker services
echo "📦 Starting Docker services (PostgreSQL, Redis, Ollama)..."
docker-compose up -d postgres redis ollama

echo "⏳ Waiting for services to be ready..."
sleep 5

# Check if Ollama model is downloaded
echo "🤖 Checking Ollama model..."
if ! docker exec db-qa-ollama ollama list | grep -q "llama3"; then
    echo "📥 Pulling llama3 model (this may take a few minutes)..."
    docker exec -it db-qa-ollama ollama pull llama3
else
    echo "✅ llama3 model already available"
fi

# Activate virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📦 Installing Python dependencies..."
pip install -q -r requirements.txt

# Initialize database
echo "📊 Initializing database..."
python src/database/init_db.py

echo ""
echo "="
echo "🎉 Database Guru is ready!"
echo "="
echo ""
echo "Starting API server on http://localhost:8000"
echo ""
echo "Available endpoints:"
echo "  • Interactive docs: http://localhost:8000/docs"
echo "  • Health check: http://localhost:8000/health"
echo "  • API: http://localhost:8000/api/query/"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the application
python src/main.py
