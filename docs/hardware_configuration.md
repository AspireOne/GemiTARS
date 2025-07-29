# Raspberry Pi Zero 2W Audio Setup - INMP441 + MAX98357A

## Hardware Configuration

### Microphone: INMP441

- **Type**: I2S MEMS microphone
- **Connection**: Shared I2S bus with speaker

### Speaker: MAX98357A

- **Type**: I2S Class-D amplifier
- **Connection**: Shared I2S bus with microphone

### Wiring (I2S Bus Sharing)

- **SCK (INMP441) + BCLK (MAX98357A)**: Shared clock line
- **WS (INMP441) + LRC (MAX98357A)**: Shared word select line
- **SD (INMP441)**: I2S data input to Pi
- **DIN (MAX98357A)**: I2S data output from Pi

### Aplay HW Parameters (aplay -D hw:0,0 --dump-hw-params /dev/zero):

```
Playing raw data '/dev/zero' : Unsigned 8 bit, Rate 8000 Hz, Mono

HW Params of device "hw:0,0":
--------------------
ACCESS:        MMAP_INTERLEAVED, RW_INTERLEAVED
FORMAT:        S32_LE
SUBFORMAT:     STD
SAMPLE_BITS:   32
FRAME_BITS:    64
CHANNELS:      2
RATE:          48000
PERIOD_TIME:   (666 682667)
PERIOD_SIZE:   [32 32768]
PERIOD_BYTES:  [256 262144]
PERIODS:       [2 2048]
BUFFER_TIME:   (1333 1365334)
BUFFER_SIZE:   [64 65536]
BUFFER_BYTES:  [512 524288]
TICK_TIME:     ALL
--------------------

aplay: set_params:1352: Sample format not available

Available formats:
- S32_LE
```

### Arecord HW Parameters (arecord -D hw:0,0 --dump-hw-params /dev/null):

```
Recording WAVE '/dev/null' : Unsigned 8 bit, Rate 8000 Hz, Mono

HW Params of device "hw:0,0":
--------------------
ACCESS:        MMAP_INTERLEAVED, RW_INTERLEAVED
FORMAT:        S32_LE
SUBFORMAT:     STD
SAMPLE_BITS:   32
FRAME_BITS:    64
CHANNELS:      2
RATE:          48000
PERIOD_TIME:   (666 682667)
PERIOD_SIZE:   [32 32768]
PERIOD_BYTES:  [256 262144]
PERIODS:       [2 2048]
BUFFER_TIME:   (1333 1365334)
BUFFER_SIZE:   [64 65536]
BUFFER_BYTES:  [512 524288]
TICK_TIME:     ALL
--------------------

arecord: set_params:1352: Sample format not available

Available formats:
- S32_LE
```

## Software Configuration

### ALSA Mixer Settings:

```
amixer -c 0 contents
amixer -c 0 controls
# (Output not included, likely too verbose or omitted)
```

### Device Overlay Help (dtoverlay -h googlevoicehat-soundcard):

```
Name:   googlevoicehat-soundcard

Info:   Configures the Google voiceHAT soundcard

Usage:  dtoverlay=googlevoicehat-soundcard

Params: <None>

```

### Other

```
aplay -D hw:0,0 -f S16_LE -r 44100 -c 2 /dev/zero & PID=$!; sleep 1; kill $PID

# Check dmesg for any format messages
dmesg | grep -i "rate\|format\|channel" | tail -10
[1] 660
Playing raw data '/dev/zero' : Signed 16 bit Little Endian, Rate 44100 Hz, Stereo
aplay: set_params:1352: Sample format non available
Available formats:
- S32_LE
[1]+  Exit 1                  aplay -D hw:0,0 -f S16_LE -r 44100 -c 2 /dev/zero
-bash: kill: (660) - No such process
[    0.145848] RPC: Registered tcp NFSv4.1 backchannel transport module.
[    1.271597] simple-framebuffer 1eaa9000.framebuffer: format=a8r8g8b8, mode=720x480x32, linelength=2880
[    2.356191] mmc-bcm2835 3f300000.mmcnr: DMA channel allocated
[    5.283328] systemd[1]: Set up automount proc-sys-fs-binfmt_misc.automount - Arbitrary Executable File Formats File System Automount Point.
```

### /boot/firmware/config.txt

```ini
# Enable I2S interface
dtparam=i2s=on
dtparam=audio=on

# Use Google Voice HAT overlay (handles both mic and speaker)
dtoverlay=googlevoicehat-soundcard

# Optional audio optimizations
audio_pwm_mode=2
disable_splash=1
```

### Key Points

- **Use ONLY `googlevoicehat-soundcard` overlay** - it handles both input and output
- **Do NOT use `max98357a` overlay** when using googlevoicehat-soundcard
- **Remove any `/etc/asound.conf`** files created by installation scripts

## Verification Commands

### Check Audio Devices

```bash
# List playback devices
aplay -l

# List capture devices
arecord -l

# Expected output: Both should show card 0 as "snd_rpi_googlevoicehat_soundcar"
```

### Test Audio

```bash
# Test microphone
arecord -D plughw:0,0 -f S32_LE -r 48000 -c 2 -V stereo recording.wav

# Test speaker (playback)
aplay -D hw:0,0 test.wav
```

## Working Configuration Result

- **Card 0**: `snd_rpi_googlevoicehat_soundcar` - Both input AND output
- **Device 0**: Both playback and capture available
- **Hardware**: `hw:0,0` for both recording and playback

## Troubleshooting

### If Audio Devices Don't Appear

1. Check for corrupted ALSA config: `sudo mv /etc/asound.conf /etc/asound.conf.backup`
2. Verify I2S is enabled: `dtparam=i2s=on` in config.txt
3. Ensure only one overlay is used: either `googlevoicehat-soundcard` OR `max98357a`, not both

### If Microphone Stops Working After Adding Speaker

- This was caused by overlay conflicts and corrupted asound.conf, possibly after adafruit install script
- Solution: Use only `googlevoicehat-soundcard` overlay and remove asound.conf

## Installation Script Issues

- Adafruit installation scripts may create conflicting `/etc/asound.conf`
- Always test after running third-party scripts
- Keep a backup of working config.txt
