/**
 * @file    test_main.c
 * @brief   호스트 단위시험. 하드웨어 없이 전 계층을 검증한다.
 *
 * 프레임워크 의존을 피하려고 최소 하니스만 둔다. 실제 프로젝트에서는
 * Unity + CMock (Ceedling) 으로 대체한다 (STD-FW-001 FW-TST-003).
 */

#include <stdio.h>
#include <string.h>

#include "app_speaker.h"
#include "can_if.h"
#include "can_signal.h"
#include "port_loopback.h"

static int s_checks;
static int s_failures;
static const char *s_case;

#define CASE(name)  do { s_case = (name); } while (0)

#define CHECK(cond) do {                                                   \
        s_checks++;                                                        \
        if (!(cond)) {                                                     \
            s_failures++;                                                  \
            (void)printf("  FAIL  %-38s  %s:%d  %s\n",                     \
                         s_case, __FILE__, __LINE__, #cond);               \
        }                                                                  \
    } while (0)

#define CHECK_EQ_U(actual, expect) do {                                    \
        unsigned long a_ = (unsigned long)(actual);                        \
        unsigned long e_ = (unsigned long)(expect);                        \
        s_checks++;                                                        \
        if (a_ != e_) {                                                    \
            s_failures++;                                                  \
            (void)printf("  FAIL  %-38s  %s:%d  %s: 0x%lX != 0x%lX\n",     \
                         s_case, __FILE__, __LINE__, #actual, a_, e_);     \
        }                                                                  \
    } while (0)

/* ---- 신호 계층 ---------------------------------------------------------- */

static void test_signal_intel(void)
{
    const can_signal_def_t def =
        { 8U, 16U, CAN_SIGNAL_INTEL, false, 1.0, 0.0, 0.0, 65535.0 };
    uint8_t data[8] = { 0x00U, 0x34U, 0x12U, 0U, 0U, 0U, 0U, 0U };
    uint8_t out[8];

    CASE("Intel 16비트 디코딩");
    CHECK_EQ_U(can_signal_get_raw(data, 8U, &def), 0x1234U);

    CASE("Intel 인코딩 왕복");
    (void)memset(out, 0, sizeof(out));
    CHECK(can_signal_set_raw(out, 8U, &def, 0x1234U));
    CHECK_EQ_U(out[1], 0x34U);
    CHECK_EQ_U(out[2], 0x12U);
    CHECK_EQ_U(can_signal_get_raw(out, 8U, &def), 0x1234U);
}

static void test_signal_motorola(void)
{
    const can_signal_def_t def =
        { 7U, 16U, CAN_SIGNAL_MOTOROLA, false, 1.0, 0.0, 0.0, 65535.0 };
    uint8_t data[8] = { 0x12U, 0x34U, 0U, 0U, 0U, 0U, 0U, 0U };
    uint8_t out[8];

    CASE("Motorola 16비트 디코딩");
    CHECK_EQ_U(can_signal_get_raw(data, 8U, &def), 0x1234U);

    CASE("Motorola 인코딩 왕복");
    (void)memset(out, 0, sizeof(out));
    CHECK(can_signal_set_raw(out, 8U, &def, 0xABCDU));
    CHECK_EQ_U(out[0], 0xABU);
    CHECK_EQ_U(out[1], 0xCDU);
    CHECK_EQ_U(can_signal_get_raw(out, 8U, &def), 0xABCDU);
}

static void test_signal_roundtrip_all_positions(void)
{
    uint8_t start;

    CASE("Intel 모든 시작 위치 왕복");
    for (start = 0U; start <= 52U; start++)
    {
        const can_signal_def_t def =
            { start, 12U, CAN_SIGNAL_INTEL, false, 1.0, 0.0, 0.0, 4095.0 };
        uint8_t buf[8];

        (void)memset(buf, 0xFFU, sizeof(buf));   /* 주변 비트 오염 확인 */
        CHECK(can_signal_set_raw(buf, 8U, &def, 0x5A5U));
        CHECK_EQ_U(can_signal_get_raw(buf, 8U, &def), 0x5A5U);
    }
}

