# FOC_3 넷 수준 연결표 (OrCAD Capture 입력용)

작성 2026-10-24 · 상태: **초안. 핀 번호는 원문 데이터시트 확인 전까지 전부 ❓**
설계 근거: [schematic-design.md](schematic-design.md) · 부품: [bom-draft.csv](bom-draft.csv)

## 규칙

- **핀 번호 열**: 데이터시트 원문으로 확인하기 전에는 `❓`. 핀 **이름**도 원문 미확인이면 이름 뒤에 `❓`.
  (6ED2742S01Q 핀 이름 중 CSO / CSO GAIN / STR / ITRIP / ITRIP CONF / RFE / VSS / COM 은 데이터시트 블록도 요약에서 🔍,
  나머지 HIN·LIN·HO·LO·VB·VS·VCC는 동종 3상 드라이버 관례명 ❓)
- OrCAD 페이지 분할 제안: P1 전원입력·브레이크 / P2 브리지·션트 / P3 게이트 드라이버 / P4 전류증폭·센싱 /
  P5 보조전원 / P6 MCU / P7 CAN·엔코더·디버그 / P8 STO / P9 모듈 핀.
- 넷 이름 규칙: 전원 `+12V_GD`, `VCC_GD`, `+5V`, `+3V3`, `+3V3A` / 접지 `PGND`(전력), `AGND`(아날로그), `GND`(디지털) —
  **AGND·GND는 PGND 스타점 1곳에서 결합** (넷 타이 NT1). 신호는 `블록_기능` 형태.
- 경로 B/C 공용 풋프린트. 값 차이는 BOM variant 열로 처리.

---

## 1. 모듈 외부 핀 (P9) — J1 (PCB 실장 핀 헤더/캐스텔레이션)

| 핀 그룹 | 넷 | 핀 수 (안) | 비고 |
|---|---|---|---|
| VBUS+ | VBUS | 4 ❓ | 47.5 A DC. 핀당 전류 정격 ❓로 핀 수 결정 |
| PGND | PGND | 4 ❓ | |
| U / V / W | PH_U / PH_V / PH_W | 각 3 ❓ | 35.3 A RMS (진폭 50 A), 피크 진폭 100 A |
| BRK | BRK | 1–2 ❓ | 외부 제동저항 연결 (다른 끝은 VBUS+) |
| VL | VL_IN | 1 | 12–95 V 제어 전원 |
| GND | GND | 2 | 로직 리턴 (내부에서 PGND 스타점 결합) |
| STO | STO1_P, STO1_N, STO2_P, STO2_N | 4 | 옵토 절연 입력 |
| CAN | CANH, CANL | 2 | GND 공용 |
| 엔코더 A | ENC_A_P/N, ENC_B_P/N, ENC_Z_P/N | 6 | |
| 엔코더 B | HALL_U, HALL_V, HALL_W | 3 | |
| 엔코더 C | ABS_CLK_P/N, ABS_DAT_P/N | 4 | |
| 엔코더 전원 | ENC_5V | 1–2 | 200 mA |
| UART | UART_TX, UART_RX | 2 | 3.3 V TTL |
| I/O | DI1–DI4, DO1–DO2, AIN_P, AIN_N | 8 `[제품 사양 미확정]` | |

---

## 2. P1 — 전원 입력·버스 C·브레이크

| Ref | 부품 | 핀 (이름) | 핀# | 넷 | 비고 |
|---|---|---|---|---|---|
| C1–C(n) | MLCC ≥150 V | 1 / 2 | – | VBUS / PGND | 각 하프브리지 근접 분산. 수량 ❓ (리플 22.9 A RMS 🔢) |
| D10 | TVS (ESD/서지용) | K / A | – | VBUS / PGND | 회생 클램프 아님 (SD §2.1). 부품 ❓ |
| Q7 | 브레이크 MOSFET (TOLL 또는 소형) | D | ❓ | BRK | |
| | | S | ❓ | PGND | 켈빈 소스 핀이 있으면 → BRK_KS |
| | | G | ❓ | BRK_G | |
| D_BRK | 프리휠 다이오드 ≥150 V | K / A | – | VBUS / BRK | |
| U3 | 로우사이드 게이트 드라이버 (브레이크용) ❓ | IN | ❓ | BRK_PWM_GATED | |
| | | OUT | ❓ | BRK_G (R_BRKG 경유) | |
| | | VDD | ❓ | VCC_GD | STO1로 함께 차단 |
| | | GND | ❓ | PGND | |
| R_BRKG | 게이트 저항 | 1 / 2 | – | U3.OUT / BRK_G | |
| R_DIV1–3 | 332 kΩ 0805 직렬 | – | – | VBUS → DIV_A → DIV_B → VBUS_SNS | |
| R_DIV4 | 20.0 kΩ | 1 / 2 | – | VBUS_SNS / AGND | |
| C_DIV | 1 nF C0G | 1 / 2 | – | VBUS_SNS / AGND | |

