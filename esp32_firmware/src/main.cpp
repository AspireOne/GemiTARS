#include <Arduino.h>
#include "driver/i2s.h"

// 1. PIN CONFIGURATION
#define I2S_WS 25
#define I2S_SD 33
#define I2S_SCK 32
#define I2S_PORT I2S_NUM_0

// 2. I2S CONFIGURATION
#define I2S_SAMPLE_RATE 16000
#define I2S_BITS_PER_SAMPLE I2S_BITS_PER_SAMPLE_32BIT
#define I2S_CHANNEL_FORMAT I2S_CHANNEL_FMT_ONLY_LEFT // For mono INMP441 with L/R pin connected to GND

// 3. Buffer
#define I2S_BUFFER_SIZE 1024
int32_t i2s_buffer[I2S_BUFFER_SIZE];

void setup() {
  Serial.begin(115200);
  Serial.println("--- Final INMP441 Test Firmware ---");

  i2s_config_t i2s_config = {
      .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
      .sample_rate = I2S_SAMPLE_RATE,
      .bits_per_sample = I2S_BITS_PER_SAMPLE,
      .channel_format = I2S_CHANNEL_FORMAT,
      .communication_format = I2S_COMM_FORMAT_STAND_MSB, // For Left-Justified data
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
  Serial.println("I2S driver installed and buffer cleared. Starting read loop.");
}

void loop() {
  size_t bytes_read = 0;
  esp_err_t result = i2s_read(I2S_PORT, &i2s_buffer, sizeof(i2s_buffer), &bytes_read, portMAX_DELAY);

  if (result == ESP_OK && bytes_read > 0) {
    int samples_read = bytes_read / sizeof(int32_t);
    for (int i = 0; i < samples_read; i++) {
      // Right-shift the 32-bit sample to get the 24-bit value
      int32_t sample = i2s_buffer[i] >> 8;
      Serial.println(sample);
    }
  }
}
