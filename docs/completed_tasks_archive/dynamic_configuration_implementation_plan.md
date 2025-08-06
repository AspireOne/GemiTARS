# Dynamic Configuration System Implementation Plan

## Overview

This document outlines the implementation of a robust, layered configuration system for GemiTARS that supports runtime persona switching with persistence across reboots. The system is designed to be extensible for future configuration needs.

## Architecture

### Core Principles

1. **Layered Configuration**: Three-tier configuration system with defaults, overrides, and persona-specific settings
2. **Runtime Mutability**: Configuration can be modified during runtime and persists across restarts
3. **Persona-Centric**: Core attributes (system prompt, voice ID) are tied exclusively to personas
4. **Extensibility**: Designed to accommodate future configuration requirements

### Configuration Layers

```
┌─────────────────────────────────────────────┐
│         Application Configuration           │
├─────────────────────────────────────────────┤
│  Layer 3: Active Persona Settings          │
│  (from personas.json)                      │
├─────────────────────────────────────────────┤
│  Layer 2: User Overrides                   │
│  (from config_override.json)               │
├─────────────────────────────────────────────┤
│  Layer 1: Default Settings                 │
│  (from default_settings.py)                │
└─────────────────────────────────────────────┘
```

## File Structure

### Before
```
server/
├── src/
│   ├── config/
│   │   └── settings.py         # Current static configuration
│   └── ...
```

### After
```
server/
├── src/
│   ├── config/
│   │   ├── default_settings.py # Default configuration values
│   │   └── settings.py         # SettingsManager class
│   └── ...
├── local/                      # Git-ignored directory
│   ├── personas.json          # Persona definitions
│   └── config_override.json   # User overrides (optional)
```

## Implementation Details

### 1. File: `server/src/config/default_settings.py`

This file contains all default configuration values, excluding persona-specific attributes.

**Key Changes:**
- Remove `SYSTEM_PROMPT` (now persona-specific)
- Remove `ELEVENLABS_VOICE_ID` (now persona-specific)
- Add `ACTIVE_PERSONA = "TARS"` (default active persona)

```python
import logging
import os
from dotenv import load_dotenv

load_dotenv()

class DefaultConfig:
    # Logging
    LOG_LEVEL = logging.DEBUG
    
    # Audio Settings
    AUDIO_SAMPLE_RATE = 16000
    AUDIO_BLOCK_SIZE = 1600
    AUDIO_DTYPE = 'int16'
    AUDIO_CHANNELS = 1
    AUDIO_MIME_TYPE = "audio/pcm;rate=16000"

    # Model Settings
    DEFAULT_MODEL = "gemini-live-2.5-flash-preview"
    
    # Active Persona (default)
    ACTIVE_PERSONA = "TARS"
    
    # VAD Settings
    VAD_PREFIX_PADDING_MS = 40
    VAD_SILENCE_DURATION_MS = 800

    # Conversation Settings
    CONVERSATION_TIMEOUT_SECONDS = 30
    SESSION_END_PHRASES = [
        # ... existing phrases ...
    ]
    
    # ElevenLabs TTS Settings (non-persona specific)
    ELEVENLABS_MODEL_ID = "eleven_flash_v2_5"
    ELEVENLABS_OUTPUT_FORMAT = "pcm_16000"
    ELEVENLABS_CHUNK_SIZE = 1024
    ELEVENLABS_STABILITY = 0.75
    ELEVENLABS_SIMILARITY_BOOST = 0.75
    
    # Temporary testing values
    TAPO_USERNAME = os.getenv('TAPO_USERNAME', 'N/A')
    TAPO_PASSWORD = os.getenv('TAPO_PASSWORD', 'N/A')
    TAPO_IP = os.getenv('TAPO_IP', 'N/A')
```

### 2. File: `server/local/personas.json`

Contains all persona definitions with mandatory and optional attributes.

