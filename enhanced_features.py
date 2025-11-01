"""
Asena AI - Geliştirilmiş Özellikler
Tüm yeni geliştirmeleri içerir
"""

import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from collections import defaultdict
import random

logger = logging.getLogger(__name__)

# ============================================================================
# 1. HAFIZA SİSTEMİ GELİŞTİRMESİ
# ============================================================================

class AdvancedMemorySystem:
    """Geliştirilmiş hafıza yönetimi"""
    
    def __init__(self):
        self.memory_categories = {
            'preferences': 'Tercihler (yemek, müzik, aktivite)',
            'habits': 'Alışkanlıklar (sabah, akşam rutini)',
            'relationships': 'İlişkiler (aile, arkadaş)',
            'schedule': 'Zaman çizelgesi',
            'goals': 'Hedefler',
            'health': 'Sağlık ve wellness',
            'events': 'Önemli olaylar',
            'temporary': 'Geçici bilgiler (bugün yapılacaklar)'
        }
        self.memory_importance = defaultdict(int)
    
    def categorize_memory(self, content: str, context: str = "") -> str:
        """Hafızayı otomatik kategorilendır"""
        content_lower = content.lower()
        
        if any(word in content_lower for word in ['sever', 'bayılır', 'hoşlanır', 'yemek', 'içecek']):
            return 'preferences'
        elif any(word in content_lower for word in ['sabah', 'akşam', 'gece', 'her gün', 'her sabah']):
            return 'habits'
        elif any(word in content_lower for word in ['nuri', 'rabia', 'eş', 'sevgili', 'arkadaş', 'aile']):
            return 'relationships'
        elif any(word in content_lower for word in ['yarın', 'bugün', 'saat', 'zaman', 'çalışma']):
            return 'schedule'
        elif any(word in content_lower for word in ['hedef', 'amaç', 'başarmak', 'öğrenmek']):
            return 'goals'
        elif any(word in content_lower for word in ['spor', 'antrenman', 'sağlık', 'yoga', 'yürüyüş']):
            return 'health'
        elif any(word in content_lower for word in ['doğum', 'yıldönümü', 'kutlama', 'özel']):
            return 'events'
        else:
            return 'temporary'
    
    def should_expire_memory(self, memory_category: str, created_days_ago: int) -> bool:
        """Hafızanın süresi doldumu kontrol et"""
        expiry_days = {
            'temporary': 1,
            'schedule': 7,
            'habits': 90,
            'preferences': 365,
            'relationships': 999,  # Hiç süresi dolmaz
            'goals': 180,
            'health': 30,
            'events': 365
        }
        return created_days_ago > expiry_days.get(memory_category, 30)

# ============================================================================
# 2. PROAKTIF ÖZELLİKLER
# ============================================================================

class ProactiveAssistant:
    """Proaktif yardımcı özellikler"""
    
    def generate_morning_briefing(self, user_name: str, weather_info: str, 
                                 user_schedule: Optional[List[str]] = None) -> str:
        """Sabah özeti oluştur"""
        hour = datetime.now().hour
        
        greetings = {
            'Nuri Can': [
                "Günaydın Nuri!",
                "Merhaba Nuri Can! Yeni bir gün başlıyor",
                "Sabahın hayırlı olsun Nuri! Kahven hazır"
            ],
            'Rabia': [
                "Günaydın Rabia!",
                "Selam Rabia! Enerjik bir gün için hazır mısın?",
                "Sabahın hayırlı olsun! Antrenman var mı bugün?"
            ]
        }
        
        greeting = random.choice(greetings.get(user_name, greetings['Nuri Can']))
        
        briefing = f"{greeting}\n\n"
        briefing += f"Hava Durumu:\n{weather_info}\n\n"
        
        if user_schedule:
            briefing += "Bugünün Programı:\n"
            for item in user_schedule[:3]:
                briefing += f"  - {item}\n"
            briefing += "\n"
        
        briefing += "İpucu: Sabah rutini devam ettir. Başarılar dilerim!"
        
        return briefing
    
    def suggest_wellness_activity(self, mood: str, time_of_day: str) -> str:
        """Ruh haliye uygun wellness aktivitesi öner"""
        suggestions = {
            'happy': {
                'morning': ' Müzik dinle ve dans et!',
                'afternoon': ' Kısa bir yürüyüş yapabilirsin',
                'evening': ' Sevdiğin birine telefon et'
            },
            'tired': {
                'morning': ' Kahve içip dinlen biraz',
                'afternoon': ' Kısa bir uyku veya meditasyon yap',
                'evening': ' Sakin bir dizi izle'
            },
            'sad': {
                'morning': ' Sevdiğin müzikleri dinle',
                'afternoon': ' Arkadaşla buluş',
                'evening': ' Meditasyon veya yoga yap'
            },
            'anxious': {
                'morning': ' Derin nefes al',
                'afternoon': ' Yaratıcı bir aktivite yap',
                'evening': ' Sakinleşme egzersizi yap'
            }
        }
        
        mood_suggestions = suggestions.get(mood, {})
        if mood_suggestions and isinstance(mood_suggestions, dict):
            result = mood_suggestions.get(time_of_day)
            if result:
                return result
        return ' Güne başla!'

