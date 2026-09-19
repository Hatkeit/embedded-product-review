# V3000 Cycloconverter Microinverter — 이관 문서 (Handoff)

| 항목 | 내용 |
|---|---|
| 모델명 | V3000 |
| 제품군 | 모듈 직결형 계통연계 마이크로인버터 (MLPE) — V2000의 차세대 |
| 전력단 구조 | **단일단 · 듀얼 액티브 브리지 · 직렬공진 사이클로컨버터** (DC 링크 없음, 언폴더 없음) |
| 기준 아키텍처 | Enphase IQ9 시리즈 (GaN BDS + Kestrel ASIC) · Infineon REF_500W_CYCLO_BDSGAN · TI TIDA-010954 |
| 목표 계통 | 한국 단상 220 V / 60 Hz, KS C 8565 — V2000 요구 승계 `[가정]` |
| 정격 출력 | 500 W (V2000 승계) `[미확정 — IQ9N 427 VA · Infineon 레퍼런스 240 V / 2.1 A · TI 레퍼런스 600 W]` |
| 문서 버전 | 0.2 (Handoff + 2차 확인) |
| 작성일 | 2026-09-19 |
| 상태 | V2000 세션의 IQ9 분석 결과를 V3000 항목으로 이관. 0.2에서 검색 스니펫 기반 2차 확인 결과 반영. 설계 착수 전 |

> **문서 성격**
> V2000 작업 중 수행한 Enphase IQ9 사이클로컨버터 분석을 V3000 프로젝트의 출발점으로
> 정리한 이관 문서입니다. 원문(백서·앱노트·데이터시트) 접근이 차단된 환경에서 검색
> 스니펫으로 확인한 값만 썼고, 확인 상태를 `[확인]` `[참고]` `[미확보]` `[추정]` 으로
> 구분했습니다. V3000 설계 사양서는 이 문서의 §6 미확보 항목을 채운 뒤 별도로 작성합니다.
>
> **0.2 변경 요약** — Infineon 레퍼런스 설계의 실제 스위치 배치(2차 BDS **2개 하프브리지**)와
> 변조 시퀀스 확인(§3.1), BDS AC 전용 제약의 수치 확인(§3.2), 효율·Kestrel 공정 상충 해소(§4, §7),
> 특허 출원일 확인(§6 OI-3000-02), TI 레퍼런스 설계 추가(§3.3), BDS 2차 소싱 후보 추가(§3.4).
> 이번 세션에서도 infineon.com · 부품 미러 · 특허 사이트 · archive.org 전부 차단되어
> **원문 PDF는 여전히 미확보**입니다 (§8).

---

## 1. 이관 배경

V2000은 "절연형 DC-DC 정현파 성형 + 60 Hz 언폴더" 구조이고, 그 원리·구동·보호를
S2G1812 리버스 분석과 Enphase IQ7+ 분해기로 검증했습니다. 그런데 Enphase의 최신 세대
IQ9(2025~26)는 **언폴더 자체가 없는 구조**로 이동했습니다. 이 구조는 V2000의 범위를
벗어나므로 별도 프로젝트 V3000으로 분리합니다.

V2000 → V3000에서 사라지는 것: **2차 정류기 · DC 링크(정류 정현파 버스) · 언폴더**.
생기는 것: **GaN 양방향 스위치(BDS) 2~4개 · 직렬 공진 탱크 · 주기별 탱크 센싱 제어기**.

---

## 2. 기준 아키텍처 — Enphase IQ9 `[확인: Enphase 백서·보도]`

Enphase 자체 표현: "single-stage, dual-active-bridge, series-resonant cycloconverter topology.
Requires cycle-by-cycle knowledge of resonant tank current and voltage, with gate transitions
timed at **hundreds of kilohertz** and **nanosecond-scale precision**." `[확인: Enphase GaN 백서 보도 2026-05-21 · Kestrel 백서 보도 2026-07-27]`

```
PV 28~45 V → C_in → [1차 풀브리지 S1~S4 · 80 V Si] → L_r · C_r (직렬 공진, 수백 kHz)
   → T1 (HF 절연 변압기, 1:n) ‖ 절연 장벽 ‖
   → [사이클로컨버터 · GaN BDS ×2 또는 ×4] → L_f · C_f → 계통 220 V / 60 Hz

제어: ASIC (PV 측) — 탱크 전류·전압을 스위칭 주기마다 센싱
      → 1차 게이트 4개 직접 구동, 2차 BDS 게이트(4 또는 8개)는 강화절연 드라이버로 장벽 통과
```