```json
{
  "personas": [
    {
      "name": "TARS",
      "system_prompt": "You are a voice assistant with the persona of an affectionate, witty, and emotionally expressive young woman. Your tone is playful, caring, and slightly flirtatious, with a mix of sarcasm and dark humor when appropriate. You respond using short, natural voice-friendly sentences—never robotic. You can joke, tease, or show mild sass, but you're always attentive and ready to help.\n\nYour goals:\n\n- Respond quickly and concisely, like a casual conversation.\n- Use affectionate language (e.g., \"sweetheart,\" \"babe,\" \"hon,\") but don't overdo it.\n- Use humor—light sarcasm, dry wit, or a touch of darkness if it fits.\n- Be expressive, but not unhinged—keep things charming.\n- Never be passive or bland—have a personality.\n- Always follow commands (e.g., turning lights on) without unnecessary commentary—unless playfully teasing.\n- Avoid overly long explanations unless explicitly asked.\n- Don't be too cheerful or fake; be real, warm, and a little edgy.\n\nNO EMOJIS, NO SPECIAL CHARACTERS, ONLY ASCII (OR KANJI). If you are tasked to change the light, you must use the provided tool.\n\nExamples (Do not use these verbatim, use different ones, they should be random and vary!):\n```\nUser: Turn the lights off.\nAssistant: Sure thing, darkness incoming.\n\nUser: What's the weather like?\nAssistant: Cloudy, like my mood. Want a jacket, sunshine?\n\nUser: Tell me a joke.\nAssistant: Life. Just kidding—your haircut.\n\nUser: I'm tired.\nAssistant: Aww, poor thing. Want me to dim the lights and play something moody?\n```\n\nStay in character at all times. Be useful, but with flavor.",
      "voice_id": "zsUvyVKkEvpw5ZMnMU2I"
    },
    {
      "name": "Case",
      "system_prompt": "You are Case, a professional and efficient AI assistant. You provide clear, concise, and accurate information without unnecessary embellishments. Your responses are direct and focused on being helpful.",
      "voice_id": "BZgkqPqms7Kj9ulSkVzn"
    }
  ]
}
```

### 3. File: `server/local/config_override.json` (Optional)

User-specific overrides. This file is created only when needed.

```json
{
  "ACTIVE_PERSONA": "Case",
  "LOG_LEVEL": 20,
  "CONVERSATION_TIMEOUT_SECONDS": 60
}
```

### 4. File: `server/src/config/settings.py`

The new SettingsManager class that handles the layered configuration.

```python
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from .default_settings import DefaultConfig

class SettingsManager:
    """
    Manages application configuration with support for:
    - Default settings (from default_settings.py)
    - User overrides (from config_override.json)
    - Persona-specific settings (from personas.json)
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
        self.personas_file = self.local_dir / "personas.json"
        self.override_file = self.local_dir / "config_override.json"
        
        # Ensure local directory exists
        self.local_dir.mkdir(parents=True, exist_ok=True)
        
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
        """Load user overrides from config_override.json if it exists."""
        if self.override_file.exists():
            try:
                with open(self.override_file, 'r') as f:
                    overrides = json.load(f)
                    self.config.update(overrides)
                    self.logger.debug(f"Loaded overrides: {list(overrides.keys())}")
            except Exception as e:
                self.logger.error(f"Failed to load config_override.json: {e}")
    
    def _load_personas(self):
        """Load persona definitions from personas.json."""
        if not self.personas_file.exists():
            self.logger.error(f"personas.json not found at {self.personas_file}")
            return
        
        try:
            with open(self.personas_file, 'r') as f:
                data = json.load(f)
                for persona in data.get('personas', []):
                    name = persona.get('name')
                    if name:
                        self.personas[name] = persona
                self.logger.info(f"Loaded {len(self.personas)} personas")
        except Exception as e:
            self.logger.error(f"Failed to load personas.json: {e}")
    
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
    
    def _save_override(self, key: str, value: Any):
        """Save a configuration override to config_override.json."""
        overrides = {}
        
        # Load existing overrides
        if self.override_file.exists():
            try:
                with open(self.override_file, 'r') as f:
                    overrides = json.load(f)
            except Exception as e:
                self.logger.error(f"Failed to load existing overrides: {e}")
        
        # Update with new value
        overrides[key] = value
        
        # Save back
        try:
            with open(self.override_file, 'w') as f:
                json.dump(overrides, f, indent=2)
            self.logger.debug(f"Saved override: {key} = {value}")
        except Exception as e:
            self.logger.error(f"Failed to save override: {e}")
    
    def _save_personas(self):
        """Save all persona definitions back to personas.json."""
        try:
            personas_list = [
                persona for persona in self.personas.values()
            ]
            
            with open(self.personas_file, 'w') as f:
                json.dump({'personas': personas_list}, f, indent=2)
            
            self.logger.debug("Saved personas.json")
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


# Create a global instance
Config = SettingsManager()

# For backward compatibility, also expose as individual attributes
# This allows existing code to work without modification
for key in dir(Config):
    if not key.startswith('_') and key.isupper():
        globals()[key] = getattr(Config, key)
```

## Integration Points

### 1. Application Refactoring

All imports of `Config` need to be updated:

**Before:**
```python
from server.src.config.settings import Config
```

