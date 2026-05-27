#include "tui.h"
#include "mock_arduino.h"
#include "security_cam.h"
#include "sim_engine.h"
#include "logger.h"
#include <ncurses.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <ctype.h>

/* Window geometry */
#define PIN_WIN_H      20
#define PIN_WIN_W      40
#define SERIAL_WIN_H   10
#define SERIAL_WIN_W   80
#define STATUS_WIN_H   3
#define STATUS_WIN_W   80
#define CTRL_WIN_H     8
#define CTRL_WIN_W     40

/* Module-level state */
static TuiState tui;
static unsigned long step_size_ms = 100;

/* Color pairs */
#define COLOR_PAIR_GREEN  1
#define COLOR_PAIR_RED    2
#define COLOR_PAIR_YELLOW 3
#define COLOR_PAIR_CYAN   4
#define COLOR_PAIR_WHITE  5

static const char *pin_mode_str(uint8_t mode) {
    switch (mode) {
    case INPUT:       return "IN ";
    case OUTPUT:      return "OUT";
    case INPUT_PULLUP: return "PU ";
    default:          return "???";
    }
}

void tui_init(void) {
    initscr();
    cbreak();
    noecho();
    keypad(stdscr, TRUE);
    nodelay(stdscr, TRUE);
    curs_set(0);

    if (has_colors()) {
        start_color();
        init_pair(COLOR_PAIR_GREEN,  COLOR_GREEN,  COLOR_BLACK);
        init_pair(COLOR_PAIR_RED,    COLOR_RED,    COLOR_BLACK);
        init_pair(COLOR_PAIR_YELLOW, COLOR_YELLOW, COLOR_BLACK);
        init_pair(COLOR_PAIR_CYAN,   COLOR_CYAN,   COLOR_BLACK);
        init_pair(COLOR_PAIR_WHITE,  COLOR_WHITE,  COLOR_BLACK);
    }

    int max_y, max_x;
    getmaxyx(stdscr, max_y, max_x);

    int pin_x = 0;
    int pin_y = 0;
    int ser_x = PIN_WIN_W + 1;
    int ser_y = 0;
    int stat_x = 0;
    int stat_y = PIN_WIN_H + 1;
    int ctrl_x = SERIAL_WIN_W - CTRL_WIN_W;
    int ctrl_y = PIN_WIN_H + 1;

    /* Clamp to terminal size */
    if (ser_x + SERIAL_WIN_W > max_x) ser_x = max_x - SERIAL_WIN_W;
    if (stat_y + STATUS_WIN_H > max_y) stat_y = max_y - STATUS_WIN_H;
    if (ctrl_y + CTRL_WIN_H > max_y) ctrl_y = max_y - CTRL_WIN_H;

    tui.pin_window     = newwin(PIN_WIN_H,     PIN_WIN_W,     pin_y,  pin_x);
    tui.serial_window  = newwin(SERIAL_WIN_H,  SERIAL_WIN_W,  ser_y,  ser_x);
    tui.status_window  = newwin(STATUS_WIN_H,  STATUS_WIN_W,  stat_y, stat_x);
    tui.control_window = newwin(CTRL_WIN_H,     CTRL_WIN_W,    ctrl_y, ctrl_x);

    tui.selected_pin = 0;
    tui.running = 0;
}

