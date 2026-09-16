#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PSIM 심볼 스타일 회로도 생성기.  실행: python3 make_schematic.py"""

W, H = 1600, 1140
K, B, C, R, G = "#0f172a", "#1d4ed8", "#0891b2", "#dc2626", "#64748b"
p = []
add = p.append


def wire(pts, col=K, w=1.8, dash=None):
    d = " ".join(f"{x},{y}" for x, y in pts)
    da = f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<polyline points="{d}" fill="none" stroke="{col}" stroke-width="{w}"{da}/>')


def dot(x, y, col=K):
    add(f'<circle cx="{x}" cy="{y}" r="3.4" fill="{col}"/>')


def txt(x, y, s, size=11, col=K, anchor="start", weight="400"):
    add(f'<text x="{x}" y="{y}" font-size="{size}" fill="{col}" text-anchor="{anchor}" '
        f'font-weight="{weight}">{s}</text>')


def lines(x, y, rows, size=9, col=G, anchor="start", lh=12):
    for i, s in enumerate(rows):
        txt(x, y + i * lh, s, size, col, anchor)


def block(x, y, w, h, title, sub=(), col=K, fill="#ffffff"):
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{fill}" '
        f'stroke="{col}" stroke-width="1.6"/>')
    sub = list(sub)
    total = 14 + len(sub) * 12
    y0 = y + h / 2 - total / 2 + 11
    txt(x + w / 2, y0, title, 11.5, K, "middle", "700")
    lines(x + w / 2, y0 + 15, sub, 9, G, "middle")


def res_v(x, y, h, lab=None, col=K):
    add(f'<rect x="{x-7}" y="{y}" width="14" height="{h}" fill="#fff" stroke="{col}" stroke-width="1.5"/>')
    if lab:
        txt(x + 13, y + h / 2 + 4, lab, 9.5, K)


def res_h(x, y, w, lab=None, col=K):
    add(f'<rect x="{x}" y="{y-7}" width="{w}" height="14" fill="#fff" stroke="{col}" stroke-width="1.5"/>')
    if lab:
        txt(x + w / 2, y - 13, lab, 9.5, K, "middle")


def cap_v(x, y, lab=None, col=K, labside=1):
    add(f'<line x1="{x-14}" y1="{y}" x2="{x+14}" y2="{y}" stroke="{col}" stroke-width="2.6"/>')
    add(f'<line x1="{x-14}" y1="{y+10}" x2="{x+14}" y2="{y+10}" stroke="{col}" stroke-width="2.6"/>')
    if lab:
        txt(x + labside * 20, y + 9, lab, 9.5, K, "start" if labside > 0 else "end")


def cap_h(x, y, lab=None, col=K):
    add(f'<line x1="{x}" y1="{y-14}" x2="{x}" y2="{y+14}" stroke="{col}" stroke-width="2.6"/>')
    add(f'<line x1="{x+10}" y1="{y-14}" x2="{x+10}" y2="{y+14}" stroke="{col}" stroke-width="2.6"/>')
    if lab:
        txt(x + 5, y + 30, lab, 9.5, K, "middle")


def ind_h(x, y, lab=None, col=K, n=4, r=9):
    add(f'<path d="M {x},{y} ' + " ".join(f"a {r},{r} 0 0 1 {2*r},0" for _ in range(n)) +
        f'" fill="none" stroke="{col}" stroke-width="1.8"/>')
    if lab:
        txt(x + n * r, y - 15, lab, 9.5, K, "middle")


def coil_v(x, y, n=6, r=9, side=1, col=K):
    """세로 권선.  side=+1 이면 오른쪽으로 부푼다.  높이 = 2*n*r"""
    add(f'<path d="M {x},{y} ' + " ".join(
        f"a {r},{r} 0 0 {1 if side > 0 else 0} 0,{2*r}" for _ in range(n)) +
        f'" fill="none" stroke="{col}" stroke-width="1.9"/>')