---

## 3. P2 — 3상 브리지·션트

상 x ∈ {U, V, W}, 하이사이드 Q_H (Q1/Q3/Q5), 로우사이드 Q_L (Q2/Q4/Q6). TOLL 핀 배치(드레인 탭, 소스 다수 핀, 켈빈 소스 유무) ❓.

| Ref | 핀 | 넷 | 비고 |
|---|---|---|---|
| Q_H(x) | D (탭) | VBUS | |
| | S | PH_x | |
| | KS (켈빈, 있으면) ❓ | VS_x | 없으면 S 패드 근접에서 VS_x 분기 |
| | G | GH_x | |
| Q_L(x) | D (탭) | PH_x | |
| | S | SH_x_HI | 션트 상단 |
| | KS ❓ | GL_RTN_x | |
| | G | GL_x | |
| R_SH_x (0.5 mΩ 4단자) | I+ / I− | SH_x_HI / PGND | 전류 단자 |
| | S+ / S− | ISNS_x_P / ISNS_x_N | 켈빈 감지 → 증폭기 (P4) |
| R_DC (DNP, 0.5 mΩ) | I+ / I− | PGND_SH / PGND | 옵션 DC 링크 션트. 미실장 시 동판 단락 |
| RT1 (NTC 10 kΩ) | 1 / 2 | NTC1 / AGND | 로우사이드 소자 사이 |
| R_NTC1 (10 kΩ 0.1 %) | 1 / 2 | +3V3A / NTC1 | |

게이트 회로 (상별, 하이/로우 각각):

| Ref (예: U상 하이) | 핀 | 넷 |
|---|---|---|
| R_GON_UH (4.7 Ω) | 1 / 2 | HO_U / GH_U |
| D_GOFF_UH (쇼트키) | K / A | HO_U / GOFF_UH |
| R_GOFF_UH (2.2 Ω) | 1 / 2 | GOFF_UH / GH_U |
| R_GS_UH (10 kΩ) | 1 / 2 | GH_U / VS_U |

> 턴오프 가지: `HO_x —(K)D(A)— GOFF_xH —R_GOFF— GH_x`. 턴오프 때만 게이트 → 드라이버 방향으로 도통하고, 이때 R_GON과
> 병렬이 된다. 로우사이드도 같은 구조 (LO_x, GL_x, GOFF_xL, R_GS 하단은 GL_RTN_x).

---

## 4. P3 — 게이트 드라이버 U2: 6ED2742S01Q (PG-VQFN-32)

| 핀 이름 | 핀# | 넷 | 연결·부품 |
|---|---|---|---|
| VCC ❓ | ❓ | VCC_GD | C_VCC 10 µF + 1 µF + 100 nF → COM/VSS ❓ (디커플링 기준점 원문 확인) |
| VSS 🔍 | ❓ | GND (스타점 근접) | 로직 접지 |
| COM 🔍 | ❓ | PGND (세 션트 하단 공통점) | 로우사이드 게이트 리턴. R_DC 실장 시 PGND_SH |
| HIN1 / HIN2 / HIN3 ❓ | ❓ | PWM_UH_G / PWM_VH_G / PWM_WH_G | U42 (STO2 버퍼) 출력. 극성 ❓ |
| LIN1 / LIN2 / LIN3 ❓ | ❓ | PWM_UL_G / PWM_VL_G / PWM_WL_G | 극성 ❓ (액티브 로우면 풀업, 하이면 풀다운으로 기본 OFF) |
| HO1 / HO2 / HO3 ❓ | ❓ | HO_U / HO_V / HO_W | → 게이트 저항 (P2) |
| VS1 / VS2 / VS3 ❓ | ❓ | VS_U / VS_V / VS_W | = PH_x 의 켈빈 분기 |
| VB1 / VB2 / VB3 ❓ | ❓ | VB_U / VB_V / VB_W | C_BS_x 1 µF/25 V: VB_x – VS_x. 부트스트랩 다이오드 내장(🔍) → 외부 다이오드 없음 |
| LO1 / LO2 / LO3 ❓ | ❓ | LO_U / LO_V / LO_W | → 게이트 저항 (P2) |
| RFE 🔍 | ❓ | GD_RFE | 오픈드레인 ❓. 풀업 R → +3V3 ❓(로직 전압 원문 확인). MCU GD_FAULT 입력 + STO2 경로 오픈드레인 끌어내림 (Q41) + MCU GD_EN 오픈드레인 |
| ITRIP 🔍 | ❓ | GD_ITRIP | 기본: CSO에서 RC ❓ 또는 OC_HW(외부 비교) 옵션. 미사용 시 비활성 레벨 ❓ |
| ITRIP CONF 🔍 | ❓ | GD_ITRIP_CONF | 임계값 선택 — 저항/스트랩 방식 ❓ |
| CSO 🔍 | ❓ | GD_CSO | → MCU ADC (옵션, R_DC 실장 시 의미) |
| CSO GAIN 🔍 | ❓ | GD_CSO_GAIN | 이득 선택 — 스트랩 방식 ❓ |
| STR 🔍 | ❓ | GD_STR | 0점 시프트. 분압 또는 MCU DAC ❓ |
| VBAT / 차지펌프 / 기타 ❓ | ❓ | ❓ | "pre-regulated" 명칭상 배터리 입력·차지펌프 커패시터 핀 존재 가능 — 원문 확인 필수 |
| EP (노출 패드) ❓ | ❓ | ❓ (COM 또는 VSS) | |

