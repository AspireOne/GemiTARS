"""
Test ElevenLabs TTS Integration

Basic test to verify ElevenLabs service integration works correctly.
"""

import asyncio
import os

import sys
from dotenv import load_dotenv
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from services.elevenlabs_service import ElevenLabsService
from config import Config

load_dotenv()

async def test_elevenlabs_service_basic():
    """Test basic ElevenLabs service functionality."""
    print("🧪 Testing ElevenLabs service initialization...")
    
    # Check if API key is available
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        print("⚠️ ELEVENLABS_API_KEY not set, skipping live test")
        return
    
    service = ElevenLabsService()
    
    try:
        # Test initialization
        await service.initialize()
        print("✅ Service initialized successfully")
        
        # Test status
        status = service.get_status()
        print(f"📊 Service status: {status}")
        
        # Test availability
        available = service.is_available()
        print(f"🔍 Service available: {available}")
        
        if available:
            print("🎵 Testing TTS streaming with short text...")
            
            # Test with a short phrase
            test_text = "Hello, this is TARS speaking."
            chunk_count = 0
            
            async for chunk in service.stream_tts(test_text):
                chunk_count += 1
                print(f"📦 Received audio chunk {chunk_count}, size: {len(chunk)} bytes")
                if chunk_count >= 5:  # Limit test to first 5 chunks
                    print("🛑 Stopping test after 5 chunks...")
                    break
            
            print(f"✅ TTS streaming test completed ({chunk_count} chunks)")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
    
    finally:
        # Cleanup
        await service.shutdown()
        print("✅ Service shutdown complete")


async def test_config_values():
    """Test that all required config values are set."""
    print("🧪 Testing configuration values...")
    
    required_configs = [
        'ELEVENLABS_VOICE_ID',
        'ELEVENLABS_MODEL_ID', 
        'ELEVENLABS_OUTPUT_FORMAT',
        'ELEVENLABS_CHUNK_SIZE',
        'ELEVENLABS_STABILITY',
        'ELEVENLABS_SIMILARITY_BOOST'
    ]
    
    for config_name in required_configs:
        value = getattr(Config, config_name, None)
        if value is not None:
            print(f"✅ {config_name}: {value}")
        else:
            print(f"❌ {config_name}: NOT SET")
    
    print("📊 Configuration test complete")


if __name__ == "__main__":
    print("🤖 ElevenLabs Integration Test")
    print("=" * 50)
    
    async def run_tests():
        await test_config_values()
        print()
        await test_elevenlabs_service_basic()
    
    try:
        asyncio.run(run_tests())
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"\n💥 Test suite failed: {e}")