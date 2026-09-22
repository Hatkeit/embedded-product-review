# -*- coding: utf-8 -*-
"""MICROINV V2000 — KS C 8560:2020 기준 250×250 배치 계획 (넷리스트 2026-09-22)."""
import re, math, collections, csv, json
from inv_parse import load
from fp2_parts import SIZE, HEIGHT, PASSIVE_AREA, THT_PSM
import ks_rules as KS

prims, parts, nets, _ = load('.')
pin2net = {}
for n, nodes in nets.items():
    for ref, pin in nodes: pin2net[(ref, pin)] = n
def part_nets(ref):
    out = []
    for (pname, pnum, puse) in parts[ref]['pins']:
        for num in pnum.strip('()').split(','):
            n = pin2net.get((ref, num.strip()))
            if n and n != 'NC': out.append(n)
    return list(dict.fromkeys(out))
DOM = json.load(open('net_domains.json'))   # 참고용 (Q9 때문에 전부 병합됨)

BOARD = 250.0
BLOCK = {1:'PV_A DC-DC', 2:'PV_B DC-DC', 3:'GRID 입출력·보호', 4:'AUX 전원', 5:'MCU',
         6:'ESP32·TPM·USB·CAN', 7:'절연 센싱', 8:'2차 게이트 로직', 9:'아날로그', 10:'ADC 보호'}

# ─────────────────── 1. 절연 경계 (ㄴ자) ───────────────────
BAR_W   = 8.0                 # 연면 8.0 mm (표 5, 400V·PD2·IIIa 4.0 ×2 보강)
BAR_VX  = 128.0               # 세로 경계 중심
BAR_HY  = 216.0               # 가로 경계 중심
BAR_V   = (BAR_VX - BAR_W/2, 0, BAR_VX + BAR_W/2, BAR_HY + BAR_W/2)
BAR_H   = (BAR_VX - BAR_W/2, BAR_HY - BAR_W/2, BOARD, BAR_HY + BAR_W/2)
SEC_RGN = (BAR_VX + BAR_W/2, 0, BOARD, BAR_HY - BAR_W/2)          # 2차 (PHV·AC·PGND)
PRI_RGN2= (BAR_VX + BAR_W/2, BAR_HY + BAR_W/2, BOARD, BOARD)      # 1차 보조 (AMC 출력·센싱)

# ─────────────────── 2. 배치 ───────────────────
P = {}
def put(ref, x, y, rot=0, side='TOP', w=None, h=None):
    P[ref] = dict(x=x, y=y, rot=rot, side=side, w=w, h=h)

# ── 경계 통과 부품 (세로 경계) ──
put('T2', BAR_VX, 28); put('ISO1', BAR_VX, 55); put('T4', BAR_VX, 82)
put('T6', BAR_VX, 128); put('ISO4', BAR_VX, 155); put('T8', BAR_VX, 183)
# ── 경계 통과 부품 (가로 경계) ──
put('T9', 172, BAR_HY); put('ISO2', 200, BAR_HY, 90); put('ISO3', 213, BAR_HY, 90)
put('U23', 228, BAR_HY, 90); put('U24', 243, BAR_HY, 90)

# ── 1차: 상·하 에지 밴드 (PV 탭 + PE + Y캡) ──
put('J5', 9, 9); put('C4', 28, 9)
for i, r in enumerate(['J1','J2','J3','J4']): put(r, 48 + 14*i, 9)
put('J10', 9, 241); put('C24', 28, 241)
for i, r in enumerate(['J6','J7','J8','J9']): put(r, 48 + 14*i, 241)

# ── 1차: PV 전해캡 12개 (눕힘, 2열 × 3행 × 2뱅크) ──
for i, r in enumerate(['EC1','EC3','EC5']): put(r, 30, 26 + 21*i)
for i, r in enumerate(['EC2','EC4','EC6']): put(r, 74, 26 + 21*i)
for i, r in enumerate(['EC7','EC9','EC11']): put(r, 30, 172 + 21*i)
for i, r in enumerate(['EC8','EC10','EC12']): put(r, 74, 172 + 21*i)

# ── 1차: 제어·통신 (좌측 에지 커넥터) ──
put('U18', 7, 148); put('J19', 11, 92); put('J20', 11, 102); put('J21', 9, 112)
put('J22', 8, 120); put('J23', 7, 128)
put('U17', 34, 108); put('U19', 34, 128); put('U20', 34, 138); put('L11', 34, 145)
put('D39', 34, 151); put('TSW1', 46, 150)
put('U16', 62, 104); put('Y1', 62, 118); put('U27', 62, 126)
# ── 1차: 아날로그 ──
for i, r in enumerate(['U2','U3','U10','U11']): put(r, 88 + 0*i, 92 + 8*i)
put('U12', 88, 124); put('D42', 96, 92); put('D43', 96, 98); put('D44', 96, 104)
put('R6', 100, 8, 90); put('U21', 104, 8, 90); put('R43', 100, 244, 90); put('U22', 104, 244, 90)
put('R101', 96, 136, 90)
# ── 1차: FET (하면) + 드라이버 ──
for i, (r, y) in enumerate([('Q1',18),('Q2',32),('Q3',72),('Q4',86)]): put(r, 108, y, 0, 'BOTTOM')
put('U13', 108, 52, 0, 'BOTTOM')
for i, (r, y) in enumerate([('Q5',150),('Q6',164),('Q7',196),('Q8',210)]): put(r, 108, y, 0, 'BOTTOM')
put('U14', 108, 178, 0, 'BOTTOM')
put('R10', 118, 20, 90, 'BOTTOM'); put('R30', 118, 84, 90, 'BOTTOM')
put('R47', 118, 152, 90, 'BOTTOM'); put('R67', 118, 208, 90, 'BOTTOM')
put('D2', 102, 18); put('D13', 102, 236)
put('C69', 100, 96); put('C70', 100, 106)
# ── 1차: AUX 전원 (T9 1차측 = 보드 우하단) ──
put('L12', 144, 240); put('U15', 158, 240); put('Q10', 168, 240, 0, 'BOTTOM')
put('D29', 190, 232); put('D30', 190, 240)
put('C162', 208, 238); put('C164', 232, 238)

