# Implementation Plan: Server-Pi Dynamic Configuration Synchronization

This document outlines the technical plan to enable dynamic, persistent configuration changes on the Raspberry Pi client, synchronized from the central server.

## 1. Goals

- **Centralized Management**: The server will act as the single source of truth for all configuration changes, including those affecting the Pi.
- **Persona-Driven Configuration**: Changing the active persona on the server will automatically trigger corresponding configuration changes on the Pi (e.g., updating hotword models).
- **Runtime Updates**: The Pi client must react to configuration changes in real-time without requiring a restart.
- **Persistence**: All configuration changes on the Pi must be saved locally and persist across reboots.

## 2. Architecture Overview

The solution involves three main components:

1.  **Server-Side Logic**: The server's `SettingsManager` will be enhanced to send configuration updates to the Pi.
2.  **Communication Protocol**: A new WebSocket message type will be defined for sending configuration data.
3.  **Pi-Side Logic**: The Pi will have its own `SettingsManager` to receive, apply, and persist these updates, and a mechanism to notify services of changes.

```mermaid
graph TD
    subgraph Server
        A[LLM Command: update_config] --> B{SettingsManager};
        C[personas.json] -- Defines pi_config --> B;
        B -- 1. Updates local config --> D[config_override.json];
        B -- 2. Extracts pi_config --> E[PiInterface];
    end

    subgraph "WebSocket"
        E -- 3. Sends 'config_update' message --> F[WebSocket Client];
    end

    subgraph Raspberry Pi
        F -- 4. Receives message --> G{Pi SettingsManager};
        G -- 5. Updates & persists --> H[pi_local/config_override.json];
        G -- 6. Notifies services --> I[HotwordDetector];
        G -- 6. Notifies services --> J[Logger];
        I -- 7. Re-initializes with new model --> K[Hardware];
    end

    style Server fill:#d5f5e3
    style "Raspberry Pi" fill:#eaf2f8
```

## 3. Implementation Phases

### Phase 1: Pi Configuration Foundation (Completed)

- **[x] Restructure Pi Config Files**:
  - Renamed `pi_software/src/config/settings.py` to `default_settings.py`.
  - Created a new `SettingsManager` in `pi_software/src/config/settings.py`.
- **[x] Implement Local Overrides**:
  - The new `SettingsManager` loads defaults and applies overrides from `pi_software/local/config_override.json`.
- **[x] Ensure `.gitignore` is Updated**:
  - Added `pi_software/local/` to `.gitignore`.

### Phase 2: Server-to-Pi Communication

- **Task 2.1: Extend Persona Definitions**

  - **File**: `server/local/personas.json`
  - **File**: `server/src/config/personas.example.json`
  - **Action**: Add a `pi_config` object to each persona definition. This object will contain key-value pairs for Pi-specific settings.
  - **Example**:
    ```json
    "TARS": {
      "voice_id": "...",
      "pi_config": {
        "HOTWORD_MODELS": ["Hey_Tars.tflite", "Tars.tflite"],
        "ACKNOWLEDGEMENT_AUDIO_FILES": ["yes.raw"]
      }
    }
    ```

- **Task 2.2: Update Server `SettingsManager` to Send `pi_config`**

  - **File**: `server/src/config/settings.py`
  - **Action**: Modify the `_switch_persona` method. After successfully switching the persona, it should check if a `pi_config` exists for the new persona.
  - **Action**: If `pi_config` exists, call a new method on the `PiInterface` service (e.g., `pi_interface.send_config_update(pi_config)`).

- **Task 2.3: Implement `PiInterface` Logic**

  - **File**: `server/src/services/pi_interface.py`
  - **Action**: Create a new method `send_config_update(config_payload: dict)`.
  - **Action**: This method will format a WebSocket message with `type: 'config_update'` and `payload: config_payload` and send it to the connected Pi client.

- **Task 2.4: Implement `config_update` Handler on Pi**
  - **File**: `pi_software/src/services/websocket_client.py`
  - **Action**: In the message handling loop, add a case for `message['type'] == 'config_update'`.
  - **Action**: When this message is received, call the `update_bulk` method on the Pi's `SettingsManager` instance (`Config.update_bulk(message['payload'])`).

### Phase 3: Dynamic Re-configuration on the Pi

- **Task 3.1: Introduce a Notification/Callback System**

  - **File**: `pi_software/src/config/settings.py`
  - **Action**: Add a callback registration system to the Pi's `SettingsManager`. It will maintain a dictionary mapping configuration keys to a list of callback functions.
  - **Action**: Create methods `register_callback(key: str, callback: Callable)` and `unregister_callback(key: str, callback: Callable)`.
  - **Action**: In the `set` and `update_bulk` methods, after a value is changed, iterate through the registered callbacks for the updated key(s) and execute them.

- **Task 3.2: Add `reconfigure` Methods to Pi Services**
  - **File**: `pi_software/src/core/hotword_detector.py`
  - **Action**: Create a `reconfigure()` method. This method will re-initialize the `openwakeword.Model` with the new `HOTWORD_MODELS` and `HOTWORD_THRESHOLD` from the `Config` object.
  - **Action**: In the `__init__` method of `HotwordDetector`, register its `reconfigure` method as a callback for the `HOTWORD_MODELS` and `HOTWORD_THRESHOLD` keys.
  - **File**: `pi_software/src/utils/logger.py`
  - **Action**: Create a function `update_log_level()` that gets the current logger and sets its level based on `Config.LOG_LEVEL`.
  - **Action**: In `setup_logger`, register `update_log_level` as a callback for the `LOG_LEVEL` key.

### Phase 4: Finalization & Testing

- **Task 4.1: End-to-End Test**
  - **Action**: Start both the server and the Pi client.
  - **Action**: Use an LLM command (or a test script) to switch the persona on the server.
  - **Verification**:
    1.  Check server logs to confirm the `pi_config` was sent.
    2.  Check Pi logs to confirm the `config_update` message was received and applied.
    3.  Check the contents of `pi_software/local/config_override.json` to verify persistence.
    4.  Observe the Pi's `HotwordDetector` logs to confirm it re-initialized with the new models.
- **Task 4.2: Code Cleanup**
  - **Action**: Remove any temporary test files or code.
  - **Action**: Ensure all new code is documented and follows project style guidelines.
