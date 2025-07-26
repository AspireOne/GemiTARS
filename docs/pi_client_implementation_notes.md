# Raspberry Pi General Client Implementation

The Python application in `pi_software/` must perform the following tasks:

1.  **Audio Setup:**
    -   Use a library like `sounddevice` or `PyAudio` to interface with the I2S microphone and speaker via ALSA, as configured in the OS.
2.  **Local Hotword Detection:**
    -   Continuously read from the microphone.
    -   Feed the audio into an instance of `openwakeword`.
    -   When the wake word ("Hey, TARS!") is detected, proceed to the next step.
3.  **Server Connection:**
    -   On hotword detection, establish a WebSocket connection to the main server.
    -   Play a local acknowledgment sound ("mhm," "listening...").
4.  **Audio Streaming:**
    -   Stream live microphone audio to the server over the WebSocket connection.
    -   Simultaneously, listen for incoming audio from the server (the TTS response).
    -   Play the received TTS audio through the speaker.
5.  **Session Management:**
    -   If the server closes the connection (e.g., due to a timeout), the client should disconnect, stop streaming, and return to local hotword detection.
    

## Notes: Possible structure for future shared configs etc. with the server repo 

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

## Audio settings that might need runtime adjustment
HOTWORD_THRESHOLD=0.3
AUDIO_BLOCK_SIZE=1600

.env.pi

SERVER_HOST=192.168.1.100
AUDIO_INPUT_DEVICE=hw:1,0
AUDIO_OUTPUT_DEVICE=hw:1,1

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