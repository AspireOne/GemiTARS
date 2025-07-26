# Revised Architecture Proposal: Persistent WebSocket Connection

After analyzing the current implementation, this revised proposal addresses the complexities and challenges of implementing persistent WebSocket connections in the TARS system.

## 1. Current Architecture Issues

The current architecture has the following problems:
- Connection latency (~50-500ms) after hotword detection affects user experience
- Client state machine tightly couples connection establishment with session management
- Server assumes short-lived connections with full resource cleanup on disconnect
- No resilience against temporary network issues

## 2. Revised Proposed Changes

### Pi Client Changes

#### 2.1 WebSocketClient Redesign (`websocket_client.py`)

**New Architecture:**
```python
class WebSocketClient:
    def __init__(self):
        self._connection_manager_task = None
        self._connection_status = ConnectionStatus.DISCONNECTED
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 5
        self._base_backoff_delay = 1.0  # seconds
        
    async def start_persistent_connection(self):
        """Start the persistent connection management loop"""
        
    async def _connection_manager(self):
        """Manages connection lifecycle with exponential backoff"""
        
    async def _heartbeat_handler(self):
        """Handles ping/pong to detect connection health"""
        
    async def shutdown(self):
        """Gracefully close the persistent connection on app shutdown"""
        if self._connection_manager_task:
            self._connection_manager_task.cancel()
        await self.disconnect()
```

**Key Changes:**
- Connection management runs as a background task
- Exponential backoff reconnection (1s, 2s, 4s, 8s, 16s max)
- Built-in heartbeat every 30 seconds
- Connection status tracking separate from session state

#### 2.2 Simplified Client State Machine

**New States:**
- `IDLE` → `LISTENING_FOR_HOTWORD` → `HOTWORD_DETECTED` → `ACTIVE_SESSION`

**Removed States:**
- `CONNECTING_TO_SERVER` (connection is always managed separately)

#### 2.3 SessionManager Refactor (`session_manager.py`)

**Key Changes:**
```python
async def start(self):
    """Start both connection manager and hotword detection"""
    await self.websocket_client.start_persistent_connection()
    await self._start_hotword_detection()

async def handle_active_session(self):
    """Simplified - just send hotword message and start audio streaming"""
    if not self.websocket_client.is_connected():
        logger.warning("Cannot start session: not connected to server")
        return
    
    await self.websocket_client.send_message({"type": "hotword_detected"})
    # ... rest of session logic

async def end_session(self):
    """CRITICAL: Remove disconnect() call to maintain persistent connection"""
    await self.audio_manager.stop_recording()
    # REMOVED: await self.websocket_client.disconnect()  # DON'T disconnect!
    
    # Wait for any lingering playback to finish
    await self.audio_manager.wait_for_playback_completion()
    
    logger.info("Session ended. Connection remains active for next hotword.")
    self.state_machine.transition_to(ClientState.LISTENING_FOR_HOTWORD)
    await self.audio_manager.start_recording(self.hotword_detector.process_audio)

async def shutdown(self):
    """Gracefully shutdown the entire client application"""
    logger.info("Shutting down client application...")
    await self.audio_manager.stop_recording()
    await self.websocket_client.shutdown()  # Only disconnect on app shutdown
```

### Server Changes

#### 2.4 PiWebsocketService Redesign (`pi_websocket_service.py`)

**Key Changes:**
- Preserve playback queue across reconnections for ongoing sessions
- Implement connection health monitoring
- Graceful handling of temporary disconnects during active sessions

```python
class PiWebsocketService:
    def __init__(self):
        self.session_state = SessionState.IDLE  # Track session separate from connection
        self.pending_audio_queue = []  # Buffer audio during disconnects
        
    async def _connection_handler(self, websocket):
        """Handle reconnections gracefully"""
        # If client reconnects during active session, restore context
        if self.session_state == SessionState.ACTIVE:
            await self._restore_session_context(websocket)
```

#### 2.5 TARSAssistant Updates (`main.py`)

**Key Changes:**
- Distinguish between connection loss and session end
- Implement session timeout separate from connection timeout

## 3. Critical Implementation Requirements

### 3.1 Essential Changes for Always-On Connection

**CRITICAL:** The following changes are mandatory for achieving true persistent connections:

1. **Remove Disconnect on Session End**: The current `SessionManager.end_session()` calls `websocket_client.disconnect()`. This **MUST** be removed or the connection will close after every conversation.

2. **Add Graceful Shutdown**: Both `WebSocketClient` and `SessionManager` need `shutdown()` methods that only disconnect when the application is terminating.

3. **Connection vs Session State**: The implementation must clearly distinguish between:
   - Connection state (should persist across sessions)
   - Session state (starts/ends with each conversation)

### 3.2 Validation Checklist

Before deployment, verify:
- [ ] Connection establishes on client startup
- [ ] Connection survives multiple conversation sessions
- [ ] Automatic reconnection works during network interruptions
- [ ] Zero latency when starting conversations (no connection setup)
- [ ] Graceful shutdown on application termination

## 4. Implementation Phases

### Phase 1: Connection Management
1. Implement persistent connection loop in WebSocketClient
2. Add heartbeat mechanism
3. Implement exponential backoff reconnection

### Phase 2: State Machine Refactor
1. Remove CONNECTING_TO_SERVER state
2. Update SessionManager to work with persistent connections
3. Update server to handle reconnections gracefully

### Phase 3: Session Resilience
1. Implement session restoration on reconnect
2. Add audio buffering during disconnects
3. Add connection health monitoring

## 4. Benefits and Risks

### Benefits
- **Eliminated Latency:** No connection setup after hotword detection
- **Better Reliability:** Automatic reconnection with exponential backoff
- **Session Resilience:** Can survive temporary network hiccups
- **Future-Proof:** Enables push notifications and real-time updates

### Risks
- **Increased Complexity:** More complex connection and session management
- **Resource Usage:** Always-on connections consume more resources
- **State Synchronization:** Risk of client/server state mismatches
- **Testing Complexity:** More edge cases to test (reconnection scenarios)

## 5. Migration Strategy

### Backwards Compatibility
- Maintain existing message protocol
- Server should support both persistent and non-persistent clients initially
- Gradual rollout with feature flags

### Testing Strategy
- Network simulation testing (disconnects, reconnects, latency)
- Long-running stability tests
- Session interruption recovery tests

## 6. Conclusion

This revised proposal addresses the architectural challenges identified in the current implementation. The phased approach reduces risk while delivering the latency improvements that motivated this change. The key insight is that connection management and session management should be decoupled, allowing for more robust and responsive operation.

The implementation complexity is justified by the significant user experience improvements and the foundation it provides for future features.