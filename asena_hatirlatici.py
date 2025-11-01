"""
Asena Hatırlatıcı Modülü
Bu modül, veritabanındaki hatırlatmaları kontrol eder ve zamanı gelenleri bildirir.
"""

import sqlite3
from datetime import datetime, timedelta
import time
import threading
import logging

# Bildirim callback fonksiyonu
send_notification = None

def set_notification_callback(callback):
    """
    Bildirim fonksiyonunu ayarla
    Bu fonksiyon ana uygulama tarafından çağrılır
    """
    global send_notification
    send_notification = callback
    logging.info("✅ Bildirim callback fonksiyonu ayarlandı")

def get_db_connection():
    """
    Thread-safe veritabanı bağlantısı oluştur
    """
    conn = sqlite3.connect('asena_memory.db', timeout=30.0, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.row_factory = sqlite3.Row
    return conn

def normalize_user_name(name):
    """Kullanıcı adını standartlaştır"""
    if not name:
        return None
    name_lower = str(name).lower().strip()
    if 'nuri' in name_lower:
        return 'Nuri Can'
    elif 'rabia' in name_lower:
        return 'Rabia'
    return name.strip()

def save_reminder(user_name, content, reminder_time, target_user=None):
    """
    Veritabanına yeni hatırlatma ekler
    
    Args:
        user_name: Hatırlatmayı oluşturan kullanıcı
        content: Hatırlatma içeriği
        reminder_time: Hatırlatma zamanı (ISO format)
        target_user: Hedef kullanıcı (opsiyonel)
    
    Returns:
        int: Oluşturulan hatırlatmanın ID'si
    """
    try:
        conn = get_db_connection()
        c = conn.cursor()
        now = datetime.now().isoformat()
        
        # Kullanıcı adlarını standartlaştır
        user_name = normalize_user_name(user_name)
        if target_user:
            target_user = normalize_user_name(target_user)
        
        c.execute("""
            INSERT INTO reminders (user_name, content, reminder_time, target_user, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (user_name, content, reminder_time, target_user, now))
        
        reminder_id = c.lastrowid
        conn.commit()
        conn.close()
        
        logging.info(f"✅ Hatırlatma oluşturuldu: ID={reminder_id}, User={user_name}, Target={target_user}")
        return reminder_id
    except Exception as e:
        logging.error(f"❌ Hatırlatma kaydetme hatası: {e}")
        raise

def get_due_reminders():
    """
    Zamanı gelmiş ve henüz bildirilmemiş hatırlatmaları getirir
    
    Returns:
        list: Hatırlatma kayıtlarının listesi
    """
    try:
        conn = get_db_connection()
        c = conn.cursor()
        now = datetime.now().isoformat()
        
        c.execute("""
            SELECT id, user_name, content, reminder_time, target_user, notification_count
            FROM reminders 
            WHERE reminder_time <= ? 
            AND (notified = 0 OR notified IS NULL)
            ORDER BY reminder_time ASC
        """, (now,))
        
        reminders = c.fetchall()
        conn.close()
        
        # Dict'e dönüştür
        result = []
        for row in reminders:
            result.append({
                'id': row['id'],
                'user_name': row['user_name'],
                'content': row['content'],
                'reminder_time': row['reminder_time'],
                'target_user': row['target_user'],
                'notification_count': row['notification_count'] or 0
            })
        
        return result
    except Exception as e:
        logging.error(f"❌ Hatırlatmaları getirme hatası: {e}")
        return []

def mark_reminder_notified(reminder_id):
    """
    Hatırlatmanın gönderildiğini işaretler
    
    Args:
        reminder_id: Hatırlatma ID'si
    """
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        c.execute("""
            UPDATE reminders 
            SET notified = 1,
                notification_count = COALESCE(notification_count, 0) + 1
            WHERE id = ?
        """, (reminder_id,))
        
        conn.commit()
        conn.close()
        
        logging.info(f"✅ Hatırlatma işaretlendi: ID={reminder_id}")
    except Exception as e:
        logging.error(f"❌ Hatırlatma işaretleme hatası: {e}")

def increment_notification_count(reminder_id):
    """
    Hatırlatmanın bildirim sayısını artırır
    
    Args:
        reminder_id: Hatırlatma ID'si
    
    Returns:
        int: Yeni bildirim sayısı
    """
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        c.execute("""
            UPDATE reminders 
            SET notification_count = COALESCE(notification_count, 0) + 1
            WHERE id = ?
        """, (reminder_id,))
        
        c.execute("SELECT notification_count FROM reminders WHERE id = ?", (reminder_id,))
        new_count = c.fetchone()[0]
        
        # Eğer 2 veya daha fazla bildirim gönderildiyse, hatırlatmayı tamamlanmış işaretle
        if new_count >= 2:
            c.execute("UPDATE reminders SET notified = 1 WHERE id = ?", (reminder_id,))
        
        conn.commit()
        conn.close()
        
        logging.info(f"✅ Bildirim sayısı artırıldı: ID={reminder_id}, Count={new_count}")
        return new_count
    except Exception as e:
        logging.error(f"❌ Bildirim sayısı artırma hatası: {e}")
        return 0

def should_send_notification(reminder):
    """
    Hatırlatma için bildirim gönderilip gönderilmeyeceğini kontrol eder
    
    Args:
        reminder: Hatırlatma dict'i
    
    Returns:
        bool: Bildirim gönderilmeli mi?
    """
    # Maksimum 2 bildirim
    if reminder['notification_count'] >= 2:
        return False
    
    # Zamanı kontrol et
    try:
        reminder_dt = datetime.fromisoformat(reminder['reminder_time'])
        now = datetime.now()
        
        # Zaman henüz gelmediyse
        if reminder_dt > now:
            return False
        
        # İlk bildirim için: zaman geçtiyse hemen gönder
        if reminder['notification_count'] == 0:
            return True
        
        # İkinci bildirim için: en az 10 dakika geçmiş olmalı
        time_diff = (now - reminder_dt).total_seconds()
        if reminder['notification_count'] == 1 and time_diff > 600:  # 10 dakika
            return True
        
        return False
    except Exception as e:
        logging.error(f"❌ Zaman kontrolü hatası: {e}")
        return False

def process_reminder(reminder):
    """
    Tek bir hatırlatmayı işler ve bildirim gönderir
    
    Args:
        reminder: Hatırlatma dict'i
    
    Returns:
        bool: Başarılı ise True
    """
    global send_notification
    
    if not send_notification:
        logging.error("❌ Bildirim callback fonksiyonu ayarlanmamış!")
        return False
    
    try:
        # Boş içerik kontrolü
        if not reminder['content'] or not str(reminder['content']).strip():
            logging.warning(f"⚠️  Boş içerikli hatırlatma atlandı: ID={reminder['id']}")
            mark_reminder_notified(reminder['id'])
            return False
        
        # Kullanıcı adlarını standartlaştır
        creator = normalize_user_name(reminder['user_name'])
        target = normalize_user_name(reminder['target_user']) if reminder['target_user'] else None
        
        # Hedef kullanıcıyı belirle
        if target and target != creator:
            # Başkasına hatırlatma
            notify_user = target
            message = f"{creator} hatırlatıyor: {reminder['content']}"
            title = f"{creator}'dan Hatırlatma"
        else:
            # Kendi kendine hatırlatma
            notify_user = creator
            message = f"Hatırlatma: {reminder['content']}"
            title = "Hatırlatma Zamanı"
        
        # Bildirim gönder
        logging.info(f"📤 Bildirim gönderiliyor: {creator} → {notify_user}")
        success = send_notification(
            user_name=notify_user,
            message=message,
            title=title,
            priority=4,
            tags=["bell", "alarm_clock"]
        )
        
        if success:
            # Bildirim sayısını artır
            new_count = increment_notification_count(reminder['id'])
            logging.info(f"✅ Hatırlatma başarıyla gönderildi: ID={reminder['id']}, Count={new_count}")
            return True
        else:
            logging.error(f"❌ Hatırlatma gönderilemedi: ID={reminder['id']}")
            return False
            
    except Exception as e:
        logging.error(f"❌ Hatırlatma işleme hatası (ID={reminder['id']}): {e}")
        return False

def check_reminders():
    """
    Ana hatırlatma kontrol döngüsü
    Her dakika çalışır ve zamanı gelmiş hatırlatmaları işler
    """
    global send_notification
    
    if not send_notification:
        logging.error("❌ Bildirim callback fonksiyonu ayarlanmamış! Hatırlatıcı başlatılamadı.")
        return
    
    logging.info("🔔 Hatırlatıcı servisi başlatıldı")
    
    while True:
        try:
            # Zamanı gelmiş hatırlatmaları al
            reminders = get_due_reminders()
            
            if reminders:
                logging.info(f"📋 {len(reminders)} adet hatırlatma bulundu")
                
                for reminder in reminders:
                    # Bildirim gönderilmeli mi kontrol et
                    if should_send_notification(reminder):
                        process_reminder(reminder)
                        time.sleep(2)  # Bildirimler arası kısa bekleme
            
            # Bir sonraki kontrol için bekle (60 saniye)
            time.sleep(60)
            
        except Exception as e:
            logging.error(f"❌ Hatırlatıcı döngüsü hatası: {e}")
            time.sleep(10)  # Hata durumunda 10 saniye bekle

def start_reminder_service():
    """
    Hatırlatıcı servisini arka planda başlatır
    """
    global send_notification
    
    if not send_notification:
        logging.error("❌ Bildirim callback fonksiyonu ayarlanmamış!")
        return None
    
    thread = threading.Thread(target=check_reminders, daemon=True)
    thread.start()
    logging.info("✅ Hatırlatıcı servisi arka planda başlatıldı")
    return thread

if __name__ == "__main__":
    # Test modu
    print("🔔 Asena Hatırlatıcı Sistemi")
    print("=" * 50)
    print("ℹ️  Bu modül bağımsız çalışamaz.")
    print("ℹ️  Ana uygulama (asenasunucu.py) tarafından import edilmelidir.")
    print("=" * 50)
    
    # Basit bir test bildirimi fonksiyonu
    def test_notification(user_name, message, **kwargs):
        print(f"\n📤 Test Bildirimi:")
        print(f"   Kullanıcı: {user_name}")
        print(f"   Mesaj: {message}")
        if 'title' in kwargs:
            print(f"   Başlık: {kwargs['title']}")
    
    # Callback ayarla
    set_notification_callback(test_notification)
    
    # Test hatırlatması oluştur
    print("\n📝 Test hatırlatması oluşturuluyor...")
    test_time = (datetime.now() - timedelta(minutes=1)).isoformat()  # 1 dakika önce
    
    try:
        reminder_id = save_reminder("Nuri Can", "Test hatırlatması", test_time)
        print(f"✅ Test hatırlatması oluşturuldu: ID={reminder_id}")
        
        # Hatırlatmayı kontrol et
        print("\n🔍 Hatırlatmalar kontrol ediliyor...")
        reminders = get_due_reminders()
        print(f"📋 {len(reminders)} adet zamanı geçmiş hatırlatma bulundu")
        
        if reminders:
            print("\n📤 Test hatırlatması işleniyor...")
            process_reminder(reminders[0])
    except Exception as e:
        print(f"❌ Test hatası: {e}")