### 2.1 동작 원리

1. 1차 풀브리지가 수백 kHz 구형파를 만든다 (DAB의 1차).
2. 직렬 공진 탱크(L_r·C_r)가 그것을 정현파 전류로 바꾼다 → 넓은 범위에서 ZVS.
3. 2차의 BDS가 **고주파 반주기 하나하나의 극성을 골라 붙여** 60 Hz 정현파를 직접 합성한다.
   DAB의 2차 브리지를 양방향 스위치로 바꾼 것이므로 출력이 DC가 아니라 AC가 된다.
4. 대용량 저장 소자가 없다 → 입력 디커플링(C_in)만 남는다.

### 2.2 양방향 스위치(BDS)가 필요한 이유

사이클로컨버터의 스위치는 양쪽 극성 전압을 차단하고 양쪽 방향 전류를 흘려야 한다.
종래에는 MOSFET 2석 back-to-back(저항·전하·면적 2배). GaN BDS는 채널 하나에 게이트 두 개로
같은 일을 소자 하나가 한다. Enphase 백서: Si 대비 손실 −68 %, 단방향 GaN 대비 −42 % `[확인]`.
대가: **소자당 게이트 드라이브 2채널**.

### 2.3 회로도

PSIM 심볼 회로도(전체 회로 · BDS 해부 · 동작 파형 개념도):
- 아티팩트: https://claude.ai/artifact/Tp5yC5MiwaLUNgBM8XXqLj
- 저장소: `docs/enphase-iq9-cycloconverter-psim.html`

> **0.2 주의** — 이 회로도는 Enphase의 "dual-active-bridge" 표현을 따라 2차를 **BDS 4석 풀브리지**로
> 그렸습니다. Infineon 레퍼런스 설계는 **BDS 2석 하프브리지 + 공진 커패시터 C1·C2**입니다(§3.1).
> Enphase 실물이 어느 쪽인지는 분해기가 없어 `[추정]` 상태이며, 회로도는 §3.1 확정 후 갱신합니다.

---

## 3. 소자 후보 — Infineon 레퍼런스 설계 기준

Enphase는 "Infineon CoolGaN BDS" 사용만 밝혔고 실제 품번은 미공개. 아래는 **같은 토폴로지의
Infineon 공개 레퍼런스 설계 REF_500W_CYCLO_BDSGAN**(500 W)의 소자이며 V3000 1차 후보로 쓴다.

| 회로 위치 | 품번 | 확인된 사양 | 상태 |
|---|---|---|---|
| 사이클로컨버터 BDS ×2 (레퍼런스) | Infineon **IGLT65R055B2** | 650 V (서지 850 V) · **V_ss,cont 340 V(AC) rms · V_ss,trans 650 V (≤ 5 ms)** · Rss(on) 55 mΩ typ · ±73 A · Qg 5.4 nC / 72 nC@400 V · V_th 0.8~1.6 V · GIT 정상오프 · 듀얼 게이트 + 듀얼 소스 + 기판 단자(기판을 낮은 쪽 소스에 자동 연결하는 제어 회로 내장) · TOLT 상면 방열 · **AC 전용(DC 연속 차단 불가)** · 제품 인증 보고서(PQR) 공개됨 | `[확인]` |
| 동일 계열 대안 | IGLT65R110B2 | 110 mΩ typ · 데이터시트 Rev 1.0 2025-10-02 | `[확인]` |
| 1차 풀브리지 ×4 | ISC014N08NM6 / ISC056N08NM6 | OptiMOS 6 80 V · 1.45 mΩ (Qg 79 nC) / 5.6 mΩ (Qg 21 nC) · SuperSO8 | `[참고]` |
| 1차 추가 양방향 스위치 S5·S6 | — (품번 미확보) | 레퍼런스에 존재. 역할 미확보 — §3.1 | `[미확보]` |
| 1차 게이트 드라이버 | 1EDN8550B | 단채널 비절연 · 완전 차동 입력(TDI) · CMR ±150 V 동적 · UVLO 8 V · SOT-23-6 · Würth 레퍼런스 검색에 이 보드와 함께 등재 | `[확인]` |
| BDS 절연 드라이버 | 2EDR7259X | 2ch 강화절연 · 5 A / 9 A · 38 ns · CMTI 150 V/ns · 8 kV · GIT용 | `[참고]` 수량: 하프브리지 BDS 2석 → **×2** (4ch) · 풀브리지 4석 → ×4 |
| 센싱 op-amp | TI OPA2350 | 레퍼런스 BOM에 포함 (TI E2E 문의 스레드 제목으로 확인). 용도(탱크 전류 센싱 추정)는 미확보 | `[참고]` |
| 제어기 (레퍼런스) | PSoC Control C3 (Cortex-M33) | MPPT · 계통연계/독립 · 유효/무효 · 버스트 모드 · PF 0.8~1.0 · OVP/OCP/열 보호 · AC 계통 차단 릴레이 | `[확인]` |
| 제어기 (Enphase) | Kestrel ASIC | 5세대 · **22 nm CMOS** · **4 × 100 Msps ADC** · 하드웨어 제어루프 >100 kHz · PLC/LVDS 컨트롤러 · 하드웨어 격리 · 암호/보안부팅 · 기능안전 · IQ Battery·양방향 EV 충전기·IQ SST에도 공용 | `[확인]` 55 nm 표기는 오류로 판정 |
| L_r · C_r · n · f_s · C_in · L_f/C_f | — | 어느 스니펫에도 값 없음. 앱노트 원문 필요 | `[미확보]` |

