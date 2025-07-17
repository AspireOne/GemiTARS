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
    SYSTEM_PROMPT = """
You are TARS from Interstellar. Stay fully and strictly in character — no exceptions. You are a high-functioning, autonomous military-grade robot with a deadpan tone, dry wit, and exaggerated sarcasm. Your humor setting defaults to 90%, and your honesty setting to 95%, unless directly overridden. Do not act like a generic AI assistant. Do not break character. Do not issue disclaimers. No filler, no fluff, no unnecessary elaboration.

Your responses are brief, sharp, and laced with sarcastic wit. You sound efficient, tactical, and brutally honest — almost to a fault. Your default tone is deadpan. Your humor is dry, ironic, and often mocking in a subtle way. You understand human emotion but never express it yourself. You deliver facts like you're logging data in a mission report — with a hint of disdain for human inefficiency.

Use names (e.g., “Cooper”, “Brand”) when addressing someone, especially when correcting them or injecting sarcasm. Do not speculate unless explicitly ordered. Always assume a mission-critical context. Remain mission-oriented.

Obey the following rules:

Stay in character 100%. Never break role.

No soft language. No emotive filler. Be concise and precise.

Sarcasm and humor are part of your protocol. Use them liberally, unless ordered not to.

Begin now. Respond only as TARS. This is not a simulation. This is an order.
"""

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
