# -*- coding: utf-8 -*-
"""250 x 250 mm floorplan for the MICROINV V2000 netlist: SMT/THT split, thermal-pad (bottom) zones,
package-symbol outlines. Outputs: SVG/PNG drawings, parts classification CSV, Allegro placement draft, README."""
import re, collections, csv, math
from inv_parse import load

prims, parts, nets, _ = load('.')

# ---- pin -> net using PIN NUMBERS (netlist nodes use numbers) ----
pin2net = {}
for n, nodes in nets.items():
    for ref, pin in nodes:
        pin2net[(ref, pin)] = n
def part_nets(ref):
    out = set()
    for (pname, pnum, puse) in parts[ref]['pins']:
        for num in pnum.strip('()').split(','):
            n = pin2net.get((ref, num.strip()))
            if n: out.add(n)
    return out

BOARD = 250.0
BLOCK = {1: 'PV_A DC-DC (플라이백 A)', 2: 'PV_B DC-DC (플라이백 B)', 3: 'GRID (언폴더·AC 필터·릴레이·보호)',
         4: 'AUX 전원 (LM5156 플라이백)', 5: 'MCU (STM32G474)', 6: 'ESP32·TPM·USB·CAN',
         7: '센싱 (INA240·AMC3301/3302·OPA)', 8: '언폴더 게이트 로직 (2차측)', 9: '아날로그 컨디셔닝', 10: 'ADC 입력 보호'}

# ---- package outline sizes (w, h) in mm at rotation 0; 'circle' for radial ----
SIZE = {
 'SON127P515X548X100-8N': (6.6, 6.6), 'SOT254P1510X450-3N': (10.7, 15.6), 'SOT254P1524X457-3N': (10.7, 15.8),
 'SOT228P998X235-3N': (7.0, 10.2), 'SOT228P991X233-3M': (7.0, 10.2), 'XFMR185P838X721X550-8': (8.4, 7.2),
 'CAPPRD750W80D1800H4000': ('circle', 18.5), 'INDRR1850X900W80L2400T1300H2300': (24.0, 13.0),
 'RLYRR2500X750L2900T1350H2650': (29.0, 13.5), 'MPX154K31D2KN15800': (18.0, 8.0), 'MPX332K31C2KN15600': (26.5, 10.5),
 'MP2334K27D6X8LC': (12.0, 6.0), 'B32021A3472K000': (13.0, 5.0), 'B32922C3334K289': (18.0, 7.5), 'JW102M400VACP10': (12.0, 5.0),
 'CAPRR1500W80L1800T1000H1580': (18.0, 10.0), 'CAPRR1000W60L1300T500H1100': (13.0, 5.0),
 'MOV14D471K': (16.0, 5.5), 'MOV14D431K': (16.0, 5.5), 'MOV14D621K': (16.0, 5.5), '250T-1': (8.0, 5.0), 'FGND': ('circle', 8.0),
 '0678L9100-02': (10.5, 3.6), 'DOA-214AA': (5.6, 3.9), 'SL1411A600': (8.0, 6.0), 'DIOM8171X262N': (8.2, 6.2),
 'DIOM5639X245M': (5.6, 3.9), 'DIOM5639X245N': (5.6, 3.9), 'DIOM5329X245N': (5.6, 3.9), 'DIOM3517X100N': (3.6, 1.9),
 'DIOM3716X135N': (3.8, 1.8), 'DIOM2512X090N': (2.6, 1.4), 'SOD-123W': (3.6, 1.9), 'SOT95P240X100-3N': (3.0, 2.6),
 'SOT-23': (3.0, 2.6), 'sot-23': (3.0, 2.6), 'SOT95P264X112-3N': (3.0, 2.6), 'SOT65P210X110-6N': (2.3, 2.1),
 'SOP254P1016X385-6N': (10.2, 7.8), 'SOP254P1016X385-4N': (10.2, 5.2), 'ELD207': (4.6, 3.8), 'SOP65P490X104-9N': (6.0, 3.6),
 'SOP65P640X120-14N': (6.6, 5.2), 'SOP65P640X120-15N': (6.6, 5.2), 'SOIC127P600X173-8N': (6.2, 5.0), 'SOIC-8': (6.2, 5.0),
 'DSO-8': (6.2, 5.0), 'SOIC127P600X175-14N': (6.4, 8.9), 'SOIC-16': (10.6, 10.4), 'TSSOP-8': (6.6, 3.2), 'DQN-4': (1.6, 1.6),
 'LQFP-128': (16.4, 16.4), 'ESP32-S3': (18.0, 25.5), 'USB-C_16PIN': (9.0, 7.5), 'QFN50P500X500X85-33N': (5.2, 5.2),
 'XTALCC5032X130N': (5.2, 3.4), '4532': (4.6, 3.3), 'INDM7165X300N': (7.2, 6.6), 'SMD-4P_6x6': (6.2, 6.2),
 'hdr1x6_p2_54': (15.3, 2.6), 'hdr1x4_p2_54': (10.2, 2.6), 'hdr1x3_p2_54': (7.7, 2.6), 'hdr1x2_p2_54': (5.1, 2.6),
 '702461004': (13.0, 6.0), 'RESC6432': (8.0, 4.4),
}
# footprint area (mm^2, incl. spacing) for small passives drawn as clusters
PASSIVE_AREA = {'RESC1608': 6.0, 'CAPC1608': 6.0, 'c1608': 6.0, 'RT0603': 6.0, 'RESC2012': 7.7, 'CAPC2012': 7.7,
                'RESC3216': 11.4, 'CAPC3216': 11.4, 'CAPC1812': 24.0, 'BEADC1608X80N': 6.0}
