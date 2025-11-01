import flask
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
import json
import os
from datetime import datetime, timedelta
import sqlite3
from groq import Groq
from typing import Any
import re
import threading
import time
import asena_hatirlatici
from notifications import send_notification, forward_message
import tv_connect
import logging
import sqlite3
import re
from functools import wraps
from dotenv import load_dotenv
from memory_manager import get_memory_manager
from conversation_summarizer import get_conversation_summarizer
from weather_service import get_weather_service, get_morning_weather
from enhanced_features import (
    ProactiveAssistant, FamilyIntelligence, EnhancedEmotionalIntelligence,
    ConversationIntelligence, SmartHomeControl, SmartScheduler,
    PersonalizationEngine, AnalyticsEngine, QuickSolutions
)
from response_cache import get_response_cache
from advanced_context import get_advanced_context_builder
from tv_manager import get_tv_manager
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

# .env dosyasını yükle
load_dotenv()

# Asena AI Asistanın Kişiliği - DÜZELTILDI
ASENA_PERSONALITY = {
    "name": "Asena",
    "role": "AI Asistan",
    "description": "Yardımcı, anlayışlı ve empatik bir yapay zeka asistanı",
    "capabilities": ["Konuşma", "Hatırlatmalar", "Ev Otomasyonu", "Duygusal Destek", "Planlama"],
}

# Başlangıç hafızası
INITIAL_MEMORIES = {
    "Nuri Can": {
        "kişisel": {
            "yaş": 25,
            "şehir": "İstanbul",
            "ilişki_durumu": "Evli (Rabia ile)",
            "kişilik": ["mantıklı", "meraklı", "teknolojiye düşkün", "analitik düşünmeyi seven"]
        },
        "çalışma": {
            "meslek": "E-Ticaret Uzmanı ve Yazılımcı",
            "çalışma_saatleri": "Hafta içi 09:00 - 18:00",
            "hedef": "Kendi şirketini kurmak",
            "projeler": ["AI Destekli Psikolog Terminali", "Asena Akıllı Ev Asistanı"]
        },
        "hobiler": ["Piyano çalmak", "Felsefe ve astrofizik okumak", "Film izlemek", "Yapay zeka projeleri geliştirmek"],
        "alışkanlıklar": {
            "sabah": "Kahve içmeden güne başlamaz",
            "akşam": "Rabia ile müzik dinlemeyi sever"
        },
        "ilişkiler": {
            "Rabia": "Eşi, hayat arkadaşı ve en yakın dostu",
            "Lina": "Evdeki kedisi, genelde sabah Nuri'nin yanına gelir"
        }
    },
    "Rabia": {
        "kişisel": {
            "yaş": 23,
            "şehir": "Istanbul",
            "ilişki_durumu": "Evli (Nuri Can ile)",
            "kişilik": ["sıcakkanlı", "sabırlı", "enerjik", "çocuklarla iletişimi güçlü"]
        },
        "çalışma": {
            "meslek": "Fitness antrenörü",
            "çalışma_yerleri": ["Maverapark"],
            "çalışma_saatleri": {
                "Pazartesi": "İzinli",
                "Salı": "14:00 - 22:00",
                "Çarşamba": "08:00 - 16:00",
                "Perşembe": "14:00 - 22:00",
                "Cuma": "08:00 - 16:00",
                "Cumartesi": "14:00 - 22:00",
                "Pazar": "08:00 - 16:00"
            }
        },
        "hobiler": ["Ukulele çalmak", "Hobilerle uğraşmak (özellikle el işleri ve müzik)", "Sağlıklı tarifler denemek", "Nuri ile vakit geçirmek"],
        "alışkanlıklar": {
            "sabah": "Genelde erken kalkar ve hafif kahvaltı yapar",
            "akşam": "Dizi izlemeyi veya ukulele çalışmayı sever"
        },
        "ilişkiler": {
            "Nuri Can": "Eşi ve birlikte birçok proje ürettiği kişi"
        }
    }
}

# Groq API anahtarını yükle
try:
    GROQ_API_KEY = os.getenv('GROQ_API_KEY')
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY ortam değişkeninde bulunamadı. Lütfen .env dosyasına Groq API anahtarınızı ekleyin.")
except Exception as e:
    print(f"Hata: {e}")
    raise

# Hatırlatıcı modülüne bildirim fonksiyonunu ilet
asena_hatirlatici.set_notification_callback(send_notification)

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
CORS(app)

# Initialize memory manager and summarizer
memory_manager = get_memory_manager()
conversation_summarizer = get_conversation_summarizer()
response_cache = get_response_cache()
advanced_context_builder = get_advanced_context_builder()

# Initialize new enhanced features
proactive_assistant = ProactiveAssistant()
family_intelligence = FamilyIntelligence()
emotional_intelligence = EnhancedEmotionalIntelligence()
conversation_intelligence = ConversationIntelligence()
smart_home = SmartHomeControl()
smartscheduler = SmartScheduler()
personalization = PersonalizationEngine()
analytics = AnalyticsEngine()
quick_solutions = QuickSolutions()

# UTF-8 Encoding
import sys
import codecs
if sys.stdout.encoding != 'utf-8':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Groq API (Önceki tanımlanmıştır)

def initialize_groq():
    try:
        client = Groq(api_key=GROQ_API_KEY)
        print("Groq API başarıyla yapılandırıldı!")
        return client
    except Exception as e:
        print(f"Groq API başlatılırken hata: {e}")
        raise

try:
    groq_client = initialize_groq()
except Exception as e:
    print(f"Groq client oluşturulamadı: {e}")
    groq_client = None



def load_permanent_memories_to_manager():
    """İNITIAL_MEMORIES'den kalıcı hafızaları memory_manager'a yükle"""
    try:
        for user_name, user_data in INITIAL_MEMORIES.items():
            # Kişisel bilgiler
            if 'kişisel' in user_data:
                personal_info = user_data['kişisel']
                for key, value in personal_info.items():
                    if isinstance(value, list):
                        value = ', '.join(value)
                    memory_manager.add_memory(
                        user_name=user_name,
                        memory_type='personal',
                        content=f"{key}: {value}",
                        importance=8,
                        is_permanent=True
                    )
            
            # Çalışma bilgileri
            if 'çalışma' in user_data:
                work_info = user_data['çalışma']
                for key, value in work_info.items():
                    if isinstance(value, dict):
                        # Çalışma saatleri gibi diçer yapıları string'e dönüştür
                        value = str(value)
                    memory_manager.add_memory(
                        user_name=user_name,
                        memory_type='work',
                        content=f"{key}: {value}",
                        importance=7,
                        is_permanent=True
                    )
            
            # Hobiler
            if 'hobiler' in user_data:
                hobbies = ', '.join(user_data['hobiler'])
                memory_manager.add_memory(
                    user_name=user_name,
                    memory_type='hobby',
                    content=f"Hobiler: {hobbies}",
                    importance=6,
                    is_permanent=True
                )
            
            # İlişkiler
            if 'ilişkiler' in user_data:
                for person, relation in user_data['ilişkiler'].items():
                    memory_manager.add_memory(
                        user_name=user_name,
                        memory_type='relationship',
                        content=f"{person}: {relation}",
                        importance=9,
                        is_permanent=True
                    )
        
        logging.info("Kalıcı hafızalar memory_manager'a yüklendi")
    except Exception as e:
        logging.error(f"Permanent memory yükleme hatası: {e}")

