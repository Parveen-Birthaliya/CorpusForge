#!/bin/bash

# Navigate to the project directory
cd "$(dirname "$0")" || exit

echo "🛑 Stopping any running servers..."
pkill -f "src.corpusforge.app" || true
pkill -f "src.corpusforge.server:app" || true
sleep 1

echo "🟢 Starting FastAPI server..."
# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the app
PYTHONPATH=. uvicorn src.corpusforge.server:app --host 0.0.0.0 --port 7860
