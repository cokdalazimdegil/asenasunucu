import flask
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
import json
import os
from datetime import datetime, timedelta
import sqlite3
from groq import Groq
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
from typing import List, Dict, Any, cast
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

# .env dosyasını yükle
load_dotenv()

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
            "meslek": "Siber güvenlik uzmanı",
            "çalışma_saatleri": "Hafta içi 09:00 - 19:00",
            "hedef": "Kendi siber güvenlik şirketini kurmak",
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
            "meslek": "Fitness ve çocuklar için jimnastik antrenörü",
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
        raise ValueError("GROQ_API_KEY bulunamadı!")
except Exception as e:
    print(f"Hata: {e}")
    GROQ_API_KEY = "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"

# Hatırlatıcı modülüne bildirim fonksiyonunu ilet
asena_hatirlatici.set_notification_callback(send_notification)

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
CORS(app)

# UTF-8 Encoding
import sys
import codecs
if sys.stdout.encoding != 'utf-8':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Groq API
GROQ_API_KEY = "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"

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

# === BAŞLANGIÇ HAFIZASI - TÜM DOSYADA KULLANILABİLİR ===
INITIAL_MEMORIES = {
    "Nuri Can": {
        "kişisel": {
            "yaş": 25,
            "şehir": "İstanbul",
            "ilişki_durumu": "Evli (Rabia ile)",
            "kişilik": ["mantıklı", "meraklı", "teknolojiye düşkün", "analitik düşünmeyi seven"]
        },
        "çalışma": {
            "meslek": "Siber güvenlik uzmanı",
            "çalışma_saatleri": "Hafta içi 09:00 - 18:00",
            "hedef": "Kendi siber güvenlik şirketini kurmak",
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
            "meslek": "Fitness ve çocuklar için jimnastik antrenörü",
            "çalışma_yerleri": ["Fitstation Spor Merkezi"],
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
            logging.info("✅ Hafızalar zaten yüklü")
            return True
        
        logging.info("🔄 Başlangıç hafızaları yükleniyor...")
        
        # Her kullanıcı için
        for user_name, categories in INITIAL_MEMORIES.items():
            logging.info(f"📝 {user_name} için hafızalar yükleniyor...")
            
            # Kişisel bilgiler
            if "kişisel" in categories:
                for key, value in categories["kişisel"].items():
                    if isinstance(value, list):
                        value = ", ".join(value)
                    memory_text = f"{key}: {value}"
                    c.execute(
                        """INSERT OR IGNORE INTO memories 
                        (user_name, memory_type, content, created_at, updated_at) 
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
                        (user_name, memory_type, content, created_at, updated_at) 
                        VALUES (?, ?, ?, datetime('now'), datetime('now'))""",
                        (user_name, "çalışma", memory_text)
                    )
            
            # Hobiler
            if "hobiler" in categories:
                hobbies = ", ".join(categories["hobiler"])
                c.execute(
                    """INSERT OR IGNORE INTO memories 
                    (user_name, memory_type, content, created_at, updated_at) 
                    VALUES (?, ?, ?, datetime('now'), datetime('now'))""",
                    (user_name, "hobiler", f"Hobiler: {hobbies}")
                )
            
            # Alışkanlıklar
            if "alışkanlıklar" in categories:
                for time_of_day, habit in categories["alışkanlıklar"].items():
                    c.execute(
                        """INSERT OR IGNORE INTO memories 
                        (user_name, memory_type, content, created_at, updated_at) 
                        VALUES (?, ?, ?, datetime('now'), datetime('now'))""",
                        (user_name, "alışkanlık", f"{time_of_day}: {habit}")
                    )
            
            # İlişkiler
            if "ilişkiler" in categories:
                for person, relation in categories["ilişkiler"].items():
                    c.execute(
                        """INSERT OR IGNORE INTO memories 
                        (user_name, memory_type, content, created_at, updated_at) 
                        VALUES (?, ?, ?, datetime('now'), datetime('now'))""",
                        (user_name, "ilişki", f"{person}: {relation}")
                    )
        
        conn.commit()
        logging.info("✅ Başlangıç hafızaları başarıyla yüklendi!")
        
        # Kontrol et
        c.execute("SELECT COUNT(*) FROM memories")
        final_count = c.fetchone()[0]
        logging.info(f"📊 Toplam hafıza kaydı: {final_count}")
        
        return True
    except Exception as e:
        logging.error(f"❌ Hafıza yükleme hatası: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

# TV KOMUTLARI İÇİN GLOBAL HANDLER
import tv_connect
TV_IP = '192.168.1.23'
def handle_tv_command(message):
    msg = message.lower()
    import re
    # --- Ses Komutları ---
    if any(kw in msg for kw in ["sesini aç", "sesi aç"]):
        tv_connect.connect_adb(TV_IP)
        tv_connect.volume_up(TV_IP, 3)
        return "Televizyonun sesi açılıyor."
    if any(kw in msg for kw in ["sesini kapat", "sesi kapat"]):
        tv_connect.connect_adb(TV_IP)
        tv_connect.volume_down(TV_IP, 3)
        return "Televizyonun sesi kısılıyor."
    if any(kw in msg for kw in ["sessize", "mute"]):
        tv_connect.connect_adb(TV_IP)
        tv_connect.mute(TV_IP)
        return "Televizyonun sesi tamamen kapatıldı."
    # ... x'e getir, yarıya getir, yüzde ...'ye getir gibi ---
    # "15'e getir", "yirmiye getir", "yarıya getir", "%70'e getir" gibi
    max_level = 30
    # Rakam ve sayı metinleri
    numwords = {"sıfır":0,"bir":1,"iki":2,"üç":3,"dört":4,"beş":5,"altı":6,"yedi":7,"sekiz":8,"dokuz":9,"on":10,"onbir":11,"oniki":12,"onüç":13,"ondört":14,"onbeş":15,"onaltı":16,"onyedi":17,"onsekiz":18,"ondokuz":19,"yirmi":20,"yirmi bir":21,"yirmibir":21,"yirmi iki":22,"yirmi üç":23,"yirmi dört":24,"yirmi beş":25,"otuz":30}
    # Önce basit regex ile sayı bul
    match_num = re.search(r'(\d{1,2})[ \'"]*([a-zçşıöüğ]*)(?:e getir| e getir| ye getir| yap| olsun| seviye| ayarla)', msg)
    if match_num:
        level = int(match_num.group(1))
        if level > max_level: level = max_level
        tv_connect.connect_adb(TV_IP)
        tv_connect.set_volume(TV_IP, level)
        return f"Televizyonun sesi {level} seviyesine ayarlandı."
    # Metin sayılarını yakala
    for w in numwords:
        if w in msg and any(x in msg for x in ["e getir","ye getir","seviye","yap","olsun"]):
            tv_connect.connect_adb(TV_IP)
            lvl = numwords[w]
            tv_connect.set_volume(TV_IP, lvl)
            return f"Televizyonun sesi {lvl} seviyesine ayarlandı."
    # Yarıya getir:
    if "yarıya getir" in msg:
        tv_connect.connect_adb(TV_IP)
        tv_connect.set_volume(TV_IP, max_level//2)
        return "Televizyonun sesi yarıya getirildi."
    mpc = re.search(r'%\s*(\d+)[^\d]*?getir', msg)
    if mpc: # yüzde komutu
        percent = int(mpc.group(1))
        if percent > 100: percent = 100
        level = int(round(max_level * percent / 100))
        tv_connect.connect_adb(TV_IP)
        tv_connect.set_volume(TV_IP, level)
        return f"Televizyonun sesi %{percent} seviyesine getirildi."
    if any(kw in msg for kw in ['tv aç', 'televizyon aç', 'televizyonu aç']):
        tv_connect.connect_adb(TV_IP)
        tv_connect.tv_power(TV_IP, state='on')
        return 'TV açılıyor.'
    if any(kw in msg for kw in ['tv kapat', 'televizyon kapat', 'televizyonu kapat']):
        tv_connect.connect_adb(TV_IP)
        tv_connect.tv_power(TV_IP, state='off')
        return 'TV kapatılıyor.'
    if 'netflix' in msg:
        tv_connect.connect_adb(TV_IP)
        tv_connect.open_netflix(TV_IP)
        return 'Netflix açılıyor.'
    if 'hbo' in msg or 'hbomax' in msg or 'hbo max' in msg:
        tv_connect.connect_adb(TV_IP)
        tv_connect.open_hbo_max(TV_IP)
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
        if not query:
            tv_connect.connect_adb(TV_IP)
            tv_connect.open_app(TV_IP, "com.google.android.youtube.tv")
            return 'YouTube açılıyor.'
        tv_connect.connect_adb(TV_IP)
        tv_connect.open_youtube_search(TV_IP, query)
        return f'YouTube açılıyor, arama: {query}'
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
        
        # Kullanıcı tablosu
        c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Konuşma geçmişi tablosu
        c.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_name TEXT NOT NULL,
            message TEXT NOT NULL,
            response TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Hatırlatıcılar tablosu
        c.execute('''
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_name TEXT NOT NULL,
            content TEXT NOT NULL,
            reminder_time DATETIME NOT NULL,
            target_user TEXT,
            notified BOOLEAN DEFAULT 0,
            notification_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Cihazlar tablosu
        c.execute('''
        CREATE TABLE IF NOT EXISTS devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_name TEXT NOT NULL,
            device_id TEXT UNIQUE NOT NULL,
            push_token TEXT,
            last_seen TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Hafıza tablosu
        c.execute('''
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_name TEXT NOT NULL,
            memory_type TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # updated_at sütunu yoksa ekle
        try:
            c.execute('ALTER TABLE memories ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
        except sqlite3.OperationalError:
            # Sütun zaten varsa hata verme
            pass
            
        conn.commit()
        
        # Tablo varlığını doğrula
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in c.fetchall()]
        logging.info(f"📋 Mevcut tablolar: {existing_tables}")
        
    except sqlite3.Error as e:
        logging.error(f"❌ Veritabanı hatası: {e}")
        raise
    finally:
        if conn:
            conn.close()

def ensure_database():
    """Veritabanının varlığından emin ol ve gerekirse başlangıç verilerini yükle"""
    db_exists = os.path.exists('asena_memory.db')
    
    # Veritabanı yoksa veya tablolar eksikse oluştur
    if not db_exists:
        logging.info("🔧 Veritabanı oluşturuluyor...")
        init_db()
        logging.info("✅ Veritabanı oluşturuldu.")
    
    # Tabloların varlığını kontrol et
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        required_tables = ['conversations', 'reminders', 'memories']
        missing_tables = [t for t in required_tables if t not in tables]
        
        if missing_tables:
            logging.info(f"🔧 Eksik tablolar oluşturuluyor: {missing_tables}")
            init_db()
            logging.info("✅ Eksik tablolar oluşturuldu.")
        
        # İlk kurulumda veya tablolar yeni oluşturulduysa başlangıç verilerini yükle
        if not db_exists or missing_tables:
            logging.info("🔄 Başlangıç hafızaları yükleniyor...")
            if load_initial_memories():
                logging.info("✅ Başlangıç hafızaları başarıyla yüklendi.")
            else:
                logging.warning("⚠️ Başlangıç hafızaları yüklenirken hata oluştu.")
    except Exception as e:
        logging.error(f"❌ Veritabanı hatası: {e}")
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
            
            time_parts = []
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
        if conn is not None:
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
    """Kullanıcı için hafızaları getir - GÜNCELLENDİ
    
    Args:
        user_name: Hafızaları getirilecek kullanıcı adı
        mem_type: İsteğe bağlı olarak belirli bir hafıza türü (örn: 'food_preference', 'allergy')
        
    Returns:
        list: Kullanıcı ve aile üyelerine ait hafızaların listesi
    """
    if not user_name:
        logging.warning("❌ Geçersiz kullanıcı adı")
        return []
        
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # 1. Kullanıcının kendi hafızalarını al
        query = """
            SELECT id, user_name, memory_type, content, created_at, updated_at
            FROM memories 
            WHERE user_name = ?
            {}
            ORDER BY updated_at DESC 
            LIMIT 50
        """
        
        query_params = [user_name]
        
        # 2. Eğer belirli bir hafıza türü belirtildiyse filtrele
        if mem_type:
            query = query.format("AND memory_type = ?")
            query_params.append(mem_type)
        else:
            query = query.format("")
            
        c.execute(query, query_params)
        db_results = c.fetchall()
        
        # 3. Aile üyelerinin hafızalarını da ekle
        family_members = ["Rabia", "Nuri Can"]
        if user_name in family_members:
            family_members.remove(user_name)  # Kendi hafızalarını tekrar ekleme
            
        if family_members:
            family_query = """
                SELECT id, user_name, memory_type, content, created_at, updated_at
                FROM memories 
                WHERE user_name IN ({})
                {}
                ORDER BY updated_at DESC
                LIMIT 50
            """.format(", ".join(["?"] * len(family_members)), 
                       "AND memory_type = ?" if mem_type else "")
            
            family_params = family_members.copy()
            if mem_type:
                family_params.append(mem_type)
                
            c.execute(family_query, family_params)
            family_results = c.fetchall()
            db_results.extend(family_results)
        
        # 4. JSON içerikleri parse et ve hafızaları işle
        memories = []
        for mem_id, mem_user, mem_type, content, created_at, updated_at in db_results:
            try:
                # İçerik JSON ise parse et, değilse olduğu gibi kullan
                if isinstance(content, str) and (content.startswith('{') or content.startswith('[')):
                    try:
                        content = json.loads(content)
                    except json.JSONDecodeError:
                        pass  # JSON parse edilemezse olduğu gibi bırak
                
                memory = {
                    'id': mem_id,
                    'user_name': mem_user,
                    'memory_type': mem_type,
                    'content': content,
                    'created_at': created_at,
                    'updated_at': updated_at
                }
                
                # Özel işlem gerektiren hafıza tipleri için özet oluştur
                if mem_type == 'food_preference':
                    if isinstance(content, dict) and 'foods' in content and isinstance(content['foods'], list):
                        memory['summary'] = f"{mem_user} şu yiyecekleri sever: " + ", ".join(content['foods'])
                    elif isinstance(content, str):
                        memory['summary'] = f"{mem_user} şu yiyeceği sever: {content}"
                    
                elif mem_type == 'allergy':
                    if isinstance(content, dict) and 'allergens' in content and isinstance(content['allergens'], list):
                        memory['summary'] = f"{mem_user} şu alerjilere sahip: " + ", ".join(content['allergens'])
                    elif isinstance(content, str):
                        memory['summary'] = f"{mem_user} şu alerjiye sahip: {content}"
                
                memories.append(memory)
                
            except Exception as e:
                logging.error(f"Hafıza işlenirken hata (ID: {mem_id}): {e}")
        
        # 5. Eşsiz hafızaları döndür (aynı içerikten birden fazla olmaması için)
        unique_memories = []
        seen_contents = set()
        
        for mem in memories:
            # Hafızayı benzersiz bir şekilde tanımlamak için anahtar oluştur
            content_key = f"{mem['user_name']}:{mem['memory_type']}:"
            
            if isinstance(mem['content'], (str, int, float, bool)):
                content_key += str(mem['content'])
            elif isinstance(mem['content'], (list, dict)):
                try:
                    content_key += json.dumps(mem['content'], sort_keys=True)
                except (TypeError, ValueError):
                    content_key += str(mem['content'])
            else:
                content_key += str(mem['content'])
            
            if content_key not in seen_contents:
                seen_contents.add(content_key)
                unique_memories.append(mem)
        
        # 6. Hata ayıklama için hafıza sayısını logla
        if mem_type:
            logging.info(f" {len(unique_memories)} adet '{mem_type}' türünde hafıza getirildi")
        else:
            logging.info(f" Toplam {len(unique_memories)} adet hafıza getirildi")
            
        return unique_memories
        
    except sqlite3.Error as e:
        logging.error(f" Veritabanı hatası (get_memories): {e}")
        return []
    except Exception as e:
        logging.error(f" Beklenmeyen hata (get_memories): {e}")
        return []
    finally:
        if conn is not None:
            conn.close()

def update_or_create_memory(user_name, mem_type, content):
    conn = get_db_connection()
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute("SELECT id FROM memories WHERE user_name = ? AND memory_type = ?", (user_name, mem_type))
    row = c.fetchone()
    if row:
        c.execute("UPDATE memories SET content = ?, updated_at = ? WHERE id = ?", (content, now, row[0]))
    else:
        c.execute("INSERT INTO memories (user_name, memory_type, content, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                  (user_name, mem_type, content, now, now))
    conn.commit()
    conn.close()

def extract_learnable_info(user_name, message):
    message_lower = message.lower()
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    tomorrow = (now + timedelta(days=1)).strftime("%Y-%m-%d")
    yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")

    # Zamanlı planlar
    if any(word in message_lower for word in ['yarın', 'yarınki', 'yarına']):
        update_or_create_memory(user_name, "plan", f"[YARIN] {message}")

    if any(word in message_lower for word in ['bugün', 'bu akşam', 'bu gece']):
        update_or_create_memory(user_name, "plan", f"[BUGÜN] {message}")

    if 'dün' in message_lower:
        update_or_create_memory(user_name, "memory", f"[DÜN] {message}")

    # Çalışma durumu
    if 'işe gidiyorum' in message_lower or 'çalışıyorum' in message_lower:
        update_or_create_memory(user_name, "routine", f"Şu an işte: {message}")

    # Yemek tercihleri ve alerjiler
    if any(name in message_lower for name in ['rabia', 'nuri can', 'nurican']):
        # Yemek sevme
        if any(verb in message_lower for verb in ['seviyor', 'bayılıyor', 'hoşlanıyor', 'sever', 'bayılır', 'hoşlanır']):
            if any(food in message_lower for food in ['yemek', 'yiyecek', 'içecek', 'içki', 'tatlı', 'yemesi', 'içmesi']):
                update_or_create_memory("Rabia" if 'rabia' in message_lower else "Nuri Can", 
                                     "food_preference", 
                                     message.strip())
        
        # Alerji bilgisi
        if any(word in message_lower for word in ['alerjisi var', 'alerjimiz var', 'alerjimiz yok', 'yiyemez', 'içemez']):
            update_or_create_memory("Rabia" if 'rabia' in message_lower else "Nuri Can",
                                 "allergy",
                                 message.strip())

    # Genel tercihler
    if any(word in message_lower for word in ['seviyorum', 'seviyoruz', 'severim', 'severiz']):
        if any(category in message_lower for category in ['yemek', 'içecek', 'müzik', 'film', 'dizi', 'aktivite']):
            update_or_create_memory(user_name, "preference", message.strip())

    # Hatırlatma tespiti (basit: "bana [zaman] [içerik] hatırlat")
    if 'hatırlat' in message_lower:
        # Basit parsing: zamanı bul
        time_match = re.search(r'(\d{1,2}):(\d{2})', message)  # Saat:dk
        if time_match:
            hour, minute = time_match.groups()
            due = now.replace(hour=int(hour), minute=int(minute)).isoformat()
        else:
            due = (now + timedelta(hours=1)).isoformat()  # Varsayılan 1 saat sonrası
        
        content = message.split('hatırlat')[-1].strip()
        save_reminder(user_name, content, due)

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
def build_context_prompt(user_name, user_message):
    """GÜNCELLENMİŞ - Halüsinasyon önleyici prompt"""
    time_ctx = get_time_context()
    
    # Son konuşmaları getir
    recent_convs = get_recent_conversations(user_name, limit=2)
    
    # Tüm ilgili hafızaları getir (kullanıcının kendi hafızaları ve aile üyelerinin önemli hafızaları)
    all_memories = []
    
    # Kullanıcının tüm hafızalarını getir
    user_memories = get_memories(user_name)
    all_memories.extend([{
        'memory_type': mem['memory_type'],
        'content': mem['content'],
        'user_name': user_name
    } for mem in user_memories])
    
    # Aile üyelerinin önemli hafızalarını getir (yemek tercihleri, alerjiler vb.)
    for member in ["Rabia", "Nuri Can"]:
        if member.lower() != user_name.lower():
            # Sadece önemli hafızaları al
            important_memories = get_memories(member)
            for memory in important_memories:
                mem_type = memory['memory_type']
                content = memory['content']
                if any(keyword in str(mem_type).lower() for keyword in ['food', 'yemek', 'allergy', 'alerji', 'work', 'iş', 'saat', 'time']):
                    all_memories.append({
                        'memory_type': f"{member}_{mem_type}",
                        'content': content,
                        'user_name': member
                    })
    
    # Bağlamı sınırla ve kategorilere ayır
    food_prefs = []
    allergies = []
    work_schedule = []
    other_memories = []
    
    for memory in all_memories[:50]:  # Toplam 50 hafıza
        mem_type = str(memory['memory_type']).lower()
        content = memory['content']
        
        # Yemek tercihleri
        if any(keyword in mem_type for keyword in ['food', 'yemek', 'seviyor', 'sevmeyen', 'tercih']):
            food_prefs.append(f"- {content}")
        # Alerjiler
        elif any(keyword in mem_type for keyword in ['allergy', 'alerji', 'yemiyor', 'yiyemez']):
            allergies.append(f"- {content}")
        # İş programı
        elif any(keyword in mem_type for keyword in ['work', 'iş', 'saat', 'time', 'çalışma']):
            work_schedule.append(f"- {content}")
        else:
            other_memories.append(f"- {content}")
    
    # Bağlam metinlerini oluştur
    memory_sections = []
    
    if work_schedule:
        memory_sections.append("İŞ PROGRAMLARI:" + "\n" + "\n".join(work_schedule))
    
    if food_prefs:
        memory_sections.append("YEMEK TERCİHLERİ:" + "\n" + "\n".join(food_prefs))
    
    if allergies:
        memory_sections.append("ALERJİ BİLGİLERİ:" + "\n" + "\n".join(allergies))
    
    if other_memories:
        memory_sections.append("DİĞER BİLGİLER:" + "\n" + "\n".join(other_memories))
    
    memory_text = "\n\n".join(memory_sections) if memory_sections else "- Henüz kayıtlı bilgi yok"
    
    # Kısa bir özet oluştur
    summary = []
    if work_schedule:
        summary.append("Aile üyelerinin iş programları hakkında bilgim var.")
    if food_prefs:
        summary.append("Aile üyelerinin yemek tercihlerini biliyorum.")
    if allergies:
        summary.append("Aile üyelerinin alerjileri hakkında bilgim var.")
    
    summary_text = " ".join(summary) if summary else ""
    
    prompt = f"""Senin adın Asena. Nuri Can ve Rabia'nın ev asistanısın. Aynı zamanda genel konularda da sohbet edebilir, yemek tarifleri önerebilir ve çeşitli konularda bilgi verebilirsin.

GERÇEK ZAMAN: {time_ctx['date']} {time_ctx['day']} {time_ctx['time']} ({time_ctx['time_of_day']})

KULLANICI: {user_name}

HAFIZAMDAN:
{memory_text}

{summary_text}

KURALLAR:
1. Yukarıdaki bilgileri KESİNLİKLE dikkate al
2. Sadece verilen bilgiler doğrultusunda yanıt ver
3. Bilmediğin bir şeyi asla uydurma
4. Genel konularda (yemek, bilgi, sohbet) serbestçe yanıt verebilirsin
5. Kısa ve net yanıtlar ver
6. Emoji KULLANMA
7. Eğer bir bilgi hafızanda yoksa, sadece "Bu konuda bir bilgim yok" de

SORU: {user_message}

YANIT:"""

    return prompt

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

def filter_hallucinations(ai_response, user_name, user_message):
    """Gelişmiş halüsinasyon filtresi"""
    # Şüpheli ifadeler
    suspicion_patterns = [
        r'dün\s+[a-zçşıöüğ]*\s+(yapmıştı|hazırlamıştı|gelmişti|gitmişti)',
        r'yarın\s+[a-zçşıöüğ]*\s+(yapacak|hazırlayacak|gelecek|gidecek)',
        r'rabia\s+[a-zçşıöüğ]*\s+(hazırladı|yaptı|söyledi)',
        r'nuri\s+can\s+[a-zçşıöüğ]*\s+(hazırladı|yaptı|söyledi)',
        r'planlıyoruz|planlıyorum|hazırlık\s+yapıyor'
    ]
    
    # Mevcut bağlamı kontrol et
    conversations = get_recent_conversations(user_name, limit=5)
    memories = get_memories(user_name)
    
    # Convert conversations to text
    context_text = " ".join([f"{msg} {resp}" for msg, resp, _ in conversations])
    
    # Convert memories to text, handling both string and dictionary content
    memory_texts = []
    for memory in memories:
        if isinstance(memory, dict):
            content = memory.get('content', '')
            if isinstance(content, dict):
                # Handle dictionary content (e.g., for food preferences)
                if 'foods' in content:
                    memory_texts.append(", ".join(content['foods']))
                elif 'allergens' in content:
                    memory_texts.append(", ".join(content['allergens']))
            else:
                # Handle string content
                memory_texts.append(str(content))
        else:
            # Fallback for any unexpected memory format
            memory_texts.append(str(memory))
    
    context_text += " " + " ".join(memory_texts)
    context_text = context_text.lower()
    
    for pattern in suspicion_patterns:
        if re.search(pattern, ai_response.lower()):
            # Şüpheli ifade bağlamda var mı kontrol et
            if not re.search(pattern, context_text) and not re.search(pattern, user_message.lower()):
                return "Bu konuda bir bilgim yok. Lütfen daha net ifade eder misiniz?"
    
    return ai_response

def query_groq(user_name, user_message):
    """GÜNCELLENMİŞ - Halüsinasyon korumalı"""
    global groq_client
    
    if not groq_client:
        return "Üzgünüm, şu anda yanıt veremiyorum. Lütfen daha sonra tekrar deneyin."
    
    try:
        # Öğrenilebilir bilgi varsa kaydet
        extract_learnable_info(user_name, user_message)
        
        # Bağlam oluştur
        context = build_context_prompt(user_name, user_message)
        
        # API'ye gönderilecek mesajı oluştur - Tip güvenli
        messages: list[dict[str, str]] = [
            {"role": "system", "content": """Sen Asena'sın. Gerçek zamanlı aile asistanısın.

KURALLAR:
1. SADECE sana verilen bilgileri kullan
2. Asla hayali olay/kişi/plan oluşturma  
3. Bilmiyorsan "Bu konuda bilgim yok" de
4. Kısa, net, gerçekçi yanıtlar ver
5. Emoji KULLANMA
6. Gelecek tahmini YAPMA

ÖRNEK YANITLAR:
- "Bu konu hakkında bir bilgim yok"
- "Hafızamda böyle bir kayıt bulunmuyor"
- "Anladım, hatırlatma oluşturuyorum"
- "Mesajını iletiyorum"

Unutma: Güvenilirlik en önemli önceliğin."""},
            {"role": "user", "content": context}
        ]
        
        # API çağrısı
        response = groq_client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=messages,  # type: ignore[arg-type]
            temperature=0.7,
            max_tokens=1000,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
            stop=None
        )
        
        # Yanıtı al ve temizle
        content = response.choices[0].message.content
        if content is None:
            logging.warning("Groq API boş yanıt döndü")
            return "Üzgünüm, bir hata oluştu. Lütfen tekrar deneyin."
        
        ai_response = content.strip()
        
        # Gelişmiş halüsinasyon filtresi uygula
        ai_response = filter_hallucinations(ai_response, user_name, user_message)
        
        # Emojileri temizle
        emoji_pattern = re.compile("["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags (iOS)
            "]+", flags=re.UNICODE)
        ai_response = emoji_pattern.sub(r'', ai_response).strip()
        
        # Konuşmayı kaydet
        save_conversation(user_name, user_message, ai_response)
        
        # Öğrenilebilir bilgi varsa çıkar
        extract_learnable_info(user_name, user_message)
        
        return ai_response
        
    except Exception as e:
        logging.error(f"Groq API hatası: {e}", exc_info=True)
        return "Üzgünüm, bir hata oluştu. Lütfen daha sonra tekrar deneyin."

# --- AI cevabında halüsinasyonu filtrele ---
def filter_hallucination(ai_response, user_name, user_message):
    import re
    suspicion_words = ["dün", "yarın", "hazırlamıştı", "planlıyor", "yarın da", "yemek", "yapmak istiyor"]
    if any(w in ai_response for w in suspicion_words):
        conversations = get_recent_conversations(user_name, limit=10)
        memories = get_memories(user_name)
        context = " ".join([str(x) for x in conversations + memories]).lower()
        for w in suspicion_words:
            if w in ai_response and w not in context and w not in user_message.lower():
                return "Böyle bir kayıt yok."
    return ai_response

# === ROUTES ===
@app.route('/asena', methods=['POST'])
def asena():
    try:
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict() or {'message': request.data.decode('utf-8')}

        user_name = data.get('user', 'Nuri Can')
        user_message = data.get('message', str(data))

        if not user_message or user_message.strip() in ['', '{}']:
            return jsonify({"success": False, "response": "Ne dedin ki?"}), 400

        # Bilgi güncelleme
        if any(x in user_message.lower() for x in ['değilim', 'artık', 'değişti', 'yanlış']):
            if 'yaş' in user_message.lower():
                update_or_create_memory(user_name, "personal_info", user_message)

        response = query_groq(user_name, user_message)

        resp = make_response(response)
        resp.headers['Content-Type'] = 'text/plain; charset=utf-8'
        return resp

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/memories/<user_name>', methods=['GET'])
def get_memories_route(user_name):
    mems = get_memories(user_name)
    convs = get_recent_conversations(user_name, 10)
    return jsonify({
        "user": user_name,
        "memories": [{"type": m["memory_type"], "content": m["content"], "time": m["created_at"]} for m in mems],
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
        "model": "openai/gpt-oss-120b",
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

if __name__ == '__main__':
    print("=" * 70)
    print("ASENA 2.1 – GELİŞTİRİLMİŞ AİLE ASİSTANI (HATIRLATMA DESTEKLİ)")
    print("=" * 70)
    print(f"Başlangıç: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    print("Özellikler: Tarih Bilinci • Kullanıcı Hafızası • Güncelleme • Plan Takibi • Hatırlatma Bildirimleri")
    print("Model: openai/gpt-oss-120b")
    print("=" * 70)
    
    print("\n🔧 Veritabanı kontrol ediliyor...")
    try:
        ensure_database()
        print("✅ Veritabanı hazır!")
    except Exception as e:
        print(f"❌ Veritabanı hatası: {e}")
        print("⚠️  Uygulama yine de başlatılıyor, ancak bazı özellikler çalışmayabilir.")
    
    # Hatırlatıcı servisini başlat
    print("\n🔔 Hatırlatıcı servisi başlatılıyor...")
    try:
        reminder_thread = asena_hatirlatici.start_reminder_service()
        if reminder_thread:
            print("✅ Hatırlatıcı servisi başlatıldı!")
        else:
            print("⚠️  Hatırlatıcı servisi başlatılamadı!")
    except Exception as e:
        print(f"❌ Hatırlatıcı servisi hatası: {e}")
    
    print("\n" + "=" * 70)
    print("🚀 Asena başlatılıyor...")
    print("📡 Sunucu: http://0.0.0.0:5000")
    print("=" * 70 + "\n")
    
    # Uygulamayı başlat
    app.run(host="0.0.0.0", port=5000, debug=True)