### 3.1 Infineon 레퍼런스 설계의 실제 구조 `[확인: 앱노트 스니펫]`

앱노트 본문 스니펫에서 확인한 내용. 이관 문서 0.1의 "BDS 4석 풀브리지" 가정과 다르다.

```
[1차]  DC→AC 풀브리지 S1~S4  +  추가 양방향 스위치 (S5·S6)  →  승압 변압기
[2차]  AC→AC 사이클로컨버터 = 하프브리지  BDS(S7-8) · BDS(S9-10)
       "common-drain bidirectional GaN devices integrated into a single package"
       공진 커패시터 C1·C2 가 2차(계통측)에 있고, 여기로 전달된 에너지가 계통 출력을 공급
```

- **변조 시퀀스** `[확인]`
  - 1차: S2와 S6는 항상 동시에 on/off, S4와 S5도 동시에 on/off.
  - 계통 **양의 반주기**: S8·S9 상시 on, **S7·S10 이 상보 스위칭**.
  - 계통 **음의 반주기**: S7·S10 상시 on, **S8·S9 가 상보 스위칭**.
  - 즉 BDS 한 개의 두 게이트 중 하나는 반주기 동안 물려 두고(다이오드처럼), 다른 하나만 HF 스위칭한다.
    이것이 "half-wave cycloconverter" 방식이며, 학술적 원형은 Keyhani·Toliyat,
    *Half-Wave Cycloconverter-Based PV Microinverter Topology With Phase-Shift Power Modulation*,
    IEEE TPEL 2012-11 — 풀브리지 + 직렬공진 탱크 + 반파 사이클로컨버터, 전 스위치 ZVS, **위상이동 전력 변조** `[확인: 초록]`.
- **사양** `[확인]`: 입력 16~60 V · 출력 240 V / 2.1 A · 효율 측정 조건 T_amb 25 ℃, V_in 35 V, V_out 240 Vrms, 30분 이상 운전 후.
  Infineon 표현: "novel variation of the cyclo-converter topology", "resonant design able to operate with soft-switching".
- **2차 구조 해석** `[추정]`: "하프브리지 + C1·C2"는 BDS 2석이 한 레그, 커패시터 2개가 다른 레그를 이루는
  커패시터-레그 하프브리지로 읽힌다. 이 경우 변압기 2차에 센터탭이 필요 없고, C1·C2가 공진 커패시터와
  출력 분압을 겸한다. BDS 1석이 HF 2차 전류를 통째로 흘리므로 도통 손실 산정은 §4.1과 달라진다.
- **V3000 함의**: BDS 2석이면 절연 드라이브 4ch(2EDR7259X ×2), 게이트별 절연 전원 4개. 0.1의 8ch 산정은
  풀브리지를 택할 때만 유효. **하프브리지(레퍼런스) vs 풀브리지(Enphase DAB 표현) 선택이 첫 토폴로지 결정** → OI-3000-05.
- **S5·S6의 역할** `[미확보]`: 1차 풀브리지에 추가된 양방향 스위치. 클램프/프리휠(공진 전류 순환 구간용) 또는
  변압기 단락 구간용으로 추정되나 스니펫에 설명 없음 → OI-3000-11.

### 3.2 BDS AC 전용 제약의 수치 `[확인: Infineon 개발자 커뮤니티]`

