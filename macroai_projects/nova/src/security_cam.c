#include "security_cam.h"
#include "mock_arduino.h"
#include <stdio.h>
#include <string.h>

static SecurityCamConfig cam_config;
static SecurityCamState cam_state;
static uint8_t motion_readings;
static char status_buf[128];

static uint8_t debounce_threshold(void) {
    uint8_t t = (uint8_t)((11 - cam_config.sensitivity) / 2);
    if (t < 1) t = 1;
    if (t > 5) t = 5;
    return t;
}

void security_cam_init(const SecurityCamConfig *config) {
    cam_config = *config;
    if (cam_config.sensitivity < 1) cam_config.sensitivity = 1;
    if (cam_config.sensitivity > 10) cam_config.sensitivity = 10;

    cam_state.current_state = CAM_IDLE;
    cam_state.state_entered_ms = millis();
    cam_state.motion_count = 0;
    cam_state.alarm_active = 0;
    cam_state.recording = 0;
    motion_readings = 0;

    pinMode(PIR_PIN, INPUT);
    pinMode(BUZZER_PIN, OUTPUT);
    pinMode(LED_GREEN_PIN, OUTPUT);
    pinMode(LED_RED_PIN, OUTPUT);
    pinMode(CAMERA_TRIGGER_PIN, OUTPUT);

    digitalWrite(BUZZER_PIN, LOW);
    digitalWrite(LED_GREEN_PIN, HIGH);
    digitalWrite(LED_RED_PIN, LOW);
    digitalWrite(CAMERA_TRIGGER_PIN, LOW);
}

void security_cam_update(void) {
    unsigned long now = millis();
    unsigned long elapsed = now - cam_state.state_entered_ms;

    switch (cam_state.current_state) {
    case CAM_IDLE:
        digitalWrite(LED_GREEN_PIN, HIGH);
        if (digitalRead(PIR_PIN) == HIGH) {
            motion_readings++;
        } else {
            motion_readings = 0;
        }
        if (motion_readings >= debounce_threshold()) {
            cam_state.current_state = CAM_MOTION_DETECTED;
            cam_state.state_entered_ms = now;
            cam_state.motion_count++;
            motion_readings = 0;
            Serial_println("[CAM] Motion detected");
        }
        break;

    case CAM_MOTION_DETECTED:
        digitalWrite(BUZZER_PIN, HIGH);
        digitalWrite(LED_RED_PIN, HIGH);
        digitalWrite(LED_GREEN_PIN, LOW);
        digitalWrite(CAMERA_TRIGGER_PIN, HIGH);
        cam_state.alarm_active = 1;
        cam_state.recording = 0;
        cam_state.current_state = CAM_ALARM_ACTIVE;
        cam_state.state_entered_ms = now;
        Serial_println("[CAM] Alarm activated");
        break;

    case CAM_ALARM_ACTIVE:
        if (elapsed >= cam_config.alarm_duration_ms) {
            cam_state.current_state = CAM_RECORDING;
            cam_state.state_entered_ms = now;
            cam_state.recording = 1;
            Serial_println("[CAM] Recording started");
        }
        break;

    case CAM_RECORDING:
        if (elapsed >= cam_config.recording_duration_ms) {
            cam_state.current_state = CAM_COOLDOWN;
            cam_state.state_entered_ms = now;
            cam_state.recording = 0;
            Serial_println("[CAM] Entering cooldown");
        }
        break;

    case CAM_COOLDOWN:
        if (digitalRead(PIR_PIN) == HIGH) {
            motion_readings++;
        } else {
            motion_readings = 0;
        }
        if (motion_readings >= debounce_threshold()) {
            cam_state.state_entered_ms = now;
            motion_readings = 0;
            cam_state.motion_count++;
            Serial_println("[CAM] Motion during cooldown — timer reset");
        }
        if (elapsed >= cam_config.cooldown_duration_ms) {
            digitalWrite(BUZZER_PIN, LOW);
            digitalWrite(LED_RED_PIN, LOW);
            digitalWrite(CAMERA_TRIGGER_PIN, LOW);
            digitalWrite(LED_GREEN_PIN, HIGH);
            cam_state.alarm_active = 0;
            cam_state.recording = 0;
            cam_state.current_state = CAM_IDLE;
            cam_state.state_entered_ms = now;
            Serial_println("[CAM] Returned to idle");
        }
        break;
    }
}

const char *security_cam_get_status_string(void) {
    const char *state_name;
    switch (cam_state.current_state) {
    case CAM_IDLE:            state_name = "IDLE"; break;
    case CAM_MOTION_DETECTED: state_name = "MOTION_DETECTED"; break;
    case CAM_ALARM_ACTIVE:    state_name = "ALARM_ACTIVE"; break;
    case CAM_RECORDING:       state_name = "RECORDING"; break;
    case CAM_COOLDOWN:        state_name = "COOLDOWN"; break;
    default:                  state_name = "UNKNOWN"; break;
    }
    snprintf(status_buf, sizeof(status_buf),
             "State: %s | Motions: %u | Alarm: %s | Rec: %s | Time: %lu",
             state_name,
             cam_state.motion_count,
             cam_state.alarm_active ? "ON" : "OFF",
             cam_state.recording ? "ON" : "OFF",
             millis());
    return status_buf;
}
