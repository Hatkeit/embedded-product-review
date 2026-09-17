#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PV 보조전원 8 W 플라이백 - PSIM 심볼 회로도 생성기 (Rev.D : LM5156H 핀 단위 주변회로)."""

W, H = 1820, 1560
K, B, C, R, G, V, O = ("#0f172a", "#1d4ed8", "#0891b2", "#dc2626",
                       "#64748b", "#7c3aed", "#b45309")
p = []
add = p.append
esc = lambda s: str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def wire(pts, col=K, w=1.8, dash=None):
    d = " ".join(f"{x},{y}" for x, y in pts)
    add(f'<polyline points="{d}" fill="none" stroke="{col}" stroke-width="{w}"'
        + (f' stroke-dasharray="{dash}"' if dash else "") + '/>')


def dot(x, y, col=K):
    add(f'<circle cx="{x}" cy="{y}" r="3.3" fill="{col}"/>')


def txt(x, y, s, sz=11, col=K, an="start", wt="400"):
    add(f'<text x="{x}" y="{y}" font-size="{sz}" fill="{col}" text-anchor="{an}" '
        f'font-weight="{wt}">{esc(s)}</text>')


def lines(x, y, rows, sz=9, col=G, an="start", lh=12):
    for i, s in enumerate(rows):
        txt(x, y + i * lh, s, sz, col, an)


def block(x, y, w, h, title, sub=(), col=K, fill="#fff"):
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{fill}" '
        f'stroke="{col}" stroke-width="1.6"/>')
    sub = list(sub)
    y0 = y + h / 2 - (14 + len(sub) * 12) / 2 + 11
    txt(x + w / 2, y0, title, 11.5, K, "middle", "700")
    lines(x + w / 2, y0 + 15, sub, 9, G, "middle")


def res_v(x, y, h, lab=None, col=K, side=1):
    add(f'<rect x="{x-6}" y="{y}" width="12" height="{h}" fill="#fff" stroke="{col}" stroke-width="1.5"/>')
    if lab:
        txt(x + side * 12, y + h / 2 + 4, lab, 9, K, "start" if side > 0 else "end")


def res_h(x, y, w, lab=None, col=K, above=True):
    add(f'<rect x="{x}" y="{y-6}" width="{w}" height="12" fill="#fff" stroke="{col}" stroke-width="1.5"/>')
    if lab:
        txt(x + w / 2, y - 11 if above else y + 20, lab, 9, K, "middle")


def cap_v(x, y, lab=None, col=K, side=1):
    add(f'<line x1="{x-12}" y1="{y}" x2="{x+12}" y2="{y}" stroke="{col}" stroke-width="2.4"/>')
    add(f'<line x1="{x-12}" y1="{y+9}" x2="{x+12}" y2="{y+9}" stroke="{col}" stroke-width="2.4"/>')
    if lab:
        txt(x + side * 17, y + 8, lab, 9, K, "start" if side > 0 else "end")


def cap_h(x, y, lab=None, col=K):
    add(f'<line x1="{x}" y1="{y-12}" x2="{x}" y2="{y+12}" stroke="{col}" stroke-width="2.4"/>')
    add(f'<line x1="{x+9}" y1="{y-12}" x2="{x+9}" y2="{y+12}" stroke="{col}" stroke-width="2.4"/>')
    if lab:
        txt(x + 4, y - 17, lab, 9, K, "middle")


def coil_v(x, y, n=4, r=8, side=1, col=K):
    add(f'<path d="M {x},{y} ' + " ".join(
        f"a {r},{r} 0 0 {1 if side>0 else 0} 0,{2*r}" for _ in range(n)) +
        f'" fill="none" stroke="{col}" stroke-width="1.9"/>')


def mosfet(x, y, col=K):
    """(x,y)=소스, 드레인은 y-44, 게이트 단자는 (x-38, y-22)"""
    for a in (f'<line x1="{x}" y1="{y}" x2="{x}" y2="{y-13}" stroke="{col}" stroke-width="1.7"/>',
              f'<line x1="{x-14}" y1="{y-13}" x2="{x+14}" y2="{y-13}" stroke="{col}" stroke-width="1.7"/>',
              f'<line x1="{x-14}" y1="{y-13}" x2="{x-14}" y2="{y-31}" stroke="{col}" stroke-width="1.7"/>',
              f'<line x1="{x-14}" y1="{y-31}" x2="{x+14}" y2="{y-31}" stroke="{col}" stroke-width="1.7"/>',
              f'<line x1="{x}" y1="{y-31}" x2="{x}" y2="{y-44}" stroke="{col}" stroke-width="1.7"/>',
              f'<line x1="{x-22}" y1="{y-10}" x2="{x-22}" y2="{y-34}" stroke="{col}" stroke-width="2.3"/>',
              f'<line x1="{x-22}" y1="{y-22}" x2="{x-38}" y2="{y-22}" stroke="{col}" stroke-width="1.7"/>',
              f'<path d="M {x+8},{y-13} L {x+8},{y-23} L {x+15},{y-18} Z" fill="{col}"/>'):
        add(a)