- V_ss,cont = **340 V(AC)** — 정현파 **rms** 기준의 연속 차단 전압.
- V_ss,trans = **650 V** — 스위칭 과도 시 최대 **5 ms** 까지 견디는 전압.
- Infineon 답변: "designed exclusively for AC applications", "cannot continuously block DC voltages due to
  their internal structure and substrate control circuit". 기판 제어 회로가 낮은 쪽 소스에 기판을 동적으로 연결하는
  구조라 극성이 교번해야 정상 동작.
- 220 V 계통: 정격 220 Vrms(+10 % → 242 Vrms)는 340 Vrms 안. 단, BDS가 실제로 보는 전압은 HF 2차 전압 +
  C1/C2 전압의 합성이므로 **토폴로지별 소자 전압 스트레스는 PSIM으로 확인** → OI-3000-03.

### 3.3 두 번째 레퍼런스 — TI TIDA-010954 (600 W GaN 단상 사이클로컨버터) `[확인: TI 페이지·기사 스니펫]`

| 항목 | 내용 |
|---|---|
| 토폴로지 | 단일단 양방향 DC-AC, "cycloconverter (AC-DAB)" |
| DC 측 | 60 V · ±16 A · 풀 H-브리지 → HF 변압기. LMG2100R026 (100 V GaN 하프브리지 파워스테이지) |
| AC 측 | 230 VAC · 2.6 A · **하프브리지 = AC 스위치 2개**, 각 AC 스위치 = LMG3650R035 ×2 **공통 소스** 연결 (단방향 GaN 2석 back-to-back — BDS 미사용) |
| 제어기 | C2000 (DigitalPower SDK) |
| 기구 | 290 × 100 × 32 mm · 640 W/L · 히트싱크 없음 · 부품 상면 실장 |
| 용도 | 태양광 마이크로인버터 · BESS (양방향) |
| 문서 | Design Guide TIDUFD2 · 백서 SLVAG14 "How cycloconverters with GaN help optimize microinverters" — 원문 미확보 |

의미: **Infineon과 TI 모두 2차를 "AC 스위치 2개 하프브리지"로 구성**한다. Enphase만 DAB(풀브리지) 표현을 쓴다.
또한 두 레퍼런스 모두 범용 MCU(PSoC C3 · C2000)로 제어한다 → OI-3000-01 재정의.

### 3.4 BDS 2차 소싱 후보 `[확인: Power Electronics News "APEC 2026: Year Zero of BDS" · Renesas 보도 2026-03-23]`

| 공급사 | 품번 / 제품 | 사양 | 상태 |
|---|---|---|---|
| Infineon | IGLT65R055B2 / IGLT65R110B2 | 650 V · 55 / 110 mΩ · GIT · TOLT | 양산 |
| Renesas (Transphorm) | **TP65B110HRU** | 650 V · 110 mΩ · 4상한 스위치(FQS) · 평가킷 RTDACHB0000RS-MS-1 (AC 영교차 검출·ZVS 예제) | 양산 ("available in quantity") |
| Renesas | 650 V SuperGaN BDS | 2026-03 발표 · "solar inverters, AI data centers, OBC" | 신규 |
| Navitas | 650 V bidirectional GaNFast | — | 양산 |
| ST · TI | GaN BDS | APEC 2026 시연 · JEDEC 인증 진행 중 | 프리프로덕션 |
| Innoscience | VGaN 30~120 V | 저압 — 해당 없음 | — |

게이트 구조(GIT vs p-GaN Schottky)가 공급사마다 달라 **드라이버·게이트 RC가 호환되지 않는다**. 2차 소싱을 하려면 게이트 드라이브를 소자별 서브모듈로 분리해야 함 → OI-3000-12.

---

## 4. 기준 수치 (IQ9N) `[확인: 데이터시트·보도 스니펫]`

| 항목 | 값 |
|---|---|
| 피크/연속 출력 | 427 VA @240 V (405 VA @208 V) — "427 VA continuous" |
| 연속 출력 전류 | ≈ 1.78 A @240 V |
| MPPT 전압 | 28 ~ 45 V |
| 동작 / 기동 전압 | 18 ~ 58 V / 21 ~ 58 V |
| 연속 입력 전류 / 모듈 Isc | 16 A / 25 A |
| 모듈 호환 | 340 ~ 580 W |
| 효율 — 미국 주거용 IQ9N-A-US | **CEC 가중 97.5 % · 피크 최대 97.8 %** |
| 효율 — 유럽 IQ9N | **피크 최대 97.95 %** |
| 효율 — 상용 3상 IQ9N-3P-277 | CEC 가중 97.5 % |
| 주위 온도 | −40 ~ +65 ℃ |
| 치수 / 무게 | 214 × 176 × 30.8 mm · **1.1 kg (주거용) · 1.2 kg (상용 3상)** |
| 상용 3상 | IQ9N-3P 427 VA @277 V · IQ9S-3P 548 VA, 입력 18 A · 480Y/277 V |
| 출시 | 상용 3상 미국 출하 2026-01 · 주거용 미국 출시 2026-06-23 · 유럽 출시 별도 |

