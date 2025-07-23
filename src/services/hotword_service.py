"""
HotwordService: OpenWakeWord-based hotword detection for "Alexa" activation.

This service provides:
- Continuous audio buffer analysis
- Configurable detection threshold
- Thread-safe activation callbacks
- Resource-efficient processing
- Cooldown mechanism to prevent multiple rapid detections
"""

import numpy as np
from typing import Optional, Callable, List
import threading
import time
import collections
import os
from utils.logger import setup_logger

try:
    from openwakeword.model import Model
except ImportError:
    raise ImportError(
        "OpenWakeWord is not installed. Please install it with: pip install openwakeword"
    )

from config.settings import Config

logger = setup_logger(os.path.splitext(os.path.basename(__file__))[0])


class HotwordService:
    """
    OpenWakeWord-based hotword detection service.
    
    Features:
    - Continuous audio buffer analysis for wake word detection
    - Configurable detection threshold
    - Thread-safe activation callbacks
    - Resource-efficient processing with rolling audio buffer
    """
    
    def __init__(self, wake_words: List[str] = Config.HOTWORD_MODELS, threshold: float = Config.HOTWORD_THRESHOLD):
        """
        Initialize hotword detection service.
        
        Args:
            wake_words: A list of wake word model paths (default from config)
            threshold: Detection confidence threshold (0.0-1.0)
        """
        self.wake_words = wake_words
        self.threshold = threshold
        self.is_active = False
        self.activation_callback: Optional[Callable] = None
        self._lock = threading.Lock()
        
        # Cooldown mechanism to prevent multiple rapid detections
        self.last_detection_time = 0.0
        self.cooldown_seconds = Config.HOTWORD_REDETECTION_TIMEOUT_SECONDS  # Prevent re-detection for x seconds
        
        # Audio configuration matching GemiTARS setup
        self.sample_rate = Config.AUDIO_SAMPLE_RATE  # 16kHz
        self.chunk_size = Config.AUDIO_BLOCK_SIZE    # 1600 samples
        self.buffer_max_seconds = Config.HOTWORD_BUFFER_SECONDS  # 2.0 seconds
        
        # Initialize OpenWakeWord model
        wakeword_names = [os.path.splitext(os.path.basename(w))[0] for w in wake_words]
        logger.info(f"Initializing hotword detection with models: {wakeword_names}")
        try:
            self.model = Model(
                wakeword_models=wake_words,
                inference_framework='onnx'  # CPU-optimized
            )
            logger.info(f"Hotword models '{wakeword_names}' loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load hotword models '{wakeword_names}': {e}")
            raise
        
        # Calculate buffer management parameters
        self.samples_per_second = self.sample_rate
        self.max_buffer_size = int(self.samples_per_second * self.buffer_max_seconds)
        self.audio_buffer = collections.deque(maxlen=self.max_buffer_size)
        self.min_detection_samples = self.sample_rate  # 1 second minimum for detection
        
    def set_activation_callback(self, callback: Callable[[], None]) -> None:
        """
        Set callback function to execute when hotword is detected.
        
        Args:
            callback: Function to call when wake word is detected
        """
        with self._lock:
            self.activation_callback = callback
        logger.info("Hotword activation callback registered")
        
    def start_detection(self) -> None:
        """Start hotword detection."""
        with self._lock:
            self.is_active = True
            self.audio_buffer.clear()
            # Clear OpenWakeWord model's internal prediction buffer
            self._clear_model_buffer()
            # Reset cooldown timer to prevent immediate re-detection
            self.last_detection_time = time.time()
        wakeword_names = [os.path.splitext(os.path.basename(w))[0] for w in self.wake_words]
        logger.info(f"Hotword detection started - listening for '{wakeword_names}'...")
        
    def stop_detection(self) -> None:
        """Stop hotword detection."""
        with self._lock:
            self.is_active = False
            self.audio_buffer.clear()
            # Clear OpenWakeWord model's internal prediction buffer
            self._clear_model_buffer()
        logger.info("Hotword detection stopped")
        
    def _clear_model_buffer(self) -> None:
        """Clear OpenWakeWord model's internal prediction buffer."""
        try:
            # Clear the model's internal prediction buffer
            if hasattr(self.model, 'prediction_buffer'):
                for key in self.model.prediction_buffer.keys():
                    self.model.prediction_buffer[key].clear()
                logger.debug("Cleared OpenWakeWord model buffer")
        except Exception as e:
            logger.warning(f"Could not clear model buffer: {e}")
        
    def process_audio_chunk(self, audio_data: bytes) -> bool:
        """
        Process audio chunk for hotword detection.
        
        Args:
            audio_data: Raw audio bytes from sounddevice (int16 PCM)
            
        Returns:
            bool: True if hotword was detected
        """
        with self._lock:
            if not self.is_active:
                return False
                
            # Convert bytes to numpy array (matching GemiTARS audio format)
            try:
                audio_np = np.frombuffer(audio_data, dtype=Config.AUDIO_DTYPE)
            except Exception as e:
                logger.warning(f"Error converting audio data: {e}")
                return False
            
            # Accumulate audio for model processing
            # The deque automatically handles the size limit efficiently
            self.audio_buffer.extend(audio_np)
            
            # Only process if we have enough audio for detection
            if len(self.audio_buffer) >= self.min_detection_samples:
                return self._run_detection()
                
        return False
        
    def _run_detection(self) -> bool:
        """
        Run hotword detection on current audio buffer.
        
        Returns:
            bool: True if hotword was detected
        """
        try:
            # Convert buffer to numpy array for OpenWakeWord
            audio_array = np.array(self.audio_buffer, dtype=np.float32)
            
            # Normalize audio to [-1, 1] range (OpenWakeWord expects float32)
            if audio_array.dtype == np.int16:
                audio_array = audio_array.astype(np.float32) / 32768.0
            elif audio_array.dtype != np.float32:
                audio_array = audio_array.astype(np.float32)
            
            # Run hotword detection
            # Note: predict() processes the audio but scores are in prediction_buffer
            self.model.predict(audio_array)
            
            # Check prediction buffer for wake word scores
            # Based on official OpenWakeWord implementation
            max_confidence = 0.0
            
            for wake_word_path in self.wake_words:
                model_name = os.path.splitext(os.path.basename(wake_word_path))[0]
                
                if hasattr(self.model, 'prediction_buffer') and model_name in self.model.prediction_buffer:
                    # Get the latest score for our wake word
                    scores = list(self.model.prediction_buffer[model_name])
                    if scores:
                        confidence = scores[-1]  # Latest prediction score
                        max_confidence = max(max_confidence, confidence)

                        if confidence >= self.threshold:
                            # Check cooldown to prevent multiple rapid detections
                            current_time = time.time()
                            if current_time - self.last_detection_time < self.cooldown_seconds:
                                logger.info(f"Hotword '{model_name}' detected but in cooldown period ({self.cooldown_seconds}s)")
                                return False
                            
                            # Update last detection time
                            self.last_detection_time = current_time
                            
                            logger.info(f"Hotword detected! '{model_name}' (confidence: {confidence:.3f})")
                            
                            # Execute activation callback if set
                            if self.activation_callback:
                                try:
                                    self.activation_callback()
                                except Exception as e:
                                    logger.warning(f"Error in activation callback: {e}")
                            
                            return True

            # Optional: Log low-confidence detections for debugging
            if max_confidence > 0.1:  # Only log if there's some confidence
                logger.debug(f"Low confidence detection: {max_confidence:.3f} (threshold: {self.threshold})")
                        
        except Exception as e:
            logger.error(f"Error during hotword detection: {e}")
            
        return False
        
    def get_status(self) -> dict:
        """
        Get current status of hotword detection.
        
        Returns:
            dict: Status information
        """
        with self._lock:
            return {
                "is_active": self.is_active,
                "wake_words": self.wake_words,
                "threshold": self.threshold,
                "buffer_size": len(self.audio_buffer),
                "buffer_seconds": len(self.audio_buffer) / self.sample_rate if self.audio_buffer else 0,
                "has_callback": self.activation_callback is not None
            }
            
    def set_threshold(self, threshold: float) -> None:
        """
        Update detection threshold.
        
        Args:
            threshold: New threshold value (0.0-1.0)
        """
        if 0.0 <= threshold <= 1.0:
            with self._lock:
                self.threshold = threshold
            logger.info(f"Hotword threshold updated to: {threshold}")
        else:
            logger.warning(f"Invalid threshold: {threshold}. Must be between 0.0 and 1.0")