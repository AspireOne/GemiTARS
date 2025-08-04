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
import string
import unicodedata
from typing import Optional
from websockets.exceptions import ConnectionClosedOK

from dotenv import load_dotenv

from .services.gemini_service import GeminiService
from .services.pi_interface import PiInterfaceService
from .services.pi_websocket_service import PiWebsocketService
from .services.elevenlabs_service import ElevenLabsService
from .services.available_tools import tool_schemas, available_tools
from .core.conversation_state import ConversationManager, ConversationState
from .config.settings import Config
from .utils.logger import setup_logger


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
    
    def __init__(self):
        
        # Core services
        self.gemini_service: Optional[GeminiService] = None
        self.elevenlabs_service: Optional[ElevenLabsService] = None
        self.conversation_manager = ConversationManager()
        
        # Pi communication service
        self.pi_service: PiInterfaceService = PiWebsocketService()
        
        # Event loop reference for thread-safe operations
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        
        # Task management
        self.persistent_tasks = set()
        self.session_tasks = set()
        
        # Pre-sanitize session end phrases for efficient matching
        self.sanitized_session_end_phrases = [
            self._sanitize_transcript_for_keyword_matching(phrase)
            for phrase in Config.SESSION_END_PHRASES
        ]
        
    async def run(self) -> None:
        """Main TARS assistant execution loop."""
        logger.info("TARS Assistant starting...")
        
        # Store event loop reference for thread-safe operations
        self.loop = asyncio.get_running_loop()
        
        try:
            # Initialize services
            await self._initialize_elevenlabs_service()
            
            # Start persistent background tasks
            self._create_task(self._conversation_management_loop(), self.persistent_tasks)

            # The pi_service will be initialized and run here, blocking until exit.
            # It takes callbacks to interact with the assistant.
            if self.pi_service:
                logger.info("Starting Pi Interface Service...")
                await self.pi_service.initialize(
                    hotword_callback=self._enter_active_mode,
                    audio_callback=self._on_audio_chunk_received,
                    disconnect_callback=self._on_client_disconnected
                )
            else:
                logger.critical("Pi Interface Service not initialized. Exiting.")
                return

            logger.info(f"TARS is ready and waiting for a client connection...")
            logger.info("Press Ctrl+C to exit.")
            
            # Wait for all persistent tasks to complete
            if self.persistent_tasks:
                await asyncio.gather(*self.persistent_tasks)
            
        except Exception as e:
            logger.error(f"An error occurred: {e}", exc_info=True)
        finally:
            await self._cleanup()
    
    
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
        
    def _on_audio_chunk_received(self, audio_bytes: bytes) -> None:
        """Callback to handle incoming audio chunks from the Pi."""
        # Route audio to Gemini Live API if in the right state
        if self.conversation_manager.state == ConversationState.ACTIVE:
            if self.gemini_service:
                self.gemini_service.queue_audio(audio_bytes)
        # In all other states, audio is ignored.
            
    async def _on_client_disconnected(self) -> None:
        """Callback for when the client disconnects."""
        logger.warning("Client disconnected. Checking if a session cleanup is needed.")
        if self.conversation_manager.state != ConversationState.PASSIVE:
            logger.info("Client disconnected during an active session. Forcing return to passive mode.")
            await self._enter_passive_mode()

    async def _end_session_by_keyword(self) -> None:
        """End a session triggered by keyword detection, notifying the Pi client first."""
        logger.info("Ending session due to keyword detection. Notifying client.")
        if self.pi_service:
            await self.pi_service.send_control_message({"type": "session_end"})
        await self._enter_passive_mode()

    async def _enter_passive_mode(self) -> None:
        """End a conversation and return to a passive state."""
        logger.info("Conversation ended. Returning to passive state.")
        
        # Close any active Gemini session
        if self.gemini_service:
            try:
                await self.gemini_service.close_session()
            except Exception as e:
                logger.warning(f"Error closing Gemini session: {e}")
            finally:
                self.gemini_service = None
            
        # Cancel all session-specific tasks
        for task in list(self.session_tasks):
            task.cancel()
        self.session_tasks.clear()
            
        self.conversation_manager.transition_to(ConversationState.PASSIVE)
        
        logger.info(f"Ready for next activation.")
        
    async def _enter_active_mode(self) -> None:
        """Enter active conversation mode, triggered by the client."""
        # Only activate if we're in passive mode
        if self.conversation_manager.state != ConversationState.PASSIVE:
            logger.warning("Attempted to activate conversation while not in passive state. Ignoring.")
            return

        logger.info("Hotword detected by client. Activating conversation mode...")
        
        # Initialize and start Gemini session
        try:
            self.gemini_service = GeminiService(system_prompt=Config.SYSTEM_PROMPT)
            self.gemini_service.enable_function_calling(
                schemas=tool_schemas,
                functions=available_tools
            )
            await self.gemini_service.start_session()
            
            # Transition to active conversation
            self.conversation_manager.transition_to(ConversationState.ACTIVE)
            
            # Start Gemini audio processing tasks
            self._create_task(self._gemini_audio_sender(), self.session_tasks)
            self._create_task(self._gemini_response_handler(), self.session_tasks)
            
            logger.info("Listening for user speech...")
            
        except Exception as e:
            logger.error(f"Error activating conversation mode: {e}", exc_info=True)
            # Fall back to passive mode on error
            self.gemini_service = None
            await self._enter_passive_mode()
        
        
    def _create_task(self, coro, task_set):
        """Create an asyncio task, add it to a set, and set up a callback for cleanup."""
        task = asyncio.create_task(coro)
        task_set.add(task)
        task.add_done_callback(task_set.discard)
        return task
    
    def _sanitize_transcript_for_keyword_matching(self, text: str) -> str:
            """Remove punctuation, whitespace, diacritics, and '<noise>' from transcript for keyword matching."""
            # Remove <noise> and lowercase
            sanitized = text.lower().replace("<noise>", "")
            # Normalize and remove diacritics (accents)
            sanitized = ''.join(
                c for c in unicodedata.normalize('NFKD', sanitized)
                if not unicodedata.combining(c)
            )
            # Remove specific punctuation and whitespace
            chars_to_remove = '.!?," \n\t\r"\''
            translator = str.maketrans('', '', chars_to_remove)
            return sanitized.translate(translator)

    async def _conversation_management_loop(self) -> None:
        """Manage conversation timeouts and state transitions."""
        while True:
            try:
                if self.conversation_manager.state == ConversationState.ACTIVE:
                    # Check for conversation timeout
                    if self.conversation_manager.is_conversation_timeout():
                        logger.info("Conversation timeout. Notifying client and returning to standby.")
                        if self.pi_service:
                            await self.pi_service.send_control_message({"type": "session_end"})
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
            except ConnectionClosedOK:
                # This is an expected closure when the session times out or is otherwise gracefully terminated.
                logger.info("Gemini session closed normally.")
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
                # Log the raw response for debugging tool usage
                # logger.debug(f"RAW GEMINI RESPONSE: {response.raw_response}")

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
                    current_transcription = ""  # Reset transcript after each turn
                    
        except ConnectionClosedOK:
            # This is an expected closure when the session times out or is otherwise gracefully terminated.
            logger.info("Gemini response handler closed normally.")
        except asyncio.CancelledError:
            logger.debug("Gemini response handler cancelled")
        except Exception as e:
            logger.error(f"Error in Gemini response handler: {e}", exc_info=True)

    def _handle_gemini_text_chunk(self, text: str, full_response: str, is_processing: bool) -> tuple[str, bool]:
        """Handle a chunk of text from Gemini's response."""
        if not is_processing:
            print()  # Newline to separate user speech from assistant response
            self.conversation_manager.transition_to(ConversationState.PROCESSING)
            is_processing = True
        
        print(text, end="", flush=True)
        full_response += text
        return full_response, is_processing

    def _handle_transcription_chunk(self, response, current_transcription: str) -> str:
        """Handle a chunk of user speech transcription."""
        self.conversation_manager.update_activity()
        
        if not current_transcription:
            print("> You said:", end="", flush=True)
        
        print(response.transcription_text, end="", flush=True)
        current_transcription += response.transcription_text
        
        sanitized_transcript = self._sanitize_transcript_for_keyword_matching(current_transcription)
        if sanitized_transcript in self.sanitized_session_end_phrases:
            logger.info(f"Session ending phrase detected. Ending session.")
            asyncio.create_task(self._end_session_by_keyword())
            return "" # Return empty string to stop further processing

        if response.transcription_finished:
            current_transcription = ""
            
        return current_transcription

    async def _handle_turn_completion(self, full_response: str) -> None:
        """Handle the completion of a conversational turn."""
        if full_response.strip():
            print()  # Add newline after complete response from the LLM
            await self._stream_tts_response(full_response.strip())
            
                    
    async def _stream_tts_response(self, text: str) -> None:
        """Stream TTS audio for the given text response."""
        if not self.elevenlabs_service or not self.pi_service:
            logger.warning("TTS or ESP32 service not available, skipping voice output")
            # If services are unavailable, transition back to ACTIVE immediately
            self.conversation_manager.transition_to(ConversationState.ACTIVE)
            return
    
        try:
            # 1. Transition from PROCESSING to SPEAKING
            self.conversation_manager.transition_to(ConversationState.SPEAKING)
            
            # 2. Clear any stale playback completion events from previous turns
            await self.pi_service.clear_playback_event()

            # 3. Signal to client that TTS streaming is about to start (to stop microphone)
            await self.pi_service.send_control_message({"type": "start_of_tts_stream"})
            
            logger.info("Converting to speech and streaming...")
            
            # 4. Stream TTS audio
            chunk_count = 0
            async for audio_chunk in self.elevenlabs_service.stream_tts(text):
                await self.pi_service.play_audio_chunk(audio_chunk)
                chunk_count += 1
            
            # Signal to the client that the audio stream is finished
            await self.pi_service.send_control_message({"type": "tts_stream_end"})

            # Wait for the client to confirm that playback is complete
            await self.pi_service.wait_for_playback_completion()
            
            logger.info(f"Voice output completed ({chunk_count} chunks)")
    
        except Exception as e:
            logger.error(f"Error in TTS streaming: {e}", exc_info=True)
        finally:
            # 3. IMPORTANT: Always transition back to ACTIVE after speaking/error
            self.conversation_manager.update_activity()
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
        
        # Wait for all tasks to be cancelled, with a timeout
        if all_tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*all_tasks, return_exceptions=True),
                    timeout=5.0  # 5-second timeout for graceful shutdown
                )
            except asyncio.TimeoutError:
                logger.warning("Shutdown timeout: Some tasks did not exit gracefully.")
        
        # Shutdown Pi service
        if self.pi_service:
            try:
                await self.pi_service.shutdown()
            except Exception as e:
                logger.warning(f"Error shutting down Pi service: {e}")
            
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
            
        
        logger.info("Shutdown complete")

    def get_status(self) -> dict:
        """Get current status of TARS assistant."""
        return {
            "conversation_state": self.conversation_manager.state.value,
            "gemini_active": self.gemini_service is not None,
            "elevenlabs_status": self.elevenlabs_service.get_status() if self.elevenlabs_service else None,
            "elevenlabs_available": self.elevenlabs_service.is_available() if self.elevenlabs_service else False,
            "client_connected": self.pi_service.is_client_connected() if self.pi_service else False
        }


async def main() -> None:
    """Main entry point."""
    # Create and run TARS assistant
    assistant = TARSAssistant()
    await assistant.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Goodbye!")
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)