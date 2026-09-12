/**
 * @file    can_signal.h
 * @brief   CAN 프레임의 비트 단위 신호 인코딩 · 디코딩.
 *
 * 실무에서는 이 계층을 DBC 로부터 자동 생성한다 (STD-FW-001 FW-COM-001).
 * 본 파일은 생성기가 무엇을 만들어 내는지 이해하기 위한 참조 구현이다.
 *
 * 비트 번호는 DBC 규약을 따른다:
 *   바이트 n 의 최상위 비트 = 비트 번호 (n*8 + 7)
 *   바이트 n 의 최하위 비트 = 비트 번호 (n*8 + 0)
 */
#ifndef CAN_SIGNAL_H
#define CAN_SIGNAL_H

#include <stdint.h>
#include <stdbool.h>

typedef enum
{
    CAN_SIGNAL_INTEL = 0,   /**< little-endian, start_bit = LSB 위치 */
    CAN_SIGNAL_MOTOROLA     /**< big-endian,    start_bit = MSB 위치 */
} can_signal_order_t;

/** 신호 1개의 정의. DBC 한 줄에 해당한다. */
typedef struct
{
    uint8_t            start_bit;
    uint8_t            length;      /**< 1..32 */
    can_signal_order_t order;
    bool               is_signed;
    double             factor;      /**< 물리값 = raw * factor + offset */
    double             offset;
    double             min;
    double             max;
} can_signal_def_t;

/* --- raw 값 수준 --- */
uint32_t can_signal_get_raw(const uint8_t *p_data, uint8_t len,
                            const can_signal_def_t *p_def);
bool     can_signal_set_raw(uint8_t *p_data, uint8_t len,
                            const can_signal_def_t *p_def, uint32_t raw);

/* --- 물리값 수준 (스케일 · 오프셋 · 클램핑 적용) --- */
double   can_signal_get_phys(const uint8_t *p_data, uint8_t len,
                             const can_signal_def_t *p_def);
bool     can_signal_set_phys(uint8_t *p_data, uint8_t len,
                             const can_signal_def_t *p_def, double phys);

#endif /* CAN_SIGNAL_H */
