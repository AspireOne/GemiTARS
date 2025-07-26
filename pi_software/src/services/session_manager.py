"""
Session Manager for GemiTARS Client with Persistent Connection
"""

import asyncio
from typing import Optional

from ..core.state_machine import StateMachine, ClientState
from ..audio.audio_interface import AudioInterface
from ..core.hotword_detector import HotwordDetector
from .websocket_client import PersistentWebSocketClient, ConnectionStatus
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
        loop: asyncio.AbstractEventLoop
    ):
        self.state_machine = state_machine
        self.audio_manager = audio_manager
        self.hotword_detector = hotword_detector
        self.websocket_client = websocket_client
        self.loop = loop
        
        self._setup_callbacks()

    def _setup_callbacks(self):
        """Set up callbacks between components."""
        self.hotword_detector.set_callback(self.on_hotword_detected)
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
        await self.audio_manager.stop_recording()
        await self.websocket_client.shutdown()

    async def _start_hotword_listening(self):
        """Start listening for hotwords."""
        self.state_machine.transition_to(ClientState.LISTENING_FOR_HOTWORD)
        await self.audio_manager.start_recording(self.hotword_detector.process_audio)

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
        # The start_session method will handle the state transition
        asyncio.run_coroutine_threadsafe(self.start_session(), self.loop)

    async def start_session(self):
        """Start an active conversation session."""
        # Check if we're connected
        if not self.websocket_client.is_connected():
            logger.warning("Cannot start session: not connected to server")
            await self._start_hotword_listening()  # Go back to listening
            return
        
        logger.info("Starting conversation session")
        
        # Transition to active session
        if not self.state_machine.transition_to(ClientState.ACTIVE_SESSION):
            logger.warning("Could not transition to ACTIVE_SESSION state.")
            return
        
        # Stop hotword detection, start conversation audio
        await self.audio_manager.stop_recording()
        
        # Notify server
        await self.websocket_client.send_message({"type": "hotword_detected"})
        
        # Start streaming audio to server
        await self.audio_manager.start_recording(
            lambda audio_chunk: asyncio.run_coroutine_threadsafe(
                self.websocket_client.send_audio(audio_chunk), self.loop
            )
        )

    async def end_session(self):
        """End the active conversation session."""
        logger.info("Ending conversation session")
        
        # Stop recording
        await self.audio_manager.stop_recording()
        
        # CRITICAL: DO NOT disconnect WebSocket - it stays connected!
        
        # Wait for any pending playback
        await self.audio_manager.wait_for_playback_completion()
        
        # Return to hotword listening
        await self._start_hotword_listening()

    def on_audio_received(self, audio_chunk: bytes):
        """Handle TTS audio from server."""
        asyncio.run_coroutine_threadsafe(
            self.audio_manager.play_audio_chunk(audio_chunk),
            self.loop
        )

    def on_control_message(self, message: dict):
        """Handle control messages from server."""
        msg_type = message.get("type")
        
        if msg_type == "tts_stream_end":
            logger.info("TTS stream ended")
            asyncio.run_coroutine_threadsafe(
                self.confirm_playback_completion(), self.loop
            )
        elif msg_type == "session_end":
            logger.info("Server ended the session")
            asyncio.run_coroutine_threadsafe(self.end_session(), self.loop)

    async def confirm_playback_completion(self):
        """Confirm TTS playback is complete."""
        await self.audio_manager.wait_for_playback_completion()
        logger.info("Playback complete")
        await self.websocket_client.send_message({"type": "playback_complete"})