def diode_h(x, y, col=K, flip=False):
    """flip=False : 애노드 x -> 캐소드 x+20 (전류 오른쪽).  flip=True : 캐소드 x, 애노드 x+20"""
    if flip:
        add(f'<path d="M {x+20},{y-10} L {x+20},{y+10} L {x},{y} Z" fill="#fff" stroke="{col}" stroke-width="1.6"/>')
        add(f'<line x1="{x}" y1="{y-10}" x2="{x}" y2="{y+10}" stroke="{col}" stroke-width="2.4"/>')
    else:
        add(f'<path d="M {x},{y-10} L {x},{y+10} L {x+20},{y} Z" fill="#fff" stroke="{col}" stroke-width="1.6"/>')
        add(f'<line x1="{x+20}" y1="{y-10}" x2="{x+20}" y2="{y+10}" stroke="{col}" stroke-width="2.4"/>')


def gnd(x, y, lab=None, col=K, sz=1.0):
    add(f'<line x1="{x-13*sz}" y1="{y}" x2="{x+13*sz}" y2="{y}" stroke="{col}" stroke-width="2.2"/>')
    add(f'<line x1="{x-8*sz}" y1="{y+5*sz}" x2="{x+8*sz}" y2="{y+5*sz}" stroke="{col}" stroke-width="2"/>')
    add(f'<line x1="{x-3*sz}" y1="{y+10*sz}" x2="{x+3*sz}" y2="{y+10*sz}" stroke="{col}" stroke-width="2"/>')
    if lab:
        txt(x, y + 23, lab, 9, G, "middle")


def netlab(x, y, s, col=K, an="start"):
    """PSIM 네트 라벨 (깃발)"""
    w = 7 * len(s) + 10
    if an == "start":
        add(f'<path d="M {x},{y} L {x+8},{y-8} L {x+w},{y-8} L {x+w},{y+8} L {x+8},{y+8} Z" '
            f'fill="#fff" stroke="{col}" stroke-width="1.2"/>')
        txt(x + 11, y + 4, s, 9, col, "start", "700")
    else:
        add(f'<path d="M {x},{y} L {x-8},{y-8} L {x-w},{y-8} L {x-w},{y+8} L {x-8},{y+8} Z" '
            f'fill="#fff" stroke="{col}" stroke-width="1.2"/>')
        txt(x - 11, y + 4, s, 9, col, "end", "700")


# ================================================================= 캔버스
add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
    f'font-family="ui-monospace,Menlo,Consolas,monospace">')
add(f'<rect width="{W}" height="{H}" fill="#fff"/>')
txt(24, 34, "PV 보조전원 8 W 다출력 플라이백   U1 = TI LM5156H (HTSSOP-14) + 외부 MOSFET, DCM 100 kHz",
    17, K, "start", "800")
txt(24, 54, "PS-AUX-8W Rev.D  |  NCP1031DR2(U600) 대체  |  입력 PV 18~50 V  |  출력 VCC_3V3 5 W / VDDA_3V3 1 W / "
            "VCC_5V0 1 W / VCC_12V0 1 W  |  calc_aux.py 16/16 · calc_lm5156.py 19/19 PASS, 효율 69.8 %", 10.5, G)

# ================================================================= A. 플라이백 + 컨트롤러
PA, PAH = 72, 880
add(f'<rect x="24" y="{PA}" width="{W-48}" height="{PAH}" rx="10" fill="#fbfcfe" stroke="#cbd5e1"/>')
txt(40, PA + 22, "A.  플라이백 전력단 + LM5156H 주변회로   (DCM, T1 EFD20  Np:Ns1:Ns2:Naux = 15 : 3 : 8 : 4)",
    13, K, "start", "800")
add('<g transform="translate(60,0)">')

RAIL, PGND, SWY = 252, 850, 328
X_IN, X_CIN, X_CL, X_T, X_CORE, X_S, X_D = 226, 284, 500, 690, 778, 840, 960
UX0, UX1, UY0, UY1 = 300, 520, 330, 790          # U1 박스

# ---- 입력
block(X_IN - 170, RAIL - 32, 104, 64, "PV 입력", ["18 ~ 50 V", "0.64 A @18 V"], B, "#eff6ff")
wire([(X_IN - 66, RAIL), (X_T, RAIL)], B, 2.2)
wire([(X_IN - 66, RAIL + 24), (X_IN - 50, RAIL + 24), (X_IN - 50, RAIL + 32)], B, 2.2)
gnd(X_IN - 50, RAIL + 32, None, B, 0.8)
dot(X_CIN, RAIL, B)
wire([(X_CIN, RAIL), (X_CIN, RAIL + 58)], B, 2.2)
cap_v(X_CIN, RAIL + 58, None, B)
txt(X_CIN + 12, RAIL + 66, "Cin 22 uF/100 V x2", 9, K, "start")
wire([(X_CIN, RAIL + 67), (X_CIN, RAIL + 76)], B, 2.2)
gnd(X_CIN, RAIL + 76, None, B, 0.8)

