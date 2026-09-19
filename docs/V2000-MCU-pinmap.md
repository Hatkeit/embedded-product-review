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
| GPIO32 / GPIO33 (I²C) | 24AA64 EEPROM (02) | 없음. 필요 시 I2C1 | PA15 (99/77) SCL / PB7 (122/93) SDA | I2C1 | 선택 |
| GPIO39, 40, 9, 15 | 확장 헤더 P503 (02) | 없음. 예비 | PE0 (125/97) / PE1 (126/98) / PD7 (117/89) / PB4 (119/91) | GPIO | 예비 |
| TCK / TMS / TDI / TDO / TRST_N | JTAG (02) | SWD | PA14 (98/77) SWCLK / PA13 (96/76) SWDIO / PB3 (118/90) SWO | SWD | 대체 |
| XRS_N | 리셋 | /RESET_C | NRST (21/14) | NRST | 동일 |
| (원본 없음) | — | easyDSP UART, CAN FD | PC10/PC11 USART3, PD0/PD1/PD2 FDCAN1 | | 신설 |

### B-3. 검증 결과

- 원본 라벨 46개 중 동일 기능 매핑 20개, 절연 센싱으로 대체 6개, 내부 주변장치로 흡수 3개(TZ2, ECAP1, COMP3B 기준), 삭제 8개(RF 모듈·ADCINA5·TRST), 선택/예비 8개.
- 원본에 있으나 V2000에 없는 감시 3개(PVA+/PVB+ 직접 전압, 보조 10 V)는 추가를 권장하며 핀을 미리 잡아 두었다: PC0, PA3, PE13.
- 위 핀 전부 LQFP-128·LQFP-100 양쪽에 존재하며 기존 핀맵(§1~§3)과 충돌이 없다.
