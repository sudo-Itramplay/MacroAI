#ifndef LOGGER_H
#define LOGGER_H

#include <stdio.h>
#include <stdint.h>
#include "sim_engine.h"

#define LOG_PIN_CHANGE     0
#define LOG_SERIAL_OUTPUT  1
#define LOG_STATE_CHANGE   2
#define LOG_SENSOR_EVENT   3

#define MAX_LOG_ENTRIES 1000

typedef struct {
    unsigned long timestamp;
    uint8_t entry_type;
    char message[128];
} LogEntry;

typedef struct {
    LogEntry entries[MAX_LOG_ENTRIES];
    uint16_t entry_count;
    uint8_t recording;
    uint8_t playback_active;
    FILE *file_handle;
} Logger;

void logger_init(Logger *logger);
int logger_record(Logger *logger, LogEntry entry);
int logger_start_recording(Logger *logger, const char *filename);
void logger_stop_recording(Logger *logger);
int logger_save_to_file(Logger *logger);
int logger_load_from_file(Logger *logger, const char *filename);
void logger_playback_init(Logger *logger);
int logger_playback_step(Logger *logger, SimEngine *engine);

#endif