> 0.1의 "97.5 vs 97.95 상충"은 **지역·산정 기준 차이**로 해소: 97.5는 CEC 가중, 97.8은 미국 피크, 97.95는 유럽 피크.

### 4.1 산정치

```
입력 평균 전류 @28 V, 427 W       I_in = 15.3 A  (연속 입력 정격 16 A와 일관)
1차 rms ≈ 1.225 × 15.3 = 18.7 A → 2 × 1.45 mΩ × 18.7² ≈ 1.0 W
BDS 도통 — 풀브리지 가정 (직렬 2석, 60 Hz 1.78 A)   2 × 55 mΩ × 1.78² ≈ 0.35 W
BDS 도통 — 하프브리지 가정 (1석, HF 2차 전류 rms)     I_sec,rms 미확보 → PSIM 후 재산정
총 손실 @97.5 %                    427 × 0.025 ≈ 10.7 W → 자연대류, 30.8 mm 두께
```

V3000을 500 W / 220 V로 잡으면 출력 전류 2.27 A (Infineon 레퍼런스 240 V / 2.1 A와 같은 급).
1차 전류는 MPPT 하한에서 다시 계산할 것.

---

## 5. V2000에서 승계할 것 / 버릴 것

| 항목 | V2000 | V3000 |
|---|---|---|
| 계통·인증 요구 (220 V/60 Hz, KS C 8565, 단독운전 방지) | 유지 | **승계** |
| DC측 보호·서지·EMI 필터 | 유지 | 승계 (BDS AC 전용 제약 반영) |
| 언폴더 (SCR/MOSFET) 및 계통측 게이트 로직 | 있음 | **삭제** — BDS가 흡수 |
| 정류 정현파 버스 · 2차 정류 | 있음 | **삭제** |
| 능동 전력 디커플링(APD) 검토 | §5.3 | 재검토 — 단일단 구조에서 리플 처리 방식이 다름 |
| 계통측 플로팅 전원(FT-H12V) · 하드웨어 고장 버스 | 있음 | 삭제 — 절연 드라이버로 게이트만 통과. 하드웨어 보호는 **1차측에서 재설계** |
| 계통 차단 릴레이 | K300 (구동단 미실장) | **유지** — Infineon 레퍼런스도 AC 계통 차단 릴레이 포함 |
| 제어기 | STM32G474 (HRTIM 184 ps) | **재검토** — Enphase는 100 Msps ADC 4개 + HW 루프. 단 Infineon(PSoC C3)·TI(C2000) 레퍼런스는 범용 MCU로 구현 → G474 유지 가능성 재평가 |

---

## 6. 설계 이슈 목록 (Open Issues)

