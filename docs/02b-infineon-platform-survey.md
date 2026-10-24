# Infineon 플랫폼으로 Elmo급 사양 구성 가능성 조사

작성 2026-10-24 · 상태: **후보 선별 단계. 데이터시트 원문 대조 전**
선행 문서: [01-target-analysis.md](01-target-analysis.md), [02-power-device-survey.md](02-power-device-survey.md)

표기는 02와 같다 (✅ 검증 · 🔍 검색 확인 · 🔢 유도 · ❓ 미확인). **이 문서의 Infineon 측 값은
전부 🔍다** — 작성 환경에서 제조사·유통사 사이트 직접 접속이 차단되어 검색 요약과 유통사
표기로만 확인했다.

질문: **Infineon MCU 기반으로 Elmo G-TWIR50/100 (95 V max, 35.3 A RMS, 4.0 kW, 12.6 cm³,
CAN 또는 EtherCAT)에 견줄 제품·레퍼런스 디자인이 있는가?**

---

## 1. 결론

**완제품이나 레퍼런스 디자인으로는 없다.** 가장 가까운 Infineon 레퍼런스도 전압(최대 60 V급)이나
전력·크기에서 Elmo에 못 미친다. 다만 **부품 수준에서는 Elmo급 CAN 버전을 구성할 블록이 모두
있다** — MCU(PSC3M8), 160 V 게이트 드라이버(6ED2742S01Q), 120/150 V MOSFET(02 문서).
EtherCAT 버전은 PSC3M8 단독으로는 안 되고 EtherCAT 내장 MCU(XMC4300/4800)를 추가해야 한다.

---

## 2. 🔍 가장 가까운 Infineon 레퍼런스

| 보드 | MCU | 입력 전압 | 전력 | 전력단 | 통신 | Elmo 대비 |
|---|---|---|---|---|---|---|
| **Elmo G-TWIR50/100** (✅ 01) | 비공개 | 10–85–**95 V** | **4.0 kW** | 비공개 | CAN 또는 EtherCAT | 기준 |
| **REF_48V_2X1KW_ASFOC** | **PSOC C3M** 1개로 인버터 2개 | 12–60 V | 1 kW × 2 | 6EDL7151 + OptiMOS 6 **80 V** SuperSO8 (5×6 mm) | CAN | 로봇용·PSOC C3 사용으로 가장 근접. 전압 60 V 한계 |
| **EVAL_TOLT_DC48V_3KW** | XMC1300 (트래페조이달) / XMC4400 (FOC) | 36–52 V | 3 kW | ILD8150 + OptiMOS 5 **100 V** TOLT | — | 전력은 근접. 전압·용도(전동공구) 다름 |
| **EVAL-6ED2742S01QM1** | iMOTION IMC101T 제어 카드 | ❓ | ❓ | **6ED2742S01Q (160 V)** + OptiMOS 5 **150 V** BSC074N15NS5 × 6 | — | **유일한 150 V급 전력단.** MCU가 PSOC가 아님 |
| Windpute 로봇 액추에이터 (서드파티) | **XMC4800** | ❓ | ❓ | ❓ | **EtherCAT** | Infineon MCU + EtherCAT 조합의 실사례 |

> REF_48V_2X1KW_ASFOC의 "출력 120 A"는 상전류·피크 여부가 불명확해 표에 넣지 않았다 (01 §2.1의
> 단위 규칙). Infineon 산업용 22 kW 레퍼런스(REF-22K-GPD-INV-EASY3B)는 XMC4800(제어) +
> XMC4300(통신) 2칩 구성의 사례로만 참고하며, 380–480 V 계통용이라 비교 대상이 아니다.

---

## 3. 🔍 Elmo급을 구성할 수 있는 블록

### 3.1 MCU — PSC3M8 (PSOC Control C3 Performance line)

| 항목 | 값 |
|---|---|
| 메인 코어 | Cortex-M33 **180 MHz**, DSP·FPU |
| 보조 코어 (PPCA) | **Cortex-M33 × 2** 독립 코어, DSP·FPU, 112 KB SRAM |
| 메모리 | Flash 512 KB (RWW, ECC), SRAM 128 KB (+PPCA 112 KB) |
| PWM | TCPWM 16비트 × 14, 32비트 × 12, **HRPWM < 100 ps** |
| 통신 | **CAN FD × 2** (1채널 8 Mbps), SCB × 7 |
| 패키지 | VQFN-48/64, E-LQFP-64/80/100 |
| Ethernet / EtherCAT | **검색 결과에 없음** ❓ (원문 통신 인터페이스 절에서 부재 확인 필요) |

