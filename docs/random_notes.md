Here are common software strategies to eliminate popping:

- Play Silence: The simplest solution is to have your system continuously play silence whenever it's not playing audible audio. This keeps the I2S clocks active and stable, so the amplifier never sees the start/stop signal that causes the pop. For a system like a Raspberry Pi, this can be done by running a background process that sends a silent audio stream to the amplifier.

- Use Mute Functions: Instead of shutting down the I2S stream between tracks, use a software "mute" function. This keeps the stream alive but sends zero-value data, effectively producing silence without stopping the clocks.

- Driver Configuration: On some platforms like Raspberry Pi, you can modify the audio driver settings. For example, using the dtoverlay=max98357a configuration in /boot/config.txt without the no-sdmode option allows the system to manage the shutdown pin, which can help reduce pops.

- to convert mp3 files to the specs below, use: `ffmpeg -i input.mp3 -ar 16000 -ac 1 -f s16le -acodec pcm_s16le input.raw`

```
* Sample Rate: 16000 Hz
* Data Type: 16-bit signed integers (int16)
* Channels: 1 (Mono)
* Format: Raw bytes (no headers like WAV, MP3, etc.)
```