void tui_draw_pins(void) {
    werase(tui.pin_window);
    box(tui.pin_window, 0, 0);

    wattron(tui.pin_window, A_BOLD);
    mvwprintw(tui.pin_window, 1, 1, "  Pin  Mode  State  Analog");
    wattroff(tui.pin_window, A_BOLD);
    mvwhline(tui.pin_window, 2, 1, ACS_HLINE, PIN_WIN_W - 2);

    for (uint8_t i = 0; i < MAX_PINS; i++) {
        int row = 3 + i;
        if (row >= PIN_WIN_H - 1) break;

        uint8_t mode = mock_get_pin_mode(i);
        uint8_t state = mock_get_digital_state(i);

        /* Highlight selected pin */
        if (i == tui.selected_pin) {
            wattron(tui.pin_window, A_REVERSE);
        }

        /* Pin number and mode */
        mvwprintw(tui.pin_window, row, 1, "  %-4u %s ", i, pin_mode_str(mode));

        /* State with color coding */
        if (mode == OUTPUT) {
            if (state == HIGH) {
                wattron(tui.pin_window, COLOR_PAIR(COLOR_PAIR_GREEN));
                wprintw(tui.pin_window, " HIGH ");
                wattroff(tui.pin_window, COLOR_PAIR(COLOR_PAIR_GREEN));
            } else {
                wattron(tui.pin_window, COLOR_PAIR(COLOR_PAIR_RED));
                wprintw(tui.pin_window, " LOW  ");
                wattroff(tui.pin_window, COLOR_PAIR(COLOR_PAIR_RED));
            }
        } else if (mode == INPUT || mode == INPUT_PULLUP) {
            wattron(tui.pin_window, COLOR_PAIR(COLOR_PAIR_YELLOW));
            wprintw(tui.pin_window, " %s ", state == HIGH ? "HIGH" : "LOW ");
            wattroff(tui.pin_window, COLOR_PAIR(COLOR_PAIR_YELLOW));
        } else {
            wprintw(tui.pin_window, "  ---  ");
        }

        /* Analog value for analog-capable pins */
        if (i < MAX_ANALOG_PINS) {
            wprintw(tui.pin_window, " %4d", analogRead(i));
        }

        if (i == tui.selected_pin) {
            wattroff(tui.pin_window, A_REVERSE);
        }
    }

    wrefresh(tui.pin_window);
}

void tui_draw_serial(void) {
    werase(tui.serial_window);
    box(tui.serial_window, 0, 0);

    wattron(tui.serial_window, A_BOLD);
    mvwprintw(tui.serial_window, 1, 1, " Serial Output ");
    wattroff(tui.serial_window, A_BOLD);
    mvwhline(tui.serial_window, 2, 1, ACS_HLINE, SERIAL_WIN_W - 2);

    const char *tx = mock_get_serial_tx_buffer();
    int tx_len = mock_get_serial_tx_length();

    /* Build a scrolled view: show last (SERIAL_WIN_H - 4) lines */
    int max_lines = SERIAL_WIN_H - 4;
    int max_cols = SERIAL_WIN_W - 3;
    int line_count = 0;
    int line_starts[SERIAL_WIN_H];
    line_starts[0] = 0;

    /* Count lines in buffer */
    for (int i = 0; i < tx_len && line_count < max_lines + 100; i++) {
        if (tx[i] == '\n') {
            line_count++;
            if (line_count < SERIAL_WIN_H)
                line_starts[line_count] = i + 1;
        }
    }

    /* Display last max_lines lines */
    int start_line = line_count > max_lines ? line_count - max_lines : 0;
    int disp_row = 3;

    for (int ln = start_line; ln < line_count && disp_row < SERIAL_WIN_H - 1; ln++) {
        int start = line_starts[ln];
        int end = start;
        while (end < tx_len && tx[end] != '\n') end++;

        int len = end - start;
        if (len > max_cols) len = max_cols;

        wmove(tui.serial_window, disp_row, 1);
        for (int j = 0; j < len; j++) {
            waddch(tui.serial_window, (unsigned char)tx[start + j]);
        }
        disp_row++;
    }

    wrefresh(tui.serial_window);
}

void tui_draw_status(void) {
    werase(tui.status_window);
    box(tui.status_window, 0, 0);

    wattron(tui.status_window, A_BOLD | COLOR_PAIR(COLOR_PAIR_CYAN));
    mvwprintw(tui.status_window, 1, 1, " %s | Step: %lums | %s ",
              security_cam_get_status_string(),
              step_size_ms,
              tui.running ? "RUNNING" : "PAUSED");
    wattroff(tui.status_window, A_BOLD | COLOR_PAIR(COLOR_PAIR_CYAN));

    wrefresh(tui.status_window);
}

