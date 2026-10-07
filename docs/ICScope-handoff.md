# ICScope 작업 인계서 (2026-10-07)

다른 환경에서 이어서 작업하기 위한 정리입니다. 저장소 `hatkeit/embedded-product-review`, 브랜치 `claude/sharp-cerf-1rmlfa`.
코드는 `tools/icscope/` (Go 1.22+, 표준 라이브러리만 사용, 외부 의존성 없음).

---

## 1. 요청 이력

| # | 요청 | 상태 |
|---|---|---|
| 1 | "Opamp 나 inverter pdf를 import 기능을 갖는 exe 실행파일 만들 수 있나요?" → 기능: **데이터시트 사양 추출 + 회로도에서 Op-amp/인버터 찾아 IC 대체 제안 (둘 다)**, UI: **exe가 띄우는 브라우저 창** | **완료** — v0.9, 커밋 `6fd0431`, `tools/icscope/dist/ICScope.exe` |
| 2 | "V2000 회로도 기반으로 만들어주세요. 심볼을 클릭하면 제조사 PDF를 import 해서 회로도 기반으로 시뮬레이션이 가능하게. PSpice처럼 원하는 포인트를 지정하면 그래프로 파형, **결과창은 분리**해서 볼 수 있게" | **진행 중** — 엔진·모델·회로도 형상 추출 완료, 서버 API·UI·결과창 남음 (아래 4, 6절) |

---

## 2. 완료된 것 — ICScope v0.9 (커밋 6fd0431)

실행: `ICScope.exe` 더블클릭 → 127.0.0.1:17321 로컬 서버 + 기본 브라우저. 인터넷 미사용. 콘솔 창 닫기 또는 [종료] 버튼으로 끝.

| 입력 | 처리 |
|---|---|
| 데이터시트 PDF | 표(MIN/TYP/MAX/UNIT)에서 핵심 사양 + 페이지·표 이름, 핀 표, 패키지, 분류. 사양 비교 탭, CSV |
| OrCAD `pstxnet.dat` (+`pstxprt.dat`, `pstchip.dat`) | 정확한 넷리스트 → 회로 분석 |
| OrCAD 기본 색상 회로도 PDF | 선 색상으로 넷리스트 복원(추정) → 회로 분석, "회로도 보기"(해당 부품 확대 SVG) |
| 기타 회로도 PDF | 부품 목록만 |

회로 분석: Op-amp·비교기·인버터 섹션별 팔로워/반전/비반전/차동/비교기/미사용 판정, 이득·극·분압·히스테리시스 계산, 대체 제안(전류감지 앰프, 분압 직결, MCU 내장 OPAMP/COMP, 극성 설정), 이중 드라이버·`NC` 넷 병합 경고, STM32G474 핀의 ADC/COMP/OPAMP 기능 표시.

검증: V2001 넷리스트 결과가 수작업 검토서 `docs/V2001-opamp-to-ic.md`와 일치(U2 이득 51.1/75, R101 2 mΩ → 0.102 V/A, INA240 이중 구동, U12 히스테리시스 0.30 V, U4B·U11B 미사용, NC 150핀). V2000 PDF 복원: 2단자 수동소자 513개 중 481개 정확히 2핀.

---

## 3. 코드 구조 (`tools/icscope/`)

