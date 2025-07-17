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
from typing import Optional, Callable
import threading
import time

try:
    from openwakeword.model import Model
except ImportError:
    raise ImportError(
        "OpenWakeWord is not installed. Please install it with: pip install openwakeword"
    )

from config.settings import Config


class HotwordService:
    """
    OpenWakeWord-based hotword detection service.
    
    Features:
    - Continuous audio buffer analysis for wake word detection
    - Configurable detection threshold
    - Thread-safe activation callbacks
    - Resource-efficient processing with rolling audio buffer
    """
    
    def __init__(self, wake_word: str = Config.HOTWORD_MODEL, threshold: float = Config.HOTWORD_THRESHOLD):
        """
        Initialize hotword detection service.
        
        Args:
            wake_word: Wake word model name (default from config)
            threshold: Detection confidence threshold (0.0-1.0)
        """
        self.wake_word = wake_word
        self.threshold = threshold
        self.is_active = False
        self.audio_buffer = []
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
        print(f"🔊 Initializing hotword detection with model: {wake_word}")
        try:
            self.model = Model(
                wakeword_models=[wake_word],
                inference_framework='onnx'  # CPU-optimized
            )
            print(f"✅ Hotword model '{wake_word}' loaded successfully")
        except Exception as e:
            print(f"❌ Failed to load hotword model '{wake_word}': {e}")
            raise
        
        # Calculate buffer management parameters
        self.samples_per_second = self.sample_rate
        self.max_buffer_size = int(self.samples_per_second * self.buffer_max_seconds)
        self.min_detection_samples = self.sample_rate  # 1 second minimum for detection
        
    def set_activation_callback(self, callback: Callable[[], None]) -> None:
        """
        Set callback function to execute when hotword is detected.
        
        Args:
            callback: Function to call when wake word is detected
        """
        with self._lock:
            self.activation_callback = callback
        print(f"🔗 Hotword activation callback registered")
        
    def start_detection(self) -> None:
        """Start hotword detection."""
        with self._lock:
            self.is_active = True
            self.audio_buffer.clear()
            # Clear OpenWakeWord model's internal prediction buffer
            self._clear_model_buffer()
            # Reset cooldown timer to prevent immediate re-detection
            self.last_detection_time = time.time()
        print(f"🎤 Hotword detection started - listening for '{self.wake_word}'...")
        
    def stop_detection(self) -> None:
        """Stop hotword detection."""
        with self._lock:
            self.is_active = False
            self.audio_buffer.clear()
            # Clear OpenWakeWord model's internal prediction buffer
            self._clear_model_buffer()
        print("🔇 Hotword detection stopped")
        
    def _clear_model_buffer(self) -> None:
        """Clear OpenWakeWord model's internal prediction buffer."""
        try:
            # Clear the model's internal prediction buffer
            if hasattr(self.model, 'prediction_buffer'):
                for key in self.model.prediction_buffer.keys():
                    self.model.prediction_buffer[key].clear()
                print("🧹 Cleared OpenWakeWord model buffer")
        except Exception as e:
            print(f"⚠️ Could not clear model buffer: {e}")
        
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
                print(f"⚠️ Error converting audio data: {e}")
                return False
            
            # Accumulate audio for model processing
            self.audio_buffer.extend(audio_np.tolist())
            
            # Maintain rolling buffer (keep only recent audio)
            if len(self.audio_buffer) > self.max_buffer_size:
                # Remove oldest samples to maintain buffer size
                excess = len(self.audio_buffer) - self.max_buffer_size
                self.audio_buffer = self.audio_buffer[excess:]
            
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
            audio_array = np.array(self.audio_buffer[-self.min_detection_samples:], dtype=np.float32)
            
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
            confidence = 0.0
            
            if hasattr(self.model, 'prediction_buffer') and self.wake_word in self.model.prediction_buffer:
                # Get the latest score for our wake word
                scores = list(self.model.prediction_buffer[self.wake_word])
                if scores:
                    confidence = scores[-1]  # Latest prediction score
            
            if confidence >= self.threshold:
                # Check cooldown to prevent multiple rapid detections
                current_time = time.time()
                if current_time - self.last_detection_time < self.cooldown_seconds:
                    print(f"🔇 Hotword detected but in cooldown period ({self.cooldown_seconds}s)")
                    return False
                
                # Update last detection time
                self.last_detection_time = current_time
                
                print(f"🚀 Hotword detected! '{self.wake_word}' (confidence: {confidence:.3f})")
                
                # Execute activation callback if set
                if self.activation_callback:
                    try:
                        self.activation_callback()
                    except Exception as e:
                        print(f"⚠️ Error in activation callback: {e}")
                
                return True
            else:
                # Optional: Log low-confidence detections for debugging
                if confidence > 0.1:  # Only log if there's some confidence
                    print(f"🔍 Low confidence detection: {confidence:.3f} (threshold: {self.threshold})")
                        
        except Exception as e:
            print(f"❌ Error during hotword detection: {e}")
            
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
                "wake_word": self.wake_word,
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
            print(f"🎯 Hotword threshold updated to: {threshold}")
        else:
            print(f"⚠️ Invalid threshold: {threshold}. Must be between 0.0 and 1.0")