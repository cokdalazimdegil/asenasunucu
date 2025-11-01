"""
TV Kontrol Modülü
ADB üzerinden Android TV kontrolü sağlar
"""

import subprocess
import sys
import time
import logging

# Logging yapılandırması
logging.basicConfig(level=logging.INFO)

def run_adb_command(command, timeout=10):
    """
    ADB komutunu çalıştırır ve sonucu döndürür
    
    Args:
        command: ADB komut listesi
        timeout: Maksimum bekleme süresi (saniye)
    
    Returns:
        tuple: (success, output, error)
    """
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        success = result.returncode == 0
        output = result.stdout.strip()
        error = result.stderr.strip()
        
        if success:
            logging.debug(f"✅ ADB komutu başarılı: {' '.join(command)}")
        else:
            logging.error(f"❌ ADB komutu başarısız: {error}")
        
        return success, output, error
    except subprocess.TimeoutExpired:
        logging.error(f"⏱️  ADB komutu zaman aşımı: {' '.join(command)}")
        return False, "", "Timeout"
    except Exception as e:
        logging.error(f"❌ ADB komutu hatası: {e}")
        return False, "", str(e)

def connect_adb(ip, port=5555):
    """
    ADB ile TV'ye bağlanır
    
    Args:
        ip: TV IP adresi
        port: ADB port (varsayılan: 5555)
    
    Returns:
        bool: Bağlantı başarılı ise True
    """
    host = f"{ip}:{port}"
    logging.info(f"📡 TV'ye bağlanılıyor: {host}")
    
    success, output, error = run_adb_command(["adb", "connect", host])
    
    if success and "connected" in output.lower():
        logging.info(f"✅ TV'ye başarıyla bağlanıldı: {host}")
        return True
    else:
        logging.error(f"❌ TV'ye bağlanılamadı: {error}")
        return False

def disconnect_adb(ip, port=5555):
    """
    ADB bağlantısını keser
    
    Args:
        ip: TV IP adresi
        port: ADB port
    
    Returns:
        bool: Başarılı ise True
    """
    host = f"{ip}:{port}"
    success, output, error = run_adb_command(["adb", "disconnect", host])
    
    if success:
        logging.info(f"✅ Bağlantı kesildi: {host}")
    return success

def tv_power(ip, state="toggle", port=5555):
    """
    TV'yi açar/kapatır
    
    Args:
        ip: TV IP adresi
        state: 'toggle', 'on', veya 'off' (varsayılan: toggle)
        port: ADB port
    
    Returns:
        bool: Başarılı ise True
    """
    logging.info(f"🔌 TV güç komutu: {state}")
    
    # Power button keycode: 26
    success, _, _ = run_adb_command([
        "adb", "-s", f"{ip}:{port}",
        "shell", "input", "keyevent", "26"
    ])
    
    if success:
        time.sleep(1)
        logging.info(f"✅ TV güç komutu gönderildi")
    
    return success

def open_app(ip, package, port=5555):
    """
    TV'de uygulama açar
    
    Args:
        ip: TV IP adresi
        package: Uygulama paket adı
        port: ADB port
    
    Returns:
        bool: Başarılı ise True
    """
    logging.info(f"📱 Uygulama açılıyor: {package}")
    
    success, _, _ = run_adb_command([
        "adb", "-s", f"{ip}:{port}",
        "shell", "monkey", "-p", package,
        "-c", "android.intent.category.LAUNCHER", "1"
    ])
    
    if success:
        logging.info(f"✅ Uygulama açıldı: {package}")
    
    return success

def open_youtube_search(ip, query, port=5555):
    """
    YouTube'da arama yapar
    
    Args:
        ip: TV IP adresi
        query: Arama sorgusu
        port: ADB port
    
    Returns:
        bool: Başarılı ise True
    """
    logging.info(f"🔍 YouTube araması: {query}")
    
    # Önce YouTube'u aç
    open_app(ip, "com.google.android.youtube.tv", port)
    time.sleep(3)
    
    # Arama URL'si ile aç
    search_url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
    
    success, _, _ = run_adb_command([
        "adb", "-s", f"{ip}:{port}",
        "shell", "am", "start", "-a", "android.intent.action.VIEW",
        "-d", search_url
    ])
    
    if success:
        logging.info(f"✅ YouTube araması başlatıldı: {query}")
    
    return success

def open_netflix(ip, port=5555):
    """
    Netflix açar
    
    Args:
        ip: TV IP adresi
        port: ADB port
    
    Returns:
        bool: Başarılı ise True
    """
    logging.info("📺 Netflix açılıyor")
    return open_app(ip, "com.netflix.ninja", port)

def open_hbo_max(ip, port=5555):
    """
    HBO Max açar
    
    Args:
        ip: TV IP adresi
        port: ADB port
    
    Returns:
        bool: Başarılı ise True
    """
    logging.info("📺 HBO Max açılıyor")
    return open_app(ip, "com.hbo.hbonow", port)

def tv_home(ip, port=5555):
    """
    Ana ekrana döner
    
    Args:
        ip: TV IP adresi
        port: ADB port
    
    Returns:
        bool: Başarılı ise True
    """
    logging.info("🏠 Ana ekrana dönülüyor")
    
    success, _, _ = run_adb_command([
        "adb", "-s", f"{ip}:{port}",
        "shell", "input", "keyevent", "3"
    ])
    
    return success

