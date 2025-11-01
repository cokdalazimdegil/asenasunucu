import requests
from urllib.parse import quote
import time
import logging
import re

# Son bildirimler için önbellek
recent_notifications = {}

def normalize_topic_name(user_name):
    """
    Kullanıcı adını ntfy topic formatına dönüştürür
    Örnek: "Nuri Can" -> "asena-nuri-can"
    """
    if not user_name:
        return "asena-default"
    
    # Türkçe karakterleri normalize et
    tr_map = str.maketrans(
        'ıİğĞüÜşŞöÖçÇ',
        'iigguussoocc'
    )
    
    # Küçük harfe çevir ve Türkçe karakterleri değiştir
    normalized = user_name.lower().translate(tr_map)
    
    # Sadece alfanumerik ve tire bırak
    normalized = re.sub(r'[^a-z0-9-]', '-', normalized)
    
    # Art arda gelen tireleri tek tireye düşür
    normalized = re.sub(r'-+', '-', normalized)
    
    # Baş ve sondaki tireleri temizle
    normalized = normalized.strip('-')
    
    # asena prefix ekle
    return f"asena-{normalized}"

def format_message_for_recipient(sender, recipient, message):
    """
    Mesajı alıcıya göre formatlar
    """
    # Eğer mesajda zaten gönderen bilgisi varsa, olduğu gibi bırak
    if sender.lower() in message.lower() and any(x in message.lower() for x in ['diyor', 'hatırlat', 'söylüyor']):
        return message
    
    # Aksi halde, gönderen bilgisini ekle
    action_verbs = ['yap', 'et', 'git', 'gel', 'al', 'ver', 'bak', 'ara', 'hazırla', 'getir']
    
    if any(verb in message.lower() for verb in action_verbs):
        return f"{sender} hatırlatıyor: {message}"
    else:
        return f"{sender} diyor ki: {message}"

