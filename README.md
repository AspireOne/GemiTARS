# GemiTARS: A replica of TARS from Intersellar

A replica of TARS from interstellar, featuring continuous conversations powered by Gemini Live API. Uses a distributed architecture with a compact Raspberry Pi Zero 2W "head" for local wake word detection and I/O, while a powerful server "brain" manages AI processing, state management, and other processing, enabling rich voice and vision interactions with function calling capabilities.

This file provides overview and high level goals/features and architecture of the project.

`/server`: contains the server code.
`/pi_software`: contains the code for the Raspberry Pi client.

- To see the current state of the project: [`docs/todo.md`](docs/todo.md).
- External documentation is in [`docs/external/`](docs/external_docs/) (for gemini Live API, ElevenLabs TTS, OpenWakeWord etc.).
- The Raspberry Pi software is in [`pi_software/`](pi_software/).
- [`/tars_voice_clips`](/tars_voice_clips) contains most of tars' voice from the original movie with the voice isolated. Can  
  be used to train a model for voice cloning.

## Core Features Overview

- **Hotword Detection**: Listening for a wake word ("Hey, TARS!") using local detection on the Raspberry Pi.
- **Continuous Conversation**: After activation, the assistant actively listens for a set duration (connection to Gemini LIVE API is established), allowing for natural, back-and-forth conversation without re-triggering the hotword. When a timeout is reached, the assistant will return to passive hotword listening.
- **Direct Audio-to-LLM**: Audio is streamed directly to the Gemini Live API, skipping an intermediate transcription step to minimize latency and improve conversational flow.
- **Multimodal Input**: (later feature) Capable of capturing and sending on-demand images to the LLM alongside voice commands for visual context.
- **Custom Voice Output**: Generates a high-fidelity TARS-like voice using ElevenLabs' text-to-speech (TTS) streaming service.
- **Distributed Architecture**: A compact, low-profile Raspberry Pi Zero 2W unit handles local wake word detection and sensor I/O, while a powerful server manages all the heavy lifting (AI processing, audio processing, logic...).
- **Function Calling:** The assistant will be able to process complex conversational sentences and execute functions (e.g., control smart home devices, perform internet searches...).

## Gemini Live API

Extremely fast and low-latency LLM API that:

- Takes in not only text text, but also images, audio, or combination of these.
- Streams back responses in real-time.
- Has a built-in VAD (voice activity detection) to automatically wait for a user's speech before responding etc.
- Has a Live mode, where it itself manages the whole session - it takes in the user's talking (input audio) directly, and decides when and how to respond, whether to be interrupted etc. - no processing on the side of our server.

## System Architecture

The system uses a distributed architecture split into two main components communicating over WiFi, designed to keep the user-facing device compact while leveraging powerful server-side processing.

- **Remote Unit (The "Head"):** A small, Raspberry Pi Zero 2W-based device that handles local wake word detection and physical input/output. Its responsibilities are:
  - Locally detecting the wake word using OpenWakeWord.
  - Capturing microphone audio and streaming it to the processing hub only after wake word detection.
  - Capturing on-demand camera images and sending them to the server.
  - Receiving the final audio stream and playing it through a connected speaker.
- **Processing Hub (The "Brain"):** A server that runs the core logic. It is responsible for:
  - Receiving the raw audio (or image) streams from the Raspberry Pi after wake word trigger.
  - Communicating with a cloud-based Large Language Model (LLM) for conversation and logic.
  - Managing the entire interaction flow and state.
  - Sending the final, synthesized speech back to the Raspberry Pi for playback.

This distributed approach was chosen to fulfill the goal of a minimal physical footprint for the user-facing device, with the Raspberry Pi Zero 2W acting as an efficient "sensor pod" that handles local wake word detection for privacy and bandwidth efficiency, while offloading intensive AI computation to the more powerful server. The direct LLM audio processing (via Gemini Live) reduces latency by eliminating the traditional Speech-to-Text transcription step, while high-fidelity TTS (ElevenLabs) provides authentic TARS voice synthesis rather than attempting complex real-time voice transformation.

## The logic flow