def volume_up(ip, count=1, port=5555):
    """
    Ses seviyesini artırır
    
    Args:
        ip: TV IP adresi
        count: Kaç kez artırılacak
        port: ADB port
    
    Returns:
        bool: Başarılı ise True
    """
    logging.info(f"🔊 Ses artırılıyor: {count} kez")
    
    success = True
    for _ in range(int(count)):
        s, _, _ = run_adb_command([
            "adb", "-s", f"{ip}:{port}",
            "shell", "input", "keyevent", "24"
        ])
        success = success and s
        time.sleep(0.1)
    
    if success:
        logging.info(f"✅ Ses {count} kez artırıldı")
    
    return success

def volume_down(ip, count=1, port=5555):
    """
    Ses seviyesini azaltır
    
    Args:
        ip: TV IP adresi
        count: Kaç kez azaltılacak
        port: ADB port
    
    Returns:
        bool: Başarılı ise True
    """
    logging.info(f"🔉 Ses azaltılıyor: {count} kez")
    
    success = True
    for _ in range(int(count)):
        s, _, _ = run_adb_command([
            "adb", "-s", f"{ip}:{port}",
            "shell", "input", "keyevent", "25"
        ])
        success = success and s
        time.sleep(0.1)
    
    if success:
        logging.info(f"✅ Ses {count} kez azaltıldı")
    
    return success

def mute(ip, port=5555):
    """
    Sesi kapatır/açar (toggle)
    
    Args:
        ip: TV IP adresi
        port: ADB port
    
    Returns:
        bool: Başarılı ise True
    """
    logging.info("🔇 Sessiz modu")
    
    success, _, _ = run_adb_command([
        "adb", "-s", f"{ip}:{port}",
        "shell", "input", "keyevent", "164"
    ])
    
    if success:
        logging.info("✅ Sessiz mod değiştirildi")
    
    return success

def set_volume(ip, level=15, max_level=30, port=5555):
    """
    Ses seviyesini belirli bir değere ayarlar
    
    Args:
        ip: TV IP adresi
        level: Hedef ses seviyesi (0-max_level)
        max_level: Maksimum ses seviyesi (varsayılan: 30)
        port: ADB port
    
    Returns:
        bool: Başarılı ise True
    """
    logging.info(f"🔊 Ses seviyesi ayarlanıyor: {level}/{max_level}")
    
    # Önce sesi minimum seviyeye çek
    volume_down(ip, max_level, port)
    time.sleep(0.5)
    
    # Sonra istenen seviyeye çıkar
    success = volume_up(ip, int(level), port)
    
    if success:
        logging.info(f"✅ Ses seviyesi {level} olarak ayarlandı")
    
    return success

def send_key(ip, keycode, port=5555):
    """
    Belirli bir tuş kodunu gönderir
    
    Args:
        ip: TV IP adresi
        keycode: Android keycode
        port: ADB port
    
    Returns:
        bool: Başarılı ise True
    """
    success, _, _ = run_adb_command([
        "adb", "-s", f"{ip}:{port}",
        "shell", "input", "keyevent", str(keycode)
    ])
    
    return success

# Popüler keycode'lar
KEYCODES = {
    'HOME': 3,
    'BACK': 4,
    'POWER': 26,
    'VOLUME_UP': 24,
    'VOLUME_DOWN': 25,
    'VOLUME_MUTE': 164,
    'DPAD_UP': 19,
    'DPAD_DOWN': 20,
    'DPAD_LEFT': 21,
    'DPAD_RIGHT': 22,
    'DPAD_CENTER': 23,
    'MENU': 82,
    'PLAY_PAUSE': 85,
}

if __name__ == "__main__":
    print("📺 Asena TV Kontrol Modülü")
    print("=" * 50)
    
    # Komut satırı argümanları
    ip = sys.argv[1] if len(sys.argv) > 1 else "192.168.1.23"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 5555
    command = sys.argv[3] if len(sys.argv) > 3 else None
    
    if not command:
        print("\nKullanım:")
        print(f"  python {sys.argv[0]} <IP> [PORT] <KOMUT> [PARAMETRE]")
        print("\nKomutlar:")
        print("  power_toggle      - TV'yi aç/kapat")
        print("  netflix           - Netflix aç")
        print("  hbo               - HBO Max aç")
        print("  youtube [arama]   - YouTube aç (arama opsiyonel)")
        print("  home              - Ana ekran")
        print("  volup [sayı]      - Ses artır")
        print("  voldown [sayı]    - Ses azalt")
        print("  mute              - Sessiz")
        print("  set_volume [0-30] - Ses seviyesi ayarla")
        sys.exit(0)
    
    # TV'ye bağlan
    if not connect_adb(ip, port):
        print("❌ TV'ye bağlanılamadı!")
        sys.exit(1)
    
    # Komutu çalıştır
    if command == "power_toggle":
        tv_power(ip, port=port)
    elif command == "netflix":
        open_netflix(ip, port)
    elif command == "hbo":
        open_hbo_max(ip, port)
    elif command == "youtube":
        query = sys.argv[4] if len(sys.argv) > 4 else ""
        if query:
            open_youtube_search(ip, query, port)
        else:
            open_app(ip, "com.google.android.youtube.tv", port)
    elif command == "home":
        tv_home(ip, port)
    elif command == "volup":
        n = int(sys.argv[4]) if len(sys.argv) > 4 else 1
        volume_up(ip, n, port)
    elif command == "voldown":
        n = int(sys.argv[4]) if len(sys.argv) > 4 else 1
        volume_down(ip, n, port)
    elif command == "mute":
        mute(ip, port)
    elif command == "set_volume":
        v = int(sys.argv[4]) if len(sys.argv) > 4 else 15
        set_volume(ip, v, port=port)
    else:
        print(f"❌ Bilinmeyen komut: {command}")
        sys.exit(1)
