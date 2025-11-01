"""
Integration Example: How to Use Unified Core System
Shows practical before/after comparisons
"""

# ============================================================
# BEFORE: Multiple imports, duplicate systems
# ============================================================
"""
from memory_manager import get_memory_manager
from intelligent_memory import IntelligentMemoryManager
from enhanced_sentiment import analyze_sentiment
from error_handler import get_error_handler
from response_cache import get_response_cache

memory_mgr = get_memory_manager()
intelligent_mem = IntelligentMemoryManager()
error_handler = get_error_handler()
cache = get_response_cache()
"""

# ============================================================
# AFTER: Single unified import
# ============================================================
from core import (
    get_unified_memory,
    analyze_emotion,
    get_monitoring,
    get_groq_rate_limiter,
    safe_operation
)

memory = get_unified_memory()
monitor = get_monitoring()
groq_limiter = get_groq_rate_limiter()


# ============================================================
# Example 1: Memory Operations
# ============================================================

def example_memory_operations(user_name: str):
    """Show unified memory usage"""
    
    # Add permanent memory
    memory.add_memory(
        user_name=user_name,
        memory_type='preference',
        content='Sevdiği içecek: Türk kahvesi',
        importance=8,
        is_permanent=True
    )
    
    # Add temporary memory with expiration
    from datetime import datetime, timedelta
    memory.add_memory(
        user_name=user_name,
        memory_type='plan',
        content='Yarın doktora gidecek',
        importance=7,
        expires_at=datetime.now() + timedelta(days=2)
    )
    
    # Get contextually relevant memories
    current_msg = "kahve içmek istiyorum"
    relevant = memory.get_contextual_memories(user_name, current_msg, limit=5)
    
    print(f"Found {len(relevant)} relevant memories")
    for mem in relevant:
        print(f"  - {mem['content']}")
    
    # Get recent conversations
    conversations = memory.get_recent_conversations(user_name, limit=3)
    print(f"\nRecent conversations: {len(conversations)}")
    
    # Build unified context for AI
    context = memory.build_context(user_name, current_msg)
    print(f"\nContext for AI:\n{context}")


# ============================================================
# Example 2: Emotion Analysis
# ============================================================

def example_emotion_analysis():
    """Show emotion analysis with AI and fallback"""
    
    messages = [
        "Çok mutluyum bugün!",
        "Moralim çok bozuk, üzgünüm",
        "Bu durum beni çok sinirlendirdi",
        "Normal bir gün işte"
    ]
    
    for msg in messages:
        # Analyze emotion (AI first, then fallback)
        emotion_result = analyze_emotion(msg)
        
        print(f"\nMessage: {msg}")
        print(f"Emotion: {emotion_result.emotion}")
        print(f"Intensity: {emotion_result.intensity}/10")
        print(f"Confidence: {emotion_result.confidence:.2f}")
        
        # Get response guidance
        from core import get_emotion_engine
        engine = get_emotion_engine()
        guide = engine.get_response_guide(emotion_result.emotion, emotion_result.intensity)
        
        print(f"Response Tone: {guide['tone']}")
        if guide['prefixes']:
            print(f"Suggested Prefix: {guide['prefixes'][0]}")


# ============================================================
# Example 3: Rate Limiting Groq API
# ============================================================

@safe_operation(fallback_return="Error occurred", log_errors=True)
def example_groq_call_with_rate_limit(user_name: str, message: str):
    """Show rate-limited Groq API call"""
    
    # Check rate limit
    if not groq_limiter.can_request('groq_api'):
        remaining = groq_limiter.get_remaining('groq_api')
        reset_time = groq_limiter.get_reset_time('groq_api')
        
        return {
            'success': False,
            'error': f'API limit reached. {remaining} calls remaining. Resets at {reset_time}'
        }
    
    # Track performance
    with monitor.measure('groq_api_call'):
        # Simulate Groq API call
        import time
        time.sleep(0.1)  # Simulated API delay
        
        response = f"Mock response for: {message}"
    
    # Log success
    monitor.log_error(
        error_type='INFO',
        error_message=f'Groq call successful for {user_name}',
        severity='INFO'
    )
    
    return {'success': True, 'response': response}


# ============================================================
# Example 4: Performance Monitoring
# ============================================================

def example_performance_monitoring():
    """Show performance tracking"""
    
    # Simulate some operations
    with monitor.measure('database_query'):
        import time
        time.sleep(0.05)
    
    with monitor.measure('groq_api_call'):
        time.sleep(0.15)
    
    with monitor.measure('database_query'):
        time.sleep(0.03)
    
    # Get statistics
    stats = monitor.performance.get_stats()
    
    print("\n=== Performance Statistics ===")
    for operation, data in stats.items():
        print(f"\n{operation}:")
        print(f"  Count: {data['count']}")
        print(f"  Avg: {data['avg']:.3f}s")
        print(f"  Max: {data['max']:.3f}s")


# ============================================================
# Example 5: Complete Chat Flow
# ============================================================

def example_complete_chat_flow(user_name: str, message: str):
    """Show complete flow with all components"""
    
    print(f"\n{'='*60}")
    print(f"User: {user_name}")
    print(f"Message: {message}")
    print(f"{'='*60}\n")
    
    # 1. Check rate limit
    if not groq_limiter.can_request(user_name):
        return "Too many requests, please wait."
    
    # 2. Analyze emotion
    with monitor.measure('emotion_analysis'):
        emotion = analyze_emotion(message)
    
    print(f"Detected Emotion: {emotion.emotion} (intensity: {emotion.intensity})")
    
    # 3. Get relevant context
    with monitor.measure('context_building'):
        context = memory.build_context(user_name, message)
    
    print(f"Context Length: {len(context)} chars")
    
    # 4. Generate response (simulated)
    with monitor.measure('response_generation'):
        import time
        time.sleep(0.1)  # Simulate processing
        response = f"[{emotion.emotion.upper()}] Response to: {message}"
    
    # 5. Save conversation
    memory.add_conversation(user_name, message, response, emotion.to_dict())
    
    # 6. Add short-term memory
    memory.add_short_term(user_name, {'type': 'chat', 'content': message[:50]})
    
    print(f"\nResponse: {response}")
    
    # 7. Show performance
    stats = monitor.performance.get_stats('response_generation')
    if stats:
        print(f"Response Time: {stats['avg']:.3f}s")
    
    return response


# ============================================================
# Main Demo
# ============================================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("UNIFIED CORE SYSTEM - INTEGRATION EXAMPLES")
    print("="*60)
    
    # Example 1: Memory
    print("\n\n--- Example 1: Memory Operations ---")
    example_memory_operations("Nuri Can")
    
    # Example 2: Emotion
    print("\n\n--- Example 2: Emotion Analysis ---")
    example_emotion_analysis()
    
    # Example 3: Rate Limiting
    print("\n\n--- Example 3: Rate Limited API Call ---")
    result = example_groq_call_with_rate_limit("Nuri Can", "Test message")
    print(f"Result: {result}")
    
    # Example 4: Performance
    print("\n\n--- Example 4: Performance Monitoring ---")
    example_performance_monitoring()
    
    # Example 5: Complete Flow
    print("\n\n--- Example 5: Complete Chat Flow ---")
    example_complete_chat_flow("Nuri Can", "Bugün çok mutluyum!")
    
    print("\n\n" + "="*60)
    print("DEMO COMPLETE")
    print("="*60 + "\n")