def mosfet(x, y, rot=0, col=K):
    """(x,y) = 소스 단자.  rot=0 드레인 위 / rot=90 드레인 오른쪽 / rot=-90 드레인 왼쪽"""
    add(f'<g transform="translate({x},{y}) rotate({rot})">')
    for a in (f'<line x1="0" y1="0" x2="0" y2="-14" stroke="{col}" stroke-width="1.7"/>',
              f'<line x1="-15" y1="-14" x2="15" y2="-14" stroke="{col}" stroke-width="1.7"/>',
              f'<line x1="-15" y1="-14" x2="-15" y2="-34" stroke="{col}" stroke-width="1.7"/>',
              f'<line x1="-15" y1="-34" x2="15" y2="-34" stroke="{col}" stroke-width="1.7"/>',
              f'<line x1="0" y1="-34" x2="0" y2="-48" stroke="{col}" stroke-width="1.7"/>',
              f'<line x1="-24" y1="-11" x2="-24" y2="-37" stroke="{col}" stroke-width="2.4"/>',
              f'<line x1="-24" y1="-24" x2="-40" y2="-24" stroke="{col}" stroke-width="1.7"/>',
              f'<path d="M 9,-14 L 9,-25 L 16,-19.5 Z" fill="{col}"/>',
              f'<line x1="9" y1="-14" x2="16" y2="-14" stroke="{col}" stroke-width="1.4"/>'):
        add(a)
    add('</g>')


def diode_h(x, y, col=K):
    add(f'<path d="M {x},{y-12} L {x},{y+12} L {x+22},{y} Z" fill="#fff" stroke="{col}" stroke-width="1.7"/>')
    add(f'<line x1="{x+22}" y1="{y-12}" x2="{x+22}" y2="{y+12}" stroke="{col}" stroke-width="2.6"/>')


def gnd(x, y, lab=None, col=K):
    add(f'<line x1="{x-15}" y1="{y}" x2="{x+15}" y2="{y}" stroke="{col}" stroke-width="2.4"/>')
    add(f'<line x1="{x-9}" y1="{y+6}" x2="{x+9}" y2="{y+6}" stroke="{col}" stroke-width="2.1"/>')
    add(f'<line x1="{x-4}" y1="{y+12}" x2="{x+4}" y2="{y+12}" stroke="{col}" stroke-width="2.1"/>')
    if lab:
        txt(x, y + 26, lab, 9, G, "middle")


# ================================================================= 캔버스
add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
    f'font-family="ui-monospace,Menlo,Consolas,monospace">')
