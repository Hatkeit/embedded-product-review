#!/usr/bin/env python3
"""V2000 트랜스포머 보빈 풋프린트 생성기.

Allegro는 .dra/.psm 가 바이너리라 텍스트로 만들 수 없다. 대신 아래 4가지를 낸다.

  *.dxf        Allegro / 모든 EDA 로 import 하는 기구 형상 (패드 중심·드릴·외곽·코트야드)
  *.kicad_mod  KiCad 풋프린트 — 좌표·드릴·패드를 눈으로 즉시 검증하는 용도
  *.svg        치수 붙은 미리보기
  *.scr        Allegro PCB Editor 용 핀 배치 스크립트 (패드스택 이름만 채우면 됨)
  *.md         패드 좌표표

치수 출처는 각 BOBBIN 정의의 src 필드에 적었다. `VERIFY` 로 표시한 값은
데이터시트 도면으로 확인하지 못한 값이다(세션 프록시가 부품사 도메인을 차단).
"""
import math, os

OUT = os.path.join(os.path.dirname(__file__), "..", "..", "footprints")

# ---------------------------------------------------------------- 보빈 정의
BOBBINS = [
    dict(
        name="XFMR510P3550X3800X3800-12N",
        title="PQ35/35 12핀 보빈 (T2·T4·T6·T8)",
        part="Ferroxcube CPV-PQ35/35-1S-12P-Z / TDK B65882B0012T001",
        # 한 열의 핀 X 좌표(열 중심 기준). 간격 5.1×4 + 9.6×1 = 30.0 mm
        row_x=[-15.0, -9.9, -4.8, 4.8, 9.9, 15.0],
        row_pitch_y=35.5,            # 열 간 거리
        # 핀 번호 배치: (번호, 열, 인덱스).  열 A = -Y, 열 B = +Y
        # 1차(PV, 18~50 V)를 A열, 2차(400 V, PGND)를 B열에 둔다 → 부록 B 요구 3
        pins=[(1, "A", 0), (2, "A", 1), (3, "A", 2), (4, "A", 3), (5, "A", 4), (6, "A", 5),
              (7, "B", 5), (8, "B", 4), (9, "B", 3), (10, "B", 2), (11, "B", 1), (12, "B", 0)],
        used=[1, 2, 9, 10],          # T2 실사용: 1차 1·2 / 2차 9·10
        drill=1.3, pad=2.6,          # VERIFY: 보빈 핀 지름 미확보. ∅1.0 mm 핀 가정
        body=(38.0, 38.0),           # VERIFY: 조립 외곽 (코어 A=35.1, 열간 35.5 기준 추정)
        height=37.7,                 # VERIFY
        src=("핀 간격 5.1(×8)·9.6(×2), 열간 35.5 mm = Ferroxcube CPV-PQ35/35-1S-12P-Z "
             "치수표(검색 스니펫). TDK PQ35 코일포머는 피치 5.0 / 열간 35.8 mm. "
             "권선면적 152 mm²(Ferroxcube) / 158 mm²(TDK), 평균 1턴 75~76 mm."),
    ),
    dict(
        name="XFMR508P2540X3360X3110-13N",
        title="ETD29/16/10 13핀 보빈 (T9)",
        part="Ferroxcube CPH-ETD29-1S-13P",
        # A열 7핀 / B열 6핀, 피치 5.08. A열 span 30.48, B열 span 25.40
        row_x_a=[-15.24, -10.16, -5.08, 0.0, 5.08, 10.16, 15.24],
        row_x_b=[-12.70, -7.62, -2.54, 2.54, 7.62, 12.70],
        row_pitch_y=25.40,
        # VERIFY: 8번이 7번 맞은편인지(되돌림 번호) 1번 맞은편인지 도면 확인 필요.
        # 아래는 되돌림(가장 흔한 관례): A열 1→7 좌→우, B열 8→13 우→좌
        pins=[(1, "A", 0), (2, "A", 1), (3, "A", 2), (4, "A", 3), (5, "A", 4), (6, "A", 5), (7, "A", 6),
              (8, "B", 5), (9, "B", 4), (10, "B", 3), (11, "B", 2), (12, "B", 1), (13, "B", 0)],
        used=[1, 2, 3, 4, 5, 6, 9, 10],   # T9 넷리스트 실사용
        drill=1.3, pad=2.6,               # VERIFY
        body=(33.6, 31.1),                # 보빈 외형 33.60 × 31.10 × 28.96 mm
        height=28.96,
        src=("피치 5.08 mm, 열간 25.40 mm, 외형 33.60×31.10×28.96 mm = 유통사 파라메트릭 표. "
             "권선면적 95 mm², 최소 권선폭 19.4 mm, 평균 1턴 53 mm = Ferroxcube ETD29 데이터시트."),
    ),
]

