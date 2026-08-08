# PSC3P8-CM100 코어 모듈 — 하드웨어 설계 사양서

Infineon **PSOC™ Control C3 Performance Line (PSC3P8)** 을 탑재한 **2.54 mm 핀헤더 인출형 보급형 코어 모듈**의 설계 사양서입니다.

싱크웍스([tms320f28x.co.kr](https://www.tms320f28x.co.kr/))가 판매하는 `TMS320F28P650DK9 모듈`(goodsNo=200903200)과 같은 **"MCU 코어 모듈 + 전 포트 2.54 mm 핀헤더 인출"** 제품 형태를 목표로 합니다.

| 항목 | 값 |
|---|---|
| 모델명 | PSC3P8-CM100 |
| 리비전 | Rev 0.1 (설계 착수 단계) |
| MCU | Infineon PSC3P8 (PSOC™ Control C3 Performance Line, Power Conversion) |
| 인출 커넥터 | 2 × (2×25) 2.54 mm 핀헤더, 총 100 핀 |
| 인출 I/O | GPIO 60 전핀 + 전원/GND/디버그/아날로그 기준 |
| 기판 | 70 × 50 mm, 4층, FR-4 1.6 mm |
| 입력 전원 | +5 V 단일 입력 (온보드 3.3 V 생성) |
| 디버그 | Cortex Debug 10핀 (1.27 mm) + 헤더 인출 SWD |

## 문서 구성

| 문서 | 내용 |
|---|---|
| [01-product-spec.md](01-product-spec.md) | 제품 정의, 대상 MCU 사양, 모듈 전기적 사양 |
| [02-block-design.md](02-block-design.md) | 블록도, 전원 트리, 회로 블록별 설계 상세 |
| [03-connector-pinout.md](03-connector-pinout.md) | J1/J2 100핀 인출표, 권장 기능 배치 |
| [04-bom.md](04-bom.md) | 부품표(BOM) |
| [05-mechanical-layout.md](05-mechanical-layout.md) | 기구 치수, 층 구성, 레이아웃 규칙 |
| [06-design-checklist.md](06-design-checklist.md) | 설계 검토 체크리스트 및 브링업 절차 |
| [07-open-items.md](07-open-items.md) | **데이터시트 대조로 확정해야 하는 미확정 항목** |

## 이 문서를 읽기 전 반드시 알아야 할 것

이 사양서는 **검색으로 확인 가능한 PSC3P8 제품 정보와 코어 모듈 설계 관례**를 근거로 작성했습니다.
작성 환경의 네트워크 정책상 `infineon.com`, `documentation.infineon.com`, `digikey.com`,
`tms320f28x.co.kr` 접속이 차단되어 **PSC3P8 데이터시트 원문(패키지 핀아웃, 전기적 특성)과
참조 제품의 상세 사양 페이지를 직접 확인하지 못했습니다.**

따라서:

- **커넥터 인출 구조·전원 트리·기구 치수는 확정 설계**로 사용할 수 있습니다.
- **MCU 실제 핀 번호(포트/핀 이름) 매핑, VCCD 커패시터 값, 크리스털 허용 범위 등은
  미확정**이며 [07-open-items.md](07-open-items.md)에 전부 목록화했습니다.
  회로도 입력 전에 이 목록을 먼저 닫아야 합니다.

## 참고 자료

- [PSOC™ Control C3 Arm® Cortex®-M33 — Infineon](https://www.infineon.com/products/microcontroller/32-bit-psoc-arm-cortex/32-bit-psoc-control-arm-cortex-m33-mcu)
- [PSC3P8GFS3PAHQ1 제품 페이지 — Infineon](https://www.infineon.com/part/PSC3P8GFS3PAHQ1)
- [PSOC™ Control C3 문서 포털](https://documentation.infineon.com/psoccontrolc3/docs/kfc1732622054982)
- [KIT_PSC3M5_EVK 평가보드](https://www.infineon.com/evaluation-board/kit-psc3m5-evk)
- [TARGET_KIT_PSC3M5_EVK BSP — GitHub](https://github.com/Infineon/TARGET_KIT_PSC3M5_EVK)
- [TMS320F28P650DK9 모듈 (참조 제품) — 싱크웍스](https://www.tms320f28x.co.kr/goods/goods_view.php?goodsNo=200903200)
