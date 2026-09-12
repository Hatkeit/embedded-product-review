/**
 * @file    can_if.c
 * @brief   CAN 송수신 서비스 계층 구현.
 */

#include <stddef.h>
#include <string.h>

#include "can_if.h"

#define RX_DRAIN_PER_TICK (8U)   /* 1 틱에 처리할 최대 수신 프레임 수 */

/* ---- 내부 함수 ---------------------------------------------------------- */

static uint8_t queue_next(uint8_t idx)
{
    return (uint8_t)((idx + 1U) % CAN_IF_RX_QUEUE_LEN);
}

static bool queue_push(can_if_ctx_t *p_ctx, const can_frame_t *p_frame)
{
    uint8_t next = queue_next(p_ctx->rx_head);

    if (next == p_ctx->rx_tail)
    {
        return false;   /* 가득 참: 가장 오래된 것을 지키고 새 것을 버린다 */
    }

    p_ctx->rx_queue[p_ctx->rx_head] = *p_frame;
    p_ctx->rx_head = next;
    return true;
}

static bool queue_pop(can_if_ctx_t *p_ctx, can_frame_t *p_out)
{
    if (p_ctx->rx_tail == p_ctx->rx_head)
    {
        return false;
    }

    *p_out = p_ctx->rx_queue[p_ctx->rx_tail];
    p_ctx->rx_tail = queue_next(p_ctx->rx_tail);
    return true;
}

static can_if_sub_t *find_sub(can_if_ctx_t *p_ctx, uint32_t id)
{
    uint8_t i;

    for (i = 0U; i < CAN_IF_MAX_SUBS; i++)
    {
        if (p_ctx->subs[i].in_use && (p_ctx->subs[i].id == id))
        {
            return &p_ctx->subs[i];
        }
    }

    return NULL;
}

/** 32비트 밀리초 카운터의 랩어라운드에 안전한 비교. */
static bool time_reached(uint32_t now_ms, uint32_t deadline_ms)
{
    return (int32_t)(now_ms - deadline_ms) >= 0;
}

static void dispatch_rx(can_if_ctx_t *p_ctx, uint32_t now_ms)
{
    can_frame_t frame;
    uint8_t     n;

    for (n = 0U; n < RX_DRAIN_PER_TICK; n++)
    {
        can_if_sub_t *p_sub;

        if (!queue_pop(p_ctx, &frame))
        {
            break;
        }

        p_sub = find_sub(p_ctx, frame.id);
        if (p_sub == NULL)
        {
            p_ctx->stats.rx_unhandled++;
            continue;
        }

        p_sub->last_rx_ms = now_ms;
        p_sub->timed_out  = false;

        if (p_sub->on_rx != NULL)
        {
            p_sub->on_rx(&frame, p_sub->p_user);
        }
    }
}

static void check_timeouts(can_if_ctx_t *p_ctx, uint32_t now_ms)
{
    uint8_t i;

    for (i = 0U; i < CAN_IF_MAX_SUBS; i++)
    {
        can_if_sub_t *p_sub = &p_ctx->subs[i];

        if (!p_sub->in_use || (p_sub->timeout_ms == 0U) || p_sub->timed_out)
        {
            continue;
        }

        if (time_reached(now_ms, p_sub->last_rx_ms + p_sub->timeout_ms))
        {
            p_sub->timed_out = true;
            p_ctx->stats.timeouts++;

            if (p_sub->on_timeout != NULL)
            {
                p_sub->on_timeout(p_sub->id, p_sub->p_user);
            }
        }
    }
}

