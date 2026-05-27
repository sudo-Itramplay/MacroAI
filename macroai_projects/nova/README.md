# arduino-security-sim

A simulated security camera system built on a mock Arduino HAL. Develop and test Arduino-style security camera logic on a Linux desktop without any hardware.

## Build

```
make              # build the macroai_sim binary
make test         # run headless test mode (runs scenario from -f)
make clean        # remove build artifacts
make debug        # build with -g -O0 for debugging
make install      # copy binary to /usr/local/bin/
```

Requires `gcc` and `ncurses` (`libncurses-dev` on Debian/Ubuntu).

## Usage

### TUI mode (default)

```
./macroai_sim
./macroai_sim -t -l session.log -v
```

Interactive ncurses interface with pin display, serial output, status panel, and keyboard controls:

| Key | Action |
|-----|--------|
| `q` | Quit |
| `n` | Step time forward (50 ms) |
| `r` | Toggle continuous run |
| `p` | Pause |
| `1` | Load constant motion profile |
| `2` | Load burst motion profile |
| `3` | Load noisy profile |
| `4` | Load edge case profile |
| `s` | Save log to file |
| `l` | Load log from file |

### Headless test mode

```
./macroai_sim -h -f tests/scenarios/basic_motion.txt
./macroai_sim -h -f tests/scenarios/edge_cases.txt -v
```

Executes a scenario script without TUI. Serial output is printed to stdout. Exit code is 0 on pass, 1 on fail.

### Unit tests (dedicated binaries)

```
make test_mock_arduino  # compile and run HAL tests
make test_security_cam  # compile and run camera logic tests
```

## Pin Assignment

| Pin | Function | Type |
|-----|----------|------|
| 2 | PIR motion sensor | Input |
| 3 | Buzzer | Output |
| 4 | Green LED (idle) | Output |
| 5 | Red LED (alarm) | Output |
| 6 | Camera trigger | Output |

Pins 0-1 are reserved for serial (not simulated). Pins 7-19 are general-purpose digital I/O. Analog pins 0-5 support `analogRead` (0-1023).

## Camera State Machine

```
IDLE → MOTION_DETECTED → ALARM_ACTIVE → RECORDING → COOLDOWN → IDLE
```

- **IDLE**: Green LED on. Waiting for motion.
- **MOTION_DETECTED**: PIR went high. Debouncing (counts N readings based on sensitivity).
- **ALARM_ACTIVE**: Buzzer and red LED on. Camera trigger HIGH.
- **RECORDING**: Alarm stops. Recording for `recording_duration_ms`.
- **COOLDOWN**: Waiting before returning to IDLE. New motion resets the cooldown timer.

## Test Scenario Script Format

Simple text format, one command per line:

```
SET_PIN <pin> <HIGH|LOW>    Set digital pin state
SET_ANALOG <pin> <value>    Set analog value (0-1023)
WAIT <ms>                   Advance simulation time
ASSERT_PIN <pin> <HIGH|LOW> Assert pin state (fails if mismatch)
ASSERT_SERIAL "<text>"      Assert serial buffer contains text
LOG <message>               Print message during execution
REPEAT <count>              Repeat last block N times
```

Example (`tests/scenarios/basic_motion.txt`):

```
SET_PIN 2 LOW
WAIT 500
SET_PIN 2 HIGH
WAIT 100
ASSERT_PIN 3 HIGH
ASSERT_PIN 5 HIGH
WAIT 5000
ASSERT_PIN 3 LOW
WAIT 2000
ASSERT_PIN 4 HIGH
```

## Sensor Profile Configuration (CSV)

Sensor profiles can be loaded from a CSV file with the format:

```
time_ms,pin,value
0,2,1
200,2,0
400,2,1
...
```

Each row schedules a digital write event at `time_ms` on `pin` with `value` (0=LOW, 1=HIGH). Load via the `-f` flag during headless test or via the TUI profile keys.

## Log File Format (CSV)

Logs are written as CSV:

```
timestamp,type,message
0,0,PIN_CHANGE pin=2 val=1
100,2,STATE_CHANGE CAM_MOTION_DETECTED
```

Entry types: 0=PIN_CHANGE, 1=SERIAL_OUTPUT, 2=STATE_CHANGE, 3=SENSOR_EVENT.

## Architecture

```
┌──────────────────────────────────────────────────┐
│                    main.c                         │
│  Mode dispatch: TUI / headless / test            │
├──────────────────────────────────────────────────┤
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  │
│  │   tui.c    │  │test_harness│  │  logger.c  │  │
│  │  ncurses   │  │  .c        │  │ CSV I/O    │  │
│  │ interface  │  │ script exe │  │ record/play│  │
│  └────────────┘  └────────────┘  └────────────┘  │
├──────────────────────────────────────────────────┤
│  ┌────────────┐  ┌────────────┐                  │
│  │security_cam│  │sensor_prof │                  │
│  │  .c        │  │  iles.c    │                  │
│  │ state mach │  │ generators  │                  │
│  └────────────┘  └────────────┘                  │
├──────────────────────────────────────────────────┤
│  ┌────────────┐  ┌────────────┐                  │
│  │ sim_engine │  │mock_arduino│                  │
│  │  .c        │  │  .c        │                  │
│  │ event queue│  │ pin state, │                  │
│  │ time step  │  │ serial buf │                  │
│  └────────────┘  └────────────┘                  │
└──────────────────────────────────────────────────┘
```

Layered design: the mock HAL abstracts hardware access, the simulation engine drives time, the camera state machine implements business logic, and the TUI/test harness provide two interfaces to the same system.

## Known Limitations

- **No PWM simulation**: `analogWrite` stores a value but no PWM waveform is generated.
- **No EEPROM**: `EEPROM.read/write` are not implemented.
- **No interrupts**: `attachInterrupt/detachInterrupt` are not supported.
- **No true analog input**: `analogRead` returns values set programmatically, not from a real ADC.
- **Single-threaded**: All simulation runs in one thread; no concurrent I/O.
- **No AVR instruction emulation**: This is a functional mock, not a cycle-accurate simulator.
