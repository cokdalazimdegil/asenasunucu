"""
Response Caching System
Optimizes performance by caching similar responses and reducing API calls
"""

import hashlib
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class ResponseCache:
    """Manages cached responses to improve performance and reduce API usage"""
    
    def __init__(self, db_path: str = 'asena_memory.db', cache_ttl_hours: int = 24):
        """
        Initialize ResponseCache
        
        Args:
            db_path: Path to SQLite database
            cache_ttl_hours: Cache time-to-live in hours
        """
        self.db_path = db_path
        self.cache_ttl = timedelta(hours=cache_ttl_hours)
        self._init_database()
    
    def _init_database(self):
        """Initialize cache table"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS response_cache (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        query_hash TEXT UNIQUE NOT NULL,
                        user_name TEXT NOT NULL,
                        query_text TEXT NOT NULL,
                        response_text TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        access_count INTEGER DEFAULT 1,
                        confidence_score REAL DEFAULT 0.8
                    )
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_cache_user 
                    ON response_cache(user_name, created_at)
                ''')
                
                conn.commit()
                logger.info("Response cache table initialized")
        except Exception as e:
            logger.error(f"Cache database initialization error: {e}")
    
    def _generate_query_hash(self, user_name: str, query: str) -> str:
        """Generate hash for query"""
        combined = f"{user_name}:{query.lower().strip()}"
        return hashlib.sha256(combined.encode('utf-8')).hexdigest()
    
    def get_cached_response(self, user_name: str, query: str) -> Optional[Dict[str, Any]]:
        """
        Get cached response if available and not expired
        
        Args:
            user_name: User identifier
            query: User query text
            
        Returns:
            Cached response dict or None
        """
        query_hash = self._generate_query_hash(user_name, query)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM response_cache 
                    WHERE query_hash = ? 
                    AND datetime(created_at, '+' || ? || ' hours') > datetime('now')
                ''', (query_hash, self.cache_ttl.total_seconds() / 3600))
                
                row = cursor.fetchone()
                
                if row:
                    # Update access metrics
                    cursor.execute('''
                        UPDATE response_cache 
                        SET last_accessed = CURRENT_TIMESTAMP, 
                            access_count = access_count + 1
                        WHERE query_hash = ?
                    ''', (query_hash,))
                    conn.commit()
                    
                    return {
                        'response': row['response_text'],
                        'confidence': row['confidence_score'],
                        'cached': True,
                        'access_count': row['access_count']
                    }
        except Exception as e:
            logger.error(f"Cache retrieval error: {e}")
        
        return None
    
    def store_response(self, user_name: str, query: str, response: str, 
                      confidence: float = 0.8) -> bool:
        """
        Store response in cache
        
        Args:
            user_name: User identifier
            query: User query
            response: Generated response
            confidence: Confidence score (0-1)
            
        Returns:
            Success status
        """
        query_hash = self._generate_query_hash(user_name, query)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO response_cache 
                    (query_hash, user_name, query_text, response_text, confidence_score)
                    VALUES (?, ?, ?, ?, ?)
                ''', (query_hash, user_name, query, response, confidence))
                
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Cache storage error: {e}")
            return False
    
    def clear_old_cache(self, days: int = 7) -> int:
        """
        Clear cached responses older than specified days
        
        Args:
            days: Age in days
            
        Returns:
            Number of rows deleted
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    DELETE FROM response_cache 
                    WHERE datetime(created_at, '+' || ? || ' days') < datetime('now')
                ''', (days,))
                
                conn.commit()
                deleted = cursor.rowcount
                
                if deleted > 0:
                    logger.info(f"Cleared {deleted} old cache entries")
                
                return deleted
        except Exception as e:
            logger.error(f"Cache cleanup error: {e}")
            return 0
    
    def get_cache_stats(self, user_name: Optional[str] = None) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = "SELECT COUNT(*) as total, AVG(access_count) as avg_access, AVG(confidence_score) as avg_confidence FROM response_cache"
                params = []
                
                if user_name:
                    query += " WHERE user_name = ?"
                    params.append(user_name)
                
                cursor.execute(query, params)
                row = cursor.fetchone()
                
                return {
                    'total_cached': row[0],
                    'avg_access_count': row[1] or 0,
                    'avg_confidence': row[2] or 0
                }
        except Exception as e:
            logger.error(f"Cache stats error: {e}")
            return {'total_cached': 0, 'avg_access_count': 0, 'avg_confidence': 0}


# Global cache instance
response_cache = ResponseCache()


def get_response_cache() -> ResponseCache:
    """Get global response cache instance"""
    return response_cache
