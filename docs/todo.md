# 📝 Project TODO (Server + Raspberry Pi Client)

> **Note:** This list includes rough ideas and items in flux. Some may not be feasible or finalized.

---

## 🛠️ Core Tasks

- [ ] 🔴 Play local acknowledgment sound (e.g., “mhm”, “listening...”).
- [ ] 🔴 Implement actual I2S mic/speaker code on the Pi client.
- [ ] 🟠 Test mic/speaker reliability, audio clarity, and latency.
- [ ] 🟠 ElevenLabs retraining
  - Use voice samples from the current model to reduce pitch inconsistency.
- [ ] 🟠 Refactor session & state management
  - Reduce complexity and avoid server/client state desync.
  - Possibly merge passive/listening/processing/active phases.
- [ ] 🔴 Maintain persistent WebSocket connection from Pi to server.
  - Required for immediate audio streaming after hotword detection.
- [ ] 🔴 Improve connection stability & reconnection logic.
- [ ] 🟡 Noise cancellation
  - Implement software noise reduction (e.g., ONNX/OpenWakeWord).
  - Calibrate for INMP441 mic specifically.
- [ ] 🟡 Handle interruptions and echo/feedback cancellation.
- [ ] 🟡 Dynamic configuration of system settings (e.g., timeout) via voice.
- [ ] 🟢 Dynamic user preferences
  - Humor/personality settings, memory of prior choices.
- [ ] 🟢 Long-term memory system
  - Vector DB and/or chat memory (e.g., 1-hour rolling context).
- [ ] 🟢 Custom wake word verifier model
  - See: [openWakeWord user-specific models](https://github.com/dscripka/openWakeWord#user-specific-models)
- [ ] 🟢 Consolidate `/server` and `/pi_software` startup methods.
- [ ] 🟢 Implement TARS robot display output.

---

## 🐛 Known Bugs

- None formally tracked here yet.

---

## 🤔 Questionable / Experimental

- Nothing tracked here yet.

---

## 🔧 PI Software-Specific TODOs

### 1. Session Timeout

- [ ] Add `SESSION_TIMEOUT` to `pi_software/src/config/settings.py`.
- [ ] In `session_manager.py`, start a timeout timer when session activates.
- [ ] On timeout, force disconnect WebSocket and return to idle/hotword state.

### 2. WebSocket Reconnection Logic

- [ ] Add `RECONNECT_DELAY` and `MAX_RECONNECT_ATTEMPTS` to settings.
- [ ] In `session_manager.py`, retry WebSocket connection on failure using exponential backoff.

---

## ✅ Completed

- Nothing tracked here yet.