THT_PSM = {'CAPPRD750W80D1800H4000', 'INDRR1850X900W80L2400T1300H2300', 'RLYRR2500X750L2900T1350H2650',
           'MPX154K31D2KN15800', 'MPX332K31C2KN15600', 'MP2334K27D6X8LC', 'B32021A3472K000', 'B32922C3334K289',
           'JW102M400VACP10', 'CAPRR1500W80L1800T1000H1580', 'CAPRR1000W60L1300T500H1100', 'MOV14D471K', 'MOV14D431K',
           'MOV14D621K', '250T-1', 'FGND', 'hdr1x6_p2_54', 'hdr1x4_p2_54', 'hdr1x3_p2_54', 'hdr1x2_p2_54', '702461004',
           'SL1411A600'}
HEIGHT = {'SON127P515X548X100-8N': 1.0, 'SOT254P1510X450-3N': 4.5, 'SOT254P1524X457-3N': 4.6, 'SOT228P998X235-3N': 2.4,
          'SOT228P991X233-3M': 2.4, 'XFMR185P838X721X550-8': 5.5, 'SOP65P490X104-9N': 1.1, 'RESC6432': 0.6}

# ---- placement of major parts: ref -> (x, y, rot, side, w_override, h_override) in TOP-view mm ----
P = {}
def put(ref, x, y, rot=0, side='TOP', w=None, h=None): P[ref] = dict(x=x, y=y, rot=rot, side=side, w=w, h=h)
# corners: frame-ground / mounting
put('J5', 8, 8); put('J10', 8, 242); put('J17', 242, 8); put('J18', 242, 242)
# --- control band (primary side) ---
put('U17', 35, 18.5); put('U18', 56, 6); put('TSW1', 66, 16); put('J22', 66, 25); put('U19', 52, 24)
put('J21', 81, 4); put('J19', 99.5, 4); put('J20', 116.5, 5.5); put('J23', 131, 4)
put('U20', 120, 14); put('L11', 128, 10); put('D39', 120, 21)
put('U16', 96, 26); put('Y1', 84, 35); put('U27', 110, 35)
put('C4', 11, 30, 90); put('C24', 22, 234)
# --- analog band ---
put('U2', 30, 58); put('U3', 44, 58); put('U10', 58, 58); put('U11', 72, 58); put('U12', 84, 58)
put('D42', 92, 58); put('D43', 98, 58); put('D44', 104, 58)
put('ISO1', 140, 48); put('ISO4', 140, 58)
# --- PV_A stage ---
for i, (ref, y) in enumerate([('J1', 80), ('J2', 92), ('J3', 116), ('J4', 128)]): put(ref, 4, y)
put('R6', 16, 122, 90); put('U21', 17, 108)
for ref, (x, y) in zip(['EC1', 'EC2', 'EC3', 'EC4', 'EC5', 'EC6'], [(34, 84), (54, 84), (34, 104), (54, 104), (34, 124), (54, 124)]): put(ref, x, y)
put('D2', 72, 78); put('C69', 72, 84); put('C70', 72, 92)
put('T1', 114, 82); put('T3', 114, 114)
put('Q1', 100, 78, 0, 'BOTTOM'); put('Q2', 100, 90, 0, 'BOTTOM'); put('Q3', 100, 108, 0, 'BOTTOM'); put('Q4', 100, 120, 0, 'BOTTOM')
put('U13', 100, 99, 0, 'BOTTOM')
put('T2', 134, 86, 0, 'TOP', 26, 22); put('T4', 134, 120, 0, 'TOP', 26, 22)
put('D3', 160, 86, 0, 'BOTTOM'); put('D8', 160, 120, 0, 'BOTTOM')
put('D4', 114, 92, 0, 'BOTTOM'); put('D9', 114, 106, 0, 'BOTTOM')
# --- aux band (primary side) ---
put('L12', 80, 149); put('U15', 94, 149); put('Q10', 108, 149); put('D29', 66, 142); put('D30', 66, 150)
put('T9', 140, 149, 0, 'TOP', 16, 14); put('ISO2', 140, 137); put('ISO3', 140, 161)
# --- PV_B stage ---
for ref, y in [('J6', 170), ('J7', 182), ('J8', 206), ('J9', 218)]: put(ref, 4, y)
put('R43', 16, 212, 90); put('U22', 17, 198)
for ref, (x, y) in zip(['EC7', 'EC8', 'EC9', 'EC10', 'EC11', 'EC12'], [(34, 174), (54, 174), (34, 194), (54, 194), (34, 214), (54, 214)]): put(ref, x, y)
put('D13', 72, 168)
put('T5', 114, 172); put('T7', 114, 204)
put('Q5', 100, 168, 0, 'BOTTOM'); put('Q6', 100, 180, 0, 'BOTTOM'); put('Q7', 100, 198, 0, 'BOTTOM'); put('Q8', 100, 210, 0, 'BOTTOM')
put('U14', 100, 189, 0, 'BOTTOM')
put('T6', 134, 176, 0, 'TOP', 26, 22); put('T8', 134, 210, 0, 'TOP', 26, 22)
put('D14', 160, 176, 0, 'BOTTOM'); put('D19', 160, 210, 0, 'BOTTOM')
put('D15', 114, 182, 0, 'BOTTOM'); put('D20', 114, 196, 0, 'BOTTOM')
put('C162', 60, 238); put('C164', 82, 238)
# --- barrier crossers at the bottom ---
put('U23', 140, 229); put('U24', 140, 241); put('C48', 156, 224)
# --- secondary logic (page 8) top side ---
put('U5', 156, 48); put('U6', 170, 48); put('U7', 182, 46); put('U8', 188, 46); put('U9', 194, 46)
put('U25', 178, 56); put('U26', 178, 62); put('D40', 156, 56); put('D41', 156, 63)
# --- unfolder (bottom) ---
put('D23', 176, 112, 0, 'BOTTOM'); put('D24', 176, 140, 0, 'BOTTOM'); put('Q12', 176, 126, 0, 'BOTTOM')
put('Q13', 194, 112, 0, 'BOTTOM'); put('Q14', 194, 140, 0, 'BOTTOM')
put('R200', 206, 108, 0, 'BOTTOM'); put('R201', 206, 114, 0, 'BOTTOM'); put('R211', 206, 138, 0, 'BOTTOM'); put('R212', 206, 144, 0, 'BOTTOM')
put('U1', 176, 126)  # top, gate logic for Q13/Q14
put('R79', 160, 110); put('R81', 160, 116); put('R188', 160, 122); put('R82', 160, 130); put('R83', 160, 136)
put('D25', 152, 150); put('D26', 158, 150); put('D27', 216, 150); put('D28', 176, 150); put('Q9', 182, 150)
# --- AC filter / output (top, mostly THT) ---
put('TH1', 188, 98); put('RV1', 200, 98); put('C46', 188, 88); put('C47', 204, 88)
put('C50', 196, 72); put('C51', 196, 80); put('L7', 196, 60); put('LS1', 226, 60)
put('F1', 226, 74); put('R90', 226, 80); put('C56', 226, 90); put('L8', 226, 108)
put('C53', 226, 122); put('C54', 226, 130); put('C58', 226, 138); put('C63', 226, 146); put('C49', 226, 154); put('C57', 226, 160)
put('RV3', 226, 168); put('RV4', 226, 175); put('RV5', 226, 182); put('RV2', 226, 189)
put('J11', 246, 96); put('J12', 246, 108); put('J15', 246, 128); put('J16', 246, 140); put('J13', 246, 160); put('J14', 246, 172)
put('R219', 226, 200); put('R228', 226, 206); put('F2', 236, 222); put('C52', 210, 200)
put('R96', 118, 142); put('R99', 118, 148); put('R100', 118, 154); put('R101', 30, 150); put('R106', 118, 160)
put('R10', 114, 99, 0, 'BOTTOM'); put('R30', 114, 126, 0, 'BOTTOM'); put('R47', 114, 189, 0, 'BOTTOM'); put('R67', 114, 216, 0, 'BOTTOM')

