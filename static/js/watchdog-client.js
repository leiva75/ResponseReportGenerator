/**
 * Watchdog Client - Frontend Monitoring System
 * 
 * Captures:
 * - JavaScript errors
 * - Unhandled promise rejections
 * - User actions (clicks, form submissions, navigation)
 * - Console errors and warnings
 * - Performance issues
 * - Network errors
 */

(function() {
    'use strict';
    
    const WatchdogClient = {
        enabled: true,
        logQueue: [],
        flushInterval: 5000,
        maxQueueSize: 50,
        endpoint: '/api/watchdog/log',
        sessionId: null,
        
        init: function() {
            this.sessionId = this.generateSessionId();
            this.installErrorHandlers();
            this.installActionTracking();
            this.installPerformanceMonitoring();
            this.startFlushTimer();
            this.log('CLIENT_INIT', 'Watchdog client initialized', { 
                sessionId: this.sessionId,
                userAgent: navigator.userAgent.substring(0, 100),
                url: window.location.href
            });
        },
        
        generateSessionId: function() {
            return 'sess_' + Date.now().toString(36) + '_' + Math.random().toString(36).substr(2, 9);
        },
        
        log: function(eventType, message, data) {
            if (!this.enabled) return;
            
            const logEntry = {
                timestamp: new Date().toISOString(),
                sessionId: this.sessionId,
                eventType: eventType,
                message: message,
                data: data || {},
                url: window.location.pathname
            };
            
            this.logQueue.push(logEntry);
            
            if (this.logQueue.length >= this.maxQueueSize) {
                this.flushLogs();
            }
        },
        
        flushLogs: function() {
            if (this.logQueue.length === 0) return;
            
            const logsToSend = this.logQueue.splice(0, this.maxQueueSize);
            
            if (navigator.sendBeacon) {
                navigator.sendBeacon(this.endpoint, JSON.stringify({ logs: logsToSend }));
            } else {
                fetch(this.endpoint, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ logs: logsToSend }),
                    keepalive: true
                }).catch(function() {});
            }
        },
        
        startFlushTimer: function() {
            const self = this;
            setInterval(function() {
                self.flushLogs();
            }, this.flushInterval);
            
            window.addEventListener('beforeunload', function() {
                self.log('PAGE_UNLOAD', 'User leaving page');
                self.flushLogs();
            });
            
            document.addEventListener('visibilitychange', function() {
                if (document.visibilityState === 'hidden') {
                    self.flushLogs();
                }
            });
        },
        
        installErrorHandlers: function() {
            const self = this;
            
            window.onerror = function(message, source, lineno, colno, error) {
                self.log('JS_ERROR', message, {
                    source: source,
                    line: lineno,
                    column: colno,
                    stack: error ? error.stack : null
                });
                return false;
            };
            
            window.addEventListener('unhandledrejection', function(event) {
                let reason = 'Unknown promise rejection';
                if (event.reason) {
                    reason = event.reason.message || event.reason.toString();
                }
                self.log('PROMISE_REJECTION', reason, {
                    stack: event.reason && event.reason.stack ? event.reason.stack : null
                });
            });
            
            const originalConsoleError = console.error;
            console.error = function() {
                const args = Array.prototype.slice.call(arguments);
                self.log('CONSOLE_ERROR', args.map(function(a) { 
                    return typeof a === 'object' ? JSON.stringify(a) : String(a);
                }).join(' '));
                originalConsoleError.apply(console, arguments);
            };
            
            const originalConsoleWarn = console.warn;
            console.warn = function() {
                const args = Array.prototype.slice.call(arguments);
                self.log('CONSOLE_WARN', args.map(function(a) { 
                    return typeof a === 'object' ? JSON.stringify(a) : String(a);
                }).join(' '));
                originalConsoleWarn.apply(console, arguments);
            };
        },
        
        installActionTracking: function() {
            const self = this;
            
            document.addEventListener('click', function(event) {
                const target = event.target;
                const tagName = target.tagName.toLowerCase();
                
                if (['button', 'a', 'input'].includes(tagName) || 
                    target.closest('button') || 
                    target.classList.contains('btn') ||
                    target.hasAttribute('data-action')) {
                    
                    let actionName = target.textContent ? target.textContent.trim().substring(0, 50) : '';
                    if (target.id) actionName = '#' + target.id;
                    if (target.name) actionName = target.name;
                    if (target.getAttribute('data-action')) actionName = target.getAttribute('data-action');
                    
                    self.log('USER_CLICK', actionName, {
                        tag: tagName,
                        id: target.id || null,
                        class: target.className ? target.className.substring(0, 100) : null
                    });
                }
            }, { passive: true });
            
            document.addEventListener('submit', function(event) {
                const form = event.target;
                self.log('FORM_SUBMIT', 'Form submitted', {
                    formId: form.id || null,
                    formAction: form.action ? form.action.substring(0, 100) : null,
                    method: form.method
                });
            }, { passive: true });
            
            window.addEventListener('popstate', function() {
                self.log('NAVIGATION', 'Browser navigation', {
                    newUrl: window.location.pathname
                });
            });
            
            const originalPushState = history.pushState;
            history.pushState = function() {
                self.log('NAVIGATION', 'pushState navigation', {
                    newUrl: arguments[2]
                });
                return originalPushState.apply(history, arguments);
            };
        },
        
        installPerformanceMonitoring: function() {
            const self = this;
            
            if (window.PerformanceObserver) {
                try {
                    const longTaskObserver = new PerformanceObserver(function(list) {
                        list.getEntries().forEach(function(entry) {
                            if (entry.duration > 100) {
                                self.log('LONG_TASK', 'Long task detected', {
                                    duration: Math.round(entry.duration),
                                    startTime: Math.round(entry.startTime)
                                });
                            }
                        });
                    });
                    longTaskObserver.observe({ entryTypes: ['longtask'] });
                } catch (e) {}
                
                try {
                    const resourceObserver = new PerformanceObserver(function(list) {
                        list.getEntries().forEach(function(entry) {
                            if (entry.duration > 3000) {
                                self.log('SLOW_RESOURCE', 'Slow resource load', {
                                    name: entry.name.substring(0, 100),
                                    duration: Math.round(entry.duration),
                                    type: entry.initiatorType
                                });
                            }
                        });
                    });
                    resourceObserver.observe({ entryTypes: ['resource'] });
                } catch (e) {}
            }
            
            window.addEventListener('load', function() {
                setTimeout(function() {
                    if (window.performance && window.performance.timing) {
                        const timing = window.performance.timing;
                        const loadTime = timing.loadEventEnd - timing.navigationStart;
                        const domReady = timing.domContentLoadedEventEnd - timing.navigationStart;
                        
                        self.log('PAGE_LOAD', 'Page load complete', {
                            totalLoadTime: loadTime,
                            domReadyTime: domReady,
                            url: window.location.pathname
                        });
                        
                        if (loadTime > 5000) {
                            self.log('SLOW_PAGE_LOAD', 'Page load exceeded 5 seconds', {
                                loadTime: loadTime
                            });
                        }
                    }
                }, 100);
            });
            
            const originalFetch = window.fetch;
            window.fetch = function(url, options) {
                const startTime = Date.now();
                const urlStr = typeof url === 'string' ? url : url.toString();
                
                return originalFetch.apply(window, arguments)
                    .then(function(response) {
                        const duration = Date.now() - startTime;
                        
                        if (duration > 5000) {
                            self.log('SLOW_FETCH', 'Slow fetch request', {
                                url: urlStr.substring(0, 100),
                                duration: duration,
                                status: response.status
                            });
                        }
                        
                        if (!response.ok) {
                            self.log('FETCH_ERROR', 'Fetch returned error status', {
                                url: urlStr.substring(0, 100),
                                status: response.status,
                                statusText: response.statusText
                            });
                        }
                        
                        return response;
                    })
                    .catch(function(error) {
                        self.log('NETWORK_ERROR', 'Fetch failed', {
                            url: urlStr.substring(0, 100),
                            error: error.message
                        });
                        throw error;
                    });
            };
        },
        
        trackCustomEvent: function(eventName, data) {
            this.log('CUSTOM_EVENT', eventName, data);
        },
        
        trackError: function(message, context) {
            this.log('MANUAL_ERROR', message, context);
        }
    };
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            WatchdogClient.init();
        });
    } else {
        WatchdogClient.init();
    }
    
    window.WatchdogClient = WatchdogClient;
    
})();
