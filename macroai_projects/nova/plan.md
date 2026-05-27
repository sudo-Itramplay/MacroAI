# Project Plan: arduino-security-sim

## Architecture
The system follows a layered architecture with a hardware abstraction layer (HAL) at the bottom, business logic in the middle, and UI/testing at the top. The mock HAL implements Arduino-compatible function signatures using static memory pools, allowing the security camera logic to be developed and tested without real hardware. A simulation engine manages time progression and event scheduling, while the TUI and test harness provide two distinct interfaces to the same underlying system.

## Project Structure
- `src/mock_arduino.h` - HAL API declarations mirroring real Arduino functions
- `src/mock_arduino.c` - HAL implementation with pin state, timers, serial buffer
- `src/security_cam.h` - Security camera logic API
- `src/security_cam.c` - Camera state machine and sensor processing
- `src/sim_engine.h` - Simulation engine for time and event management
- `src/sim_engine.c` - Event queue and time stepping implementation
- `src/sensor_profiles.h` - Configurable sensor profile definitions
- `src/sensor_profiles.c` - Profile loading and event generation
- `src/logger.h` - Event logging and playback API
- `src/logger.c` - File I/O for recording and replaying scenarios
- `src/tui.h` - Terminal UI declarations
- `src/tui.c` - ncurses-based interactive interface
- `src/test_harness.h` - Automated test runner API
- `src/test_harness.c` - Script execution and validation
- `src/main.c` - Application entry point and module wiring
- `tests/test_security_cam.c` - Unit tests for camera logic
- `tests/test_mock_arduino.c` - Unit tests for HAL
- `tests/scenarios/` - Test scenario scripts directory
- `Makefile` - Build system with all/clean/test targets
- `README.md` - Project documentation

## Tasks

### [SIMPLE] ✅ Define mock Arduino HAL header
- **File**: `src/mock_arduino.h`
- **Description**: Define function signatures: `void pinMode(uint8_t pin, uint8_t mode)`, `void digitalWrite(uint8_t pin, uint8_t value)`, `int digitalRead(uint8_t pin)`, `int analogRead(uint8_t pin)`, `void analogWrite(uint8_t pin, int value)`, `unsigned long millis()`, `void delay(unsigned long ms)`, `void Serial_begin(unsigned long baud)`, `void Serial_print(const char *str)`, `void Serial_println(const char *str)`, `int Serial_available()`, `char Serial_read()`. Define constants: `HIGH`, `LOW`, `INPUT`, `OUTPUT`, `INPUT_PULLUP`. Define `MAX_PINS` (20), `MAX_SERIAL_BUFFER` (1024), `MAX_ANALOG_PINS` (6).

### [SIMPLE] ✅ Define data structures for pin state and serial buffer
- **File**: `src/mock_arduino.c`
- **Description**: Create static arrays: `uint8_t pin_modes[MAX_PINS]`, `uint8_t digital_states[MAX_PINS]`, `int analog_values[MAX_ANALOG_PINS]`, `char serial_tx_buffer[MAX_SERIAL_BUFFER]`, `char serial_rx_buffer[MAX_SERIAL_BUFFER]`. Create `serial_tx_index`, `serial_rx_index`, `serial_rx_available` counters. Create `unsigned long current_time_ms` for simulated time.

### [COMPLEX] ✅ Implement mock Arduino HAL functions
- **File**: `src/mock_arduino.c`
- **Description**: Implement all HAL functions. `pinMode` validates pin < MAX_PINS and sets mode. `digitalWrite` sets digital_states[pin] if mode is OUTPUT. `digitalRead` returns digital_states[pin]. `analogRead` returns analog_values[pin] (0-1023). `analogWrite` stores PWM value (0-255) in analog_values. `millis()` returns current_time_ms. `delay()` increments current_time_ms by argument. `Serial_print/println` appends to serial_tx_buffer with bounds checking. `Serial_available` returns serial_rx_available. `Serial_read` pops from serial_rx_buffer (FIFO). Implement `mock_arduino_reset()` to zero all state.

