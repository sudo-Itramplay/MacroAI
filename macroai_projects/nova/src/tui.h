#ifndef TUI_H
#define TUI_H

#include <stdint.h>
#include <ncurses.h>

#define KEY_QUIT 'q'
#define KEY_TOGGLE_PIN 't'
#define KEY_INJECT_ANALOG 'a'
#define KEY_STEP_TIME 'n'
#define KEY_RUN_CONTINUOUS 'r'
#define KEY_PAUSE 'p'
#define KEY_SAVE_LOG 's'
#define KEY_LOAD_LOG 'l'
#define KEY_PROFILE_SELECT_1 '1'
#define KEY_PROFILE_SELECT_2 '2'
#define KEY_PROFILE_SELECT_3 '3'
#define KEY_PROFILE_SELECT_4 '4'

typedef struct {
    WINDOW *pin_window;
    WINDOW *serial_window;
    WINDOW *status_window;
    WINDOW *control_window;
    uint8_t selected_pin;
    uint8_t running;
} TuiState;

void tui_init(void);
void tui_draw_pins(void);
void tui_draw_serial(void);
void tui_draw_status(void);
int tui_handle_input(void);
void tui_update(void);
void tui_cleanup(void);

#endif
