/* ============================================================================
 *  01 · Classic CAN 내부 루프백 예제  (STM32G4 / FDCAN, Classic 모드)
 * ----------------------------------------------------------------------------
 *  이 파일은 "CubeMX가 자동생성한 main.c에 당신이 직접 추가하는 부분"만 모은
 *  참고 코드입니다. 각 조각을 main.c의 표시된 위치(/* USER CODE ... */ 구역)에
 *  옮겨 넣으세요. C가 처음이어도 읽히도록 줄마다 하드웨어 관점 주석을 달았습니다.
 *
 *  전체 동작: 1초마다 ID=0x123 프레임 송신 → 내부 루프백으로 되돌아옴
 *            → 수신 인터럽트 콜백에서 꺼내 UART로 PC에 출력.
 * ==========================================================================*/

#include "main.h"     /* CubeMX가 만든 핸들·핀 정의 (hfdcan1, huart2 등) */
#include <stdio.h>    /* printf 사용 위해 */
#include <string.h>   /* memset 사용 위해 */

/* CubeMX가 main.c에 이미 만들어 둔 전역 핸들. 여기선 "이게 존재한다"고 알려주는 선언.
 *   FDCAN_HandleTypeDef = FDCAN 주변장치 하나를 통째로 다루는 '구조체'(핀맵 묶음 같은 것) */
extern FDCAN_HandleTypeDef hfdcan1;   /* CAN 컨트롤러 핸들 */
extern UART_HandleTypeDef  huart2;    /* PC 로그용 UART 핸들 */


/* ============================================================================
 *  [A] printf 를 UART로 내보내기  ── main.c 아무 곳(함수 밖)에 붙이세요
 * ----------------------------------------------------------------------------
 *  printf가 출력할 글자를 USART2(=Nucleo의 PC 가상COM)로 흘려보내는 '배관'.
 *  이게 있어야 printf 결과가 PC 터미널에 보입니다.
 * ==========================================================================*/
int _write(int file, char *ptr, int len)
{
    /* HAL_UART_Transmit: "이 데이터(ptr)를 len바이트, UART로 내보내라" (블로킹) */
    HAL_UART_Transmit(&huart2, (uint8_t *)ptr, len, HAL_MAX_DELAY);
    return len;   /* 몇 바이트 보냈는지 반환 (printf 내부 규약) */
}


/* ============================================================================
 *  [B] CAN 시작 루틴  ── main()의 while(1) '진입 전'에 한 번 호출
 * ----------------------------------------------------------------------------
 *  필터(어떤 ID를 받을지), 수신 인터럽트 켜기, 컨트롤러 가동 순서.
 * ==========================================================================*/
void CAN_Start(void)
{
    /* --- (1) 수신 필터: "들어오는 모든 표준 ID를 RX FIFO0에 담아라" ------------
     *   FDCAN_FilterTypeDef = 필터 설정을 담는 구조체. 점(.)으로 항목을 채웁니다. */
    FDCAN_FilterTypeDef sFilter;
    sFilter.IdType       = FDCAN_STANDARD_ID;        /* 11비트 표준 ID 대상 */
    sFilter.FilterIndex  = 0;                         /* 0번 필터 슬롯 사용 */
    sFilter.FilterType   = FDCAN_FILTER_MASK;         /* '값+마스크' 방식 */
    sFilter.FilterConfig = FDCAN_FILTER_TO_RXFIFO0;   /* 통과분은 FIFO0로 */
    sFilter.FilterID1    = 0x000;                      /* 비교할 값 */
    sFilter.FilterID2    = 0x000;                      /* 마스크 0 = 전부 무시 → 모든 ID 통과 */
    HAL_FDCAN_ConfigFilter(&hfdcan1, &sFilter);

    /* 필터에 안 걸린 나머지 프레임 처리 규칙: 여기선 표준/확장 모두 거부(REJECT) */
    HAL_FDCAN_ConfigGlobalFilter(&hfdcan1,
                                 FDCAN_REJECT, FDCAN_REJECT,
                                 FDCAN_FILTER_REMOTE, FDCAN_FILTER_REMOTE);

    /* --- (2) CAN 컨트롤러 가동 (전원 인가 스위치 ON 같은 것) ------------------- */
    HAL_FDCAN_Start(&hfdcan1);

    /* --- (3) 수신 인터럽트 켜기 ------------------------------------------------
     *   "FIFO0에 새 메시지가 들어오면 콜백([D])을 자동 호출하라" */
    HAL_FDCAN_ActivateNotification(&hfdcan1,
                                   FDCAN_IT_RX_FIFO0_NEW_MESSAGE, 0);

    printf("CAN loopback start\r\n");
}


/* ============================================================================
 *  [C] 프레임 1개 송신  ── while(1) 안에서 1초마다 호출
 * ----------------------------------------------------------------------------
 *  ID=0x123, 8바이트 데이터. 첫 바이트에 카운터를 넣어 매번 다르게.
 * ==========================================================================*/