# ---- RCD 클램프
dot(X_CL, RAIL, R)
wire([(X_CL, RAIL), (X_CL, RAIL - 62)], R, 1.8)
res_h(X_CL - 60, RAIL - 62, 44, "R_cl 4.3 k / 2 W", R)
cap_h(X_CL + 30, RAIL - 62, None, R)
txt(X_CL + 44, RAIL - 46, "C_cl 22 nF/100 V", 9, K, "start")
wire([(X_CL - 16, RAIL - 62), (X_CL, RAIL - 62)], R, 1.8)
wire([(X_CL, RAIL - 62), (X_CL + 30, RAIL - 62)], R, 1.8)
wire([(X_CL - 60, RAIL - 62), (X_CL - 90, RAIL - 62), (X_CL - 90, RAIL)], R, 1.8)
dot(X_CL - 90, RAIL, R)
wire([(X_CL + 39, RAIL - 62), (X_CL + 70, RAIL - 62), (X_CL + 70, RAIL - 100)], R, 1.8)
diode_h(X_CL + 70, RAIL - 100, R, True)
wire([(X_CL + 90, RAIL - 100), (X_T, RAIL - 100), (X_T, RAIL + 4)], R, 1.8)
txt(X_CL + 118, RAIL - 108, "D_cl 200 V 초고속", 9, R, "start")
txt(X_CL - 150, RAIL - 134, "RCD 클램프 : tau = R_cl·C_cl = 95 us (9.5 T), 손실 0.62 W (Llk 2 %)", 9.5, R, "start", "700")

# ---- 트랜스포머 T1
dot(X_T, RAIL, B)
coil_v(X_T, RAIL + 6, 4, 8, -1, B)
add(f'<circle cx="{X_T-12}" cy="{RAIL+13}" r="3" fill="{K}"/>')
txt(X_T - 22, RAIL + 44, "Np 15", 9.5, K, "end", "700")
txt(X_T - 22, RAIL + 56, "Lp 40 uH +-5 %", 8.5, G, "end")
wire([(X_T, RAIL + 70), (X_T, SWY + 16)], B, 2.2)
for cx in (X_CORE, X_CORE + 9):
    add(f'<line x1="{cx}" y1="{RAIL}" x2="{cx}" y2="{RAIL+300}" stroke="{G}" stroke-width="2.8"/>')
txt(X_CORE + 5, RAIL - 10, "EFD20 / PC44", 9, G, "middle")

# ---- Q1 + Rcs
mosfet(X_T, SWY + 60, B)
txt(712, SWY + 12, "Q1 150 V", 9, K, "start", "700")
txt(712, SWY + 24, "Rds 75 mOhm", 8.5, K, "start")
txt(712, SWY + 36, "Ipk 2.38 A", 8.5, G, "start")
txt(712, SWY + 48, "Vds 112 V", 8.5, G, "start")
res_v(X_T, SWY + 60, 34, None, B)
txt(X_T + 12, SWY + 82, "Rcs 33 mOhm", 9, K, "start", "700")
txt(X_T + 12, SWY + 94, "I_CL 2.8~3.2 A", 8.5, G, "start")
wire([(X_T, SWY + 94), (X_T, SWY + 112), (X_T + 30, SWY + 112), (X_T + 30, PGND)], B, 2.2)
gnd(X_T + 30, PGND, "PGND (스타점)", B)

# ---- Naux (1차 GND 기준, VCC 급전)
NA = 480
coil_v(X_T, NA, 3, 8, -1, O)
add(f'<circle cx="{X_T-12}" cy="{NA+7}" r="3" fill="{O}"/>')
txt(X_T - 18, NA + 46, "Naux 4", 9.5, O, "end", "700")
txt(X_T - 18, NA + 58, "7.9 V (무부하 <= 14 V)", 8.5, G, "end")
wire([(X_T, NA + 48), (X_T, NA + 66), (X_T + 30, NA + 66)], O, 1.7)
dot(X_T + 30, NA + 66, O)

# ---- Ns1 / Ns2
coil_v(X_S, RAIL + 6, 3, 8, 1, C)
add(f'<circle cx="{X_S+12}" cy="{RAIL+48}" r="3" fill="{K}"/>')
txt(X_S + 22, RAIL + 30, "Ns1 3", 9.5, K, "start", "700")
coil_v(X_S, RAIL + 130, 4, 8, 1, V)
add(f'<circle cx="{X_S+12}" cy="{RAIL+194}" r="3" fill="{K}"/>')
txt(X_S + 22, RAIL + 160, "Ns2 8", 9.5, K, "start", "700")

