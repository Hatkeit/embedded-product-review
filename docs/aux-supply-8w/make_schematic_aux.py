#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PV 보조전원 8 W 플라이백 - PSIM 심볼 회로도 생성기."""

W, H = 1720, 1300
K, B, C, R, G, V, O = ("#0f172a", "#1d4ed8", "#0891b2", "#dc2626",
                       "#64748b", "#7c3aed", "#b45309")
p = []
add = p.append
esc = lambda s: str(s).replace("<", "&lt;").replace(">", "&gt;")


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


def res_h(x, y, w, lab=None, col=K):
    add(f'<rect x="{x}" y="{y-6}" width="{w}" height="12" fill="#fff" stroke="{col}" stroke-width="1.5"/>')
    if lab:
        txt(x + w / 2, y - 11, lab, 9, K, "middle")


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
    """(x,y)=소스, 드레인 위"""
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
    if flip:
        add(f'<path d="M {x+20},{y-10} L {x+20},{y+10} L {x},{y} Z" fill="#fff" stroke="{col}" stroke-width="1.6"/>')
        add(f'<line x1="{x}" y1="{y-10}" x2="{x}" y2="{y+10}" stroke="{col}" stroke-width="2.4"/>')
    else:
        add(f'<path d="M {x},{y-10} L {x},{y+10} L {x+20},{y} Z" fill="#fff" stroke="{col}" stroke-width="1.6"/>')
        add(f'<line x1="{x+20}" y1="{y-10}" x2="{x+20}" y2="{y+10}" stroke="{col}" stroke-width="2.4"/>')


def gnd(x, y, lab=None, col=K):
    add(f'<line x1="{x-13}" y1="{y}" x2="{x+13}" y2="{y}" stroke="{col}" stroke-width="2.2"/>')
    add(f'<line x1="{x-8}" y1="{y+5}" x2="{x+8}" y2="{y+5}" stroke="{col}" stroke-width="2"/>')
    add(f'<line x1="{x-3}" y1="{y+10}" x2="{x+3}" y2="{y+10}" stroke="{col}" stroke-width="2"/>')
    if lab:
        txt(x, y + 23, lab, 9, G, "middle")


# ================================================================= 캔버스
add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
    f'font-family="ui-monospace,Menlo,Consolas,monospace">')
add(f'<rect width="{W}" height="{H}" fill="#fff"/>')
txt(24, 34, "PV 보조전원 8 W 다출력 플라이백   외부 컨트롤러 + 외부 MOSFET, DCM 100 kHz", 17, K, "start", "800")
txt(24, 54, "PS-AUX-8W Rev.B  |  입력 PV 18~50 V  |  출력 VCC_3V3 5 W / VDDA_3V3 1 W / "
            "VCC_5V0 1 W / VCC_12V0 1 W  |  calc_aux.py 12/12 PASS, 실측효율 68.6 %", 10.5, G)

# ================================================================= A. 플라이백
PA, PAH = 72, 648
add(f'<rect x="24" y="{PA}" width="{W-48}" height="{PAH}" rx="10" fill="#fbfcfe" stroke="#cbd5e1"/>')
txt(40, PA + 22, "A.  플라이백 전력단   (DCM, Np:Ns1:Ns2:Naux = 15 : 3 : 8 : 6)", 13, K, "start", "800")

RAIL, PGND = 252, 628
X_IN, X_CIN, X_CL, X_T, X_CORE, X_S, X_D = 56, 210, 330, 520, 578, 640, 760

block(X_IN, RAIL - 32, 104, 64, "PV 입력", ["18 ~ 50 V", "0.65 A @18 V"], B, "#eff6ff")
wire([(X_IN + 104, RAIL), (X_T, RAIL)], B, 2.2)
wire([(X_IN + 104, RAIL + 24), (X_IN + 132, RAIL + 24), (X_IN + 132, PGND), (X_T + 40, PGND)], B, 2.2)
dot(X_CIN, RAIL, B)
wire([(X_CIN, RAIL), (X_CIN, RAIL + 58)], B, 2.2)
cap_v(X_CIN, RAIL + 58, "Cin 22 uF/100 V x2", B)
wire([(X_CIN, RAIL + 67), (X_CIN, PGND)], B, 2.2)
dot(X_CIN, PGND, B)

