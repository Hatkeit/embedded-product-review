/**
 * @file    can_signal.c
 * @brief   CAN 신호 비트 패킹 참조 구현.
 */

#include <math.h>
#include <stddef.h>

#include "can_signal.h"

#define BITS_PER_BYTE   (8U)
#define MAX_SIGNAL_BITS (32U)

/**
 * @brief 논리 비트 순번 i 에 해당하는 DBC 비트 번호를 돌려준다.
 *
 * Intel 은 start 에서 위로 올라가고, Motorola 는 바이트 안에서 내려가다가
 * 바이트 경계를 만나면 다음 바이트의 최상위 비트로 건너뛴다(톱니 배열).
 * 반환값이 UINT16_MAX 이면 프레임 밖이다.
 */
static uint16_t bit_index(const can_signal_def_t *p_def, uint8_t i, uint8_t len)
{
    uint16_t bit;

    if (p_def->order == CAN_SIGNAL_INTEL)
    {
        bit = (uint16_t)p_def->start_bit + (uint16_t)i;
    }
    else
    {
        /* Motorola: start_bit 이 MSB. i 번째 비트까지 톱니 경로를 따라간다. */
        uint16_t cur = (uint16_t)p_def->start_bit;
        uint8_t  n;

        for (n = 0U; n < i; n++)
        {
            if ((cur % BITS_PER_BYTE) == 0U)
            {
                cur = (uint16_t)(cur + 15U);   /* 다음 바이트의 비트 7 로 */
            }
            else
            {
                cur = (uint16_t)(cur - 1U);
            }
        }
        bit = cur;
    }

    return (bit < ((uint16_t)len * BITS_PER_BYTE)) ? bit : UINT16_MAX;
}

static bool def_is_valid(const can_signal_def_t *p_def)
{
    return (p_def != NULL) &&
           (p_def->length >= 1U) &&
           (p_def->length <= MAX_SIGNAL_BITS);
}

uint32_t can_signal_get_raw(const uint8_t *p_data, uint8_t len,
                            const can_signal_def_t *p_def)
{
    uint32_t raw = 0U;
    uint8_t  i;

    if ((p_data == NULL) || !def_is_valid(p_def))
    {
        return 0U;
    }

    for (i = 0U; i < p_def->length; i++)
    {
        uint16_t bit = bit_index(p_def, i, len);
        uint8_t  byte_idx;
        uint8_t  bit_off;

        if (bit == UINT16_MAX)
        {
            return 0U;   /* 프레임 밖: 규격 불일치 */
        }

        byte_idx = (uint8_t)(bit / BITS_PER_BYTE);
        bit_off  = (uint8_t)(bit % BITS_PER_BYTE);

        if (((p_data[byte_idx] >> bit_off) & 1U) != 0U)
        {
            /* Intel 은 i 가 LSB 부터, Motorola 는 MSB 부터 채워진다. */
            if (p_def->order == CAN_SIGNAL_INTEL)
            {
                raw |= ((uint32_t)1U << i);
            }
            else
            {
                raw |= ((uint32_t)1U << (p_def->length - 1U - i));
            }
        }
    }

    return raw;
}

bool can_signal_set_raw(uint8_t *p_data, uint8_t len,
                        const can_signal_def_t *p_def, uint32_t raw)
{
    uint8_t i;

    if ((p_data == NULL) || !def_is_valid(p_def))
    {
        return false;
    }

    /* 먼저 전 구간이 프레임 안에 있는지 확인한다. 부분 기록을 남기지 않는다. */
    for (i = 0U; i < p_def->length; i++)
    {
        if (bit_index(p_def, i, len) == UINT16_MAX)
        {
            return false;
        }
    }

    for (i = 0U; i < p_def->length; i++)
    {
        uint16_t bit      = bit_index(p_def, i, len);
        uint8_t  byte_idx = (uint8_t)(bit / BITS_PER_BYTE);
        uint8_t  bit_off  = (uint8_t)(bit % BITS_PER_BYTE);
        uint8_t  shift    = (p_def->order == CAN_SIGNAL_INTEL)
                            ? i : (uint8_t)(p_def->length - 1U - i);
        uint8_t  value    = (uint8_t)((raw >> shift) & 1U);

        if (value != 0U)
        {
            p_data[byte_idx] |= (uint8_t)(1U << bit_off);
        }
        else
        {
            p_data[byte_idx] &= (uint8_t)~(1U << bit_off);
        }
    }

    return true;
}

/** raw 를 부호 있는 값으로 해석한다 (길이만큼 부호 확장). */
static double raw_to_signed(uint32_t raw, uint8_t length)
{
    double result;

    if (length >= MAX_SIGNAL_BITS)
    {
        result = (double)(int32_t)raw;
    }
    else
    {
        uint32_t sign_bit = (uint32_t)1U << (length - 1U);

        if ((raw & sign_bit) != 0U)
        {
            uint32_t span = (uint32_t)1U << length;
            result = (double)((int64_t)raw - (int64_t)span);
        }
        else
        {
            result = (double)raw;
        }
    }

    return result;
}

double can_signal_get_phys(const uint8_t *p_data, uint8_t len,
                           const can_signal_def_t *p_def)
{
    uint32_t raw;
    double   value;

    if ((p_data == NULL) || !def_is_valid(p_def))
    {
        return 0.0;
    }

    raw   = can_signal_get_raw(p_data, len, p_def);
    value = p_def->is_signed ? raw_to_signed(raw, p_def->length) : (double)raw;

    return (value * p_def->factor) + p_def->offset;
}

bool can_signal_set_phys(uint8_t *p_data, uint8_t len,
                         const can_signal_def_t *p_def, double phys)
{
    double   clamped;
    double   scaled;
    uint32_t raw;

    if ((p_data == NULL) || !def_is_valid(p_def) || (p_def->factor == 0.0))
    {
        return false;
    }

    /* 물리 범위로 먼저 자른다. 범위를 넘긴 값을 그대로 감싸 보내면
       수신 측에서 전혀 다른 값으로 읽힌다 — 실무에서 흔한 사고. */
    clamped = phys;
    if (clamped < p_def->min) { clamped = p_def->min; }
    if (clamped > p_def->max) { clamped = p_def->max; }

    scaled = round((clamped - p_def->offset) / p_def->factor);

    if (p_def->is_signed)
    {
        int64_t  lo = -((int64_t)1 << (p_def->length - 1U));
        int64_t  hi =  ((int64_t)1 << (p_def->length - 1U)) - 1;
        int64_t  s  = (int64_t)scaled;

        if (s < lo) { s = lo; }
        if (s > hi) { s = hi; }

        raw = (uint32_t)((uint64_t)s & (((uint64_t)1U << p_def->length) - 1U));
    }
    else
    {
        uint64_t hi = ((uint64_t)1U << p_def->length) - 1U;
        int64_t  s  = (int64_t)scaled;

        if (s < 0) { s = 0; }
        if ((uint64_t)s > hi) { s = (int64_t)hi; }

        raw = (uint32_t)s;
    }

    return can_signal_set_raw(p_data, len, p_def, raw);
}