static void test_signal_physical(void)
{
    /* 온도: 8비트, factor 1, offset -40 → -40 ~ 215 °C */
    const can_signal_def_t temp =
        { 24U, 8U, CAN_SIGNAL_INTEL, false, 1.0, -40.0, -40.0, 215.0 };
    /* 회전수: 16비트, factor 0.25 → 0 ~ 16383.75 rpm */
    const can_signal_def_t rpm =
        { 0U, 16U, CAN_SIGNAL_INTEL, false, 0.25, 0.0, 0.0, 16383.75 };
    uint8_t buf[8];

    CASE("오프셋 있는 물리값");
    (void)memset(buf, 0, sizeof(buf));
    CHECK(can_signal_set_phys(buf, 8U, &temp, -40.0));
    CHECK_EQ_U(buf[3], 0x00U);
    CHECK(can_signal_set_phys(buf, 8U, &temp, 25.0));
    CHECK_EQ_U(buf[3], 65U);
    CHECK(can_signal_get_phys(buf, 8U, &temp) == 25.0);

    CASE("스케일 있는 물리값");
    (void)memset(buf, 0, sizeof(buf));
    CHECK(can_signal_set_phys(buf, 8U, &rpm, 2000.0));
    CHECK_EQ_U(can_signal_get_raw(buf, 8U, &rpm), 8000U);
    CHECK(can_signal_get_phys(buf, 8U, &rpm) == 2000.0);

    CASE("범위를 넘는 값은 감싸지 않고 잘린다");
    (void)memset(buf, 0, sizeof(buf));
    CHECK(can_signal_set_phys(buf, 8U, &temp, 999.0));
    CHECK(can_signal_get_phys(buf, 8U, &temp) == 215.0);
    CHECK(can_signal_set_phys(buf, 8U, &temp, -999.0));
    CHECK(can_signal_get_phys(buf, 8U, &temp) == -40.0);
}

static void test_signal_signed(void)
{
    const can_signal_def_t def =
        { 0U, 12U, CAN_SIGNAL_INTEL, true, 0.1, 0.0, -204.8, 204.7 };
    uint8_t buf[8];
    double  got;

    CASE("부호 있는 신호");
    (void)memset(buf, 0, sizeof(buf));
    CHECK(can_signal_set_phys(buf, 8U, &def, -12.5));
    got = can_signal_get_phys(buf, 8U, &def);
    CHECK((got > -12.55) && (got < -12.45));
}

static void test_signal_out_of_frame(void)
{
    /* 8바이트 프레임에서 bit 60 부터 16비트는 프레임 밖이다. */
    const can_signal_def_t def =
        { 60U, 16U, CAN_SIGNAL_INTEL, false, 1.0, 0.0, 0.0, 65535.0 };
    uint8_t buf[8];

    CASE("프레임 밖 신호는 거부된다");
    (void)memset(buf, 0, sizeof(buf));
    CHECK(!can_signal_set_raw(buf, 8U, &def, 0xFFFFU));
    CHECK_EQ_U(buf[7], 0x00U);   /* 부분 기록이 남지 않는다 */
    CHECK_EQ_U(can_signal_get_raw(buf, 8U, &def), 0U);

    CASE("짧은 DLC 에서도 안전하다");
    CHECK_EQ_U(can_signal_get_raw(buf, 2U, &def), 0U);
}

/* ---- 인터페이스 계층 ---------------------------------------------------- */

static uint32_t s_rx_hits;
static uint32_t s_timeout_hits;

static void count_rx(const can_frame_t *p_frame, void *p_user)
{
    (void)p_frame; (void)p_user;
    s_rx_hits++;
}

static void count_timeout(uint32_t id, void *p_user)
{
    (void)id; (void)p_user;
    s_timeout_hits++;
}

static void run_ticks(can_if_ctx_t *p_if, uint32_t from_ms, uint32_t count)
{
    uint32_t t;

    for (t = 0U; t < count; t++)
    {
        (void)can_if_tick_1ms(p_if, from_ms + t);
    }
}

static can_if_ctx_t s_if;

static void setup_if(bool loopback)
{
    const can_hal_cfg_t cfg = { 500000U, 87U, loopback };

    loopback_reset();
    s_rx_hits      = 0U;
    s_timeout_hits = 0U;
    (void)can_if_init(&s_if, &cfg);
}

