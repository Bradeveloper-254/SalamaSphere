# SalamaSphere wearable firmware

Open `ble_communication.ino` in Arduino IDE and select the ESP32-S3 board.
Install the ESP32 board package and NimBLE-Arduino 2.5.1. The sketch uses
microSD (SPI) for WAV storage, NimBLE for BLE, and the built-in I2S driver.

Before uploading, verify `ble_config.h` and the pin assignments against the
actual board, microphone, SOS button, and microSD wiring.

The sketch records a 10-second, 16 kHz mono WAV file to the SD card. It
advertises SOS events and keeps recordings for later transfer if the phone is
disconnected. Subscribe to `AUDIO_DATA_UUID` before sending `GET:<event_id>` or
`RESUME:<event_id>:<byteOffset>` to `AUDIO_CONTROL_UUID`. Send cumulative
`ACK:<sequence>` writes to `TRANSFER_ACK_UUID`.

The SOS event JSON includes `call_requested: true`. This is a request for the
paired phone application to initiate its configured call flow; the ESP32
firmware has no cellular/telephony capability and cannot place calls itself.

The default pin assignments are placeholders until verified against the
production hardware.