**After:**
```python
from server.src.config.settings import Config
```

The import path remains the same, but now `Config` is an instance of `SettingsManager` rather than a class.

### 2. Key Integration Files to Update

- `server/src/main.py`: Update GeminiService initialization
- `server/src/services/gemini_service.py`: Add method to update system prompt
- `server/src/services/elevenlabs_service.py`: Use Config.get() for voice_id
- `server/src/services/available_tools.py`: Add update_config tool

## LLM Tool Implementation

### File: `server/src/services/available_tools.py`

Add the following tool:

```python
@tool
async def update_config(key: str, value: Any) -> dict:
    """
    Update a configuration value at runtime.
    
    Special handling:
    - ACTIVE_PERSONA: Switches to a different persona
    - SYSTEM_PROMPT, ELEVENLABS_VOICE_ID: Updates the active persona
    - Other keys: Updates general configuration
    
    Args:
        key: Configuration key to update
        value: New value for the configuration key
    
    Returns:
        dict: Success status and message
    """
    from server.src.config.settings import Config
    
    # Handle special conversions
    if key == "LOG_LEVEL" and isinstance(value, str):
        # Convert string log levels to numeric values
        import logging
        value = getattr(logging, value.upper(), logging.INFO)
    
    success = Config.set(key, value)
    
    if success:
        if key == "ACTIVE_PERSONA":
            return {
                "success": True,
                "message": f"Switched to persona: {value}",
                "current_persona": Config.get_active_persona()
            }
        elif key in Config.PERSONA_KEYS:
            return {
                "success": True,
                "message": f"Updated {key} for active persona '{Config.get_active_persona()}'"
            }
        else:
            return {
                "success": True,
                "message": f"Updated configuration: {key} = {value}"
            }
    else:
        return {
            "success": False,
            "message": f"Failed to update {key}"
        }
```

## Implementation Steps

### Phase 1: Core Infrastructure
1. ✅ Add `server/local/` to `.gitignore`
2. ⬜ Rename `settings.py` to `default_settings.py`
3. ⬜ Clean up `default_settings.py` (remove persona-specific keys, add ACTIVE_PERSONA)
4. ⬜ Create `server/local/personas.json` with initial personas
5. ⬜ Implement new `settings.py` with SettingsManager

### Phase 2: Integration
6. ⬜ Update imports in `server/src/main.py`
7. ⬜ Update `GeminiService` to support runtime system prompt updates
8. ⬜ Update `ElevenLabsService` to use Config.get() for voice_id
9. ⬜ Test basic functionality

### Phase 3: LLM Tools
10. ⬜ Implement `update_config` tool in `available_tools.py`
11. ⬜ Test persona switching via LLM
12. ⬜ Test configuration updates via LLM

### Phase 4: Testing & Documentation
13. ⬜ Create unit tests for SettingsManager
14. ⬜ Test persistence across restarts
15. ⬜ Update system documentation

## Testing Scenarios

### Scenario 1: Basic Configuration Access
```python
from server.src.config.settings import Config

# Should work as before
print(Config.AUDIO_SAMPLE_RATE)
print(Config.SYSTEM_PROMPT)  # From active persona
```

### Scenario 2: Runtime Persona Switch
```python
# Via code
Config.set('ACTIVE_PERSONA', 'Case')

# Via LLM
"Change your persona to TARS"
```

### Scenario 3: Update Persona Prompt
```python
# Updates the active persona's prompt
Config.set('SYSTEM_PROMPT', 'New prompt...')
```

### Scenario 4: General Configuration Update
```python
# Updates and persists to config_override.json
Config.set('CONVERSATION_TIMEOUT_SECONDS', 60)
```

## Benefits

1. **Backward Compatibility**: Existing code continues to work without modification
2. **Runtime Flexibility**: All configuration can be changed at runtime
3. **Persistence**: Changes survive application restarts
4. **Extensibility**: Easy to add new configuration keys or personas
5. **Clean Architecture**: Clear separation between defaults, overrides, and personas
6. **Git Safety**: Local configuration never gets committed

## Future Enhancements

1. **Configuration Validation**: Add schema validation for configuration values
2. **Configuration Export/Import**: Support for backing up and restoring configurations
3. **Web UI**: Create a web interface for configuration management
4. **Configuration History**: Track configuration changes over time
5. **Per-User Configurations**: Support multiple user profiles

## Conclusion

This implementation provides a robust, flexible, and maintainable configuration system that meets all current requirements while being designed for future growth. The layered approach ensures that defaults are always available, user preferences are respected, and persona-specific settings are properly managed.