def load_initial_memories():
    """Başlangıç hafızalarını veritabanına yükler - DÜZELTİLMİŞ"""
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # Önce mevcut kayıtları kontrol et
        c.execute("SELECT COUNT(*) FROM memories")
        count = c.fetchone()[0]
        
        if count > 0:
            logging.info(" Hafızalar zaten yüklü")
            return True
        
        logging.info(" Başlangıç hafızaları yükleniyor...")
        
        # Her kullanıcı için
        for user_name, categories in INITIAL_MEMORIES.items():
            logging.info(f" {user_name} için hafızalar yükleniyor...")
            
            # Kişisel bilgiler
            if "kişisel" in categories:
                for key, value in categories["kişisel"].items():
                    if isinstance(value, list):
                        value = ", ".join(value)
                    memory_text = f"{key}: {value}"
                    c.execute(
                        """INSERT OR IGNORE INTO memories 
                        (user_name, memory_type, content, created_at, last_accessed) 
                        VALUES (?, ?, ?, datetime('now'), datetime('now'))""",
                        (user_name, "kişisel", memory_text)
                    )
            
            # Çalışma bilgileri
            if "çalışma" in categories:
                for key, value in categories["çalışma"].items():
                    if key == "çalışma_saatleri":
                        if isinstance(value, dict):
                            # Çalışma saatlerini düzgün formatla
                            schedule_text = ""
                            for day, hours in value.items():
                                schedule_text += f"{day}: {hours}, "
                            schedule_text = schedule_text.rstrip(", ")
                            memory_text = f"Çalışma saatleri: {schedule_text}"
                        else:
                            memory_text = f"Çalışma saatleri: {value}"
                    else:
                        if isinstance(value, list):
                            value = ", ".join(value)
                        memory_text = f"{key}: {value}"
                    
                    c.execute(
                        """INSERT OR IGNORE INTO memories 
                        (user_name, memory_type, content, created_at, last_accessed) 
                        VALUES (?, ?, ?, datetime('now'), datetime('now'))""",
                        (user_name, "çalışma", memory_text)
                    )
            
            # Hobiler
            if "hobiler" in categories:
                hobbies = ", ".join(categories["hobiler"])
                c.execute(
                    """INSERT OR IGNORE INTO memories 
                    (user_name, memory_type, content, created_at, last_accessed) 
                    VALUES (?, ?, ?, datetime('now'), datetime('now'))""",
                    (user_name, "hobiler", f"Hobiler: {hobbies}")
                )
            
            # Alışkanlıklar
            if "alışkanlıklar" in categories:
                for time_of_day, habit in categories["alışkanlıklar"].items():
                    c.execute(
                        """INSERT OR IGNORE INTO memories 
                        (user_name, memory_type, content, created_at, last_accessed) 
                        VALUES (?, ?, ?, datetime('now'), datetime('now'))""",
                        (user_name, "alışkanlık", f"{time_of_day}: {habit}")
                    )
            
            # İlişkiler
            if "ilişkiler" in categories:
                for person, relation in categories["ilişkiler"].items():
                    c.execute(
                        """INSERT OR IGNORE INTO memories 
                        (user_name, memory_type, content, created_at, last_accessed) 
                        VALUES (?, ?, ?, datetime('now'), datetime('now'))""",
                        (user_name, "ilişki", f"{person}: {relation}")
                    )
        
        conn.commit()
        logging.info(" Başlangıç hafızaları başarıyla yüklendi!")
        
        # Kontrol et
        c.execute("SELECT COUNT(*) FROM memories")
        final_count = c.fetchone()[0]
        logging.info(f" Toplam hafıza kaydı: {final_count}")
        
        return True
    except Exception as e:
        logging.error(f" Hafıza yükleme hatası: {e}")
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                pass
        return False
    finally:
        if conn:
            conn.close()

# TV KOMUTLARI İÇİN GLOBAL HANDLER
import tv_connect
TV_IP = '192.168.1.23'
tv_manager = get_tv_manager(TV_IP)

