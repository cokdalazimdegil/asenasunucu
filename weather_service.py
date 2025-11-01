"""
Hava Durumu Servisi
OpenWeather API'sini kullanarak hava durumu bilgisi sağlar
"""

import requests
import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from dotenv import load_dotenv

# Ortam değişkenlerini yükle
load_dotenv()

# Loglama ayarları
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

class WeatherService:
    """OpenWeather API'sini yönetir"""
    
    def __init__(self, api_key: Optional[str] = None):
        """WeatherService'i başlat"""
        self.api_key = api_key or os.getenv('OPENWEATHER_API_KEY')
        if not self.api_key:
            logger.warning("OpenWeather API anahtarı bulunamadı")
        self.base_url = "https://api.openweathermap.org/data/2.5/weather"
    
    def get_weather(self, city: str = "Istanbul", language: str = "tr") -> Optional[Dict[str, Any]]:
        """
        Şehir için hava durumu bilgisi getir
        
        Args:
            city: Şehir adı
            language: Dil kodu (tr, en, vb.)
            
        Returns:
            Hava durumu bilgisi veya None
        """
        if not self.api_key:
            logger.error("OpenWeather API anahtarı yok")
            return None
        
        try:
            params = {
                'q': city,
                'appid': self.api_key,
                'lang': language,
                'units': 'metric'  # Celsius cinsinden
            }
            
            response = requests.get(self.base_url, params=params, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            
            return {
                'city': data.get('name'),
                'country': data.get('sys', {}).get('country'),
                'temperature': data.get('main', {}).get('temp'),
                'feels_like': data.get('main', {}).get('feels_like'),
                'humidity': data.get('main', {}).get('humidity'),
                'pressure': data.get('main', {}).get('pressure'),
                'description': data.get('weather', [{}])[0].get('description'),
                'wind_speed': data.get('wind', {}).get('speed'),
                'clouds': data.get('clouds', {}).get('all'),
                'sunrise': data.get('sys', {}).get('sunrise'),
                'sunset': data.get('sys', {}).get('sunset')
            }
            
        except requests.exceptions.Timeout:
            logger.error(f"Hava durumu servisi zaman aşımı: {city}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Hava durumu servisi hatası: {e}")
            return None
        except Exception as e:
            logger.error(f"Beklenmeyen hava durumu hatası: {e}")
            return None
    
    def format_weather_message(self, city: str = "Istanbul") -> str:
        """
        Hava durumunu Türkçe mesaj olarak formatla
        
        Args:
            city: Şehir adı
            
        Returns:
            Formatlanmış hava durumu mesajı
        """
        weather = self.get_weather(city)
        
        if not weather:
            return f"Üzgünüm, {city} için hava durumu bilgisi alınamadı."
        
        temp = weather.get('temperature', 'Bilinmiyor')
        feels = weather.get('feels_like', 'Bilinmiyor')
        desc = weather.get('description', 'Bilinmiyor')
        humidity = weather.get('humidity', 'Bilinmiyor')
        wind = weather.get('wind_speed', 'Bilinmiyor')
        
        message = f"""
 **{city} Hava Durumu**

 Sıcaklık: {temp}°C (Hissedilen: {feels}°C)
 Durum: {desc.capitalize() if isinstance(desc, str) else desc}
 Rüzgar: {wind} m/s
 Nem: {humidity}%
"""
        return message.strip()
    
    def should_show_weather(self, user_name: str, hour: int) -> bool:
        """
        Hava durumu gösterilmeli mi kontrol et
        
        Args:
            user_name: Kullanıcı adı
            hour: Saat (0-23)
            
        Returns:
            Hava durumu gösterilmeli mi
        """
        # Sabah saatleri (6-10) ve henüz işe gitmemiş ise
        if 6 <= hour < 10:
            # Nuri Can ve Rabia için geçerli
            if user_name in ["Nuri Can", "Rabia"]:
                return True
        
        return False

# Global instance
_weather_service = None

def get_weather_service() -> WeatherService:
    """WeatherService singleton'ı döndür"""
    global _weather_service
    if _weather_service is None:
        _weather_service = WeatherService()
    return _weather_service

def get_morning_weather() -> str:
    """Sabah hava durumu mesajını döndür"""
    service = get_weather_service()
    return service.format_weather_message("Istanbul")
