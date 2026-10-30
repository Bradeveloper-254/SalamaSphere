#ifndef BLE_CONFIG_H
#define BLE_CONFIG_H

// This protocol is shared with lib/services/ble_service.dart.
#define SALAMA_SERVICE_UUID "7b6a0001-7d42-4a8e-9b31-2f4c8a6e1000"
#define DEVICE_ID_UUID "7b6a0002-7d42-4a8e-9b31-2f4c8a6e1000"
#define SOS_EVENT_UUID "7b6a0003-7d42-4a8e-9b31-2f4c8a6e1000"
#define RECORDING_STATUS_UUID "7b6a0004-7d42-4a8e-9b31-2f4c8a6e1000"
#define AUDIO_METADATA_UUID "7b6a0005-7d42-4a8e-9b31-2f4c8a6e1000"
#define AUDIO_CONTROL_UUID "7b6a0006-7d42-4a8e-9b31-2f4c8a6e1000"
#define AUDIO_DATA_UUID "7b6a0007-7d42-4a8e-9b31-2f4c8a6e1000"
#define TRANSFER_ACK_UUID "7b6a0008-7d42-4a8e-9b31-2f4c8a6e1000"
#define BATTERY_STATUS_UUID "7b6a0009-7d42-4a8e-9b31-2f4c8a6e1000"

#define DEVICE_NAME "SalamaSphere"
#define DEVICE_ID "SALAMA-DEVICE-001"

// Change these four values to match the actual ESP32-S3 wiring.
#define I2S_PORT I2S_NUM_0

// Match the wiring that passed the earlier hardware tests.
#define I2S_BCLK_PIN 15
#define I2S_LRCLK_PIN 16
#define I2S_DATA_PIN 17

#define SOS_BUTTON_PIN 4
#define SOS_BUTTON_ACTIVE_LOW 1

#define AUDIO_SAMPLE_RATE 16000
#define AUDIO_RECORD_SECONDS 10
#define AUDIO_CHANNELS 1
#define AUDIO_BITS_PER_SAMPLE 16
#define AUDIO_FILE_PATH "/sos_latest.wav"
#define AUDIO_MIME_TYPE "audio/wav"
#define AUDIO_CHUNK_SIZE 180

#endif

