import serial
import pyaudio
import time

# --- Configuration ---
SERIAL_PORT = 'COM6'  # IMPORTANT: Change this to your ESP32's serial port
BAUD_RATE = 921600 # Increased to handle high-speed audio data
SAMPLE_RATE = 16000
CHUNK_SIZE = 1024  # Number of frames per buffer

# PyAudio parameters
FORMAT = pyaudio.paInt16  # 16-bit audio
CHANNELS = 1  # Mono

def stream_from_esp32():
    """
    Connects to the ESP32, triggers a live audio stream,
    and plays it in real-time through the computer's speakers.
    """
    print("--- Starting Live Audio Stream ---")
    
    # --- 1. Initialize PyAudio ---
    p = pyaudio.PyAudio()
    try:
        stream = p.open(format=FORMAT,
                        channels=CHANNELS,
                        rate=SAMPLE_RATE,
                        output=True,
                        frames_per_buffer=CHUNK_SIZE)
        print("PyAudio stream opened successfully.")
    except Exception as e:
        print(f"Error opening PyAudio stream: {e}")
        p.terminate()
        return

    # --- 2. Connect to Serial Port ---
    print(f"Attempting to connect to serial port {SERIAL_PORT}...")
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        time.sleep(2)
        print("Connection successful.")
    except serial.SerialException as e:
        print(f"Error opening serial port: {e}")
        stream.stop_stream()
        stream.close()
        p.terminate()
        return

    # --- 3. Start the Stream on ESP32 ---
    ser.reset_input_buffer()
    print("Sending 'l' to start live stream...")
    ser.write(b'l')

    # Wait for confirmation
    while True:
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        if "Starting live audio stream" in line:
            print("ESP32 has started streaming.")
            break
        elif line:
            print(f"ESP32 says: {line}")

    # --- 4. Main Loop: Read from Serial and Write to Audio Stream ---
    print("\n--- Streaming audio... Press Ctrl+C to stop. ---")
    try:
        while True:
            # Read a chunk of audio data from the serial port
            audio_data = ser.read(CHUNK_SIZE)
            # Write the data to the audio stream to play it
            stream.write(audio_data)
    except KeyboardInterrupt:
        print("\n--- Stopping stream ---")
    finally:
        # --- 5. Cleanup ---
        stream.stop_stream()
        stream.close()
        p.terminate()
        ser.close()
        print("Audio stream and serial port closed.")

if __name__ == '__main__':
    stream_from_esp32()