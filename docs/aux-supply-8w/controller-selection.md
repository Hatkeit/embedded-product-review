# NCP1031DR2 대체 컨트롤러 선정

| 항목 | 내용 |
|---|---|
| 문서번호 | PS-AUX-8W-SEL Rev. A |
| 대상 | 기존 보드 U600 `NCP1031DR2` (SOIC-8, MOSFET 내장) 대체 |
| 요구 동작점 | PV 18~50 V, 플라이백 출력 9.3 W (입력 11.5 W), DCM 100 kHz, **Ipk 2.42 A, Vds 111.6 V** |
| 전제 | 같은 기준의 부하는 공통 GND (Rev.B 확정). 피드백은 직접 분압 |
| 검증 근거 | 각 후보의 수치는 제조사 데이터시트/앱노트 **검색 스니펫에서 확인된 값만** 기재. 미확인 항목은 "확인 필요"로 표시 |

> **출처 접근 제한** — 세션 프록시가 ti.com·analog.com·onsemi.com 및 디스트리뷰터 PDF 호스트를 차단해
> 데이터시트 본문을 직접 열지 못했습니다. 아래 수치는 검색 결과에 인용된 원문 문장 기준이며,
> **발주 전 데이터시트 원본으로 재확인이 필요합니다.** 특히 "확인 필요" 표시 항목.

---

## 1. NCP1031이 탈락하는 근거 — 이제 제조사 수치로 확정

앞서 SOIC-8 열저항으로 추정했던 결론이 onsemi 자료로 확인됩니다.

| 항목 | NCP1031 (원 사양) | 본 설계 요구 | 판정 |
|---|---|---|---|
| 용도 | 48 V 텔레콤/PoE, MOSFET 내장 | PV 18~50 V | — |
| 내장 MOSFET | **200 V** | Vds 111.6 V | 정격은 충분 |
| **출력 전력** | **"up to 6 W"** (NCP1030은 3 W) | **9.3 W** | **55 % 초과 → 탈락** |
| 평가보드 | 6.5 W PoE (EVBUM2142) | — | 상한 근처 실증 |
| 패키지 | SOIC-8 (DR2) / DFN (MNTXG) | — | 방열 한계 |
| 오실레이터 | 최대 1 MHz | 100 kHz | — |
| 기동 | DSS (Dynamic Self Supply), VCC 7.5~10 V | — | — |

**결론: 통합형(내장 FET)으로 가려면 다른 부품, 외부 FET로 가면 컨트롤러 교체.** 아래 두 경로.

---

## 2. 후보 비교표

### 2-A. 외부 FET 컨트롤러 (현재 DCM 플라이백 설계 유지)

