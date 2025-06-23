"""
GeminiService: Handles all interactions with the Gemini Live API.

This service encapsulates:
- Client initialization and authentication
- Session lifecycle management
- Audio streaming to the API
- Response processing and handling
- Centralized configuration management
- Extension points for function calling and multimodal features
"""

import asyncio
from typing import Any, AsyncGenerator, Optional, Callable
from google import genai
from google.genai import types

from core.conversation_state import ConversationManager, ConversationState
from config import TARSConfig, get_default_config


class GeminiResponse:
    """Wrapper for Gemini API responses with processed data."""
    
    def __init__(self, raw_response: Any):
        self.raw_response = raw_response
        self.text = raw_response.text if raw_response.text else ""
        self.is_turn_complete = (
            raw_response.server_content and 
            raw_response.server_content.turn_complete
        ) if raw_response.server_content else False
        
        # Handle transcription
        self.transcription_text = ""
        self.transcription_finished = False
        if (raw_response.server_content and
            raw_response.server_content.input_transcription and
            raw_response.server_content.input_transcription.text):
            transcript = raw_response.server_content.input_transcription
            self.transcription_text = transcript.text.strip()
            self.transcription_finished = transcript.finished
            
        # Handle interruption detection (separate from transcription)
        self.interrupted = (
            raw_response.server_content and
            raw_response.server_content.interrupted
        ) if raw_response.server_content else False


