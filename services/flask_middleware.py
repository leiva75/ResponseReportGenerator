"""
Flask Middleware for Watchdog Integration

Provides automatic request/response logging and error handling
for Flask applications.
"""

import traceback
from functools import wraps
from flask import request, g, jsonify
from services.watchdog import watchdog


class WatchdogMiddleware:
    """
    WSGI middleware that wraps Flask app for request/response monitoring.
    """
    
    def __init__(self, app):
        self.app = app
        self._register_hooks(app)
        self._register_error_handlers(app)
        watchdog.log_startup('Flask Application')
    
    def _register_hooks(self, app):
        """Register Flask before/after request hooks."""
        import time
        
        @app.before_request
        def before_request_handler():
            """Log request start and capture timing."""
            g.watchdog_start_time = time.time()
            
            watchdog.log_request_start(
                method=request.method,
                path=request.path,
                client_ip=request.remote_addr,
                user_agent=request.headers.get('User-Agent', '')
            )
        
        @app.after_request
        def after_request_handler(response):
            """Log request completion with timing and status."""
            try:
                start_time = getattr(g, 'watchdog_start_time', None)
                duration = time.time() - start_time if start_time else 0
                response_size = response.content_length
                watchdog.log_request_end(
                    status_code=response.status_code,
                    response_size=response_size
                )
            finally:
                g.watchdog_start_time = None
            return response
        
        @app.teardown_request
        def teardown_request_handler(exception):
            """Clean up request context."""
            g.watchdog_start_time = None
    
    def _register_error_handlers(self, app):
        """Register global error handlers."""
        
        @app.errorhandler(Exception)
        def handle_exception(e):
            """Catch-all exception handler."""
            watchdog.log_exception(
                exc_type=type(e).__name__,
                exc_value=str(e),
                exc_traceback=traceback.format_exception(type(e), e, e.__traceback__),
                context='FLASK_UNHANDLED_EXCEPTION',
                extra_data={
                    'path': request.path,
                    'method': request.method
                }
            )
            
            if request.is_json or request.path.startswith('/api'):
                return jsonify({
                    'success': False,
                    'error': 'Internal server error'
                }), 500
            
            return "An unexpected error occurred. Please try again.", 500
        
        @app.errorhandler(404)
        def handle_404(e):
            """Handle 404 errors."""
            watchdog.log_event(
                'HTTP_404',
                f"Not found: {request.path}",
                'WARNING',
                {'method': request.method, 'referrer': request.referrer}
            )
            
            if request.is_json or request.path.startswith('/api'):
                return jsonify({
                    'success': False,
                    'error': 'Not found',
                    'message': f"Path {request.path} not found"
                }), 404
            
            return f"Page not found: {request.path}", 404
        
        @app.errorhandler(400)
        def handle_400(e):
            """Handle bad request errors."""
            watchdog.log_event(
                'HTTP_400',
                f"Bad request: {request.path}",
                'WARNING',
                {'method': request.method}
            )
            
            if request.is_json or request.path.startswith('/api'):
                return jsonify({
                    'success': False,
                    'error': 'Bad request'
                }), 400
            
            return "Bad request. Please check your input.", 400
        
        @app.errorhandler(500)
        def handle_500(e):
            """Handle 500 errors explicitly."""
            watchdog.log_exception(
                exc_type='HTTP500Error',
                exc_value=str(e),
                exc_traceback=[],
                context='FLASK_500_ERROR',
                extra_data={'path': request.path, 'method': request.method}
            )
            
            if request.is_json or request.path.startswith('/api'):
                return jsonify({
                    'success': False,
                    'error': 'Internal server error'
                }), 500
            
            return "An unexpected error occurred. Please try again.", 500


def init_watchdog(app):
    """
    Initialize watchdog middleware for a Flask app.
    
    Usage:
        from services.flask_middleware import init_watchdog
        app = Flask(__name__)
        init_watchdog(app)
    """
    return WatchdogMiddleware(app)


def monitored_route(check_json_response=True, log_payload=False):
    """
    Decorator for route functions to add extra monitoring.
    
    Args:
        check_json_response: Validate JSON response structure
        log_payload: Log incoming request payload
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if log_payload:
                try:
                    payload = request.get_json(silent=True) or dict(request.form)
                    if payload:
                        watchdog.log_event(
                            'REQUEST_PAYLOAD',
                            f"Payload for {request.path}",
                            'DEBUG',
                            {'keys': list(payload.keys())[:10]}
                        )
                except Exception as e:
                    watchdog.log_warning(
                        'PAYLOAD_PARSE_ERROR',
                        f"Failed to parse payload: {str(e)}"
                    )
            
            try:
                result = f(*args, **kwargs)
                
                if check_json_response and hasattr(result, 'get_json'):
                    try:
                        json_data = result.get_json()
                        if json_data and isinstance(json_data, dict):
                            if 'success' in json_data and json_data['success'] is False:
                                watchdog.log_event(
                                    'API_FAILURE_RESPONSE',
                                    f"API returned success=false for {request.path}",
                                    'WARNING',
                                    {'message': json_data.get('message', 'No message')}
                                )
                    except:
                        pass
                
                return result
                
            except Exception as e:
                watchdog.log_exception(
                    exc_type=type(e).__name__,
                    exc_value=str(e),
                    exc_traceback=traceback.format_exception(type(e), e, e.__traceback__),
                    context=f'ROUTE_ERROR:{request.path}'
                )
                raise
        
        return wrapper
    return decorator
