"""
Services package for GemiTARS.

This package contains service classes that handle specific functionality:
- GeminiService: Handles all Gemini Live API interactions
- HotwordService: Handles hotword detection using OpenWakeWord
- ESP32ServiceInterface: Abstract interface for ESP32 services
- ESP32MockService: Mock implementation for development and testing
"""

from .gemini_service import GeminiService
from .hotword_service import HotwordService
from .esp32_interface import ESP32ServiceInterface, AudioStreamConfig, ESP32Status
from .esp32_mock_service import ESP32MockService
from .esp32_streaming_service import ESP32StreamingService
from .elevenlabs_service import ElevenLabsService

__all__ = [
    'GeminiService',
    'HotwordService',
    'ESP32ServiceInterface',
    'ESP32MockService',
    'ESP32StreamingService',
    'ElevenLabsService',
    'AudioStreamConfig',
    'ESP32Status'
]