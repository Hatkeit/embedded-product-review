# TIDA-010954 분석 — 600W GaN 단상 사이클로컨버터 (TI 레퍼런스)

**문헌**: TI TIDUFD2 (2025-05), *600W GaN-Based Single-Phase Cycloconverter Reference Design*
**의의**: 앞서 우리가 분석/구현한 **HF-link 사이클로컨버터(`cycloconverter_control.c`)의 양산급 실제 구현**.
TI가 부르는 정식 명칭은 **AC-DAB (Cycloconverter = AC측 Dual Active Bridge)**.

---

## 1. 핵심 사양

| 항목 | 값 |
|------|-----|
| 토폴로지 | 단일단 양방향 DC-AC, 사이클로컨버터(AC-DAB) |
| 입력 DC | 27 ~ 60 V (max 16 A) — 저전압 PV/48V 배터리 |
| 출력 AC | 230 VAC / 2.6 A / **600 W** (50 Hz) |
| 스위칭 주파수 | **300 ~ 600 kHz** (가변) |
| **피크 효율** | **96.1 %** (VIN=40 V) |
| 전력밀도 | **640 W/L** (290×100×32 mm, 방열판 없음) |
| 양방향 | ✅ PV 마이크로인버터 ↔ BESS(배터리) 겸용 |
| 반도체 | GaN: LMG2100R026(DC 풀브리지), LMG3650R035(AC 사이클로) |
| 제어기 | C2000 **TMS320F28P55x** 단일 MCU |
| 제어 | **SOGI-PLL + PR + MPPT**, DAB **위상천이(SPS/EPS)**, ZVS, 데드타임 보상 |

---

## 2. 동작 원리 (우리 분석과 일치 확인)

```
 PV/배터리(27-60V) ─[풀브리지 Q1-Q4]─HFAC→[HF변압기+누설L]→[사이클로 S1A/B,S2A/B]→ 230VAC
        ① 3레벨(+Vdc,0,-Vdc)        ② 전력전달=위상천이      ③ 2레벨(±Vac/2) 언폴딩
```

- **DC측 풀브리지**: DC를 고주파 구형파로 → 변압기. 풀브리지라 **3레벨(+VDC, 0, -VDC)** 출력 가능(EPS).
- **전력 전달 = 위상천이(Phase Shift)**: 1차·2차 전압 파형의 **위상차**로 인덕터(누설 L) 전류를 제어 → DAB 원리. 듀티가 아니라 위상으로 전력 조절.
- **AC측 사이클로컨버터**: AC 스위치 = GaN 2개 common-source(4상한).
  - **한 소자는 정류(반주기 내내 ON), 다른 소자는 HF 스위칭** — 계통 영교차에서 역할 교대.
  - 예: 계통 + 반주기엔 S1B/S2B 정류·S1A/S2A 스위칭, - 반주기엔 반대. (← 우리 `cycloconverter_control.c`의 언폴딩 로직과 동일)
- **DAB 등가**: 양(+) 반주기엔 S1B/S2B 상시 ON → 제거하면 S1A/S2A 반브리지 = 일반 DAB로 단순화.

---

## 3. ★우리 사전 검토가 그대로 검증된 지점

| 우리가 지적했던 점 | TI 문서의 확인 |
|-------------------|----------------|
| 단일단은 **2ω(2×계통) 맥동을 둘 곳이 없다** | "single-stage approach, **there is no DC-Link capacitor** to handle the power ripple" |
| **APD 부착할 DC 링크 노드가 없음** → 입력으로 반사 | "energy storage … provided by the **input capacitors** … reflected onto the **PV panel** voltage" |
| 입력캡 사이징 공식 | `C ≥ Pin/(2π·Vin·fAC·Vripple)` — **우리가 쓴 식과 동일** |
| 순시전력 = 평균의 2배 | "instantaneous power … from zero up to **double the average power**" |
| 4상한 스위치 커뮤테이션 + 데드타임 | "dead time … rectification devices provide a path for inductor current" + 데드타임 보상 블록 |
| 제어 = PLL + PR | 컨트롤러 블록도: **SOGI-PLL × sine + PR + MPPT** (우리 구현과 동일 구조) |

