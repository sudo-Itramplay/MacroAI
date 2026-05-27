#ifndef SIM_ENGINE_H
#define SIM_ENGINE_H

#include <stdint.h>

#define EVENT_DIGITAL_WRITE 0
#define EVENT_ANALOG_WRITE 1
#define EVENT_DELAY 2
#define EVENT_CHECK_SERIAL 3

#define MAX_EVENTS 100

typedef struct SimEvent {
    unsigned long trigger_ms;
    uint8_t event_type;
    uint8_t pin;
    int value;
    struct SimEvent *next;
} SimEvent;

typedef struct {
    unsigned long current_time;
    unsigned long target_time;
    unsigned long step_ms;
    SimEvent *event_queue;
    uint8_t running;
} SimEngine;

void sim_engine_init(SimEngine *engine);
int sim_engine_schedule(SimEngine *engine, unsigned long delay_ms, SimEvent event);
int sim_engine_step(SimEngine *engine);
void sim_engine_run_until(SimEngine *engine, unsigned long target_time);
unsigned long sim_engine_get_time(const SimEngine *engine);
void sim_engine_pause(SimEngine *engine);
void sim_engine_resume(SimEngine *engine);

#endif
