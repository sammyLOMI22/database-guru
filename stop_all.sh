#!/bin/bash

# Stop Database Guru Complete Stack
# This script stops Redis, Ollama, backend, and frontend

echo "🛑 Stopping Database Guru Complete Stack..."
echo ""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP 1: Stop Application (Backend + Frontend)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

echo "📦 Stopping application servers..."

# Call the regular stop script to stop backend/frontend
if [ -f "./stop.sh" ]; then
    ./stop.sh
else
    # Fallback: manual cleanup
    if [ -f ".backend.pid" ]; then
        BACKEND_PID=$(cat .backend.pid)
        if kill -0 $BACKEND_PID 2>/dev/null; then
            kill $BACKEND_PID
            echo "✅ Backend server stopped (PID: $BACKEND_PID)"
        fi
        rm -f .backend.pid
    fi

    if [ -f ".frontend.pid" ]; then
        FRONTEND_PID=$(cat .frontend.pid)
        if kill -0 $FRONTEND_PID 2>/dev/null; then
            kill $FRONTEND_PID
            echo "✅ Frontend server stopped (PID: $FRONTEND_PID)"
        fi
        rm -f .frontend.pid
    fi

    rm -f backend.log frontend.log
fi

echo ""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP 2: Stop Ollama
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

echo "🤖 Stopping Ollama..."

# Check if we started Ollama (vs it was already running)
OLLAMA_MANAGED_BY_SCRIPT=false
if [ -f ".services.pid" ]; then
    source .services.pid
fi

if [ "$OLLAMA_MANAGED_BY_SCRIPT" = "true" ]; then
    # We started it, so we stop it
    if [ -f ".ollama.pid" ]; then
        OLLAMA_PID=$(cat .ollama.pid)
        if kill -0 $OLLAMA_PID 2>/dev/null; then
            kill $OLLAMA_PID
            echo "✅ Ollama stopped (PID: $OLLAMA_PID)"
        else
            echo "⚠️  Ollama process not found (may have already stopped)"
        fi
        rm -f .ollama.pid
    else
        # Try to stop by process name
        if pkill -f "ollama serve"; then
            echo "✅ Ollama stopped"
        else
            echo "⚠️  Ollama not running"
        fi
    fi
    rm -f ollama.log
else
    echo "⏭️  Ollama was already running - leaving it active"
fi

echo ""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP 3: Stop Redis
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

echo "💾 Stopping Redis..."

# Check if we started Redis (vs it was already running)
REDIS_MANAGED_BY_SCRIPT=false
if [ -f ".services.pid" ]; then
    source .services.pid
fi

if [ "$REDIS_MANAGED_BY_SCRIPT" = "true" ]; then
    # We started it, so we stop it
    if redis-cli ping &> /dev/null; then
        redis-cli shutdown
        echo "✅ Redis stopped"
    else
        echo "⚠️  Redis not running"
    fi
else
    echo "⏭️  Redis was already running - leaving it active"
fi

echo ""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Cleanup
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if [ -f ".services.pid" ]; then
    rm -f .services.pid
    echo "🧹 Cleaned up service tracking file"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "👋 Database Guru Complete Stack stopped!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