static void test_if_dispatch(void)
{
    can_frame_t f = { 0x120U, false, 2U, { 0x07U, 0x32U, 0U, 0U, 0U, 0U, 0U, 0U } };

    CASE("구독한 ID 만 콜백된다");
    setup_if(false);
    CHECK(can_if_subscribe(&s_if, 0x120U, 0U, count_rx, NULL, NULL) == CAN_IF_OK);
    CHECK(loopback_inject(&f));
    f.id = 0x200U;
    CHECK(loopback_inject(&f));
    run_ticks(&s_if, 0U, 3U);
    CHECK_EQ_U(s_rx_hits, 1U);

    CASE("중복 구독은 거부된다");
    CHECK(can_if_subscribe(&s_if, 0x120U, 0U, count_rx, NULL, NULL) == CAN_IF_ERR_PARAM);
}

static void test_if_timeout(void)
{
    can_frame_t f = { 0x120U, false, 2U, { 1U, 50U, 0U, 0U, 0U, 0U, 0U, 0U } };

    CASE("수신이 끊기면 타임아웃이 한 번 난다");
    setup_if(false);
    CHECK(can_if_subscribe(&s_if, 0x120U, 500U, count_rx, count_timeout, NULL) == CAN_IF_OK);

    CHECK(loopback_inject(&f));
    run_ticks(&s_if, 0U, 400U);
    CHECK_EQ_U(s_timeout_hits, 0U);

    run_ticks(&s_if, 400U, 300U);      /* 마지막 수신 후 500 ms 경과 */
    CHECK_EQ_U(s_timeout_hits, 1U);

    run_ticks(&s_if, 700U, 300U);      /* 반복 발화하지 않는다 */
    CHECK_EQ_U(s_timeout_hits, 1U);

    CASE("다시 수신되면 타임아웃이 해제된다");
    CHECK(loopback_inject(&f));
    run_ticks(&s_if, 1000U, 3U);
    run_ticks(&s_if, 1003U, 600U);
    CHECK_EQ_U(s_timeout_hits, 2U);
}

static void test_if_periodic_tx(void)
{
    uint8_t     handle = 0U;
    uint8_t     payload[8] = { 0xA1U, 0U, 0U, 0U, 0U, 0U, 0U, 0U };
    can_frame_t sent;
    uint32_t    count = 0U;

    CASE("주기 송신이 100 ms 마다 나간다");
    setup_if(false);
    CHECK(can_if_tx_register(&s_if, 0x121U, 8U, 100U, &handle) == CAN_IF_OK);
    CHECK(can_if_tx_update(&s_if, handle, payload, 8U) == CAN_IF_OK);

    run_ticks(&s_if, 0U, 1000U);       /* 0, 100, ... 900 → 10회 */
    while (loopback_pop_sent(&sent))
    {
        CHECK_EQ_U(sent.id, 0x121U);
        CHECK_EQ_U(sent.data[0], 0xA1U);
        count++;
    }
    CHECK_EQ_U(count, 10U);
}

static void test_if_queue_overflow(void)
{
    can_frame_t     f = { 0x300U, false, 1U, { 0U, 0U, 0U, 0U, 0U, 0U, 0U, 0U } };
    can_if_stats_t  stats;
    uint8_t         i;

    CASE("수신 큐가 넘치면 버린 수를 센다");
    setup_if(false);
    CHECK(can_if_subscribe(&s_if, 0x300U, 0U, count_rx, NULL, NULL) == CAN_IF_OK);

    /* HAL 큐(32) 를 채우고 1 틱만 돌린다. 틱당 8개만 꺼내므로 남는다. */
    for (i = 0U; i < 31U; i++)
    {
        f.data[0] = i;
        (void)loopback_inject(&f);
    }
    (void)can_if_tick_1ms(&s_if, 0U);

    CHECK(can_if_get_stats(&s_if, &stats) == CAN_IF_OK);
    CHECK_EQ_U(stats.rx_frames, 8U);
    CHECK_EQ_U(s_rx_hits, 8U);

    run_ticks(&s_if, 1U, 10U);
    CHECK(can_if_get_stats(&s_if, &stats) == CAN_IF_OK);
    CHECK_EQ_U(stats.rx_frames, 31U);
    CHECK_EQ_U(s_rx_hits, 31U);
}

