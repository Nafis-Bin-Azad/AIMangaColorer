#!/bin/bash
# Convenience script to run the GUI

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Node modules not found. Installing..."
    npm install
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Creating..."
    python3 -m venv venv
fi

# Start the GUI
npm start
