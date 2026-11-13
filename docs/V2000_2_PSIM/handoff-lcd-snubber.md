# V2000 플라이백 LCD 스너버 — 인계 문서

| 항목 | 내용 |
|---|---|
| 작성일 | 2026-11-13 |
| 대상 | V2000 언폴딩 마이크로인버터, 2상 인터리브 플라이백의 1차 클램프 |
| 목적 | 다른 세션에서 이어서 진행할 수 있도록 지금까지의 조건·계산·결정·미해결 항목을 한 파일에 정리 |
| 상태 | 스너버 값 최종 선정 완료. PSIM·실측 검증과 전제조건 3건 미해결 |

이 문서만으로 이어갈 수 있게 계산식, 결과 표, 시뮬레이션 스크립트 전문을 모두 넣었다.

---

## 1. 결론

| 부품 | 값 | 정격 | 연결 |
|---|---|---|---|
| **Cs** | **PP 필름 330 nF × 4 직렬 = 82.5 nF** | 개당 dv/dt ≥ 70 V/µs, 100 kHz 리플 ≥ 5 A | 드레인 ↔ 노드 X |
| **Ls** | **10 µH** | 포화 ≥ 10 A, 실효 ≥ 3 A | D2 캐소드 ↔ X |
| **D1** | 초고속 다이오드 | 200 V / 5 A | X → Vin+ |
| **D2** | 초고속 다이오드 | 200 V / 5 A | GND → Ls |

스너버는 상(트랜스)마다 1개. FET 를 병렬로 써도 스너버는 늘리지 않는다.

| 시정수 | 식 | 값 | 조건 |
|---|---|---|---|
| 클램프(누설 전류 소멸) | (π/2)·√(Llk·Cs) | 0.18 µs | 오프 구간보다 충분히 짧음 |
| 반전 반주기 | π·√(Ls·Cs) | 2.85 µs | — |
| 반전 완료(잔류 전류 포함) | 시뮬레이션 | 3.4~3.9 µs | 온타임 5.3~6.0 µs 보다 짧음 |

**이 선정은 5장의 전제조건이 충족될 때만 성립한다.** 현재 V2000 설계와는 FET 내압, 과전류 설정, Lp 값이 충돌한다.

---

## 2. 조건

| 구분 | 값 | 출처 |
|---|---|---|
| 입력 | 18~50 V, MPPT 30~37.6 V | 사용자 |
| 출력 | PHV 342 V 피크, 상당 250 W 피크, 라인 평균 125 W/상 | 사용자 |
| 메인 트랜스 | ER4042H, Lp 12 µH, Np:Ns = 4:30 (a = 7.5), Llk 0.16 µH | 사용자 |
| Cs 소자 | 필름 330 nF 를 직렬로 사용 | 사용자 |
| 스위칭 주파수 | 100 kHz | **가정** |
| 효율(전류 계산용) | 0.93 | **가정** |
| 1차 FET | 150 V, 7 mΩ, Coss 1 nF | **가정** |
| 2차 다이오드 Vf | 1.5 V | **가정** |

V2000_CAN 세션의 교차 검토 요약(상세 파일은 받지 못함):

| 항목 | 이 문서의 전제 | V2000 세션 보고 |
|---|---|---|
| 1차 FET 내압 | 150 V | 100 V (IAUCN10S7L040) |
| 과전류 설정 | Ipk 22.4 A 허용 | 18 A |
| Lp | 12 µH | 펌웨어는 24 µH 기준 |

→ Lp 12 µH 와 24 µH 두 경우를 모두 계산해 두었다.

---

## 3. 회로와 동작

```
Vin+ ──┬───────────────────┬──
       │                   │
   [1차 권선]              D1  (X → Vin+)
   (Lp + Llk)              │
       │                   │
드레인 ├──────── Cs ───────┤ X
       │                   │
      [Q]                  Ls
       │                   │
       │                   D2  (GND → X)
GND ───┴───────────────────┴──
```