# RCD 클램프
dot(X_CL, RAIL, R)
wire([(X_CL, RAIL), (X_CL, RAIL - 62)], R, 1.8)
res_h(X_CL - 60, RAIL - 62, 44, "R_cl 4.3 k / 2 W", R)
cap_h(X_CL + 30, RAIL - 62, "C_cl 22 nF/100 V", R)
wire([(X_CL - 16, RAIL - 62), (X_CL, RAIL - 62)], R, 1.8)
wire([(X_CL, RAIL - 62), (X_CL + 30, RAIL - 62)], R, 1.8)
wire([(X_CL - 60, RAIL - 62), (X_CL - 90, RAIL - 62), (X_CL - 90, RAIL)], R, 1.8)
dot(X_CL - 90, RAIL, R)
wire([(X_CL + 39, RAIL - 62), (X_CL + 70, RAIL - 62), (X_CL + 70, RAIL - 100)], R, 1.8)
diode_h(X_CL + 70, RAIL - 100, R, True)
wire([(X_CL + 90, RAIL - 100), (X_T, RAIL - 100), (X_T, RAIL + 4)], R, 1.8)
txt(X_CL + 118, RAIL - 100, "D_cl 200 V 초고속", 9, R, "start")
txt(X_CL - 160, RAIL - 134, "RCD 클램프 : 손실 0.62 W (입력의 5.3 %),  누설을 Lp의 1 %로 낮추면 0.31 W",
    9.5, R, "start", "700")

# 트랜스포머 T1
dot(X_T, RAIL, B)
coil_v(X_T, RAIL + 6, 4, 8, -1, B)
add(f'<circle cx="{X_T-12}" cy="{RAIL+13}" r="3" fill="{K}"/>')
txt(X_T - 22, RAIL + 44, "Np 15", 9.5, K, "end", "700")
SWY = RAIL + 76
wire([(X_T, SWY), (X_T, SWY + 26)], B, 2.2)
for cx in (X_CORE, X_CORE + 9):
    add(f'<line x1="{cx}" y1="{RAIL}" x2="{cx}" y2="{RAIL+250}" stroke="{G}" stroke-width="2.8"/>')
txt(X_CORE + 5, RAIL - 10, "EFD20 / PC44", 9, G, "middle")

# Naux (1차측)
coil_v(X_T, RAIL + 150, 3, 8, -1, O)
add(f'<circle cx="{X_T-12}" cy="{RAIL+157}" r="3" fill="{O}"/>')
txt(X_T - 22, RAIL + 178, "Naux 6", 9.5, O, "end", "700")
wire([(X_T, RAIL + 150), (X_T - 70, RAIL + 150), (X_T - 70, RAIL + 132)], O, 1.7)
diode_h(X_T - 110, RAIL + 132, O, True)
wire([(X_T - 110, RAIL + 132), (X_T - 150, RAIL + 132)], O, 1.7)
wire([(X_T, RAIL + 198), (X_T + 40, RAIL + 198), (X_T + 40, PGND)], O, 1.7)
dot(X_T + 40, PGND, O)
txt(X_T - 100, RAIL + 120, "D_aux", 9, O, "middle")
txt(X_T - 190, RAIL + 136, "VCC 12.2 V", 9.5, O, "end", "700")

# Ns1 / Ns2
coil_v(X_S, RAIL + 6, 3, 8, 1, C)
add(f'<circle cx="{X_S+12}" cy="{RAIL+48}" r="3" fill="{K}"/>')
txt(X_S + 22, RAIL + 30, "Ns1 3", 9.5, K, "start", "700")
coil_v(X_S, RAIL + 130, 4, 8, 1, V)
add(f'<circle cx="{X_S+12}" cy="{RAIL+194}" r="3" fill="{K}"/>')
txt(X_S + 22, RAIL + 160, "Ns2 8", 9.5, K, "start", "700")

