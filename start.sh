#!/bin/bash

# Database Guru Startup Script
# This script starts both the backend and frontend servers

set -e  # Exit on error

echo "🧙‍♂️  Starting Database Guru..."
echo ""

# Check if Python virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install Python dependencies if needed
if [ ! -f "venv/.installed" ]; then
    echo "📦 Installing Python dependencies..."
    pip install -q --upgrade pip
    pip install -q fastapi uvicorn[standard] pydantic pydantic-settings python-multipart \
        sqlalchemy aiosqlite ollama httpx python-dotenv sqlparse greenlet
    touch venv/.installed
    echo "✅ Python dependencies installed"
fi

# Check if sample database exists
if [ ! -f "sample_ecommerce.db" ]; then
    echo "📊 Creating sample database..."
    python3 scripts/create_sample_db.py
    echo "✅ Sample database created"
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚙️  Creating .env configuration..."
    cat > .env << 'EOF'
# Database Guru Configuration
APP_NAME=Database Guru
VERSION=2.0.0
DEBUG=True

# Database - Using SQLite for local development
DATABASE_URL=sqlite+aiosqlite:///./database_guru.db

# Redis - Optional (disabled for local dev)
REDIS_URL=

# Ollama - Using local installation
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5-coder:32b
OLLAMA_ALLOW_MODEL_SELECTION=True

# Security (Development only - change for production!)
SECRET_KEY=dev-secret-key-change-in-production-12345678901234567890

# Query Limits
MAX_QUERY_ROWS=1000
QUERY_TIMEOUT_SECONDS=30
EOF
    echo "✅ Configuration file created"
fi

# Check if Ollama is running
echo "🔍 Checking Ollama status..."
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "⚠️  Ollama is not running!"
    echo "   Start it with: ollama serve"
    echo "   Or in another terminal: brew services start ollama"
    echo ""
    read -p "Do you want to continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "✅ Ollama is running"
fi

# Install frontend dependencies if needed
if [ ! -d "frontend/node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    cd frontend
    npm install --silent
    cd ..
    echo "✅ Frontend dependencies installed"
fi

echo ""
echo "🚀 Starting servers..."
echo ""

# Start backend in background
echo "🐍 Starting backend server (http://localhost:8000)..."
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
BACKEND_PID=$!
echo "   Backend PID: $BACKEND_PID"

# Wait for backend to start
echo "⏳ Waiting for backend to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ Backend is ready!"
        break
    fi
    sleep 1
    if [ $i -eq 30 ]; then
        echo "❌ Backend failed to start. Check backend.log for errors."
        kill $BACKEND_PID 2>/dev/null
        exit 1
    fi
done

# Start frontend
echo "⚛️  Starting frontend server (http://localhost:3000)..."
cd frontend
npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!
echo "   Frontend PID: $FRONTEND_PID"
cd ..

# Wait for frontend to start
echo "⏳ Waiting for frontend to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        echo "✅ Frontend is ready!"
        break
    fi
    sleep 1
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✨ Database Guru is running!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🌐 Frontend:  http://localhost:3000"
echo "🔧 Backend:   http://localhost:8000"
echo "📚 API Docs:  http://localhost:8000/docs"
echo ""
echo "📊 Sample Database: sample_ecommerce.db"
echo ""
echo "📝 Next Steps:"
echo "   1. Open http://localhost:3000 in your browser"
echo "   2. Click 'Connections' tab in the sidebar"
echo "   3. Click '+ Add Connection'"
echo "   4. Select 'SQLite' as database type"
echo "   5. Enter: $(pwd)/sample_ecommerce.db"
echo "   6. Click 'Test Connection' then 'Save'"
echo "   7. Click the connection to activate it"
echo "   8. Start asking questions!"
echo ""
echo "💡 Example Questions:"
echo "   • What are the top 5 best-selling products?"
echo "   • Show me orders from customers in California"
echo "   • What's the average order value?"
echo "   • Which products have low stock?"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Log files:"
echo "   Backend:  backend.log"
echo "   Frontend: frontend.log"
echo ""
echo "🛑 To stop: Press Ctrl+C or run: ./stop.sh"
echo ""

# Save PIDs to file for stop script
echo "$BACKEND_PID" > .backend.pid
echo "$FRONTEND_PID" > .frontend.pid

# Wait for Ctrl+C
trap "echo ''; echo '🛑 Shutting down...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; rm -f .backend.pid .frontend.pid backend.log frontend.log; echo '👋 Goodbye!'; exit 0" INT

# Keep script running
wait