1. **턴오프**: 누설 전류가 Cs → D1 → Vin+ 로 흐르며 Cs 충전(드레인 쪽 +). Vds 피크 = Vin + Vc,pk.
2. **턴온**: GND → D2 → Ls → Cs → Q 로 반주기 공진. Cs 전압이 뒤집혀 −Vin 에 고정되고, Ls 의 남은 전류는 D1 로 입력에 돌아간다.
3. **다음 턴오프**: Cs 가 −Vin 에서 다시 충전을 시작한다.

회로도 그림: 저장소 `docs/lcd-snubber/lcd-snubber-schematic.svg` (브랜치 `claude/1ed3431-flt-rdy-waveform-iuu0vx`).

---

## 4. 계산

### 4.1 식

```
VOR    = (Vo + Vf)/a = 343.5/7.5 = 45.8 V
D      = VOR/(VOR + Vin)
Imid   = P/(η·Vin·D),  ΔI = Vin·D·T/Lp,  Ipk = Imid + ΔI/2,  Ivalley = Imid − ΔI/2
Vc,pk  = VOR + Ipk·√(Llk/Cs)
Vds,pk = Vin + Vc,pk
I_res  = Vc,pk·√(Cs/Ls)
t_inv  ≈ π·√(Ls·Cs) + 잔류 전류 소멸 시간   (< t_on 이어야 함)
순환 전력 = ½·Cs·(Vc,pk² − Vin²)·f      (매 주기 Cs 를 거쳐 입력으로 되돌아가는 전력)
Bpk    = Lp·Ipk/(Np·Ae)
```

### 4.2 동작점 (PHV 342 V)

| Lp | 입력 | 출력 | D | Ipk | 밸리 |
|---|---|---|---|---|---|
| 12 µH | 18 V | 204 W (전류 제한 22.4 A) | 0.718 | 22.4 A | 11.6 A |
| 12 µH | 30 V | 250 W | 0.604 | 22.4 A | 7.3 A |
| 12 µH | 37.6 V | 250 W | 0.549 | 21.6 A | 4.4 A |
| 12 µH | 50 V | 경부하 25 W | 0.161 | 6.7 A | 0 (DCM) |
| 24 µH | 30 V | 250 W | 0.604 | 18.6 A | 11.1 A |
| 24 µH | 37.6 V | 250 W | 0.549 | 17.3 A | 8.7 A |

18 V 에서 250 W 를 내려면 Ipk 26.2 A 가 필요하다.

### 4.3 Cs — 직렬 개수 (Lp 12 µH, 입력 37.6 V)

| 직렬 수 | Cs | Vds 피크 (150 V 대비) | 순환 전력 | 판정 |
|---|---|---|---|---|
| 2 | 165 nF | 104.7 V (70 %) | — | 손실 크고 반전 여유 부족 |
| 3 | 110 nF | 109.5 V (73 %) | 20.7 W | 가능, 손실 큼 |
| **4** | **82.5 nF** | **113.5 V (76 %)** | **17.9 W** | **채택** |
| 5 | 66 nF | 117.1 V (78 %) | 16.2 W | 가능, Llk 편차 여유 작음 |
| 6 | 55 nF | 120.2 V (80 %) | — | 여유 없음 |

- 4직렬은 Llk 가 0.22 µH 로 커져도 Vds 118.7 V (79 %).
- 일반 범위: Cs 56~100 nF, Ls 4.7~15 µH. Llk 가 달라지면 Cs 하한은 약 `350 nF × Llk[µH]` 로 움직인다.

### 4.4 Ls (Cs 82.5 nF, 입력 37.6 V)

| Ls | 반전 완료 / 온타임 | Ls 실효전류 | 판정 |
|---|---|---|---|
| 6.8 µH | 2.87 / 5.38 µs | 2.97 A | 가능, 전류 큼 |
| **10 µH** | **3.48 / 5.38 µs** | **2.70 A** | **채택** |
| 15 µH | 4.27 / 5.38 µs | 2.44 A | 여유 1.1 µs |
| 22 µH | 5.18 / 5.38 µs | 2.22 A | 여유 없음 |

### 4.5 시뮬레이션 검증 (Cs 82.5 nF, Ls 10 µH, 직류 동작점, 무손실 이상 소자)

