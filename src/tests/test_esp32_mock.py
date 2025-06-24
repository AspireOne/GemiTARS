"""
Test ESP32 Mock Service Integration

This test verifies that the ESP32 mock service works correctly
and integrates properly with the TARSAssistant system.
"""

import asyncio
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from services.esp32_mock_service import ESP32MockService
from config import Config


async def test_esp32_mock_service():
    """Test basic ESP32 mock service functionality."""
    print("🧪 Testing ESP32 Mock Service...")
    
    # Initialize service
    esp32_service = ESP32MockService()
    
    try:
        # Test initialization
        print("📡 Testing service initialization...")
        await esp32_service.initialize()
        
        assert esp32_service.is_connected(), "Service should be connected after initialization"
        print("✅ Service initialization successful")
        
        # Test status reporting
        print("📊 Testing status reporting...")
        status = esp32_service.get_status()
        assert status['service_type'] == 'ESP32Mock'
        assert status['is_connected'] == True
        assert status['audio_streaming'] == False
        print("✅ Status reporting working correctly")
        
        # Test audio callback registration
        print("🔗 Testing audio callback registration...")
        audio_received = []
        
        def test_callback(audio_data: bytes):
            audio_received.append(len(audio_data))
            print(f"📨 Received audio chunk: {len(audio_data)} bytes")
        
        esp32_service.set_audio_callback(test_callback)
        print("✅ Audio callback registered")
        
        # Test audio streaming
        print("🎤 Testing audio streaming...")
        await esp32_service.start_audio_streaming()
        
        status = esp32_service.get_status()
        assert status['audio_streaming'] == True
        print("✅ Audio streaming started")
        
        # Wait for some audio data
        print("⏱️ Waiting for audio data (3 seconds)...")
        await asyncio.sleep(3.0)
        
        # Verify we received some audio
        assert len(audio_received) > 0, f"Should have received audio data, got {len(audio_received)} chunks"
        print(f"✅ Received {len(audio_received)} audio chunks")
        
        # Test audio output
        print("🔊 Testing audio output...")
        test_audio = b'\x00' * 1600  # Silent audio chunk
        await esp32_service.play_audio_chunk(test_audio)
        
        # Allow some time for audio to be processed
        await asyncio.sleep(0.5)
        
        statistics = status.get('statistics', {})
        print(f"✅ Audio output test completed")
        
        # Test stopping audio streaming
        print("🔇 Testing stop audio streaming...")
        await esp32_service.stop_audio_streaming()
        
        status = esp32_service.get_status()
        assert status['audio_streaming'] == False
        print("✅ Audio streaming stopped")
        
        # Test image capture (should return None for now)
        print("📷 Testing image capture...")
        image_data = await esp32_service.capture_image()
        assert image_data is None, "Image capture should return None (not implemented)"
        print("✅ Image capture behaving as expected (not implemented)")
        
        print("\n🎉 All ESP32 Mock Service tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise
    finally:
        # Clean shutdown
        print("🔄 Cleaning up...")
        await esp32_service.shutdown()
        print("✅ Cleanup complete")


async def test_integration_with_audio_routing():
    """Test ESP32 service with audio routing similar to TARSAssistant."""
    print("\n🧪 Testing ESP32 Mock Service with Audio Routing...")
    
    esp32_service = ESP32MockService()
    audio_chunks_routed = []
    
    def audio_router(audio_data: bytes):
        """Simple audio router that just logs received data."""
        audio_chunks_routed.append(len(audio_data))
        if len(audio_chunks_routed) % 10 == 0:  # Log every 10th chunk
            print(f"📊 Routed {len(audio_chunks_routed)} audio chunks")
    
    try:
        await esp32_service.initialize()
        esp32_service.set_audio_callback(audio_router)
        await esp32_service.start_audio_streaming()
        
        print("⏱️ Testing audio routing for 2 seconds...")
        await asyncio.sleep(2.0)
        
        await esp32_service.stop_audio_streaming()
        
        assert len(audio_chunks_routed) > 0, "Should have routed some audio chunks"
        print(f"✅ Successfully routed {len(audio_chunks_routed)} audio chunks")
        
        # Test getting final statistics
        status = esp32_service.get_status()
        stats = status.get('statistics', {})
        print(f"📈 Final statistics: {stats}")
        
        print("🎉 Audio routing integration test passed!")
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        raise
    finally:
        await esp32_service.shutdown()


async def main():
    """Run all tests."""
    print("🚀 Starting ESP32 Mock Service Tests\n")
    
    try:
        await test_esp32_mock_service()
        await test_integration_with_audio_routing()
        print("\n🏆 All tests completed successfully!")
        
    except Exception as e:
        print(f"\n💥 Tests failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Tests interrupted by user")
    except Exception as e:
        print(f"\n💥 Fatal error: {e}")
        sys.exit(1)