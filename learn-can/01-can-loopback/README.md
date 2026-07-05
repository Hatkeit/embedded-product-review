# 01 · Classic CAN 내부 루프백 (보드 1개, 배선 없음)

> **목표**: STM32G4 보드 하나로 CAN 프레임을 만들어 보내고, 그걸 다시 받아
> PC 터미널에 출력한다. 트랜시버·120Ω·두 번째 노드 **전부 불필요**.

## 왜 루프백부터?

STM32G4의 FDCAN에는 **내부 루프백 모드**가 있습니다. 송신한 프레임이
칩 내부에서 곧바로 수신부로 되돌아옵니다. 즉 실제 배선 없이도 CAN의 핵심 흐름
**"프레임 구성 → 송신 → 수신 인터럽트 → 파싱"** 을 전부 연습할 수 있습니다.

물리계층(트랜시버·종단저항·차동신호)은 이미 잘 아시는 영역이니,
소프트웨어 흐름부터 확실히 잡고 02단계에서 실제 버스에 붙입니다.

---

## 무엇을 만드나

```
매 1초:
  ┌─────────────────────────────────────────────┐
  │ TX:  ID=0x123, 데이터=[카운터, 0,0,0,0,0,0,0]  │  ← main 루프에서 송신
  └─────────────────────────────────────────────┘
                    │ (내부 루프백으로 되돌아옴)
                    ▼
  ┌─────────────────────────────────────────────┐
  │ RX 인터럽트 발생 → 콜백에서 데이터 꺼냄        │  ← 자동 호출
  │ → UART로 PC에 출력:  RX ID=0x123 DATA=00 ...   │
  └─────────────────────────────────────────────┘
```

PC 터미널(예: PuTTY, Tera Term, CubeIDE 콘솔)에 아래처럼 찍히면 성공:

```
CAN loopback start
TX #1  ID=0x123
RX     ID=0x123  DLC=8  DATA= 01 00 00 00 00 00 00 00
TX #2  ID=0x123
RX     ID=0x123  DLC=8  DATA= 02 00 00 00 00 00 00 00
...
```

---

## CubeMX 설정 (GUI 클릭만, 코드 자동생성)

새 STM32CubeIDE 프로젝트에서 `.ioc` 파일을 열고:

### 1) 클럭 (Clock Configuration 탭)
- FDCAN 커널 클럭 소스를 정확히 알아야 비트타이밍이 맞습니다.
  일반적으로 **PCLK1** 또는 **PLLQ** 를 FDCAN 클럭으로 사용. 예제는 **커널 클럭 = 170 MHz** 기준.

### 2) FDCAN1 활성화 (Connectivity → FDCAN1)
- Mode: **Activated**
- Frame Format: **Classic** (FD 아님 — 이번엔 Classic만)
- Operating Mode: **Internal LoopBack**  ← 핵심! 배선 없이 되돌려받기
- **Nominal 비트타이밍** (커널클럭 170MHz → 500 kbps, 샘플포인트 ~87.5% 예시):
  - Prescaler = **20**   → 170MHz / 20 = 8.5 MHz (타임퀀텀 클럭)
  - Nominal Time Seg1 = **14**
  - Nominal Time Seg2 = **2**
  - Sync Jump Width = **2**
  - 검산: 비트당 tq = 1(sync)+14+2 = 17tq → 8.5MHz / 17 = **500 kbps** ✓
  - 샘플포인트 = (1+14)/17 = **88.2%** (자동차 권장 75~90% 범위) ✓

> 비트타이밍은 하드웨어 엔지니어에겐 익숙한 개념입니다: "한 비트를 몇 조각(tq)으로
> 나누고 어디서 샘플링하느냐". 커널 클럭이 다르면 Prescaler만 바꿔 500kbps를 맞추세요.

### 3) USART2 활성화 (PC 로그용)
- Nucleo는 보통 **USART2**가 ST-Link의 가상 COM 포트와 연결됨 → PC에서 바로 터미널로 봄
- Mode: **Asynchronous**, Baud rate: **115200**

### 4) 인터럽트 (NVIC)
- FDCAN1 interrupt 0 을 **Enable**

설정 후 저장하면 CubeMX가 `MX_FDCAN1_Init()`, `MX_USART2_UART_Init()` 등
**초기화 코드를 자동생성**합니다. 우리는 아래 [`can_loopback.c`](./can_loopback.c) 의
"사용자가 직접 넣는 부분"만 추가하면 됩니다.

---

## PCAN으로 확장 (02단계 예고)

이 루프백이 되면, 다음은 간단합니다:
1. CubeMX에서 Operating Mode를 **Internal LoopBack → Normal** 로만 바꿈
2. 보드의 FDCAN_TX/RX 핀에 **트랜시버**(예: TJA1051) 연결, 버스 양끝 **120Ω**
3. **PCAN-USB FD**를 같은 버스에 연결 → PCAN-View에서 `ID=0x123` 프레임이 실제로 보임
4. PCAN-View에서 프레임을 쏘면 → 보드의 RX 콜백이 받음 (PCAN이 "두 번째 노드")

코드는 거의 그대로, **모드 한 줄만** 바뀝니다.
