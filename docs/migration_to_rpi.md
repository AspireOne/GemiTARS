# Migration Plan: ESP32 to Raspberry Pi Zero 2W

This document provides a detailed, step-by-step plan for migrating the GemiTARS project from an ESP32-based architecture to a Raspberry Pi Zero 2W. The core architectural change is moving from server-side hotword detection to on-device hotword detection.

**Old Architecture:** ESP32 streams all audio to the server -> Server detects hotword -> Server manages conversation.
**New Architecture:** Raspberry Pi detects hotword locally -> Pi initiates connection and streams audio to the server -> Server manages conversation.

## Server-Side Refactoring

This phase adapts the main server application to the new, more passive operational flow.

### Refactor Main Application (`src/main.py`)

The `TARSAssistant` class needs significant changes to remove all dependencies on the ESP32 and server-side hotword detection.

-   **Imports:**
    -   Remove imports for `ESP32ServiceInterface`, `ESP32MockService`, and `HotwordService`.
    -   Add an import for a new `PiInterfaceService` (to be created).

-   **`__init__` method:**
    -   Remove `self.hotword_service` and `self.esp32_service` attributes.
    -   Remove the line `self.hotword_service.set_activation_callback(...)`.
    -   Add a `self.pi_service` attribute, initialized to an instance of the new `PiInterfaceService`.

-   **Delete Methods:**
    -   `_initialize_esp32_service()`: No longer needed.
    -   `_route_audio_based_on_state()`: The server will no longer route audio for hotword detection. The new `PiInterfaceService` will handle incoming audio directly.
    -   `_on_hotword_detected()`: This callback is obsolete.

-   **Refactor `run()` method:**
    -   The main loop will change. Instead of starting services and entering a passive listening mode, it should initialize the `PiInterfaceService` and wait for incoming connections.
    -   The concept of the server's `_enter_passive_mode()` is no longer valid in the same way. The server is *always* passive until a Pi connects.

-   **Refactor `_enter_passive_mode()`:**
    -   This method's logic needs to be re-evaluated. It was responsible for stopping a Gemini session and starting hotword detection. Now, it will simply mean closing the connection to a specific Pi client.

-   **Refactor `_enter_active_mode()`:**
    -   This method will no longer be triggered by a local hotword callback. It will be triggered by the new `PiInterfaceService` when a Pi client connects and signals that a hotword was detected.

-   **Refactor `_stream_tts_response()` and other methods:**
    -   All calls to `self.esp32_service` must be replaced with calls to `self.pi_service`. For example, `self.esp32_service.play_audio_chunk(audio_chunk)` becomes `self.pi_service.play_audio_chunk(audio_chunk)`.

### 2.3. Create New Pi Interface Service

A new service is required to manage communication with the Raspberry Pi clients.

-   **Action:** Create a new file `src/services/pi_interface.py`.
-   **Functionality:**
    -   It should implement a WebSocket server (or similar protocol).
    -   It will listen for incoming connections from Pi clients.
    -   When a client connects, it will trigger the `_enter_active_mode()` logic in `main.py`.
    -   It will receive the audio stream from the Pi and forward it to the `GeminiService`.
    -   It will receive the synthesized TTS audio from the `ElevenLabsService` and stream it back to the correct Pi client.
    -   It needs a similar abstract interface to the old `ESP32ServiceInterface` for methods like `play_audio_chunk`, `wait_for_playback_completion`, etc., to minimize changes in `main.py`.

---

DO NOT YET IMPLEMENT ANYTHING BELOW!!

## Phase 3: New Raspberry Pi Client Implementation -

This phase involves creating the new software that will run on the Raspberry Pi itself.

### 3.1. Create Project Structure

-   **Action:** Create a new directory named `pi_software/`.
-   **Contents:** This directory will contain the Python application for the Pi, including:
    -   A `main.py` or `client.py` entry point.
    -   A `requirements.txt` for its dependencies (e.g., `openwakeword`, `websockets`, `sounddevice`).
    -   Configuration files for the Pi (e.g., server IP address).

### 3.2. Implement Client Functionality

The Python application in `pi_software/` must perform the following tasks:

1.  **Audio Setup:**
    -   Use a library like `sounddevice` or `PyAudio` to interface with the I2S microphone and speaker via ALSA, as configured in the OS.
2.  **Local Hotword Detection:**
    -   Continuously read from the microphone.
    -   Feed the audio into an instance of `openwakeword`.
    -   When the wake word ("Hey, TARS!") is detected, proceed to the next step.
3.  **Server Connection:**
    -   On hotword detection, establish a WebSocket connection to the main server.
    -   Play a local acknowledgment sound ("mhm," "listening...").
4.  **Audio Streaming:**
    -   Stream live microphone audio to the server over the WebSocket connection.
    -   Simultaneously, listen for incoming audio from the server (the TTS response).
    -   Play the received TTS audio through the speaker.
5.  **Session Management:**
    -   If the server closes the connection (e.g., due to a timeout), the client should disconnect, stop streaming, and return to local hotword detection.