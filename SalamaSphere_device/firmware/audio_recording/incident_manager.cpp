#include "incident_manager.h"
#include "../ble_communication/ble_config.h"
#include <esp_system.h>

String IncidentManager::newEventId() {
  char id[48];
  snprintf(id, sizeof(id), "%08lx-%04lx-%04lx-%04lx-%012lx",
           (unsigned long)ESP.getEfuseMac(), (unsigned long)millis() & 0xffff,
           (unsigned long)ESP.getChipRevision() & 0xffff,
           (unsigned long)ESP.getCpuFreqMHz() & 0xffff,
           (unsigned long)esp_random());
  return String(id);
}

String IncidentManager::eventJson(const String& eventId) const {
  return "{\"event_id\":\"" + eventId +
         "\",\"device_identifier\":\"" + DEVICE_ID +
         "\",\"event_type\":\"SOS\",\"timestamp\":null,"
         "\"protocol_version\":1,\"recording_status\":\"ready\"}";
}
