#!/bin/bash

# Database Guru Complete Stack Startup Script
# This script starts Redis, Ollama, and the application (backend + frontend)

set -e  # Exit on error

# Cleanup on exit - stop services we started
cleanup_on_exit() {
    echo ""
    echo "🧹 Cleaning up services started by this script..."

    # Check which services we need to stop
    if [ -f ".services.pid" ]; then
        source .services.pid

        # Stop Ollama if we started it
        if [ "$OLLAMA_MANAGED_BY_SCRIPT" = "true" ]; then
            echo "🤖 Stopping Ollama..."
            if [ -f ".ollama.pid" ]; then
                OLLAMA_PID=$(cat .ollama.pid)
                if kill -0 $OLLAMA_PID 2>/dev/null; then
                    kill $OLLAMA_PID
                    echo "✅ Ollama stopped"
                fi
                rm -f .ollama.pid ollama.log
            fi
        fi

        # Stop Redis if we started it
        if [ "$REDIS_MANAGED_BY_SCRIPT" = "true" ]; then
            echo "💾 Stopping Redis..."
            if redis-cli ping &> /dev/null; then
                redis-cli shutdown &> /dev/null
                echo "✅ Redis stopped"
            fi
        fi

        rm -f .services.pid
    fi

    echo "✨ Cleanup complete"
}
trap cleanup_on_exit EXIT INT

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
    echo "✅ Redis is already running (will not manage)"
    REDIS_ALREADY_RUNNING=true
else
    echo "🔧 Starting Redis..."
    # Check if Redis is configured as a service
    if brew services list | grep -q "redis.*started"; then
        echo "✅ Redis service is already configured (will not manage)"
        REDIS_ALREADY_RUNNING=true
    else
        # Start Redis in background
        redis-server --daemonize yes

        # Wait for Redis to be ready
        echo "⏳ Waiting for Redis to be ready..."
        for i in {1..10}; do
            if redis-cli ping &> /dev/null; then
                echo "✅ Redis started successfully (will stop on exit)"
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

# Save Redis status for stop script (invert logic: if already running, we don't manage it)
if [ "$REDIS_ALREADY_RUNNING" = "true" ]; then
    echo "REDIS_MANAGED_BY_SCRIPT=false" > .services.pid
else
    echo "REDIS_MANAGED_BY_SCRIPT=true" > .services.pid
fi

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
    echo "✅ Ollama is already running (will not manage)"
    OLLAMA_ALREADY_RUNNING=true
else
    echo "🔧 Starting Ollama..."
    # Check if Ollama is configured as a service
    if brew services list | grep -q "ollama.*started"; then
        echo "✅ Ollama service is already configured (will not manage)"
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
                echo "✅ Ollama started successfully (will stop on exit)"
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

# Update services file with Ollama status (invert logic: if already running, we don't manage it)
if [ "$OLLAMA_ALREADY_RUNNING" = "true" ]; then
    echo "OLLAMA_MANAGED_BY_SCRIPT=false" >> .services.pid
else
    echo "OLLAMA_MANAGED_BY_SCRIPT=true" >> .services.pid
fi

echo ""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP 3: Start Application (Backend + Frontend)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Starting Application..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Call the regular start script (this will block until stopped)
# When start.sh exits (either normally or via Ctrl+C), our trap will clean up Redis/Ollama
./start.sh

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
