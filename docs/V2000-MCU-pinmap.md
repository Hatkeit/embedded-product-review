# V2000 MCU 핀맵 — STM32G474 (LQFP-128 QET / LQFP-100 VET 공통)

- 기준 도면: `sch_microinv_v2000.pdf` (2026-09-19판, 10 시트), 원본 S2G1812 리버스 도면(6 시트)
- 핀 기능 근거: ST STM32CubeMX 핀 데이터 `STM32G474QB-C-ETx.xml` / `STM32G474VB-C-ETx.xml` (핀 번호는 LQFP-128 기준, 괄호는 LQFP-100)
- 기준전압: TI **REF3030A** 3.0 V (사용자 선정, 2025-12 개정 데이터시트 SBVS032K 기준)
- 표기: ✔ 현 도면에 이미 결선 / ＋ 신규 결선 필요 / △ 포트명 변경 필요

## 1. 전력단 타이밍 — HRTIM1 (모두 한 타이머 블록)

| 신호(도면 포트명) | 역할 · 출처 시트 | 전기 특성 | G474 핀 | 기능 | 상태 |
|---|---|---|---|---|---|
| PWM_A1 | PV_A 1상 플라이백 게이트 (01 · U13 INA → Q1‖Q2) | 3.3 V 로직, 고속, 22 Ω 직렬 + 10 kΩ 풀다운 | PA8 (89 / 69) | HRTIM1_CHA1 | ＋ |
| PWM_A2 | PV_A 2상 (01 · U13 INB → Q3‖Q4) | 동일, A1 대비 180° | PA9 (90 / 70) | HRTIM1_CHA2 | ＋ |
| PWM_B1 | PV_B 1상 (02 · U14 INA → Q5‖Q6) | 동일 | PA10 (91 / 71) | HRTIM1_CHB1 | ＋ |
| PWM_B2 | PV_B 2상 (02 · U14 INB → Q7‖Q8) | 동일 | PA11 (92 / 72) | HRTIM1_CHB2 | ＋ |
| GATE_UNF_N (구 OFFPAGELEFT-L) | 언폴더 저압측 MOSFET Q13, AC_N 레그 (08 · U5A → ISO1A) | **액티브 로우**, 10 kΩ 풀업(R192), 60 Hz | PC8 (87 / 67) | HRTIM1_CHE1 | △＋ |
| GATE_UNF_L (구 OFFPAGELEFT-L) | 언폴더 저압측 MOSFET Q14, AC_L 레그 (08 · U5B → ISO1B) | 액티브 로우, 10 kΩ 풀업(R205) | PC9 (88 / 68) | HRTIM1_CHE2 | △＋ |
| GATE_AC_N | 고압측 SCR D23 점호 (03 · U1B → ISO2 MOC3063) | 액티브 로우, 10 kΩ 풀업(R76) | PC6 (80 / 65) | HRTIM1_CHF1 | ＋ |
| GATE_AC_L | 고압측 SCR D24 점호 (03 · U1A → ISO3) | 액티브 로우, 10 kΩ 풀업(R77) | PC7 (81 / 66) | HRTIM1_CHF2 | ＋ |
| FAULT_HW (구 OFFPAGELEFT-R) | 하드웨어 고장 플래그 (08 · 고장 버스 → U6F → ISO4 FOD817 → U5C/U5D → R187) | 액티브 로우, 3.3 V 도메인 | PA12 (93 / 73) | HRTIM1_FLT1 + EXTI12 | △＋ |
| RELAY_GRID | 계통 릴레이 LS1 구동 (03 · R91 → Q9) | 액티브 하이 GPIO | PB10 (62 / 47) | GPIO 출력 | ✔ |

HRTIM 배치: Timer A = PV_A 2상(CHA1/CHA2 위상 180°), Timer B = PV_B 2상, Timer E = 언폴더 MOSFET 2레그(하드웨어 데드타임), Timer F = SCR 점호 펄스, FLT1 = 하드웨어 고장으로 A·B·E·F 출력 즉시 차단. Timer C/D는 미사용이므로 PB12–PB15는 ADC로 쓴다.

## 2. 아날로그 — ADC1~5 · COMP1~4 (풀스케일 3.0 V = REF3030A)

