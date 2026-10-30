#include <Arduino.h>
#include <SPI.h>
#include <SD.h>
#include <driver/i2s.h>
#include <esp_system.h>
#include <NimBLEDevice.h>

// ============================================================
// SALAMASPHERE - DAY 9 (v1.3.0)
// SOS + AUDIO RECORDING + RELIABLE BLE FILE TRANSFER
// WITH RESUME, RECONNECTION AND HARDWARE RECOVERY
// Board: ESP32-S3 N16R8
// Library: NimBLE-Arduino 2.5.1
// ============================================================
//
// PROTOCOL SUMMARY (all commands are written to TRANSFER_ACK_UUID)
//
//   Phone -> Device (write):
//     GET:<event_id>                  full file from byte 0
//     RESUME:<event_id>:<byteOffset>  continue after a dropped link
//     ACK:<seq>                       cumulative: chunks 0..seq received
//     ABORT                           stop the current transfer
//     STATUS                          report recording status
//     LIST                            list WAV files stored on the SD card
//     DELETE:<event_id>               delete a file (after you verified it)
//
//   Device -> Phone (notify on FILE_TRANSFER_UUID):
//     START:<id>:<fileSize>:<totalChunks>:<chunkSize>:<startOffset>:<crc32hex>
//     <binary chunk>  = 4-byte seq (LE) + 2-byte len (LE) + payload
//     COMPLETE:<id>:<fileSize>:<totalChunks>:<crc32hex>
//     ERROR:<reason>[:<resumeOffset>]
//     FILE:<id>:<size> ... LIST_END:<count>
//     STATUS:<state>   DELETED:<id>
//
//   Sequence numbers restart at 0 for every START (including RESUME).
//   The byte position of chunk N = startOffset + N * chunkSize.
//   The CRC32 is of the WHOLE file (standard zlib CRC32).
//
//   REQUIREMENTS ON THE PHONE
//     1. Request MTU 247 right after connecting (control messages
//        are longer than the 20 bytes a default MTU of 23 allows).
//     2. Enable notifications on FILE_TRANSFER_UUID first.
//     3. ACK in order. If a chunk arrives out of order or duplicated,
//        drop it and re-send ACK for the last in-order sequence.
// ============================================================

// ---------------- HARDWARE PINS -----------------------------

#define SOS_BUTTON_PIN 4

#define GREEN_LED_PIN 5
#define RED_LED_PIN   6

#define I2S_BCLK 15
#define I2S_WS   16
#define I2S_DIN  17

#define SD_CS    10
#define SD_MOSI  11
#define SD_SCLK  12
#define SD_MISO  13

// ---------------- DEVICE CONFIGURATION ----------------------

#define DEVICE_NAME      "SalamaSphere"
#define DEVICE_ID        "SALAMA-DEVICE-001"
#define FIRMWARE_VERSION "1.3.0"

// ---------------- AUDIO CONFIGURATION -----------------------

#define SAMPLE_RATE               16000
#define RECORD_SECONDS            10
#define BITS_PER_SAMPLE           16
#define AUDIO_CHANNELS            1
#define AUDIO_SAMPLES_PER_BUFFER  256

// ---------------- BUTTON CONFIGURATION ----------------------

const unsigned long LONG_PRESS_MS = 1500;
const unsigned long DEBOUNCE_MS = 40;

// ---------------- TRANSFER CONFIGURATION --------------------

#define PACKET_HEADER_SIZE    6
#define MAX_CHUNK_PAYLOAD     238   // fits MTU 247 (247 - 3 - 6 = 238)
#define PREFERRED_MTU         247
#define MIN_MTU_FOR_TRANSFER  100   // control messages need > 20 bytes

#define WINDOW_SIZE           6     // chunks in flight before an ACK is needed

const unsigned long ACK_TIMEOUT_MS = 2000;
const int MAX_STALLS = 5;           // consecutive timeouts before giving up

#define MAX_LIST_ENTRIES      50

// ---------------- TYPES (must be defined before any function) --

enum ChunkResult {
  CHUNK_SENT,
  CHUNK_BUSY,    // BLE stack had no buffer; retry later
  CHUNK_FATAL    // SD read problem
};

// ---------------- COMMAND QUEUE -----------------------------

#define CMD_QUEUE_SIZE 4
#define CMD_MAX_LEN    96

// ---------------- BLE UUIDS ----------------------------------

#define SERVICE_UUID \
  "7b6a0001-7d42-4a8e-9b31-2f4c8a6e1000"

#define DEVICE_ID_UUID \
  "7b6a0002-7d42-4a8e-9b31-2f4c8a6e1000"

#define SOS_EVENT_UUID \
  "7b6a0003-7d42-4a8e-9b31-2f4c8a6e1000"

#define RECORDING_STATUS_UUID \
  "7b6a0004-7d42-4a8e-9b31-2f4c8a6e1000"

#define AUDIO_METADATA_UUID \
  "7b6a0005-7d42-4a8e-9b31-2f4c8a6e1000"

// Phone writes GET, RESUME and ACK commands here.
#define TRANSFER_ACK_UUID \
  "7b6a0006-7d42-4a8e-9b31-2f4c8a6e1000"

// Device sends START, binary chunks and COMPLETE here.
#define FILE_TRANSFER_UUID \
  "7b6a0007-7d42-4a8e-9b31-2f4c8a6e1000"

#define BATTERY_UUID \
  "7b6a0008-7d42-4a8e-9b31-2f4c8a6e1000"
// ---------------- BATTERY CONFIGURATION ---------------------
// BATTERY_ADC_PIN: GPIO wired to the middle of a 2:1 resistor divider
// from the battery (+). Set to -1 if no divider is fitted; the app
// then receives battery_percent = -1 ("unknown").
#define BATTERY_ADC_PIN     -1
#define BATTERY_DIVIDER     2.0f
#define BATTERY_EMPTY_MV    3300
#define BATTERY_FULL_MV     4200
#define BATTERY_UPDATE_MS   60000UL

// ============================================================
// HARDWARE OBJECTS
// ============================================================

SPIClass sdSPI(FSPI);