add(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
txt(24, 34, "PV 입력 액티브클램프 플라이백   18-50 V(PV) / 400 V / 150 W   -   PSIM 심볼 회로도",
    17, K, "start", "800")
txt(24, 54, "PS-FBT-150W-400V Rev.A   |   소자 파라미터 : psim-circuit.md 4장   |   "
            "제어 C 코드 : psim_control.c   |   검증 : sim_verify.py (32/32 PASS)", 10.5, G)

# ================================================================= A. 전력단
PA_Y, PA_H = 70, 452
add(f'<rect x="24" y="{PA_Y}" width="{W-48}" height="{PA_H}" rx="10" fill="#fbfcfe" stroke="#cbd5e1"/>')
txt(40, PA_Y + 22, "A.  전력단   Active Clamp Flyback", 13, K, "start", "800")

RAIL, CLAMP, SW, SRC, PG = 214, 132, 338, 412, 468
X_PV, X_Q3, X_LCM, X_CIN, X_CC = 56, 200, 322, 410, 508
X_T1, X_CORE, X_SEC, X_D1, X_CO, X_BUS = 704, 762, 806, 950, 1060, 1290
COILH = 108   # 권선 높이 (6 x 2 x 9)

# --- PV 모듈
block(X_PV, RAIL - 34, 118, 92, "PV Module",
      ["Solar Module", "(functional model)"], B, "#eff6ff")
lines(X_PV, RAIL + 76, ["Voc(STC) &#8804; 43.1 V  (저온 -25 &#176;C 상승분 포함)",
                        "Pmp &#8804; 150 W,  Vmp 18 ~ 42 V"], 9, G)
wire([(X_PV + 118, RAIL), (X_Q3 - 22, RAIL)], B, 2.3)
wire([(X_PV + 118, RAIL + 40), (X_PV + 150, RAIL + 40), (X_PV + 150, PG), (X_T1, PG)], B, 2.3)

# --- 역극성 보호 + 퓨즈 + CM 초크
block(X_Q3 - 22, RAIL - 25, 92, 50, "Q3", ["역극성 보호", "ideal-diode ctrl"], B, "#eff6ff")
wire([(X_Q3 + 70, RAIL), (X_Q3 + 86, RAIL)], B, 2.3)
res_h(X_Q3 + 86, RAIL, 34, "F1 10 A", B)
wire([(X_Q3 + 120, RAIL), (X_LCM, RAIL)], B, 2.3)
ind_h(X_LCM, RAIL, "L_CM", B)
wire([(X_LCM + 72, RAIL), (X_CC, RAIL)], B, 2.3)

# --- 입력 커패시터
dot(X_CIN, RAIL, B)
wire([(X_CIN, RAIL), (X_CIN, RAIL + 54)], B, 2.3)
cap_v(X_CIN, RAIL + 54, None, B)
wire([(X_CIN, RAIL + 64), (X_CIN, PG)], B, 2.3)
dot(X_CIN, PG, B)
lines(X_CIN + 22, RAIL + 52, ["Cin 250 uF", "전해 2x220 uF/63 V", "+ 세라믹 6x10 uF/100 V"], 9, G)
txt(X_CIN + 22, RAIL + 88, "리플 5.68 Arms", 9, R)

# --- 액티브 클램프 :  VIN+ -- Cc -- Q2(D<-S) -- SW
dot(X_CC, RAIL, B)
wire([(X_CC, RAIL), (X_CC, CLAMP)], B, 2.3)
cap_h(X_CC, CLAMP, "Cc 18 uF / 100 V", B)
wire([(X_CC + 10, CLAMP), (X_CC + 92, CLAMP)], B, 2.3)
mosfet(X_CC + 140, CLAMP, -90, B)      # 소스가 오른쪽(SW) -> 하이사이드 부트스트랩 가능
wire([(X_CC + 140, CLAMP), (X_T1, CLAMP), (X_T1, SW)], B, 2.3)
txt(X_CC + 86, CLAMP + 34, "D", 9, G, "middle")
txt(X_CC + 146, CLAMP + 34, "S (= SW)", 9, G, "middle")
txt(X_CC + 116, CLAMP - 42, "Q2  클램프 150 V", 10.5, K, "middle", "700")
lines(196, CLAMP - 30, [
    "액티브 클램프 : 누설에너지 회수 + ZVS &#8594; Vds 스파이크 없음",
    "V_Cc = VOR = 50.2 V,   Cc &#8805; 5.3 uF  (T_res &#8805; 3 x Toff,max)",
    "100 V X7R 은 50 V 바이어스에서 용량이 절반 &#8594; 18 uF 실장"], 9.5, B)

# --- 트랜스포머 T1
wire([(X_CC, RAIL), (X_T1, RAIL)], B, 2.3)
dot(X_T1, RAIL, B)
coil_v(X_T1, RAIL + 4, 6, 9, -1, B)
add(f'<circle cx="{X_T1-13}" cy="{RAIL+12}" r="3.2" fill="{K}"/>')
txt(X_T1 - 26, RAIL + 56, "Np 9 T", 10, K, "end", "700")
wire([(X_T1, RAIL + 4 + COILH), (X_T1, SW)], B, 2.3)
dot(X_T1, SW, B)
for cx in (X_CORE, X_CORE + 10):
    add(f'<line x1="{cx}" y1="{RAIL}" x2="{cx}" y2="{RAIL+COILH+8}" stroke="{G}" stroke-width="3"/>')
txt(X_CORE + 5, RAIL - 10, "ETD44", 9, G, "middle")
coil_v(X_SEC, RAIL + 4, 6, 9, 1, R)
add(f'<circle cx="{X_SEC+13}" cy="{RAIL+COILH-4}" r="3.2" fill="{K}"/>')
txt(X_SEC + 28, RAIL + 56, "Ns 72 T", 10, K, "start", "700")

# --- 2차 : 비도트단(상) -> D1 -> VOUT+ ,  도트단(하) -> SGND
VB, SG = RAIL - 62, SW + 96
wire([(X_SEC, RAIL + 4), (X_SEC, VB), (X_D1, VB)], R, 2.3)
diode_h(X_D1, VB, R)
wire([(X_D1 + 22, VB), (X_BUS, VB)], R, 2.3)
wire([(X_SEC, RAIL + 4 + COILH), (X_SEC, SG), (X_BUS, SG)], R, 2.3)
txt(X_D1 + 11, VB - 22, "D1  1200 V SiC", 10.5, K, "middle", "700")
txt(X_D1 + 11, VB - 36, "VR = 800 V  (1200 V 의 67 %)", 9, R, "middle")
for xx, lab in ((X_CO, "Cout 4.7 uF / 630 V"), (X_CO + 150, None)):
    dot(xx, VB, R)
    dot(xx, SG, R)
wire([(X_CO, VB), (X_CO, VB + 42)], R, 2.3)
cap_v(X_CO, VB + 42, "Cout 4.7 uF / 630 V", R)
wire([(X_CO, VB + 52), (X_CO, SG)], R, 2.3)
wire([(X_CO + 150, VB), (X_CO + 150, VB + 36)], R, 2.3)
res_v(X_CO + 150, VB + 36, 64, "R_bleed 440 k&#937;", R)
wire([(X_CO + 150, VB + 100), (X_CO + 150, SG)], R, 2.3)
txt(X_BUS + 10, VB - 4, "VOUT+  400 V", 11.5, R, "start", "700")
txt(X_BUS + 10, VB + 12, "하류 인버터 DC-link", 9, G)
txt(X_BUS + 10, SG + 4, "SGND", 11.5, R, "start", "700")

# --- 주 스위치 Q1 + 전류 트랜스
mosfet(X_T1, SRC, 0, B)
wire([(X_T1, SW), (X_T1, SRC - 48)], B, 2.3)
wire([(X_T1, SRC), (X_T1, SRC + 6)], B, 2.3)
add(f'<circle cx="{X_T1}" cy="{SRC+22}" r="15" fill="none" stroke="{C}" stroke-width="1.9"/>')
add(f'<circle cx="{X_T1+23}" cy="{SRC+22}" r="15" fill="none" stroke="{C}" stroke-width="1.9"/>')
wire([(X_T1, SRC + 37), (X_T1, PG)], B, 2.3)
dot(X_T1, PG, B)
gnd(X_T1 + 4, PG, "PGND", B)
txt(X_T1 + 46, SRC + 18, "CT1  1:100", 10, C, "start", "700")
txt(X_T1 + 46, SRC + 31, "&#8594; Rb 10 &#937; (2차측)", 9, G)
txt(X_T1 + 46, SRC - 30, "Q1  주스위치", 10.5, K, "start", "700")
txt(X_T1 + 46, SRC - 17, "150 V, Rds(on) &#8804; 7 m&#937;", 9, G, "start")
txt(X_T1 + 22, SW - 8, "SW", 11, B, "start", "700")
txt(X_T1 + 22, SW + 6, "Vds,max 100.2 V", 9, R)

block(X_CIN + 30, RAIL + 112, 204, 56, "T1   ETD44 / N97",
      ["Lm 26.3 uH &#177;7 %,  Llk &#8804; 0.30 uH", "Np:Ns:Naux = 9 : 72 : 4"], G, "#f8fafc")

# ================================================================= B. 제어단
PB_Y = PA_Y + PA_H + 22
add(f'<rect x="24" y="{PB_Y}" width="{W-48}" height="524" rx="10" fill="#fbfcfe" stroke="#cbd5e1"/>')
txt(40, PB_Y + 22, "B.  센싱 및 제어   PSIM Simplified C Block 기반 디지털 제어", 13, K, "start", "800")

YS = PB_Y + 46
block(56, YS, 176, 58, "Vpv 센싱", ["분압 1/20 + RC 10 kHz"], C, "#ecfeff")
block(56, YS + 74, 176, 58, "Ipv 센싱", ["션트 3 m&#937; + 차동증폭"], C, "#ecfeff")
block(56, YS + 148, 176, 58, "Vout 센싱 (절연)", ["TL431 + 포토커플러"], R, "#fef2f2")
lines(56, YS + 226, ["* MPPT 는 1차측, 버스전압은 2차측 &#8594; Vout 만 절연 전달",
                     "* 리미터 기준 420 V : 하류 인버터(400 V)보다 높게 두어야",
                     "  두 레귤레이터가 서로 싸우지 않는다"], 9, G)
block(56, YS + 274, 300, 62, "보호",
      ["출력 OVP 440 V  /  입력 OVP 55 V",
       "1차 OCP 18.9 A 히컵  /  NTC 과온"], R, "#fef2f2")
block(56, YS + 352, 300, 62, "바이어스",
      ["Vin(18-50 V) &#8594; 65 V급 벅 &#8594; 12 V &#8594; 3.3 V",
       "UVLO 기동 16 V / 정지 13 V (야간 채터링 방지)"], C, "#ecfeff")

CBX, CBY, CBW, CBH = 388, YS - 12, 306, 268
block(CBX, CBY, CBW, CBH, "", (), C)
txt(CBX + CBW / 2, CBY + 24, "Simplified C Block", 12.5, C, "middle", "800")
txt(CBX + CBW / 2, CBY + 39, "psim_control.c   |   fs = 25 kHz", 9.5, G, "middle")
for i, (a, b) in enumerate([
        ("1. 전역 MPP 스캔", "0.95&#8594;0.30 x Voc,  1.2 V / 2 ms"),
        ("2. 개선형 P&amp;O MPPT", "적응스텝 + 일사량 급변 검출"),
        ("3. 루프 A : Vpv PI", "Kp 2.0 / Ki 4000   (~760 Hz)"),
        ("4. 루프 B : Vout 리미트 PI", "Kp 3.5 / Ki 1100, 비대칭 적분"),
        ("5. min-select + 백캘큘레이션", "SS / MPPT / VO 모드 선택"),
        ("6. 소프트스타트 20 ms", "전류지령 상한 램프")]):
    y = CBY + 56 + i * 34
    add(f'<rect x="{CBX+12}" y="{y}" width="{CBW-24}" height="28" rx="4" fill="#f8fafc" stroke="#e2e8f0"/>')
    txt(CBX + 20, y + 12, a, 9.5, K, "start", "700")
    txt(CBX + 20, y + 23, b, 8.5, G)
for i, y in enumerate((YS + 29, YS + 103, YS + 177)):
    wire([(232, y), (310, y), (310, CBY + 96 + i * 44), (CBX, CBY + 96 + i * 44)], C, 1.5)
    txt(238, y - 6, f"in[{i}]", 9, C)

# --- 지령 -> 슬로프보상 -> 비교기 -> RS 래치 -> 게이트드라이버
X2 = 760
txt(CBX + CBW + 8, CBY + 112, "out[0]", 9.5, C, "start", "700")
txt(CBX + CBW + 8, CBY + 124, "Ipk*", 9.5, C)
wire([(CBX + CBW, CBY + 140), (X2, CBY + 140)], C, 1.8)
block(X2, CBY + 116, 104, 48, "DAC", ["0 ~ 27.8 A"], C, "#ecfeff")
wire([(X2 + 104, CBY + 140), (X2 + 146, CBY + 140)], C, 1.8)
add(f'<circle cx="{X2+164}" cy="{CBY+140}" r="18" fill="#fff" stroke="{C}" stroke-width="1.7"/>')
txt(X2 + 164, CBY + 146, "&#8722;", 17, C, "middle", "700")
block(X2 + 96, CBY + 208, 140, 46, "슬로프 램프", ["Se = 0.60 x Sf"], C, "#ecfeff")
wire([(X2 + 164, CBY + 208), (X2 + 164, CBY + 158)], C, 1.8)
lines(X2 + 96, CBY + 272, ["Sf = VOR / Lm = 1.91 A/us",
                           "Se = 1.14 A/us  &#8594; &#955; = &#8722;0.41",
                           "(전 듀티영역 무조건 안정)"], 9, G)

X3 = X2 + 216
add(f'<path d="M {X3},{CBY+108} L {X3},{CBY+172} L {X3+54},{CBY+140} Z" '
    f'fill="#fff" stroke="{C}" stroke-width="1.8"/>')
txt(X3 + 13, CBY + 134, "&#8722;", 13, C, "middle")
txt(X3 + 13, CBY + 158, "+", 13, C, "middle")
txt(X3 + 20, CBY + 96, "비교기", 9.5, C, "middle", "700")
wire([(X2 + 182, CBY + 140), (X3, CBY + 124)], C, 1.8)
block(X2 - 20, CBY + 340, 220, 48, "CT1 버든 + LEB", ["10 &#937;,  리딩엣지 블랭킹 200 ns"], C, "#ecfeff")
wire([(X2 + 200, CBY + 364), (X3 - 24, CBY + 364), (X3 - 24, CBY + 156), (X3, CBY + 156)], C, 1.8)
lines(X2 - 20, CBY + 404, ["OCP 비교기(18.9 A)는 이 raw 센스에 별도로 건다.",
                           "보상램프가 섞인 신호로 OCP 를 걸면 저입력 전부하에 도달하지 못한다."],
      9, R)

X4 = X3 + 96
block(X4, CBY + 106, 96, 78, "RS 래치", ["R / S"], C, "#ecfeff")
wire([(X3 + 54, CBY + 140), (X4, CBY + 128)], C, 1.8)
block(X4 - 104, CBY + 214, 100, 46, "클록 100 kHz", ["Dmax 0.78"], C, "#ecfeff")
wire([(X4 - 54, CBY + 214), (X4 - 54, CBY + 166), (X4, CBY + 166)], C, 1.8)

X5 = X4 + 158
block(X5, CBY + 92, 178, 106, "하프브리지 게이트드라이버",
      ["HO / LO + 부트스트랩", "적응 데드타임 100 ~ 200 ns"], C, "#ecfeff")
wire([(X4 + 96, CBY + 145), (X5, CBY + 145)], C, 1.8)
wire([(X5 + 178, CBY + 120), (X5 + 218, CBY + 120)], C, 1.8)
wire([(X5 + 178, CBY + 170), (X5 + 218, CBY + 170)], C, 1.8)
txt(X5 + 224, CBY + 116, "&#8594; Q2 게이트  (HO, SW 기준)", 9.5, C)
txt(X5 + 224, CBY + 166, "&#8594; Q1 게이트  (LO, PGND 기준)", 9.5, C)
lines(X5, CBY + 228, ["* 2차 바이어스 : T1 보조권선 4 T &#8594; 22.2 V &#8594; LDO 12 V",
                      "* 스위칭 100 kHz / 제어루프 25 kHz / MPPT 2 ms"], 9, G)

add("</svg>")
out = "docs/flyback-150w-400v/schematic-psim.svg"
open(out, "w", encoding="utf-8").write("\n".join(p))
print("wrote", out)