SG = RAIL + 300
wire([(X_S, RAIL + 6), (X_S, RAIL - 40), (X_D, RAIL - 40)], C, 2.2)
diode_h(X_D, RAIL - 40, C)
wire([(X_D + 20, RAIL - 40), (X_D + 250, RAIL - 40)], C, 2.2)
wire([(X_S, RAIL + 54), (X_S - 30, RAIL + 54), (X_S - 30, SG), (X_D + 300, SG)], C, 2.2)
txt(X_D + 10, RAIL - 54, "D1 40 V/5 A SBD", 9.5, K, "middle", "700")
cap_v(X_D + 70, RAIL - 12, None, C)
txt(X_D + 88, RAIL - 4, "Co1 22 uF x3 (X7R)", 9, K, "start")
wire([(X_D + 70, RAIL - 40), (X_D + 70, RAIL - 12)], C, 2.2)
wire([(X_D + 70, RAIL - 3), (X_D + 70, SG)], C, 2.2)
dot(X_D + 70, RAIL - 40, C); dot(X_D + 70, SG, C)
cap_v(X_D + 70, RAIL + 30, None, C)
txt(X_D + 88, RAIL + 38, "Co1b 100 uF/10 V 폴리머 (Rev.D)", 9, K, "start")
txt(X_D + 88, RAIL + 50, "ESR 30 mOhm, 부하스텝 언더슈트 3.6 %", 8.5, G, "start")
txt(X_D + 256, RAIL - 44, "S1  6.0 V / 8.1 W", 11, C, "start", "700")
netlab(X_D + 260, RAIL - 26, "S1", C)
txt(X_D + 300, RAIL - 22, "-> R_FBT", 9, G)

wire([(X_S, RAIL + 130), (X_S, RAIL + 104), (X_D, RAIL + 104)], V, 2.2)
diode_h(X_D, RAIL + 104, V)
wire([(X_D + 20, RAIL + 104), (X_D + 250, RAIL + 104)], V, 2.2)
wire([(X_S, RAIL + 194), (X_S - 30, RAIL + 194)], V, 2.2)
dot(X_S - 30, RAIL + 194, V)
txt(X_D + 10, RAIL + 90, "D2 60 V SBD", 9.5, K, "middle", "700")
cap_v(X_D + 70, RAIL + 132, None, V)
txt(X_D + 52, RAIL + 140, "Co2 10 uF/50 V", 9, K, "end")
wire([(X_D + 70, RAIL + 104), (X_D + 70, RAIL + 132)], V, 2.2)
wire([(X_D + 70, RAIL + 141), (X_D + 70, SG)], V, 2.2)
dot(X_D + 70, RAIL + 104, V); dot(X_D + 70, SG, V)
txt(X_D + 256, RAIL + 100, "S2  16.6 V / 1.2 W", 11, V, "start", "700")
txt(X_D + 256, RAIL + 113, "교차조정 14.1 ~ 19.1 V", 9, G)
txt(X_D + 256, RAIL + 126, "Ns2 만 절연 (HGND 기준)", 9, R, "start", "700")
res_v(X_D + 150, RAIL + 132, 40, "R_pre 1.7 k / 0.25 W", V)
wire([(X_D + 150, RAIL + 104), (X_D + 150, RAIL + 132)], V, 2.2)
wire([(X_D + 150, RAIL + 172), (X_D + 150, SG)], V, 2.2)
dot(X_D + 150, RAIL + 104, V); dot(X_D + 150, SG, V)
txt(X_D + 150, RAIL + 190, "무부하 과전압 방지", 8.5, R, "middle")
gnd(X_D + 300, SG, "SGND (= PGND, 공통)", C)

# ================================================================= U1 LM5156H
add(f'<rect x="{UX0}" y="{UY0}" width="{UX1-UX0}" height="{UY1-UY0}" rx="4" fill="#eff6ff" '
    f'stroke="{B}" stroke-width="2"/>')
txt((UX0 + UX1) / 2, UY0 + 20, "U1  LM5156H", 12.5, B, "middle", "800")
txt((UX0 + UX1) / 2, UY0 + 34, "HTSSOP-14 (PWP), EP -> AGND", 8.5, G, "middle")
txt((UX0 + UX1) / 2, UY0 + 46, "피크전류모드, VREF 1.0 V, gm 2 mA/V", 8.5, G, "middle")
LP = [("BIAS", 1, 350), ("EN/UVLO", 14, 410), ("RT", 12, 470), ("SS", 11, 530),
      ("FB", 10, 590), ("COMP", 8, 650), ("DITHOFF", 9, 710), ("PGOOD", 13, 760)]
RP = [("GATE", 4, 366), ("CS", 7, 420), ("VCC", 3, 480), ("PGND", 5, 560), ("AGND", 6, 640)]
for nm, no, y in LP:
    wire([(UX0 - 16, y), (UX0, y)], B, 1.7)
    txt(UX0 + 6, y + 4, nm, 9.5, K, "start", "700")
    txt(UX0 - 20, y - 6, str(no), 7.5, G, "end")
