#!/bin/bash

# Stop Database Guru servers

echo "🛑 Stopping Database Guru..."

# Kill backend if PID file exists
if [ -f ".backend.pid" ]; then
    BACKEND_PID=$(cat .backend.pid)
    if kill -0 $BACKEND_PID 2>/dev/null; then
        kill $BACKEND_PID
        echo "✅ Backend server stopped (PID: $BACKEND_PID)"
    fi
    rm -f .backend.pid
fi

# Kill frontend if PID file exists
if [ -f ".frontend.pid" ]; then
    FRONTEND_PID=$(cat .frontend.pid)
    if kill -0 $FRONTEND_PID 2>/dev/null; then
        kill $FRONTEND_PID
        echo "✅ Frontend server stopped (PID: $FRONTEND_PID)"
    fi
    rm -f .frontend.pid
fi

# Clean up log files
rm -f backend.log frontend.log

echo "👋 Database Guru stopped!"
