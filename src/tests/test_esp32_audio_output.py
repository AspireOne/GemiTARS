"""
Test ESP32 Mock Service Audio Output

Test to diagnose why audio chunks are processed but no sound is produced.
"""

import asyncio
import numpy as np
import sounddevice as sd
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from services.esp32_mock_service import ESP32MockService
from config import Config


async def test_esp32_audio_output():
    """Test ESP32 mock service audio output with known good audio."""
    print("🧪 Testing ESP32 Mock Service Audio Output")
    print("=" * 50)
    
    # Test 1: Check available audio devices
    print("🔍 Available audio devices:")
    print(sd.query_devices())
    print(f"🔍 Default output device: {sd.default.device[1]}")
    print()
    
    # Test 2: Generate test tone and play directly with sounddevice
    print("🎵 Test 2: Direct sounddevice test tone...")
    sample_rate = Config.AUDIO_SAMPLE_RATE
    duration = 1.0  # 1 second
    frequency = 440  # A4 note
    
    # Generate sine wave
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    tone = np.sin(2 * np.pi * frequency * t) * 0.3  # 30% volume
    tone_int16 = (tone * 32767).astype(np.int16)
    
    print(f"🔊 Playing {frequency}Hz tone for {duration}s...")
    print(f"🔍 Tone shape: {tone_int16.shape}, dtype: {tone_int16.dtype}")
    
    try:
        sd.play(tone_int16, samplerate=sample_rate, blocking=True)
        print("✅ Direct sounddevice test completed")
    except Exception as e:
        print(f"❌ Direct sounddevice test failed: {e}")
        return
    
    print()
    
    # Test 3: Test ESP32MockService with the same tone
    print("🎵 Test 3: ESP32MockService with test tone...")
    
    service = ESP32MockService()
    try:
        await service.initialize()
        print("✅ ESP32MockService initialized")
        
        # Split tone into chunks like ElevenLabs would
        chunk_size = 256  # samples per chunk (matches ElevenLabs output)
        tone_bytes = tone_int16.tobytes()
        chunk_size_bytes = chunk_size * 2  # 2 bytes per int16 sample
        
        print(f"🔍 Total audio size: {len(tone_bytes)} bytes")
        print(f"🔍 Chunk size: {chunk_size_bytes} bytes ({chunk_size} samples)")
        
        # Send chunks to ESP32 service
        for i in range(0, len(tone_bytes), chunk_size_bytes):
            chunk = tone_bytes[i:i + chunk_size_bytes]
            if len(chunk) > 0:
                await service.play_audio_chunk(chunk)
                print(f"📦 Sent chunk {i//chunk_size_bytes + 1}, size: {len(chunk)} bytes")
        
        # Wait for all audio to finish playing
        await asyncio.sleep(2)
        print("✅ ESP32MockService test completed")
        
    except Exception as e:
        print(f"❌ ESP32MockService test failed: {e}")
    finally:
        await service.shutdown()
    
    print()
    
    # Test 4: Test with ElevenLabs-like audio format
    print("🎵 Test 4: Test with ElevenLabs-like stereo audio...")
    
    # Create stereo tone (simulate ElevenLabs output)
    stereo_tone = np.column_stack([tone_int16, tone_int16])  # Duplicate to stereo
    stereo_bytes = stereo_tone.tobytes()
    
    service2 = ESP32MockService()
    try:
        await service2.initialize()
        
        # Send stereo chunks (like ElevenLabs sends)
        chunk_size_bytes = 512  # Match ElevenLabs chunk size
        
        print(f"🔍 Stereo audio size: {len(stereo_bytes)} bytes")
        print("🔊 Playing stereo audio through ESP32MockService...")
        
        for i in range(0, len(stereo_bytes), chunk_size_bytes):
            chunk = stereo_bytes[i:i + chunk_size_bytes]
            if len(chunk) > 0:
                await service2.play_audio_chunk(chunk)
        
        # Wait for all audio to finish
        await asyncio.sleep(2)
        print("✅ Stereo audio test completed")
        
    except Exception as e:
        print(f"❌ Stereo audio test failed: {e}")
    finally:
        await service2.shutdown()


async def test_audio_device_selection():
    """Test different audio device configurations."""
    print("🧪 Testing Audio Device Selection")
    print("=" * 50)
    
    try:
        # Get device info
        devices = sd.query_devices()
        default_output = sd.default.device[1]
        
        print(f"🔍 Default output device ID: {default_output}")
        if default_output is not None:
            device_info = devices[default_output]
            print(f"🔍 Device info: {device_info}")
            print(f"🔍 Max output channels: {device_info['max_output_channels']}")
            print(f"🔍 Default sample rate: {device_info['default_samplerate']}")
        
        # Test setting specific device
        print("\n🎵 Testing with explicit device selection...")
        
        sample_rate = 16000
        duration = 0.5
        frequency = 880  # Higher pitch
        
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        tone = np.sin(2 * np.pi * frequency * t) * 0.5
        tone_int16 = (tone * 32767).astype(np.int16)
        
        # Play with explicit device and channel configuration
        sd.play(
            tone_int16.reshape(-1, 1),  # Ensure mono
            samplerate=sample_rate,
            device=default_output,
            blocking=True
        )
        print("✅ Explicit device test completed")
        
    except Exception as e:
        print(f"❌ Audio device test failed: {e}")


if __name__ == "__main__":
    print("🔊 ESP32 Audio Output Diagnostic Test")
    print("=" * 50)
    
    async def run_tests():
        await test_audio_device_selection()
        print()
        await test_esp32_audio_output()
    
    try:
        asyncio.run(run_tests())
        print("\n🎯 If you heard test tones, the audio system is working!")
        print("   If not, check your speaker volume and default audio device.")
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"\n💥 Test suite failed: {e}")