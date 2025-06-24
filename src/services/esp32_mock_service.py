"""
ESP32 Mock Service: PC-based simulation of ESP32 hardware.

This service simulates ESP32 behavior by:
- Using PC microphone for audio input
- Using PC speakers for audio output  
- Providing the same interface as real ESP32 service
- Simulating network latency and behavior characteristics
"""

import asyncio
import numpy as np
import sounddevice as sd
import threading
import time
from typing import Callable, Optional, Dict, Any
from queue import Queue

from .esp32_interface import ESP32ServiceInterface, AudioStreamConfig, ESP32Status
from config import Config


class ESP32MockService(ESP32ServiceInterface):
    """
    Mock implementation of ESP32 service using PC audio hardware.
    
    This service simulates ESP32 behavior by using PC audio I/O while
    maintaining the same interface that the real ESP32 service will use.
    """
    
    def __init__(self):
        # Core components
        self.audio_config = AudioStreamConfig()
        self.status = ESP32Status()
        
        # Audio streaming
        self.audio_callback: Optional[Callable[[bytes], None]] = None
        self.input_stream: Optional[sd.InputStream] = None
        self.output_stream: Optional[sd.OutputStream] = None
        
        # Audio output queue and management
        self.audio_output_queue = Queue()
        self.audio_output_task: Optional[asyncio.Task] = None
        self.is_playing_audio = False
        
        # Threading and synchronization
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self._lock = threading.Lock()
        
        # Statistics and monitoring
        self.stats = {
            'audio_chunks_received': 0,
            'audio_chunks_played': 0,
            'total_audio_bytes_in': 0,
            'total_audio_bytes_out': 0,
            'connection_time': None
        }
    
    async def initialize(self) -> None:
        """Initialize the mock ESP32 service."""
        print("🔌 ESP32 Mock: Initializing...")
        
        # Store event loop for thread-safe operations
        self.loop = asyncio.get_running_loop()
        
        # Simulate connection time
        await asyncio.sleep(0.1)  # Mock network connection delay
        
        # Initialize audio output processing task
        self.audio_output_task = asyncio.create_task(self._audio_output_worker())
        
        # Update status
        with self._lock:
            self.status.is_connected = True
            self.status.last_activity = time.time()
            self.stats['connection_time'] = time.time()
        
        print("✅ ESP32 Mock: Initialized successfully")
    
    async def shutdown(self) -> None:
        """Clean shutdown of mock service."""
        print("🔄 ESP32 Mock: Shutting down...")
        
        # Stop audio streaming
        await self.stop_audio_streaming()
        await self.stop_audio_playback()
        
        # Cancel output worker task
        if self.audio_output_task and not self.audio_output_task.done():
            self.audio_output_task.cancel()
            try:
                await self.audio_output_task
            except asyncio.CancelledError:
                pass
        
        # Update status
        with self._lock:
            self.status.is_connected = False
            self.status.audio_streaming = False
            self.status.audio_playing = False
        
        print("✅ ESP32 Mock: Shutdown complete")
    
    async def start_audio_streaming(self) -> None:
        """Start audio streaming from PC microphone."""
        if self.status.audio_streaming:
            print("⚠️ ESP32 Mock: Audio streaming already active")
            return
        
        def audio_callback(indata, frames, time_info, status):
            if status:
                print(f"⚠️ ESP32 Mock: Audio input status: {status}")
                
            # Convert audio data to bytes
            audio_bytes = indata.tobytes()
            
            # Update statistics
            import time
            with self._lock:
                self.stats['audio_chunks_received'] += 1
                self.stats['total_audio_bytes_in'] += len(audio_bytes)
                self.status.last_activity = time.time()
            
            # Call the registered callback (thread-safe)
            if self.audio_callback:
                if self.loop:
                    try:
                        self.loop.call_soon_threadsafe(
                            self.audio_callback, audio_bytes
                        )
                    except Exception as e:
                        print(f"⚠️ Error in audio callback: {e}")
                else:
                    print("⚠️ No event loop available for audio callback")
        
        try:
            # Create and start input stream
            self.input_stream = sd.InputStream(
                samplerate=self.audio_config.sample_rate,
                blocksize=self.audio_config.block_size,
                dtype=self.audio_config.dtype,
                channels=self.audio_config.channels,
                callback=audio_callback,
            )
            
            self.input_stream.start()
            
            # Update status
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
        """Stop audio streaming."""
        if not self.status.audio_streaming:
            return
        
        try:
            if self.input_stream:
                self.input_stream.stop()
                self.input_stream.close()
                self.input_stream = None
            
            # Update status
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
        """Set callback for incoming audio data."""
        with self._lock:
            self.audio_callback = callback
        print("🔗 ESP32 Mock: Audio callback registered")
    
    async def play_audio_chunk(self, audio_data: bytes) -> None:
        """Queue audio chunk for playback."""
        if not self.status.is_connected:
            print("⚠️ ESP32 Mock: Cannot play audio - not connected")
            return
        
        # Add to output queue
        self.audio_output_queue.put(audio_data)
        
        # Update statistics
        with self._lock:
            self.stats['audio_chunks_played'] += 1
            self.stats['total_audio_bytes_out'] += len(audio_data)
            self.status.last_activity = time.time()
    
    async def stop_audio_playback(self) -> None:
        """Stop audio playback and clear queue."""
        # Clear the queue
        while not self.audio_output_queue.empty():
            try:
                self.audio_output_queue.get_nowait()
            except:
                break
        
        # Stop output stream if running
        if self.output_stream and self.output_stream.active:
            self.output_stream.stop()
        
        with self._lock:
            self.status.audio_playing = False
        
        print("🔇 ESP32 Mock: Audio playback stopped")
    
    async def _audio_output_worker(self) -> None:
        """Background worker for audio output processing."""
        print("🔊 ESP32 Mock: Audio output worker started")
        
        try:
            while True:
                # Wait for audio data
                if self.audio_output_queue.empty():
                    await asyncio.sleep(0.01)  # Small delay to prevent busy waiting
                    continue
                
                # Get audio chunk
                audio_data = self.audio_output_queue.get()
                
                # Convert bytes to numpy array for playback
                try:
                    audio_array = np.frombuffer(audio_data, dtype=self.audio_config.dtype)
                    
                    # Ensure we have the right shape (samples, channels)
                    if self.audio_config.channels == 1:
                        audio_array = audio_array.reshape(-1, 1)
                    
                    # Play audio using sounddevice
                    with self._lock:
                        self.status.audio_playing = True
                    
                    # This will block until audio finishes playing
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
        """Simulate image capture (placeholder for future implementation)."""
        # For now, return None to indicate no camera available
        # Future implementation could use PC webcam
        print("📷 ESP32 Mock: Image capture not implemented yet")
        return None
    
    def get_status(self) -> Dict[str, Any]:
        """Get current mock service status."""
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
        """Check if mock service is operational."""
        return self.status.is_connected