def send_notification(user_name, message, title=None, priority=3, tags=None, repeat_window_sec=120):
    """
    Kullanıcıya ntfy.sh üzerinden bildirim gönderir
    
    Args:
        user_name: Hedef kullanıcı adı (örn: "Nuri Can", "Rabia")
        message: Bildirim mesajı
        title: Bildirim başlığı (opsiyonel)
        priority: Bildirim önceliği (1-5, varsayılan: 3)
        tags: Bildirim etiketleri (liste, örn: ["bell", "alarm_clock"])
        repeat_window_sec: Aynı bildirimi tekrar göndermemek için süre (saniye)
    
    Returns:
        bool: Bildirim başarılı ise True, değilse False
    """
    def safe_str(s):
        """Güvenli string dönüşümü, Türkçe karakterleri korur"""
        if s is None:
            return ""
        if isinstance(s, str):
            return s
        try:
            return str(s, 'utf-8')
        except (TypeError, UnicodeDecodeError):
            return str(s)
    try:
        global recent_notifications
        
        # Parametre kontrolü
        if not user_name or not message:
            logging.error("Bildirim gönderilemedi: Kullanıcı adı veya mesaj eksik")
            return False
        
        # Mesajı temizle ve güvenli hale getir
        message = safe_str(message).strip()
        if not message:
            logging.error("Bildirim gönderilemedi: Boş mesaj")
            return False
            
        # Kullanıcı adını güvenli hale getir
        user_name = safe_str(user_name).strip()
        if not user_name:
            logging.error("Bildirim gönderilemedi: Geçersiz kullanıcı adı")
            return False
        
        # Tekrar kontrolü
        notif_key = (user_name, message[:50], title or "")
        now = time.time()
        
        if notif_key in recent_notifications:
            last_time = recent_notifications[notif_key]
            if now - last_time < repeat_window_sec:
                logging.info(f"Bildirim atlandı (tekrar): {user_name} - {message[:30]}...")
                return False
        
        recent_notifications[notif_key] = now
        
        # Topic adını oluştur
        topic = normalize_topic_name(user_name)
        
        # Başlık kontrolü ve güvenli hale getirme
        title = safe_str(title) if title else 'Asena Bildirimi'
        
        # Başlığı Latin-1 uyumlu hale getir (Türkçe karakterleri ASCII'ye çevir)
        # Karakterleri eşle: ı->i, ş->s, ç->c, ğ->g, ü->u, ö->o, İ->I, Ş->S, Ç->C, Ğ->G, Ü->U, Ö->O
        tr_to_ascii = str.maketrans(
            'ıışçğöüİŞÇĞÖÜ',
            'iiscgouISCGOU'
        )
        title = title.translate(tr_to_ascii)
        
        # Öncelik kontrolü
        if priority not in (1, 2, 3, 4, 5):
            priority = 3
        
        # Etiketler
        if tags is None:
            tags = []
        elif isinstance(tags, str):
            tags = [tags]
        
        # İstek başlıkları - başlık zaten ASCII uyumlu hale getirildi
        headers = {
            'Title': title[:250],
            'Priority': str(priority),
            'Content-Type': 'text/plain; charset=utf-8'
        }
        
        # Etiketleri güvenli hale getir
        if tags:
            safe_tags = []
            for tag in tags:
                try:
                    safe_tag = safe_str(tag).strip()
                    if safe_tag:
                        safe_tags.append(safe_tag)
                except Exception as e:
                    logging.warning(f"Geçersiz etiket atlandı: {e}")
            if safe_tags:
                headers['Tags'] = ','.join(safe_tags)
        
        # URL
        url = f'https://ntfy.sh/{topic}'
        
        # İstek gönder
        logging.info(f"Bildirim gönderiliyor → {topic} ({user_name})")
        logging.info(f"Başlık: {title}")
        logging.info(f"Mesaj: {message[:100]}...")
        
        try:
            # Mesajı UTF-8 ile encode et
            encoded_message = message.encode('utf-8')
            
            # Headers'ı güvenli hale getir - Latin-1 ile encode et
            safe_headers = {}
            for k, v in headers.items():
                if isinstance(v, str):
                    try:
                        # Header değerlerini Latin-1 ile encode etmeyi dene
                        safe_headers[k] = v.encode('latin-1').decode('latin-1')
                    except (UnicodeEncodeError, UnicodeDecodeError):
                        # Başarısız olursa, Türkçe karakterleri kaldır
                        safe_headers[k] = v.encode('ascii', errors='replace').decode('ascii')
                else:
                    safe_headers[k] = str(v)
            
            # İstek gönder
            response = requests.post(
                url,
                data=encoded_message,
                headers=safe_headers,
                timeout=10
            )
        
            # Hata kontrolü
            response.raise_for_status()
            
            logging.info(f"✅ Bildirim başarıyla gönderildi → {topic}")
            return True
            
        except requests.exceptions.Timeout:
            logging.error(f"❌ Bildirim zaman aşımı: {topic}")
            return False
        except requests.exceptions.RequestException as e:
            logging.error(f"❌ Bildirim hatası ({topic}): {e}")
            return False
        except Exception as e:
            logging.error(f"❌ Beklenmeyen bildirim hatası: {e}")
            return False
            
    except Exception as e:
        logging.error(f"❌ Bildirim işlenirken hata: {e}")
        return False

def forward_message(sender, recipient, message):
    """
    Bir kullanıcıdan diğerine mesaj iletir
    
    Args:
        sender: Gönderen kullanıcı adı
        recipient: Alıcı kullanıcı adı
        message: İletilecek mesaj
    
    Returns:
        bool: Başarılı ise True
    """
    try:
        # Mesajı formatla
        formatted_message = format_message_for_recipient(sender, recipient, message)
        
        # Başlık
        title = f"{sender}'dan Mesajın Var"
        
        # Bildirimi gönder
        return send_notification(
            user_name=recipient,
            message=formatted_message,
            title=title,
            priority=4,
            tags=["envelope", "speech_balloon"]
        )
    except Exception as e:
        logging.error(f"Mesaj iletme hatası: {e}")
        return False

