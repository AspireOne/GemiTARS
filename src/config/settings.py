import logging

"""
Simple centralized configuration for GemiTARS.
All magic values are defined here for easy maintenance.
"""

class Config:
    # Logging
    LOG_LEVEL = logging.DEBUG
    
    # Audio Settings
    AUDIO_SAMPLE_RATE = 16000
    AUDIO_BLOCK_SIZE = 1600
    AUDIO_DTYPE = 'int16'
    AUDIO_CHANNELS = 1
    AUDIO_MIME_TYPE = "audio/pcm;rate=16000"

    # Model Settings
    DEFAULT_MODEL = "gemini-live-2.5-flash-preview"

    # VAD Settings
    VAD_PREFIX_PADDING_MS = 40
    VAD_SILENCE_DURATION_MS = 900

    # Conversation Settings
    CONVERSATION_TIMEOUT_SECONDS = 30
    
    # Hotword Detection Settings
    HOTWORD_MODEL = "alexa"  # Using the default Alexa model you downloaded
    HOTWORD_THRESHOLD = 0.4
    HOTWORD_BUFFER_SECONDS = 1.5 # How long does it take to say? + buffer
    HOTWORD_REDETECTION_TIMEOUT_SECONDS = 2
    
    # ESP32 Service Settings
    ESP32_SERVICE_TYPE = "mock"  # "mock" or "real"
    
    # ElevenLabs TTS Settings
    ELEVENLABS_VOICE_ID = "dXtC3XhB9GtPusIpNtQx"
    ELEVENLABS_MODEL_ID = "eleven_flash_v2_5"  # Ultra-low latency model
    ELEVENLABS_OUTPUT_FORMAT = "pcm_16000"      # 16kHz PCM for optimal ESP32 performance
    ELEVENLABS_CHUNK_SIZE = 1024                # Streaming chunk size
    ELEVENLABS_STABILITY = 0.5                  # Voice stability (0-1)
    ELEVENLABS_SIMILARITY_BOOST = 0.75          # Voice similarity (0-1) - match demo