### [SIMPLE] ✅ Define simulation engine structures
- **File**: `src/sim_engine.h`
- **Description**: Define `SimEvent` struct with fields: `unsigned long trigger_ms`, `uint8_t event_type`, `uint8_t pin`, `int value`, `struct SimEvent *next`. Define `SimEngine` struct with: `unsigned long current_time`, `unsigned long target_time`, `unsigned long step_ms`, `SimEvent *event_queue`, `uint8_t running`. Define event types: `EVENT_DIGITAL_WRITE`, `EVENT_ANALOG_WRITE`, `EVENT_DELAY`, `EVENT_CHECK_SERIAL`. Define `MAX_EVENTS` (100).

### [COMPLEX] ✅ Implement simulation engine event queue and time stepping
- **File**: `src/sim_engine.c`
- **Description**: Implement static event pool `SimEvent events[MAX_EVENTS]` with free list. Functions: `sim_engine_init(SimEngine *engine)`, `sim_engine_schedule(SimEngine *engine, unsigned long delay_ms, SimEvent event)`, `sim_engine_step(SimEngine *engine)` processes next event in queue if time >= trigger_ms, `sim_engine_run_until(SimEngine *engine, unsigned long target_time)` loops step until target. Priority queue based on trigger_ms. `sim_engine_get_time()` returns current_time. `sim_engine_pause/resume()` toggles running flag.

### [SIMPLE] ✅ Define security camera logic header
- **File**: `src/security_cam.h`
- **Description**: Define pin assignments: `PIR_PIN` (2), `BUZZER_PIN` (3), `LED_GREEN_PIN` (4), `LED_RED_PIN` (5), `CAMERA_TRIGGER_PIN` (6). Define states: `CAM_IDLE`, `CAM_MOTION_DETECTED`, `CAM_ALARM_ACTIVE`, `CAM_RECORDING`, `CAM_COOLDOWN`. Define `SecurityCamConfig` struct: `uint16_t alarm_duration_ms`, `uint16_t cooldown_duration_ms`, `uint16_t recording_duration_ms`, `uint8_t sensitivity` (1-10). Define `SecurityCamState` struct: `uint8_t current_state`, `unsigned long state_entered_ms`, `uint8_t motion_count`, `uint8_t alarm_active`, `uint8_t recording`.

### [COMPLEX] ✅ Implement security camera state machine
- **File**: `src/security_cam.c`
- **Description**: Implement `security_cam_init(config)` to set initial state to CAM_IDLE. Implement `security_cam_update()` called each simulation step: reads PIR_PIN via digitalRead, debounces motion (requires N readings in window based on sensitivity), transitions IDLE->MOTION_DETECTED->ALARM_ACTIVE after threshold, activates BUZZER_PIN and LED_RED_PIN via digitalWrite, sets CAMERA_TRIGGER_PIN HIGH, transitions to RECORDING for recording_duration_ms, then COOLDOWN for cooldown_duration_ms, back to IDLE. Edge case: rapid successive motions reset cooldown timer. Implement `security_cam_get_status_string()` for display.

### [SIMPLE] ✅ Define sensor profile structures
- **File**: `src/sensor_profiles.h`
- **Description**: Define `SensorEvent` struct: `unsigned long time_ms`, `uint8_t pin`, `int value`, `uint8_t event_type`. Define `SensorProfile` struct: `char name[32]`, `SensorEvent events[200]`, `uint16_t event_count`, `unsigned long duration_ms`, `uint8_t loop`. Define preset profiles: `PROFILE_CONSTANT_MOTION` (regular intervals), `PROFILE_BURST_MOTION` (clustered events), `PROFILE_NOISY` (random noise), `PROFILE_EDGE_CASE` (rapid on/off).

### [COMPLEX] ✅ Implement sensor profile generation and loading
- **File**: `src/sensor_profiles.c`
- **Description**: Implement `sensor_profile_generate_constant(SensorProfile *profile, unsigned long interval_ms, unsigned long duration)` with regular PIR HIGH/LOW cycles. Implement `sensor_profile_generate_burst()` with clusters of motion events separated by gaps. Implement `sensor_profile_generate_noisy()` with random PIR spikes using LCG PRNG (seed from time). Implement `sensor_profile_load_from_file()` to parse CSV format: `time_ms,pin,value`. Implement `sensor_profile_apply_to_engine()` to schedule all events into SimEngine. Implement `sensor_profile_reset()`.