| 경로 | 내용 | 상태 |
|---|---|---|
| `internal/pdf` | PDF 파서(xref·객체스트림·필터·암호화), 폰트(Type0/1/TrueType/Type3), 콘텐츠 해석기. `Glyph.Adv`(진행폭) 추가됨 | 완료 |
| `internal/datasheet` | 표 추출, 핵심 사양(`specDefs`), 핀 표. 이번에 `vtp, vtn, vf, vbr, vgsth, rdson, ctr, vcmout` 키와 `Datasheet.Text`(첫 페이지 본문, JSON 제외) 추가 | 완료(미커밋분 포함) |
| `internal/orcad` | PST 3종 읽기 | 완료 |
| `internal/netlist` | 공통 모델(Part/Pin/Net), 값 파서 `ParseValue`, `SI` | 완료 |
| `internal/analysis` | 분류(`ClassOf`), 게이트 배정, 회로 판정·제안. `GatesOf`, `PinRole`, `RailVolts` 공개 | 완료 |
| `internal/schematic` | OrCAD PDF → 넷리스트(`FromPDF(doc)`), 참조번호 위치, 페이지 SVG, **페이지 형상 `Doc.Geo[page]`(신규)** | 형상 추출 완료(미커밋분) |
| `internal/sim` | **신규** SPICE형 시뮬레이터 | 완료, 테스트 통과(미커밋분) |
| `internal/model` | **신규** 부품 → 시뮬레이션 모델, 핀 역할, 데이터시트 매핑, 회로 생성 | 작성 완료, **통합 테스트 전**(미커밋분) |
| `cmd/icscope` | 로컬 웹서버 + `web/index.html`(내장) | v0.9. 시뮬레이션 API·UI **미작성** |
| `cmd/pdfdump`, `cmd/nlcheck` | 개발용 점검 도구 (`pdfdump <pdf> <page> stexts|scomps|svg|json|lines`, `pdfdump <pdf> ds`, `SCH=<파일명> [DUMP=1] nlcheck <pdf>` 또는 `nlcheck pstxnet.dat pstxprt.dat pstchip.dat [datasheet.pdf…]`) | |

빌드·테스트:
```
cd tools/icscope
go test ./...
GOOS=windows GOARCH=amd64 CGO_ENABLED=0 go build -trimpath -ldflags "-s -w" -o dist/ICScope.exe ./cmd/icscope
```

---

## 4. 이번 세션에 만든 것 (요청 2, 미완)

### 4-1. `internal/sim` — 시뮬레이터 엔진 (완료)

- MNA + Newton-Raphson, 밀집 LU(0 원소 건너뜀), 해석: **OP**(gmin·소스 스테핑), **과도해석**(사다리꼴, 브레이크포인트 직후 후진 오일러, 가변 스텝, 최대 간격), **DC 스윕**, **AC**(동작점 선형화, dB/위상).
- 소자: R, C, L/결합 인덕터(변압기, 인덕턴스 행렬), V/I 소스(DC·SIN·PULSE·PWL), 다이오드(pnjlim 리미팅, 항복), BJT(Ebers-Moll), MOSFET(레벨1 + 부드러운 문턱), **Amp**(행동 증폭기: Op-amp/비교기/전류감지/절연/기준전압 공용 — 단극·슬루제한·레일 소프트클램프·오픈드레인·히스테리시스), **Gate**(슈미트 인버터/버퍼/게이트드라이버, enable), **Opto**(LED + CTR 트랜지스터).
- 결과 `Result{Kind, X, Signals["V(net)"|"I(소자)"], Order, Notes}`. AC는 `"V(net)|db"`, `"V(net)|ph"`.
- 해결한 수치 문제: ① Op-amp 목표값 클램프가 루프이득을 죽임 → 상태 x에 softplus 클램프(반와인드업)로 이동 ② Newton이 두 포화 상태 사이를 왕복 → x를 반복당 max(0.5 V, 0.25·레일폭)로 제한 ③ 사다리꼴 링잉 → 행동 내부 상태는 항상 후진 오일러.
- 테스트(`sim_test.go`): RC 계단, RLC 링잉, 변압기 n=2, 반파정류, 반전증폭 −10·포화, RC −3 dB/−45°, 슈미트 문턱(1.98/1.32 V), MOSFET 스위치, BJT 공통이미터 — 전부 통과.

### 4-2. `internal/schematic` — 클릭용 형상 (완료)

`FromPDF` 실행 시 `Doc.Geo[page] = PageGeo{Parts[], Wires[]}`:
- `GPart{Ref(섹션 포함, 예 U2A), Base(U2), Body, Text, Lines, Pins[GPin{i(넷리스트 핀 인덱스), num, name, net, seg, inner}], Diag(몸체 사선 = 다이오드 삼각형/화살표)}`
- `GWire{seg, net, k('w' 배선 / 'b' 전원·포트 기호)}` — 넷 이름은 전역 라벨(미라벨은 `N###`/`W###`).
- 여러 섹션에 그려진 같은 전원핀(U2A/U2B 4·8번)은 같은 핀으로 합침(섹션 IC만; 커넥터 중복 번호는 합치지 않음 — 이전에 GND가 UART 넷과 합쳐지는 회귀를 고침).

