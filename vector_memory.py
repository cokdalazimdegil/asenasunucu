"""
Vector-based Memory System with ChromaDB
"""
import os
import json
import sqlite3
import chromadb
from typing import List, Dict, Any, Optional, Tuple
from chromadb.utils import embedding_functions
import numpy as np
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

class VectorMemory:
    def __init__(self, db_path: str = "./chroma_db"):
        """
        Initialize the vector memory system with ChromaDB.
        
        Args:
            db_path: Path to store the ChromaDB data
        """
        self.db_path = db_path
        
        # Initialize Chroma client with persistence
        self.client = chromadb.PersistentClient(path=db_path)
        
        # Use the default embedding function (all-MiniLM-L6-v2)
        self.embedding_function = embedding_functions.DefaultEmbeddingFunction()
        
        # Create or get the collection
        self.collection = self.client.get_or_create_collection(
            name="memory_embeddings",
            embedding_function=self.embedding_function,
            metadata={"hnsw:space": "cosine"}  # Use cosine similarity
        )
        
        # Connect to SQLite for metadata
        self.sql_conn = sqlite3.connect('asena_memory.db')
        self._init_db()
    
    def _init_db(self):
        """Initialize the SQLite database for metadata storage."""
        cursor = self.sql_conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS memory_metadata (
            id TEXT PRIMARY KEY,
            user_name TEXT NOT NULL,
            memory_type TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            access_count INTEGER DEFAULT 1
        )
        ''')
        self.sql_conn.commit()
    
    def add_memory(
        self, 
        user_name: str, 
        memory_type: str, 
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add a new memory to the vector database.
        
        Args:
            user_name: Name of the user this memory belongs to
            memory_type: Type/category of the memory
            content: The actual content to remember
            metadata: Additional metadata to store
            
        Returns:
            The ID of the created memory
        """
        # Generate a unique ID for this memory
        memory_id = f"mem_{hash(f'{user_name}_{memory_type}_{content}') & 0xffffffff}"
        
        # Add to ChromaDB
        self.collection.add(
            documents=[content],
            metadatas=[{"user": user_name, "type": memory_type, **(metadata or {})}],
            ids=[memory_id]
        )
        
        # Add to SQLite for metadata
        cursor = self.sql_conn.cursor()
        cursor.execute('''
        INSERT OR REPLACE INTO memory_metadata 
        (id, user_name, memory_type, content, last_accessed, access_count)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, COALESCE(
            (SELECT access_count + 1 FROM memory_metadata WHERE id = ?), 1
        ))
        ''', (memory_id, user_name, memory_type, content, memory_id))
        
        self.sql_conn.commit()
        logging.info(f"Added memory for {user_name}: {content[:50]}...")
        return memory_id
    
    def search_memories(
        self, 
        query: str, 
        user_name: Optional[str] = None,
        memory_type: Optional[str] = None,
        limit: int = 5,
        threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant memories using semantic similarity.
        
        Args:
            query: The search query
            user_name: Optional filter by user
            memory_type: Optional filter by memory type
            limit: Maximum number of results to return
            threshold: Minimum similarity score (0-1)
            
        Returns:
            List of relevant memories with metadata and scores
        """
        # Prepare filters
        filters = {}
        if user_name:
            filters["user"] = user_name
        if memory_type:
            filters["type"] = memory_type
        
        # Search in ChromaDB
        results = self.collection.query(
            query_texts=[query],
            n_results=limit,
            where=filters or None,
            where_document={"$contains": query} if query else None
        )
        
        # Process results
        memories = []
        if results and 'documents' in results:
            for i in range(len(results['ids'][0])):
                memory_id = results['ids'][0][i]
                distance = results['distances'][0][i]
                content = results['documents'][0][i]
                metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                
                # Convert distance to similarity score (1 - normalized distance)
                similarity = 1.0 - (distance / 2.0)  # Assuming cosine distance (0-2)
                
                if similarity >= threshold:
                    # Get additional metadata from SQLite
                    cursor = self.sql_conn.cursor()
                    cursor.execute('''
                    UPDATE memory_metadata 
                    SET last_accessed = CURRENT_TIMESTAMP, 
                        access_count = access_count + 1 
                    WHERE id = ?
                    ''', (memory_id,))
                    
                    cursor.execute('''
                    SELECT created_at, access_count 
                    FROM memory_metadata 
                    WHERE id = ?
                    ''', (memory_id,))
                    
                    row = cursor.fetchone()
                    created_at = row[0] if row else None
                    access_count = row[1] if row else 1
                    
                    memories.append({
                        'id': memory_id,
                        'content': content,
                        'user_name': metadata.get('user'),
                        'memory_type': metadata.get('type'),
                        'similarity': similarity,
                        'created_at': created_at,
                        'access_count': access_count,
                        'metadata': {k: v for k, v in metadata.items() if k not in ['user', 'type']}
                    })
        
        # Sort by similarity (highest first)
        memories.sort(key=lambda x: x['similarity'], reverse=True)
        return memories
    
    def get_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific memory by ID.
        
        Args:
            memory_id: The ID of the memory to retrieve
            
        Returns:
            The memory data or None if not found
        """
        try:
            # Get from ChromaDB
            result = self.collection.get(ids=[memory_id])
            if not result or 'documents' not in result or not result['documents']:
                return None
            
            # Get metadata from SQLite
            cursor = self.sql_conn.cursor()
            cursor.execute('''
            UPDATE memory_metadata 
            SET last_accessed = CURRENT_TIMESTAMP, 
                access_count = access_count + 1 
            WHERE id = ?
            ''', (memory_id,))
            
            cursor.execute('''
            SELECT user_name, memory_type, content, created_at, access_count 
            FROM memory_metadata 
            WHERE id = ?
            ''', (memory_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
                
            user_name, memory_type, content, created_at, access_count = row
            
            return {
                'id': memory_id,
                'user_name': user_name,
                'memory_type': memory_type,
                'content': content,
                'created_at': created_at,
                'access_count': access_count,
                'metadata': result['metadatas'][0] if result.get('metadatas') else {}
            }
            
        except Exception as e:
            logging.error(f"Error retrieving memory {memory_id}: {e}")
            return None
    
    def delete_memory(self, memory_id: str) -> bool:
        """
        Delete a memory by ID.
        
        Args:
            memory_id: The ID of the memory to delete
            
        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            # Delete from ChromaDB
            self.collection.delete(ids=[memory_id])
            
            # Delete from SQLite
            cursor = self.sql_conn.cursor()
            cursor.execute('DELETE FROM memory_metadata WHERE id = ?', (memory_id,))
            self.sql_conn.commit()
            
            return cursor.rowcount > 0
            
        except Exception as e:
            logging.error(f"Error deleting memory {memory_id}: {e}")
            self.sql_conn.rollback()
            return False
    
    def get_user_memories(
        self, 
        user_name: str, 
        memory_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get all memories for a specific user, optionally filtered by type.
        
        Args:
            user_name: Name of the user
            memory_type: Optional memory type filter
            limit: Maximum number of memories to return
            
        Returns:
            List of memories for the user
        """
        try:
            cursor = self.sql_conn.cursor()
            
            if memory_type:
                cursor.execute('''
                SELECT id, memory_type, content, created_at, last_accessed, access_count
                FROM memory_metadata
                WHERE user_name = ? AND memory_type = ?
                ORDER BY last_accessed DESC
                LIMIT ?
                ''', (user_name, memory_type, limit))
            else:
                cursor.execute('''
                SELECT id, memory_type, content, created_at, last_accessed, access_count
                FROM memory_metadata
                WHERE user_name = ?
                ORDER BY last_accessed DESC
                LIMIT ?
                ''', (user_name, limit))
            
            memories = []
            for row in cursor.fetchall():
                memory_id, mem_type, content, created_at, last_accessed, access_count = row
                
                # Get the full memory to include metadata
                memory = self.get_memory(memory_id)
                if memory:
                    memories.append(memory)
            
            return memories
            
        except Exception as e:
            logging.error(f"Error getting memories for user {user_name}: {e}")
            return []
    
    def close(self):
        """Close database connections."""
        try:
            self.sql_conn.close()
        except Exception as e:
            logging.error(f"Error closing database connection: {e}")

# Singleton instance
_vector_memory = None

def get_vector_memory() -> VectorMemory:
    """
    Get or create a singleton instance of VectorMemory.
    
    Returns:
        VectorMemory instance
    """
    global _vector_memory
    if _vector_memory is None:
        _vector_memory = VectorMemory()
    return _vector_memory

# Example usage
if __name__ == "__main__":
    # Initialize the memory system
    memory = get_vector_memory()
    
    # Add some memories
    memory.add_memory(
        user_name="Nuri Can",
        memory_type="preference",
        content="Sevdiği içecek: Türk kahvesi, şekersiz"
    )
    
    memory.add_memory(
        user_name="Rabia",
        memory_type="preference",
        content="Sevdiği içecek: Çay, açık ve limonlu"
    )
    
    # Search for memories
    results = memory.search_memories("Nuri ne içmeyi sever?", user_name="Nuri Can")
    print("Search results:")
    for i, mem in enumerate(results, 1):
        print(f"{i}. {mem['content']} (Similarity: {mem['similarity']:.2f})")
    
    # Close the database connection when done
    memory.close()
