# Server Refactoring Plan: Single-Client Architecture

This document outlines the step-by-step plan for refactoring the GemiTARS server to support the new Raspberry Pi client. The architecture will be designed to handle a single client connection at a time.

---

## **Step 1: Create `PiInterfaceService` Skeleton**

*   **Goal:** Create the new service's abstract interface, defining the contract for how `TARSAssistant` will communicate with the Raspberry Pi.
*   **Action:** Create a new file, `src/services/pi_interface.py`. This file will contain an abstract base class `PiInterfaceService` that defines all the necessary methods for communication (e.g., `initialize`, `play_audio_chunk`, `shutdown`, `set_callbacks`). This provides a clean blueprint for the concrete implementation and makes refactoring `TARSAssistant` straightforward.

---

## **Step 2: Refactor `TARSAssistant` for New Interface**

*   **Goal:** Decouple `TARSAssistant` from the obsolete ESP32 and hotword services and connect it to the new `PiInterfaceService`.
*   **Actions in `src/main.py`:**
    1.  **Replace Imports**: Remove imports for `ESP32ServiceInterface`, `ESP32MockService`, and `HotwordService`. Add an import for the new `PiInterfaceService`.
    2.  **Update `__init__`**: Replace `self.esp32_service` and `self.hotword_service` with a single `self.pi_service`.
    3.  **Delete Obsolete Methods**: Remove `_initialize_esp32_service()`, `_route_audio_based_on_state()`, and `_on_hotword_detected()`.
    4.  **Adapt Core Logic**:
        *   The `run()` method will now initialize and start the `pi_service`.
        *   `_enter_active_mode()` will be triggered by a callback from the `pi_service` when the client signals a hotword was detected.
        *   `_stream_tts_response()` will use `self.pi_service.play_audio_chunk()` to send audio to the Pi.

---

## **Step 3: Implement `PiInterfaceService` WebSocket Logic**

*   **Goal:** Build the concrete implementation of the `PiInterfaceService` that handles the actual WebSocket communication.
*   **Actions:**
    1.  **Create `PiWebsocketService`**: Create a new class, likely in a new file like `src/services/pi_websocket_service.py`, that implements the `PiInterfaceService` abstract class.
    2.  **Implement WebSocket Server**: This class will start and manage a WebSocket server. It will be designed to handle only one client connection at a time.
    3.  **Implement Message Handling**: The server will listen for messages and distinguish between:
        *   **JSON commands** (e.g., `{"type": "hotword_detected"}`) which will trigger callbacks into `TARSAssistant`.
        *   **Binary audio data**, which will be passed back to `TARSAssistant` to be forwarded to the `GeminiService`.
    4.  **Implement Audio Playback**: The `play_audio_chunk` method will send binary TTS audio from the server to the connected client.

---

## **Step 4: Final Integration and Cleanup**

*   **Goal:** Ensure the new system works correctly and remove all obsolete files.
*   **Actions:**
    1.  **Integration Test**: Verify the complete, end-to-end communication flow.
    2.  **Delete Obsolete Files**: Permanently delete `src/services/esp32_interface.py`, `src/services/esp32_mock_service.py`, and `src/services/_hotword_service_deprecated.py`.