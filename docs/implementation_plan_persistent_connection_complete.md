# Complete Implementation Plan: Persistent WebSocket Connection

This document provides a comprehensive implementation guide that redesigns the WebSocket client APIs from scratch for persistent connections.

## Overview

We're completely redesigning the WebSocket client to be purpose-built for persistent connections, eliminating the old on-demand connection model entirely.

**Benefits:**
- **Eliminated Latency:** No connection setup after hotword detection
- **Better Reliability:** Automatic reconnection with exponential backoff
- **Session Resilience:** Can survive temporary network hiccups
- **Future-Proof:** Enables push notifications and real-time updates
- ...

**Issues with existing approach:** 
The current architecture has issues, some of which are e.g.
- Connection latency (~50-500ms) after hotword detection affects user experience
- Client state machine tightly couples connection establishment with session management and makes state management complex
- Server assumes short-lived connections with full resource cleanup on disconnect
- No resilience against temporary network issues
- ...

_(future things to consider: push notifications / real time updates should be standardized, parts of the server should be decoupled, and the error handling, state handling and edge cases must be rock solid so that the potential for desynchronization, hangs etc. is minimized)_  


## Phase 1: Complete WebSocketClient Redesign

### 1.1. New `pi_software/src/services/websocket_client.py`

**Complete new implementation:**

```python
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
```

## Phase 2: Simplified State Machine

### 2.1. Updated `pi_software/src/core/state_machine.py`

**Remove the `CONNECTING_TO_SERVER` state entirely:**

```python
class ClientState(Enum):
    """Simplified client states for persistent connection model."""
    IDLE = auto()
    LISTENING_FOR_HOTWORD = auto()
    HOTWORD_DETECTED = auto()
    ACTIVE_SESSION = auto()

class StateMachine:
    def __init__(self, initial_state: ClientState = ClientState.IDLE):
        self._state = initial_state
        self._transitions: Dict[ClientState, Set[ClientState]] = {
            ClientState.IDLE: {ClientState.LISTENING_FOR_HOTWORD},
            ClientState.LISTENING_FOR_HOTWORD: {ClientState.HOTWORD_DETECTED, ClientState.IDLE},
            ClientState.HOTWORD_DETECTED: {ClientState.ACTIVE_SESSION, ClientState.LISTENING_FOR_HOTWORD},
            ClientState.ACTIVE_SESSION: {ClientState.LISTENING_FOR_HOTWORD, ClientState.IDLE}
        }
        # ... rest remains the same
```

## Phase 3: Complete SessionManager Redesign

### 3.1. New `pi_software/src/services/session_manager.py`

**Complete rewrite for persistent connection model:**

```python
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
        if self.state_machine.transition_to(ClientState.HOTWORD_DETECTED):
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
        self.state_machine.transition_to(ClientState.ACTIVE_SESSION)
        
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
```

## Phase 4: Updated Main Application

### 4.1. Updated `pi_software/src/main.py`

```python
"""
Main entry point for GemiTARS Pi Client
"""

import asyncio
from .core.state_machine import StateMachine
from .audio.pc_audio_manager import PCAudioManager
from .core.hotword_detector import HotwordDetector
from .services.websocket_client import PersistentWebSocketClient
from .services.session_manager import SessionManager
from .utils.logger import setup_logger

logger = setup_logger(__name__)

async def main():
    """Main application entry point."""
    logger.info("Starting GemiTARS Pi Client...")
    
    # Initialize components
    state_machine = StateMachine()
    audio_manager = PCAudioManager()
    hotword_detector = HotwordDetector()
    websocket_client = PersistentWebSocketClient()
    
    # Get event loop
    loop = asyncio.get_running_loop()
    
    # Create session manager
    session_manager = SessionManager(
        state_machine=state_machine,
        audio_manager=audio_manager,
        hotword_detector=hotword_detector,
        websocket_client=websocket_client,
        loop=loop
    )
    
    try:
        # Start the session manager (establishes persistent connection)
        await session_manager.start()
        
        logger.info("GemiTARS Pi Client ready. Say 'Hey TARS' to activate.")
        
        # Keep running until interrupted
        await asyncio.Event().wait()
        
    except asyncio.CancelledError:
        logger.info("Application cancelled")
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
    finally:
        await session_manager.shutdown()
        logger.info("GemiTARS Pi Client shutdown complete")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Goodbye!")
```

## Summary of Key Changes

1. **Complete API Redesign**: New `PersistentWebSocketClient` designed from scratch for persistent connections
2. **Simplified State Machine**: Removed `CONNECTING_TO_SERVER` state entirely
3. **Clean Session Management**: Connection and session concerns completely separated
4. **Robust Error Handling**: Comprehensive reconnection logic with exponential backoff
5. **Clear Lifecycle**: Start connection once, maintain it throughout app lifetime

This implementation provides a clean, robust foundation for persistent WebSocket connections with automatic reconnection and proper error handling.