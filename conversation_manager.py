"""
Konuşma Yöneticisi
Konuşma akışını yönetir, konu değişikliklerini takip eder ve uygun müdahaleleri yapar
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import re
import json
import logging
import random
from dataclasses import dataclass, asdict
from collections import deque, defaultdict

# Loglama ayarları
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ConversationTopic:
    """Konuşma konusunu temsil eden sınıf"""
    topic: str  # Konu başlığı
    confidence: float  # 0-1 arası güven skoru
    keywords: List[str]  # İlgili anahtar kelimeler
    started_at: datetime  # Konunun başlangıç zamanı
    last_mentioned: datetime  # Son bahsedilme zamanı
    message_count: int = 1  # Bu konuda geçen mesaj sayısı
    
    def to_dict(self) -> Dict[str, Any]:
        """Sınıfı sözlüğe çevir"""
        result = asdict(self)
        result['started_at'] = self.started_at.isoformat()
        result['last_mentioned'] = self.last_mentioned.isoformat()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationTopic':
        """Sözlükten sınıf oluştur"""
        if 'started_at' in data and data['started_at']:
            if isinstance(data['started_at'], str):
                data['started_at'] = datetime.fromisoformat(data['started_at'])
        if 'last_mentioned' in data and data['last_mentioned']:
            if isinstance(data['last_mentioned'], str):
                data['last_mentioned'] = datetime.fromisoformat(data['last_mentioned'])
        return cls(**data)

class ConversationManager:
    """Konuşma yöneticisi sınıfı"""
    
    def __init__(self, max_topics: int = 10, topic_timeout: int = 1800):
        """
        Konuşma yöneticisini başlat
        
        Args:
            max_topics: Takip edilecek maksimum konu sayısı
            topic_timeout: Konunun zaman aşımına uğraması için geçen süre (saniye)
        """
        self.max_topics = max_topics
        self.topic_timeout = topic_timeout
        self.user_conversations = {}  # Kullanıcı ID'si -> Konuşma durumu
        self.topic_keywords = self._load_topic_keywords()
    
    def _load_topic_keywords(self) -> Dict[str, List[str]]:
        """Konu anahtar kelimelerini yükle"""
        return {
            'iş': ['iş', 'kariyer', 'çalışma', 'toplantı', 'proje', 'sunum', 'mülakat', 'maaş', 'terfi'],
            'eğitim': ['okul', 'üniversite', 'ders', 'sınav', 'ödev', 'proje', 'tez', 'öğrenci', 'hoca'],
            'sağlık': ['hasta', 'doktor', 'hastane', 'tedavi', 'ilaç', 'ağrı', 'rahatsız', 'kontrol'],
            'aile': ['aile', 'anne', 'baba', 'kardeş', 'eş', 'çocuk', 'akraba', 'akrabalar'],
            'ilişkiler': ['arkadaş', 'sevgili', 'eş', 'partner', 'flört', 'aşk', 'ilişki', 'dost'],
            'hobiler': ['hobi', 'spor', 'müzik', 'kitap', 'film', 'dizi', 'oyun', 'gezi', 'seyahat', 'yemek', 'sanat'],
            'teknoloji': ['telefon', 'bilgisayar', 'yazılım', 'donanım', 'internet', 'uygulama', 'sosyal medya'],
            'ekonomi': ['para', 'bütçe', 'tasarruf', 'yatırım', 'kredi', 'borç', 'harcama', 'fiyat', 'zam'],
            'gündem': ['haber', 'güncel', 'dünya', 'siyaset', 'ekonomi', 'spor', 'magazin', 'savaş', 'barış'],
            'genel': ['merhaba', 'nasılsın', 'iyi akşamlar', 'günaydın', 'iyi geceler', 'teşekkür', 'sağ ol']
        }
    
    def process_message(self, user_id: str, message: str, timestamp: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Gelen mesajı işle ve güncel konuşma durumunu güncelle
        
        Returns:
            Konuşma durumu ve önerilen yanıtlar
        """
        if not timestamp:
            timestamp = datetime.now()
        
        # Kullanıcı için konuşma durumunu al veya oluştur
        if user_id not in self.user_conversations:
            self.user_conversations[user_id] = {
                'topics': [],
                'last_message_time': timestamp,
                'message_count': 0,
                'active_topic': None
            }
        
        conv_state = self.user_conversations[user_id]
        conv_state['last_message_time'] = timestamp
        conv_state['message_count'] += 1
        
        # Konu tespiti yap
        detected_topics = self._detect_topics(message)
        
        # Konu güncellemelerini yap
        self._update_conversation_topics(user_id, detected_topics, timestamp)
        
        # Konuşma akışını analiz et
        flow_analysis = self._analyze_conversation_flow(user_id)
        
        # Uygun müdahaleleri belirle
        interventions = self._determine_interventions(user_id, flow_analysis)
        
        # Güncel konuşma durumunu hazırla
        current_topic = conv_state['active_topic']
        if current_topic:
            current_topic = current_topic.to_dict()
        
        return {
            'status': 'success',
            'current_topic': current_topic,
            'detected_topics': [t.to_dict() for t in detected_topics],
            'recent_topics': [t.to_dict() for t in conv_state['topics'][-3:]],
            'interventions': interventions,
            'message_count': conv_state['message_count']
        }
    
    def _detect_topics(self, message: str) -> List[ConversationTopic]:
        """Mesajdaki konuları tespit et"""
        message_lower = message.lower()
        detected_topics = []
        
        for topic, keywords in self.topic_keywords.items():
            # Her anahtar kelime için eşleşme kontrolü
            matched_keywords = [kw for kw in keywords if kw in message_lower]
            
            if matched_keywords:
                # Eşleşme güven skoru (0-1 arası)
                confidence = min(1.0, len(matched_keywords) * 0.3)
                
                # Yeni konu oluştur
                topic_obj = ConversationTopic(
                    topic=topic,
                    confidence=confidence,
                    keywords=matched_keywords,
                    started_at=datetime.now(),
                    last_mentioned=datetime.now()
                )
                
                detected_topics.append(topic_obj)
        
        # Eğer hiç konu bulunamadıysa genel kategorisini ekle
        if not detected_topics:
            detected_topics.append(ConversationTopic(
                topic='genel',
                confidence=0.3,
                keywords=[],
                started_at=datetime.now(),
                last_mentioned=datetime.now()
            ))
        
        return detected_topics
    
    def _update_conversation_topics(self, user_id: str, detected_topics: List[ConversationTopic], timestamp: datetime):
        """Konuşma konularını güncelle"""
        if user_id not in self.user_conversations:
            return
        
        conv_state = self.user_conversations[user_id]
        existing_topics = {t.topic: t for t in conv_state['topics']}
        
        # Zaman aşımına uğrayan konuları temizle
        self._cleanup_old_topics(user_id)
        
        # Tespit edilen konuları işle
        for detected in detected_topics:
            if detected.topic in existing_topics:
                # Mevcut konuyu güncelle
                existing = existing_topics[detected.topic]
                existing.last_mentioned = timestamp
                existing.message_count += 1
                existing.keywords = list(set(existing.keywords + detected.keywords))
                existing.confidence = min(1.0, existing.confidence + 0.1)  # Güveni artır
            else:
                # Yeni konu ekle
                if len(conv_state['topics']) >= self.max_topics:
                    # En eski konuyu çıkar
                    conv_state['topics'].pop(0)
                conv_state['topics'].append(detected)
                existing_topics[detected.topic] = detected
        
        # Aktif konuyu güncelle (en yüksek puanlı ve en son konuşulan)
        if conv_state['topics']:
            # Son 5 mesajda en çok geçen konu
            recent_topics = conv_state['topics'][-5:]
            topic_scores = defaultdict(float)
            
            for topic in recent_topics:
                # Son kullanıma göre ağırlıklandırma
                recency = (timestamp - topic.last_mentioned).total_seconds() / 3600  # Saat cinsinden
                recency_weight = max(0, 1 - (recency / 24))  # 24 saat içindeki kullanımlar daha önemli
                
                topic_scores[topic.topic] += topic.confidence * (1 + recency_weight)
            
            if topic_scores:
                active_topic = max(topic_scores.items(), key=lambda x: x[1])[0]
                conv_state['active_topic'] = next(t for t in conv_state['topics'] if t.topic == active_topic)
    
    def _cleanup_old_topics(self, user_id: str):
        """Zaman aşımına uğrayan konuları temizle"""
        if user_id not in self.user_conversations:
            return
        
        conv_state = self.user_conversations[user_id]
        now = datetime.now()
        
        # Zaman aşımına uğrayan konuları kaldır
        conv_state['topics'] = [
            t for t in conv_state['topics']
            if (now - t.last_mentioned).total_seconds() < self.topic_timeout
        ]
    
    def _analyze_conversation_flow(self, user_id: str) -> Dict[str, Any]:
        """Konuşma akışını analiz et"""
        if user_id not in self.user_conversations or not self.user_conversations[user_id]['topics']:
            return {'status': 'no_topics'}
        
        conv_state = self.user_conversations[user_id]
        topics = conv_state['topics']
        active_topic = conv_state.get('active_topic')
        
        # Konu çeşitliliği
        topic_diversity = len(set(t.topic for t in topics)) / len(topics) if topics else 0
        
        # Konu süreleri
        topic_durations = []
        for i in range(1, len(topics)):
            if topics[i].topic == topics[i-1].topic:
                duration = (topics[i].last_mentioned - topics[i-1].started_at).total_seconds()
                topic_durations.append(duration)
        
        avg_topic_duration = sum(topic_durations) / len(topic_durations) if topic_durations else 0
        
        # Son konu değişikliği
        last_topic_change = None
        if len(topics) > 1:
            last_topic_change = (datetime.now() - topics[-1].started_at).total_seconds()
        
        return {
            'topic_diversity': topic_diversity,
            'avg_topic_duration': avg_topic_duration,
            'active_topic_duration': (datetime.now() - active_topic.started_at).total_seconds() if active_topic else 0,
            'last_topic_change': last_topic_change,
            'topic_count': len(topics)
        }
    
    def _determine_interventions(self, user_id: str, flow_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Gerekli müdahaleleri belirle"""
        interventions = []
        
        # Uzun süren konu
        if flow_analysis.get('active_topic_duration', 0) > 300:  # 5 dakikadan uzun süren konu
            interventions.append({
                'type': 'suggest_topic_change',
                'reason': 'long_topic_duration',
                'message': 'Bu konu hakkında başka bir şey sormak ister misiniz?'
            })
        
        # Düşük konu çeşitliliği
        if flow_analysis.get('topic_diversity', 0) < 0.3 and flow_analysis.get('topic_count', 0) > 3:
            interventions.append({
                'type': 'suggest_new_topic',
                'reason': 'low_topic_diversity',
                'message': 'Başka bir konu hakkında konuşmak ister misiniz?'
            })
        
        # Uzun süredir aynı konu
        if flow_analysis.get('last_topic_change', 0) > 600:  # 10 dakikadır aynı konu
            interventions.append({
                'type': 'check_engagement',
                'reason': 'extended_same_topic',
                'message': 'Bu konu hakkında konuşmaya devam etmek istiyor musunuz?'
            })
        
        return interventions
    
    def suggest_topics(self, user_id: str, count: int = 3) -> List[Dict[str, Any]]:
        """Konu önerileri getir"""
        if user_id not in self.user_conversations:
            return []
        
        conv_state = self.user_conversations[user_id]
        recent_topics = set(t.topic for t in conv_state['topics'][-3:])
        
        # Mevcut konular dışındaki konuları öner
        available_topics = [t for t in self.topic_keywords.keys() if t not in recent_topics]
        
        # Rastgele seç (eğer yeterli sayıda varsa)
        if len(available_topics) <= count:
            return [{'topic': t, 'keywords': self.topic_keywords[t][:3]} for t in available_topics]
        
        suggested = random.sample(available_topics, count)
        return [{'topic': t, 'keywords': self.topic_keywords[t][:3]} for t in suggested]
    
    def get_conversation_summary(self, user_id: str) -> Dict[str, Any]:
        """Konuşma özetini getir"""
        if user_id not in self.user_conversations:
            return {
                'status': 'no_data',
                'message': 'Kullanıcıya ait konuşma verisi bulunamadı.'
            }
        
        conv_state = self.user_conversations[user_id]
        flow_analysis = self._analyze_conversation_flow(user_id)
        
        return {
            'status': 'success',
            'active_topic': conv_state['active_topic'].to_dict() if conv_state['active_topic'] else None,
            'recent_topics': [t.to_dict() for t in conv_state['topics'][-3:]],
            'message_count': conv_state['message_count'],
            'flow_analysis': flow_analysis,
            'suggested_topics': self.suggest_topics(user_id, 3)
        }

# Global instance
conversation_manager = ConversationManager()

def get_conversation_manager() -> ConversationManager:
    """Konuşma yöneticisini döndür"""
    return conversation_manager