| 신호 | 역할 · 출처 | 신호 범위(3.0 V 기준) | G474 핀 | 기능 | 상태 |
|---|---|---|---|---|---|
| ADC_I_PA1 | PV_A 1상 CST T1 피크 전류 (01 · D1/R4 2 Ω 부담 → R1 680 Ω) | 20 mV/A, 18 A → 0.36 V | PA1 (28 / 21) | ADC1_IN2 · **COMP1_INP** | ＋ |
| ADC_I_PA2 | PV_A 2상 CST T3 | 동일 | PA7 (36 / 29) | ADC2_IN4 · **COMP2_INP** | ＋ |
| ADC_I_PB1 | PV_B 1상 CST T5 | 동일 | PC1 (23 / 16) | ADC1_IN7·ADC2_IN7 · **COMP3_INP** | ＋ |
| ADC_I_PB2 | PV_B 2상 CST T7 | 동일 | PE7 (53 / 38) | ADC3_IN4 · **COMP4_INP** | ＋ |
| ADC_V_PA | PV_A 클램프 노드 전압 (07 · U3A, 1 MΩ/20 kΩ = 51:1) | 3.0 V ↔ 153 V | PA0 (27 / 20) | ADC1_IN1·ADC2_IN1 | ＋ |
| ADC_V_PB | PV_B 클램프 노드 전압 (07 · U3B) | 동일 | PA2 (29 / 22) | ADC1_IN3 | ＋ |
| ADC_I_PV_A | PV_A 입력 전류 (07 · U21 INA240A2, 3 mΩ ×50) | 0.15 V/A, 15 A → 2.25 V | PC2 (24 / 17) | ADC1_IN8·ADC2_IN8 | ＋ |
| ADC_I_PV_B | PV_B 입력 전류 (07 · U22) | 동일 | PC3 (25 / 18) | ADC1_IN9·ADC2_IN9 | ＋ |
| ADC_V_GRID_P / N | 계통 전압 (07 · U23 AMC3301 OUTP/OUTN, 1 kΩ + 4.7 nF) | 차동 ±~1.25 V, CM 1.44 V | PB14 (68 / 53) / PB15 (69 / 54) | ADC4_IN4(+)·ADC4_IN5(−) 차동 | ＋ |
| ADC_I_GRID_P / N | 계통 전류 (07 · U24 AMC3302, 10 mΩ) | 차동 ±~0.16 V | PE14 (60 / 45) / PE15 (61 / 46) | ADC4_IN1(+)·ADC4_IN2(−) 차동 | ＋ |
| ADC_I_GRID_Lk | 절연·누설 감시 (08 · U4A) | 저속 | PD12 (74 / 59) | ADC3/4/5_IN9 | ＋ |
| AIN1 | DC/DC MOSFET NTC (10) | 25 ℃ 1.25 V | PC4 (37 / 30) | ADC2_IN5 | ✔ |
| AIN2 | DC/AC MOSFET NTC | 〃 | PC5 (38 / 31) | ADC2_IN11 | ✔ |
| AIN3 | PV CAP NTC | 〃 | PB0 (39 / 32) | ADC1_IN15 | ✔ |
| AIN4 | DCLINK CAP NTC | 〃 | PB1 (40 / 33) | ADC1_IN12 | ✔ |
| (예비) ADC_V_10V0 | 원본 ADCINB2 보조 10 V 감시 복원 권장 | 100 k/20 k | PE13 (59 / 44) | ADC3_IN3 | 제안 |

COMP1~4의 반전 입력은 내부 DAC(DAC1_OUT1/2, DAC3)로 잡아 4상 각각의 사이클별 피크 전류 제한을 HRTIM 이벤트로 직결한다. 외부 핀 불필요.

## 3. 통신 · 디버그 · 시스템

| 신호 | 상대 | G474 핀 | 기능 | 상태 |
|---|---|---|---|---|
| UART0_TXD / UART0_RXD | ESP32-S3 IO18 / IO17 (06) | PD5 (115 / 87) / PD6 (116 / 88) | USART2_TX / USART2_RX | ✔ (ESP32 쪽 IO18=RX, IO17=TX로 펌웨어 매핑) |
| UART2_TXD_C / UART2_RXD_C | easyDSP J20 (05) | PC10 (100 / 79) / PC11 (101 / 80) | USART3_TX / USART3_RX | ✔ |
| CAN_TX / CAN_RX / CAN_NEN | TLE9251VSJ (06) | PD1 (109 / 83) / PD0 (108 / 82) / PD2 (112 / 84) | FDCAN1_TX / FDCAN1_RX / GPIO | ✔ |
| SWDIO_C / SWCLK_C / SWO_C | J19 (05) | PA13 (96 / 76) / PA14 (98 / 77) / PB3 (118 / 90) | SWD + SWO | ✔ |
| /BOOT_C | J20 핀 7, R112 10 kΩ 풀다운 | PB8-BOOT0 (123 / 95) | BOOT0 | ✔ |
| /RESET_C | J19/J20, R118 10 kΩ 풀업 | NRST (21 / 14) | NRST | ✔ |
| OSC_IN / OSC_OUT | Y1 24 MHz | PF0 (19 / 12) / PF1 (20 / 13) | HSE | ✔ |
| (예비) LED_ST1 / LED_ST2 | 상태 LED (원본 GPIO10/11) | PD3 (113 / 85) / PD4 (114 / 86) | GPIO | 제안 |

## 4. 전원 · 기준전압

| 핀 | 결선 | 비고 |
|---|---|---|
| VDD ×8 (LQFP-128) / VBAT | VDD_3V3 | ✔ 100 nF ×14 + 1 µF + 2.2 µF |
| VDDA (45) / VSSA (42) | VDDA_3V3 / GND | ✔ 100 nF + 4.7 µF |
| **VREF+a (43), VREF+b (44)** | **REF3030A OUT** — 두 핀을 함께 묶고 핀 옆에 100 nF + 1 µF | ＋ 현 도면 미결선 |
| REF3030A IN | **VCC_5V0**에서 10 Ω + 1 µF RC로 공급 (VDDA_3V3에서 공급하면 VIN 하한 VOUT+0.2 V = 3.2 V에 걸림) | 데이터시트 §6 권장 동작 조건 |
| REF3030A 규격 | 3.0 V ±0.2 %, 75 ppm/℃, 25 mA, SOT-23-3 | 정밀 필요 시 REF3030E(±0.1 %, 15 ppm/℃) 검토 |

## 5. 집계와 패키지

| 항목 | 수 |
|---|---|
| 신호 핀 (표 1~3, 예비 제외) | 38 |
| HRTIM 출력 / 고장 입력 | 8 / 1 |
| ADC 채널 (차동 2쌍 포함) | 17 |
| COMP 입력 겸용 | 4 |

