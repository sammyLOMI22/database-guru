#!/bin/bash
# Setup and start Redis for Database Guru

set -e

echo "🔧 Database Guru - Redis Setup"
echo "================================"
echo ""

# Check if Redis is installed
if command -v redis-server &> /dev/null; then
    echo "✅ Redis is already installed"
    REDIS_VERSION=$(redis-server --version | head -n1)
    echo "   Version: $REDIS_VERSION"
else
    echo "❌ Redis is not installed"
    echo ""
    echo "Would you like to install Redis? (y/n)"
    read -r response

    if [[ "$response" =~ ^[Yy]$ ]]; then
        echo ""
        echo "📦 Installing Redis via Homebrew..."

        # Check if Homebrew is installed
        if ! command -v brew &> /dev/null; then
            echo "❌ Homebrew is not installed"
            echo "   Please install Homebrew first: https://brew.sh"
            exit 1
        fi

        brew install redis
        echo "✅ Redis installed successfully"
    else
        echo ""
        echo "⚠️  Redis not installed. Database Guru will use in-memory cache fallback."
        echo "   For persistent caching, install Redis later:"
        echo "   brew install redis"
        exit 0
    fi
fi

echo ""
echo "🔍 Checking Redis status..."

# Check if Redis is running
if redis-cli ping &> /dev/null; then
    echo "✅ Redis is already running"
    echo ""

    # Show Redis info
    echo "📊 Redis Information:"
    redis-cli info server | grep -E "redis_version|uptime_in_days|tcp_port" || true
    echo ""
    echo "✨ Redis is ready for Database Guru!"
else
    echo "⚠️  Redis is not running"
    echo ""
    echo "Would you like to start Redis? (y/n)"
    echo "  [1] As a background service (auto-starts on boot)"
    echo "  [2] In foreground (this terminal)"
    echo "  [3] Skip"
    read -r choice

    case $choice in
        1)
            echo ""
            echo "🚀 Starting Redis as a service..."
            brew services start redis
            sleep 2

            if redis-cli ping &> /dev/null; then
                echo "✅ Redis service started successfully"
                echo "   Redis will auto-start on system boot"
            else
                echo "❌ Failed to start Redis service"
                exit 1
            fi
            ;;
        2)
            echo ""
            echo "🚀 Starting Redis in foreground..."
            echo "   Press Ctrl+C to stop Redis"
            echo ""
            redis-server
            ;;
        *)
            echo ""
            echo "⚠️  Redis not started. Database Guru will use in-memory cache fallback."
            echo "   To start Redis later:"
            echo "   brew services start redis"
            exit 0
            ;;
    esac
fi

echo ""
echo "🎉 Redis Setup Complete!"
echo ""
echo "📝 Configuration:"
echo "   Add to your .env file:"
echo "   REDIS_URL=redis://localhost:6379"
echo ""
echo "💡 Useful commands:"
echo "   Check status:  redis-cli ping"
echo "   Stop service:  brew services stop redis"
echo "   Restart:       brew services restart redis"
echo "   View logs:     tail -f /usr/local/var/log/redis.log"
echo ""