def handle_tv_command(message):
    msg = message.lower()
    import re
    
    # ... existing code ...
    if any(kw in msg for kw in ["sesini aç", "sesi aç"]):
        tv_manager.connect()
        tv_manager.volume_up(3)
        return "Televizyonun sesi açılıyor."
    if any(kw in msg for kw in ["sesini kapat", "sesi kapat"]):
        tv_manager.connect()
        tv_manager.volume_down(3)
        return "Televizyonun sesi kısılıyor."
    if any(kw in msg for kw in ["sessize", "mute"]):
        tv_manager.connect()
        tv_manager.mute()
        return "Televizyonun sesi tamamen kapatıldı."
    # ... x'e getir, yarıya getir, yüzde ...'ye getir gibi ---
    # "15'e getir", "yirmiye getir", "yarıya getir", "%70'e getir" gibi
    max_level = 30
    # Rakam ve sayı metinleri
    numwords = {"sıfır":0,"bir":1,"iki":2,"üç":3,"dört":4,"beş":5,"altı":6,"yedi":7,"sekiz":8,"dokuz":9,"on":10,"onbir":11,"oniki":12,"onüç":13,"ondört":14,"onbeş":15,"onaltı":16,"onyedi":17,"onseki":18,"ondokuz":19,"yirmi":20,"yirmi bir":21,"yirmibir":21,"yirmi iki":22,"yirmi üç":23,"yirmi dört":24,"yirmi beş":25,"otuz":30}
    # Önce basit regex ile sayı bul
    match_num = re.search(r'(\d{1,2})[ \'"]*([a-zçşıöüğ]*)(?:e getir| e getir| ye getir| yap| olsun| seviye| ayarla)', msg)
    if match_num:
        level = int(match_num.group(1))
        if level > max_level: level = max_level
        tv_manager.connect()
        tv_manager.set_volume(level)
        return f"Televizyonun sesi {level} seviyesine ayarlandı."
    # Metin sayılarını yakala
    for w in numwords:
        if w in msg and any(x in msg for x in ["e getir","ye getir","seviye","yap","olsun"]):
            tv_manager.connect()
            lvl = numwords[w]
            tv_manager.set_volume(lvl)
            return f"Televizyonun sesi {lvl} seviyesine ayarlandı."
    # Yarıya getir:
    if "yarıya getir" in msg:
        tv_manager.connect()
        tv_manager.set_volume(max_level//2)
        return "Televizyonun sesi yarıya getirildi."
    mpc = re.search(r'%\s*(\d+)[^\d]*?getir', msg)
    if mpc: # yüzde komutu
        percent = int(mpc.group(1))
        if percent > 100: percent = 100
        level = int(round(max_level * percent / 100))
        tv_manager.connect()
        tv_manager.set_volume(level)
        return f"Televizyonun sesi %{percent} seviyesine getirildi."
    if any(kw in msg for kw in ['tv aç', 'televizyon aç', 'televizyonu aç']):
        tv_manager.power_on()
        return 'TV açılıyor.'
    if any(kw in msg for kw in ['tv kapat', 'televizyon kapat', 'televizyonu kapat']):
        tv_manager.power_off()
        return 'TV kapatılıyor.'
    if 'netflix' in msg:
        tv_manager.connect()
        tv_manager.open_app('netflix')
        return 'Netflix açılıyor.'
    if 'hbo' in msg or 'hbomax' in msg or 'hbo max' in msg:
        tv_manager.connect()
        tv_manager.open_app('hbo')
        return 'HBO Max açılıyor.'
    # YouTube araması
    if 'youtube' in msg:
        import re
        find = re.search(r'youtube[^ - ]*?(.*) aç', msg)
        query = None
        if find:
            query = find.group(1).strip()
        else:
            idx = msg.find('youtube')
            after = msg[idx+7:]
            if 'aç' in after:
                query = after.replace('aç','').strip()
        tv_manager.connect()
        if query:
            tv_manager.youtube_search(query)
            return f'YouTube açılıyor, arama: {query}'
        else:
            tv_manager.open_app('youtube')
            return 'YouTube açılıyor.'
    return None

db_lock = threading.Lock()

def with_db_lock(func):
    """Decorator for thread-safe DB operations"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        with db_lock:
            return func(*args, **kwargs)
    return wrapper

def get_db_connection():
    """Thread-safe veritabanı bağlantısı"""
    conn = sqlite3.connect('asena_memory.db', timeout=30.0, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn

@with_db_lock
def init_db():
    """GÜVENLİ veritabanı başlatma"""
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # Tabloları sırayla oluştur
        tables = {
            'conversations': '''
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_name TEXT NOT NULL,
                    message TEXT NOT NULL,
                    response TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )''',
            'reminders': '''
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_name TEXT NOT NULL,
                    target_user TEXT,
                    content TEXT NOT NULL,
                    reminder_time TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    notification_count INTEGER DEFAULT 0,
                    notified INTEGER DEFAULT 0
                )''',
            'memories': '''
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_name TEXT NOT NULL,
                    memory_type TEXT DEFAULT 'general',
                    content TEXT NOT NULL,
                    importance INTEGER DEFAULT 5,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    last_accessed TEXT DEFAULT CURRENT_TIMESTAMP,
                    access_count INTEGER DEFAULT 1,
                    context_hash TEXT,
                    is_permanent BOOLEAN DEFAULT 0,
                    UNIQUE(user_name, content)
                )''',
            'devices': '''
                CREATE TABLE IF NOT EXISTS devices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_name TEXT NOT NULL,
                    device_id TEXT UNIQUE NOT NULL,
                    push_token TEXT NOT NULL,
                    last_seen TEXT DEFAULT CURRENT_TIMESTAMP,
                    registered_at TEXT DEFAULT CURRENT_TIMESTAMP
                )'''
        }
        
        for table_name, table_sql in tables.items():
            try:
                c.execute(table_sql)
                logging.info(f" Tablo oluşturuldu: {table_name}")
            except sqlite3.Error as e:
                logging.error(f" Tablo hatası {table_name}: {e}")
        
        conn.commit()
        
        # Tablo varlığını doğrula
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in c.fetchall()]
        logging.info(f" Mevcut tablolar: {existing_tables}")
        
    except sqlite3.Error as e:
        logging.error(f" Veritabanı hatası: {e}")
        raise
    finally:
        if conn:
            conn.close()

def ensure_database():
    """Veritabanının varlığından emin ol ve gerekirse başlangıç verilerini yükle"""
    db_exists = os.path.exists('asena_memory.db')
    
    # Veritabanı yoksa veya tablolar eksikse oluştur
    if not db_exists:
        logging.info(" Veritabanı oluşturuluyor...")
        init_db()
        logging.info(" Veritabanı oluşturuldu.")
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        required_tables = ['conversations', 'reminders', 'memories']
        missing_tables = [t for t in required_tables if t not in tables]
        
        if missing_tables:
            logging.info(f" Eksik tablolar oluşturuluyor: {missing_tables}")
            init_db()
            logging.info(" Eksik tablolar oluşturuldu.")
        
        # İlk kurulumda veya tablolar yeni oluşturulduysa başlangıç verilerini yükle
        if not db_exists or missing_tables:
            logging.info(" Başlangıç hafızaları yükleniyor...")
            if load_initial_memories():
                logging.info(" Başlangıç hafızaları başarıyla yüklendi.")
            else:
                logging.warning(" Başlangıç hafızaları yüklenirken hata oluştu.")
        
        # Kalıcı hafızaları memory_manager'a da yükle
        load_permanent_memories_to_manager()
    except Exception as e:
        logging.error(f" Veritabanı hatası: {e}")
        raise
    finally:
        if conn:
            conn.close()
def save_reminder(user_name, content, reminder_time, target_user=None):
    """
    Kullanıcı için hatırlatma oluşturur - DÜZELTİLMİŞ
    """
    # Parametre validasyonu
    if not user_name or not str(user_name).strip():
        logging.error("Hata: Kullanıcı adı boş olamaz")
        return False, "Hata: Kullanıcı adı boş olamaz"
        
    if not content or not str(content).strip():
        logging.error(f"Hata: Boş içerikli hatırlatma oluşturulamaz - Kullanıcı: {user_name}")
        return False, "Hata: Hatırlatma içeriği boş olamaz"
        
    if not reminder_time:
        logging.error(f"Hata: Hatırlatma zamanı belirtilmedi - Kullanıcı: {user_name}")
        return False, "Hata: Hatırlatma zamanı belirtilmedi"
    
    try:
        conn = get_db_connection()
        c = conn.cursor()
        now = datetime.now().isoformat()
        
        # Kullanıcı adını ve içeriği temizle
        user_name = str(user_name).strip()
        content = str(content).strip()
        
        # Kullanıcı adlarını standartlaştır
        user_name = 'Nuri Can' if user_name.lower() == 'nuri can' else 'Rabia' if user_name.lower() == 'rabia' else user_name
        
        # Hedef kullanıcı işlemleri
        if target_user and str(target_user).strip():
            target_user = str(target_user).strip()
            target_user = 'Nuri Can' if target_user.lower() == 'nuri can' else 'Rabia' if target_user.lower() == 'rabia' else target_user
            
            # İçerikteki kişi zamirlerini düzelt
            if 'bana' in content.lower():
                content = content.replace('bana', 'sana').replace('Bana', 'Sana')
            if 'ben' in content.lower():
                content = re.sub(r'\b(?:ben|Ben)\b', 'sen' if target_user.lower() == 'nuri can' else 'siz', content)
            
            # Eğer içerik bir eylem içeriyorsa, daha doğal hale getir
            action_verbs = ['yap', 'et', 'hatırlat', 'git', 'gel', 'al', 'ver', 'bak', 'ara']
            if not any(verb in content.lower() for verb in action_verbs) and not content.endswith(('.', '!', '?')):
                content = content + ' yap'
        
        # Veritabanına kaydet
        params = (user_name, content, reminder_time, target_user, now)
        logging.info(f'INSERT reminders params: {params}')
        
        c.execute("""
        INSERT INTO reminders (user_name, content, reminder_time, target_user, created_at)
        VALUES (?, ?, ?, ?, ?)
        """, params)
        
        reminder_id = c.lastrowid
        conn.commit()
        conn.close()
        
        # Bildirim mesajını oluştur
        reminder_time_str = datetime.fromisoformat(reminder_time).strftime('%d.%m.%Y %H:%M')
        
        if target_user and target_user.lower() != user_name.lower():
            # Başkasına hatırlatma bırakılıyorsa
            # Mesajı düzenle
            if content.startswith('bana '):
                content = content[4:].strip().capitalize()
            
            if content.endswith('.'):
                content = content[:-1]
            
            # HEDEF KULLANICIYA gönderilecek mesaj - DÜZELTİLDİ
            notification_msg = f"{user_name} diyor ki: \"{content}\""
            
            # Eğer bir eylem içeriyorsa daha kişisel hale getir
            action_verbs = ['yap', 'et', 'hatırlat', 'git', 'gel', 'al', 'ver', 'bak', 'ara']
            if any(verb in content.lower() for verb in action_verbs):
                notification_msg = f"{user_name} şunları yapmanı istiyor: {content}"
            
            # HEDEF KULLANICIYA bildirim gönder - DÜZELTİLDİ
            send_notification(
                user_name=target_user,  # Bu satır değişti - artık target_user'e gidecek
                message=notification_msg,
                title=f"{user_name}'dan Mesajın Var",
                priority=3,
                tags=["speech_balloon"]
            )
            
            # Ayrıca hatırlatma bırakan kişiye de bilgi ver
            send_notification(
                user_name=user_name,
                message=f"{target_user} için hatırlatma oluşturuldu:\n\n{content}\n\n⏰ {reminder_time_str}",
                title="Hatırlatma Ayarlandı",
                priority=2,
                tags=["white_check_mark"]
            )
        else:
            # Kendi kendine hatırlatma
            send_notification(
                user_name=user_name,
                message=f"Hatırlatma oluşturuldu:\n\n{content}\n\nZaman: {reminder_time_str}",
                title="Hatırlatma Ayarlandı",
                priority=2,
                tags=["alarm_clock"]
            )
            
        return reminder_id
    except Exception as e:
        logging.error(f'save_reminder error: {type(e).__name__}: {e}')
        raise

def get_due_reminders(user_name):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        now = datetime.now().isoformat()
        logging.info(f'GET reminders for {user_name} at {now}')
        c.execute("""
        SELECT id, content, user_name 
        FROM reminders 
        WHERE (user_name = ? OR target_user = ?) 
        AND reminder_time <= ? 
        AND (notified = 0 OR notified IS NULL)
    """, (user_name, user_name, now))
        reminders = c.fetchall()
        for reminder in reminders:
            c.execute("UPDATE reminders SET notified = 1 WHERE id = ?", (reminder[0],))
        conn.commit()
        conn.close()
        return reminders
    except Exception as e:
        logging.error(f'get_due_reminders error: {type(e).__name__}: {e}')
        raise

def mark_reminder_notified(reminder_id):
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # Hatırlatma bilgilerini al
        c.execute("SELECT user_name, content, reminder_time FROM reminders WHERE id = ?", (reminder_id,))
        reminder = c.fetchone()
        
        if not reminder:
            logging.warning(f"mark_reminder_notified: {reminder_id} ID'li hatırlatma bulunamadı")
            return
            
        user_name, content, reminder_time = reminder
        now = datetime.now().isoformat()
        
        # Hatırlatmayı işaretle
        c.execute("UPDATE reminders SET notified = 1 WHERE id = ?", 
                 (reminder_id,))
        conn.commit()
        
        # Zamanı formatla
        reminder_time_dt = datetime.fromisoformat(reminder_time)
        reminder_time_str = reminder_time_dt.strftime('%d.%m.%Y %H:%M')
        
        # Mesajı oluştur
        time_left = ""
        time_diff = (reminder_time_dt - datetime.now()).total_seconds()
        
        if time_diff > 0:  # Gelecekteki hatırlatma
            days = int(time_diff // (24 * 3600))
            hours = int((time_diff % (24 * 3600)) // 3600)
            
            time_parts: list[str] = []
            if days > 0:
                time_parts.append(f"{days} gün")
            if hours > 0 or not time_parts:
                time_parts.append(f"{hours} saat")
                
            time_left = f" (Kalan süre: {', '.join(time_parts)})"
        
        # Bildirimi gönder
        notification_title = "Hatırlatma Zamanı!" 
        if datetime.now() < reminder_time_dt:
            notification_title = "Yaklaşan Hatırlatma"
            
        send_notification(
            user_name=user_name,
            message=f"{content}\nZaman: {reminder_time_str}{time_left}",
            title=notification_title,
            priority=4,
            tags=["alarm_clock"]
        )
        
    except Exception as e:
        logging.error(f'mark_reminder_notified error: {type(e).__name__}: {e}')
        import traceback
        logging.error(traceback.format_exc())
        
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass

# Arka plan thread ile hatırlatmaları kontrol et (opsiyonel, konsola yazdırır)
def reminder_checker():
    while True:
        time.sleep(60)  # Her dakika kontrol
        try:
            # Tüm kullanıcılar için tek seferde kontrol et
            conn = get_db_connection()
            c = conn.cursor()
            now = datetime.now().isoformat()
            
            # Vadesi gelen tüm hatırlatmaları al
            c.execute("""
                SELECT id, user_name, content, target_user 
                FROM reminders 
                WHERE reminder_time <= ? 
                AND (notified = 0 OR notified IS NULL)
            """, (now,))
            
            reminders = c.fetchall()
            
            for reminder in reminders:
                rid, creator, content, target_user = reminder
                
                # Boş içerik kontrolü
                if not content or not str(content).strip():
                    logging.warning(f"Boş içerikli hatırlatma atlandı (ID: {rid})")
                    mark_reminder_notified(rid)  # Boş hatırlatmayı işaretle
                    continue
                
                # Kullanıcı adlarını düzgün bir şekilde formatla
                creator = 'Nuri Can' if creator and str(creator).lower() == 'nuri can' else 'Rabia' if creator and str(creator).lower() == 'rabia' else creator
                
                # HEDEF KULLANICIYI DOĞRU BELİRLE
                if target_user and str(target_user).strip():
                    target_user = 'Nuri Can' if str(target_user).lower() == 'nuri can' else 'Rabia' if str(target_user).lower() == 'rabia' else target_user
                    notify_user = target_user
                    
                    # Mesajı hedef kullanıcı için formatla
                    content = str(content).strip()
                    if any(verb in content.lower() for verb in ['yap', 'et', 'git', 'gel', 'al', 'ver', 'bak', 'ara', 'hazırla']):
                        if creator.lower() == 'nuri can' and 'nuri' not in content.lower():
                            message = f"Nuri Can: {content}"
                        elif creator.lower() == 'rabia' and 'rabia' not in content.lower():
                            message = f"Rabia: {content}"
                        else:
                            message = content
                    else:
                        message = f"{creator}: {content}"
                    
                    title = f"{creator}'dan Hatırlatma"
                else:
                    # Kendi kendine hatırlatma
                    notify_user = creator
                    message = f"Hatırlatma: {content}"
                    title = "Hatırlatma"
                
                logging.info(f"Bildirim hazırlanıyor: {creator} -> {notify_user} - {message}")
                
                # BİLDİRİMİ DOĞRU KULLANICIYA GÖNDER - DÜZELTİLDİ
                try:
                    logging.info(f"Bildirim gönderiliyor: {notify_user} için - {message}")
                    send_notification(
                        user_name=notify_user,  # Hedef kullanıcıya gönder
                        message=message,
                        title=title,
                        priority=4,
                        tags=["bell"]
                    )
                    mark_reminder_notified(rid)
                    logging.info(f"Hatırlatma gönderildi: {notify_user} için {content}")
                except Exception as e:
                    logging.error(f"Bildirim gönderilirken hata (ID: {rid}): {e}")
                    
            conn.close()
            
        except Exception as e:
            logging.error(f"Hatırlatıcı kontrolü sırasında hata: {e}")
            time.sleep(10)  # Hata durumunda 10 saniye bekle

# Hatırlatıcı thread'ini başlat
threading.Thread(target=reminder_checker, daemon=True).start()

# === BILDIRIM FONKSIYONLARI ===
# Bildirim fonksiyonları artık notifications.py modülünde

# === YARDIMCI FONKSİYONLARI ===
def save_conversation(user_name, message, response):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO conversations (user_name, message, response, timestamp) VALUES (?, ?, ?, ?)",
              (user_name, message, response, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_recent_conversations(user_name, limit=5):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""SELECT message, response, timestamp FROM conversations 
                 WHERE user_name = ? 
                 ORDER BY timestamp DESC LIMIT ?""", (user_name, limit))
    results = c.fetchall()
    conn.close()
    return [(msg, resp, ts) for msg, resp, ts in reversed(results)]

