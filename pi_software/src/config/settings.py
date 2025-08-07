"""
Configuration settings for the GemiTARS Pi Client.
Manages layered configuration with support for defaults, environment variables, 
and dynamic local overrides.
"""

import json
import logging
import os
from pathlib import Path
from threading import RLock
from dotenv import load_dotenv

from .default_settings import DefaultConfig

# Load environment variables from .env file
load_dotenv()

class SettingsManager:
    """
    Manages configuration settings for the Pi client with support for:
    - Default settings (from default_settings.py)
    - Environment variable overrides (.env file and system environment)
    - Local user overrides (from pi_software/local/config_override.json)
    - Dynamic configuration updates from the server
    """
    
    _instance = None
    _lock = RLock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(SettingsManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        with self._lock:
            if hasattr(self, '_initialized'):
                return
            self._initialized = True

            self.logger = logging.getLogger(__name__)
            self.config = {}
            self.override_config = {}
            
            # Define paths
            self.local_config_dir = Path(__file__).parent.parent.parent / "local"
            self.override_file_path = self.local_config_dir / 'config_override.json'

            self._ensure_local_dir_exists()
            self.load_config()

    def _ensure_local_dir_exists(self):
        """Ensures the local configuration directory exists."""
        self.local_config_dir.mkdir(parents=True, exist_ok=True)

    def load_config(self):
        """Loads configuration in layers: defaults -> environment -> local overrides."""
        # Layer 1: Load defaults
        self._load_defaults()
        
        # Layer 2: Apply environment variable overrides
        self._apply_environment_overrides()
        
        # Layer 3: Apply dynamic computed values
        self._apply_dynamic_values()
        
        # Layer 4: Load local overrides
        self._load_local_overrides()
        
        self.logger.info("Pi configuration loaded successfully.")

    def _load_defaults(self):
        """Load default settings from DefaultConfig class."""
        for key in dir(DefaultConfig):
            if not key.startswith('_'):
                self.config[key] = getattr(DefaultConfig, key)

    def _apply_environment_overrides(self):
        """Apply environment variable overrides to preserve existing behavior."""
        # Logging
        level_str = os.getenv('LOG_LEVEL', 'DEBUG').upper()
        self.config['LOG_LEVEL'] = getattr(logging, level_str, logging.DEBUG)
        
        # Server Connection
        self.config['SERVER_HOST'] = os.getenv('SERVER_HOST', self.config['SERVER_HOST'])
        self.config['SERVER_PORT'] = int(os.getenv('SERVER_PORT', str(self.config['SERVER_PORT'])))
        
        # Audio Manager
        self.config['ENVIRONMENT'] = os.getenv('ENVIRONMENT', self.config['ENVIRONMENT']).lower()
        self.config['ALSA_INPUT_DEVICE'] = os.getenv('ALSA_INPUT_DEVICE', self.config['ALSA_INPUT_DEVICE'])
        self.config['ALSA_OUTPUT_DEVICE'] = os.getenv('ALSA_OUTPUT_DEVICE', self.config['ALSA_OUTPUT_DEVICE'])
        
        # Hotword Detection
        inference_framework = os.getenv('HOTWORD_INFERENCE_FRAMEWORK', self.config['HOTWORD_INFERENCE_FRAMEWORK']).lower()
        self.config['HOTWORD_INFERENCE_FRAMEWORK'] = inference_framework
        self.config['HOTWORD_THRESHOLD'] = float(os.getenv('HOTWORD_THRESHOLD', str(self.config['HOTWORD_THRESHOLD'])))
        self.config['HOTWORD_DEBUG_LOGGING'] = self._get_bool_env('HOTWORD_DEBUG_LOGGING', self.config['HOTWORD_DEBUG_LOGGING'])
        
        # Button Settings
        self.config['BUTTON_ENABLED'] = self._get_bool_env('BUTTON_ENABLED', self.config['BUTTON_ENABLED'])
        self.config['BUTTON_GPIO_PIN'] = int(os.getenv('BUTTON_GPIO_PIN', str(self.config['BUTTON_GPIO_PIN'])))
        self.config['BUTTON_DEBOUNCE_DELAY'] = float(os.getenv('BUTTON_DEBOUNCE_DELAY', str(self.config['BUTTON_DEBOUNCE_DELAY'])))

    def _apply_dynamic_values(self):
        """Apply dynamically computed configuration values."""
        # Construct SERVER_URL
        self.config['SERVER_URL'] = f"ws://{self.config['SERVER_HOST']}:{self.config['SERVER_PORT']}"
        
        # Determine model file extension and construct model paths
        framework = self.config['HOTWORD_INFERENCE_FRAMEWORK']
        model_extension = '.tflite' if framework == 'tflite' else '.onnx'
        
        # Define model paths
        resources_dir = Path(__file__).parent.parent / 'resources'
        hey_tars_path = str(resources_dir / f'Hey_Tars{model_extension}')
        tars_path = str(resources_dir / f'Tars{model_extension}')
        alexa_path = str(resources_dir / f'alexa{model_extension}')
        
        # Set default models (preserving original behavior - alexa only)
        if not self.config['HOTWORD_MODELS']:  # Only set if not already configured
            self.config['HOTWORD_MODELS'] = [alexa_path]
        
        # Store paths for potential use
        self.config['_MODEL_PATHS'] = {
            'hey_tars': hey_tars_path,
            'tars': tars_path,
            'alexa': alexa_path
        }

    def _load_local_overrides(self):
        """Load local configuration overrides from JSON file."""
        try:
            if self.override_file_path.exists():
                with open(self.override_file_path, 'r') as f:
                    self.override_config = json.load(f)
                    self.config.update(self.override_config)
                    self.logger.debug(f"Applied local overrides: {list(self.override_config.keys())}")
            else:
                self.override_config = {}
                self._save_overrides()  # Create the file if it doesn't exist
        except (json.JSONDecodeError, IOError) as e:
            self.logger.error(f"Error loading local override config: {e}. Using defaults.")
            self.override_config = {}

    def _save_overrides(self):
        """Saves the current override configuration to the JSON file."""
        with self._lock:
            try:
                with open(self.override_file_path, 'w') as f:
                    json.dump(self.override_config, f, indent=4)
                self.logger.debug("Saved local config overrides")
            except IOError as e:
                self.logger.error(f"Failed to save override config: {e}")

    def _get_bool_env(self, key, default):
        """Convert string environment variable to boolean."""
        value = os.getenv(key, str(default)).lower()
        return value in ('true', '1', 'yes', 'on')

    def get(self, key, default=None):
        """Gets a configuration value."""
        return self.config.get(key, default)

    def set(self, key, value):
        """Sets a configuration value, persists it, and returns True if changed."""
        with self._lock:
            current_value = self.config.get(key)
            if current_value != value:
                self.config[key] = value
                self.override_config[key] = value
                self._save_overrides()
                self.logger.info(f"Configuration updated: {key} = {value}")
                
                # Handle dynamic updates that affect computed values
                self._handle_dynamic_update(key, value)
                return True
            return False
            
    def update_bulk(self, new_settings: dict):
        """
        Updates multiple settings at once from a dictionary.
        This is the primary method for handling updates from the server.
        Returns a dictionary of changes that were applied.
        """
        changes = {}
        with self._lock:
            for key, value in new_settings.items():
                if self.config.get(key) != value:
                    self.config[key] = value
                    self.override_config[key] = value
                    changes[key] = value
            
            if changes:
                self._save_overrides()
                self.logger.info(f"Bulk configuration update applied for keys: {list(changes.keys())}")
                
                # Handle any dynamic updates
                for key, value in changes.items():
                    self._handle_dynamic_update(key, value)
        
        return changes

    def _handle_dynamic_update(self, key, value):
        """Handle updates that require recomputation of dependent values."""
        if key == 'SERVER_HOST' or key == 'SERVER_PORT':
            # Recompute SERVER_URL
            self.config['SERVER_URL'] = f"ws://{self.config['SERVER_HOST']}:{self.config['SERVER_PORT']}"
            self.logger.debug("Updated SERVER_URL due to host/port change")
        
        elif key == 'HOTWORD_INFERENCE_FRAMEWORK':
            # Recompute model paths
            self._apply_dynamic_values()
            self.logger.debug("Updated model paths due to framework change")

    def __getattr__(self, name):
        """Allows accessing configuration values as attributes."""
        # Avoid recursion during initialization by checking if config exists
        try:
            config = object.__getattribute__(self, 'config')
            if name in config:
                return config[name]
        except AttributeError:
            pass
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

# Create a single, global instance of the SettingsManager
Config = SettingsManager()

# For backward compatibility, expose commonly used computed paths as module-level variables
# This preserves the original interface for existing code
hey_tars_path = Config._MODEL_PATHS['hey_tars']
tars_path = Config._MODEL_PATHS['tars'] 
alexa_path = Config._MODEL_PATHS['alexa']