#ifndef MOCK_ARDUINO_H
#define MOCK_ARDUINO_H

#include <stdint.h>
#include <stddef.h>

#define HIGH 1
#define LOW 0
#define INPUT 0
#define OUTPUT 1
#define INPUT_PULLUP 2

#define MAX_PINS 20
#define MAX_SERIAL_BUFFER 1024
#define MAX_ANALOG_PINS 6

void pinMode(uint8_t pin, uint8_t mode);
void digitalWrite(uint8_t pin, uint8_t value);
int digitalRead(uint8_t pin);
int analogRead(uint8_t pin);
void analogWrite(uint8_t pin, int value);
unsigned long millis(void);
void delay(unsigned long ms);

void Serial_begin(unsigned long baud);
void Serial_print(const char *str);
void Serial_println(const char *str);
int Serial_available(void);
char Serial_read(void);

void mock_arduino_reset(void);

void mock_serial_inject(const char *data, int len);

uint8_t mock_get_pin_mode(uint8_t pin);
uint8_t mock_get_digital_state(uint8_t pin);
const char *mock_get_serial_tx_buffer(void);
int mock_get_serial_tx_length(void);

#endif
