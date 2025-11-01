"""
Advanced TV Management System
Provides intelligent TV control with state tracking, scheduling, and device management
"""

import logging
import sqlite3
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import json
import tv_connect
from error_handler import safe_operation, get_error_handler

logger = logging.getLogger(__name__)


@dataclass
class TVState:
    """Represents current TV state"""
    ip: str
    is_on: bool
    volume: int
    is_muted: bool
    current_app: Optional[str]
    last_updated: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'ip': self.ip,
            'is_on': self.is_on,
            'volume': self.volume,
            'is_muted': self.is_muted,
            'current_app': self.current_app,
            'last_updated': self.last_updated.isoformat()
        }


class TVManager:
    """Advanced TV management with state tracking and scheduling"""
    
    # App package names
    APPS = {
        'netflix': 'com.netflix.ninja',
        'hbo': 'com.hbo.hbonow',
        'youtube': 'com.google.android.youtube.tv',
        'prime': 'com.amazon.amazonvideo.livingroom',
        'disney': 'com.disney.disneyplus',
        'spotify': 'com.spotify.tv',
        'tuner': 'com.android.tv.tuner',
        'settings': 'com.android.tv.settings',
        'home': 'com.google.android.leanbacklauncher'
    }
    
    def __init__(self, tv_ip: str = '192.168.1.23', db_path: str = 'asena_memory.db'):
        """Initialize TV Manager"""
        self.tv_ip = tv_ip
        self.db_path = db_path
        self.state = TVState(
            ip=tv_ip,
            is_on=False,
            volume=15,
            is_muted=False,
            current_app=None,
            last_updated=datetime.now()
        )
        self.connected = False
        self.init_database()
    
    def init_database(self):
        """Initialize TV control database tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # TV commands history
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS tv_commands (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        command_type TEXT NOT NULL,
                        command_params TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        success BOOLEAN DEFAULT 1
                    )
                ''')
                
                # TV state snapshots
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS tv_state_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tv_ip TEXT NOT NULL,
                        is_on BOOLEAN,
                        volume INTEGER,
                        is_muted BOOLEAN,
                        current_app TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Scheduled commands
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS tv_schedules (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        command_type TEXT NOT NULL,
                        command_params TEXT,
                        schedule_time TIME NOT NULL,
                        repeat_daily BOOLEAN DEFAULT 0,
                        enabled BOOLEAN DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Favorite presets
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS tv_presets (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE NOT NULL,
                        commands TEXT NOT NULL,
                        description TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Indices
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_tv_commands_time ON tv_commands(timestamp)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_tv_state_time ON tv_state_history(timestamp)')
                
                conn.commit()
                logger.info("TV management database initialized")
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
            get_error_handler().log_error(
                error_type='DatabaseError',
                error_message=str(e),
                function_name='init_database',
                severity='ERROR'
            )
    
    @safe_operation(fallback_return=False)
    def connect(self, port: int = 5555) -> bool:
        """Connect to TV"""
        if tv_connect.connect_adb(self.tv_ip, port):
            self.connected = True
            self.state.is_on = True
            self.state.last_updated = datetime.now()
            self._save_command('connect', {'port': port})
            return True
        return False
    
    @safe_operation(fallback_return=False)
    def disconnect(self, port: int = 5555) -> bool:
        """Disconnect from TV"""
        if tv_connect.disconnect_adb(self.tv_ip, port):
            self.connected = False
            self._save_command('disconnect', {'port': port})
            return True
        return False
    
    @safe_operation(fallback_return=False)
    def power_on(self) -> bool:
        """Turn TV on"""
        if not self.connected:
            self.connect()
        
        if tv_connect.tv_power(self.tv_ip, state='on'):
            self.state.is_on = True
            self.state.last_updated = datetime.now()
            self._save_command('power_on')
            return True
        return False
    
    @safe_operation(fallback_return=False)
    def power_off(self) -> bool:
        """Turn TV off"""
        if not self.connected:
            return False
        
        if tv_connect.tv_power(self.tv_ip, state='off'):
            self.state.is_on = False
            self.state.last_updated = datetime.now()
            self._save_command('power_off')
            return True
        return False
    
    @safe_operation(fallback_return=False)
    def set_volume(self, level: int, max_level: int = 30) -> bool:
        """Set volume to specific level"""
        if not self.connected:
            self.connect()
        
        # Clamp to valid range
        level = max(0, min(level, max_level))
        
        if tv_connect.set_volume(self.tv_ip, level, max_level):
            self.state.volume = level
            self.state.last_updated = datetime.now()
            self._save_command('set_volume', {'level': level})
            return True
        return False
    
    @safe_operation(fallback_return=False)
    def volume_up(self, steps: int = 1) -> bool:
        """Increase volume"""
        if not self.connected:
            self.connect()
        
        if tv_connect.volume_up(self.tv_ip, steps):
            self.state.volume = min(self.state.volume + steps, 30)
            self.state.last_updated = datetime.now()
            self._save_command('volume_up', {'steps': steps})
            return True
        return False
    
    @safe_operation(fallback_return=False)
    def volume_down(self, steps: int = 1) -> bool:
        """Decrease volume"""
        if not self.connected:
            self.connect()
        
        if tv_connect.volume_down(self.tv_ip, steps):
            self.state.volume = max(self.state.volume - steps, 0)
            self.state.last_updated = datetime.now()
            self._save_command('volume_down', {'steps': steps})
            return True
        return False
    
    @safe_operation(fallback_return=False)
    def mute(self) -> bool:
        """Toggle mute"""
        if not self.connected:
            self.connect()
        
        if tv_connect.mute(self.tv_ip):
            self.state.is_muted = not self.state.is_muted
            self.state.last_updated = datetime.now()
            self._save_command('mute')
            return True
        return False
    
    @safe_operation(fallback_return=False)
    def open_app(self, app_name: str) -> bool:
        """Open app by name"""
        if not self.connected:
            self.connect()
        
        app_name = app_name.lower()
        if app_name not in self.APPS:
            logger.error(f"Unknown app: {app_name}")
            return False
        
        package = self.APPS[app_name]
        
        if tv_connect.open_app(self.tv_ip, package):
            self.state.current_app = app_name
            self.state.last_updated = datetime.now()
            self._save_command('open_app', {'app': app_name})
            return True
        return False
    
    @safe_operation(fallback_return=False)
    def youtube_search(self, query: str) -> bool:
        """Search on YouTube"""
        if not self.connected:
            self.connect()
        
        if tv_connect.open_youtube_search(self.tv_ip, query):
            self.state.current_app = 'youtube'
            self.state.last_updated = datetime.now()
            self._save_command('youtube_search', {'query': query})
            return True
        return False
    
    @safe_operation(fallback_return=False)
    def go_home(self) -> bool:
        """Return to home screen"""
        if not self.connected:
            self.connect()
        
        if tv_connect.tv_home(self.tv_ip):
            self.state.current_app = 'home'
            self.state.last_updated = datetime.now()
            self._save_command('go_home')
            return True
        return False
    
    @safe_operation(fallback_return=False)
    def send_key(self, key_name: str) -> bool:
        """Send key by name"""
        key_name = key_name.upper()
        if key_name not in tv_connect.KEYCODES:
            logger.error(f"Unknown key: {key_name}")
            return False
        
        keycode = tv_connect.KEYCODES[key_name]
        
        if not self.connected:
            self.connect()
        
        if tv_connect.send_key(self.tv_ip, keycode):
            self._save_command('send_key', {'key': key_name})
            return True
        return False
    
    def create_preset(self, name: str, commands: List[Dict[str, Any]], 
                     description: str = '') -> bool:
        """Create a preset for multiple commands"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                commands_json = json.dumps(commands)
                
                cursor.execute('''
                    INSERT OR REPLACE INTO tv_presets 
                    (name, commands, description)
                    VALUES (?, ?, ?)
                ''', (name, commands_json, description))
                
                conn.commit()
                logger.info(f"Preset created: {name}")
                return True
        except Exception as e:
            logger.error(f"Error creating preset: {e}")
            return False
    
    def execute_preset(self, name: str) -> bool:
        """Execute a saved preset"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT commands FROM tv_presets WHERE name = ?
                ''', (name,))
                
                result = cursor.fetchone()
                if not result:
                    logger.error(f"Preset not found: {name}")
                    return False
                
                commands = json.loads(result[0])
                
                # Execute each command
                for cmd in commands:
                    command_type = cmd.get('type')
                    params = cmd.get('params', {})
                    
                    if command_type == 'volume':
                        self.set_volume(params.get('level', 15))
                    elif command_type == 'app':
                        self.open_app(params.get('app', 'netflix'))
                    elif command_type == 'power':
                        if params.get('state') == 'on':
                            self.power_on()
                        else:
                            self.power_off()
                    elif command_type == 'key':
                        self.send_key(params.get('key'))
                
                logger.info(f"Preset executed: {name}")
                return True
        except Exception as e:
            logger.error(f"Error executing preset: {e}")
            return False
    
    def get_available_apps(self) -> List[str]:
        """Get list of available apps"""
        return list(self.APPS.keys())
    
    def get_state(self) -> Dict[str, Any]:
        """Get current TV state"""
        return self.state.to_dict()
    
    def _save_command(self, command_type: str, params: Optional[Dict] = None) -> None:
        """Save command to history"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                params_json = json.dumps(params) if params else None
                
                cursor.execute('''
                    INSERT INTO tv_commands (command_type, command_params)
                    VALUES (?, ?)
                ''', (command_type, params_json))
                
                conn.commit()
        except Exception as e:
            logger.error(f"Error saving command: {e}")
    
    def get_command_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get command history"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM tv_commands 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (limit,))
                
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting command history: {e}")
            return []
    
    def get_presets(self) -> List[Dict[str, str]]:
        """Get list of saved presets"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT name, description FROM tv_presets 
                    ORDER BY name
                ''')
                
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting presets: {e}")
            return []


# Global instance
_tv_manager = None


def get_tv_manager(tv_ip: str = '192.168.1.23') -> TVManager:
    """Get or create global TV manager instance"""
    global _tv_manager
    if _tv_manager is None:
        _tv_manager = TVManager(tv_ip=tv_ip)
    return _tv_manager
