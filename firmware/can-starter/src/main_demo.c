/**
 * @file    main_demo.c
 * @brief   SocketCAN 위에서 스피커 노드를 실제로 돌린다.
 *
 *   make demo && ./build/demo
 *   cansend vcan0 120#0346      # sound_id=3, volume=70
 *   candump vcan0
 */

#include <stdio.h>
#include <time.h>

#include "app_speaker.h"
#include "can_if.h"

static can_if_ctx_t  s_if;
static app_speaker_t s_app;

static void sleep_1ms(void)
{
    struct timespec ts = { 0, 1000000L };
    (void)nanosleep(&ts, NULL);
}

int main(void)
{
    const can_hal_cfg_t cfg = { 500000U, 87U, false };
    uint32_t            tick = 0U;

    if (can_if_init(&s_if, &cfg) != CAN_IF_OK)
    {
        (void)fprintf(stderr,
            "CAN 인터페이스를 열 수 없습니다. vcan0 가 올라와 있는지 확인하세요:\n"
            "  sudo modprobe vcan && sudo ip link add dev vcan0 type vcan\n"
            "  sudo ip link set up vcan0\n");
        return 1;
    }

    if (app_speaker_init(&s_app, &s_if) != CAN_IF_OK)
    {
        (void)fprintf(stderr, "앱 초기화 실패\n");
        return 1;
    }

    (void)printf("스피커 노드 시작 — 명령 0x%03X 수신, 상태 0x%03X 송신 (100 ms)\n",
                 SPEAKER_CMD_ID, SPEAKER_STATUS_ID);

    for (;;)
    {
        uint32_t now = can_hal_now_ms();

        (void)can_if_tick_1ms(&s_if, now);

        if ((tick % 100U) == 0U)
        {
            app_speaker_tick_100ms(&s_app);
        }

        if ((tick % 1000U) == 0U)
        {
            can_if_stats_t st;
            (void)can_if_get_stats(&s_if, &st);
            (void)printf("t=%6u ms  state=%u fault=%u sound=%u vol=%u  "
                         "rx=%u tx=%u drop=%u timeout=%u\n",
                         now, (unsigned)s_app.state, (unsigned)s_app.fault,
                         s_app.cur_sound, s_app.cur_volume,
                         st.rx_frames, st.tx_frames, st.rx_dropped, st.timeouts);
        }

        tick++;
        sleep_1ms();
    }
}