HEADER = ("V2000 보빈 풋프린트 — 치수는 데이터시트 도면이 아니라 검색으로 얻은 "
          "치수표에서 왔다. 제작 전 원본 PDF 도면과 대조할 것.")


def pin_xy(b, row, idx):
    if "row_x" in b:
        xs = b["row_x"]
    else:
        xs = b["row_x_a"] if row == "A" else b["row_x_b"]
    y = -b["row_pitch_y"] / 2 if row == "A" else b["row_pitch_y"] / 2
    return xs[idx], y


def coords(b):
    return [(n, *pin_xy(b, r, i)) for n, r, i in b["pins"]]


def extents(b):
    c = coords(b)
    r = b["pad"] / 2
    return (min(x for _, x, _ in c) - r, min(y for _, _, y in c) - r,
            max(x for _, x, _ in c) + r, max(y for _, _, y in c) + r)


# ---------------------------------------------------------------- DXF (R12)
def dxf(b):
    L = []
    def g(code, val): L.append(str(code)); L.append(str(val))
    layers = ["PAD_CENTER", "DRILL", "ASSEMBLY", "SILKSCREEN", "PLACE_BOUND", "PIN_NUMBER"]
    g(0, "SECTION"); g(2, "HEADER"); g(0, "ENDSEC")
    g(0, "SECTION"); g(2, "TABLES"); g(0, "TABLE"); g(2, "LAYER"); g(70, len(layers))
    for i, n in enumerate(layers):
        g(0, "LAYER"); g(2, n); g(70, 0); g(62, i + 1); g(6, "CONTINUOUS")
    g(0, "ENDTAB"); g(0, "ENDSEC")
    g(0, "SECTION"); g(2, "ENTITIES")

    def circle(layer, x, y, r):
        g(0, "CIRCLE"); g(8, layer); g(10, f"{x:.4f}"); g(20, f"{y:.4f}"); g(30, 0); g(40, f"{r:.4f}")

    def line(layer, x1, y1, x2, y2):
        g(0, "LINE"); g(8, layer)
        g(10, f"{x1:.4f}"); g(20, f"{y1:.4f}"); g(30, 0)
        g(11, f"{x2:.4f}"); g(21, f"{y2:.4f}"); g(31, 0)

    def rect(layer, x1, y1, x2, y2):
        line(layer, x1, y1, x2, y1); line(layer, x2, y1, x2, y2)
        line(layer, x2, y2, x1, y2); line(layer, x1, y2, x1, y1)

    def text(layer, x, y, h, s):
        g(0, "TEXT"); g(8, layer); g(10, f"{x:.4f}"); g(20, f"{y:.4f}"); g(30, 0)
        g(40, f"{h:.3f}"); g(1, s)

    for n, x, y in coords(b):
        if n not in b["used"]:
            continue
        circle("PAD_CENTER", x, y, b["pad"] / 2)
        circle("DRILL", x, y, b["drill"] / 2)
        text("PIN_NUMBER", x + b["pad"] / 2 + 0.2, y - 0.6, 1.2, str(n))
    bx, by = b["body"]
    rect("ASSEMBLY", -bx / 2, -by / 2, bx / 2, by / 2)
    x1, y1, x2, y2 = extents(b)
    rect("PLACE_BOUND", min(x1, -bx / 2) - 1.0, min(y1, -by / 2) - 1.0,
         max(x2, bx / 2) + 1.0, max(y2, by / 2) + 1.0)
    sx, sy, br = bx / 2 + 0.3, by / 2 + 0.3, 5.0        # 패드를 가로지르지 않도록 모서리만
    for ux in (-1, 1):
        for uy in (-1, 1):
            line("SILKSCREEN", ux * sx, uy * sy, ux * (sx - br), uy * sy)
            line("SILKSCREEN", ux * sx, uy * sy, ux * sx, uy * (sy - br))
    # 1번 핀 표식
    p1 = [c for c in coords(b) if c[0] == 1][0]
    circle("SILKSCREEN", p1[1] - b["pad"] / 2 - 1.0, p1[2], 0.4)
    text("ASSEMBLY", -bx / 2, by / 2 + 1.0, 1.5, b["name"])
    g(0, "ENDSEC"); g(0, "EOF")
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------- KiCad
def kicad(b):
    o = [f'(footprint "{b["name"]}" (version 20221018) (generator v2000_bobbin_gen)',
         '  (layer "F.Cu")',
         f'  (descr "{b["title"]} — {b["part"]}. {HEADER}")',
         '  (attr through_hole)',
         f'  (fp_text reference "T**" (at 0 {-b["body"][1]/2 - 2:.2f}) (layer "F.SilkS")'
         ' (effects (font (size 1.5 1.5) (thickness 0.25))))',
         f'  (fp_text value "{b["name"]}" (at 0 {b["body"][1]/2 + 2:.2f}) (layer "F.Fab")'
         ' (effects (font (size 1.5 1.5) (thickness 0.25))))']
    bx, by = b["body"]
    x, y = bx / 2, by / 2
    pts = [(-x, -y), (x, -y), (x, y), (-x, y), (-x, -y)]
    for (ax, ay), (bx2, by2) in zip(pts, pts[1:]):
        o.append(f'  (fp_line (start {ax:.2f} {ay:.2f}) (end {bx2:.2f} {by2:.2f})'
                 f' (stroke (width 0.1) (type solid)) (layer "F.Fab"))')
    sx, sy, br = bx / 2 + 0.3, by / 2 + 0.3, 5.0
    for ux in (-1, 1):
        for uy in (-1, 1):
            for e in ((ux * (sx - br), uy * sy), (ux * sx, uy * (sy - br))):
                o.append(f'  (fp_line (start {ux*sx:.2f} {uy*sy:.2f}) (end {e[0]:.2f} {e[1]:.2f})'
                         f' (stroke (width 0.12) (type solid)) (layer "F.SilkS"))')
    x1, y1, x2, y2 = extents(b)
    cx1, cy1 = min(x1, -bx / 2) - 1.0, min(y1, -by / 2) - 1.0
    cx2, cy2 = max(x2, bx / 2) + 1.0, max(y2, by / 2) + 1.0
    pts = [(cx1, cy1), (cx2, cy1), (cx2, cy2), (cx1, cy2), (cx1, cy1)]
    for (ax, ay), (bx2, by2) in zip(pts, pts[1:]):
        o.append(f'  (fp_line (start {ax:.2f} {ay:.2f}) (end {bx2:.2f} {by2:.2f})'
                 f' (stroke (width 0.05) (type solid)) (layer "F.CrtYd"))')
    for n, x, y in coords(b):
        if n not in b["used"]:
            continue
        shape = "rect" if n == 1 else "circle"
        o.append(f'  (pad "{n}" thru_hole {shape} (at {x:.3f} {y:.3f})'
                 f' (size {b["pad"]:.2f} {b["pad"]:.2f}) (drill {b["drill"]:.2f})'
                 ' (layers "*.Cu" "*.Mask"))')
    o.append(")")
    return "\n".join(o) + "\n"


