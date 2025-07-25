# Migration Plan: ESP32 to Raspberry Pi Zero 2W

This document provides a detailed, step-by-step plan for migrating the GemiTARS project from an ESP32-based architecture to a Raspberry Pi Zero 2W. The core architectural change is moving from server-side hotword detection to on-device hotword detection.

**Old Architecture:** ESP32 streams all audio to the server -> Server detects hotword -> Server manages conversation.
**New Architecture:** Raspberry Pi detects hotword locally -> Pi initiates connection and streams audio to the server -> Server manages conversation.

## New Raspberry Pi Client Implementation

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