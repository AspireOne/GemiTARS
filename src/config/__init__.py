"""
Configuration package for GemiTARS.

This package provides centralized configuration management for all components,
including audio processing, VAD settings, model configuration, and conversation management.

Key Features:
- Type-safe configuration with dataclasses
- Environment variable support
- Backwards compatibility with existing code
- Validation and sensible defaults
"""

from .settings import (
    AudioConfig,
    VADConfig, 
    ModelConfig,
    ConversationConfig,
    TARSConfig
)

from .defaults import get_default_config, load_config_from_env

__all__ = [
    'AudioConfig',
    'VADConfig', 
    'ModelConfig',
    'ConversationConfig',
    'TARSConfig',
    'get_default_config',
    'load_config_from_env'
]