#!/bin/bash
# Convenience script to run the CLI

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Creating..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Run CLI with arguments
python cli/cli.py "$@"
