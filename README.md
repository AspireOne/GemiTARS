# GemiTARS: A TARS-themed Conversational AI assistant

A conversational AI voice assistant inspired by TARS from Interstellar, featuring continuous multimodal conversations powered by Gemini Live API. Uses a distributed architecture with a compact ESP32 "head" for I/O and a server "brain" for AI processing, enabling rich voice and vision interactions with function calling capabilities.

## Core Features Overview

- **Hotword Detection**: Listening for a wake word ("Hey, TARS!").
- **Continuous Conversation**: After activation, the assistant actively listens for a set duration (connection to Gemini LIVE API is established), allowing for natural, back-and-forth conversation without re-triggering the hotword. When a timeout is reached, the assistant will return to passive hotword listening.
- **Direct Audio-to-LLM**: Audio is streamed directly to the Gemini Live API, skipping an intermediate transcription step to minimize latency and improve conversational flow.
- **Multimodal Input**: Capable of capturing and sending on-demand images to the LLM alongside voice commands for visual context.
- **Custom Voice Output**: Generates a high-fidelity TARS-like voice using ElevenLabs' text-to-speech (TTS) streaming service.
- **Distributed Architecture**: A compact, low-profile ESP32 unit handles all sensor I/O, while a powerful server manages all the heavy lifting (AI processing, audio processing, logic).
- **Function Calling:** The assistant will be able to process complex conversational sentences and execute functions (e.g., control smart home devices, perform internet searches...).

## System Architecture

The system uses a distributed architecture split into two main components communicating over WiFi, designed to keep the user-facing device compact while leveraging powerful server-side processing.

- **Remote Unit (The "Head"):** A small, ESP32-based device that handles all physical input/output. Its sole responsibilities are:
  - Capturing microphone audio and streaming it to the processing hub.
  - Capturing on-demand camera images/video and sending/streaming them.
  - Receiving the final audio stream and playing it through a connected speaker.
- **Processing Hub (The "Brain"):** A server that runs the core logic. It is responsible for:
  - Receiving the raw audio (or image/video) streams from the ESP32.
  - Hotword detection etc.
  - Communicating with a cloud-based Large Language Model (LLM) for conversation and logic.
  - Managing the entire interaction flow and state.
  - Sending the final, synthesized speech back to the ESP32 for playback.

This distributed approach was chosen to fulfill the goal of a minimal physical footprint for the user-facing device, with the ESP32 acting as a lightweight "sensor pod" that offloads all intensive computation to the more powerful server. The direct LLM audio processing (via Gemini Live) reduces latency by eliminating the traditional Speech-to-Text transcription step, while high-fidelity TTS (ElevenLabs) provides authentic TARS voice synthesis rather than attempting complex real-time voice transformation.

#### Key Technology \& Component Decisions

- **Audio Input Processing:** The project will **stream raw audio directly** to a cloud LLM instead of performing local transcription first.
  - **Chosen Tool:** **Gemini Live API**, selected for its ability to handle low-latency, real-time, bidirectional audio streams, which is ideal for a conversational assistant.
- **Voice Synthesis (The TARS Voice):** The chosen method is to receive text from the LLM and then synthesize it into the TARS voice. The alternative—modifying a generic voice on-the-fly—was deemed too complex and likely to produce a lower-quality result.
  - **Chosen Tool:** **ElevenLabs API**, selected for its high-fidelity voice cloning and streaming capabilities, which will be used to create an authentic-sounding TARS voice.
- **Single Image Capture:** On demand, the ESP32 will capture a still image and send it to the server. This visual context will be sent to the LLM along with the user's speech to enable multimodal understanding.

## Hardware

1. **Server (core processor)**: Any local or hosted server (computer, VPS, Raspberry Pi 5 (4GB+ recommended)...)
2. **Sensor Hub**: An ESP32 development board.
3. **Microphone**: A high-quality I²S microphone (e.g., INMP441) for clear audio capture and from far away.
4. **Camera**: A camera for capturing images, so Tars can 'see' (e.g. OV2640 2MP).
5. **Speaker**: An I²S amplifier/DAC module (e.g., MAX98357A) connected to a 3W or 5W speaker.
6. **Power**: Separate, stable power supplies for the ESP32.
7. **Casing**: (Optional) 3D-printed (TARS) case to house the ESP32, camera, mic, and speaker.

**Below are less important details and setup info.**

---

## Setup and Installation

### 1. ESP32 Firmware Setup

- **Libraries**:
  - `ArduinoWebsockets`: For real-time, bidirectional communication.
  - Libraries for I²S audio handling (e.g., `I2S.h`).
  - ESP32 Camera libraries.

1. Set up your development environment using **PlatformIO** in VSCode (recommended).
2. Navigate to the `esp32_firmware/` directory.
3. Modify `src/config.h` to include your WiFi SSID and password, and the static IP address of your Raspberry Pi.
4. Connect the I²S microphone and speaker amplifier to the correct GPIO pins as defined in the firmware.
5. Compile and upload the firmware to your ESP32-CAM board. Use a USB-to-TTL serial programmer if your board doesn't have a built-in USB port.

### 2. Server/Backend Setup

- **Python**: 3.11
- **Libraries**:
  - `google-generativeai`: For Gemini Live API.
  - `elevenlabs`: For TTS streaming.
  - `websockets` or `aiohttp`: For communication with the ESP32.
  - `pvporcupine`: For hotword detection.
  - etc., see requirements.txt for full list.

1. Clone this repository to your server:

```bash
git clone https://github.com/your-username/project-tars.git
cd project-tars
```

2. Create and activate a Python virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install all required Python packages:

```bash
pip install -r requirements.txt
```

### 3. API Configuration

1. Create a `.env` file in the root directory of the project by copying the example:

```bash
cp .env.example .env
```

2. Open the `.env` file and fill in your API keys:

```
GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
# ... more ...
```

3. In the ElevenLabs dashboard, create your custom "TARS" voice and place its Voice ID in the `.env` file.

## Future Work \& Roadmap

- [ ] **Improve Noise Cancellation**: Implement software-based noise reduction on the audio stream received from the ESP32.
- [ ] **Dynamic Configuration of system settings**: Allow system settings (e.g., conversation timeout) to be changed via voice commands.
- [ ] **Dynamic Configuration of preferences**: Allow to save preferences, possibly in a system of memories (humor setting, personality etc.).
