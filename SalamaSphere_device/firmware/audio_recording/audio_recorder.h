#ifndef AUDIO_RECORDER_H
#define AUDIO_RECORDER_H

#include <Arduino.h>

class AudioRecorder {
 public:
  bool begin();
  bool record(const char* path, uint32_t seconds);
};

#endif
