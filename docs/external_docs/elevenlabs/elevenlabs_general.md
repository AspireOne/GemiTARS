# General ElevenLabs API documentation

## Basic info

Voice quality
For real-time applications, Flash v2.5 provides ultra-low 75ms latency, while Multilingual v2 delivers the highest quality audio with more nuanced expression.

Supported formats
The default response format is “mp3”, but other formats like “PCM”, & “μ-law” are available.

MP3
Sample rates: 22.05kHz - 44.1kHz
Bitrates: 32kbps - 192kbps
22.05kHz @ 32kbps
44.1kHz @ 32kbps, 64kbps, 96kbps, 128kbps, 192kbps
PCM (S16LE)
Sample rates: 16kHz - 44.1kHz
Bitrates: 8kHz, 16kHz, 22.05kHz, 24kHz, 44.1kHz, 48kHz
16-bit depth
μ-law
8kHz sample rate
Optimized for telephony applications
A-law
8kHz sample rate
Optimized for telephony applications
Opus
Sample rate: 48kHz
Bitrates: 32kbps - 192kbps

Supported languages
Our v2 models support 29 languages:

English (USA, UK, Australia, Canada), Japanese, Chinese, German, Hindi, French (France, Canada), Korean, Portuguese (Brazil, Portugal), Italian, Spanish (Spain, Mexico), Indonesian, Dutch, Turkish, Filipino, Polish, Swedish, Bulgarian, Romanian, Arabic (Saudi Arabia, UAE), Czech, Greek, Finnish, Croatian, Malay, Slovak, Danish, Tamil, Ukrainian & Russian.

Flash v2.5 supports all languages from v2.

Simply input text in any of our supported languages and select a matching voice from our voice library. For the most natural results, choose a voice with an accent that matches your target language and region.

Prompting
The models interpret emotional context directly from the text input. For example, adding descriptive text like “she said excitedly” or using exclamation marks will influence the speech emotion. Voice settings like Stability and Similarity help control the consistency, while the underlying emotion comes from textual cues.

## Examples

Stream audio in real-time, as it's being generated.

```python
from elevenlabs import stream
from elevenlabs.client import ElevenLabs

client = ElevenLabs()

audio_stream = client.text_to_speech.stream(
    text="This is a test",
    voice_id="JBFqnCBsd6RMkjVDRZzb",
    model_id="eleven_multilingual_v2"
)

# option 1: play the streamed audio locally
stream(audio_stream)

# option 2: process the audio bytes manually
for chunk in audio_stream:
    if isinstance(chunk, bytes):
        print(chunk)
```

Use AsyncElevenLabs if you want to make API calls asynchronously.

```python
import asyncio

from elevenlabs.client import AsyncElevenLabs

eleven = AsyncElevenLabs(
  api_key="MY_API_KEY"
)

async def print_models() -> None:
    models = await eleven.models.list()
    print(models)

asyncio.run(print_models())
```