위 핀은 전부 LQFP-100(STM32G474VET7, 105 ℃)에도 존재한다. LQFP-128(QET6, 85 ℃)을 유지할 이유가 없다.

## 6. 도면에서 바꿔야 할 포트명

| 현재 | 변경 | 이유 |
|---|---|---|
| OFFPAGELEFT-L (U5A 입력) | GATE_UNF_N | CAD 기본명, 두 레그가 같은 넷 |
| OFFPAGELEFT-L (U5B 입력) | GATE_UNF_L | 〃 |
| OFFPAGELEFT-R (U5D 출력) | FAULT_HW | 〃 |
| I_GIRD_Lk (03 시트) | I_GRID_Lk | 오타로 08 시트와 단절 |

## 부록 A. STM32G474 LQFP-128 ADC 핀 전수표 (ST CubeMX 핀 데이터 STM32G474QB-C-ETx.xml)

42핀 · 채널 매핑 74개 (ADC1 14 · ADC2 16 · ADC3 15 · ADC4 16 · ADC5 13). 괄호는 LQFP-100 핀 번호.
차동 입력은 같은 ADC의 INx(+)와 INx+1(−) 조합만 가능하다.

| 핀 | 포트 | ADC 채널 | COMP | DAC | HRTIM | V2000 배정 |
|---|---|---|---|---|---|---|
| 19 (12) | PF0 | ADC1_IN10 |  |  |  | OSC_IN |
| 20 (13) | PF1 | ADC2_IN10 | COMP3_INM |  |  | OSC_OUT |
| 22 (15) | PC0 | ADC1_IN6, ADC2_IN6 | COMP3_INM |  |  |  |
| 23 (16) | PC1 | ADC1_IN7, ADC2_IN7 | COMP3_INP |  |  | ADC_I_PB1 |
| 24 (17) | PC2 | ADC1_IN8, ADC2_IN8 |  |  |  | ADC_I_PV_A |
| 25 (18) | PC3 | ADC1_IN9, ADC2_IN9 |  |  |  | ADC_I_PV_B |
| 27 (20) | PA0 | ADC1_IN1, ADC2_IN1 | COMP1_INM, COMP3_INP |  |  | ADC_V_PA |
| 28 (21) | PA1 | ADC1_IN2, ADC2_IN2 | COMP1_INP |  |  | ADC_I_PA1 |
| 29 (22) | PA2 | ADC1_IN3 | COMP2_INM |  |  | ADC_V_PB |
| 32 (25) | PA3 | ADC1_IN4 | COMP2_INP |  |  |  |
| 33 (26) | PA4 | ADC2_IN17 | COMP1_INM | DAC1_OUT1 |  |  |
| 34 (27) | PA5 | ADC2_IN13 | COMP2_INM | DAC1_OUT2 |  |  |
| 35 (28) | PA6 | ADC2_IN3 |  | DAC2_OUT1 |  |  |
| 36 (29) | PA7 | ADC2_IN4 | COMP2_INP |  |  | ADC_I_PA2 |
| 37 (30) | PC4 | ADC2_IN5 |  |  |  | AIN1 |
| 38 (31) | PC5 | ADC2_IN11 |  |  |  | AIN2 |
| 39 (32) | PB0 | ADC1_IN15, ADC3_IN12 | COMP4_INP |  | HRTIM1_FLT5 | AIN3 |
| 40 (33) | PB1 | ADC1_IN12, ADC3_IN1 | COMP1_INP |  |  | AIN4 |
| 41 (34) | PB2 | ADC2_IN12 | COMP4_INM |  |  |  |
| 53 (38) | PE7 | ADC3_IN4 | COMP4_INP |  |  | ADC_I_PB2 |
| 54 (39) | PE8 | ADC3_IN6, ADC4_IN6, ADC5_IN6 | COMP4_INM |  |  |  |
| 55 (40) | PE9 | ADC3_IN2 |  |  |  |  |
| 56 (41) | PE10 | ADC3_IN14, ADC4_IN14, ADC5_IN14 |  |  |  |  |
| 57 (42) | PE11 | ADC3_IN15, ADC4_IN15, ADC5_IN15 |  |  |  |  |
| 58 (43) | PE12 | ADC3_IN16, ADC4_IN16, ADC5_IN16 |  |  |  |  |
| 59 (44) | PE13 | ADC3_IN3 |  |  |  | (예비) ADC_V_10V0 |
| 60 (45) | PE14 | ADC4_IN1 |  |  |  | ADC_I_GRID_P |
| 61 (46) | PE15 | ADC4_IN2 |  |  |  | ADC_I_GRID_N |
| 65 (50) | PB11 | ADC1_IN14, ADC2_IN14 | COMP6_INP |  | HRTIM1_FLT4 |  |
| 66 (51) | PB12 | ADC1_IN11, ADC4_IN3 | COMP7_INM |  | HRTIM1_CHC1 |  |
| 67 (52) | PB13 | ADC3_IN5 | COMP5_INP |  | HRTIM1_CHC2 |  |
| 68 (53) | PB14 | ADC1_IN5, ADC4_IN4 | COMP7_INP |  | HRTIM1_CHD1 | ADC_V_GRID_P |
| 69 (54) | PB15 | ADC2_IN15, ADC4_IN5 | COMP6_INM |  | HRTIM1_CHD2 | ADC_V_GRID_N |
| 70 (55) | PD8 | ADC4_IN12, ADC5_IN12 |  |  |  |  |
| 71 (56) | PD9 | ADC4_IN13, ADC5_IN13 |  |  |  |  |
| 72 (57) | PD10 | ADC3_IN7, ADC4_IN7, ADC5_IN7 | COMP6_INM |  |  |  |
| 73 (58) | PD11 | ADC3_IN8, ADC4_IN8, ADC5_IN8 | COMP6_INP |  |  |  |
| 74 (59) | PD12 | ADC3_IN9, ADC4_IN9, ADC5_IN9 | COMP5_INP |  |  | ADC_I_GRID_Lk |
| 75 (60) | PD13 | ADC3_IN10, ADC4_IN10, ADC5_IN10 | COMP5_INM |  |  |  |
| 76 (61) | PD14 | ADC3_IN11, ADC4_IN11, ADC5_IN11 | COMP7_INP |  |  |  |
| 89 (69) | PA8 | ADC5_IN1 |  |  | HRTIM1_CHA1 | PWM_A1 |
| 90 (70) | PA9 | ADC5_IN2 |  |  | HRTIM1_CHA2 | PWM_A2 |

