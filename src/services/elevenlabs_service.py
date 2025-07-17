"""
ElevenLabs TTS Service: Handles text-to-speech conversion using ElevenLabs API.

This service provides:
- Async text-to-speech conversion with streaming
- Audio format conversion to match ESP32 requirements
- Progressive chunk delivery without buffering
- Error handling and retry logic
- Integration with TARS conversation flow
"""

import os
import asyncio
import numpy as np
from typing import AsyncGenerator, Optional
from elevenlabs.client import AsyncElevenLabs
from elevenlabs import VoiceSettings
from dataclasses import dataclass, field, asdict

from config.settings import Config


@dataclass
class ElevenLabsStats:
    """Statistics for monitoring ElevenLabs TTS service."""
    tts_requests: int = 0
    audio_chunks_generated: int = 0
    total_characters_processed: int = 0
    total_audio_bytes_generated: int = 0
    errors: int = 0
    last_error: Optional[str] = None


class ElevenLabsService:
    """
    Async service for ElevenLabs TTS integration.
    
    Converts text responses from Gemini Live API into TARS voice audio,
    streaming chunks immediately to minimize latency.
    """
    
    def __init__(self):
        self.client: Optional[AsyncElevenLabs] = None
        self.is_initialized = False
        
        # Statistics for monitoring
        self.stats = ElevenLabsStats()
    
    async def initialize(self) -> None:
        """Initialize the ElevenLabs service."""
        print("🔊 ElevenLabs: Initializing TTS service...")
        
        # Get API key from environment
        api_key = os.environ.get("ELEVENLABS_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ELEVENLABS_API_KEY environment variable is not set. "
                "Please set it in your environment or in a .env file."
            )
        
        # Initialize async client
        try:
            self.client = AsyncElevenLabs(api_key=api_key)
            self.is_initialized = True
            print("✅ ElevenLabs: TTS service initialized successfully")
            
        except Exception as e:
            error_msg = f"Failed to initialize ElevenLabs client: {e}"
            print(f"❌ ElevenLabs: {error_msg}")
            self.stats.errors += 1
            self.stats.last_error = error_msg
            raise
    
    async def shutdown(self) -> None:
        """Clean shutdown of the ElevenLabs service."""
        print("🔄 ElevenLabs: Shutting down...")
        
        if self.client:
            # AsyncElevenLabs client doesn't need explicit shutdown
            self.client = None
        
        self.is_initialized = False
        print("✅ ElevenLabs: Shutdown complete")
    
    async def stream_tts(self, text: str) -> AsyncGenerator[bytes, None]:
        """
        Stream TTS audio chunks for the given text.
        
        Args:
            text: Text to convert to speech
            
        Yields:
            Audio chunks in 16kHz, 16-bit PCM mono format
            
        Raises:
            RuntimeError: If service is not initialized
            Exception: For API errors or network issues
        """
        if not self.is_initialized or not self.client:
            raise RuntimeError("ElevenLabs service is not initialized")
        
        if not text or not text.strip():
            print("⚠️ ElevenLabs: Empty text provided, skipping TTS")
            return
        
        text = text.strip()
        print(f"🎵 ElevenLabs: Starting TTS for text: '{text[:50]}{'...' if len(text) > 50 else ''}'")
        
        # Update statistics
        self.stats.tts_requests += 1
        self.stats.total_characters_processed += len(text)
        
        try:
            # Create voice settings
            voice_settings = VoiceSettings(
                stability=Config.ELEVENLABS_STABILITY,
                similarity_boost=Config.ELEVENLABS_SIMILARITY_BOOST
            )
            
            # Start TTS streaming
            audio_stream = self.client.text_to_speech.stream(
                text=text,
                voice_id=Config.ELEVENLABS_VOICE_ID,
                model_id=Config.ELEVENLABS_MODEL_ID,
                output_format=Config.ELEVENLABS_OUTPUT_FORMAT,
                voice_settings=voice_settings
            )
            
            # Stream chunks as they arrive
            chunk_count = 0
            async for chunk in audio_stream:
                if isinstance(chunk, bytes) and len(chunk) > 0:
                    # Update statistics
                    chunk_count += 1
                    self.stats.audio_chunks_generated += 1
                    self.stats.total_audio_bytes_generated += len(chunk)
                    
                    # Stream chunk directly - format is already pcm_16000
                    yield chunk
            
            print(f"✅ ElevenLabs: TTS completed, generated {chunk_count} audio chunks")
            
        except Exception as e:
            error_msg = f"TTS streaming failed: {e}"
            print(f"❌ ElevenLabs: {error_msg}")
            self.stats.errors += 1
            self.stats.last_error = error_msg
            raise
    
    
    def get_status(self) -> dict:
        """Get current service status and statistics."""
        return {
            'service_type': 'ElevenLabs',
            'is_initialized': self.is_initialized,
            'client_connected': self.client is not None,
            'statistics': asdict(self.stats),
            'config': {
                'voice_id': Config.ELEVENLABS_VOICE_ID,
                'model_id': Config.ELEVENLABS_MODEL_ID,
                'output_format': Config.ELEVENLABS_OUTPUT_FORMAT,
                'stability': Config.ELEVENLABS_STABILITY,
                'similarity_boost': Config.ELEVENLABS_SIMILARITY_BOOST
            }
        }
    
    def is_available(self) -> bool:
        """Check if the service is available for TTS requests."""
        return self.is_initialized and self.client is not None