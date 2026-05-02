#!/bin/bash

# Navigate to the project directory
cd "$(dirname "$0")" || exit

echo "🛑 Stopping any running Gradio servers..."
pkill -f "src.corpusforge.app" || true
sleep 1

echo "🟢 Starting Gradio server..."
# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the app
PYTHONPATH=. python -m src.corpusforge.app
