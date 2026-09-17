#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""250 W 언폴딩 마이크로인버터 시스템 회로도 생성기.  실행: python3 make_schematic_mi.py"""

W, H = 1660, 1095
K, B, C, R, G, V = "#0f172a", "#1d4ed8", "#0891b2", "#dc2626", "#64748b", "#7c3aed"
p = []
add = p.append


def wire(pts, col=K, w=1.9, dash=None):
    d = " ".join(f"{x},{y}" for x, y in pts)
    da = f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<polyline points="{d}" fill="none" stroke="{col}" stroke-width="{w}"{da}/>')


def dot(x, y, col=K):
    add(f'<circle cx="{x}" cy="{y}" r="3.4" fill="{col}"/>')


def esc(s):
    """XML 이스케이프.  &#NNNN; 엔티티와 &amp; 는 그대로 둔다."""
    return str(s).replace("<", "&lt;").replace(">", "&gt;")


def txt(x, y, s, sz=11, col=K, an="start", wt="400"):
    add(f'<text x="{x}" y="{y}" font-size="{sz}" fill="{col}" text-anchor="{an}" '
        f'font-weight="{wt}">{esc(s)}</text>')


def lines(x, y, rows, sz=9, col=G, an="start", lh=12):
    for i, s in enumerate(rows):
        txt(x, y + i * lh, s, sz, col, an)


def block(x, y, w, h, title, sub=(), col=K, fill="#fff"):
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{fill}" stroke="{col}" stroke-width="1.6"/>')
    sub = list(sub)
    y0 = y + h / 2 - (14 + len(sub) * 12) / 2 + 11
    txt(x + w / 2, y0, title, 11.5, K, "middle", "700")
    lines(x + w / 2, y0 + 15, sub, 9, G, "middle")


def cap_v(x, y, lab=None, col=K, side=1):
    add(f'<line x1="{x-14}" y1="{y}" x2="{x+14}" y2="{y}" stroke="{col}" stroke-width="2.6"/>')
    add(f'<line x1="{x-14}" y1="{y+10}" x2="{x+14}" y2="{y+10}" stroke="{col}" stroke-width="2.6"/>')
    if lab:
        txt(x + side * 20, y + 9, lab, 9.5, K, "start" if side > 0 else "end")


def ind_h(x, y, lab=None, col=K, n=4, r=9):
    add(f'<path d="M {x},{y} ' + " ".join(f"a {r},{r} 0 0 1 {2*r},0" for _ in range(n)) +
        f'" fill="none" stroke="{col}" stroke-width="1.9"/>')
    if lab:
        txt(x + n * r, y - 15, lab, 9.5, K, "middle")


def mosfet(x, y, rot=0, col=K):
    add(f'<g transform="translate({x},{y}) rotate({rot})">')
    for a in (f'<line x1="0" y1="0" x2="0" y2="-13" stroke="{col}" stroke-width="1.7"/>',
              f'<line x1="-14" y1="-13" x2="14" y2="-13" stroke="{col}" stroke-width="1.7"/>',
              f'<line x1="-14" y1="-13" x2="-14" y2="-31" stroke="{col}" stroke-width="1.7"/>',
              f'<line x1="-14" y1="-31" x2="14" y2="-31" stroke="{col}" stroke-width="1.7"/>',
              f'<line x1="0" y1="-31" x2="0" y2="-44" stroke="{col}" stroke-width="1.7"/>',
              f'<line x1="-22" y1="-10" x2="-22" y2="-34" stroke="{col}" stroke-width="2.3"/>',
              f'<line x1="-22" y1="-22" x2="-36" y2="-22" stroke="{col}" stroke-width="1.7"/>',
              f'<path d="M 8,-13 L 8,-23 L 15,-18 Z" fill="{col}"/>'):
        add(a)
    add('</g>')


def diode_h(x, y, col=K):
    add(f'<path d="M {x},{y-11} L {x},{y+11} L {x+20},{y} Z" fill="#fff" stroke="{col}" stroke-width="1.7"/>')
    add(f'<line x1="{x+20}" y1="{y-11}" x2="{x+20}" y2="{y+11}" stroke="{col}" stroke-width="2.5"/>')


def coil_v(x, y, n=5, r=8, side=1, col=K):
    add(f'<path d="M {x},{y} ' + " ".join(f"a {r},{r} 0 0 {1 if side>0 else 0} 0,{2*r}" for _ in range(n)) +
        f'" fill="none" stroke="{col}" stroke-width="1.9"/>')


