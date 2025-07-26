# Raspberry Pi Client Implementation Plan

## Overview

This document outlines the complete implementation plan for the GemiTARS Raspberry Pi client software. The client is designed with a hardware abstraction layer that allows development/testing on a PC using standard audio devices, while maintaining compatibility with the Raspberry Pi's I2S audio hardware.

## Architecture Principles

1. **Hardware Abstraction**: Audio I/O is abstracted to allow both PC and Pi implementations
2. **Event-Driven Design**: Components communicate through callbacks and async patterns
3. **Clean Separation**: Each component has a single responsibility
4. **Fail-Safe Operation**: Graceful handling of connection failures and hardware issues

## Pre-Requirements

### Dependencies (requirements.txt)
```
python-dotenv==1.0.0
sounddevice==0.4.6      # For PC audio implementation
pyaudio==0.2.14         # Alternative/backup audio library
openwakeword==0.5.1     # Local hotword detection
websockets==12.0        # WebSocket client
colorlog==6.8.0         # Colored logging
numpy==1.24.3           # Audio processing
asyncio-mqtt==0.16.2    # For future GPIO/LED control (optional)
```

### System Requirements
- Python 3.9+ (for asyncio improvements)
- On Raspberry Pi: ALSA configured for I2S devices
- On PC: Working microphone and speakers

## Project Structure

```
pi_software/
├── docs/
│   ├── pi_client_implementation_plan.md (this file)
│   └── rpi_implementation_notes.md
├── src/
│   ├── audio/
│   │   ├── __init__.py
│   │   ├── audio_interface.py      # Abstract base class
│   │   ├── pc_audio_manager.py     # PC implementation using sounddevice
│   │   └── pi_audio_manager.py     # Pi implementation for I2S hardware
│   ├── services/
│   │   ├── __init__.py
│   │   ├── websocket_client.py     # WebSocket connection manager
│   │   └── session_manager.py      # Manages conversation sessions
│   ├── core/
│   │   ├── __init__.py
│   │   ├── hotword_detector.py     # OpenWakeWord wrapper (existing, needs update)
│   │   └── state_machine.py        # Client state management
│   ├── config/
│   │   └── settings.py              # Configuration (existing)
│   ├── utils/
│   │   └── logger.py                # Logging setup (existing)
│   ├── resources/                   # Hotword models (existing)
│   └── main.py                      # Entry point
├── tests/
│   ├── test_audio_abstraction.py
│   └── test_websocket_client.py
├── requirements.txt
├── .env.example
└── README.md
```

## Component Specifications

### 1. Audio Abstraction Layer

**File: `src/audio/audio_interface.py`**
```python
from abc import ABC, abstractmethod
from typing import Callable, Optional

class AudioInterface(ABC):
    """Abstract interface for audio I/O operations."""
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize audio hardware/devices."""
        pass
    
    @abstractmethod
    async def start_recording(self, callback: Callable[[bytes], None]) -> None:
        """Start recording audio, calling callback with chunks."""
        pass
    
    @abstractmethod
    async def stop_recording(self) -> None:
        """Stop recording audio."""
        pass
    
    @abstractmethod
    async def play_audio(self, audio_data: bytes) -> None:
        """Play audio data through speakers."""
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up audio resources."""
        pass
```

**Purpose**: Defines the contract that both PC and Pi audio implementations must follow.

### 2. PC Audio Implementation

**File: `src/audio/pc_audio_manager.py`**

- Implements `AudioInterface` using `sounddevice`
- Uses system default audio devices
- Handles audio streaming with proper buffering
- Includes error handling for device disconnection

### 3. Pi Audio Implementation

**File: `src/audio/pi_audio_manager.py`**

- Implements `AudioInterface` for I2S hardware
- Configures ALSA devices (`hw:1,0` for mic, `hw:1,1` for speaker)
- Handles Pi-specific audio quirks
- Future: May include GPIO control for audio amplifier enable/disable

### 4. WebSocket Client

**File: `src/services/websocket_client.py`**

**Responsibilities:**
- Establish and maintain WebSocket connection to server
- Handle reconnection logic with exponential backoff
- Send control messages (JSON) and audio data (binary)
- Receive and route TTS audio from server
- Emit events for connection state changes