SG = RAIL + 300
wire([(X_S, RAIL + 6), (X_S, RAIL - 40), (X_D, RAIL - 40)], C, 2.2)
diode_h(X_D, RAIL - 40, C)
wire([(X_D + 20, RAIL - 40), (X_D + 240, RAIL - 40)], C, 2.2)
wire([(X_S, RAIL + 54), (X_S - 30, RAIL + 54), (X_S - 30, SG), (X_D + 300, SG)], C, 2.2)
txt(X_D + 10, RAIL - 54, "D1 40 V/5 A SBD", 9.5, K, "middle", "700")
cap_v(X_D + 80, RAIL - 12, "Co1 22 uF x3 (2.8 Arms)", C)
wire([(X_D + 80, RAIL - 40), (X_D + 80, RAIL - 12)], C, 2.2)
wire([(X_D + 80, RAIL - 3), (X_D + 80, SG)], C, 2.2)
dot(X_D + 80, RAIL - 40, C); dot(X_D + 80, SG, C)
txt(X_D + 246, RAIL - 44, "S1  6.0 V / 8.1 W", 11, C, "start", "700")
txt(X_D + 246, RAIL - 31, "피드백 대상", 9, G)

wire([(X_S, RAIL + 130), (X_S, RAIL + 104), (X_D, RAIL + 104)], V, 2.2)
diode_h(X_D, RAIL + 104, V)
wire([(X_D + 20, RAIL + 104), (X_D + 240, RAIL + 104)], V, 2.2)
wire([(X_S, RAIL + 194), (X_S - 30, RAIL + 194)], V, 2.2)
dot(X_S - 30, RAIL + 194, V)
txt(X_D + 10, RAIL + 90, "D2 60 V SBD", 9.5, K, "middle", "700")
cap_v(X_D + 80, RAIL + 132, "Co2 10 uF/50 V", V, -1)
wire([(X_D + 80, RAIL + 104), (X_D + 80, RAIL + 132)], V, 2.2)
wire([(X_D + 80, RAIL + 141), (X_D + 80, SG)], V, 2.2)
dot(X_D + 80, RAIL + 104, V); dot(X_D + 80, SG, V)
txt(X_D + 246, RAIL + 100, "S2  16.6 V / 1.2 W", 11, V, "start", "700")
txt(X_D + 246, RAIL + 113, "교차조정 14.1 ~ 19.1 V", 9, G)
txt(X_D + 246, RAIL + 126, "Ns2 만 절연 (HGND 기준)", 9, R, "start", "700")
res_v(X_D + 150, RAIL + 132, 40, "R_pre 1.7 k / 0.25 W", V)
wire([(X_D + 150, RAIL + 104), (X_D + 150, RAIL + 132)], V, 2.2)
wire([(X_D + 150, RAIL + 172), (X_D + 150, SG)], V, 2.2)
dot(X_D + 150, RAIL + 104, V); dot(X_D + 150, SG, V)
txt(X_D + 150, RAIL + 190, "무부하 과전압 방지", 8.5, R, "middle")
gnd(X_D + 300, SG, "SGND", C)

# 컨트롤러 + Q1 + Rcs
block(X_T - 320, SWY - 18, 150, 86, "U1  전류모드 PWM",
      ["VCC 10~30 V, 100 kHz", "CS 문턱 0.5 V", "최대듀티 >= 0.6"], B, "#eff6ff")
wire([(X_T - 170, SWY + 16), (X_T - 38, SWY + 16)], B, 1.7)
mosfet(X_T, SWY + 60, B)
wire([(X_T, SWY + 26), (X_T, SWY + 16)], B, 2.2)
txt(X_T - 44, SWY + 112, "Q1 150 V / Rds 75 mOhm", 9.5, K, "end", "700")
txt(X_T - 44, SWY + 124, "Ipk 2.31 A, Vds 111.6 V (74 %)", 9, G, "end")
res_v(X_T, SWY + 60, 34, "Rcs 0.20 Ohm / 1 W", B)
wire([(X_T, SWY + 94), (X_T, PGND)], B, 2.2)
dot(X_T, PGND, B)
wire([(X_T - 24, SWY + 77), (X_T - 250, SWY + 77), (X_T - 250, SWY + 68)], B, 1.5)
gnd(X_T + 80, PGND, "PGND", B)
# 기동저항
wire([(X_CL - 90, RAIL), (X_CL - 90, RAIL + 150)], B, 1.5, "4,3")
res_v(X_CL - 90, RAIL + 150, 34, None, B)
txt(X_CL - 102, RAIL + 172, "R_st 100 k", 9, K, "end")
wire([(X_CL - 90, RAIL + 184), (X_CL - 90, RAIL + 210), (X_T - 150, RAIL + 210),
      (X_T - 150, RAIL + 132)], B, 1.5, "4,3")
