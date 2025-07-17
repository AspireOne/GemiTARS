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

from services import GeminiService, ESP32ServiceInterface, ESP32StreamingService, ElevenLabsService
from services.hotword_service import HotwordService
from core.conversation_state import ConversationManager, ConversationState
from config import Config

load_dotenv()


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
        
        # Task references for cleanup
        self.conversation_task: Optional[asyncio.Task] = None
        self.gemini_sender_task: Optional[asyncio.Task] = None
        self.gemini_receiver_task: Optional[asyncio.Task] = None
        
    async def run(self) -> None:
        """Main TARS assistant execution loop."""
        print("🤖 TARS Assistant starting...")
        print("🔧 Initializing ESP32 service...")
        
        # Store event loop reference for thread-safe operations
        self.loop = asyncio.get_running_loop()
        
        try:
            # Initialize services
            await self._initialize_esp32_service()
            await self._initialize_elevenlabs_service()
            
            # Start in passive listening mode
            await self._enter_passive_mode()
            
            # Start concurrent tasks
            self.conversation_task = asyncio.create_task(self._conversation_management_loop())
            
            print(f"\n🎯 TARS is ready! Say '{Config.HOTWORD_MODEL}' to activate.")
            print("Press Ctrl+C to exit.")
            
            await self.conversation_task
            
        except Exception as e:
            print(f"\n❌ An error occurred: {e}")
        finally:
            await self._cleanup()
    
    async def _initialize_esp32_service(self) -> None:
        """Initialize ESP32 service based on configuration."""
        if Config.ESP32_SERVICE_TYPE == "mock":
            self.esp32_service = ESP32StreamingService()
        else:
            # Future: ESP32RealService
            raise NotImplementedError("Real ESP32 service not implemented yet")
        
        try:
            await self.esp32_service.initialize()
            self.esp32_service.set_audio_callback(self._route_audio_based_on_state)
            print("✅ ESP32 service initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize ESP32 service: {e}")
            self.esp32_service = None
            raise
    
    async def _initialize_elevenlabs_service(self) -> None:
        """Initialize ElevenLabs TTS service."""
        try:
            self.elevenlabs_service = ElevenLabsService()
            await self.elevenlabs_service.initialize()
            print("✅ ElevenLabs service initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize ElevenLabs service: {e}")
            print("⚠️ TTS will be disabled, continuing with text-only responses")
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
            print(f"⚠️ Error routing audio: {e}")
            
    async def _enter_passive_mode(self) -> None:
        """Enter passive listening mode (hotword detection)."""
        print("💤 TARS: Entering passive listening mode...")
        
        # Close any active Gemini session
        if self.gemini_service:
            try:
                await self.gemini_service.close_session()
                # Stop audio output
                if self.esp32_service:
                    await self.esp32_service.stop_audio_playback()
            except Exception as e:
                print(f"⚠️ Error closing Gemini session: {e}")
            finally:
                self.gemini_service = None
            
        # Cancel Gemini-related tasks
        if self.gemini_sender_task and not self.gemini_sender_task.done():
            self.gemini_sender_task.cancel()
        if self.gemini_receiver_task and not self.gemini_receiver_task.done():
            self.gemini_receiver_task.cancel()
            
        # Start audio streaming for hotword detection
        if self.esp32_service:
            # Only start if not already streaming
            status = self.esp32_service.get_status()
            if not status.get('audio_streaming', False):
                await self.esp32_service.start_audio_streaming()
        self.hotword_service.start_detection()
        self.conversation_manager.transition_to(ConversationState.PASSIVE)
        
        print(f"🎤 Listening for '{Config.HOTWORD_MODEL}'...")
        
    async def _enter_active_mode(self) -> None:
        """Enter active conversation mode."""
        print("🚀 TARS: Activating conversation mode...")
        
        # Stop hotword detection
        self.hotword_service.stop_detection()
        
        # Initialize and start Gemini session
        try:
            self.gemini_service = GeminiService(api_key=self.api_key)
            await self.gemini_service.start_session()
            
            # Transition to active conversation
            self.conversation_manager.transition_to(ConversationState.ACTIVE)
            
            # Start Gemini audio processing tasks
            self.gemini_sender_task = asyncio.create_task(self._gemini_audio_sender())
            self.gemini_receiver_task = asyncio.create_task(self._gemini_response_handler())
            
            # Play acknowledgment
            print(f"🎤 TARS: Listening...")
            # TODO: At the end of the project, add random audio as acknowledgment ("hmh", "listening", "yes?" etc.)
            
        except Exception as e:
            print(f"❌ Error activating conversation mode: {e}")
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
                print("⚠️ No event loop available for activation")
        
    async def _conversation_management_loop(self) -> None:
        """Manage conversation timeouts and state transitions."""
        while True:
            try:
                if self.conversation_manager.state in [ConversationState.ACTIVE, ConversationState.PROCESSING, ConversationState.SPEAKING]:
                    # Check for conversation timeout
                    if self.conversation_manager.is_conversation_timeout():
                        print("⏰ TARS: Conversation timeout, returning to standby.")
                        await self._enter_passive_mode()
                        
                await asyncio.sleep(1)  # Check every second
                
            except Exception as e:
                print(f"⚠️ Error in conversation management: {e}")
                await asyncio.sleep(1)
            
    async def _gemini_audio_sender(self) -> None:
        """Send queued audio to Gemini Live API."""
        if self.gemini_service:
            try:
                await self.gemini_service.start_audio_sender()
            except asyncio.CancelledError:
                print("🔇 Gemini audio sender cancelled")
            except Exception as e:
                print(f"❌ Error in Gemini audio sender: {e}")
            
    async def _gemini_response_handler(self) -> None:
        """Handle responses from Gemini Live API."""
        if not self.gemini_service:
            return
            
        full_response = ""
        is_processing = False  # Flag to ensure we only transition once per turn
        
        try:
            async for response in self.gemini_service.receive_responses():
                # Handle Gemini's text output
                if response.text:
                    # On the first text chunk, transition to PROCESSING to mute the mic
                    if not is_processing:
                        self.conversation_manager.transition_to(ConversationState.PROCESSING)
                        is_processing = True
                    
                    print(response.text, end="", flush=True)
                    full_response += response.text

                if response.is_turn_complete:
                    if full_response.strip():
                        print()  # Add newline after complete response
                        
                        # NEW: Stream TTS audio for complete response
                        await self._stream_tts_response(full_response.strip())
                        
                    full_response = ""
                    is_processing = False  # Reset for the next turn
                    
                    # Reset conversation timeout on complete response
                    self.conversation_manager.update_activity()

                # Handle user transcription
                if response.transcription_text:
                    if response.transcription_finished:
                        print(f"\n> You said: {response.transcription_text}\n")
                        # Reset timeout on user speech
                        self.conversation_manager.update_activity()
                    else:
                        print(f"> You said: {response.transcription_text}", end="\r")
                        
        except asyncio.CancelledError:
            print("🔇 Gemini response handler cancelled")
        except Exception as e:
            print(f"❌ Error in Gemini response handler: {e}")
                    
    async def _stream_tts_response(self, text: str) -> None:
        """Stream TTS audio for the given text response."""
        if not self.elevenlabs_service or not self.esp32_service:
            print("⚠️ TTS or ESP32 service not available, skipping voice output")
            # If services are unavailable, transition back to ACTIVE immediately
            self.conversation_manager.transition_to(ConversationState.ACTIVE)
            return
    
        try:
            # 1. Transition from PROCESSING to SPEAKING
            self.conversation_manager.transition_to(ConversationState.SPEAKING)
            
            print(f"🎵 TARS: Converting to speech and streaming...")
            
            # 2. Stream TTS audio
            chunk_count = 0
            async for audio_chunk in self.elevenlabs_service.stream_tts(text):
                await self.esp32_service.play_audio_chunk(audio_chunk)
                chunk_count += 1
            
            # Wait for the audio queue to be fully processed
            await self.esp32_service.wait_for_playback_completion()
            
            print(f"✅ TARS: Voice output completed ({chunk_count} chunks)")
    
        except Exception as e:
            print(f"❌ Error in TTS streaming: {e}")
        finally:
            # 3. IMPORTANT: Always transition back to ACTIVE after speaking/error
            if self.conversation_manager.state == ConversationState.SPEAKING:
                self.conversation_manager.transition_to(ConversationState.ACTIVE)
                    
    async def _cleanup(self) -> None:
        """Clean up resources."""
        print("\n🔄 TARS: Shutting down...")
        
        # Cancel all tasks
        tasks_to_cancel = [
            self.conversation_task,
            self.gemini_sender_task,
            self.gemini_receiver_task
        ]
        
        for task in tasks_to_cancel:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Shutdown ESP32 service
        if self.esp32_service:
            try:
                await self.esp32_service.shutdown()
            except Exception as e:
                print(f"⚠️ Error shutting down ESP32 service: {e}")
            
        # Close Gemini service
        if self.gemini_service:
            try:
                await self.gemini_service.close_session()
            except Exception as e:
                print(f"⚠️ Error closing Gemini service: {e}")
        
        # Shutdown ElevenLabs service
        if self.elevenlabs_service:
            try:
                await self.elevenlabs_service.shutdown()
            except Exception as e:
                print(f"⚠️ Error shutting down ElevenLabs service: {e}")
            
        # Stop hotword detection
        self.hotword_service.stop_detection()
        
        print("✅ TARS: Shutdown complete")

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
        print("\n👋 TARS: Goodbye!")
    except Exception as e:
        print(f"\n💥 Fatal error: {e}")