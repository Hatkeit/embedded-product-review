/**
 * @file    port_loopback.c
 * @brief   MCU 없이 호스트에서 돌리는 CAN HAL 구현.
 *
 * 하드웨어가 오기 전에 comm/ 과 app/ 을 전부 작성하고 시험할 수 있게 한다
 * (STD-FW-001 FW-ARC-004). 벤더 SDK 를 전혀 포함하지 않는다.
 */

#include <stddef.h>
#include <string.h>

#include "port_loopback.h"

#define LB_QUEUE_LEN (32U)

typedef struct
{
    can_frame_t items[LB_QUEUE_LEN];
    uint8_t     head;
    uint8_t     tail;
} lb_queue_t;

static lb_queue_t      s_rx;            /* 노드가 읽어갈 프레임 */
static lb_queue_t      s_tx;            /* 노드가 내보낸 프레임 */
static uint32_t        s_now_ms;
static bool            s_initialized;
static bool            s_loopback;
static can_bus_state_t s_bus_state = CAN_BUS_ERROR_ACTIVE;
static uint32_t        s_recover_count;

static uint8_t q_next(uint8_t i)
{
    return (uint8_t)((i + 1U) % LB_QUEUE_LEN);
}

static bool q_push(lb_queue_t *p_q, const can_frame_t *p_f)
{
    uint8_t next = q_next(p_q->head);

    if (next == p_q->tail)
    {
        return false;
    }

    p_q->items[p_q->head] = *p_f;
    p_q->head = next;
    return true;
}

static bool q_pop(lb_queue_t *p_q, can_frame_t *p_out)
{
    if (p_q->tail == p_q->head)
    {
        return false;
    }

    *p_out = p_q->items[p_q->tail];
    p_q->tail = q_next(p_q->tail);
    return true;
}

/* ---- 시험 훅 ------------------------------------------------------------ */

void loopback_reset(void)
{
    (void)memset(&s_rx, 0, sizeof(s_rx));
    (void)memset(&s_tx, 0, sizeof(s_tx));
    s_now_ms        = 0U;
    s_initialized   = false;
    s_loopback      = false;
    s_bus_state     = CAN_BUS_ERROR_ACTIVE;
    s_recover_count = 0U;
}

void loopback_set_time(uint32_t ms)     { s_now_ms = ms; }
void loopback_advance(uint32_t ms)      { s_now_ms += ms; }
void loopback_set_bus_state(can_bus_state_t state) { s_bus_state = state; }
uint32_t loopback_recover_count(void)   { return s_recover_count; }

bool loopback_inject(const can_frame_t *p_frame)
{
    return (p_frame != NULL) && q_push(&s_rx, p_frame);
}

bool loopback_pop_sent(can_frame_t *p_out)
{
    return (p_out != NULL) && q_pop(&s_tx, p_out);
}

/* ---- HAL 구현 ----------------------------------------------------------- */

can_hal_status_t can_hal_init(const can_hal_cfg_t *p_cfg)
{
    if (p_cfg == NULL)
    {
        return CAN_HAL_ERR_PARAM;
    }
    if ((p_cfg->bitrate_bps == 0U) || (p_cfg->bitrate_bps > 1000000U))
    {
        return CAN_HAL_ERR_PARAM;
    }

    s_loopback    = p_cfg->loopback;
    s_initialized = true;
    return CAN_HAL_OK;
}

can_hal_status_t can_hal_send(const can_frame_t *p_frame)
{
    if (p_frame == NULL)
    {
        return CAN_HAL_ERR_PARAM;
    }
    if (!s_initialized)
    {
        return CAN_HAL_ERR_STATE;
    }
    if (p_frame->dlc > CAN_HAL_MAX_DLC)
    {
        return CAN_HAL_ERR_PARAM;
    }
    if (s_bus_state == CAN_BUS_OFF)
    {
        return CAN_HAL_ERR_HW;   /* Bus-Off 에서는 송신되지 않는다 */
    }

    if (!q_push(&s_tx, p_frame))
    {
        return CAN_HAL_ERR_BUSY;
    }

    if (s_loopback)
    {
        (void)q_push(&s_rx, p_frame);
    }

    return CAN_HAL_OK;
}

can_hal_status_t can_hal_recv(can_frame_t *p_frame)
{
    if (p_frame == NULL)
    {
        return CAN_HAL_ERR_PARAM;
    }
    if (!s_initialized)
    {
        return CAN_HAL_ERR_STATE;
    }

    return q_pop(&s_rx, p_frame) ? CAN_HAL_OK : CAN_HAL_ERR_NO_DATA;
}

can_hal_status_t can_hal_bus_state(can_bus_state_t *p_state)
{
    if (p_state == NULL)
    {
        return CAN_HAL_ERR_PARAM;
    }

    *p_state = s_bus_state;
    return CAN_HAL_OK;
}

can_hal_status_t can_hal_recover(void)
{
    s_recover_count++;
    return CAN_HAL_OK;
}

uint32_t can_hal_now_ms(void)
{
    return s_now_ms;
}