def send_reminder_notification(user_name, reminder_content, reminder_time=None, creator=None):
    """
    Hatırlatma bildirimi gönderir
    
    Args:
        user_name: Hedef kullanıcı
        reminder_content: Hatırlatma içeriği
        reminder_time: Hatırlatma zamanı (opsiyonel)
        creator: Hatırlatmayı oluşturan kişi (opsiyonel)
    
    Returns:
        bool: Başarılı ise True
    """
    try:
        # Başlık ve mesaj
        if creator and creator.lower() != user_name.lower():
            # Başkasından hatırlatma
            title = f"{creator}'dan Hatırlatma"
            message = format_message_for_recipient(creator, user_name, reminder_content)
        else:
            # Kendi hatırlatması
            title = "Hatırlatma Zamanı"
            message = f"Hatırlatma: {reminder_content}"
        
        # Zaman bilgisi ekle
        if reminder_time:
            from datetime import datetime
            try:
                if isinstance(reminder_time, str):
                    reminder_dt = datetime.fromisoformat(reminder_time)
                    time_str = reminder_dt.strftime('%d.%m.%Y %H:%M')
                    message += f"\n\n⏰ Zaman: {time_str}"
            except:
                pass
        
        # Bildirimi gönder
        return send_notification(
            user_name=user_name,
            message=message,
            title=title,
            priority=4,
            tags=["bell", "alarm_clock"]
        )
    except Exception as e:
        logging.error(f"Hatırlatma bildirimi hatası: {e}")
        return False

def send_system_notification(user_name, message, title="Asena Sistemi"):
    """
    Sistem bildirimi gönderir (düşük öncelik)
    
    Args:
        user_name: Hedef kullanıcı
        message: Bildirim mesajı
        title: Başlık (varsayılan: "Asena Sistemi")
    
    Returns:
        bool: Başarılı ise True
    """
    return send_notification(
        user_name=user_name,
        message=message,
        title=title,
        priority=2,
        tags=["information_source"]
    )

def test_notification(user_name):
    """
    Test bildirimi gönderir
    """
    return send_notification(
        user_name=user_name,
        message="Bu bir test bildirimidir. Asena başarıyla çalışıyor!",
        title="Test Bildirimi",
        priority=3,
        tags=["white_check_mark"]
    )

# Bildirim önbelleğini temizle (her 5 dakikada bir)
def cleanup_notification_cache():
    """
    Eski bildirim kayıtlarını temizler
    """
    global recent_notifications
    try:
        now = time.time()
        # 5 dakikadan eski kayıtları sil
        recent_notifications = {
            k: v for k, v in recent_notifications.items()
            if now - v < 300
        }
    except Exception as e:
        logging.error(f"Önbellek temizleme hatası: {e}")

if __name__ == "__main__":
    # Test
    print("🔔 Asena Bildirim Sistemi Test")
    print("-" * 50)
    
    # Topic normalizasyonu testi
    test_names = ["Nuri Can", "Rabia", "Test User"]
    for name in test_names:
        topic = normalize_topic_name(name)
        print(f"{name:15} → {topic}")
    
    print("\n" + "-" * 50)
    print("Test bildirimi göndermek için kullanıcı adı girin:")
    print("Örnek: Nuri Can, Rabia")
    
    user_input = input("\nKullanıcı adı: ").strip()
    if user_input:
        print(f"\n📤 Test bildirimi gönderiliyor: {user_input}")
        success = test_notification(user_input)
        if success:
            print("✅ Bildirim başarıyla gönderildi!")
            print(f"📱 Uygulamanızda '{normalize_topic_name(user_input)}' topic'ine abone olun")
        else:
            print("❌ Bildirim gönderilemedi!")
    else:
        print("\n⚠️  Kullanıcı adı girilmedi, test iptal edildi.")