---

## 5. P4 — 전류 증폭·바이어스 (상별 동일, x ∈ {U,V,W})

| Ref | 핀 | 넷 | 값/비고 |
|---|---|---|---|
| R_IN_xP, R_IN_xN | – | ISNS_x_P → AMP_x_INP / ISNS_x_N → AMP_x_INN | 차동 입력 저항 (G = R_F/R_IN = 20) |
| R_F_x | – | AMP_x_INN ↔ AMP_x_OUT | |
| R_REF_x | – | AMP_x_INP ↔ VBIAS_1V65 | 비반전측 기준 (= R_F_x) |
| U5x (앰프 ❓) | +IN / −IN / OUT / V+ / V− | AMP_x_INP / AMP_x_INN / AMP_x_OUT / +3V3A / AGND | 핀 번호 ❓ (부품 미선정) |
| R_AAF_x + C_AAF_x | – | AMP_x_OUT → I_x_ADC → AGND | 앤티에일리어싱. 컷오프는 ADC 샘플 창 확정 후 ❓ |
| U6 (기준 버퍼) | IN / OUT | VBIAS_DIV / VBIAS_1V65 | +3V3A 1:1 분압 → 버퍼 |

---

## 6. P5 — 보조 전원

| Ref | 부품 | 핀 (기능) ❓ | 핀# | 넷 |
|---|---|---|---|---|
| F1 | 칩 퓨즈 | 1 / 2 | – | VL_IN / VL_F |
| D1 | 쇼트키 ≥150 V | A / K | – | VL_F / VAUX |
| D2 (DNP) + R_OR (DNP) | 다이오드 + 돌입 제한 | A / K | – | VBUS → VAUX | 단일 전원 모드 |
| C_VAUX | MLCC ≥150 V | – | – | VAUX / GND |
| U10 | LM5169 → 12 V | VIN | ❓ | VAUX |
| | | EN/UVLO | ❓ | VAUX 분압 (UVLO 9–10 V ❓) |
| | | RON (주파수) | ❓ | R_ON10 → 500 kHz (식은 원문 ❓) |
| | | BST | ❓ | C_BST10 → SW10 |
| | | SW | ❓ | SW10 → L10 → +12V_GD |
| | | FB | ❓ | +12V_GD 분압 (V_REF 1.2 V 🔍 → R_top/R_bot = 9) |
| | | PGOOD | ❓ | PG_12V → MCU (풀업 +3V3) |
| | | GND / EP | ❓ | GND |
| U11 | LM5169 → 5 V | 동일 구조 | ❓ | 출력 +5V, FB 비 R_top/R_bot = 3.167, 400 kHz, PGOOD → PG_5V |
| U12 | LDO 5→3.3 V ❓ | IN / OUT / EN / GND | ❓ | +5V / +3V3 / +5V / GND |
| FB1 + C | 페라이트 LC | – | – | +3V3 → +3V3A |
| Q40 | 로드스위치 (STO1) ❓ | IN / OUT / ON | ❓ | +12V_GD / VCC_GD / STO1_EN |
| U13 | 엔코더 5 V 전류제한 스위치 ❓ | IN / OUT / EN / FLT | ❓ | +5V / ENC_5V / ENC_PWR_EN / ENC_PWR_FLT |