→ Elmo **CAN 버전**의 MCU 역할은 PSC3M8 단독으로 가능해 보인다. 보조 코어 2개에 전류 루프를,
메인 코어에 통신·상위 제어를 나누는 구성이 가능하다 (구조상 가능성이며 성능 검증 전).

### 3.2 EtherCAT이 필요할 때 — XMC4300 / XMC4800

- Cortex-M4 기반, **EtherCAT 슬레이브 컨트롤러(ESC) 내장** — 별도 ESC ASIC·외부 메모리·수정
  발진기 불필요, 내장 PLL이 25 MHz 공급
- XMC4300: Flash 256 KB, RAM 128 KB, 주변 온도 125 °C 인증, 저가형
- XMC4300 ↔ XMC4800 핀·코드 호환

→ **EtherCAT 버전 = PSC3M8(모터 제어) + XMC4300(EtherCAT) 2칩**, 또는 XMC4800 단독(모터 제어 +
EtherCAT) 중 선택. 2칩 구성은 Infineon 22 kW 레퍼런스가 쓰는 방식과 같다.

### 3.3 게이트 드라이버 — 전압이 결정한다

| 드라이버 | 동작 전압 | 95 V 버스 | 비고 |
|---|---|---|---|
| 6EDL7151 (REF_48V_2X1KW에 사용) | **5.5–70 V** | ❌ **불가** | 벅·LDO·차지펌프 내장, 게이트 전압 7/10/12/15 V 설정 |
| **6ED2742S01Q** | 배터리 **10.8–120 V**, VB **160 V** | ✅ 가능 | 3상, SOI, 부트스트랩 다이오드 내장, 100 % 듀티(트리클 차지펌프), 소스 1 A / 싱크 2 A, 전류 센스 앰프 내장, 과전류 보호, QFN-32 5×5 mm, −40~125 °C |

→ **Infineon 3상 드라이버 중 95 V 버스를 다룰 수 있는 것은 이번 조사 범위에서 6ED2742S01Q
하나다.** 따라서 가장 가까운 레퍼런스(REF_48V_2X1KW_ASFOC)를 그대로 키우는 방식은 안 되고,
게이트 드라이버부터 바꿔야 한다.

---

## 4. 🔢 유도 — 블록 조합에서 드러나는 제약

### 4.1 6ED2742S01Q로 TOLL Si를 구동할 때의 게이트 충전 시간

입력: 소스 전류 1 A (🔍), IPTC017N12NM6 Qg = 113 nC (🔍, 02 §1의 형제 품번).

```
t ≈ Qg / I_source = 113 nC / 1 A ≈ 113 ns   (총 게이트 충전 기준의 상한 근사)
```

