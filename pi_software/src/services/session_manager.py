"""
Session Manager for GemiTARS Client with Persistent Connection
"""

import asyncio
import random
from typing import Optional

from pi_software.src.config.settings import Config

from ..core.state_machine import StateMachine, ClientState
from ..audio.audio_interface import AudioInterface
from ..core.hotword_detector import HotwordDetector
from ..hardware.button_manager import ButtonManager
from .websocket_client import PersistentWebSocketClient, ConnectionStatus
from .local_sound_manager import LocalSoundManager
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

class SessionManager:
    """
    Orchestrates conversation sessions over a persistent WebSocket connection.
    """

    def __init__(
        self,
        state_machine: StateMachine,
        audio_manager: AudioInterface,
        hotword_detector: HotwordDetector,
        websocket_client: PersistentWebSocketClient,
        local_sound_manager: LocalSoundManager,
        button_manager: ButtonManager,
        loop: asyncio.AbstractEventLoop
    ):
        self.state_machine = state_machine
        self.audio_manager = audio_manager
        self.hotword_detector = hotword_detector
        self.websocket_client = websocket_client
        self.local_sound_manager = local_sound_manager
        self.button_manager = button_manager
        self.loop = loop
        
        # Audio state tracking: "stopped", "hotword", "session"
        self._audio_state = "stopped"
        
        self._setup_callbacks()

    def _setup_callbacks(self):
        """Set up callbacks between components."""
        self.hotword_detector.set_callback(self.on_hotword_detected)
        self.button_manager.set_callback(self.on_button_pressed)
        self.websocket_client.on_connected = self.on_connection_established
        self.websocket_client.on_disconnected = self.on_connection_lost
        self.websocket_client.on_audio_received = self.on_audio_received
        self.websocket_client.on_control_message_received = self.on_control_message

    async def start(self):
        """Start the session manager and establish persistent connection."""
        logger.info("Starting session manager...")
        
        # Start persistent WebSocket connection
        await self.websocket_client.start()
        
        # Start listening for hotwords
        await self._start_hotword_listening()

    async def shutdown(self):
        """Gracefully shutdown all components."""
        logger.info("Shutting down session manager...")
        await self._ensure_audio_state("stopped")
        await self.websocket_client.shutdown()

    async def _start_hotword_listening(self):
        """Start listening for hotwords."""
        self.state_machine.transition_to(ClientState.LISTENING_FOR_HOTWORD)
        success = await self._ensure_audio_state("hotword")
        if not success:
            logger.error("Failed to start hotword listening")
            # Consider transitioning to IDLE state on failure
            self.state_machine.transition_to(ClientState.IDLE)

    def on_connection_established(self):
        """Called when WebSocket connection is established."""
        logger.info("Connection to server established")
        # Continue with current state - no need to change anything

    def on_connection_lost(self):
        """Called when WebSocket connection is lost."""
        logger.warning("Connection to server lost")
        
        # If we're in an active session, end it
        if self.state_machine.state == ClientState.ACTIVE_SESSION:
            logger.info("Ending active session due to connection loss")
            asyncio.run_coroutine_threadsafe(self.end_session(), self.loop)

    def on_hotword_detected(self):
        """Callback executed when hotword is detected."""
        logger.info("Hotword detected - starting session")
        self._trigger_session_activation()
        
    def on_button_pressed(self):
        """Callback executed when button is pressed."""
        logger.info("Button pressed - starting session")
        self._trigger_session_activation()
        
    def _trigger_session_activation(self):
        """Common method to trigger session activation from hotword or button."""
        # The start_session method will handle the state transition
        future = asyncio.run_coroutine_threadsafe(self.start_session(), self.loop)
        future.add_done_callback(self._handle_session_start_result)
        self._play_acknowledgement_sound()
        
    def _play_acknowledgement_sound(self):
        """Play an acknowledgement sound when hotword is detected."""
        try:
            # For now, hardcode to play 'huh' - Later you can add logic to choose different sounds
            ack_sound_name = random.choice(Config.ACKNOWLEDGEMENT_AUDIO_FILES)
            sound_data = self.local_sound_manager.get_sound(ack_sound_name)
            
            if sound_data:
                # Use the existing audio playback infrastructure
                asyncio.run_coroutine_threadsafe(
                    self.audio_manager.play_audio_chunk(sound_data),
                    self.loop
                )
                logger.info("Playing acknowledgement sound: " + ack_sound_name)
            else:
                logger.warning(f"Acknowledgement sound '{ack_sound_name}' not found")
                
        except Exception as e:
            logger.error(f"Error playing acknowledgement sound: {e}")

    def _handle_session_start_result(self, future):
        """Handle the result of session start attempts."""
        try:
            success = future.result()
            if not success:
                logger.warning("Session start failed, remaining in listening state")
        except Exception as e:
            logger.error(f"Session start raised exception: {e}", exc_info=True)

    async def start_session(self):
        """Start an active conversation session with comprehensive error handling."""
        try:
            # Check connection first
            if not self.websocket_client.is_connected():
                logger.warning("Cannot start session: not connected to server")
                return False
            
            logger.info("Starting conversation session")
            
            # Attempt state transition
            if not self.state_machine.transition_to(ClientState.ACTIVE_SESSION):
                logger.error("Failed to transition to ACTIVE_SESSION")
                return False
            
            # Switch to session audio mode
            success = await self._ensure_audio_state("session")
            if not success:
                logger.error("Failed to start session audio recording")
                await self._recover_to_listening_state()
                return False
            
            # Notify server with error handling
            try:
                success = await self.websocket_client.send_message_with_confirmation(
                    {"type": "hotword_detected"}
                )
                if not success:
                    logger.error("Failed to notify server of hotword detection")
                    await self._recover_to_listening_state()
                    return False
            except Exception as e:
                logger.error(f"Error notifying server: {e}")
                await self._recover_to_listening_state()
                return False
            
            logger.info("Session started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Unexpected error starting session: {e}", exc_info=True)
            await self._recover_to_listening_state()
            return False

    async def end_session(self):
        """End the active conversation session with enhanced error handling."""
        logger.info("Ending conversation session")
        
        try:
            # CRITICAL: DO NOT disconnect WebSocket - it stays connected!
            
            # Wait for any pending playback
            try:
                await self.audio_manager.wait_for_playback_completion()
            except Exception as e:
                logger.error(f"Error waiting for playback completion: {e}")
                # Continue with state recovery
            
            # Return to hotword listening
            success = await self._ensure_audio_state("hotword")
            if success:
                self.state_machine.transition_to(ClientState.LISTENING_FOR_HOTWORD)
                logger.info("Session ended successfully")
            else:
                logger.error("Failed to return to hotword listening after session end")
                await self._recover_to_listening_state()
            
        except Exception as e:
            logger.error(f"Error during session end: {e}", exc_info=True)
            # Ensure we attempt recovery even if end_session fails
            try:
                await self._recover_to_listening_state()
            except Exception as recovery_error:
                logger.error(f"Recovery also failed: {recovery_error}", exc_info=True)
                # Last resort: force state to IDLE
                self.state_machine.transition_to(ClientState.IDLE)
                await self._ensure_audio_state("stopped")

    def on_audio_received(self, audio_chunk: bytes):
        """Handle TTS audio from server."""
        asyncio.run_coroutine_threadsafe(
            self.audio_manager.play_audio_chunk(audio_chunk),
            self.loop
        )

    def on_control_message(self, message: dict):
        """Handle control messages from server."""
        msg_type = message.get("type")
        
        if msg_type == "start_of_tts_stream":
            logger.info("TTS stream starting - stopping microphone")
            asyncio.run_coroutine_threadsafe(
                self.on_tts_stream_start(), self.loop
            )
        elif msg_type == "tts_stream_end":
            logger.info("TTS stream ended")
            asyncio.run_coroutine_threadsafe(
                self.confirm_playback_completion(), self.loop
            )
        elif msg_type == "session_end":
            logger.info("Server ended the session")
            asyncio.run_coroutine_threadsafe(self.end_session(), self.loop)

    async def on_tts_stream_start(self):
        """Handle start of TTS stream from server."""
        # Transition to PROCESSING_RESPONSE state
        if self.state_machine.transition_to(ClientState.PROCESSING_RESPONSE):
            # Stop microphone to prevent audio bleeding
            success = await self._ensure_audio_state("stopped")
            if not success:
                logger.error("Failed to stop microphone during TTS stream start")
        else:
            logger.error("Failed to transition to PROCESSING_RESPONSE state")

    async def confirm_playback_completion(self):
        """Confirm TTS playback is complete and re-enable microphone for next user input."""
        await self.audio_manager.wait_for_playback_completion()
        logger.info("Playback complete")
        
        # Only transition back to ACTIVE_SESSION if we're currently in PROCESSING_RESPONSE
        if self.state_machine.state == ClientState.PROCESSING_RESPONSE:
            if self.state_machine.transition_to(ClientState.ACTIVE_SESSION):
                # Re-enable microphone for next user input
                success = await self._ensure_audio_state("session")
                if not success:
                    logger.error("Failed to restart microphone after TTS playback")
                    # Fall back to recovery
                    await self._recover_to_listening_state()
            else:
                logger.error("Failed to transition back to ACTIVE_SESSION after TTS playback")
        
        await self.websocket_client.send_message({"type": "playback_complete"})

    async def _ensure_audio_state(self, desired_state: str):
        """Ensure audio is in the desired state, avoiding unnecessary restarts."""
        if self._audio_state == desired_state:
            logger.debug(f"Audio already in desired state: {desired_state}")
            return True
        
        logger.info(f"Transitioning audio from '{self._audio_state}' to '{desired_state}'")
        
        # Stop current audio if not already stopped
        if self._audio_state != "stopped":
            try:
                await self.audio_manager.stop_recording()
                logger.debug("Audio recording stopped")
            except Exception as e:
                logger.error(f"Error stopping audio recording: {e}")
                # Continue with state change attempt
            finally:
                self._audio_state = "stopped"
        
        # Start new audio if needed
        if desired_state == "hotword":
            try:
                success = await self.audio_manager.start_recording(self.hotword_detector.process_audio)
                if success:
                    self._audio_state = "hotword"
                    logger.debug("Hotword audio recording started")
                    return True
                else:
                    logger.error("Failed to start hotword recording")
                    return False
            except Exception as e:
                logger.error(f"Error starting hotword recording: {e}")
                return False
                
        elif desired_state == "session":
            try:
                success = await self.audio_manager.start_recording(
                    lambda audio_chunk: self._safe_send_audio(audio_chunk.tobytes())
                )
                if success:
                    self._audio_state = "session"
                    logger.debug("Session audio recording started")
                    return True
                else:
                    logger.error("Failed to start session recording")
                    return False
            except Exception as e:
                logger.error(f"Error starting session recording: {e}")
                return False
                
        elif desired_state == "stopped":
            # Already handled above
            logger.debug("Audio recording stopped")
            return True
        else:
            logger.error(f"Unknown audio state requested: {desired_state}")
            return False

    async def _recover_to_listening_state(self):
        """Recover to a consistent listening state after errors."""
        logger.info("Recovering to listening state...")
        
        try:
            # Use centralized audio management for recovery
            success = await self._ensure_audio_state("hotword")
            if success:
                self.state_machine.transition_to(ClientState.LISTENING_FOR_HOTWORD)
                logger.info("Successfully recovered to listening state")
            else:
                logger.error("Failed to start hotword listening during recovery")
                # Fall back to stopped state
                self.state_machine.transition_to(ClientState.IDLE)
                await self._ensure_audio_state("stopped")
                
        except Exception as e:
            logger.error(f"Error during state recovery: {e}", exc_info=True)
            # If recovery fails, try transitioning to IDLE
            self.state_machine.transition_to(ClientState.IDLE)
            await self._ensure_audio_state("stopped")

    def _safe_send_audio(self, audio_chunk: bytes):
        """Safely send audio with error handling."""
        try:
            future = asyncio.run_coroutine_threadsafe(
                self.websocket_client.send_audio(audio_chunk), self.loop
            )
            # Don't wait for completion to avoid blocking audio thread
            future.add_done_callback(self._handle_send_audio_result)
        except Exception as e:
            logger.error(f"Error scheduling audio send: {e}")

    def _handle_send_audio_result(self, future):
        """Handle the result of audio send operations."""
        try:
            future.result()  # This will raise if the send failed
        except Exception as e:
            logger.warning(f"Audio send failed: {e}")
            # Optionally trigger session recovery if too many failures