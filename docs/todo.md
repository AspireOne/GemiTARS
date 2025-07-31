# 📝 Project TODO (Server + Raspberry Pi Client)

> **Note:** This list includes rough ideas and items in flux. Some may not be feasible or finalized.

---

## 🛠️ Core Tasks

**Pi:**

- [ ] 🟠 Fix popping sound on PI 2 W microphone + fix auto-starting aplay service (installed by Adafruit, tries to always play silence to fix the popping). (https://claude.ai/chat/1212c816-140e-4e45-a94e-b5cf1bcfb1ed)
- [ ] 🟠 Check CPU/mem usage (from another terminal) during hotword detection?

---

- [ ] 🔴 Use Cartesia instead of ElevenLabs / switch services
  - ~~play.ht~~ - Registration disabled,
  - ~~Murf.ai~~ - Ultra low limits,
  - Cartesia,
  - Speechify (300ms latency w/o network VS ElevenLabs 70ms w/o network),
  - Resemble.AI,
  - Azure AI Speech,
  - Google TTS - No cloning,
  - Amazon TTS / Amazon Polly - Not exactly cloning,
  - Humane Octave, Papla P1,
  - Built-in TTS for testing at development (+ abstract out elevenlabsService so I can switch them?)?
  - ========= LOCAL =========
  - NOTE: [alltalkbeta](https://github.com/erew123/alltalk_tts/tree/alltalkbeta) - tools for local TTS (Coqui XTTS TTS, Piper, F5...)
  - [GPT-Sovits](https://github.com/RVC-Boss/GPT-SoVITS)
  - [Kokoro onnx](https://github.com/thewh1teagle/kokoro-onnx) (no cloning)
  - Fish, MaskCGT, OpenVoice, RVC/XTTS2, F5-TTS...
  - ~~CosyVoice~~ (GPU heavy), ~~Spark-TTS~~ (1s latency), 
- [ ] 🔴 Add Pi client notifications (e.g. session timeout, end hotword detected session end, or just general session end) directly to state management logic (and possibly do that for other actions too) so that it's always necessarily synchronized and doesn't rely on us properly calling both change state and notify client (? needs more research)
- [ ] 🔴 Play local acknowledgment sound (e.g., “mhm”, “listening...”) after hotword detection.
- [ ] 🔴 Play sound before TARS replies, like "Mmmm..." to make it seem more snappy? (maybe)
  - Use voice samples from the current model to reduce pitch inconsistency.
- [ ] 🟠 Refactor session & state management (maybe?)
  - Reduce complexity and avoid server/client state desync.
  - Possibly merge passive/listening/processing/active phases.
- [ ] 🟡 Handle interruptions and echo/feedback cancellation (?).
- [ ] 🟡 Retrain ElevenLabs voice.
- [ ] 🟡 Add physical button to turn on the conversation (adjust code to allow it)
- [ ] 🟡 Dynamic configuration of system settings (e.g., timeout) via voice.
- [ ] 🟢 Dynamic user preferences
  - Humor/personality settings, memory of prior choices.
- [ ] 🟢 Long-term memory system
  - Vector DB and/or chat memory (e.g., 1-hour rolling context).
- [ ] 🟢 Custom wake word verifier model

  - See: [openWakeWord user-specific models](https://github.com/dscripka/openWakeWord#user-specific-models)

- [ ] 🟢 Possibly play a sound or otherwise singalise when a session ends (times out or session ending word is detected or something) (?)
- [ ] 🟢 Implement TARS robot display output.
- [ ] 🟢 Use normal .wav or .mp3 files for acknowledgement audio instead of raw binary data. We'll just convert it during startup before loading it into memory.

---

## 🐛 Known Bugs

- [ ] 🟢 When TTS is too long, the speaker craps itself (lags during playback, has long pauses between playback (buffer issue?))
- [ ] 🔴 'Audio playback finished' message sent prematurely from the PI if TTS audio long (> ~2 sentences)!
- [ ] 🟠 Fix popping sound on PI 2 W microphone + fix auto-starting aplay service (installed by Adafruit, tries to always play silence to fix the popping).
- [ ] 🔴 When playing acknowledgement audio on the Pi, right after detecting a hotword, there's a chance the speaker output will be fed into the microphone (if the session establishes faster than the audio playback finishes). More likely with longer sentences. Solution: the mic should be somehow disabled or something (depending on the specific implementation of the current code) before the acknowledgement audio playback finishes.

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
- [x] 🟡 Potentially use bidirectional WS in elevenlab? https://elevenlabs.io/docs/best-practices/latency-optimization#websockets
- [x] 🔴 on RPI 2 W, USE .tflite (ARM) instead of .onnx!! More performant, but Windows (and my laptop) don't support it.
- [x] 🔴 Move relevant settings from config file to .env file.
- [x] 🔴 Implement actual I2S mic/speaker code on the Pi client.
- [x] 🟠 Explore whether to replace `googlevoicehat-soundcard` overlay with `max98357a` and `i2s-mems-mic`, to potentially support 16kHz 16-bit natively.
- [x] 🟠 Make sure the Pi client is using the ALSA-created mic_mono and speaker_mono devices (make sure they are set as 'default')
- [x] 🟠 Test the sound quality difference in 16khz 16-bit vs native 48khz 32-bit (full example of the commands in docs/hardware_configuration.md - "Optimized ALSA Configuration")
- [x] 🟠 Optimize audio playing on the Pi client (stability/reliability/robustness, performance, configuration with the speaker... Currently it seems to stutter and the TTS audio buffer (audio sent from server) is being exceeded)
- [x] 🟠 Review, improve I2S mic/speaker code on the Pi client.
- [x] 🟠 Actually test mic/speaker reliability, audio clarity, and latency (add latency logging to every step possible)
- [x] 🟠 Calibrate hotword sensitivity and parameters for INMP441 mic specifically.
