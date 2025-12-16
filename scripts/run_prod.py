#!/usr/bin/env python3
"""
Production server launcher for Response Report Generator.

Usage:
    python scripts/run_prod.py
    
Features:
    - Uses Waitress WSGI server (production-ready)
    - No debug mode
    - Opens browser automatically
    - Validates configuration
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

os.environ['APP_ENV'] = 'prod'
os.environ['FLASK_ENV'] = 'production'


def check_waitress():
    """Check if waitress is installed, install if not."""
    try:
        import waitress
        return True
    except ImportError:
        print("  Waitress not installed. Installing...")
        import subprocess
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'waitress'])
        return True


def validate_config():
    """Validate production configuration."""
    secret = os.environ.get('SESSION_SECRET') or \
             os.environ.get('FLASK_SECRET_KEY') or \
             os.environ.get('SECRET_KEY')
    
    if not secret or len(secret) < 16 or 'change' in secret.lower():
        print("\n  WARNING: Insecure or missing SECRET_KEY!")
        print("  Generate a secure key with:")
        print('    python -c "import secrets; print(secrets.token_hex(32))"')
        print("  Then set SESSION_SECRET in your .env file.\n")
        response = input("  Continue anyway? (y/N): ")
        if response.lower() != 'y':
            sys.exit(1)


def open_browser(port):
    """Open the default web browser after a short delay."""
    time.sleep(2)
    url = f"http://127.0.0.1:{port}"
    print(f"\n  Opening browser at {url}")
    webbrowser.open(url)


def main():
    """Main entry point for production server."""
    check_waitress()
    validate_config()
    
    host = os.environ.get('HOST', '127.0.0.1')
    port = int(os.environ.get('PORT', 5000))
    
    print("=" * 60)
    print("  Response Report Generator - PRODUCTION MODE")
    print("=" * 60)
    print(f"\n  Server: http://{host}:{port}")
    print("  WSGI: Waitress")
    print("  Debug: OFF")
    print("\n  Press Ctrl+C to stop the server")
    print("=" * 60)
    
    browser_thread = threading.Thread(target=open_browser, args=(port,), daemon=True)
    browser_thread.start()
    
    from waitress import serve
    
    try:
        from src.response.app import create_app
        app = create_app('prod')
    except ImportError:
        from app import app
    
    serve(app, host=host, port=port, threads=4)


if __name__ == '__main__':
    main()
