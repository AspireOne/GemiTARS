"""
WebSocket Client for GemiTARS
"""

import asyncio
import json
import websockets
from typing import Callable, Optional, Any

from ..config.settings import Config
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

class WebSocketClient:
    """
    Manages the WebSocket connection to the TARS server.
    """

    def __init__(self):
        self.uri = Config.SERVER_URL
        self.connection: Optional[Any] = None
        self.is_connected = False
        self.on_audio_received: Optional[Callable[[bytes], None]] = None
        self.on_connection_lost: Optional[Callable[[], None]] = None
        self._receive_task: Optional[asyncio.Task] = None

    async def connect(self) -> bool:
        """
        Establishes a connection to the WebSocket server.
        
        Returns:
            True if the connection was successful, False otherwise.
        """
        if self.is_connected:
            logger.warning("Already connected.")
            return True
        
        logger.info(f"Attempting to connect to server at {self.uri}...")
        try:
            self.connection = await websockets.connect(self.uri)
            self.is_connected = True
            self._receive_task = asyncio.create_task(self._receive_loop())
            logger.info("Successfully connected to server.")
            return True
        except (websockets.exceptions.ConnectionClosedError, OSError) as e:
            logger.error(f"Failed to connect to server: {e}")
            self.is_connected = False
            return False

    async def _receive_loop(self):
        """Continuously listens for messages from the server."""
        if not self.connection:
            return
            
        try:
            async for message in self.connection:
                if isinstance(message, bytes):
                    if self.on_audio_received:
                        self.on_audio_received(message)
                # Add handling for JSON control messages from server if needed later
        except websockets.exceptions.ConnectionClosed:
            logger.warning("Connection to server was closed.")
            self.is_connected = False
            if self.on_connection_lost:
                self.on_connection_lost()

    async def send_message(self, message: dict):
        """Sends a JSON message to the server."""
        if not self.is_connected or not self.connection:
            logger.error("Cannot send message: not connected.")
            return
        
        try:
            await self.connection.send(json.dumps(message))
        except websockets.exceptions.ConnectionClosed:
            logger.error("Failed to send message: connection closed.")
            self.is_connected = False

    async def send_audio(self, audio_data: bytes):
        """Sends a binary audio chunk to the server."""
        if not self.is_connected or not self.connection:
            logger.error("Cannot send audio: not connected.")
            return
            
        try:
            await self.connection.send(audio_data)
        except websockets.exceptions.ConnectionClosed:
            logger.error("Failed to send audio: connection closed.")
            self.is_connected = False

    async def disconnect(self):
        """Closes the WebSocket connection."""
        if self.is_connected and self.connection:
            self.is_connected = False
            if self._receive_task:
                self._receive_task.cancel()
            await self.connection.close()
            self.connection = None
            logger.info("Disconnected from server.")