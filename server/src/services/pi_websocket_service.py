"""
Pi Websocket Service: Concrete implementation for Raspberry Pi communication.
"""

import asyncio
import json
import socket
from typing import Optional, Any
import websockets
from websockets.exceptions import ConnectionClosed

from .pi_interface import PiInterfaceService, HotwordCallback, AudioCallback, DisconnectCallback
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

class PiWebsocketService(PiInterfaceService):
    """
    Manages WebSocket communication with a single Raspberry Pi client.
    """
    
    # TODO: Move the port to a env/config/settings file!!
    def __init__(self, host: str = "0.0.0.0", port: int = 7456):
        self.host = host
        self.port = port
        self.server_task: Optional[asyncio.Task] = None
        self.client: Optional[Any] = None
        self.playback_queue: asyncio.Queue = asyncio.Queue()
        self.playback_complete_event: asyncio.Event = asyncio.Event()

        # Callbacks to the main assistant
        self.hotword_callback: Optional[HotwordCallback] = None
        self.audio_callback: Optional[AudioCallback] = None
        self.disconnect_callback: Optional[DisconnectCallback] = None

    def _get_local_ip(self) -> str:
        """Retrieves the local IP address of the machine."""
        try:
            # Connect to an external server to determine the local IP
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except Exception:
            return "127.0.0.1"

    async def initialize(
        self,
        hotword_callback: HotwordCallback,
        audio_callback: AudioCallback,
        disconnect_callback: Optional[DisconnectCallback] = None
    ) -> None:
        self.hotword_callback = hotword_callback
        self.audio_callback = audio_callback
        self.disconnect_callback = disconnect_callback
        
        local_ip = self._get_local_ip()
        logger.info(f"Starting WebSocket server on {self.host}:{self.port}")
        logger.info(f"Connect your Pi to: ws://{local_ip}:{self.port}")
        
        try:
            server = await websockets.serve(self._connection_handler, self.host, self.port)
            await server.wait_closed()
        except OSError as e:
            logger.error(f"Failed to start WebSocket server: {e}")
            logger.error("This might be due to the port being in use or insufficient permissions.")
            raise

    async def _connection_handler(self, websocket: Any):
        """Handle a new client connection."""
        if self.client is not None:
            logger.warning("New client tried to connect, but one is already active. Rejecting.")
            await websocket.close(1013, "Server busy, another client is connected.")
            return

        self.client = websocket
        logger.info(f"Client connected from {websocket.remote_address}")

        # Start the audio playback task for this client
        playback_task = asyncio.create_task(self._audio_playback_handler())

        try:
            await self._message_handler()
        except ConnectionClosed:
            logger.info("Client connection closed.")
        except Exception as e:
            logger.error(f"An error occurred in the connection handler: {e}", exc_info=True)
        finally:
            self.client = None
            playback_task.cancel()
            # Ensure queue is cleared for the next connection
            while not self.playback_queue.empty():
                self.playback_queue.get_nowait()
            
            # Notify the main assistant that the client has disconnected
            if self.disconnect_callback:
                asyncio.create_task(self.disconnect_callback()) # type: ignore

            logger.info("Client disconnected and resources cleaned up.")

    async def _message_handler(self):
        """Process incoming messages from the connected client."""
        if not self.client:
            return
            
        async for message in self.client:
            if isinstance(message, str):
                try:
                    command = json.loads(message)
                    if command.get("type") == "hotword_detected" and self.hotword_callback:
                        asyncio.create_task(self.hotword_callback()) # type: ignore
                    elif command.get("type") == "playback_complete":
                        logger.debug("Received playback complete signal from client.")
                        self.playback_complete_event.set()
                except json.JSONDecodeError:
                    logger.warning(f"Received invalid JSON from client: {message}")

            elif isinstance(message, bytes) and self.audio_callback:
                self.audio_callback(message)

    async def _audio_playback_handler(self):
        """Continuously send queued audio chunks to the client."""
        while self.client:
            try:
                audio_chunk = await self.playback_queue.get()
                await self.client.send(audio_chunk)
                self.playback_queue.task_done()
            except ConnectionClosed:
                logger.warning("Playback handler failed: Connection closed.")
                break
            except asyncio.CancelledError:
                break

    async def shutdown(self) -> None:
        logger.info("Shutting down WebSocket service...")
        if self.client:
            await self.client.close(1001, "Server is shutting down.")
        if self.server_task:
            self.server_task.cancel()
            try:
                await self.server_task
            except asyncio.CancelledError:
                pass
        logger.info("WebSocket service shut down.")

    async def play_audio_chunk(self, audio_data: bytes) -> None:
        if self.client:
            await self.playback_queue.put(audio_data)

    async def wait_for_playback_completion(self) -> None:
        if self.client:
            logger.debug("Waiting for playback completion signal...")
            await self.playback_complete_event.wait()

    async def clear_playback_event(self) -> None:
        """Clear the playback complete event."""
        self.playback_complete_event.clear()

    def is_client_connected(self) -> bool:
        return self.client is not None

    async def send_control_message(self, message: dict) -> None:
        if self.client:
            try:
                await self.client.send(json.dumps(message))
            except ConnectionClosed:
                logger.warning("Failed to send control message: connection closed.")