| Lp | 입력 | Vds 해석 | Vds 시뮬 | 반전 / 온타임 | 공진 구간 FET 전류 최대 | 턴오프 피크 | D1 평균 |
|---|---|---|---|---|---|---|---|
| 12 µH | 18 V | — | 94.7 V | 4.13 / 7.12 µs | 19.0 A | 22.7 A | 1.35 A |
| 12 µH | 30 V | 107.0 V | 107.0 V | 3.86 / 5.95 µs | 18.7 A | 22.9 A | 1.52 A |
| 12 µH | 37.6 V | 113.5 V | 113.8 V | 3.48 / 5.38 µs | 17.3 A | 22.3 A | 1.41 A |
| 12 µH | 50 V (250 W 가정) | 125.3 V | 126.0 V | 3.12 / 4.63 µs | 16.5 A | 22.2 A | 1.31 A |
| 24 µH | 30 V | 101.7 V | 101.7 V | 3.77 / 5.92 µs | **19.8 A** | 18.9 A | 1.41 A |
| 24 µH | 37.6 V | 107.5 V | 107.7 V | 3.37 / 5.33 µs | **18.1 A** | 17.8 A | 1.27 A |

해석식과 시뮬레이션의 Vds 차이는 0.7 V 이내.

### 4.6 손실·효율·FET 온도 (추정)

Cs 68 nF, Lp 12 µH 로 계산한 값이다. 82.5 nF 로는 다시 계산하지 않았으며, 스너버 손실이 조금 늘어난다.
가정: FET 150 V 7 mΩ 1개(고온 저항 1.7배, 전환 20 ns), 트랜스 1차 3 mΩ·2차 0.35 Ω·철손 1.0 W, 스너버 다이오드 Vf 0.8 V.

라인 평균(출력 0~342 V, 0~250 W 맥동, 평균 125 W/상):

| 항목 | 18 V (피크 204 W) | 30 V | 37.6 V |
|---|---|---|---|
| FET (도통 + 스위칭) | 1.81 W | 1.39 W | 1.15 W |
| 트랜스 | 0.77 W | 1.04 W | 1.16 W |
| 2차 SiC 다이오드 | 0.50 W | 0.65 W | 0.65 W |
| LCD 스너버 | 1.62 W | 1.32 W | 1.22 W |
| 기타 | 0.25 W | 0.33 W | 0.33 W |
| **합계** | **4.95 W** | **4.73 W** | **4.51 W** |
| **플라이백 단 효율** | **95.4 %** | **96.4 %** | **96.5 %** |
| 참고: RCD(80 V 클램프) | 93.5 % | 94.5 % | 94.7 % |

- 직류 동작점(342 V, 250 W 연속, 468 Ω 부하에 해당)에서는 FET 3.24 W @30 V, 효율 96.4 %.
- FET 접합 온도 = 주위 온도 + 손실 × 열저항. 주위 60 ℃, 30 V 라인 평균 1.39 W 기준: 20 K/W → 88 ℃, 40 K/W → 116 ℃.
- 언폴더, 출력 필터, 제어 전원 손실은 포함하지 않았다.
- FET 품번, 방열 방식, 케이스 내부 온도가 정해지지 않아 온도는 한 값으로 확정하지 못했다.

### 4.7 코어 포화

```
Bpk = 12 µH × 22.4 A / (4 × Ae) = 67.1 / Ae[mm²]  (T)
```

| Ae | Bpk | 판정 |
|---|---|---|
| 149 mm² | 0.45 T | 포화 |
| 170 mm² | 0.39 T | 포화 경계 |
| 224 mm² | 0.30 T | 설계 한계선 |

ER4042H 의 Ae 와 재질은 확인하지 못했다. Ae 가 224 mm² 미만이면 권선비 7.5 를 유지한 채 턴수를 6:45 또는 8:60 으로 올린다(이 경우 Llk 재측정 필요).

---

## 5. 전제조건과 미해결 항목