int32_t i2sSamples[AUDIO_SAMPLES_PER_BUFFER];

// ============================================================
// BLE OBJECTS
// ============================================================

NimBLEServer* bleServer = nullptr;
NimBLEService* salamaService = nullptr;

NimBLECharacteristic* deviceIdCharacteristic = nullptr;
NimBLECharacteristic* sosEventCharacteristic = nullptr;
NimBLECharacteristic* recordingStatusCharacteristic = nullptr;
NimBLECharacteristic* audioMetadataCharacteristic = nullptr;
NimBLECharacteristic* fileTransferCharacteristic = nullptr;
NimBLECharacteristic* transferAckCharacteristic = nullptr;
NimBLECharacteristic* batteryCharacteristic = nullptr;

// ============================================================
// STATE VARIABLES
// ============================================================

volatile bool deviceConnected = false;
volatile bool transferSubscribed = false;
volatile uint16_t currentMtu = 23;
volatile bool syncRequested = false;   // phone just (re)subscribed: push pending file list

bool microphoneReady = false;
bool sdReady = false;
bool sdInitAttempted = false;
bool micDriverInstalled = false;

int lastRawButtonState = HIGH;
int stableButtonState = HIGH;

unsigned long lastDebounceTime = 0;
unsigned long pressStartTime = 0;

bool activationHandled = false;

// An SOS long-press detected while a transfer was running.
bool sosPending = false;
unsigned long sosPendingHold = 0;

uint32_t eventCounter = 0;

String currentEventId = "";
String currentFilename = "";

String recordingStatus = "INITIALIZING";

// Transfer state shared with the BLE callback task
volatile bool transferActive = false;
volatile bool abortRequested = false;
volatile int32_t highestAck = -1;
volatile uint32_t transferSentLimit = 0;

// Command queue (written by BLE task, read by loop())
char cmdQueue[CMD_QUEUE_SIZE][CMD_MAX_LEN];
volatile uint8_t cmdHead = 0;
volatile uint8_t cmdTail = 0;
portMUX_TYPE cmdMux = portMUX_INITIALIZER_UNLOCKED;

// ============================================================
// FUNCTION DECLARATIONS
// ============================================================

String generateEventId();
bool isValidEventId(const String& id);

void updateRecordingStatus(const char* status);
bool publishTransferMessage(const String& message);
void publishAudioMetadata(const String& eventId, const String& filename, uint32_t fileSize);

bool initializeMicrophone();
bool initializeSD();
bool ensureHardwareReady();
void updateReadyLeds();

void writeWavHeader(File& file, uint32_t sampleRate, uint16_t bitsPerSample,
                    uint16_t channels, uint32_t dataSize);

bool recordAudio(const String& eventId);
void generateSosEvent(unsigned long holdDuration);

uint32_t computeFileCrc32(File& file);
void transferAudioFile(const String& eventId, uint32_t startOffset);
void listRecordings();
void deleteRecording(const String& eventId);

bool pollSosButton(unsigned long& holdDuration);
void processPendingCommand();
void maintainBle();
void updateBattery(bool force);

// ============================================================
// COMMAND QUEUE HELPERS
// ============================================================

bool enqueueCommand(const char* text) {

  bool ok = false;

  portENTER_CRITICAL(&cmdMux);

  uint8_t next = (cmdHead + 1) % CMD_QUEUE_SIZE;

  if (next != cmdTail) {
    strlcpy(cmdQueue[cmdHead], text, CMD_MAX_LEN);
    cmdHead = next;
    ok = true;
  }

  portEXIT_CRITICAL(&cmdMux);

  return ok;
}

bool dequeueCommand(char* out) {

  bool ok = false;

  portENTER_CRITICAL(&cmdMux);

  if (cmdTail != cmdHead) {
    strlcpy(out, cmdQueue[cmdTail], CMD_MAX_LEN);
    cmdTail = (cmdTail + 1) % CMD_QUEUE_SIZE;
    ok = true;
  }

  portEXIT_CRITICAL(&cmdMux);

  return ok;
}

void clearCommandQueue() {

  portENTER_CRITICAL(&cmdMux);
  cmdTail = cmdHead;
  portEXIT_CRITICAL(&cmdMux);
}

// ============================================================
// BLE SERVER CALLBACKS
// ============================================================

class SalamaServerCallbacks : public NimBLEServerCallbacks {

  void onConnect(NimBLEServer* server, NimBLEConnInfo& connInfo) override {

    deviceConnected = true;
    transferSubscribed = false;
    currentMtu = 23;           // updated by onMTUChange
    syncRequested = false;
    abortRequested = false;
    highestAck = -1;

    clearCommandQueue();

    // Ask for a fast, but not too aggressive, connection:
    // 15-30 ms interval, no latency, 4 s supervision timeout.
    server->updateConnParams(connInfo.getConnHandle(), 12, 24, 0, 400);

    Serial.println();
    Serial.println("BLE CLIENT CONNECTED");
  }

  void onMTUChange(uint16_t MTU, NimBLEConnInfo& connInfo) override {

    currentMtu = MTU;

    Serial.printf("MTU negotiated: %u\n", (unsigned int)MTU);
  }

  void onDisconnect(NimBLEServer* server, NimBLEConnInfo& connInfo, int reason) override {

    deviceConnected = false;
    transferSubscribed = false;
    currentMtu = 23;

    // Any running transfer notices deviceConnected == false and stops.
    // The WAV file stays on the SD card for RESUME / GET after reconnect.
    clearCommandQueue();

    Serial.println();
    Serial.printf("BLE CLIENT DISCONNECTED (reason %d)\n", reason);

    NimBLEDevice::startAdvertising();
  }
};

// ============================================================
// FILE TRANSFER CHARACTERISTIC CALLBACKS (subscription tracking)
// ============================================================

class TransferStreamCallbacks : public NimBLECharacteristicCallbacks {

  void onSubscribe(NimBLECharacteristic* characteristic, NimBLEConnInfo& connInfo,
                   uint16_t subValue) override {

    transferSubscribed = (subValue & 0x01) != 0;
    syncRequested = transferSubscribed;   // loop() will list pending recordings

    Serial.printf("FILE_TRANSFER notifications %s\n",
                  transferSubscribed ? "ENABLED" : "DISABLED");
  }
};

