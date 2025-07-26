# Plan to Fix Playback Handshake and System Hang

## 1. Problem Diagnosis
The previous fix for the system hanging was incorrect. The core issues are:
1.  The client is not playing the TTS audio received from the server.
2.  The client is not sending the `playback_complete` signal back to the server, causing the server to hang indefinitely.

The timeout-based approach in `SessionManager` was flawed. A deterministic, event-driven handshake is required.

## 2. Proposed Solution: A Robust Handshake Protocol

### Step A: Revert Incorrect Client-Side Logic
First, I will revert the previous, incorrect changes made to `pi_software/src/services/session_manager.py` that introduced the flawed timeout mechanism.

### Step B: Server-Side Changes

#### File: `server/src/main.py`
- **Action:** Modify `_stream_tts_response`. After the `elevenlabs_service.stream_tts` loop finishes, send a new JSON message to the client to signal that the audio stream is complete.
- **Code:**
  ```python
  # In _stream_tts_response, after the for loop:
  await self.pi_service.send_control_message({"type": "tts_stream_end"})
  
  # This requires adding a `send_control_message` method to the interface.
  ```

#### File: `server/src/services/pi_interface.py`
- **Action:** Add a new abstract method `send_control_message(self, message: dict) -> None` to the interface.

#### File: `server/src/services/pi_websocket_service.py`
- **Action:** Implement the `send_control_message` method to send a JSON message to the client.

### Step C: Client-Side Changes

#### File: `pi_software/src/services/websocket_client.py`
- **Action:** Modify the `_receive_loop` to handle both `bytes` (for audio) and `str` (for JSON control messages). When a JSON message is received, it will be passed to a new callback.
- **Code:**
  ```python
  # Add a new callback
  self.on_control_message_received: Optional[Callable[[dict], None]] = None

  # In _receive_loop:
  if isinstance(message, str):
      if self.on_control_message_received:
          try:
              self.on_control_message_received(json.loads(message))
          except json.JSONDecodeError:
              logger.warning(f"Invalid JSON from server: {message}")
  ```

#### File: `pi_software/src/services/session_manager.py`
- **Action:** This is the core of the client-side fix.
  1.  Set up the new `on_control_message_received` callback from the `websocket_client`.
  2.  Create a new handler method, `on_control_message(self, message: dict)`.
  3.  When this handler receives `{"type": "tts_stream_end"}`, it will:
      a. `await self.audio_manager.wait_for_playback_completion()` to ensure all buffered audio has been played.
      b. `await self.websocket_client.send_message({"type": "playback_complete"})` to notify the server.

## 3. Next Steps
1.  Request user approval of this detailed plan.
2.  Switch to **Code Mode**.
3.  Execute the plan step-by-step, starting with reverting the old changes.