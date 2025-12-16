#!/usr/bin/env python3
"""
Response Report Generator - Entry Point

This script starts the Flask web application and opens the default browser.
For use on Windows and other platforms.

Usage:
    python run.py
    
Or on Windows:
    Double-click run_windows.bat
"""

import os
import sys
import webbrowser
import threading
import time


def get_runtime_root():
    """
    Get the runtime root directory.
    
    For frozen builds (PyInstaller): directory containing the executable
    For development: project root directory
    """
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def get_bundle_dir():
    """
    Get the bundle directory for frozen builds.
    
    For frozen builds: sys._MEIPASS (temp extraction directory)
    For development: project root directory
    """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def ensure_directories():
    """
    Ensure required directories exist.
    
    Uses the paths module for proper Windows user directory support.
    """
    from services.paths import ensure_dirs_exist
    ensure_dirs_exist()
    print("Runtime directories initialized")


def load_environment():
    """
    Load environment variables from .env file.
    
    For frozen builds: looks next to the executable
    For development: looks in project root
    """
    from dotenv import load_dotenv
    
    runtime_root = get_runtime_root()
    env_file = os.path.join(runtime_root, '.env')
    
    if os.path.exists(env_file):
        load_dotenv(env_file)
        print(f"Loaded configuration from {env_file}")
    else:
        print("No .env file found, using environment defaults")


def open_browser(port):
    """Open the default web browser after a short delay."""
    time.sleep(1.5)
    url = f"http://127.0.0.1:{port}"
    print(f"\nOpening browser at {url}")
    webbrowser.open(url)


def main():
    """Main entry point."""
    runtime_root = get_runtime_root()
    bundle_dir = get_bundle_dir()
    
    if getattr(sys, 'frozen', False):
        os.chdir(bundle_dir)
    
    load_environment()
    
    ensure_directories()
    
    host = os.environ.get('HOST', '127.0.0.1')
    port = int(os.environ.get('PORT', 5000))
    
    browser_thread = threading.Thread(target=open_browser, args=(port,), daemon=True)
    browser_thread.start()
    
    print("=" * 60)
    print("  Response Report Generator")
    print("=" * 60)
    print(f"\n  Starting server at http://{host}:{port}")
    print("  Press Ctrl+C to stop the server\n")
    print("=" * 60)
    
    from app import app
    app.run(host=host, port=port, debug=False, use_reloader=False)


if __name__ == '__main__':
    main()