| # | 항목 | 내용 | 필요한 조치 |
|---|---|---|---|
| 1 | **FET 내압** | LCD 를 달아도 Vds 는 Vin + VOR = 83 V 아래로 내려가지 않는다. 100 V 소자로는 불가 | 150 V 급으로 교체 |
| 2 | **전류 검출 위치** | 턴온 후 약 3.5 µs 동안 공진 전류가 FET 에 겹친다. Lp 24 µH 면 그 최대값이 턴오프 피크를 넘어 피크전류 비교기가 조기 트립 → 반전 미완료 → 다음 턴오프에서 클램프 상실 | 전류 검출을 1차 권선 직렬 위치로 옮기거나 Lp 12 µH 유지(여유 약 4 A) |
| 3 | **과전류 설정** | 필요 Ipk: 12 µH 22.4 A, 24 µH 18.6 A. 현 설정 18 A 로는 30 V 에서 250 W 불가 | 설정 상향 |
| 4 | 최소 온타임 | 전류가 큰 구간에서 온타임 ≥ 4 µs. 영교차 부근의 반전 미완료는 에너지가 작아 무해 | 펌웨어 확인 |
| 5 | **실제 Lp** | 12 µH(사용자 제공)와 24 µH(펌웨어) 중 어느 쪽인지 미확정 | 실측 |
| 6 | Llk | 0.16 µH 의 실측 여부 미확인 | 2차 단락 후 1차 측정 |
| 7 | ER4042H Ae·재질 | 미확인 | 데이터시트 |
| 8 | 스위칭 주파수 | 100 kHz 는 가정 | 확인 |
| 9 | PSIM 검증 | 미실시 | 6장 |

---

## 6. 다음 작업

### 6.1 PSIM 검증

회로: Vin — (Llk 0.16 µH + 이상 트랜스 4:30, Lm 12 또는 24 µH) — FET(Coss 1 nF) / 2차 SiC 다이오드 — 342 V 전압원.
스너버: Cs 82.5 nF(드레인–X), D1(X→Vin+), D2 + Ls 10 µH(GND→X).
제어: 100 kHz 피크전류 + 슬로프 보상(VOR/Lm). 듀티가 0.5 를 넘으므로 보상이 없으면 저조파 진동이 난다. 스텝 ≤ 5 ns.

| 측정 | 기준값 (Lp 12 µH) | 합격 |
|---|---|---|
| Vds 피크 @37.6 V | 113.8 V | ≤ 120 V |
| Vds 피크 @30 V | 107.0 V | ≤ 120 V |
| Cs 전압 범위 | −Vin ~ +76 V | — |
| 반전 완료 시간 | 3.5~3.9 µs | < 온타임 |
| 공진 구간 FET 전류 최대 | 17.3~18.7 A | < 턴오프 피크 |
| Ls 실효전류 | 2.7 A | ≤ 3 A |
| D1 평균전류 | 1.4~1.5 A | ≤ 5 A |

라인주기(0~342 V |sin|) 운전에서 15° 이하 구간의 Vds 와 Cs 전압도 확인한다.

### 6.2 실물 확인 순서

1. Lp, Llk 실측 → 4장 식에 넣어 Cs 직렬 수 재확인
2. FET 150 V 급 선정, 전류 검출 위치 결정
3. Cs 필름의 재질(PP 여야 함)과 리플 전류·dv/dt 정격 확인
4. 저전압·저전류에서 Vds, Cs 전압, Ls 전류 파형 확인 후 단계 승압

### 6.3 LCD 가 맞지 않을 때

| 상황 | 대안 |
|---|---|
| Llk 가 0.3 µH 이상 | 권선 구조 변경으로 Llk 저감, 또는 200 V FET |
| FET 100 V 유지 | 권선비 상향(반사전압 저감) 또는 액티브 클램프 |
| 단순화 우선 | RCD 클램프 (효율 약 2 %p 손해) |

---

## 7. 부품 관련 메모

- **Cs 재질**: PP 필름 또는 C0G. X7R·X7T MLCC 는 손실계수가 커서 자체 발열이 약 2.4 W 로 어림되어 부적합. 450 V 100 nF MLCC 는 C0G 일 때만 가능.
- **필름 직렬**: 개당 전체 전류가 흐른다. 전압은 개당 약 20 V 라 분담 저항 불필요. 직렬 수만큼 배선 인덕턴스가 늘므로 서로 붙여 배치하고 드레인–Cs–D1 경로를 짧게.
- **병렬 FET**: 스너버는 트랜스당 1개. Cs 를 두 드레인의 합류점에 대칭으로 배치. 게이트 저항은 FET 별로.

