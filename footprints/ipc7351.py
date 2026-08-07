#!/usr/bin/env python3
"""
IPC-7351B 랜드 패턴 계산기

packages.csv 의 부품 치수를 읽어 패드 형상 / courtyard / IPC 심볼명을 산출한다.

    python3 ipc7351.py                 # 하우스 기본값(Level A) 로 계산
    python3 ipc7351.py --level B       # 등급 비교
    python3 ipc7351.py --level A B C   # 세 등급 동시 비교
    python3 ipc7351.py --csv out.csv   # 결과를 CSV 로 저장

적용 범위:
    datasheet 에 권장 랜드 패턴이 **없는** 부품에만 쓴다.
    권장 패턴이 있는 부품(IC / 커넥터 / 크리스탈 / 전력 패키지)은
    그 패턴을 그대로 쓰고 이 계산기를 거치지 않는다. README.md 참조.
"""

import argparse
import csv
import math
import sys
from pathlib import Path

# ============================================================================
# 검증이 필요한 상수 — 사용 전 IPC-7351B 원문 표와 대조할 것
# ----------------------------------------------------------------------------
# 아래 필렛 목표값(JT/JH/JS), 제조 여유(F), 배치 정확도(P), courtyard 여유(CE)
# 는 IPC-7351B 의 패키지 패밀리별 표에서 가져와야 한다.
# 여기 채워진 값은 계산 구조 확인용 잠정값이며, 라이브러리를 확정하기 전에
# 반드시 원문 또는 검증된 구현(PCB Libraries LP Wizard 등)과 1행 이상
# 대조해야 한다. 이 값이 틀리면 오차가 라이브러리 전체에 전파된다.
#
# 구조(공식)는 IPC-7351B 그대로이므로, 아래 숫자만 교체하면 전체가 확정된다.
# ============================================================================

VERIFY_REQUIRED = True  # 상수 대조를 마쳤으면 False 로 바꾼다

# 필렛 목표값 [mm]: family -> level -> (JT toe, JH heel, JS side)
FILLET_GOALS = {
    # chip 단자는 바디 밑으로 감싸 들어가므로 힐 필렛이 물리적으로 생기지 않는다.
    # -> JH = 0. (JH 를 걸윙처럼 0.35 로 두면 소형 사이즈에서 패드 간격이
    #    음수가 되어 validate() 에서 걸린다. 진단 근거로 남겨 둔다.)
    "CHIP": {
        "A": (0.35, 0.00, 0.05),   # VERIFY
        "B": (0.15, 0.00, 0.00),   # VERIFY
        "C": (0.00, 0.00, -0.05),  # VERIFY
    },
    "GULLWING": {
        "A": (0.55, 0.45, 0.05),   # VERIFY
        "B": (0.35, 0.35, 0.03),   # VERIFY
        "C": (0.15, 0.25, 0.01),   # VERIFY
    },
    # 리드가 바디 밑으로 들어가는 무리드 패키지(SOD-123 등)는 toe 여유가 작다
    "FLATLEAD": {
        "A": (0.40, 0.00, 0.05),   # VERIFY
        "B": (0.30, 0.00, 0.00),   # VERIFY
        "C": (0.20, 0.00, -0.05),  # VERIFY
    },
}

F_FABRICATION = 0.05   # 기판 제조 공차 여유 [mm]  VERIFY
P_PLACEMENT = 0.025    # 실장기 배치 정확도 [mm]   VERIFY

# courtyard 여유 [mm]: level -> CE
COURTYARD_EXCESS = {"A": 0.50, "B": 0.25, "C": 0.10}  # VERIFY

# 밀도 등급 -> IPC 심볼명 접미사 (Most / Nominal / Least)
DENSITY_SUFFIX = {"A": "M", "B": "N", "C": "L"}


def rss(*terms):
    """제곱합의 제곱근. 독립 공차의 통계 합성."""
    return math.sqrt(sum(t * t for t in terms))


