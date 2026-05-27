#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>
#include <unistd.h>
#include <getopt.h>

#include "mock_arduino.h"
#include "sim_engine.h"
#include "security_cam.h"
#include "logger.h"
#include "sensor_profiles.h"
#include "tui.h"
#include "test_harness.h"

/* Default camera configuration */
#define DEFAULT_ALARM_DURATION   5000
#define DEFAULT_COOLDOWN_DURATION 2000
#define DEFAULT_RECORDING_DURATION 3000
#define DEFAULT_SENSITIVITY      5

/* Time step for TUI continuous run mode (ms) */
#define TUI_STEP_MS 50

/* Application modes */
typedef enum {
    MODE_TUI,
    MODE_TEST,
    MODE_HEADLESS
} AppMode;

/* Application configuration */
typedef struct {
    AppMode mode;
    char log_file[256];
    char scenario_file[256];
    char config_file[256];
    SecurityCamConfig cam_config;
    uint8_t verbose;
} AppConfig;

/* Global state for signal handling */
static volatile sig_atomic_t g_running = 1;
static int g_tui_initialized = 0;

/* Signal handler: set flag and cleanup ncurses if active */
static void sigint_handler(int sig) {
    (void)sig;
    g_running = 0;
    if (g_tui_initialized) {
        tui_cleanup();
        g_tui_initialized = 0;
    }
}

/* Print usage information */
static void print_usage(const char *prog) {
    fprintf(stderr,
        "Usage: %s [OPTIONS]\n"
        "  -t            Run in TUI mode (default)\n"
        "  -h            Run in headless test mode\n"
        "  -f <file>     Load scenario file\n"
        "  -l <file>     Log file for recording/playback\n"
        "  -c <file>     Camera configuration file\n"
        "  -v            Verbose output\n"
        "  --help        Show this help\n",
        prog);
}

/* Initialize all modules with default state */
static void app_init(AppConfig *config) {
    mock_arduino_reset();
    Serial_begin(9600);

    if (config->verbose) {
        printf("[init] Arduino HAL reset, serial at 9600 baud\n");
    }
}

/* Cleanup resources */
static void app_cleanup(void) {
    if (g_tui_initialized) {
        tui_cleanup();
        g_tui_initialized = 0;
    }
}

