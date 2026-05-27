#define _POSIX_C_SOURCE 200809L

#include "test_harness.h"
#include "mock_arduino.h"
#include "sim_engine.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <ctype.h>
#include <dirent.h>
#include <sys/stat.h>

static uint32_t total_tests = 0;
static uint32_t passed_tests = 0;
static uint32_t failed_tests = 0;

static SimEngine engine;
static uint8_t engine_initialized = 0;

static void trim(char *str) {
    char *end;
    while (isspace((unsigned char)*str)) str++;
    if (*str == 0) return;
    end = str + strlen(str) - 1;
    while (end > str && isspace((unsigned char)*end)) end--;
    end[1] = '\0';
}

static int parse_pin_value(const char *token, uint8_t *out) {
    if (strcasecmp(token, "HIGH") == 0) {
        *out = HIGH;
        return 0;
    }
    if (strcasecmp(token, "LOW") == 0) {
        *out = LOW;
        return 0;
    }
    return -1;
}

static int parse_command_line(const char *line, TestCommand *cmd) {
    char buf[256];
    strncpy(buf, line, sizeof(buf) - 1);
    buf[sizeof(buf) - 1] = '\0';
    trim(buf);

    if (buf[0] == '#' || buf[0] == '\0') {
        cmd->command[0] = '\0';
        return 0;
    }

    char *saveptr = NULL;
    char *token = strtok_r(buf, " ", &saveptr);
    if (!token) {
        cmd->command[0] = '\0';
        return 0;
    }

    strncpy(cmd->command, token, sizeof(cmd->command) - 1);
    cmd->command[sizeof(cmd->command) - 1] = '\0';

    cmd->arg1 = 0;
    cmd->arg2 = 0;
    cmd->delay_after_ms = 0;

    if (strcasecmp(token, "SET_PIN") == 0) {
        char *pin_str = strtok_r(NULL, " ", &saveptr);
        char *val_str = strtok_r(NULL, " ", &saveptr);
        if (!pin_str || !val_str) return -1;
        cmd->arg1 = atoi(pin_str);
        uint8_t val;
        if (parse_pin_value(val_str, &val) != 0) return -1;
        cmd->arg2 = val;
        cmd->command[0] = 'S';
    } else if (strcasecmp(token, "SET_ANALOG") == 0) {
        char *pin_str = strtok_r(NULL, " ", &saveptr);
        char *val_str = strtok_r(NULL, " ", &saveptr);
        if (!pin_str || !val_str) return -1;
        cmd->arg1 = atoi(pin_str);
        cmd->arg2 = atoi(val_str);
        cmd->command[0] = 'A';
    } else if (strcasecmp(token, "ASSERT_PIN") == 0) {
        char *pin_str = strtok_r(NULL, " ", &saveptr);
        char *val_str = strtok_r(NULL, " ", &saveptr);
        if (!pin_str || !val_str) return -1;
        cmd->arg1 = atoi(pin_str);
        uint8_t val;
        if (parse_pin_value(val_str, &val) != 0) return -1;
        cmd->arg2 = val;
        cmd->command[0] = 'P';
    } else if (strcasecmp(token, "ASSERT_SERIAL") == 0) {
        char *rest = strtok_r(NULL, "", &saveptr);
        if (!rest) return -1;
        while (*rest && (*rest == ' ' || *rest == '"')) rest++;
        char *end = rest + strlen(rest) - 1;
        while (end > rest && (*end == '"' || *end == ' ')) { *end = '\0'; end--; }
        cmd->arg1 = 0;
        cmd->arg2 = 0;
        strncpy(cmd->command + 1, rest, sizeof(cmd->command) - 2);
        cmd->command[sizeof(cmd->command) - 1] = '\0';
        cmd->command[0] = 'X';
    } else if (strcasecmp(token, "WAIT") == 0) {
        char *ms_str = strtok_r(NULL, " ", &saveptr);
        if (!ms_str) return -1;
        cmd->arg1 = atoi(ms_str);
        cmd->command[0] = 'W';
    } else if (strcasecmp(token, "LOG") == 0) {
        char *rest = strtok_r(NULL, "", &saveptr);
        if (rest) {
            strncpy(cmd->command + 1, rest, sizeof(cmd->command) - 2);
            cmd->command[sizeof(cmd->command) - 1] = '\0';
        }
        cmd->command[0] = 'L';
    } else if (strcasecmp(token, "REPEAT") == 0) {
        char *count_str = strtok_r(NULL, " ", &saveptr);
        if (!count_str) return -1;
        cmd->arg1 = atoi(count_str);
        cmd->command[0] = 'R';
    } else {
        return -1;
    }

    return 0;
}

void test_harness_init(void) {
    if (!engine_initialized) {
        sim_engine_init(&engine);
        engine_initialized = 1;
    }
    total_tests = 0;
    passed_tests = 0;
    failed_tests = 0;
}