def compute(part, level):
    """부품 치수 + 밀도 등급 -> 패드 형상.

    IPC-7351B 공식:
        Zmax = Lmin + 2*JT + rss(CL, F, P)     패드 바깥 끝 ~ 끝
        Gmin = Smax - 2*JH - rss(CS, F, P)     패드 안쪽 끝 ~ 끝 (간격)
        Xmax = Wmin + 2*JS + rss(CW, F, P)     패드 폭
    """
    family = part["family"]
    try:
        jt, jh, js = FILLET_GOALS[family][level]
    except KeyError:
        raise ValueError(f"{part['ref']}: 알 수 없는 family/level: {family}/{level}")

    l_min, l_max = part["L_min"], part["L_max"]
    w_min, w_max = part["W_min"], part["W_max"]
    t_min, t_max = part["T_min"], part["T_max"]

    # 힐-힐 간격 S 는 리드 span L 과 리드 길이 T 에서 유도된다.
    # T 공차가 넓은 부품(SOIC, chip 수동)은 여기서 CS 가 커져 패드가 길어진다.
    s_max = l_max - 2 * t_min
    s_min = l_min - 2 * t_max

    cl = l_max - l_min          # 리드 span 공차 폭
    cs = s_max - s_min          # 힐 간격 공차 폭
    cw = w_max - w_min          # 리드 폭 공차 폭

    z_max = l_min + 2 * jt + rss(cl, F_FABRICATION, P_PLACEMENT)
    g_min = s_max - 2 * jh - rss(cs, F_FABRICATION, P_PLACEMENT)
    x_max = w_min + 2 * js + rss(cw, F_FABRICATION, P_PLACEMENT)

    pad_y = (z_max - g_min) / 2          # 패드 길이 (부품 축 방향)
    pad_x = x_max                        # 패드 폭
    center = (z_max + g_min) / 4         # 원점에서 패드 중심까지

    ce = COURTYARD_EXCESS[level]
    body_w = max(part["body_W_max"], x_max)
    courtyard_y = z_max + 2 * ce
    courtyard_x = body_w + 2 * ce

    return {
        "ref": part["ref"],
        "name": symbol_name(part, level),
        "pad_x": pad_x,
        "pad_y": pad_y,
        "gap": g_min,
        "span": z_max,
        "center": center,
        "pitch_c2c": center * 2 if part["pins"] == 2 else part["pitch"],
        "courtyard_x": courtyard_x,
        "courtyard_y": courtyard_y,
        "errors": validate(pad_x, pad_y, g_min),
    }


MIN_MASK_DAM = 0.10   # 솔더마스크 dam 최소치 [mm]. 고급 공정은 0.075


def validate(pad_x, pad_y, gap):
    """물리적으로 성립하지 않는 결과를 걸러낸다.

    입력 치수나 필렛 상수가 틀리면 여기서 잡힌다. 조용히 통과시키면
    잘못된 값이 라이브러리 전체로 전파되므로 반드시 실패로 표시한다.
    """
    errs = []
    if gap <= 0:
        errs.append(f"패드 간격 음수({gap:+.3f}) — 두 패드가 겹친다. 성립 불가")
    elif gap < MIN_MASK_DAM:
        errs.append(f"패드 간격 {gap:.3f} < 마스크 dam 최소 {MIN_MASK_DAM} — 제조 불가")
    if pad_x <= 0 or pad_y <= 0:
        errs.append("패드 치수가 0 이하")
    return errs


def symbol_name(part, level):
    """IPC-7351 명명 규칙에 따른 심볼명.

    CHIP      : {prefix}{LL}{WW}X{HH}{suffix}      예) RESC1608X55M
    그 외     : {prefix}{PP}P{ZZZ}X{HH}-{pins}{suffix}  예) SOT95P237X112-3M

    치수는 0.01mm 단위 정수로 인코딩한다(IPC 규칙).
    Level A -> 접미사 M, B -> N, C -> L (등급 문자와 다르다).
    """
    sfx = DENSITY_SUFFIX[level]
    prefix = part["name_prefix"]
    h = round(part["height"] * 100)

    if part["family"] == "CHIP":
        # 바디 공칭 치수를 0.1mm 단위로 (1.6 x 0.8 -> 1608)
        ll = round((part["L_min"] + part["L_max"]) / 2 * 10)
        ww = round((part["W_min"] + part["W_max"]) / 2 * 10)
        return f"{prefix}{ll:02d}{ww:02d}X{h:02d}{sfx}"

    pitch = round(part["pitch"] * 100)
    span = round((part["L_min"] + part["L_max"]) / 2 * 100)
    return f"{prefix}{pitch}P{span}X{h}-{part['pins']}{sfx}"


NUMERIC = ("L_min", "L_max", "W_min", "W_max", "T_min", "T_max",
           "pitch", "height", "body_W_max")


