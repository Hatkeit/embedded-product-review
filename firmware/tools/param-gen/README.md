# 엑셀 파라미터 → C 헤더 생성기

엑셀(또는 CSV) 표를 **단일 진실 원천**으로 삼아 `gen_params.h` 를 만든다.
자동차 업계가 DBC·A2L·ARXML 로 하는 것과 같은 구조를, 전용 툴 없이 쓰는 방식이다.

```
params.xlsx  ──►  gen_params.py  ──►  generated/gen_params.h  ──►  컴파일
  (원본)                                  (생성물, 수정 금지)
```

## 파일

| 파일 | 역할 |
|---|---|
| `params.xlsx` | 파라미터 표. **노란색 value 열만** 수정한다 |
| `gen_params.py` | 표 → C 헤더 변환기. 범위를 벗어나면 헤더를 만들지 않고 종료 코드 1 |
| `make_xlsx.py` | 템플릿을 처음 만들 때 쓴 스크립트. 평소에는 필요 없다 |

## 사용법

```bash
# 엑셀에서 값 수정 → 저장 → 닫기
python gen_params.py params.xlsx <프로젝트>/generated
```

`openpyxl` 이 필요하다 (`pip install openpyxl`).
설치가 어려우면 엑셀을 **CSV 로 저장**해서 같은 명령에 넘기면 된다 — CSV 경로는
표준 라이브러리만 쓴다.

## 코드에서 쓰기

```c
#include "gen_params.h"   /* 기존 #define 들을 지우고 이것으로 대체 */
```

컴파일러가 `generated/` 를 찾도록 Makefile 에 경로를 추가한다.

```make
INCLUDES+=$(CY_APP_PATH)/generated
```

## 빌드에 걸기

`Makefile` 의 `PREBUILD` 에 걸면 `make build` 마다 자동 생성된다.

```make
PREBUILD=python $(CY_APP_PATH)/tools/gen_params.py \
                $(CY_APP_PATH)/config/params.xlsx \
                $(CY_APP_PATH)/generated
```

**처음에는 걸지 말고 수동으로 먼저 돌려보라.** 빌드가 깨졌을 때 원인이
코드인지 생성기인지 갈라지지 않게 하기 위해서다.

## 표 규칙

| 열 | 설명 |
|---|---|
| `name` | C 식별자. 앞에 `#` 를 붙이면 그 행은 제외된다 |
| `value` | 값. **여기만 고친다** |
| `type` | `uint8_t` `uint16_t` `uint32_t` `int8_t` `int16_t` `int32_t` `float` `double` `bool` |
| `min` `max` | 물리 범위. 벗어나면 생성 실패 |
| `unit` `description` | 생성된 헤더의 주석으로 들어간다 |

**빈 행에서 표가 끝난 것으로 본다.** 표 아래에 메모를 적어도 무방하다.

## 형상관리 규칙

1. **생성물(`gen_params.h`)도 커밋한다** — 엑셀·파이썬 없이도 빌드되어야 한다
2. **생성물을 손으로 고치지 않는다** — 다음 생성에서 덮어써진다
3. **CI 에서 재생성 후 diff 를 검사한다** — 누군가 생성물을 고쳤으면 실패시킨다
4. **엑셀은 CSV 로도 내보내 함께 커밋한다** — `.xlsx` 는 바이너리라 git diff 가 안 보인다

생성 헤더에 타임스탬프를 넣지 않는 것도 같은 이유다. 빌드마다 diff 가 생기면
형상관리가 지저분해지고, 무엇이 실제로 바뀌었는지 알 수 없게 된다.

## 검증 동작

값이 잘못되면 헤더를 만들지 않고 멈춘다. `PREBUILD` 에 걸려 있으면 빌드가 실패한다.

```
[gen_params] params.xlsx 에 오류 2건 — 헤더를 생성하지 않았습니다.
  - USE_CANFD_NODE: 값 5 이 최대값 2 보다 큽니다.
  - CANFD_DLC: 값 9 이 최대값 8 보다 큽니다.
```

잘못된 값이 컴파일까지 가지 않는 것이 이 방식의 핵심 이득이다.