# ============================================================================
# 3. ÇOK KULLANICILI ZEKA
# ============================================================================

class FamilyIntelligence:
    """Aile üyeleri arasında zeka"""
    
    def __init__(self):
        self.family_members = {
            'Nuri Can': {
                'role': 'Teknolog, Siber Güvenlik Uzmanı',
                'schedule': 'Hafta içi 09:00-18:00',
                'interests': ['Teknoloji', 'Yazılım', 'Müzik'],
                'relationship': 'Rabia ile evli'
            },
            'Rabia': {
                'role': 'Fitness ve Jimnastik Antrenörü',
                'schedule': 'Pazartesi hariç, değişken saatler',
                'interests': ['Fitness', 'Müzik', 'El işleri'],
                'relationship': 'Nuri Can ile evli'
            }
        }
        self.shared_memories = []
    
    def suggest_family_activity(self) -> str:
        """Aile aktivitesi öner"""
        activities = [
            " Müzik dinle ve dans et",
            " Beraber dizi izle",
            " Yeni bir tarif dene",
            " Sabah yürüyüşü yap",
            " Beraber bir aktivite planla"
        ]
        return random.choice(activities)
    
    def get_shared_context(self, topic: str) -> str:
        """Aile bağlamında paylaşılan bilgi getir"""
        if 'müzik' in topic.lower():
            return "Nuri ve Rabia müzik dinlemeyi severler. Rabia ukulele çalıyor!"
        elif 'antrenman' in topic.lower():
            return "Rabia fitness antrenörü. Nuri da sağlık konusunda ilgili."
        elif 'teknoloji' in topic.lower():
            return "Nuri Can teknoloji tutkunudur. Rabia da onun projelerine katılıyor."
        return ""

# ============================================================================
# 4. DUYGUSAL ZEKA İYİLEŞTİRMESİ
# ============================================================================

class EnhancedEmotionalIntelligence:
    """Geliştirilmiş duygusal zeka"""
    
    def __init__(self):
        self.mood_history = {}
        self.mood_trends = {}
    
    def track_mood(self, user_name: str, mood: str, intensity: int = 5):
        """Ruh halini takip et"""
        if user_name not in self.mood_history:
            self.mood_history[user_name] = []
        
        self.mood_history[user_name].append({
            'mood': mood,
            'intensity': intensity,
            'timestamp': datetime.now().isoformat()
        })
    
    def detect_mood_pattern(self, user_name: str) -> Dict[str, Any]:
        """Ruh hali paternini tespit et"""
        if user_name not in self.mood_history or len(self.mood_history[user_name]) < 3:
            return {'pattern': 'insufficient_data'}
        
        moods = self.mood_history[user_name][-7:]  # Son 7 gün
        mood_counts = defaultdict(int)
        
        for record in moods:
            mood_counts[record['mood']] += 1
        
        most_common = max(mood_counts.items(), key=lambda x: x[1]) if mood_counts else ('neutral', 0)
        
        return {
            'pattern': 'detected',
            'most_common_mood': most_common[0],
            'frequency': most_common[1],
            'recommendation': self._suggest_wellness(most_common[0])
        }
    
    def _suggest_wellness(self, mood: str) -> str:
        """Wellness önerisi sun"""
        suggestions = {
            'happy': ' Bu harika duyguyu korumaya devam et!',
            'sad': ' Konuşmak, yürümek veya müzik dinlemek sana iyi gelebilir',
            'anxious': ' Derin nefes egzersizleri ve meditasyon dene',
            'tired': ' İyi bir uyku ve dinlenme zamanı gerekiyor',
            'angry': ' Sakinleşmek için biraz zaman al'
        }
        return suggestions.get(mood, ' Başarılar dilerim!')