/* Run in TUI mode */
static int run_tui_mode(AppConfig *config) {
    SimEngine engine;
    Logger logger;
    SecurityCamState cam_state;
    SensorProfile profile;
    int ch;
    int continuous = 0;
    int profile_loaded = 0;

    sim_engine_init(&engine);
    logger_init(&logger);
    security_cam_init(&config->cam_config);

    if (config->log_file[0] != '\0') {
        if (logger_start_recording(&logger, config->log_file) != 0) {
            fprintf(stderr, "[warn] Could not open log file: %s\n", config->log_file);
        }
    }

    tui_init();
    g_tui_initialized = 1;

    if (config->verbose) {
        printf("[tui] Initialized. Press 'q' to quit.\n");
    }

    /* Main TUI loop */
    while (g_running) {
        ch = tui_handle_input();

        switch (ch) {
        case 'q':
            g_running = 0;
            break;

        case 'n':
            /* Step time forward */
            engine.step_ms = TUI_STEP_MS;
            sim_engine_step(&engine);
            security_cam_update();
            break;

        case 'r':
            continuous = !continuous;
            if (continuous) {
                sim_engine_resume(&engine);
            } else {
                sim_engine_pause(&engine);
            }
            break;

        case 'p':
            continuous = 0;
            sim_engine_pause(&engine);
            break;

        case '1':
            memset(&profile, 0, sizeof(profile));
            /* Generate constant motion profile (200ms interval, 10s duration) */
            {
                unsigned long interval = 200;
                unsigned long duration = 10000;
                unsigned long t = 0;
                uint16_t idx = 0;
                while (t < duration && idx < 200) {
                    profile.events[idx].time_ms = t;
                    profile.events[idx].pin = PIR_PIN;
                    profile.events[idx].value = HIGH;
                    profile.events[idx].event_type = EVENT_DIGITAL_WRITE;
                    idx++;
                    t += interval;
                    if (t < duration && idx < 200) {
                        profile.events[idx].time_ms = t;
                        profile.events[idx].pin = PIR_PIN;
                        profile.events[idx].value = LOW;
                        profile.events[idx].event_type = EVENT_DIGITAL_WRITE;
                        idx++;
                        t += interval;
                    }
                }
                profile.event_count = idx;
                profile.duration_ms = duration;
                profile.loop = 0;
                strncpy(profile.name, "Constant Motion", sizeof(profile.name) - 1);
            }
            profile_loaded = 1;
            if (config->verbose) {
                printf("[profile] Loaded constant motion (%u events)\n", profile.event_count);
            }
            break;

        case '2':
            memset(&profile, 0, sizeof(profile));
            /* Generate burst motion profile */
            {
                unsigned long t = 0;
                uint16_t idx = 0;
                int burst;
                for (burst = 0; burst < 3 && idx < 190; burst++) {
                    int i;
                    for (i = 0; i < 5 && idx < 199; i++) {
                        profile.events[idx].time_ms = t;
                        profile.events[idx].pin = PIR_PIN;
                        profile.events[idx].value = HIGH;
                        profile.events[idx].event_type = EVENT_DIGITAL_WRITE;
                        idx++;
                        t += 50;
                        if (idx < 199) {
                            profile.events[idx].time_ms = t;
                            profile.events[idx].pin = PIR_PIN;
                            profile.events[idx].value = LOW;
                            profile.events[idx].event_type = EVENT_DIGITAL_WRITE;
                            idx++;
                            t += 50;
                        }
                    }
                    t += 3000; /* Gap between bursts */
                }
                profile.event_count = idx;
                profile.duration_ms = t;
                profile.loop = 0;
                strncpy(profile.name, "Burst Motion", sizeof(profile.name) - 1);
            }
            profile_loaded = 1;
            if (config->verbose) {
                printf("[profile] Loaded burst motion (%u events)\n", profile.event_count);
            }
            break;

        case '3':
            memset(&profile, 0, sizeof(profile));
            /* Generate noisy profile */
            {
                unsigned long t = 0;
                uint16_t idx = 0;
                unsigned int seed = (unsigned int)engine.current_time;
                while (t < 10000 && idx < 200) {
                    seed = seed * 1103515245 + 12345;
                    if ((seed >> 16) & 0x01) {
                        profile.events[idx].time_ms = t;
                        profile.events[idx].pin = PIR_PIN;
                        profile.events[idx].value = HIGH;
                        profile.events[idx].event_type = EVENT_DIGITAL_WRITE;
                        idx++;
                        if (idx < 200) {
                            profile.events[idx].time_ms = t + 20;
                            profile.events[idx].pin = PIR_PIN;
                            profile.events[idx].value = LOW;
                            profile.events[idx].event_type = EVENT_DIGITAL_WRITE;
                            idx++;
                        }
                    }
                    t += 100;
                }
                profile.event_count = idx;
                profile.duration_ms = 10000;
                profile.loop = 0;
                strncpy(profile.name, "Noisy", sizeof(profile.name) - 1);
            }
            profile_loaded = 1;
            if (config->verbose) {
                printf("[profile] Loaded noisy profile (%u events)\n", profile.event_count);
            }
            break;

        case '4':
            memset(&profile, 0, sizeof(profile));
            /* Generate edge case: rapid on/off */
            {
                uint16_t idx = 0;
                unsigned long t = 0;
                while (t < 5000 && idx < 198) {
                    profile.events[idx].time_ms = t;
                    profile.events[idx].pin = PIR_PIN;
                    profile.events[idx].value = HIGH;
                    profile.events[idx].event_type = EVENT_DIGITAL_WRITE;
                    idx++;
                    profile.events[idx].time_ms = t + 10;
                    profile.events[idx].pin = PIR_PIN;
                    profile.events[idx].value = LOW;
                    profile.events[idx].event_type = EVENT_DIGITAL_WRITE;
                    idx++;
                    t += 20;
                }
                profile.event_count = idx;
                profile.duration_ms = 5000;
                profile.loop = 0;
                strncpy(profile.name, "Edge Case", sizeof(profile.name) - 1);
            }
            profile_loaded = 1;
            if (config->verbose) {
                printf("[profile] Loaded edge case profile (%u events)\n", profile.event_count);
            }
            break;

        case 's':
            if (config->log_file[0] != '\0') {
                logger_save_to_file(&logger);
                if (config->verbose) {
                    printf("[log] Saved to %s\n", config->log_file);
                }
            }
            break;

        case 'l':
            if (config->log_file[0] != '\0') {
                logger_load_from_file(&logger, config->log_file);
                if (config->verbose) {
                    printf("[log] Loaded from %s\n", config->log_file);
                }
            }
            break;

        default:
            break;
        }

        /* Apply loaded profile events to engine */
        if (profile_loaded) {
            uint16_t i;
            for (i = 0; i < profile.event_count; i++) {
                SimEvent evt;
                memset(&evt, 0, sizeof(evt));
                evt.trigger_ms = profile.events[i].time_ms;
                evt.event_type = profile.events[i].event_type;
                evt.pin = profile.events[i].pin;
                evt.value = profile.events[i].value;
                evt.next = NULL;
                sim_engine_schedule(&engine, profile.events[i].time_ms, evt);
            }
            profile_loaded = 0;
        }

        /* Continuous run: step engine and update camera */
        if (continuous && engine.running) {
            sim_engine_step(&engine);
            security_cam_update();
        }

        /* Draw TUI */
        tui_draw_pins();
        tui_draw_serial();
        tui_draw_status();
        tui_update();

        /* Frame rate limit */
        usleep(TUI_STEP_MS * 1000);
    }

    logger_stop_recording(&logger);
    app_cleanup();
    return 0;
}

