/**
 * @file    can_if.h
 * @brief   CAN 송수신 서비스 계층.
 *
 * HAL 위에 실무에서 항상 필요한 네 가지를 얹는다.
 *   1. 수신 프레임 디스패치 (ID → 콜백)
 *   2. 주기 송신
 *   3. 수신 타임아웃 감시 (신호 age)
 *   4. Bus-Off 자동 복구
 *
 * 편차 DEV-STARTER-001 : STD-FW-001 FW-API-002(불투명 타입)를 적용하지 않고
 * 컨텍스트 구조체를 헤더에 노출한다. 정적 할당만 허용하는 환경에서 호출자가
 * 인스턴스를 직접 잡을 수 있게 하기 위함이며, 내부 필드 접근은 금지한다.
 * 대체 검증: 필드 접근 여부를 코드 리뷰 체크리스트에 포함.
 */
#ifndef CAN_IF_H
#define CAN_IF_H

#include <stdint.h>
#include <stdbool.h>

#include "can_hal.h"

#define CAN_IF_MAX_SUBS      (8U)
#define CAN_IF_MAX_TX_JOBS   (8U)
#define CAN_IF_RX_QUEUE_LEN  (16U)
#define CAN_IF_BUS_OFF_DELAY_MS (200U)

typedef enum
{
    CAN_IF_OK = 0,
    CAN_IF_ERR_PARAM,
    CAN_IF_ERR_STATE,
    CAN_IF_ERR_FULL,
    CAN_IF_ERR_HW
} can_if_status_t;

/** 프레임 수신 시 호출된다. 콜백 안에서 블로킹 동작을 하지 않는다. */
typedef void (*can_if_rx_cb_t)(const can_frame_t *p_frame, void *p_user);

/** 구독한 ID 가 timeout_ms 동안 오지 않으면 호출된다. */
typedef void (*can_if_timeout_cb_t)(uint32_t id, void *p_user);

typedef struct
{
    uint32_t rx_frames;
    uint32_t tx_frames;
    uint32_t rx_dropped;    /**< 큐 넘침 */
    uint32_t rx_unhandled;  /**< 구독자 없는 ID */
    uint32_t timeouts;
    uint32_t bus_off_events;
} can_if_stats_t;

/* --- 이하 내부 구조. 호출자가 직접 접근하지 않는다. --- */
typedef struct
{
    uint32_t            id;
    uint32_t            timeout_ms;
    uint32_t            last_rx_ms;
    bool                in_use;
    bool                timed_out;
    can_if_rx_cb_t      on_rx;
    can_if_timeout_cb_t on_timeout;
    void               *p_user;
} can_if_sub_t;

typedef struct
{
    uint32_t id;
    uint32_t next_due_ms;
    uint16_t period_ms;
    uint8_t  dlc;
    uint8_t  data[CAN_HAL_MAX_DLC];
    bool     in_use;
    bool     armed;     /**< 최초 can_if_tx_update() 전에는 송신하지 않는다 */
} can_if_tx_job_t;

typedef struct
{
    bool            initialized;
    can_bus_state_t bus_state;
    uint32_t        bus_off_since_ms;
    can_if_sub_t    subs[CAN_IF_MAX_SUBS];
    can_if_tx_job_t tx_jobs[CAN_IF_MAX_TX_JOBS];
    can_frame_t     rx_queue[CAN_IF_RX_QUEUE_LEN];
    uint8_t         rx_head;
    uint8_t         rx_tail;
    can_if_stats_t  stats;
} can_if_ctx_t;

can_if_status_t can_if_init(can_if_ctx_t *p_ctx, const can_hal_cfg_t *p_cfg);

can_if_status_t can_if_subscribe(can_if_ctx_t *p_ctx,
                                 uint32_t id,
                                 uint32_t timeout_ms,
                                 can_if_rx_cb_t on_rx,
                                 can_if_timeout_cb_t on_timeout,
                                 void *p_user);

/**
 * @brief 주기 송신 슬롯을 확보한다.
 *
 * 등록만으로는 송신이 시작되지 않는다. 최초 can_if_tx_update() 가 호출된
 * 뒤부터 나간다. 초기화되지 않은 0 프레임을 버스에 publish 하면 수신 노드가
 * 그것을 유효한 상태로 받아들이기 때문이다.
 */
can_if_status_t can_if_tx_register(can_if_ctx_t *p_ctx,
                                   uint32_t id,
                                   uint8_t dlc,
                                   uint16_t period_ms,
                                   uint8_t *p_handle);

can_if_status_t can_if_tx_update(can_if_ctx_t *p_ctx,
                                 uint8_t handle,
                                 const uint8_t *p_data,
                                 uint8_t dlc);

can_if_status_t can_if_send(can_if_ctx_t *p_ctx, const can_frame_t *p_frame);

/** 1 ms 주기로 호출한다. 내부에서 시간을 직접 읽지 않는다(FW-API-004). */
can_if_status_t can_if_tick_1ms(can_if_ctx_t *p_ctx, uint32_t now_ms);

can_if_status_t can_if_get_stats(const can_if_ctx_t *p_ctx, can_if_stats_t *p_out);

#endif /* CAN_IF_H */
