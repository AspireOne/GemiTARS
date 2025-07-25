- On this page

- [Example applications](https://ai.google.dev/gemini-api/docs/live#example-applications)
- [Partner integrations](https://ai.google.dev/gemini-api/docs/live#partner-integrations)
- [Before you begin building](https://ai.google.dev/gemini-api/docs/live#before-you-begin)
  - [Choose an audio generation architecture](https://ai.google.dev/gemini-api/docs/live#audio-generation)
  - [Choose an implementation approach](https://ai.google.dev/gemini-api/docs/live#implementation-approach)
- [Get started](https://ai.google.dev/gemini-api/docs/live#get-started)
- [What's next](https://ai.google.dev/gemini-api/docs/live#whats-next)

# Get started with Live API

- On this page
- [Example applications](https://ai.google.dev/gemini-api/docs/live#example-applications)
- [Partner integrations](https://ai.google.dev/gemini-api/docs/live#partner-integrations)
- [Before you begin building](https://ai.google.dev/gemini-api/docs/live#before-you-begin)
  - [Choose an audio generation architecture](https://ai.google.dev/gemini-api/docs/live#audio-generation)
  - [Choose an implementation approach](https://ai.google.dev/gemini-api/docs/live#implementation-approach)
- [Get started](https://ai.google.dev/gemini-api/docs/live#get-started)
- [What's next](https://ai.google.dev/gemini-api/docs/live#whats-next)

The Live API enables low-latency, real-time voice and video interactions with
Gemini. It processes continuous streams of audio, video, or text to deliver
immediate, human-like spoken responses, creating a natural conversational
experience for your users.

![Live API Overview](https://ai.google.dev/static/gemini-api/docs/images/live-api-overview.png)

Live API offers a comprehensive set of features such as [Voice Activity Detection](https://ai.google.dev/gemini-api/docs/live-guide#interruptions), [tool use and function calling](https://ai.google.dev/gemini-api/docs/live-tools), [session management](https://ai.google.dev/gemini-api/docs/live-session) (for managing long running conversations) and [ephemeral tokens](https://ai.google.dev/gemini-api/docs/ephemeral-tokens) (for secure client-sided authentication).

This page gets you up and running with examples and basic code samples.

## Example applications

Check out the following example applications that illustrate how to use Live API
for end-to-end use cases:

- [Live audio starter app](https://aistudio.google.com/apps/bundled/live_audio?showPreview=true&showCode=true&showAssistant=false) on AI Studio,
  using JavaScript libraries to connect to Live API and stream bidirectional
  audio through your microphone and speakers.
- Live API [Python cookbook](https://github.com/google-gemini/cookbook/blob/main/quickstarts/Get_started_LiveAPI.py)
  using Pyaudio that connects to Live API.

## Partner integrations

If you prefer a simpler development process, you can use [Daily](https://www.daily.co/products/gemini/multimodal-live-api/) or [LiveKit](https://docs.livekit.io/agents/integrations/google/#multimodal-live-api). These are third-party partner platforms that have already integrated the Gemini Live API over the WebRTC protocol to streamline the development of real-time audio and video applications.

## Before you begin building

There are two important decisions to make before you begin building with the
Live API: choosing a model and choosing an implementation
approach.

### Choose an audio generation architecture

If you're building an audio-based use case, your choice of model determines the
audio generation architecture used to create the audio response:

- **[Native audio](https://ai.google.dev/gemini-api/docs/live-guide#native-audio-output):**
  This option provides the most natural and realistic-sounding speech and
  better multilingual performance.
  It also enables advanced features like [affective (emotion-aware) dialogue](https://ai.google.dev/gemini-api/docs/live-guide#affective-dialog), [proactive audio](https://ai.google.dev/gemini-api/docs/live-guide#proactive-audio) (where the model can decide to
  ignore or respond to certain inputs), and ["thinking"](https://ai.google.dev/gemini-api/docs/live-guide#native-audio-output-thinking).
  Native audio is supported by the following [native audio models](https://ai.google.dev/gemini-api/docs/models#gemini-2.5-flash-native-audio):

  - `gemini-2.5-flash-preview-native-audio-dialog`
  - `gemini-2.5-flash-exp-native-audio-thinking-dialog`

- **Half-cascade audio**:
  This option uses a cascaded model architecture (native audio input and text-to-speech output).
  It offers better performance and reliability in production environments,
  especially with [tool use](https://ai.google.dev/gemini-api/doc/live-tools). Half-cascaded audio is
  supported by the following models:

  - `gemini-live-2.5-flash-preview`
  - `gemini-2.0-flash-live-001`

### Choose an implementation approach

When integrating with Live API, you'll need to choose one of the following
implementation approaches:

- **Server-to-server**: Your backend connects to the Live API using
  [WebSockets](https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API). Typically, your client sends stream data (audio, video,
  text) to your server, which then forwards it to the Live API.
- **Client-to-server**: Your frontend code connects directly to the Live API
  using [WebSockets](https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API) to stream data, bypassing your backend.

## Get started

This example **_reads a WAV file_**, sends it in the correct format, and saves
the received data as WAV file.

You can send audio by converting it to 16-bit PCM, 16kHz, mono format, and you
can receive audio by setting `AUDIO` as response modality. The output uses a
sample rate of 24kHz.

[Python](https://ai.google.dev/gemini-api/docs/live#python)[JavaScript](https://ai.google.dev/gemini-api/docs/live#javascript)More

```
# Test file: https://storage.googleapis.com/generativeai-downloads/data/16000.wav
# Install helpers for converting files: pip install librosa soundfile
import asyncio
import io
from pathlib import Path
import wave
from google import genai
from google.genai import types
import soundfile as sf
import librosa

client = genai.Client(api_key="GEMINI_API_KEY")

# Half cascade model:
# model = "gemini-live-2.5-flash-preview"

# Native audio output model:
model = "gemini-2.5-flash-preview-native-audio-dialog"

config = {
  "response_modalities": ["AUDIO"],
  "system_instruction": "You are a helpful assistant and answer in a friendly tone.",
}

async def main():
    async with client.aio.live.connect(model=model, config=config) as session:

        buffer = io.BytesIO()
        y, sr = librosa.load("sample.wav", sr=16000)
        sf.write(buffer, y, sr, format='RAW', subtype='PCM_16')
        buffer.seek(0)
        audio_bytes = buffer.read()

        # If already in correct format, you can use this:
        # audio_bytes = Path("sample.pcm").read_bytes()

        await session.send_realtime_input(
            audio=types.Blob(data=audio_bytes, mime_type="audio/pcm;rate=16000")
        )

        wf = wave.open("audio.wav", "wb")
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(24000)  # Output is 24kHz

        async for response in session.receive():
            if response.data is not None:
                wf.writeframes(response.data)

            # Un-comment this code to print audio data info
            # if response.server_content.model_turn is not None:
            #      print(response.server_content.model_turn.parts[0].inline_data.mime_type)

        wf.close()

if __name__ == "__main__":
    asyncio.run(main())

```

```
// Test file: https://storage.googleapis.com/generativeai-downloads/data/16000.wav
import { GoogleGenAI, Modality } from '@google/genai';
import * as fs from "node:fs";
import pkg from 'wavefile';  // npm install wavefile
const { WaveFile } = pkg;

const ai = new GoogleGenAI({ apiKey: "GEMINI_API_KEY" });
// WARNING: Do not use API keys in client-side (browser based) applications
// Consider using Ephemeral Tokens instead
// More information at: https://ai.google.dev/gemini-api/docs/ephemeral-tokens

// Half cascade model:
// const model = "gemini-live-2.5-flash-preview"

// Native audio output model:
const model = "gemini-2.5-flash-preview-native-audio-dialog"

const config = {
  responseModalities: [Modality.AUDIO],
  systemInstruction: "You are a helpful assistant and answer in a friendly tone."
};

async function live() {
    const responseQueue = [];

    async function waitMessage() {
        let done = false;
        let message = undefined;
        while (!done) {
            message = responseQueue.shift();
            if (message) {
                done = true;
            } else {
                await new Promise((resolve) => setTimeout(resolve, 100));
            }
        }
        return message;
    }

    async function handleTurn() {
        const turns = [];
        let done = false;
        while (!done) {
            const message = await waitMessage();
            turns.push(message);
            if (message.serverContent && message.serverContent.turnComplete) {
                done = true;
            }
        }
        return turns;
    }

    const session = await ai.live.connect({
        model: model,
        callbacks: {
            onopen: function () {
                console.debug('Opened');
            },
            onmessage: function (message) {
                responseQueue.push(message);
            },
            onerror: function (e) {
                console.debug('Error:', e.message);
            },
            onclose: function (e) {
                console.debug('Close:', e.reason);
            },
        },
        config: config,
    });

    // Send Audio Chunk
    const fileBuffer = fs.readFileSync("sample.wav");

    // Ensure audio conforms to API requirements (16-bit PCM, 16kHz, mono)
    const wav = new WaveFile();
    wav.fromBuffer(fileBuffer);
    wav.toSampleRate(16000);
    wav.toBitDepth("16");
    const base64Audio = wav.toBase64();

    // If already in correct format, you can use this:
    // const fileBuffer = fs.readFileSync("sample.pcm");
    // const base64Audio = Buffer.from(fileBuffer).toString('base64');

    session.sendRealtimeInput(
        {
            audio: {
                data: base64Audio,
                mimeType: "audio/pcm;rate=16000"
            }
        }

    );

    const turns = await handleTurn();

    // Combine audio data strings and save as wave file
    const combinedAudio = turns.reduce((acc, turn) => {
        if (turn.data) {
            const buffer = Buffer.from(turn.data, 'base64');
            const intArray = new Int16Array(buffer.buffer, buffer.byteOffset, buffer.byteLength / Int16Array.BYTES_PER_ELEMENT);
            return acc.concat(Array.from(intArray));
        }
        return acc;
    }, []);

    const audioBuffer = new Int16Array(combinedAudio);

    const wf = new WaveFile();
    wf.fromScratch(1, 24000, '16', audioBuffer);  // output is 24kHz
    fs.writeFileSync('audio.wav', wf.toBuffer());

    session.close();
}

async function main() {
    await live().catch((e) => console.error('got error', e));
}

main();

```

## What's next

- Read the full Live API [Capabilities](https://ai.google.dev/gemini-api/docs/live-guide) guide for key capabilities and configurations; including Voice Activity Detection and native audio features.
- Read the [Tool use](https://ai.google.dev/gemini-api/docs/live-tools) guide to learn how to integrate Live API with tools and function calling.
- Read the [Session management](https://ai.google.dev/gemini-api/docs/live-session) guide for managing long running conversations.
- Read the [Ephemeral tokens](https://ai.google.dev/gemini-api/docs/ephemeral-tokens) guide for secure authentication in [client-to-server](https://ai.google.dev/gemini-api/docs/live#implementation-approach) applications.
- For more information about the underlying WebSockets API, see the [WebSockets API reference](https://ai.google.dev/api/live).
