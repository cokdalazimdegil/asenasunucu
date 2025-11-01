"""
Akıllı Hafıza Yönetim Sistemi
Kullanıcı etkileşimlerini bağlamsal olarak yönetir ve hatırlar
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import re
import logging
import json
from collections import defaultdict

logger = logging.getLogger(__name__)

class IntelligentMemoryManager:
    """Akıllı hafıza yöneticisi"""
    
    def __init__(self, db_path: str = 'asena_memory.db'):
        """Hafıza yöneticisini başlat"""
        self.db_path = db_path
        self.memory_priority = defaultdict(int)
        self.learning_patterns = {}
        self.conversation_contexts = {}
        self._init_database()
    
    def _init_database(self):
        """Veritabanını başlat"""
        try:
            import sqlite3
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Hafızalar tablosu
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_name TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    importance INTEGER DEFAULT 5,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    metadata TEXT
                )
            ''')
            
            # Konuşma geçmişi tablosu
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_name TEXT NOT NULL,
                    message TEXT NOT NULL,
                    response TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    sentiment TEXT,
                    metadata TEXT
                )
            ''')
            
            # Öğrenme kalıpları tablosu
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS learning_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_name TEXT NOT NULL,
                    pattern_type TEXT NOT NULL,
                    pattern_data TEXT NOT NULL,
                    last_used TIMESTAMP,
                    usage_count INTEGER DEFAULT 1,
                    metadata TEXT
                )
            ''')
            
            # İndeksler
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_memories_user ON memories(user_name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(memory_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_patterns_user ON learning_patterns(user_name, pattern_type)')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Veritabanı başlatma hatası: {e}")
    
    def get_contextual_memories(self, user_name: str, current_message: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Mevcut konuşmaya göre en ilgili hafızaları getir"""
        try:
            all_memories = self.get_memories(user_name)
            
            # Mesajdan anahtar kelimeler çıkar
            keywords = self._extract_keywords(current_message)
            
            # Hafızaları puanla
            scored_memories = []
            for memory in all_memories:
                score = self._calculate_relevance_score(memory, keywords, user_name)
                scored_memories.append((score, memory))
            
            # En yüksek puanlıları sırala
            scored_memories.sort(key=lambda x: x[0], reverse=True)
            
            return [mem for score, mem in scored_memories[:limit]]
            
        except Exception as e:
            logger.error(f"Bağlamsal hafıza getirme hatası: {e}")
            return []
    
    def _extract_keywords(self, message: str) -> List[str]:
        """Mesajdan anahtar kelimeler çıkar"""
        if not message:
            return []
            
        # Noktalama işaretlerini kaldır ve küçük harfe çevir
        message = re.sub(r'[^\w\s]', '', message.lower())
        
        # Durdurma kelimeleri
        stop_words = {'ve', 'veya', 'ama', 'ile', 'bir', 'bu', 'şu', 'o', 'de', 'da', 'ki', 'mi', 'mı', 'mu', 'mü', 'ise', 'değil', 'amaçlı'}
        
        # Anahtar kelimeleri çıkar (2 harften uzun olanlar)
        words = [word for word in message.split() if len(word) > 2 and word not in stop_words]
        
        # Tekrarları kaldır
        return list(set(words))
    
    def _calculate_relevance_score(self, memory: Dict[str, Any], keywords: List[str], user_name: str) -> float:
        """Hafızanın mevcut bağlama uygunluk puanı"""
        if not memory or not keywords:
            return 0.0
            
        score = 0.0
        content = str(memory.get('content', '')).lower()
        
        # Anahtar kelime eşleşmeleri
        for keyword in keywords:
            if keyword in content:
                score += 3.0  # Temel puan
                
                # Anahtar kelime tırnak içindeyse veya özel bir vurgu varsa ek puan
                if f'"{keyword}"' in content or f'\'{keyword}\'' in content:
                    score += 2.0
                
                # Anahtar kelime başlık veya başlangıçta geçiyorsa ek puan
                if content.startswith(keyword):
                    score += 1.5
        
        # Hafıza tipi önceliği
        mem_type = memory.get('memory_type', '').lower()
        if mem_type in ['food_preference', 'allergy', 'work_schedule']:
            score += 2.0
        
        # Önem puanı
        importance = float(memory.get('importance', 5.0))
        score += (importance / 10.0) * 2  # 0-2 arasında ek puan
        
        # Güncellik puanı
        updated_at = memory.get('updated_at')
        if updated_at:
            if isinstance(updated_at, str):
                try:
                    updated_at = datetime.fromisoformat(updated_at)
                except (ValueError, TypeError):
                    updated_at = None
            
            if isinstance(updated_at, datetime):
                days_old = (datetime.now() - updated_at).days
                if days_old <= 7:  # Son 7 gün içinde güncellenmişse
                    score += 2.0
                elif days_old <= 30:  # Son 30 gün içindeyse
                    score += 1.0
        
        # Kullanım sıklığı puanı
        usage_count = int(memory.get('usage_count', 0))
        if usage_count > 0:
            score += min(3.0, usage_count * 0.5)  # En fazla 3 puan
        
        return score
    
    def get_memories(self, user_name: str, mem_type: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Kullanıcının hafızalarını getir"""
        try:
            import sqlite3
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = 'SELECT * FROM memories WHERE user_name = ?'
            params = [user_name]
            
            if mem_type:
                query += ' AND memory_type = ?'
                params.append(mem_type)
            
            query += ' ORDER BY updated_at DESC, importance DESC'
            
            if limit > 0:
                query += ' LIMIT ?'
                params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            memories = []
            for row in rows:
                memory = dict(row)
                if 'metadata' in memory and memory['metadata']:
                    try:
                        memory['metadata'] = json.loads(memory['metadata'])
                    except (json.JSONDecodeError, TypeError):
                        memory['metadata'] = {}
                memories.append(memory)
            
            conn.close()
            return memories
            
        except Exception as e:
            logger.error(f"Hafıza getirme hatası: {e}")
            return []
    
    def add_memory(self, user_name: str, memory_type: str, content: str, 
                  importance: int = 5, expires_at: Optional[datetime] = None, 
                  metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Yeni hafıza ekle"""
        try:
            import sqlite3
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Aynı içerik zaten varsa güncelle
            cursor.execute(
                'SELECT id FROM memories WHERE user_name = ? AND content = ?',
                (user_name, content)
            )
            existing = cursor.fetchone()
            
            metadata_str = json.dumps(metadata) if metadata else None
            expires_at_str = expires_at.isoformat() if expires_at else None
            
            if existing:
                # Mevcut kaydı güncelle
                cursor.execute('''
                    UPDATE memories 
                    SET memory_type = ?, importance = ?, updated_at = CURRENT_TIMESTAMP,
                        expires_at = ?, metadata = ?
                    WHERE id = ?
                ''', (memory_type, importance, expires_at_str, metadata_str, existing[0]))
            else:
                # Yeni kayıt ekle
                cursor.execute('''
                    INSERT INTO memories 
                    (user_name, memory_type, content, importance, expires_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (user_name, memory_type, content, importance, expires_at_str, metadata_str))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Hafıza ekleme hatası: {e}")
            return False
    
    def save_conversation(self, user_name: str, message: str, response: str, 
                         sentiment: Optional[Dict[str, Any]] = None) -> bool:
        """Konuşmayı kaydet"""
        try:
            import sqlite3
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            sentiment_str = json.dumps(sentiment) if sentiment else None
            
            cursor.execute('''
                INSERT INTO conversations 
                (user_name, message, response, sentiment)
                VALUES (?, ?, ?, ?)
            ''', (user_name, message, response, sentiment_str))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Konuşma kaydetme hatası: {e}")
            return False
    
    def get_recent_conversations(self, user_name: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Son konuşmaları getir"""
        try:
            import sqlite3
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM conversations 
                WHERE user_name = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (user_name, limit))
            
            rows = cursor.fetchall()
            conversations = [dict(row) for row in rows]
            
            # JSON verilerini parse et
            for conv in conversations:
                if 'sentiment' in conv and conv['sentiment']:
                    try:
                        conv['sentiment'] = json.loads(conv['sentiment'])
                    except (json.JSONDecodeError, TypeError):
                        conv['sentiment'] = None
            
            conn.close()
            return conversations
            
        except Exception as e:
            logger.error(f"Konuşma geçmişi getirme hatası: {e}")
            return []
    
    def learn_from_interaction(self, user_name: str, message: str, response: str, 
                             feedback: Optional[Dict[str, Any]] = None) -> bool:
        """Etkileşimden öğren"""
        try:
            # Konuşmayı kaydet
            self.save_conversation(user_name, message, response)
            
            # Öğrenme kalıplarını güncelle
            self._update_learning_patterns(user_name, message, response, feedback)
            
            # Önemli bilgileri çıkar ve hafızaya al
            self._extract_and_store_important_info(user_name, message, response)
            
            return True
            
        except Exception as e:
            logger.error(f"Öğrenme hatası: {e}")
            return False
    
    def _update_learning_patterns(self, user_name: str, message: str, 
                                 response: str, feedback: Optional[Dict[str, Any]] = None):
        """Öğrenme kalıplarını güncelle"""
        # Basit bir örnek: Mesajdaki anahtar kelimelere göre yanıtları öğren
        keywords = self._extract_keywords(message)
        
        for keyword in keywords:
            if len(keyword) < 4:  # Çok kısa anahtar kelimeleri atla
                continue
                
            # Bu anahtar kelime için öğrenme kalıbını güncelle
            self._update_pattern(user_name, 'keyword_response', keyword, response, feedback)
    
    def _update_pattern(self, user_name: str, pattern_type: str, pattern_key: str, 
                       pattern_data: Any, feedback: Optional[Dict[str, Any]] = None):
        """Öğrenme kalıbını güncelle"""
        try:
            import sqlite3
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Mevcut kalıbı kontrol et
            cursor.execute('''
                SELECT id, pattern_data, usage_count 
                FROM learning_patterns 
                WHERE user_name = ? AND pattern_type = ? AND pattern_data LIKE ?
            ''', (user_name, pattern_type, f'%{pattern_key}%'))
            
            existing = cursor.fetchone()
            
            if existing:
                # Mevcut kalıbı güncelle
                pattern_id, existing_data, count = existing
                
                # Geri bildirime göre öğrenme
                if feedback and feedback.get('is_positive') is False:
                    # Olumsuz geri bildirim: Bu kalıbın kullanımını azalt
                    new_count = max(0, count - 1)
                else:
                    # Olumlu veya nötr geri bildirim: Kullanım sayısını artır
                    new_count = count + 1
                
                cursor.execute('''
                    UPDATE learning_patterns 
                    SET usage_count = ?, last_used = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (new_count, pattern_id))
            else:
                # Yeni kalıp ekle
                cursor.execute('''
                    INSERT INTO learning_patterns 
                    (user_name, pattern_type, pattern_data, last_used, usage_count)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP, 1)
                ''', (user_name, pattern_type, pattern_key))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Öğrenme kalıbı güncelleme hatası: {e}")
    
    def _extract_and_store_important_info(self, user_name: str, message: str, response: str):
        """Mesajdan önemli bilgileri çıkar ve hafızaya al"""
        # Kişisel bilgileri çıkar (örnek: doğum günü, tercihler)
        self._extract_personal_info(user_name, message)
        
        # Planları ve hatırlatmaları çıkar
        self._extract_plans(user_name, message)
        
        # Tercihleri çıkar
        self._extract_preferences(user_name, message)
    
    def _extract_personal_info(self, user_name: str, message: str):
        """Kişisel bilgileri çıkar"""
        # Doğum günü örneği
        import re
        birthday_match = re.search(r'(doğum günüm|yaş günüm|birthday)[\s\w]*\b(\d{1,2})[\s\-\/](\d{1,2})[\s\-\/](\d{4})\b', message, re.IGNORECASE)
        if birthday_match:
            day, month, year = birthday_match.groups()[1:]
            self.add_memory(
                user_name=user_name,
                memory_type='personal_info',
                content=f'Doğum günü: {day}/{month}/{year}',
                importance=8
            )
    
    def _extract_plans(self, user_name: str, message: str):
        """Planları ve hatırlatmaları çıkar"""
        # Basit bir plan çıkarma örneği
        import re
        from datetime import datetime, timedelta
        
        # Bugün/yarın gibi zaman ifadeleri
        time_expr = {
            'bugün': 0,
            'yarın': 1,
            'pazartesi': None,  # Haftanın günleri için özel işlem gerekir
            'salı': None,
            'çarşamba': None,
            'perşembe': None,
            'cuma': None,
            'cumartesi': None,
            'pazar': None
        }
        
        # Plan kalıbını ara
        plan_match = re.search(r'(yarın|bugün|pazartesi|salı|çarşamba|perşembe|cuma|cumartesi|pazar)[^.]*(yapacağım|edeceğim|gideceğim|geleceğim|var|planlıyorum|planladım)', message, re.IGNORECASE)
        if plan_match:
            time_expr = plan_match.group(1).lower()
            plan_text = message[plan_match.start():].strip()
            
            # Planı hafızaya al
            self.add_memory(
                user_name=user_name,
                memory_type='plan',
                content=plan_text,
                importance=7,
                expires_at=datetime.now() + timedelta(days=7)  # 1 hafta geçerli
            )
    
    def _extract_preferences(self, user_name: str, message: str):
        """Tercihleri çıkar"""
        # Yemek tercihleri
        food_prefs = {
            'seviyorum': 1,
            'severim': 1,
            'hoşlanırım': 1,
            'beğenirim': 1,
            'sevmem': -1,
            'hoşlanmam': -1,
            'beğenmem': -1
        }
        
        for word, sentiment in food_prefs.items():
            if word in message.lower():
                # Mesajdaki yemek isimlerini bul (basit bir yaklaşım)
                food_keywords = ['yemek', 'içecek', 'kahve', 'çay', 'tatlı', 'yemeği']
                for food_word in food_keywords:
                    if food_word in message.lower():
                        # Yemek tercihini hafızaya al
                        pref_type = 'food_like' if sentiment > 0 else 'food_dislike'
                        self.add_memory(
                            user_name=user_name,
                            memory_type=pref_type,
                            content=message,
                            importance=6
                        )
                        break

# Global instance
memory_manager = IntelligentMemoryManager()

def get_memory_manager() -> IntelligentMemoryManager:
    """Hafıza yöneticisini döndür"""
    return memory_manager
