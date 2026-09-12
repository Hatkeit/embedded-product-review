/**
 * @file    can_hal.h
 * @brief   CAN 컨트롤러 하드웨어 추상화 인터페이스.
 *
 * STD-FW-001 의 hal/ 계층. 선언만 존재하며 구현은 port/ 에 둔다.
 * 이 헤더는 어떤 MCU 벤더 헤더도 포함하지 않는다 (FW-ARC-002).
 */
#ifndef CAN_HAL_H
#define CAN_HAL_H

#include <stdint.h>
#include <stdbool.h>

#define CAN_HAL_MAX_DLC   (8U)

typedef enum
{
    CAN_HAL_OK = 0,
    CAN_HAL_ERR_PARAM,      /**< 인자가 유효하지 않음 */
    CAN_HAL_ERR_STATE,      /**< 초기화 전 호출 */
    CAN_HAL_ERR_BUSY,       /**< 송신 메일박스 가득 참 */
    CAN_HAL_ERR_NO_DATA,    /**< 수신 큐 비어 있음 */
    CAN_HAL_ERR_HW          /**< 컨트롤러 오류 */
} can_hal_status_t;

/** ISO 11898-1 오류 상태. Bus-Off 복구 로직의 입력이 된다. */
typedef enum
{
    CAN_BUS_ERROR_ACTIVE = 0,
    CAN_BUS_ERROR_WARNING,
    CAN_BUS_ERROR_PASSIVE,
    CAN_BUS_OFF
} can_bus_state_t;

typedef struct
{
    uint32_t id;            /**< 11비트 또는 29비트 식별자 */
    bool     is_extended;   /**< true 이면 29비트 */
    uint8_t  dlc;           /**< 0..8 */
    uint8_t  data[CAN_HAL_MAX_DLC];
} can_frame_t;

typedef struct
{
    uint32_t bitrate_bps;   /**< 예: 500000 */
    uint8_t  sample_point_pct; /**< 예: 87 (= 87.5% 를 정수로 내림) */
    bool     loopback;      /**< true 이면 버스 없이 자기 수신 */
} can_hal_cfg_t;

can_hal_status_t can_hal_init(const can_hal_cfg_t *p_cfg);
can_hal_status_t can_hal_send(const can_frame_t *p_frame);
can_hal_status_t can_hal_recv(can_frame_t *p_frame);
can_hal_status_t can_hal_bus_state(can_bus_state_t *p_state);
can_hal_status_t can_hal_recover(void);   /**< Bus-Off 복구 시작 */
uint32_t         can_hal_now_ms(void);

#endif /* CAN_HAL_H */
