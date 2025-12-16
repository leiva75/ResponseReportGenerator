#!/usr/bin/env python3
"""
Development server launcher for Response Report Generator.

Usage:
    python scripts/run_dev.py
    
Features:
    - Auto-reload on code changes
    - Debug mode enabled
    - Opens browser automatically
"""

import os
import sys
import webbrowser
import threading
import time

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
os.chdir(project_root)

from dotenv import load_dotenv

load_dotenv(os.path.join(project_root, '.env'))

os.environ.setdefault('APP_ENV', 'dev')
os.environ.setdefault('FLASK_ENV', 'development')


def open_browser(port):
    """Open the default web browser after a short delay."""
    time.sleep(2)
    url = f"http://127.0.0.1:{port}"
    print(f"\n  Opening browser at {url}")
    webbrowser.open(url)


def main():
    """Main entry point for development server."""
    host = os.environ.get('HOST', '127.0.0.1')
    port = int(os.environ.get('PORT', 5000))
    
    print("=" * 60)
    print("  Response Report Generator - DEVELOPMENT MODE")
    print("=" * 60)
    print(f"\n  Server: http://{host}:{port}")
    print("  Debug: ON")
    print("  Auto-reload: ON")
    print("\n  Press Ctrl+C to stop the server")
    print("=" * 60)
    
    browser_thread = threading.Thread(target=open_browser, args=(port,), daemon=True)
    browser_thread.start()
    
    try:
        from src.response.app import create_app
        app = create_app('dev')
    except ImportError:
        from app import app
    
    app.run(host=host, port=port, debug=True, use_reloader=True)


if __name__ == '__main__':
    main()