### 4-3. `internal/model` — 부품 모델 (작성 완료, 통합 테스트 필요)

- 종류(`Kinds`): NONE, R, C(ESR), L, BEAD, SHORT, D(다중·양방향 TVS), NPN/PNP(다중), NMOS/PMOS(바디다이오드·Ciss/Coss/Crss), OPAMP, COMP, INV, BUF, GATEDRV, CSA, ISOAMP, VREF, OPTO(다중), XFMR(권선 ≤4, k).
- 핀 역할: `Model.Roles[넷리스트 핀 인덱스] = "IN+1"`, 한 핀에 여러 역할은 쉼표(`"K1,K2"`). `RoleOptions(m)`가 편집기 선택지 생성.
- `Auto(part, hints)` 추정 규칙:
  - 다이오드: 몸체 사선의 공통 끝점(삼각형 꼭짓점) = 캐소드 쪽 (`Hints.Apex`, `Hints.Inner`). BAV70/BAV99/BAW56 3핀 배치 내장. TVS 항복전압은 품번(SMBJ400CA → 1.11×400 V, PTVS3V3 등), `CA` = 양방향.
  - MOSFET 8핀: 핀 수로 G(1)·S(3)·D(4) / SOT-23 번호 1G 2S 3D / 번호 없으면 핀 방향(제어핀만 방향이 다름)·위=드레인.
  - BC847 6핀: SOT-363 표준(1 E1, 2 B1, 3 C2, 4 E2, 5 B2, 6 C1) — **V2000 U7/U8/U9 추출 결과가 이 배치와 맞지 않아 보임, 확인 필요**.
  - IC: `analysis.ClassOf` + 게이트드라이버(2EDN…)·기준(REF30…)·포토커플러(FOD817, ELD207 듀얼)·트라이악(MOC30 → 제외). 핀 이름 우선, 없으면 표준 핀배치.
  - MCU·커넥터·변압기(T)·배리스터 → NONE(변압기는 XFMR로 바꾸고 권선 지정하면 시뮬레이션).
- `ApplyDatasheet(ds, part)`: 단위 환산(`UnitScale`: V/µs, dB, V/mV, mΩ, kHz …) 후 파라미터 채움 + 출처 `"데이터시트 p.N 파라미터명"`. CSA 이득은 변형 행(INA240A2 → 50)에서, MOSFET RDS(on)은 변형 중 최소값(VGS 10 V), 비교기 오픈드레인은 본문 텍스트에서. 데이터시트 핀 표로 빈 핀 이름 채운 뒤 IC 핀 역할 재계산.
- `Build(nl, models, Setup{Parts, Ground, Stims})` → `Built{C, Warnings, Included, Skipped}`. 접지 = 넷 별칭 중 `Ground`(기본 GND)와 같은 것. `RailOf(net)`로 3V3·12V0 등 전원 넷 자동 DC 소스 생성(ADC/AIN 이름 제외, Auto 소스는 사용되는 넷에만).

---

## 5. 설계 결정·주의

