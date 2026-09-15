#!/usr/bin/env python3
"""엑셀(또는 CSV) 파라미터 표를 C 헤더로 변환한다.

사용법:
    python gen_params.py <params.xlsx | params.csv> <출력 디렉터리>

엑셀은 openpyxl 이 필요하다 (pip install openpyxl).
CSV 는 표준 라이브러리만으로 동작하므로 파이썬 환경이 제한적일 때 대안이 된다.

표는 다음 열을 가져야 한다 (순서는 자유, 헤더 이름으로 찾는다):
    name  value  type  min  max  unit  description

값이 min~max 를 벗어나면 헤더를 만들지 않고 종료 코드 1 로 끝난다.
빌드 전(PREBUILD)에 걸어 두면 잘못된 값이 컴파일까지 가지 않는다.
"""

import csv
import re
import sys
from pathlib import Path

HEADERS = ["name", "value", "type", "min", "max", "unit", "description"]

UNSIGNED = {"uint8_t", "uint16_t", "uint32_t", "uint64_t"}
SIGNED = {"int8_t", "int16_t", "int32_t", "int64_t"}
ALLOWED = UNSIGNED | SIGNED | {"float", "double", "bool"}

IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

TYPE_RANGE = {
    "uint8_t":  (0, 255),
    "uint16_t": (0, 65535),
    "uint32_t": (0, 4294967295),
    "int8_t":   (-128, 127),
    "int16_t":  (-32768, 32767),
    "int32_t":  (-2147483648, 2147483647),
}


def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return [dict(r) for r in csv.DictReader(f)]


def read_xlsx(path):
    try:
        import openpyxl
    except ImportError:
        sys.exit("[gen_params] openpyxl 이 없습니다. 'pip install openpyxl' 또는 CSV 를 쓰세요.")

    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb["params"] if "params" in wb.sheetnames else wb[wb.sheetnames[0]]

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        sys.exit("[gen_params] 시트가 비어 있습니다.")

    header = None
    start = 0
    for i, row in enumerate(rows):
        cells = [str(c).strip().lower() if c is not None else "" for c in row]
        if "name" in cells and "value" in cells:
            header = cells
            start = i + 1
            break
    if header is None:
        sys.exit("[gen_params] 'name' 과 'value' 열이 있는 헤더 행을 찾지 못했습니다.")

    out = []
    for row in rows[start:]:
        rec = {}
        for key, cell in zip(header, row):
            if key in HEADERS:
                rec[key] = cell
        out.append(rec)   # 빈 행도 넘긴다 — 표의 끝을 main() 이 판단한다
    return out


def as_num(value):
    """빈 칸은 None, 그 외는 숫자로. 숫자가 아니면 예외."""
    if value is None or str(value).strip() == "":
        return None
    return float(str(value).strip())


def literal(name, value, ctype, errors):
    """C 리터럴 문자열을 만든다."""
    if ctype == "bool":
        text = str(value).strip().lower()
        if text in ("1", "true", "yes", "y"):
            return "true"
        if text in ("0", "false", "no", "n"):
            return "false"
        errors.append(f"{name}: bool 값이 '{value}' 입니다. true/false 또는 1/0 을 쓰세요.")
        return None

    try:
        num = as_num(value)
    except ValueError:
        errors.append(f"{name}: 값 '{value}' 이 숫자가 아닙니다.")
        return None
    if num is None:
        errors.append(f"{name}: 값이 비어 있습니다.")
        return None

    if ctype in ("float", "double"):
        return f"{num:g}F" if ctype == "float" else f"{num:g}"

    if num != int(num):
        errors.append(f"{name}: 정수형({ctype})인데 값이 {num} 입니다.")
        return None
    num = int(num)

    lo, hi = TYPE_RANGE[ctype]
    if not (lo <= num <= hi):
        errors.append(f"{name}: {num} 이 {ctype} 범위({lo}~{hi})를 벗어납니다.")
        return None

    return f"{num}U" if ctype in UNSIGNED else str(num)


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)

    src = Path(sys.argv[1])
    outdir = Path(sys.argv[2])

    if not src.exists():
        sys.exit(f"[gen_params] 입력 파일이 없습니다: {src}")

    rows = read_csv(src) if src.suffix.lower() == ".csv" else read_xlsx(src)

    errors = []
    seen = set()
    entries = []      # (name, literal, note) — 폭은 실제 항목이 정해진 뒤에 계산한다

    started = False
    for r in rows:
        name = str(r.get("name") or "").strip()
        if not name:
            if started:
                break          # 빈 행에서 표가 끝난다. 아래는 메모로 본다.
            continue
        started = True
        if name.startswith("#"):
            continue           # 주석 처리된 행
        if not IDENT.match(name):
            errors.append(f"{name}: C 식별자로 쓸 수 없는 이름입니다.")
            continue
        if name in seen:
            errors.append(f"{name}: 이름이 중복됩니다.")
            continue
        seen.add(name)

        ctype = str(r.get("type", "")).strip()
        if ctype not in ALLOWED:
            errors.append(f"{name}: type '{ctype}' 을 지원하지 않습니다. {sorted(ALLOWED)}")
            continue

        # 사용자가 지정한 물리 범위 검사 (타입 범위와 별개)
        try:
            lo, hi, val = as_num(r.get("min")), as_num(r.get("max")), as_num(r.get("value"))
            if None not in (lo, val) and val < lo:
                errors.append(f"{name}: 값 {val:g} 이 최소값 {lo:g} 보다 작습니다.")
            if None not in (hi, val) and val > hi:
                errors.append(f"{name}: 값 {val:g} 이 최대값 {hi:g} 보다 큽니다.")
        except ValueError:
            pass  # 아래 literal() 이 숫자 오류를 보고한다

        lit = literal(name, r.get("value"), ctype, errors)
        if lit is None:
            continue

        unit = str(r.get("unit") or "").strip()
        desc = str(r.get("description") or "").strip()
        entries.append((name, lit, " · ".join(x for x in (ctype, unit, desc) if x)))

    if errors:
        print(f"[gen_params] {src.name} 에 오류 {len(errors)}건 — 헤더를 생성하지 않았습니다.",
              file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)

    width = max([len(n) for n, _, _ in entries] + [24])
    defines = [
        f"#define {n:<{width}} ({lit})" + (f"   /* {note} */" if note else "")
        for n, lit, note in entries
    ]

    guard = "GEN_PARAMS_H"
    lines = [
        "/*",
        " * 자동 생성 파일 — 직접 수정하지 마십시오.",
        f" * 원본: {src.name}",
        " * 생성기: firmware/tools/param-gen/gen_params.py",
        " *",
        " * 값을 바꾸려면 원본 표를 고치고 다시 생성하십시오.",
        " * 이 파일을 고치면 다음 빌드에서 그대로 덮어써집니다.",
        " */",
        f"#ifndef {guard}",
        f"#define {guard}",
        "",
        "#include <stdint.h>",
        "#include <stdbool.h>",
        "",
    ]
    lines += defines
    lines += ["", f"#endif /* {guard} */", ""]

    outdir.mkdir(parents=True, exist_ok=True)
    dest = outdir / "gen_params.h"
    text = "\n".join(lines)

    # 내용이 같으면 쓰지 않는다 — 불필요한 재빌드를 막는다
    if dest.exists() and dest.read_text(encoding="utf-8") == text:
        print(f"[gen_params] 변경 없음: {dest}")
        return

    dest.write_text(text, encoding="utf-8")
    print(f"[gen_params] {len(defines)}개 파라미터 → {dest}")


if __name__ == "__main__":
    main()