for nm, no, y in RP:
    wire([(UX1, y), (UX1 + 16, y)], B, 1.7)
    txt(UX1 - 6, y + 4, nm, 9.5, K, "end", "700")
    txt(UX1 + 20, y - 6, str(no), 7.5, G, "start")

# ---- 우측 핀
# GATE -> R_G -> Q1 게이트 (X_T-38, SWY+38)
GY = 366
wire([(UX1 + 16, GY), (560, GY)], B, 1.7)
res_h(560, GY, 44, "R_G 10 Ohm", B)
wire([(604, GY), (X_T - 38, GY)], B, 1.7)
# CS <- R_F <- Q1 소스 노드 (X_T, SWY+60)
CY = 420
wire([(X_T, SWY + 60), (640, SWY + 60), (640, CY), (624, CY)], B, 1.7)
dot(X_T, SWY + 60, B)
res_h(580, CY, 44, "R_F 100 Ohm", B)
wire([(580, CY), (UX1 + 16, CY)], B, 1.7)
dot(556, CY, B)
wire([(556, CY), (556, CY + 8)], B, 1.7)
cap_v(556, CY + 8, None, B)
wire([(556, CY + 17), (556, CY + 30)], B, 1.7)
gnd(556, CY + 30, None, B, 0.8)
txt(566, CY + 20, "C_F 470 pF", 8.5, K, "start")
txt(566, CY + 32, "tau 47 ns", 8.5, G, "start")
# VCC <- C_VCC, D_aux <- Naux
VY = 480
wire([(UX1 + 16, VY), (X_T, VY)], O, 1.7)
dot(600, VY, O)
wire([(600, VY), (600, VY + 10)], O, 1.7)
cap_v(600, VY + 10, None, O)
wire([(600, VY + 19), (600, VY + 32)], O, 1.7)
gnd(600, VY + 32, None, O, 0.8)
txt(592, VY + 16, "C_VCC 2.2 uF", 8.5, K, "end")
diode_h(640, VY, O, True)
txt(650, VY - 14, "D_aux 100 V", 8.5, O, "middle")
txt(560, VY - 6, "VCC 7.9 V", 8.5, O, "start", "700")
# PGND -> Rcs 하단 스타점
wire([(UX1 + 16, 560), (X_T + 30, 560)], B, 1.7)
dot(X_T + 30, 560, B)
txt(560, 556, "PGND : Rcs 하단에 켈빈 접속", 8.5, G, "start")
# AGND
wire([(UX1 + 16, 640), (580, 640)], B, 1.7)
gnd(580, 640, None, B)
txt(600, 646, "AGND = EP 평면", 8.5, G, "start")
txt(600, 658, "PGND 와 1점 접속", 8.5, G, "start")