## 부록 B. 원본 TMS320F28034 핀 → STM32G474 대응표

근거: S2G1812 리버스 도면의 `U500-TMS320F28034-xxx` 포트 라벨(46개, 시트 00/01/02/03/04/05)과 V2000 도면 넷리스트.
GPIO41~44는 뒤의 언폴더 구동 분석(docs/ac-unfolder-drive-protection.html)대로 4개 모두 **MCU → 옵토 지령 출력**이다(이식 검토서 §2.4의 "극성 검출 입력" 분류는 이 표로 대체).

### B-1. ADC 16채널

| F28034 | 원본 회로 (시트) | 원본 기능 | V2000 대응 신호 | G474 핀 (128 / 100) | 기능 | 판정 |
|---|---|---|---|---|---|---|
| ADCINA0 | U400A → R407/R406/C400 (03) | AC-L 전압, RC 필터 경로 | ADC_V_GRID_P/N (AMC3301, 절연) | PB14 (68/53) / PB15 (69/54) | ADC4_IN4/IN5 차동 | 대체 |
| ADCINA1 | U400B R411 62k / R414 130k (03) | AC 차동(L−N) 전압 | ADC_V_GRID_P/N 로 통합 | 〃 | 〃 | 대체 |
| ADCINA2 (COMP1A) | TR100 → D100/R102/R101 (04) | PVA 1상 피크 전류 + 비교기 | ADC_I_PA1 | PA1 (28/21) | ADC1_IN2 + COMP1_INP | 동일 |
| ADCINA3 | R433 1M / R435 51k → U403A (03) | PVA+ 전압 (고게인) | **없음 → 추가 권장** ADC_V_PVA | PC0 (22/15) | ADC1_IN6·ADC2_IN6 | 추가 |
| ADCINA4 (COMP2A) | TR101 → D104/R111/R110 (04) | PVA 2상 피크 전류 + 비교기 | ADC_I_PA2 | PA7 (36/29) | ADC2_IN4 + COMP2_INP | 동일 |
| ADCINA5 | U502/R510 전부 NC (02) | 미실장 옵션 | 없음 | — | — | 삭제 |
| ADCINA6 (COMP3A) | U400A 직결 (03) | AC-L 고속 경로, 영교차 비교기 | 영교차 → COMP7 (PB14 = COMP7_INP, 내부 DAC 기준) | PB14 공용 | COMP7 → HRTIM EEV / TIM 캡처 | 대체 |
| ADCINA7 | R434 1M / R436 51k → U403B (03) | PVB+ 전압 (고게인) | **없음 → 추가 권장** ADC_V_PVB | PA3 (32/25) | ADC1_IN4 | 추가 |
| ADCINB0 | 3 mΩ R103 → U405A TP5592 (01) | PVA 입력 전류 | ADC_I_PV_A (INA240A2) | PC2 (24/17) | ADC1_IN8·ADC2_IN8 | 동일 |
| ADCINB1 | 3 mΩ R203 → U405B (03) | PVB 입력 전류 | ADC_I_PV_B | PC3 (25/18) | ADC1_IN9·ADC2_IN9 | 동일 |
| ADCINB2 | R454 100k / R457 20k (02) | 보조 10 V 레일 감시 | **없음 → 추가 권장** ADC_V_10V0 | PE13 (59/44) | ADC3_IN3 | 추가 |
| ADCINB3 | U402A → R421/C410 (03) | AC-N 전압, RC 필터 경로 | ADC_V_GRID_P/N 로 통합 | PB14 / PB15 | 〃 | 대체 |
| ADCINB4 (COMP2B) | R214/R215 2M + R416/R417 1M → U402B (00) | PV 버스 절연·누설 감시 | ADC_I_GRID_Lk (U4A) | PD12 (74/59) | ADC3/4/5_IN9 | 동일 |
| ADCINB5 | R429 1M / R437 20k → U404A (04) | PVA 클램프 노드 전압 (저게인) | ADC_V_PA (U3A) | PA0 (27/20) | ADC1_IN1·ADC2_IN1 | 동일 |
| ADCINB6 (COMP3B) | U402A 직결, U406B 기준 분기 (03, 05) | AC-N 고속 경로 + PVB 전류제한 기준 | 영교차는 COMP7, 전류제한 기준은 내부 DAC | — | — | 내부화 |
| ADCINB7 | R441 1M / R449 20k → U404B (05) | PVB 클램프 노드 전압 | ADC_V_PB (U3B) | PA2 (29/22) | ADC1_IN3 | 동일 |
| (원본 없음) | — | PVB 1·2상 피크 전류 (원본은 TP1946 비교기만) | ADC_I_PB1 / ADC_I_PB2 (CST T5/T7) | PC1 (23/16) / PE7 (53/38) | ADC1_IN7 + COMP3_INP / ADC3_IN4 + COMP4_INP | 신설 |
| (원본 없음) | — | 계통 전류 (원본은 언폴더 션트 하드웨어만) | ADC_I_GRID_P/N (AMC3302) | PE14 (60/45) / PE15 (61/46) | ADC4_IN1/IN2 차동 | 신설 |
| (원본 없음) | — | NTC 4채널 | AIN1~4 | PC4 / PC5 / PB0 / PB1 | ADC2_IN5 / ADC2_IN11 / ADC1_IN15 / ADC1_IN12 | 신설 |