def get_memories(user_name, mem_type=None):
    """Kullanıcı için hafızaları getir - GÜNCELLENDİ"""
    if not user_name:
        return []
    
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # 1. Kullanıcının kendi hafızalarını al
        query = "SELECT id, user_name, memory_type, content, created_at FROM memories WHERE user_name = ?"
        query_params = [user_name]
        
        if mem_type:
            query += " AND memory_type = ?"
            query_params.append(mem_type)
        
        query += " ORDER BY created_at DESC LIMIT 50"
        c.execute(query, query_params)
        db_results = c.fetchall()
        
        # Hafızaları formatla
        memories = []
        for mem_id, mem_user, mem_type, content, created_at in db_results:
            try:
                # JSON içeriği parse et
                if isinstance(content, str) and (content.startswith('{') or content.startswith('[')):
                    try:
                        content = json.loads(content)
                    except json.JSONDecodeError:
                        pass
                
                memory = {
                    'id': mem_id,
                    'user_name': mem_user,
                    'memory_type': mem_type,
                    'content': content,
                    'created_at': created_at
                }
                memories.append(memory)
            except Exception as e:
                logging.error(f"Hafıza işlenirken hata (ID: {mem_id}): {e}")
        
        return memories
        
    except sqlite3.Error as e:
        logging.error(f"Veritabanı hatası (get_memories): {e}")
        return []
    except Exception as e:
        logging.error(f"Beklenmeyen hata (get_memories): {e}")
        return []
    finally:
        if conn:
            conn.close()

def update_or_create_memory(user_name, mem_type, content):
    conn = get_db_connection()
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute("SELECT id FROM memories WHERE user_name = ? AND memory_type = ?", (user_name, mem_type))
    row = c.fetchone()
    if row:
        c.execute("UPDATE memories SET content = ? WHERE id = ?", (content, row[0]))
    else:
        c.execute("INSERT INTO memories (user_name, memory_type, content, created_at) VALUES (?, ?, ?, ?)",
                  (user_name, mem_type, content, now))
    conn.commit()
    conn.close()