**Key Methods:**
```python
class WebSocketClient:
    async def connect(self) -> None
    async def disconnect(self) -> None
    async def send_message(self, message: dict) -> None
    async def send_audio(self, audio_data: bytes) -> None
    async def receive_loop(self) -> None
    def on_audio_received(self, callback: Callable[[bytes], None]) -> None
    def on_connection_lost(self, callback: Callable[[], None]) -> None
```

### 5. Session Manager

**File: `src/services/session_manager.py`**

**Purpose**: Orchestrates a complete conversation session from hotword detection to completion.

**Responsibilities:**
- Coordinate between hotword detector, WebSocket client, and audio manager
- Manage session lifecycle (start, maintain, end)
- Handle timeouts and error conditions
- Ensure clean state transitions

### 6. State Machine

**File: `src/core/state_machine.py`**

**States:**
```
IDLE -> LISTENING_FOR_HOTWORD -> CONNECTING -> ACTIVE_SESSION -> IDLE
         ↑                                            ↓
         └────────────────────────────────────────────┘
```

**Purpose**: Ensures the client maintains consistent state and prevents invalid operations.

### 7. Main Application Loop

**File: `src/main.py`**

**Flow:**
```python
async def main():
    # 1. Load configuration
    # 2. Initialize audio manager (PC or Pi based on config/detection)
    # 3. Initialize hotword detector
    # 4. Initialize WebSocket client
    # 5. Setup state machine and session manager
    # 6. Main loop:
    #    - Listen for hotword
    #    - On detection: establish connection, stream audio
    #    - Handle TTS playback
    #    - Return to listening on session end
```

## Configuration Strategy

**File: `src/config/settings.py`** (enhance existing)

```python
class Config:
    # Existing audio settings...
    
    # Hardware selection
    AUDIO_BACKEND = os.getenv("AUDIO_BACKEND", "auto")  # "pc", "pi", or "auto"
    
    # Pi-specific
    PI_MIC_DEVICE = os.getenv("PI_MIC_DEVICE", "hw:1,0")
    PI_SPEAKER_DEVICE = os.getenv("PI_SPEAKER_DEVICE", "hw:1,1")
    
    # Connection settings
    RECONNECT_DELAY = 5.0
    MAX_RECONNECT_ATTEMPTS = 10
    
    # Session settings
    SESSION_TIMEOUT = 30.0
```

## Integration with Server

### Message Protocol

**Client → Server:**
```json
// Hotword detected
{"type": "hotword_detected", "timestamp": "2025-01-25T12:00:00Z"}

// Session control (future)
{"type": "end_session", "reason": "user_request"}
```

**Server → Client:**
- Binary audio data (TTS output)
- Future: JSON control messages for session state

### Connection Flow

1. **Hotword Detection**: Client detects wake word locally
2. **Connection**: Client establishes WebSocket connection to `ws://server:7456`
3. **Notification**: Client sends `{"type": "hotword_detected"}`
4. **Audio Streaming**: Client begins streaming microphone audio as binary frames
5. **TTS Reception**: Client receives and plays TTS audio from server
6. **Session End**: Server closes connection, client returns to hotword listening

## Error Handling

1. **Connection Failures**: Exponential backoff with max retries
2. **Audio Device Errors**: Graceful degradation with user notification
3. **Hotword Model Loading**: Fallback to alternative models
4. **Session Timeouts**: Clean session termination and reset

## Testing Strategy

1. **Unit Tests**: Test each component in isolation
2. **Integration Tests**: Test component interactions
3. **Mock Audio**: Use file-based audio for automated testing
4. **End-to-End**: Test complete flow with mock server

## Development Phases

### Phase 1: Core Infrastructure
- [ ] Audio abstraction interface
- [ ] PC audio implementation
- [ ] Basic WebSocket client
- [ ] Update existing hotword detector

### Phase 2: Integration
- [ ] Session manager
- [ ] State machine
- [ ] Main application loop
- [ ] Basic error handling

### Phase 3: Pi Implementation
- [ ] Pi audio manager
- [ ] Hardware detection logic
- [ ] Pi-specific optimizations

### Phase 4: Polish
- [ ] Comprehensive error handling
- [ ] Reconnection logic
- [ ] Performance optimization
- [ ] Logging and debugging tools

## Future Enhancements

1. **LED Indicators**: Visual feedback for system state
2. **Local Audio Feedback**: Acknowledgment sounds stored locally
3. **Voice Activity Detection**: Optimize when to send audio
4. **Configuration UI**: Web interface for Pi configuration
5. **Multi-Wake-Word**: Support for multiple trigger phrases