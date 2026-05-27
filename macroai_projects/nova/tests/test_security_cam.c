#include "security_cam.h"
#include "mock_arduino.h"
#include <stdio.h>
#include <string.h>

static int tests_passed = 0;
static int tests_failed = 0;

#define ASSERT(cond, msg) do { \
    if (!(cond)) { \
        fprintf(stderr, "  FAIL: %s (%s:%d)\n", msg, __FILE__, __LINE__); \
        tests_failed++; \
        return; \
    } \
} while (0)

#define RUN_TEST(name) do { \
    int _before = tests_failed; \
    printf("  %s ... ", #name); \
    mock_arduino_reset(); \
    security_cam_init(&default_config); \
    test_##name(); \
    if (_before == tests_failed) { \
        printf("PASS\n"); \
        tests_passed++; \
    } else { \
        printf("FAIL\n"); \
    } \
} while (0)

static SecurityCamConfig default_config = {
    .alarm_duration_ms = 1000,
    .cooldown_duration_ms = 2000,
    .recording_duration_ms = 1000,
    .sensitivity = 5
};

static void set_pir(uint8_t value) {
    pinMode(PIR_PIN, OUTPUT);
    digitalWrite(PIR_PIN, value);
}

static int status_contains(const char *text) {
    return strstr(security_cam_get_status_string(), text) != NULL;
}

static void test_camera_init(void) {
    ASSERT(mock_get_digital_state(BUZZER_PIN) == LOW, "buzzer should be LOW after init");
    ASSERT(mock_get_digital_state(LED_GREEN_PIN) == HIGH, "green LED should be HIGH after init");
    ASSERT(mock_get_digital_state(LED_RED_PIN) == LOW, "red LED should be LOW after init");
    ASSERT(mock_get_digital_state(CAMERA_TRIGGER_PIN) == LOW, "camera trigger should be LOW after init");
    ASSERT(status_contains("IDLE"), "initial state should be IDLE");
}

static void test_motion_detection(void) {
    set_pir(HIGH);

    security_cam_update();
    ASSERT(!status_contains("MOTION_DETECTED"), "should stay IDLE after 1 reading");

    security_cam_update();
    ASSERT(!status_contains("MOTION_DETECTED"), "should stay IDLE after 2 readings");

    security_cam_update();
    ASSERT(status_contains("MOTION_DETECTED"), "should transition to MOTION_DETECTED after 3rd reading (sensitivity=5)");
}

static void test_alarm_activation(void) {
    set_pir(HIGH);
    security_cam_update();
    security_cam_update();
    security_cam_update();
    ASSERT(status_contains("MOTION_DETECTED"), "should be in MOTION_DETECTED");

    security_cam_update();
    ASSERT(status_contains("ALARM_ACTIVE"), "should transition to ALARM_ACTIVE");
    ASSERT(mock_get_digital_state(BUZZER_PIN) == HIGH, "buzzer should be HIGH during alarm");
    ASSERT(mock_get_digital_state(LED_RED_PIN) == HIGH, "red LED should be HIGH during alarm");
    ASSERT(mock_get_digital_state(LED_GREEN_PIN) == LOW, "green LED should be LOW during alarm");
    ASSERT(mock_get_digital_state(CAMERA_TRIGGER_PIN) == HIGH, "camera trigger should be HIGH during alarm");
}

static void test_cooldown(void) {
    set_pir(HIGH);

    security_cam_update();
    security_cam_update();
    security_cam_update();
    ASSERT(status_contains("MOTION_DETECTED"), "should reach MOTION_DETECTED");

    security_cam_update();
    ASSERT(status_contains("ALARM_ACTIVE"), "should reach ALARM_ACTIVE");

    delay(1000);
    security_cam_update();
    ASSERT(status_contains("RECORDING"), "should transition to RECORDING after alarm duration");

    delay(1000);
    security_cam_update();
    ASSERT(status_contains("COOLDOWN"), "should transition to COOLDOWN after recording duration");

    delay(2000);
    security_cam_update();
    ASSERT(status_contains("IDLE"), "should return to IDLE after cooldown");
    ASSERT(mock_get_digital_state(LED_GREEN_PIN) == HIGH, "green LED should be HIGH in IDLE");
    ASSERT(mock_get_digital_state(BUZZER_PIN) == LOW, "buzzer should be LOW after cooldown");
    ASSERT(mock_get_digital_state(LED_RED_PIN) == LOW, "red LED should be LOW after cooldown");
    ASSERT(mock_get_digital_state(CAMERA_TRIGGER_PIN) == LOW, "camera trigger should be LOW after cooldown");
}

static void test_rapid_motions(void) {
    for (int i = 0; i < 10; i++) {
        set_pir(HIGH);
        security_cam_update();
        set_pir(LOW);
        security_cam_update();
    }
    ASSERT(status_contains("IDLE"), "should remain IDLE with rapid toggling");
    ASSERT(mock_get_digital_state(BUZZER_PIN) == LOW, "buzzer should remain LOW");
    ASSERT(mock_get_digital_state(LED_RED_PIN) == LOW, "red LED should remain LOW");
}

int main(void) {
    printf("=== Security Camera Logic Tests ===\n\n");

    RUN_TEST(camera_init);
    RUN_TEST(motion_detection);
    RUN_TEST(alarm_activation);
    RUN_TEST(cooldown);
    RUN_TEST(rapid_motions);

    printf("\n=== Results: %d passed, %d failed ===\n",
           tests_passed, tests_failed);

    return tests_failed > 0 ? 1 : 0;
}
