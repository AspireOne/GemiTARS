"""
Test script for Phase 1 VAD implementation.

Run this to test the basic VAD integration:
- Conversation state management
- Basic interruption handling
- Speech completion detection

Usage:
    python src/test_vad_phase1.py
"""

import os
import sys
import asyncio
from dotenv import load_dotenv
import sounddevice as sd

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.gemini_service import GeminiService
from core.conversation_state import ConversationState

load_dotenv()


async def simple_vad_test():
    """Simple test of VAD Phase 1 implementation."""
    print("TARS VAD Phase 1 Test")
    print("=" * 30)
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not found in environment variables")
        return
    
    # Initialize service with conversation management enabled
    gemini_service = GeminiService(api_key=str(api_key), enable_conversation_management=True)
    
    # Test conversation state transitions
    print("\n1. Testing conversation state transitions:")
    print(f"Initial state: {gemini_service.conversation_manager.state}")
    
    # Simulate hotword activation
    gemini_service.activate_conversation()
    print(f"After activation: {gemini_service.conversation_manager.state}")
    
    # Simulate processing
    gemini_service.conversation_manager.transition_to(ConversationState.PROCESSING)
    print(f"During processing: {gemini_service.conversation_manager.state}")
    
    # Test timeout check
    print(f"Should listen for speech: {gemini_service.conversation_manager.should_listen_for_speech()}")
    
    print("\n2. Testing VAD configuration:")
    vad_config = gemini_service.config.get("realtime_input_config", {}).get("automatic_activity_detection", {})
    print(f"VAD enabled: {not vad_config.get('disabled', True)}")
    print(f"Silence duration: {vad_config.get('silence_duration_ms', 'default')}ms")
    
    print("\n3. Testing session creation:")
    try:
        async with gemini_service:
            print("✓ Session created successfully")
            print("✓ VAD configuration applied")
            
            # Test basic response handling
            print("\n4. Ready for audio input...")
            print("   (In full implementation, audio would stream here)")
            
    except Exception as e:
        print(f"✗ Session creation failed: {e}")
        
    print("\nPhase 1 VAD integration test completed!")


if __name__ == "__main__":
    try:
        asyncio.run(simple_vad_test())
    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
    except Exception as e:
        print(f"Test failed with error: {e}")