# ============================================================================
# 5. KONUŞMA ZEKASİ
# ============================================================================

class ConversationIntelligence:
    """Konuşma zekası"""
    
    def __init__(self):
        self.active_topics = {}
        self.conversation_context = {}
    
    def maintain_topic_continuity(self, user_name: str, current_message: str) -> str:
        """Konu kalıcılığını sağla"""
        if user_name not in self.active_topics:
            return ""
        
        previous_topic = self.active_topics[user_name]
        
        if previous_topic and previous_topic not in current_message.lower():
            return f"Biraz önceki '{previous_topic}' konusundan bahsediyorduk..."
        
        return ""
    
    def ask_clarifying_questions(self, message: str) -> Optional[str]:
        """Açıklayıcı sorular sor"""
        ambiguous_phrases = {
            'onu': 'Kimi kastettin? Lütfen biraz daha aç?',
            'bunu': 'Neyi kastettiniz? Detay verir misin?',
            'bu': 'Hangisinden bahsediyorsun?',
            'o gün': 'Hangi günden bahsediyorsun? Tarih verir misin?'
        }
        
        for phrase, question in ambiguous_phrases.items():
            if phrase in message.lower():
                return question
        
        return None

# ============================================================================
# 6. CİHAZ & EV ENTEGRASYONU (TV ZATEn VAR, GENIŞLET)
# ============================================================================

class SmartHomeControl:
    """Akıllı ev kontrolü"""
    
    def __init__(self):
        self.devices = {
            'lights': {'status': 'off', 'brightness': 0},
            'ac': {'status': 'off', 'temperature': 22},
            'music': {'status': 'off', 'volume': 50},
            'tv': {'status': 'off', 'channel': ''}
        }
        self.automation_rules = []
    
    def set_device_status(self, device: str, command: str) -> str:
        """Cihaz durumunu ayarla"""
        device_lower = device.lower()
        command_lower = command.lower()
        
        if device_lower == 'lights':
            if 'aç' in command_lower:
                return " Işıklar açılıyor..."
            elif 'kapat' in command_lower:
                return " Işıklar kapatılıyor..."
            elif 'azalt' in command_lower or 'kısık' in command_lower:
                return " Işıklar kısılıyor..."
        
        elif device_lower == 'ac' or device_lower == 'klima':
            if 'aç' in command_lower:
                return " Klima açılıyor..."
            elif 'kapat' in command_lower:
                return " Klima kapatılıyor..."
            elif any(x in command_lower for x in ['derece', '°', 'sıcak']):
                temp = ''.join(filter(str.isdigit, command))
                return f" Klima {temp}°C'ye ayarlanıyor..."
        
        elif device_lower == 'music' or device_lower == 'müzik':
            if 'aç' in command_lower or 'çal' in command_lower:
                return " Müzik çalınıyor..."
            elif 'kapat' in command_lower:
                return " Müzik durduruluyor..."
        
        return f" {device} için komut işleniyor..."
    
    def add_automation_rule(self, trigger: str, action: str) -> str:
        """Otomasyon kuralı ekle"""
        rule = {'trigger': trigger, 'action': action}
        self.automation_rules.append(rule)
        return f" Otomasyon kuralı eklendi: {trigger} → {action}"

# ============================================================================
# 7. ZAMANLAMA & PLANLAMA
# ============================================================================

class SmartScheduler:
    """Akıllı zamanlama"""
    
    def __init__(self):
        self.tasks = []
        self.calendar_events = []
    
    def suggest_best_meeting_time(self, users: List[str], duration_minutes: int = 60) -> str:
        """En iyi toplantı zamanını öner"""
        # Nuri Can: 09:00-18:00, Rabia: Değişken
        suggestion = " En iyi buluşma zamanı: Cuma öğleden sonra 15:00-16:00 arası"
        return suggestion
    
    def create_task(self, title: str, due_date: Optional[str] = None, priority: str = 'normal') -> str:
        """Görev oluştur"""
        task = {
            'title': title,
            'due_date': due_date,
            'priority': priority,
            'created_at': datetime.now().isoformat(),
            'status': 'pending'
        }
        self.tasks.append(task)
        return f" Görev oluşturuldu: {title}"
    
    def get_upcoming_deadlines(self) -> List[str]:
        """Yaklaşan son tarihleri getir"""
        deadlines = []
        for task in self.tasks:
            if task['due_date']:
                deadline = datetime.fromisoformat(task['due_date'])
                if deadline > datetime.now():
                    days_left = (deadline - datetime.now()).days
                    if days_left <= 7:
                        deadlines.append(f" {task['title']} - {days_left} gün kaldı")
        return deadlines