// ============================================================
// COMMAND AND ACK CALLBACK
// ============================================================

class TransferCommandCallbacks : public NimBLECharacteristicCallbacks {

  void onWrite(NimBLECharacteristic* characteristic, NimBLEConnInfo& connInfo) override {

    std::string value = characteristic->getValue();

    if (value.empty()) {
      return;
    }

    char text[CMD_MAX_LEN];

    size_t n = value.size();

    if (n > sizeof(text) - 1) {
      n = sizeof(text) - 1;
    }

    memcpy(text, value.data(), n);
    text[n] = '\0';

    String command = String(text);
    command.trim();

    // ----------------------------------------
    // Cumulative acknowledgement (hot path: no logging)
    // ----------------------------------------

    if (command.startsWith("ACK:")) {

      String sequenceText = command.substring(4);

      if (sequenceText.length() == 0 || sequenceText.length() > 9) {
        return;
      }

      for (size_t i = 0; i < sequenceText.length(); i++) {
        if (!isDigit(sequenceText.charAt(i))) {
          return;
        }
      }

      uint32_t sequence = (uint32_t)strtoul(sequenceText.c_str(), nullptr, 10);

      // Accept only sequences that have actually been sent
      // and that move the acknowledged point forward.
      if (
        transferActive &&
        sequence < transferSentLimit &&
        (int32_t)sequence > highestAck
      ) {
        highestAck = (int32_t)sequence;
      }

      return;
    }

    if (command == "ABORT") {

      if (transferActive) {
        abortRequested = true;
      }

      return;
    }

    Serial.print("BLE command received: ");
    Serial.println(command);

    if (!enqueueCommand(command.c_str())) {
      Serial.println("Command queue full; command dropped.");
    }
  }
};

// ============================================================
// EVENT ID GENERATION / VALIDATION
// ============================================================

String generateEventId() {

  eventCounter++;

  uint32_t randomPart = esp_random();

  char id[48];

  snprintf(
    id,
    sizeof(id),
    "SALAMA-%08lX-%08lX-%04lX",
    (unsigned long)(ESP.getEfuseMac() & 0xFFFFFFFF),
    (unsigned long)randomPart,
    (unsigned long)(eventCounter & 0xFFFF)
  );

  return String(id);
}

bool isValidEventId(const String& id) {

  if (id.length() == 0 || id.length() > 40) {
    return false;
  }

  if (!id.startsWith("SALAMA-")) {
    return false;
  }

  for (size_t i = 0; i < id.length(); i++) {

    char c = id.charAt(i);

    bool valid =
      (c >= 'A' && c <= 'Z') ||
      (c >= '0' && c <= '9') ||
      c == '-';

    if (!valid) {
      return false;
    }
  }

  return true;
}

// ============================================================
// RECORDING STATUS
// ============================================================

void updateRecordingStatus(const char* status) {

  recordingStatus = status;

  if (recordingStatusCharacteristic != nullptr) {

    recordingStatusCharacteristic->setValue(status);

    if (deviceConnected) {
      recordingStatusCharacteristic->notify();
    }
  }

  Serial.print("Recording status: ");
  Serial.println(status);
}

// ============================================================
// TRANSFER STATUS MESSAGE (with retry if the BLE stack is busy)
// ============================================================

bool publishTransferMessage(const String& message) {

  Serial.print("Transfer message: ");
  Serial.println(message);

  if (fileTransferCharacteristic == nullptr) {
    return false;
  }

  // Always keep the latest message readable, even if notify fails.
  fileTransferCharacteristic->setValue(message.c_str());

  if (!deviceConnected) {
    return false;
  }

  if ((int)message.length() > (int)currentMtu - 3) {
    Serial.println("WARNING: message longer than MTU-3; the phone must request a larger MTU.");
  }

  for (int attempt = 0; attempt < 10; attempt++) {

    if (fileTransferCharacteristic->notify()) {
      return true;
    }

    if (!deviceConnected) {
      return false;
    }

    delay(10);
  }

  return false;
}

// ============================================================
// WAV HEADER
// ============================================================

void writeWavHeader(File& file, uint32_t sampleRate, uint16_t bitsPerSample,
                    uint16_t channels, uint32_t dataSize) {

  uint32_t byteRate = sampleRate * channels * bitsPerSample / 8;
  uint16_t blockAlign = channels * bitsPerSample / 8;

  uint32_t chunkSize = 36 + dataSize;
  uint32_t subchunk1Size = 16;

  uint16_t audioFormat = 1;

  file.write((const uint8_t*)"RIFF", 4);
  file.write((uint8_t*)&chunkSize, 4);

  file.write((const uint8_t*)"WAVE", 4);
  file.write((const uint8_t*)"fmt ", 4);

  file.write((uint8_t*)&subchunk1Size, 4);
  file.write((uint8_t*)&audioFormat, 2);
  file.write((uint8_t*)&channels, 2);

  file.write((uint8_t*)&sampleRate, 4);
  file.write((uint8_t*)&byteRate, 4);

  file.write((uint8_t*)&blockAlign, 2);
  file.write((uint8_t*)&bitsPerSample, 2);

  file.write((const uint8_t*)"data", 4);
  file.write((uint8_t*)&dataSize, 4);
}

// ============================================================
// MICROPHONE INITIALIZATION (safe to call again for recovery)
// ============================================================

