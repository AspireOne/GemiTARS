# Implementation Plan: Persistent WebSocket Connection

This document provides a detailed, step-by-step guide to implementing the architectural changes outlined in the revised proposal for a persistent WebSocket connection.

## Phase 1: Pi Client Refactoring

### 1.1. `pi_software/src/services/websocket_client.py`

This file requires the most significant changes. The `WebSocketClient` will be transformed from a simple connection wrapper into a robust connection manager.

**Summary of Changes:**
-   Introduce a connection status enum.
-   Implement a main `_connection_manager` task that runs in the background.
-   Add exponential backoff for reconnection attempts.
-   Implement a `_heartbeat` task to ensure the connection is alive.
-   Add `start()` and `shutdown()` methods to control the lifecycle.

**Detailed Implementation:**

```python
# Add near the top of the file
from enum import Enum
import random

class ConnectionStatus(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"

class WebSocketClient:
    def __init__(self):
        self.uri = Config.SERVER_URL
        self.connection: Optional[Any] = None
        self.status = ConnectionStatus.DISCONNECTED
        self.on_audio_received: Optional[Callable[[bytes], None]] = None
        self.on_connection_lost: Optional[Callable[[], None]] = None
        self.on_control_message_received: Optional[Callable[[dict], None]] = None
        
        self._receive_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._manager_task: Optional[asyncio.Task] = None
        self._reconnect_attempts = 0

    async def start(self):
        """Start the connection manager as a background task."""
        if not self._manager_task:
            self._manager_task = asyncio.create_task(self._connection_manager())

    async def shutdown(self):
        """Gracefully shut down the connection and all background tasks."""
        if self._manager_task:
            self._manager_task.cancel()
        if self.connection:
            await self.connection.close()
        logger.info("WebSocket client shut down.")

    async def _connection_manager(self):
        """Maintains the connection, with exponential backoff for retries."""
        while True:
            try:
                self.status = ConnectionStatus.CONNECTING
                logger.info(f"Attempting to connect to server at {self.uri}...")
                
                # The actual connection logic
                async with websockets.connect(self.uri) as websocket:
                    self.connection = websocket
                    self.status = ConnectionStatus.CONNECTED
                    self._reconnect_attempts = 0
                    logger.info("Successfully connected to server.")

                    # Start listener and heartbeat
                    self._receive_task = asyncio.create_task(self._receive_loop())
                    self._heartbeat_task = asyncio.create_task(self._heartbeat())
                    
                    # Wait for either task to complete (which indicates a disconnect)
                    await asyncio.wait(
                        [self._receive_task, self._heartbeat_task],
                        return_when=asyncio.FIRST_COMPLETED,
                    )
            
            except (websockets.exceptions.ConnectionClosedError, OSError) as e:
                logger.warning(f"Connection failed or lost: {e}")

            finally:
                self.status = ConnectionStatus.DISCONNECTED
                if self.on_connection_lost:
                    self.on_connection_lost()

                # Cancel tasks if they are still running
                if self._receive_task and not self._receive_task.done():
                    self._receive_task.cancel()
                if self._heartbeat_task and not self._heartbeat_task.done():
                    self._heartbeat_task.cancel()

                # Exponential backoff logic
                self._reconnect_attempts += 1
                delay = min(2 ** self._reconnect_attempts + random.uniform(0, 1), 60)
                logger.info(f"Will attempt to reconnect in {delay:.2f} seconds...")
                await asyncio.sleep(delay)

    async def _heartbeat(self):
        """Sends a ping every 30 seconds to keep the connection alive."""
        while self.status == ConnectionStatus.CONNECTED:
            try:
                await self.connection.ping()
                await asyncio.sleep(30)
            except websockets.exceptions.ConnectionClosed:
                logger.warning("Heartbeat failed: connection closed.")
                break
    
    # _receive_loop, send_message, and send_audio methods remain largely the same,
    # but should check self.status instead of self.is_connected.
```

### 1.2. `pi_software/src/services/session_manager.py`

**Summary of Changes:**
-   Start the `WebSocketClient` at application startup.
-   Remove connection logic from `handle_active_session`.
-   **Crucially, remove the `disconnect()` call from `end_session`.**
-   Add a `shutdown` method.