# ── 2차: PHV 정류 (하면 SiC) ──
put('D3', 152, 28, 0, 'BOTTOM'); put('D8', 152, 82, 0, 'BOTTOM')
put('D14', 152, 128, 0, 'BOTTOM'); put('D19', 152, 183, 0, 'BOTTOM')
put('D4', 156, 52); put('D9', 156, 106); put('D15', 156, 152); put('D20', 156, 196)
# ── 2차: 게이트 로직 (상면) ──
put('U6', 170, 12); put('U7', 180, 10); put('U8', 186, 10); put('U9', 192, 10)
put('U25', 180, 17); put('U26', 187, 17); put('D40', 200, 10); put('D41', 200, 17)
put('U1', 168, 62); put('U5', 96, 116)     # U5 는 1차(VDD_U5/GND)
# ── 2차: 언폴더 (하면) ──
put('D23', 172, 62, 0, 'BOTTOM'); put('Q12', 172, 82, 0, 'BOTTOM'); put('D24', 172, 102, 0, 'BOTTOM')
put('Q13', 192, 62, 0, 'BOTTOM'); put('Q14', 192, 102, 0, 'BOTTOM')
for i, r in enumerate(['R200','R201']): put(r, 206, 56 + 7*i, 90, 'BOTTOM')
for i, r in enumerate(['R211','R212']): put(r, 206, 96 + 7*i, 90, 'BOTTOM')
put('R79', 164, 32, 90); put('R81', 164, 40, 90); put('R188', 164, 48, 90)
put('R82', 172, 32, 90); put('R83', 172, 40, 90)
put('D25', 160, 120); put('D26', 160, 128); put('Q9', 164, 134)
# ── 2차: AC 필터·보호·릴레이 (THT, 상면) ──
put('L7', 215, 32); put('L8', 215, 50); put('LS1', 215, 74)
put('C56', 215, 96); put('C50', 215, 112); put('C51', 215, 124)
put('C53', 215, 134); put('C58', 215, 142); put('C54', 215, 150); put('C52', 215, 160)
put('C46', 176, 126); put('C47', 176, 140); put('C48', 176, 154)
put('F1', 240, 30); put('F2', 240, 42); put('D27', 240, 56); put('TH1', 240, 68)
for i, r in enumerate(['RV1','RV3','RV4','RV5','RV2']): put(r, 241, 80 + 9*i)
put('C49', 240, 128); put('C57', 240, 138); put('C63', 240, 148)
put('R90', 200, 94, 90); put('R219', 200, 104, 90); put('R228', 200, 112, 90)
put('R96', 190, 126, 90); put('R99', 190, 134, 90); put('R100', 190, 142, 90); put('R106', 190, 150, 90)
# ── 2차: AC / PE 탭 (우측 에지) ──
for i, r in enumerate(['J11','J12','J15','J16']): put(r, 246, 166 + 11*i)
put('J13', 241, 10); put('J14', 241, 22); put('J17', 241, 206); put('J18', 241, 240)

# ─────────────────── 3. 소형 SMD 군집 ───────────────────
CLUSTERS = [
 (5,'TOP', 52, 86, 78, 100, 'p5 MCU 주변'), (5,'TOP', 52, 132, 78, 146, 'p5 MCU 주변'),
 (6,'TOP', 22, 96, 46, 104, 'p6 ESP32/TPM/CAN'), (6,'TOP', 22, 154, 60, 162, 'p6'),
 (10,'TOP', 84, 132, 100, 146, 'p10 ADC 보호 (ZD1~4)'),
 (7,'TOP', 84, 152, 122, 168, 'p7 센싱'), (7,'TOP', 196, 226, 232, 248, 'p7 AMC 출력 (1차측)'),
 (9,'TOP', 84, 108, 100, 120, 'p9 아날로그'),
 (1,'BOTTOM', 96, 40, 104, 66, 'p1 게이트·스너버'), (1,'BOTTOM', 158, 14, 172, 52, 'p1 PHV 캡'),
 (2,'BOTTOM', 96, 172, 104, 194, 'p2 게이트·스너버'), (2,'BOTTOM', 158, 160, 172, 200, 'p2 PHV 캡'),
 (4,'TOP', 136, 228, 182, 234, 'p4 AUX'), (4,'BOTTOM', 150, 232, 182, 248, 'p4 AUX'),
 (8,'TOP', 164, 20, 204, 26, 'p8 로직'), (8,'TOP', 156, 74, 200, 82, 'p8 로직'),
 (3,'TOP', 186, 30, 206, 60, 'p3 GRID'), (3,'TOP', 160, 168, 208, 186, 'p3 GRID'),
]
# ─────────────────── 4. 하면 서멀 존 ───────────────────
ZONES = [
 (100, 10, 116, 94,  'A-FET Q1~Q4 + U13', 'PQFN 1.0'),
 (100, 142, 116, 218,'B-FET Q5~Q8 + U14', 'PQFN 1.0'),
 (145, 18, 160, 92,  'A-SiC D3/D8', 'D2PAK 4.5'),
 (145, 118, 160, 192,'B-SiC D14/D19', 'D2PAK 4.5'),
 (164, 50, 212, 116, 'C-UNFOLD D23/D24/Q12 + Q13/Q14', 'DPAK 2.4 / D2PAK 4.6'),
]
# 열 이격 치수 (전해캡 65 ℃ / 단자 60 ℃ — 표 13)
THERMAL_DIMS = [
 ('h', 100, 107, 100, 'EC 뱅크 ↔ FET 존  7'),
 ('h', 100, 145, 158, 'EC 뱅크 ↔ SiC 존  45'),
 ('v', 92, 76, 100, 'PV 탭 ↔ 발열부'),
]
ANT_KEEPOUT = (25, 96, 43, 120)      # ESP32 안테나
TEST_ZONES = [                        # 8.3.1 / 8.3.2 시험 시 탈착 (바리스터·Y캡·서지)
 (231, 74, 250, 128, '탈착: RV1~RV5 (바리스터)'),
 (231, 122, 250, 156, '탈착: C49/C57/C63 (Y캡)'),
 (232, 50, 250, 76, '탈착: D27 GDT'),
 (20, 3, 40, 17, '탈착: C4'), (20, 233, 40, 247, '탈착: C24'),
 (198, 230, 246, 248, '탈착: C162/C164 (Y캡)'),
]
# 절연 부품 중 치수 미달 (경고)
ISO_WARN = {'ISO1': 'ELD207 리드스팬 4.6 mm < 보강 8.0 mm → 광절연 부품 교체 필요'}
BARRIER_CROSS = ['T2','T4','T6','T8','T9','ISO1','ISO2','ISO3','ISO4','U23','U24']
GALVANIC_BUG = ['Q9']   # 1차 GND ↔ 2차 PGND 를 단락하는 부품

