"""
Enhanced Sentiment Analysis using Groq API
"""
import os
import json
from groq import Groq
from typing import Dict, Optional, Literal
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

# Emotion type definition
EmotionType = Literal[
    'happy', 'sad', 'angry', 'anxious', 
    'excited', 'tired', 'neutral'
]

class GroqSentimentAnalyzer:
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the GroqSentimentAnalyzer with an optional API key.
        If no API key is provided, it will be loaded from environment variables.
        """
        self.api_key = api_key or os.getenv('GROQ_API_KEY')
        if not self.api_key:
            raise ValueError("Groq API key not provided and not found in environment variables")
        
        self.client = Groq(api_key=self.api_key)
        self.model = "llama-3.1-8b-instant"
        
    def analyze_sentiment(self, message: str) -> Dict[str, str | float]:
        """
        Analyze the sentiment of a message using Groq's LLM.
        
        Args:
            message: The text message to analyze
            
        Returns:
            Dict containing emotion, intensity, and confidence
        """
        if not message or not message.strip():
            return {
                'emotion': 'neutral',
                'intensity': 5.0,
                'confidence': 1.0
            }
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """Sen bir duygu analizcisin. Kullanıcının mesajındaki duyguyu analiz edeceksin. 
                        Cevabını JSON formatında ver: 
                        {
                            "emotion": "happy | sad | angry | anxious | excited | tired | neutral",
                            "intensity": 1-10,
                            "confidence": 0.0-1.0
                        }"""
                    },
                    {
                        "role": "user",
                        "content": f"Aşağıdaki mesajdaki duyguyu analiz et: {message}"
                    }
                ],
                temperature=0.0,
                max_tokens=100,
                response_format={"type": "json_object"}
            )
            
            # Parse the response
            content = response.choices[0].message.content
            if content is None:
                raise ValueError("No content in API response")
            result = json.loads(content)
            
            # Validate the response
            if not all(key in result for key in ['emotion', 'intensity', 'confidence']):
                raise ValueError("Invalid response format from Groq API")
                
            # Ensure emotion is one of the allowed values
            emotion = result['emotion'].lower()
            if emotion not in ['happy', 'sad', 'angry', 'anxious', 'excited', 'tired', 'neutral']:
                emotion = 'neutral'
                
            # Ensure intensity is within bounds
            intensity = max(1, min(10, float(result['intensity'])))
            
            # Ensure confidence is within bounds
            confidence = max(0.0, min(1.0, float(result['confidence'])))
            
            return {
                'emotion': emotion,
                'intensity': intensity,
                'confidence': confidence
            }
            
        except Exception as e:
            logging.error(f"Error in sentiment analysis: {str(e)}")
            # Fallback to neutral sentiment on error
            return {
                'emotion': 'neutral',
                'intensity': 5.0,
                'confidence': 0.0
            }

# Singleton instance
_analyzer = None

def get_sentiment_analyzer(api_key: Optional[str] = None) -> GroqSentimentAnalyzer:
    """
    Get or create a singleton instance of GroqSentimentAnalyzer.
    
    Args:
        api_key: Optional Groq API key. If not provided, will use GROQ_API_KEY from environment.
        
    Returns:
        GroqSentimentAnalyzer instance
    """
    global _analyzer
    if _analyzer is None:
        _analyzer = GroqSentimentAnalyzer(api_key=api_key)
    return _analyzer

def analyze_sentiment(message: str) -> Dict[str, str | float]:
    """
    Convenience function to analyze sentiment of a message.
    
    Args:
        message: The text message to analyze
        
    Returns:
        Dict containing emotion, intensity, and confidence
    """
    analyzer = get_sentiment_analyzer()
    return analyzer.analyze_sentiment(message)
