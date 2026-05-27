CC=gcc
CFLAGS=-std=c11 -Wall -Wextra -pedantic -D_POSIX_C_SOURCE=200809L
LDFLAGS=-lncurses
SRC_DIR=src
OBJ_DIR=obj
TARGET=macroai_sim

SRCS=$(wildcard $(SRC_DIR)/*.c)
OBJS=$(patsubst $(SRC_DIR)/%.c,$(OBJ_DIR)/%.o,$(SRCS))
DEPS=$(OBJS:.o=.d)

.PHONY: all clean test install debug

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

$(OBJ_DIR)/%.o: $(SRC_DIR)/%.c | $(OBJ_DIR)
	$(CC) $(CFLAGS) -MMD -MP -c -o $@ $<

$(OBJ_DIR):
	mkdir -p $(OBJ_DIR)

clean:
	rm -rf $(OBJ_DIR) $(TARGET)

test: CFLAGS += -DTEST_MODE
test: $(TARGET)
	./$(TARGET) -h

install: $(TARGET)
	cp $(TARGET) /usr/local/bin/

debug: CFLAGS += -g -O0
debug: $(TARGET)

-include $(DEPS)