The GemiTARS system operates through several distinct phases, seamlessly transitioning between passive listening and active conversation modes (details of this implementation plan might change):

Tl;Dr:

- Raspberry Pi continuously listens for hotword locally using OpenWakeWord.
- If hotword is detected, it starts streaming audio to the server and plays an acknowledgment tone ("mhm"...).
- Server establishes Gemini Live API session.
- The conversation now continues through the Gemini Live API, with the Raspberry Pi streaming audio to the server and the server streaming audio (the LLM response audio) back to the Raspberry Pi.
- When Gemini Live API returns text -> send it to ElevenLabs -> stream back its audio chunks directly to the Raspberry Pi.
- If no sound is detected / no reply is coming, time out and return to passive listening mode.

note:
A user cannot interrupt TARS while he is thinking (PROCESSING) or speaking (SPEAKING). If the user says "Stop" or "Wait, I meant something else," the microphone is effectively off. This is a current decision and might be changed in the future.

**1. Passive Listening State**

- The **Remote Unit** (Raspberry Pi) continuously monitors microphone audio locally for the wake word "Hey, TARS!" using OpenWakeWord for offline recognition.
- No audio is streamed to the server during this phase, preserving privacy and bandwidth.
- System remains in low-power mode, with minimal processing overhead on the Pi.

**2. Wake Word Activation**

- When "Hey, TARS!" is detected locally on the Raspberry Pi, the system immediately transitions to **Active Conversation Mode**.
- The Pi starts streaming audio to the server and plays a local acknowledgment tone (e.g., "yeah", "mhm", "listening", "Yes sir"...).
- The server establishes a **Gemini Live API session** for real-time, bidirectional audio streaming.
- A conversation timeout timer begins (configurable duration, typically 30-60 seconds).

**3. Active Conversation Mode**

- **Direct Audio Streaming**: Raw audio from the Raspberry Pi microphone is streamed directly to the Gemini Live API via the server.
  - No local speech-to-text transcription occurs, reducing latency.
  - Gemini Live handles real-time audio processing and understanding.
- **Multimodal Input**: User can request visual context by saying phrases like "look at this" or "what do you see?"
  - Raspberry Pi captures a still image using the connected camera.
  - Image is sent to the server and included in the next Gemini API request alongside audio.
- **Continuous Listening**: The system maintains the connection and actively listens for follow-up questions or commands.
- **Conversation Timer**: Resets with each user interaction to maintain natural conversation flow.

**4. Response Generation and Playback**

- **LLM Processing**: Gemini Live processes the audio (and optional image) input and generates a text response.
- **Function Calling**: If the response includes function calls (smart home control, web searches, etc.), these are executed on the server.
- **Voice Synthesis**: The text response is sent to **ElevenLabs TTS API** for conversion to TARS-like voice.
- **Audio Streaming**: The synthesized audio is streamed back to the Raspberry Pi in real-time.
- **Playback**: Raspberry Pi plays the audio through the connected I²S speaker/amplifier.

**5. Conversation Continuation or Timeout**

- **Active Listening Continues**: After each response, the system continues listening for follow-up input.
- **Timer Management**: Each user interaction resets the conversation timeout.
- **Natural Conversation**: Users can interrupt, ask follow-up questions, or change topics without re-triggering the wake word.
- **Timeout Handling**: If no user input is detected within the timeout period, the system gracefully closes the Gemini Live session and reverts back to passive listening mode.

**6. Return to Passive State**

- **Session Cleanup**: The Gemini Live API connection is terminated.
- **State Reset**: System returns to passive hotword detection mode on the Raspberry Pi.
- **Resource Management**: Server reduces processing load; Pi stops streaming and returns to local monitoring.
- **Ready for Next Activation**: Raspberry Pi resumes local listening for the next "Hey, TARS!" detection.

**Error Handling and Edge Cases**

- **Network Interruptions**: If WiFi connection is lost, Raspberry Pi attempts reconnection while buffering audio locally.
- **Audio Quality Issues**: Automatic gain control and noise reduction (e.g., via ALSA) are applied to microphone input.
- **Concurrent Requests**: System queues multiple rapid inputs to prevent audio stream conflicts.
