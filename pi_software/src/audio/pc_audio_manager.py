"""
PC Audio Manager: Implementation of the AudioInterface for standard PCs.
"""

import asyncio
import sounddevice as sd
import numpy as np
from typing import Callable, Optional, Any

from .audio_interface import AudioInterface
from ..config.settings import Config
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

class PcAudioManager(AudioInterface):
    """
    Manages audio I/O for a standard PC using the sounddevice library.
    """

    def __init__(self):
        self.input_stream: Optional[sd.InputStream] = None
        self.output_stream: Optional[sd.OutputStream] = None
        self.audio_callback: Optional[Callable[[np.ndarray], Any]] = None
        self.playback_queue: asyncio.Queue = asyncio.Queue()
        self.playback_task: Optional[asyncio.Task] = None

    async def initialize(self) -> bool:
        """Initializes and checks for available audio devices."""
        try:
            devices = sd.query_devices()
            logger.debug(f"Available audio devices: {devices}")
            # Basic check to see if there are any input/output devices
            devices_list = sd.query_devices()
            if isinstance(devices_list, dict): # It can be a single dict if only one device
                devices_list = [devices_list]
            has_input = any(dict(d).get('max_input_channels', 0) > 0 for d in devices_list)
            has_output = any(dict(d).get('max_output_channels', 0) > 0 for d in devices_list)
            if not has_input or not has_output:
                logger.error("No suitable input or output audio device found.")
                return False
            logger.info("PC audio manager initialized successfully.")
            return True
        except Exception as e:
            logger.error(f"Error initializing audio devices: {e}", exc_info=True)
            return False

    async def start_recording(self, callback: Callable[[np.ndarray], Any]) -> bool:
        """Starts capturing audio from the default microphone."""
        if self.input_stream:
            logger.warning("Microphone stream already running.")
            return True  # Already recording is considered success
        
        try:
            self.audio_callback = callback
            
            self.input_stream = sd.InputStream(
                samplerate=Config.AUDIO_SAMPLE_RATE,
                blocksize=Config.AUDIO_BLOCK_SIZE,
                dtype=Config.AUDIO_DTYPE,
                channels=Config.AUDIO_CHANNELS,
                callback=self._mic_callback
            )
            
            self.input_stream.start()
            logger.info("Microphone stream started successfully.")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start microphone stream: {e}", exc_info=True)
            # Ensure clean state
            self.input_stream = None
            self.audio_callback = None
            return False

    def _mic_callback(self, indata: np.ndarray, frames: int, time, status: sd.CallbackFlags):
        """Internal callback for sounddevice to process microphone data."""
        if status:
            logger.warning(f"Microphone stream status: {status}")
        if self.audio_callback:
            # Flatten the audio array to ensure it's a 1D array, as expected by openwakeword
            self.audio_callback(indata.flatten())

    async def stop_recording(self) -> None:
        """Stops the microphone stream."""
        if self.input_stream:
            self.input_stream.stop()
            self.input_stream.close()
            self.input_stream = None
            logger.info("Microphone stream stopped.")

    async def play_audio_chunk(self, audio_data: bytes) -> None:
        """Plays a chunk of audio data through the default speakers."""
        if not self.playback_task or self.playback_task.done():
            self.playback_task = asyncio.create_task(self._playback_handler())
        
        await self.playback_queue.put(audio_data)

    async def _playback_handler(self):
        """Handles the playback of audio from the queue."""
        try:
            self.output_stream = sd.OutputStream(
                samplerate=Config.AUDIO_SAMPLE_RATE,
                dtype=Config.AUDIO_DTYPE,
                channels=Config.AUDIO_CHANNELS
            )
            self.output_stream.start()
            logger.info("Audio output stream started.")
            
            while True:
                audio_chunk = await self.playback_queue.get()
                self.output_stream.write(np.frombuffer(audio_chunk, dtype=Config.AUDIO_DTYPE))
                self.playback_queue.task_done()

        except asyncio.CancelledError:
            logger.info("Playback handler cancelled.")
        except Exception as e:
            logger.error(f"Error in playback handler: {e}", exc_info=True)
        finally:
            if self.output_stream:
                self.output_stream.stop()
                self.output_stream.close()
                self.output_stream = None
                logger.info("Audio output stream closed.")

    async def wait_for_playback_completion(self) -> None:
        """Waits until all queued audio chunks have been played."""
        await self.playback_queue.join()

    async def check_audio_health(self) -> bool:
        """Check if audio devices are healthy and available."""
        try:
            # Query devices to ensure they're still available
            devices = sd.query_devices()
            logger.debug(f"Audio devices check: {len(devices) if hasattr(devices, '__len__') else 'single device'}")
            
            # Check if default devices are available
            try:
                default_input = sd.default.device[0]
                default_output = sd.default.device[1]
                
                if default_input is None or default_output is None:
                    logger.error("Default audio devices not available")
                    return False
            except Exception as e:
                logger.error(f"Error checking default devices: {e}")
                return False
            
            # Basic check to see if there are any input/output devices
            devices_list = sd.query_devices()
            if isinstance(devices_list, dict):  # Single device case
                devices_list = [devices_list]
            
            has_input = any(dict(d).get('max_input_channels', 0) > 0 for d in devices_list)
            has_output = any(dict(d).get('max_output_channels', 0) > 0 for d in devices_list)
            
            if not has_input or not has_output:
                logger.error("No suitable input or output audio devices found")
                return False
            
            logger.debug("Audio health check passed")
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
        logger.info("PC audio manager cleaned up.")