실제 스위칭 전이 시간은 Qgd 구간이 결정하므로 이보다 짧지만, 1 A 드라이브가 **저 RDS(on)·대면적
소자에는 넉넉하지 않다**는 신호다. 스위칭 손실(02 §5 #6) 계산 시 드라이버 전류를 입력으로 써야 한다.

### 4.2 GaN 경로(02 경로 A)와는 드라이버가 맞지 않는다

6ED2742S01Q는 차지펌프로 **12 V 게이트 전원**을 만든다 (🔍). eGaN FET은 게이트 정격이 이보다
훨씬 낮아(EPC2305는 5 V 구동 조건으로 RDS(on) 표기) **이 드라이버로 직접 구동할 수 없다.**
→ 02의 경로 A(EPC2305)를 택하면 **GaN 전용 하프브리지 드라이버**가 필요하고, 그 후보는 이번
조사 범위 밖이다 ❓.

### 4.3 경로별 Infineon 블록 정리

| 02 경로 | 소자 | 게이트 드라이버 | MCU (CAN판) | MCU (EtherCAT판) |
|---|---|---|---|---|
| A. 소형 | EPC2305 GaN 150 V | ❓ GaN 전용 필요 | PSC3M8 | PSC3M8 + XMC4300 |
| B. 저손실 | IPT017N12NM6 120 V | 6ED2742S01Q | PSC3M8 | PSC3M8 + XMC4300 |
| C. 보수적 | IPT025N15NM6 150 V | 6ED2742S01Q | PSC3M8 | PSC3M8 + XMC4300 |

---

## 5. ❓ 남은 확인 항목

| # | 항목 | 막고 있는 결정 | 확인 경로 |
|---|---|---|---|
| 1 | PSC3M8 **Ethernet/EtherCAT 부재** 원문 확인 | EtherCAT판 2칩 여부 | PSC3 Performance 데이터시트 |
| 2 | 6ED2742S01Q **전류 센스 앰프 채널 수** | 3션트 FOC를 외부 앰프 없이 할 수 있는지 | 6ED2742S01Q 데이터시트 |
| 3 | EVAL-6ED2742S01QM1 **정격 전압·전류·전력** | 150 V급 Infineon 전력단의 실측 기준점 | 보드 사용자 가이드 |
| 4 | REF_48V_2X1KW_ASFOC **상전류 정격(진폭/RMS)**·크기 | PSOC C3 기반 실제 밀도 기준점 | 보드 사용자 가이드 |
| 5 | GaN 전용 게이트 드라이버 후보 | 경로 A 성립 여부 | 별도 조사 |
| 6 | PSC3M8 **ADC 사양**(채널·변환 속도), CORDIC 유무 | 전류 루프 주기 | PSC3 Performance 데이터시트 |

**최우선은 #1·#2다.** #1이 EtherCAT판의 칩 구성(1칩/2칩)을, #2가 전류 센싱 회로 규모를 정한다.

## 참고한 검색 결과 (🔍 출처)

- PSC3 Performance (PSC3P7/M7/P8/M8) 데이터시트: <https://www.infineon.com/assets/row/public/documents/30/49/infineon-psc3-performance-psc3p7-m7-p8-m8-datasheet-datasheet-en.pdf>
- KIT_PSC3M8_CC1 제품 브리프: <https://www.infineon.com/assets/row/public/documents/30/45/infineon-psoc-control-kit-psc3m8-cc1-productbrief-en.pdf>
- PSOC Control C3 Main line 문서: <https://documentation.infineon.com/psoccontrolc3/docs/zme1730181802915>
- REF_48V_2X1KW_ASFOC: <https://we-online.com/en/components/icref/infineon-technologies/6EDL7151-REF-48V-2X1KW-ASFOC-Motor-Drive>, <https://we-online.com/de/components/icref/infineon-technologies/6EDL7151-REF-48V-2X1KW-ASFOC-PWR-Si-Motor-Drive>
- EVAL_TOLT_DC48V_3KW: <https://www.we-online.com/de/components/icref/infineon-technologies/ILD8150-EVAL-TOLT-DC48V-3KW-Buck>
- 고출력 200 V 이하 모터 드라이브 솔루션: <https://www.infineon.com/cms/en/product/applications/Motor_Control_Drives/BLCD_CD.html>
- EVAL-6ED2742S01QM1: <https://www.mouser.se/infineon-eval-6ed2742s01qm1-eval-kit>
- 6ED2742S01Q 데이터시트: <https://www.infineon.com/assets/row/public/documents/24/49/infineon-6ed2742s01q-datasheet-en.pdf>
- 6EDL7151 데이터시트: <https://mouser.com/datasheet/2/196/Infineon_6EDL7151_DataSheet_v01_00_EN-3536870.pdf>
- XMC4300 EtherCAT: <https://www.ethercat.org/en/products/807069D8872C48498E55CE1E4A88F35D.htm>, <https://www.eenewseurope.com/en/infineon-targets-ethercat-installations-with-xmc4300-mcus/>
- REF-22K-GPD-INV-EASY3B: <https://se.rs-online.com/web/p/power-motor-robotics-development-tools/2325738>
- Windpute XMC4800 로봇 액추에이터: <https://www.ethercat.org/it/products/EDC5C55B53AF46EE8B40776275D18C37.htm>
- Infineon–NVIDIA 휴머노이드 발표: <https://www.businesswire.com/news/home/20250825221082/en/Infineon-to-Enable-Humanoid-Robots-With-Precise-Motion-and-Efficiency-Powered-by-NVIDIA-Technology>