---

## 8. 정정 이력

| 내용 | 정정 |
|---|---|
| 초기 예시에 Llk 0.81 µH 사용 | 그 값은 8 W 보조전원 트랜스의 것. 메인은 0.16 µH |
| 초기 클램프 전압 근사식 | `Vc,pk = VOR + Ipk·√(Llk/Cs)` 로 교체 |
| "턴온 직후 FET 전류 13~14 A" | 주 전류 상승분 누락. 시뮬레이션 값 17~20 A 가 맞다 |
| "반전 미완료는 무해" | 저전류(영교차 부근)에서만 해당. 고전류에서는 클램프 상실 |

---

## 9. 관련 자료

| 자료 | 위치 |
|---|---|
| 이 문서, 선정 문서, 시뮬레이션 | 저장소 `Hatkeit/embedded-product-review`, 브랜치 `claude/1ed3431-flt-rdy-waveform-iuu0vx`, `docs/V2000_2_PSIM/` |
| LCD 회로도 | 같은 브랜치 `docs/lcd-snubber/` |
| 이전 설계서(ETD44, 10:60, 23 µH, 액티브 클램프 기준안) | 브랜치 `claude/flyback-transformer-150w-spec-o2yup2`, `docs/microinverter-250w/system-spec.md` |
| V2000 회로도 검토(25건) | V2000_CAN 세션의 artifact "V2000 회로도 검토" |
| V2000 교차 검토 상세 | V2000_CAN 세션 내 `v2000-cross-review.md` (푸시되지 않음) |
| PSIM 준비 세션 | `V2000_2_PSIM` (2026-11-13 생성, 결과 미확인) |
| V1109 브링업 연구노트(1ED3431, LTC4368) | 같은 브랜치 `notes/research-note-1ed3431.md` |

---

## 부록 A. 시뮬레이션 스크립트 `lcd_snubber_sim.py`

Python 3 표준 라이브러리만 사용. `python3 lcd_snubber_sim.py` 로 실행.

