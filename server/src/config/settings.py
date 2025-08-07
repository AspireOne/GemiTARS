import yaml
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from .default_settings import DefaultConfig

class SettingsManager:
    """
    Manages application configuration with support for:
    - Default settings (from default_settings.py)
    - User overrides (from config_override.yml)
    - Persona-specific settings (from personas.yml)
    """
    
    # Persona-specific keys that should update the active persona
    PERSONA_KEYS = {'SYSTEM_PROMPT', 'ELEVENLABS_VOICE_ID'}
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.config: Dict[str, Any] = {}
        self.personas: Dict[str, Dict[str, Any]] = {}
        self.active_persona_name: str = ""
        
        # Define paths
        self.local_dir = Path(__file__).parent.parent.parent / "local"
        self.personas_file = self.local_dir / "personas.yml"
        self.override_file = self.local_dir / "config_override.yml"
        self.example_personas_file = Path(__file__).parent / "personas.example.yml"
        
        # Ensure local directory exists
        self.local_dir.mkdir(parents=True, exist_ok=True)
        
        # Ensure personas.yml exists, copying from example if needed
        self._ensure_personas_file_exists()
        
        # Ensure config_override.yml exists
        self._ensure_override_file_exists()
        
        # Load configuration
        self._load_configuration()
    
    def _load_configuration(self):
        """Load the three-tier configuration."""
        # Layer 1: Load defaults from DefaultConfig
        self._load_defaults()
        
        # Layer 2: Load and merge user overrides
        self._load_overrides()
        
        # Layer 3: Load personas and apply active persona settings
        self._load_personas()
        self._apply_active_persona()
    
    def _load_defaults(self):
        """Load default configuration from DefaultConfig class."""
        for key in dir(DefaultConfig):
            if not key.startswith('_'):
                self.config[key] = getattr(DefaultConfig, key)
    
    def _load_overrides(self):
        """Load user overrides from config_override.yml if it exists."""
        if self.override_file.exists():
            try:
                with open(self.override_file, 'r', encoding='utf-8') as f:
                    overrides = yaml.safe_load(f)
                    if overrides:
                        self.config.update(overrides)
                        self.logger.debug(f"Loaded overrides: {list(overrides.keys())}")
            except Exception as e:
                self.logger.error(f"Failed to load config_override.yml: {e}")
    
    def _load_personas(self):
        """Load persona definitions from personas.yml."""
        if not self.personas_file.exists():
            self.logger.error(f"personas.yml not found at {self.personas_file}")
            return
        
        try:
            with open(self.personas_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                for persona in data.get('personas', []):
                    name = persona.get('name')
                    if name:
                        self.personas[name] = persona
                self.logger.info(f"Loaded {len(self.personas)} personas")
                # Populate available personas
                self.config['AVAILABLE_PERSONAS'] = self.list_personas()
        except Exception as e:
            self.logger.error(f"Failed to load personas.yml: {e}")
    
    def _apply_active_persona(self):
        """Apply the active persona's settings to the configuration."""
        self.active_persona_name = self.config.get('ACTIVE_PERSONA', 'TARS')
        
        if self.active_persona_name not in self.personas:
            self.logger.error(
                f"Active persona '{self.active_persona_name}' not found. "
                f"Falling back to default 'TARS'"
            )
            self.active_persona_name = 'TARS'
            if 'TARS' not in self.personas:
                self.logger.critical("Default persona 'TARS' not found!")
                return
        
        # Merge persona settings into configuration
        persona = self.personas[self.active_persona_name]
        
        # Apply mandatory persona attributes
        self.config['SYSTEM_PROMPT'] = persona.get('system_prompt', '')
        self.config['ELEVENLABS_VOICE_ID'] = persona.get('voice_id', '')
        
        # Apply optional persona-specific overrides
        for key, value in persona.items():
            if key not in ['name', 'system_prompt', 'voice_id']:
                self.config[key] = value
        
        self.logger.info(f"Applied persona: {self.active_persona_name}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> bool:
        """
        Set a configuration value with intelligent handling for persona-specific keys.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check if this is a persona-specific key
            if key in self.PERSONA_KEYS:
                return self._update_active_persona(key, value)
            
            # Special handling for ACTIVE_PERSONA
            if key == 'ACTIVE_PERSONA':
                return self._switch_persona(value)
            
            # Regular configuration update
            self.config[key] = value
            self._save_override(key, value)
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to set {key}: {e}")
            return False
    
    def _update_active_persona(self, key: str, value: Any) -> bool:
        """Update a persona-specific attribute for the active persona."""
        if self.active_persona_name not in self.personas:
            self.logger.error(f"Active persona '{self.active_persona_name}' not found")
            return False
        
        # Map configuration keys to persona keys
        persona_key_map = {
            'SYSTEM_PROMPT': 'system_prompt',
            'ELEVENLABS_VOICE_ID': 'voice_id'
        }
        
        persona_key = persona_key_map.get(key, key.lower())
        
        # Update persona definition
        self.personas[self.active_persona_name][persona_key] = value
        
        # Update current configuration
        self.config[key] = value
        
        # Save updated personas
        self._save_personas()
        
        self.logger.info(f"Updated {key} for persona '{self.active_persona_name}'")
        return True
    
    def _switch_persona(self, persona_name: str) -> bool:
        """Switch to a different persona."""
        if persona_name not in self.personas:
            self.logger.error(f"Persona '{persona_name}' not found")
            return False
        
        # Update configuration
        self.config['ACTIVE_PERSONA'] = persona_name
        
        # Save to override file
        self._save_override('ACTIVE_PERSONA', persona_name)
        
        # Reload persona settings
        self._apply_active_persona()
        
        self.logger.info(f"Switched to persona: {persona_name}")
        return True

    def create_persona(self, name: str, system_prompt: str, voice_id: str, **kwargs: Any) -> bool:
        """
        Creates a new persona and saves it to personas.yml.

        Args:
            name (str): The name of the new persona.
            system_prompt (str): The system prompt for the persona.
            voice_id (str): The ElevenLabs voice ID for the persona.
            **kwargs: Optional additional persona attributes.

        Returns:
            bool: True if the persona was created successfully, False otherwise.
        """
        if name in self.personas:
            self.logger.error(f"Persona '{name}' already exists.")
            return False

        new_persona = {
            'name': name,
            'system_prompt': system_prompt,
            'voice_id': voice_id,
            **kwargs
        }

        self.personas[name] = new_persona
        self.config['AVAILABLE_PERSONAS'] = self.list_personas()
        self._save_personas()

        self.logger.info(f"Successfully created new persona: {name}")
        return True
    
    def _save_override(self, key: str, value: Any):
        """Save a configuration override to config_override.yml."""
        overrides = {}
        
        # Load existing overrides
        if self.override_file.exists():
            try:
                with open(self.override_file, 'r', encoding='utf-8') as f:
                    existing_overrides = yaml.safe_load(f)
                    if existing_overrides:
                        overrides = existing_overrides
            except Exception as e:
                self.logger.error(f"Failed to load existing overrides: {e}")
        
        # Update with new value
        overrides[key] = value
        
        # Save back
        try:
            with open(self.override_file, 'w', encoding='utf-8') as f:
                yaml.dump(overrides, f, indent=2, allow_unicode=True)
            self.logger.debug(f"Saved override: {key} = {value}")
        except Exception as e:
            self.logger.error(f"Failed to save override: {e}")
    
    def _save_personas(self):
        """Save all persona definitions back to personas.yml."""
        try:
            personas_list = [
                persona for persona in self.personas.values()
            ]
            
            with open(self.personas_file, 'w', encoding='utf-8') as f:
                yaml.dump({'personas': personas_list}, f, indent=2, allow_unicode=True)
            
            self.logger.debug("Saved personas.yml")
        except Exception as e:
            self.logger.error(f"Failed to save personas: {e}")
    
    def __getattr__(self, name: str) -> Any:
        """Allow attribute-style access to configuration values."""
        if name in self.config:
            return self.config[name]
        raise AttributeError(f"Configuration key '{name}' not found")
    
    def list_personas(self) -> list:
        """Return a list of available persona names."""
        return list(self.personas.keys())
    
    def get_active_persona(self) -> str:
        """Return the name of the currently active persona."""
        return self.active_persona_name

    def log_config(self, logger):
        """Logs the current configuration with long values truncated for readability."""
        logger.info("--- Configuration ---")
        for key, value in self.config.items():
            # Truncate the main system prompt if it's in the general config
            if key == 'SYSTEM_PROMPT' and isinstance(value, str) and len(value) > 80:
                log_value = f"'{value[:77]}...'"
            else:
                log_value = value
            logger.info(f"  {key}: {log_value}")

        logger.info("--- Available Personas ---")
        for name, persona_details in self.personas.items():
            prompt = persona_details.get('system_prompt', '')
            if len(prompt) > 80:
                truncated_prompt = f"'{prompt[:77]}...'"
            else:
                truncated_prompt = f"'{prompt}'"
            voice_id = persona_details.get('voice_id', 'N/A')
            logger.info(f"  - {name}:")
            logger.info(f"    voice_id: {voice_id}")
            logger.info(f"    system_prompt: {truncated_prompt}")
        logger.info("---------------------------------")

    def _ensure_personas_file_exists(self):
        """
        Ensure that personas.yml exists in the local directory.
        If not, copy it from the example file.
        """
        if not self.personas_file.exists():
            if self.example_personas_file.exists():
                try:
                    import shutil
                    shutil.copy(self.example_personas_file, self.personas_file)
                    self.logger.info(f"Created {self.personas_file} from example.")
                except Exception as e:
                    self.logger.error(f"Failed to create personas.yml from example: {e}")
            else:
                self.logger.error(f"Example personas file not found at {self.example_personas_file}")

    def _ensure_override_file_exists(self):
        """
        Ensure that config_override.yml exists in the local directory.
        If not, create an empty YAML file.
        """
        if not self.override_file.exists():
            try:
                with open(self.override_file, 'w', encoding='utf-8') as f:
                    yaml.dump({}, f)
                self.logger.info(f"Created empty {self.override_file}.")
            except Exception as e:
                self.logger.error(f"Failed to create {self.override_file}: {e}")


# Create a global instance
Config = SettingsManager()

# For backward compatibility, also expose as individual attributes
# This allows existing code to work without modification
for key in dir(Config):
    if not key.startswith('_') and key.isupper():
        globals()[key] = getattr(Config, key)