→ 앞선 `cycloconverter_topology_review.md`의 결론(단일단의 본질적 약점 = 2ω 디커플링,
APD 불가, 커뮤테이션)이 **TI 양산 디자인에서 그대로 확인**됨.

---

## 4. 우리 구현과의 비교 / 개선점

| 구분 | 우리 `cycloconverter_control.c` | TIDA-010954 (TI) |
|------|-------------------------------|------------------|
| 제어법 | SOGI-PLL + PR + 전력지령×sine | **동일** (+ MPPT) |
| 변조 | **듀티 PWM**(\|m\| 듀티, 능동/프리휠) | **위상천이 DAB(SPS/EPS, D1·D2)** |
| 소프트스위칭 | 미적용(하드스위칭) | **ZVS** (효율 핵심) |
| 효율 | (평균모델, 손실 미모델) | **96.1 %** 실측 |
| 스위칭 | 예시 50 kHz | 300–600 kHz GaN |
| 2ω 처리 | 입력캡(검토에서 지적) | 입력캡(99% MPPT 기준 사이징) |

**개선 방향(우리 코드 → 양산급)**:
1. **변조를 듀티 PWM → 위상천이(D1 내부, D2 외부)로 교체** → ZVS 확보 (96% 효율의 핵심).
   - 전력 = 위상차로 제어, EPS로 3레벨(+VDC,0,-VDC) 활용해 ZVS 범위 확장·순환전류 감소.
2. **데드타임 보상** 블록 추가.
3. **주파수 변조(FSW 가변)** 로 경부하 ZVS 유지.
4. 우리의 제어법(PLL+PR+MPPT)은 **이미 TI와 동일 구조** → 그대로 재사용 가능.

---

## 5. 2단형 vs 단일단(TI) 종합

| | 2단형 IIBC+H브리지+APD (우리) | 단일단 AC-DAB (TIDA-010954) |
|---|---|---|
| 변환단 | 2 | **1** |
| 효율(피크) | ~93 %(IIBC)×96 %(인버터)≈90 % | **96.1 %** (단일단+GaN+ZVS) |
| 전력밀도 | 보통 | **640 W/L (방열판 無)** |
| 2ω 디커플링 | **APD로 분리**(PV 리플 無, 검증 1Vpp) | 입력캡(PV에 리플 반영, 99% MPPT) |
| 양방향(BESS) | 추가 설계 필요 | **기본 지원** |
| 커뮤테이션/ZVS 난이도 | 낮음(표준 H브리지) | 높음(4상한+위상천이+ZVS) |
| 제어 복잡도 | 중 | 높음(C2000급 필요) |

**결론**:
- **효율·전력밀도·양방향(BESS)** 가 목표라면 → **단일단 AC-DAB(TI 방식)**. 단 GaN+위상천이+ZVS+C2000급 제어 역량 필요. 2ω는 PV 리플을 감수(입력캡 사이징).
- **설계·제어 단순성, PV MPPT 품질(낮은 입력 리플), APD로 깔끔한 2ω 분리** 가 목표라면 → **2단형(우리 구현)**.
- 우리 `cycloconverter_control.c`는 TI와 **제어 구조가 동일**하므로, **변조를 위상천이+ZVS로 교체**하면 TIDA-010954에 정합하는 양산 경로가 됨.

---

## 6. 참고: 사용 디바이스
| 기능 | 부품 |
|------|------|
| DC 풀브리지 GaN | LMG2100R026 (100 V, 53 A 하프브리지) |
| AC 사이클로 GaN | LMG3650R035 (650 V, 35 mΩ) |
| MCU | TMS320F28P550SJ (C2000) |
| 전류센서 | TMCS1123 / TMCS1133 / INA185 |
| 절연/게이트 | ISO6762 / UCC33421-Q1 |
