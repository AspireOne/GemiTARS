"""
Local Sound Manager: Handles loading and management of local audio files.
"""

import os
import soundfile as sf
import numpy as np
from scipy.signal import resample_poly
from typing import Dict, Optional
from ..config.settings import Config
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class LocalSoundManager:
    """
    Manages local audio files by loading them into memory at startup.
    """
    WAV_FILE_EXTENSION = '.wav'

    def __init__(self):
        self.sounds: Dict[str, bytes] = {}
        self.resources_path = os.path.join(
            os.path.dirname(__file__), '..', 'resources', 'acknowledgements'
        )

    async def initialize(self) -> bool:
        """
        Load all configured acknowledgement audio files into memory, converting them
        to the required raw PCM format.
        
        Returns:
            True if initialization was successful, False otherwise.
        """
        try:
            for filename in Config.ACKNOWLEDGEMENT_AUDIO_FILES:
                file_path = os.path.join(self.resources_path, filename)
                
                if not os.path.exists(file_path):
                    logger.warning(f"Acknowledgement audio file not found: {file_path}")
                    continue
                
                try:
                    # Read WAV file as is
                    audio_data, samplerate = sf.read(file_path, dtype=Config.AUDIO_DTYPE)

                    # Convert to mono if necessary
                    if audio_data.ndim > 1 and audio_data.shape[1] > 1:
                        audio_data = np.mean(audio_data, axis=1).astype(Config.AUDIO_DTYPE)

                    # Resample if necessary
                    if samplerate != Config.AUDIO_SAMPLE_RATE:
                        num_samples = int(len(audio_data) * Config.AUDIO_SAMPLE_RATE / samplerate)
                        audio_data = resample_poly(audio_data, Config.AUDIO_SAMPLE_RATE, samplerate, window=('kaiser', 4.0))[:num_samples]
                        audio_data = audio_data.astype(Config.AUDIO_DTYPE)

                    # Convert numpy array to raw bytes
                    raw_audio_data = audio_data.tobytes()
                    
                    # Store the filename without extension as the key
                    key = os.path.splitext(filename)[0]
                    self.sounds[key] = raw_audio_data
                    logger.info(f"Loaded and converted acknowledgement sound: {filename} ({len(raw_audio_data)} bytes)")
                    
                except Exception as e:
                    logger.error(f"Error loading/converting audio file {filename}: {e}")
                    
            if not self.sounds:
                logger.warning("No acknowledgement audio files were loaded successfully")
                return False
                
            logger.info(f"LocalSoundManager initialized with {len(self.sounds)} audio files")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing LocalSoundManager: {e}", exc_info=True)
            return False

    def get_sound(self, sound_name: str) -> Optional[bytes]:
        """
        Get audio data for a specific sound.
        
        Args:
            sound_name: Name of the sound (without file extension)
            
        Returns:
            Audio data as bytes, or None if not found
        """
        
        # Strip ".wav" from sound_name if present
        if sound_name.endswith(self.WAV_FILE_EXTENSION):
            sound_name = sound_name[:-len(self.WAV_FILE_EXTENSION)]
        
        return self.sounds.get(sound_name)

    def list_available_sounds(self) -> list[str]:
        """
        Get a list of all available sound names.
        
        Returns:
            List of sound names (without file extensions)
        """
        return list(self.sounds.keys())