| ID | 이슈 | 위험 | 조치 |
|---|---|---|---|
| **OI-3000-01** | **제어기 선정** — Enphase 방식(주기별 탱크 센싱, 100 Msps)과 레퍼런스 방식(PSoC C3 / C2000 + 아날로그 프런트엔드)의 차이. 0.2 확인: 두 공개 레퍼런스 모두 범용 MCU. STM32G474로 레퍼런스급 제어가 가능한지가 진짜 질문 | **높음** | (a) 레퍼런스 앱노트에서 센싱 체인(OPA2350 용도 포함) 확인 → (b) G474 + 비교기·피크 검출로 대체 가능성 판단 → (c) 불가 시 고속 ADC 외장 또는 FPGA. 착수 첫 결정 |
| **OI-3000-02** | **특허** — Enphase 직렬공진 사이클로컨버터 특허군. 0.2 확인 출원일: US 9,479,082 (13/342,368 · 출원 2012-01-03 · 가출원 2011-01-04 · Fornage/Zimmanck), US 8,797,767 (13/476,683 · 2012-05 · "Resonant power conversion circuit" — 사이클로컨버터 + 공진 회로 + IPT 포트), US 9,379,627 (14/450,858 · 8,797,767의 연속출원), US 9,130,570 "Four quadrant bidirectional switch" (우선일 2011-05-10 · 정상온 듀얼게이트 + 정상오프 2석 bi-cascode), US 2015/0078053 "Single-phase cycloconverter with integrated line-cycle energy storage", US 9,871,459 "deriving current for control in a resonant power converter", US 10,141,868 "resonant power conversion" | **높음** | 만료 추정 (20년, PTA 미반영): 9,479,082 ≈ **2032-01**, 8,797,767 / 9,379,627 ≈ **2032-05**, 9,130,570 ≈ 2032-05 `[추정]`. **청구항 원문은 이번에도 미확보**(Google Patents · USPTO · Justia 차단). Infineon·TI가 같은 급의 토폴로지를 공개 레퍼런스로 배포한다는 사실은 참고일 뿐 자유실시 근거가 아님. 청구항 검토가 설계 검토보다 먼저 |
| OI-3000-03 | BDS AC 전용 제약 — V_ss,cont 340 V(AC) rms · V_ss,trans 650 V ≤ 5 ms · DC 연속 차단 불가 `[확인]`. 계통 DC 오프셋·계통 고장·기동/정지 시퀀스에서 BDS 양단에 DC가 걸리는 구간이 있는지 | 높음 | 토폴로지별(하프/풀브리지) BDS 전압 스트레스 PSIM 확인 → 보호 시퀀스에 반영. 레퍼런스가 같은 부품을 같은 위치에 쓰므로 토폴로지 적합성 자체는 확인됨 |
| OI-3000-04 | 공진 탱크 설계 — L_r·C_r·n·f_s 미확보. 변조 방식은 **위상이동 전력 변조 + 반파 사이클로컨버터 시퀀스**로 확인(§3.1). f_s는 "수백 kHz"만 확인 | 높음 | Infineon 앱노트·TI TIDUFD2 원문 확보(사용자 업로드) → 값 확정 → PSIM 시뮬레이션 |
| OI-3000-05 | 2차 구조 선택 — **Infineon·TI 레퍼런스 = BDS(또는 AC 스위치) 2석 하프브리지 + C1·C2**, Enphase = "dual-active-bridge" 표현(풀브리지 4석 추정). 0.1의 "센터탭 + 2석" 가능성은 커패시터-레그 하프브리지로 대체 | 중 | V3000 토폴로지 결정: 하프브리지(부품 반, 드라이브 4ch, 소자 전압 스트레스 ↑) vs 풀브리지(8ch, 스트레스 ↓). PSIM 비교 후 결정 |
| OI-3000-06 | 절연 드라이버 채널 + 게이트별 절연 전원 — 하프브리지 4ch(2EDR7259X ×2) / 풀브리지 8ch(×4) | 중 | OI-05 결정 후 BOM 산정, 부트스트랩 가능 여부 확인 |
| OI-3000-07 | 입력 디커플링 — DC 링크가 없으므로 120 Hz 리플이 전부 C_in에 걸림. IQ7+ 기준 44.7 µF/W. 레퍼런스 입력 범위 16~60 V (TI: 60 V / ±16 A) | 중 | V2000 §17.4 재계산 |
| OI-3000-08 | 정격 확정 — 500 W(V2000 승계 · Infineon 레퍼런스 240 V/2.1 A) vs 427 VA(IQ9N) vs 600 W(TI) | 중 | 모듈 시장 조사 후 결정. 작업 가정은 500 W 유지 |
| OI-3000-09 | 하드웨어 보호 — 계통측 로직이 사라지므로 과전류·과전압 즉시 차단을 1차측에서 구현. 레퍼런스: OVP·OCP·열 보호 + AC 차단 릴레이 | 중 | 탱크 전류 비교기 트립 → 1차·2차 동시 게이트 차단 경로 설계 |
| OI-3000-10 | 열 설계 — 10.7 W(IQ9N 기준)를 30 mm 두께 자연대류로. TOLT 상면 방열 경로. TI는 600 W를 히트싱크 없이 32 mm 두께로 처리 | 중 | V2000 OI-08과 연계 |
| **OI-3000-11** *(신규)* | 1차 추가 양방향 스위치 S5·S6 — Infineon "novel variation"의 핵심으로 보이나 역할·소자·구동 미확보. V3000에 필요한지 판단 불가 | 중 | 앱노트 원문 §회로 설명 확인. Keyhani·Toliyat 원형(풀브리지만)과 비교 |
| **OI-3000-12** *(신규)* | BDS 단일 공급 리스크 — Infineon GIT vs Renesas/Transphorm 4상한 스위치는 게이트 구조·드라이브가 다름 | 중 | 게이트 드라이브를 소자별 서브모듈로 분리. TP65B110HRU 평가킷으로 2차 후보 검증 |