| 항목 | **TI LM5156** | TI UCC28C43 | ADI LTC3803 | ADI MAX17596 | TI LM5021 | TI LM5155 |
|---|---|---|---|---|---|---|
| 토폴로지 | Boost/SEPIC/**Flyback** | 범용 전류모드 | Flyback 전용 | Flyback/Boost | Flyback/Forward (AC-DC) | Boost/SEPIC/Flyback |
| 전원(BIAS/VIN/VCC) | **BIAS ≤ 60 V (abs 65 V)** | VDD abs **20 V** | VCC 기동 8.7 V / 정지 5.7 V, abs max **확인 필요** | IN 4.5~**36 V** | VIN 클램프 36 V, **VIN UVLO 기동 20 V** | BIAS ≤ 45 V (**abs 50 V**) |
| 50 V 입력 직결 | **가능 (여유 15 V)** | 불가 → Naux+제너 | 불가 → Naux+레귤 (접지기준 센싱이라 Vin은 무관) | **불가 (36 V)** → Naux 급전 | 불가 | **abs max = Vin,max → 부적합** |
| **18 V 기동** | 가능 | 가능 (기동저항) | 가능 (기동저항) | 가능 | **불가 — VIN 20 V 도달 못함** | 가능 |
| **CS 문턱** | **100 mV ±7 %** | 1 V (0.9~1.1) | 확인 필요 (SENSE −0.3~1 V 범위) | **300 mV typ** | 500 mV | 100 mV |
| **Rcs 손실 @Ipk 2.42 A** | **0.04 W** | **0.43 W** | ~0.1 W 추정 | 0.13 W | 0.21 W | 0.04 W |
| 주파수 | 100 kHz~2.2 MHz 가변 | RT/CT 가변 | **200 kHz 고정** (-5: 300 kHz) | 100 kHz~1 MHz | 가변 | 100 kHz~2.2 MHz |
| 최대 듀티 | 주파수 의존 (**0.535 @100 kHz 확인 필요**) | 100 % (C43) | 80 % | 확인 필요 | 80 % (-1) / 50 % (-2) | 확인 필요 |
| 슬로프 보상 | **내장(프로그래머블)** | 없음 → 외부 | **내장** | 내장 | 내장 (-1) | 내장 |
| LEB | ~50 ns | 확인 필요 | — | — | — | — |
| 게이트 | 1.5 A | ±1 A | 확인 필요 | NDRV | 확인 필요 | 1.5 A |
| 오차증폭기 | 내장 | 내장 | 내장 (ITH 0.7~1.9 V) | 내장, 1 % 기준 | 내장 | 내장 |
| 기타 | 스프레드스펙트럼 옵션 | 최저가·최다수급, UC3843 호환 | ThinSOT(SOT-23-6) 최소면적 | TQFN-16 | 25 µA 기동 | — |
| **판정** | **1순위** | 2순위 (손실 감수) | 3순위 (200 kHz 재설계) | 조건부 (Naux 급전 필수) | **탈락** | **탈락** |

**Rcs 손실은 CS 문턱에 정비례**합니다 (`calc_aux.py` 출력):

```
CS 1.0 V -> Rcs 0.419 Ohm, 0.43 W   UCC28C43
CS 0.5 V -> Rcs 0.210 Ohm, 0.21 W   LM5021
CS 0.3 V -> Rcs 0.126 Ohm, 0.13 W   MAX17596
CS 0.1 V -> Rcs 0.042 Ohm, 0.04 W   LM5156   <- 채택
```

UCC28C43 대비 **0.39 W (입력의 3.4 %p)** 차이입니다. 8 W 전원에서 무시 못 할 크기입니다.

### 2-B. 내장 FET (통합형)

| 항목 | **TI LM5160 / LM5160A** | ADI MAX17693A/B | ADI LT3573 | TI UCC25230 |
|---|---|---|---|---|
| 토폴로지 | 동기 벅 / **Fly-Buck** | No-opto 절연 플라이백 | 절연 플라이백 | Forward-Flyback |
| 입력 | **4.5~65 V** | 4.2~60 V | 3~40 V | 12~105 V |
| 내장 스위치 | HS+LS FET, **피크전류제한 2.875 A (max)** | **76 V** nMOSFET | 60 V / 1.25 A NPN | HS+LS |
| 정격 출력 | 1.5 A (A: 2 A), 참조설계 ~11 W | — | ≤ 7 W | **0.2 A** |
| 본 설계 대비 | 65 V ✔, S1 1.35 A ✔ (피크 여유 **확인 필요**) | **76 V < Vds 111.6 V** | 40 V < 50 V, 7 W < 9.3 W | 0.2 A ≪ 1.35 A |
| 제어 | COT, **1차측 레귤레이션(옵토 불요)** | — | — | 380 kHz 고정 |
| 패키지 | WSON-12 | TDFN-12 | MSOP-16 | SON-8 |
| **판정** | **강력 대안 (토폴로지 변경 조건)** | 탈락 | 탈락 | 탈락 |

---

## 3. 조건별 선정

"조건에 따라 외부 FET 사용도 가능"이라 하셨으니, **조건 → 부품**으로 정리합니다.

| 조건 | 선정 | 이유 | 대가 |
|---|---|---|---|
| **A. 현재 DCM 플라이백 설계를 그대로 쓴다** | **LM5156 + 외부 150 V FET** | BIAS 65 V로 50 V 직결, CS 100 mV로 Rcs 손실 0.43→0.04 W, 슬로프보상·LEB 내장, 플라이백 지원(TI E2E 설계검토 사례 있음) | 부품 2점(IC+FET). 최대듀티 0.535@100 kHz 데이터시트 확인 |
| **B. 토폴로지 변경을 허용한다 (Fly-Buck)** | **LM5160 (내장 FET)** | 공통 GND + 플로팅 12 V 구조에 **정확히 대응** — S1 6 V는 벅으로 직접 레귤, S2 12 V는 결합권선. RCD 클램프(0.62 W)·Rcs(0.22 W) 손실 소멸 → **효율 69.7 → 추정 74~76 %** | 자성체를 결합 인덕터로 재설계(별도 계산 필요). 피크전류 2.875 A 대비 여유 확인 |
| **C. 최저가 · 최다 수급** | UCC28C43 + 외부 FET | UC3843 호환, 어디서나 구함 | Rcs 0.43 W, VDD 20 V라 Naux+제너 필수, 외부 슬로프보상 |
| **D. 최소 면적** | LTC3803 + 외부 FET | ThinSOT, 슬로프보상 내장 | 200 kHz 고정 → Lp 41.7→~21 µH, 코어 축소 재설계. VCC abs max 확인 |

### 권장

- **1순위: LM5156** — 지금까지의 설계(`calc_aux.py` 15/15 PASS, EFD20, n=5)를 그대로 가져갑니다.
- **B가 가능하면 LM5160이 더 낫습니다.** 이유는 단순합니다 — **8.1 W짜리 S1 레일을 플라이백(82 %)이 아니라 벅(90 %+)으로 만들기 때문**이고, RCD 클램프라는 최대 손실원이 아예 없어집니다. 다만 Fly-Buck은 별도 설계 계산이 필요하므로 이번 문서에서는 "대안"으로 둡니다.

---

## 4. 탈락 사유 (한 줄씩)

| 부품 | 사유 |
|---|---|
| **NCP1031** (원품) | 제조사 정격 "up to 6 W" < 요구 9.3 W |
| LM5021 | VIN UVLO 기동 20 V > Vin,min 18 V → **18 V에서 기동 불가** |
| LM5155 | BIAS abs max 50 V = Vin,max → 마진 0 |
| MAX17693A/B | 내장 FET 76 V < Vds 111.6 V |
| LT3573 | 입력 최대 40 V < 50 V, 출력 7 W < 9.3 W |
| UCC25230 | 출력 0.2 A ≪ S1 1.35 A |
| MAX17596 | IN 36 V < 50 V — Naux 급전 시에만 가능 (조건부) |

---

## 5. LM5156 채택 시 회로 변경점

기존 `aux-supply-spec.md` 5장 U1 행을 다음으로 확정합니다.

| 참조 | 사양 |
|---|---|
| **U1** | **TI LM5156** (또는 LM51561 / LM5156H 변형 — 스펙트럼확산·UVLO 옵션 차이 확인). BIAS ← Vin 직결(≤60 V), fsw 100 kHz, CS 100 mV, 슬로프보상 프로그래밍, LEB 50 ns |
| **Rcs** | **42 mΩ / 0.5 W** (0.1 V / 2.42 A). 손실 0.04 W. 저인덕턴스 필수 — 100 mV 문턱은 노이즈에 민감 |
| R_st | **불요** (BIAS 직결). Naux는 VCC 외부 급전으로 효율 개선용 선택 |
| 슬로프보상 | 데이터시트 절차대로 D>0.5 구간 대응 설정 (D 0.535 @18 V) |

> **100 mV 문턱의 대가**: 전류센스 신호가 작아 **PCB 레이아웃 노이즈에 민감**합니다.
> Rcs–GND–CS 핀을 켈빈 연결하고, 게이트 구동 루프와 분리해야 합니다.
> LEB 50 ns가 있지만 링잉이 길면 오동작하므로 Q1 게이트저항으로 dv/dt를 다스릴 필요가 있습니다.

---

## 6. 확인 필요 항목 (발주 전)

| # | 항목 | 이유 |
|---|---|---|
| 1 | LM5156 **최대 듀티 @100 kHz ≥ 0.535** | 스니펫에 "주파수 의존"만 확인됨 |
| 2 | LM5156 플라이백 모드 슬로프보상 설정 절차 | 데이터시트/SNVA941 |
| 3 | LM5160 선택 시 **Fly-Buck 피크전류 vs 2.875 A** | S1 1.35 A + S2 반사분 + 리플 |
| 4 | LTC3803 VCC abs max, SENSE 문턱 typ | 스니펫에 없음 |
| 5 | 각 부품 **수급/단종 상태** | 검색으로 확인 불가 |

---

## 출처

- NCP1031: [onsemi 제품페이지](https://onsemi.com/products/power-management/dc-dc-controllers-converters-regulators/converters/ncp1031), [6.5 W PoE 평가보드 EVBUM2142](https://www.onsemi.com/pub/Collateral/EVBUM2142-D.PDF), [Digi-Key 데이터시트](https://www.digikey.com.mx/htmldatasheets/production/202668/0/0/1/ncp1030-31.html), [Würth 참조설계](https://www.we-online.com/en/components/icref/onsemi/NCP1031-NCP1031-EVB-Flyback)
- LM5156: [TI 제품페이지](https://www.ti.com/product/LM5156), [데이터시트](https://www.ti.com/lit/ds/symlink/lm51561.pdf), [TI E2E 플라이백 설계검토](https://e2e.ti.com/support/power-management-group/power-management/f/power-management-forum/1261067/lm5156-lm5156-flyback-converter-schmatic-review), [SNVA941 앱노트](https://www.ti.com/lit/pdf/snva941)
- LM5155: [TI 제품페이지](https://www.ti.com/product/LM5155), [데이터시트](https://www.ti.com/lit/ds/symlink/lm5155.pdf?ts=1740337137757)
- UCC28C43: [TI 제품페이지](https://www.ti.com/product/UCC28C43), [데이터시트](https://www.ti.com/lit/ds/symlink/ucc28c40.pdf), [E2E 전류제한](https://e2e.ti.com/support/power-management-group/power-management/f/power-management-forum/474183/ucc28c43-current-limit-issue)
- LM5021: [TI 제품페이지](https://www.ti.com/product/LM5021), [데이터시트](https://www.ti.com/lit/ds/symlink/lm5021.pdf), [E2E VCC 최대전압](https://e2e.ti.com/support/power-management-group/power-management/f/power-management-forum/1388900/lm5021-what-is-the-maximum-voltage-of-the-vcc-pin-on-lm5021)
- LTC3803: [ADI 제품페이지](https://www.analog.com/en/products/ltc3803.html), [데이터시트](https://www.analog.com/media/en/technical-documentation/data-sheets/3803fc.pdf)
- MAX17596: [ADI 제품페이지](https://www.analog.com/en/products/max17596.html), [데이터시트](https://www.analog.com/media/en/technical-documentation/data-sheets/max17595-max17597.pdf), [MAXREFDES1122](https://www.analog.com/media/en/reference-design-documentation/reference-designs/maxrefdes1122.pdf)
- LM5160: [TI 제품페이지](https://www.ti.com/product/LM5160), [Fly-Buck 사용자가이드 SNVU408](https://www.ti.com/lit/pdf/snvu408), [PMP10532 참조설계](https://www.we-online.com/en/components/icref/texas-instruments/LM5160-PMP10532-Flyback), [E2E Fly-Buck](https://e2e.ti.com/support/power-management-group/power-management/f/power-management-forum/620768/lm5160-fly-buck-power-supply)
- MAX17693A/B: [ADI 제품페이지](https://www.analog.com/en/products/max17693a.html)
- LT3573: [ADI 제품페이지](https://www.analog.com/en/products/lt3573.html)
- UCC25230: [TI 제품페이지](https://www.ti.com/product/UCC25230), [digchip](https://www.digchip.com/datasheets/3293351-ucc25230.html)