def gnd(x, y, lab=None, col=K):
    add(f'<line x1="{x-14}" y1="{y}" x2="{x+14}" y2="{y}" stroke="{col}" stroke-width="2.3"/>')
    add(f'<line x1="{x-8}" y1="{y+6}" x2="{x+8}" y2="{y+6}" stroke="{col}" stroke-width="2"/>')
    add(f'<line x1="{x-3}" y1="{y+12}" x2="{x+3}" y2="{y+12}" stroke="{col}" stroke-width="2"/>')
    if lab:
        txt(x, y + 26, lab, 9, G, "middle")


add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
    f'font-family="ui-monospace,Menlo,Consolas,monospace">')
add(f'<rect width="{W}" height="{H}" fill="#fff"/>')
txt(24, 34, "PV 250 W 언폴딩 마이크로인버터   2상 인터리브 플라이백 + 공유 언폴더   계통 220 V / 60 Hz",
    17, K, "start", "800")
txt(24, 54, "PS-MI-250W-220V Rev.A   |   설계 : calc_mi.py (10/10 PASS)   |   "
            "동작검증 : sim_mi.py (23/23 PASS, THD 1.68 %, PF 0.9999)", 10.5, G)

# ===================================================== A. 전력단
PA, PAH = 72, 566
add(f'<rect x="24" y="{PA}" width="{W-48}" height="{PAH}" rx="10" fill="#fbfcfe" stroke="#cbd5e1"/>')
txt(40, PA + 22, "A.  전력단", 13, K, "start", "800")

RA, RB, PG = 182, 332, 502          # A상 레일 / B상 레일 / 1차 GND
X_PV, X_DEC, X_T, X_CORE, X_S, X_D, X_NODE = 56, 250, 500, 558, 604, 700, 812
X_UNF, X_LF, X_GRID = 900, 1150, 1400

block(X_PV, 214, 116, 96, "PV Module", ["250 W 60셀", "Vmp 30.5 V / Imp 8.2 A"], B, "#eff6ff")
lines(X_PV, 326, ["Voc(STC) 37.6 V  (상한 43.4 V)", "저온 -25 C : 43.6 V",
                  "-> 입력 절대최대 50 V"], 9, G)
wire([(X_PV + 116, 240), (X_DEC, 240), (X_DEC, RA), (X_T, RA)], B, 2.3)
wire([(X_PV + 116, 284), (X_DEC - 60, 284), (X_DEC - 60, PG), (X_T + 30, PG)], B, 2.3)
wire([(X_DEC, 240), (X_DEC, RB), (X_T, RB)], B, 2.3)
dot(X_DEC, 240, B)

# --- 2w 디커플링
XD = X_DEC - 42
cap_v(XD, 310, None, V)
wire([(XD, 240), (XD, 310)], V, 2.3)
wire([(XD, 320), (XD, PG)], V, 2.3)
dot(XD, 240, V); dot(XD, PG, V)
txt(XD, 232, "2w 디커플링", 10, V, "middle", "700")
block(56, 542, 356, 92, "2w 디커플링 663 mJ  -  63 V 2,700 uF x 5 실장",
      ["= 13,500 uF  (설계 최소요구 7,129 uF 의 1.89 배)",
       "2w 리플 1,589 mVpp (5.2 %),  MPPT 이용률 99.75 %",
       "리플전류 개당 1.47 Arms(120 Hz 등가) - 정격 대조 필수",
       "입력 절대최대 50 V (63 V 의 79.4 %),  저장에너지 12.8 J"], V, "#faf5ff")