bool initializeMicrophone() {

  if (micDriverInstalled) {
    i2s_driver_uninstall(I2S_NUM_0);
    micDriverInstalled = false;
  }

  i2s_config_t i2sConfig = {

    .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),

    .sample_rate = SAMPLE_RATE,

    .bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT,

    .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,

    .communication_format = I2S_COMM_FORMAT_STAND_I2S,

    .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,

    .dma_buf_count = 4,

    .dma_buf_len = AUDIO_SAMPLES_PER_BUFFER,

    .use_apll = false,

    .tx_desc_auto_clear = false,

    .fixed_mclk = 0
  };

  esp_err_t result = i2s_driver_install(I2S_NUM_0, &i2sConfig, 0, nullptr);

  if (result != ESP_OK) {

    Serial.printf("Microphone driver error: %d\n", result);

    return false;
  }

  micDriverInstalled = true;

  i2s_pin_config_t pinConfig = {

    .bck_io_num = I2S_BCLK,

    .ws_io_num = I2S_WS,

    .data_out_num = I2S_PIN_NO_CHANGE,

    .data_in_num = I2S_DIN
  };

  result = i2s_set_pin(I2S_NUM_0, &pinConfig);

  if (result != ESP_OK) {

    i2s_driver_uninstall(I2S_NUM_0);
    micDriverInstalled = false;

    Serial.printf("Microphone pin error: %d\n", result);

    return false;
  }

  i2s_zero_dma_buffer(I2S_NUM_0);

  Serial.println("Microphone initialized.");

  return true;
}

// ============================================================
// MICROSD INITIALIZATION (safe to call again for recovery)
// ============================================================

bool initializeSD() {

  if (sdInitAttempted) {
    SD.end();
    sdSPI.end();
  }

  sdInitAttempted = true;

  sdSPI.begin(SD_SCLK, SD_MISO, SD_MOSI, SD_CS);

  if (!SD.begin(SD_CS, sdSPI, 4000000)) {

    Serial.println("microSD initialization failed.");

    return false;
  }

  if (SD.cardType() == CARD_NONE) {

    Serial.println("No microSD card detected.");

    return false;
  }

  Serial.printf(
    "microSD ready. Capacity: %llu MB\n",
    SD.cardSize() / (1024ULL * 1024ULL)
  );

  return true;
}

// ============================================================
// HARDWARE RECOVERY
// ============================================================

void updateReadyLeds() {

  if (sdReady && microphoneReady) {

    digitalWrite(GREEN_LED_PIN, HIGH);
    digitalWrite(RED_LED_PIN, LOW);

  } else {

    digitalWrite(GREEN_LED_PIN, LOW);
    digitalWrite(RED_LED_PIN, HIGH);
  }
}

bool ensureHardwareReady() {

  if (!sdReady) {
    Serial.println("Recovery: re-initializing microSD...");
    sdReady = initializeSD();
  }

  if (!microphoneReady) {
    Serial.println("Recovery: re-initializing microphone...");
    microphoneReady = initializeMicrophone();
  }

  updateReadyLeds();

  return sdReady && microphoneReady;
}

// ============================================================
// AUDIO METADATA
// ============================================================

void publishAudioMetadata(const String& eventId, const String& filename, uint32_t fileSize) {

  if (audioMetadataCharacteristic == nullptr) {
    return;
  }

  String metadata =
    String("{\"event_id\":\"") + eventId +
    "\",\"filename\":\"" + filename +
    "\",\"format\":\"WAV\"" +
    ",\"sample_rate\":16000" +
    ",\"channels\":1" +
    ",\"bits_per_sample\":16" +
    ",\"file_size\":" + String(fileSize) +
    ",\"transfer_status\":\"PENDING\"}";

  // The value stays stored, so a phone that connects LATER can still READ it.
  audioMetadataCharacteristic->setValue(metadata.c_str());

  if (deviceConnected) {
    audioMetadataCharacteristic->notify();
  }

  Serial.println("Audio metadata:");
  Serial.println(metadata);
}

// ============================================================
// AUDIO RECORDING
// ============================================================

bool recordAudio(const String& eventId) {

  if (!ensureHardwareReady()) {

    Serial.println("Recording unavailable: hardware not ready.");

    updateRecordingStatus("ERROR");

    return false;
  }

  String filename = "/" + eventId + ".wav";

  uint32_t expectedDataSize =
    SAMPLE_RATE * AUDIO_CHANNELS * (BITS_PER_SAMPLE / 8) * RECORD_SECONDS;

  uint32_t minPartialBytes =
    SAMPLE_RATE * AUDIO_CHANNELS * (BITS_PER_SAMPLE / 8) * 1;   // 1 second

  if (SD.exists(filename.c_str())) {

    Serial.println("File already exists; refusing overwrite.");

    return false;
  }

  File audioFile = SD.open(filename.c_str(), FILE_WRITE);

  if (!audioFile) {

    Serial.println("Could not create WAV file.");

    sdReady = false;   // force re-init on next attempt

    updateRecordingStatus("ERROR");

    return false;
  }

  // Temporary header.
  writeWavHeader(audioFile, SAMPLE_RATE, BITS_PER_SAMPLE, AUDIO_CHANNELS, 0);

  unsigned long startTime = millis();

  uint32_t totalAudioBytes = 0;

  bool recordingOK = true;

  Serial.println("AUDIO RECORDING STARTED");

  while (millis() - startTime < (unsigned long)RECORD_SECONDS * 1000UL) {

    size_t bytesRead = 0;

    esp_err_t result = i2s_read(
      I2S_NUM_0,
      i2sSamples,
      sizeof(i2sSamples),
      &bytesRead,
      pdMS_TO_TICKS(1000)
    );

    if (result != ESP_OK || bytesRead == 0) {

      recordingOK = false;
      microphoneReady = false;   // force re-init on next attempt

      Serial.println("Microphone read failed.");

      break;
    }

    int count = bytesRead / sizeof(int32_t);

    int16_t pcm[AUDIO_SAMPLES_PER_BUFFER];

    for (int i = 0; i < count; i++) {

      int32_t sample = i2sSamples[i] >> 14;

      if (sample > 32767) {
        sample = 32767;
      }

      if (sample < -32768) {
        sample = -32768;
      }

      pcm[i] = (int16_t)sample;
    }

    size_t bytesToWrite = count * sizeof(int16_t);

    size_t bytesWritten = audioFile.write((const uint8_t*)pcm, bytesToWrite);

    if (bytesWritten != bytesToWrite) {

      recordingOK = false;
      sdReady = false;   // force re-init on next attempt

      Serial.println("microSD write failed.");

      break;
    }

    totalAudioBytes += bytesWritten;
  }

  // Rewrite the WAV header with the actual data size.
  audioFile.seek(0);

  writeWavHeader(audioFile, SAMPLE_RATE, BITS_PER_SAMPLE, AUDIO_CHANNELS, totalAudioBytes);

  audioFile.flush();
  audioFile.close();

  uint32_t actualFileSize = 0;

  if (SD.exists(filename.c_str())) {

    File verifyFile = SD.open(filename.c_str(), FILE_READ);

    if (verifyFile) {

      actualFileSize = verifyFile.size();

      verifyFile.close();
    }
  }

  bool sizeConsistent = (actualFileSize == 44 + totalAudioBytes);

  bool complete =
    recordingOK &&
    sizeConsistent &&
    totalAudioBytes >= expectedDataSize * 9 / 10;

  // In an emergency a truncated recording is still valuable.
  bool partial =
    !complete &&
    sizeConsistent &&
    totalAudioBytes >= minPartialBytes;

  if (!complete && !partial) {

    Serial.println("Recording verification failed; removing bad file.");

    if (SD.exists(filename.c_str())) {
      SD.remove(filename.c_str());
    }

    updateRecordingStatus("ERROR");

    return false;
  }

  currentFilename = filename;

  updateRecordingStatus(complete ? "SAVED" : "SAVED_PARTIAL");

  publishAudioMetadata(eventId, filename, actualFileSize);

  Serial.print("Saved file: ");
  Serial.println(filename);

  Serial.printf("File size: %lu bytes\n", (unsigned long)actualFileSize);

  return true;
}