### B-2. GPIO · 통신 · 디버그

| F28034 | 원본 기능 (시트) | V2000 대응 | G474 핀 (128 / 100) | 기능 | 판정 |
|---|---|---|---|---|---|
| GPIO0 (EPWM1A) | PVA 1상 → U100 INA (04) | PWM_A1 → U13 INA | PA8 (89/69) | HRTIM1_CHA1 | 동일 |
| GPIO2 (EPWM2A) | PVA 2상 → U100 INB (04) | PWM_A2 → U13 INB | PA9 (90/70) | HRTIM1_CHA2 | 동일 |
| GPIO4 (EPWM3A) | PVB 1상 → U200 INA (05) | PWM_B1 → U14 INA | PA10 (91/71) | HRTIM1_CHB1 | 동일 |
| GPIO6 (EPWM4A) | PVB 2상 → U200 INB (05) | PWM_B2 → U14 INB | PA11 (92/72) | HRTIM1_CHB2 | 동일 |
| GPIO41 | SCR AC_N 측 점호 지령, 10k 풀업 (00) | GATE_AC_N → U1B → ISO2 | PC6 (80/65) | HRTIM1_CHF1 | 동일 |
| GPIO42 | SCR AC_L 측 점호 지령 (00) | GATE_AC_L → U1A → ISO3 | PC7 (81/66) | HRTIM1_CHF2 | 동일 |
| GPIO43 | 언폴더 MOSFET S300 AC_L 측 (00) | GATE_UNF_L (구 OFFPAGELEFT-L, U5B) | PC9 (88/68) | HRTIM1_CHE2 | 동일 |
| GPIO44 | 언폴더 MOSFET S301 AC_N 측 (00) | GATE_UNF_N (구 OFFPAGELEFT-L, U5A) | PC8 (87/67) | HRTIM1_CHE1 | 동일 |
| GPIO12 (TZ1) | 언폴더 과전류 트립 ← FOD817 (00) | FAULT_HW (구 OFFPAGELEFT-R) | PA12 (93/73) | HRTIM1_FLT1 + EXTI | 동일 |
| GPIO13 (TZ2) | PVB 과전류 트립 ← TP1946 ×2 wired-OR (05) | CST + COMP3/COMP4 내부 → HRTIM 이벤트 | — (외부 비교기 유지 시 PA15 = HRTIM1_FLT2) | — | 내부화 |
| GPIO14 | AC 릴레이 K300 구동 (00, 본 변형 NC) | RELAY_GRID → R91 → Q9 | PB10 (62/47) | GPIO | 동일 |
| GPIO24 (ECAP1) | 계통 영교차 캡처 ← U401 SGM8709 (03) | COMP7 (PB14) 출력 → HRTIM EEV / TIM 캡처 | 추가 핀 없음 | — | 내부화 |
| GPIO10 / GPIO11 | 상태 LED D501(RED) / D503(GREEN) (02) | 없음 → LED_ST1 / LED_ST2 제안 | PD3 (113/85) / PD4 (114/86) | GPIO | 제안 |
| GPIO28 / GPIO29 (SCI-A) | HM2401 RF 모듈 UART (02) | ESP32-S3 UART0 | PD6 (116/88) RX / PD5 (115/87) TX | USART2 | 대체 |
| GPIO8, 16, 17, 18, 19, 25 | RF 모듈 SPI·제어·리셋 (02) | 무선은 ESP32가 담당, TPM은 ESP32 SPI | — | — | 삭제 |
| GPIO32 / GPIO33 (I²C) | 24AA64 EEPROM (02) | 없음. 필요 시 I2C1 | PA15 (99/78) SCL / PB7 (122/94) SDA | I2C1 | 선택 |
| GPIO39, 40, 9, 15 | 확장 헤더 P503 (02) | 없음. 예비 | PE0 (125/97) / PE1 (126/98) / PD7 (117/89) / PB4 (119/91) | GPIO | 예비 |
| TCK / TMS / TDI / TDO / TRST_N | JTAG (02) | SWD | PA14 (98/77) SWCLK / PA13 (96/76) SWDIO / PB3 (118/90) SWO | SWD | 대체 |
| XRS_N | 리셋 | /RESET_C | NRST (21/14) | NRST | 동일 |
| (원본 없음) | — | easyDSP UART, CAN FD | PC10/PC11 USART3, PD0/PD1/PD2 FDCAN1 | | 신설 |

### B-3. 검증 결과

- 원본 라벨 46개 중 동일 기능 매핑 20개, 절연 센싱으로 대체 6개, 내부 주변장치로 흡수 3개(TZ2, ECAP1, COMP3B 기준), 삭제 8개(RF 모듈·ADCINA5·TRST), 선택/예비 8개.
- 원본에 있으나 V2000에 없는 감시 3개(PVA+/PVB+ 직접 전압, 보조 10 V)는 추가를 권장하며 핀을 미리 잡아 두었다: PC0, PA3, PE13.
- 위 핀 전부 LQFP-128·LQFP-100 양쪽에 존재하며 기존 핀맵(§1~§3)과 충돌이 없다.