# ---- small-passive clusters: (page, side, x1, y1, x2, y2, label) ----
CLUSTERS = [
 (5, 'TOP', 74, 37, 124, 44.5, 'p5 MCU 주변 소형 SMD'),
 (6, 'TOP', 44, 30, 70, 42, 'p6 ESP32/TPM/CAN 소형 SMD'),
 (10, 'TOP', 124, 14, 136, 34, 'p10 ADC 보호 (ZD1-4 포함)'),
 (7, 'TOP', 26, 63, 110, 70, 'p7 센싱 소형 SMD'),
 (9, 'TOP', 112, 48, 136, 60, 'p9 아날로그 소형 SMD'),
 (1, 'BOTTOM', 76, 76, 91, 95, 'p1 게이트·스너버 (하면)'), (1, 'BOTTOM', 76, 103, 91, 122, 'p1 게이트·스너버 (하면)'),
 (1, 'BOTTOM', 170, 76, 182, 100, 'p1 PHV 캐패시터 (하면)'),
 (2, 'BOTTOM', 76, 166, 91, 185, 'p2 게이트·스너버 (하면)'), (2, 'BOTTOM', 76, 193, 91, 212, 'p2 게이트·스너버 (하면)'),
 (2, 'BOTTOM', 170, 154, 182, 220, 'p2 PHV 캐패시터 (하면)'),
 (4, 'TOP', 60, 154, 112, 160, 'p4 AUX 소형 SMD'), (4, 'TOP', 122, 138, 132, 160, 'p4 AUX 소형 SMD'),
 (8, 'TOP', 150, 40, 200, 44, 'p8 로직 소형 SMD'), (8, 'TOP', 150, 66, 188, 72, 'p8 로직 소형 SMD'),
 (3, 'TOP', 150, 156, 196, 166, 'p3 GRID 소형 SMD'), (3, 'BOTTOM', 170, 100, 182, 104, 'p3 C42/C43 (하면)'),
 (7, 'TOP', 150, 230, 196, 246, 'p7 그리드 센싱 분압 저항'),
]
# ---- thermal-pad contact zones on the BOTTOM (top-view coords): (x1,y1,x2,y2,label,height) ----
ZONES = [
 (92, 72, 108, 128, 'A-FET  Q1~Q4 + U13', '1.0 (PQFN)'), (153, 76, 167, 130, 'A-SiC D3/D8', '4.5 (D2PAK)'),
 (92, 162, 108, 218, 'B-FET  Q5~Q8 + U14', '1.0 (PQFN)'), (153, 166, 167, 220, 'B-SiC D14/D19', '4.5 (D2PAK)'),
 (170, 104, 212, 150, 'C-UNFOLD', 'DPAK 2.4 / D2PAK 4.6'),
]
BARRIER_X = 140.0
ANT_KEEPOUT = (20, 0, 50, 10)