/* Run in test mode (automated, with TUI) */
static int run_test_mode(AppConfig *config) {
    TestScenario scenario;
    int result;

    test_harness_init();

    if (config->scenario_file[0] == '\0') {
        fprintf(stderr, "[error] No scenario file specified. Use -f <file>.\n");
        return 1;
    }

    if (config->verbose) {
        printf("[test] Loading scenario: %s\n", config->scenario_file);
    }

    if (test_harness_load_scenario(config->scenario_file, &scenario) != 0) {
        fprintf(stderr, "[error] Failed to load scenario: %s\n", config->scenario_file);
        return 1;
    }

    result = test_harness_execute(&scenario);
    test_harness_report();

    return result == 0 ? 0 : 1;
}

/* Run in headless mode (no TUI, output serial to stdout) */
static int run_headless_mode(AppConfig *config) {
    SimEngine engine;
    Logger logger;
    TestScenario scenario;
    int result;

    sim_engine_init(&engine);
    logger_init(&logger);
    security_cam_init(&config->cam_config);

    if (config->scenario_file[0] == '\0') {
        fprintf(stderr, "[error] No scenario file specified. Use -f <file>.\n");
        return 1;
    }

    if (config->verbose) {
        printf("[headless] Loading scenario: %s\n", config->scenario_file);
    }

    test_harness_init();

    if (test_harness_load_scenario(config->scenario_file, &scenario) != 0) {
        fprintf(stderr, "[error] Failed to load scenario: %s\n", config->scenario_file);
        return 1;
    }

    result = test_harness_execute(&scenario);

    /* Output serial buffer to stdout */
    {
        const char *serial_buf = mock_get_serial_tx_buffer();
        int serial_len = mock_get_serial_tx_length();
        if (serial_len > 0) {
            fwrite(serial_buf, 1, (size_t)serial_len, stdout);
            fputc('\n', stdout);
        }
    }

    if (config->verbose) {
        printf("[headless] Scenario complete. Result: %s\n",
               result == 0 ? "PASS" : "FAIL");
    }

    logger_stop_recording(&logger);
    return result == 0 ? 0 : 1;
}

int main(int argc, char *argv[]) {
    AppConfig config;
    struct sigaction sa;
    int opt;
    int long_index = 0;

    static struct option long_options[] = {
        {"help", no_argument, 0, 0},
        {0, 0, 0, 0}
    };

    /* Initialize config with defaults */
    memset(&config, 0, sizeof(config));
    config.mode = MODE_TUI;
    config.cam_config.alarm_duration_ms = DEFAULT_ALARM_DURATION;
    config.cam_config.cooldown_duration_ms = DEFAULT_COOLDOWN_DURATION;
    config.cam_config.recording_duration_ms = DEFAULT_RECORDING_DURATION;
    config.cam_config.sensitivity = DEFAULT_SENSITIVITY;

    /* Parse arguments */
    while ((opt = getopt_long(argc, argv, "thf:l:c:v", long_options, &long_index)) != -1) {
        switch (opt) {
        case 't':
            config.mode = MODE_TUI;
            break;
        case 'h':
            config.mode = MODE_HEADLESS;
            break;
        case 'f':
            strncpy(config.scenario_file, optarg, sizeof(config.scenario_file) - 1);
            config.scenario_file[sizeof(config.scenario_file) - 1] = '\0';
            break;
        case 'l':
            strncpy(config.log_file, optarg, sizeof(config.log_file) - 1);
            config.log_file[sizeof(config.log_file) - 1] = '\0';
            break;
        case 'c':
            strncpy(config.config_file, optarg, sizeof(config.config_file) - 1);
            config.config_file[sizeof(config.config_file) - 1] = '\0';
            break;
        case 'v':
            config.verbose = 1;
            break;
        case 0: /* long option */
            print_usage(argv[0]);
            return 0;
        default:
            print_usage(argv[0]);
            return 1;
        }
    }

    /* Install signal handler for clean shutdown */
    memset(&sa, 0, sizeof(sa));
    sa.sa_handler = sigint_handler;
    sigemptyset(&sa.sa_mask);
    sa.sa_flags = 0;
    sigaction(SIGINT, &sa, NULL);
    sigaction(SIGTERM, &sa, NULL);

    /* Initialize base modules */
    app_init(&config);

    /* Dispatch to mode */
    switch (config.mode) {
    case MODE_TUI:
        return run_tui_mode(&config);
    case MODE_TEST:
        return run_test_mode(&config);
    case MODE_HEADLESS:
        return run_headless_mode(&config);
    default:
        fprintf(stderr, "[error] Unknown mode\n");
        return 1;
    }
}
