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