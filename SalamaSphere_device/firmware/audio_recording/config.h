#ifndef AUDIO_RECORDING_CONFIG_H
#define AUDIO_RECORDING_CONFIG_H

#include "../ble_communication/ble_config.h"

#ifndef I2S_PORT
#define I2S_PORT I2S_NUM_0
#endif

#ifndef I2S_BCLK_PIN
#define I2S_BCLK_PIN 15
#endif

#ifndef I2S_LRCLK_PIN
#define I2S_LRCLK_PIN 16
#endif

#ifndef I2S_DATA_PIN
#define I2S_DATA_PIN 17
#endif

#ifndef AUDIO_SAMPLE_RATE
#define AUDIO_SAMPLE_RATE 16000
#endif

#ifndef AUDIO_CHANNELS
#define AUDIO_CHANNELS 1
#endif

#ifndef AUDIO_BITS_PER_SAMPLE
#define AUDIO_BITS_PER_SAMPLE 16
#endif

#endif