- **저장소가 public** — V2000 회로도 PDF·넷리스트·데이터시트를 exe나 저장소에 넣지 않는다. 실행 후 사용자가 PDF를 끌어다 놓는 방식.
- 시뮬레이션 넷리스트는 **V2000 회로도 PDF에서 복원한 것**(요청이 "V2000 회로도 기반"). V2000 이름의 `pstxnet.dat`는 09-20 이후 수정본이라 09-19 PDF와 리비전이 다를 수 있음(V2001 = 09-22 13:31).
- 모델은 **데이터시트 사양 기반 행동 모델**. 제조사 SPICE(.lib) 모델 import는 미지원(필요하면 서브서킷 파서 추가 과제).
- MCU는 시뮬레이션하지 않음 → MCU 출력 넷에 PWM(PULSE) 등 신호원을 지정.
- 업로드 원본 위치(이 컨테이너 한정, 저장소에 없음): `sch_microinv_v2000.pdf`(595576e1, 09-19 13:48 최신본), `Reverse_Enginering_MPPT.pdf`, V2001 PST 3종(403fa8c6/6f3609e3/d931eae3), 데이터시트 INA240, AMC3301/3302, 2EDN7524, LM5156H, REF3030, MOC3063, IAUCN10S7L040, SCS205KNHR, PA1005. 다른 환경에서는 사용자가 다시 제공해야 함.

---

## 6. 남은 작업 (요청 2 완성까지)

### 6-1. 서버 API (`cmd/icscope/simapi.go` 신규 예정)

server 구조체에 추가: `schNL *netlist.Netlist`(회로도 PDF 넷리스트, PST 로드와 별개로 항상 유지), `models map[string]*model.Model`(Base ref별, 지연 생성), `stims []model.Stim`, `probes []Probe{Sig, Color}`, `runs`(최근 5개 결과).

| 엔드포인트 | 내용 |
|---|---|
| `GET /api/sch/geo?page=N` | `Doc.Geo[N]` + 그 페이지 부품의 모델 요약(kind, enabled) |
| `GET /api/part?ref=U2` | 넷리스트 핀(번호·이름·넷), 모델, `Kinds`, `RoleOptions` |
| `POST /api/part?ref=U2` | kind·params·roles·enabled·gates 갱신(`User=true`) |
| `POST /api/part/datasheet?ref=U2[&all=1]` | PDF 업로드 → `datasheet.Analyze` → 데이터시트 목록 추가 + `ApplyDatasheet`(all=1이면 같은 품번 전부) → 적용 로그 반환 |
| `GET/POST /api/stims`, `/api/probes` | 신호원·프로브 목록 |
| `POST /api/sim/run` | `{analysis: tran|op|ac|dc, pages[], ground, tran{stop,maxstep,start,uic}, ac{src,fstart,fstop,pts}, dc{src,from,to,step}}` → 포함 부품 = 선택 페이지에 GPart가 있는 Base ref → `model.Build` → 실행 → `{id, kind, signals, notes, warnings, included, skipped, op}` |
| `GET /api/sim/trace?id=&sig=…&n=&x0=&x1=` | 파형(구간 min/max 데시메이션) |
| `GET /api/sim/latest` | 최신 실행 id(결과창 폴링용) |

- Hints 생성: `Geo`의 GPin `inner`, 가로/세로 여부(`|y1−y2|<0.3`), `Diag` 끝점 중 사선 2개가 공유하는 점 = Apex.
- 실행은 잠금 밖에서, 시간 제한(예: 120 s) 추가 필요 — `TranOpts`에 Deadline 필드 추가 예정.

### 6-2. UI — "회로도·시뮬레이션" 탭 (`web/index.html`)

- 페이지 선택, `/api/svg` 위에 투명 오버레이 SVG: 배선(굵은 투명 선, 호버 시 같은 넷 전체 강조), 부품(몸체+참조번호 박스, 모델 없음은 빨간 점선).
- 모드 버튼: 선택 / **전압 프로브**(배선 클릭 → `V(net)`, 색 마커) / **전류 프로브**(2단자 부품 클릭 → `I(ref)`) / **신호원**(넷 클릭 → DC·SIN·PULSE(PWM)·PWL 폼).
- 오른쪽 패널: 넷 정보(연결 핀, 프로브/신호원 버튼) 또는 **부품 모델 편집기**(종류, 사용 여부, 섹션 수, 파라미터+출처, 핀 표: 번호·이름·넷·역할 드롭다운 — 호버 시 회로도 핀 위치 표시, **[제조사 PDF 가져오기]**).
- 해석 설정: 포함 시트 체크(기본 현재 시트), 기준 넷, 과도(종료 시간·최대 간격·UIC), AC(입력 소스·주파수), DC 스윕. [실행], OP 후 넷마다 전압 라벨 표시(PSpice 바이어스 표시).
- 하단에 결과창 iframe + **[새 창으로 분리]**.

