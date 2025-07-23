#include <Arduino.h>
#include "driver/i2s.h"

// 1. PIN CONFIGURATION
#define I2S_WS 25
#define I2S_SD 33
#define I2S_SCK 32
#define I2S_PORT I2S_NUM_0

// 2. I2S CONFIGURATION
#define I2S_SAMPLE_RATE 16000
#define I2S_BITS_PER_SAMPLE I2S_BITS_PER_SAMPLE_16BIT // Using 16-bit for WAV file compatibility
#define I2S_CHANNEL_FORMAT I2S_CHANNEL_FMT_ONLY_LEFT // For mono INMP441 with L/R pin connected to GND

// 3. Recording Configuration
#define RECORD_DURATION_SECONDS 5
const int RECORD_BUFFER_SIZE = I2S_SAMPLE_RATE * RECORD_DURATION_SECONDS * sizeof(int16_t);

// 4. I2S Buffer
#define I2S_BUFFER_SIZE 1024
int16_t i2s_buffer[I2S_BUFFER_SIZE];

void setup() {
  Serial.begin(921600); // Increased baud rate for high-speed data transfer
  Serial.println("--- INMP441 Audio Recorder ---");
  Serial.println("Send 'r' to start a 5-second recording.");

  i2s_config_t i2s_config = {
      .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
      .sample_rate = I2S_SAMPLE_RATE,
      .bits_per_sample = I2S_BITS_PER_SAMPLE,
      .channel_format = I2S_CHANNEL_FORMAT,
      .communication_format = I2S_COMM_FORMAT_STAND_I2S, // Standard I2S for 16-bit
      .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
      .dma_buf_count = 8,
      .dma_buf_len = 64,
      .use_apll = false,
      .tx_desc_auto_clear = false,
      .fixed_mclk = 0
  };

  i2s_pin_config_t pin_config = {
      .bck_io_num = I2S_SCK,
      .ws_io_num = I2S_WS,
      .data_out_num = I2S_PIN_NO_CHANGE,
      .data_in_num = I2S_SD
  };

  esp_err_t err = i2s_driver_install(I2S_PORT, &i2s_config, 0, NULL);
  if (err != ESP_OK) {
    Serial.printf("Failed to install driver: %d\n", err);
    while (true);
  }
  
  err = i2s_set_pin(I2S_PORT, &pin_config);
  if (err != ESP_OK) {
    Serial.printf("Failed to set pin: %d\n", err);
    while (true);
  }

  i2s_zero_dma_buffer(I2S_PORT);
  Serial.println("I2S driver installed. Ready to record.");
}

void record_audio() {
  Serial.println("Recording...");

  int total_bytes_read = 0;
  size_t bytes_read_in_chunk = 0;

  while (total_bytes_read < RECORD_BUFFER_SIZE) {
    esp_err_t result = i2s_read(I2S_PORT, &i2s_buffer, sizeof(i2s_buffer), &bytes_read_in_chunk, portMAX_DELAY);

    if (result == ESP_OK && bytes_read_in_chunk > 0) {
      // Write the raw audio data directly to the serial port
      Serial.write((const uint8_t*)i2s_buffer, bytes_read_in_chunk);
      total_bytes_read += bytes_read_in_chunk;
    }
  }
  
  Serial.println("Recording finished.");
}

void print_samples_continuously() {
  Serial.println("Starting continuous sample printing. Send any character to stop.");
  
  // Clear the serial buffer before starting
  while(Serial.available()) Serial.read();

  while (Serial.available() == 0) {
    size_t bytes_read = 0;
    esp_err_t result = i2s_read(I2S_PORT, &i2s_buffer, sizeof(i2s_buffer), &bytes_read, portMAX_DELAY);

    if (result == ESP_OK && bytes_read > 0) {
      int samples_read = bytes_read / sizeof(int16_t);
      for (int i = 0; i < samples_read; i++) {
        Serial.println(i2s_buffer[i]);
      }
    }
  }
  // Clear the buffer again after stopping
  while(Serial.available()) Serial.read();
  Serial.println("Stopped continuous printing.");
  Serial.println("Send 'r' to record or 'd' to print samples.");
}


void stream_audio_continuously() {
  Serial.println("Starting live audio stream. Stop the Python script to exit.");
  
  // Clear the serial buffer before starting
  while(Serial.available()) Serial.read();

  while (Serial.available() == 0) {
    size_t bytes_read = 0;
    esp_err_t result = i2s_read(I2S_PORT, &i2s_buffer, sizeof(i2s_buffer), &bytes_read, portMAX_DELAY);

    if (result == ESP_OK && bytes_read > 0) {
      // Write the raw audio data directly to the serial port
      Serial.write((const uint8_t*)i2s_buffer, bytes_read);
    }
  }
  // Clear the buffer again after stopping
  while(Serial.available()) Serial.read();
  Serial.println("Stopped live audio stream.");
  Serial.println("Send 'r' to record, 'd' to print samples, or 'l' to stream.");
}

void loop() {
  // Check if there's a command from the serial port
  if (Serial.available() > 0) {
    char cmd = Serial.read();
    if (cmd == 'r') {
      record_audio();
    } else if (cmd == 'd') {
      print_samples_continuously();
    } else if (cmd == 'l') {
      stream_audio_continuously();
    }
  }
}
