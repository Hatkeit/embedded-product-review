# CAN 스타터 — 호스트 빌드
#
#   make test    단위시험 실행
#   make clean

CC      ?= gcc
CFLAGS  := -std=c99 -O1 -g \
           -Wall -Wextra -Werror -Wconversion -Wshadow -Wundef \
           -Iinclude -Iport
LDLIBS  := -lm

SRC := src/can_signal.c src/can_if.c src/app_speaker.c port/port_loopback.c
BIN := build/run_tests

.PHONY: all test clean
all: $(BIN)

$(BIN): $(SRC) test/test_main.c
	@mkdir -p build
	$(CC) $(CFLAGS) $^ -o $@ $(LDLIBS)

test: $(BIN)
	@./$(BIN)

clean:
	@rm -rf build

# --- 2단계: 진짜 CAN 버스 (리눅스 SocketCAN) ---------------------------------
DEMO_SRC := src/can_signal.c src/can_if.c src/app_speaker.c \
            port/port_socketcan.c src/main_demo.c

.PHONY: demo
demo: build/demo

# 포트 계층만 POSIX 를 쓴다. 시험 빌드는 순수 ISO C99 로 유지한다.
build/demo: $(DEMO_SRC)
	@mkdir -p build
	$(CC) $(CFLAGS) -D_DEFAULT_SOURCE $^ -o $@ $(LDLIBS)
