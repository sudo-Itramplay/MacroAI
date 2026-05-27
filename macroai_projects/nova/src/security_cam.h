#ifndef SECURITY_CAM_H
#define SECURITY_CAM_H

#include <stdint.h>

#define PIR_PIN 2
#define BUZZER_PIN 3
#define LED_GREEN_PIN 4
#define LED_RED_PIN 5
#define CAMERA_TRIGGER_PIN 6

#define CAM_IDLE 0
#define CAM_MOTION_DETECTED 1
#define CAM_ALARM_ACTIVE 2
#define CAM_RECORDING 3
#define CAM_COOLDOWN 4

typedef struct {
    uint16_t alarm_duration_ms;
    uint16_t cooldown_duration_ms;
    uint16_t recording_duration_ms;
    uint8_t sensitivity;
} SecurityCamConfig;

typedef struct {
    uint8_t current_state;
    unsigned long state_entered_ms;
    uint8_t motion_count;
    uint8_t alarm_active;
    uint8_t recording;
} SecurityCamState;

void security_cam_init(const SecurityCamConfig *config);
void security_cam_update(void);
const char *security_cam_get_status_string(void);

#endif