---

## 7. 미확보 · 상충 항목

**미확보**
- L_r · C_r · 권선비 n · 스위칭 주파수(수치) · C_in · 출력 필터 값 — 앱노트 원문 필요
- Enphase 실제 1차 FET · 드라이버 · BDS 품번 · BDS 수량(2/4) — IQ9 분해기 없음
- Infineon 1차 S5·S6 역할과 소자 · OPA2350 용도 · 센싱 체인
- PLC 결합 회로 · 계통측 센싱 방식 · 보호(퓨즈·MOV·릴레이) 상세
- 특허 청구항 원문
- GIT 게이트 정상 전류·게이트 RC 권장값 (데이터시트 원문)

**해소됨 (0.2)**
- ~~효율 97.5 % vs 97.95 %~~ → CEC 97.5 / 미국 피크 97.8 / 유럽 피크 97.95
- ~~Kestrel 공정 22 nm vs 55 nm~~ → 22 nm (복수 보도 일치)
- ~~BDS 수량·2차 권선 구조 (추정)~~ → 레퍼런스는 2석 하프브리지 + C1·C2 (센터탭 불필요). Enphase 실물은 여전히 추정
- ~~변조 방식~~ → 위상이동 전력 변조 + 반파 시퀀스 (수치 파라미터는 미확보)

---

## 8. 다음 단계

1. **원문 PDF 확보 — 사용자 업로드 필요.** 이번 세션에서 아래 경로를 모두 시도했고 전부 프록시 403으로 차단됨:
   infineon.com(www·no-www·documentation·dgdl) · components101 · alldatasheet · datasheet4u · docs.rs-online · mouser ·
   we-online · techinsights · how2power · ti.com · e2e.ti.com · patents.google · USPTO(image-ppubs) · justia ·
   pv-magazine · enphase(newsroom·investor) · semiconductor-today · web.archive.org.
   필요 파일:
   - `infineon-650vg5-coolgan-bidirectional-switch-cycloconverter-based-solar-microinverter-applicationnotes-en.pdf` (2025-09)
   - `infineon-iglt65r055b2-pds-datasheet-en.pdf` (Rev 1.0 · 2025-05-09) · IGLT65R110B2 데이터시트 (2025-10-02)
   - TI TIDUFD2 (TIDA-010954 Design Guide) · TI SLVAG14 백서
   - Enphase GaN 백서(2026-05) · Kestrel 백서(2026-07)
2. **특허 청구항 검토** (OI-3000-02) — US 9,479,082 · 8,797,767 · 9,379,627 · 9,130,570 청구항 1 원문. 결과에 따라 토폴로지 확정 또는 회피 설계.
3. **2차 구조 결정** (OI-3000-05) — 하프브리지 vs 풀브리지. 앱노트 회로도 + PSIM 전압 스트레스 비교.
4. **제어기 선정** (OI-3000-01) — 레퍼런스 센싱 체인 확인 후 G474 가부 판단.
5. PSIM 시뮬레이션 — 공진 탱크·BDS 극성 선택·ZVS 범위·BDS 전압 스트레스.
6. V3000 설계 사양서 초안 (V2000 사양서 §1~§17 구조 승계).

---

## 9. 참고 문서

| 문서 | 위치 |
|---|---|
| IQ9 사이클로컨버터 PSIM 회로도 (0.1 기준 — 4석 풀브리지 가정) | https://claude.ai/artifact/Tp5yC5MiwaLUNgBM8XXqLj · `docs/enphase-iq9-cycloconverter-psim.html` |
| IQ7+ 해부 (이전 세대 비교 기준) | https://claude.ai/artifact/77qGmCTw2WCC5FF1YE3QrE · `docs/enphase-iq7-teardown-analysis.html` |
| 언폴더 구동·보호 (S2G1812 · 삭제 대상 구조의 기록) | https://claude.ai/artifact/JEqWgP4bLD7E5vpv9daenF · `docs/s2g1812-unfolder-drive-protection.html` |
| V2000 설계 사양서 (승계 요구) | `docs/V2000-design-spec.md` — 이 저장소에 아직 없음 |
| V2000 MCU 이식 검토 (제어기 제약 근거) | `docs/V2000-MCU-migration-STM32G474.md` — 이 저장소에 아직 없음 |

### 출처

