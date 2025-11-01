"""
Sentiment Analizi ve Duygusal Zeka Modülü
Kullanıcının ruh halini analiz eder ve uygun yanıtlar önerir
"""

import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import numpy as np

# Duygu kelimeleri ve yoğunlukları
EMOTION_KEYWORDS = {
    'happy': {
        'keywords': ['mutlu', 'harika', 'süper', 'mükemmel', 'güzel', 'iyi', 'sevindim', 'keyifli', 'hoş', 'eğlenceli', 'neşeli'],
        'intensity_multipliers': {'çok': 1.5, 'gerçekten': 1.3, 'son derece': 1.7, 'aşırı': 1.8}
    },
    'sad': {
        'keywords': ['üzgün', 'kötü', 'mutsuz', 'hüzünlü', 'kederli', 'moral', 'depresif', 'sıkıntılı', 'üzülüyorum'],
        'intensity_multipliers': {'çok': 1.5, 'gerçekten': 1.3, 'son derece': 1.7, 'aşırı': 1.8}
    },
    'angry': {
        'keywords': ['sinirli', 'kızgın', 'öfkeli', 'bıktım', 'nefret', 'rahatsız', 'sinirlendim', 'deliriyorum'],
        'intensity_multipliers': {'çok': 1.5, 'gerçekten': 1.3, 'son derece': 1.7, 'aşırı': 1.8}
    },
    'anxious': {
        'keywords': ['endişeli', 'kaygılı', 'tedirgin', 'gergin', 'stresli', 'huzursuz', 'korku', 'panik'],
        'intensity_multipliers': {'çok': 1.5, 'gerçekten': 1.3, 'son derece': 1.7, 'aşırı': 1.8}
    },
    'excited': {
        'keywords': ['heyecanlı', 'coşkulu', 'sabırsız', 'meraklı', 'istekli', 'hevesli', 'heyecan'],
        'intensity_multipliers': {'çok': 1.5, 'gerçekten': 1.3, 'son derece': 1.7, 'aşırı': 1.8}
    },
    'tired': {
        'keywords': ['yorgun', 'bitkin', 'tükenmiş', 'uykusuz', 'halsiz', 'enerjisiz', 'yoruldum'],
        'intensity_multipliers': {'çok': 1.5, 'gerçekten': 1.3, 'son derece': 1.7, 'aşırı': 1.8}
    }
}

def analyze_sentiment(message):
    """
    Mesajın duygusal tonunu analiz eder
    
    Returns:
        dict: {'emotion': str, 'intensity': float, 'confidence': float}
    """
    if not message:
        return {'emotion': 'neutral', 'intensity': 5.0, 'confidence': 0.0}
    
    message_lower = message.lower()
    
    # Her duygu için skor hesapla
    emotion_scores = {}
    
    for emotion, data in EMOTION_KEYWORDS.items():
        score = 0
        keyword_count = 0
        
        for keyword in data['keywords']:
            if keyword in message_lower:
                keyword_count += 1
                base_score = 5.0
                
                # Yoğunluk çarpanlarını kontrol et
                for multiplier_word, multiplier_value in data['intensity_multipliers'].items():
                    if multiplier_word in message_lower:
                        base_score *= multiplier_value
                        break
                
                score += base_score
        
        if keyword_count > 0:
            emotion_scores[emotion] = {
                'score': score,
                'keyword_count': keyword_count,
                'avg_intensity': score / keyword_count
            }
    
    # En yüksek skora sahip duyguyu bul
    if not emotion_scores:
        return {'emotion': 'neutral', 'intensity': 5.0, 'confidence': 0.0}
    
    dominant_emotion = max(emotion_scores.items(), key=lambda x: x[1]['score'])
    emotion_name = dominant_emotion[0]
    emotion_data = dominant_emotion[1]
    
    # Yoğunluk ve güven hesapla
    intensity = min(10.0, emotion_data['avg_intensity'])
    confidence = min(1.0, emotion_data['keyword_count'] * 0.3)
    
    return {
        'emotion': emotion_name,
        'intensity': intensity,
        'confidence': confidence
    }

def get_emotional_response_guide(emotion, intensity):
    """
    Duyguya uygun yanıt rehberi döndürür
    
    Args:
        emotion: Tespit edilen duygu
        intensity: Duygu yoğunluğu (0-10)
    
    Returns:
        dict: Yanıt için rehber
    """
    guides = {
        'happy': {
            'tone': 'Sevinçli ve destekleyici',
            'prefix_options': [
                'Ne güzel!',
                'Harika!',
                'Çok sevindim!',
                'Süper!'
            ]
        },
        'sad': {
            'tone': 'Empatik ve destekleyici',
            'prefix_options': [
                'Üzüldüğünü anlıyorum.',
                'Zor bir durum, yanındayım.',
                'Moralinin bozuk olduğunu görüyorum.',
                'Anlıyorum, bu gerçekten zor.'
            ]
        },
        'angry': {
            'tone': 'Sakin ve anlayışlı',
            'prefix_options': [
                'Sinirlenmen çok normal.',
                'Bu durumun seni rahatsız ettiğini anlıyorum.',
                'Haklısın, bu gerçekten sinir bozucu.',
                'Anlıyorum, bu can sıkıcı.'
            ]
        },
        'anxious': {
            'tone': 'Rahatlatıcı ve güven verici',
            'prefix_options': [
                'Endişelenme, her şey yoluna girecek.',
                'Anlıyorum, stresli bir durum.',
                'Kaygılandığını görüyorum.',
                'Sakin ol, birlikte hallederiz.'
            ]
        },
        'excited': {
            'tone': 'Coşkulu ve destekleyici',
            'prefix_options': [
                'Vay be!',
                'Ne kadar heyecanlı!',
                'Harika!',
                'Çok güzel!'
            ]
        },
        'tired': {
            'tone': 'Anlayışlı ve rahatlatıcı',
            'prefix_options': [
                'Yorgun görünüyorsun.',
                'Yorucu bir gün geçirmişsin galiba.',
                'Dinlenmeye ihtiyacın var gibi.',
                'Anlıyorum, yorulmuşsun.'
            ]
        },
        'neutral': {
            'tone': 'Doğal ve yardımsever',
            'prefix_options': []
        }
    }
    
    return guides.get(emotion, guides['neutral'])

def should_show_empathy(emotion, intensity):
    """
    Empati gösterilmesi gerekip gerekmediğini belirler
    
    Returns:
        bool: Empati gösterilmeli mi?
    """
    # Yüksek yoğunluklu negatif duygularda empati göster
    negative_emotions = ['sad', 'angry', 'anxious', 'tired']
    
    if emotion in negative_emotions and intensity >= 5.0:
        return True
    
    return False

def generate_empathetic_prefix(emotion, intensity):
    """
    Empatik bir yanıt başlangıcı oluşturur
    
    Returns:
        str: Empatik prefix
    """
    import random
    guide = get_emotional_response_guide(emotion, intensity)
    
    if guide['prefix_options']:
        return random.choice(guide['prefix_options'])
    
    return ""
