# 2단형 단상 마이크로인버터 — 전체 시스템 (PSIM)

**PV → IIBC DC/DC → (능동 전력디커플링) DC 링크 400 V → DC/AC → 220 Vac 계통**

`dcdc_stage_review.md` 검토에서 도출된 두 보완사항(① 능동 전력디커플링, ② DC/AC 결합)을
모두 구현한 250 W급 단상 마이크로인버터 전체 모델입니다.

---

## 1. 시스템 블록도

```
  PV 모듈        ┌── IIBC DC/DC ──┐   DC 링크 400V    ┌── DC/AC 인버터 ──┐    계통
  10~30V  ─────▶ │ 절연 인터리브   │ ───────┬────────▶ │ H-Bridge + L필터  │ ─▶ 220Vac
  ~250W          │ 부스트 (n=5)    │        │          │ PR 전류 + SOGI-PLL│    60Hz
                 │ 제어: P&O MPPT  │     [벌크캡 20µF]  │ MODE 1: 링크 400V │
                 └─────────────────┘        │          └───────────────────┘
                  iibc_dcdc_control.c        │           grid_tied_inverter_control.c
                                      ┌──────┴───────┐
                                      │ 능동 전력디커플링 │  ← 120Hz 맥동 흡수
                                      │ Cd 40µF + 하프브리지│
                                      └──────────────┘
                                   active_power_decoupling_control.c
```

### 제어 역할 분담 (★핵심)
| 단 | 제어 변수 | 목적 |
|----|-----------|------|
| **IIBC DC/DC** | PV 입력전류(듀티) | **MPPT** (Vpv → 최대전력점). 버스전압은 잡지 않음 |
| **DC/AC 인버터 (MODE 1)** | DC 링크 전압 | **Vdc=400 V 정전압** 유지 + 계통 송전 |
| **APD** | Cd 전압 | **120 Hz(2ω) 맥동 흡수** → 벌크캡 소형화 |

이 분담이 2단형 단상 마이크로인버터의 표준 구조입니다.
DC/DC는 들어오는 전력을 결정(MPPT), DC/AC는 그 전력을 일정 버스전압으로 계통에 내보냅니다.

---

## 2. 사양 요약

| 항목 | 값 |
|------|-----|
| PV 입력 | 10 ~ 30 V (40-cell 모듈, Vmp ≈ 26 V) |
| 정격 전력 | 250 W |
| DC 링크 | 400 V |
| 계통 출력 | 220 Vrms / 60 Hz 단상 |
| DC/DC | IIBC, n=5, fsw 100 kHz, 인터리브 2브랜치 |
| DC/AC | H-Bridge 유니폴라 SPWM, fsw 20 kHz, L=5 mH |
| DC 링크 벌크캡 | **20 µF** (APD 사용 시) / 470 µF (수동 시) |
| 디커플링 캡 Cd | 40 µF 필름 / 400 V (APD) |

---

## 3. DC 링크 디커플링: 능동 vs 수동 (검증 결과)

단상 인버터의 120 Hz 맥동(`ΔVdc = P/(2ω·C·Vdc)`)을 처리하는 두 방식. 평균모델 시뮬 결과:

| 방식 | 구성 | Vdc 리플 | 비고 |
|------|------|---------|------|
| 수동 | 전해 **470 µF** | ±1.8 V (0.4 %) | 단순하나 전해캡=수명 취약 |
| 수동 | 필름 4 µF (논문 원안) | ±207 V (52 %) | **사용 불가** |
| **능동(APD)** | 필름 **20 µF + 40 µF** | **1.0 Vpp (0.2 %)** | 전해캡 제거, 장수명 |

> **결론**: 마이크로인버터(패널 후면 고온·25년)에는 전해캡을 피하는 **APD 방식 권장**.
> 소형 필름캡만으로 470 µF 전해캡보다 우수한 리플 억제 달성.

---

## 4. 부품/파라미터

### DC/DC (IIBC) — 논문 Table 2 기반
| 부품 | 값 |
|------|-----|
| 변압기 n | 5 (절연) |
| 스위치 S1,S2 | 100 V Si MOSFET (Ron 3.1 mΩ), 접지기준 |
| 출력 다이오드 | 600 V ×2 |
| 입력 인덕터 L1,L2 | 47 µH / 14 A ×2 |
| 입력캡 Cin | 100 V MLCC 5×4.7 µF |
| fsw | 100 kHz (인터리브 180°) |

