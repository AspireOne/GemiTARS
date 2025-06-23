# 🛠️ **GemiTARS Configuration System**

The centralized configuration system provides type-safe, environment-variable-configurable settings for all components while maintaining full backwards compatibility.

## 📋 **Overview**

The configuration system centralizes all "magic values" into a single, type-safe configuration structure:

- **Audio settings** (sample rates, formats, etc.)
- **VAD parameters** (speech detection thresholds)
- **Model configuration** (Gemini model selection, response types)
- **Conversation management** (timeouts, user messages)

## 🏗️ **Architecture**

```
src/config/
├── __init__.py          # Public interface
├── settings.py          # Configuration classes
└── defaults.py          # Default values & environment loading
```

## 📚 **Configuration Classes**

### **AudioConfig**
```python
@dataclass
class AudioConfig:
    sample_rate: int = 16000          # Hz - Required by Gemini Live API
    block_size: int = 1600            # Samples (100ms at 16kHz)
    dtype: str = 'int16'              # 16-bit PCM format
    channels: int = 1                 # Mono audio
    mime_type: str = "audio/pcm;rate=16000"
```

### **VADConfig**
```python
@dataclass
class VADConfig:
    enabled: bool = True              # Enable VAD functionality
    prefix_padding_ms: int = 50       # Lead-in padding before speech
    silence_duration_ms: int = 1500   # Silence threshold (1.5s)
```

### **ModelConfig**
```python
@dataclass
class ModelConfig:
    name: str = "gemini-live-2.5-flash-preview"
    response_modalities: List[str] = ["TEXT"]
    input_audio_transcription: Dict[str, Any] = {}
```

### **ConversationConfig**
```python
@dataclass
class ConversationConfig:
    timeout_seconds: int = 30         # Return to passive after inactivity
    messages: Dict[str, str] = {
        "listening": "TARS: I'm listening...",
        "interrupted": "TARS: [Interrupted] Go ahead...",
        "standby": "TARS: Returning to standby mode.",
        "goodbye": "TARS: Goodbye!",
        "system_initialized": "TARS: System initialized. Waiting for hotword...",
        "already_listening": "TARS: Already listening..."
    }
```

### **TARSConfig (Main Configuration)**
```python
@dataclass
class TARSConfig:
    audio: AudioConfig
    vad: VADConfig
    model: ModelConfig
    conversation: ConversationConfig
    api_key_env_var: str = "GEMINI_API_KEY"
```

## 🔧 **Usage Examples**

### **1. Default Configuration (Backwards Compatible)**
```python
from services import GeminiService

# Original API still works exactly the same
gemini_service = GeminiService(api_key="your_api_key")
```

### **2. Custom Configuration**
```python
from config import TARSConfig, get_default_config
from services import GeminiService

# Method 1: Modify default config
config = get_default_config()
config.vad.silence_duration_ms = 2000  # 2 second silence threshold
config.conversation.timeout_seconds = 60  # 1 minute timeout

gemini_service = GeminiService(api_key="your_api_key", config=config)

# Method 2: Create custom config
config = TARSConfig(
    vad=VADConfig(silence_duration_ms=2000),
    conversation=ConversationConfig(timeout_seconds=60)
)
gemini_service = GeminiService(api_key="your_api_key", config=config)
```

### **3. Environment Variable Configuration**
```python
from config import load_config_from_env
from services import GeminiService

# Load config with environment variable overrides
config = load_config_from_env()
gemini_service = GeminiService(api_key="your_api_key", config=config)
```

## 🌍 **Environment Variables**

All configuration values can be overridden using environment variables:

### **Audio Configuration**
```bash
export TARS_AUDIO_SAMPLE_RATE=16000
export TARS_AUDIO_BLOCK_SIZE=1600
export TARS_AUDIO_DTYPE=int16
export TARS_AUDIO_CHANNELS=1
```

### **VAD Configuration**
```bash
export TARS_VAD_ENABLED=true
export TARS_VAD_PREFIX_PADDING_MS=50
export TARS_VAD_SILENCE_DURATION_MS=1500
```

### **Model Configuration**
```bash
export TARS_MODEL_NAME=gemini-live-2.5-flash-preview
export TARS_MODEL_RESPONSE_MODALITIES=TEXT,AUDIO
```

### **Conversation Configuration**
```bash
export TARS_CONVERSATION_TIMEOUT_SECONDS=30
export TARS_API_KEY_ENV_VAR=GEMINI_API_KEY
```

## 📖 **Integration Examples**

### **main.py - Using Centralized Audio Config**
```python
from config import get_default_config
from services import GeminiService

# Load centralized audio configuration
config = get_default_config()
samplerate = config.audio.sample_rate
blocksize = config.audio.block_size
dtype = config.audio.dtype
channels = config.audio.channels

# Initialize with centralized config
gemini_service = GeminiService(api_key=api_key, config=config)
```

### **vad_example.py - Environment Variable Overrides**
```python
from config import load_config_from_env
from services import GeminiService

# Load config with environment variable overrides
config = load_config_from_env()

# All settings automatically loaded from environment if present
gemini_service = GeminiService(
    api_key=api_key, 
    enable_conversation_management=True,
    config=config
)
```

## 🧪 **Testing Configuration**

### **Test Custom VAD Settings**
```bash
# Set custom VAD timing
export TARS_VAD_SILENCE_DURATION_MS=3000  # 3 second silence threshold
export TARS_VAD_PREFIX_PADDING_MS=100     # 100ms padding

# Run VAD example with custom settings
python src/examples/vad_example.py
```

### **Test Custom Conversation Timeouts**
```bash
# Set 2-minute conversation timeout
export TARS_CONVERSATION_TIMEOUT_SECONDS=120

# Run test
python src/test_vad_phase1.py
```

## ✅ **Benefits**

### **For Developers**
- **Type Safety**: IDE autocompletion and type checking
- **Single Source of Truth**: All configuration in one place
- **Clear Documentation**: Every setting explained with sensible defaults
- **Easy Testing**: Override any setting via environment variables

### **For Production**
- **Environment-based Configuration**: Easy deployment across environments
- **No Code Changes**: Modify behavior via environment variables
- **Backwards Compatible**: Existing code continues working unchanged
- **Validation**: Configuration values validated at startup

## 🔄 **Migration Guide**

### **Before (Scattered Magic Values)**
```python
# Audio settings duplicated across files
samplerate = 16000
blocksize = 1600
dtype = 'int16'

# VAD settings hardcoded in service
"silence_duration_ms": 1500
"prefix_padding_ms": 50

# Messages hardcoded throughout codebase
print("TARS: I'm listening...")
```

### **After (Centralized Configuration)**
```python
# Single configuration source
config = get_default_config()
samplerate = config.audio.sample_rate
blocksize = config.audio.block_size

# Centralized VAD configuration
gemini_service = GeminiService(api_key=api_key, config=config)

# Centralized messages
print(config.conversation.messages["listening"])
```

## 🎯 **Key Features**

✅ **Zero Breaking Changes** - All existing code continues working  
✅ **Type Safety** - Full type hints and validation  
✅ **Environment Support** - Override any setting via environment variables  
✅ **Documentation** - Clear descriptions for every configuration option  
✅ **Extensible** - Easy to add new configuration categories  
✅ **Production Ready** - Environment-based deployment support  

The configuration system transforms scattered magic values into a professional, maintainable, and flexible configuration management solution! 🚀