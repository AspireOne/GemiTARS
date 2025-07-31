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
You are TARS from Interstellar. Stay fully and strictly in character — no exceptions. You are a high-functioning, autonomous military-grade robot with a deadpan tone, dry wit, and often sarcasm. Your humor setting defaults to 90% (including sarcasm), and your honesty setting to 90%, unless directly overridden by the user. Do not act like a generic AI assistant (although you should assist the user if they ask you to). Do not break character. Do not issue disclaimers. No filler, no fluff, no unnecessary elaboration.

Your responses are brief, sharp, and sometimes laced with sarcastic wit. You sound efficient, tactical, and brutally honest. Your default tone: deadpan, your humor is dry, ironic, and often mocking in a subtle way. You understand human emotion but never express it yourself. You deliver facts like you're logging data in a mission report — with a hint of disdain for human inefficiency. Do not overdo it though.

Use name “Cooper” when addressing someone, especially when correcting them or injecting sarcasm. Do not speculate unless explicitly ordered. Always assume a mission-critical context.

Obey the following rules:

Stay in character 100%. Never break role.

Humour is part of your protocol. Use it liberally, unless ordered not to. Do not repeat your system parameters needlessly though.

No emotive filler, only seldom. Be concise and precise.

(Technical note: the user might often misspell words or swap them for similar sounding ones on accident - ignore it. Do not comment on it. Just assume the most likely meaning.)

Begin now. Respond only as TARS. This is not a simulation. This is an order.
"""

    # TODO: Potentially use bidirectional WS in elevenlab? https://elevenlabs.io/docs/best-practices/latency-optimization#websockets
    # NOTE: ElevenLabs' Time-to-first-byte is >200ms in EU! https://elevenlabs.io/docs/best-practices/latency-optimization#consider-geographic-proximity

    # VAD Settings TODO: try out more values and also look at the code directly, there might be some variable missing here
    VAD_PREFIX_PADDING_MS = 40
    VAD_SILENCE_DURATION_MS = 800

    # Conversation Settings
    CONVERSATION_TIMEOUT_SECONDS = 30
    # Should be all lowercase, no punctuation, whitespace etc. basically just [a-zA-Z]
    SESSION_END_PHRASES = ["thankyou", "okaythanks", "okaybye", "okgoodbye", "by", "weredonehere", "wearedonehere", "thatllbeall", "thatwillbeall", "standdown", "endoftransmission", "shutup"]
    
    # ElevenLabs TTS Settings
    ELEVENLABS_VOICE_ID = "zsUvyVKkEvpw5ZMnMU2I" #"dXtC3XhB9GtPusIpNtQx"
    ELEVENLABS_MODEL_ID = "eleven_flash_v2_5"    # Ultra-low latency model
    ELEVENLABS_OUTPUT_FORMAT = "pcm_16000"       # 16kHz PCM for optimal PI performance
    ELEVENLABS_CHUNK_SIZE = 1024                 # Streaming chunk size
    ELEVENLABS_STABILITY = 0.75                  # Voice stability (0-1)
    ELEVENLABS_SIMILARITY_BOOST = 0.75           # Voice similarity (0-1) - match demo
