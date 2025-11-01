"""
Duygusal Zeka Motoru
Kullanıcının duygusal durumunu analiz eder ve uygun yanıtlar üretir
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import random
import json
import logging
from dataclasses import dataclass, asdict
import re

# Loglama ayarları
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class EmotionalState:
    """Kullanıcının duygusal durumunu temsil eden sınıf"""
    primary_emotion: str = 'neutral'  # Ana duygu
    secondary_emotions: Optional[List[str]] = None  # İkincil duygular
    intensity: float = 5.0  # 0-10 arası yoğunluk
    confidence: float = 0.0  # 0-1 arası güven skoru
    mood_trend: str = 'stable'  # 'increasing', 'decreasing', 'stable'
    last_updated: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Sınıfı sözlüğe çevir"""
        result = asdict(self)
        if self.last_updated:
            result['last_updated'] = self.last_updated.isoformat()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EmotionalState':
        """Sözlükten sınıf oluştur"""
        if 'last_updated' in data and data['last_updated']:
            if isinstance(data['last_updated'], str):
                data['last_updated'] = datetime.fromisoformat(data['last_updated'])
        return cls(**data)

class EmotionalIntelligenceEngine:
    """Duygusal zeka motoru"""
    
    def __init__(self):
        self.user_states = {}  # Kullanıcı kimliği -> EmotionalState
        self.emotion_history = {}  # Duygu geçmişi
        self.response_templates = self._load_response_templates()
        self.emotion_lexicon = self._load_emotion_lexicon()
    
    def _load_response_templates(self) -> Dict[str, Dict[str, List[str]]]:
        """Yanıt şablonlarını yükle"""
        return {
            'happy': {
                'acknowledge': [
                    "Ne güzel bir enerji! 😊",
                    "Bu harika bir haber! 🎉",
                    "Senin mutluluğun bulaşıcı! 😄",
                    "Bunu duyduğuma çok sevindim! ✨"
                ],
                'follow_up': [
                    "Bu harika hissiyatın devam etmesini dilerim!",
                    "Daha fazla paylaşmak ister misin?",
                    "Bu güzel enerjini korumak için ne yapıyorsun?"
                ]
            },
            'sad': {
                'acknowledge': [
                    "Üzgün hissetmen çok doğal, yanındayım. 💙",
                    "Bu duyguyu hissetmen çok anlaşılır. 🫂",
                    "Zor bir dönemden geçiyor olabilirsin, yalnız değilsin.",
                    "Senin için üzüldüm. 🥺"
                ],
                'follow_up': [
                    "Bu konuda konuşmak ister misin?",
                    "Sana nasıl yardımcı olabilirim?",
                    "Biraz daha açılmak ister misin?"
                ]
            },
            'angry': {
                'acknowledge': [
                    "Bu duruma sinirlenmen çok doğal. 😤",
                    "Haklısın, bu gerçekten sinir bozucu olmalı.",
                    "Böyle hissetmeni anlıyorum, bu tür durumlar insanı gerçekten öfkelendirebiliyor.",
                    "Sinirlenmekte haklısın."
                ],
                'follow_up': [
                    "Bu konuda ne düşünüyorsun?",
                    "Bu durumla ilgili ne yapmayı düşünüyorsun?",
                    "Bu seni daha çok ne öfkelendiriyor?"
                ]
            },
            'anxious': {
                'acknowledge': [
                    "Endişelendiğini anlıyorum, bu çok doğal bir tepki. 🫂",
                    "Böyle hissetmen çok normal, yanındayım. 💙",
                    "Bu tür durumlarda endişelenmek çok doğal.",
                    "Endişelerini anlıyorum."
                ],
                'follow_up': [
                    "Bu konuda daha fazla konuşmak ister misin?",
                    "Seni rahatlatmak için bir şeyler yapabilir miyim?",
                    "Bu endişeyle başa çıkmak için ne yapıyorsun?"
                ]
            },
            'excited': {
                'acknowledge': [
                    "Ne kadar heyecan verici! 🎊",
                    "Bu harika bir haber! 🎉",
                    "Senin adına çok heyecanlandım! ✨",
                    "Bu inanılmaz! 😃"
                ],
                'follow_up': [
                    "Daha fazla detay paylaşmak ister misin?",
                    "Bu senin için ne ifade ediyor?",
                    "Bu heyecanını paylaşmak güzel!"
                ]
            },
            'tired': {
                'acknowledge': [
                    "Yorulmuş olman çok doğal, dinlenmeyi hak ettin. 💤",
                    "Kendine iyi bakmalısın, dinlenmek önemli. 🛌",
                    "Yorgun hissetmeni anlıyorum, böyle zamanlarda kendini şımartmalısın.",
                    "Dinlenmek için kendine zaman ayırmak önemli."
                ],
                'follow_up': [
                    "Kendini iyi hissetmek için ne yapıyorsun?",
                    "Dinlenmek için bir şeyler yapmayı düşünüyor musun?",
                    "Kendine iyi bakmak için bir planın var mı?"
                ]
            },
            'neutral': {
                'acknowledge': [
                    "Anlıyorum.",
                    "Teşekkür ederim paylaştığın için.",
                    "Bunu duymak ilginç.",
                    "Anladım."
                ],
                'follow_up': [
                    "Biraz daha açabilir misin?",
                    "Bu konuda başka bir şey söylemek ister misin?",
                    "Devam etmek ister misin?"
                ]
            }
        }
    
    def _load_emotion_lexicon(self) -> Dict[str, Dict[str, Any]]:
        """Duygu sözlüğünü yükle"""
        return {
            # Mutluluk
            'mutlu': {'primary': 'happy', 'intensity': 7.0, 'tags': ['positive']},
            'neşeli': {'primary': 'happy', 'intensity': 7.5, 'tags': ['positive']},
            'sevinç': {'primary': 'happy', 'intensity': 8.0, 'tags': ['positive']},
            'heyecan': {'primary': 'excited', 'intensity': 7.0, 'tags': ['positive', 'aroused']},
            'coşku': {'primary': 'excited', 'intensity': 8.0, 'tags': ['positive', 'aroused']},
            
            # Üzüntü
            'üzgün': {'primary': 'sad', 'intensity': 7.0, 'tags': ['negative']},
            'hüzün': {'primary': 'sad', 'intensity': 8.0, 'tags': ['negative']},
            'keder': {'primary': 'sad', 'intensity': 8.5, 'tags': ['negative']},
            'mutsuz': {'primary': 'sad', 'intensity': 7.5, 'tags': ['negative']},
            'çaresiz': {'primary': 'sad', 'intensity': 8.0, 'tags': ['negative', 'hopeless']},
            
            # Öfke
            'kızgın': {'primary': 'angry', 'intensity': 7.5, 'tags': ['negative', 'high_arousal']},
            'sinirli': {'primary': 'angry', 'intensity': 7.0, 'tags': ['negative', 'high_arousal']},
            'öfkeli': {'primary': 'angry', 'intensity': 8.5, 'tags': ['negative', 'high_arousal']},
            'hiddet': {'primary': 'angry', 'intensity': 9.0, 'tags': ['negative', 'high_arousal']},
            'küskün': {'primary': 'angry', 'intensity': 6.5, 'tags': ['negative', 'resentful']},
            
            # Endişe
            'endişe': {'primary': 'anxious', 'intensity': 7.0, 'tags': ['negative', 'uncertainty']},
            'kaygı': {'primary': 'anxious', 'intensity': 7.5, 'tags': ['negative', 'uncertainty']},
            'stres': {'primary': 'anxious', 'intensity': 7.0, 'tags': ['negative', 'tension']},
            'gergin': {'primary': 'anxious', 'intensity': 6.5, 'tags': ['negative', 'tension']},
            'panik': {'primary': 'anxious', 'intensity': 8.5, 'tags': ['negative', 'high_arousal']},
            
            # Yorgunluk
            'yorgun': {'primary': 'tired', 'intensity': 6.5, 'tags': ['low_energy']},
            'bitkin': {'primary': 'tired', 'intensity': 7.5, 'tags': ['low_energy']},
            'tükenmiş': {'primary': 'tired', 'intensity': 8.0, 'tags': ['low_energy']},
            'halsiz': {'primary': 'tired', 'intensity': 6.0, 'tags': ['low_energy']},
            'bıkkın': {'primary': 'tired', 'intensity': 7.0, 'tags': ['low_energy', 'frustrated']},
            
            # Nötr/Diğer
            'merak': {'primary': 'neutral', 'intensity': 5.0, 'tags': ['curious']},
            'şaşkın': {'primary': 'neutral', 'intensity': 5.5, 'tags': ['surprised']},
            'kararsız': {'primary': 'neutral', 'intensity': 5.0, 'tags': ['uncertain']}
        }
    
    def analyze_emotion(self, user_id: str, text: str, context: Optional[Dict[str, Any]] = None) -> EmotionalState:
        """Metindeki duyguyu analiz et"""
        if not text:
            return EmotionalState()
        
        # Önceki durumu al veya yeni oluştur
        current_state = self.user_states.get(user_id, EmotionalState())
        
        # Duygu analizi yap
        emotion_scores = self._calculate_emotion_scores(text)
        
        # Bağlamı değerlendir (eğer varsa)
        if context:
            self._apply_context(emotion_scores, context)
        
        # Önceki durumu da dikkate al
        self._apply_previous_state(emotion_scores, current_state)
        
        # Yeni duygusal durumu oluştur
        primary_emotion, intensity = self._determine_primary_emotion(emotion_scores)
        secondary_emotions = self._get_secondary_emotions(emotion_scores, primary_emotion)
        
        # Ruh hali trendini güncelle
        mood_trend = self._update_mood_trend(user_id, primary_emotion, intensity)
        
        # Yeni durumu kaydet
        new_state = EmotionalState(
            primary_emotion=primary_emotion,
            secondary_emotions=secondary_emotions,
            intensity=intensity,
            confidence=self._calculate_confidence(emotion_scores, primary_emotion),
            mood_trend=mood_trend,
            last_updated=datetime.now()
        )
        
        self.user_states[user_id] = new_state
        self._update_emotion_history(user_id, new_state)
        
        return new_state
    
    def _calculate_emotion_scores(self, text: str) -> Dict[str, float]:
        """Metindeki duygu puanlarını hesapla"""
        # Küçük harfe çevir ve noktalama işaretlerini kaldır
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Duygu puanlarını hesapla
        emotion_scores = {}
        words = text.split()
        
        for word in words:
            # Duygu sözlüğünde kelimeyi ara
            if word in self.emotion_lexicon:
                emotion_data = self.emotion_lexicon[word]
                primary = emotion_data['primary']
                intensity = emotion_data['intensity']
                
                # Yoğunluk çarpanlarını kontrol et
                multiplier = 1.0
                if 'çok' in words[max(0, words.index(word)-1):words.index(word)]:
                    multiplier = 1.5
                elif 'aşırı' in words[max(0, words.index(word)-1):words.index(word)]:
                    multiplier = 1.8
                
                # Puanı güncelle
                if primary in emotion_scores:
                    emotion_scores[primary] = max(emotion_scores[primary], intensity * multiplier)
                else:
                    emotion_scores[primary] = intensity * multiplier
        
        # Eğer hiç duygu bulunamadıysa nötr döndür
        if not emotion_scores:
            return {'neutral': 5.0}
            
        return emotion_scores
    
    def _apply_context(self, emotion_scores: Dict[str, float], context: Dict[str, Any]):
        """Bağlamsal bilgileri uygula"""
        # Önceki konuşmalardan duygu durumunu al
        if 'previous_emotion' in context:
            prev_emotion = context['previous_emotion']
            if isinstance(prev_emotion, dict) and 'primary_emotion' in prev_emotion:
                prev_primary = prev_emotion['primary_emotion']
                prev_intensity = prev_emotion.get('intensity', 5.0)
                
                # Önceki duygunun etkisini azaltarak ekle
                decayed_intensity = prev_intensity * 0.6  # Önceki etkinin azalarak devam etmesi
                if prev_primary in emotion_scores:
                    emotion_scores[prev_primary] = max(emotion_scores[prev_primary], decayed_intensity)
                else:
                    emotion_scores[prev_primary] = decayed_intensity
        
        # Konuşma konusuna göre duygu ağırlıklarını ayarla
        if 'topic' in context and context['topic']:
            topic = context['topic'].lower()
            
            # Belirli konular belirli duygularla ilişkilendirilebilir
            if 'sorun' in topic or 'problem' in topic:
                emotion_scores['sad'] = emotion_scores.get('sad', 0) + 2.0
                emotion_scores['anxious'] = emotion_scores.get('anxious', 0) + 1.5
            elif 'başarı' in topic or 'mutluluk' in topic:
                emotion_scores['happy'] = emotion_scores.get('happy', 0) + 2.0
                emotion_scores['excited'] = emotion_scores.get('excited', 0) + 1.5
    
    def _apply_previous_state(self, emotion_scores: Dict[str, float], previous_state: EmotionalState):
        """Önceki duygu durumunu dikkate al"""
        if not previous_state or not previous_state.primary_emotion:
            return
        
        # Önceki ana duygunun etkisini ekle (azaltılmış olarak)
        decay_factor = 0.4  # Önceki durumun etkisi
        prev_emotion = previous_state.primary_emotion
        prev_intensity = previous_state.intensity * decay_factor
        
        if prev_emotion in emotion_scores:
            emotion_scores[prev_emotion] = max(emotion_scores[prev_emotion], prev_intensity)
        else:
            emotion_scores[prev_emotion] = prev_intensity
    
    def _determine_primary_emotion(self, emotion_scores: Dict[str, float]) -> Tuple[str, float]:
        """Birincil duyguyu ve yoğunluğunu belirle"""
        if not emotion_scores:
            return 'neutral', 5.0
        
        # En yüksek puanlı duyguyu bul
        primary_emotion = max(emotion_scores.items(), key=lambda x: x[1])[0]
        intensity = min(emotion_scores[primary_emotion], 10.0)  # Maksimum 10
        
        return primary_emotion, intensity
    
    def _get_secondary_emotions(self, emotion_scores: Dict[str, float], primary_emotion: str) -> List[str]:
        """İkincil duyguları belirle"""
        if not emotion_scores or len(emotion_scores) <= 1:
            return []
        
        # Birincil duygu dışındaki duyguları al
        other_emotions = [(e, s) for e, s in emotion_scores.items() if e != primary_emotion]
        
        # Puanlarına göre sırala
        other_emotions.sort(key=lambda x: x[1], reverse=True)
        
        # En yüksek puanlı 2 duyguyu al (eğer yeterliyse)
        threshold = 0.7 * emotion_scores[primary_emotion]  # Birincil duygunun %70'i kadar olanlar
        secondary = [e for e, s in other_emotions if s >= threshold][:2]
        
        return secondary
    
    def _update_mood_trend(self, user_id: str, current_emotion: str, current_intensity: float) -> str:
        """Ruh hali trendini güncelle"""
        if user_id not in self.emotion_history:
            self.emotion_history[user_id] = []
        
        # Son 3 duygu durumunu al
        recent_states = self.emotion_history[user_id][-2:]  # Son 2 durum + mevcut = 3
        
        if not recent_states:
            return 'stable'
        
        # Ortalama yoğunluğu hesapla
        avg_intensity = sum(s.intensity for s in recent_states) / len(recent_states)
        
        # Trendi belirle
        if current_intensity > avg_intensity + 1.5:
            return 'increasing'
        elif current_intensity < avg_intensity - 1.5:
            return 'decreasing'
        else:
            return 'stable'
    
    def _calculate_confidence(self, emotion_scores: Dict[str, float], primary_emotion: str) -> float:
        """Duygu tespiti için güven skoru hesapla"""
        if not emotion_scores or primary_emotion not in emotion_scores:
            return 0.0
        
        primary_score = emotion_scores[primary_emotion]
        total_score = sum(emotion_scores.values())
        
        if total_score == 0:
            return 0.0
        
        # Birincil duygunun toplam içindeki oranı
        ratio = primary_score / total_score
        
        # Yoğunluğa göre ölçeklendir (0-10 -> 0-1)
        intensity_factor = min(primary_score / 10.0, 1.0)
        
        # Nihai güven skoru (0-1 arası)
        confidence = ratio * intensity_factor
        
        return min(max(confidence, 0.0), 1.0)
    
    def _update_emotion_history(self, user_id: str, state: EmotionalState):
        """Duygu geçmişini güncelle"""
        if user_id not in self.emotion_history:
            self.emotion_history[user_id] = []
        
        # Son 10 durumu sakla
        self.emotion_history[user_id] = self.emotion_history[user_id][-9:] + [state]
    
    def generate_response(self, user_id: str, message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Duygu durumuna uygun yanıt oluştur"""
        # Duygu analizi yap
        emotion_state = self.analyze_emotion(user_id, message, context)
        
        # Uygun yanıt şablonlarını seç
        templates = self.response_templates.get(emotion_state.primary_emotion, 
                                              self.response_templates['neutral'])
        
        # Onaylama ve devam sorularını seç
        acknowledge = random.choice(templates['acknowledge']) if templates['acknowledge'] else ""
        follow_up = random.choice(templates['follow_up']) if templates['follow_up'] and random.random() > 0.5 else ""
        
        # Yanıtı oluştur
        response = {
            'text': f"{acknowledge} {follow_up}".strip(),
            'emotion': emotion_state.to_dict(),
            'suggested_actions': self._get_suggested_actions(emotion_state)
        }
        
        return response
    
    def _get_suggested_actions(self, emotion_state: EmotionalState) -> List[Dict[str, str]]:
        """Duygu durumuna göre önerilen eylemler"""
        actions = []
        
        # Duyguya özel eylemler
        if emotion_state.primary_emotion == 'sad':
            actions.append({'text': 'Hikayeni paylaş', 'type': 'share_story'})
            actions.append({'text': 'Motivasyon konuşması ister misin?', 'type': 'request_motivation'})
        elif emotion_state.primary_emotion == 'angry':
            actions.append({'text': 'Sakinleşmek için nefes egzersizi yapalım mı?', 'type': 'breathing_exercise'})
        elif emotion_state.primary_emotion == 'anxious':
            actions.append({'text': 'Rahatlamak için bir şeyler önerebilirim', 'type': 'suggest_relaxation'})
        elif emotion_state.primary_emotion == 'happy':
            actions.append({'text': 'Bu güzel haberi kutlayalım!', 'type': 'celebrate'})
        
        # Genel eylemler
        actions.append({'text': 'Başka bir konuya geçelim', 'type': 'change_topic'})
        actions.append({'text': 'Yardımcı olabileceğim başka bir şey var mı?', 'type': 'offer_help'})
        
        return actions
    
    def get_user_emotion_summary(self, user_id: str) -> Dict[str, Any]:
        """Kullanıcının duygu özetini getir"""
        if user_id not in self.user_states:
            return {
                'status': 'no_data',
                'message': 'Kullanıcıya ait duygu verisi bulunamadı.'
            }
        
        current_state = self.user_states[user_id]
        history = self.emotion_history.get(user_id, [])
        
        # Duygu dağılımını hesapla
        emotion_distribution = {}
        for state in history:
            emotion = state.primary_emotion
            emotion_distribution[emotion] = emotion_distribution.get(emotion, 0) + 1
        
        # En sık görülen duyguyu bul
        most_common_emotion = max(emotion_distribution.items(), key=lambda x: x[1])[0] if emotion_distribution else 'neutral'
        
        return {
            'status': 'success',
            'current_emotion': current_state.to_dict(),
            'most_common_emotion': most_common_emotion,
            'emotion_distribution': emotion_distribution,
            'total_interactions': len(history),
            'last_updated': current_state.last_updated.isoformat() if current_state.last_updated else None
        }

# Global instance
emotional_engine = EmotionalIntelligenceEngine()

def get_emotional_engine() -> EmotionalIntelligenceEngine:
    """Duygusal zeka motorunu döndür"""
    return emotional_engine
