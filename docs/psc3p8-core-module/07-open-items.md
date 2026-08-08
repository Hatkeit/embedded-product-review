# 07. 미확정 항목 (Open Items)

이 사양서는 작성 환경의 네트워크 정책 때문에 아래 도메인에 접속하지 못한 상태에서 작성되었다.

| 도메인 | 결과 |
|---|---|
| `www.infineon.com` | 차단 (EGRESS_BLOCKED) |
| `documentation.infineon.com` | 차단 |
| `www.digikey.com` | 차단 |
| `www.tms320f28x.co.kr` (참조 제품) | 차단 |
| `docs.zephyrproject.org` | 차단 |
| `raw.githubusercontent.com` | **접속 가능** — KIT_PSC3M5_EVK BSP 만 원문 확인 |

따라서 아래 항목은 **검색 결과 요약에 의존하거나 미확정 상태**이며,
회로도 입력 전에 데이터시트 원문으로 닫아야 한다.

## P0 — 블로커 (닫히기 전 회로도 입력 불가)

| # | 항목 | 현재 상태 | 확인처 |
|---:|---|---|---|
| 1 | **PSC3P8 패키지와 핀아웃 전체** | "최대 100핀 옵션 존재" 만 확인. LQFP-100 여부·핀 배열 미확인 | PSC3P8 데이터시트 Pinout 장 |
| 2 | **60 GPIO 의 포트/핀 이름 (`P0_0` 형식)** | 미확인. [03](03-connector-pinout.md) 의 `MCU 핀` 컬럼이 전부 비어 있음 | 데이터시트 Pinout / ModusToolbox Device Configurator |
| 3 | **ADC 24 입력 라인 ↔ 물리 핀 매핑** | 미확인. `A00`~`A23` 배정의 근거 | 데이터시트 ADC 장 |
| 4 | **HRPWM 출력 ↔ 물리 핀 매핑, 상보 쌍 구성** | 미확인 | 데이터시트 / TRM |
| 5 | **`VCCD` 커패시터 값·종류·ESR 조건** | 미확인. BOM C15 가 미정 | 데이터시트 전원 장 |
| 6 | **전원 핀 종류와 개수** (VDDD/VDDIO/VDDA/VSSA/VCCD/VBACKUP) | 미확인. 디커플링 개수가 이에 종속 | 데이터시트 Pinout |
| 7 | **ECO(외부 크리스털) 허용 주파수 범위 및 부하 조건** | X1 = 16 MHz 는 가정치 | 데이터시트 클럭 장 |

## P1 — 설계에 영향 (레이아웃 확정 전 필요)

| # | 항목 | 현재 상태 |
|---:|---|---|
| 8 | 최대 CPU 동작 주파수 | Main Line 180 MHz / C3M5 EVK BSP 최대 240 MHz. **Performance Line 값 미확인** |
| 9 | I/O 의 5 V 톨러런트 여부 | 미확인. 현재 "톨러런트 아님" 으로 보수적 가정 |
| 10 | 전원 인가 순서(power sequencing) 제약 | 미확인 |
| 11 | XRES 전기적 특성 (내부 풀업 유무, 최소 펄스 폭) | 미확인 |
| 12 | SWD 핀의 GPIO 겸용 가능 여부 / 디버그 포트 보안 정책 | 미확인. [01 §1.4](01-product-spec.md) 의 "회수 가능" 표기가 이에 종속 |
| 13 | 소비 전류 실측치 (Active / Sleep / DeepSleep) | 미확인. LDO 500 mA 등급은 여유 있는 가정 |
| 14 | WCO(32.768 kHz) 지원 핀 | `P29`/`P30` 배정은 가정치 |
| 15 | 내장 비교기 채널 수와 핀 매핑 | 미확인. `A22`/`A23` 권장 배치가 이에 종속 |
| 16 | USB 탑재 여부 | 미확인. 현재 사양서에서 USB 미고려 |

## P2 — 사업/조달

| # | 항목 | 현재 상태 |
|---:|---|---|
| 17 | PSC3P8 정식 양산 OPN 과 리드타임 | Performance Line: 2025년 말 샘플 / 2026년 양산 (검색 기준). 대리점 확인 필요 |
| 18 | `PSC3P8GFS3PAHQ1` 의 `Q1` 접미사 = AEC-Q100 여부 | 미확인. 산업용/차량용 등급 구분 필요 |
| 19 | ModusToolbox™ 의 PSC3P8 지원 여부 및 BSP 생성 가능성 | 미확인 (KIT_PSC3M5_EVK 용 BSP 만 확인됨) |
| 20 | Zephyr / 기타 RTOS 의 PSC3 Performance Line 지원 | 미확인 |
| 21 | 참조 제품(TMS320F28P650DK9 모듈)의 실제 치수·헤더 배열·가격 | **미확인** — 판매 페이지 차단. 본 사양서의 70×50 mm / 2×25 헤더는 참조 제품을 복제한 것이 아니라 독립적으로 산출한 값 |

## 확정 작업 순서 (권장)

1. Infineon 계정 또는 대리점으로 **PSC3P8 데이터시트 + TRM** 확보 → P0 #1, #5, #6, #7 해결
2. ModusToolbox™ 설치 후 PSC3P8 프로젝트 생성 → **Device Configurator 로 핀 목록 추출** → P0 #2, #3, #4 해결
3. 추출한 핀 목록을 [03-connector-pinout.md §3.5](03-connector-pinout.md) 규칙에 따라 `MCU 핀` 컬럼에 채움
4. 채워진 결과로 [06-design-checklist.md](06-design-checklist.md) Gate 1 재실행
5. 대리점 견적으로 P2 #17, #18 확정 → 원가·판가 결정
6. 그 후에 회로도 입력 착수

> **P0 를 닫지 않은 상태에서 PCB 를 발주하지 말 것.**
> 항목 #1~#4 는 커넥터 인출표 전체를 무효화할 수 있는 종류의 미확정 사항이다.
