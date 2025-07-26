# A pinned TODO list of tasks for the whole project - both server and client (raspberry pi software).

- Implement the actul I2S code on the PI client to access the connected mic and speaker.
- Test that the sound processing, mic processing etc. are clear, efficient and reliable.
- ElevenLabs: retrain the voice using some samples from the voice model itself. Sometimes, some generations are randomly high-pitched.
- The "playback completed" signal might be redundant. IF the playback is completed right after the last audio byte is sent from the server to the PI client, we can just do it right after that (with a small delay). The PI client necessarily plays it out loud in real-time. (ALTHOUGH IT SEEMS LIKE THAT IS NOT THE CASE - WILL HAVE TO INVESTIGATE)
- Refactor the session / state management to be less complex and more performant. E.g. the server-side passive/listening/processing/active might
  be redundant, and there's too much surface for errors because the PI client keeps it's own state too so it can get desynchronized. The goal should be
  to streamline it as much as possible.
- The PI Client should ALWAYS have a websocket connection open to the server so that after detection a hotword, we can IMMEDIATELY with no delay start streaming audio to the server.
- Make connection closing more reliable - EXTREMELY RELIABLE. My server just threw an error during listening, went to passive mode, but the PI client was kept in active session state becaus apparantely the connection wasn't closed or something.
- Unite /server and /pi_software startup methods (one is module and other is directly by script...)
- Display: A display for the TARS robot.
- Improve Noise Cancellation: Implement software-based noise reduction on the audio stream received from the ESP32.
- Dynamic Configuration of system settings: Allow system settings (e.g., conversation timeout) to be changed via voice commands.
- Dynamic Configuration of preferences: Allow to save preferences, possibly in a system of memories (humor setting, personality etc.).
- Long term memory: System of storing memories/information (e.g. vector DB), and other memory solutions (e.g. always show previous chat context of the last 1 hour etc.?)
- Handle interruptions: Interruptions handling (includes echo/feedback cancellation (since the mic is listening while the speaker is outputting audio) etc.)

## Raspberry Pi Client Software TODO

### 1. Implement Session Timeout

- **Current State:** The client currently relies entirely on the server to close the connection to end a session.
- **Risk:** If the server fails to close the connection, the client will get stuck in an active session, streaming audio indefinitely and becoming unresponsive.
- **Required Action:**
  - Add a `SESSION_TIMEOUT` setting to `pi_software/src/config/settings.py`.
  - Update `pi_software/src/services/session_manager.py` to start a timer when a session becomes active.
  - If the timer expires, the session manager should forcefully end the session, disconnect the WebSocket, and return to the hotword listening state.

### 2. Implement WebSocket Reconnection Logic

- **Current State:** If the initial WebSocket connection fails, the client immediately gives up and returns to the hotword listening state.
- **Risk:** Transient network issues or a brief server restart will cause user interactions to fail unnecessarily.
- **Required Action:**
  - Add `RECONNECT_DELAY` and `MAX_RECONNECT_ATTEMPTS` settings to `pi_software/src/config/settings.py`.
  - Update the connection logic in `pi_software/src/services/session_manager.py` to include a retry loop with exponential backoff if the initial connection fails.
