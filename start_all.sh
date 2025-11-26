#!/bin/bash

# Database Guru Complete Stack Startup Script
# This script starts Redis, Ollama, and the application (backend + frontend)

set -e  # Exit on error

echo "🚀 Starting Database Guru Complete Stack..."
echo ""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP 1: Check and Start Redis
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

echo "🔍 Checking Redis status..."

if ! command -v redis-server &> /dev/null; then
    echo "❌ Redis is not installed!"
    echo "   Install it with: brew install redis"
    echo "   Or run: ./scripts/setup_redis.sh"
    exit 1
fi

# Check if Redis is already running
if redis-cli ping &> /dev/null; then
    echo "✅ Redis is already running"
    REDIS_ALREADY_RUNNING=true
else
    echo "🔧 Starting Redis..."
    # Check if Redis is configured as a service
    if brew services list | grep -q "redis.*started"; then
        echo "✅ Redis service is already configured and starting..."
        REDIS_ALREADY_RUNNING=true
    else
        # Start Redis in background
        redis-server --daemonize yes

        # Wait for Redis to be ready
        echo "⏳ Waiting for Redis to be ready..."
        for i in {1..10}; do
            if redis-cli ping &> /dev/null; then
                echo "✅ Redis is ready!"
                REDIS_ALREADY_RUNNING=false
                break
            fi
            sleep 1
            if [ $i -eq 10 ]; then
                echo "❌ Redis failed to start"
                exit 1
            fi
        done
    fi
fi

# Save Redis status for stop script
echo "REDIS_MANAGED_BY_SCRIPT=$REDIS_ALREADY_RUNNING" > .services.pid

echo ""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP 2: Check and Start Ollama
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

echo "🔍 Checking Ollama status..."

if ! command -v ollama &> /dev/null; then
    echo "❌ Ollama is not installed!"
    echo "   Install it with: brew install ollama"
    echo "   Or run: ./scripts/setup_ollama.sh"
    exit 1
fi

# Check if Ollama is already running
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "✅ Ollama is already running"
    OLLAMA_ALREADY_RUNNING=true
else
    echo "🔧 Starting Ollama..."
    # Check if Ollama is configured as a service
    if brew services list | grep -q "ollama.*started"; then
        echo "✅ Ollama service is already configured and starting..."
        OLLAMA_ALREADY_RUNNING=true
    else
        # Start Ollama in background
        nohup ollama serve > ollama.log 2>&1 &
        OLLAMA_PID=$!
        echo "$OLLAMA_PID" > .ollama.pid

        # Wait for Ollama to be ready
        echo "⏳ Waiting for Ollama to be ready..."
        for i in {1..30}; do
            if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
                echo "✅ Ollama is ready!"
                OLLAMA_ALREADY_RUNNING=false
                break
            fi
            sleep 1
            if [ $i -eq 30 ]; then
                echo "❌ Ollama failed to start. Check ollama.log for errors."
                kill $OLLAMA_PID 2>/dev/null
                rm -f .ollama.pid
                exit 1
            fi
        done
    fi
fi

# Update services file with Ollama status
echo "OLLAMA_MANAGED_BY_SCRIPT=$OLLAMA_ALREADY_RUNNING" >> .services.pid

echo ""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP 3: Start Application (Backend + Frontend)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Starting Application..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Call the regular start script
./start.sh

# Note: start.sh will handle Ctrl+C and cleanup
# The trap in start.sh will call stop.sh which stops backend/frontend
# We need our own cleanup for Redis/Ollama

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✨ Complete Stack is Running!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📦 Services Running:"
echo "   • Redis:    localhost:6379"
echo "   • Ollama:   localhost:11434"
echo "   • Backend:  http://localhost:8000"
echo "   • Frontend: http://localhost:3000"
echo ""
echo "🛑 To stop all services: Press Ctrl+C or run: ./stop_all.sh"
echo ""
