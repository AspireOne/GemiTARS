# Implementation Plan: Server-Pi Configuration Synchronization

## 1. Objective

To dynamically update the Raspberry Pi client's configuration (specifically hotword models, detection thresholds, and acknowledgment sounds) in real-time when the server's active persona changes. The system must be robust, reliable, and handle errors gracefully without compromising the client's operational state.

## 2. Core Architecture

This plan implements a **server-push model** using the existing WebSocket connection. The server acts as the single source of truth for Pi-related configuration settings, and the Pi client is a reactive component that validates and applies these settings.

-   **State Synchronization on Connection:** The server will send the current, complete Pi configuration to the client immediately upon a successful WebSocket connection. This ensures the client is always in sync, even if it restarts or was disconnected when a persona change occurred.
-   **Real-time Updates:** The server will proactively push configuration updates to all connected clients whenever the active persona is changed on the server.
-   **Client-Side Resilience & Validation:** The Pi client will treat all incoming configuration data as untrusted. It will perform rigorous validation, including checking for the existence of specified model and audio files. Invalid or incomplete configurations will be logged and rejected, and the client will fall back to its last known-good configuration, ensuring it never crashes or enters an unusable state.

---

## 3. Phase 1: Server-Side Enhancements

**Goal:** Enable the server to manage and transmit Pi-specific configuration for each persona.

#### **Task 1.1: Extend Persona Schema**

