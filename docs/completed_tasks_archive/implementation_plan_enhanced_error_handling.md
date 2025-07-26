# Implementation Plan: Enhanced Error Handling

## Overview
This document outlines the implementation of comprehensive error handling and recovery mechanisms to improve system reliability and prevent inconsistent states.

## Identified Error Handling Gaps

### 1. SessionManager Issues
- **Problem**: No exception handling in `start_session()` around critical operations
- **Impact**: Failures can leave system in inconsistent state (e.g., wrong state, audio not properly configured)
- **Examples**: WebSocket send failures, audio manager failures, state transition failures

### 2. Audio Manager Issues  
- **Problem**: `start_recording()` doesn't return success/failure status
- **Impact**: Callers can't detect when audio operations fail
- **Examples**: Microphone device failures, sounddevice initialization errors

### 3. WebSocket Client Issues
- **Problem**: Send operations fail silently without notifying callers
- **Impact**: SessionManager doesn't know when messages fail to send
- **Examples**: Connection drops between send attempts

### 4. State Recovery Issues
- **Problem**: No centralized recovery mechanisms when errors occur
- **Impact**: System can get stuck in incorrect states
- **Examples**: Failed session start leaves system in ACTIVE_SESSION but no actual session

## Enhanced Error Handling Design

### 1. Error Recovery in SessionManager

#### Add Comprehensive Error Handling to start_session()
```python
async def start_session(self):
    """Start an active conversation session with comprehensive error handling."""
    try:
        # Check connection first
        if not self.websocket_client.is_connected():
            logger.warning("Cannot start session: not connected to server")
            return False
        
        # Attempt state transition
        if not self.state_machine.transition_to(ClientState.ACTIVE_SESSION):
            logger.error("Failed to transition to ACTIVE_SESSION")
            return False
        
        # Stop hotword detection safely
        try:
            await self.audio_manager.stop_recording()
        except Exception as e:
            logger.error(f"Failed to stop hotword recording: {e}")
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
        
        # Start session audio recording
        try:
            success = await self.audio_manager.start_recording(
                lambda audio_chunk: self._safe_send_audio(audio_chunk)
            )
            if not success:
                logger.error("Failed to start session audio recording")
                await self._recover_to_listening_state()
                return False
        except Exception as e:
            logger.error(f"Error starting session recording: {e}")
            await self._recover_to_listening_state()
            return False
        
        logger.info("Session started successfully")
        return True
        
    except Exception as e:
        logger.error(f"Unexpected error starting session: {e}", exc_info=True)
        await self._recover_to_listening_state()
        return False
```

#### Add Recovery Method
```python
async def _recover_to_listening_state(self):
    """Recover to a consistent listening state after errors."""
    logger.info("Recovering to listening state...")
    
    try:
        # Ensure audio is stopped
        await self.audio_manager.stop_recording()
        
        # Return to listening state
        await self._start_hotword_listening()
        
        logger.info("Successfully recovered to listening state")
        
    except Exception as e:
        logger.error(f"Error during state recovery: {e}", exc_info=True)
        # If recovery fails, try transitioning to IDLE
        self.state_machine.transition_to(ClientState.IDLE)
```

#### Add Safe Audio Sending
```python
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
```

### 2. Enhanced Audio Manager Error Handling

#### Modify start_recording() to Return Status
```python
async def start_recording(self, callback: Callable[[bytes], Any]) -> bool:
    """Start recording with proper error handling and status return."""
    if self.input_stream:
        logger.warning("Microphone stream already running.")
        return True  # Already recording is considered success
    
    try:
        self.audio_callback = callback
        
        self.input_stream = sd.InputStream(
            samplerate=Config.AUDIO_SAMPLE_RATE,
            blocksize=Config.AUDIO_BLOCK_SIZE,
            dtype=Config.AUDIO_DTYPE,
            channels=Config.AUDIO_CHANNELS,
            callback=self._mic_callback
        )
        
        self.input_stream.start()
        logger.info("Microphone stream started successfully.")
        return True
        
    except Exception as e:
        logger.error(f"Failed to start microphone stream: {e}", exc_info=True)
        # Ensure clean state
        self.input_stream = None
        self.audio_callback = None
        return False
```

#### Add Audio Device Health Check
```python
async def check_audio_health(self) -> bool:
    """Check if audio devices are healthy and available."""
    try:
        # Query devices to ensure they're still available
        devices = sd.query_devices()
        
        # Check if current devices are still available
        default_input = sd.default.device[0]
        default_output = sd.default.device[1]
        
        if default_input is None or default_output is None:
            logger.error("Default audio devices not available")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Audio health check failed: {e}", exc_info=True)
        return False
```

### 3. Enhanced WebSocket Client Error Handling

#### Add Confirmed Message Sending
```python
async def send_message_with_confirmation(self, message: dict, timeout: float = 5.0) -> bool:
    """Send a message and confirm it was sent successfully."""
    if not self.is_connected() or not self._connection:
        logger.warning(f"Cannot send message - not connected (status: {self.status.value})")
        return False
    
    try:
        await asyncio.wait_for(
            self._connection.send(json.dumps(message)), 
            timeout=timeout
        )
        return True
        
    except asyncio.TimeoutError:
        logger.warning(f"Message send timed out after {timeout}s")
        return False
    except websockets.exceptions.ConnectionClosed:
        logger.warning("Failed to send message: connection closed")
        return False
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        return False
```

#### Enhanced Audio Sending with Buffering
```python
async def send_audio(self, audio_data: bytes) -> bool:
    """Send audio with enhanced error handling."""
    if not self.is_connected() or not self._connection:
        logger.debug("Cannot send audio - not connected")
        return False
    
    try:
        await self._connection.send(audio_data)
        return True
        
    except websockets.exceptions.ConnectionClosed:
        logger.debug("Failed to send audio: connection closed")
        return False
    except Exception as e:
        logger.warning(f"Failed to send audio: {e}")
        return False
```

## Implementation Steps

### Phase 1: Audio Manager Improvements
1. **Modify `start_recording()` return type** to `bool`
2. **Add `check_audio_health()` method**
3. **Update exception handling** in audio operations
4. **Update callers** to handle boolean return values

### Phase 2: WebSocket Client Improvements  
1. **Add `send_message_with_confirmation()` method**
2. **Modify `send_audio()` return type** to `bool`
3. **Add timeout handling** for send operations
4. **Update error logging** levels

### Phase 3: SessionManager Improvements
1. **Add comprehensive try-catch** to `start_session()`
2. **Implement `_recover_to_listening_state()` method**
3. **Add `_safe_send_audio()` helper**
4. **Update `end_session()` error handling**
5. **Add periodic health checks**

### Phase 4: Integration and Testing
1. **Update all callers** to handle new return types
2. **Add error recovery testing**
3. **Validate state consistency**
4. **Performance impact assessment**

## Expected Benefits

1. **Improved Reliability**: System recovers gracefully from failures
2. **Consistent States**: No more stuck states after errors
3. **Better Diagnostics**: Clear error reporting and recovery actions
4. **Graceful Degradation**: System continues operating when possible
5. **Reduced Manual Intervention**: Automatic recovery from common issues

## Backward Compatibility

- Most changes are additive (new methods, enhanced error handling)
- Return type changes for `start_recording()` and `send_audio()` require caller updates
- All existing functionality preserved
- Error handling is opt-in where possible

## Testing Strategy

1. **Unit Tests**: Test individual error scenarios
2. **Integration Tests**: Test error recovery flows
3. **Stress Tests**: Test under network/audio device failures
4. **State Consistency Tests**: Verify state machine integrity after errors