def extract_learnable_info(user_name, message):
    """Öğrenilebilir bilgileri çıkar ve kalıcı hafızaya ekle"""
    message_lower = message.lower()
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    tomorrow = (now + timedelta(days=1)).strftime("%Y-%m-%d")
    yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")

    # Hayvan bilgileri - Negatif durumlar (artık yok)
    if any(phrase in message_lower for phrase in ['lina yok', 'kedimiz yok', 'kedisi yok', 'lina gitti', 'lina öldü']):
        # Lina hakkında tüm hafızaları sil
        logging.info(f"Lina hakkındaki hafızalar temizleniyor")
        try:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("DELETE FROM memories WHERE user_name = ? AND content LIKE ?", (user_name, '%Lina%'))
            c.execute("DELETE FROM memories WHERE user_name = ? AND content LIKE ?", (user_name, '%kedi%'))
            conn.commit()
            conn.close()
        except Exception as e:
            logging.error(f"Hafıza silme hatası: {e}")

    # Alerji bilgileri - Kalıcı
    if any(word in message_lower for word in ['alerjim var', 'alerjimiz var', 'alerjim oldu', 'yiyemem', 'içemem']):
        # Alerji bilgisini belirle
        allergy_info = message.strip()
        memory_manager.add_memory(
            user_name=user_name,
            memory_type='allergy',
            content=allergy_info,
            importance=9,  # Yüksek önemlilik
            is_permanent=True
        )
        logging.info(f"Alerji bilgisi kaydedildi: {allergy_info}")

    # Yemek tercihleri - Kalıcı
    if any(verb in message_lower for verb in ['seviyor', 'bayılıyor', 'hoşlanıyor', 'sever', 'bayılır', 'hoşlanır', 'seviyorum', 'seviyoruz']):
        if any(food in message_lower for food in ['yemek', 'yiyecek', 'içecek', 'içki', 'tatlı', 'kahve', 'çay', 'meyve', 'sebze', 'et', 'balık']):
            # Kiş i tercihi
            person = 'Rabia' if 'rabia' in message_lower else 'Nuri Can' if 'nuri' in message_lower else user_name
            preference_info = message.strip()
            memory_manager.add_memory(
                user_name=person,
                memory_type='food_preference',
                content=preference_info,
                importance=7,
                is_permanent=True
            )
            logging.info(f"Yemek tercihi kaydedildi: {preference_info}")

    # Hayvan bilgileri - Kalıcı
    if any(word in message_lower for word in ['köpek', 'kedi', 'kuş', 'balık', 'tavşan', 'hamster', 'lina', 'havlayan', 'tırmalayan']):
        if 'var' in message_lower or 'aldık' in message_lower or 'sahibiz' in message_lower:
            pet_info = message.strip()
            memory_manager.add_memory(
                user_name=user_name,
                memory_type='pet',
                content=pet_info,
                importance=8,
                is_permanent=True
            )
            logging.info(f"Evcil hayvan bilgisi kaydedildi: {pet_info}")

    # İlişki bilgileri - Kalıcı
    if any(word in message_lower for word in ['eşim', 'nişanım', 'erkek arkadaşım', 'kız arkadaşım', 'evli', 'nişanlı', 'flörtü']):
        relationship_info = message.strip()
        memory_manager.add_memory(
            user_name=user_name,
            memory_type='relationship',
            content=relationship_info,
            importance=9,
            is_permanent=True
        )
        logging.info(f"İlişki bilgisi kaydedildi: {relationship_info}")

    # Çalışma durumu - Kalıcı
    if any(word in message_lower for word in ['işe gidiyorum', 'çalışıyorum', 'meslek', 'antrenör', 'uzman', 'mühendis', 'doktor', 'öğretmen']):
        if 'değilim' not in message_lower and 'artık' not in message_lower:
            work_info = message.strip()
            memory_manager.add_memory(
                user_name=user_name,
                memory_type='work',
                content=work_info,
                importance=7,
                is_permanent=True
            )
            logging.info(f"Çalışma bilgisi kaydedildi: {work_info}")

    # Zamanlı planlar - Geçici
    if any(word in message_lower for word in ['yarın', 'yarınki', 'yarına']):
        memory_manager.add_memory(
            user_name=user_name,
            memory_type='plan',
            content=f"[YARIN] {message}",
            importance=5,
            is_permanent=False
        )
    elif any(word in message_lower for word in ['bugün', 'bu akşam', 'bu gece', 'şu an']):
        memory_manager.add_memory(
            user_name=user_name,
            memory_type='plan',
            content=f"[BUGÜN] {message}",
            importance=6,
            is_permanent=False
        )

    # Hatırlatma tespiti (basit: "bana [zaman] [içerik] hatırlat" veya "rabia/nuri için [içerik] hatırlat")
    if 'hatırlat' in message_lower:
        # Hedef kullanıcıyı belirle (eğer "X için hatırlat" şeklinde ise)
        target_user = None
        target_match = re.search(r'(rabia|nuri|nuri can|nuri can\')?(?: için| en)? .*?hatırlat', message_lower)
        
        if 'rabia' in message_lower and 'rabia için' in message_lower:
            target_user = 'Rabia'
        elif 'nuri' in message_lower and ('nuri için' in message_lower or 'nuri can için' in message_lower):
            target_user = 'Nuri Can'
        
        # Zamanı bul
        time_match = re.search(r'(\d{1,2}):(\d{2})', message)  # Saat:dk
        if time_match:
            hour, minute = time_match.groups()
            due = now.replace(hour=int(hour), minute=int(minute)).isoformat()
        else:
            due = (now + timedelta(hours=1)).isoformat()  # Varsayılan 1 saat sonrası
        
        # İçeriği çıkar - HAT İRLATMA KÖLİMESİNDEN SONRA GELEN METNİ AL
        # "Rabia için hatırlatma kurar mısın X" şeklinde - X'i çıkar
        
        # Hatırlat kelimesi pattern'i - tüm varyasyonları yakala
        hatirlatma_pattern = r'hat[ıı]rlat(?:[am]*[ıı]*\s*(?:m[ıı]s[ıı]n|misin|musun|m[ıı]sin)?|mays[ıı]|mas[ıı]|mak)?(?:\s+(?:kurar|kur|edeyim|et|ede|edin)(?:\s+(?:m[ıı]s[ıı]n|misin|musun|m[ıı]sin)?)?)?'
        
        # İçeriği çıkar
        content = ""
        if 'için' in message_lower:
            # "X için Y hatırlat" şeklinde çalış
            parts = message.split('için')
            if len(parts) > 1:
                # "için" sonrası kısım
                after_for = parts[1].strip()
                
                # Hatırlatma pattern'ini ara
                match = re.search(hatirlatma_pattern, after_for, flags=re.IGNORECASE)
                if match:
                    # Hatırlatma kelimesinin BİTİŞİNDEN sonrası
                    end_pos = match.end()
                    content = after_for[end_pos:].strip()
                else:
                    # Eğer pattern bulunamazsa, hatırlatma kelimesini ara
                    if 'hatırlat' in after_for.lower():
                        parts2 = re.split(r'hatırlat\w*', after_for, maxsplit=1, flags=re.IGNORECASE)
                        # Hatırlatmadan sonraki metni al
                        if len(parts2) > 1:
                            content = parts2[1].strip()
        else:
            # "Y hatırlat" şeklinde çalış
            # Hatırlatma pattern'ini ara
            match = re.search(hatirlatma_pattern, message, flags=re.IGNORECASE)
            if match:
                # Hatırlatma kelimesinin BİTİŞİNDEN sonrası
                end_pos = match.end()
                content = message[end_pos:].strip()
            else:
                # Eğer pattern bulunamazsa, hatırlatma kelimesini ara
                if 'hatırlat' in message_lower:
                    parts2 = re.split(r'hatırlat\w*', message, maxsplit=1, flags=re.IGNORECASE)
                    # Hatırlatmadan sonraki metni al
                    if len(parts2) > 1:
                        content = parts2[1].strip()
        
        # İçerik boş ise uyarı ver ve devam etme
        if not content:
            logging.warning(f"Hatırlatma içeriği boş çıktı: '{message}'")
            return

        # Hatırlatmayı kaydet
        try:
            save_reminder(user_name, content, due, target_user=target_user)
        except Exception as e:
            logging.error(f"Hatırlatma kaydı hatası: {e}")

# === ZAMAN FONKSİYONLARI ===
def get_time_context():
    now = datetime.now()
    hour = now.hour
    weekday = now.weekday()
    day_name = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"][weekday]

    time_of_day = "sabah" if 5 <= hour < 12 else "öğlen" if 12 <= hour < 17 else "akşam" if 17 <= hour < 22 else "gece"
    return {
        "time": now.strftime("%H:%M"),
        "date": now.strftime("%d.%m.%Y"),
        "day": day_name,
        "time_of_day": time_of_day,
        "is_weekend": weekday >= 5
    }

# === BAĞLAM OLUŞTURMA ===
def build_context_prompt(user_name: str, user_message: str) -> str:
    """GÜNCELLENMİŞ - Gelişmiş bağlam oluşturucu
    
    Args:
        user_name: Kullanıcı adı
        user_message: Kullanıcı mesajı
        
    Returns:
        str: Hazırlanmış bağlam metni
    """
    time_ctx = get_time_context()
    
    # Son konuşmaları getir
    recent_convs = get_recent_conversations(user_name, limit=3)
    
    # Eski fonksiyondan hafızaları getir (geçici destek)
    relevant_memories = get_memories(user_name)
    
    # Kalıcı hafızaları memory_manager'dan getir
    permanent_memories = memory_manager.get_relevant_memories(
        user_name=user_name,
        limit=10,
        memory_types=['allergy', 'food_preference', 'pet', 'relationship', 'work']
    )
    
    # Bağlam bölümlerini oluştur
    context_sections = []
    
    # 1. Zaman bilgisi
    context_sections.append(
        f"ŞU AN: {time_ctx['date']} {time_ctx['day']}, {time_ctx['time']} ({time_ctx['time_of_day']})"
    )
    
    # 2. Kalıcı hafızalar (özel bilgiler)
    if permanent_memories:
        permanent_text = "\n".join([
            f"- {mem.get('content', '')}" 
            for mem in permanent_memories
            if mem.get('content')
        ])
        if permanent_text:
            context_sections.append("KALICI HAFIZA (ÖNEMLİ BİLGİLER):\n" + permanent_text)
    
    # 3. İlgili hafızalar (eski sistem - graduel olarak kaldırılacak)
    if relevant_memories:
        mem_text = "\n".join([
            f"- {mem.get('content', '')}" 
            for mem in relevant_memories[:3]
            if mem.get('content')
        ])
        if mem_text:
            context_sections.append("İLGİLİ HAFIZALAR:\n" + mem_text)
    
    # 4. Son konuşmalar
    if recent_convs:
        conv_text = "\n".join([
            f"- {conv[0]}"
            for conv in recent_convs[-2:]
        ])
        if conv_text:
            context_sections.append("SON KONUŞMALAR:\n" + conv_text)
    
    # Tüm bağlamı birleştir
    context = "\n\n".join(context_sections)
    
    # Sistem prompt'u oluştur
    system_prompt = f"""Merhaba! Ben Asena, Nuri Can ve Rabia'nın ev asistanıyım.

KİMLİK VE ROL:
- Ben bir yapay zeka asistanıyım. Nuri Can veya Rabia değilim.
- Sadece asistanı olarak görev yapıyorum.
- Asistanlık dışında başka bir kimliğe sahip değilim.

BAĞLAM BİLGİLERİ:
{context}

NASIL KONUŞMALIYIM:
1. Doğal ve samimi bir dille konuş
2. Gereksiz resmiyetten kaçın
3. Kısa ve öz yanıtlar ver
4. EMOJİ KULLANMA! Hiç emoji kullanma!
5. Eğer bir konuda bilgin yoksa dürüstçe söyle
6. Sadece bildiklerinden bahset, kurgu yapma.
7. Türkçe'yi doğru kullan
8. Eğer kalıcı hafızada bir bilgi güncellenirse (örneğin alerjiler, tercihler), o bilgiyi hatırla ve eskileri unut
"""
    
    return system_prompt