### [SIMPLE] ✅ Define logging structures and header
- **File**: `src/logger.h`
- **Description**: Define `LogEntry` struct: `unsigned long timestamp`, `uint8_t entry_type`, `char message[128]`. Define entry types: `LOG_PIN_CHANGE`, `LOG_SERIAL_OUTPUT`, `LOG_STATE_CHANGE`, `LOG_SENSOR_EVENT`. Define `MAX_LOG_ENTRIES` (1000). Define `Logger` struct: `LogEntry entries[MAX_LOG_ENTRIES]`, `uint16_t entry_count`, `uint8_t recording`, `uint8_t playback_active`, `FILE *file_handle`.

### [COMPLEX] ✅ Implement logging and playback system
- **File**: `src/logger.c`
- **Description**: Implement `logger_init(Logger *logger)`. Implement `logger_record(Logger *logger, LogEntry entry)` to append to entries[] with bounds check. Implement `logger_start_recording(Logger *logger, const char *filename)` opens file for writing. Implement `logger_stop_recording()` flushes and closes. Implement `logger_save_to_file()` writes all entries as CSV: `timestamp,type,message`. Implement `logger_load_from_file()` reads CSV into entries. Implement `logger_playback_init()` sets playback_active and resets index. Implement `logger_playback_step(Logger *logger, SimEngine *engine)` schedules next event from log if time matches. Edge case: handle corrupted file lines gracefully, skip invalid entries.

### [SIMPLE] ✅ Define TUI layout and state structures
- **File**: `src/tui.h`
- **Description**: Define `TuiState` struct with: `WINDOW *pin_window`, `WINDOW *serial_window`, `WINDOW *status_window`, `WINDOW *control_window`, `uint8_t selected_pin`, `uint8_t running`. Define key bindings: `KEY_QUIT` ('q'), `KEY_TOGGLE_PIN` ('t'), `KEY_INJECT_ANALOG` ('a'), `KEY_STEP_TIME` ('n'), `KEY_RUN_CONTINUOUS` ('r'), `KEY_PAUSE` ('p'), `KEY_SAVE_LOG` ('s'), `KEY_LOAD_LOG` ('l'), `KEY_PROFILE_SELECT` ('1'-'4').

### [COMPLEX] ✅ Implement TUI with ncurses
- **File**: `src/tui.c`
- **Description**: Implement `tui_init()` to initialize ncurses, create windows (pin display 20x40, serial output 10x80, status bar 3x80, control panel 8x40). Implement `tui_draw_pins()` showing all pin modes and states with color coding (green=HIGH, red=LOW, yellow=INPUT). Implement `tui_draw_serial()` scrolling serial output buffer. Implement `tui_draw_status()` showing security camera state, current time, simulation status. Implement `tui_handle_input()` mapping keys to actions: toggle pin state, inject analog value (prompt for 0-1023), advance time by configurable step, start/stop continuous run. Implement `tui_update()` refreshes all windows. Implement `tui_cleanup()` for proper ncurses teardown.

### [SIMPLE] ✅ Define test harness header
- **File**: `src/test_harness.h`
- **Description**: Define `TestCommand` struct: `char command[16]`, `int arg1`, `int arg2`, `unsigned long delay_after_ms`. Define `TestScenario` struct: `char name[64]`, `TestCommand commands[100]`, `uint8_t command_count`, `uint8_t auto_run`. Define commands: `CMD_SET_PIN`, `CMD_SET_ANALOG`, `CMD_ASSERT_PIN`, `CMD_ASSERT_SERIAL`, `CMD_WAIT`, `CMD_LOG`, `CMD_REPEAT`. Define `MAX_COMMANDS` (100).

### [COMPLEX] ✅ Implement test harness script execution
- **File**: `src/test_harness.c`
- **Description**: Implement `test_harness_init()`. Implement `test_harness_load_scenario(const char *filename)` parsing simple text format: `SET_PIN 2 HIGH`, `WAIT 1000`, `ASSERT_PIN 3 HIGH`, `ASSERT_SERIAL "Motion detected"`. Implement `test_harness_execute(TestScenario *scenario, SimEngine *engine)` stepping through commands, calling sim_engine_schedule for delays, using mock_arduino functions for pin operations, comparing assertions and recording PASS/FAIL. Implement `test_harness_run_all(const char *directory)` to scan and execute all .txt files in tests/scenarios/. Implement `test_harness_report()` printing summary: total tests, passed, failed with details.