static void service_periodic_tx(can_if_ctx_t *p_ctx, uint32_t now_ms)
{
    uint8_t i;

    for (i = 0U; i < CAN_IF_MAX_TX_JOBS; i++)
    {
        can_if_tx_job_t *p_job = &p_ctx->tx_jobs[i];
        can_frame_t      frame;

        if (!p_job->in_use || !p_job->armed || (p_job->period_ms == 0U))
        {
            continue;
        }

        if (!time_reached(now_ms, p_job->next_due_ms))
        {
            continue;
        }

        frame.id          = p_job->id;
        frame.is_extended = false;
        frame.dlc         = p_job->dlc;
        (void)memcpy(frame.data, p_job->data, CAN_HAL_MAX_DLC);

        if (can_hal_send(&frame) == CAN_HAL_OK)
        {
            p_ctx->stats.tx_frames++;
        }
        /* 송신 실패는 다음 주기에 다시 시도한다. 지터를 만들지 않기 위해
           주기 기준점은 성공 여부와 무관하게 전진시킨다. */
        p_job->next_due_ms = now_ms + p_job->period_ms;
    }
}

static void service_bus_state(can_if_ctx_t *p_ctx, uint32_t now_ms)
{
    can_bus_state_t state;

    if (can_hal_bus_state(&state) != CAN_HAL_OK)
    {
        return;
    }

    if ((state == CAN_BUS_OFF) && (p_ctx->bus_state != CAN_BUS_OFF))
    {
        p_ctx->stats.bus_off_events++;
        p_ctx->bus_off_since_ms = now_ms;
    }

    p_ctx->bus_state = state;

    /* Bus-Off 는 즉시 복구하지 않는다. 원인이 남아 있으면 복구·재진입을
       반복하며 버스를 더 망가뜨린다. 일정 시간 기다린 뒤 한 번 시도한다. */
    if ((state == CAN_BUS_OFF) &&
        time_reached(now_ms, p_ctx->bus_off_since_ms + CAN_IF_BUS_OFF_DELAY_MS))
    {
        (void)can_hal_recover();
        p_ctx->bus_off_since_ms = now_ms;
    }
}

/* ---- 공개 함수 ---------------------------------------------------------- */

can_if_status_t can_if_init(can_if_ctx_t *p_ctx, const can_hal_cfg_t *p_cfg)
{
    if ((p_ctx == NULL) || (p_cfg == NULL))
    {
        return CAN_IF_ERR_PARAM;
    }

    (void)memset(p_ctx, 0, sizeof(*p_ctx));

    if (can_hal_init(p_cfg) != CAN_HAL_OK)
    {
        return CAN_IF_ERR_HW;
    }

    p_ctx->bus_state   = CAN_BUS_ERROR_ACTIVE;
    p_ctx->initialized = true;
    return CAN_IF_OK;
}

can_if_status_t can_if_subscribe(can_if_ctx_t *p_ctx,
                                 uint32_t id,
                                 uint32_t timeout_ms,
                                 can_if_rx_cb_t on_rx,
                                 can_if_timeout_cb_t on_timeout,
                                 void *p_user)
{
    uint8_t i;

    if ((p_ctx == NULL) || (on_rx == NULL))
    {
        return CAN_IF_ERR_PARAM;
    }
    if (!p_ctx->initialized)
    {
        return CAN_IF_ERR_STATE;
    }
    if (find_sub(p_ctx, id) != NULL)
    {
        return CAN_IF_ERR_PARAM;   /* 같은 ID 중복 구독 금지 */
    }

    for (i = 0U; i < CAN_IF_MAX_SUBS; i++)
    {
        if (!p_ctx->subs[i].in_use)
        {
            p_ctx->subs[i].id         = id;
            p_ctx->subs[i].timeout_ms = timeout_ms;
            p_ctx->subs[i].on_rx      = on_rx;
            p_ctx->subs[i].on_timeout = on_timeout;
            p_ctx->subs[i].p_user     = p_user;
            p_ctx->subs[i].in_use     = true;
            p_ctx->subs[i].timed_out  = false;
            p_ctx->subs[i].last_rx_ms = 0U;
            return CAN_IF_OK;
        }
    }

    return CAN_IF_ERR_FULL;
}

