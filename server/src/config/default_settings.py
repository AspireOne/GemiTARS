import logging
import os
from dotenv import load_dotenv

load_dotenv()

"""
Default configuration for GemiTARS.
These are the baseline values that can be overridden by config_override.json
and persona-specific settings from personas.json.
"""

class DefaultConfig:
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
    
    # Active Persona (default)
    ACTIVE_PERSONA = "TARS"
    AVAILABLE_PERSONAS = []

    # TODO: Potentially use bidirectional WS in elevenlab? https://elevenlabs.io/docs/best-practices/latency-optimization#websockets
    # NOTE: ElevenLabs' Time-to-first-byte is >200ms in EU! https://elevenlabs.io/docs/best-practices/latency-optimization#consider-geographic-proximity

    # VAD Settings TODO: try out more values and also look at the code directly, there might be some variable missing here
    VAD_PREFIX_PADDING_MS = 40
    VAD_SILENCE_DURATION_MS = 800

    # Conversation Settings
    CONVERSATION_TIMEOUT_SECONDS = 30
    # These phrases will be sanitized at runtime to match transcript sanitization
    SESSION_END_PHRASES = [
        # Czech phrases
        "díky", "děkuji", "děkuju", "to je všechno", "to je všechno díky", "na shledanou", "měj se",
        "drž hubu", "pakuj do píči", "díky moc", "díky ti", "díky tars", "to je vše", "končím", "konec",
        "sbohem", "měj se hezky", "měj se fajn", "čau", "čauky", "nazdar", "zatím", "pa", "papa",
        
        # English phrases   
        "thank you", "thanks", "okay thanks", "okay bye", "okay goodbye", "bye", "goodbye", "we're done here",
        "we are done here", "that'll be all", "that will be all", "stand down", "end of transmission", "shut up",
        "see you", "see ya", "later", "talk to you later", "end session", "end conversation", "disconnect",
        "terminate", "stop listening", "stop", "that's all", "that's it", "done", "finished", "enough",
        "no more", "exit", "close", "abort", "over and out"
    ]
    
    # ElevenLabs TTS Settings (non-persona specific)
    ELEVENLABS_MODEL_ID = "eleven_flash_v2_5"    # Ultra-low latency model
    ELEVENLABS_OUTPUT_FORMAT = "pcm_16000"       # 16kHz PCM for optimal PI performance
    ELEVENLABS_CHUNK_SIZE = 1024                 # Streaming chunk size
    ELEVENLABS_STABILITY = 0.75                  # Voice stability (0-1)
    ELEVENLABS_SIMILARITY_BOOST = 0.75           # Voice similarity (0-1) - match demo
    
    # These are just temporary for some testing, I will delete them later
    TAPO_USERNAME = os.getenv('TAPO_USERNAME', None)
    TAPO_PASSWORD = os.getenv('TAPO_PASSWORD', None)
    TAPO_IP = os.getenv('TAPO_IP', None)
