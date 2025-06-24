"""
Standalone test for ESP32 Mock Service - avoiding dependency conflicts.
"""

import asyncio
import sys
import os
import time
from typing import Callable, Optional, Dict, Any
from abc import ABC, abstractmethod
from queue import Queue
import threading
import numpy as np
import sounddevice as sd

# Standalone config for testing
class TestConfig:
    AUDIO_SAMPLE_RATE = 16000
    AUDIO_BLOCK_SIZE = 1600
    AUDIO_DTYPE = 'int16'
    AUDIO_CHANNELS = 1
    AUDIO_MIME_TYPE = "audio/pcm;rate=16000"

# Copy the interface and implementation directly for testing
class AudioStreamConfig:
    def __init__(self):
        self.sample_rate: int = 16000
        self.channels: int = 1
        self.dtype: str = 'int16'
        self.block_size: int = 1600
        self.mime_type: str = "audio/pcm;rate=16000"

class ESP32Status:
    def __init__(self):
        self.is_connected: bool = False
        self.audio_streaming: bool = False
        self.audio_playing: bool = False
        self.last_activity: Optional[float] = None
        self.error_count: int = 0
        self.last_error: Optional[str] = None

class ESP32ServiceInterface(ABC):
    @abstractmethod
    async def initialize(self) -> None: pass
    @abstractmethod
    async def shutdown(self) -> None: pass
    @abstractmethod
    async def start_audio_streaming(self) -> None: pass
    @abstractmethod
    async def stop_audio_streaming(self) -> None: pass
    @abstractmethod
    def set_audio_callback(self, callback: Callable[[bytes], None]) -> None: pass
    @abstractmethod
    async def play_audio_chunk(self, audio_data: bytes) -> None: pass
    @abstractmethod
    async def stop_audio_playback(self) -> None: pass
    @abstractmethod
    async def capture_image(self) -> Optional[bytes]: pass
    @abstractmethod
    def get_status(self) -> Dict[str, Any]: pass
    @abstractmethod
    def is_connected(self) -> bool: pass

class ESP32MockService(ESP32ServiceInterface):
    def __init__(self):
        self.audio_config = AudioStreamConfig()
        self.status = ESP32Status()
        self.audio_callback: Optional[Callable[[bytes], None]] = None
        self.input_stream: Optional[sd.InputStream] = None
        self.output_stream: Optional[sd.OutputStream] = None
        self.audio_output_queue = Queue()
        self.audio_output_task: Optional[asyncio.Task] = None
        self.is_playing_audio = False
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self._lock = threading.Lock()
        self.stats = {
            'audio_chunks_received': 0,
            'audio_chunks_played': 0,
            'total_audio_bytes_in': 0,
            'total_audio_bytes_out': 0,
            'connection_time': None
        }
    
    async def initialize(self) -> None:
        print("🔌 ESP32 Mock: Initializing...")
        self.loop = asyncio.get_running_loop()
        await asyncio.sleep(0.1)
        self.audio_output_task = asyncio.create_task(self._audio_output_worker())
        with self._lock:
            self.status.is_connected = True
            self.status.last_activity = time.time()
            self.stats['connection_time'] = time.time()
        print("✅ ESP32 Mock: Initialized successfully")
    
    async def shutdown(self) -> None:
        print("🔄 ESP32 Mock: Shutting down...")
        await self.stop_audio_streaming()
        await self.stop_audio_playback()
        if self.audio_output_task and not self.audio_output_task.done():
            self.audio_output_task.cancel()
            try:
                await self.audio_output_task
            except asyncio.CancelledError:
                pass
        with self._lock:
            self.status.is_connected = False
            self.status.audio_streaming = False
            self.status.audio_playing = False
        print("✅ ESP32 Mock: Shutdown complete")
    
    async def start_audio_streaming(self) -> None:
        if self.status.audio_streaming:
            print("⚠️ ESP32 Mock: Audio streaming already active")
            return
        
        def audio_callback(indata, frames, time, status):
            if status:
                print(f"⚠️ ESP32 Mock: Audio input status: {status}")
            audio_bytes = indata.tobytes()
            with self._lock:
                self.stats['audio_chunks_received'] += 1
                self.stats['total_audio_bytes_in'] += len(audio_bytes)
                self.status.last_activity = time.time()
            if self.audio_callback and self.loop:
                self.loop.call_soon_threadsafe(
                    self.audio_callback, audio_bytes
                )
        
        try:
            self.input_stream = sd.InputStream(
                samplerate=self.audio_config.sample_rate,
                blocksize=self.audio_config.block_size,
                dtype=self.audio_config.dtype,
                channels=self.audio_config.channels,
                callback=audio_callback,
            )
            self.input_stream.start()
            with self._lock:
                self.status.audio_streaming = True
                self.status.last_activity = time.time()
            print("🎤 ESP32 Mock: Audio streaming started")
        except Exception as e:
            error_msg = f"Failed to start audio streaming: {e}"
            print(f"❌ ESP32 Mock: {error_msg}")
            with self._lock:
                self.status.error_count += 1
                self.status.last_error = error_msg
            raise
    
    async def stop_audio_streaming(self) -> None:
        if not self.status.audio_streaming:
            return
        try:
            if self.input_stream:
                self.input_stream.stop()
                self.input_stream.close()
                self.input_stream = None
            with self._lock:
                self.status.audio_streaming = False
                self.status.last_activity = time.time()
            print("🔇 ESP32 Mock: Audio streaming stopped")
        except Exception as e:
            error_msg = f"Error stopping audio streaming: {e}"
            print(f"⚠️ ESP32 Mock: {error_msg}")
            with self._lock:
                self.status.error_count += 1
                self.status.last_error = error_msg
    
    def set_audio_callback(self, callback: Callable[[bytes], None]) -> None:
        with self._lock:
            self.audio_callback = callback
        print("🔗 ESP32 Mock: Audio callback registered")
    
    async def play_audio_chunk(self, audio_data: bytes) -> None:
        if not self.status.is_connected:
            print("⚠️ ESP32 Mock: Cannot play audio - not connected")
            return
        self.audio_output_queue.put(audio_data)
        with self._lock:
            self.stats['audio_chunks_played'] += 1
            self.stats['total_audio_bytes_out'] += len(audio_data)
            self.status.last_activity = time.time()
    
    async def stop_audio_playback(self) -> None:
        while not self.audio_output_queue.empty():
            try:
                self.audio_output_queue.get_nowait()
            except:
                break
        if self.output_stream and self.output_stream.active:
            self.output_stream.stop()
        with self._lock:
            self.status.audio_playing = False
        print("🔇 ESP32 Mock: Audio playback stopped")
    
    async def _audio_output_worker(self) -> None:
        print("🔊 ESP32 Mock: Audio output worker started")
        try:
            while True:
                if self.audio_output_queue.empty():
                    await asyncio.sleep(0.01)
                    continue
                audio_data = self.audio_output_queue.get()
                try:
                    audio_array = np.frombuffer(audio_data, dtype=self.audio_config.dtype)
                    if self.audio_config.channels == 1:
                        audio_array = audio_array.reshape(-1, 1)
                    with self._lock:
                        self.status.audio_playing = True
                    sd.play(
                        audio_array,
                        samplerate=self.audio_config.sample_rate,
                        blocking=True
                    )
                except Exception as e:
                    error_msg = f"Error playing audio: {e}"
                    print(f"⚠️ ESP32 Mock: {error_msg}")
                    with self._lock:
                        self.status.error_count += 1
                        self.status.last_error = error_msg
                finally:
                    with self._lock:
                        self.status.audio_playing = False
        except asyncio.CancelledError:
            print("🔇 ESP32 Mock: Audio output worker cancelled")
        except Exception as e:
            print(f"❌ ESP32 Mock: Audio output worker error: {e}")
    
    async def capture_image(self) -> Optional[bytes]:
        print("📷 ESP32 Mock: Image capture not implemented yet")
        return None
    
    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                'service_type': 'ESP32Mock',
                'is_connected': self.status.is_connected,
                'audio_streaming': self.status.audio_streaming,
                'audio_playing': self.status.audio_playing,
                'last_activity': self.status.last_activity,
                'error_count': self.status.error_count,
                'last_error': self.status.last_error,
                'statistics': self.stats.copy(),
                'audio_config': {
                    'sample_rate': self.audio_config.sample_rate,
                    'channels': self.audio_config.channels,
                    'dtype': self.audio_config.dtype,
                    'block_size': self.audio_config.block_size
                }
            }
    
    def is_connected(self) -> bool:
        return self.status.is_connected


