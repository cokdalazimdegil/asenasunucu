"""
Core Module - Unified System Components
Consolidates redundant modules into optimized, single-responsibility components
"""

from .unified_memory import UnifiedMemoryManager, get_unified_memory
from .unified_emotion import UnifiedEmotionEngine, get_emotion_engine, EmotionResult, analyze_emotion
from .monitoring import (
    UnifiedMonitoring, 
    RateLimiter, 
    PerformanceMonitor,
    get_monitoring, 
    get_groq_rate_limiter,
    safe_operation
)

__all__ = [
    # Memory
    'UnifiedMemoryManager',
    'get_unified_memory',
    
    # Emotion
    'UnifiedEmotionEngine',
    'get_emotion_engine',
    'EmotionResult',
    'analyze_emotion',
    
    # Monitoring
    'UnifiedMonitoring',
    'RateLimiter',
    'PerformanceMonitor',
    'get_monitoring',
    'get_groq_rate_limiter',
    'safe_operation',
]