# === GROQ SORGUSU ===
def safe_turkish_text(text):
    """Türkçe metin güvenliği"""
    if not text:
        return ""
    
    # UTF-8 garantisi
    if isinstance(text, bytes):
        text = text.decode('utf-8')
    
    # Temel temizlik
    text = re.sub(r'[^\w\sçğıöşüÇĞİÖŞÜ.,!?-]', '', text)
    return text.strip()

def filter_hallucinations(ai_response: str, user_name: str, user_message: str) -> str:
    """Hafif halüsinasyon filtresi - Sadece ciddi hataları engelle
    
    Args:
        ai_response: AI'nın ürettiği yanıt
        user_name: Kullanıcı adı
        user_message: Kullanıcı mesajı
        
    Returns:
        str: Filtrelenmiş yanıt
    """
    if not ai_response:
        return "Üzgünüm, bir yanıt oluşturamadım."
    
    response_lower = ai_response.lower()
    
    # SADECE KRİTİK KİMLİK KARMAŞASINI ENGELLE
    # "Ben Nuri Can" veya "Ben Rabia" gibi açık kimlik karmaşası
    identity_confusion_patterns = [
        r'^ben\s+(nuri|rabia)\s+',  # "Ben Nuri" ile başlayan
        r'\sben\s+(nuri|rabia)\.',  # "ben Nuri." diyen
        r'benim\s+adım\s+(nuri|rabia)',  # "Benim adım Nuri"
        r'ben\s+de\s+(nuri|rabia)',  # "Ben de Nuri"
    ]
    
    for pattern in identity_confusion_patterns:
        if re.search(pattern, response_lower):
            logging.warning(f"Kimlik karmaşası engellendi: {pattern}")
            return "Özür dilerim, ben Asena'yım, sizin asistanınız. Size nasıl yardımcı olabilirim?"
    
    # Yanıt çok uzunsa kısalt (halüsinasyon değil, sadece uzun)
    if len(ai_response) > 600:
        return ai_response[:400] + "..."
    
    return ai_response

def analyze_conversation_style(user_message: str) -> dict:
    """Kullanıcının konuşma tarzını analiz et
    
    Args:
        user_message: Kullanıcı mesajı
        
    Returns:
        dict: Konuşma tarzı özellikleri
    """
    msg_lower = user_message.lower()
    
    style = {
        'formality': 'casual',  # casual, formal, friendly
        'length': 'short',      # short, medium, long
        'tone': 'neutral',      # neutral, enthusiastic, calm, urgent
        'punctuation': 'normal' # normal, excited, questioning
    }
    
    # Formalite kontrolü
    formal_words = ['lütfen', 'rica ederim', 'teşekkür ederim', 'teşekkürler']
    casual_words = ['naber', 'selam', 'slm', 'mrb', 'nbr', 'ey', 'hey']
    
    if any(word in msg_lower for word in formal_words):
        style['formality'] = 'formal'
    elif any(word in msg_lower for word in casual_words):
        style['formality'] = 'casual'
    else:
        style['formality'] = 'friendly'
    
    # Mesaj uzunluğu
    word_count = len(user_message.split())
    if word_count <= 3:
        style['length'] = 'short'
    elif word_count <= 10:
        style['length'] = 'medium'
    else:
        style['length'] = 'long'
    
    # Ton analizi
    urgent_words = ['acil', 'hemen', 'çabuk', 'acele', 'hızlı', 'şimdi']
    enthusiastic_words = ['harika', 'süper', 'muhteşem', 'çok iyi', 'yaşa', 'bravo']
    
    if any(word in msg_lower for word in urgent_words):
        style['tone'] = 'urgent'
    elif any(word in msg_lower for word in enthusiastic_words) or '!' in user_message:
        style['tone'] = 'enthusiastic'
    elif '?' in user_message or any(word in msg_lower for word in ['nasıl', 'ne', 'neden', 'nerede', 'kim', 'hangi']):
        style['tone'] = 'questioning'
    else:
        style['tone'] = 'neutral'
    
    # Noktalama analizi
    if user_message.count('!') > 1:
        style['punctuation'] = 'excited'
    elif user_message.count('?') > 1:
        style['punctuation'] = 'questioning'
    
    return style

def build_adaptive_system_prompt(user_name: str, user_message: str, advanced_context: str) -> str:
    """Kullanıcının tarzına göre sistem promptu oluştur
    
    Args:
        user_name: Kullanıcı adı
        user_message: Kullanıcı mesajı
        advanced_context: Gelişmiş bağlam
        
    Returns:
        str: Sistem promptu
    """
    style = analyze_conversation_style(user_message)
    
    response_style = ""
    
    # Formalite
    if style['formality'] == 'formal':
        response_style = "Kibar ama samimi konuş."
    else:
        response_style = "Doğal ve arkadaşça konuş."
    
    # Uzunluk
    if style['length'] == 'short':
        response_style += " Kısa yanıt ver (1-2 cümle)."
    elif style['length'] == 'medium':
        response_style += " Orta uzunlukta yanıt ver (2-3 cümle)."
    else:
        response_style += " Detaylı yanıt ver."
    
    # Ton
    if style['tone'] == 'urgent':
        response_style += " Hızlı ve direkt yanıt ver, gereksiz detay verme."
    elif style['tone'] == 'enthusiastic':
        response_style += " Olumlu ve enerjik ton kullan."
    elif style['tone'] == 'questioning':
        response_style += " Açıklayıcı ama kısa yanıt ver."
    else:
        response_style += " Net ve anlatışlı yanıt ver."
    
    system_prompt = f"""Sen Asena, {user_name}'ın AI asistanısın.

Kimliğin:
- Nuri Can ve Rabia'nın yardımcısısın
- Akıllı, yardımsever ve empatik bir asistansın

Bağlam:
{advanced_context}

Yanıt Tarzı:
{response_style}

Kurallar:
1. Doğal ve samimi konuş
2. Net ve anlaşılır cümleler kur
3. Günlük konuşma dilinde yanıt ver
4. Kullanıcının ihtiyaçlarına odaklan
"""
    
    return system_prompt

def query_groq(user_name: str, user_message: str) -> str:
    """Groq API'sini kullanarak yanıt oluşturur - İyileştirilmiş Caching ve Context ile
    
    Args:
        user_name: Kullanıcı adı
        user_message: Kullanıcı mesajı
        
    Returns:
        str: Oluşturulan yanıt
    """
    try:
        # Groq client'ının mevcut olduğunu kontrol et
        if groq_client is None:
            logging.error("Groq client başlatılmadı. API anahtarını kontrol edin.")
            return "Üzgünüm, şu anda yanıt veremiyorum. Lütfen daha sonra tekrar deneyin."
        
        # 1. Cache'yi kontrol et
        cached = response_cache.get_cached_response(user_name, user_message)
        if cached:
            logging.info(f"Cache hit for user {user_name} - Access count: {cached['access_count']}")
            return cached['response']
        
        # 2. İleri bağlam oluştur
        advanced_context = advanced_context_builder.build_enhanced_context(
            user_name, user_message, include_emotions=True
        )
        
        # 3. Kullanıcı tarzına göre sistem promptu oluştur
        system_prompt = build_adaptive_system_prompt(user_name, user_message, advanced_context)
        
        # API'ye gönderilecek mesajı oluştur
        messages: Any = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        try:
            # Groq API'sine istek gönder
            response = groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=messages,  # type: ignore
                temperature=0.7,
                max_tokens=500,
                top_p=0.9,
                frequency_penalty=0.0,
                presence_penalty=0.0,
                stop=None
            )
            
            # Yanıtı al ve işle
            content = response.choices[0].message.content
            if not content:
                ai_response = "Üzgünüm, boş bir yanıt alındı. Lütfen daha sonra tekrar deneyin."
            else:
                ai_response = content.strip()
                # Halüsinasyonları filtrele
                ai_response = filter_hallucinations(ai_response, user_name, user_message)
                
                # Cache'ye kaydet (confidence skoru ile)
                response_cache.store_response(user_name, user_message, ai_response, confidence=0.85)
                logging.info(f"Response cached for user {user_name}")
            
            return ai_response
            
        except Exception as api_error:
            logging.error(f"Groq API hatası: {api_error}", exc_info=True)
            return "Üzgünüm, şu anda yanıt veremiyorum. Lütfen daha sonra tekrar deneyin."
            
    except Exception as e:
        logging.error(f"Sorgu hatası: {e}", exc_info=True)
        return "Üzgünüm, bir hata oluştu. Lütfen daha sonra tekrar deneyin."