def load(path):
    """packages.csv 를 읽는다. TODO 가 남은 행은 건너뛰고 보고한다."""
    parts, skipped = [], []
    with open(path, newline="", encoding="utf-8") as fh:
        # '#' 로 시작하는 주석행은 헤더 인식 전에 걷어낸다
        lines = [ln for ln in fh if not ln.lstrip().startswith("#")]
        for row in csv.DictReader(lines):
            if not row.get("ref"):
                continue
            missing = [k for k in NUMERIC
                       if not row.get(k, "").strip()
                       or row[k].strip().upper() == "TODO"]
            if missing:
                skipped.append((row["ref"], missing))
                continue
            part = {"ref": row["ref"], "family": row["family"].strip().upper(),
                    "name_prefix": row["name_prefix"].strip(),
                    "pins": int(row["pins"]), "notes": row.get("notes", "")}
            for k in NUMERIC:
                part[k] = float(row[k])
            parts.append(part)
    return parts, skipped


def main():
    ap = argparse.ArgumentParser(description="IPC-7351B 랜드 패턴 계산기")
    ap.add_argument("--csv-in", default=str(Path(__file__).parent / "packages.csv"))
    ap.add_argument("--level", nargs="+", default=["A"], choices=["A", "B", "C"],
                    help="밀도 등급 (기본 A = Most). 여러 개 주면 비교 출력")
    ap.add_argument("--csv", metavar="OUT", help="결과를 CSV 로 저장")
    args = ap.parse_args()

    parts, skipped = load(args.csv_in)

    if VERIFY_REQUIRED:
        print("=" * 78)
        print("  경고: 잠정값(PROVISIONAL) — 필렛 상수 미검증")
        print("  FILLET_GOALS / F / P / COURTYARD_EXCESS 를 IPC-7351B 원문과")
        print("  대조한 뒤 VERIFY_REQUIRED = False 로 바꿀 것.")
        print("=" * 78)

    rows = []
    for level in args.level:
        print(f"\n{'#' * 78}\n#  Density Level {level} "
              f"({ {'A': 'Most', 'B': 'Nominal', 'C': 'Least'}[level] })"
              f" — 접미사 '{DENSITY_SUFFIX[level]}'\n{'#' * 78}")
        hdr = (f"{'ref':<12} {'symbol name':<22} {'pad X':>7} {'pad Y':>7} "
               f"{'gap':>7} {'span':>7} {'c2c':>7} {'courtyard':>14}")
        print(hdr)
        print("-" * len(hdr))
        for part in parts:
            r = compute(part, level)
            r["level"] = level
            rows.append(r)
            flag = " <== FAIL" if r["errors"] else ""
            print(f"{r['ref']:<12} {r['name']:<22} "
                  f"{r['pad_x']:>7.3f} {r['pad_y']:>7.3f} {r['gap']:>7.3f} "
                  f"{r['span']:>7.3f} {r['pitch_c2c']:>7.3f} "
                  f"{r['courtyard_x']:>6.2f} x {r['courtyard_y']:<5.2f}{flag}")
            for e in r["errors"]:
                print(f"{'':<12} !! {e}")

    print("\n단위: mm.  pad X = 패드 폭, pad Y = 패드 길이, "
          "gap = 패드 안쪽 간격,\n"
          "span = 패드 바깥 끝~끝, c2c = 패드 중심 간 거리.")

    if skipped:
        print(f"\n치수 미입력으로 건너뛴 부품 {len(skipped)}개 "
              f"— datasheet 에서 채울 것:")
        for ref, missing in skipped:
            print(f"  {ref:<14} {', '.join(missing)}")

    if args.csv:
        fields = ["level", "ref", "name", "pad_x", "pad_y", "gap", "span",
                  "center", "pitch_c2c", "courtyard_x", "courtyard_y"]
        with open(args.csv, "w", newline="", encoding="utf-8") as fh:
            wr = csv.DictWriter(fh, fieldnames=fields)
            wr.writeheader()
            for r in rows:
                wr.writerow({k: (round(v, 3) if isinstance(v, float) else v)
                             for k, v in r.items() if k in fields})
        print(f"\n결과 저장: {args.csv}")

    failed = [r for r in rows if r["errors"]]
    if failed:
        print(f"\n{'=' * 78}\n  검증 실패 {len(failed)}건 — 이 값으로 심볼을 만들지 말 것.\n"
              f"  원인은 (1) 입력 치수 오류 또는 (2) 필렛 상수 오류 중 하나다.\n"
              f"{'=' * 78}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
