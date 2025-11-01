"""
Advanced Context Management
Builds rich, contextual prompts with intelligent memory retrieval and prioritization
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from memory_manager import get_memory_manager
from conversation_summarizer import get_conversation_summarizer

logger = logging.getLogger(__name__)


class AdvancedContextBuilder:
    """Builds advanced context prompts with intelligent filtering and prioritization"""
    
    def __init__(self):
        self.memory_manager = get_memory_manager()
        self.conversation_summarizer = get_conversation_summarizer()
        self.context_weights = {
            'relationships': 1.0,
            'work': 0.9,
            'health': 0.95,
            'allergy': 0.99,
            'hobby': 0.7,
            'habit': 0.8,
            'personal': 0.85
        }
    
    def build_enhanced_context(self, user_name: str, current_message: str, 
                              include_emotions: bool = True) -> str:
        """
        Build enhanced context with intelligent prioritization
        
        Args:
            user_name: User identifier
            current_message: Current user message
            include_emotions: Include emotional context
            
        Returns:
            Formatted context string
        """
        context_parts = []
        
        # Get user profile
        profile = self._get_user_profile(user_name)
        if profile:
            context_parts.append(self._format_profile(profile))
        
        # Get relevant memories with smart filtering
        relevant_memories = self._get_relevant_memories(user_name, current_message)
        if relevant_memories:
            context_parts.append(self._format_memories(relevant_memories))
        
        # Get conversation summary
        summary = self._get_conversation_summary(user_name)
        if summary:
            context_parts.append(self._format_summary(summary))
        
        # Add emotional context if requested
        if include_emotions:
            emotional_context = self._get_emotional_context(user_name)
            if emotional_context:
                context_parts.append(emotional_context)
        
        # Get relevant habits/routines
        habits = self._get_relevant_habits(user_name, current_message)
        if habits:
            context_parts.append(self._format_habits(habits))
        
        return "\n\n".join(context_parts)
    
    def _get_user_profile(self, user_name: str) -> Optional[Dict[str, Any]]:
        """Get user profile information"""
        try:
            memories = self.memory_manager.get_permanent_memories(user_name)
            
            if not memories:
                return None
            
            profile = {
                'name': user_name,
                'info': {}
            }
            
            for memory in memories:
                # Parse key-value format
                content = memory.get('content', '')
                if ':' in content:
                    key, value = content.split(':', 1)
                    profile['info'][key.strip()] = value.strip()
            
            return profile if profile['info'] else None
        except Exception as e:
            logger.error(f"Error getting user profile: {e}")
            return None
    
    def _get_relevant_memories(self, user_name: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get memories most relevant to current query"""
        try:
            # Use memory manager's built-in relevance search
            return self.memory_manager.get_relevant_memories(user_name, query=query, limit=limit)
        except Exception as e:
            logger.error(f"Error getting relevant memories: {e}")
            return []
    
    def _score_memory_relevance(self, memory: Dict[str, Any], keywords: List[str]) -> float:
        """Calculate relevance score for a memory"""
        score = 0.0
        content = str(memory.get('content', '')).lower()
        
        # Keyword matching
        for keyword in keywords:
            if keyword.lower() in content:
                score += 2.0
        
        # Apply type weight
        mem_type = memory.get('memory_type', '')
        weight = self.context_weights.get(mem_type, 0.5)
        score *= weight
        
        # Apply importance weight
        importance = memory.get('importance', 5)
        score += (importance / 10.0)
        
        # Recency bonus
        created_at = memory.get('created_at')
        if created_at:
            try:
                created = datetime.fromisoformat(created_at)
                age_days = (datetime.now() - created).days
                
                if age_days <= 7:
                    score *= 1.5
                elif age_days <= 30:
                    score *= 1.2
                elif age_days > 365:
                    score *= 0.8
            except Exception:
                pass
        
        return score
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract important keywords from text"""
        import re
        
        # Remove punctuation and convert to lowercase
        text = re.sub(r'[^\w\s]', '', text.lower())
        
        # Stop words to exclude
        stop_words = {
            've', 'veya', 'ama', 'ile', 'bir', 'bu', 'şu', 'o', 'de', 'da', 
            'ki', 'mi', 'mı', 'mu', 'mü', 'ise', 'değil', 'amaçlı', 'nasıl',
            'ne', 'nedir', 'kaç', 'hangisi', 'hangi', 'kime', 'kimin'
        }
        
        words = text.split()
        keywords = [w for w in words if len(w) > 2 and w not in stop_words]
        
        return list(set(keywords))
    
    def _get_conversation_summary(self, user_name: str) -> Optional[str]:
        """Get conversation summary"""
        try:
            recent_conversations = self.memory_manager.get_recent_conversations(
                user_name, limit=5
            )
            
            if not recent_conversations:
                return None
            
            summary_text = "Recent conversation context:\n"
            for conv in recent_conversations[-3:]:
                if isinstance(conv, dict):
                    user_msg = conv.get('user_message', '')
                    if user_msg:
                        summary_text += f"- {user_msg[:100]}...\n"
            
            return summary_text if summary_text != "Recent conversation context:\n" else None
        except Exception as e:
            logger.error(f"Error getting conversation summary: {e}")
            return None
    
    def _get_emotional_context(self, user_name: str) -> Optional[str]:
        """Get emotional/mood context for user"""
        try:
            # Try to get recent memories for emotional state indicators
            memories = self.memory_manager.get_permanent_memories(user_name)
            
            mood_keywords = ['happy', 'sad', 'angry', 'anxious', 'excited', 'tired']
            emotional_state = None
            
            for memory in memories:
                content = str(memory.get('content', '')).lower()
                for mood in mood_keywords:
                    if mood in content:
                        emotional_state = mood
                        break
            
            if emotional_state:
                return f"User's current mood: {emotional_state}"
            return None
        except Exception as e:
            logger.error(f"Error getting emotional context: {e}")
            return None
    
    def _get_relevant_habits(self, user_name: str, query: str) -> Optional[str]:
        """Get user habits relevant to query"""
        try:
            habits = self.memory_manager.get_relevant_memories(
                user_name, query=query, memory_types=['habit'], limit=5
            )
            
            if not habits:
                return None
            
            # Check if habits are relevant to query
            keywords = self._extract_keywords(query)
            relevant_habits = []
            
            for habit in habits:
                content = str(habit.get('content', '')).lower()
                if any(kw in content for kw in keywords):
                    relevant_habits.append(content)
            
            if relevant_habits:
                return "Relevant user habits:\n" + "\n".join([f"- {h}" for h in relevant_habits])
            
            return None
        except Exception as e:
            logger.error(f"Error getting habits: {e}")
            return None
    
    def _format_profile(self, profile: Dict[str, Any]) -> str:
        """Format profile information"""
        text = f"Kullanıcı {profile['name']}'in Profil Bilgileri:\n"
        for key, value in profile['info'].items():
            text += f"  • {key}: {value}\n"
        return text
    
    def _format_memories(self, memories: List[Dict[str, Any]]) -> str:
        """Format memories section"""
        if not memories:
            return ""
        
        text = "Relevant Information:\n"
        for mem in memories:
            content = mem.get('content', '')
            mem_type = mem.get('memory_type', '')
            text += f"  • [{mem_type}] {content}\n"
        return text
    
    def _format_summary(self, summary: str) -> str:
        """Format summary section"""
        return f"Conversation Context:\n{summary}"
    
    def _format_habits(self, habits: str) -> str:
        """Format habits section"""
        return f"Habits & Routines:\n{habits}"


# Global instance
_advanced_context_builder = None


def get_advanced_context_builder() -> AdvancedContextBuilder:
    """Get or create global context builder instance"""
    global _advanced_context_builder
    if _advanced_context_builder is None:
        _advanced_context_builder = AdvancedContextBuilder()
    return _advanced_context_builder
