# Server Refactoring Plan: Single-Client Architecture

This document outlines the step-by-step plan for refactoring the GemiTARS server to support the new Raspberry Pi client. The architecture will be designed to handle a single client connection at a time.

---

## **Step 1: Create `PiInterfaceService` Skeleton**

*   **Goal:** Create the new service's abstract interface, defining the contract for how `TARSAssistant` will communicate with the Raspberry Pi.
*   **Action:** Create a new file, `src/services/pi_interface.py`. This file will contain an abstract base class `PiInterfaceService` that defines all the necessary methods for communication (e.g., `initialize`, `play_audio_chunk`, `shutdown`, `set_callbacks`). This provides a clean blueprint for the concrete implementation and makes refactoring `TARSAssistant` straightforward.

---

## **Step 2: Refactor `TARSAssistant` for New Interface**

*   **Goal:** Decouple `TARSAssistant` from the obsolete ESP32 and hotword services and connect it to the new `PiInterfaceService`.
*   **Actions in `src/main.py`:**
    1.  **Replace Imports**: Remove imports for `ESP32ServiceInterface`, `ESP32MockService`, and `HotwordService`. Add an import for the new `PiInterfaceService`.
    2.  **Update `__init__`**: Replace `self.esp32_service` and `self.hotword_service` with a single `self.pi_service`.
    3.  **Delete Obsolete Methods**: Remove `_initialize_esp32_service()`, `_route_audio_based_on_state()`, and `_on_hotword_detected()`.
    4.  **Adapt Core Logic**:
        *   The `run()` method will now initialize and start the `pi_service`.
        *   `_enter_active_mode()` will be triggered by a callback from the `pi_service` when the client signals a hotword was detected.
        *   `_stream_tts_response()` will use `self.pi_service.play_audio_chunk()` to send audio to the Pi.

---

## **Step 3: Implement `PiInterfaceService` WebSocket Logic**

*   **Goal:** Build the concrete implementation of the `PiInterfaceService` that handles the actual WebSocket communication.
*   **Actions:**
    1.  **Create `PiWebsocketService`**: Create a new class, likely in a new file like `src/services/pi_websocket_service.py`, that implements the `PiInterfaceService` abstract class.
    2.  **Implement WebSocket Server**: This class will start and manage a WebSocket server. It will be designed to handle only one client connection at a time.
    3.  **Implement Message Handling**: The server will listen for messages and distinguish between:
        *   **JSON commands** (e.g., `{"type": "hotword_detected"}`) which will trigger callbacks into `TARSAssistant`.
        *   **Binary audio data**, which will be passed back to `TARSAssistant` to be forwarded to the `GeminiService`.
    4.  **Implement Audio Playback**: The `play_audio_chunk` method will send binary TTS audio from the server to the connected client.

---

## **Step 4: Final Integration and Cleanup**

*   **Goal:** Ensure the new system works correctly and remove all obsolete files.
*   **Actions:**
    1.  **Integration Test**: Verify the complete, end-to-end communication flow.
    2.  **Delete Obsolete Files**: Permanently delete `src/services/esp32_interface.py`, `src/services/esp32_mock_service.py`, and `src/services/_hotword_service_deprecated.py`.
    
    
    
    
    
    
    
    
    
---

## Other unrelated info (TODO)

Configuration Strategy Analysis
Shared Configuration Elements:
Audio Settings - These MUST be identical:

Sample rate (16kHz)
Audio format (16-bit PCM)
Channels (mono)
Block size for streaming
Communication Protocol - These MUST match:

WebSocket port
Message formats (JSON schemas)
Audio chunk sizes
Hotword Models - Potentially shared:

Model files (.onnx files in src/resources/)
Threshold values
Detection parameters
Separate Configuration Elements:
Server-Specific:

Gemini API keys
ElevenLabs API keys
System prompts
Conversation timeouts
Pi-Specific:

Audio device configurations (ALSA settings)
GPIO pin mappings
Local file paths
Hardware-specific parameters
My Recommendation: Hybrid Approach
Structure:
GemiTARS/
├── shared_config/
│   ├── audio_config.py      # Shared audio settings
│   ├── protocol_config.py   # WebSocket/communication settings
│   └── hotword_config.py    # Shared hotword parameters
├── src/
│   ├── config/
│   │   └── settings.py      # Server-specific config (imports from shared)
│   └── ...
├── pi_software/
│   ├── config/
│   │   └── settings.py      # Pi-specific config (imports from shared)
│   └── ...
├── .env.server              # Server environment variables
├── .env.pi                  # Pi environment variables
└── .env.shared              # Shared environment variables

txt


Implementation Example:
shared_config/audio_config.py:

class AudioConfig:
    SAMPLE_RATE = 16000
    CHANNELS = 1
    DTYPE = 'int16'
    BLOCK_SIZE = 1600
    MIME_TYPE = "audio/pcm;rate=16000"

python


shared_config/protocol_config.py:

class ProtocolConfig:
    WEBSOCKET_PORT = 7456
    WEBSOCKET_HOST = "0.0.0.0"
    
    # Message types
    MSG_HOTWORD_DETECTED = "hotword_detected"
    MSG_SPEECH_ENDED = "speech_ended"

python


src/config/settings.py (Server):

from shared_config.audio_config import AudioConfig
from shared_config.protocol_config import ProtocolConfig

class Config(AudioConfig, ProtocolConfig):
    # Server-specific settings
    DEFAULT_MODEL = "gemini-live-2.5-flash-preview"
    SYSTEM_PROMPT = "..."
    CONVERSATION_TIMEOUT_SECONDS = 30
    
    # From environment
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

python


pi_software/config/settings.py (Pi):

from shared_config.audio_config import AudioConfig
from shared_config.protocol_config import ProtocolConfig

class PiConfig(AudioConfig, ProtocolConfig):
    # Pi-specific settings
    AUDIO_INPUT_DEVICE = "hw:1,0"  # I2S microphone
    AUDIO_OUTPUT_DEVICE = "hw:1,1"  # I2S speaker
    
    # From environment
    SERVER_HOST = os.getenv("SERVER_HOST", "192.168.1.100")
    SERVER_PORT = os.getenv("SERVER_PORT", ProtocolConfig.WEBSOCKET_PORT)

python


Environment Variables Strategy:
.env.shared:

# Audio settings that might need runtime adjustment
HOTWORD_THRESHOLD=0.3
AUDIO_BLOCK_SIZE=1600

txt


.env.server:

GEMINI_API_KEY=your_key_here
ELEVENLABS_API_KEY=your_key_here
ELEVENLABS_VOICE_ID=zsUvyVKkEvpw5ZMnMU2I

txt


.env.pi:

SERVER_HOST=192.168.1.100
AUDIO_INPUT_DEVICE=hw:1,0
AUDIO_OUTPUT_DEVICE=hw:1,1

txt


Benefits of This Approach:
DRY Principle: Audio and protocol settings are defined once
Consistency: Impossible to have mismatched audio formats
Flexibility: Each component can have its own specific settings
Environment Separation: Different deployment environments are cleanly separated
Easy Updates: Change audio format once, both components update
What Should Definitely Be Shared:
Audio configuration (sample rate, format, etc.)
WebSocket port and message formats
Hotword model references and thresholds
Any constants that define the communication protocol
What Should Remain Separate:
API keys and secrets
Hardware-specific configurations
File paths and device names
Component-specific timeouts and behaviors