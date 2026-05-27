#ifndef TEST_HARNESS_H
#define TEST_HARNESS_H

#include <stdint.h>

#define MAX_COMMANDS 100

#define CMD_SET_PIN       0
#define CMD_SET_ANALOG    1
#define CMD_ASSERT_PIN    2
#define CMD_ASSERT_SERIAL 3
#define CMD_WAIT          4
#define CMD_LOG           5
#define CMD_REPEAT        6

typedef struct {
    char command[16];
    int arg1;
    int arg2;
    unsigned long delay_after_ms;
} TestCommand;

typedef struct {
    char name[64];
    TestCommand commands[MAX_COMMANDS];
    uint8_t command_count;
    uint8_t auto_run;
} TestScenario;

void test_harness_init(void);
int test_harness_load_scenario(const char *filename, TestScenario *scenario);
int test_harness_execute(TestScenario *scenario);
int test_harness_run_all(const char *directory);
void test_harness_report(void);

#endif
