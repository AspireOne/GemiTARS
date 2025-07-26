# GemiTARS: A replica of TARS from Interstellar

A replica of TARS from Interstellar, featuring continuous conversations powered by Gemini Live API. Uses a distributed architecture with a compact Raspberry Pi Zero 2W "head" for local wake word detection and I/O, while a powerful server "brain" manages AI processing, state management, and other processing, enabling rich voice interactions with function calling capabilities.

This file provides overview and high level goals/features and architecture of the project.

`/server`: contains the server code.
`/pi_software`: contains the code for the Raspberry Pi client.

- To see reamining tasks: [`docs/TODO.md`](docs/TODO.md).
- External documentation is in [`docs/external/`](docs/external_docs/) (for gemini Live API, ElevenLabs TTS, OpenWakeWord etc.).
- Technical description of the system architecture: [`docs/system_architecture.md`](docs/system_architecture.md).

- The Raspberry Pi client software is in [`pi_software/`](pi_software/).
- The server/processing hub software is in [`server/`](server/).

## Core Features Overview

### Currently Implemented ✅

- **Hotword Detection**: Local, offline listening for wake words ("Hey, TARS!" and "TARS") using OpenWakeWord models on the Raspberry Pi. Includes configurable thresholds and cooldown mechanisms to prevent false triggers.

- **Continuous Conversation**: After activation, the assistant maintains an active connection to the Gemini Live API for a configurable duration (default 30 seconds), allowing natural back-and-forth conversation without re-triggering the hotword. The timeout resets with each user interaction.

- **Direct Audio-to-LLM**: Raw audio from the Raspberry Pi microphone is streamed directly to the Gemini Live API via the server, bypassing local speech-to-text transcription to minimize latency and improve conversational flow.

- **Custom TARS Voice Output**: High-fidelity text-to-speech using ElevenLabs' streaming API with a custom TARS-like voice profile. Audio is streamed in real-time chunks to minimize response latency.

- **Distributed Architecture**: A compact Raspberry Pi Zero 2W handles local wake word detection and audio I/O, while a powerful server manages AI processing, state management, and API integrations. Communication occurs over a persistent WebSocket connection.

- **Robust State Management**: Both client and server implement comprehensive state machines to handle the conversation flow (passive listening → active conversation → processing → speaking → back to active).

- **Real-time Audio Streaming**: Bidirectional audio streaming with proper synchronization - microphone audio flows from Pi → Server → Gemini, while TTS audio flows from ElevenLabs → Server → Pi.

### Planned Features 🔮

- **Multimodal Input**: Integration with the Raspberry Pi camera for visual context. Users will be able to say phrases like "look at this" or "what do you see?" to include images in their queries to the LLM.

- **Function Calling**: The assistant will process complex conversational requests and execute functions such as controlling smart home devices, performing web searches, or interacting with external APIs and services.

- **Enhanced Error Recovery**: More sophisticated handling of network interruptions, including client-side audio buffering during connection issues and automatic retry mechanisms.

## Gemini Live API

Extremely fast and low-latency LLM API that:

- Takes in not only text, but also images, audio, or combination of these.
- Streams back responses in real-time.
- Has a built-in VAD (voice activity detection) to automatically wait for a user's speech before responding etc.
- Has a Live mode, where it itself manages the whole session - it takes in the user's talking (input audio) directly, and decides when and how to respond, whether to be interrupted etc. - no processing on the side of our server.

## System Architecture

The system uses a distributed architecture split into two main components communicating over WiFi, designed to keep the user-facing device compact while leveraging powerful server-side processing.

- **Pi Client (The "Head"):** A Raspberry Pi Zero 2W-based device that handles local wake word detection and physical input/output. Its responsibilities are:

  - Locally detecting wake words using OpenWakeWord with custom TARS models (`Hey_Tars.onnx`, `Tars.onnx`)
  - Maintaining a persistent WebSocket connection to the server via `PersistentWebSocketClient` with automatic reconnection and heartbeat monitoring
  - Capturing microphone audio and streaming it to the server only after wake word detection
  - Managing client-side state through `StateMachine` (IDLE → LISTENING_FOR_HOTWORD → HOTWORD_DETECTED → ACTIVE_SESSION)
  - Receiving and playing back TTS audio streams through the connected speaker
  - Coordinating the session lifecycle via `SessionManager`

- **Server (The "Brain"):** A server that orchestrates the complete conversation flow. It is responsible for:
  - Managing WebSocket connections from Pi clients via `PiWebsocketService`
  - Coordinating conversation state through `ConversationManager` (PASSIVE → ACTIVE → PROCESSING → SPEAKING)
  - Interfacing with the Gemini Live API via `GeminiService` for real-time audio processing and response generation
  - Converting text responses to speech via `ElevenLabsService` using streaming TTS
  - Handling session timeouts and graceful cleanup of resources
  - Managing bidirectional audio streaming with proper synchronization and playback completion handshakes

This distributed approach was chosen to fulfill the goal of a minimal physical footprint for the user-facing device, with the Raspberry Pi Zero 2W acting as an efficient "sensor pod" that handles local wake word detection for privacy and bandwidth efficiency, while offloading intensive AI computation to the more powerful server. The direct LLM audio processing (via Gemini Live) reduces latency by eliminating the traditional Speech-to-Text transcription step, while high-fidelity TTS (ElevenLabs) provides authentic TARS voice synthesis rather than attempting complex real-time voice transformation.

## The Logic Flow

The GemiTARS system operates through several distinct phases, seamlessly transitioning between passive listening and active conversation modes:

**TL;DR:**