## 부록 C. 실제 넷리스트 대조 — 확정 핀맵 (pstxnet.dat, PSTWRITER 17.4, 2026-09-20 00:46)

OrCAD 패키저 출력(pstxnet/pstxprt/pstchip)을 파싱해 U16 128핀 전부와 명명 넷 99개를 대조했다.
PDF 복원 넷리스트가 아니라 **실제 넷리스트**이므로 이 부록이 §1~§3·부록 B보다 우선한다.

### C-1. U16에 실제 결선된 신호 — 핀맵과 일치 (그대로 확정)

| 신호 (넷 이름) | U16 핀 | 기능 | 판정 |
|---|---|---|---|
| PWM_A1 / PWM_A2 / PWM_B1 / PWM_B2 | PA8 / PA9 / PA10 / PA11 | HRTIM1 CHA1·CHA2·CHB1·CHB2 | ✔ |
| GATE_AC_N / GATE_AC_L | PC6 / PC7 | HRTIM1 CHF1 / CHF2 | ✔ |
| ADC_V_PA1 / ADC_V_PA2 (CST T1/T3 피크 전류) | PA1 / PA7 | ADC1_IN2+COMP1_INP / ADC2_IN4+COMP2_INP | ✔ (이름은 전류이므로 ADC_I_PA1/PA2 권장) |
| ADC_V_PB1 / ADC_V_PB2 (CST T5/T7) | PC1 / PE7 | ADC1_IN7+COMP3_INP / ADC3_IN4+COMP4_INP | ✔ (동일) |
| ADC_V_PA / ADC_V_PB (클램프 노드 전압) | PA0 / PA2 | ADC1_IN1 / ADC1_IN3 | ✔ |
| ADC_V_GRID_L (AMC3301 OUTN 측) | PB14 | ADC4_IN4 (+) | ✔ |
| ADC_I_GRID_P (AMC3302 OUTP) | PE14 | ADC4_IN1 (+) | ✔ |
| ADC_I_GRID_N (AMC3302 OUTN) | PE15 | ADC4_IN2 (−) | ✔ |
| ADC_I_GRID_LK | PD12 | ADC3_IN9 | ✔ |
| AIN1~AIN4 | PC4 / PC5 / PB0 / PB1 | ADC2_IN5 / ADC2_IN11 / ADC1_IN15 / ADC1_IN12 | ✔ |
| RELAY_GRID | PB10 | GPIO | ✔ |
| UART0_TXD / UART0_RXD ↔ ESP32 IO18 / IO17 | PD5 / PD6 | USART2 | ✔ |
| UART2_TXD_C / UART2_RXD_C ↔ J20 | PC10 / PC11 | USART3 | ✔ |
| CAN_TX / CAN_RX / CAN_NEN | PD1 / PD0 / PD2 | FDCAN1 | ✔ |
| SWDIO_C / SWCLK_C / SWO_C | PA13 / PA14 / PB3 | SWD | ✔ |
| /BOOT_C (R112 풀다운) / /RESET_C (R118 풀업) | PB8 / NRST | | ✔ |
| OSC_IN / OSC_OUT | PF0 / PF1 | HSE | ✔ |
| VDD_3V0 (U27 REF3030A OUT, C200 100 nF + C201 4.7 µF) | VREF+A(43) · VREF+B(44) | 기준전압 | ✔ 핀 1 IN·2 OUT·3 GND 데이터시트와 일치 |

### C-2. 겹치는 신호 · 미결선 — 수정 후 확정

| # | 넷리스트 상태 | 문제 | 확정 조치 |
|---|---|---|---|
| X1 | **ADC_I_GRID_N이 PE15와 PB15 두 핀**에 붙어 있고, ADC_V_GRID_N은 C156·R175에만 있어 MCU 미결선 | 같은 넷이 두 ADC 핀에 병렬, 계통 전압 (−) 미결선 | PB15를 ADC_I_GRID_N에서 떼어 **ADC_V_GRID_N → PB15 (ADC4_IN5)** |
| X2 | **ADC_I_PA** 넷 = R157(U2A OPA2387 출력) + R166(U21 INA240 출력) + C127 + C135, MCU 미결선. ADC_I_PB 동일(R156 + R171) | op-amp 출력 두 개가 한 넷에 묶임 | U2 OPA2387 블록 삭제(R152~R160, C123·C125·C126·C127·C128). INA240 출력만 남겨 **ADC_I_PA → PC2 (ADC1_IN8), ADC_I_PB → PC3 (ADC1_IN9)** |
| X3 | **ADC1** 넷 = R187 + C167 = 고장 플래그(U5D 출력) | 이름이 ADC 계열과 겹치고 MCU 미결선 | **FAULT_HW로 개명 → PA12 (HRTIM1_FLT1)** |
| X4 | **IO1** = R194(U5A 입력), **IO2** = R208(U5B 입력), MCU 미결선 | 언폴더 MOSFET 지령 두 레그. 이전 판의 OFFPAGELEFT-L 공유는 해소됨 | **IO1 → GATE_UNF_N → PC8 (CHE1), IO2 → GATE_UNF_L → PC9 (CHE2)** |
| X5 | **ADC2·ADC3·ADC4·ADC5·IO3** = 09 시트 U10/U11/U12(20 mΩ·비절연 op-amp 블록) 출력, MCU 미결선 | 전회 C3. AMC3301과 기능 중복 | 블록 삭제. 유지가 강행되면 PD13 / PD14 / PD10 / PD11 (ADC3/4/5) · IO3 → PB6 (TIM4_CH1) |
| X6 | ADC_V_PA1/PA2/PB1/PB2 는 CST **전류** 신호, ADC_V_PA/PB 는 **전압** 신호 | 접두어 V/I 혼동 | CST 신호를 ADC_I_PA1/PA2/PB1/PB2 로 개명 (핀은 그대로) |
| X7 | U27 REF3030A IN = VDD_3V3 | 데이터시트 VIN 하한 = VOUT + 0.2 V = 3.2 V, 3.3 V 레일 여유 0.1 V | IN을 VCC_5V0 + 10 Ω/1 µF 로 |