can_if_status_t can_if_tx_register(can_if_ctx_t *p_ctx,
                                   uint32_t id,
                                   uint8_t dlc,
                                   uint16_t period_ms,
                                   uint8_t *p_handle)
{
    uint8_t i;

    if ((p_ctx == NULL) || (p_handle == NULL) || (dlc > CAN_HAL_MAX_DLC))
    {
        return CAN_IF_ERR_PARAM;
    }
    if (!p_ctx->initialized)
    {
        return CAN_IF_ERR_STATE;
    }

    for (i = 0U; i < CAN_IF_MAX_TX_JOBS; i++)
    {
        if (!p_ctx->tx_jobs[i].in_use)
        {
            p_ctx->tx_jobs[i].id          = id;
            p_ctx->tx_jobs[i].dlc         = dlc;
            p_ctx->tx_jobs[i].period_ms   = period_ms;
            p_ctx->tx_jobs[i].next_due_ms = 0U;
            p_ctx->tx_jobs[i].in_use      = true;
            p_ctx->tx_jobs[i].armed       = false;
            (void)memset(p_ctx->tx_jobs[i].data, 0, CAN_HAL_MAX_DLC);
            *p_handle = i;
            return CAN_IF_OK;
        }
    }

    return CAN_IF_ERR_FULL;
}

can_if_status_t can_if_tx_update(can_if_ctx_t *p_ctx,
                                 uint8_t handle,
                                 const uint8_t *p_data,
                                 uint8_t dlc)
{
    if ((p_ctx == NULL) || (p_data == NULL) ||
        (handle >= CAN_IF_MAX_TX_JOBS) || (dlc > CAN_HAL_MAX_DLC))
    {
        return CAN_IF_ERR_PARAM;
    }
    if (!p_ctx->tx_jobs[handle].in_use)
    {
        return CAN_IF_ERR_STATE;
    }

    (void)memcpy(p_ctx->tx_jobs[handle].data, p_data, dlc);
    p_ctx->tx_jobs[handle].dlc   = dlc;
    p_ctx->tx_jobs[handle].armed = true;
    return CAN_IF_OK;
}

can_if_status_t can_if_send(can_if_ctx_t *p_ctx, const can_frame_t *p_frame)
{
    if ((p_ctx == NULL) || (p_frame == NULL) || (p_frame->dlc > CAN_HAL_MAX_DLC))
    {
        return CAN_IF_ERR_PARAM;
    }
    if (!p_ctx->initialized)
    {
        return CAN_IF_ERR_STATE;
    }

    if (can_hal_send(p_frame) != CAN_HAL_OK)
    {
        return CAN_IF_ERR_HW;
    }

    p_ctx->stats.tx_frames++;
    return CAN_IF_OK;
}

can_if_status_t can_if_tick_1ms(can_if_ctx_t *p_ctx, uint32_t now_ms)
{
    can_frame_t frame;
    uint8_t     n;

    if (p_ctx == NULL)
    {
        return CAN_IF_ERR_PARAM;
    }
    if (!p_ctx->initialized)
    {
        return CAN_IF_ERR_STATE;
    }

    /* 1. 컨트롤러 수신 FIFO 를 큐로 옮긴다 (여기서는 콜백을 부르지 않는다). */
    for (n = 0U; n < RX_DRAIN_PER_TICK; n++)
    {
        if (can_hal_recv(&frame) != CAN_HAL_OK)
        {
            break;
        }

        p_ctx->stats.rx_frames++;

        if (!queue_push(p_ctx, &frame))
        {
            p_ctx->stats.rx_dropped++;
        }
    }

    /* 2. 큐를 비우며 구독자에게 전달한다. */
    dispatch_rx(p_ctx, now_ms);

    /* 3. 감시와 송신. */
    check_timeouts(p_ctx, now_ms);
    service_periodic_tx(p_ctx, now_ms);
    service_bus_state(p_ctx, now_ms);

    return CAN_IF_OK;
}

can_if_status_t can_if_get_stats(const can_if_ctx_t *p_ctx, can_if_stats_t *p_out)
{
    if ((p_ctx == NULL) || (p_out == NULL))
    {
        return CAN_IF_ERR_PARAM;
    }

    *p_out = p_ctx->stats;
    return CAN_IF_OK;
}
