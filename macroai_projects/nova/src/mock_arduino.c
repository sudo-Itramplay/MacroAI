#include "mock_arduino.h"
#include <string.h>

/* Pin state arrays */
static uint8_t pin_modes[MAX_PINS];
static uint8_t digital_states[MAX_PINS];
static int analog_values[MAX_ANALOG_PINS];

/* Serial buffers (TX = output from device, RX = input to device) */
static char serial_tx_buffer[MAX_SERIAL_BUFFER];
static int serial_tx_index;
static char serial_rx_buffer[MAX_SERIAL_BUFFER];
static int serial_rx_index;
static int serial_rx_available;

/* Simulated time */
static unsigned long current_time_ms;

/* Baud rate (stored but not functionally used) */
static unsigned long serial_baud;

void pinMode(uint8_t pin, uint8_t mode) {
    if (pin < MAX_PINS) {
        pin_modes[pin] = mode;
    }
}

void digitalWrite(uint8_t pin, uint8_t value) {
    if (pin < MAX_PINS && pin_modes[pin] == OUTPUT) {
        digital_states[pin] = value;
    }
}

int digitalRead(uint8_t pin) {
    if (pin < MAX_PINS) {
        return digital_states[pin];
    }
    return LOW;
}

int analogRead(uint8_t pin) {
    if (pin < MAX_ANALOG_PINS) {
        return analog_values[pin];
    }
    return 0;
}

void analogWrite(uint8_t pin, int value) {
    if (pin < MAX_ANALOG_PINS) {
        /* Clamp PWM value to 0-255 */
        if (value < 0) value = 0;
        if (value > 255) value = 255;
        analog_values[pin] = value;
    }
}

unsigned long millis(void) {
    return current_time_ms;
}

void delay(unsigned long ms) {
    current_time_ms += ms;
}

void Serial_begin(unsigned long baud) {
    serial_baud = baud;
}

void Serial_print(const char *str) {
    if (!str) return;
    size_t len = strlen(str);
    for (size_t i = 0; i < len; i++) {
        if (serial_tx_index < MAX_SERIAL_BUFFER - 1) {
            serial_tx_buffer[serial_tx_index++] = str[i];
        }
    }
    serial_tx_buffer[serial_tx_index] = '\0';
}

void Serial_println(const char *str) {
    Serial_print(str);
    if (serial_tx_index < MAX_SERIAL_BUFFER - 2) {
        serial_tx_buffer[serial_tx_index++] = '\n';
        serial_tx_buffer[serial_tx_index] = '\0';
    }
}

int Serial_available(void) {
    return serial_rx_available;
}

char Serial_read(void) {
    if (serial_rx_available <= 0) {
        return '\0';
    }
    char c = serial_rx_buffer[serial_rx_index];
    serial_rx_index++;
    serial_rx_available--;
    if (serial_rx_available <= 0) {
        serial_rx_index = 0;
        serial_rx_available = 0;
    }
    return c;
}

void mock_serial_inject(const char *data, int len) {
    for (int i = 0; i < len && serial_rx_available < MAX_SERIAL_BUFFER; i++) {
        int write_pos = (serial_rx_index + serial_rx_available) % MAX_SERIAL_BUFFER;
        serial_rx_buffer[write_pos] = data[i];
        serial_rx_available++;
    }
}

uint8_t mock_get_pin_mode(uint8_t pin) {
    if (pin < MAX_PINS) return pin_modes[pin];
    return INPUT;
}

uint8_t mock_get_digital_state(uint8_t pin) {
    if (pin < MAX_PINS) return digital_states[pin];
    return LOW;
}

const char *mock_get_serial_tx_buffer(void) {
    return serial_tx_buffer;
}

int mock_get_serial_tx_length(void) {
    return serial_tx_index;
}

void mock_arduino_reset(void) {
    memset(pin_modes, 0, sizeof(pin_modes));
    memset(digital_states, 0, sizeof(digital_states));
    memset(analog_values, 0, sizeof(analog_values));

    memset(serial_tx_buffer, 0, sizeof(serial_tx_buffer));
    serial_tx_index = 0;
    memset(serial_rx_buffer, 0, sizeof(serial_rx_buffer));
    serial_rx_index = 0;
    serial_rx_available = 0;

    current_time_ms = 0;
    serial_baud = 0;
}