// ============================================================
// SOS ACTIVATION
// ============================================================

void generateSosEvent(unsigned long holdDuration) {

  currentEventId = generateEventId();

  Serial.println();
  Serial.println("==================================");
  Serial.println("SALAMASPHERE SOS ACTIVATED");
  Serial.println("==================================");

  Serial.print("Event ID: ");
  Serial.println(currentEventId);

  Serial.printf("Button hold: %lu ms\n", holdDuration);

  String eventJson =
    String("{\"event_id\":\"") + currentEventId +
    "\",\"device_identifier\":\"" + DEVICE_ID +
    "\",\"event_type\":\"SOS\"" +
    "\",\"recording_status\":\"recording\"}";

  // Stored even when nobody is connected: a phone that reconnects
  // later can READ this characteristic or send LIST.
  if (sosEventCharacteristic != nullptr) {

    sosEventCharacteristic->setValue(eventJson.c_str());

    if (deviceConnected) {
      sosEventCharacteristic->notify();
    }
  }

  updateRecordingStatus("RECORDING");

  digitalWrite(GREEN_LED_PIN, LOW);
  digitalWrite(RED_LED_PIN, HIGH);

  bool saved = recordAudio(currentEventId);

  if (!saved) {

    // One automatic retry after re-initializing the hardware.
    Serial.println("First recording attempt failed; retrying once.");

    updateRecordingStatus("RECORDING");

    saved = recordAudio(currentEventId);
  }

  if (saved) {

    Serial.println("SOS recording saved.");

  } else {

    Serial.println("SOS recording failed.");

    // Try to bring the hardware back so the next SOS works.
    if (ensureHardwareReady()) {
      updateRecordingStatus("READY");
    }
  }

  updateReadyLeds();
}

// ============================================================
// CRC32 (standard zlib polynomial) OF A WHOLE FILE
// ============================================================

uint32_t computeFileCrc32(File& file) {

  uint32_t crc = 0xFFFFFFFFUL;

  uint8_t buffer[512];

  file.seek(0);

  while (true) {

    int n = file.read(buffer, sizeof(buffer));

    if (n <= 0) {
      break;
    }

    for (int i = 0; i < n; i++) {

      crc ^= buffer[i];

      for (int b = 0; b < 8; b++) {
        crc = (crc & 1) ? ((crc >> 1) ^ 0xEDB88320UL) : (crc >> 1);
      }
    }
  }

  return ~crc;
}

// ============================================================
// SEND ONE AUDIO CHUNK
// ============================================================

ChunkResult sendAudioChunk(
  File& file,
  uint32_t startOffset,
  uint32_t fileSize,
  uint32_t chunkSize,
  uint32_t sequence,
  uint8_t* packet
) {

  uint32_t position = startOffset + sequence * chunkSize;

  if (position >= fileSize) {
    return CHUNK_FATAL;
  }

  uint32_t remaining = fileSize - position;
  uint32_t toRead = (remaining < chunkSize) ? remaining : chunkSize;

  if ((uint32_t)file.position() != position) {

    if (!file.seek(position)) {

      Serial.println("Could not seek in audio file.");

      return CHUNK_FATAL;
    }
  }

  int n = file.read(packet + PACKET_HEADER_SIZE, toRead);

  if (n != (int)toRead) {

    Serial.println("Chunk read failed.");

    return CHUNK_FATAL;
  }

  packet[0] = sequence & 0xFF;
  packet[1] = (sequence >> 8) & 0xFF;
  packet[2] = (sequence >> 16) & 0xFF;
  packet[3] = (sequence >> 24) & 0xFF;

  packet[4] = toRead & 0xFF;
  packet[5] = (toRead >> 8) & 0xFF;

  // Publish the new send limit BEFORE notifying so that an
  // immediate ACK from the phone is never rejected.
  if (sequence + 1 > transferSentLimit) {
    transferSentLimit = sequence + 1;
  }

  fileTransferCharacteristic->setValue(packet, PACKET_HEADER_SIZE + toRead);

  if (!fileTransferCharacteristic->notify()) {
    return CHUNK_BUSY;
  }

  return CHUNK_SENT;
}

// ============================================================
// TRANSFER A SAVED WAV FILE (sliding window, resumable)
// ============================================================

