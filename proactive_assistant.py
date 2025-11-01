"""
Proaktif Asistan Modülü
Kullanıcıya proaktif önerilerde bulunur
"""

from datetime import datetime, timedelta
import random

def should_be_proactive(time_ctx, user_name, recent_conversations):
    """
    Proaktif davranılması gerekip gerekmediğini belirler
    """
    hour = time_ctx.get('hour', datetime.now().hour)
    
    # Sabah saatleri (07:00 - 10:00)
    if 7 <= hour < 10:
        return True
    
    # Akşam saatleri (18:00 - 21:00)
    if 18 <= hour < 21:
        return True
    
    return False

def generate_proactive_suggestion(user_name, time_ctx):
    """
    Kullanıcıya proaktif öneriler oluşturur
    
    Returns:
        str: Öneri metni veya None
    """
    suggestions = []
    hour = time_ctx.get('hour', datetime.now().hour)
    is_weekend = time_ctx.get('is_weekend', False)
    
    # Sabah önerileri
    if 7 <= hour < 10:
        if user_name == "Nuri Can":
            suggestions.append("Günaydın! Kahven hazır mı? İyi bir gün geçirmeni diliyorum.")
        elif user_name == "Rabia":
            suggestions.append("Günaydın! Bugün antrenman var mı? Enerjik bir gün olsun!")
    
    # Öğle önerileri
    elif 12 <= hour < 14:
        suggestions.append("Öğle yemeği zamanı yaklaşıyor. Ne yemek istersin?")
    
    # Akşam önerileri
    elif 18 <= hour < 21:
        if user_name == "Nuri Can":
            suggestions.append("İşten döndün mü? Rabia ile birlikte müzik dinlemek ister misiniz?")
        elif user_name == "Rabia":
            suggestions.append("Akşam nasıl geçti? Ukulele çalmak ister misin?")
    
    # Gece önerileri
    elif 22 <= hour or hour < 2:
        suggestions.append("Geç oldu, dinlenme zamanı. Yarın için hatırlatma oluşturmamı ister misin?")
    
    # Hafta sonu önerileri
    if is_weekend:
        suggestions.append("Hafta sonu! Birlikte vakit geçirmek için planınız var mı?")
    
    # Rastgele bir öneri seç
    if suggestions:
        return random.choice(suggestions)
    
    return None

def generate_wellness_reminder(user_name, time_ctx):
    """
    Sağlık ve wellness hatırlatmaları oluşturur
    """
    reminders = []
    hour = time_ctx.get('hour', datetime.now().hour)
    
    # Su içme hatırlatması
    if hour % 3 == 0:
        reminders.append("Su içmeyi unutma! Sağlığın için önemli.")
    
    # Hareket hatırlatması
    if hour in [10, 15, 20]:
        reminders.append("Biraz hareket etmek ister misin? Kısa bir yürüyüş iyi gelir.")
    
    # Mola hatırlatması (çalışma saatlerinde)
    if user_name == "Nuri Can" and 9 <= hour < 18:
        if hour % 2 == 0:
            reminders.append("Uzun süredir çalışıyorsun. Kısa bir mola vermek ister misin?")
    
    if reminders:
        return random.choice(reminders)
    
    return None
