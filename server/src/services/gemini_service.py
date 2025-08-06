"""
GeminiService: Handles all interactions with the Gemini Live API.

This service encapsulates:
- Client initialization and authentication
- Session lifecycle management  
- Audio streaming to the API
- Response processing and handling
- Configuration management
- Extension points for function calling and multimodal features
"""

import asyncio
import inspect
import os
from typing import Any, AsyncGenerator, Optional, Callable, AsyncContextManager, List
from google import genai
from google.genai import types
from google.genai.live import AsyncSession

from ..config.settings import Config
from ..utils.logger import setup_logger
from .available_tools import available_tools, tool_schemas

logger = setup_logger(os.path.splitext(os.path.basename(__file__))[0])


class GeminiResponse:
    """Wrapper for Gemini API responses with processed data."""
    
    def __init__(self, raw_response: types.LiveServerMessage):
        self.raw_response = raw_response
        self.text = raw_response.text if raw_response.text else ""
        self.is_turn_complete = (
            raw_response.server_content and
            raw_response.server_content.turn_complete
        ) if raw_response.server_content else False
        
        # Handle tool calls
        self.tool_call = raw_response.tool_call if raw_response.tool_call else None

        # Handle transcription
        self.transcription_text = ""
        self.transcription_finished = False
        if (raw_response.server_content and
            raw_response.server_content.input_transcription):
            transcript = raw_response.server_content.input_transcription
            if transcript.text:
                self.transcription_text = transcript.text
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
    SLIDING_WINDOW_TOKENS_TRIGGER = 32000
    TEMPERATURE = 0.85
    
    def __init__(self, model: str = Config.DEFAULT_MODEL,
                 system_prompt: Optional[str] = None):
        """
        Initialize the Gemini service.

        Args:
            model: Model name to use (default: Config.DEFAULT_MODEL)
            system_prompt: The system prompt to send to the model at the start of the session
        """
        self.api_key = os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment.")
        
        self.model = model
        self.system_prompt = system_prompt
        self.client = genai.Client(api_key=self.api_key)
        self.session: Optional[AsyncSession] = None
        self._connection_manager: Optional[AsyncContextManager[AsyncSession]] = None
        self.audio_queue = asyncio.Queue()

        # Default configuration with VAD enabled
        self.config: types.LiveConnectConfig = types.LiveConnectConfig(
            response_modalities=[types.Modality.TEXT],
            tools=tool_schemas,
            context_window_compression=types.ContextWindowCompressionConfig(
                sliding_window=types.SlidingWindow(),
                trigger_tokens=GeminiService.SLIDING_WINDOW_TOKENS_TRIGGER,
            ),
            input_audio_transcription=types.AudioTranscriptionConfig(),
            realtime_input_config=types.RealtimeInputConfig(
                activity_handling=types.ActivityHandling.NO_INTERRUPTION,
                automatic_activity_detection=types.AutomaticActivityDetection(
                    disabled=False,
                    prefix_padding_ms=Config.VAD_PREFIX_PADDING_MS,
                    silence_duration_ms=Config.VAD_SILENCE_DURATION_MS,
                    start_of_speech_sensitivity=types.StartSensitivity.START_SENSITIVITY_HIGH,
                )
            ),
            generation_config=types.GenerationConfig(
                temperature=GeminiService.TEMPERATURE
            ),
        )

        # Extension points for future features
        self.function_registry = {}  # Maps tool names to functions
        self.response_handlers = []
        self.tools_config = None # For storing tool schemas
        
    def set_config(self, config: dict) -> None:
        """
        Update the session configuration by creating a new model with updated values.
        """
        self.config = self.config.model_copy(update=config)
        
    def add_function(self, name: str, function: Callable) -> None:
        """Register a function for function calling."""
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
            audio_data: Raw audio bytes (PCM format, 16kHz, 16-bit)
        """
        if not self.session:
            raise RuntimeError("Session not started. Call start_session() first.")
            
        await self.session.send_realtime_input(
            audio=types.Blob(data=audio_data, mime_type=Config.AUDIO_MIME_TYPE)
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
            media=types.Blob(data=image_data, mime_type=mime_type)
        )
        
    async def receive_responses(self) -> AsyncGenerator[GeminiResponse, None]:
        """
        Async generator that yields processed Gemini responses and handles tool calls.
        
        Yields:
            GeminiResponse: Processed response objects
        """
        if not self.session:
            raise RuntimeError("Session not started. Call start_session() first.")
            
        while True:
            async for raw_response in self.session.receive():
                response = GeminiResponse(raw_response)

                if response.tool_call:
                    asyncio.create_task(self._handle_tool_call(response.tool_call))
                
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
                if audio_chunk_bytes is None: # Add a way to gracefully exit
                    break
                await self.send_audio(audio_chunk_bytes)
                self.audio_queue.task_done()
            except asyncio.CancelledError:
                logger.debug("Audio sender task cancelled.")
                break # Or just re-raise
            except Exception:
                logger.exception("Error in audio sender")
                
    def queue_audio(self, audio_data: bytes) -> None:
        """
        Queue audio data for sending (thread-safe).

        Args:
            audio_data: Raw audio bytes to send
        """
        self.audio_queue.put_nowait(audio_data)
        
    async def __aenter__(self):
        """Async context manager entry."""
        # Store the context manager from the client
        final_config = self.config
        update_dict = {}
        if self.system_prompt:
            update_dict['system_instruction'] = self.system_prompt
        if self.tools_config:
            update_dict['tools'] = self.tools_config
            
        if update_dict:
            final_config = self.config.model_copy(update=update_dict)

        self._connection_manager = self.client.aio.live.connect(
            model=self.model,
            config=final_config,
        )
        self.session = await self._connection_manager.__aenter__()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._connection_manager:
            await self._connection_manager.__aexit__(exc_type, exc_val, exc_tb)
            self.session = None
            self._connection_manager = None
    
    # Future extension methods
    
    async def _handle_tool_call(self, tool_call: Any) -> None:
        """Handle incoming tool calls from the Gemini API."""
        logger.info(f"Handling tool call: {tool_call}")
        function_responses = []
        
        for fc in tool_call.function_calls:
            tool_name = fc.name
            logger.info(f"Attempting to execute tool: '{tool_name}'")
            
            if tool_name in self.function_registry:
                tool_func = self.function_registry[tool_name]
                tool_args = dict(fc.args) if fc.args else {}
                logger.info(f"Executing with args: {tool_args}")
                
                try:
                    # Check if the function is a coroutine function and await it
                    if inspect.iscoroutinefunction(tool_func):
                        result = await tool_func(**tool_args)
                    else:
                        result = tool_func(**tool_args)
                        
                    logger.info(f"Tool '{tool_name}' executed successfully. Result: {result}")
                    
                    function_response = types.FunctionResponse(
                        id=fc.id,
                        name=tool_name,
                        response={"result": result}
                    )
                    function_responses.append(function_response)
                    
                except Exception as e:
                    logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
                    function_responses.append(types.FunctionResponse(
                        id=fc.id,
                        name=tool_name,
                        response={"error": str(e)}
                    ))
            else:
                logger.warning(f"Tool '{tool_name}' not found in registry.")

        if function_responses and self.session:
            logger.info(f"Sending tool responses: {function_responses}")
            await self.session.send_tool_response(function_responses=function_responses)
        else:
            logger.warning("No function responses to send.")

    def enable_function_calling(self, schemas: List[types.FunctionDeclaration], functions: dict) -> None:
        """
        Enable function calling with provided function definitions.
        
        Args:
            schemas: A list of FunctionDeclaration objects for the API.
            functions: A dictionary mapping function names to their implementations.
        """
        self.tools_config = [{"function_declarations": schemas}]
        self.function_registry = functions
        
    def set_system_instruction(self, instruction: str) -> None:
        """
        Set or update the system instruction for the model.
        This will be applied the next time a session is started.
        """
        self.system_prompt = instruction
        
    def enable_voice_activity_detection(self) -> None:
        """Enable voice activity detection (future feature)."""
        # This will be implemented when VAD is added
        pass