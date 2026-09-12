/**
 * @file    app_speaker.h
 * @brief   CAN 스피커 노드 애플리케이션.
 *
 * STD-FW-001 의 app/ 계층. MCU · 레지스터 · RTOS 를 전혀 모른다.
 * 따라서 호스트에서 그대로 단위시험할 수 있다.
 *
 * 통신 규격 (실무에서는 DBC 가 원본이고 이 파일은 생성물이 된다)
 *   0x120 SPEAKER_CMD     수신, 100 ms 주기, 타임아웃 500 ms
 *     sound_id   bit  0, 8비트
 *     volume     bit  8, 7비트, 0..100 %
 *     repeat     bit 15, 1비트
 *   0x121 SPEAKER_STATUS  송신, 100 ms 주기
 *     state      bit  0, 3비트
 *     fault      bit  3, 2비트
 *     cur_sound  bit  8, 8비트
 *     cur_volume bit 16, 7비트
 *     temp_c     bit 24, 8비트, factor 1, offset -40
 *     counter    bit 48, 4비트  롤링 카운터
 *     checksum   bit 56, 8비트  바이트 0..6 XOR
 */
#ifndef APP_SPEAKER_H
#define APP_SPEAKER_H

#include <stdint.h>
#include <stdbool.h>

#include "can_if.h"

#define SPEAKER_CMD_ID     (0x120U)
#define SPEAKER_STATUS_ID  (0x121U)
#define SPEAKER_CMD_TIMEOUT_MS (500U)
#define SPEAKER_STATUS_PERIOD_MS (100U)

typedef enum
{
    SPEAKER_STATE_IDLE = 0,
    SPEAKER_STATE_PLAYING,
    SPEAKER_STATE_SAFE      /**< 명령 두절 → 정지 */
} speaker_state_t;

typedef enum
{
    SPEAKER_FAULT_NONE = 0,
    SPEAKER_FAULT_OPEN,     /**< 드라이버 단선 */
    SPEAKER_FAULT_SHORT
} speaker_fault_t;

typedef struct
{
    can_if_ctx_t   *p_if;
    uint8_t         tx_handle;
    speaker_state_t state;
    speaker_fault_t fault;
    uint8_t         cur_sound;
    uint8_t         cur_volume;
    int16_t         temp_c;
    uint8_t         counter;
    bool            initialized;
} app_speaker_t;

can_if_status_t app_speaker_init(app_speaker_t *p_app, can_if_ctx_t *p_if);

/** 100 ms 주기로 호출한다. 상태 프레임 내용을 갱신한다. */
void app_speaker_tick_100ms(app_speaker_t *p_app);

/** 드라이버 진단 결과를 반영한다 (실제로는 임피던스 측정 결과). */
void app_speaker_set_fault(app_speaker_t *p_app, speaker_fault_t fault);

void app_speaker_set_temperature(app_speaker_t *p_app, int16_t temp_c);

#endif /* APP_SPEAKER_H */