**Detailed Implementation:**

```python
class SessionManager:
    # ... __init__ remains the same ...

    async def start(self):
        """Starts the WebSocket client and then begins listening for the hotword."""
        logger.info("Session manager starting...")
        await self.websocket_client.start()  # Start the persistent connection
        self.state_machine.transition_to(ClientState.LISTENING_FOR_HOTWORD)
        await self.audio_manager.start_recording(self.hotword_detector.process_audio)

    async def handle_active_session(self):
        """Manages the flow of an active conversation session."""
        # Connection is already handled, just check status
        if self.websocket_client.status != ConnectionStatus.CONNECTED:
            logger.error("Cannot start session: not connected to server.")
            # Optionally, provide user feedback (e.g., a sound)
            return

        self.state_machine.transition_to(ClientState.ACTIVE_SESSION)
        await self.websocket_client.send_message({"type": "hotword_detected"})
        # ... rest of the method ...

    async def end_session(self):
        """Cleans up an active session and returns to listening."""
        await self.audio_manager.stop_recording()
        
        # CRITICAL: DO NOT DISCONNECT THE WEBSOCKET
        # await self.websocket_client.disconnect() # This line is removed.
        
        await self.audio_manager.wait_for_playback_completion()
        logger.info("Session ended. Connection remains active.")
        self.state_machine.transition_to(ClientState.LISTENING_FOR_HOTWORD)
        await self.audio_manager.start_recording(self.hotword_detector.process_audio)

    async def shutdown(self):
        """Gracefully shuts down all components."""
        logger.info("Shutting down session manager...")
        await self.audio_manager.stop_recording()
        await self.websocket_client.shutdown()
```

### 1.3. `pi_software/src/main.py`

**Summary of Changes:**
-   Ensure the main application loop handles `KeyboardInterrupt` gracefully by calling the new `shutdown` method.

**Detailed Implementation:**

```python
async def main():
    # ... setup ...
    session_manager = SessionManager(...)
    
    try:
        await session_manager.start()
        # Keep the main task running
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        logger.info("Main task cancelled.")
    finally:
        await session_manager.shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user.")
```

## Phase 2: Server Refactoring

The server-side changes are less extensive but are crucial for supporting persistent clients gracefully.

### 2.1. `server/src/services/pi_websocket_service.py`

**Summary of Changes:**
-   Modify `_connection_handler` to be less destructive on client disconnect. It should clean up session-specific resources but not assume the server needs to reset completely.

**Detailed Implementation:**

```python
class PiWebsocketService:
    # ... __init__ ...

    async def _connection_handler(self, websocket: Any):
        """Handle a new or returning client connection."""
        if self.client is not None:
            logger.warning("A client is already connected. Closing the old connection.")
            await self.client.close(1013, "New connection replacing this one.")
        
        self.client = websocket
        logger.info(f"Client connected from {websocket.remote_address}")

        # The disconnect_callback should now handle session cleanup, not server cleanup.
        # The main assistant can decide if a full passive mode transition is needed.
        try:
            await self._message_handler()
        except ConnectionClosed:
            logger.info(f"Client {websocket.remote_address} disconnected.")
        finally:
            self.client = None
            if self.disconnect_callback:
                # This callback now signals a temporary disconnect, not a fatal one.
                asyncio.create_task(self.disconnect_callback())
```

### 2.2. `server/src/main.py`

**Summary of Changes:**
-   The `_on_client_disconnected` callback needs to be more nuanced. It should only reset the conversation state if a conversation was active.

**Detailed Implementation:**

```python
class TARSAssistant:
    # ...

    async def _on_client_disconnected(self) -> None:
        """Callback for when the client disconnects."""
        logger.warning("Client disconnected.")
        if self.conversation_manager.state != ConversationState.PASSIVE:
            logger.info("Client disconnected during an active session. Ending session and returning to passive mode.")
            await self._enter_passive_mode()
        else:
            logger.info("Client disconnected while in passive mode. Awaiting reconnection.")
```

This detailed plan provides a clear path to refactoring the application. Once you approve this plan, I can proceed to the implementation phase.