```python
#!/usr/bin/env python3
"""V2000 플라이백 LCD 스너버 시간영역 검증 (이상 스위치·이상 다이오드, 고정 출력전압).

상태: ip(1차 전류), im(자화 전류), vD(드레인), vCs(=vD-vX), iLs
제어: 고정 주파수 피크전류 제어 + 슬로프 보상(Se = VOR/Lm, D>0.5 저조파 진동 방지).
실행: python3 lcd_snubber_sim.py
"""
import math

def analytic(Lp, Vin, Cs, Ls, Llk=0.16e-6, a=7.5, Vo=342.0, P=250.0, f=100e3, eta=0.93, Vf=1.5):
    T = 1 / f; VOR = (Vo + Vf) / a
    D = VOR / (VOR + Vin); Imid = P / eta / (Vin * D); dI = Vin * D * T / Lp
    Ipk, Iv = Imid + dI / 2, Imid - dI / 2
    Vc = VOR + Ipk * math.sqrt(Llk / Cs)
    w = 1 / math.sqrt(Ls * Cs); Ires = Vc * math.sqrt(Cs / Ls)
    t1 = (math.pi - math.acos(Vin / Vc)) / w
    t2 = Ls * Ires * math.sqrt(1 - (Vin / Vc) ** 2) / Vin
    return dict(VOR=VOR, D=D, Ipk=Ipk, Iv=Iv, Vc=Vc, Vds=Vin + Vc, Ires=Ires, t_inv=t1 + t2, t_on=D * T)

def simulate(Lp, Vin, Cs, Ls, Ipk_ref, Llk=0.16e-6, a=7.5, Vo=342.0, f=100e3, Vf=1.5,
             Coss=1e-9, cycles=30, dt=0.25e-9):
    T = 1 / f; VOR = (Vo + Vf) / a; n_per = int(round(T / dt)); Lm = Lp
    Se = VOR / Lm; D0 = VOR / (VOR + Vin)      # 보상 램프: 정상상태 턴오프 시점에서 Ipk_ref와 일치
    ip = im = 0.0; vD = Vin; vCs = 0.0; iLs = 0.0; on = False
    meas = None
    for k in range(cycles * n_per):
        ph = k % n_per
        if ph == 0:
            on = True; t_on_start = k
            if k // n_per >= cycles - 5 and meas is None:
                meas = dict(vds=0.0, vcs_max=-1e9, vcs_min=1e9, isw_on=0.0, e_out=0.0, q_d1=0.0,
                            ils2=0.0, isw2=0.0, n=0, tinv=[], ton=[], ipk=0.0)
            inv_done = False
        if on and ip >= Ipk_ref + Se * (D0 * T - (k - t_on_start) * dt) and (k - t_on_start) * dt > 200e-9:
            on = False
            if meas is not None: meas['ton'].append((k - t_on_start) * dt)
        iD1 = 0.0
        if on:
            vD = 0.0
            if im > ip + 1e-9:                     # 2차 다이오드 도통 중(턴온 직후 전류 전이)
                ip += (Vin + VOR) / Llk * dt; im -= VOR / Lm * dt
                if ip > im: ip = im
            else:
                ip += Vin / (Llk + Lm) * dt; im = ip
            vX = -vCs
            if iLs > 0 or vX < 0:
                if vX >= Vin - 1e-6 and iLs > 0:   # D1 도통: Cs는 -Vin에 고정, Ls 전류는 입력으로
                    vCs = -Vin; iD1 = iLs; iLs -= Vin / Ls * dt
                else:
                    iLs += vCs / Ls * dt; vCs -= max(iLs, 0.0) / Cs * dt
                if iLs <= 0:
                    iLs = 0.0
                    if meas is not None and not inv_done and (k - t_on_start) * dt > 100e-9:
                        meas['tinv'].append((k - t_on_start) * dt); inv_done = True
            isw = ip + (iLs if iD1 == 0.0 else 0.0)
        else:
            sec = (im > ip + 1e-9) or (Lm / (Lm + Llk) * (Vin - vD) < -VOR and im > 0)
            if sec:
                ip += (Vin + VOR - vD) / Llk * dt; im -= VOR / Lm * dt
                if im < 0: im = 0.0
            else:
                ip += (Vin - vD) / (Llk + Lm) * dt; im = ip
            vX = vD - vCs
            d1 = vX >= Vin - 1e-6 and (ip * Cs / (Cs + Coss) + iLs) > 0   # 허용오차: 부동소수 비교로 인한 D1 채터링 방지
            if d1:
                dv = ip / (Cs + Coss) * dt; vD += dv; vCs = vD - Vin
                iD1 = ip * Cs / (Cs + Coss) + iLs
                if iLs > 0: iLs = max(0.0, iLs - Vin / Ls * dt)
            else:
                vD += (ip + iLs) / Coss * dt; vCs -= iLs / Cs * dt
                vX = vD - vCs
                if iLs > 0 or vX < 0: iLs = max(0.0, iLs - vX / Ls * dt)
            if vD < 0: vD = 0.0                    # 바디 다이오드
            isw = 0.0
        if meas is not None:
            m = meas; m['n'] += 1
            m['vds'] = max(m['vds'], vD); m['vcs_max'] = max(m['vcs_max'], vCs); m['vcs_min'] = min(m['vcs_min'], vCs)
            m['ipk'] = max(m['ipk'], ip)
            if on and iLs > 0 and iD1 == 0.0: m['isw_on'] = max(m['isw_on'], isw)   # 공진 구간의 스위치 전류 최대
            if (not on) and im > ip: m['e_out'] += VOR * (im - ip) * dt
            m['q_d1'] += iD1 * dt; m['ils2'] += iLs * iLs * dt; m['isw2'] += isw * isw * dt
    tt = meas['n'] * dt
    return dict(Vds=meas['vds'], Vc=meas['vcs_max'], Vcs_min=meas['vcs_min'], Isw_on=meas['isw_on'],
                Pout=meas['e_out'] / tt, Id1=meas['q_d1'] / tt, Pret=Vin * meas['q_d1'] / tt,
                ILs_rms=math.sqrt(meas['ils2'] / tt), Isw_rms=math.sqrt(meas['isw2'] / tt),
                t_inv=sum(meas['tinv']) / max(1, len(meas['tinv'])), t_on=sum(meas['ton']) / max(1, len(meas['ton'])),
                Ipk=meas['ipk'])

if __name__ == "__main__":
    print("== Ls 스윕 (Cs = 330 nF x4 = 82.5 nF): 공진 구간 스위치 전류가 턴오프 피크를 넘으면 피크전류 비교기 조기 트립 위험")
    for Lp in (12e-6, 24e-6):
        for Vin in (30.0, 37.6):
            for Lsx in (6.8e-6, 10e-6, 15e-6, 22e-6):
                an = analytic(Lp, Vin, 82.5e-9, Lsx); r = simulate(Lp, Vin, 82.5e-9, Lsx, an['Ipk'])
                print(f"  Lp={Lp*1e6:.0f}u Vin={Vin:4.1f} Ls={Lsx*1e6:4.1f}u  Vds={r['Vds']:6.1f}  t_inv/t_on={r['t_inv']*1e6:4.2f}/{r['t_on']*1e6:4.2f}"
                      f"  Isw_bump={r['Isw_on']:5.1f}  Ipk={r['Ipk']:5.1f}  {'조기트립 위험' if r['Isw_on'] > r['Ipk'] - 1.0 else 'OK'}  ILs_rms={r['ILs_rms']:.2f}")
    Ls = 10e-6
    cases = [(Lp, Vin, n) for Lp in (12e-6, 24e-6) for Vin in (30.0, 37.6) for n in (4,)]
    cases += [(12e-6, 37.6, 3), (12e-6, 37.6, 5), (12e-6, 18.0, 4), (12e-6, 50.0, 4)]
    print("Lp  Vin  Cs      | 해석: Ipk  Vds   t_inv/t_on | 시뮬: Ipk  Pout  Vds    Vcs(min)  t_inv/t_on  Isw_on  ILs_rms Id1  Pret")
    for Lp, Vin, n in cases:
        Cs = 330e-9 / n
        an = analytic(Lp, Vin, Cs, Ls)
        ipk_ref = an['Ipk'] if Vin > 20 else 22.4          # 18 V는 전류 제한 운전
        s = simulate(Lp, Vin, Cs, Ls, ipk_ref)
        print(f"{Lp*1e6:3.0f} {Vin:5.1f} {Cs*1e9:5.1f}n(x{n}) | {an['Ipk']:5.1f} {an['Vds']:6.1f} {an['t_inv']*1e6:4.2f}/{an['t_on']*1e6:4.2f} |"
              f" {s['Ipk']:5.1f} {s['Pout']:5.0f} {s['Vds']:6.1f} {s['Vcs_min']:7.1f}   {s['t_inv']*1e6:4.2f}/{s['t_on']*1e6:4.2f}   {s['Isw_on']:5.1f}  {s['ILs_rms']:5.2f} {s['Id1']:5.2f} {s['Pret']:5.1f}")
```

