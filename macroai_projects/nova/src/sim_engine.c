#include "sim_engine.h"
#include <string.h>

static SimEvent events[MAX_EVENTS];
static SimEvent *free_list = NULL;

static void init_free_list(void) {
    free_list = NULL;
    for (int i = MAX_EVENTS - 1; i >= 0; i--) {
        events[i].next = free_list;
        free_list = &events[i];
    }
}

static SimEvent *alloc_event(void) {
    if (!free_list) return NULL;
    SimEvent *e = free_list;
    free_list = free_list->next;
    e->next = NULL;
    return e;
}

static void free_event(SimEvent *e) {
    e->next = free_list;
    free_list = e;
}

void sim_engine_init(SimEngine *engine) {
    init_free_list();
    memset(engine, 0, sizeof(*engine));
    engine->step_ms = 1;
    engine->running = 0;
}

int sim_engine_schedule(SimEngine *engine, unsigned long delay_ms, SimEvent event) {
    SimEvent *node = alloc_event();
    if (!node) return -1;

    *node = event;
    node->trigger_ms = engine->current_time + delay_ms;
    node->next = NULL;

    SimEvent **pp = &engine->event_queue;
    while (*pp && (*pp)->trigger_ms <= node->trigger_ms)
        pp = &(*pp)->next;
    node->next = *pp;
    *pp = node;

    return 0;
}

int sim_engine_step(SimEngine *engine) {
    if (!engine->event_queue) return 0;

    SimEvent *head = engine->event_queue;
    if (engine->current_time < head->trigger_ms)
        return 0;

    engine->event_queue = head->next;
    engine->current_time = head->trigger_ms;

    SimEvent consumed = *head;
    free_event(head);

    switch (consumed.event_type) {
    case EVENT_DIGITAL_WRITE:
        /* handled by caller via mock_arduino */
        break;
    case EVENT_ANALOG_WRITE:
        break;
    case EVENT_DELAY:
        break;
    case EVENT_CHECK_SERIAL:
        break;
    }

    return 1;
}

void sim_engine_run_until(SimEngine *engine, unsigned long target_time) {
    while (engine->event_queue && engine->current_time < target_time) {
        if (!sim_engine_step(engine)) {
            engine->current_time = engine->event_queue->trigger_ms;
        }
    }
    if (engine->current_time < target_time)
        engine->current_time = target_time;
}

unsigned long sim_engine_get_time(const SimEngine *engine) {
    return engine->current_time;
}

void sim_engine_pause(SimEngine *engine) {
    engine->running = 0;
}

void sim_engine_resume(SimEngine *engine) {
    engine->running = 1;
}
