#!/bin/bash
# Manga Colorizer Launcher

cd "$(dirname "$0")"

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Creating..."
    python3 -m venv venv
fi

# Activate venv and run
source venv/bin/activate
python manga_colorizer_gui.py
