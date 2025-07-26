"""
Persistent WebSocket Client for GemiTARS
"""

import asyncio
import json
import websockets
import random
from enum import Enum
from typing import Callable, Optional, Any

from ..config.settings import Config
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

class ConnectionStatus(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting" 
    CONNECTED = "connected"
    SHUTTING_DOWN = "shutting_down"

class PersistentWebSocketClient:
    """
    Manages a persistent WebSocket connection with automatic reconnection.
    
    This client establishes connection on startup and maintains it throughout
    the application lifecycle, automatically reconnecting on connection loss.
    """

    def __init__(self):
        self.uri = Config.SERVER_URL
        self.status = ConnectionStatus.DISCONNECTED
        
        # Connection management
        self._connection: Optional[Any] = None
        self._connection_manager_task: Optional[asyncio.Task] = None
        self._receive_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        
        # Reconnection logic
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 10
        self._base_backoff_delay = 1.0
        self._max_backoff_delay = 60.0
        
        # Callbacks
        self.on_connected: Optional[Callable[[], None]] = None
        self.on_disconnected: Optional[Callable[[], None]] = None
        self.on_audio_received: Optional[Callable[[bytes], None]] = None
        self.on_control_message_received: Optional[Callable[[dict], None]] = None

    async def start(self):
        """Start the persistent connection manager."""
        if self._connection_manager_task is None:
            logger.info("Starting persistent WebSocket client...")
            self._connection_manager_task = asyncio.create_task(self._connection_manager())

    async def shutdown(self):
        """Gracefully shutdown the client."""
        logger.info("Shutting down WebSocket client...")
        self.status = ConnectionStatus.SHUTTING_DOWN
        
        # Cancel connection manager
        if self._connection_manager_task:
            self._connection_manager_task.cancel()
            try:
                await self._connection_manager_task
            except asyncio.CancelledError:
                pass
        
        # Close connection
        await self._cleanup_connection()
        logger.info("WebSocket client shutdown complete.")

    def is_connected(self) -> bool:
        """Check if currently connected to server."""
        return self.status == ConnectionStatus.CONNECTED

    async def send_message(self, message: dict):
        """Send a JSON control message to the server."""
        if not self.is_connected() or not self._connection:
            logger.warning(f"Cannot send message - not connected (status: {self.status.value})")
            return
        
        try:
            await self._connection.send(json.dumps(message))
        except websockets.exceptions.ConnectionClosed:
            logger.warning("Failed to send message: connection closed")
            # Connection manager will handle reconnection
        except Exception as e:
            logger.error(f"Failed to send message: {e}")

    async def send_audio(self, audio_data: bytes):
        """Send binary audio data to the server."""
        if not self.is_connected() or not self._connection:
            logger.warning("Cannot send audio - not connected")
            return
            
        try:
            await self._connection.send(audio_data)
        except websockets.exceptions.ConnectionClosed:
            logger.warning("Failed to send audio: connection closed")
            # Connection manager will handle reconnection
        except Exception as e:
            logger.error(f"Failed to send audio: {e}")

    async def _connection_manager(self):
        """Main connection management loop with automatic reconnection."""
        while self.status != ConnectionStatus.SHUTTING_DOWN:
            try:
                await self._establish_connection()
                
                # Wait for connection to close
                await self._connection_monitor()
                
            except Exception as e:
                logger.error(f"Connection manager error: {e}")
            finally:
                await self._cleanup_connection()
                
                # Don't reconnect if shutting down
                if self.status == ConnectionStatus.SHUTTING_DOWN:
                    break
                
                # Wait before reconnecting
                delay = self._calculate_backoff_delay()
                logger.info(f"Reconnecting in {delay:.1f} seconds...")
                await asyncio.sleep(delay)

    async def _establish_connection(self):
        """Establish WebSocket connection."""
        self.status = ConnectionStatus.CONNECTING
        logger.info(f"Connecting to {self.uri}...")
        
        try:
            self._connection = await websockets.connect(self.uri)
            self.status = ConnectionStatus.CONNECTED
            self._reconnect_attempts = 0
            
            logger.info("Connected to server")
            if self.on_connected:
                self.on_connected()
            
            # Start background tasks
            self._receive_task = asyncio.create_task(self._receive_loop())
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            
        except Exception as e:
            logger.warning(f"Connection failed: {e}")
            self.status = ConnectionStatus.DISCONNECTED
            raise

    async def _connection_monitor(self):
        """Monitor connection and wait for it to close."""
        if not self._receive_task or not self._heartbeat_task:
            return
        
        # Wait for either task to complete (indicates connection issue)
        done, pending = await asyncio.wait(
            [self._receive_task, self._heartbeat_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # Cancel remaining tasks
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    async def _receive_loop(self):
        """Continuously receive messages from server."""
        if not self._connection:
            return
            
        try:
            async for message in self._connection:
                if isinstance(message, bytes):
                    if self.on_audio_received:
                        self.on_audio_received(message)
                elif isinstance(message, str):
                    if self.on_control_message_received:
                        try:
                            self.on_control_message_received(json.loads(message))
                        except json.JSONDecodeError:
                            logger.warning(f"Received invalid JSON: {message}")
        except websockets.exceptions.ConnectionClosed:
            logger.info("Server closed connection")
        except Exception as e:
            logger.error(f"Receive loop error: {e}")

    async def _heartbeat_loop(self):
        """Send periodic heartbeat to keep connection alive."""
        while self.status == ConnectionStatus.CONNECTED:
            try:
                await asyncio.sleep(30)  # Heartbeat every 30 seconds
                if self._connection and self.status == ConnectionStatus.CONNECTED:
                    await self._connection.ping()
            except websockets.exceptions.ConnectionClosed:
                logger.debug("Heartbeat failed: connection closed")
                break
            except Exception as e:
                logger.warning(f"Heartbeat error: {e}")
                break

    async def _cleanup_connection(self):
        """Clean up connection and tasks."""
        old_status = self.status
        self.status = ConnectionStatus.DISCONNECTED
        
        # Cancel tasks
        for task in [self._receive_task, self._heartbeat_task]:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Close connection
        if self._connection:
            try:
                await self._connection.close()
            except:
                pass
            self._connection = None
        
        # Reset tasks
        self._receive_task = None
        self._heartbeat_task = None
        
        # Notify disconnection (but not during shutdown)
        if old_status == ConnectionStatus.CONNECTED and self.on_disconnected:
            self.on_disconnected()

    def _calculate_backoff_delay(self) -> float:
        """Calculate exponential backoff delay."""
        self._reconnect_attempts += 1
        delay = min(
            self._base_backoff_delay * (2 ** self._reconnect_attempts) + random.uniform(0, 1),
            self._max_backoff_delay
        )
        return delay