# ============================================================================
# 8. KİŞİSELLEŞTİRME
# ============================================================================

class PersonalizationEngine:
    """Kişiselleştirme motoru"""
    
    def __init__(self):
        self.user_preferences = {
            'communication_style': 'casual',  # casual, formal
            'response_length': 'moderate',     # brief, moderate, detailed
            'notification_frequency': 'smart'  # frequent, smart, minimal
        }
        self.learned_preferences = defaultdict(dict)
    
    def learn_preference(self, user_name: str, category: str, preference: str):
        """Tercih öğren"""
        self.learned_preferences[user_name][category] = preference
    
    def adapt_communication(self, user_name: str, message: str) -> str:
        """İletişimi kişiselleştir"""
        if user_name == 'Nuri Can':
            # Teknik konular, net yanıtlar
            return f" Teknik konu: {message}\n(Nuri için detaylı/teknik açıklama)"
        elif user_name == 'Rabia':
            # Samimi, motivasyonel
            return f" {message}\n(Rabia için motivasyonel mesaj)"
        return message

# ============================================================================
# 9. ANALİTİKS & İÇGÖRÜLER
# ============================================================================

class AnalyticsEngine:
    """Analitik motoru"""
    
    def __init__(self):
        self.interaction_stats = defaultdict(int)
        self.topic_frequency = defaultdict(int)
        self.mood_stats = defaultdict(list)
    
    def track_interaction(self, user_name: str, topic: str):
        """Etkileşimi takip et"""
        self.interaction_stats[user_name] += 1
        self.topic_frequency[topic] += 1
    
    def get_user_insights(self, user_name: str) -> Dict[str, Any]:
        """Kullanıcı hakkında içgörüler getir"""
        return {
            'total_interactions': self.interaction_stats.get(user_name, 0),
            'favorite_topics': sorted(self.topic_frequency.items(), 
                                    key=lambda x: x[1], reverse=True)[:3],
            'average_mood': 'stable',
            'engagement_level': 'high'
        }

# ============================================================================
# 10. HIZLI ÇÖZÜMLER
# ============================================================================

class QuickSolutions:
    """Hızlı çözümler"""
    
    @staticmethod
    def time_aware_greeting(hour: int, user_name: str = "Kullanıcı") -> str:
        """Zaman-farkındı selamlama"""
        if 5 <= hour < 12:
            return f" Günaydın {user_name}! Yeni bir gün başladı"
        elif 12 <= hour < 17:
            return f" İyi öğleden sonralar {user_name}!"
        elif 17 <= hour < 22:
            return f" İyi akşamlar {user_name}!"
        else:
            return f" Gece geç oldu {user_name}! Dinlenme zamanı"
    
    @staticmethod
    def get_daily_tip() -> str:
        """Günlük ipucu getir"""
        tips = [
            " Sabah 10 dakikalık meditasyon yapabilirsin",
            " Günde en az 2 litre su iç",
            " Kısa yürüyüşler çok etkili",
            " Gece 7-8 saat uyumaya çalış",
            " Akşam ekrandan uzak dur"
        ]
        return random.choice(tips)
    
    @staticmethod
    def get_motivational_quote() -> str:
        """Motivasyonel alıntı getir"""
        quotes = [
            " 'Küçük adımlar büyük başarılara götürür.' - Konfüçyüs",
            " 'Başarı bir yolculuktur, varış noktası değil.'",
            " 'Bugün yapabileceğini yarına erteleme.'",
            " 'Zorluklar seni güçlendirir, zayıflatmaz.'",
            " 'Sen yapabilirsin! Her gün biraz daha iyi ol.'"
        ]
        return random.choice(quotes)
