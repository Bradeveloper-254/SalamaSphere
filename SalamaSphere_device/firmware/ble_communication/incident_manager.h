#ifndef BLE_INCIDENT_MANAGER_H
#define BLE_INCIDENT_MANAGER_H

// Compatibility include for sketches that keep BLE and recording modules
// separate. The implementation lives in audio_recording/incident_manager.*.
#include "../audio_recording/incident_manager.h"
using BleIncidentManager = IncidentManager;

#endif