void CAN_SendOnce(uint8_t counter)
{
    /* 송신 헤더: 이 프레임의 '설명표' (ID·길이·종류 등) */
    FDCAN_TxHeaderTypeDef TxHeader;
    TxHeader.Identifier          = 0x123;                 /* 이 메시지의 ID */
    TxHeader.IdType              = FDCAN_STANDARD_ID;     /* 11비트 표준 ID */
    TxHeader.TxFrameType         = FDCAN_DATA_FRAME;      /* 데이터 프레임(요청 아님) */
    TxHeader.DataLength          = FDCAN_DLC_BYTES_8;     /* 데이터 8바이트 */
    TxHeader.ErrorStateIndicator = FDCAN_ESI_ACTIVE;
    TxHeader.BitRateSwitch       = FDCAN_BRS_OFF;         /* Classic → 속도전환 없음 */
    TxHeader.FDFormat            = FDCAN_CLASSIC_CAN;     /* ★ Classic 프레임 (FD 아님) */
    TxHeader.TxEventFifoControl  = FDCAN_NO_TX_EVENTS;
    TxHeader.MessageMarker       = 0;

    /* 실제 데이터 8칸. 배열 = 연속된 메모리 8칸 (data[0]~data[7]) */
    uint8_t data[8];
    memset(data, 0, sizeof(data));  /* 8칸 전부 0으로 초기화 */
    data[0] = counter;              /* 첫 칸에만 카운터 값 */

    /* 송신 큐에 넣기 → 컨트롤러가 알아서 버스로 내보냄 */
    HAL_FDCAN_AddMessageToTxFifoQ(&hfdcan1, &TxHeader, data);

    printf("TX #%u  ID=0x123\r\n", counter);
}


/* ============================================================================
 *  [D] 수신 인터럽트 콜백  ── main.c 함수 밖에 붙이세요 (이름 고정!)
 * ----------------------------------------------------------------------------
 *  HAL이 미리 정해둔 이름. 새 CAN 메시지가 오면 HAL이 '자동으로' 이 함수를 호출.
 *  (하드웨어의 트리거 신호가 들어오면 처리 루틴이 도는 것과 동일한 개념)
 * ==========================================================================*/
void HAL_FDCAN_RxFifo0Callback(FDCAN_HandleTypeDef *hfdcan, uint32_t RxFifo0ITs)
{
    /* '새 메시지 도착' 플래그가 켜져 있을 때만 처리 (& = 비트 AND 검사) */
    if ((RxFifo0ITs & FDCAN_IT_RX_FIFO0_NEW_MESSAGE) == 0)
        return;

    FDCAN_RxHeaderTypeDef RxHeader;   /* 받은 프레임의 설명표가 여기 채워짐 */
    uint8_t RxData[8];                /* 받은 데이터가 여기 채워짐 */

    /* FIFO0에서 한 프레임 꺼내기: 헤더는 RxHeader에, 데이터는 RxData에 담긴다 */
    HAL_FDCAN_GetRxMessage(hfdcan, FDCAN_RX_FIFO0, &RxHeader, RxData);

    /* ★ G4 특이점: RxHeader.DataLength 는 바이트수가 아니라 '16비트 왼쪽으로 밀린 코드'.
     *   실제 바이트 수 = >> 16 (오른쪽 16칸 시프트). Classic(≤8)에선 이렇게 바로 나옴. */
    uint8_t dlc = (uint8_t)(RxHeader.DataLength >> 16) & 0x0F;

    printf("RX     ID=0x%03lX  DLC=%u  DATA=",
           RxHeader.Identifier, dlc);
    for (uint8_t i = 0; i < dlc; i++)     /* 데이터 바이트를 한 칸씩 16진수로 출력 */
        printf(" %02X", RxData[i]);
    printf("\r\n");
}


/* ============================================================================
 *  [E] main() 배치 예시  ── 위 조각들을 어떻게 쓰는지 전체 그림
 * ----------------------------------------------------------------------------
 *  실제로는 CubeMX가 만든 main.c 안에 이미 HAL_Init / SystemClock_Config /
 *  MX_FDCAN1_Init / MX_USART2_UART_Init 이 들어 있습니다. 아래는 흐름 참고용.
 * ==========================================================================*/
#if 0   /* 참고용 — 실제로는 CubeMX main.c의 해당 위치에 CAN_Start/CAN_SendOnce만 넣으세요 */
int main(void)
{
    HAL_Init();
    SystemClock_Config();
    MX_GPIO_Init();
    MX_USART2_UART_Init();    /* PC 로그용 UART */
    MX_FDCAN1_Init();         /* CAN 컨트롤러 (Classic + Internal LoopBack) */

    CAN_Start();              /* [B] 필터·인터럽트·가동 */

    uint8_t counter = 0;
    while (1)
    {
        counter++;            /* 1,2,3,... (255 넘으면 0으로 순환) */
        CAN_SendOnce(counter);/* [C] 송신 → 루프백으로 [D]가 자동 호출됨 */
        HAL_Delay(1000);      /* 1000ms 대기 (블로킹) */
    }
}
#endif
