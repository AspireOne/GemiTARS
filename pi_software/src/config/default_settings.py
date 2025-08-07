"""
Default configuration settings for the GemiTARS Pi Client.
These values are loaded first and can be overridden by local settings or environment variables.
"""

import logging
import os

class DefaultConfig:
    # Logging
    LOG_LEVEL = logging.DEBUG

    # Audio Settings (must match server)
    AUDIO_SAMPLE_RATE = 16000
    # IMPACTS LATENCY! Ideally multiples of 80ms - '1280' for 80ms or '2560' for 160ms 
    AUDIO_BLOCK_SIZE = 2560
    AUDIO_DTYPE = 'int16'
    AUDIO_CHANNELS = 1
    AUDIO_MIME_TYPE = "audio/pcm;rate=16000"
    AUDIO_PLAYBACK_QUEUE_SIZE = 1000

    # Server Connection
    SERVER_HOST = 'localhost'
    SERVER_PORT = 7456
    # SERVER_URL will be constructed dynamically

    # Audio Manager
    ENVIRONMENT = 'pc'  # 'pc' or 'pi'
    ALSA_INPUT_DEVICE = 'default'
    ALSA_OUTPUT_DEVICE = 'default'

    # Hotword Detection
    HOTWORD_INFERENCE_FRAMEWORK = 'onnx'  # 'onnx' or 'tflite'
    HOTWORD_MODELS = []  # Will be populated dynamically based on framework
    HOTWORD_THRESHOLD = 0.1
    HOTWORD_BUFFER_SECONDS = 1.4  # How long does it take to say? + buffer | TODO: Revise
    HOTWORD_REDETECTION_TIMEOUT_SECONDS = 2  # Timeout to prevent immediate re-detection
    HOTWORD_DEBUG_LOGGING = False  # Enable detailed confidence logging for debugging
    
    # Acknowledgement Audio Files
    ACKNOWLEDGEMENT_AUDIO_FILES = ['huh.raw', 'yes.raw']
    
    # Button Settings
    BUTTON_ENABLED = True  # Enable/disable button functionality
    BUTTON_GPIO_PIN = 5  # GPIO pin number for button
    BUTTON_DEBOUNCE_DELAY = 1.0  # Debounce delay in seconds