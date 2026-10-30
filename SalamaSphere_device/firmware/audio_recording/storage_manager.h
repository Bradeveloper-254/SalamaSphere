#ifndef STORAGE_MANAGER_H
#define STORAGE_MANAGER_H

#include <Arduino.h>
#include <LittleFS.h>

class StorageManager {
 public:
  bool begin() { return LittleFS.begin(true); }
  bool exists(const char* path) { return LittleFS.exists(path); }
  size_t size(const char* path) {
    File file = LittleFS.open(path, "r");
    if (!file) return 0;
    const size_t result = file.size();
    file.close();
    return result;
  }
  bool remove(const char* path) { return !LittleFS.exists(path) || LittleFS.remove(path); }
};

#endif