-   **File to Modify:** `server/src/config/personas.json.example` (and implicitly the user's `server/local/personas.json`).
-   **Action:** Add a new `pi_config` object to each persona definition. This object will hold all configuration parameters relevant to the Pi client.
-   **Example Schema:**
    ```json
    "TARS": {
      "SYSTEM_PROMPT": "You are TARS...",
      "ELEVENLABS_VOICE_ID": "...",
      "pi_config": {
        "HOTWORD_MODELS": ["Tars.onnx"],
        "HOTWORD_THRESHOLD": 0.2,
        "ACKNOWLEDGEMENT_AUDIO_FILES": ["talk_to_me.raw", "yes.raw"]
      }
    },
    "Alexa": {
        "SYSTEM_PROMPT": "You are Alexa...",
        "ELEVENLABS_VOICE_ID": "...",
        "pi_config": {
            "HOTWORD_MODELS": ["alexa.onnx"],
            "HOTWORD_THRESHOLD": 0.1,
            "ACKNOWLEDGEMENT_AUDIO_FILES": ["huh.raw"]
        }
    }
    ```

#### **Task 1.2: Enhance `SettingsManager`**

-   **File to Modify:** `server/src/config/settings.py`
-   **Action:** Add a new method, `get_active_pi_config()`, to the `SettingsManager` class.
-   **Logic:** This method will retrieve the `pi_config` object from the currently active persona. It must handle cases where `pi_config` is not defined for a persona, returning an empty dictionary to prevent errors.

#### **Task 1.3: Centralize Pi Configuration Logic**

-   **File to Modify:** `server/src/services/pi_websocket_service.py`
-   **Action:**
    1.  Create a new helper method: `_send_pi_config(websocket)`.
    2.  This method will fetch the active Pi config using `Config.get_active_pi_config()`.
    3.  It will then construct and send a JSON message to the specified WebSocket client.
-   **Standardized Message Format:**
    ```json
    {
      "type": "pi_config_update",
      "payload": {
        "HOTWORD_MODELS": ["Tars.onnx"],
        "HOTWORD_THRESHOLD": 0.2,
        "ACKNOWLEDGEMENT_AUDIO_FILES": ["talk_to_me.raw", "yes.raw"]
      }
    }
    ```

---

## 4. Phase 2: WebSocket Communication Integration

**Goal:** Implement the logic for pushing configuration updates from the server to the Pi client.

#### **Task 2.1: Implement Sync-on-Connect**

-   **File to Modify:** `server/src/services/pi_websocket_service.py`
-   **Action:** In the main connection handler (`handle_connection`), add a call to `await self._send_pi_config(websocket)` immediately after a client connection is successfully established and registered.

#### **Task 2.2: Implement Real-time Updates on Persona Change**

-   **File to Modify:** `server/src/config/settings.py`
-   **Action:** The `set` method in `SettingsManager` needs to trigger the broadcast. A clean way to do this without creating a circular dependency is to use a callback system.
    1.  Add a `register_on_persona_change_callback(callback)` method to `SettingsManager`.
    2.  In the `set` method, if `key == 'ACTIVE_PERSONA'`, invoke the registered callbacks.
-   **File to Modify:** `server/src/services/pi_websocket_service.py`
    1.  Create a method `broadcast_pi_config()` that iterates through all connected clients and calls `_send_pi_config()` for each.
    2.  In the service's initialization, register `self.broadcast_pi_config` as a callback with the `SettingsManager`.

---

## 5. Phase 3: Pi Client Implementation

**Goal:** Enable the Pi client to receive, validate, and dynamically apply the new configuration.

#### **Task 3.1: Create a Lightweight `PiConfigManager`**

-   **New File:** `pi_software/src/services/config_manager.py`
-   **Action:** Create a new `PiConfigManager` class. This class is a simple, in-memory state manager, not a file-based one.
-   **Core Logic:**
    -   It will hold the current, validated configuration in a dictionary.
    -   It will expose an `update_config(new_config)` method that will be called by the WebSocket client.
    -   **Validation is Key:** The `update_config` method must:
        -   Iterate through the received `new_config` dictionary.
        -   Ignore any keys that are not in a predefined whitelist (e.g., `['HOTWORD_MODELS', 'HOTWORD_THRESHOLD', 'ACKNOWLEDGEMENT_AUDIO_FILES']`).
        -   For `HOTWORD_MODELS` and `ACKNOWLEDGEMENT_AUDIO_FILES`, verify that each file exists within the `pi_software/src/resources/` directory. Log a warning and discard any file that does not exist.
        -   For `HOTWORD_THRESHOLD`, validate that it is a float between 0.0 and 1.0.
        -   Only apply settings that pass validation.
    -   It will implement a simple observer pattern (e.g., `register_listener(key, callback)`) to notify other services when a specific configuration value has changed.

#### **Task 3.2: Handle Incoming WebSocket Messages**

-   **File to Modify:** `pi_software/src/services/websocket_client.py`
-   **Action:** In the `_receive_loop`, add logic to handle the `pi_config_update` message type. When a message with this type is received, its `payload` should be passed to the `PiConfigManager`'s `update_config` method.

#### **Task 3.3: Make `HotwordDetector` and `LocalSoundManager` Dynamic**

-   **Files to Modify:** `pi_software/src/core/hotword_detector.py` and `pi_software/src/services/local_sound_manager.py`.
-   **Action (for both):**
    1.  During initialization, get the singleton instance of `PiConfigManager`.
    2.  Register a callback with the config manager. For `HotwordDetector`, it will listen for changes to `HOTWORD_MODELS` and `HOTWORD_THRESHOLD`. For `LocalSoundManager`, it will listen for changes to `ACKNOWLEDGEMENT_AUDIO_FILES`.
    3.  The callback function will trigger the necessary re-initialization logic. For the hotword detector, this means reloading the `openwakeword` models. For the sound manager, it means updating its internal list of sound files.

---

## 6. Phase 4: Integration and Resilience Testing

**Goal:** Verify the entire system works as expected and gracefully handles all anticipated error conditions.

#### **Test Plan:**

1.  **Happy Path:**
    -   Start the server and Pi client.
    -   **Verify:** The Pi client logs that it received and applied the configuration for the server's default persona.
    -   Use an LLM command to change the server's persona.
    -   **Verify:** The Pi client logs show it received a new configuration, reloaded its hotword models, and updated its acknowledgment sounds. The new hotword should be active.
2.  **Resilience Testing (Error Conditions):**
    -   **Invalid File:** Manually edit `personas.json` on the server to point to a non-existent hotword model file. Change to that persona.
        -   **Verify:** The Pi client logs a warning about the missing file but **does not crash**. It should continue to use its last known-good hotword model.
    -   **Invalid Value:** Edit `personas.json` to have a `HOTWORD_THRESHOLD` of `2.0`.
        -   **Verify:** The Pi client logs a warning about the invalid value and continues to use its last valid threshold.
3.  **Reconnection Test:**
    -   With the server on a non-default persona, restart only the Pi client.
    -   **Verify:** Upon reconnection, the Pi client immediately receives the correct configuration for the server's current persona and loads the appropriate models and sounds, demonstrating the effectiveness of the sync-on-connect strategy.