### APD
| 부품 | 값 |
|------|-----|
| 하프브리지 Sd1,Sd2 | 500 V급 ×2, fsw 20 kHz |
| 디커플링 인덕터 Ld | 1 mH |
| 디커플링 캡 Cd | 40 µF / 400 V 필름 (평균 Vd0=200 V, 스윙 ≈150~240 V) |

### DC/AC (인버터)
| 부품 | 값 |
|------|-----|
| H-Bridge | 600 V급 ×4 (Vds ≥ 400+마진) |
| 필터 L | 5 mH / Isat ≥ 2.5 A |
| 벌크캡 | 20 µF (APD) / 470 µF (수동) |
| fsw | 20 kHz 유니폴라 |

---

## 5. 제어 코드(파일) 및 C 블록 I/O

| 파일 | 단 | 입력 | 출력 |
|------|----|------|------|
| `iibc_dcdc_control.c` | DC/DC | Vpv, Ipv, Vdc | **d**(듀티), Vpv_ref, iL_ref, Ppv, d_ff |
| `active_power_decoupling_control.c` | APD | Vdc, iLd, vCd, **theta**, Pest | **d_apd**, vCd_ref, iLd_ref, p_apd |
| `grid_tied_inverter_control.c` | DC/AC | Vgrid, Igrid, Vdc | **m**, theta, iref, Iamp, Vamp, ferr |

### 단 간 신호 연결 (★)
- 인버터 `grid_tied_inverter_control.c` 를 **MODE 1** (DC 링크 전압 제어)로 설정.
- 인버터 출력 `theta`(y[1]) → APD 입력 `x[3]` (2ω 위상 동기에 사용).
- 인버터 추정전력 `Vamp·Iamp/2` → APD 입력 `Pest`(x[4]) (또는 정격 250 W 상수).

---

## 6. PSIM 구성·시뮬레이션 절차

1. **전력단 작성**
   - PV 모델(Solar Module) → IIBC(인터리브 부스트 + 변압기 n=5 + 출력 정류) → DC 링크 노드
   - DC 링크에 벌크캡 20 µF + APD 리플포트(하프브리지+Ld+Cd) 병렬
   - DC 링크 → H-Bridge → L필터 → 단상 계통(220 Vrms/60 Hz)
2. **제어단(Simplified C Block 3개)**
   - 각 `.c` 파일을 해당 블록에 붙여넣고 센서 → 입력 매핑
   - DC/DC: 듀티 d → 인터리브 캐리어 2개(100 kHz, 180°)와 비교
   - APD: d_apd → 하프브리지 캐리어(20 kHz)
   - DC/AC: m, -m → 삼각파 캐리어(20 kHz) 유니폴라 비교
3. **Simulation Control**
   - Time step ≤ **0.2 µs** (100 kHz DC/DC 해상 위해), Total ≥ 0.3 s
4. **확인 항목**
   - DC/DC: Vpv 가 Vmp(≈26 V)에 수렴, Ppv ≈ 250 W (MPPT 효율 >98 %)
   - DC 링크: 400 V 근처, 120 Hz 리플 < 1 % (APD 동작 시)
   - 계통: Igrid 가 Vgrid 와 동상, 출력 ≈ 250 W, 역률 ≈ 1

---

## 7. 검증 요약 (평균모델 폐루프, 본 저장소 테스트)

| 단 | 결과 |
|----|------|
| DC/AC 인버터 | P=249.9 W, Irms=1.136 A, 역률≈1, PLL 잠금 ✅ |
| IIBC DC/DC | MPPT Vmp=25.7 V 수렴, Ppv≈266 W = Pmax의 ~99 % ✅ |
| APD | 벌크 20 µF 에서 리플 83.5 Vpp → **1.0 Vpp** 로 억제 ✅ |

> 위 검증은 부호·안정성·정상상태 정확도 확인용 평균모델 결과입니다.
> 실제 스위칭 리플/THD/효율은 PSIM 스위칭 모델에서 최종 확인하세요.

---

## 8. 파일 목록
| 파일 | 설명 |
|------|------|
| `grid_tied_inverter_control.c` | DC/AC 단상 계통연계 제어 (PR + SOGI-PLL) |
| `iibc_dcdc_control.c` | DC/DC IIBC 부스트 제어 (P&O MPPT) |
| `active_power_decoupling_control.c` | 능동 전력디커플링 제어 |
| `microinverter_system.md` | 본 통합 문서 |
| `dcdc_stage_review.md` | DC/DC 단 적합성 검토 |
| `README.md` | DC/AC 인버터 설계 문서 |
