"""
Default configuration and environment variable loading for GemiTARS.

This module provides utilities for creating default configurations
and loading overrides from environment variables.
"""

import os
from typing import Optional
from .settings import TARSConfig, AudioConfig, VADConfig, ModelConfig, ConversationConfig


def get_default_config() -> TARSConfig:
    """
    Get the default TARS configuration.
    
    Returns:
        TARSConfig: Default configuration with all sensible defaults
    """
    return TARSConfig()


def load_config_from_env(base_config: Optional[TARSConfig] = None) -> TARSConfig:
    """
    Load configuration from environment variables.
    
    Environment variables follow the pattern: TARS_{SECTION}_{SETTING}
    For example: TARS_AUDIO_SAMPLE_RATE=16000
    
    Args:
        base_config: Base configuration to override. If None, uses defaults.
        
    Returns:
        TARSConfig: Configuration with environment variable overrides applied
    """
    if base_config is None:
        config = get_default_config()
    else:
        # Create a copy to avoid modifying the original
        config = TARSConfig(
            audio=AudioConfig(**base_config.audio.__dict__),
            vad=VADConfig(**base_config.vad.__dict__),
            model=ModelConfig(**base_config.model.__dict__),
            conversation=ConversationConfig(**base_config.conversation.__dict__),
            api_key_env_var=base_config.api_key_env_var
        )
    
    # Audio configuration overrides
    if env_val := os.environ.get("TARS_AUDIO_SAMPLE_RATE"):
        config.audio.sample_rate = int(env_val)
    if env_val := os.environ.get("TARS_AUDIO_BLOCK_SIZE"):
        config.audio.block_size = int(env_val)
    if env_val := os.environ.get("TARS_AUDIO_DTYPE"):
        config.audio.dtype = env_val
    if env_val := os.environ.get("TARS_AUDIO_CHANNELS"):
        config.audio.channels = int(env_val)
    
    # VAD configuration overrides
    if env_val := os.environ.get("TARS_VAD_ENABLED"):
        config.vad.enabled = env_val.lower() in ("true", "1", "yes", "on")
    if env_val := os.environ.get("TARS_VAD_PREFIX_PADDING_MS"):
        config.vad.prefix_padding_ms = int(env_val)
    if env_val := os.environ.get("TARS_VAD_SILENCE_DURATION_MS"):
        config.vad.silence_duration_ms = int(env_val)
    
    # Model configuration overrides
    if env_val := os.environ.get("TARS_MODEL_NAME"):
        config.model.name = env_val
    if env_val := os.environ.get("TARS_MODEL_RESPONSE_MODALITIES"):
        # Parse comma-separated list
        config.model.response_modalities = [m.strip() for m in env_val.split(",")]
    
    # Conversation configuration overrides
    if env_val := os.environ.get("TARS_CONVERSATION_TIMEOUT_SECONDS"):
        config.conversation.timeout_seconds = int(env_val)
    
    # API key environment variable override
    if env_val := os.environ.get("TARS_API_KEY_ENV_VAR"):
        config.api_key_env_var = env_val
    
    return config


def create_config_from_legacy_params(**kwargs) -> TARSConfig:
    """
    Create configuration from legacy parameter names for backwards compatibility.
    
    This function helps migrate from the old parameter-based configuration
    to the new centralized configuration system.
    
    Args:
        **kwargs: Legacy parameter names and values
        
    Returns:
        TARSConfig: Configuration object with legacy parameters applied
    """
    config = get_default_config()
    
    # Map legacy parameter names to new configuration structure
    legacy_mapping = {
        "model": ("model", "name"),
        "samplerate": ("audio", "sample_rate"),
        "blocksize": ("audio", "block_size"),
        "dtype": ("audio", "dtype"),
        "channels": ("audio", "channels"),
        "conversation_timeout": ("conversation", "timeout_seconds"),
    }
    
    for legacy_key, value in kwargs.items():
        if legacy_key in legacy_mapping:
            section, attr = legacy_mapping[legacy_key]
            setattr(getattr(config, section), attr, value)
    
    return config