## 부록 B. 실행 결과

```
== Ls 스윕 (Cs = 330 nF x4 = 82.5 nF): 공진 구간 스위치 전류가 턴오프 피크를 넘으면 피크전류 비교기 조기 트립 위험
  Lp=12u Vin=30.0 Ls= 6.8u  Vds= 107.0  t_inv/t_on=3.17/5.95  Isw_bump= 19.3  Ipk= 22.9  OK  ILs_rms=2.99
  Lp=12u Vin=30.0 Ls=10.0u  Vds= 107.0  t_inv/t_on=3.86/5.95  Isw_bump= 18.7  Ipk= 22.9  OK  ILs_rms=2.74
  Lp=12u Vin=30.0 Ls=15.0u  Vds= 107.0  t_inv/t_on=4.74/5.95  Isw_bump= 18.5  Ipk= 22.9  OK  ILs_rms=2.49
  Lp=12u Vin=30.0 Ls=22.0u  Vds= 107.0  t_inv/t_on=5.74/5.96  Isw_bump= 18.8  Ipk= 22.8  OK  ILs_rms=2.27
  Lp=12u Vin=37.6 Ls= 6.8u  Vds= 113.8  t_inv/t_on=2.87/5.38  Isw_bump= 17.7  Ipk= 22.3  OK  ILs_rms=2.97
  Lp=12u Vin=37.6 Ls=10.0u  Vds= 113.8  t_inv/t_on=3.48/5.38  Isw_bump= 17.3  Ipk= 22.3  OK  ILs_rms=2.70
  Lp=12u Vin=37.6 Ls=15.0u  Vds= 113.8  t_inv/t_on=4.27/5.38  Isw_bump= 17.5  Ipk= 22.3  OK  ILs_rms=2.44
  Lp=12u Vin=37.6 Ls=22.0u  Vds= 113.8  t_inv/t_on=5.18/5.38  Isw_bump= 18.2  Ipk= 22.3  OK  ILs_rms=2.22
  Lp=24u Vin=30.0 Ls= 6.8u  Vds= 101.7  t_inv/t_on=3.11/5.92  Isw_bump= 20.8  Ipk= 18.9  조기트립 위험  ILs_rms=2.86
  Lp=24u Vin=30.0 Ls=10.0u  Vds= 101.7  t_inv/t_on=3.77/5.92  Isw_bump= 19.8  Ipk= 18.9  조기트립 위험  ILs_rms=2.60
  Lp=24u Vin=30.0 Ls=15.0u  Vds= 101.7  t_inv/t_on=4.63/5.92  Isw_bump= 19.1  Ipk= 18.9  조기트립 위험  ILs_rms=2.36
  Lp=24u Vin=30.0 Ls=22.0u  Vds= 101.7  t_inv/t_on=5.61/5.91  Isw_bump= 18.8  Ipk= 18.9  조기트립 위험  ILs_rms=2.14
  Lp=24u Vin=37.6 Ls= 6.8u  Vds= 107.7  t_inv/t_on=2.78/5.33  Isw_bump= 19.0  Ipk= 17.8  조기트립 위험  ILs_rms=2.72
  Lp=24u Vin=37.6 Ls=10.0u  Vds= 107.7  t_inv/t_on=3.37/5.33  Isw_bump= 18.1  Ipk= 17.8  조기트립 위험  ILs_rms=2.47
  Lp=24u Vin=37.6 Ls=15.0u  Vds= 107.7  t_inv/t_on=4.12/5.33  Isw_bump= 17.5  Ipk= 17.8  조기트립 위험  ILs_rms=2.24
  Lp=24u Vin=37.6 Ls=22.0u  Vds= 107.7  t_inv/t_on=5.00/5.33  Isw_bump= 17.4  Ipk= 17.8  조기트립 위험  ILs_rms=2.03
Lp  Vin  Cs      | 해석: Ipk  Vds   t_inv/t_on | 시뮬: Ipk  Pout  Vds    Vcs(min)  t_inv/t_on  Isw_on  ILs_rms Id1  Pret
 12  30.0  82.5n(x4) |  22.4  107.0 3.94/6.04 |  22.9   255  107.0   -30.0   3.86/5.95    18.7   2.74  1.52  45.6
 12  37.6  82.5n(x4) |  21.6  113.5 3.49/5.49 |  22.3   260  113.8   -37.6   3.48/5.38    17.3   2.70  1.41  53.1
 24  30.0  82.5n(x4) |  18.6  101.7 3.79/6.04 |  18.9   251  101.7   -30.0   3.77/5.92    19.8   2.60  1.41  42.3
 24  37.6  82.5n(x4) |  17.3  107.5 3.37/5.49 |  17.8   255  107.7   -37.6   3.37/5.33    18.1   2.47  1.27  47.8
 12  37.6 110.0n(x3) |  21.6  109.5 3.93/5.49 |  22.5   259  109.9   -37.6   3.94/5.33    19.1   3.18  1.76  66.3
 12  37.6  66.0n(x5) |  21.6  117.1 3.19/5.49 |  22.1   260  117.2   -37.6   3.16/5.41    16.0   2.37  1.19  44.6
 12  18.0  82.5n(x4) |  26.2  100.3 5.68/7.18 |  22.7   208   94.7   -18.0   4.13/7.12    19.0   2.06  1.35  24.3
 12  50.0  82.5n(x4) |  21.2  125.3 3.11/4.78 |  22.2   270  126.0   -50.0   3.12/4.63    16.5   2.64  1.31  65.5
```
