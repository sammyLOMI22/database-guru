#!/bin/bash

# Database Guru - Frontend Setup Script

echo "🎨 Setting up Database Guru Frontend..."
echo ""

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed"
    echo "   Please install Node.js 18+ from: https://nodejs.org/"
    exit 1
fi

NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo "⚠️  Node.js version is $NODE_VERSION, but version 18+ is recommended"
fi

echo "✅ Node.js $(node -v) detected"
echo ""

# Navigate to frontend directory
cd frontend

# Install dependencies
echo "📦 Installing dependencies..."
npm install

if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies"
    exit 1
fi

echo ""
echo "✅ Dependencies installed successfully!"
echo ""

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cat > .env << EOF
VITE_API_URL=http://localhost:8000
EOF
    echo "✅ .env file created"
fi

echo ""
echo "="
echo "🎉 Frontend setup complete!"
echo "="
echo ""
echo "Next steps:"
echo ""
echo "1. Start the backend API:"
echo "   cd .."
echo "   python src/main.py"
echo ""
echo "2. In a new terminal, start the frontend:"
echo "   cd frontend"
echo "   npm run dev"
echo ""
echo "3. Open your browser:"
echo "   http://localhost:3000"
echo ""
echo "Happy coding! 🚀"
