#include "logger.h"
#include "sim_engine.h"
#include <string.h>
#include <stdlib.h>

void logger_init(Logger *logger) {
    logger->entry_count = 0;
    logger->recording = 0;
    logger->playback_active = 0;
    logger->file_handle = NULL;
}

int logger_record(Logger *logger, LogEntry entry) {
    if (logger->entry_count >= MAX_LOG_ENTRIES) {
        return -1;
    }
    logger->entries[logger->entry_count++] = entry;
    return 0;
}

int logger_start_recording(Logger *logger, const char *filename) {
    if (logger->file_handle) {
        fclose(logger->file_handle);
    }
    logger->file_handle = fopen(filename, "w");
    if (!logger->file_handle) {
        return -1;
    }
    logger->recording = 1;
    return 0;
}

void logger_stop_recording(Logger *logger) {
    if (logger->file_handle) {
        fflush(logger->file_handle);
        fclose(logger->file_handle);
        logger->file_handle = NULL;
    }
    logger->recording = 0;
}

int logger_save_to_file(Logger *logger) {
    if (!logger->file_handle) {
        return -1;
    }
    for (uint16_t i = 0; i < logger->entry_count; i++) {
        fprintf(logger->file_handle, "%lu,%u,%s\n",
                logger->entries[i].timestamp,
                logger->entries[i].entry_type,
                logger->entries[i].message);
    }
    fflush(logger->file_handle);
    return 0;
}

int logger_load_from_file(Logger *logger, const char *filename) {
    FILE *f = fopen(filename, "r");
    if (!f) {
        return -1;
    }

    logger->entry_count = 0;
    char line[256];

    while (fgets(line, sizeof(line), f) && logger->entry_count < MAX_LOG_ENTRIES) {
        unsigned long ts;
        unsigned int type;
        char msg[128];

        if (sscanf(line, "%lu,%u,%127[^\n]", &ts, &type, msg) == 3) {
            if (type <= LOG_SENSOR_EVENT) {
                LogEntry *e = &logger->entries[logger->entry_count];
                e->timestamp = ts;
                e->entry_type = (uint8_t)type;
                strncpy(e->message, msg, sizeof(e->message) - 1);
                e->message[sizeof(e->message) - 1] = '\0';
                logger->entry_count++;
            }
        }
    }

    fclose(f);
    return 0;
}

static uint16_t playback_index = 0;

void logger_playback_init(Logger *logger) {
    logger->playback_active = 1;
    playback_index = 0;
}

int logger_playback_step(Logger *logger, SimEngine *engine) {
    if (!logger->playback_active || playback_index >= logger->entry_count) {
        logger->playback_active = 0;
        return -1;
    }

    unsigned long now = sim_engine_get_time(engine);
    LogEntry *entry = &logger->entries[playback_index];

    if (entry->timestamp <= now) {
        SimEvent ev;
        ev.trigger_ms = entry->timestamp;
        ev.event_type = entry->entry_type;
        ev.pin = 0;
        ev.value = 0;
        ev.next = NULL;
        sim_engine_schedule(engine, 0, ev);
        playback_index++;
        return 0;
    }

    return 1;
}
