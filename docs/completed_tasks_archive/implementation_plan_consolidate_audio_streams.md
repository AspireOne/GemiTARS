# Implementation Plan: Consolidate Audio Stream Management

## Overview

This document outlines the implementation plan for **Improvement 3: Consolidate Audio Stream Management** from the targeted improvements plan. This improvement will centralize audio stream management with state tracking to eliminate redundant operations and potential race conditions.

## Problem Analysis

### Current Issues
1. **Scattered audio operations**: Multiple methods directly call `start_recording`/`stop_recording`
2. **No state tracking**: Unclear what audio mode is currently active
3. **Redundant operations**: Potential unnecessary start/stop cycles
4. **Race conditions**: Multiple methods can modify audio state simultaneously

### Current Audio Flow Analysis
```
┌─────────────────────────────────────────────────┐
│ Current Audio Management (Problematic)          │
├─────────────────────────────────────────────────┤
│ _start_hotword_listening()                      │
│   └─ start_recording(hotword_callback)          │
│                                                 │
│ start_session()                                 │
│   ├─ stop_recording()                           │
│   └─ start_recording(session_callback)          │
│                                                 │
│ end_session()                                   │
│   ├─ stop_recording()                           │
│   └─ _start_hotword_listening()                 │
│       └─ start_recording(hotword_callback)      │
│                                                 │
│ _recover_to_listening_state()                   │
│   ├─ stop_recording()                           │
│   └─ _start_hotword_listening()                 │
│       └─ start_recording(hotword_callback)      │
└─────────────────────────────────────────────────┘
```

## Solution Design

### Centralized Audio State Management

Add audio state tracking and a centralized method to ensure desired audio state:

```python
class SessionManager:
    def __init__(self, ...):
        # Existing init...
        self._audio_state = "stopped"  # "stopped", "hotword", "session"
    
    async def _ensure_audio_state(self, desired_state: str):
        """Ensure audio is in the desired state, avoiding unnecessary restarts."""
        if self._audio_state == desired_state:
            logger.debug(f"Audio already in desired state: {desired_state}")
            return
        
        # Stop current audio
        if self._audio_state != "stopped":
            await self.audio_manager.stop_recording()
            self._audio_state = "stopped"
        
        # Start new audio if needed
        if desired_state == "hotword":
            success = await self.audio_manager.start_recording(self.hotword_detector.process_audio)
            if success:
                self._audio_state = "hotword"
            else:
                logger.error("Failed to start hotword recording")
                # State remains "stopped"
        elif desired_state == "session":
            success = await self.audio_manager.start_recording(
                lambda audio_chunk: self._safe_send_audio(audio_chunk)
            )
            if success:
                self._audio_state = "session"
            else:
                logger.error("Failed to start session recording")
                # State remains "stopped"
```

### New Audio Flow
```
┌─────────────────────────────────────────────────┐
│ Centralized Audio Management (Improved)         │
├─────────────────────────────────────────────────┤
│ _start_hotword_listening()                      │
│   └─ _ensure_audio_state("hotword")             │
│                                                 │
│ start_session()                                 │
│   └─ _ensure_audio_state("session")             │
│                                                 │
│ end_session()                                   │
│   └─ _ensure_audio_state("hotword")             │
│                                                 │
│ _recover_to_listening_state()                   │
│   └─ _ensure_audio_state("hotword")             │
│                                                 │
│ shutdown()                                      │
│   └─ _ensure_audio_state("stopped")             │
└─────────────────────────────────────────────────┘
```

## Implementation Steps

### Phase 1: Add Audio State Tracking
1. Add `_audio_state` field to SessionManager `__init__`
2. Implement `_ensure_audio_state()` method
3. Add error handling for audio state transitions

### Phase 2: Update Existing Methods
1. Update `_start_hotword_listening()` to use centralized management
2. Update `start_session()` to use centralized management
3. Update `end_session()` to use centralized management
4. Update `_recover_to_listening_state()` to use centralized management
5. Update `shutdown()` to use centralized management

### Phase 3: Add Debugging and Monitoring
1. Add debug logging for audio state transitions
2. Add audio state validation
3. Ensure proper error recovery

## Detailed Changes Required

### 1. SessionManager.__init__() Updates
```python
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
    
    # Add audio state tracking
    self._audio_state = "stopped"  # "stopped", "hotword", "session"
    
    self._setup_callbacks()
```

### 2. New _ensure_audio_state() Method
```python
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
                lambda audio_chunk: self._safe_send_audio(audio_chunk)
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
```

### 3. Updated _start_hotword_listening()
```python
async def _start_hotword_listening(self):
    """Start listening for hotwords."""
    self.state_machine.transition_to(ClientState.LISTENING_FOR_HOTWORD)
    success = await self._ensure_audio_state("hotword")
    if not success:
        logger.error("Failed to start hotword listening")
        # Consider transitioning to IDLE state on failure
        self.state_machine.transition_to(ClientState.IDLE)
```

### 4. Updated start_session()
```python
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
```

### 5. Updated end_session()
```python
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
```

### 6. Updated _recover_to_listening_state()
```python
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
```

### 7. Updated shutdown()
```python
async def shutdown(self):
    """Gracefully shutdown all components."""
    logger.info("Shutting down session manager...")
    await self._ensure_audio_state("stopped")
    await self.websocket_client.shutdown()
```

## Benefits

1. **Eliminates redundant audio operations**: Only changes audio state when actually needed
2. **Provides clear audio state tracking**: Always know what audio mode is active
3. **Reduces potential race conditions**: Centralized management prevents conflicts
4. **Simplifies debugging**: Clear logging of audio state transitions
5. **Improves reliability**: Better error handling for audio state changes
6. **Maintains existing functionality**: All current features preserved

## Testing Strategy

1. **State transition testing**: Verify audio states change correctly
2. **Error recovery testing**: Ensure audio recovers properly from failures
3. **Performance testing**: Confirm no unnecessary audio restarts
4. **Integration testing**: Verify all existing functionality still works

## Validation Criteria

- [ ] Audio never restarts unnecessarily (same state requested twice)
- [ ] All audio state transitions are logged clearly
- [ ] Error recovery always leads to a consistent audio state
- [ ] No audio streams are left running during shutdown
- [ ] All existing audio functionality continues to work

This implementation will significantly improve the reliability and maintainability of audio stream management while preserving all current functionality.