### 6-3. 결과창 `web/scope.html` (분리 창)

- `window.open('/scope.html','icscope-scope','width=1100,height=700')`. 메인↔결과창: `BroadcastChannel('icscope')` `{type:'run', id}`, `{type:'probes'}` + `/api/sim/latest` 2초 폴링 백업.
- 캔버스 플롯: 플롯 여러 개(전압/전류 자동 분리, AC는 dB·위상), X축 공유, 휠 확대·드래그 이동·더블클릭 맞춤, 커서 2개(값·Δt·1/Δt·ΔV), 트레이스 추가(전체 신호 검색)·삭제·색, 화면 구간 측정(min/max/avg/RMS/p-p), CSV·PNG 저장.

### 6-4. 검증 시나리오 (V2000 PDF)

1. 07 ADC 시트: `PV_A-`에 SIN 2 mV/1 kHz → U2A 출력 `ADC_I_PA` ≈ 51.1배·위상 반전, 피드백 극 3.1 kHz(AC), INA240(U21) 출력과 비교.
2. 09 시트 U12 비교기: 입력 램프 → 출력 히스테리시스 약 0.30 V(VDDA 3.3 V 기준) 확인.
3. 게이트 드라이버(U13/U14) 입력에 PWM → OUT 파형, Q1~Q8 게이트(IAUCN10S7L040 데이터시트 Vth 1.6 V, RDS(on) 3.55 mΩ).
4. 08 시트 U6(HEF40106)·U5(HC14) 슈미트 체인.
- 이후 exe 재빌드, README·이 문서 갱신, 커밋/푸시.

---

## 7. 알려진 한계·이슈

**회로도 PDF 복원(V2000)**
- 2단자 부품 중 32개가 2핀이 아님(대부분 3핀 듀얼 다이오드는 정상; C107/C87/R127 4핀, R104 15핀, R130/R132 6핀, C108/C99/R123/R133~R137 0핀 등은 오류).
- 다이오드·트랜지스터 핀 번호가 PDF에 없음 → 심볼 모양 추정 + 사용자 확인 필요.
- 값 누락: D3/D4/D8/D9/D14/D15/D19/D20/D27, J*, L9, Q9, RV1~4, T1~T9, TH1. U11은 핀 일부만(1·2·3·4·8), U15 LM5156은 2핀만, T2/T4/T6/T8 핀 일부.
- V2000 PDF에서 `I_PV_A+`·`I_PV_B+`가 GND와 같은 넷(설계 지적 G1과 관련).
- U2B 귀환 소자(R287/C207) 핀 누락으로 "개루프"로 판정된 적 있음 → 시뮬레이션 전 모델 편집기에서 확인 필요.
- 값이 풋프린트와 붙어 읽히는 경우("51.1KFRESC1608") → `analysis.val`에서 분리 처리함.

**데이터시트 추출**
- AMC3301 PSRR 단위 누락, REF30·LM5156 전원 범위가 절대최대정격에서 옴(라벨에 "(절대최대정격)" 표시), MOC3063·2EDN7524 핀 표 미추출, 2EDN VIH/VIL은 `vt` 키로만 잡힘.

**v0.9 미검증**
- Windows 실기 실행 미확인(교차 컴파일만). Linux 빌드로 Playwright 화면 검증 완료.

---

## 8. 설계 검토에서 넘어온 미조치 항목 (참고)

NC 넷 150핀 병합(최우선), R219/R228 20 mΩ, U24 AMC3302DWR→DWER, RV1/RV3 교체, C58 표기, C100 풋프린트, TH1 DOA-214AA, L11 4532, MLCC 정격전압, R6/R101 결정, PV_B−, N13 이중 드라이버, U2 이득 비대칭, LM5156 FB/SS, G1/G2. 상세는 `docs/V2001-*.md`, `docs/V2000-*.md`.