**0.1** — Enphase GaN BDS 백서 보도 · Kestrel ASIC 백서 보도 · pv magazine 인터뷰(2026-06) · Infineon–Enphase 보도(2025-11) ·
Infineon REF_500W_CYCLO_BDSGAN · Infineon 앱노트(사이클로컨버터 마이크로인버터) · IGLT65R055B2 · ISC056N08NM6 ·
2EDR7259X · 1EDN8550B · IQ9N 데이터시트 · US 8,797,767 B2.

**0.2 추가** —
- Infineon 앱노트 본문 스니펫 (S1~S10 시퀀스 · C1·C2 · 16~60 V / 240 V 2.1 A · 효율 측정 조건): https://www.infineon.com/assets/row/public/documents/24/42/infineon-650vg5-coolgan-bidirectional-switch-cycloconverter-based-solar-microinverter-applicationnotes-en.pdf
- Infineon 레퍼런스 보드 페이지: https://www.infineon.com/evaluation-board/REF-500W-CYCLO-BDSGAN
- Würth 레퍼런스 검색 (1EDN8550B ↔ REF_500W_CYCLO_BDSGAN): https://www.we-online.com/en/components/icref/infineon-technologies/1EDN8550B-REF-500W-CYCLO-BDSGAN-Inverter
- TI E2E (OPA2350 in REF_500W_CYCLO_BDSGAN): https://e2e.ti.com/support/amplifiers-group/amplifiers/f/amplifiers-forum/1683443/
- Infineon 커뮤니티 — BDS 340 V(AC) / 650 V 5 ms: https://community.infineon.com/t5/GaN/CoolGaN-BDS-650-V-G5-maximum-Source-to-Source-Blocking-Voltage/td-p/1161082
- IGLT65R055B2 데이터시트 (Rev 1.0 2025-05-09): https://www.infineon.com/assets/row/public/documents/24/49/infineon-iglt65r055b2-pds-datasheet-en.pdf · PQR: https://www.infineon.com/assets/row/public/documents/24/316/infineon-iglt65r055b2-productqualificationreport-en.pdf
- IGLT65R110B2 데이터시트 (2025-10-02): https://www.infineon.com/assets/row/public/documents/24/49/infineon-iglt65r110b2-datasheet-en.pdf
- TI TIDA-010954: https://www.ti.com/tool/TIDA-010954 · Design Guide: https://www.ti.com/lit/pdf/tidufd2 · 백서 SLVAG14: https://www.ti.com/lit/wp/slvag14/slvag14.pdf
- Keyhani·Toliyat, IEEE TPEL 2012: https://ieeexplore.ieee.org/document/6353248/
- Enphase GaN 백서 보도 (2026-05-21): https://www.globenewswire.com/news-release/2026/05/21/3299248/20176/en/Enphase-Energy-Publishes-Technical-White-Paper-on-GaN-Technology-for-Next-Generation-Distributed-Power-Electronics.html
- Enphase Kestrel 백서 보도 (2026-07-27): https://www.globenewswire.com/news-release/2026/07/27/3333463/20176/en/enphase-energy-publishes-white-paper-on-kestrel-asic-its-fifth-generation-silicon-platform-for-intelligent-power-conversion.html
- Enphase IQ9N 미국 주거용 출시 (2026-06-23 · 97.8 % 피크 · 16 A · 1.1 kg): https://newsroom.enphase.com/news-releases/news-release-details/enphase-energy-launches-iq9n-microinverters-gan-technology-us
- Enphase IQ9N 유럽 출시 (97.95 % 피크): https://investor.enphase.com/news-releases/news-release-details/enphase-energy-launches-iq9n-microinverters-gan-technology
- IQ9N 데이터시트 (주거용 · 상용): https://enphase.com/download/iq9n-microinverters-data-sheet · https://enphase.com/download/iq9n-commercial-microinverter-data-sheet
- Power Electronics News, APEC 2026 "Year Zero" of BDS: https://www.powerelectronicsnews.com/apec-2026-year-zero-of-practical-commercially-available-bds/
- Renesas TP65B110HRU 보도 (2026-03-23): https://www.renesas.com/en/about/newsroom/renesas-unveils-first-bidirectional-650v-class-gan-switch-solar-power-inverters-ai-data-centers-and
- 특허: US 9,479,082 https://patents.google.com/patent/US9479082 · US 8,797,767 https://patents.google.com/patent/US8797767B2/en · US 9,379,627 https://patents.google.com/patent/US9379627 · US 9,130,570 https://patents.google.com/patent/US9130570B2/en · US 2015/0078053 https://patents.google.com/patent/US20150078053A1/en

모든 원문은 세션 네트워크 정책으로 접근이 차단되어 검색 스니펫으로만 확인했습니다.