dot(X_T - 150, RAIL + 132, O)
txt(X_CL - 160, RAIL + 228, "기동 : Vin -> R_st -> VCC,  정상운전 : Naux 인계", 9, G)

# 피드백
block(X_D + 100, RAIL + 210, 230, 66, "피드백  (공통 GND 확정)",
      ["직접 분압 Rtop 14 k / Rbot 10 k", "TL431 + 옵토 불요 (부품 3~5점 절감)"], C, "#ecfeff")
wire([(X_D + 100, RAIL + 243), (X_T - 245, RAIL + 243), (X_T - 245, SWY + 42)], C, 1.5, "5,3")
txt(X_D + 88, RAIL + 300, "S1 을 피드백 -> 5 W 레일이 직접 레귤레이션됨", 9, G, "end")
txt(X_D + 100, RAIL + 292, "옵토 극점(약 10 kHz) 제거 -> 루프 대역 확보, CTR 경년변화 리스크 소멸",
    9, C, "start")

# ================================================================= B. POL
PB = PA + PAH + 20
add(f'<rect x="24" y="{PB}" width="{W-48}" height="520" rx="10" fill="#fbfcfe" stroke="#cbd5e1"/>')
txt(40, PB + 22, "B.  POL 후단 레귤레이터", 13, K, "start", "800")
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
lines(70, YB + 352, [
    "* SOT-23 LDO 는 두 레일 모두 불가 (Tj 189 C / 208 C).  SOT-223 + 방열동박 필수.",
    "* VDDA 는 아날로그 전용 별도 LDO + 스타그라운드.  3.3 V 에서 페라이트 분기하면 0.52 W 절약되나 노이즈 공유.",
], 9, G)

# GND 구성 설명
block(880, YB - 4, 400, 196, "", (), C, "#ecfeff")
txt(1080, YB + 20, "GND 구성 - 확정", 12.5, C, "middle", "800")
lines(896, YB + 40, [
    "결론 : 같은 기준의 부하는 공통 GND 사용.",
    "",
    "  VCC_3V3 / VDDA_3V3 / VCC_5V0  -> 공통 GND",
    "  VCC_12V0 (Ns2)                -> 독립 / 플로팅",
    "",
    "이에 따른 단순화 :",
    "  1. 피드백을 직접 분압으로  (TL431+옵토 삭제)",
    "     옵토 극점 제거 -> 루프 대역 확보",
    "  2. Np/Ns1/Naux 는 일반 에나멜선 가능",
    "     창 점유율 43 % -> 36 % (Ku 0.25 -> 0.30)",
    "  3. Np-Ns1 간 연면/내압 시험 대상에서 제외",
], 9.5, K)
block(880, YB + 208, 400, 150, "", (), R, "#fef2f2")
txt(1080, YB + 230, "남은 확인사항 - Ns2 절연 등급", 12, R, "middle", "800")
lines(896, YB + 248, [
    "HGND 가 무엇이냐로 Ns2 사양이 갈린다.",
    "",
    "  PV측 스위치노드  -> 기능절연, 수십 V",
    "  계통측(언폴더)   -> PV측 대비 +-342 V 스윙",
    "                     강화절연 + 연면/공간거리",
    "                     + 내압시험 대상",
    "",
    "-> Ns2 의 TIW 필수 여부와 시험사양이 여기서 결정",
], 9.5, K)

# 손실 요약
block(1320, YB - 4, 370, 350, "", (), G, "#f8fafc")
txt(1505, YB + 20, "손실 배분 (입력 11.67 W)", 12, K, "middle", "800")
lines(1336, YB + 42, [
    "S1 쇼트키 (Vf 0.45 V)        0.61 W",
    "RCD 클램프 (Llk 2 %)         0.62 W",
    "LDO VDDA (5 -> 3.3 V)       0.52 W",
    "동기벅 3.3 V                 0.38 W",
    "LDO 12 V                    0.33 W",
    "트랜스포머 (dT 14 K)           0.34 W",
    "1차 MOSFET (도통+스위칭)        0.32 W",
    "동기벅 5.0 V                 0.22 W",
    "전류센스 Rcs                  0.22 W",
    "S2 쇼트키 / 컨트롤러            0.12 W",
    "──────────────────────────────────",
    "집계 3.67 W  =  입력-출력 3.67 W  (수지 일치)",
    "",
    "전체 효율 68.6 %",
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