### [SIMPLE] ✅ Define main.c application structure
- **File**: `src/main.c`
- **Description**: Define `AppMode` enum: `MODE_TUI`, `MODE_TEST`, `MODE_HEADLESS`. Define `AppConfig` struct: `AppMode mode`, `char log_file[256]`, `char scenario_file[256]`, `SecurityCamConfig cam_config`, `uint8_t verbose`. Implement argument parsing: `-t` for TUI, `-h` for headless test, `-f <file>` for scenario file, `-l <file>` for log file, `-v` for verbose, `-c <config>` for camera config file.

### [COMPLEX] ✅ Implement main.c application wiring and mode dispatch
- **File**: `src/main.c`
- **Description**: Implement `main(int argc, char *argv[])` with argument parsing using getopt. In MODE_TUI: init all modules, run tui_init, enter main loop calling sim_engine_step and security_cam_update each frame, handle input via tui_handle_input, cleanup on exit. In MODE_TEST: init modules, load scenario via test_harness, execute scenario, print report, exit with 0/1. In MODE_HEADLESS: init modules, load scenario, execute without TUI, output serial to stdout, exit. Implement signal handler for SIGINT to cleanup ncurses. Implement `app_init()` calling mock_arduino_reset, security_cam_init, sim_engine_init, logger_init. Implement `app_cleanup()` for teardown.

### [SIMPLE] ✅ Create Makefile with build targets
- **File**: `Makefile`
- **Description**: Define `CC=gcc`, `CFLAGS=-std=c11 -Wall -Wextra -pedantic -D_POSIX_C_SOURCE=200809L`, `LDFLAGS=-lncurses`. Define targets: `all` depends on `macroai_sim`, `macroai_sim` links all .o files, `clean` removes .o and binary, `test` compiles with `-DTEST_MODE` and runs headlessly. Define pattern rule `%.o: src/%.c`. Add `install` target to copy binary to /usr/local/bin. Add `debug` target with `-g -O0` flags. Add dependency tracking with `-MMD -MP`.

### [SIMPLE] ✅ Create test scenario files
- **File**: `tests/scenarios/basic_motion.txt`
- **Description**: Create test scenario: `SET_PIN 2 INPUT`, `SET_ANALOG 2 0`, `WAIT 500`, `SET_PIN 2 HIGH`, `WAIT 100`, `ASSERT_PIN 3 HIGH` (buzzer), `ASSERT_PIN 5 HIGH` (red LED), `WAIT 5000`, `ASSERT_PIN 3 LOW` (alarm off), `WAIT 2000`, `ASSERT_PIN 4 HIGH` (green LED, idle).

### [SIMPLE] ✅ Create unit test for mock Arduino HAL
- **File**: `tests/test_mock_arduino.c`
- **Description**: Implement `test_pin_mode()` verifies pinMode sets mode array. Implement `test_digital_write_read()` verifies write followed by read returns same value. Implement `test_analog_read()` verifies analog value storage. Implement `test_millis_delay()` verifies time increments correctly. Implement `test_serial_buffer()` verifies Serial_print appends and Serial_read pops FIFO. Implement `main()` calling all test functions, returning 0 on success, 1 on failure.

### [SIMPLE] ✅ Create unit test for security camera logic
- **File**: `tests/test_security_cam.c`
- **Description**: Implement `test_camera_init()` verifies initial state is CAM_IDLE. Implement `test_motion_detection()` simulates PIR HIGH, verifies state transitions to MOTION_DETECTED. Implement `test_alarm_activation()` verifies buzzer and red LED activate. Implement `test_cooldown()` verifies state returns to IDLE after cooldown period. Implement `test_rapid_motions()` verifies debounce prevents alarm spam. Implement `main()` calling all tests.

### [COMPLEX] ✅ Create comprehensive edge case test scenario
- **File**: `tests/scenarios/edge_cases.txt`
- **Description**: Create scenario testing: rapid pin toggling (10ms intervals), analog value injection at boundaries (0, 1023, out of range), concurrent sensor events, serial buffer overflow (fill to MAX_SERIAL_BUFFER), time step larger than alarm duration, motion during cooldown period, multiple overlapping motion bursts.

### [SIMPLE] ✅ Create README documentation
- **File**: `README.md`
- **Description**: Document: project overview, build instructions (`make`, `make test`, `make clean`), usage examples for each mode (TUI, headless test, automated), configuration file format for sensor profiles, test scenario script format, architecture diagram (ASCII), pin assignment table, known limitations (no PWM simulation, no EEPROM, no interrupts).