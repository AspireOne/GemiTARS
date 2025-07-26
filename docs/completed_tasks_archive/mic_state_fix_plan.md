# Implementation Plan: Microphone State Management Fix

This document outlines the step-by-step plan to fix the audio buffering bug by implementing a more robust, server-authoritative state management system for the client's microphone.

## 1. Update Client State Machine

The first step is to introduce a new state to represent the period when the client is processing the server's response.

**File:** `pi_software/src/core/state_machine.py`

- **Action:** Add a new `PROCESSING_RESPONSE` state to the `ClientState` enum.
- **Action:** Update the `_transitions` dictionary to define valid transitions to and from the new state.

```python
class ClientState(Enum):
    """Simplified client states for persistent connection model."""
    IDLE = auto()
    LISTENING_FOR_HOTWORD = auto()
    ACTIVE_SESSION = auto()
    PROCESSING_RESPONSE = auto() # New state

# ... inside StateMachine class ...
self._transitions: Dict[ClientState, Set[ClientState]] = {
    ClientState.IDLE: {ClientState.LISTENING_FOR_HOTWORD},
    ClientState.LISTENING_FOR_HOTWORD: {ClientState.ACTIVE_SESSION, ClientState.IDLE},
    ClientState.ACTIVE_SESSION: {ClientState.PROCESSING_RESPONSE, ClientState.LISTENING_FOR_HOTWORD, ClientState.IDLE},
    ClientState.PROCESSING_RESPONSE: {ClientState.ACTIVE_SESSION, ClientState.LISTENING_FOR_HOTWORD, ClientState.IDLE}
}
```

## 2. Implement New Server-Side Control Messages

The server needs to be updated to send the new control messages that will direct the client's state.

**File:** `server/src/services/pi_websocket_service.py` (and potentially `gemini_service.py`)

- **Action:** Before the `ElevenLabsService` starts streaming TTS audio, send the `{"type": "start_of_tts_stream"}` message to the client.
- **Action:** When the conversation turn is over (e.g., Gemini is waiting for the user's next response), the server should ensure the client is ready to listen. The existing `tts_stream_end` message will now be used for this.
- **Action:** When the entire conversation is finished (e.g., after a "goodbye" intent), send the `{"type": "end_of_session"}` message.

## 3. Update Client-Side Session Manager

The `SessionManager` on the Pi client will be updated to handle the new states and control messages.

**File:** `pi_software/src/services/session_manager.py`

- **Action:** In the `on_control_message` method, add handlers for the new message types:
    - **`start_of_tts_stream`**:
        - Transition to `ClientState.PROCESSING_RESPONSE`.
        - Call `_ensure_audio_state("stopped")` to turn off the microphone.
    - **`tts_stream_end`**:
        - This message now signals that the client should prepare to listen again.
        - After playback is complete, transition back to `ClientState.ACTIVE_SESSION`.
        - Call `_ensure_audio_state("session")` to re-enable the microphone.
    - **`session_end`**:
        - Rename the existing `session_end` message handler to `end_of_session` for clarity.
        - Call the `end_session` method, which will transition the client back to `LISTENING_FOR_HOTWORD`.

This structured approach ensures that all necessary changes are made in a logical order, minimizing the risk of errors and ensuring the bug is fully resolved.