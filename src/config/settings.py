"""
Simple centralized configuration for GemiTARS.
All magic values are defined here for easy maintenance.
"""

class Config:
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
    VAD_SILENCE_DURATION_MS = 1000

    # Conversation Settings
    CONVERSATION_TIMEOUT_SECONDS = 30