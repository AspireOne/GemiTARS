"""
Configuration settings for the GemiTARS Pi Client.
"""

import logging
import os

hey_tars_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'resources', 'Hey_Tars.onnx'))
tars_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'resources', 'Tars.onnx'))

class Config:
    # Logging
    LOG_LEVEL = logging.DEBUG

    # Audio Settings (must match server)
    AUDIO_SAMPLE_RATE = 16000
    AUDIO_BLOCK_SIZE = 1600  # 100ms of audio
    AUDIO_DTYPE = 'int16'
    AUDIO_CHANNELS = 1
    AUDIO_MIME_TYPE = "audio/pcm;rate=16000"

    # Server Connection
    SERVER_HOST = "localhost"
    SERVER_PORT = 7456
    SERVER_URL = f"ws://{SERVER_HOST}:{SERVER_PORT}"

    # Omit "alexa" for now - needs to somehow be downloaded to the openwakeword cache.
    HOTWORD_MODELS = [hey_tars_path, tars_path]
    HOTWORD_THRESHOLD = 0.2 # OpenWakeWord's default is 0.5. Will need to be adjusted with the specific esp32 mic.
    HOTWORD_BUFFER_SECONDS = 1.4 # How long does it take to say? + buffer
    HOTWORD_REDETECTION_TIMEOUT_SECONDS = 2
    HOTWORD_DEBUG_LOGGING = True  # Enable detailed confidence logging for debugging