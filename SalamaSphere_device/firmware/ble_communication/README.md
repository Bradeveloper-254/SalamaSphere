# SalamaSphere wearable firmware

Open `ble_communication.ino` in Arduino IDE and select the ESP32-S3 board.
Install the ESP32 board package. The sketch uses the ESP32 Arduino BLE stack,
LittleFS, and the built-in I2S driver; no third-party library is required.

Before uploading, edit `ble_config.h`:

- `I2S_BCLK_PIN`, `I2S_LRCLK_PIN`, and `I2S_DATA_PIN` must match the microphone.
- `SOS_BUTTON_PIN` must match the physical SOS button.
- `SOS_BUTTON_ACTIVE_LOW` must match the button wiring.

The sketch records a 10-second, 16 kHz mono WAV file in LittleFS, advertises
the SOS event, waits for the app's `GET:<event_id>` command, then sends the WAV
file in 180-byte notifications over the audio-data characteristic.

The pin defaults are placeholders because the hardware inventory does not yet
specify the board or microphone wiring. Verify the wiring before deployment.
