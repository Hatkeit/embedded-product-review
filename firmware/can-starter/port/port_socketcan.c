/**
 * @file    port_socketcan.c
 * @brief   리눅스 SocketCAN 용 HAL 구현 (학습 2단계: 진짜 버스).
 *
 * 가상 인터페이스로 MCU 없이 2노드 통신을 연습할 수 있다.
 *
 *   sudo modprobe vcan
 *   sudo ip link add dev vcan0 type vcan
 *   sudo ip link set up vcan0
 *   candump vcan0                 # 다른 터미널에서 관찰
 *   cansend vcan0 120#0346        # 명령 주입
 *
 * 실제 어댑터라면 vcan0 대신 can0 을 쓰고 비트레이트를 지정한다.
 *   sudo ip link set can0 type can bitrate 500000 sample-point 0.875
 */

#include <errno.h>
#include <fcntl.h>
#include <net/if.h>
#include <stddef.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <unistd.h>

#include <linux/can.h>
#include <linux/can/raw.h>

#include "can_hal.h"

#ifndef SOCKETCAN_IFNAME
#define SOCKETCAN_IFNAME "vcan0"
#endif

static int      s_fd = -1;
static uint32_t s_epoch_ms;

static uint32_t monotonic_ms(void)
{
    struct timeval tv;

    (void)gettimeofday(&tv, NULL);
    return (uint32_t)(((uint64_t)tv.tv_sec * 1000U) + ((uint64_t)tv.tv_usec / 1000U));
}

can_hal_status_t can_hal_init(const can_hal_cfg_t *p_cfg)
{
    struct sockaddr_can addr;
    struct ifreq        ifr;
    int                 flags;

    if (p_cfg == NULL)
    {
        return CAN_HAL_ERR_PARAM;
    }

    /* 비트레이트는 커널 인터페이스 설정으로 정해진다. 여기서는 검증만 한다. */
    if ((p_cfg->bitrate_bps == 0U) || (p_cfg->bitrate_bps > 1000000U))
    {
        return CAN_HAL_ERR_PARAM;
    }

    s_fd = socket(PF_CAN, SOCK_RAW, CAN_RAW);
    if (s_fd < 0)
    {
        return CAN_HAL_ERR_HW;
    }

    (void)memset(&ifr, 0, sizeof(ifr));
    (void)strncpy(ifr.ifr_name, SOCKETCAN_IFNAME, IFNAMSIZ - 1U);
    if (ioctl(s_fd, SIOCGIFINDEX, &ifr) < 0)
    {
        (void)close(s_fd);
        s_fd = -1;
        return CAN_HAL_ERR_HW;
    }

    (void)memset(&addr, 0, sizeof(addr));
    addr.can_family  = AF_CAN;
    addr.can_ifindex = ifr.ifr_ifindex;

    if (bind(s_fd, (struct sockaddr *)&addr, sizeof(addr)) < 0)
    {
        (void)close(s_fd);
        s_fd = -1;
        return CAN_HAL_ERR_HW;
    }

    /* 논블로킹. can_hal_recv() 는 절대 블로킹하지 않는다. */
    flags = fcntl(s_fd, F_GETFL, 0);
    (void)fcntl(s_fd, F_SETFL, flags | O_NONBLOCK);

    s_epoch_ms = monotonic_ms();
    return CAN_HAL_OK;
}

can_hal_status_t can_hal_send(const can_frame_t *p_frame)
{
    struct can_frame raw;
    ssize_t          n;

    if (p_frame == NULL)
    {
        return CAN_HAL_ERR_PARAM;
    }
    if (s_fd < 0)
    {
        return CAN_HAL_ERR_STATE;
    }
    if (p_frame->dlc > CAN_HAL_MAX_DLC)
    {
        return CAN_HAL_ERR_PARAM;
    }

    (void)memset(&raw, 0, sizeof(raw));
    raw.can_id  = p_frame->id;
    if (p_frame->is_extended)
    {
        raw.can_id |= CAN_EFF_FLAG;
    }
    raw.can_dlc = p_frame->dlc;
    (void)memcpy(raw.data, p_frame->data, p_frame->dlc);

    n = write(s_fd, &raw, sizeof(raw));
    if (n != (ssize_t)sizeof(raw))
    {
        return (errno == ENOBUFS) ? CAN_HAL_ERR_BUSY : CAN_HAL_ERR_HW;
    }

    return CAN_HAL_OK;
}

can_hal_status_t can_hal_recv(can_frame_t *p_frame)
{
    struct can_frame raw;
    ssize_t          n;

    if (p_frame == NULL)
    {
        return CAN_HAL_ERR_PARAM;
    }
    if (s_fd < 0)
    {
        return CAN_HAL_ERR_STATE;
    }

    n = read(s_fd, &raw, sizeof(raw));
    if (n != (ssize_t)sizeof(raw))
    {
        return CAN_HAL_ERR_NO_DATA;
    }

    p_frame->is_extended = ((raw.can_id & CAN_EFF_FLAG) != 0U);
    p_frame->id  = raw.can_id & (p_frame->is_extended ? CAN_EFF_MASK : CAN_SFF_MASK);
    p_frame->dlc = (raw.can_dlc > CAN_HAL_MAX_DLC) ? CAN_HAL_MAX_DLC : raw.can_dlc;
    (void)memcpy(p_frame->data, raw.data, CAN_HAL_MAX_DLC);

    return CAN_HAL_OK;
}

can_hal_status_t can_hal_bus_state(can_bus_state_t *p_state)
{
    if (p_state == NULL)
    {
        return CAN_HAL_ERR_PARAM;
    }

    /* 실제 상태는 CAN_RAW_ERR_FILTER 로 오류 프레임을 구독해 얻는다.
       가상 인터페이스에는 Bus-Off 가 없으므로 항상 정상으로 보고한다. */
    *p_state = CAN_BUS_ERROR_ACTIVE;
    return CAN_HAL_OK;
}

can_hal_status_t can_hal_recover(void)
{
    return CAN_HAL_OK;
}

uint32_t can_hal_now_ms(void)
{
    return monotonic_ms() - s_epoch_ms;
}