async def test_esp32_mock_service():
    """Test basic ESP32 mock service functionality."""
    print("🧪 Testing ESP32 Mock Service...")
    
    esp32_service = ESP32MockService()
    
    try:
        print("📡 Testing service initialization...")
        await esp32_service.initialize()
        assert esp32_service.is_connected(), "Service should be connected after initialization"
        print("✅ Service initialization successful")
        
        print("📊 Testing status reporting...")
        status = esp32_service.get_status()
        assert status['service_type'] == 'ESP32Mock'
        assert status['is_connected'] == True
        assert status['audio_streaming'] == False
        print("✅ Status reporting working correctly")
        
        print("🔗 Testing audio callback registration...")
        audio_received = []
        
        def test_callback(audio_data: bytes):
            audio_received.append(len(audio_data))
            if len(audio_received) <= 3:  # Only print first few
                print(f"📨 Received audio chunk: {len(audio_data)} bytes")
        
        esp32_service.set_audio_callback(test_callback)
        print("✅ Audio callback registered")
        
        print("🎤 Testing audio streaming...")
        await esp32_service.start_audio_streaming()
        
        status = esp32_service.get_status()
        assert status['audio_streaming'] == True
        print("✅ Audio streaming started")
        
        print("⏱️ Waiting for audio data (2 seconds)...")
        await asyncio.sleep(2.0)
        
        assert len(audio_received) > 0, f"Should have received audio data, got {len(audio_received)} chunks"
        print(f"✅ Received {len(audio_received)} audio chunks")
        
        print("🔊 Testing audio output...")
        test_audio = b'\x00' * 1600  # Silent audio chunk
        await esp32_service.play_audio_chunk(test_audio)
        await asyncio.sleep(0.5)
        print("✅ Audio output test completed")
        
        print("🔇 Testing stop audio streaming...")
        await esp32_service.stop_audio_streaming()
        
        status = esp32_service.get_status()
        assert status['audio_streaming'] == False
        print("✅ Audio streaming stopped")
        
        print("📷 Testing image capture...")
        image_data = await esp32_service.capture_image()
        assert image_data is None, "Image capture should return None (not implemented)"
        print("✅ Image capture behaving as expected (not implemented)")
        
        print("\n🎉 All ESP32 Mock Service tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise
    finally:
        print("🔄 Cleaning up...")
        await esp32_service.shutdown()
        print("✅ Cleanup complete")


async def main():
    """Run all tests."""
    print("🚀 Starting ESP32 Mock Service Tests\n")
    
    try:
        await test_esp32_mock_service()
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