---

## 7. P7 — CAN FD·엔코더·디버그

### 7.1 U20 TLE9251VLE (PG-TSON-8)

핀 번호는 동종 CAN 트랜시버 통상 배치 기준 **미확인 ❓ — 원문 확인 필수**.

| 핀 이름 | 핀# | 넷 |
|---|---|---|
| TxD | ❓ | CAN_TX (MCU) |
| RxD | ❓ | CAN_RX (MCU) |
| VCC | ❓ | +5V (100 nF) |
| VIO | ❓ | +3V3 (100 nF) |
| GND / EP | ❓ | GND |
| CANH | ❓ | CANH → ESD → J1 |
| CANL | ❓ | CANL → ESD → J1 |
| STB | ❓ | CAN_STB (MCU, 기본 레벨 ❓) |
| 종단 | – | CANH–60 Ω–CAN_SPLIT–60 Ω–CANL, CAN_SPLIT–4.7 nF–GND, **솔더 점퍼 JP1** 직렬 |

### 7.2 엔코더

| Ref | 기능 | 입력 넷 | 출력 넷 (MCU) |
|---|---|---|---|
| U30 | RS-422 4ch 수신기 ❓ | ENC_A_P/N, ENC_B_P/N, ENC_Z_P/N (+120 Ω 종단 각) | ENC_A, ENC_B, ENC_Z |
| U32 | 슈미트 버퍼 3ch ❓ | HALL_U/V/W (4.7 kΩ → +5V 풀업, 1 kΩ/1 nF RC) | HALL_U_L, HALL_V_L, HALL_W_L |
| U31 | RS-485 트랜시버 ❓ | ABS_CLK_P/N (출력), ABS_DAT_P/N (양방향) | ABS_CLK, ABS_DAT_RX, ABS_DAT_TX, ABS_DE |

※ BiSS-C는 CLK 출력 + DATA 입력 2쌍 → 송신기 1 + 수신기 1 구성이 필요할 수 있음 (프로토콜 선택 후 확정 ❓).

### 7.3 디버그

| Ref | 핀 | 넷 |
|---|---|---|
| J2 (SWD 패드) | 1–5(+6) | +3V3, SWDIO, SWCLK, XRES, GND, (SWO) |
| J1 UART | – | UART_TX, UART_RX (100 Ω 직렬 + ESD) |

---

## 8. P8 — STO

| Ref | 핀 | 넷 | 비고 |
|---|---|---|---|
| R_STO1 / R_STO2 | – | STO1_P → U40.A / STO2_P → U41.A | 직렬 저항 = (5 V − V_F)/I_F, 값 ❓ (옵토 원문) |
| D_STO1/2 | – | 옵토 LED 역병렬 | 역전압 보호 |
| U40 (옵토) | A / K / C / E | STO1_P(R경유) / STO1_N / STO1_EN / GND | 출력 → Q40.ON (활성=전원 공급). 풀업 극성은 "입력 없음 = 차단"이 되도록 |
| U41 (옵토) | A / K / C / E | STO2_P(R경유) / STO2_N / STO2_OK / GND | → U42.OE, Q41 |
| U42 | 8ch 버퍼 (OE 내장) ❓ | 입력 PWM_UH…PWM_WL, BRK_PWM (MCU) / 출력 *_G / OE ← STO2_OK | OE 비활성 시 출력 Hi-Z → 게이트 드라이버 입력 풀다운(또는 풀업)으로 OFF 레벨 확정 |
| Q41 | NMOS 오픈드레인 | D=GD_RFE, G=STO2_OK 반전 ❓, S=GND | STO2 활성 시 RFE 강제 로우 |
| STO1_FB | – | VCC_GD 분압 → MCU | |
| STO2_FB | – | STO2_OK → MCU | |

---

## 9. P6 — MCU U1: PSC3M8 핀 배정

**전부 ❓.** PSC3M8 데이터시트의 핀맵(포트별 대체 기능 표: TCPWM 라인, HPPASS 아날로그 입력, CAN FD, SCB)을
확인하기 전에는 핀 번호를 쓰지 않는다. 아래는 **필요 신호 목록과 요구 주변장치**만이다.