# ─────────────────── 5. 분류 ───────────────────
HIGH = {'Q1','Q2','Q3','Q4','Q5','Q6','Q7','Q8','Q12','Q13','Q14','D3','D8','D14','D19','D23','D24'}
MED  = ({'T2','T4','T6','T8','T9','Q10','U13','U14','U15','L12','D2','D13','D4','D9','D15','D20',
         'R6','R43','R101','R79','R81','R188','R82','R83','R90','R96','R106','R200','R201','R211',
         'R212','R219','R228','L7','L8','LS1','D25','D26','TH1','RV1','RV2','RV3','RV4','RV5',
         'T1','T3','T5','T7','R10','R30','R47','R67'} | {f'EC{i}' for i in range(1,13)})
def mount(ref):
    psm = parts[ref]['psm']
    if psm in THT_PSM: return 'THT'
    if psm == 'USB-C_16PIN': return 'SMT(+THT 고정핀)'
    return 'SMT'
def heat(ref): return 'H' if ref in HIGH else ('M' if ref in MED else 'L')
def side(ref): return P[ref]['side'] if ref in P else 'TOP'
def size_of(ref):
    p = P.get(ref, {}); s = SIZE.get(parts[ref]['psm'], (4.0, 3.0))
    if p.get('w'): s = (p['w'], p['h'])
    return s
def domain(ref):
    if ref in BARRIER_CROSS: return 'BAR'
    if ref not in P: return 'PRI'
    x, y = P[ref]['x'], P[ref]['y']
    if x > BAR_VX + BAR_W/2 and y < BAR_HY - BAR_W/2: return 'SEC'
    return 'PRI'

# ═══════════════════ 6. 도면 ═══════════════════
SC = 5.0; OX, OY = 72, 96
def X(mm): return OX + mm * SC
def Y(mm): return OY + mm * SC
FONT = "Noto Sans KR, Apple SD Gothic Neo, Arial, sans-serif"
def esc(s): return s.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
def text(x, y, s, size=9, anchor='middle', weight='normal', fill='#111', rot=0):
    tf = f' transform="rotate({rot} {x:.1f} {y:.1f})"' if rot else ''
    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" font-weight="{weight}" fill="{fill}" font-family="{FONT}"{tf}>{esc(s)}</text>'
def rectpx(x, y, w, h, **kw):
    st = ' '.join(f'{k.replace("_","-")}="{v}"' for k, v in kw.items())
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(w,0.1):.1f}" height="{max(h,0.1):.1f}" {st}/>'
def rmm(x1, y1, x2, y2, **kw): return rectpx(X(x1), Y(y1), (x2-x1)*SC, (y2-y1)*SC, **kw)
def lmm(x1, y1, x2, y2, **kw):
    st = ' '.join(f'{k.replace("_","-")}="{v}"' for k, v in kw.items())
    return f'<line x1="{X(x1):.1f}" y1="{Y(y1):.1f}" x2="{X(x2):.1f}" y2="{Y(y2):.1f}" {st}/>'
def cmm(cx, cy, d, **kw):
    st = ' '.join(f'{k.replace("_","-")}="{v}"' for k, v in kw.items())
    return f'<circle cx="{X(cx):.1f}" cy="{Y(cy):.1f}" r="{d/2*SC:.1f}" {st}/>'
def mx(x, mir): return (BOARD - x) if mir else x

DEFS = '''<defs>
<pattern id="dots" patternUnits="userSpaceOnUse" width="6" height="6"><circle cx="3" cy="3" r="1" fill="#5d6d7e" fill-opacity="0.55"/></pattern>
<pattern id="bar" patternUnits="userSpaceOnUse" width="9" height="9" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="9" stroke="#b7950b" stroke-width="2.4" stroke-opacity="0.55"/></pattern>
<pattern id="lead" patternUnits="userSpaceOnUse" width="7" height="7" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="7" stroke="#c0392b" stroke-width="1.5" stroke-opacity="0.8"/></pattern>
<marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#17a589"/></marker>
</defs>'''
COL = {'PRI': '#eaf2fb', 'SEC': '#fdeeec', 'PE': '#fcf3cf'}
PE_ISLANDS = [(2,2,20,20),(2,230,20,248),(232,2,250,32),(230,196,250,216),(232,230,250,248)]