# === ROUTES ===
@app.route('/asena', methods=['POST'])
def asena():
    try:
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict() or {'message': request.data.decode('utf-8')}

        user_name = data.get('user', 'Nuri Can').strip()
        user_message = data.get('message', str(data)).strip()
        
        # SADECE Nuri Can ve Rabia'ya izin ver
        allowed_users = ['Nuri Can', 'Rabia']
        if user_name not in allowed_users:
            logging.warning(f"Yetkisiz kullanıcı giriş denemesi: {user_name}")
            return jsonify({
                "success": False, 
                "response": "Yetkisiz erişim. Sadece Nuri Can ve Rabia kullanabilir."
            }), 403

        if not user_message or user_message.strip() in ['', '{}']:
            return jsonify({"success": False, "response": "Ne dedin ki?"}), 400
            
        try:
            # Kullanıcı mesajını kısa süreli hafızaya ekle
            memory_manager.update_short_term_memory(user_name, {
                'type': 'user_message',
                'content': user_message,
                'timestamp': datetime.now().isoformat()
            })
            
            # Bilgi güncelleme kontrolü
            if any(x in user_message.lower() for x in ['değilim', 'artık', 'değişti', 'yanlış']):
                if 'yaş' in user_message.lower():
                    update_or_create_memory(user_name, "personal_info", user_message)
                    
            # AI yanıtını al
            response = query_groq(user_name, user_message)
            
            # Konuşmayı kaydet
            save_conversation(user_name, user_message, response)
            
            # Önemli bilgileri çıkar
            extract_learnable_info(user_name, user_message)
            
            # Rabia için hatırlatma oluşturulmussa, yanıta bilgi ekle
            if 'rabia için' in user_message.lower() and 'hatırlat' in user_message.lower():
                # Rabia için hatırlatma kuruldu, AI'nin yanıtını düzenle
                response = f"Rabia'ya hatırlatma oluşturdum. {response}"
            elif 'hatırlat' in user_message.lower():
                # Kendi hatırlatması durumu
                if 'nuri için' not in user_message.lower() and 'bana' not in user_message.lower():
                    # Kendi için hatırlatma
                    response = f"Hatırlatma oluşturdum. {response}"
            
            resp = make_response(response)
            resp.headers['Content-Type'] = 'text/plain; charset=utf-8'
            return resp

        except Exception as api_error:
            logging.error(f"API Hatası: {str(api_error)}", exc_info=True)
            return jsonify({"success": False, "error": "Üzgünüm, şu anda yanıt veremiyorum. Lütfen daha sonra tekrar deneyin."}), 500
            
    except Exception as e:
        logging.error(f"Genel Hata: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": "Üzgünüm, bir hata oluştu. Lütfen daha sonra tekrar deneyin."}), 500



@app.route('/memories/<user_name>', methods=['GET'])
def get_memories_route(user_name):
    mems = get_memories(user_name)
    convs = get_recent_conversations(user_name, 10)
    return jsonify({
        "user": user_name,
        "memories": [{"type": t, "content": c, "time": tm} for t, c, tm in mems],
        "conversations": [{"msg": m, "resp": r, "time": t} for m, r, t in convs]
    })

@app.route('/family-status', methods=['GET'])
def family_status():
    return jsonify({
        "Nuri Can": {"last_seen": get_recent_conversations("Nuri Can", 1)},
        "Rabia": {"last_seen": get_recent_conversations("Rabia", 1)},
        "time": get_time_context()
    })