| 신호 넷 | 방향 | 요구 주변장치 | 포트.핀 | 핀# | 제약 |
|---|---|---|---|---|---|
| PWM_UH / PWM_UL | O | TCPWM 상보 출력 쌍 (HRPWM 가능) | ❓ | ❓ | 3상이 **같은 TCPWM 그룹**에서 동기 |
| PWM_VH / PWM_VL | O | 동상 | ❓ | ❓ | |
| PWM_WH / PWM_WL | O | 동상 | ❓ | ❓ | |
| BRK_PWM | O | TCPWM | ❓ | ❓ | |
| PWM_KILL (외부, 옵션) | I | TCPWM kill/trigger 입력 | ❓ | ❓ | 내부 비교기 연결 가능하면 불필요 |
| I_U_ADC / I_V_ADC / I_W_ADC | AI | HPPASS SAR — **동시 샘플** + 비교기 입력 | ❓ | ❓ | 3채널 동시 샘플 가능한 입력 조합 ❓ |
| VBUS_SNS | AI | HPPASS SAR + 비교기 (BRK/OV) | ❓ | ❓ | |
| NTC1 (NTC2 옵션) | AI | SAR | ❓ | ❓ | |
| GD_CSO (옵션) | AI | SAR | ❓ | ❓ | |
| AIN_P / AIN_N | AI | SAR (차동 가능 여부 ❓) | ❓ | ❓ | 제품 사양 미확정 |
| VBIAS_1V65 (옵션) | AI | SAR (오프셋 보정) | ❓ | ❓ | |
| CAN_TX / CAN_RX | O / I | CAN FD0 | ❓ | ❓ | |
| CAN_STB | O | GPIO | ❓ | ❓ | |
| ENC_A / ENC_B / ENC_Z | I | TCPWM 쿼드러처 (count/up/index) | ❓ | ❓ | |
| HALL_U_L / V_L / W_L | I | GPIO 인터럽트 또는 TCPWM 캡처 | ❓ | ❓ | |
| ABS_CLK / ABS_DAT_RX / ABS_DAT_TX / ABS_DE | O/I/O/O | SCB (SPI 또는 UART) | ❓ | ❓ | |
| UART_TX / UART_RX | O / I | SCB UART | ❓ | ❓ | |
| SWDIO / SWCLK / SWO | IO / I / O | 전용 디버그 핀 | ❓ | ❓ | |
| XRES | I | 리셋 | ❓ | ❓ | 10 kΩ 풀업 + 100 nF ❓ |
| GD_FAULT (← GD_RFE) | I | GPIO 인터럽트 | ❓ | ❓ | |
| GD_EN (→ GD_RFE, 오픈드레인) | O | GPIO | ❓ | ❓ | |
| STO1_FB / STO2_FB | I | GPIO | ❓ | ❓ | |
| PG_12V / PG_5V | I | GPIO | ❓ | ❓ | |
| ENC_PWR_EN / ENC_PWR_FLT | O / I | GPIO | ❓ | ❓ | |
| DI1–DI4 / DO1–DO2 | I / O | GPIO | ❓ | ❓ | 제품 사양 미확정 |
| LED_STAT | O | GPIO | ❓ | ❓ | |
| XTAL_IN / XTAL_OUT (DNP) | – | 외부 수정 | ❓ | ❓ | 필요 여부 ❓ |
| VDDD / VDDA / VREF / VCCD 등 전원 핀 | – | +3V3 / +3V3A / 디커플링 | ❓ | ❓ | 전원 핀 목록·디커플링 값 원문 필요 |

### 9.1 PSC3M8 핀 배정 확인 필요 목록

1. 패키지별 핀맵 (VQFN-64 / LQFP-64 / LQFP-80) 과 I/O 가용 수
2. TCPWM: 상보 출력 쌍 + 하드웨어 데드타임 지원 카운터와 해당 출력 핀, HRPWM 지원 채널
3. TCPWM kill/stop 입력에 HPPASS 비교기를 **내부 연결**할 수 있는지 (트리거 멀티플렉서)
4. HPPASS: 동시 샘플 가능한 채널 그룹, 비교기 입력이 될 수 있는 핀, 최소 샘플 시간·샘플 커패시터
5. ADC 기준 전압 옵션 (VDDA / 내부 / 외부 VREF 핀)
6. CAN FD0/1 TX·RX 가능 핀
7. TCPWM 쿼드러처 디코더 입력 핀
8. SCB 핀 (SPI·UART), GPIO 5 V 내성 여부
9. 전원 핀 구성·디커플링 권장, 내부 레귤레이터 외부 커패시터 핀
10. SWD/SWO 핀, 부트 모드 핀
11. CAN FD 비트 타이밍을 위한 외부 수정 필요 여부 (IMO 정확도)
12. Ethernet/EtherCAT 부재 확인 (02b §5 #1)
