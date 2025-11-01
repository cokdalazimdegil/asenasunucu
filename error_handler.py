"""
Enhanced Error Handling and Recovery System
Provides robust error management with recovery mechanisms
"""

import logging
import sqlite3
from typing import Optional, Dict, Any, Callable
from datetime import datetime, timedelta
from functools import wraps
import traceback

logger = logging.getLogger(__name__)


class ErrorHandler:
    """Centralized error handling with logging and recovery"""
    
    def __init__(self, db_path: str = 'asena_memory.db'):
        self.db_path = db_path
        self.error_log_table = 'error_logs'
        self.init_error_table()
    
    def init_error_table(self):
        """Initialize error logging table"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute(f'''
                    CREATE TABLE IF NOT EXISTS {self.error_log_table} (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        error_type TEXT NOT NULL,
                        error_message TEXT NOT NULL,
                        function_name TEXT,
                        user_name TEXT,
                        traceback_text TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        severity TEXT DEFAULT 'INFO',
                        resolved BOOLEAN DEFAULT 0
                    )
                ''')
                
                cursor.execute(f'''
                    CREATE INDEX IF NOT EXISTS idx_error_timestamp 
                    ON {self.error_log_table}(timestamp)
                ''')
                
                conn.commit()
                logger.info("Error log table initialized")
        except Exception as e:
            logger.error(f"Error initializing error table: {e}")
    
    def log_error(self, error_type: str, error_message: str, 
                 function_name: Optional[str] = None,
                 user_name: Optional[str] = None,
                 severity: str = 'ERROR',
                 traceback_text: Optional[str] = None) -> None:
        """Log an error to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute(f'''
                    INSERT INTO {self.error_log_table}
                    (error_type, error_message, function_name, user_name, severity, traceback_text)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (error_type, error_message, function_name, user_name, severity, traceback_text))
                
                conn.commit()
                
                # Also log to console
                log_level = getattr(logging, severity, logging.ERROR)
                logger.log(log_level, f"{error_type}: {error_message}")
        except Exception as e:
            logger.error(f"Failed to log error: {e}")
    
    def get_recent_errors(self, limit: int = 10, unresolved_only: bool = False) -> list:
        """Get recent errors from log"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                query = f'SELECT * FROM {self.error_log_table}'
                params = []
                
                if unresolved_only:
                    query += ' WHERE resolved = 0'
                
                query += ' ORDER BY timestamp DESC LIMIT ?'
                params.append(limit)
                
                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get error logs: {e}")
            return []
    
    def resolve_error(self, error_id: int) -> bool:
        """Mark error as resolved"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute(f'''
                    UPDATE {self.error_log_table}
                    SET resolved = 1
                    WHERE id = ?
                ''', (error_id,))
                
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to resolve error: {e}")
            return False
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute(f'''
                    SELECT 
                        COUNT(*) as total_errors,
                        SUM(CASE WHEN resolved = 0 THEN 1 ELSE 0 END) as unresolved_errors,
                        MAX(timestamp) as last_error_time
                    FROM {self.error_log_table}
                ''')
                
                result = cursor.fetchone()
                
                return {
                    'total_errors': result[0] or 0,
                    'unresolved_errors': result[1] or 0,
                    'last_error_time': result[2]
                }
        except Exception as e:
            logger.error(f"Failed to get error stats: {e}")
            return {'total_errors': 0, 'unresolved_errors': 0, 'last_error_time': None}


# Global error handler
_error_handler = None


def get_error_handler() -> ErrorHandler:
    """Get or create global error handler"""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler


def safe_operation(fallback_return: Any = None, log_errors: bool = True) -> Callable:
    """
    Decorator for safe operation with error handling
    
    Args:
        fallback_return: Value to return on error
        log_errors: Whether to log errors
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_handler = get_error_handler()
                
                if log_errors:
                    error_handler.log_error(
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


def validate_input(input_dict: Dict[str, Any], required_keys: list) -> Optional[Dict[str, Any]]:
    """
    Validate input dictionary for required keys
    
    Returns:
        Validated dict or None
    """
    missing_keys = [k for k in required_keys if k not in input_dict]
    
    if missing_keys:
        logger.warning(f"Missing required keys: {missing_keys}")
        return None
    
    return input_dict


class RateLimiter:
    """Simple rate limiter for API calls"""
    
    def __init__(self, max_calls: int = 10, time_window_seconds: int = 60):
        self.max_calls = max_calls
        self.time_window = timedelta(seconds=time_window_seconds)
        self.call_times: Dict[str, list] = {}
    
    def is_allowed(self, identifier: str) -> bool:
        """Check if operation is allowed for identifier"""
        now = datetime.now()
        
        if identifier not in self.call_times:
            self.call_times[identifier] = []
        
        # Remove old timestamps outside the window
        self.call_times[identifier] = [
            t for t in self.call_times[identifier]
            if now - t < self.time_window
        ]
        
        if len(self.call_times[identifier]) >= self.max_calls:
            return False
        
        self.call_times[identifier].append(now)
        return True
    
    def get_remaining_calls(self, identifier: str) -> int:
        """Get remaining calls for identifier"""
        if identifier not in self.call_times:
            return self.max_calls
        
        now = datetime.now()
        recent_calls = [
            t for t in self.call_times[identifier]
            if now - t < self.time_window
        ]
        
        return max(0, self.max_calls - len(recent_calls))


# Global rate limiter
api_rate_limiter = RateLimiter(max_calls=100, time_window_seconds=3600)  # 100 calls per hour