@app.route('/health', methods=['GET'])
def health():
    conn = sqlite3.connect('asena_memory.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM conversations"); convs = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM memories"); mems = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM reminders"); rems = c.fetchone()[0]
    conn.close()
    return jsonify({
        "status": "online",
        "model": "llama-3.3-70b-versatile",
        "time": get_time_context(),
        "stats": {"conversations": convs, "memories": mems, "reminders": rems}
    })

@app.route('/reset', methods=['POST'])
def reset():
    conn = sqlite3.connect('asena_memory.db')
    c = conn.cursor()
    c.execute("DELETE FROM conversations")
    c.execute("DELETE FROM memories")
    c.execute("DELETE FROM reminders")
    conn.commit()
    conn.close()
    load_initial_memories()
    return jsonify({"success": True, "message": "Hafıza sıfırlandı ve yeniden yüklendi."})

@app.route('/reminders/<user_name>', methods=['GET'])
def get_reminders(user_name):
    conn = sqlite3.connect('asena_memory.db')
    c = conn.cursor()
    c.execute("SELECT content, reminder_time, notified FROM reminders WHERE user_name = ? ORDER BY reminder_time",
              (user_name,))
    results = c.fetchall()
    conn.close()
    return jsonify([{"content": r[0], "due": r[1], "notified": bool(r[2])} for r in results])

@app.route('/register_device', methods=['POST'])
def register_device():
    """Cihaz kaydı için endpoint"""
    try:
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict() or {}
            
        user_name = data.get('user')
        device_id = data.get('device_id')
        push_token = data.get('push_token')
        
        if not all([user_name, device_id, push_token]):
            return jsonify({"success": False, "error": "Eksik parametre: user, device_id ve push_token gerekli"}), 400
        
        now = datetime.now().isoformat()
        conn = sqlite3.connect('asena_memory.db')
        c = conn.cursor()
        
        # Aynı cihaz ID'si varsa güncelle, yoksa ekle
        c.execute("""
            INSERT INTO devices (user_name, device_id, push_token, last_seen)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(device_id) 
            DO UPDATE SET 
                user_name = excluded.user_name,
                push_token = excluded.push_token,
                last_seen = excluded.last_seen
        """, (user_name, device_id, push_token, now))
        
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Cihaz başarıyla kaydedildi"})
        
    except Exception as e:
        print(f"Cihaz kaydı hatası: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

# ============================================================================
# YENİ ENDPOINT'LER - GELİŞTİRİLMİŞ ÖZELLİKLER
# ============================================================================

@app.route('/morning-briefing/<user_name>', methods=['GET'])
def morning_briefing(user_name):
    """Sabah özeti getir (hava durumu, program, ipuçları)"""
    try:
        hour = datetime.now().hour
        
        # Hava durumunu al
        weather_service = get_weather_service()
        weather_info = weather_service.format_weather_message("Istanbul")
        
        # Sabah özeti oluştur
        briefing = proactive_assistant.generate_morning_briefing(
            user_name=user_name,
            weather_info=weather_info,
            user_schedule=['09:00 İşe git', '12:00 Öğle yemeği', '18:00 İş bitti']
        )
        
        # Günlük ipucu ekle
        briefing += f"\n\n{quick_solutions.get_daily_tip()}"
        
        return jsonify({
            "success": True,
            "user": user_name,
            "hour": hour,
            "briefing": briefing,
            "time": get_time_context()
        })
        
    except Exception as e:
        logging.error(f"Sabah özeti hatası: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/weather/<city>', methods=['GET'])
def get_weather(city="Istanbul"):
    """Hava durumu bilgisi getir"""
    try:
        weather_service = get_weather_service()
        weather = weather_service.get_weather(city)
        
        if not weather:
            return jsonify({
                "success": False,
                "error": f"{city} için hava durumu bilgisi alınamadı"
            }), 404
        
        return jsonify({
            "success": True,
            "city": city,
            "weather": weather
        })
        
    except Exception as e:
        logging.error(f"Hava durumu hatası: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/smart-home', methods=['POST'])
def control_smart_home():
    """Akıllı ev kontrolü"""
    try:
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict() or {}
        
        device = data.get('device', 'lights')
        command = data.get('command', '')
        
        result = smart_home.set_device_status(device, command)
        
        return jsonify({
            "success": True,
            "device": device,
            "command": command,
            "result": result
        })
        
    except Exception as e:
        logging.error(f"Akıllı ev kontrolü hatası: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/task/create', methods=['POST'])
def create_task():
    """Görev oluştur"""
    try:
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict() or {}
        
        title = data.get('title', '')
        due_date = data.get('due_date')
        priority = data.get('priority', 'normal')
        
        if not title:
            return jsonify({"success": False, "error": "Görev başlığı gerekli"}), 400
        
        result = smartscheduler.create_task(title, due_date, priority)
        
        return jsonify({
            "success": True,
            "message": result,
            "task": {
                "title": title,
                "due_date": due_date,
                "priority": priority
            }
        })
        
    except Exception as e:
        logging.error(f"Görev oluşturma hatası: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/mood/<user_name>', methods=['POST'])
def track_mood(user_name):
    """Ruh halini takip et"""
    try:
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict() or {}
        
        mood = data.get('mood', 'neutral')
        intensity = int(data.get('intensity', 5))
        
        emotional_intelligence.track_mood(user_name, mood, intensity)
        pattern = emotional_intelligence.detect_mood_pattern(user_name)
        
        return jsonify({
            "success": True,
            "user": user_name,
            "mood": mood,
            "intensity": intensity,
            "pattern": pattern
        })
        
    except Exception as e:
        logging.error(f"Ruh hali takibi hatası: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/wellness-suggestion', methods=['GET'])
def wellness_suggestion():
    """Wellness önerisi getir"""
    try:
        mood = request.args.get('mood', 'happy')
        time_of_day = request.args.get('time', 'morning')
        
        suggestion = proactive_assistant.suggest_wellness_activity(mood, time_of_day)
        tip = quick_solutions.get_daily_tip()
        quote = quick_solutions.get_motivational_quote()
        
        return jsonify({
            "success": True,
            "mood": mood,
            "time_of_day": time_of_day,
            "wellness_suggestion": suggestion,
            "daily_tip": tip,
            "motivational_quote": quote
        })
        
    except Exception as e:
        logging.error(f"Wellness önerisi hatası: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/family-context', methods=['GET'])
def family_context():
    """Aile bağlamı bilgisi getir"""
    try:
        topic = request.args.get('topic', '')
        
        context = family_intelligence.get_shared_context(topic)
        activity = family_intelligence.suggest_family_activity()
        
        return jsonify({
            "success": True,
            "family_members": family_intelligence.family_members,
            "context": context,
            "suggested_activity": activity
        })
        
    except Exception as e:
        logging.error(f"Aile bağlamı hatası: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/daily-summary/<user_name>', methods=['GET'])
def daily_summary(user_name):
    """Günlük özet getir"""
    try:
        time_ctx = get_time_context()
        greeting = quick_solutions.time_aware_greeting(time_ctx['hour'], user_name)
        tip = quick_solutions.get_daily_tip()
        quote = quick_solutions.get_motivational_quote()
        
        # İstatistikleri getir
        insights = analytics.get_user_insights(user_name)
        
        return jsonify({
            "success": True,
            "user": user_name,
            "time_context": time_ctx,
            "greeting": greeting,
            "daily_tip": tip,
            "quote": quote,
            "insights": insights
        })
        
    except Exception as e:
        logging.error(f"Günlük özet hatası: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    print("=" * 70)
    print("ASENA 2.1 – GELİŞTİRİLMİŞ AİLE ASİSTANI (HATIRLATMA DESTEKLİ)")
    print("=" * 70)
    print(f"Başlangıç: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    print("Özellikler: Tarih Bilinci • Kullanıcı Hafızası • Güncelleme • Plan Takibi • Hatırlatma Bildirimleri")
    print("Model: Llama3-70B (Groq)")
    print("=" * 70)
    
    # Veritabanını başlat
    try:
        print(" Veritabanı başlatılıyor...")
        ensure_database()
        print(" Veritabanı başarıyla başlatıldı")
    except Exception as e:
        print(f" Veritabanı başlatılırken hata oluştu: {str(e)}")
        raise
    
    # Hatırlatıcı servisini başlat
    print(" Hatırlatıcı servisi başlatılıyor...")
    reminder_thread = threading.Thread(target=asena_hatirlatici.check_reminders)
    reminder_thread.daemon = True
    reminder_thread.start()
    
# ============================================================================
# TV KONTROL API ENDPOİNTLERİ
# ============================================================================

@app.route('/tv/status', methods=['GET'])
def tv_status():
    """TV'nin mevcut durumunu getir"""
    try:
        state = tv_manager.get_state()
        return jsonify({
            "success": True,
            "tv_state": state,
            "available_apps": tv_manager.get_available_apps()
        })
    except Exception as e:
        logging.error(f"TV status hatası: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/tv/power', methods=['POST'])
def tv_power():
    """TV'yi aç/kapat"""
    try:
        data = request.get_json() or {}
        action = data.get('action', 'toggle')  # on, off, toggle
        
        if action == 'on':
            success = tv_manager.power_on()
        elif action == 'off':
            success = tv_manager.power_off()
        else:
            success = tv_manager.power_on() if not tv_manager.state.is_on else tv_manager.power_off()
        
        return jsonify({
            "success": success,
            "action": action,
            "state": tv_manager.get_state()
        })
    except Exception as e:
        logging.error(f"TV power hatası: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/tv/volume', methods=['POST'])
def tv_volume():
    """TV ses seviyesini kontrol et"""
    try:
        data = request.get_json() or {}
        action = data.get('action')  # set, up, down, mute
        value = data.get('value', 1)
        
        if action == 'set':
            success = tv_manager.set_volume(value)
        elif action == 'up':
            success = tv_manager.volume_up(value)
        elif action == 'down':
            success = tv_manager.volume_down(value)
        elif action == 'mute':
            success = tv_manager.mute()
        else:
            return jsonify({"success": False, "error": "Unknown action"}), 400
        
        return jsonify({
            "success": success,
            "action": action,
            "state": tv_manager.get_state()
        })
    except Exception as e:
        logging.error(f"TV volume hatası: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/tv/app', methods=['POST'])
def tv_app():
    """TV'de uygulama aç"""
    try:
        data = request.get_json() or {}
        app_name = data.get('app')
        
        if not app_name:
            return jsonify({"success": False, "error": "App name required"}), 400
        
        success = tv_manager.open_app(app_name)
        
        return jsonify({
            "success": success,
            "app": app_name,
            "state": tv_manager.get_state()
        })
    except Exception as e:
        logging.error(f"TV app hatası: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/tv/youtube', methods=['POST'])
def tv_youtube():
    """YouTube'da arama yap"""
    try:
        data = request.get_json() or {}
        query = data.get('query')
        
        if not query:
            return jsonify({"success": False, "error": "Query required"}), 400
        
        success = tv_manager.youtube_search(query)
        
        return jsonify({
            "success": success,
            "query": query,
            "state": tv_manager.get_state()
        })
    except Exception as e:
        logging.error(f"TV YouTube hatası: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/tv/preset', methods=['POST'])
def tv_preset():
    """TV preset'i oluştur veya çalıştır"""
    try:
        data = request.get_json() or {}
        action = data.get('action')  # create, execute
        
        if action == 'create':
            name = data.get('name')
            commands = data.get('commands', [])
            description = data.get('description', '')
            
            # Validate that name is provided
            if not name or not isinstance(name, str):
                return jsonify({"success": False, "error": "Preset name is required and must be a string"}), 400
            
            success = tv_manager.create_preset(name, commands, description)
            return jsonify({"success": success, "preset": name})
        
        elif action == 'execute':
            name = data.get('name')
            
            # Validate that name is provided
            if not name or not isinstance(name, str):
                return jsonify({"success": False, "error": "Preset name is required and must be a string"}), 400
            
            success = tv_manager.execute_preset(name)
            return jsonify({
                "success": success,
                "preset": name,
                "state": tv_manager.get_state()
            })
        else:
            return jsonify({"success": False, "error": "Invalid action"}), 400
    except Exception as e:
        logging.error(f"TV preset hatası: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/tv/presets', methods=['GET'])
def tv_presets():
    """Kaydedilen preset'leri listele"""
    try:
        presets = tv_manager.get_presets()
        return jsonify({
            "success": True,
            "presets": presets
        })
    except Exception as e:
        logging.error(f"TV presets hatası: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/tv/history', methods=['GET'])
def tv_history():
    """TV komut geçmişini getir"""
    try:
        limit = request.args.get('limit', 20, type=int)
        history = tv_manager.get_command_history(limit)
        
        return jsonify({
            "success": True,
            "history": history
        })
    except Exception as e:
        logging.error(f"TV history hatası: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)