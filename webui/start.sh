#!/bin/bash
# Quick start script for radiod Web UI

echo "=========================================="
echo "radiod Web UI - Starting..."
echo "=========================================="
echo ""

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed"
    exit 1
fi

# Check if Flask is installed
if ! python3 -c "import flask" 2>/dev/null; then
    echo "⚠️  Flask not found. Installing dependencies..."
    pip3 install -r requirements.txt
    echo ""
fi

# Check if ka9q-python is installed
if ! python3 -c "import ka9q" 2>/dev/null; then
    echo "⚠️  ka9q-python not found. Installing..."
    cd ..
    pip3 install -e .
    cd webui
    echo ""
fi

echo "✅ Dependencies OK"
echo ""
echo "Starting web server..."
echo "Access the UI at: http://localhost:5000"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Start the Flask app
python3 app.py