void transferAudioFile(const String& eventId, uint32_t startOffset) {

  if (!deviceConnected) {

    Serial.println("Transfer rejected: Android is disconnected.");

    return;
  }

  if (transferActive) {

    Serial.println("Another transfer is active.");

    return;
  }

  if (!isValidEventId(eventId)) {

    publishTransferMessage("ERROR:INVALID_EVENT_ID");

    return;
  }

  if (!transferSubscribed) {

    Serial.println(
      "Transfer rejected: enable notifications on FILE_TRANSFER first."
    );

    fileTransferCharacteristic->setValue("ERROR:NOT_SUBSCRIBED");

    return;
  }

  if (currentMtu < MIN_MTU_FOR_TRANSFER) {

    // Short enough to fit even in a 23-byte MTU.
    publishTransferMessage("ERROR:MTU_TOO_SMALL");

    return;
  }

  if (!sdReady) {
    sdReady = initializeSD();
  }

  if (!sdReady) {

    publishTransferMessage("ERROR:SD_UNAVAILABLE");

    return;
  }

  String filename = "/" + eventId + ".wav";

  if (!SD.exists(filename.c_str())) {

    publishTransferMessage("ERROR:FILE_NOT_FOUND");

    return;
  }

  File file = SD.open(filename.c_str(), FILE_READ);

  if (!file) {

    publishTransferMessage("ERROR:OPEN_FAILED");

    return;
  }

  uint32_t fileSize = file.size();

  if (fileSize < 44) {

    file.close();

    publishTransferMessage("ERROR:INVALID_WAV_SIZE");

    return;
  }

  if (startOffset > fileSize) {

    file.close();

    publishTransferMessage("ERROR:BAD_OFFSET");

    return;
  }

  uint32_t chunkSize = (uint32_t)currentMtu - 3 - PACKET_HEADER_SIZE;

  if (chunkSize > MAX_CHUNK_PAYLOAD) {
    chunkSize = MAX_CHUNK_PAYLOAD;
  }

  uint32_t totalChunks =
    (fileSize - startOffset + chunkSize - 1) / chunkSize;

  uint32_t crc = computeFileCrc32(file);

  if (!file.seek(startOffset)) {

    file.close();

    publishTransferMessage("ERROR:SEEK_FAILED");

    return;
  }

  // ----- reset shared transfer state -----

  abortRequested = false;
  highestAck = -1;
  transferSentLimit = 0;
  transferActive = true;

  char msg[128];

  snprintf(
    msg,
    sizeof(msg),
    "START:%s:%lu:%lu:%lu:%lu:%08lX",
    eventId.c_str(),
    (unsigned long)fileSize,
    (unsigned long)totalChunks,
    (unsigned long)chunkSize,
    (unsigned long)startOffset,
    (unsigned long)crc
  );

  publishTransferMessage(String(msg));

  Serial.println();
  Serial.println("AUDIO TRANSFER STARTED");
  Serial.printf("File size: %lu, offset: %lu, chunk size: %lu, chunks: %lu\n",
                (unsigned long)fileSize,
                (unsigned long)startOffset,
                (unsigned long)chunkSize,
                (unsigned long)totalChunks);

  // Give the phone a moment to process START before data arrives.
  delay(100);

  static uint8_t packet[PACKET_HEADER_SIZE + MAX_CHUNK_PAYLOAD];

  uint32_t base = 0;   // first chunk not yet acknowledged
  uint32_t next = 0;   // next chunk to send

  int stalls = 0;

  unsigned long lastProgress = millis();

  const char* failReason = nullptr;

  while (base < totalChunks) {

    // ----- abort conditions -----

    if (!deviceConnected) {
      failReason = "DISCONNECTED";
      break;
    }

    if (abortRequested) {
      failReason = "ABORTED";
      break;
    }

    // An SOS must never be blocked by a file transfer.
    unsigned long holdMs = 0;

    if (pollSosButton(holdMs)) {

      sosPending = true;
      sosPendingHold = holdMs;

      failReason = "ABORTED_FOR_SOS";
      break;
    }

    // ----- fill the window -----

    bool fatal = false;

    while (next < totalChunks && next < base + WINDOW_SIZE) {

      ChunkResult r = sendAudioChunk(
        file, startOffset, fileSize, chunkSize, next, packet
      );

      if (r == CHUNK_SENT) {
        next++;
        continue;
      }

      if (r == CHUNK_FATAL) {
        fatal = true;
      }

      break;   // BUSY: wait for ACKs / try again next pass
    }

    if (fatal) {
      failReason = "SD_READ_ERROR";
      break;
    }

    // ----- process acknowledgements -----

    int32_t ack = highestAck;

    if (ack >= (int32_t)base) {

      base = (uint32_t)ack + 1;

      if (next < base) {
        next = base;
      }

      stalls = 0;
      lastProgress = millis();

      if (base % 200 == 0) {
        Serial.printf("Progress: %lu / %lu chunks\n",
                      (unsigned long)base, (unsigned long)totalChunks);
      }

      continue;
    }

    // ----- timeout: go back to the oldest unacknowledged chunk -----

    if (millis() - lastProgress > ACK_TIMEOUT_MS) {

      stalls++;

      Serial.printf("ACK timeout at chunk %lu (stall %d of %d)\n",
                    (unsigned long)base, stalls, MAX_STALLS);

      if (stalls >= MAX_STALLS) {
        failReason = "ACK_TIMEOUT";
        break;
      }

      next = base;

      lastProgress = millis();
    }

    delay(2);
  }

  file.close();

  uint32_t resumeOffset = startOffset + base * chunkSize;

  if (resumeOffset > fileSize) {
    resumeOffset = fileSize;
  }

  if (failReason == nullptr) {

    snprintf(
      msg,
      sizeof(msg),
      "COMPLETE:%s:%lu:%lu:%08lX",
      eventId.c_str(),
      (unsigned long)fileSize,
      (unsigned long)totalChunks,
      (unsigned long)crc
    );

    publishTransferMessage(String(msg));

    Serial.println();
    Serial.println("AUDIO TRANSFER COMPLETED");

  } else {

    Serial.println();
    Serial.printf("AUDIO TRANSFER STOPPED: %s (resume offset %lu)\n",
                  failReason, (unsigned long)resumeOffset);

    if (deviceConnected) {

      snprintf(
        msg,
        sizeof(msg),
        "ERROR:TRANSFER_INCOMPLETE:%s:%lu",
        failReason,
        (unsigned long)resumeOffset
      );

      publishTransferMessage(String(msg));
    }
  }

  transferActive = false;
  abortRequested = false;
}

