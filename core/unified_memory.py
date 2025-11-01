"""
Unified Memory Management System
Consolidates memory_manager.py, intelligent_memory.py, and vector_memory.py
Single source of truth for all memory operations
"""

import sqlite3
import json
import hashlib
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import deque, defaultdict
from contextlib import contextmanager
import queue
import threading

logger = logging.getLogger(__name__)


class DatabasePool:
    """Connection pooling for better performance"""
    def __init__(self, db_path: str, max_connections: int = 5):
        self.db_path = db_path
        self.pool = queue.Queue(maxsize=max_connections)
        self.lock = threading.Lock()
        
        for _ in range(max_connections):
            conn = sqlite3.connect(db_path, check_same_thread=False)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=30000")
            conn.row_factory = sqlite3.Row
            self.pool.put(conn)
    
    @contextmanager
    def get_connection(self):
        """Get connection from pool"""
        conn = self.pool.get()
        try:
            yield conn
        finally:
            self.pool.put(conn)


class UnifiedMemoryManager:
    """Single unified memory system combining all previous implementations"""
    
    def __init__(self, db_path: str = 'asena_memory.db', max_short_term: int = 10):
        self.db_path = db_path
        self.max_short_term = max_short_term
        
        # Connection pool for performance
        self.db_pool = DatabasePool(db_path, max_connections=5)
        
        # Short-term memory (per-session)
        self.short_term_memory: Dict[str, deque] = {}
        
        # Memory priority tracking
        self.memory_priority = defaultdict(int)
        
        # Initialize database
        self._init_database()
    
    def _init_database(self):
        """Initialize unified database schema"""
        with self.db_pool.get_connection() as conn:
            cursor = conn.cursor()
            
            # Unified memories table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_name TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    importance INTEGER DEFAULT 5,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    access_count INTEGER DEFAULT 1,
                    context_hash TEXT,
                    is_permanent BOOLEAN DEFAULT 0,
                    expires_at TIMESTAMP,
                    metadata TEXT,
                    UNIQUE(user_name, context_hash)
                )
            ''')
            
            # Conversation history
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_name TEXT NOT NULL,
                    user_message TEXT NOT NULL,
                    assistant_response TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    context_hash TEXT,
                    sentiment TEXT,
                    metadata TEXT
                )
            ''')
            
            # Optimized indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_memories_user_type ON memories(user_name, memory_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_memories_hash ON memories(context_hash)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_memories_accessed ON memories(last_accessed DESC)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_conv_user_time ON conversation_history(user_name, timestamp DESC)')
            
            conn.commit()
            logger.info("✅ Unified memory database initialized")
    
    def _generate_hash(self, user_name: str, content: str) -> str:
        """Generate hash for deduplication"""
        combined = f"{user_name}:{content.lower().strip()}"
        return hashlib.sha256(combined.encode('utf-8')).hexdigest()
    
    # ==================== MEMORY OPERATIONS ====================
    
    def add_memory(
        self,
        user_name: str,
        memory_type: str,
        content: str,
        importance: int = 5,
        is_permanent: bool = False,
        expires_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[int]:
        """
        Add memory with automatic deduplication
        
        Returns:
            Memory ID
        """
        if not user_name or not content:
            return None
        
        context_hash = self._generate_hash(user_name, content)
        metadata_json = json.dumps(metadata) if metadata else None
        expires_str = expires_at.isoformat() if expires_at else None
        
        with self.db_pool.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check for existing memory
            cursor.execute('''
                SELECT id, access_count FROM memories 
                WHERE user_name = ? AND context_hash = ?
            ''', (user_name, context_hash))
            
            existing = cursor.fetchone()
            
            if existing:
                # Update existing
                memory_id = existing[0]
                cursor.execute('''
                    UPDATE memories 
                    SET updated_at = CURRENT_TIMESTAMP,
                        last_accessed = CURRENT_TIMESTAMP,
                        access_count = access_count + 1,
                        importance = ?,
                        is_permanent = ?
                    WHERE id = ?
                ''', (importance, is_permanent, memory_id))
                logger.debug(f"Updated existing memory ID: {memory_id}")
            else:
                # Insert new
                cursor.execute('''
                    INSERT INTO memories 
                    (user_name, memory_type, content, importance, is_permanent, 
                     context_hash, expires_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (user_name, memory_type, content, importance, is_permanent, 
                      context_hash, expires_str, metadata_json))
                memory_id = cursor.lastrowid
                logger.info(f"Added new memory ID: {memory_id} for {user_name}")
            
            conn.commit()
            return memory_id
    
    def get_memories(
        self,
        user_name: str,
        memory_type: Optional[str] = None,
        limit: int = 50,
        include_expired: bool = False
    ) -> List[Dict[str, Any]]:
        """Get memories with optional filtering"""
        with self.db_pool.get_connection() as conn:
            cursor = conn.cursor()
            
            query = 'SELECT * FROM memories WHERE user_name = ?'
            params: List[Any] = [user_name]
            
            if memory_type:
                query += ' AND memory_type = ?'
                params.append(memory_type)
            
            if not include_expired:
                query += ' AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)'
            
            query += ' ORDER BY importance DESC, last_accessed DESC LIMIT ?'
            params.append(limit)
            
            cursor.execute(query, params)
            
            memories = []
            for row in cursor.fetchall():
                memory = dict(row)
                if memory.get('metadata'):
                    try:
                        memory['metadata'] = json.loads(memory['metadata'])
                    except (json.JSONDecodeError, TypeError):
                        memory['metadata'] = {}
                memories.append(memory)
            
            return memories
    
    def get_contextual_memories(
        self,
        user_name: str,
        current_message: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get contextually relevant memories using keyword matching"""
        all_memories = self.get_memories(user_name, limit=100)
        
        # Extract keywords
        keywords = self._extract_keywords(current_message)
        
        if not keywords:
            return all_memories[:limit]
        
        # Score memories by relevance
        scored_memories = []
        for memory in all_memories:
            score = self._calculate_relevance(memory, keywords)
            scored_memories.append((score, memory))
        
        # Sort by score descending
        scored_memories.sort(key=lambda x: x[0], reverse=True)
        
        return [mem for score, mem in scored_memories[:limit]]
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract meaningful keywords from text"""
        import re
        
        if not text:
            return []
        
        # Turkish stop words
        stop_words = {
            've', 'veya', 'ama', 'ile', 'bir', 'bu', 'şu', 'o', 
            'de', 'da', 'ki', 'mi', 'mı', 'mu', 'mü', 'ise', 'değil'
        }
        
        # Clean and tokenize
        text = re.sub(r'[^\w\s]', '', text.lower())
        words = [w for w in text.split() if len(w) > 2 and w not in stop_words]
        
        return list(set(words))
    
    def _calculate_relevance(self, memory: Dict[str, Any], keywords: List[str]) -> float:
        """Calculate relevance score for a memory"""
        score = 0.0
        content = str(memory.get('content', '')).lower()
        
        # Keyword matching
        for keyword in keywords:
            if keyword in content:
                score += 3.0
                if content.startswith(keyword):
                    score += 1.5
        
        # Importance bonus
        importance = float(memory.get('importance', 5))
        score += (importance / 10.0) * 2
        
        # Recency bonus
        updated_at = memory.get('updated_at')
        if updated_at:
            try:
                if isinstance(updated_at, str):
                    updated_at = datetime.fromisoformat(updated_at)
                days_old = (datetime.now() - updated_at).days
                if days_old <= 7:
                    score += 2.0
                elif days_old <= 30:
                    score += 1.0
            except (ValueError, TypeError):
                pass
        
        # Access frequency bonus
        access_count = int(memory.get('access_count', 0))
        score += min(3.0, access_count * 0.5)
        
        return score
    
    def delete_memory(
        self,
        user_name: str,
        memory_type: Optional[str] = None,
        pattern: Optional[str] = None
    ) -> int:
        """Delete memories matching criteria"""
        with self.db_pool.get_connection() as conn:
            cursor = conn.cursor()
            
            query = 'DELETE FROM memories WHERE user_name = ?'
            params: List[Any] = [user_name]
            
            if memory_type:
                query += ' AND memory_type = ?'
                params.append(memory_type)
            
            if pattern:
                query += ' AND content LIKE ?'
                params.append(f'%{pattern}%')
            
            cursor.execute(query, params)
            conn.commit()
            
            deleted = cursor.rowcount
            if deleted > 0:
                logger.info(f"Deleted {deleted} memories for {user_name}")
            
            return deleted
    
    # ==================== CONVERSATION OPERATIONS ====================
    
    def add_conversation(
        self,
        user_name: str,
        user_message: str,
        assistant_response: str,
        sentiment: Optional[Dict[str, Any]] = None
    ) -> Optional[int]:
        """Add conversation to history"""
        context_hash = self._generate_hash(user_name, user_message)
        sentiment_json = json.dumps(sentiment) if sentiment else None
        
        with self.db_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO conversation_history 
                (user_name, user_message, assistant_response, context_hash, sentiment)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_name, user_message, assistant_response, context_hash, sentiment_json))
            
            conn.commit()
            return cursor.lastrowid
    
    def get_recent_conversations(
        self,
        user_name: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Get recent conversation history"""
        with self.db_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM conversation_history 
                WHERE user_name = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (user_name, limit))
            
            conversations = []
            for row in cursor.fetchall():
                conv = dict(row)
                if conv.get('sentiment'):
                    try:
                        conv['sentiment'] = json.loads(conv['sentiment'])
                    except (json.JSONDecodeError, TypeError):
                        conv['sentiment'] = None
                conversations.append(conv)
            
            return list(reversed(conversations))  # Oldest first
    
    # ==================== SHORT-TERM MEMORY ====================
    
    def add_short_term(self, user_name: str, content: Dict[str, Any]):
        """Add to short-term session memory"""
        if user_name not in self.short_term_memory:
            self.short_term_memory[user_name] = deque(maxlen=self.max_short_term)
        
        self.short_term_memory[user_name].append({
            'timestamp': datetime.now().isoformat(),
            'content': content
        })
    
    def get_short_term(self, user_name: str) -> List[Dict[str, Any]]:
        """Get short-term memories"""
        return list(self.short_term_memory.get(user_name, []))
    
    def clear_short_term(self, user_name: str):
        """Clear short-term memory for user"""
        if user_name in self.short_term_memory:
            self.short_term_memory[user_name].clear()
    
    # ==================== CONTEXT BUILDING ====================
    
    def build_context(
        self,
        user_name: str,
        current_message: str,
        max_tokens: int = 1000
    ) -> str:
        """Build unified context for AI"""
        context_parts = []
        
        # Recent conversations
        recent = self.get_recent_conversations(user_name, limit=3)
        if recent:
            context_parts.append("--- Recent Conversation ---")
            for conv in recent:
                context_parts.append(f"{user_name}: {conv['user_message']}")
                context_parts.append(f"Asena: {conv['assistant_response']}")
        
        # Relevant memories
        memories = self.get_contextual_memories(user_name, current_message, limit=5)
        if memories:
            context_parts.append("\n--- Relevant Memories ---")
            for mem in memories:
                context_parts.append(f"- {mem['content']}")
        
        # Short-term context
        short_term = self.get_short_term(user_name)
        if short_term:
            context_parts.append("\n--- Current Session ---")
            for item in short_term[-3:]:  # Last 3 items
                context_parts.append(f"- {item.get('content', '')}")
        
        # Join and truncate
        context = "\n".join(context_parts)
        if len(context) > max_tokens * 4:
            context = context[:max_tokens * 4] + "..."
        
        return context
    
    # ==================== CLEANUP ====================
    
    def cleanup_expired(self) -> int:
        """Remove expired memories"""
        with self.db_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM memories 
                WHERE expires_at IS NOT NULL 
                AND expires_at < CURRENT_TIMESTAMP
            ''')
            conn.commit()
            
            deleted = cursor.rowcount
            if deleted > 0:
                logger.info(f"Cleaned up {deleted} expired memories")
            return deleted


# Singleton instance
_unified_memory = None


def get_unified_memory() -> UnifiedMemoryManager:
    """Get global unified memory instance"""
    global _unified_memory
    if _unified_memory is None:
        _unified_memory = UnifiedMemoryManager()
    return _unified_memory
