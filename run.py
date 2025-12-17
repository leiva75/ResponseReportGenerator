#!/usr/bin/env python3
"""
Response Report Generator - Entry Point

Starts the Flask web app and opens Safari (macOS) or the default browser.
"""

import os
import sys
import time
import socket
import threading
import webbrowser
import subprocess


def get_runtime_root() -> str:
    """
    For PyInstaller: directory containing the executable
    For dev: directory containing this file
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def get_bundle_dir() -> str:
    """
    For PyInstaller: sys._MEIPASS (temp extraction dir)
    For dev: directory containing this file
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def ensure_directories():
    from services.paths import ensure_dirs_exist
    ensure_dirs_exist()
    print("Runtime directories initialized")


def load_environment():
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
        if not _is_port_free(host, port):  # port is now LISTENING
            return True
        time.sleep(0.2)
    return False


def choose_port(host: str, preferred: int) -> int:
    # 1) preferred
    if _is_port_free(host, preferred):
        return preferred

    # 2) common alternates
    for p in (5050, 5001, 8000, 8080, 8888):
        if _is_port_free(host, p):
            return p

    # 3) ask OS for a free port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, 0))
        return s.getsockname()[1]


def _open_safari(url: str):
    """Force Safari on macOS; fallback to default browser otherwise."""
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
    runtime_root = get_runtime_root()
    bundle_dir = get_bundle_dir()

    if getattr(sys, "frozen", False):
        os.chdir(bundle_dir)

    load_environment()
    ensure_directories()

    host = os.environ.get("HOST", "127.0.0.1")
    preferred = int(os.environ.get("PORT", "5050"))
    port = choose_port(host, preferred)

    # keep everything coherent
    os.environ["HOST"] = host
    os.environ["PORT"] = str(port)

    # Import app AFTER env/dirs are set (and before starting browser thread)
    from app import app

    # Start browser opener thread (IMPORTANT: args=(host, port))
    browser_thread = threading.Thread(target=open_browser, args=(host, port), daemon=True)
    browser_thread.start()

    print("=" * 60)
    print("  Response Report Generator")
    print("=" * 60)
    print(f"\n  Starting server at http://{host}:{port}/")
    print("  Press Ctrl+C to stop the server\n")
    print("=" * 60)

    app.run(host=host, port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
