"""
ESP32 Service Interface: Abstract interface for ESP32 services.

This module defines the contract that all ESP32 service implementations
must follow, ensuring seamless switching between mock and real hardware.
"""

from abc import ABC, abstractmethod
from typing import Callable, Optional, Dict, Any
import asyncio


class AudioStreamConfig:
    """Configuration for audio streaming."""
    
    def __init__(self):
        self.sample_rate: int = 16000
        self.channels: int = 1
        self.dtype: str = 'int16'
        self.block_size: int = 1600
        self.mime_type: str = "audio/pcm;rate=16000"


class ESP32Status:
    """Standard status structure for ESP32 services."""
    
    def __init__(self):
        self.is_connected: bool = False
        self.audio_streaming: bool = False
        self.audio_playing: bool = False
        self.last_activity: Optional[float] = None
        self.error_count: int = 0
        self.last_error: Optional[str] = None


class ESP32ServiceInterface(ABC):
    """
    Abstract interface for ESP32 services (both mock and real implementations).
    
    This interface defines the contract that all ESP32 service implementations
    must follow, ensuring seamless switching between mock and real hardware.
    """
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the ESP32 service and establish connections."""
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """Clean shutdown of the ESP32 service."""
        pass
    
    # Audio Input Methods
    @abstractmethod
    async def start_audio_streaming(self) -> None:
        """Start continuous audio streaming from microphone."""
        pass
    
    @abstractmethod
    async def stop_audio_streaming(self) -> None:
        """Stop audio streaming."""
        pass
    
    @abstractmethod
    def set_audio_callback(self, callback: Callable[[bytes], None]) -> None:
        """
        Set callback function for incoming audio data.
        
        Args:
            callback: Function that receives audio bytes (16kHz, 16-bit PCM)
        """
        pass
    
    # Audio Output Methods
    @abstractmethod
    async def play_audio_chunk(self, audio_data: bytes) -> None:
        """
        Play audio chunk through speaker.
        
        Args:
            audio_data: Audio bytes to play (format matches input format)
        """
        pass
    
    @abstractmethod
    async def stop_audio_playback(self) -> None:
        """Stop current audio playback and clear audio queue."""
        pass
    
    # Camera Methods (Future Implementation)
    @abstractmethod
    async def capture_image(self) -> Optional[bytes]:
        """
        Capture image from camera.
        
        Returns:
            Image bytes in JPEG format, or None if unavailable
        """
        pass
    
    # Status and Control
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """
        Get current device status.
        
        Returns:
            Dictionary containing device status information
        """
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if the ESP32 service is connected and operational."""
        pass