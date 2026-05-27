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
    test_##name(); \
    if (_before == tests_failed) { \
        printf("PASS\n"); \
        tests_passed++; \
    } else { \
        printf("FAIL\n"); \
    } \
} while (0)

static void test_pin_mode(void) {
    pinMode(0, OUTPUT);
    ASSERT(mock_get_pin_mode(0) == OUTPUT, "pin 0 mode should be OUTPUT");
    ASSERT(mock_get_pin_mode(1) == INPUT, "pin 1 should default to INPUT");

    pinMode(5, INPUT_PULLUP);
    ASSERT(mock_get_pin_mode(5) == INPUT_PULLUP, "pin 5 mode should be INPUT_PULLUP");

    pinMode(MAX_PINS, OUTPUT);
    ASSERT(mock_get_pin_mode(MAX_PINS) == INPUT, "out-of-range pin should return INPUT");
}

static void test_digital_write_read(void) {
    pinMode(3, OUTPUT);
    digitalWrite(3, HIGH);
    ASSERT(digitalRead(3) == HIGH, "digitalRead should return HIGH after write");

    digitalWrite(3, LOW);
    ASSERT(digitalRead(3) == LOW, "digitalRead should return LOW after write");

    pinMode(4, INPUT);
    digitalWrite(4, HIGH);
    ASSERT(digitalRead(4) == LOW, "digitalWrite on INPUT pin should not change state");
}

static void test_analog_read(void) {
    analogWrite(0, 128);
    ASSERT(analogRead(0) == 128, "analogRead should return 128 after analogWrite(0, 128)");

    analogWrite(0, 0);
    ASSERT(analogRead(0) == 0, "analogRead should return 0 after analogWrite(0, 0)");

    analogWrite(0, 255);
    ASSERT(analogRead(0) == 255, "analogRead should return 255 after analogWrite(0, 255)");

    analogWrite(1, 300);
    ASSERT(analogRead(1) == 255, "analogWrite should clamp to 255");

    analogWrite(1, -10);
    ASSERT(analogRead(1) == 0, "analogWrite should clamp negative to 0");

    ASSERT(analogRead(MAX_ANALOG_PINS) == 0, "out-of-range analogRead should return 0");
}

static void test_millis_delay(void) {
    ASSERT(millis() == 0, "millis() should start at 0");

    delay(100);
    ASSERT(millis() == 100, "millis() should be 100 after delay(100)");

    delay(50);
    ASSERT(millis() == 150, "millis() should be 150 after another delay(50)");

    delay(0);
    ASSERT(millis() == 150, "millis() should be 150 after delay(0)");
}

static void test_serial_buffer(void) {
    Serial_print("Hello");
    ASSERT(mock_get_serial_tx_length() == 5, "serial TX length should be 5");
    ASSERT(strcmp(mock_get_serial_tx_buffer(), "Hello") == 0,
           "serial TX buffer should contain 'Hello'");

    Serial_print(" World");
    ASSERT(strcmp(mock_get_serial_tx_buffer(), "Hello World") == 0,
           "serial TX buffer should contain 'Hello World'");

    mock_arduino_reset();

    Serial_println("Line1");
    ASSERT(strcmp(mock_get_serial_tx_buffer(), "Line1\n") == 0,
           "Serial_println should append newline");

    Serial_print((const char *)NULL);
    ASSERT(strcmp(mock_get_serial_tx_buffer(), "Line1\n") == 0,
           "Serial_print(NULL) should be no-op");

    mock_arduino_reset();

    ASSERT(Serial_available() == 0, "Serial_available should be 0 initially");
    ASSERT(Serial_read() == '\0', "Serial_read on empty buffer should return '\\0'");

    mock_serial_inject("AB", 2);
    ASSERT(Serial_available() == 2, "Serial_available should be 2");
    ASSERT(Serial_read() == 'A', "Serial_read should pop first char (FIFO)");
    ASSERT(Serial_read() == 'B', "Serial_read should pop second char (FIFO)");
    ASSERT(Serial_available() == 0, "Serial_available should be 0 after draining");
    ASSERT(Serial_read() == '\0', "Serial_read on drained buffer should return '\\0'");

    mock_serial_inject("Hello", 5);
    mock_serial_inject(" World", 6);
    ASSERT(Serial_available() == 11, "Serial_available should reflect total injected bytes");
    ASSERT(Serial_read() == 'H', "Serial_read FIFO order: H");
    ASSERT(Serial_read() == 'e', "Serial_read FIFO order: e");
    ASSERT(Serial_read() == 'l', "Serial_read FIFO order: l");
    ASSERT(Serial_read() == 'l', "Serial_read FIFO order: l");
    ASSERT(Serial_read() == 'o', "Serial_read FIFO order: o");
    ASSERT(Serial_read() == ' ', "Serial_read FIFO order: space");
    ASSERT(Serial_available() == 5, "5 bytes remaining after partial read");
}

int main(void) {
    printf("=== Mock Arduino HAL Tests ===\n\n");

    RUN_TEST(pin_mode);
    RUN_TEST(digital_write_read);
    RUN_TEST(analog_read);
    RUN_TEST(millis_delay);
    RUN_TEST(serial_buffer);

    printf("\n=== Results: %d passed, %d failed ===\n",
           tests_passed, tests_failed);

    return tests_failed > 0 ? 1 : 0;
}
