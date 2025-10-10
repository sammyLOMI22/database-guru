#!/bin/bash
echo "🧙‍♂️ Starting Database Guru..."

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

# Install requirements
pip install -q -r requirements.txt

# Run the app
python src/main.py