- Raspberry Pi continuously listens for hotword locally using OpenWakeWord.
- If hotword is detected, it starts streaming audio to the server and plays an acknowledgment tone.
- Server establishes Gemini Live API session.
- The conversation now continues through the Gemini Live API, with the Raspberry Pi streaming audio to the server and the server streaming audio (the LLM response audio) back to the Raspberry Pi.
- When Gemini Live API returns text → send it to ElevenLabs → stream back its audio chunks directly to the Raspberry Pi.
- If no sound is detected / no reply is coming, time out and return to passive listening mode.

**Note:**
A user cannot interrupt TARS while he is thinking (PROCESSING) or speaking (SPEAKING). If the user says "Stop" or "Wait, I meant something else," the microphone is effectively off. This is a current design decision and might be changed in the future.

**1. Passive Listening State**

- The Pi Client runs `HotwordDetector` which continuously monitors microphone audio locally for wake words ("Hey, TARS!" or "TARS") using OpenWakeWord models
- No audio is streamed to the server during this phase, preserving privacy and bandwidth
- System remains in low-power mode with the server in `PASSIVE` state

**2. Wake Word Activation**

- When a wake word is detected locally, the Pi Client transitions to `ACTIVE_SESSION` state
- The client sends a `{"type": "hotword_detected"}` JSON message over the persistent WebSocket
- The server receives this message and transitions from `PASSIVE` to `ACTIVE` state
- Server initializes a new `GeminiService` session and establishes connection to Gemini Live API
- Conversation timeout timer begins (configurable, default 30 seconds)

**3. Active Conversation Mode**

- **Audio Streaming**: Pi Client streams raw microphone audio as binary WebSocket messages to the server
- **Server Processing**: Server forwards audio chunks to `GeminiService` which streams them to Gemini Live API
- **Real-time Transcription**: Gemini Live provides real-time speech transcription that the server logs for monitoring
- **Continuous Listening**: System maintains the connection and actively listens for follow-up input
- **Activity Tracking**: Each user interaction resets the conversation timeout via `ConversationManager.update_activity()`

**4. Response Generation and Playback**

- **Turn Completion**: When Gemini Live signals turn completion, server transitions to `PROCESSING` state
- **TTS Conversion**: Server sends the text response to `ElevenLabsService` for conversion to TARS-like voice
- **Streaming Protocol**:
  - Server sends `{"type": "start_of_tts_stream"}` to signal audio playback start
  - Server transitions to `SPEAKING` state
  - Server streams TTS audio chunks as binary messages to the Pi Client
  - Server sends `{"type": "tts_stream_end"}` when streaming completes
- **Playback Completion**: Pi Client responds with `{"type": "playback_complete"}` after finishing audio playback
- **State Return**: Server transitions back to `ACTIVE` state, ready for next user input

**5. Session Management**

- **Timeout Monitoring**: Server's `_conversation_management_loop()` continuously checks for conversation timeout
- **Graceful Termination**: On timeout, server sends `{"type": "session_end"}` and transitions to `PASSIVE`
- **Resource Cleanup**: `GeminiService` session is closed, background tasks are cancelled, Pi Client returns to hotword listening

**6. Return to Passive State**

- **Session Cleanup**: The Gemini Live API connection is terminated.
- **State Reset**: System returns to passive hotword detection mode on the Raspberry Pi.
- **Resource Management**: Server reduces processing load; Pi stops streaming and returns to local monitoring.
- **Ready for Next Activation**: Raspberry Pi resumes local listening for the next "Hey, TARS!" detection.

**Error Handling and Edge Cases**

**Connection Management and Recovery**

- **Persistent WebSocket Connection**: The Pi Client maintains a persistent connection with automatic reconnection using exponential backoff (up to 10 attempts with delays from 1 to 60 seconds).
- **Heartbeat Monitoring**: Client sends periodic ping frames to detect connection issues and trigger reconnection when needed.
- **Connection State Management**: Robust state tracking (DISCONNECTED → CONNECTING → CONNECTED → SHUTTING_DOWN) with proper cleanup between states.
- **Graceful Degradation**: If WebSocket connection fails, the client continues attempting to reconnect while the server can handle multiple client connection attempts.

**Session and Resource Management**

- **Client Disconnection Handling**: When a client disconnects unexpectedly during an active session, the server automatically performs session cleanup - closing Gemini API connections, cancelling background tasks, and returning to passive state.
- **Service Failure Tolerance**: If ElevenLabs TTS service fails to initialize, the system continues operating in text-only mode rather than crashing.
- **Timeout Management**: Conversation sessions automatically timeout after configurable periods (default 30 seconds) with proper resource cleanup.
- **Graceful Shutdown**: Both client and server implement controlled shutdown procedures with task cancellation timeouts (5 seconds) to prevent resource leaks.

**Audio and Communication Error Handling**

- **Message Send Failures**: Client handles WebSocket send failures gracefully, with timeout detection and connection state validation before attempting to send.
- **Audio Streaming Resilience**: Audio send failures return status indicators rather than crashing, allowing the system to continue operating.
- **JSON Parsing Protection**: Both client and server include JSON parsing error handling to prevent crashes from malformed control messages.
- **Playback Interruption**: Server properly handles connection closures during TTS audio streaming, cleaning up audio queues and resetting conversation state.

**Current Limitations**

- **No Local Audio Buffering**: The Pi Client does not currently buffer audio locally during network interruptions - audio is simply dropped until connection is restored.
- **Single Session Handling**: The system handles one conversation session at a time per client rather than queuing multiple concurrent requests.
- **Manual Audio Quality**: Audio quality improvements rely on proper microphone configuration rather than automated noise reduction or gain control.
