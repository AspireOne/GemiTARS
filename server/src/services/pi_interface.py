"""
Pi Interface Service: Abstract interface for Raspberry Pi communication.

This module defines the contract that all Pi communication service implementations
must follow. It handles the bidirectional flow of audio and control messages.
"""

from abc import ABC, abstractmethod
from typing import Callable, Awaitable

# Define callback types for clarity
HotwordCallback = Callable[[], Awaitable[None]]
AudioCallback = Callable[[bytes], None]

class PiInterfaceService(ABC):
    """
    Abstract interface for services that manage communication with the 
    Raspberry Pi client.
    """

    @abstractmethod
    async def initialize(
        self, 
        hotword_callback: HotwordCallback,
        audio_callback: AudioCallback
    ) -> None:
        """
        Initialize the service, starting any necessary servers (e.g., WebSockets)
        and setting up callbacks to the main assistant.

        Args:
            hotword_callback: An awaitable function to call when the hotword is detected.
            audio_callback: A function to call to process incoming audio chunks.
        """
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Cleanly shut down the service and close connections."""
        pass

    @abstractmethod
    async def play_audio_chunk(self, audio_data: bytes) -> None:
        """
        Send a chunk of audio data to the Pi to be played.

        Args:
            audio_data: Audio bytes to play (e.g., 16kHz, 16-bit PCM).
        """
        pass

    @abstractmethod
    async def wait_for_playback_completion(self) -> None:
        """
        Wait until all queued audio chunks have been sent to the client and 
        are likely played.
        """
        pass

    @abstractmethod
    def is_client_connected(self) -> bool:
        """Check if a client is currently connected."""
        pass