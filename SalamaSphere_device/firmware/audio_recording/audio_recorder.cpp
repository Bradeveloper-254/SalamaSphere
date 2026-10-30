#include "audio_recorder.h"
#include <LittleFS.h>
#include <driver/i2s.h>
#include "config.h"

namespace {
void writeLe16(File& file, uint16_t value) {
  uint8_t bytes[2] = {(uint8_t)(value & 0xff), (uint8_t)(value >> 8)};
  file.write(bytes, sizeof(bytes));
}
void writeLe32(File& file, uint32_t value) {
  uint8_t bytes[4] = {(uint8_t)value, (uint8_t)(value >> 8),
                      (uint8_t)(value >> 16), (uint8_t)(value >> 24)};
  file.write(bytes, sizeof(bytes));
}
void writeWavHeader(File& file, uint32_t dataSize) {
  file.seek(0);
  file.write((const uint8_t*)"RIFF", 4); writeLe32(file, 36 + dataSize);
  file.write((const uint8_t*)"WAVEfmt ", 8); writeLe32(file, 16);
  writeLe16(file, 1); writeLe16(file, AUDIO_CHANNELS);
  writeLe32(file, AUDIO_SAMPLE_RATE);
  writeLe32(file, AUDIO_SAMPLE_RATE * AUDIO_CHANNELS * AUDIO_BITS_PER_SAMPLE / 8);
  writeLe16(file, AUDIO_CHANNELS * AUDIO_BITS_PER_SAMPLE / 8);
  writeLe16(file, AUDIO_BITS_PER_SAMPLE);
  file.write((const uint8_t*)"data", 4); writeLe32(file, dataSize);
}
}

bool AudioRecorder::begin() {
  i2s_config_t config = {};
  config.mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX);
  config.sample_rate = AUDIO_SAMPLE_RATE;
  config.bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT;
  config.channel_format = I2S_CHANNEL_FMT_ONLY_LEFT;
  config.communication_format = I2S_COMM_FORMAT_I2S;
  config.intr_alloc_flags = ESP_INTR_FLAG_LEVEL1;
  config.dma_buf_count = 8;
  config.dma_buf_len = 256;
  config.use_apll = false;
  config.tx_desc_auto_clear = false;
  config.fixed_mclk = 0;
  i2s_pin_config_t pins = {};
  pins.bck_io_num = I2S_BCLK_PIN; pins.ws_io_num = I2S_LRCLK_PIN;
  pins.data_out_num = I2S_PIN_NO_CHANGE; pins.data_in_num = I2S_DATA_PIN;
  if (i2s_driver_install(I2S_PORT, &config, 0, nullptr) != ESP_OK) return false;
  return i2s_set_pin(I2S_PORT, &pins) == ESP_OK;
}

bool AudioRecorder::record(const char* path, uint32_t seconds) {
  File file = LittleFS.open(path, "w");
  if (!file) return false;
  uint8_t header[44] = {};
  file.write(header, sizeof(header));
  uint32_t total = 0;
  const uint32_t target = AUDIO_SAMPLE_RATE * seconds;
  int32_t samples[256];
  while (total < target) {
    size_t bytesRead = 0;
    const esp_err_t status = i2s_read(I2S_PORT, samples, sizeof(samples), &bytesRead, pdMS_TO_TICKS(100));
    if (status != ESP_OK) {
      file.close();
      return false;
    }
    if (bytesRead == 0) {
      continue;
    }

    const size_t samplesRead = min(bytesRead / sizeof(int32_t), (size_t)(target - total));
    for (size_t i = 0; i < samplesRead; ++i) {
      const int16_t sample = static_cast<int16_t>(samples[i] >> 14);
      file.write(reinterpret_cast<const uint8_t*>(&sample), sizeof(sample));
    }
    total += samplesRead;
  }
  writeWavHeader(file, total * sizeof(int16_t));
  file.close();
  return true;
}
