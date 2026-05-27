#ifndef SENSOR_PROFILES_H
#define SENSOR_PROFILES_H

#include <stdint.h>

#define PROFILE_CONSTANT_MOTION 0
#define PROFILE_BURST_MOTION 1
#define PROFILE_NOISY 2
#define PROFILE_EDGE_CASE 3

typedef struct {
    unsigned long time_ms;
    uint8_t pin;
    int value;
    uint8_t event_type;
} SensorEvent;

typedef struct {
    char name[32];
    SensorEvent events[200];
    uint16_t event_count;
    unsigned long duration_ms;
    uint8_t loop;
} SensorProfile;

#endif
