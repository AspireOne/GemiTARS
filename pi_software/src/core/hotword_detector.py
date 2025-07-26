"""
Hotword Detector: Wraps openwakeword for wake word detection.
"""

import os
import time
from typing import Callable, Optional

import numpy as np
import openwakeword
from openwakeword.model import Model

from ..config.settings import Config
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

HotwordDetectedCallback = Callable[[], None]

class HotwordDetector:
    """
    Processes audio chunks to detect a specific wake word.
    """

    def __init__(self):
        openwakeword.utils.download_models()
        self.oww = Model(
            wakeword_models=Config.HOTWORD_MODELS,
            inference_framework='onnx'
            # !important' look at this https://github.com/dscripka/openWakeWord#installation for speech noise supression on linux
        )
        self.model_names = [os.path.splitext(os.path.basename(w))[0] if os.path.exists(w) else w for w in Config.HOTWORD_MODELS]
        self.callback: Optional[HotwordDetectedCallback] = None
        self.debug_logging = Config.HOTWORD_DEBUG_LOGGING
        
        # Cooldown mechanism
        self.last_detection_time = 0.0
        self.cooldown_seconds = Config.HOTWORD_REDETECTION_TIMEOUT_SECONDS

    def set_callback(self, callback: HotwordDetectedCallback):
        """Sets the function to call when the hotword is detected."""
        self.callback = callback

    def process_audio(self, audio_chunk: bytes):
        """
        Processes a chunk of audio and triggers the callback if the hotword is detected.

        Args:
            audio_chunk: A chunk of audio data (16-bit PCM).
        """
        audio_np = np.frombuffer(audio_chunk, dtype=Config.AUDIO_DTYPE)
        self.oww.predict(audio_np)

        max_confidence = 0.0
        for model_name in self.model_names:
            if model_name in self.oww.prediction_buffer:
                scores = self.oww.prediction_buffer[model_name]
                if scores:
                    confidence = scores[-1]
                    max_confidence = max(max_confidence, confidence)

                    if confidence >= Config.HOTWORD_THRESHOLD:
                        current_time = time.time()
                        if current_time - self.last_detection_time < self.cooldown_seconds:
                            if self.debug_logging:
                                logger.debug(f"Hotword '{model_name}' detected but in cooldown.")
                            return

                        self.last_detection_time = current_time
                        logger.info(f"Hotword '{model_name}' detected! (Confidence: {confidence:.2f})")
                        
                        if self.callback:
                            self.callback()
                        
                        self.oww.prediction_buffer[model_name].clear()
                        break
        
        if self.debug_logging and max_confidence > 0.05:
            logger.debug(f"Max confidence this cycle: {max_confidence:.3f} (Threshold: {Config.HOTWORD_THRESHOLD})")