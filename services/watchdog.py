"""
Watchdog Module - Comprehensive Internal Monitoring System

This module provides:
- Central logging to logs/runtime_report.log
- Global exception interception
- Anomaly detection for silent errors
- Performance monitoring
- Request/response logging
- User action tracking
"""

import os
import sys
import time
import json
import threading
import traceback
import functools
from datetime import datetime
from typing import Any, Callable, Dict, Optional
import logging
from logging.handlers import RotatingFileHandler

from services.paths import get_logs_dir, get_runtime_log_file

LOGS_DIR = str(get_logs_dir())
LOG_FILE = str(get_runtime_log_file())
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10 MB
BACKUP_COUNT = 5
SLOW_RESPONSE_THRESHOLD = 5.0  # seconds


class WatchdogLogger:
    """Central logging system with rotating file handler."""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._setup_logs_directory()
        self._setup_logger()
        self._install_exception_hooks()
        self._request_context = threading.local()
        self._performance_stats = {
            'request_count': 0,
            'error_count': 0,
            'slow_requests': 0,
            'total_response_time': 0.0
        }
        self._stats_lock = threading.Lock()
    
    def _setup_logs_directory(self):
        """Create logs directory if it doesn't exist."""
        logs_dir = get_logs_dir()
        logs_dir.mkdir(parents=True, exist_ok=True)
    
    def _setup_logger(self):
        """Configure the main logger with rotating file handler."""
        self.logger = logging.getLogger('watchdog')
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers = []
        
        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=MAX_LOG_SIZE,
            backupCount=BACKUP_COUNT,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(logging.WARNING)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
    
    def _install_exception_hooks(self):
        """Install global exception handlers."""
        self._original_excepthook = sys.excepthook
        sys.excepthook = self._global_exception_handler
        
        threading.excepthook = self._thread_exception_handler
    
    def _global_exception_handler(self, exc_type, exc_value, exc_traceback):
        """Handle uncaught exceptions globally."""
        if issubclass(exc_type, KeyboardInterrupt):
            self._original_excepthook(exc_type, exc_value, exc_traceback)
            return
        
        self.log_exception(
            exc_type=exc_type.__name__,
            exc_value=str(exc_value),
            exc_traceback=traceback.format_exception(exc_type, exc_value, exc_traceback),
            context='GLOBAL_UNCAUGHT_EXCEPTION'
        )
        
        self._original_excepthook(exc_type, exc_value, exc_traceback)
    
    def _thread_exception_handler(self, args):
        """Handle uncaught exceptions in threads."""
        self.log_exception(
            exc_type=args.exc_type.__name__ if args.exc_type else 'Unknown',
            exc_value=str(args.exc_value) if args.exc_value else 'Unknown',
            exc_traceback=traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback) if args.exc_traceback else [],
            context=f'THREAD_EXCEPTION (thread: {args.thread.name if args.thread else "unknown"})'
        )
    
    def log_event(self, event_type: str, message: str, level: str = 'INFO', 
                  extra_data: Optional[Dict] = None):
        """Log a general event."""
        log_entry = {
            'event_type': event_type,
            'message': message
        }
        if extra_data:
            log_entry['extra'] = extra_data
        
        log_message = f"[{event_type}] {message}"
        if extra_data:
            log_message += f" | Data: {json.dumps(extra_data, default=str)}"
        
        log_level = getattr(logging, level.upper(), logging.INFO)
        self.logger.log(log_level, log_message)
    
    def log_exception(self, exc_type: str, exc_value: str, 
                      exc_traceback: list, context: str = 'EXCEPTION',
                      extra_data: Optional[Dict] = None):
        """Log an exception with full details."""
        with self._stats_lock:
            self._performance_stats['error_count'] += 1
        
        tb_str = ''.join(exc_traceback) if exc_traceback else 'No traceback available'
        
        log_message = (
            f"[{context}] Type: {exc_type} | "
            f"Value: {exc_value} | "
            f"Traceback:\n{tb_str}"
        )
        
        if extra_data:
            log_message += f"\nExtra Data: {json.dumps(extra_data, default=str)}"
        
        self.logger.error(log_message)
    
    def log_warning(self, warning_type: str, message: str, 
                    extra_data: Optional[Dict] = None):
        """Log a warning (non-fatal issue)."""
        log_message = f"[WARNING:{warning_type}] {message}"
        if extra_data:
            log_message += f" | Data: {json.dumps(extra_data, default=str)}"
        
        self.logger.warning(log_message)
    
    def log_anomaly(self, anomaly_type: str, description: str,
                    expected: Any = None, actual: Any = None,
                    extra_data: Optional[Dict] = None):
        """Log a silent anomaly (doesn't crash but is abnormal)."""
        anomaly_data = {
            'anomaly_type': anomaly_type,
            'description': description
        }
        if expected is not None:
            anomaly_data['expected'] = str(expected)
        if actual is not None:
            anomaly_data['actual'] = str(actual)
        if extra_data:
            anomaly_data.update(extra_data)
        
        log_message = (
            f"[ANOMALY:{anomaly_type}] {description}"
        )
        if expected is not None or actual is not None:
            log_message += f" | Expected: {expected} | Actual: {actual}"
        if extra_data:
            log_message += f" | Extra: {json.dumps(extra_data, default=str)}"
        
        self.logger.warning(log_message)
    
    def log_request_start(self, method: str, path: str, 
                          client_ip: str = None, user_agent: str = None):
        """Log the start of an HTTP request."""
        self._request_context.start_time = time.time()
        self._request_context.method = method
        self._request_context.path = path
        
        with self._stats_lock:
            self._performance_stats['request_count'] += 1
        
        extra = {}
        if client_ip:
            extra['client_ip'] = client_ip
        if user_agent:
            extra['user_agent'] = user_agent[:100]
        
        self.log_event('REQUEST_START', f"{method} {path}", 'DEBUG', extra if extra else None)
    
    def log_request_end(self, status_code: int, response_size: int = None):
        """Log the end of an HTTP request with timing."""
        start_time = getattr(self._request_context, 'start_time', None)
        method = getattr(self._request_context, 'method', 'UNKNOWN')
        path = getattr(self._request_context, 'path', 'UNKNOWN')
        
        if start_time:
            duration = time.time() - start_time
            with self._stats_lock:
                self._performance_stats['total_response_time'] += duration
                if duration > SLOW_RESPONSE_THRESHOLD:
                    self._performance_stats['slow_requests'] += 1
        else:
            duration = -1
        
        extra = {
            'status_code': status_code,
            'duration_ms': round(duration * 1000, 2) if duration >= 0 else None
        }
        if response_size:
            extra['response_size'] = response_size
        
        level = 'DEBUG'
        if status_code >= 500:
            level = 'ERROR'
        elif status_code >= 400:
            level = 'WARNING'
        elif duration > SLOW_RESPONSE_THRESHOLD:
            level = 'WARNING'
            self.log_anomaly(
                'SLOW_RESPONSE',
                f"Request took {duration:.2f}s (threshold: {SLOW_RESPONSE_THRESHOLD}s)",
                expected=f"<{SLOW_RESPONSE_THRESHOLD}s",
                actual=f"{duration:.2f}s",
                extra_data={'method': method, 'path': path}
            )
        
        self.log_event(
            'REQUEST_END',
            f"{method} {path} -> {status_code} ({duration*1000:.0f}ms)",
            level,
            extra
        )
    
    def log_user_action(self, action_type: str, action_details: str,
                        user_id: str = None, extra_data: Optional[Dict] = None):
        """Log a user action from the frontend."""
        action_data = {
            'action_type': action_type,
            'details': action_details
        }
        if user_id:
            action_data['user_id'] = user_id
        if extra_data:
            action_data.update(extra_data)
        
        self.log_event('USER_ACTION', f"{action_type}: {action_details}", 'INFO', action_data)
    
    def log_data_anomaly(self, field_name: str, issue: str,
                         expected_type: str = None, actual_value: Any = None):
        """Log a data validation anomaly."""
        self.log_anomaly(
            'DATA_VALIDATION',
            f"Field '{field_name}': {issue}",
            expected=expected_type,
            actual=type(actual_value).__name__ if actual_value is not None else None,
            extra_data={'value_preview': str(actual_value)[:100] if actual_value else None}
        )
    
    def log_function_anomaly(self, function_name: str, issue: str,
                             args_preview: str = None, return_value: Any = None):
        """Log a function execution anomaly."""
        extra = {}
        if args_preview:
            extra['args'] = args_preview[:200]
        if return_value is not None:
            extra['return_value'] = str(return_value)[:200]
        
        self.log_anomaly(
            'FUNCTION_BEHAVIOR',
            f"Function '{function_name}': {issue}",
            extra_data=extra if extra else None
        )
    
    def get_performance_stats(self) -> Dict:
        """Get current performance statistics."""
        with self._stats_lock:
            stats = self._performance_stats.copy()
            if stats['request_count'] > 0:
                stats['avg_response_time_ms'] = round(
                    (stats['total_response_time'] / stats['request_count']) * 1000, 2
                )
            else:
                stats['avg_response_time_ms'] = 0
            return stats
    
    def log_startup(self, app_name: str = 'Application'):
        """Log application startup."""
        self.logger.info('=' * 80)
        self.logger.info(f"[STARTUP] {app_name} started at {datetime.now().isoformat()}")
        self.logger.info(f"[STARTUP] Python version: {sys.version}")
        self.logger.info(f"[STARTUP] Log file: {LOG_FILE}")
        self.logger.info('=' * 80)
    
    def log_shutdown(self, app_name: str = 'Application'):
        """Log application shutdown."""
        stats = self.get_performance_stats()
        self.logger.info('=' * 80)
        self.logger.info(f"[SHUTDOWN] {app_name} shutting down at {datetime.now().isoformat()}")
        self.logger.info(f"[SHUTDOWN] Stats: {json.dumps(stats)}")
        self.logger.info('=' * 80)


