"""
Unified Monitoring, Error Handling, and Rate Limiting
Consolidates error_handler.py with enhanced monitoring and rate limiting
"""

import logging
import sqlite3
import traceback
import time
from typing import Optional, Dict, Any, Callable
from datetime import datetime, timedelta
from functools import wraps
from collections import deque, defaultdict
import threading

logger = logging.getLogger(__name__)


class RateLimiter:
    """Advanced rate limiter with multiple time windows"""
    
    def __init__(self, max_calls: int = 100, window_seconds: int = 3600):
        self.max_calls = max_calls
        self.window = timedelta(seconds=window_seconds)
        self.calls: Dict[str, deque] = defaultdict(lambda: deque())
        self.lock = threading.Lock()
    
    def can_request(self, identifier: str) -> bool:
        """Check if request is allowed"""
        with self.lock:
            now = datetime.now()
            
            # Remove old calls outside window
            while self.calls[identifier] and now - self.calls[identifier][0] > self.window:
                self.calls[identifier].popleft()
            
            # Check limit
            if len(self.calls[identifier]) >= self.max_calls:
                return False
            
            self.calls[identifier].append(now)
            return True
    
    def get_remaining(self, identifier: str) -> int:
        """Get remaining calls in current window"""
        with self.lock:
            now = datetime.now()
            
            # Clean old calls
            while self.calls[identifier] and now - self.calls[identifier][0] > self.window:
                self.calls[identifier].popleft()
            
            return max(0, self.max_calls - len(self.calls[identifier]))
    
    def get_reset_time(self, identifier: str) -> Optional[datetime]:
        """Get when the rate limit resets"""
        with self.lock:
            if not self.calls[identifier]:
                return None
            return self.calls[identifier][0] + self.window


class PerformanceMonitor:
    """Track performance metrics"""
    
    def __init__(self):
        self.metrics: Dict[str, list] = defaultdict(list)
        self.lock = threading.Lock()
    
    def record(self, operation: str, duration: float):
        """Record operation duration"""
        with self.lock:
            self.metrics[operation].append({
                'duration': duration,
                'timestamp': datetime.now()
            })
            
            # Keep only last 1000 entries per operation
            if len(self.metrics[operation]) > 1000:
                self.metrics[operation] = self.metrics[operation][-1000:]
            
            # Warn on slow operations
            if duration > 1.0:
                logger.warning(f"⚠️ Slow operation: {operation} took {duration:.2f}s")
    
    def get_stats(self, operation: Optional[str] = None) -> Dict[str, Any]:
        """Get performance statistics"""
        with self.lock:
            if operation:
                if operation not in self.metrics:
                    return {}
                
                durations = [m['duration'] for m in self.metrics[operation]]
                return {
                    'operation': operation,
                    'count': len(durations),
                    'avg': sum(durations) / len(durations) if durations else 0,
                    'min': min(durations) if durations else 0,
                    'max': max(durations) if durations else 0
                }
            
            # All operations
            stats = {}
            for op, data in self.metrics.items():
                durations = [m['duration'] for m in data]
                stats[op] = {
                    'count': len(durations),
                    'avg': sum(durations) / len(durations) if durations else 0,
                    'max': max(durations) if durations else 0
                }
            return stats


class UnifiedMonitoring:
    """Centralized monitoring and error handling"""
    
    def __init__(self, db_path: str = 'asena_memory.db'):
        self.db_path = db_path
        self.performance = PerformanceMonitor()
        self._init_database()
    
    def _init_database(self):
        """Initialize error logging table"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS error_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        error_type TEXT NOT NULL,
                        error_message TEXT NOT NULL,
                        function_name TEXT,
                        user_name TEXT,
                        traceback_text TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        severity TEXT DEFAULT 'ERROR',
                        resolved BOOLEAN DEFAULT 0
                    )
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_error_timestamp 
                    ON error_logs(timestamp DESC)
                ''')
                
                conn.commit()
                logger.info("✅ Error logging initialized")
        except Exception as e:
            logger.error(f"Failed to init error logging: {e}")
    
    def log_error(
        self,
        error_type: str,
        error_message: str,
        function_name: Optional[str] = None,
        user_name: Optional[str] = None,
        severity: str = 'ERROR',
        traceback_text: Optional[str] = None
    ):
        """Log error to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO error_logs
                    (error_type, error_message, function_name, user_name, severity, traceback_text)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (error_type, error_message, function_name, user_name, severity, traceback_text))
                conn.commit()
            
            # Also log to console
            log_level = getattr(logging, severity, logging.ERROR)
            logger.log(log_level, f"{error_type}: {error_message}")
        except Exception as e:
            logger.error(f"Failed to log error: {e}")
    
    def get_recent_errors(self, limit: int = 10) -> list:
        """Get recent errors"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM error_logs 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (limit,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get errors: {e}")
            return []
    
    def measure(self, operation: str):
        """Context manager for measuring performance"""
        class MeasureContext:
            def __init__(ctx_self, monitor, op):
                ctx_self.monitor = monitor
                ctx_self.operation = op
                ctx_self.start = None
            
            def __enter__(ctx_self):
                ctx_self.start = time.time()
                return ctx_self
            
            def __exit__(ctx_self, *args):
                if ctx_self.start is not None:
                    duration = time.time() - ctx_self.start
                    ctx_self.monitor.performance.record(ctx_self.operation, duration)
        
        return MeasureContext(self, operation)


def safe_operation(fallback_return: Any = None, log_errors: bool = True) -> Callable:
    """Decorator for safe operations with error handling"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_errors:
                    monitor = get_monitoring()
                    monitor.log_error(
                        error_type=type(e).__name__,
                        error_message=str(e),
                        function_name=func.__name__,
                        severity='ERROR',
                        traceback_text=traceback.format_exc()
                    )
                logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
                return fallback_return
        return wrapper
    return decorator


# Global instances
_monitoring = None
_groq_rate_limiter = None


def get_monitoring() -> UnifiedMonitoring:
    """Get global monitoring instance"""
    global _monitoring
    if _monitoring is None:
        _monitoring = UnifiedMonitoring()
    return _monitoring


def get_groq_rate_limiter() -> RateLimiter:
    """Get Groq API rate limiter (100 requests/hour)"""
    global _groq_rate_limiter
    if _groq_rate_limiter is None:
        _groq_rate_limiter = RateLimiter(max_calls=100, window_seconds=3600)
    return _groq_rate_limiter