### C-3. 핀맵보다 먼저 고쳐야 할 넷리스트 오류 (치명)

| # | 넷리스트 근거 | 문제 |
|---|---|---|
| G1 | **GND 넷에 01·02 시트 부품이 하나도 없다.** Q1~Q8 소스, U13/U14 GND, EC2~EC6·EC8~EC12 (−), C10~C20 등 30핀이 **I_PV_A+ / I_PV_B+** 넷에만 있고, 그 넷의 시트 밖 연결은 U21/U22 IN+ 한 핀뿐 | DC-DC 전력단 귀환이 시스템 GND에서 떠 있다. PV 전류의 귀환 경로도, 보조전원(04 시트, GND 기준)의 귀환 경로도 없다. R6/R43 션트의 GND 측(I_PV_A+ / I_PV_B+)을 GND에 한 점으로 연결해야 한다 |
| G2 | **PV_A-** 넷 = C68·C70·R101(04 시트) + R159(07 시트)뿐, **PV_B-** 넷 = R158 한 핀. PV 단자 J3/J4/J8/J9 는 I_PV_A- / I_PV_B- 넷 | 04·07 시트의 PV_A-/PV_B- 전원 심볼이 PV 단자와 다른 넷. R101 2 mΩ은 어디에도 이어지지 않은 GND 션트가 됐고, U2A/U2B 입력도 떠 있다 | 
| G3 | **PV_A+** 넷에 02 시트 C35·C36·T7 핀 4·5·6·8 포함 (PV_B+ 넷은 T5만) | 전회 N1 그대로. PV_B 2상 1차가 PV_A+ |
| G4 | U21/U22 INA240 심볼 핀 번호: 2=IN+, 3=IN−, 8=OUT, 5=VS, 6=REF2, 7=REF1 | **해결 — 데이터시트(SBOS662C, PW 패키지) 핀 배열과 정확히 일치.** 앞서 "실물과 반대로 보인다"고 한 것은 제 오류(SOIC D 패키지 배열과 혼동). IN+ = 션트 GND측(I_PV_A+), IN− = PV 단자측(I_PV_A-)이므로 귀환 전류에 대해 출력은 양(+) |
| G5 | 'NC' 넷 131핀 (U16 미사용 핀, U17 IO, U19 NC 핀, T1.2 등) | OrCAD 무접속 의사 넷으로 보이나(경로 없는 C_SIGNAL='NC'), Allegro에서 NC 넷 래츠가 생기지 않는지 확인 |
| G6 | 그 밖에 전회 지적이 그대로임: VCC_3V3 소스 없음(C8), Q9 소스 GND ↔ LS1 코일 VCC_12V0(C4), USB VBUS = VCC_5V0(N5), TLE9251 VIO = 5 V(H3) | |

### C-4. 확정 핀맵 집계

| 구분 | 핀 |
|---|---|
| 이미 결선·확정 (C-1) | 38핀 (VREF+ 2핀 포함) |
| 추가 결선 (C-2) | PB15 ADC_V_GRID_N · PC2 ADC_I_PA · PC3 ADC_I_PB · PA12 FAULT_HW · PC8 GATE_UNF_N · PC9 GATE_UNF_L |
| 예비 (미결선 유지) | PC0/PA3 PV 직접 전압, PE13 10 V 감시, PD3/PD4 LED, PA15/PB7 I2C |

수정 순서: G1·G2·G3 (접지·전원 넷) → X1~X5 (핀 결선·삭제) → X6·X7.

## 부록 D. 데이터시트 대조로 닫은 항목 (2026-09-20 업로드분)

