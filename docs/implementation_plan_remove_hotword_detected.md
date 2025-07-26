# Implementation Plan: Remove HOTWORD_DETECTED State

## Overview
This document outlines the specific implementation steps to remove the transient `HOTWORD_DETECTED` state from the client architecture.

## Current Flow
```
LISTENING_FOR_HOTWORD → HOTWORD_DETECTED → ACTIVE_SESSION
```

## New Simplified Flow
```
LISTENING_FOR_HOTWORD → ACTIVE_SESSION
```

## Changes Required

### 1. Update State Machine (`pi_software/src/core/state_machine.py`)

**File:** `pi_software/src/core/state_machine.py`

**Change 1: Remove HOTWORD_DETECTED from ClientState enum**
```python
# BEFORE:
class ClientState(Enum):
    """Simplified client states for persistent connection model."""
    IDLE = auto()
    LISTENING_FOR_HOTWORD = auto()
    HOTWORD_DETECTED = auto()  # REMOVE THIS LINE
    ACTIVE_SESSION = auto()

# AFTER:
class ClientState(Enum):
    """Simplified client states for persistent connection model."""
    IDLE = auto()
    LISTENING_FOR_HOTWORD = auto()
    ACTIVE_SESSION = auto()
```

**Change 2: Update transitions dictionary**
```python
# BEFORE:
self._transitions: Dict[ClientState, Set[ClientState]] = {
    ClientState.IDLE: {ClientState.LISTENING_FOR_HOTWORD},
    ClientState.LISTENING_FOR_HOTWORD: {ClientState.HOTWORD_DETECTED, ClientState.IDLE},
    ClientState.HOTWORD_DETECTED: {ClientState.ACTIVE_SESSION, ClientState.LISTENING_FOR_HOTWORD},  # REMOVE THIS LINE
    ClientState.ACTIVE_SESSION: {ClientState.LISTENING_FOR_HOTWORD, ClientState.IDLE}
}

# AFTER:
self._transitions: Dict[ClientState, Set[ClientState]] = {
    ClientState.IDLE: {ClientState.LISTENING_FOR_HOTWORD},
    ClientState.LISTENING_FOR_HOTWORD: {ClientState.ACTIVE_SESSION, ClientState.IDLE},
    ClientState.ACTIVE_SESSION: {ClientState.LISTENING_FOR_HOTWORD, ClientState.IDLE}
}
```

### 2. Update Session Manager (`pi_software/src/services/session_manager.py`)

**File:** `pi_software/src/services/session_manager.py`

**Change: Update on_hotword_detected method**
```python
# BEFORE:
def on_hotword_detected(self):
    """Callback executed when hotword is detected."""
    if self.state_machine.transition_to(ClientState.HOTWORD_DETECTED):
        asyncio.run_coroutine_threadsafe(self.start_session(), self.loop)

# AFTER:
def on_hotword_detected(self):
    """Callback executed when hotword is detected."""
    asyncio.run_coroutine_threadsafe(self.start_session(), self.loop)
```

**Explanation:** 
- Remove the intermediate state transition to `HOTWORD_DETECTED`
- The `start_session()` method already handles the transition to `ACTIVE_SESSION` directly
- This simplifies the flow and eliminates the transient state

## Implementation Steps

1. **Remove HOTWORD_DETECTED state** from `ClientState` enum in `state_machine.py`
2. **Update transitions** in `StateMachine.__init__()` to allow direct transition from `LISTENING_FOR_HOTWORD` to `ACTIVE_SESSION`
3. **Simplify on_hotword_detected** in `session_manager.py` to call `start_session()` directly
4. **Test the changes** to ensure proper state transitions

## Expected Behavior After Changes

1. **Normal Flow:**
   - Start in `IDLE` state
   - Transition to `LISTENING_FOR_HOTWORD` when starting
   - On hotword detection, directly transition to `ACTIVE_SESSION`
   - After session ends, return to `LISTENING_FOR_HOTWORD`

2. **Error Handling:**
   - If connection is lost during session start, return to `LISTENING_FOR_HOTWORD`
   - All existing error handling remains intact

## Validation Points

- [ ] State machine transitions work correctly
- [ ] Hotword detection still triggers sessions properly
- [ ] Error cases (no connection) still handled correctly
- [ ] No regressions in existing functionality
- [ ] Reduced complexity and fewer state transitions

## Benefits

- Eliminates unnecessary intermediate state
- Reduces state machine complexity by 25%
- Simplifies debugging and logging
- Maintains all existing functionality
- No impact on other components