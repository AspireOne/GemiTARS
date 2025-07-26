# Server Refactoring Report: ESP32 to Raspberry Pi Migration

**Objective:** To refactor the GemiTARS server application, decoupling it from the legacy ESP32-based architecture and preparing it for a new, more intelligent Raspberry Pi client.

## Executive Summary of Changes

The core architectural shift was to move the server from a *proactive* to a *reactive* model.

*   **Old Model (Proactive):** The server was responsible for actively listening to a raw audio stream from a "dumb" ESP32 client, detecting the hotword, and then managing the conversation.
*   **New Model (Reactive):** The server is now a passive endpoint that waits for an intelligent Raspberry Pi client to connect. The Pi handles its own audio and hotword detection locally and initiates a conversation with the server only when needed.

This refactoring involved three key phases:
1.  **Decoupling:** Removing all hardcoded dependencies on the ESP32 and server-side hotword services.
2.  **Abstracting:** Creating a clean, new communication interface (`PiInterfaceService`) to define how the server should interact with any Pi-like client.
3.  **Implementing:** Building a concrete implementation of that interface using WebSockets (`PiWebsocketService`) to handle the actual network communication.

---

## Code-Level Walkthrough

### 1. Deletion of Obsolete Services

**What was done?**
The following files, which were central to the old architecture, were deleted:
*   `src/services/esp32_interface.py`
*   `src/services/esp32_mock_service.py`
*   `src/services/_hotword_service_deprecated.py`

**Why?**
These services were built on the premise that the server receives a continuous, raw audio stream and is responsible for processing it to find a hotword. In the new architecture, this entire responsibility shifts to the Raspberry Pi client. The Pi will now perform local hotword detection using `OpenWakeWord` and will only contact the server *after* a hotword has been detected. Therefore, these server-side services became entirely redundant. Their deletion was the first and most critical step in cleaning up the codebase.

### 2. Creation of a New, Clean Communication Interface

**What was done?**
A new file was created:
*   [`src/services/pi_interface.py`](src/services/pi_interface.py)

This file defines an abstract base class, `PiInterfaceService`, which acts as a formal contract for any service that communicates with the Pi.

**Why?**
This follows the Dependency Inversion Principle. Instead of having the main `TARSAssistant` class depend directly on a concrete implementation like WebSockets, it now depends on this abstract interface. This makes the system more modular and testable. For example, in the future, we could easily create a `PiMockService` that implements this same interface for testing purposes, and `TARSAssistant` wouldn't need to change at all.

This interface defines the essential communication methods: `initialize`, `shutdown`, `play_audio_chunk`, etc., ensuring a consistent API for the main application.

### 3. Implementation of the WebSocket Service

**What was done?**
A new file was created to provide the concrete implementation of the interface:
*   [`src/services/pi_websocket_service.py`](src/services/pi_websocket_service.py)

This file contains the `PiWebsocketService` class, which handles all the logic for running a WebSocket server, accepting a client connection, and managing the bidirectional flow of data.

**Why?**
WebSockets were chosen as the communication protocol because they provide a persistent, low-latency, full-duplex connection, which is ideal for real-time audio streaming. This service implements:
*   A connection handler that allows only one client at a time, as per our simplified design.
*   A message handler that can distinguish between:
    *   **JSON control messages** (e.g., `{"type": "hotword_detected"}`) from the Pi.
    *   **Binary audio data** (the microphone stream) from the Pi.
*   An audio playback queue to send TTS audio from the server back to the Pi without blocking.

### 4. Refactoring the Core Application (`TARSAssistant`)

**What was done?**
The `TARSAssistant` class in [`src/main.py`](src/main.py) was significantly overhauled to adapt to the new reactive model.

**Why?**
This was the central part of the refactoring, where the application's behavior was fundamentally changed.

*   **Imports and Initialization:** The old `ESP32Service` and `HotwordService` were removed and replaced with a single `self.pi_service` attribute, which is an instance of our new `PiWebsocketService`.

*   **Deleted Methods:**
    *   `_initialize_esp32_service()`: No longer needed.
    *   `_route_audio_based_on_state()`: The server no longer routes audio for hotword detection. The Pi decides when to send audio.
    *   `_on_hotword_detected()`: This server-side callback is obsolete. The new trigger is a WebSocket message from the client.

*   **Modified Methods:**
    *   **`run()`**: The main loop is now much simpler. It initializes the `PiInterfaceService` and then blocks, waiting for it to handle connections. The server is now entirely passive until a client connects.
    *   **`_enter_active_mode()`**: This is no longer called by an internal hotword service. Instead, it's now a *callback* that gets passed to the `PiInterfaceService`. The WebSocket service calls this method when it receives the `hotword_detected` message from the client.
    *   **`_enter_passive_mode()`**: This method's role has changed. It no longer needs to restart hotword detection. It now simply cleans up the Gemini session and resets the state, waiting for the next client-initiated conversation.
    *   **`_stream_tts_response()`**: All calls to the old `esp32_service` were cleanly replaced with calls to `self.pi_service`, demonstrating the value of our new abstract interface.

---

## Final State

The server is now a clean, modern, and reactive application. It has a clear separation of concerns, with the `TARSAssistant` managing the conversation state and the `PiInterfaceService` handling all network communication. This new architecture is not only more robust but also perfectly aligned with the capabilities of the new Raspberry Pi Zero 2W client.
---

## Appendix: Preservation of Timeout Logic

A key piece of existing functionality is the automatic conversation timeout, which terminates a session after a period of user inactivity. This logic remains the responsibility of the server and was carefully preserved during the refactoring.

### How it Works

1.  **The Watchdog Loop**: The `_conversation_management_loop` method in `TARSAssistant` runs as a persistent background task. Every second, it checks if the system is in the `ACTIVE` state (i.e., waiting for the user to speak).

2.  **The Timeout Condition**: If the system is `ACTIVE`, the loop calls `self.conversation_manager.is_conversation_timeout()`. This method checks if more than 30 seconds have passed since the last recorded "activity."

3.  **Activity Reset**: The definition of "activity" is crucial. The timeout clock is reset whenever:
    *   The user speaks (a transcription chunk is received from Gemini). This happens in the `_handle_transcription_chunk` method via a call to `self.conversation_manager.update_activity()`.
    *   The assistant finishes speaking its own response.

4.  **Triggering the Timeout**: If 30 seconds elapse without any of these activities, the watchdog loop logs a timeout message and calls `await self._enter_passive_mode()`, which cleanly shuts down the Gemini session and resets the server to its idle state, ready for the next activation signal from the client.

This ensures that the server will not maintain an open, costly Gemini session indefinitely if the user walks away or stops responding.