// ============================================================
// LIST AND DELETE RECORDINGS
// ============================================================

void listRecordings() {

  if (!sdReady) {
    sdReady = initializeSD();
  }

  if (!sdReady) {

    publishTransferMessage("ERROR:SD_UNAVAILABLE");

    return;
  }

  File root = SD.open("/");

  if (!root) {

    publishTransferMessage("ERROR:SD_UNAVAILABLE");

    return;
  }

  int count = 0;

  File entry = root.openNextFile();

  while (entry && deviceConnected && count < MAX_LIST_ENTRIES) {

    if (!entry.isDirectory()) {

      String name = String(entry.name());

      if (name.startsWith("/")) {
        name = name.substring(1);
      }

      if (name.startsWith("SALAMA-") && name.endsWith(".wav")) {

        String id = name.substring(0, name.length() - 4);

        publishTransferMessage(
          String("FILE:") + id + ":" + String((unsigned long)entry.size())
        );

        count++;

        delay(40);
      }
    }

    entry.close();

    entry = root.openNextFile();
  }

  if (entry) {
    entry.close();
  }

  root.close();

  publishTransferMessage(String("LIST_END:") + String(count));
}

void deleteRecording(const String& eventId) {

  if (!isValidEventId(eventId)) {

    publishTransferMessage("ERROR:INVALID_EVENT_ID");

    return;
  }

  String filename = "/" + eventId + ".wav";

  if (!SD.exists(filename.c_str())) {

    publishTransferMessage("ERROR:FILE_NOT_FOUND");

    return;
  }

  if (SD.remove(filename.c_str())) {

    publishTransferMessage(String("DELETED:") + eventId);

  } else {

    publishTransferMessage("ERROR:DELETE_FAILED");
  }
}

// ============================================================
// SOS BUTTON (debounced). Returns true once per long press.
// ============================================================

bool pollSosButton(unsigned long& holdDuration) {

  int rawState = digitalRead(SOS_BUTTON_PIN);

  if (rawState != lastRawButtonState) {

    lastDebounceTime = millis();

    lastRawButtonState = rawState;
  }

  if (millis() - lastDebounceTime >= DEBOUNCE_MS) {

    if (rawState != stableButtonState) {

      stableButtonState = rawState;

      if (stableButtonState == LOW) {

        pressStartTime = millis();

        activationHandled = false;

        Serial.println("SOS button pressed.");

      } else {

        Serial.println("SOS button released.");

        if (!activationHandled) {

          Serial.println("Short press rejected. No SOS event generated.");
        }
      }
    }
  }

  if (
    stableButtonState == LOW &&
    !activationHandled &&
    millis() - pressStartTime >= LONG_PRESS_MS
  ) {

    activationHandled = true;

    holdDuration = millis() - pressStartTime;

    return true;
  }

  return false;
}

// ============================================================
// PROCESS ANDROID COMMANDS
// ============================================================

void processPendingCommand() {

  char buffer[CMD_MAX_LEN];

  if (!dequeueCommand(buffer)) {
    return;
  }

  String command = String(buffer);

  command.trim();

  if (command.startsWith("GET:")) {

    String eventId = command.substring(4);

    eventId.trim();

    transferAudioFile(eventId, 0);

    return;
  }

  if (command.startsWith("RESUME:")) {

    String rest = command.substring(7);

    int colon = rest.lastIndexOf(':');

    if (colon <= 0 || colon == (int)rest.length() - 1) {

      publishTransferMessage("ERROR:BAD_RESUME_FORMAT");

      return;
    }

    String eventId = rest.substring(0, colon);
    String offsetText = rest.substring(colon + 1);

    eventId.trim();
    offsetText.trim();

    for (size_t i = 0; i < offsetText.length(); i++) {

      if (!isDigit(offsetText.charAt(i))) {

        publishTransferMessage("ERROR:BAD_RESUME_FORMAT");

        return;
      }
    }

    uint32_t offset = (uint32_t)strtoul(offsetText.c_str(), nullptr, 10);

    transferAudioFile(eventId, offset);

    return;
  }

  if (command == "STATUS") {

    publishTransferMessage(String("STATUS:") + recordingStatus);

    return;
  }

  if (command == "LIST") {

    listRecordings();

    return;
  }

  if (command.startsWith("DELETE:")) {

    String eventId = command.substring(7);

    eventId.trim();

    deleteRecording(eventId);

    return;
  }

  publishTransferMessage("ERROR:UNKNOWN_COMMAND");
}

// ============================================================
// BLE WATCHDOG: make sure the device is always discoverable
// ============================================================

// ============================================================
// BATTERY STATUS
// ============================================================

void updateBattery(bool force) {

  static unsigned long lastUpdate = 0;
  static int lastPercent = -2;

  if (batteryCharacteristic == nullptr) {
    return;
  }

  if (!force && millis() - lastUpdate < BATTERY_UPDATE_MS) {
    return;
  }

  lastUpdate = millis();

  int millivolts = -1;
  int percent = -1;

#if BATTERY_ADC_PIN >= 0

  uint32_t sum = 0;

  for (int i = 0; i < 8; i++) {
    sum += analogReadMilliVolts(BATTERY_ADC_PIN);
  }

  millivolts = (int)((sum / 8) * BATTERY_DIVIDER);

  percent = (int)(
    ((long)(millivolts - BATTERY_EMPTY_MV) * 100L) /
    (BATTERY_FULL_MV - BATTERY_EMPTY_MV)
  );

  if (percent < 0) {
    percent = 0;
  }

  if (percent > 100) {
    percent = 100;
  }

#endif

  char json[64];

  snprintf(
    json,
    sizeof(json),
    "{\"battery_percent\":%d,\"voltage_mv\":%d}",
    percent,
    millivolts
  );

  batteryCharacteristic->setValue(json);

  if (deviceConnected && (force || percent != lastPercent)) {
    batteryCharacteristic->notify();
  }

  lastPercent = percent;
}

void maintainBle() {

  static unsigned long lastCheck = 0;

  if (millis() - lastCheck < 2000) {
    return;
  }

  lastCheck = millis();

  if (deviceConnected) {
    return;
  }

  NimBLEAdvertising* advertising = NimBLEDevice::getAdvertising();

  if (!advertising->isAdvertising()) {

    Serial.println("Advertising was stopped; restarting.");

    advertising->start();
  }
}