watchdog = WatchdogLogger()


def monitor_function(func: Callable = None, *, 
                     check_empty_return: bool = True,
                     log_args: bool = False,
                     warn_slow: float = None):
    """
    Decorator to monitor a function for anomalies.
    
    Args:
        check_empty_return: Warn if function returns None/empty
        log_args: Log function arguments
        warn_slow: Warn if function takes longer than this (seconds)
    """
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            func_name = f"{fn.__module__}.{fn.__name__}"
            start_time = time.time()
            
            args_preview = None
            if log_args:
                try:
                    args_preview = f"args={args[:3]}, kwargs={list(kwargs.keys())}"
                except:
                    args_preview = "Unable to capture args"
            
            try:
                result = fn(*args, **kwargs)
                
                duration = time.time() - start_time
                if warn_slow and duration > warn_slow:
                    watchdog.log_function_anomaly(
                        func_name,
                        f"Slow execution: {duration:.2f}s (threshold: {warn_slow}s)",
                        args_preview
                    )
                
                if check_empty_return:
                    if result is None:
                        pass
                    elif isinstance(result, (dict, list, str)) and len(result) == 0:
                        watchdog.log_function_anomaly(
                            func_name,
                            "Returned empty collection",
                            args_preview,
                            result
                        )
                
                return result
                
            except Exception as e:
                watchdog.log_exception(
                    exc_type=type(e).__name__,
                    exc_value=str(e),
                    exc_traceback=traceback.format_exception(type(e), e, e.__traceback__),
                    context=f'FUNCTION_ERROR:{func_name}',
                    extra_data={'args_preview': args_preview} if args_preview else None
                )
                raise
        
        return wrapper
    
    if func is not None:
        return decorator(func)
    return decorator


def validate_data(data: Any, schema: Dict[str, type], context: str = 'data'):
    """
    Validate data against a schema and log anomalies.
    
    Args:
        data: Dictionary to validate
        schema: Dict mapping field names to expected types
        context: Context description for logging
    """
    if not isinstance(data, dict):
        watchdog.log_data_anomaly(
            context,
            "Expected dict, got different type",
            expected_type='dict',
            actual_value=data
        )
        return False
    
    all_valid = True
    for field, expected_type in schema.items():
        if field not in data:
            watchdog.log_data_anomaly(
                f"{context}.{field}",
                "Missing required field",
                expected_type=expected_type.__name__
            )
            all_valid = False
        elif not isinstance(data[field], expected_type):
            watchdog.log_data_anomaly(
                f"{context}.{field}",
                "Type mismatch",
                expected_type=expected_type.__name__,
                actual_value=data[field]
            )
            all_valid = False
    
    return all_valid