# ---- 좌측 핀
AX = 60                                   # AGND 버스 x
# BIAS <- Vin (R_BIAS / C_BIAS)
VIN_TAP, FY = 330, 304
dot(VIN_TAP, RAIL, B)
wire([(VIN_TAP, RAIL), (VIN_TAP, FY), (100, FY)], B, 1.7)
txt(338, 296, "Vin (BIAS 3.5~60 V, abs 65 V)", 8.5, G, "start")
dot(250, FY, B)
wire([(250, FY), (250, 306)], B, 1.7)
res_v(250, 306, 30, None, B)
txt(238, 326, "R_BIAS 10 Ohm", 9, K, "end")
wire([(250, 336), (250, 350), (UX0 - 16, 350)], B, 1.7)
dot(250, 350, B)
wire([(250, 350), (220, 350), (220, 358)], B, 1.7)
cap_v(220, 358, None, B)
wire([(220, 367), (220, 380)], B, 1.7)
gnd(220, 380, None, B, 0.8)
txt(232, 364, "C_BIAS 1 uF", 8.5, K, "start")
txt(232, 376, "tau 10 us", 8.5, G, "start")
# UVLO 분압 (Vin 감지는 R_BIAS 앞단 노드에서)
wire([(100, FY), (100, 352)], B, 1.7)
res_v(100, 352, 30, None, B)
txt(88, 372, "R_UVLOT 294 k", 9, K, "end")
wire([(100, 382), (100, 410), (UX0 - 16, 410)], B, 1.7)
dot(100, 410, B)
res_v(100, 418, 30, None, B)
txt(88, 438, "R_UVLOB 30.1 k", 9, K, "end")
wire([(100, 448), (100, 456)], B, 1.7)
gnd(100, 456, None, B, 0.8)
dot(170, 410, B)
wire([(170, 410), (170, 418)], B, 1.7)
cap_v(170, 418, None, B)
wire([(170, 427), (170, 440)], B, 1.7)
gnd(170, 440, None, B, 0.8)
txt(186, 428, "C_UVLO 10 nF", 8.5, K, "start")
txt(186, 440, "tau 273 us", 8.5, G, "start")
txt(112, 346, "기동 16.2 / 정지 14.1 V", 8.5, R, "start", "700")
txt(112, 358, "히스테리시스 5 uA", 8.5, G, "start")
# RT
wire([(UX0 - 16, 470), (230, 470), (230, 478)], B, 1.7)
res_v(230, 478, 30, None, B)
wire([(230, 508), (230, 516)], B, 1.7)
gnd(230, 516, None, B, 0.8)
txt(218, 490, "RT 220 k 1 %", 9, K, "end")
txt(218, 502, "fsw 100 kHz (T 10 us)", 8.5, G, "end")
# SS
wire([(UX0 - 16, 530), (230, 530), (230, 540)], B, 1.7)
cap_v(230, 540, None, B)
wire([(230, 549), (230, 566)], B, 1.7)
gnd(230, 566, None, B, 0.8)
txt(214, 522, "C_SS 100 nF, t_SS 10 ms", 9, K, "end")
txt(214, 534, "= C x 1 V / 10 uA", 8.5, G, "end")
# FB 분압 (S1 네트라벨)
netlab(150, 550, "S1", C, "end")
wire([(150, 550), (150, 562)], C, 1.7)
res_v(150, 562, 26, None, C)
txt(138, 580, "R_FBT 49.9 k 1 %", 9, K, "end")
wire([(150, 588), (150, 590), (UX0 - 16, 590)], C, 1.7)
dot(150, 590, C)
res_v(150, 596, 26, None, C)
txt(138, 614, "R_FBB 10 k 1 %", 9, K, "end")
wire([(150, 622), (150, 630)], C, 1.7)
gnd(150, 630, None, C, 0.8)
txt(138, 646, "FB 1.0 V -> S1 5.99 V", 8.5, C, "end", "700")
txt(138, 658, "OVP 6.6 V / PGOOD UV 5.4 V", 8.5, G, "end")
# COMP : R_COMP + C_COMP 직렬, C_HF 병렬
wire([(UX0 - 16, 650), (200, 650), (200, 656)], B, 1.7)
dot(200, 650, B)
res_v(200, 656, 26, None, B)
txt(212, 674, "R_COMP 2.49 k", 8.5, K, "start")
wire([(200, 682), (200, 690)], B, 1.7)
cap_v(200, 690, None, B)
txt(212, 698, "C_COMP 240 nF", 8.5, K, "start")
wire([(200, 699), (200, 712)], B, 1.7)
gnd(200, 712, None, B, 0.8)
wire([(200, 650), (150, 650), (150, 660)], B, 1.7)
cap_v(150, 660, None, B)
wire([(150, 669), (150, 682)], B, 1.7)
gnd(150, 682, None, B, 0.8)
txt(132, 668, "C_HF 1.3 nF", 8.5, K, "end")
txt(132, 680, "z 266 Hz / p 49 kHz", 8, G, "end")
txt(132, 692, "fc 4.5 kHz, PM 73 deg", 8, G, "end")
# DITHOFF
wire([(UX0 - 16, 710), (262, 710)], B, 1.7)
netlab(262, 710, "VCC", O, "end")
txt(196, 714, "스펙트럼확산 OFF", 8.5, G, "end")
txt(196, 726, "(ON 이면 fsw +15.6 % -> DCM 여유 소진)", 8.0, G, "end")
# PGOOD
wire([(UX0 - 16, 760), (230, 760)], B, 1.7)
dot(230, 760, B)
res_h(160, 760, 44, None, B)
txt(182, 749, "R_PG 24.9 k", 9, K, "middle")
wire([(160, 760), (130, 760)], B, 1.7)
netlab(130, 760, "VCC_3V3", C, "end")
wire([(230, 760), (230, 782)], B, 1.7)
netlab(230, 782, "nPGOOD -> MCU", G, "end")
txt(60, 800, "좌측 접지 = AGND (C_BIAS 만 PGND)", 8.5, G, "start", "700")
txt(60, 812, "PGOOD : FB > 0.9 V (S1 5.4 V) 후 25 us 디글리치 -> 오픈드레인 해제", 8.0, G, "start")
txt(60, 824, "RSL = 0 Ohm : DCM 설계라 슬로프 추가 불요, 전류제한이 듀티에 무관", 8.0, G, "start")