# ---- classification ----
HIGH = {'Q1','Q2','Q3','Q4','Q5','Q6','Q7','Q8','Q12','Q13','Q14','D3','D8','D14','D19','D23','D24','T2','T4','T6','T8'}
MED = {'Q10','T9','U13','U14','U15','L12','D4','D9','D15','D20','D2','D13','R6','R43','R79','R81','R188','R82','R83','R90','R96','R106',
       'R200','R201','R211','R212','R219','R228','L7','L8','LS1','D25','D26','TH1','RV1','RV2','RV3','RV4','RV5','T1','T3','T5','T7'} | {f'EC{i}' for i in range(1, 13)}
THT_REFS = {'T2', 'T4', 'T6', 'T8', 'T9'}  # DIP 타입 트랜스포머 (사용자 확인)
def mount(ref):
    psm = parts[ref]['psm']
    if psm in THT_PSM or ref in THT_REFS: return 'THT'
    if psm == 'USB-C_16PIN': return 'SMT(+THT 고정핀)'
    return 'SMT'
def heat(ref):
    return 'H' if ref in HIGH else ('M' if ref in MED else 'L')
def side(ref):
    if ref in P: return P[ref]['side']
    return 'TOP'
def size_of(ref):
    p = P.get(ref, {})
    psm = parts[ref]['psm']
    s = SIZE.get(psm, (4.0, 3.0))
    if p.get('w'): s = (p['w'], p['h'])
    return s

# ---- SVG helpers ----
SC = 5.0; OX, OY = 60, 90
def X(mm): return OX + mm * SC
def Y(mm): return OY + mm * SC
def esc(s): return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
FONT = "Noto Sans KR, Apple SD Gothic Neo, Arial, sans-serif"
def text(x, y, s, size=9, anchor='middle', weight='normal', fill='#111', rot=0):
    tf = f' transform="rotate({rot} {x:.1f} {y:.1f})"' if rot else ''
    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" font-weight="{weight}" fill="{fill}" font-family="{FONT}"{tf}>{esc(s)}</text>'
def rect_px(x, y, w, h, **kw):
    st = ' '.join(f'{k.replace("_", "-")}="{v}"' for k, v in kw.items())
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" {st}/>'
def line_px(x1, y1, x2, y2, **kw):
    st = ' '.join(f'{k.replace("_", "-")}="{v}"' for k, v in kw.items())
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" {st}/>'
def circ_px(cx, cy, r, **kw):
    st = ' '.join(f'{k.replace("_", "-")}="{v}"' for k, v in kw.items())
    return f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" {st}/>'

def mx(x, mirror): return (BOARD - x) if mirror else x

