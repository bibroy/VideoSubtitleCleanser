#!/usr/bin/env python
"""
Script to open the web browser for VideoSubtitleCleanser web application
"""

import webbrowser
import time
import sys

def main():
    """Open the web browser to the VideoSubtitleCleanser web application"""
    # Wait a moment for the server to start
    time.sleep(2)
    
    # Open the browser
    url = "http://localhost:5000"
    print(f"Opening web browser to {url}")
    webbrowser.open(url)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