# ================================================================= 우측 정보 : 시정수 / 타이밍
IX, IY = 1330, PA + 44
block(IX, IY, 396, 400, "", (), B, "#eff6ff")
txt(IX + 198, IY + 22, "시정수 · 타이밍 (calc_lm5156.py)", 12, B, "middle", "800")
lines(IX + 16, IY + 44, [
    "스위칭 주기 T = 1/fsw            10.0 us   RT 220 k",
    "정격 t_on @18 V / @50 V      5.35 / 1.93 us",
    "t_off (2차 도통, Lp·Ipk/VOR)      2.99 us   0.83 T DCM",
    "CS 필터 R_F·C_F                    47 ns   CL 무효 < 94 ns",
    "RCD 클램프 R_cl·C_cl               95 us   9.5 T",
    "BIAS 필터 R_BIAS·C_BIAS            10 us",
    "UVLO 필터 (R_T||R_B)·C_UVLO       273 us   채터링 방지",
    "내부 기동 지연 (UVLO > 1.5 V)       65 us   DS 9.3.1",
    "VCC UV 후 SS 시작 지연             50 us   DS 9.3.3",
    "소프트스타트 t_SS                  10 ms   C_SS 100 nF",
    "PGOOD 디글리치                     25 us   내부",
    "셧다운 지연 (UVLO < 0.52 V)        35 us   내부",
    "보상 영점 R_COMP·C_COMP           598 us   266 Hz",
    "보상 극점 R_COMP·C_HF             3.2 us   49 kHz",
    "플랜트 극점 C_out·(G_conv+G_load)  304 us   523 Hz",
    "",
    "기동 순서 : Vin > 16.2 V -> BIAS -> 내부 VCC 6.85 V",
    "  -> 65 us -> SS 램프 10 ms -> S1 5.4 V PGOOD",
    "  -> POL 기동 -> Naux 7.9 V 가 VCC 인계",
    "",
    "시뮬 : 기동 9.9 ms, 오버슈트 +0.3 %, SS 후 CL 0 회,",
    "  부하 50->100 % 언더슈트 3.6 %, 정착 470 us",
], 9, K, "start", 15)

block(IX, IY + 416, 396, 330, "", (), R, "#fef2f2")
txt(IX + 198, IY + 438, "데이터시트로 확정된 항목 (SNVSBV2)", 12, R, "middle", "800")
lines(IX + 16, IY + 460, [
    "DMAX @100 kHz  0.90 min (0.93 typ)  >>  설계 D 0.535",
    "CS 문턱 100 mV +-7 %  -> Rcs 33 mOhm, I_CL 2.82~3.24 A",
    "  (Rev.C 의 42 mOhm 은 전부하 Ipk 2.38 A 가 I_CL(min)",
    "   2.21 A 를 넘어 전력 부족 -> 33 mOhm 으로 정정)",
    "BIAS 3.5~60 V (abs 65)  ->  PV 50 V 직결, 여유 10 V",
    "VCC 외부급전 > 6.85 V, <= 16 V  ->  Naux 6 T(13 V) 는",
    "  무부하 23 V 로 abs 18 V 초과 -> 4 T (7.9 V) 로 정정",
    "슬로프 : 고정 40 mV/T + RSL(<= 2 k).  CCM 에서 필요한",
    "  15.8 mV/us 를 못 만든다 -> DCM 유지가 필수 조건",
    "  -> Lp 공차 +-5 %, DITHOFF = VCC (확산 OFF)",
    "gm 2 mA/V, VREF 1.0 V, COMP 클램프 1.15~2.5 V",
    "  전부하 V_COMP 1.90 V, 전류제한 2.05 V < 2.5 V",
    "히컵 과부하 보호는 LM51561H 에만 있음 (동일 핀)",
    "  -> 3.3 V 레일 단락 보호가 필요하면 LM51561H",
    "",
    "미확정 (변경 없음) : Ns2 절연 등급 (HGND 기준)",
], 9, K, "start", 15)

add('</g>')

# ================================================================= B. POL + 손실
PB = PA + PAH + 20
add(f'<rect x="24" y="{PB}" width="{W-48}" height="{H-PB-24}" rx="10" fill="#fbfcfe" stroke="#cbd5e1"/>')
txt(40, PB + 22, "B.  POL 후단 레귤레이터 / GND / 손실", 13, K, "start", "800")
YB = PB + 44
txt(70, YB + 6, "S1 6.0 V", 11.5, C, "start", "700")
wire([(70, YB + 16), (250, YB + 16), (250, YB + 232)], C, 2.2)
for y, t1, s1, out, col in (
        (YB + 26, "동기 벅 #1", ["6.0 V -> 3.3 V / 1.52 A", "1 MHz, eff 93 %"], "VCC_3V3   5 W", C),
        (YB + 114, "동기 벅 #2", ["6.0 V -> 5.0 V / 0.50 A", "1 MHz, eff 92 %"], "VCC_5V0   1 W", C)):
    block(300, y, 210, 66, t1, s1, col, "#ecfeff")
    wire([(250, y + 33), (300, y + 33)], col, 2.2)
    wire([(510, y + 33), (610, y + 33)], col, 2.2)
    txt(616, y + 37, out, 11, K, "start", "700")
dot(250, YB + 59, C); dot(250, YB + 147, C)
block(300, YB + 202, 210, 66, "LDO  5.0 -> 3.3 V",
      ["0.303 A, 손실 0.52 W", "SOT-223 이상 (Tj 93 C)"], C, "#ecfeff")
