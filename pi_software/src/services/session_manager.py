"""
Session Manager for the GemiTARS Client
"""

import asyncio
from typing import Optional

from ..core.state_machine import StateMachine, ClientState
from ..audio.audio_interface import AudioInterface
from ..core.hotword_detector import HotwordDetector
from .websocket_client import WebSocketClient
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

class SessionManager:
    """
    Orchestrates a complete conversation session from hotword detection to completion.
    """

    def __init__(
        self,
        state_machine: StateMachine,
        audio_manager: AudioInterface,
        hotword_detector: HotwordDetector,
        websocket_client: WebSocketClient
    ):
        self.state_machine = state_machine
        self.audio_manager = audio_manager
        self.hotword_detector = hotword_detector
        self.websocket_client = websocket_client
        
        self._setup_callbacks()

    def _setup_callbacks(self):
        """Set up callbacks between components."""
        self.hotword_detector.set_callback(self.on_hotword_detected)
        self.websocket_client.on_audio_received = self.on_audio_received
        self.websocket_client.on_connection_lost = self.on_connection_lost

    async def start(self):
        """Starts the main client loop."""
        logger.info("Session manager starting...")
        self.state_machine.transition_to(ClientState.LISTENING_FOR_HOTWORD)
        await self.audio_manager.start_recording(self.hotword_detector.process_audio)

    def on_hotword_detected(self):
        """Callback executed when the hotword is detected."""
        if self.state_machine.transition_to(ClientState.HOTWORD_DETECTED):
            asyncio.create_task(self.handle_active_session())

    async def handle_active_session(self):
        """Manages the flow of an active conversation session."""
        self.state_machine.transition_to(ClientState.CONNECTING_TO_SERVER)
        
        # Stop feeding audio to hotword detector
        await self.audio_manager.stop_recording()

        if await self.websocket_client.connect():
            self.state_machine.transition_to(ClientState.ACTIVE_SESSION)
            
            # Send hotword detected message
            await self.websocket_client.send_message({"type": "hotword_detected"})
            
            # Start streaming microphone audio to the server
            await self.audio_manager.start_recording(
                lambda audio_chunk: asyncio.create_task(self.websocket_client.send_audio(audio_chunk))
            )
        else:
            logger.error("Failed to connect to server. Returning to listening.")
            await self.end_session()

    def on_audio_received(self, audio_chunk: bytes):
        """Callback for when TTS audio is received from the server."""
        asyncio.create_task(self.audio_manager.play_audio_chunk(audio_chunk))

    def on_connection_lost(self):
        """Callback for when the WebSocket connection is lost."""
        logger.warning("Connection lost. Ending session.")
        asyncio.create_task(self.end_session())

    async def end_session(self):
        """Cleans up an active session and returns to listening."""
        await self.audio_manager.stop_recording()
        await self.websocket_client.disconnect()
        
        # Wait for any lingering playback to finish
        await self.audio_manager.wait_for_playback_completion()

        logger.info("Session ended. Returning to listening for hotword.")
        self.state_machine.transition_to(ClientState.LISTENING_FOR_HOTWORD)
        await self.audio_manager.start_recording(self.hotword_detector.process_audio)