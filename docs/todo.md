# A pinned TODO list of tasks for the GemiTARS project - both server and client (raspberry pi software).

- [ ] Display: A display for the TARS robot.
- [ ] Improve Noise Cancellation: Implement software-based noise reduction on the audio stream received from the ESP32.
- [ ] Dynamic Configuration of system settings: Allow system settings (e.g., conversation timeout) to be changed via voice commands.
- [ ] Dynamic Configuration of preferences: Allow to save preferences, possibly in a system of memories (humor setting, personality etc.).
- [ ] Long term memory: System of storing memories/information (e.g. vector DB), and other memory solutions (e.g. always show previous chat context of the last 1 hour etc.?)
- [ ] Handle interruptions: Interruptions handling (includes echo/feedback cancellation (since the mic is listening while the speaker is outputting audio) etc.)
- [ ] Create PI software:

```
pi_software/
├── src/
│   ├── main.py                 # Real Pi client
│   ├── mock_client.py          # WebSocket-based mock
│   └── core/
│       ├── audio_handler.py
│       ├── hotword_detector.py
│       └── server_client.py    # Shared WebSocket logic
└── tests/
    └── integration_tests.py
```

Benefits:
Real Protocol Testing: The mock actually uses WebSockets, so you're testing the real communication path
Shared Code: Both real and mock clients can share the WebSocket communication logic
End-to-End Validation: Tests the entire server stack, including WebSocket handling, message parsing, etc.
Development Flexibility: You can run the mock on your development machine while the server runs elsewhere
Debugging: Much easier to debug WebSocket issues when you have a controllable client

## Raspberry Pi Client Software TODO

- No Session Timeout: In SessionManager, once a session becomes active (ACTIVE_SESSION), there is no timeout mechanism. The client relies entirely on the server closing the connection to end the session. If the server fails to do so, the client will remain stuck in the active state, streaming audio indefinitely. The plan mentioned a SESSION_TIMEOUT but it has not been implemented.

- No Reconnection Logic: The plan specifies that the WebSocketClient should handle reconnection with exponential backoff. Currently, if the initial connection in handle_active_session fails, the client immediately gives up and returns to listening for the hotword. It does not attempt to reconnect.

## 1. Implement Session Timeout

- **Current State:** The client currently relies entirely on the server to close the connection to end a session.
- **Risk:** If the server fails to close the connection, the client will get stuck in an active session, streaming audio indefinitely and becoming unresponsive.
- **Required Action:**
  - Add a `SESSION_TIMEOUT` setting to `pi_software/src/config/settings.py`.
  - Update `pi_software/src/services/session_manager.py` to start a timer when a session becomes active.
  - If the timer expires, the session manager should forcefully end the session, disconnect the WebSocket, and return to the hotword listening state.

## 2. Implement WebSocket Reconnection Logic

- **Current State:** If the initial WebSocket connection fails, the client immediately gives up and returns to the hotword listening state.
- **Risk:** Transient network issues or a brief server restart will cause user interactions to fail unnecessarily.
- **Required Action:**
  - Add `RECONNECT_DELAY` and `MAX_RECONNECT_ATTEMPTS` settings to `pi_software/src/config/settings.py`.
  - Update the connection logic in `pi_software/src/services/session_manager.py` to include a retry loop with exponential backoff if the initial connection fails.
