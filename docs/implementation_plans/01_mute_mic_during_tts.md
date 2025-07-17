# Implementation Plan: Mute Microphone During Assistant Speech

**Objective**: Modify the conversation state logic to mute the microphone from the moment the Gemini API begins generating a text response until the ElevenLabs TTS audio playback is complete.

**Key Principle**: The implementation will prioritize clarity and maintainability by introducing a new `SPEAKING` state and ensuring each state has a single, well-defined purpose. This avoids complex logic or state-overloading.

---

## 1. File: `src/core/conversation_state.py`

### Task 1.1: Add `SPEAKING` state

Modify the `ConversationState` enum to include the new `SPEAKING` state. This state will represent the period when the assistant is actively playing TTS audio.

**Proposed Change:**
```python
class ConversationState(Enum):
    """Simple conversation states for VAD management."""
    PASSIVE = "passive"        # Waiting for hotword
    ACTIVE = "active"          # User can speak, listening
    PROCESSING = "processing"  # Gemini is generating response, mic is muted
    SPEAKING = "speaking"      # Assistant is playing TTS audio, mic is muted
```

### Task 1.2: Remove `should_listen_for_speech`

This helper method will become obsolete and potentially confusing, as the logic for when to listen will be simplified. Removing it improves clarity. The audio routing logic will instead depend directly on the `ACTIVE` state.

**Action**: Delete the `should_listen_for_speech` method from the `ConversationManager` class.

---

## 2. File: `src/main.py`

### Task 2.1: Update `_gemini_response_handler`

Transition to the `PROCESSING` state as soon as the first text chunk arrives from Gemini. This ensures the microphone is muted immediately when the assistant starts "thinking."

**Proposed Logic:**
A local flag `is_processing` will be added to the method to track if the transition has already occurred for the current response turn.

```python
# Inside _gemini_response_handler method
full_response = ""
is_processing = False # Flag to ensure we only transition once per turn

try:
    async for response in self.gemini_service.receive_responses():
        if response.text:
            # On the first text chunk, transition to PROCESSING to mute the mic
            if not is_processing:
                self.conversation_manager.transition_to(ConversationState.PROCESSING)
                is_processing = True
            
            print(response.text, end="", flush=True)
            full_response += response.text

        if response.is_turn_complete:
            if full_response.strip():
                print()
                await self._stream_tts_response(full_response.strip())
            
            full_response = ""
            is_processing = False # Reset for the next turn
            self.conversation_manager.update_activity()
...
```

### Task 2.2: Update `_stream_tts_response`

This method will manage the state transitions from `PROCESSING` -> `SPEAKING` -> `ACTIVE`. A `finally` block will be used to guarantee the state is always reset to `ACTIVE`, even if an error occurs during TTS streaming.

**Proposed Logic:**
```python
# Inside _stream_tts_response method
if not self.elevenlabs_service or not self.esp32_service:
    # If services are unavailable, transition back to ACTIVE immediately
    self.conversation_manager.transition_to(ConversationState.ACTIVE)
    return

try:
    # 1. Transition from PROCESSING to SPEAKING
    self.conversation_manager.transition_to(ConversationState.SPEAKING)
    
    print(f"🎵 TARS: Converting to speech and streaming...")
    
    # 2. Stream TTS audio
    async for audio_chunk in self.elevenlabs_service.stream_tts(text):
        await self.esp32_service.play_audio_chunk(audio_chunk)
    
    print(f"✅ TARS: Voice output completed")

except Exception as e:
    print(f"❌ Error in TTS streaming: {e}")
finally:
    # 3. IMPORTANT: Always transition back to ACTIVE after speaking/error
    self.conversation_manager.transition_to(ConversationState.ACTIVE)
```

### Task 2.3: Update `_route_audio_based_on_state`

Simplify the audio routing logic. Audio from the microphone will only be processed if the state is `ACTIVE`. This single check effectively mutes the mic during `PASSIVE`, `PROCESSING`, and `SPEAKING` states for the Gemini service.

**Proposed Change:**
```python
def _route_audio_based_on_state(self, audio_bytes: bytes) -> None:
    """Route audio based on current conversation state."""
    state = self.conversation_manager.state
    try:
        if state == ConversationState.PASSIVE:
            # Route to hotword detection
            self.hotword_service.process_audio_chunk(audio_bytes)

        elif state == ConversationState.ACTIVE:
            # Route to Gemini Live API
            if self.gemini_service:
                self.gemini_service.queue_audio(audio_bytes)
        
        # In all other states (PROCESSING, SPEAKING), audio is ignored.
    except Exception as e:
        print(f"⚠️ Error routing audio: {e}")
```

### Task 2.4: Confirm `_conversation_management_loop`

The existing timeout logic in `ConversationManager.is_conversation_timeout` already checks if the state is *not* `PASSIVE`. This correctly covers `ACTIVE`, `PROCESSING`, and the new `SPEAKING` state. No code change is required here, but the understanding is confirmed.