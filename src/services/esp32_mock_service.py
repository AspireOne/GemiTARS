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
import queue
import os
from typing import Callable, Optional, Dict, Any
from dataclasses import dataclass, field, asdict

from .esp32_interface import ESP32ServiceInterface, AudioStreamConfig, ESP32Status
from config.settings import Config
from utils.logger import setup_logger

logger = setup_logger(os.path.splitext(os.path.basename(__file__))[0])


@dataclass
class ESP32MockStats:
    """Statistics for monitoring the ESP32 mock service."""
    audio_chunks_received: int = 0
    audio_chunks_played: int = 0
    total_audio_bytes_in: int = 0
    total_audio_bytes_out: int = 0
    connection_time: Optional[float] = None


class ESP32MockService(ESP32ServiceInterface):
    """
    Streaming implementation of ESP32 service using proven audio streaming approach.
    
    Uses sounddevice's OutputStream with callback for smooth audio playback,
    based on the working ElevenLabs streaming demo pattern.
    """
    
    def __init__(self):
        # Core components
        self.audio_config = AudioStreamConfig()
        self.status = ESP32Status()
        
        # Audio streaming
        self.audio_callback: Optional[Callable[[bytes], None]] = None
        self.input_stream: Optional[sd.InputStream] = None
        
        # Audio output - streaming approach
        self.audio_output_queue = queue.Queue()
        self.output_stream: Optional[sd.OutputStream] = None
        self.stream_finished = threading.Event()
        self.playback_finished = threading.Event()
        self.output_buffer = b''
        
        # Threading and synchronization
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self._lock = threading.Lock()
        
        # Statistics and monitoring
        self.stats = ESP32MockStats()
    
    async def initialize(self) -> None:
        """Initialize the streaming ESP32 service."""
        logger.info("Initializing...")
        
        # Store event loop for thread-safe operations
        self.loop = asyncio.get_running_loop()
        
        # Simulate connection time
        await asyncio.sleep(0.1)  # Mock network connection delay
        
        # Update status
        with self._lock:
            self.status.is_connected = True
            self.status.last_activity = time.time()
            self.stats.connection_time = time.time()
        
        logger.info("Initialized successfully")
    
    async def shutdown(self) -> None:
        """Clean shutdown of streaming service."""
        logger.info("Shutting down...")
        
        # Stop audio streaming
        await self.stop_audio_streaming()
        await self.stop_audio_playback()
        
        # Update status
        with self._lock:
            self.status.is_connected = False
            self.status.audio_streaming = False
            self.status.audio_playing = False
        
        logger.info("Shutdown complete")
    
    async def start_audio_streaming(self) -> None:
        """Start audio streaming from PC microphone."""
        if self.status.audio_streaming:
            logger.warning("Audio streaming already active")
            return
        
        def audio_callback(indata, frames, time_info, status):
            if status:
                logger.warning(f"Audio input status: {status}")
                
            # Convert audio data to bytes
            audio_bytes = indata.tobytes()
            
            # Update statistics
            with self._lock:
                self.stats.audio_chunks_received += 1
                self.stats.total_audio_bytes_in += len(audio_bytes)
                self.status.last_activity = time.time()
            
            # Call the registered callback (thread-safe)
            if self.audio_callback:
                if self.loop:
                    try:
                        self.loop.call_soon_threadsafe(
                            self.audio_callback, audio_bytes
                        )
                    except Exception as e:
                        logger.warning(f"Error in audio callback: {e}")
                else:
                    logger.warning("No event loop available for audio callback")
        
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
            
            logger.info("Audio streaming started")
            
        except Exception as e:
            error_msg = f"Failed to start audio streaming: {e}"
            logger.error(error_msg)
            
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
            
            logger.info("Audio streaming stopped")
            
        except Exception as e:
            error_msg = f"Error stopping audio streaming: {e}"
            logger.warning(error_msg)
            
            with self._lock:
                self.status.error_count += 1
                self.status.last_error = error_msg
    
    def set_audio_callback(self, callback: Callable[[bytes], None]) -> None:
        """Set callback for incoming audio data."""
        with self._lock:
            self.audio_callback = callback
        logger.info("Audio callback registered")
    
    async def play_audio_chunk(self, audio_data: bytes) -> None:
        """Queue audio chunk for streaming playback."""
        if not self.status.is_connected:
            logger.warning("Cannot play audio - not connected")
            return
        
        # Add to output queue
        self.audio_output_queue.put(audio_data)
        
        # Start streaming if not already started
        if not self.status.audio_playing:
            await self._start_audio_streaming()
        
        # Update statistics
        with self._lock:
            self.stats.audio_chunks_played += 1
            self.stats.total_audio_bytes_out += len(audio_data)
            self.status.last_activity = time.time()

    async def wait_for_playback_completion(self):
        """
        Waits until the audio output queue is empty and then adds a small
        delay for the sounddevice buffer to clear.
        """
        while not self.audio_output_queue.empty():
            await asyncio.sleep(0.05)
        # Wait a bit for the last chunks in the sounddevice buffer to play
        await asyncio.sleep(0.2)
    
    async def _start_audio_streaming(self) -> None:
        """Start the audio output stream using the proven streaming approach."""
        if self.output_stream and self.output_stream.active:
            return  # Already streaming
        
        logger.info("Starting audio output stream...")
        
        try:
            with self._lock:
                self.status.audio_playing = True
            
            # Create output stream with callback (similar to working demo)
            self.output_stream = sd.OutputStream(
                samplerate=self.audio_config.sample_rate,
                channels=self.audio_config.channels,
                dtype=self.audio_config.dtype,
                callback=self._audio_output_callback,
                finished_callback=self._stream_finished_callback
            )
            
            self.output_stream.start()
            logger.info("Audio output stream started")
            
        except Exception as e:
            error_msg = f"Failed to start audio output stream: {e}"
            logger.error(error_msg)
            
            with self._lock:
                self.status.error_count += 1
                self.status.last_error = error_msg
                self.status.audio_playing = False
    
    def _audio_output_callback(self, outdata, frames, time, status):
        if status:
            logger.warning(f"Audio output status: {status}")

        try:
            # Prepend leftover data from the last call
            data_to_play = self.output_buffer
            self.output_buffer = b''

            # Get new data from the queue until we have enough for the frame
            while len(data_to_play) < frames * outdata.itemsize:
                try:
                    data_to_play += self.audio_output_queue.get_nowait()
                except queue.Empty:
                    break # No more data in the queue

            # Convert to numpy array
            audio_array = np.frombuffer(data_to_play, dtype=self.audio_config.dtype)
            chunk_size = len(audio_array)

            if chunk_size >= frames:
                outdata[:] = audio_array[:frames].reshape(-1, self.audio_config.channels)
                # Store the remainder for the next callback
                self.output_buffer = audio_array[frames:].tobytes()
            else:
                # Pad with silence if not enough data
                outdata[:chunk_size] = audio_array.reshape(-1, self.audio_config.channels)
                outdata[chunk_size:] = 0

        except Exception as e:
            logger.error(f"Error in audio callback: {e}", exc_info=True)
            outdata.fill(0)
            self.output_buffer = b'' # Clear buffer on error
    
    def _stream_finished_callback(self):
        """Called when the output stream finishes."""
        logger.info("Audio output stream finished")
        with self._lock:
            self.status.audio_playing = False
        self.playback_finished.set()
    
    async def stop_audio_playback(self) -> None:
        """Stop audio playback and clear queue."""
        # Clear the queue
        while not self.audio_output_queue.empty():
            try:
                self.audio_output_queue.get_nowait()
            except queue.Empty:
                break
        
        # Stop output stream if running
        if self.output_stream and self.output_stream.active:
            self.output_stream.stop()
            self.output_stream.close()
            self.output_stream = None
        
        with self._lock:
            self.status.audio_playing = False
        
        logger.info("Audio playback stopped")
    
    async def capture_image(self) -> Optional[bytes]:
        """Simulate image capture (placeholder for future implementation)."""
        # For now, return None to indicate no camera available
        logger.info("Image capture not implemented yet")
        return None
    
    def get_status(self) -> Dict[str, Any]:
        """Get current streaming service status."""
        with self._lock:
            return {
                'service_type': 'ESP32Streaming',
                'is_connected': self.status.is_connected,
                'audio_streaming': self.status.audio_streaming,
                'audio_playing': self.status.audio_playing,
                'last_activity': self.status.last_activity,
                'error_count': self.status.error_count,
                'last_error': self.status.last_error,
                'statistics': asdict(self.stats),
                'audio_config': {
                    'sample_rate': self.audio_config.sample_rate,
                    'channels': self.audio_config.channels,
                    'dtype': self.audio_config.dtype,
                    'block_size': self.audio_config.block_size
                }
            }
    
    def is_connected(self) -> bool:
        """Check if streaming service is operational."""
        return self.status.is_connected