def grid():
    o = []
    for i in range(0, 251, 10):
        maj = i % 50 == 0
        o.append(lmm(i, 0, i, 250, stroke='#d5d8dc' if maj else '#f0f2f4', stroke_width=1 if maj else 0.6))
        o.append(lmm(0, i, 250, i, stroke='#d5d8dc' if maj else '#f0f2f4', stroke_width=1 if maj else 0.6))
        if maj:
            o.append(text(X(i), Y(0)-7, str(i), size=9, fill='#7f8c8d'))
            o.append(text(X(0)-9, Y(i)+3, str(i), size=9, fill='#7f8c8d', anchor='end'))
    o.append(rmm(0, 0, 250, 250, fill='none', stroke='#b7950b', stroke_width=3))
    return '\n'.join(o)

def domains(mir):
    o = []
    def R(x1,y1,x2,y2,c):
        a,b = mx(x1,mir), mx(x2,mir)
        return rmm(min(a,b), y1, max(a,b), y2, fill=c, stroke='none')
    o.append(R(0, 0, BAR_VX-BAR_W/2, 250, COL['PRI']))
    o.append(R(BAR_VX+BAR_W/2, 0, 250, BAR_HY-BAR_W/2, COL['SEC']))
    o.append(R(BAR_VX+BAR_W/2, BAR_HY+BAR_W/2, 250, 250, COL['PRI']))
    o.append(R(BAR_V[0], BAR_V[1], BAR_V[2], BAR_V[3], 'url(#bar)'))
    o.append(R(BAR_H[0], BAR_H[1], BAR_H[2], BAR_H[3], 'url(#bar)'))
    for (x1,y1,x2,y2) in [(BAR_V[0],0,BAR_V[2],BAR_V[3]), (BAR_H[0],BAR_H[1],BAR_H[2],BAR_H[3])]:
        a,b = mx(x1,mir), mx(x2,mir)
        o.append(rmm(min(a,b), y1, max(a,b), y2, fill='none', stroke='#b7950b', stroke_width=2, stroke_dasharray='9 5'))
    lx = mx(BAR_VX, mir)
    o.append(text(X(lx), Y(BAR_HY+BAR_W/2)+16, '절연 경계 8.0 mm', size=9, fill='#7d6608', weight='bold'))
    for (x1,y1,x2,y2) in PE_ISLANDS:
        a,b = mx(x1,mir), mx(x2,mir)
        o.append(rmm(min(a,b), y1, max(a,b), y2, fill=COL['PE'], stroke='#b7950b', stroke_width=1.2, stroke_dasharray='4 2'))
        o.append(text(X((min(a,b)+max(a,b))/2), Y(y2)-2, 'PE', size=7, fill='#7d6608', weight='bold'))
    o.append(text(X(mx(60,mir)), Y(1)+11, '1차 (PV·제어, GND)', size=10, fill='#1a5276', weight='bold', anchor='middle'))
    o.append(text(X(mx(195,mir)), Y(1)+11, '2차 (PHV·AC, PGND)', size=10, fill='#922b21', weight='bold', anchor='middle'))
    o.append(text(X(mx(178,mir)), Y(247), '1차 보조 (AMC 출력·AUX 1차)', size=9, fill='#1a5276', weight='bold', anchor='middle'))
    return '\n'.join(o)