// ============================================================
// SETUP
// ============================================================

void setup() {

  Serial.begin(115200);

  delay(1000);

  pinMode(SOS_BUTTON_PIN, INPUT_PULLUP);

  pinMode(GREEN_LED_PIN, OUTPUT);
  pinMode(RED_LED_PIN, OUTPUT);

  digitalWrite(GREEN_LED_PIN, LOW);
  digitalWrite(RED_LED_PIN, LOW);

  Serial.println();
  Serial.println("==================================");
  Serial.println("SalamaSphere Day 9 BLE Transfer v1.3.0");
  Serial.println("==================================");

  sdReady = initializeSD();

  microphoneReady = initializeMicrophone();

  // ----------------------------------------
  // Initialize BLE
  // ----------------------------------------

  NimBLEDevice::init(DEVICE_NAME);

  NimBLEDevice::setMTU(PREFERRED_MTU);

  bleServer = NimBLEDevice::createServer();

  bleServer->setCallbacks(new SalamaServerCallbacks());

  salamaService = bleServer->createService(SERVICE_UUID);

  deviceIdCharacteristic =
    salamaService->createCharacteristic(
      DEVICE_ID_UUID,
      NIMBLE_PROPERTY::READ
    );

  deviceIdCharacteristic->setValue(
    "{\"device_id\":\"SALAMA-DEVICE-001\","
    "\"device_name\":\"SalamaSphere\","
    "\"firmware_version\":\"1.3.0\"}"
  );

  sosEventCharacteristic =
    salamaService->createCharacteristic(
      SOS_EVENT_UUID,
      NIMBLE_PROPERTY::READ | NIMBLE_PROPERTY::NOTIFY
    );

  sosEventCharacteristic->setValue("{\"event_type\":\"NONE\"}");

  recordingStatusCharacteristic =
    salamaService->createCharacteristic(
      RECORDING_STATUS_UUID,
      NIMBLE_PROPERTY::READ | NIMBLE_PROPERTY::NOTIFY
    );

  recordingStatusCharacteristic->setValue("INITIALIZING");

  audioMetadataCharacteristic =
    salamaService->createCharacteristic(
      AUDIO_METADATA_UUID,
      NIMBLE_PROPERTY::READ | NIMBLE_PROPERTY::NOTIFY
    );

  audioMetadataCharacteristic->setValue("{\"transfer_status\":\"NONE\"}");

  fileTransferCharacteristic =
    salamaService->createCharacteristic(
      FILE_TRANSFER_UUID,
      NIMBLE_PROPERTY::READ | NIMBLE_PROPERTY::NOTIFY
    );

  fileTransferCharacteristic->setValue("IDLE");

  fileTransferCharacteristic->setCallbacks(new TransferStreamCallbacks());

  transferAckCharacteristic =
    salamaService->createCharacteristic(
      TRANSFER_ACK_UUID,
      NIMBLE_PROPERTY::READ |
      NIMBLE_PROPERTY::WRITE |
      NIMBLE_PROPERTY::WRITE_NR |
      NIMBLE_PROPERTY::NOTIFY
    );

  transferAckCharacteristic->setValue("IDLE");

  transferAckCharacteristic->setCallbacks(new TransferCommandCallbacks());

  batteryCharacteristic =
    salamaService->createCharacteristic(
      BATTERY_UUID,
      NIMBLE_PROPERTY::READ | NIMBLE_PROPERTY::NOTIFY
    );

  batteryCharacteristic->setValue("{\"battery_percent\":-1,\"voltage_mv\":-1}");

  updateBattery(true);

  salamaService->start();

  NimBLEAdvertising* advertising = NimBLEDevice::getAdvertising();

  advertising->addServiceUUID(SERVICE_UUID);

  advertising->setName(DEVICE_NAME);

  advertising->enableScanResponse(true);

  advertising->start();

  // ----------------------------------------
  // Report initialization status
  // ----------------------------------------

  updateReadyLeds();

  if (sdReady && microphoneReady) {

    updateRecordingStatus("READY");

    Serial.println("STATUS: READY");

  } else {

    updateRecordingStatus("ERROR");

    Serial.println("STATUS: INITIALIZATION FAILED (will retry on next SOS)");
  }

  Serial.println("BLE advertising started.");
  Serial.println("Phone: connect, request MTU 247, enable notifications on FILE_TRANSFER.");
  Serial.println("Commands: STATUS | LIST | GET:<id> | RESUME:<id>:<offset> | DELETE:<id> | ABORT");
  Serial.println("Hold SOS button for at least 1.5 seconds.");
}

// ============================================================
// MAIN LOOP
// ============================================================

void loop() {

  // SOS has priority over everything else.
  unsigned long holdDuration = 0;

  bool sos = false;

  if (sosPending) {

    sos = true;
    holdDuration = sosPendingHold;
    sosPending = false;

  } else if (pollSosButton(holdDuration)) {

    sos = true;
  }

  if (sos) {
    generateSosEvent(holdDuration);
  }

  // Commands from the phone (GET / RESUME / LIST / ...).
  processPendingCommand();

  // Keep the device discoverable after any disconnect.
  maintainBle();

  // Periodic battery report.
  updateBattery(false);

  // After a (re)connection, push the list of recordings still on the
  // SD card so the app can resume synchronization automatically.
  // Waits until notifications are on and the MTU is large enough.
  if (
    syncRequested &&
    deviceConnected &&
    transferSubscribed &&
    currentMtu >= 64
  ) {

    syncRequested = false;

    delay(300);

    listRecordings();
  }

  // If hardware failed earlier (e.g. SD removed), try to recover while idle.
  static unsigned long lastRecoveryTry = 0;

  if (
    (!sdReady || !microphoneReady) &&
    millis() - lastRecoveryTry > 10000
  ) {

    lastRecoveryTry = millis();

    if (ensureHardwareReady()) {
      updateRecordingStatus("READY");
    }
  }

  delay(5);
}