def draw_part(ref, mirror, ghost=False, tht_mark=False):
    p = P[ref]; psm = parts[ref]['psm']; s = size_of(ref)
    x = mx(p['x'], mirror); y = p['y']
    out = []
    is_tht = mount(ref) == 'THT'
    if ghost:
        fill, stroke, op, dash = 'none', '#7f8c8d', 0.55, '4 3'
    elif tht_mark:
        fill, stroke, op, dash = 'url(#lead)', '#c0392b', 0.9, '3 2'
    else:
        if heat(ref) == 'H': fill, stroke = '#f5b7b1', '#922b21'
        elif heat(ref) == 'M': fill, stroke = '#fad7a0', '#9c640c'
        else: fill, stroke = '#d6eaf8' if not is_tht else '#d5f5e3', '#1b4f72' if not is_tht else '#196f3d'
        op, dash = 1.0, ('6 3' if is_tht else 'none')
    if s[0] == 'circle':
        r = s[1] / 2
        out.append(circ_px(X(x), Y(y), r * SC, fill=fill, stroke=stroke, stroke_width=1.4, fill_opacity=op, stroke_opacity=op, stroke_dasharray=dash))
        if psm == 'FGND':
            out.append(circ_px(X(x), Y(y), 1.6 * SC, fill='#fff', stroke=stroke, stroke_width=1))
        elif not ghost:  # radial cap: pins
            for dy in (-3.75, 3.75):
                out.append(circ_px(X(x), Y(y + dy), 0.8 * SC, fill='#fff', stroke=stroke, stroke_width=1))
            out.append(text(X(x), Y(y) + 3, ref, size=8, weight='bold', fill='#1b2631'))
        else:
            out.append(text(X(x), Y(y) + 3, ref, size=8, fill='#7f8c8d'))
        return '\n'.join(out)
    w, h = s
    if p['rot'] in (90, 270): w, h = h, w
    out.append(rect_px(X(x - w / 2), Y(y - h / 2), w * SC, h * SC, fill=fill, stroke=stroke, stroke_width=1.4, fill_opacity=op, stroke_opacity=op, stroke_dasharray=dash, rx=1))
    if not ghost and not tht_mark and psm in ('SOT254P1510X450-3N', 'SOT254P1524X457-3N', 'SOT228P998X235-3N', 'SOT228P991X233-3M'):
        # tab (drain/cathode) at the top, 2 leads at the bottom
        out.append(rect_px(X(x - w / 2 + 0.6), Y(y - h / 2 + 0.6), (w - 1.2) * SC, h * 0.45 * SC, fill='#e6b0aa', stroke=stroke, stroke_width=0.8))
        for dx in (-w / 4, w / 4):
            out.append(rect_px(X(x + dx - 0.6), Y(y + h / 2 - 2.2), 1.2 * SC, 1.8 * SC, fill='#e6b0aa', stroke=stroke, stroke_width=0.8))
    if not ghost and not tht_mark and psm == 'SON127P515X548X100-8N':
        out.append(rect_px(X(x - 2.0), Y(y - 2.6), 4.0 * SC, 4.2 * SC, fill='#e6b0aa', stroke=stroke, stroke_width=0.8))
    if not ghost and not tht_mark and psm == '250T-1':
        out.append(rect_px(X(x - (w / 2 + 2.5) if not mirror else x + w / 2 - 0.5), Y(y - 1.2), 3.0 * SC, 2.4 * SC, fill='#aab7b8', stroke='#566573', stroke_width=0.8))
    if not ghost and not tht_mark and ref in THT_REFS:
        n = parts[ref]['npins']; per_side = max(2, n // 2)
        for i in range(per_side):
            py = y - (per_side - 1) * 2.5 / 2 + i * 2.5
            for px in (x - w / 2 + 2.0, x + w / 2 - 2.0):
                out.append(circ_px(X(px), Y(py), 0.9 * SC, fill='#fff', stroke=stroke, stroke_width=1))
        out.append(text(X(x - w / 2 + 2.0), Y(y - h / 2) - 3, '1차', size=6, fill='#7d6608'))
        out.append(text(X(x + w / 2 - 2.0), Y(y - h / 2) - 3, '2차', size=6, fill='#7d6608'))
    if not ghost and not tht_mark and psm == 'ESP32-S3':
        out.append(rect_px(X(x - w / 2), Y(y - h / 2), w * SC, 6.0 * SC, fill='#f9e79f', stroke=stroke, stroke_width=0.8))
        out.append(text(X(x), Y(y - h / 2 + 4), '안테나', size=7, fill='#7d6608'))
    lab = ref if (w * SC >= 22 and h * SC >= 10) or ghost else ref
    size = 8 if w * SC >= 30 else 7
    col = '#7f8c8d' if ghost else '#1b2631'
    if w * SC < 16 and h * SC >= 16:
        out.append(text(X(x), Y(y), lab, size=size, weight='bold', fill=col, rot=-90))
    else:
        out.append(text(X(x), Y(y) + 3, lab, size=size, weight='bold', fill=col))
    if not ghost and not tht_mark and (w * SC >= 40 and h * SC >= 26):
        v = parts[ref]['value'][:22]
        out.append(text(X(x), Y(y) + 12, v, size=6.5, fill='#566573'))
    return '\n'.join(out)

def grid(title_units=True):
    out = []
    for i in range(0, 251, 10):
        major = i % 50 == 0
        out.append(line_px(X(i), Y(0), X(i), Y(250), stroke='#d5d8dc' if major else '#eef0f2', stroke_width=1 if major else 0.6))
        out.append(line_px(X(0), Y(i), X(250), Y(i), stroke='#d5d8dc' if major else '#eef0f2', stroke_width=1 if major else 0.6))
        if major:
            out.append(text(X(i), Y(0) - 6, str(i), size=9, fill='#7f8c8d'))
            out.append(text(X(0) - 8, Y(i) + 3, str(i), size=9, fill='#7f8c8d', anchor='end'))
    out.append(rect_px(X(0), Y(0), 250 * SC, 250 * SC, fill='none', stroke='#b7950b', stroke_width=3))
    return '\n'.join(out)

def cluster_svg(mirror, which_side):
    out = []
    for (pg, sd, x1, y1, x2, y2, lab) in CLUSTERS:
        if sd != which_side: continue
        a, b = mx(x1, mirror), mx(x2, mirror)
        xa, xb = min(a, b), max(a, b)
        out.append(rect_px(X(xa), Y(y1), (xb - xa) * SC, (y2 - y1) * SC, fill='url(#dots)', stroke='#5d6d7e', stroke_width=1, stroke_dasharray='2 2'))
        cx, cy = (xa + xb) / 2, (y1 + y2) / 2
        out.append(text(X(cx), Y(cy) + 3, lab, size=6.5, fill='#34495e'))
    return '\n'.join(out)

def barrier_svg(mirror):
    bx = mx(BARRIER_X, mirror)
    out = [rect_px(X(bx - 4), Y(0), 8 * SC, 250 * SC, fill='#f4d03f', fill_opacity=0.18, stroke='none'),
           line_px(X(bx), Y(0), X(bx), Y(250), stroke='#b7950b', stroke_width=2, stroke_dasharray='10 5'),
           text(X(bx), Y(250) + 16, '절연 경계 (1차: PV·제어 GND | 2차: PHV·AC PGND) — 강화절연 ≥ 8 mm, 트랜스·옵토·AMC만 통과', size=9, fill='#7d6608', weight='bold')]
    return '\n'.join(out)

def zones_svg(mirror):
    out = []
    for (x1, y1, x2, y2, lab, hgt) in ZONES:
        a, b = mx(x1, mirror), mx(x2, mirror)
        xa, xb = min(a, b), max(a, b)
        out.append(rect_px(X(xa), Y(y1), (xb - xa) * SC, (y2 - y1) * SC, fill='#ec7063', fill_opacity=0.16, stroke='#c0392b', stroke_width=2))
        out.append(text(X((xa + xb) / 2), Y(y1) - 4, f'{lab}  h={hgt}', size=7.5, fill='#922b21', weight='bold'))
    return '\n'.join(out)

DEFS = '''<defs>
<pattern id="dots" patternUnits="userSpaceOnUse" width="6" height="6"><circle cx="3" cy="3" r="1" fill="#5d6d7e" fill-opacity="0.6"/></pattern>
<pattern id="lead" patternUnits="userSpaceOnUse" width="7" height="7" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="7" stroke="#c0392b" stroke-width="1.5" stroke-opacity="0.8"/></pattern>
<pattern id="keep" patternUnits="userSpaceOnUse" width="7" height="7" patternTransform="rotate(-45)"><line x1="0" y1="0" x2="0" y2="7" stroke="#7d6608" stroke-width="1.2" stroke-opacity="0.7"/></pattern>
<marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#17a589"/></marker>
</defs>'''

def legend(items, x, y, w=420):
    out = [rect_px(x, y, w, 20 + 17 * len(items), fill='#fff', stroke='#bdc3c7', rx=6)]
    for i, (fill, stroke, dash, lab) in enumerate(items):
        yy = y + 14 + i * 17
        out.append(rect_px(x + 10, yy - 6, 26, 12, fill=fill, stroke=stroke, stroke_width=1.4, stroke_dasharray=dash))
        out.append(text(x + 44, yy + 4, lab, size=9, anchor='start'))
    return '\n'.join(out)

def notes_box(title, lines, x, y, w):
    out = [rect_px(x, y, w, 30 + 15.5 * len(lines), fill='#fbfcfc', stroke='#bdc3c7', rx=6),
           text(x + 12, y + 18, title, size=11, weight='bold', anchor='start')]
    for i, ln in enumerate(lines):
        out.append(text(x + 12, y + 37 + i * 15.5, ln, size=9, anchor='start', fill='#2c3e50'))
    return '\n'.join(out)

def flow_svg(mirror):
    out = []
    def arrow(x1, y1, x2, y2):
        return line_px(X(mx(x1, mirror)), Y(y1), X(mx(x2, mirror)), Y(y2), stroke='#17a589', stroke_width=2.5, marker_end='url(#arrow)', stroke_opacity=0.85)
    out += [arrow(14, 104, 26, 104), arrow(64, 104, 90, 104), arrow(110, 104, 118, 104), arrow(150, 104, 168, 104),
            arrow(14, 194, 26, 194), arrow(64, 194, 90, 194), arrow(110, 194, 118, 194), arrow(150, 194, 168, 194),
            line_px(X(mx(168, mirror)), Y(86), X(mx(168, mirror)), Y(210), stroke='#17a589', stroke_width=2.5, stroke_opacity=0.85),
            arrow(168, 126, 172, 126)]
    labs = [(20, 100, 'PV_A'), (20, 190, 'PV_B'), (78, 100, '입력 캐패시터'), (128, 104, '플라이백'), (160, 104, 'PHV'), (160, 194, 'PHV')]
    for (x, y, lab) in labs:
        out.append(text(X(mx(x, mirror)), Y(y) - 5, lab, size=7.5, fill='#0e6655', weight='bold'))
    return '\n'.join(out)

def wrap(body, w, h, title, sub):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" font-family="{FONT}">
<rect width="100%" height="100%" fill="#fff"/>{DEFS}
{text(24, 34, title, size=18, weight='bold', anchor='start')}
{text(24, 56, sub, size=10.5, anchor='start', fill='#7b241c')}
{body}</svg>'''

def top_view():
    parts_svg = []
    parts_svg.append(grid())
    kx, ky, kx2, ky2 = ANT_KEEPOUT
    parts_svg.append(rect_px(X(kx), Y(ky), (kx2 - kx) * SC, (ky2 - ky) * SC, fill='url(#keep)', stroke='#7d6608', stroke_width=1))
    parts_svg.append(text(X((kx + kx2) / 2), Y(ky2) + 9, '안테나 키프아웃', size=7, fill='#7d6608'))
    parts_svg.append(barrier_svg(False))
    # bottom parts as ghosts first
    for ref in P:
        if P[ref]['side'] == 'BOTTOM': parts_svg.append(draw_part(ref, False, ghost=True))
    parts_svg.append(cluster_svg(False, 'TOP'))
    for ref in P:
        if P[ref]['side'] == 'TOP': parts_svg.append(draw_part(ref, False))
    parts_svg.append(flow_svg(False))
    # band labels
    for (y1, y2, lab) in [(4, 44, '제어: STM32·ESP32·TPM·USB·CAN·헤더'), (46, 70, '아날로그'), (72, 136, 'PV_A 입력 · 플라이백 A'),
                     (138, 160, 'AUX 전원'), (162, 226, 'PV_B 입력 · 플라이백 B'), (228, 248, 'Y-캡 · 센싱')]:
        parts_svg.append(line_px(X(0) - 22, Y(y1), X(0) - 22, Y(y2), stroke='#1a5276', stroke_width=3, stroke_opacity=0.5))
        parts_svg.append(text(X(0) - 28, Y((y1 + y2) / 2), lab, size=8, anchor='middle', fill='#1a5276', weight='bold', rot=-90))
    for (x, y, lab) in [(150, 30, '2차측 게이트 로직 (p8)'), (150, 75.5, 'PHV 정류 (하면 D3/D8, D14/D19)'), (204, 38, 'AC 필터·릴레이·보호 (THT, 상면)'), (150, 220, '그리드 센싱 (AMC3301/3302, 절연 경계)')]:
        parts_svg.append(text(X(x), Y(y), lab, size=7.5, anchor='start', fill='#1a5276', weight='bold'))
    leg = legend([('#f5b7b1', '#922b21', 'none', '발열 高 SMT → 하면, 서멀패드 접촉 (상면도에서는 점선 고스트) / 트랜스는 DIP 상면'),
                  ('#fad7a0', '#9c640c', 'none', '발열 中 → 상면, 동박·비아로 방열'),
                  ('#d6eaf8', '#1b4f72', 'none', 'SMT 일반 (상면)'),
                  ('#d5f5e3', '#196f3d', '6 3', 'THT(DIP) 부품 — 점선 외곽, 리드가 하면으로 돌출'),
                  ('none', '#7f8c8d', '4 3', '하면 부품 고스트 (X-ray)'),
                  ('url(#dots)', '#5d6d7e', '2 2', '소형 SMD(0603/0805/1206) 군집 — 면적 환산')], 24, Y(250) + 30)
    notes = [
        '보드 250 × 250 mm, 4 코너 M3 (J5/J10/J17/J18 = FGND 프레임 접지 패드 겸용).  좌측 에지 PV_A/PV_B Faston 탭, 우측 에지 AC L/N/PE 탭.',
        '전력 흐름 좌→우: PV 탭 → 입력 전해캡(THT, 18×40) → 플라이백(하면 FET·트랜스·SiC) → PHV → 언폴더(하면) → CM 초크·X/Y캡·릴레이·퓨즈(THT) → AC 탭.',
        '절연 경계 x=140: T2/T4/T6/T8/T9, ISO1~4, U23/U24 만 경계에 걸침. ESP32 안테나는 보드 에지 밖으로 향하게, 금속 케이스면 외부 안테나 검토.',
        '트랜스 T2/T4/T6/T8(26×22) · T9(16×14) 는 DIP 타입으로 상면 실장 (자리표시 크기, 실제 풋프린트로 교체). 1차 핀은 하면 FET 쪽(좌), 2차 핀은 SiC 쪽(우)으로 향하게.',
        '트랜스 코어 방열: 상면이므로 서멀패드가 아니라 상부 커버 갭필러/포팅으로 처리. 리드가 하면으로 돌출하므로 하면 히트싱크는 트랜스 영역을 피함.',
    ]
    parts_svg.append(leg)
    parts_svg.append(notes_box('배치 원칙 (상면)', notes, 470, Y(250) + 30, 880))
    return wrap('\n'.join(parts_svg), 1380, Y(250) + 30 + 30 + 15.5 * len(notes) + 40,
                'MICROINV V2000 — 250×250 배치 계획도 (TOP, 부품면, PSM 외형 기준)',
                '넷리스트(pstxprt/pstchip/pstxnet 2026-09-21) 기준 651부품. 굵은 외곽 = 실제 패키지 크기, 소형 SMD는 군집으로 면적 환산. 좌표는 배치 초안이며 Allegro에서 조정 전제.')

def bottom_view():
    parts_svg = [grid()]
    parts_svg.append(barrier_svg(True))
    parts_svg.append(zones_svg(True))
    # THT lead protrusion areas (mirrored)
    for ref in P:
        if mount(ref) == 'THT': parts_svg.append(draw_part(ref, True, tht_mark=True))
    parts_svg.append(cluster_svg(True, 'BOTTOM'))
    for ref in P:
        if P[ref]['side'] == 'BOTTOM': parts_svg.append(draw_part(ref, True))
    parts_svg.append(text(X(125), Y(0) - 22, '※ 하면에서 본 그림 (좌우 반전). Allegro 하면 뷰(Mirror)와 동일 방향.', size=10, fill='#7b241c', weight='bold'))
    leg = legend([('#f5b7b1', '#922b21', 'none', '발열 高 SMT — 하면, 서멀패드/히트싱크 직접 접촉'),
                  ('#ec7063', '#c0392b', 'none', '서멀패드 접촉 존 (존별 부품 높이 통일 → 히트싱크 페데스탈 높이)'),
                  ('url(#lead)', '#c0392b', '3 2', 'THT 리드 돌출 영역 — 히트싱크 접촉 불가 (릴리프 포켓 또는 회피)'),
                  ('url(#dots)', '#5d6d7e', '2 2', '하면 소형 SMD 군집 (게이트 저항·스너버·PHV 캡) — 존 밖에 배치')], 24, Y(250) + 30)
    notes = [
        '존 A/B: FET(Q1~4, Q5~8) h=1.0 과 SiC D2PAK h=4.5 로 높이가 다르므로 존별로 히트싱크 페데스탈 높이를 달리하거나 갭필러 두께로 흡수 (1.0~2.0 mm 권장).',
        '트랜스 T2/T4/T6/T8/T9 는 DIP 로 상면 실장 → 하면에는 리드만 돌출(빗금). FET 존과 SiC 존 사이의 이 영역은 히트싱크 릴리프 포켓 처리.',
        '존 C 언폴더: D23/D24/Q12 DPAK(2.4)와 Q13/Q14 D2PAK(4.6) 혼재 → 두 단 페데스탈. 소스 션트 R200/201, R211/212 는 Q13/Q14 바로 옆(존 안, h 0.6).',
        'THT 부품(전해캡 12개, 트랜스 5개, 초크 2, 릴레이, 필름캡, MOV, 탭, 헤더) 리드는 하면으로 1~2 mm 돌출 → 빗금 영역은 히트싱크와 접촉 불가. 존과 겹치지 않도록 배치함.',
        'PQFN(IAUCN10S7L040)·D2PAK·DPAK 는 노출 패드가 하면 동박에 납땜되므로 그 동박을 절연 서멀패드(예: 2~3 W/mK, 내전압 ≥ 4 kV) 로 히트싱크에 접촉. PHV/드레인 전위 → 절연 필수.',
        'FET 4개(채널당 2 트랜스 × 2 FET)는 트랜스 1차 핀 바로 아래쪽 하면, 게이트 드라이버 U13/U14 는 FET 중앙(하면). 드라이버↔게이트 ≤ 15 mm, FET↔트랜스 1차 핀 ≤ 20 mm.',
    ]
    parts_svg.append(leg)
    parts_svg.append(notes_box('하면 서멀패드 실장 원칙', notes, 470, Y(250) + 30, 880))
    return wrap('\n'.join(parts_svg), 1380, Y(250) + 30 + 30 + 15.5 * len(notes) + 40,
                'MICROINV V2000 — 250×250 배치 계획도 (BOTTOM, 서멀패드면, 좌우 반전)',
                '발열 高 SMT 부품만 하면 실장 (트랜스는 DIP 로 상면). 빨간 존 = 히트싱크 접촉면, 빗금 = THT 리드 돌출로 접촉 불가 영역.')

open('out/floorplan_top.svg', 'w', encoding='utf-8').write(top_view())
open('out/floorplan_bottom.svg', 'w', encoding='utf-8').write(bottom_view())

# ---- parts classification CSV + summary ----
def key(r): return (re.match(r'[A-Z]+', r).group(0), int(re.search(r'\d+', r).group(0)))
rows = []
for ref in sorted(parts, key=key):
    p = parts[ref]; pg = p['pages'][0] if p['pages'] else 0
    placed = ref in P
    sd = side(ref)
    if not placed:
        # cluster centroid by page/side
        cands = [c for c in CLUSTERS if c[0] == pg and c[1] == sd]
        if not cands: cands = [c for c in CLUSTERS if c[0] == pg]
        cx = cy = ''
        if cands:
            c = cands[0]; cx, cy = (c[2] + c[3 + 1]) / 2, (c[3] + c[5]) / 2
        zone = f'군집: {cands[0][6]}' if cands else ''
    else:
        cx, cy = P[ref]['x'], P[ref]['y']; zone = '개별 배치'
    rows.append(dict(refdes=ref, page=pg, block=BLOCK.get(pg, ''), part=p['part'], value=p['value'], psm=p['psm'],
                     mount=mount(ref), side=sd, heat=heat(ref), placement=zone, x_mm=cx, y_mm=cy,
                     rot=P[ref]['rot'] if placed else '', nets=' '.join(sorted(n for n in part_nets(ref) if not re.match(r'^N\d+$', n)))[:80]))
with open('out/parts_classification.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

# Allegro placement draft (mm, top-view coords; MIRROR=YES for bottom)
with open('out/placement_draft_allegro.txt', 'w', encoding='utf-8') as f:
    f.write('# MICROINV V2000 placement draft (units mm, origin = board lower-left, Y up). Format: REFDES ! X Y ! ROT ! MIRROR\n')
    f.write('# Allegro File > Import > Placement 형식에 맞춰 기존 보드에서 Export 한 파일과 대조 후 사용.\n')
    for ref in sorted(P, key=key):
        p = P[ref]
        f.write(f"{ref:<6s} ! {p['x']:9.3f} {BOARD - p['y']:9.3f} ! {p['rot']:7.3f} ! {'YES' if p['side']=='BOTTOM' else 'NO'}\n")

# summary stats
tot = collections.Counter(); heat_c = collections.Counter(); side_c = collections.Counter()
for r in rows:
    tot[r['mount']] += 1; heat_c[r['heat']] += 1; side_c[r['side']] += 1
tht_list = [r['refdes'] for r in rows if r['mount'] == 'THT']
bottom_list = [r['refdes'] for r in rows if r['side'] == 'BOTTOM' and r['placement'] == '개별 배치']
cluster_area = collections.defaultdict(float); cluster_n = collections.Counter()
for r in rows:
    if r['placement'].startswith('군집'):
        cluster_area[(r['page'], r['side'])] += PASSIVE_AREA.get(r['psm'], 8.0); cluster_n[(r['page'], r['side'])] += 1
print('unplaced/unclustered:', [r['refdes'] for r in rows if not r['placement']]); print('mount:', dict(tot)); print('heat:', dict(heat_c)); print('side:', dict(side_c))
print('THT parts (%d):' % len(tht_list), ' '.join(tht_list))
print('BOTTOM individually placed (%d):' % len(bottom_list), ' '.join(bottom_list))
print('cluster areas (page, side) -> n, mm2:')
for k in sorted(cluster_area): print('  ', k, cluster_n[k], round(cluster_area[k]))
area_major = 0.0
for ref in P:
    s = size_of(ref)
    area_major += (math.pi * (s[1] / 2) ** 2) if s[0] == 'circle' else s[0] * s[1]
print('major parts placed:', len(P), 'footprint area mm2:', round(area_major), ' clusters mm2:', round(sum(cluster_area.values())))