def fp(ref, mir, ghost=False, lead=False):
    p = P[ref]; psm = parts[ref]['psm']; s = size_of(ref)
    x, y = mx(p['x'], mir), p['y']
    o = []; is_tht = mount(ref) == 'THT'
    if ghost: fill, st, op, dash = 'none', '#7f8c8d', 0.5, '4 3'
    elif lead: fill, st, op, dash = 'url(#lead)', '#c0392b', 0.9, '3 2'
    elif ref in GALVANIC_BUG: fill, st, op, dash = '#e74c3c', '#7b241c', 1.0, 'none'
    elif ref in ISO_WARN: fill, st, op, dash = '#f9e79f', '#b7950b', 1.0, '3 2'
    elif ref in BARRIER_CROSS: fill, st, op, dash = '#d5f5e3', '#117a65', 1.0, 'none'
    elif heat(ref) == 'H': fill, st, op, dash = '#f5b7b1', '#922b21', 1.0, 'none'
    elif heat(ref) == 'M': fill, st, op, dash = '#fad7a0', '#9c640c', 1.0, ('6 3' if is_tht else 'none')
    else: fill, st, op, dash = ('#d5f5e3' if is_tht else '#d6eaf8'), ('#196f3d' if is_tht else '#1b4f72'), 1.0, ('6 3' if is_tht else 'none')
    if psm == 'CAPPRD750W80D1800H4000_HZ':
        b1, b2 = (x-22, x+18) if not mir else (x-18, x+22)
        lx = x+20 if not mir else x-20
        if lead:
            o.append(rmm(min(b1,b2), y-9.25, max(b1,b2), y+9.25, fill='none', stroke='#c0392b', stroke_width=0.8, stroke_dasharray='2 3', rx=6))
            o.append(rmm(lx-2.5, y-6, lx+2.5, y+6, fill='url(#lead)', stroke='#c0392b', stroke_width=1))
            return '\n'.join(o)
        o.append(rmm(min(b1,b2), y-9.25, max(b1,b2), y+9.25, fill=fill, stroke=st, stroke_width=1.4, stroke_dasharray=dash, rx=8))
        o.append(lmm(min(b1,b2)+4, y-9.25, min(b1,b2)+4, y+9.25, stroke=st, stroke_width=1))
        for dy in (-3.75, 3.75):
            o.append(lmm(max(b1,b2), y+dy, lx, y+dy, stroke=st, stroke_width=2))
            o.append(cmm(lx, y+dy, 0.8, fill='#fff', stroke=st, stroke_width=1))
        o.append(text(X(x-2), Y(y)+3, ref, size=8.5, weight='bold'))
        o.append(text(X(x-2), Y(y)+12, '2700µF/63V 눕힘 h19', size=6.5, fill='#566573'))
        return '\n'.join(o)
    if s[0] == 'circle':
        o.append(cmm(x, y, s[1], fill=fill, stroke=st, stroke_width=1.4, stroke_dasharray=dash))
        o.append(cmm(x, y, 3.2, fill='#fff', stroke=st, stroke_width=1))
        o.append(text(X(x), Y(y)+3, ref, size=7, weight='bold'))
        return '\n'.join(o)
    w, h = s
    if p['rot'] in (90, 270): w, h = h, w
    if lead:
        if psm.startswith('XFMR508'):   # DIP 트랜스: 핀 열 2줄만 하면으로 돌출
            span = 30.48 if '3048' in psm else 25.40
            n = int(psm.rsplit('-',1)[1]); per = max(2, n//2); rowlen = (per-1)*5.08 + 3.0
            horiz = abs(p['y'] - BAR_HY) < 20 and p['x'] > BAR_VX
            o.append(rmm(x-w/2, y-h/2, x+w/2, y+h/2, fill='none', stroke='#c0392b', stroke_width=0.8, stroke_dasharray='2 3'))
            for sgn in (-1, 1):
                if horiz: o.append(rmm(x-rowlen/2, y+sgn*span/2-1.8, x+rowlen/2, y+sgn*span/2+1.8, fill='url(#lead)', stroke='#c0392b', stroke_width=1))
                else:     o.append(rmm(x+sgn*span/2-1.8, y-rowlen/2, x+sgn*span/2+1.8, y+rowlen/2, fill='url(#lead)', stroke='#c0392b', stroke_width=1))
            o.append(text(X(x), Y(y)+3, ref + ' 리드', size=7, fill='#c0392b', weight='bold'))
            return '\n'.join(o)
        o.append(rmm(x-w/2, y-h/2, x+w/2, y+h/2, fill='url(#lead)', stroke='#c0392b', stroke_width=1, stroke_dasharray='3 2'))
        o.append(text(X(x), Y(y)+3, ref, size=6.5, fill='#c0392b'))
        return '\n'.join(o)
    o.append(rmm(x-w/2, y-h/2, x+w/2, y+h/2, fill=fill, stroke=st, stroke_width=1.5, fill_opacity=op, stroke_opacity=op, stroke_dasharray=dash, rx=1))
    if not ghost and ref in BARRIER_CROSS and psm.startswith('XFMR508'):
        n = int(psm.rsplit('-', 1)[1]); per = max(2, n // 2); pitch = 5.08
        span = 30.48 if '3048' in psm else 25.40
        horiz = abs(p['y'] - BAR_HY) < 20 and p['x'] > BAR_VX
        for i in range(per):
            d = (i - (per-1)/2) * pitch
            for sgn in (-1, 1):
                px, py = (x + d, y + sgn*span/2) if horiz else (x + sgn*span/2, y + d)
                o.append(cmm(px, py, 1.2, fill='#fff', stroke=st, stroke_width=1))
        lab1 = ('1차', '2차') if not horiz else ('2차', '1차')
        if horiz:
            o.append(text(X(x), Y(y-span/2)-3, lab1[0], size=6.5, fill='#7d6608'))
            o.append(text(X(x), Y(y+span/2)+9, lab1[1], size=6.5, fill='#7d6608'))
        else:
            o.append(text(X(mx(p['x']-span/2, mir)), Y(y-h/2)-3, '1차' if not mir else '2차', size=6.5, fill='#7d6608'))
            o.append(text(X(mx(p['x']+span/2, mir)), Y(y-h/2)-3, '2차' if not mir else '1차', size=6.5, fill='#7d6608'))
    if not ghost and not lead and psm in ('SOT254P1510X450-3N','SOT254P1524X457-3N','SOT228P991X233-3M','SOT228P998X235-3N'):
        o.append(rmm(x-w/2+0.5, y-h/2+0.5, x+w/2-0.5, y-h/2+h*0.42, fill='#e6b0aa', stroke=st, stroke_width=0.8))
    if not ghost and not lead and psm == 'SON127P515X548X100-8N':
        o.append(rmm(x-2.0, y-2.2, x+2.0, y+2.2, fill='#e6b0aa', stroke=st, stroke_width=0.8))
    if not ghost and not lead and psm == 'ESP32-S3':
        o.append(rmm(x-w/2, y-h/2, x+w/2, y-h/2+6, fill='#f9e79f', stroke=st, stroke_width=0.8))
        o.append(text(X(x), Y(y-h/2+4.2), '안테나', size=6.5, fill='#7d6608'))
    size = 8 if w*SC >= 34 else (7 if w*SC >= 18 else 6)
    col = '#7f8c8d' if ghost else ('#7b241c' if ref in GALVANIC_BUG else '#1b2631')
    if w*SC < 15 and h*SC >= 15: o.append(text(X(x), Y(y), ref, size=size, weight='bold', fill=col, rot=-90))
    else: o.append(text(X(x), Y(y)+3, ref, size=size, weight='bold', fill=col))
    if not ghost and not lead and w*SC >= 42 and h*SC >= 26:
        o.append(text(X(x), Y(y)+12, parts[ref]['value'][:20], size=6.5, fill='#566573'))
        if psm.startswith('XFMR508'): o.append(text(X(x), Y(y)+21, f"h={HEIGHT.get(psm,0):.0f}", size=6.5, fill='#566573'))
    return '\n'.join(o)

def clusters(mir, sd):
    o = []
    for (pg, s, x1, y1, x2, y2, lab) in CLUSTERS:
        if s != sd: continue
        a, b = mx(x1, mir), mx(x2, mir)
        o.append(rmm(min(a,b), y1, max(a,b), y2, fill='url(#dots)', stroke='#5d6d7e', stroke_width=1, stroke_dasharray='2 2'))
        o.append(text(X((min(a,b)+max(a,b))/2), Y((y1+y2)/2)+3, lab, size=6.5, fill='#34495e'))
    return '\n'.join(o)

def testzones(mir):
    o = []
    for (x1, y1, x2, y2, lab) in TEST_ZONES:
        a, b = mx(x1, mir), mx(x2, mir)
        o.append(rmm(min(a,b), y1, max(a,b), y2, fill='none', stroke='#8e44ad', stroke_width=1.6, stroke_dasharray='6 3'))
        o.append(text(X((min(a,b)+max(a,b))/2), Y(y1)-3 if y1 > 6 else Y(y2)+9, lab, size=6.5, fill='#6c3483', weight='bold'))
    return '\n'.join(o)

def zones(mir):
    o = []
    for (x1, y1, x2, y2, lab, hh) in ZONES:
        a, b = mx(x1, mir), mx(x2, mir)
        o.append(rmm(min(a,b), y1, max(a,b), y2, fill='#ec7063', fill_opacity=0.16, stroke='#c0392b', stroke_width=2))
        o.append(text(X((min(a,b)+max(a,b))/2), Y(y1)-4, f'{lab}  h={hh}', size=7, fill='#922b21', weight='bold'))
    return '\n'.join(o)

def hdim(x1, x2, y, lab, c='#1f618d'):
    return '\n'.join([lmm(x1,y,x2,y,stroke=c,stroke_width=1), lmm(x1,y-1.2,x1,y+1.2,stroke=c,stroke_width=1),
                      lmm(x2,y-1.2,x2,y+1.2,stroke=c,stroke_width=1), text(X((x1+x2)/2), Y(y)-4, lab, size=8, fill=c, weight='bold')])
def callout(x, y, tx, ty, lab, c='#1f618d', anchor='start', size=8):
    return '\n'.join([lmm(x,y,tx,ty,stroke=c,stroke_width=1),
                      text(X(tx)+(4 if anchor=='start' else -4), Y(ty)+3, lab, size=size, fill=c, anchor=anchor, weight='bold')])
def legend(items, x, y, w=440):
    o = [rectpx(x, y, w, 20+17*len(items), fill='#fff', stroke='#bdc3c7', rx=6)]
    for i, (f, s, d, lab) in enumerate(items):
        yy = y + 14 + i*17
        o.append(rectpx(x+10, yy-6, 26, 12, fill=f, stroke=s, stroke_width=1.4, stroke_dasharray=d))
        o.append(text(x+44, yy+4, lab, size=9, anchor='start'))
    return '\n'.join(o)
def notes(title, lines, x, y, w):
    o = [rectpx(x, y, w, 30+15.5*len(lines), fill='#fbfcfc', stroke='#bdc3c7', rx=6),
         text(x+12, y+18, title, size=11, weight='bold', anchor='start')]
    for i, ln in enumerate(lines): o.append(text(x+12, y+37+i*15.5, ln, size=9, anchor='start', fill='#2c3e50'))
    return '\n'.join(o)
def wrap(body, w, h, t, sub):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" font-family="{FONT}">
<rect width="100%" height="100%" fill="#fff"/>{DEFS}
{text(24, 34, t, size=18, weight='bold', anchor='start')}
{text(24, 56, sub, size=10.5, anchor='start', fill='#7b241c')}
{text(24, 74, '넷리스트 pstxprt/pstchip/pstxnet 2026-09-22 · 653 부품 · 360 넷 · 굵은 외곽 = 실제 패키지 크기 · 소형 SMD 는 군집 면적 환산', size=9, anchor='start', fill='#566573')}
{body}</svg>'''

def top_view():
    o = [domains(False), grid()]
    kx, ky, kx2, ky2 = ANT_KEEPOUT
    o.append(rmm(kx, ky, kx2, ky2, fill='none', stroke='#7d6608', stroke_width=1, stroke_dasharray='3 2'))
    for r in P:
        if P[r]['side'] == 'BOTTOM': o.append(fp(r, False, ghost=True))
    o.append(clusters(False, 'TOP'))
    for r in P:
        if P[r]['side'] == 'TOP': o.append(fp(r, False))
    o.append(testzones(False))
    # 전력 흐름
    for (x1,y1,x2,y2) in [(96,56,104,56),(96,182,104,182),(116,56,124,56),(116,182,124,182),
                          (134,56,146,56),(134,182,146,182),(162,56,166,56),(214,116,214,150)]:
        o.append(lmm(x1,y1,x2,y2,stroke='#17a589',stroke_width=2.4,marker_end='url(#ar)',stroke_opacity=0.85))
    for (x,y,l) in [(104,64,'FET(하면)'),(128,62,'트랜스'),(152,64,'SiC(하면)'),
                    (186,44,'언폴더(하면)'),(215,20,'AC 필터'),(238,160,'AC 탭')]:
        o.append(text(X(x), Y(y), l, size=7.5, fill='#0e6655', weight='bold'))
    # 절연거리 치수
    o.append(hdim(BAR_VX-BAR_W/2, BAR_VX+BAR_W/2, 240, '8.0 연면 (보강)'))
    o.append(callout(BAR_VX-4, 112, 112, 112, '공간 5.5 / 연면 8.0', anchor='end'))
    o.append(callout(232, 190, 214, 196, 'AC↔PE 공간 3.0 / 연면 4.0', anchor='end'))
    o.append(callout(20, 9, 30, 20, 'PV↔PE 1.8 / 1.3', anchor='start'))
    o.append(callout(131, 55, 146, 66, 'ISO1 ELD207 리드스팬 4.6 < 8.0 — 교체 필요', c='#b9770e', anchor='start'))
    o.append(callout(167, 134, 158, 106, 'Q9: 1차 GND ↔ 2차 PGND 단락', c='#c0392b', anchor='end'))
    # 열 이격
    o.append(hdim(96, 104, 68, 'EC↔FET 8', c='#b9770e'))
    o.append(hdim(96, 145, 232, 'EC 뱅크 ↔ SiC 존 49', c='#b9770e'))
    leg = legend([('#d5f5e3','#117a65','none','경계 통과 절연부품 (트랜스·옵토·AMC)'),
                  ('#f5b7b1','#922b21','none','발열 高 → 하면 실장, 서멀패드 접촉'),
                  ('#fad7a0','#9c640c','none','발열 中 (전해캡·트랜스·션트·초크·MOV)'),
                  ('#d6eaf8','#1b4f72','none','SMT 일반'), ('#d5f5e3','#196f3d','6 3','THT(DIP) — 리드 하면 돌출'),
                  ('none','#8e44ad','6 3','8.3.1/8.3.2 시험 시 탈착 구역 (바리스터·Y캡·서지)'),
                  ('#e74c3c','#7b241c','none','회로 결함 (Q9)'), ('url(#dots)','#5d6d7e','2 2','소형 SMD 군집')], 24, Y(250)+30)
    nl = [
        'KS C 8560:2020 적용범위 = Pac ≤ 1 kW, Vdc ≤ 150 V, Vac ≤ 380 V. 본 설계(PV 60 V / AC 220 V)는 범위 내.',
        '절연 경계 = ㄴ자 8.0 mm 통로. 세로 x=128 (T2/T4/T6/T8 + ISO1/ISO4), 가로 y=216 (T9 + ISO2/ISO3 + U23/U24). 통로를 가로지르는 배선·비아·동박 금지.',
        '공간거리(표 4): PV 회로 1.5 (임펄스 2 500 V, 표 3 비고 4) / AC 3.0 (OVC III 4 000 V) / 1차↔2차 보강 5.5 (한 단계 위 6 000 V).',
        '연면거리(표 5, 오염등급 2, FR-4 = 재료그룹 IIIa): PHV 400 V 기본 4.0 → 보강 8.0. PWB 열(1.0/2.0) 적용은 도포·PD1 검증 시에만.',
        '전해캡 12개(EC1~EC12)는 눕힘 실장 h≈19 mm, 좌측 2열 × 3행 × 2뱅크. 표 13 한계 65 ℃ → 옥외 주위 45 ℃ 기준 허용 상승 20 K 로 가장 타이트.',
        '  → 발열원(트랜스 h35.5·SiC·FET·언폴더)과 평면 이격 8~49 mm 확보, 하면 히트싱크를 EC 구역까지 연장 금지. 온도 상승 시험(8.5.4)으로 실측 검증 필요.',
        'PV/AC 탭(250T-1)은 표 13 "외부 결선 단자 60 ℃" → 허용 상승 15 K. 보드 상·하·우 에지로 분산하여 발열부와 최대 이격.',
        '보라색 구역 = 8.3.1 절연저항 / 8.3.2 내전압 시험 시 제거 대상(바리스터 RV1~RV5, Y캡 C4·C24·C49·C57·C63·C162·C164, GDT D27). 상면·에지·단독 배치로 탈착 용이.',
        '★ Q9(BSS316NH6327)가 릴레이 코일(VCC_12V0=PGND 기준)의 저측을 1차 GND 로 당겨 절연 경계를 단락함. 이 상태로는 8.3.1/8.3.2 시험 불가 — 회로 수정 선행 필요.',
        '★ ISO1(ELD207) 리드스팬 4.6 mm < 보강 연면 8.0 mm. 8 mm 급 절연 광커플러로 교체 필요. ISO2/ISO3(MOC3063S)·ISO4(FOD817D3SD)는 10.16 mm 로 충족.',
    ]
    o.append(leg); o.append(notes('KS C 8560:2020 기반 배치 원칙 (상면)', nl, 490, Y(250)+30, 900))
    return wrap('\n'.join(o), 1420, Y(250)+30+30+15.5*len(nl)+40,
                'MICROINV V2000 — 250×250 배치 계획도 (TOP, 부품면)',
                'KS C 8560:2020 8.3.4 절연거리 · 8.5.4 온도 상승(표 13) · 8.3.1/8.3.2 시험 편의를 반영한 재배치안. 좌표는 초안이며 Allegro 에서 조정 전제.')

def bottom_view():
    o = [domains(True), grid(), zones(True)]
    for r in P:
        if mount(r) == 'THT': o.append(fp(r, True, lead=True))
    o.append(clusters(True, 'BOTTOM'))
    for r in P:
        if P[r]['side'] == 'BOTTOM': o.append(fp(r, True))
    o.append(text(X(125), Y(0)-24, '※ 하면에서 본 그림 (좌우 반전) — Allegro 하면 뷰(Mirror)와 동일 방향', size=10, fill='#7b241c', weight='bold'))
    o.append(text(X(mx(108,True)), Y(120), '히트싱크 A', size=11, fill='#922b21', weight='bold'))
    o.append(text(X(mx(108,True)), Y(127), '1차 FET 존 (PV 전위)', size=8, fill='#922b21'))
    o.append(text(X(mx(186,True)), Y(150), '히트싱크 B', size=11, fill='#922b21', weight='bold'))
    o.append(text(X(mx(186,True)), Y(157), '2차 SiC·언폴더 존 (PHV 전위)', size=8, fill='#922b21'))
    leg = legend([('#f5b7b1','#922b21','none','발열 高 SMT — 하면, 절연 서멀패드로 히트싱크 접촉'),
                  ('#ec7063','#c0392b','none','서멀패드 접촉 존 (존별 높이 통일 → 페데스탈)'),
                  ('url(#lead)','#c0392b','3 2','THT 리드 돌출 — 히트싱크 접촉 불가 (릴리프 포켓)'),
                  ('url(#dots)','#5d6d7e','2 2','하면 소형 SMD 군집 (게이트·스너버·PHV 캡)')], 24, Y(250)+30)
    nl = [
        '히트싱크를 1차용(A)·2차용(B) 2개로 분리. 하나의 금속 히트싱크가 절연 경계를 가로지르면 1차·2차가 서멀패드 2장을 통해 결합되어 보강절연이 성립하지 않음.',
        '분리가 불가능하면 단일 히트싱크를 PE(GND_EARTH)에 본딩하고, 1차↔히트싱크·2차↔히트싱크 각각을 기본절연(내전압 1 260 / 1 420 Vrms 1분)으로 설계.',
        '서멀패드 내전압: 2차측 ≥ 1 420 Vrms(8.3.2 출력측), 1차측 ≥ 1 260 Vrms(입력측). 여유 포함 4 kV 급 권장. 열전도 2~3 W/mK.',
        '존별 부품 높이: FET PQFN 1.0 / SiC D2PAK 4.5 / 언폴더 DPAK 2.4 · D2PAK 4.6 → 페데스탈 단차 또는 1~2 mm 갭필러로 흡수.',
        'THT 리드 돌출(빗금): 전해캡 12개는 눕힘이라 리드 끝단만 돌출, 트랜스 5개·초크 2·릴레이·필름캡·MOV·탭·헤더는 몸체 전체 폭으로 돌출 → 존과 겹치지 않게 배치함.',
        '하면 경계 통로(ㄴ자 8.0 mm)에도 동박·비아 금지. 히트싱크 절개선(슬롯)을 경계와 일치시켜 금속 경로를 끊을 것.',
        'PCB 자체 온도 한계 105 ℃(표 13). 존 바로 아래 내층 동박은 열확산용으로 쓰되, 경계 통로는 관통 금지.',
    ]
    o.append(leg); o.append(notes('하면 방열·절연 원칙', nl, 490, Y(250)+30, 900))
    return wrap('\n'.join(o), 1420, Y(250)+30+30+15.5*len(nl)+40,
                'MICROINV V2000 — 250×250 배치 계획도 (BOTTOM, 서멀패드면, 좌우 반전)',
                '발열 高 SMT 17개만 하면. 히트싱크는 절연 경계에서 1차용·2차용으로 분리.')

import os
os.makedirs('out2', exist_ok=True)
open('out2/ks_floorplan_top.svg','w',encoding='utf-8').write(top_view())
open('out2/ks_floorplan_bottom.svg','w',encoding='utf-8').write(bottom_view())

# ─── CSV + 배치 초안 ───
def key(r): return (re.match(r'[A-Z]+', r).group(0), int(re.search(r'\d+', r).group(0)))
rows = []
for ref in sorted(parts, key=key):
    p = parts[ref]; pg = p['pages'][0] if p['pages'] else 0
    placed = ref in P; sd = side(ref)
    if placed: cx, cy, zone = P[ref]['x'], P[ref]['y'], '개별 배치'
    else:
        c = [c for c in CLUSTERS if c[0] == pg and c[1] == sd] or [c for c in CLUSTERS if c[0] == pg]
        cx, cy, zone = ((c[0][2]+c[0][4])/2, (c[0][3]+c[0][5])/2, f'군집: {c[0][6]}') if c else ('', '', '')
    rows.append(dict(refdes=ref, page=pg, block=BLOCK.get(pg,''), part=p['part'], value=p['value'], psm=p['psm'],
                     mount=mount(ref), side=sd, heat=heat(ref), domain=domain(ref) if placed else 'PRI',
                     placement=zone, x_mm=cx, y_mm=cy, rot=P[ref]['rot'] if placed else '',
                     height_mm=HEIGHT.get(p['psm'], ''), nets=' '.join(n for n in part_nets(ref) if not re.match(r'^N\d+$', n))[:70]))
with open('out2/parts_classification.csv','w',newline='',encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
with open('out2/placement_draft_allegro.txt','w',encoding='utf-8') as f:
    f.write('# MICROINV V2000 placement draft (mm, origin = board lower-left, Y up). REFDES ! X Y ! ROT ! MIRROR\n')
    f.write('# KS C 8560:2020 기반 배치. Allegro File > Import > Placement 형식은 기존 보드 Export 파일과 대조 후 사용.\n')
    for ref in sorted(P, key=key):
        p = P[ref]
        f.write(f"{ref:<6s} ! {p['x']:9.3f} {BOARD - p['y']:9.3f} ! {p['rot']:7.3f} ! {'YES' if p['side']=='BOTTOM' else 'NO'}\n")
print('mount:', dict(collections.Counter(mount(r) for r in parts)))
print('side :', dict(collections.Counter(side(r) for r in parts)))
print('heat :', dict(collections.Counter(heat(r) for r in parts)))
print('개별 배치:', len(P), '| 경계 통과:', len(BARRIER_CROSS))
print('최대 부품 높이(상면):', max((HEIGHT.get(parts[r]['psm'], 0), r) for r in P if P[r]['side']=='TOP'))
