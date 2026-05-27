#include "sensor_profiles.h"
#include "sim_engine.h"
#include "security_cam.h"
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#define LCG_A 1103515245UL
#define LCG_C 12345UL
#define LCG_M 2147483648UL

static unsigned long lcg_state = 1;

static unsigned long lcg_next(void) {
    lcg_state = (LCG_A * lcg_state + LCG_C) % LCG_M;
    return lcg_state;
}

static void add_event(SensorProfile *profile, unsigned long time_ms,
                      uint8_t pin, int value, uint8_t event_type) {
    if (profile->event_count >= 200) return;
    SensorEvent *e = &profile->events[profile->event_count++];
    e->time_ms = time_ms;
    e->pin = pin;
    e->value = value;
    e->event_type = event_type;
}

void sensor_profile_generate_constant(SensorProfile *profile,
                                      unsigned long interval_ms,
                                      unsigned long duration) {
    memset(profile, 0, sizeof(*profile));
    strncpy(profile->name, "constant", sizeof(profile->name) - 1);
    profile->duration_ms = duration;
    profile->loop = 0;

    unsigned long t = 0;
    uint8_t high = 0;
    while (t < duration && profile->event_count < 200) {
        add_event(profile, t, PIR_PIN, high ? 1 : 0, EVENT_DIGITAL_WRITE);
        high = !high;
        t += interval_ms;
    }
}

void sensor_profile_generate_burst(SensorProfile *profile,
                                   unsigned long duration) {
    memset(profile, 0, sizeof(*profile));
    strncpy(profile->name, "burst", sizeof(profile->name) - 1);
    profile->duration_ms = duration;
    profile->loop = 0;

    unsigned long t = 0;
    while (t < duration && profile->event_count < 196) {
        for (int i = 0; i < 5 && t < duration; i++) {
            add_event(profile, t, PIR_PIN, 1, EVENT_DIGITAL_WRITE);
            t += 50;
            add_event(profile, t, PIR_PIN, 0, EVENT_DIGITAL_WRITE);
            t += 50;
        }
        t += 2000;
    }
}

void sensor_profile_generate_noisy(SensorProfile *profile,
                                   unsigned long duration) {
    memset(profile, 0, sizeof(*profile));
    strncpy(profile->name, "noisy", sizeof(profile->name) - 1);
    profile->duration_ms = duration;
    profile->loop = 0;

    lcg_state = (unsigned long)time(NULL);

    unsigned long t = 0;
    while (t < duration && profile->event_count < 198) {
        unsigned long r = lcg_next();
        if ((r % 100) < 8) {
            add_event(profile, t, PIR_PIN, 1, EVENT_DIGITAL_WRITE);
            t += 30 + (lcg_next() % 70);
            add_event(profile, t, PIR_PIN, 0, EVENT_DIGITAL_WRITE);
        }
        t += 100 + (lcg_next() % 200);
    }
}

int sensor_profile_load_from_file(SensorProfile *profile, const char *filename) {
    memset(profile, 0, sizeof(*profile));
    strncpy(profile->name, "loaded", sizeof(profile->name) - 1);

    FILE *fp = fopen(filename, "r");
    if (!fp) return -1;

    char line[128];
    unsigned long max_time = 0;
    while (fgets(line, sizeof(line), fp) && profile->event_count < 200) {
        if (line[0] == '#' || line[0] == '\n') continue;

        unsigned long time_ms;
        uint8_t pin;
        int value;
        if (sscanf(line, "%lu,%hhu,%d", &time_ms, &pin, &value) == 3) {
            uint8_t etype = EVENT_DIGITAL_WRITE;
            if (pin == PIR_PIN) etype = EVENT_DIGITAL_WRITE;
            else etype = EVENT_ANALOG_WRITE;
            add_event(profile, time_ms, pin, value, etype);
            if (time_ms > max_time) max_time = time_ms;
        }
    }

    fclose(fp);
    profile->duration_ms = max_time;
    return 0;
}

int sensor_profile_apply_to_engine(const SensorProfile *profile, SimEngine *engine) {
    int scheduled = 0;
    for (uint16_t i = 0; i < profile->event_count; i++) {
        const SensorEvent *se = &profile->events[i];
        SimEvent ev;
        ev.trigger_ms = 0;
        ev.event_type = se->event_type;
        ev.pin = se->pin;
        ev.value = se->value;
        ev.next = NULL;

        unsigned long delay = (se->time_ms > engine->current_time)
                              ? se->time_ms - engine->current_time : 0;
        if (sim_engine_schedule(engine, delay, ev) == 0)
            scheduled++;
    }
    return scheduled;
}

void sensor_profile_reset(SensorProfile *profile) {
    memset(profile, 0, sizeof(*profile));
}