# --- 2상 인터리브 플라이백
for ph, (rail, lbl, ofs) in enumerate(((RA, "A상  0 deg", 0), (RB, "B상  180 deg", 0))):
    y_sw = rail + 92
    dot(X_T, rail, B)
    coil_v(X_T, rail + 4, 5, 8, -1, B)
    add(f'<circle cx="{X_T-11}" cy="{rail+11}" r="3" fill="{K}"/>')
    txt(X_T - 24, rail + 44, "Np 10", 9.5, K, "end", "700")
    wire([(X_T, rail + 84), (X_T, y_sw)], B, 2.3)
    for cx in (X_CORE, X_CORE + 9):
        add(f'<line x1="{cx}" y1="{rail}" x2="{cx}" y2="{rail+88}" stroke="{G}" stroke-width="2.8"/>')
    coil_v(X_S, rail + 4, 5, 8, 1, R)
    add(f'<circle cx="{X_S+11}" cy="{rail+77}" r="3" fill="{K}"/>')
    txt(X_S + 22, rail + 44, "Ns 60", 9.5, K, "start", "700")
    mosfet(X_T, y_sw + 44, 0, B)
    wire([(X_T, y_sw), (X_T, y_sw + 0)], B, 2.3)
    wire([(X_T, y_sw + 44), (X_T, PG)], B, 2.3)
    dot(X_T, PG, B)
    txt(X_T + 20, y_sw + 20, f"Q{ph+1}  150 V", 9.5, K, "start", "700")
    txt(X_T - 250, rail - 14, lbl, 10.5, B, "start", "800")
    # 액티브 클램프 (간략)
    block(X_T - 226, rail + 26, 112, 42, "ACF 클램프", ["Cc + Q 150 V"], B, "#eff6ff")
    wire([(X_T - 114, rail + 47), (X_T - 22, rail + 47), (X_T - 22, y_sw), (X_T, y_sw)], B, 1.6, "4,3")
    wire([(X_T - 226, rail + 47), (X_T - 244, rail + 47), (X_T - 244, rail), (X_T, rail)], B, 1.6, "4,3")
    # 2차 -> 다이오드 -> 공통 출력노드
    wire([(X_S, rail + 4), (X_S, rail - 26), (X_D, rail - 26)], R, 2.3)
    diode_h(X_D, rail - 26, R)
    wire([(X_D + 20, rail - 26), (X_NODE, rail - 26), (X_NODE, 156)], R, 2.3)
    wire([(X_S, rail + 84), (X_S, rail + 112), (X_NODE + 90, rail + 112)], R, 2.3)
    txt(X_D + 10, rail - 42, f"D{ph+1}  1200 V SiC", 9.5, K, "middle", "700")

block(X_T - 96, 548, 200, 50, "T1 / T2  ETD44 / N97", ["Lm 23 uH,  Np:Ns:Naux = 10:60:4"], G, "#f8fafc")
gnd(X_T + 60, PG, "PGND", B)
dot(X_NODE, RA - 26, R)
dot(X_NODE + 90, RB + 112, R)

# --- 공통 출력 노드 (정류정현파) + 언폴더
SGN = 520
wire([(X_NODE, 156), (X_UNF - 40, 156)], R, 2.3)
wire([(X_NODE + 90, RB + 112), (X_NODE + 90, SGN), (X_UNF - 40, SGN)], R, 2.3)
cap_v(X_NODE + 40, 300, "Cf 0.22 uF", R, -1)
wire([(X_NODE + 40, 156), (X_NODE + 40, 300)], R, 2.3)
wire([(X_NODE + 40, 310), (X_NODE + 40, SGN)], R, 2.3)
dot(X_NODE + 40, 156, R); dot(X_NODE + 40, SGN, R)
txt(X_NODE + 66, 136, "정류정현파 0 ~ 342 V", 10, R, "start", "700")
txt(X_NODE + 66, 148, "벌크 커패시터를 달면 언폴딩이 성립하지 않는다", 9, R, "start")

block(X_UNF, 196, 170, 220, "언폴딩 브리지", ["650 V MOSFET x 4", "120 Hz 영교차 정류",
                                        "도통손 0.77 W"], V, "#faf5ff")
wire([(X_UNF - 40, 156), (X_UNF + 40, 156), (X_UNF + 40, 196)], R, 2.3)
wire([(X_UNF - 40, SGN), (X_UNF + 130, SGN), (X_UNF + 130, 416)], R, 2.3)
wire([(X_UNF + 170, 250), (X_LF, 250)], V, 2.3)
wire([(X_UNF + 170, 360), (X_LF + 130, 360)], V, 2.3)
ind_h(X_LF, 250, "Lf 2.2 mH", V)
wire([(X_LF + 72, 250), (X_GRID, 250)], V, 2.3)
wire([(X_LF + 130, 360), (X_GRID, 360)], V, 2.3)
block(X_GRID, 256, 120, 98, "계통", ["220 V / 60 Hz", "1.14 Arms"], V, "#faf5ff")
lines(X_LF - 40, 420, ["출력필터 Lf 2.2 mH + Cf 0.22 uF",
                       "fc 7.2 kHz, 200 kHz 감쇠 58 dB",
                       "Z0 = 100 Ohm -> 능동 댐핑 필수"], 9, G)

