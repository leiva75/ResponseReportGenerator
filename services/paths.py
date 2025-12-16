"""
Cross-Platform Path Management Module

Provides consistent path handling for the application across different platforms
and deployment scenarios (development, frozen executable, installed application).

Uses platformdirs for reliable Windows/macOS/Linux user directory detection.

For Windows distribution:
- Data: %APPDATA%/ResponseReportGenerator
- Cache: %LOCALAPPDATA%/ResponseReportGenerator
- Logs: %LOCALAPPDATA%/ResponseReportGenerator/logs
- Exports: %APPDATA%/ResponseReportGenerator/exports
"""

import sys
from pathlib import Path
from typing import Optional

import platformdirs

APP_NAME = "ResponseReportGenerator"
APP_AUTHOR = "Response"


def is_frozen() -> bool:
    """Check if running as a PyInstaller frozen executable."""
    return getattr(sys, 'frozen', False)


def get_runtime_root() -> Path:
    """
    Get the runtime root directory.
    
    For frozen builds: directory containing the executable
    For development: project root directory
    """
    if is_frozen():
        return Path(sys.executable).parent
    return Path(__file__).parent.parent


def get_bundle_dir() -> Path:
    """
    Get the bundle directory for frozen builds (where PyInstaller extracts files).
    
    For frozen builds: sys._MEIPASS (temp extraction directory)
    For development: project root directory
    """
    if is_frozen() and hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS)
    return Path(__file__).parent.parent


def get_data_dir() -> Path:
    """
    Get the data directory for persistent user data (history, drafts, etc.).
    
    For frozen builds: user data directory via platformdirs
    For development: project's data/ directory
    
    Windows: %APPDATA%/ResponseReportGenerator
    macOS: ~/Library/Application Support/ResponseReportGenerator
    Linux: ~/.local/share/ResponseReportGenerator
    """
    if is_frozen():
        return Path(platformdirs.user_data_dir(APP_NAME, APP_AUTHOR))
    return get_runtime_root() / 'data'


def get_cache_dir() -> Path:
    """
    Get the cache directory for temporary cached data (SQLite caches, etc.).
    
    For frozen builds: user cache directory via platformdirs
    For development: project's data/ directory
    
    Windows: %LOCALAPPDATA%/ResponseReportGenerator
    macOS: ~/Library/Caches/ResponseReportGenerator
    Linux: ~/.cache/ResponseReportGenerator
    """
    if is_frozen():
        return Path(platformdirs.user_cache_dir(APP_NAME, APP_AUTHOR))
    return get_runtime_root() / 'data'


def get_logs_dir() -> Path:
    """
    Get the logs directory.
    
    For frozen builds: user log directory via platformdirs
    For development: project's logs/ directory
    
    Windows: %LOCALAPPDATA%/ResponseReportGenerator/logs
    macOS: ~/Library/Logs/ResponseReportGenerator
    Linux: ~/.local/state/ResponseReportGenerator/log
    """
    if is_frozen():
        return Path(platformdirs.user_log_dir(APP_NAME, APP_AUTHOR))
    return get_runtime_root() / 'logs'


def get_exports_dir() -> Path:
    """
    Get the exports directory for generated reports.
    
    For frozen builds: user data directory + exports subdirectory
    For development: project's exports/ directory
    
    Windows: %APPDATA%/ResponseReportGenerator/exports
    macOS: ~/Library/Application Support/ResponseReportGenerator/exports
    Linux: ~/.local/share/ResponseReportGenerator/exports
    """
    if is_frozen():
        return Path(platformdirs.user_data_dir(APP_NAME, APP_AUTHOR)) / 'exports'
    return get_runtime_root() / 'exports'


def get_templates_dir() -> Path:
    """Get the templates directory (read-only, bundled)."""
    return get_bundle_dir() / 'templates'


def get_static_dir() -> Path:
    """Get the static files directory (read-only, bundled)."""
    return get_bundle_dir() / 'static'


def get_env_file() -> Optional[Path]:
    """
    Get the .env file path.
    
    For frozen builds: looks next to the executable
    For development: looks in project root
    """
    env_path = get_runtime_root() / '.env'
    if env_path.exists():
        return env_path
    return None


def ensure_dirs_exist() -> None:
    """
    Ensure all required runtime directories exist.
    
    Creates:
    - Data directory (for history, drafts)
    - Logs directory (for application logs)
    - Exports directory (for generated reports)
    - Cache directory (for temporary data)
    """
    dirs_to_create = [
        get_data_dir(),
        get_logs_dir(),
        get_exports_dir(),
        get_cache_dir(),
    ]
    
    for dir_path in dirs_to_create:
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            print(f"Warning: Could not create directory {dir_path}: {e}")


def get_history_file() -> Path:
    """Get the path to the history JSON file."""
    return get_data_dir() / 'history_reports.json'


def get_history_backup_file() -> Path:
    """Get the path to the history backup file."""
    return get_data_dir() / 'history_reports.backup.json'


def get_questionnaire_file() -> Path:
    """Get the path to the questionnaire JSON file."""
    return get_data_dir() / 'security_questionnaires.json'


def get_security_intel_cache_db() -> Path:
    """Get the path to the security intelligence cache database."""
    return get_cache_dir() / 'security_intel_cache.db'


def get_security_brief_cache_db() -> Path:
    """Get the path to the security brief cache database."""
    return get_cache_dir() / 'security_brief_cache.db'


def get_runtime_log_file() -> Path:
    """Get the path to the runtime log file."""
    return get_logs_dir() / 'runtime_report.log'
