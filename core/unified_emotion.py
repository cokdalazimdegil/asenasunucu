"""
Unified Emotion Analysis Engine
Consolidates emotional_intelligence.py, enhanced_sentiment.py, and sentiment_analyzer.py
Single AI-powered emotion detection with fallback
"""

import os
import json
import logging
from typing import Dict, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


@dataclass
class EmotionResult:
    """Emotion analysis result"""
    emotion: str = 'neutral'  # happy, sad, angry, anxious, excited, tired, neutral
    intensity: float = 5.0  # 1-10
    confidence: float = 0.8  # 0-1
    timestamp: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class UnifiedEmotionEngine:
    """Single emotion analysis engine with AI and rule-based fallback"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('GROQ_API_KEY')
        self.groq_client = None
        self.model = "llama-3.1-8b-instant"
        
        # Initialize Groq if API key available
        if self.api_key:
            try:
                self.groq_client = Groq(api_key=self.api_key)
                logger.info("✅ Groq emotion analysis initialized")
            except Exception as e:
                logger.warning(f"⚠️ Groq init failed, using fallback: {e}")
        
        # Fallback rule-based lexicon
        self.emotion_lexicon = self._build_lexicon()
    
    def _build_lexicon(self) -> Dict[str, Dict[str, Any]]:
        """Build emotion keyword lexicon for fallback"""
        return {
            # Happy
            'mutlu': {'emotion': 'happy', 'intensity': 7.0},
            'harika': {'emotion': 'happy', 'intensity': 8.0},
            'süper': {'emotion': 'happy', 'intensity': 7.5},
            'mükemmel': {'emotion': 'happy', 'intensity': 8.5},
            'sevinç': {'emotion': 'happy', 'intensity': 8.0},
            'neşeli': {'emotion': 'happy', 'intensity': 7.0},
            
            # Sad
            'üzgün': {'emotion': 'sad', 'intensity': 7.0},
            'hüzün': {'emotion': 'sad', 'intensity': 8.0},
            'keder': {'emotion': 'sad', 'intensity': 8.5},
            'mutsuz': {'emotion': 'sad', 'intensity': 7.5},
            'moral bozuk': {'emotion': 'sad', 'intensity': 7.0},
            
            # Angry
            'sinirli': {'emotion': 'angry', 'intensity': 7.0},
            'kızgın': {'emotion': 'angry', 'intensity': 7.5},
            'öfkeli': {'emotion': 'angry', 'intensity': 8.5},
            'bıktım': {'emotion': 'angry', 'intensity': 7.0},
            'nefret': {'emotion': 'angry', 'intensity': 9.0},
            
            # Anxious
            'endişe': {'emotion': 'anxious', 'intensity': 7.0},
            'kaygı': {'emotion': 'anxious', 'intensity': 7.5},
            'stres': {'emotion': 'anxious', 'intensity': 7.0},
            'gergin': {'emotion': 'anxious', 'intensity': 6.5},
            'panik': {'emotion': 'anxious', 'intensity': 8.5},
            
            # Excited
            'heyecan': {'emotion': 'excited', 'intensity': 7.5},
            'coşku': {'emotion': 'excited', 'intensity': 8.0},
            'sabırsız': {'emotion': 'excited', 'intensity': 7.0},
            
            # Tired
            'yorgun': {'emotion': 'tired', 'intensity': 6.5},
            'bitkin': {'emotion': 'tired', 'intensity': 7.5},
            'tükenmiş': {'emotion': 'tired', 'intensity': 8.0},
            'halsiz': {'emotion': 'tired', 'intensity': 6.0},
        }
    
    def analyze(self, message: str, use_ai: bool = True) -> EmotionResult:
        """
        Analyze emotion with AI-first approach and fallback
        
        Args:
            message: Text to analyze
            use_ai: Use Groq AI (falls back to rules if fails)
        
        Returns:
            EmotionResult
        """
        if not message or not message.strip():
            return EmotionResult()
        
        # Try AI first
        if use_ai and self.groq_client:
            try:
                result = self._analyze_with_groq(message)
                if result:
                    return result
            except Exception as e:
                logger.warning(f"AI analysis failed, using fallback: {e}")
        
        # Fallback to rule-based
        return self._analyze_with_rules(message)
    
    def _analyze_with_groq(self, message: str) -> Optional[EmotionResult]:
        """AI-powered emotion analysis"""
        if not self.groq_client:
            return None
            
        try:
            response = self.groq_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """Sen duygu analiz uzmanısın. Kullanıcının mesajındaki duyguyu analiz et.
                        Sadece JSON formatında yanıt ver:
                        {
                            "emotion": "happy|sad|angry|anxious|excited|tired|neutral",
                            "intensity": 1-10,
                            "confidence": 0.0-1.0
                        }"""
                    },
                    {
                        "role": "user",
                        "content": f"Bu mesajı analiz et: {message}"
                    }
                ],
                temperature=0.0,
                max_tokens=100,
                response_format={"type": "json_object"}
            )
            
            if not response.choices[0].message.content:
                return None
            
            data = json.loads(response.choices[0].message.content)
            
            # Validate and normalize
            emotion = data.get('emotion', 'neutral').lower()
            if emotion not in ['happy', 'sad', 'angry', 'anxious', 'excited', 'tired', 'neutral']:
                emotion = 'neutral'
            
            intensity = max(1.0, min(10.0, float(data.get('intensity', 5.0))))
            confidence = max(0.0, min(1.0, float(data.get('confidence', 0.8))))
            
            return EmotionResult(
                emotion=emotion,
                intensity=intensity,
                confidence=confidence
            )
            
        except Exception as e:
            logger.error(f"Groq analysis error: {e}")
            return None
    
    def _analyze_with_rules(self, message: str) -> EmotionResult:
        """Rule-based fallback emotion analysis"""
        message_lower = message.lower()
        
        # Score each emotion
        emotion_scores = {
            'happy': 0.0, 'sad': 0.0, 'angry': 0.0,
            'anxious': 0.0, 'excited': 0.0, 'tired': 0.0
        }
        
        keyword_count = 0
        total_intensity = 0.0
        
        for keyword, data in self.emotion_lexicon.items():
            if keyword in message_lower:
                emotion = data['emotion']
                intensity = data['intensity']
                
                # Check for intensity modifiers
                if any(mod in message_lower for mod in ['çok', 'gerçekten', 'aşırı']):
                    intensity *= 1.3
                
                emotion_scores[emotion] += intensity
                keyword_count += 1
                total_intensity += intensity
        
        # Determine dominant emotion
        if keyword_count == 0:
            return EmotionResult(emotion='neutral', intensity=5.0, confidence=0.5)
        
        dominant = max(emotion_scores.items(), key=lambda x: x[1])
        avg_intensity = min(10.0, total_intensity / keyword_count)
        confidence = min(1.0, keyword_count * 0.3)
        
        return EmotionResult(
            emotion=dominant[0],
            intensity=avg_intensity,
            confidence=confidence
        )
    
    def get_response_guide(self, emotion: str, intensity: float) -> Dict[str, Any]:
        """Get response guidance for detected emotion"""
        guides = {
            'happy': {
                'tone': 'Sevinçli ve destekleyici',
                'prefixes': ['Ne güzel!', 'Harika!', 'Çok sevindim!', 'Süper!'],
                'should_empathize': False
            },
            'sad': {
                'tone': 'Empatik ve destekleyici',
                'prefixes': ['Üzüldüğünü anlıyorum.', 'Zor bir durum, yanındayım.', 
                           'Moralinin bozuk olduğunu görüyorum.'],
                'should_empathize': True
            },
            'angry': {
                'tone': 'Sakin ve anlayışlı',
                'prefixes': ['Sinirlenmen çok normal.', 'Bu durumun seni rahatsız ettiğini anlıyorum.',
                           'Haklısın, bu gerçekten sinir bozucu.'],
                'should_empathize': True
            },
            'anxious': {
                'tone': 'Rahatlatıcı ve güven verici',
                'prefixes': ['Endişelenme, her şey yoluna girecek.', 'Anlıyorum, stresli bir durum.',
                           'Kaygılandığını görüyorum.'],
                'should_empathize': True
            },
            'excited': {
                'tone': 'Coşkulu ve destekleyici',
                'prefixes': ['Vay be!', 'Ne kadar heyecanlı!', 'Harika!', 'Çok güzel!'],
                'should_empathize': False
            },
            'tired': {
                'tone': 'Anlayışlı ve rahatlatıcı',
                'prefixes': ['Yorgun görünüyorsun.', 'Dinlenmeye ihtiyacın var gibi.',
                           'Yorucu bir gün geçirmişsin galiba.'],
                'should_empathize': True
            },
            'neutral': {
                'tone': 'Doğal ve yardımsever',
                'prefixes': [],
                'should_empathize': False
            }
        }
        
        return guides.get(emotion, guides['neutral'])


# Singleton instance
_emotion_engine = None


def get_emotion_engine() -> UnifiedEmotionEngine:
    """Get global emotion engine instance"""
    global _emotion_engine
    if _emotion_engine is None:
        _emotion_engine = UnifiedEmotionEngine()
    return _emotion_engine


def analyze_emotion(message: str) -> EmotionResult:
    """Convenience function for emotion analysis"""
    engine = get_emotion_engine()
    return engine.analyze(message)
