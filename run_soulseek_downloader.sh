#!/bin/bash

# SoulseekDownloader Launcher Script
# This script launches the Python application

echo "Starting SoulseekDownloader..."

# Check if Python 3 is available
if command -v python3 &> /dev/null; then
    # Verify that PyObjC (Cocoa) is installed
    if ! python3 -m pip show pyobjc-framework-Cocoa > /dev/null 2>&1; then
        echo "PyObjC (pyobjc-framework-Cocoa) is not installed."
        echo "Please run 'pip install -r requirements.txt' and try again."
        exit 1
    fi
    python3 soulseek_downloader.py
elif command -v python &> /dev/null; then
    python soulseek_downloader.py
else
    echo "Error: Python 3 is not installed or not in PATH"
    echo "Please install Python 3 and try again"
    exit 1
fi 