class GeminiService:
    """
    Service for managing Gemini Live API interactions.
    
    Provides a clean interface for:
    - Session management
    - Audio streaming
    - Response processing
    - Configuration
    """
    
    def __init__(self, api_key: str, model: str = "gemini-live-2.5-flash-preview",
                 enable_conversation_management: bool = False, config: Optional[TARSConfig] = None):
        """
        Initialize the Gemini service.
        
        Args:
            api_key: Google API key for Gemini
            model: Model name to use (default: gemini-live-2.5-flash-preview)
            enable_conversation_management: Enable conversation state management for VAD (default: False)
            config: Optional TARS configuration object. If None, uses defaults with legacy parameter overrides.
        """
        # Handle configuration - backwards compatibility with legacy parameters
        if config is None:
            # Create default config and override with legacy parameters
            self.tars_config = get_default_config()
            if model != "gemini-live-2.5-flash-preview":
                self.tars_config.model.name = model
        else:
            self.tars_config = config
            # Legacy model parameter takes precedence over config for backwards compatibility
            if model != "gemini-live-2.5-flash-preview":
                self.tars_config.model.name = model
        
        # Initialize client and session management
        self.api_key = api_key
        self.model = self.tars_config.model.name  # Use model from config
        self.client = genai.Client(api_key=api_key)
        self.session: Optional[Any] = None
        self._connection_manager: Optional[Any] = None
        self.audio_queue = asyncio.Queue()
        
        # Conversation state management
        self.enable_conversation_management = enable_conversation_management
        self.conversation_manager = ConversationManager(
            conversation_timeout=self.tars_config.conversation.timeout_seconds
        )
        
        # Generate Gemini API configuration from TARS config
        self.config: Any = self.tars_config.get_gemini_config()
        
        # Extension points for future features
        self.function_registry = {}
        self.response_handlers = []
        
    def set_config(self, config: dict) -> None:
        """Update the session configuration."""
        self.config.update(config)
        
    def add_function(self, name: str, function: Callable) -> None:
        """Register a function for function calling (future feature)."""
        self.function_registry[name] = function
        
    def add_response_handler(self, handler: Callable[[GeminiResponse], None]) -> None:
        """Add a custom response handler (future feature)."""
        self.response_handlers.append(handler)
        
    async def start_session(self) -> None:
        """Start a new Gemini Live session."""
        if self.session:
            await self.close_session()
            
        # Use the async context manager logic
        await self.__aenter__()
        
    async def close_session(self) -> None:
        """Close the current session."""
        if self._connection_manager:
            await self.__aexit__(None, None, None)
            
    async def send_audio(self, audio_data: bytes) -> None:
        """
        Send audio data to the Gemini API.
        
        Args:
            audio_data: Raw audio bytes (PCM format configured in TARSConfig)
        """
        if not self.session:
            raise RuntimeError("Session not started. Call start_session() first.")
            
        await self.session.send_realtime_input(
            audio=types.Blob(data=audio_data, mime_type=self.tars_config.audio.mime_type)
        )
        
    async def send_image(self, image_data: bytes, mime_type: str = "image/jpeg") -> None:
        """
        Send image data to the Gemini API (future multimodal feature).
        
        Args:
            image_data: Raw image bytes
            mime_type: MIME type of the image
        """
        if not self.session:
            raise RuntimeError("Session not started. Call start_session() first.")
            
        # This is a placeholder for future multimodal functionality
        # Implementation will depend on Gemini Live API updates
        await self.session.send_realtime_input(
            image=types.Blob(data=image_data, mime_type=mime_type)
        )
        
    async def receive_responses(self) -> AsyncGenerator[GeminiResponse, None]:
        """
        Async generator that yields processed Gemini responses.
        
        Yields:
            GeminiResponse: Processed response objects
        """
        if not self.session:
            raise RuntimeError("Session not started. Call start_session() first.")
            
        while True:  # Keep processing responses continuously
            async for raw_response in self.session.receive():
                response = GeminiResponse(raw_response)
                
                # Apply custom response handlers
                for handler in self.response_handlers:
                    handler(response)
                    
                yield response
            
    async def start_audio_sender(self) -> None:
        """
        Start the audio sender task that processes queued audio chunks.
        This method runs continuously and should be started as a task.
        """
        while True:
            try:
                audio_chunk_bytes = await self.audio_queue.get()
                await self.send_audio(audio_chunk_bytes)
                self.audio_queue.task_done()
            except Exception as e:
                print(f"Error in audio sender: {e}")
                
    def queue_audio(self, audio_data: bytes) -> None:
        """
        Queue audio data for sending (thread-safe).
        
        Args:
            audio_data: Raw audio bytes to send
        """
        # Queue audio based on conversation management setting
        if not self.enable_conversation_management or self.conversation_manager.should_listen_for_speech():
            self.audio_queue.put_nowait(audio_data)
        
    async def __aenter__(self):
        """Async context manager entry."""
        # Store the context manager from the client
        self._connection_manager = self.client.aio.live.connect(
            model=self.model,
            config=self.config
        )
        self.session = await self._connection_manager.__aenter__()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._connection_manager:
            await self._connection_manager.__aexit__(exc_type, exc_val, exc_tb)
            self.session = None
            self._connection_manager = None
    
    # VAD and conversation management methods
    
    def activate_conversation(self) -> None:
        """Activate conversation mode (called after hotword detection)."""
        self.conversation_manager.transition_to(ConversationState.ACTIVE)
        print(self.tars_config.conversation.messages["listening"])
        
    def is_speech_complete(self, response: GeminiResponse) -> bool:
        """Check if user has finished speaking based on transcription."""
        return (response.transcription_finished and
                bool(response.transcription_text.strip()))
                
    def handle_interruption(self, response: GeminiResponse) -> bool:
        """Handle interruption detection. Returns True if interrupted."""
        if response.interrupted:
            print(self.tars_config.conversation.messages["interrupted"])
            self.conversation_manager.transition_to(ConversationState.ACTIVE)
            return True
        return False
        
    def check_conversation_timeout(self) -> bool:
        """Check and handle conversation timeout."""
        if self.conversation_manager.is_conversation_timeout():
            self.conversation_manager.transition_to(ConversationState.PASSIVE)
            print(self.tars_config.conversation.messages["standby"])
            return True
        return False
        
    # Future extension methods
    
    def enable_function_calling(self, functions: list) -> None:
        """Enable function calling with provided function definitions (future feature)."""
        # This will be implemented when function calling is added
        pass
        
    def set_system_instruction(self, instruction: str) -> None:
        """Set system instruction for the model (future feature)."""
        # This will be implemented when system instructions are added
        pass
        
    def enable_voice_activity_detection(self) -> None:
        """Enable voice activity detection (future feature)."""
        # This will be implemented when VAD is added
        pass