int tui_handle_input(void) {
    int ch = getch();
    if (ch == ERR) return 0;

    switch (ch) {
    case KEY_QUIT:
        return -1;

    case KEY_TOGGLE_PIN: {
        uint8_t pin = tui.selected_pin;
        uint8_t mode = mock_get_pin_mode(pin);
        if (mode == INPUT || mode == INPUT_PULLUP) {
            uint8_t cur = mock_get_digital_state(pin);
            digitalWrite(pin, cur == HIGH ? LOW : HIGH);
        }
        break;
    }

    case KEY_INJECT_ANALOG: {
        /* Prompt for analog value */
        echo();
        nodelay(stdscr, FALSE);
        curs_set(1);

        mvwprintw(tui.status_window, 1, STATUS_WIN_W - 25, "Analog val (0-1023): ");
        wrefresh(tui.status_window);

        char buf[8] = {0};
        wgetnstr(tui.status_window, buf, 5);
        int val = atoi(buf);
        if (val < 0) val = 0;
        if (val > 1023) val = 1023;

        /* Apply to current pin if it's an analog-capable pin */
        if (tui.selected_pin < MAX_ANALOG_PINS) {
            analogWrite(tui.selected_pin, val);
        }

        noecho();
        nodelay(stdscr, TRUE);
        curs_set(0);
        break;
    }

    case KEY_STEP_TIME:
        delay(step_size_ms);
        break;

    case KEY_RUN_CONTINUOUS:
        tui.running = 1;
        break;

    case KEY_PAUSE:
        tui.running = 0;
        break;

    case KEY_SAVE_LOG:
        /* Handled externally by main */
        break;

    case KEY_LOAD_LOG:
        /* Handled externally by main */
        break;

    case KEY_PROFILE_SELECT_1:
    case KEY_PROFILE_SELECT_2:
    case KEY_PROFILE_SELECT_3:
    case KEY_PROFILE_SELECT_4:
        /* Handled externally by main */
        break;

    case KEY_UP:
        if (tui.selected_pin > 0) tui.selected_pin--;
        break;

    case KEY_DOWN:
        if (tui.selected_pin < MAX_PINS - 1) tui.selected_pin++;
        break;

    case '+':
    case '=':
        step_size_ms += 10;
        if (step_size_ms > 5000) step_size_ms = 5000;
        break;

    case '-':
        if (step_size_ms >= 10) step_size_ms -= 10;
        if (step_size_ms < 10) step_size_ms = 10;
        break;
    }

    return 0;
}

void tui_update(void) {
    tui_draw_pins();
    tui_draw_serial();
    tui_draw_status();

    /* Draw control panel */
    werase(tui.control_window);
    box(tui.control_window, 0, 0);

    wattron(tui.control_window, A_BOLD);
    mvwprintw(tui.control_window, 1, 1, " Controls ");
    wattroff(tui.control_window, A_BOLD);
    mvwhline(tui.control_window, 2, 1, ACS_HLINE, CTRL_WIN_W - 2);

    mvwprintw(tui.control_window, 3, 1, " q:Quit  t:Toggle  a:Analog");
    mvwprintw(tui.control_window, 4, 1, " n:Step  r:Run     p:Pause ");
    mvwprintw(tui.control_window, 5, 1, " +/-:Step size  Arrows:Pin");
    mvwprintw(tui.control_window, 6, 1, " Pin:%u  Step:%lums",
              tui.selected_pin, step_size_ms);

    wrefresh(tui.control_window);

    refresh();
}

void tui_cleanup(void) {
    if (tui.pin_window)     delwin(tui.pin_window);
    if (tui.serial_window)  delwin(tui.serial_window);
    if (tui.status_window)  delwin(tui.status_window);
    if (tui.control_window) delwin(tui.control_window);

    memset(&tui, 0, sizeof(tui));
    endwin();
}
