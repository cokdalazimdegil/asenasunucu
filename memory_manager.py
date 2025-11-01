"""
Enhanced Memory Management System
Handles both short-term (conversation context) and long-term (persistent) memory
"""
import json
import sqlite3
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import logging
from collections import deque
import hashlib
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

class MemoryManager:
    def __init__(self, max_short_term_memories: int = 10, db_path: str = 'asena_memory.db'):
        """
        Initialize the MemoryManager.
        
        Args:
            max_short_term_memories: Maximum number of recent memories to keep in short-term memory
            db_path: Path to the SQLite database for long-term storage
        """
        self.max_short_term_memories = max_short_term_memories
        self.db_path = db_path
        
        # Short-term memory (conversation context)
        self.short_term_memory = {}
        
        # Long-term memory (persistent storage)
        self._init_database()
    
    def _init_database(self):
        """Initialize the database tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create conversation history table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_name TEXT NOT NULL,
                user_message TEXT NOT NULL,
                assistant_response TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                context_hash TEXT
            )
            ''')
            
            # Create memory table for long-term storage
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_name TEXT NOT NULL,
                memory_type TEXT NOT NULL,
                content TEXT NOT NULL,
                importance INTEGER DEFAULT 5,  -- 1-10 scale
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_accessed DATETIME DEFAULT CURRENT_TIMESTAMP,
                access_count INTEGER DEFAULT 1,
                context_hash TEXT,
                is_permanent BOOLEAN DEFAULT 0
            )
            ''')
            
            # Create index for faster lookups
            cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_memories_user_type 
            ON memories(user_name, memory_type)
            ''')
            
            conn.commit()
    
    def _generate_context_hash(self, user_name: str, message: str) -> str:
        """Generate a hash for the conversation context."""
        context_str = f"{user_name}:{message}"
        return hashlib.md5(context_str.encode('utf-8')).hexdigest()
    
    def add_conversation(self, user_name: str, user_message: str, assistant_response: str) -> Optional[int]:
        """
        Add a conversation to the history.
        
        Args:
            user_name: Name of the user
            user_message: The message from the user
            assistant_response: The response from the assistant
            
        Returns:
            Optional[int]: The ID of the inserted conversation
        """
        context_hash = self._generate_context_hash(user_name, user_message)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
            INSERT INTO conversation_history 
            (user_name, user_message, assistant_response, context_hash)
            VALUES (?, ?, ?, ?)
            ''', (user_name, user_message, assistant_response, context_hash))
            
            conn.commit()
            return cursor.lastrowid
    
    def get_recent_conversations(self, user_name: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get recent conversations for a user.
        
        Args:
            user_name: Name of the user
            limit: Maximum number of conversations to return
            
        Returns:
            List of conversation dictionaries
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT * FROM conversation_history 
            WHERE user_name = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
            ''', (user_name, limit))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def add_memory(
        self,
        user_name: str,
        memory_type: str,
        content: str,
        importance: int = 5,
        is_permanent: bool = False
    ) -> Optional[int]:
        """
        Add a memory to long-term storage.
        
        Args:
            user_name: Name of the user
            memory_type: Type/category of the memory
            content: The content to remember
            importance: Importance level (1-10)
            is_permanent: Whether this memory should be permanent
            
        Returns:
            Optional[int]: The ID of the inserted memory
        """
        context_hash = self._generate_context_hash(user_name, content)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Check if a similar memory already exists
            cursor.execute('''
            SELECT id, access_count FROM memories 
            WHERE user_name = ? AND memory_type = ? AND context_hash = ?
            ''', (user_name, memory_type, context_hash))
            
            existing = cursor.fetchone()
            
            if existing:
                # Update existing memory
                memory_id, access_count = existing
                cursor.execute('''
                UPDATE memories 
                SET last_accessed = CURRENT_TIMESTAMP, 
                    access_count = access_count + 1,
                    is_permanent = ?
                WHERE id = ?
                ''', (is_permanent, memory_id))
                return memory_id
            else:
                # Insert new memory
                cursor.execute('''
                INSERT INTO memories 
                (user_name, memory_type, content, importance, is_permanent, context_hash)
                VALUES (?, ?, ?, ?, ?, ?)
                ''', (user_name, memory_type, content, importance, is_permanent, context_hash))
                
                conn.commit()
                return cursor.lastrowid
    
    def delete_memory(self, user_name: str, memory_type: str, pattern: Optional[str] = None) -> int:
        """
        Delete memory for a user (when they say "unut"/forget).
        Follows: "Kalıcı hafızadaki bilgiler, kullanıcı 'unut' dediğinde silinir."
        
        Args:
            user_name: Name of the user
            memory_type: Type of memory to delete
            pattern: Optional pattern to match in content (e.g., 'Lina', 'alerjisi var')
            
        Returns:
            Number of rows deleted
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if pattern:
                # Delete memories matching pattern
                cursor.execute('''
                DELETE FROM memories 
                WHERE user_name = ? AND memory_type = ? AND content LIKE ?
                ''', (user_name, memory_type, f'%{pattern}%'))
            else:
                # Delete all memories of this type
                cursor.execute('''
                DELETE FROM memories 
                WHERE user_name = ? AND memory_type = ?
                ''', (user_name, memory_type))
            
            conn.commit()
            deleted_count = cursor.rowcount
            
            if deleted_count > 0:
                logging.info(f"Silindi: {user_name} - {memory_type} ({deleted_count} kayıt) - Pattern: {pattern}")
            
            return deleted_count
    
    def update_memory(self, user_name: str, memory_type: str, old_content: str, new_content: str) -> bool:
        """
        Update an existing memory (when user provides corrected or new information).
        Follows: "Kalıcı hafızadaki bilgiler oturumlar arasında korunur. Eski kayıt işaretlenir veya silinir."
        
        Args:
            user_name: Name of the user
            memory_type: Type of memory
            old_content: Content to search for
            new_content: New content to replace with
            
        Returns:
            True if updated, False otherwise
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Check if old memory exists
            cursor.execute('''
            SELECT id FROM memories 
            WHERE user_name = ? AND memory_type = ? AND content LIKE ?
            ''', (user_name, memory_type, f'%{old_content}%'))
            
            existing = cursor.fetchone()
            
            if existing:
                # Update with new content
                cursor.execute('''
                UPDATE memories 
                SET content = ?, last_accessed = CURRENT_TIMESTAMP
                WHERE id = ?
                ''', (new_content, existing[0]))
                
                conn.commit()
                logging.info(f"Güncellendi: {user_name} - {memory_type}")
                return True
            
            return False
    
    def get_permanent_memories(self, user_name: str) -> List[Dict[str, Any]]:
        """
        Get only permanent memories for a user.
        Follows: "Kalıcı hafızadaki bilgiler oturumlar arasında korunur."
        
        Args:
            user_name: Name of the user
            
        Returns:
            List of permanent memories
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT * FROM memories 
            WHERE user_name = ? AND is_permanent = 1
            ORDER BY importance DESC, last_accessed DESC
            ''', (user_name,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def classify_memory(self, message: str, user_name: str) -> Tuple[str, bool]:
        """
        Classify a message as temporary or permanent memory.
        Follows: "Asena yeni bir bilgi aldığında önce bunu sınıflandırır: Geçici mi kalıcı mı?"
        
        Args:
            message: User message to classify
            user_name: User name
            
        Returns:
            Tuple of (memory_type, is_permanent)
        """
        message_lower = message.lower()
        
        # Permanent memory indicators
        permanent_keywords = [
            'alerjim var', 'alerjimiz var',  # Allergies
            'seviyor', 'seviyorum', 'bayılıyor',  # Preferences
            'eşim', 'nişanlım', 'sevgilim', 'arkadaş',  # Relationships
            'çalış', 'meslek', 'işim',  # Work
            'ev', 'oda', 'kedi', 'köpek', 'pet',  # Home/pets
            'her zaman', 'daima', 'her gün',  # Habits/routines
            'ayarla', 'konfigüre', 'güvenlik',  # System settings
        ]
        
        # Temporary memory indicators
        temporary_keywords = [
            'bugün', 'bu akşam', 'bu gece', 'şu an',  # Today/now
            'yarın', 'sonra', 'daha sonra',  # Soon
            '15 dakika', '30 dakika', 'saat',  # Time-limited
            'hatırla', 'bildir', 'uyar',  # One-time actions
            'test', 'dene', 'deniyoruz',  # Temporary activities
        ]
        
        # Check for permanent indicators
        for keyword in permanent_keywords:
            if keyword in message_lower:
                return ('permanent', True)
        
        # Check for temporary indicators
        for keyword in temporary_keywords:
            if keyword in message_lower:
                return ('temporary', False)
        
        # Default to temporary if unsure
        return ('temporary', False)
    
    def get_relevant_memories(
        self,
        user_name: str,
        query: Optional[str] = None,
        memory_types: Optional[List[str]] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get relevant memories for a user.
        
        Args:
            user_name: Name of the user
            query: Optional search query for semantic search
            memory_types: Optional list of memory types to filter by
            limit: Maximum number of memories to return
            
        Returns:
            List of relevant memories
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Base query
            sql = '''
            SELECT * FROM memories 
            WHERE user_name = ?
            '''
            
            params: List[Any] = [user_name]
            
            # Add memory type filter if provided
            if memory_types:
                placeholders = ','.join(['?'] * len(memory_types))
                sql += f' AND memory_type IN ({placeholders})'
                params.extend(memory_types)
            
            # Add search query if provided
            if query:
                # Simple keyword search for now - could be enhanced with full-text search
                search_terms = query.split()
                search_conditions = []
                
                for term in search_terms:
                    search_conditions.append('(content LIKE ?)')
                    params.append(f'%{term}%')
                
                sql += ' AND (' + ' OR '.join(search_conditions) + ')'
            
            # Order by importance and recency
            sql += ' ORDER BY importance DESC, last_accessed DESC LIMIT ?'
            params.append(limit)
            
            cursor.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def update_short_term_memory(self, user_name: str, memory: Dict[str, Any]):
        """
        Update short-term memory for a user.
        
        Args:
            user_name: Name of the user
            memory: Memory dictionary to add
        """
        if user_name not in self.short_term_memory:
            self.short_term_memory[user_name] = deque(maxlen=self.max_short_term_memories)
        
        self.short_term_memory[user_name].append({
            'timestamp': datetime.now().isoformat(),
            'memory': memory
        })
    
    def get_short_term_memories(self, user_name: str) -> List[Dict[str, Any]]:
        """
        Get short-term memories for a user.
        
        Args:
            user_name: Name of the user
            
        Returns:
            List of short-term memories
        """
        if user_name not in self.short_term_memory:
            return []
        return list(self.short_term_memory[user_name])
    
    def get_conversation_context(
        self,
        user_name: str,
        current_message: str,
        include_short_term: bool = True,
        include_long_term: bool = True,
        max_tokens: int = 1000
    ) -> str:
        """
        Get relevant context for a conversation.
        
        Args:
            user_name: Name of the user
            current_message: The current user message
            include_short_term: Whether to include short-term memories
            include_long_term: Whether to include long-term memories
            max_tokens: Maximum number of tokens for the context
            
        Returns:
            str: Formatted context string
        """
        context_parts = []
        
        # Add recent conversations
        recent_convos = self.get_recent_conversations(user_name, limit=3)
        if recent_convos:
            context_parts.append("\n--- Recent Conversation ---")
            for conv in reversed(recent_convos):  # Oldest first
                context_parts.append(f"{user_name}: {conv['user_message']}")
                context_parts.append(f"Asistan: {conv['assistant_response']}")
        
        # Add short-term memories
        if include_short_term and user_name in self.short_term_memory:
            short_term = self.get_short_term_memories(user_name)
            if short_term:
                context_parts.append("\n--- Short-term Memory ---")
                for mem in short_term:
                    context_parts.append(f"- {mem['memory'].get('content', '')}")
        
        # Add relevant long-term memories
        if include_long_term:
            relevant_memories = self.get_relevant_memories(
                user_name=user_name,
                query=current_message,
                limit=3
            )
            
            if relevant_memories:
                context_parts.append("\n--- Relevant Memories ---")
                for mem in relevant_memories:
                    context_parts.append(f"- {mem['content']}")
        
        # Join and truncate if needed
        context = "\n".join(context_parts)
        if len(context) > max_tokens * 4:  # Rough estimate: 4 chars per token
            context = context[:max_tokens * 4] + "..."
        
        return context

# Singleton instance
_memory_manager = None

def get_memory_manager() -> MemoryManager:
    """
    Get or create a singleton instance of MemoryManager.
    
    Returns:
        MemoryManager instance
    """
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager

# Example usage
if __name__ == "__main__":
    # Initialize memory manager
    mm = get_memory_manager()
    
    # Add some test data
    user = "Nuri Can"
    
    # Add conversation
    mm.add_conversation(
        user_name=user,
        user_message="Merhaba, bugün hava nasıl?",
        assistant_response="Merhaba! Hava güneşli ve sıcak görünüyor."
    )
    
    # Add memory
    mm.add_memory(
        user_name=user,
        memory_type="preference",
        content="Sevdiği içecek: Türk kahvesi, şekersiz",
        importance=7,
        is_permanent=True
    )
    
    # Add short-term memory
    mm.update_short_term_memory(user, {
        'type': 'location',
        'content': 'Şu anda ofiste çalışıyor',
        'timestamp': datetime.now().isoformat()
    })
    
    # Get context
    context = mm.get_conversation_context(
        user_name=user,
        current_message="Bugün ne yapıyorsun?"
    )
    
    print("Context:")
    print(context)
