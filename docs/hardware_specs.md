# Hardware

IMPROVEMENT:
Tap his head to activate!! 100% reliability, less hassle, will start the conversation right away, and also is comical when you bonk his head and he says "Huh?!!"

This document outlines the specifications, hardware integration, pinout, and setup for the hardware of this project - using a Raspberry Pi Zero 2W in a TARS-inspired voice assistant robot. The design focuses on local wake word detection (via OpenWakeWord), ALSA audio filtering (e.g., 100Hz-4000Hz for voice), and relaying audio to a remote server for processing. Components are chosen for compactness, low cost, and flexibility in a 3D-printed enclosed case.

External sources for reference:

- [ai.matejpesl.cz | First conversation about switching to RPI + choosing components and pinout](https://ai.matejpesl.cz/c/d96927eb-7d8b-4a23-b92b-3f87542ca829) (long conversation about why RPI Zero 2W VS ESP32 or alternatives, details and justifications about implementation etc.)
- [hackster.io | Charles Diaz - How To Build TARS Replica](https://www.hackster.io/charlesdiaz/how-to-build-your-own-replica-of-tars-from-interstellar-224833) (he already built the hardware version of it, focusing on 3D printing and servos for movement)
- [docs-tars-ai.vercel.app | Open-Source replicated physical build and software guide](https://docs-tars-ai.vercel.app/build/bom)
- [github.com/TARS-AI-Community](https://github.com/TARS-AI-Community/TARS-AI)

## Why Raspberry Pi Zero 2W?

- **Rationale**: The Pi Zero 2W is chosen over alternatives (e.g., ESP32) for better local wake word detection reliability (via OpenWakeWord) (regular esp32 cannot do local wake word detection at all), flexible component positioning in a TARS enclosure, and easier integration of displays/cameras/servos. It supports simultaneous I2S audio input/output, leaving GPIOs free for expansions like servos for articulating panels.
- **Trade-offs**: Boot time is ~30-40 seconds (vs. instant on ESP32), and power consumption is higher (~100-300mA), but it's efficient for wall-powered or short-battery use. Enclosure considerations (e.g., acoustic holes for mic/speaker) are critical to avoid muffled sound or echo.
- **Efficiency**: Low total cost (~$50-100), compact for 3D-printed TARS case, and scalable (e.g., add second mic later for stereo processing).

## Raspberry Pi Zero 2W Specifications

- **Form Factor:** 65mm × 30mm
- **Processor:** Broadcom BCM2710A1, quad-core 64-bit SoC (Arm Cortex-A53 @ 1GHz)
- **Memory:** 512MB LPDDR2 SDRAM
- **Power:** 5V DC, 2.5A via micro USB
- **Operating Temperature:** -20°C to +70°C

**Connectivity:**

- 2.4GHz IEEE 802.11b/g/n wireless LAN
- Bluetooth 4.2, Bluetooth Low Energy (BLE)
- Onboard antenna
- 1 × USB 2.0 interface with OTG
- HAT-compatible 40-pin GPIO header footprint (unpopulated)
- microSD card slot
- Mini HDMI port
- CSI-2 camera connector

**Video Output:**

- HDMI interface (via mini HDMI port)
- Composite video (via solder test points)

**Multimedia:**

- H.264, MPEG-4 decode (1080p30)
- H.264 encode (1080p30)
- OpenGL ES 1.1, 2.0 graphics

## Components, Wiring

### Pinout Schema

```

INMP441 Microphone #1 (Single/Mono for now):
SCK: GPIO 18 (shared with amplifier's BCLK)
WS: GPIO 19 (shared with amplifier'S LRC)
L/R: ground // Set to low for mono/left channel (or tie to 3.3V if preferred)
GND: ground
VDD: 3.3V
SD: GPIO 20 (PCM_DIN)

MAX98357A I2S Amplifier (for Speaker):
Vin: 5V // Use 5V for better power; 3.3V if low-volume is OK
GND: ground
SD: floating // tie high for always-on(3.3v), or floating (self-managed) for power saving
GAIN: floating // (default 9dB gain) or tie to GND for adjustment
DIN: GPIO 21 (PCM_DOUT, pin 40) // Output data to amp
BCLK: GPIO 18 (PCM_CLK, pin 12, shared with mic's SCK)
LRC: GPIO 19 (PCM_FS, pin 35, shared with mic's WS)
*Note: make sure to scew the screws on the green connector on the amplifier (the + - ones for speaker) so they arent loose.

SPI Display (e.g., 0.96" OLED):
VCC → Pin 17 (3.3V)
GND → Pin 20 (Ground)
SCL → Pin 23 (GPIO 11 - SPI0 SCLK)
SDA → Pin 19 (GPIO 10 - SPI0 MOSI)
RES → Pin 22 (GPIO 25 - Reset) // Or any free GPIO
DC → Pin 18 (GPIO 24 - Data/Command)
CS → Pin 24 (GPIO 8 - SPI0 CE0)

Pi Camera Module:
→ CSI connector (22-pin ribbon cable)

Available GPIOs for future use (e.g., second mic, servos, LEDs):
GPIO 2, 3 (I2C if needed)
GPIO 4, 5, 6, 7, 9, 13, 14, 15, 16, 17, 23, 26, 27 // Plenty free
```

### Components

- **Raspberry Pi Zero 2W (with pre-soldered GPIO headers)**:  
  Core processor for local wake word detection and I/O.  
  **WHY**: Headers allow easy, non-destructive wiring for prototyping  
  and flexible positioning in the TARS enclosure.

- **INMP441 I2S Microphone (single for now)**:  
  Digital mic for high-quality voice input.  
  **WHY**: Compact, low-noise, and ideal for wake word detection;  
  single mic reduces initial complexity while supporting future stereo upgrade.  
  Position behind enclosure holes for acoustics.

- **3W 4Ω Speaker with MAX98357A I2S Digital Amplifier Breakout Board**:  
  Small speaker (e.g., 40-50mm diameter) amplified for TTS playback.  
  **WHY**: Provides clear, amplified audio without buzzing (better than PWM);  
  I2S bus supports simultaneous mic input/output, so no conflicts.  
  Amp is tiny (~20mm x 20mm x 3mm) for enclosure fit.  
  **Alternative**: PWM with analog amp (e.g., PAM8403) avoids I2S  
  but may have lower quality/noise issues.

- **SPI Display (e.g., 0.96" OLED like SSD1306)**:  
  Small screen for TARS panel visuals.  
  **WHY**: Low-power, compact, and easy to position on enclosure walls  
  via flexible wires; SPI interface is efficient and leaves pins free.

- **Pi Camera Module (e.g., official Raspberry Pi Camera v2 or mini version)**:  
  For future multimodal input.  
  **WHY**: Native CSI connection with ribbon cable allows flexible positioning  
  (e.g., in TARS "eye" area); low power and small form factor.

- **MicroSD Card (16GB+ Class 10, e.g., SanDisk)**:  
  For OS storage.  
  **WHY**: Essential for booting Raspberry Pi OS;  
  high-speed card ensures smooth performance.

- **Power Supply**:  
  5V 2.5A microUSB adapter (wall power) + optional 2000mAh LiPo battery  
  with UPS module (e.g., PiSugar).  
  **WHY**: Provides stable power; UPS prevents SD corruption  
  during shutdowns for portable TARS use.

- **Wiring Accessories**:  
  Female-to-female Dupont jumper wires (various lengths),  
  optional breadboard/perfboard for prototyping.  
  **WHY**: Enables flexible component placement in the enclosed case  
  without soldering everything permanently.

**Bill of Materials (BOM) - Shopping List:**  
| Component | Example Part/Source | Approx. Price | WHY/Notes |  
|-----------|---------------------|--------------|-----------|  
| Raspberry Pi Zero 2W (pre-soldered headers) | Official Raspberry Pi resellers (e.g., Pimoroni, Adafruit) | $15-20 | Core board; headers for easy wiring. |  
| INMP441 I2S Microphone (breakout board) | Adafruit #2716 or AliExpress | $5-10 | Single mic for simplicity; add second later if needed. |  
| MAX98357A I2S Amplifier Breakout | Adafruit #3006 or Seeed Studio | $3-5 | Essential for clean audio output. |  
| 3W 4Ω Speaker (40-50mm) | Adafruit #1313 or Amazon/AliExpress | $3-5 | Basic, compact for voice; position with enclosure grille. |  
| SPI Display (0.96" OLED SSD1306) | Adafruit #326 or AliExpress | $5-10 | For TARS panels; flexible wiring. |  
| Pi Camera Module (with ribbon cable) | Official Raspberry Pi Camera Module v2 | $10-15 | Future-proof; extendable cable for positioning. |  
| MicroSD Card (16GB Class 10) | SanDisk or Samsung | $5-10 | OS storage; get pre-imaged if possible. |  
| Power Supply (5V 2.5A microUSB) | Any reliable brand (e.g., official Pi adapter) | $5-10 | Wall power; add battery/UPS for portability (~$10-20 extra). |  
| Jumper Wires (assorted pack) | Amazon/AliExpress | $5 | For flexible connections in enclosure. |  
| **Total Estimated Cost** | | $50-100 | Low-cost build; prices vary by region. |

## Software Configuration

- **OS**: Raspberry Pi OS Lite (headless for efficiency).
- **I2S Enable**: Edit `/boot/config.txt` with `dtparam=i2s=on` and `dtoverlay=i2s-mmap`; reboot.
- **Audio Setup**: Use ALSA for mic filtering (e.g., `.asoundrc` for 100Hz-4000Hz bandpass) and testing (`arecord` for input, `aplay` for output).
- **Wake Word**: Install OpenWakeWord for local detection; integrate with server relay scripts (e.g., Python with PyAudio).
- **Display/Camera**: Use libraries like Luma.OLED for display and Picamera2 for camera.
- **WHY**: Keeps processing light on the Pi, offloading heavy logic to the server while enabling low-latency local features.

## Future Expansions

- Add second mic for stereo (share SD pin on GPIO20).
- Servos for TARS panels (e.g., on GPIO13/16 for PWM).
- Echo cancellation (software via WebRTC or hardware WM8960 codec).
- Status LED (e.g., on GPIO4) for debugging.