| 부품 | 데이터시트 | 확인 내용 | 넷리스트 심볼 대조 | 검토 항목 |
|---|---|---|---|---|
| INA240A2PWR | TI SBOS662C (2021-12) | PW(TSSOP-8): 1 NC, 2 IN+, 3 IN−, 4 GND, 5 VS, 6 REF2, 7 REF1, 8 OUT. 게인 50 V/V, 출력 스윙 VS−0.2 V ~ GND+10 mV, BW 400 kHz | U21/U22 핀 번호·이름 **일치** | G4 해결. 3.3 V 공급에서 출력 상한 3.1 V > ADC 풀스케일 3.0 V, 15 A → 2.25 V 이내 |
| AMC3301-Q1 (DWE) | TI SBASA73A (2021-05) | 1 DCDC_OUT … 6 INP, 7 INN, 8 HGND, 9 GND, 10 OUTN, 11 OUTP, 12 VDD, 13 LDO_OUT, 14 DIAG, 15 DCDC_GND, 16 DCDC_IN. 게인 8.2 V/V, 출력 CM 1.44 V(1.39~1.49), 클리핑 ±2.49 V 차동 | U23 핀 번호·이름 **일치**. HGND/DCDC_HGND/INN = V_GRID_L, INP = V_GRID_N, DCDC_GND/GND = GND | 각 출력 단자 스윙 0.20~2.69 V → 3.0 V 풀스케일 이내. 152 mV pk 입력 → ±1.25 V 차동 |
| AMC3302 (DWE) | TI SBASA11B (2021-07) | 핀 배열 AMC3301과 동일. 게인 41 V/V, CM 1.44 V, 클리핑 ±2.49 V | U24 **일치**. HGND = I_GRID_N, INP = I_GRID_P | 32 mV pk 입력 → ±1.31 V 차동, 여유 충분 |
| SCS205KNHR | ROHM TSQ50244 Rev.001 (2024-09) | SiC SBD 1200 V / 5 A (Tc 148 ℃), I_FRM 26 A, V_F 1.4 V typ @5 A, Q_C 12 nC, TO-263-2L: 1 K, 2 K, 3 A | D3/D8/D14/D19 1=K1, 2=K2, 3=A **일치** | 전회 M7 해결. 원본 B1D02120E(1200 V)와 동급. 2차 평균 전류 ≈ 0.8 A, 피크 수 A 이내 |
| MOC3063S-TA | Lite-On DS70-2001-026 Rev.F (2019-05) | 제로크로스 트라이액 드라이버. I_FT ≤ 5 mA, V_F 1.2~1.4 V, V_DRM 600 V, dv/dt 1000 V/µs, V_TM 3 V @100 mA, **억제 전압 V_INH 5 V typ / 20 V max**, I_H 200 µA. 핀 1 A, 2 K, 3 NC, 4 MT1, 5 NC, 6 MT2 | ISO2/ISO3 **일치** (2 → GND, 4 → D25/D26 MURS1JAL, 6 → R79/R81 200 Ω ← PHV) | LED 전류: SN74HC14 3.3 V, R78 300 Ω → ≈ (3.0−1.3)/300 = 5.7 mA, I_FT 5 mA 대비 여유 14 %. **R78/R80 → 220 Ω(≈7.7 mA) 권장**. H8 수치화: 60 Hz 311 V pk의 영교차 기울기 117 V/ms → V_INH 5 V(typ)는 영교차 후 43 µs, 20 V(max)는 170 µs. 이 창을 놓치면 다음 반주기까지 점호 불가 |

| LM5156H | TI SNVSBV2 (2020-09) | HTSSOP-14: 1 BIAS, 2 NC, 3 VCC, 4 GATE, 5 PGND, 6 AGND, 7 CS, 8 COMP, 9 DITHOFF, 10 FB, 11 SS, 12 RT, 13 PGOOD, 14 EN/UVLO/SYNC, EP. **V_REF 1.00 V(0.99~1.01), V_CLTH 100 mV(93~107) CS-PGND, UVLO 1.5 V 상승/1.45 V 하강, I_SS 10 µA, VCC 6.85 V, f_RT = 2.21×10¹⁰/(R_RT+955)** | U15 핀 번호·이름 **일치** (PGND·AGND·EPAD·DITHOFF → GND) | N3 확정: 10 k/47.5 k → 1.21 V. C7 확정: 1 mΩ × 100 mV → 100 A, 1.7 A 피크 기준 47 mΩ. N9 확정: SS 10 µF → 1 s. UVLO 121 k/11 k → 18.0 V 상승 / 17.4 V 하강 ✓ (시트 주기 UVP 18 V와 일치). **신규 N12: R110 RT = 10 kΩ → f_sw ≈ 2.0 MHz.** 100 kHz는 220 kΩ, 200 kHz는 110 kΩ. 2 MHz는 6권선 플라이백·100 V FET·PMEG 클램프에 맞지 않음 |
| PA1005.100NLT | Pulse SPM2007_58 (2019-02) | 1:100, 정격 20 A, 2차 인덕턴스 2.0 mH min, DCR 1차 0.75 mΩ / 2차 5.5 Ω, Hipot 1000 Vrms, 20 kHz~1 MHz. 1차 8-7, 2차 1-3. B_pk = 37.59·V_ref·D_max·10⁵/(N·f_kHz) ≤ 2000 G | T1/T3/T5/T7: 1차 8→7 사용, 4·5·6은 PV+ 측에 묶임(전류 경로 아님), 2차 1-3, 2 NC **일치** | M7의 CST 부분 해결. V·s 검증: 부담 2 Ω(V_ref 0.36 V, D 0.45, 100 kHz) → 61 G, 부담 10 Ω → 304 G. 둘 다 2000 G 대비 충분 → 부담 10 Ω 상향 가능 |
| IAUCN10S7L040 | Infineon Rev.1.0 (2025-07) | OptiMOS 7, PG-TDSON-8, V_DS 100 V, R_DS(on) 3.95 mΩ, I_D 131 A(칩), Q_g 50.6 nC typ / 66 max @10 V, Q_gd 7.4 nC, V_plateau 3.0 V, E_AS 68 mJ, V_GS ±16 V, T_j 175 ℃ | Q1~Q8·Q10 | H1·N7 유지: 정격 100 V 그대로. 게이트 구동: 상당 2개 병렬 Q_g ≈ 100 nC, 100 kHz → 평균 10 mA, 2EDN7524R 5 A 여유. LM5156 VCC 6.85 V 구동에서는 R_DS(on)이 10 V 조건보다 높음(데이터시트 4.5 V 곡선 대조 필요) |

남은 미확보: LF19S-102-8A (권선 핀 대응) 하나.
