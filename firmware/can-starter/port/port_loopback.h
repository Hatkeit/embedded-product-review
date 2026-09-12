/**
 * @file    port_loopback.h
 * @brief   호스트 빌드용 가짜 CAN 컨트롤러의 시험 제어 훅.
 *
 * 이 헤더는 test/ 와 데모에서만 쓴다. app/ · comm/ 계층은 참조하지 않는다.
 */
#ifndef PORT_LOOPBACK_H
#define PORT_LOOPBACK_H

#include "can_hal.h"

void loopback_reset(void);
void loopback_set_time(uint32_t ms);
void loopback_advance(uint32_t ms);
void loopback_set_bus_state(can_bus_state_t state);

/** 버스에서 프레임이 들어온 것처럼 만든다. */
bool loopback_inject(const can_frame_t *p_frame);

/** 노드가 송신한 프레임을 오래된 순서로 꺼낸다. */
bool loopback_pop_sent(can_frame_t *p_out);

uint32_t loopback_recover_count(void);

#endif /* PORT_LOOPBACK_H */
