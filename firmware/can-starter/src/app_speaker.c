/**
 * @file    app_speaker.c
 * @brief   CAN 스피커 노드 애플리케이션 구현.
 */

#include <stddef.h>
#include <string.h>

#include "app_speaker.h"
#include "can_signal.h"

/* --- 신호 정의. DBC 한 줄씩에 대응한다. --- */
static const can_signal_def_t SIG_CMD_SOUND_ID =
    { 0U,  8U, CAN_SIGNAL_INTEL, false, 1.0, 0.0,   0.0, 255.0 };
static const can_signal_def_t SIG_CMD_VOLUME =
    { 8U,  7U, CAN_SIGNAL_INTEL, false, 1.0, 0.0,   0.0, 100.0 };

static const can_signal_def_t SIG_ST_STATE =
    { 0U,  3U, CAN_SIGNAL_INTEL, false, 1.0, 0.0,   0.0,   7.0 };
static const can_signal_def_t SIG_ST_FAULT =
    { 3U,  2U, CAN_SIGNAL_INTEL, false, 1.0, 0.0,   0.0,   3.0 };
static const can_signal_def_t SIG_ST_SOUND =
    { 8U,  8U, CAN_SIGNAL_INTEL, false, 1.0, 0.0,   0.0, 255.0 };
static const can_signal_def_t SIG_ST_VOLUME =
    { 16U, 7U, CAN_SIGNAL_INTEL, false, 1.0, 0.0,   0.0, 100.0 };
static const can_signal_def_t SIG_ST_TEMP =
    { 24U, 8U, CAN_SIGNAL_INTEL, false, 1.0, -40.0, -40.0, 215.0 };
static const can_signal_def_t SIG_ST_COUNTER =
    { 48U, 4U, CAN_SIGNAL_INTEL, false, 1.0, 0.0,   0.0,  15.0 };
static const can_signal_def_t SIG_ST_CHECKSUM =
    { 56U, 8U, CAN_SIGNAL_INTEL, false, 1.0, 0.0,   0.0, 255.0 };

/** 바이트 0..6 XOR. 수신 측이 프레임 손상과 정지 신호를 구분하게 해 준다. */
static uint8_t status_checksum(const uint8_t *p_data)
{
    uint8_t sum = 0U;
    uint8_t i;

    for (i = 0U; i < 7U; i++)
    {
        sum ^= p_data[i];
    }

    return sum;
}

static void on_cmd(const can_frame_t *p_frame, void *p_user)
{
    app_speaker_t *p_app = (app_speaker_t *)p_user;
    uint8_t        sound;
    uint8_t        volume;

    if ((p_frame == NULL) || (p_app == NULL) || (p_frame->dlc < 2U))
    {
        return;
    }

    sound  = (uint8_t)can_signal_get_raw(p_frame->data, p_frame->dlc, &SIG_CMD_SOUND_ID);
    volume = (uint8_t)can_signal_get_raw(p_frame->data, p_frame->dlc, &SIG_CMD_VOLUME);

    /* 수신값은 항상 범위 검증 후 사용한다 (STD-FW-001 FW-COM-006). */
    if (volume > 100U)
    {
        volume = 100U;
    }

    p_app->cur_sound  = sound;
    p_app->cur_volume = volume;
    p_app->state      = (sound == 0U) ? SPEAKER_STATE_IDLE : SPEAKER_STATE_PLAYING;
}

static void on_cmd_timeout(uint32_t id, void *p_user)
{
    app_speaker_t *p_app = (app_speaker_t *)p_user;

    (void)id;

    if (p_app == NULL)
    {
        return;
    }

    /* 명령이 끊기면 계속 울리지 않고 안전 상태로 간다.
       경보 장치에서 "마지막 명령 유지"는 사고를 만든다. */
    p_app->state      = SPEAKER_STATE_SAFE;
    p_app->cur_sound  = 0U;
    p_app->cur_volume = 0U;
}

can_if_status_t app_speaker_init(app_speaker_t *p_app, can_if_ctx_t *p_if)
{
    can_if_status_t st;

    if ((p_app == NULL) || (p_if == NULL))
    {
        return CAN_IF_ERR_PARAM;
    }

    (void)memset(p_app, 0, sizeof(*p_app));
    p_app->p_if   = p_if;
    p_app->state  = SPEAKER_STATE_IDLE;
    p_app->fault  = SPEAKER_FAULT_NONE;
    p_app->temp_c = 25;

    st = can_if_subscribe(p_if, SPEAKER_CMD_ID, SPEAKER_CMD_TIMEOUT_MS,
                          on_cmd, on_cmd_timeout, p_app);
    if (st != CAN_IF_OK)
    {
        return st;
    }

    st = can_if_tx_register(p_if, SPEAKER_STATUS_ID, 8U,
                            SPEAKER_STATUS_PERIOD_MS, &p_app->tx_handle);
    if (st != CAN_IF_OK)
    {
        return st;
    }

    p_app->initialized = true;
    return CAN_IF_OK;
}

void app_speaker_tick_100ms(app_speaker_t *p_app)
{
    uint8_t data[CAN_HAL_MAX_DLC];

    if ((p_app == NULL) || !p_app->initialized)
    {
        return;
    }

    (void)memset(data, 0, sizeof(data));

    (void)can_signal_set_raw(data, 8U, &SIG_ST_STATE,  (uint32_t)p_app->state);
    (void)can_signal_set_raw(data, 8U, &SIG_ST_FAULT,  (uint32_t)p_app->fault);
    (void)can_signal_set_raw(data, 8U, &SIG_ST_SOUND,  p_app->cur_sound);
    (void)can_signal_set_raw(data, 8U, &SIG_ST_VOLUME, p_app->cur_volume);
    (void)can_signal_set_phys(data, 8U, &SIG_ST_TEMP,  (double)p_app->temp_c);

    p_app->counter = (uint8_t)((p_app->counter + 1U) & 0x0FU);
    (void)can_signal_set_raw(data, 8U, &SIG_ST_COUNTER, p_app->counter);

    /* 체크섬은 나머지 필드를 모두 채운 뒤 마지막에 계산한다. */
    (void)can_signal_set_raw(data, 8U, &SIG_ST_CHECKSUM, status_checksum(data));

    (void)can_if_tx_update(p_app->p_if, p_app->tx_handle, data, 8U);
}

void app_speaker_set_fault(app_speaker_t *p_app, speaker_fault_t fault)
{
    if (p_app != NULL)
    {
        p_app->fault = fault;
    }
}

void app_speaker_set_temperature(app_speaker_t *p_app, int16_t temp_c)
{
    if (p_app != NULL)
    {
        p_app->temp_c = temp_c;
    }
}