# ===================================================== B. 제어
PB = PA + PAH + 20
add(f'<rect x="24" y="{PB}" width="{W-48}" height="400" rx="10" fill="#fbfcfe" stroke="#cbd5e1"/>')
txt(40, PB + 22, "B.  제어  (단일 MCU)", 13, K, "start", "800")
YB = PB + 46
for i, (t1_, s1) in enumerate((("Vpv / Ipv 센싱", ["분압 + 션트 3 mOhm"]),
                               ("Vgrid 센싱 + PLL", ["영교차 + SOGI-PLL"]),
                               ("Igrid 센싱", ["Lf 전류, 홀 또는 션트"]),
                               ("Vout(정류측) 센싱", ["능동댐핑용, 동기샘플링"]))):
    block(56, YB + i * 76, 200, 60, t1_, s1, C, "#ecfeff")
    wire([(256, YB + i * 76 + 30), (300, YB + i * 76 + 30), (300, YB + 60 + i * 56), (340, YB + 60 + i * 56)], C, 1.5)

block(340, YB - 6, 330, 330, "", (), C)
txt(505, YB + 18, "MCU 제어 (100 kHz)", 12.5, C, "middle", "800")
for i, (a, b) in enumerate((("1. MPPT (P&amp;O + 전역스캔)", "반주기 이동평균 Vpv 사용"),
                            ("2. 진폭루프 kp 0.42 / ki 7.2", "~25 Hz (상한 f_line/2 = 30 Hz)"),
                            ("3. 전류기준 A x |sin(wt)|", "PLL 위상 동기"),
                            ("4. 전류루프 kp 1.0 / ki 1e4", "피드포워드 + PI"),
                            ("5. 능동 댐핑 R=100 Ohm", "800 Hz ~ 20 kHz 대역통과"),
                            ("6. 모델역변환 -> Ipk*", "+ 슬로프보상 램프 보정"),
                            ("7. 언폴더 게이트 (120 Hz)", "영교차 ±1 deg, 전류 0 확인"))):
    y = YB + 34 + i * 40
    add(f'<rect x="352" y="{y}" width="306" height="32" rx="4" fill="#f8fafc" stroke="#e2e8f0"/>')
    txt(360, y + 13, a, 9.5, K, "start", "700")
    txt(360, y + 25, b, 8.5, G)

block(700, YB + 10, 230, 80, "게이트 드라이브", ["Q1/Q2 + ACF 클램프 x2", "180 deg 인터리브 PWM"], C, "#ecfeff")
block(700, YB + 110, 230, 80, "언폴더 드라이브", ["650 V 부트스트랩 x4", "영교차 데드타임"], V, "#faf5ff")
block(700, YB + 210, 230, 110, "계통 보호", ["OV/UV, OF/UF (KS C 8565)",
                                        "능동 단독운전 방지",
                                        "DC 주입 < 0.5 %", "절연저항 Riso"], R, "#fef2f2")
wire([(670, YB + 50), (700, YB + 50)], C, 1.6)
wire([(670, YB + 150), (700, YB + 150)], V, 1.6)
wire([(670, YB + 250), (700, YB + 250)], R, 1.6)

lines(970, YB + 16, [
    "검증 결과 (sim_mi.py, 23/23 PASS)",
    "",
    "  정격 THD          1.68 %      (기준 5 %)",
    "  역률               0.9999      (기준 0.99)",
    "  DC 주입            0.2 mA      (기준 5.7 mA)",
    "  개별 고조파 최악    23차 0.23 % (한도 0.60 %)",
    "  영교차 왜곡구간     +-11.8 deg  (0.55 ms)",
    "  인터리브 입력리플   13.5 -> 6.3 Arms (-54 %)",
    "  상당 Ipk           16.9 A      (OCP 23 A)",
    "  Bpk                0.224 T     (Bsat 0.41 T)",
    "  MOSFET Vds         88.7 V      (150 V 의 59 %)",
    "  2차 다이오드        642 V       (1200 V 의 54 %)",
    "",
    "  전 부하(7~96 %) 고조파 규격 적합",
    "  계통 +-10 % / PLL 오차 3 deg 허용",
], 10, K, "start", 20)
txt(970, YB + 6, "", 10)

add("</svg>")
out = "docs/microinverter-250w/schematic-mi.svg"
open(out, "w", encoding="utf-8").write("\n".join(p))
print("wrote", out)
