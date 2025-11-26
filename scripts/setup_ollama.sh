#!/bin/bash
# Setup Ollama and pull required models for Database Guru

set -e

echo "🧠 Database Guru - Ollama Setup"
echo "================================"
echo ""

# Check if Ollama is installed
if command -v ollama &> /dev/null; then
    echo "✅ Ollama is already installed"
    OLLAMA_VERSION=$(ollama --version 2>&1 | head -n1)
    echo "   Version: $OLLAMA_VERSION"
else
    echo "❌ Ollama is not installed"
    echo ""
    echo "Would you like to install Ollama? (y/n)"
    read -r response

    if [[ "$response" =~ ^[Yy]$ ]]; then
        echo ""
        echo "📦 Installing Ollama via Homebrew..."

        # Check if Homebrew is installed
        if ! command -v brew &> /dev/null; then
            echo "❌ Homebrew is not installed"
            echo "   Please install Homebrew first: https://brew.sh"
            echo "   Or install Ollama manually: https://ollama.ai/download"
            exit 1
        fi

        brew install ollama
        echo "✅ Ollama installed successfully"
    else
        echo ""
        echo "⚠️  Ollama not installed. Database Guru requires Ollama for SQL generation."
        echo "   Install Ollama: https://ollama.ai/download"
        exit 1
    fi
fi

echo ""
echo "🔍 Checking Ollama status..."

# Check if Ollama is running
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "✅ Ollama is running"
else
    echo "⚠️  Ollama is not running"
    echo ""
    echo "Would you like to start Ollama? (y/n)"
    echo "  [1] As a background service (auto-starts on boot)"
    echo "  [2] In foreground (this terminal)"
    echo "  [3] Skip for now"
    read -r choice

    case $choice in
        1)
            echo ""
            echo "🚀 Starting Ollama as a service..."
            brew services start ollama
            sleep 3

            if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
                echo "✅ Ollama service started successfully"
                echo "   Ollama will auto-start on system boot"
            else
                echo "❌ Failed to start Ollama service"
                exit 1
            fi
            ;;
        2)
            echo ""
            echo "🚀 Starting Ollama in foreground..."
            echo "   Press Ctrl+C to stop, or open a new terminal to continue setup"
            echo ""
            ollama serve
            exit 0
            ;;
        *)
            echo ""
            echo "⚠️  Ollama not started. Please start it manually:"
            echo "   ollama serve"
            exit 0
            ;;
    esac
fi

echo ""
echo "📦 Checking installed models..."
INSTALLED_MODELS=$(ollama list 2>&1)
echo "$INSTALLED_MODELS"
echo ""

# Check for required models
MODELS_TO_PULL=()

# Check for SQL generation model
if echo "$INSTALLED_MODELS" | grep -q "llama3\|codellama\|duckdb-nsql"; then
    echo "✅ SQL generation model found"
else
    echo "⚠️  No SQL generation model found"
    MODELS_TO_PULL+=("SQL")
fi

# Check for embedding model
if echo "$INSTALLED_MODELS" | grep -q "nomic-embed-text"; then
    echo "✅ Embedding model (nomic-embed-text) found"
else
    echo "⚠️  No embedding model found (will use TF-IDF fallback)"
    MODELS_TO_PULL+=("EMBED")
fi

echo ""

# Pull missing models
if [ ${#MODELS_TO_PULL[@]} -eq 0 ]; then
    echo "✨ All recommended models are already installed!"
else
    echo "📥 Recommended models to install:"
    echo ""

    if [[ " ${MODELS_TO_PULL[@]} " =~ " SQL " ]]; then
        echo "SQL Generation Models (choose one):"
        echo "  [1] llama3 (4.7GB) - Fast and general-purpose (recommended)"
        echo "  [2] codellama (3.8GB) - Code-focused"
        echo "  [3] duckdb-nsql (3.8GB) - DuckDB-specific"
        echo ""
    fi

    if [[ " ${MODELS_TO_PULL[@]} " =~ " EMBED " ]]; then
        echo "Embedding Model (for semantic caching):"
        echo "  [4] nomic-embed-text (274MB) - Recommended for better cache matching"
        echo "  [5] Skip (use TF-IDF fallback)"
        echo ""
    fi

    echo "Enter your choices (space-separated, e.g., '1 4'):"
    read -r choices

    for choice in $choices; do
        case $choice in
            1)
                echo ""
                echo "📥 Pulling llama3..."
                ollama pull llama3
                ;;
            2)
                echo ""
                echo "📥 Pulling codellama..."
                ollama pull codellama
                ;;
            3)
                echo ""
                echo "📥 Pulling duckdb-nsql..."
                ollama pull duckdb-nsql
                ;;
            4)
                echo ""
                echo "📥 Pulling nomic-embed-text..."
                ollama pull nomic-embed-text
                ;;
            5)
                echo ""
                echo "⏭️  Skipping embedding model (will use TF-IDF fallback)"
                ;;
            *)
                echo "⚠️  Unknown choice: $choice"
                ;;
        esac
    done
fi

echo ""
echo "📊 Final model list:"
ollama list

echo ""
echo "🎉 Ollama Setup Complete!"
echo ""
echo "📝 Configuration:"
echo "   Add to your .env file:"
echo "   OLLAMA_BASE_URL=http://localhost:11434"
echo "   OLLAMA_MODEL=llama3  # or your preferred model"
echo ""
echo "💡 Useful commands:"
echo "   List models:    ollama list"
echo "   Pull model:     ollama pull <model-name>"
echo "   Remove model:   ollama rm <model-name>"
echo "   Test model:     ollama run llama3 'Hello'"
echo "   Stop service:   brew services stop ollama"
echo ""
