# 📝 Project TODO (Server + Raspberry Pi Client)

> **Note:** This list includes rough ideas and items in flux. Some may not be feasible or finalized.

---

## 🛠️ Core Tasks

- [ ] 🔴 Play local acknowledgment sound (e.g., “mhm”, “listening...”).
- [ ] 🔴 on RPI 2 W, USE .tflite (ARM) instead of .onnx!! More performant, but Windows (and my laptop) don't support it.
- [ ] 🔴 Move relevant settingss from config file to .env file.
- [ ] 🔴 Implement actual I2S mic/speaker code on the Pi client.
- [ ] 🟠 Test mic/speaker reliability, audio clarity, and latency.
- [ ] 🟠 Retrain ElevenLabs voice.
  - Use voice samples from the current model to reduce pitch inconsistency.
- [ ] 🟠 Refactor session & state management
  - Reduce complexity and avoid server/client state desync.
  - Possibly merge passive/listening/processing/active phases.
- [ ] 🟡 Noise cancellation
  - Implement software noise reduction (e.g., ONNX/OpenWakeWord).
  - Calibrate for INMP441 mic specifically.
- [ ] 🟡 Handle interruptions and echo/feedback cancellation (?).
- [ ] 🟡 Dynamic configuration of system settings (e.g., timeout) via voice.
- [ ] 🟢 Dynamic user preferences
  - Humor/personality settings, memory of prior choices.
- [ ] 🟢 Long-term memory system
  - Vector DB and/or chat memory (e.g., 1-hour rolling context).
- [ ] 🟢 Custom wake word verifier model

  - See: [openWakeWord user-specific models](https://github.com/dscripka/openWakeWord#user-specific-models)

- [ ] 🟢 Implement TARS robot display output.

---

## 🐛 Known Bugs

- [ ] 🔴 'Audio playback finished' message sent prematurely from the PI if TTS audio long (> ~2 sentences).

---

## 🔧 PI Software-Specific TODOs

### 1. Session Timeout

- [ ] Add `SESSION_TIMEOUT` to `pi_software/src/config/settings.py`.
- [ ] In `session_manager.py`, start a timeout timer when session activates.
- [ ] On timeout, force disconnect WebSocket and return to idle/hotword state.

---

## ✅ Completed

- [x] 🔴 Maintain persistent WebSocket connection from Pi to server.
- [x] 🟢 Convert `/server` and `/pi_software` both to modules.
