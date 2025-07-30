"""
Local Sound Manager: Handles loading and management of local audio files.
"""

import os
from typing import Dict, Optional
from ..config.settings import Config
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class LocalSoundManager:
    """
    Manages local audio files by loading them into memory at startup.
    """
    RAW_FILE_EXTENSION = '.raw'

    def __init__(self):
        self.sounds: Dict[str, bytes] = {}
        self.resources_path = os.path.join(
            os.path.dirname(__file__), '..', 'resources', 'acknowledgements'
        )

    async def initialize(self) -> bool:
        """
        Load all configured acknowledgement audio files into memory.
        
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
                    with open(file_path, 'rb') as f:
                        audio_data = f.read()
                    
                    # Store the filename without extension as the key
                    key = os.path.splitext(filename)[0]
                    self.sounds[key] = audio_data
                    logger.info(f"Loaded acknowledgement sound: {filename} ({len(audio_data)} bytes)")
                    
                except Exception as e:
                    logger.error(f"Error loading audio file {filename}: {e}")
                    
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
        
        # Strip ".raw" from sound_name if present
        if sound_name.endswith(self.RAW_FILE_EXTENSION):
            sound_name = sound_name[:-len(self.RAW_FILE_EXTENSION)]
        
        return self.sounds.get(sound_name)

    def list_available_sounds(self) -> list[str]:
        """
        Get a list of all available sound names.
        
        Returns:
            List of sound names (without file extensions)
        """
        return list(self.sounds.keys())