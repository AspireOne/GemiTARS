"""
Raspberry Pi Audio Manager: Implementation of the AudioInterface for Pi hardware.
"""

import asyncio
import pyaudio
import numpy as np
from typing import Callable, Optional, Any

from .audio_interface import AudioInterface
from ..config.settings import Config
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

class PiAudioManager(AudioInterface):
    """
    Manages audio I/O for a Raspberry Pi using the PyAudio library.
    """

    def __init__(self):
        self.pyaudio_instance: Optional[pyaudio.PyAudio] = None
        self.input_stream: Optional[pyaudio.Stream] = None
        self.output_stream: Optional[pyaudio.Stream] = None
        self.audio_callback: Optional[Callable[[np.ndarray], Any]] = None
        self.playback_queue: asyncio.Queue = asyncio.Queue(maxsize=Config.AUDIO_PLAYBACK_QUEUE_SIZE)
        self.playback_task: Optional[asyncio.Task] = None
        self.input_device_index: Optional[int] = None
        self.output_device_index: Optional[int] = None

    def _get_device_index_by_name(self, device_name: str) -> Optional[int]:
        """Finds a PyAudio device index by its name."""
        if not self.pyaudio_instance:
            return None
        for i in range(self.pyaudio_instance.get_device_count()):
            try:
                device_info = self.pyaudio_instance.get_device_info_by_index(i)
                device_name_str = str(device_info.get('name', ''))
                if device_name.lower() in device_name_str.lower():
                    logger.info(f"Found device '{device_name}' at index {i}.")
                    return i
            except IOError as e:
                logger.warning(f"Could not query device at index {i}: {e}")
        logger.error(f"Audio device '{device_name}' not found.")
        return None

    async def initialize(self) -> bool:
        """Initializes PyAudio and finds the specified input and output devices."""
        try:
            self.pyaudio_instance = pyaudio.PyAudio()
            
            self.input_device_index = self._get_device_index_by_name(Config.ALSA_INPUT_DEVICE)
            self.output_device_index = self._get_device_index_by_name(Config.ALSA_OUTPUT_DEVICE)

            if self.input_device_index is None or self.output_device_index is None:
                logger.error("Failed to find required audio devices. Check ALSA configuration and device names.")
                return False

            logger.info("Pi audio manager initialized successfully.")
            return True
        except Exception as e:
            logger.error(f"Error initializing PyAudio: {e}", exc_info=True)
            return False

    async def start_recording(self, callback: Callable[[np.ndarray], Any]) -> bool:
        """Starts capturing audio from the default microphone."""
        if self.input_stream:
            logger.warning("Microphone stream already running.")
            return True
        
        if not self.pyaudio_instance:
            logger.error("PyAudio not initialized. Cannot start recording.")
            return False

        try:
            self.audio_callback = callback
            
            def stream_callback(in_data, frame_count, time_info, status):
                if self.audio_callback:
                    audio_chunk = np.frombuffer(in_data, dtype=Config.AUDIO_DTYPE)
                    self.audio_callback(audio_chunk)
                return (in_data, pyaudio.paContinue)

            self.input_stream = self.pyaudio_instance.open(
                format=pyaudio.paInt16,
                channels=Config.AUDIO_CHANNELS,
                rate=Config.AUDIO_SAMPLE_RATE,
                input=True,
                frames_per_buffer=Config.AUDIO_BLOCK_SIZE,
                stream_callback=stream_callback,
                input_device_index=self.input_device_index
            )
            self.input_stream.start_stream()
            logger.info("Microphone stream started successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to start microphone stream: {e}", exc_info=True)
            self.input_stream = None
            self.audio_callback = None
            return False

    async def stop_recording(self) -> None:
        """Stops the microphone stream."""
        if self.input_stream:
            self.input_stream.stop_stream()
            self.input_stream.close()
            self.input_stream = None
            logger.info("Microphone stream stopped.")

    async def play_audio_chunk(self, audio_data: bytes) -> None:
        """Plays a chunk of audio data through the default speakers."""
        if not self.playback_task or self.playback_task.done():
            self.playback_task = asyncio.create_task(self._playback_handler())
        
        if self.playback_queue.full():
            logger.warning("Playback queue is full. Waiting for space... (size: %s)", Config.AUDIO_PLAYBACK_QUEUE_SIZE)
            
        await self.playback_queue.put(audio_data)

    async def _playback_handler(self):
        """Handles the playback of audio from the queue."""
        if not self.pyaudio_instance:
            logger.error("PyAudio not initialized. Cannot start playback.")
            return
            
        try:
            self.output_stream = self.pyaudio_instance.open(
                format=pyaudio.paInt16,
                channels=Config.AUDIO_CHANNELS,
                rate=Config.AUDIO_SAMPLE_RATE,
                output=True,
                output_device_index=self.output_device_index
            )
            logger.info("Audio output stream started.")
            
            while True:
                audio_chunk = await self.playback_queue.get()
                self.output_stream.write(audio_chunk)
                self.playback_queue.task_done()

        except asyncio.CancelledError:
            logger.info("Playback handler cancelled.")
        except Exception as e:
            logger.error(f"Error in playback handler: {e}", exc_info=True)
        finally:
            if self.output_stream:
                self.output_stream.stop_stream()
                self.output_stream.close()
                self.output_stream = None
                logger.info("Audio output stream closed.")

    async def wait_for_playback_completion(self) -> None:
        """Waits until all queued audio chunks have been played."""
        await self.playback_queue.join()

    async def check_audio_health(self) -> bool:
        """Check if audio devices are healthy and available."""
        if not self.pyaudio_instance:
            logger.error("PyAudio not initialized. Health check failed.")
            return False
        try:
            device_count = self.pyaudio_instance.get_device_count()
            if device_count == 0:
                logger.error("No audio devices found during health check.")
                return False
            logger.debug(f"Audio health check passed, found {device_count} devices.")
            return True
        except Exception as e:
            logger.error(f"Audio health check failed: {e}", exc_info=True)
            return False

    async def cleanup(self) -> None:
        """Cleans up all audio resources."""
        await self.stop_recording()
        if self.playback_task and not self.playback_task.done():
            self.playback_task.cancel()
            try:
                await self.playback_task
            except asyncio.CancelledError:
                pass
        if self.pyaudio_instance:
            self.pyaudio_instance.terminate()
        logger.info("Pi audio manager cleaned up.")