# ---------------------------------------------------------------- SVG 미리보기
def svg(b):
    x1, y1, x2, y2 = extents(b)
    bx, by = b["body"]
    m = 16
    X1, Y1 = min(x1, -bx / 2) - m, min(y1, -by / 2) - m
    X2, Y2 = max(x2, bx / 2) + m, max(y2, by / 2) + m
    W, H = X2 - X1, Y2 - Y1
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{X1:.2f} {Y1:.2f} {W:.2f} {H:.2f}"'
         f' width="{W*12:.0f}" height="{H*12:.0f}">',
         f'<rect x="{X1}" y="{Y1}" width="{W}" height="{H}" fill="#fbfbfd"/>',
         f'<rect x="{-bx/2}" y="{-by/2}" width="{bx}" height="{by}" fill="none"'
         ' stroke="#1B3A8F" stroke-width="0.25" stroke-dasharray="1.2 0.8"/>']
    for n, x, y in coords(b):
        on = n in b["used"]
        s.append(f'<circle cx="{x:.3f}" cy="{y:.3f}" r="{b["pad"]/2:.3f}"'
                 f' fill="{"#C81E1E" if on else "none"}" opacity="{0.85 if on else 1}"'
                 f' stroke="{"none" if on else "#bbb"}" stroke-width="0.15"'
                 f' stroke-dasharray="{"" if on else "0.6 0.4"}"/>')
        if on:
            s.append(f'<circle cx="{x:.3f}" cy="{y:.3f}" r="{b["drill"]/2:.3f}" fill="#fbfbfd"/>')
        s.append(f'<text x="{x:.3f}" y="{y + (-b["pad"]/2 - 0.8 if y < 0 else b["pad"]/2 + 2.2):.3f}"'
                 f' font-size="2" text-anchor="middle" fill="{"#111" if on else "#aaa"}"'
                 f' font-family="monospace">{n}</text>')
    s.append(f'<text x="{X1 + 1.5}" y="{Y1 + 4}" font-size="2.6" fill="#111"'
             f' font-family="sans-serif">{b["name"]}</text>')
    s.append(f'<text x="{X1 + 1.5}" y="{Y1 + 7.2}" font-size="2" fill="#555"'
             f' font-family="sans-serif">{b["title"]} · 열간 {b["row_pitch_y"]} mm ·'
             f' 드릴 ⌀{b["drill"]} / 패드 ⌀{b["pad"]} mm</text>')
    s.append(f'<text x="{X1 + 1.5}" y="{Y2 - 4.4}" font-size="1.8" fill="#888"'
             f' font-family="sans-serif">붉은 패드 = 실사용, 점선 = 미실장(핀 제거)</text>')
    s.append(f'<text x="{X1 + 1.5}" y="{Y2 - 1.8}" font-size="1.8" fill="#888"'
             f' font-family="sans-serif">열 간 연면거리 {b["row_pitch_y"] - b["pad"]:.1f} mm'
             f' (패드 가장자리 기준, 요구 8 mm)</text>')
    s.append("</svg>")
    return "\n".join(s)


