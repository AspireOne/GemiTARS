"""
Abstract Base Class for Audio I/O
"""

from abc import ABC, abstractmethod
from typing import Callable, Any

class AudioInterface(ABC):
    """
    Abstract interface for audio I/O operations.
    
    This class defines the contract that all audio manager implementations 
    (e.g., for PC or Raspberry Pi) must follow.
    """
    
    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initializes the audio hardware and devices.
        
        Returns:
            True if initialization was successful, False otherwise.
        """
        pass
    
    @abstractmethod
    async def start_recording(self, callback: Callable[[bytes], Any]) -> None:
        """
        Starts recording audio from the microphone.
        
        Args:
            callback: A function to be called with each new chunk of audio data.
        """
        pass
    
    @abstractmethod
    async def stop_recording(self) -> None:
        """Stops recording audio."""
        pass
    
    @abstractmethod
    async def play_audio_chunk(self, audio_data: bytes) -> None:
        """
        Plays a chunk of audio data through the speakers.
        
        Args:
            audio_data: A chunk of audio data in the expected format (e.g., 16-bit PCM).
        """
        pass

    @abstractmethod
    async def wait_for_playback_completion(self) -> None:
        """Waits until all queued audio chunks have been played."""
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """Cleans up all audio resources and closes streams."""
        pass