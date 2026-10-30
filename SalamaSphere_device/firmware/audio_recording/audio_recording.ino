#include "audio_recorder.h"

// The production entry point is firmware/ble_communication/ble_communication.ino.
// This file is a recorder-only smoke-test sketch.
AudioRecorder recorder;
void setup() { Serial.begin(115200); recorder.begin(); }
void loop() {}
