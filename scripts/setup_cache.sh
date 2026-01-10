#!/bin/bash
# Master setup script for Database Guru caching (Redis + Ollama)

set -e

echo "🚀 Database Guru - Complete Cache Setup"
echo "========================================"
echo ""
echo "This script will help you set up:"
echo "  1. Redis (for persistent caching)"
echo "  2. Ollama + Models (for SQL generation and embeddings)"
echo ""
echo "Press Enter to continue or Ctrl+C to cancel..."
read -r

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  STEP 1/2: Redis Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

"$SCRIPT_DIR/setup_redis.sh"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  STEP 2/2: Ollama Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

"$SCRIPT_DIR/setup_ollama.sh"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✨ Setup Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📝 Next Steps:"
echo ""
echo "1. Update your .env file with:"
echo "   REDIS_URL=redis://localhost:6379"
echo "   OLLAMA_BASE_URL=http://localhost:11434"
echo "   OLLAMA_MODEL=llama3"
echo ""
echo "2. Start Database Guru:"
echo "   ./start.sh"
echo ""
echo "3. View cache stats in the UI:"
echo "   http://localhost:3000 → Cache tab"
echo ""
echo "💡 For more information, see: docs/technical/CACHE_SETUP.md"
echo ""
