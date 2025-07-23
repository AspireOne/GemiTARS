## Cli Commands

1. Build the Firmware
This command compiles your code and all the necessary libraries, creating a firmware binary file in the project's .pio/build/esp32dev/ directory.

`pio run -e esp32dev`


2. Upload the Firmware
This command uploads the compiled firmware to your ESP32. Make sure your device is connected to the computer and that the upload_port in your platformio.ini (COM6) is correct.

`pio run -t upload -e esp32dev`


3. Monitor the Serial Output
This command opens the serial monitor so you can see the output from your ESP32 (e.g., the Serial.println() statements).

`pio device monitor`


All-in-One: Upload and Monitor
For convenience, you can combine the upload and monitor steps into a single command. This will upload the firmware and then immediately start monitoring the serial output. This is the most common command you'll use during development.

`pio run -t upload -t monitor -e esp32dev`