static void test_if_bus_off_recovery(void)
{
    can_if_stats_t stats;

    CASE("Bus-Off 는 지연 후 복구를 시도한다");
    setup_if(false);
    loopback_set_bus_state(CAN_BUS_OFF);

    run_ticks(&s_if, 0U, 100U);
    CHECK_EQ_U(loopback_recover_count(), 0U);   /* 200 ms 전에는 시도하지 않는다 */

    run_ticks(&s_if, 100U, 150U);
    CHECK(loopback_recover_count() >= 1U);

    CHECK(can_if_get_stats(&s_if, &stats) == CAN_IF_OK);
    CHECK_EQ_U(stats.bus_off_events, 1U);
}

/* ---- 애플리케이션 계층 -------------------------------------------------- */

static uint8_t xor7(const uint8_t *p)
{
    uint8_t s = 0U;
    uint8_t i;
    for (i = 0U; i < 7U; i++) { s ^= p[i]; }
    return s;
}

static void test_app_speaker(void)
{
    app_speaker_t app;
    can_frame_t   cmd = { SPEAKER_CMD_ID, false, 2U, { 3U, 70U, 0U, 0U, 0U, 0U, 0U, 0U } };
    can_frame_t   sent;
    bool          found = false;

    CASE("명령을 받으면 상태 프레임에 반영된다");
    setup_if(false);
    CHECK(app_speaker_init(&app, &s_if) == CAN_IF_OK);
    app_speaker_set_temperature(&app, 55);
    app_speaker_set_fault(&app, SPEAKER_FAULT_OPEN);

    CHECK(loopback_inject(&cmd));
    run_ticks(&s_if, 0U, 3U);
    CHECK_EQ_U(app.cur_sound, 3U);
    CHECK_EQ_U(app.cur_volume, 70U);
    CHECK_EQ_U(app.state, (uint32_t)SPEAKER_STATE_PLAYING);

    app_speaker_tick_100ms(&app);
    run_ticks(&s_if, 3U, 200U);

    while (loopback_pop_sent(&sent))
    {
        if (sent.id != SPEAKER_STATUS_ID) { continue; }
        found = true;
        CHECK_EQ_U(sent.data[0] & 0x07U, (uint32_t)SPEAKER_STATE_PLAYING);
        CHECK_EQ_U((sent.data[0] >> 3) & 0x03U, (uint32_t)SPEAKER_FAULT_OPEN);
        CHECK_EQ_U(sent.data[1], 3U);
        CHECK_EQ_U(sent.data[2] & 0x7FU, 70U);
        CHECK_EQ_U(sent.data[3], 95U);            /* 55 °C, offset -40 */
        CHECK_EQ_U(sent.data[7], xor7(sent.data)); /* 체크섬 */
    }
    CHECK(found);

    CASE("명령이 끊기면 안전 상태로 간다");
    run_ticks(&s_if, 203U, 600U);
    CHECK_EQ_U(app.state, (uint32_t)SPEAKER_STATE_SAFE);
    CHECK_EQ_U(app.cur_volume, 0U);
}

/* ---- 진입점 ------------------------------------------------------------- */

int main(void)
{
    (void)printf("CAN 스타터 단위시험\n");
    (void)printf("--------------------------------------------------\n");

    test_signal_intel();
    test_signal_motorola();
    test_signal_roundtrip_all_positions();
    test_signal_physical();
    test_signal_signed();
    test_signal_out_of_frame();

    test_if_dispatch();
    test_if_timeout();
    test_if_periodic_tx();
    test_if_queue_overflow();
    test_if_bus_off_recovery();

    test_app_speaker();

    (void)printf("--------------------------------------------------\n");
    (void)printf("검사 %d건, 실패 %d건 → %s\n",
                 s_checks, s_failures, (s_failures == 0) ? "PASS" : "FAIL");

    return (s_failures == 0) ? 0 : 1;
}