# ---------------------------------------------------------------- Allegro .scr
def scr(b):
    o = [f"# {b['name']} — {b['title']}", f"# {b['part']}", f"# {HEADER}",
         "# Allegro PCB Editor: File > Script > Play. 먼저 패드스택을 만들고 이름을 PADSTACK 에 넣을 것.",
         f"# 권장 패드스택: 드릴 {b['drill']:.2f} mm 도금, 패드 ⌀{b['pad']:.2f} mm, 안티패드 ⌀{b['pad']+0.8:.2f} mm",
         "setwindow pcb", "units mm", "", "define PADSTACK BOBBIN_D130_P260", ""]
    for n, x, y in coords(b):
        if n not in b["used"]:
            continue
        o.append(f"add pin $PADSTACK {n} {x:.4f} {y:.4f} 0")
    o += ["", "# 조립 외곽 (Package Geometry/Assembly_Top)",
          f"# rectangle {-b['body'][0]/2:.2f} {-b['body'][1]/2:.2f}"
          f" {b['body'][0]/2:.2f} {b['body'][1]/2:.2f}", "save"]
    return "\n".join(o) + "\n"


# ---------------------------------------------------------------- 좌표표
def table(b):
    o = [f"### {b['name']} — {b['title']}", "", f"- 부품: {b['part']}",
         f"- 열 간 거리 {b['row_pitch_y']} mm, 드릴 ⌀{b['drill']} mm, 패드 ⌀{b['pad']} mm",
         f"- 조립 외곽 {b['body'][0]} × {b['body'][1]} mm, 높이 {b['height']} mm",
         f"- 치수 출처: {b['src']}", "",
         "| 핀 | X (mm) | Y (mm) | 실장 |", "|---|---|---|---|"]
    for n, x, y in coords(b):
        o.append(f"| {n} | {x:+.3f} | {y:+.3f} | {'**사용**' if n in b['used'] else '제거' } |")
    x1, y1, x2, y2 = extents(b)
    o += ["", f"- 패드 외곽: X {x1:+.2f} ~ {x2:+.2f}, Y {y1:+.2f} ~ {y2:+.2f} mm",
          f"- 열 간 연면거리(패드 가장자리 기준): **{b['row_pitch_y'] - b['pad']:.1f} mm**", ""]
    return "\n".join(o)


def with_all_pins(b):
    """핀을 자르지 않고 전부 실장하는 변형 (보빈을 개조 없이 그대로 쓸 때)."""
    c = dict(b)
    c["used"] = [n for n, _, _ in b["pins"]]
    c["name"] = b["name"].replace("-12N", "-12N-ALL").replace("-13N", "-13N-ALL")
    c["title"] = b["title"] + " — 전 핀 실장"
    return c


def main():
    os.makedirs(OUT, exist_ok=True)
    md = ["# V2000 보빈 풋프린트 좌표표", "", HEADER, ""]
    for b in [x for pair in ((b, with_all_pins(b)) for b in BOBBINS) for x in pair]:
        base = os.path.join(OUT, b["name"])
        for ext, data in ((".dxf", dxf(b)), (".kicad_mod", kicad(b)),
                          (".svg", svg(b)), (".scr", scr(b))):
            with open(base + ext, "w", encoding="utf-8") as f:
                f.write(data)
        md.append(table(b))
        print(f"{b['name']}: dxf/kicad_mod/svg/scr 생성, 사용 핀 {b['used']}")
    with open(os.path.join(OUT, "README.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md))


if __name__ == "__main__":
    main()