int test_harness_load_scenario(const char *filename, TestScenario *scenario) {
    FILE *f = fopen(filename, "r");
    if (!f) return -1;

    scenario->command_count = 0;
    scenario->auto_run = 1;

    const char *basename = strrchr(filename, '/');
    if (!basename) basename = strrchr(filename, '\\');
    if (basename) basename++; else basename = filename;
    strncpy(scenario->name, basename, sizeof(scenario->name) - 1);
    scenario->name[sizeof(scenario->name) - 1] = '\0';
    char *dot = strrchr(scenario->name, '.');
    if (dot) *dot = '\0';

    char line[256];
    while (fgets(line, sizeof(line), f) && scenario->command_count < MAX_COMMANDS) {
        TestCommand cmd;
        if (parse_command_line(line, &cmd) != 0) {
            fclose(f);
            return -1;
        }
        if (cmd.command[0] != '\0') {
            scenario->commands[scenario->command_count++] = cmd;
        }
    }

    fclose(f);
    return 0;
}

int test_harness_execute(TestScenario *scenario) {
    if (!engine_initialized) {
        sim_engine_init(&engine);
        engine_initialized = 1;
    }

    int scenario_failed = 0;

    for (uint8_t i = 0; i < scenario->command_count; i++) {
        TestCommand *cmd = &scenario->commands[i];

        switch (cmd->command[0]) {
            case 'S': {
                if (cmd->arg1 >= 0 && cmd->arg1 < MAX_PINS) {
                    pinMode((uint8_t)cmd->arg1, OUTPUT);
                    digitalWrite((uint8_t)cmd->arg1, (uint8_t)cmd->arg2);
                }
                break;
            }
            case 'A': {
                if (cmd->arg1 >= 0 && cmd->arg1 < MAX_ANALOG_PINS) {
                    analogWrite((uint8_t)cmd->arg1, cmd->arg2);
                }
                break;
            }
            case 'P': {
                int actual = digitalRead((uint8_t)cmd->arg1);
                int expected = cmd->arg2;
                if (actual != expected) {
                    fprintf(stderr, "FAIL: ASSERT_PIN %d: expected %s, got %s\n",
                            cmd->arg1,
                            expected ? "HIGH" : "LOW",
                            actual ? "HIGH" : "LOW");
                    scenario_failed = 1;
                }
                break;
            }
            case 'X': {
                const char *expected = cmd->command + 1;
                const char *actual = mock_get_serial_tx_buffer();
                if (strstr(actual, expected) == NULL) {
                    fprintf(stderr, "FAIL: ASSERT_SERIAL: expected \"%s\" in \"%s\"\n",
                            expected, actual);
                    scenario_failed = 1;
                }
                break;
            }
            case 'W': {
                if (cmd->arg1 > 0) {
                    delay((unsigned long)cmd->arg1);
                }
                break;
            }
            case 'L': {
                printf("[LOG %s] %s\n", scenario->name, cmd->command + 1);
                break;
            }
            case 'R': {
                fprintf(stderr, "WARN: REPEAT command not supported in this implementation\n");
                break;
            }
            default:
                break;
        }
    }

    total_tests++;
    if (scenario_failed) {
        failed_tests++;
    } else {
        passed_tests++;
    }

    return scenario_failed ? 0 : 1;
}

int test_harness_run_all(const char *directory) {
    DIR *dir = opendir(directory);
    if (!dir) {
        fprintf(stderr, "ERROR: Cannot open directory: %s\n", directory);
        return -1;
    }

    struct dirent *entry;
    int all_passed = 1;

    while ((entry = readdir(dir)) != NULL) {
        size_t len = strlen(entry->d_name);
        if (len < 5) continue;
        if (strcmp(entry->d_name + len - 4, ".txt") != 0) continue;

        char path[512];
        snprintf(path, sizeof(path), "%s/%s", directory, entry->d_name);

        struct stat st;
        if (stat(path, &st) != 0 || !S_ISREG(st.st_mode)) continue;

        TestScenario scenario;
        if (test_harness_load_scenario(path, &scenario) != 0) {
            fprintf(stderr, "ERROR: Failed to load scenario: %s\n", path);
            all_passed = 0;
            continue;
        }

        mock_arduino_reset();
        sim_engine_init(&engine);
        engine_initialized = 1;

        printf("Running scenario: %s\n", scenario.name);
        if (!test_harness_execute(&scenario)) {
            all_passed = 0;
        }
    }

    closedir(dir);
    return all_passed ? 0 : 1;
}

void test_harness_report(void) {
    printf("\n=== Test Harness Report ===\n");
    printf("Total scenarios: %u\n", total_tests);
    printf("Passed:          %u\n", passed_tests);
    printf("Failed:          %u\n", failed_tests);
    printf("===========================\n");

    if (failed_tests > 0) {
        printf("RESULT: FAIL\n");
    } else if (total_tests > 0) {
        printf("RESULT: PASS\n");
    } else {
        printf("RESULT: NO TESTS\n");
    }
}
