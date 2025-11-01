"""
Conversation Summarization Module
"""
from typing import List, Dict, Any, Optional
from groq import Groq
import os
import json
import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

class ConversationSummarizer:
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the ConversationSummarizer with an optional API key.
        If no API key is provided, it will be loaded from environment variables.
        """
        self.api_key = api_key or os.getenv('GROQ_API_KEY')
        if not self.api_key:
            raise ValueError("Groq API key not provided and not found in environment variables")
        
        self.client = Groq(api_key=self.api_key)
        self.model = "llama-3.1-8b-instant"
        self.max_tokens = 1000
        
    def summarize_conversation(
        self, 
        conversation: List[Dict[str, str]],
        summary_length: str = 'brief',  # 'brief', 'moderate', or 'detailed'
        language: str = 'turkish'
    ) -> str:
        """
        Generate a summary of a conversation using Groq's LLM.
        
        Args:
            conversation: List of message dictionaries with 'role' and 'content' keys
            summary_length: Desired length of the summary ('brief', 'moderate', or 'detailed')
            language: Language for the summary
            
        Returns:
            str: The generated summary
        """
        if not conversation:
            return ""
            
        # Convert conversation to text
        conversation_text = "\n".join(
            f"{msg['role'].capitalize()}: {msg['content']}" 
            for msg in conversation
        )
        
        # Determine summary length instructions
        length_instructions = {
            'brief': 'Kısa ve öz bir özet (1-2 cümle)',
            'moderate': 'Orta uzunlukta bir özet (3-5 cümle)',
            'detailed': 'Detaylı bir özet (5+ cümle)'
        }.get(summary_length, 'Orta uzunlıkta bir özet')
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": f"""Sen bir konuşma özetleme uzmanısın. Aşağıdaki konuşmayı {language} dilinde {length_instructions}.
                        Özetin ana konuları, kararları ve önemli noktaları vurgulayın.
                        Özeti 3. tekil şahıs olarak yazın."""
                    },
                    {
                        "role": "user",
                        "content": f"Aşağıdaki konuşmayı özetleyin:\n\n{conversation_text}"
                    }
                ],
                temperature=0.3,  # Slightly creative but mostly factual
                max_tokens=self.max_tokens
            )
            
            summary = response.choices[0].message.content
            if not summary:
                return ""
            return summary.strip()
            
        except Exception as e:
            logging.error(f"Error generating conversation summary: {e}")
            # Fallback to a simple summary of the last few messages
            last_messages = conversation[-3:]  # Get last 3 messages
            return " ".join([msg['content'] for msg in last_messages])
    
    def extract_action_items(
        self, 
        conversation: List[Dict[str, str]],
        language: str = 'turkish'
    ) -> List[Dict[str, Any]]:
        """
        Extract action items from a conversation.
        
        Args:
            conversation: List of message dictionaries with 'role' and 'content' keys
            language: Language for the action items
            
        Returns:
            List of action items with 'action', 'assigned_to', and 'due_date' keys
        """
        if not conversation:
            return []
            
        # Convert conversation to text
        conversation_text = "\n".join(
            f"{msg['role'].capitalize()}: {msg['content']}" 
            for msg in conversation
        )
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": f"""Sen bir konuşma analizcisisin. Aşağıdaki konuşmadan çıkarılan eylem maddelerini JSON formatında döndüreceksin.
                        
                        Çıktı formatı şu şekilde olmalıdır:
                        {{
                            "actions": [
                                {{
                                    "action": "Yapılacak işin açıklaması",
                                    "assigned_to": "Görevli kişi (eğer belirtilmişse)",
                                    "due_date": "Son tarih (eğer belirtilmişse, YYYY-MM-DD formatında)"
                                }}
                            ]
                        }}
                        
                        Eğer herhangi bir eylem maddesi yoksa, boş bir dizi döndür."""
                    },
                    {
                        "role": "user",
                        "content": f"Aşağıdaki konuşmadan eylem maddelerini çıkarın:\n\n{conversation_text}"
                    }
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            # Parse the response
            try:
                content = response.choices[0].message.content
                if not content:
                    return []
                    
                result = json.loads(content)
                actions = result.get('actions', [])
                
                # Validate actions
                valid_actions = []
                for action in actions:
                    if not isinstance(action, dict) or 'action' not in action:
                        continue
                    
                    # Ensure all required fields exist
                    valid_action = {
                        'action': action.get('action', '').strip(),
                        'assigned_to': action.get('assigned_to', '').strip() or None,
                        'due_date': action.get('due_date', '').strip() or None
                    }
                    
                    # Validate due_date format if present
                    if valid_action['due_date']:
                        try:
                            datetime.strptime(valid_action['due_date'], '%Y-%m-%d')
                        except ValueError:
                            valid_action['due_date'] = None
                    
                    valid_actions.append(valid_action)
                
                return valid_actions
                
            except (json.JSONDecodeError, AttributeError) as e:
                logging.error(f"Error parsing action items: {e}")
                return []
                
        except Exception as e:
            logging.error(f"Error extracting action items: {e}")
            return []
    
        if not conversation:
            return []
            
        # Convert conversation to text
        conversation_text = "\n".join(
            f"{msg['role'].capitalize()}: {msg['content']}" 
            for msg in conversation
        )
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": f"""Sen bir konuşma analizcisisin. Aşağıdaki konuşmadan çıkarılan eylem maddelerini JSON formatında döndüreceksin.
                        
                        Çıktı formatı şu şekilde olmalıdır:
                        {{
                            "actions": [
                                {{
                                    "action": "Yapılacak işin açıklaması",
                                    "assigned_to": "Görevli kişi (eğer belirtilmişse)",
                                    "due_date": "Son tarih (eğer belirtilmişse, YYYY-MM-DD formatında)"
                                }}
                            ]
                        }}
                        
                        Eğer herhangi bir eylem maddesi yoksa, boş bir dizi döndür."""
                    },
                    {
                        "role": "user",
                        "content": f"Aşağıdaki konuşmadan eylem maddelerini çıkarın:\n\n{conversation_text}"
                    }
                ],
                temperature=0.1,  # Very low temperature for consistent output
                max_tokens=500
            )
            
            # Parse the response
            try:
                result = json.loads(response.choices[0].message.content)
                actions = result.get('actions', [])
                
                # Validate actions
                valid_actions = []
                for action in actions:
                    if not isinstance(action, dict) or 'action' not in action:
                        continue
                    
                    # Ensure all required fields exist
                    valid_action = {
                        'action': action.get('action', '').strip(),
                        'assigned_to': action.get('assigned_to', '').strip() or None,
                        'due_date': action.get('due_date', '').strip() or None
                    }
                    
                    # Validate due_date format if present
                    if valid_action['due_date']:
                        try:
                            datetime.strptime(valid_action['due_date'], '%Y-%m-%d')
                        except ValueError:
                            valid_action['due_date'] = None
                    
                    valid_actions.append(valid_action)
                
                return valid_actions
                
            except (json.JSONDecodeError, AttributeError) as e:
                logging.error(f"Error parsing action items: {e}")
                return []
                
        except Exception as e:
            logging.error(f"Error extracting action items: {e}")
            return []

# Singleton instance
_summarizer = None

def get_conversation_summarizer(api_key: Optional[str] = None) -> 'ConversationSummarizer':
    """
    Get or create a singleton instance of ConversationSummarizer.
    
    Args:
        api_key: Optional Groq API key. If not provided, will use GROQ_API_KEY from environment.
        
    Returns:
        ConversationSummarizer instance
    """
    global _summarizer
    if _summarizer is None:
        _summarizer = ConversationSummarizer(api_key=api_key)
    return _summarizer

def summarize_conversation(
    conversation: List[Dict[str, str]],
    summary_length: str = 'brief',
    language: str = 'turkish'
) -> str:
    """
    Convenience function to summarize a conversation.
    
    Args:
        conversation: List of message dictionaries with 'role' and 'content' keys
        summary_length: Desired length of the summary ('brief', 'moderate', or 'detailed')
        language: Language for the summary
        
    Returns:
        str: The generated summary
    """
    summarizer = get_conversation_summarizer()
    return summarizer.summarize_conversation(conversation, summary_length, language)

def extract_action_items_from_conversation(
    conversation: List[Dict[str, str]],
    language: str = 'turkish'
) -> List[Dict[str, Any]]:
    """
    Convenience function to extract action items from a conversation.
    
    Args:
        conversation: List of message dictionaries with 'role' and 'content' keys
        language: Language for the action items
        
    Returns:
        List of action items with 'action', 'assigned_to', and 'due_date' keys
    """
    summarizer = get_conversation_summarizer()
    return summarizer.extract_action_items(conversation, language)

# Example usage
if __name__ == "__main__":
    # Example conversation
    example_conversation = [
        {"role": "user", "content": "Yarın saat 15:00'te toplantımız var, lütfen hatırlat."},
        {"role": "assistant", "content": "Tabii, yarın saat 15:00'teki toplantıyı hatırlatacağım."},
        {"role": "user", "content": "Ayrıca Nuri'ye proje raporunu göndermesini söyleyebilir misin?"},
        {"role": "assistant", "content": "Nuri'ye proje raporunu göndermesi gerektiğini ileteceğim."}
    ]
    
    # Initialize summarizer
    summarizer = get_conversation_summarizer()
    
    # Generate summary
    summary = summarizer.summarize_conversation(example_conversation, 'moderate')
    print("\nSummary:")
    print(summary)
    
    # Extract action items
    actions = summarizer.extract_action_items(example_conversation)
    print("\nAction Items:")
    for i, action in enumerate(actions, 1):
        print(f"{i}. {action['action']}")
        if action['assigned_to']:
            print(f"   Görevli: {action['assigned_to']}")
        if action['due_date']:
            print(f"   Son Tarih: {action['due_date']}")
