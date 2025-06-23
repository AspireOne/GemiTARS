"""
Configuration settings for GemiTARS.

This module defines all configuration classes using dataclasses for type safety
and clear documentation. All settings have sensible defaults and can be overridden
via environment variables or programmatically.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any
import os


@dataclass
class AudioConfig:
    """
    Audio processing configuration.
    
    These settings control how audio is captured and processed for the Gemini Live API.
    The defaults are optimized for the API requirements (16kHz, 16-bit PCM, mono).
    """
    sample_rate: int = 16000          # Hz - Required by Gemini Live API
    block_size: int = 1600            # Samples (100ms at 16kHz for low latency)
    dtype: str = 'int16'              # 16-bit PCM format required by API
    channels: int = 1                 # Mono audio required by API
    mime_type: str = "audio/pcm;rate=16000"  # MIME type for API requests
    
    def __post_init__(self):
        """Validate audio configuration values."""
        if self.sample_rate <= 0:
            raise ValueError("Sample rate must be positive")
        if self.block_size <= 0:
            raise ValueError("Block size must be positive")
        if self.channels < 1:
            raise ValueError("Channels must be at least 1")


@dataclass
class VADConfig:
    """
    Voice Activity Detection configuration.
    
    These settings control the automatic speech detection behavior
    used by the Gemini Live API for natural conversation flow.
    """
    enabled: bool = True              # Enable VAD functionality
    prefix_padding_ms: int = 50       # Lead-in padding before speech
    silence_duration_ms: int = 1500   # Silence threshold (1.5s for natural pauses)
    
    def __post_init__(self):
        """Validate VAD configuration values."""
        if self.prefix_padding_ms < 0:
            raise ValueError("Prefix padding must be non-negative")
        if self.silence_duration_ms < 0:
            raise ValueError("Silence duration must be non-negative")


@dataclass
class ModelConfig:
    """
    Gemini model configuration.
    
    These settings control which Gemini model to use and how it should respond.
    """
    name: str = "gemini-live-2.5-flash-preview"  # Default Live API model
    response_modalities: List[str] = field(default_factory=lambda: ["TEXT"])
    input_audio_transcription: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate model configuration."""
        if not self.name:
            raise ValueError("Model name cannot be empty")
        if not self.response_modalities:
            raise ValueError("At least one response modality must be specified")


@dataclass
class ConversationConfig:
    """
    Conversation management configuration.
    
    These settings control conversation state transitions, timeouts,
    and user-facing messages.
    """
    timeout_seconds: int = 30         # Return to passive after inactivity
    messages: Dict[str, str] = field(default_factory=lambda: {
        "listening": "TARS: I'm listening...",
        "interrupted": "TARS: [Interrupted] Go ahead...",
        "standby": "TARS: Returning to standby mode.",
        "goodbye": "TARS: Goodbye!",
        "system_initialized": "TARS: System initialized. Waiting for hotword...",
        "already_listening": "TARS: Already listening..."
    })
    
    def __post_init__(self):
        """Validate conversation configuration."""
        if self.timeout_seconds <= 0:
            raise ValueError("Timeout must be positive")
        required_messages = ["listening", "interrupted", "standby", "goodbye"]
        for msg_key in required_messages:
            if msg_key not in self.messages:
                raise ValueError(f"Required message '{msg_key}' not found in configuration")


@dataclass
class TARSConfig:
    """
    Main TARS configuration combining all settings.
    
    This is the primary configuration class that combines all subsystem
    configurations. It provides a single point of configuration for the
    entire TARS system.
    """
    audio: AudioConfig = field(default_factory=AudioConfig)
    vad: VADConfig = field(default_factory=VADConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    conversation: ConversationConfig = field(default_factory=ConversationConfig)
    api_key_env_var: str = "GEMINI_API_KEY"
    
    def get_gemini_config(self) -> Dict[str, Any]:
        """
        Generate Gemini Live API configuration dictionary.
        
        Returns:
            Dictionary formatted for Gemini Live API session creation
        """
        config = {
            "response_modalities": self.model.response_modalities,
            "input_audio_transcription": self.model.input_audio_transcription,
        }
        
        if self.vad.enabled:
            config["realtime_input_config"] = {
                "automatic_activity_detection": {
                    "disabled": False,
                    "prefix_padding_ms": self.vad.prefix_padding_ms,
                    "silence_duration_ms": self.vad.silence_duration_ms,
                }
            }
        
        return config
    
    def get_api_key(self) -> str:
        """
        Get API key from environment variable.
        
        Returns:
            API key string
            
        Raises:
            RuntimeError: If API key environment variable is not set
        """
        api_key = os.environ.get(self.api_key_env_var)
        if not api_key:
            raise RuntimeError(
                f"{self.api_key_env_var} environment variable is not set. "
                f"Please set it in your environment or in a .env file."
            )
        return api_key