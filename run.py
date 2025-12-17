#!/usr/bin/env python3
"""
Response Report Generator - Entry Point

Starts the Flask web application and opens Safari (macOS) on the correct port.
"""

import os
import sys
import webbrowser
import threading
import time
import socket
import subprocess


def get_runtime_root():
    """
    Runtime root directory.
    - Frozen (PyInstaller): directory containing the executable
    - Dev: project root directory (this file's directory)
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def get_bundle_dir():
    """
    Bundle directory for frozen builds.
    - Frozen: sys._MEIPASS (temp extraction directory)
    - Dev: project root directory
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def ensure_directories():
    """Ensure required directories exist."""
    from services.paths import ensure_dirs_exist
    ensure_dirs_exist()
    print("Runtime directories initialized")


def load_environment():
    """
    Load environment variables from .env file.
    - Frozen: next to executable
    - Dev: project root
    """
    from dotenv import load_dotenv

    runtime_root = get_runtime_root()
    env_file = os.path.join(runtime_root, ".env")

    if os.path.exists(env_file):
        load_dotenv(env_file)
        print(f"Loaded configuration from {env_file}")
    else:
        print("No .env file found, using environment defaults")


def _is_port_free(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.2)
        return s.connect_ex((host, port)) != 0


def _wait_port(host: str, port: int, timeout: float = 20.0) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        if not _is_port_free(host, port):
            return True
        time.sleep(0.2)
    return False


def choose_port(host: str, preferred: int) -> int:
    """
    Pick a usable port.
    1) try preferred
    2) try a small safe list
    3) ask OS for an ephemeral port
    """
    if _is_port_free(host, preferred):
        return preferred

    for p in (5050, 5001, 8000, 8080, 8888):
        if _is_port_free(host, p):
            return p

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, 0))
        return s.getsockname()[1]


def _open_safari(url: str):
    """
    Force Safari on macOS. Else fallback to default browser.
    """
    try:
        if sys.platform == "darwin":
            subprocess.run(["open", "-a", "Safari", url], check=False)
        else:
            webbrowser.open(url)
    except Exception:
        webbrowser.open(url)


def open_browser(host: str, port: int):
    url = f"http://{host}:{port}/"
    if _wait_port(host, port, timeout=20):
        print(f"\nOpening Safari at {url}\n")
        _open_safari(url)
    else:
        print(f"\nWARNING: Server did not open port in time: {url}\n")


def main():
    # If frozen, work from extracted bundle so relative paths behave
    bundle_dir = get_bundle_dir()
    if getattr(sys, "frozen", False):
        os.chdir(bundle_dir)

    load_environment()
    ensure_directories()

    host = os.environ.get("HOST", "127.0.0.1")

    # macOS: 5000 is often occupied (AirTunes/AirPlay). Prefer 5050 by default.
    default_port = 5050 if sys.platform == "darwin" else 5000
    preferred = int(os.environ.get("PORT", default_port))
    port = choose_port(host, preferred)

    # Open browser AFTER server is really listening
    threading.Thread(target=open_browser, args=(host, port), daemon=True).start()

    print("=" * 60)
    print("  Response Report Generator")
    print("=" * 60)
    print(f"\n  Starting server at http://{host}:{port}")
    print("  Press Ctrl+C to stop the server\n")
    print("=" * 60)

    from app import app
    app.run(host=host, port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()

