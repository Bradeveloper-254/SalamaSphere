#ifndef INCIDENT_MANAGER_H
#define INCIDENT_MANAGER_H

#include <Arduino.h>

class IncidentManager {
 public:
  String newEventId();
  String eventJson(const String& eventId) const;
};

#endif
