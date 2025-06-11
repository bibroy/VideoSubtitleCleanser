#!/usr/bin/env python
"""
Launcher script for VideoSubtitleCleanser web application
"""

import os
import sys
import webbrowser
import threading
import time
from pathlib import Path

def open_browser():
    """Open web browser after a short delay"""
    time.sleep(2)
    webbrowser.open('http://localhost:5000')

def main():
    """Main entry point for the web application launcher"""
    print("=" * 80)
    print("VideoSubtitleCleanser Web Application")
    print("=" * 80)
    
    # Check if required directories exist, create them if not
    project_root = Path(__file__).resolve().parent
    uploads_dir = project_root / 'uploads'
    outputs_dir = project_root / 'outputs'
    
    os.makedirs(uploads_dir, exist_ok=True)
    os.makedirs(outputs_dir, exist_ok=True)
    
    print(f"Uploads directory: {uploads_dir}")
    print(f"Outputs directory: {outputs_dir}")
    
    # Add project root to path
    sys.path.insert(0, str(project_root))
    
    # Start browser in a new thread
    threading.Thread(target=open_browser).start()
    
    # Import and run the web server
    try:
        from web_server import run_server
        print("Starting web server...")
        run_server(host='0.0.0.0', port=5000, open_browser_automatically=False)
    except Exception as e:
        print(f"Error starting web server: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