wire([(610, YB + 147), (770, YB + 147), (770, YB + 235), (300, YB + 235)], C, 2.2)
dot(770, YB + 147, C)
wire([(510, YB + 235), (610, YB + 235)], C, 2.2)
txt(616, YB + 239, "VDDA_3V3  1 W", 11, K, "start", "700")

txt(70, YB + 306, "S2 16.6 V", 11.5, V, "start", "700")
wire([(70, YB + 316), (300, YB + 316)], V, 2.2)
block(300, YB + 286, 210, 66, "LDO  16.6 -> 12 V",
      ["83 mA, 손실 0.38~0.59 W", "입력정격 >= 36 V (무부하)"], V, "#faf5ff")
wire([(510, YB + 319), (610, YB + 319)], V, 2.2)
txt(616, YB + 323, "VCC_12V0  1 W", 11, K, "start", "700")
lines(70, YB + 372, [
    "* SOT-23 LDO 는 두 레일 모두 불가 (Tj 189 C / 208 C).  SOT-223 + 방열동박 필수.",
    "* VDDA 는 아날로그 전용 별도 LDO + 스타그라운드.  3.3 V 에서 페라이트 분기하면 0.52 W 절약되나 노이즈 공유.",
    "* PGOOD(U1) 이 해제된 뒤 POL 을 인에이블하면 기동 중 S1 이 전류제한에 걸리지 않는다 (시뮬 확인).",
], 9, G)

block(880, YB - 4, 400, 196, "", (), C, "#ecfeff")
txt(1080, YB + 20, "GND 구성 - 확정 (Rev.B)", 12.5, C, "middle", "800")
lines(896, YB + 40, [
    "같은 기준의 부하는 공통 GND 사용.",
    "  VCC_3V3 / VDDA_3V3 / VCC_5V0  -> 공통 GND",
    "  VCC_12V0 (Ns2)                -> 독립 / 플로팅",
    "",
    "LM5156H 접지 (DS 12.1) :",
    "  PGND : Rcs 하단 - C_VCC - C_BIAS - Cin 리턴",
    "  AGND : R_UVLOB, RT, C_SS, R_FBB, 보상망, EP",
    "  두 접지는 IC 바로 아래에서 1점 접속",
    "  CS 는 Rcs 상단 켈빈, 게이트 루프와 분리",
    "  (100 mV 문턱 -> 레이아웃 노이즈 민감)",
], 9.5, K)
block(880, YB + 208, 400, 150, "", (), R, "#fef2f2")
txt(1080, YB + 230, "PDF(01 DC POWER) 대비 변경", 12, R, "middle", "800")
lines(896, YB + 248, [
    "U600 NCP1031 (FET 내장)  -> U1 LM5156H + Q1 150 V",
    "R602/R605 UV·OV 분압     -> R_UVLOT/R_UVLOB + C_UVLO",
    "CT 타이밍 커패시터        -> RT 220 k",
    "COMP 보상               -> R_COMP/C_COMP/C_HF (Type-2)",
    "R604/R607 VFB 2.5 V 분압 -> R_FBT/R_FBB (VREF 1.0 V)",
    "T600 3-4 권선 -> D605     -> Naux 4 T -> D_aux -> VCC",
    "T600 9-10 (FT-H12V)      -> Ns2 8 T -> D2 -> LDO 12 V",
    "신규 : Rcs·R_F·C_F, R_G, C_SS, PGOOD, DITHOFF, RCD",
], 9.5, K)

block(1320, YB - 4, 370, 362, "", (), G, "#f8fafc")
txt(1505, YB + 20, "손실 배분 (입력 11.47 W)", 12, K, "middle", "800")
lines(1336, YB + 42, [
    "RCD 클램프 (Llk 2 %)         0.62 W",
    "S1 쇼트키 (Vf 0.45 V)        0.61 W",
    "LDO VDDA (5 -> 3.3 V)       0.52 W",
    "동기벅 3.3 V                 0.38 W",
    "트랜스포머 (dT 14 K)           0.33 W",
    "LDO 12 V                    0.33 W",
    "1차 MOSFET (도통+스위칭)        0.32 W",
    "동기벅 5.0 V                 0.22 W",
    "S2 쇼트키 / 컨트롤러            0.12 W",
    "전류센스 Rcs 33 mOhm          0.03 W",
    "──────────────────────────────────",
    "집계 3.47 W  =  입력-출력 3.47 W  (수지 일치)",
    "",
    "전체 효율 69.8 %",
    "",
    "개선 여지 :",
    "  누설 1 % 로      -> -0.31 W",
    "  VDDA 를 3.3 V 에서 페라이트 분기 -> -0.52 W",
    "  12 V 를 LDO 대신 벅으로 -> -0.25 W",
    "  => 약 75 % 까지 가능",
], 9.5, K)

add("</svg>")
out = "docs/aux-supply-8w/schematic-aux.svg"
open(out, "w", encoding="utf-8").write("\n".join(p))
print("wrote", out)
