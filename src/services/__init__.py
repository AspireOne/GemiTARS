"""
Services package for GemiTARS.

This package contains service classes that handle specific functionality:
- GeminiService: Handles all Gemini Live API interactions
"""

try:
    from .gemini_service import GeminiService
except ImportError:
    from gemini_service import GeminiService

__all__ = ['GeminiService']