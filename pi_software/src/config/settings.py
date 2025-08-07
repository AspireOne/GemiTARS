"""
Configuration settings for the GemiTARS Pi Client.
"""

import logging
import os
from dotenv import load_dotenv

load_dotenv()

# Determine the model file extension based on the inference framework
_inference_framework = os.getenv('HOTWORD_INFERENCE_FRAMEWORK', 'onnx').lower()
_model_extension = '.tflite' if _inference_framework == 'tflite' else '.onnx'

# Define model paths
hey_tars_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'resources', f'Hey_Tars{_model_extension}'))
tars_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'resources', f'Tars{_model_extension}'))
alexa_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'resources', f'alexa{_model_extension}'))

def _get_log_level():
    """Convert string log level to logging constant."""
    level_str = os.getenv('LOG_LEVEL', 'DEBUG').upper()
    return getattr(logging, level_str, logging.DEBUG)

def _get_bool_env(key, default):
    """Convert string environment variable to boolean."""
    value = os.getenv(key, str(default)).lower()
    return value in ('true', '1', 'yes', 'on')

class Config:
    # Logging
    LOG_LEVEL = _get_log_level()

    # Audio Settings (must match server)
    AUDIO_SAMPLE_RATE = 16000
    # IMPACTS LATENCY! Ideally multiples of 80ms - '1280' for 80ms or '2560' for 160ms 
    AUDIO_BLOCK_SIZE = 2560
    AUDIO_DTYPE = 'int16'
    AUDIO_CHANNELS = 1
    AUDIO_MIME_TYPE = "audio/pcm;rate=16000"
    AUDIO_PLAYBACK_QUEUE_SIZE = 1000

    # Server Connection
    SERVER_HOST = os.getenv('SERVER_HOST', 'localhost')
    SERVER_PORT = int(os.getenv('SERVER_PORT', '7456'))
    SERVER_URL = f"ws://{SERVER_HOST}:{SERVER_PORT}"

    # Audio Manager
    ENVIRONMENT = os.getenv('ENVIRONMENT', 'pc').lower()
    ALSA_INPUT_DEVICE = os.getenv('ALSA_INPUT_DEVICE', 'default')
    ALSA_OUTPUT_DEVICE = os.getenv('ALSA_OUTPUT_DEVICE', 'default')

    # Hotword Detection
    HOTWORD_INFERENCE_FRAMEWORK = _inference_framework
    # Omit "alexa" for now - needs to somehow be downloaded to the openwakeword cache.
    HOTWORD_MODELS = [alexa_path]
    HOTWORD_THRESHOLD = float(os.getenv('HOTWORD_THRESHOLD', '0.1'))  # OpenWakeWord's default is 0.5. Will need to be adjusted with the specific raspberry pi mic.
    HOTWORD_BUFFER_SECONDS = 1.4  # How long does it take to say? + buffer | TODO: Revise
    HOTWORD_REDETECTION_TIMEOUT_SECONDS = 2  # Timeout to prevent immediate re-detection
    HOTWORD_DEBUG_LOGGING = _get_bool_env('HOTWORD_DEBUG_LOGGING', False)  # Enable detailed confidence logging for debugging
    
    # Acknowledgement Audio Files
    ACKNOWLEDGEMENT_AUDIO_FILES = ['huh.wav', 'yes.wav', 'talk_to_me.wav']
    
    # Button Settings
    BUTTON_ENABLED = _get_bool_env('BUTTON_ENABLED', True)  # Enable/disable button functionality
    BUTTON_GPIO_PIN = int(os.getenv('BUTTON_GPIO_PIN', '5'))  # GPIO pin number for button
    BUTTON_DEBOUNCE_DELAY = float(os.getenv('BUTTON_DEBOUNCE_DELAY', '1'))  # Debounce delay in seconds