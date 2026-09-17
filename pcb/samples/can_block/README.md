# CAN 인터페이스 블록 — 배치도/배선도 형식 샘플

**예시 부품으로 그린 형식 샘플입니다. 실제 회로도(OrCAD)를 받으면 실제 부품·핀·넷 이름으로 다시 작성합니다.**

| 파일 | 내용 |
|---|---|
| `can_block_placement.svg` / `.png` | 패키지 심볼 외형(패드·핀 번호·1번 핀 표시) 기준 배치도, 치수·배치 규칙 주석 |
| `can_block_routing.svg` / `.png` | 실제 배선폭을 축척으로 표시한 배선도, GND shape(동박 채움)·비아·클리어런스, 배선 규칙 |
| `gen_can_block_sample.py` | 위 두 SVG를 생성하는 스크립트 (`python3 gen_can_block_sample.py`) |

- 단위 mm, Top view(부품면), 1 mm 격자.
- 부품/값/핀 배열: TJA1051T/3 계열 SOIC-8 트랜시버, 100 nF 디커플링, ACT45B 계열 CMC, 분할 종단(60.4 Ω×2 + 4.7 nF), PESD1CAN 계열 TVS, 3핀 커넥터 — 모두 예시.
- 배선폭/간격/비아 값은 샘플값. 실제 층 구성과 제조사 임피던스 계산값으로 확정.
