### Project Summary: TARS-themed AI Voice Assistant

#### 1. Project Goal \& Vision

The primary goal is to create a custom, hardware-based AI "voice assistant" (a TARS from Interstellar robot), inspired by Google Home but with the specific personality, voice, and conversational style of the robot TARS from the movie _Interstellar_ and with function calling provided by the LLM. The device will be physically compact and capable of rich, continuous, and multimodal (voice and vision) conversations.

#### 2. Core User Interaction Flow

- **Hotword Activation:** The device is activated from a passive listening state using a local hotword detector.
- **Continuous Conversation:** Once activated, it enters an "active listening" mode, allowing for a natural, back-and-forth conversation without needing the hotword for each turn.
- **Silence Timeout:** The device will automatically return to its passive, hotword-listening state after a designated period of silence.
- **Function Calling:** The assistant must be able to process complex conversational sentences and execute functions (e.g., control smart home devices, perform lookups - this is a later step).

#### 3. High-Level Technical Architecture

_NOTE: THIS IS NOT VALID FOR NOW. FOR NOW, WE WILL USE ARDUINO CONNECTED VIA A CABLE, SO THE MICROPHONE/CAMERA DATA, AS WELL AS A SPEAKER, WILL NOT BE TRANSMITTED USING WIFI_

The architecture is split into two main components communicating over a local WiFi network to keep the user-facing device as small as possible.

- **Remote Unit (The "Head"):** A small, ESP32-based device that handles all physical input/output. Its sole responsibilities are:
  - Capturing microphone audio and streaming it to the processing hub.
  - Capturing on-demand camera images/video and streaming them.
  - Receiving the final audio stream and playing it through a connected speaker.
- **Processing Hub (The "Brain"):** A Raspberry Pi 5 that runs the core logic. It is responsible for:
  - Receiving the raw audio (or image/video) streams from the ESP32.
  - Communicating with a cloud-based Large Language Model (LLM) for conversation and logic.
  - Managing the entire interaction flow and state.
  - Sending the final, synthesized speech back to the ESP32 for playback.

#### 4. Key Technology \& Component Decisions

- **Audio Input Processing:** The project will **stream raw audio directly** to a cloud LLM instead of performing local transcription first.
  - **Chosen Tool:** **Gemini Live API**, selected for its ability to handle low-latency, real-time, bidirectional audio streams, which is ideal for a conversational assistant.
- **Voice Synthesis (The TARS Voice):** The chosen method is to receive text from the LLM and then synthesize it into the TARS voice. The alternative—modifying a generic voice on-the-fly—was deemed too complex and likely to produce a lower-quality result.
  - **Chosen Tool:** **ElevenLabs API**, selected for its high-fidelity voice cloning and streaming capabilities, which will be used to create an authentic-sounding TARS voice.
- **Visual Input (Camera):** The system must support two camera use cases.
  - **Single Image Capture:** On demand, the ESP32 will capture a still image and send it to the Raspberry Pi. This visual context will be sent to the LLM along with the user's speech to enable multimodal understanding.
  - **Continuous Video Stream:** The system will support a continuous, low-frame-rate (5-25 FPS) video stream for tasks like object tracking or robot navigation.
  
#### 5. Other
- Do not use thinking in gemini models for better latency.

### NOTE: WE WILL START WITH THE MIC ONLY IMPLEMENTATION, ARDUINO + RPI 5