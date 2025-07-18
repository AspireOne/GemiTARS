"""
TARS Assistant with Hotword Detection

This is the main application that integrates:
- Hotword detection using OpenWakeWord (passive mode)
- Gemini Live API conversation (active mode)
- State-based audio routing and management
- Automatic conversation timeouts

Usage: python src/main_with_hotword.py
"""

import os
import asyncio
from typing import Optional

from dotenv import load_dotenv

from services.gemini_service import GeminiService
from services.esp32_interface import ESP32ServiceInterface
from services.esp32_mock_service import ESP32MockService
from services.elevenlabs_service import ElevenLabsService
from services.hotword_service import HotwordService
from core.conversation_state import ConversationManager, ConversationState
from config.settings import Config
from utils.logger import setup_logger

load_dotenv()

logger = setup_logger(__name__)


class TARSAssistant:
    """
    Main TARS assistant with hotword activation.
    
    Manages the complete flow:
    1. Passive listening for "Alexa" (using existing model)
    2. Conversation activation and management
    3. Audio streaming coordination
    4. State transitions and timeouts
    """
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        
        # Core services
        self.hotword_service = HotwordService()
        self.gemini_service: Optional[GeminiService] = None
        self.elevenlabs_service: Optional[ElevenLabsService] = None
        self.conversation_manager = ConversationManager()
        
        # ESP32 service (mock or real)
        self.esp32_service: Optional[ESP32ServiceInterface] = None
        
        # Event loop reference for thread-safe operations
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        
        # Setup hotword activation callback
        self.hotword_service.set_activation_callback(self._on_hotword_detected)
        
        # Task management
        self.persistent_tasks = set()
        self.session_tasks = set()
        
    async def run(self) -> None:
        """Main TARS assistant execution loop."""
        logger.info("TARS Assistant starting...")
        
        # Store event loop reference for thread-safe operations
        self.loop = asyncio.get_running_loop()
        
        try:
            # Initialize services
            await self._initialize_esp32_service()
            await self._initialize_elevenlabs_service()
            
            # Start persistent background tasks
            self._create_task(self._conversation_management_loop(), self.persistent_tasks)
            
            # Start in passive listening mode
            await self._enter_passive_mode()
            
            logger.info(f"TARS is ready! Say '{Config.HOTWORD_MODEL}' to activate.")
            logger.info("Press Ctrl+C to exit.")
            
            # Wait for all persistent tasks to complete
            if self.persistent_tasks:
                await asyncio.gather(*self.persistent_tasks)
            
        except Exception as e:
            logger.error(f"An error occurred: {e}", exc_info=True)
        finally:
            await self._cleanup()
    
    async def _initialize_esp32_service(self) -> None:
        """Initialize ESP32 service based on configuration."""
        if Config.ESP32_SERVICE_TYPE == "mock":
            self.esp32_service = ESP32MockService()
        else:
            # Future: ESP32RealService
            raise NotImplementedError("Real ESP32 service not implemented yet")
        
        try:
            await self.esp32_service.initialize()
            self.esp32_service.set_audio_callback(self._route_audio_based_on_state)
            logger.info("ESP32 service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize ESP32 service: {e}", exc_info=True)
            self.esp32_service = None
            raise
    
    async def _initialize_elevenlabs_service(self) -> None:
        """Initialize ElevenLabs TTS service."""
        try:
            self.elevenlabs_service = ElevenLabsService()
            await self.elevenlabs_service.initialize()
            logger.info("ElevenLabs service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize ElevenLabs service: {e}", exc_info=True)
            logger.warning("TTS will be disabled, continuing with text-only responses")
            self.elevenlabs_service = None
            # Don't raise - allow system to continue without TTS
        
    def _route_audio_based_on_state(self, audio_bytes: bytes) -> None:
        """Route audio based on current conversation state."""
        state = self.conversation_manager.state
        try:
            if state == ConversationState.PASSIVE:
                # Route to hotword detection
                self.hotword_service.process_audio_chunk(audio_bytes)
    
            elif state == ConversationState.ACTIVE:
                # Route to Gemini Live API
                if self.gemini_service:
                    self.gemini_service.queue_audio(audio_bytes)
            
            # In all other states (PROCESSING, SPEAKING), audio is ignored.
        except Exception as e:
            logger.warning(f"Error routing audio: {e}")
            
    async def _enter_passive_mode(self) -> None:
        """Enter passive listening mode (hotword detection)."""
        logger.info("Entering passive listening mode...")
        
        # Close any active Gemini session
        if self.gemini_service:
            try:
                await self.gemini_service.close_session()
                # Stop audio output
                if self.esp32_service:
                    await self.esp32_service.stop_audio_playback()
            except Exception as e:
                logger.warning(f"Error closing Gemini session: {e}")
            finally:
                self.gemini_service = None
            
        # Cancel all session-specific tasks
        for task in list(self.session_tasks):
            task.cancel()
        self.session_tasks.clear()
            
        # Start audio streaming for hotword detection
        if self.esp32_service:
            # Only start if not already streaming
            status = self.esp32_service.get_status()
            if not status.get('audio_streaming', False):
                await self.esp32_service.start_audio_streaming()
        self.hotword_service.start_detection()
        self.conversation_manager.transition_to(ConversationState.PASSIVE)
        
        logger.info(f"Listening for '{Config.HOTWORD_MODEL}'...")
        
    async def _enter_active_mode(self) -> None:
        """Enter active conversation mode."""
        logger.info("Activating conversation mode...")
        
        # Stop hotword detection
        self.hotword_service.stop_detection()
        
        # Initialize and start Gemini session
        try:
            self.gemini_service = GeminiService(
                api_key=self.api_key,
                system_prompt=Config.SYSTEM_PROMPT
            )
            await self.gemini_service.start_session()
            
            # Transition to active conversation
            self.conversation_manager.transition_to(ConversationState.ACTIVE)
            
            # Start Gemini audio processing tasks
            self._create_task(self._gemini_audio_sender(), self.session_tasks)
            self._create_task(self._gemini_response_handler(), self.session_tasks)
            
            # Play acknowledgment
            logger.info("Listening...")
            # TODO: At the end of the project, add random audio as acknowledgment ("hmh", "listening", "yes?" etc.)
            
        except Exception as e:
            logger.error(f"Error activating conversation mode: {e}", exc_info=True)
            # Fall back to passive mode on error
            await self._enter_passive_mode()
        
    def _on_hotword_detected(self) -> None:
        """Callback executed when hotword is detected."""
        # Only activate if we're in passive mode
        if self.conversation_manager.state == ConversationState.PASSIVE:
            # Schedule transition to active mode using stored event loop
            if self.loop:
                self.loop.call_soon_threadsafe(
                    lambda: asyncio.create_task(self._enter_active_mode())
                )
            else:
                logger.warning("No event loop available for activation")
        
    def _create_task(self, coro, task_set):
        """Create an asyncio task, add it to a set, and set up a callback for cleanup."""
        task = asyncio.create_task(coro)
        task_set.add(task)
        task.add_done_callback(task_set.discard)
        return task

    async def _conversation_management_loop(self) -> None:
        """Manage conversation timeouts and state transitions."""
        while True:
            try:
                if self.conversation_manager.state in [ConversationState.ACTIVE, ConversationState.PROCESSING]:
                    # Check for conversation timeout
                    if self.conversation_manager.is_conversation_timeout():
                        logger.info("Conversation timeout, returning to standby.")
                        await self._enter_passive_mode()
                        
                await asyncio.sleep(1)  # Check every second
                
            except Exception as e:
                logger.warning(f"Error in conversation management: {e}")
                await asyncio.sleep(1)
            
    async def _gemini_audio_sender(self) -> None:
        """Send queued audio to Gemini Live API."""
        if self.gemini_service:
            try:
                await self.gemini_service.start_audio_sender()
            except asyncio.CancelledError:
                logger.debug("Gemini audio sender cancelled")
            except Exception as e:
                logger.error(f"Error in Gemini audio sender: {e}", exc_info=True)
            
    async def _gemini_response_handler(self) -> None:
        """Handle responses from Gemini Live API by dispatching to helper methods."""
        if not self.gemini_service:
            return

        full_response = ""
        is_processing = False
        current_transcription = ""

        try:
            async for response in self.gemini_service.receive_responses():
                if response.text:
                    full_response, is_processing = self._handle_gemini_text_chunk(
                        response.text, full_response, is_processing
                    )

                if response.transcription_text:
                    current_transcription = self._handle_transcription_chunk(response, current_transcription)

                if response.is_turn_complete:
                    await self._handle_turn_completion(full_response)
                    full_response = ""
                    is_processing = False
                    
        except asyncio.CancelledError:
            logger.debug("Gemini response handler cancelled")
        except Exception as e:
            logger.error(f"Error in Gemini response handler: {e}", exc_info=True)

    def _handle_gemini_text_chunk(self, text: str, full_response: str, is_processing: bool) -> tuple[str, bool]:
        """Handle a chunk of text from Gemini's response."""
        if not is_processing:
            self.conversation_manager.transition_to(ConversationState.PROCESSING)
            is_processing = True
        
        print(text, end="", flush=True)
        full_response += text
        return full_response, is_processing

    def _handle_transcription_chunk(self, response, current_transcription: str) -> str:
        """Handle a chunk of user speech transcription."""
        self.conversation_manager.update_activity()
        
        if not current_transcription:
            print("> You said: ", end="", flush=True)
        
        print(response.transcription_text, end="", flush=True)
        current_transcription += response.transcription_text
        
        if response.transcription_finished:
            print()
            current_transcription = ""
            
        return current_transcription

    async def _handle_turn_completion(self, full_response: str) -> None:
        """Handle the completion of a conversational turn."""
        if full_response.strip():
            print()  # Add newline after complete response
            await self._stream_tts_response(full_response.strip())
            
        self.conversation_manager.update_activity()
                    
    async def _stream_tts_response(self, text: str) -> None:
        """Stream TTS audio for the given text response."""
        if not self.elevenlabs_service or not self.esp32_service:
            logger.warning("TTS or ESP32 service not available, skipping voice output")
            # If services are unavailable, transition back to ACTIVE immediately
            self.conversation_manager.transition_to(ConversationState.ACTIVE)
            return
    
        try:
            # 1. Transition from PROCESSING to SPEAKING
            self.conversation_manager.transition_to(ConversationState.SPEAKING)
            
            logger.info("Converting to speech and streaming...")
            
            # 2. Stream TTS audio
            chunk_count = 0
            async for audio_chunk in self.elevenlabs_service.stream_tts(text):
                await self.esp32_service.play_audio_chunk(audio_chunk)
                chunk_count += 1
            
            # Wait for the audio queue to be fully processed
            await self.esp32_service.wait_for_playback_completion()
            
            logger.info(f"Voice output completed ({chunk_count} chunks)")
    
        except Exception as e:
            logger.error(f"Error in TTS streaming: {e}", exc_info=True)
        finally:
            # 3. IMPORTANT: Always transition back to ACTIVE after speaking/error
            if self.conversation_manager.state == ConversationState.SPEAKING:
                self.conversation_manager.transition_to(ConversationState.ACTIVE)
                    
    async def _cleanup(self) -> None:
        """Clean up resources."""
        logger.info("Shutting down...")
        
        # Cancel all background tasks
        all_tasks = self.persistent_tasks.union(self.session_tasks)
        for task in all_tasks:
            if not task.done():
                task.cancel()
        
        # Wait for all tasks to be cancelled
        if all_tasks:
            await asyncio.gather(*all_tasks, return_exceptions=True)
        
        # Shutdown ESP32 service
        if self.esp32_service:
            try:
                await self.esp32_service.shutdown()
            except Exception as e:
                logger.warning(f"Error shutting down ESP32 service: {e}")
            
        # Close Gemini service
        if self.gemini_service:
            try:
                await self.gemini_service.close_session()
            except Exception as e:
                logger.warning(f"Error closing Gemini service: {e}")
        
        # Shutdown ElevenLabs service
        if self.elevenlabs_service:
            try:
                await self.elevenlabs_service.shutdown()
            except Exception as e:
                logger.warning(f"Error shutting down ElevenLabs service: {e}")
            
        # Stop hotword detection
        self.hotword_service.stop_detection()
        
        logger.info("Shutdown complete")

    def get_status(self) -> dict:
        """Get current status of TARS assistant."""
        return {
            "conversation_state": self.conversation_manager.state.value,
            "hotword_status": self.hotword_service.get_status(),
            "gemini_active": self.gemini_service is not None,
            "elevenlabs_status": self.elevenlabs_service.get_status() if self.elevenlabs_service else None,
            "elevenlabs_available": self.elevenlabs_service.is_available() if self.elevenlabs_service else False,
            "esp32_status": self.esp32_service.get_status() if self.esp32_service else None,
            "esp32_connected": self.esp32_service.is_connected() if self.esp32_service else False
        }


async def main() -> None:
    """Main entry point."""
    # Check for API key
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY environment variable is not set. "
            "Please set it in your environment or in a .env file."
        )
    
    # Create and run TARS assistant
    assistant = TARSAssistant(api_key)
    await assistant.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Goodbye!")
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)