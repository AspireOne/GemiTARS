# GemiTARS: A replica of TARS from Interstellar

A replica of TARS from Interstellar, featuring continuous conversations powered by Gemini Live API. Uses a distributed architecture with a compact Raspberry Pi Zero 2W "head" for local wake word detection and I/O, while a powerful server "brain" manages AI processing, state management, and other processing, enabling rich voice interactions.

This file provides overview and high level goals/features and architecture of the project.

**Project Structure:**
- `/server`: Server/processing hub code
- `/pi_software`: Raspberry Pi client code  
- [`docs/TODO.md`](docs/TODO.md): Remaining tasks
- [`docs/external/`](docs/external_docs/): External API documentation
- [`docs/system_architecture.md`](docs/system_architecture.md): Detailed technical architecture

## Core Features Overview

### Currently Implemented ✅

- **Hotword Detection**: Local, offline listening for wake words ("Hey, TARS!" and "TARS") using OpenWakeWord models. Includes configurable thresholds and cooldown mechanisms to prevent false triggers.

- **Continuous Conversation**: After activation, maintains an active connection to Gemini Live API for a configurable duration (default 30 seconds), allowing natural back-and-forth conversation without re-triggering the hotword. Timeout resets with each user interaction.

- **Direct Audio-to-LLM**: Raw audio streams directly from Raspberry Pi microphone to Gemini Live API via the server, bypassing local speech-to-text transcription to minimize latency.

- **Custom TARS Voice Output**: High-fidelity text-to-speech using ElevenLabs' streaming API with a custom TARS-like voice profile, streamed in real-time chunks.

- **Distributed Architecture**: Compact Pi client handles local I/O while powerful server manages AI processing and API integrations. Communication via persistent WebSocket with automatic reconnection.

- **Robust State Management**: Comprehensive state machines on both client and server manage conversation flow (passive → active → processing → speaking).

- **Real-time Audio Streaming**: Bidirectional audio with proper synchronization and playback completion handshakes.

### Planned Features 🔮

- **Multimodal Input**: Camera integration for visual context ("look at this", "what do you see?")
- **Function Calling**: Smart home control, web searches, external API interactions
- **Enhanced Error Recovery**: Client-side audio buffering during network interruptions

## System Architecture

**Pi Client (The "Head"):** Raspberry Pi Zero 2W handling:
- Local wake word detection using OpenWakeWord with custom TARS models
- Persistent WebSocket connection with automatic reconnection and heartbeat monitoring  
- Audio capture and streaming (post-detection only)
- Client-side state management (IDLE → LISTENING → HOTWORD_DETECTED → ACTIVE_SESSION)
- TTS audio playback
- Session lifecycle coordination

**Server (The "Brain"):** Orchestrates complete conversation flow:
- WebSocket connection management for Pi clients
- Conversation state coordination (PASSIVE → ACTIVE → PROCESSING → SPEAKING)
- Gemini Live API interface for real-time audio processing and response generation
- ElevenLabs TTS conversion with streaming
- Session timeout handling and resource cleanup
- Bidirectional audio streaming with synchronization

This approach provides minimal physical footprint for the user-facing device while leveraging powerful server-side processing. Direct LLM audio processing reduces latency by eliminating Speech-to-Text transcription, while streaming TTS provides authentic TARS voice synthesis.

## The Logic Flow

**1. Passive Listening**
- Pi client continuously monitors microphone locally for wake words
- No audio streamed to server (privacy/bandwidth preservation)
- Server remains in PASSIVE state

**2. Wake Word Activation**  
- Local detection triggers Pi client transition to ACTIVE_SESSION
- Client sends `{"type": "hotword_detected"}` over WebSocket
- Server transitions to ACTIVE and initializes Gemini Live session
- Conversation timeout begins

**3. Active Conversation**
- Pi streams raw microphone audio as binary WebSocket messages
- Server forwards audio to Gemini Live API
- Real-time transcription logged for monitoring
- Each interaction resets conversation timeout

**4. Response Generation**
- Gemini Live signals turn completion → server enters PROCESSING state
- Text response sent to ElevenLabs for TTS conversion
- Server enters SPEAKING state and streams audio chunks to Pi
- Pi confirms playback completion → server returns to ACTIVE

**5. Session Management**
- Continuous timeout monitoring by server
- On timeout: server sends `{"type": "session_end"}` and returns to PASSIVE
- Resource cleanup: Gemini session closed, tasks cancelled, Pi returns to hotword listening

**Note:** Users cannot interrupt TARS during PROCESSING or SPEAKING states (microphone effectively muted). This design ensures clear audio playback but may be enhanced for interruption support.

## Error Handling and Edge Cases

**Connection Management**
- Persistent WebSocket with exponential backoff reconnection (up to 10 attempts, 1-60 second delays)
- Heartbeat monitoring and connection state tracking
- Graceful degradation during connection failures

**Session and Resource Management**  
- Automatic session cleanup on unexpected client disconnection
- Service failure tolerance (continues in text-only mode if TTS fails)
- Controlled shutdown with task cancellation timeouts to prevent resource leaks

**Audio and Communication**
- WebSocket send failure handling with timeout detection
- JSON parsing protection against malformed messages  
- Audio streaming resilience with status indicators rather than crashes

**Current Limitations**
- No local audio buffering during network interruptions
- Single session per client (no concurrent request queuing)
- Manual audio quality (relies on proper microphone configuration)
