# -*- coding: utf-8 -*-
"""Sample placement / routing drawings for a CAN interface block (top view, mm).
Generates two SVGs. All parts are EXAMPLE parts, not taken from the user's schematic."""
import math

SC = 27.0          # px per mm
OX, OY = 70, 120   # drawing origin (px) for mm (0,0)
W_MM, H_MM = 44.0, 24.0

def X(mm): return OX + mm * SC
def Y(mm): return OY + mm * SC

# ---------------- footprints (package symbols) ----------------
# pad: (num, cx, cy, w, h, net, kind) kind='smd'|'th'
def soic8(ref, cx, cy, nets):
    pads = []
    for i in range(4):
        y = cy - 1.905 + 1.27 * i
        pads.append((i + 1, cx - 2.7, y, 1.55, 0.6, nets[i + 1], 'smd'))
        pads.append((8 - i, cx + 2.7, y, 1.55, 0.6, nets[8 - i], 'smd'))
    return dict(ref=ref, cx=cx, cy=cy, bw=4.9, bh=3.9, pads=pads, pin1=(cx - 2.7, cy - 1.905))

def r0603(ref, cx, cy, vertical, n1, n2):
    if vertical:
        pads = [(1, cx, cy - 0.8, 1.0, 0.9, n1, 'smd'), (2, cx, cy + 0.8, 1.0, 0.9, n2, 'smd')]
        return dict(ref=ref, cx=cx, cy=cy, bw=0.8, bh=1.6, pads=pads)
    pads = [(1, cx - 0.8, cy, 0.9, 1.0, n1, 'smd'), (2, cx + 0.8, cy, 0.9, 1.0, n2, 'smd')]
    return dict(ref=ref, cx=cx, cy=cy, bw=1.6, bh=0.8, pads=pads)

FP = {}
FP['U1'] = soic8('U1', 8.0, 11.0, {1: 'TXD', 2: 'GND', 3: 'VCC', 4: 'RXD', 5: 'VIO', 6: 'CANL_T', 7: 'CANH_T', 8: 'STB'})
FP['C1'] = r0603('C1', 3.3, 11.0, True, 'GND', 'VCC')
FP['L1'] = dict(ref='L1', cx=19.5, cy=11.0, bw=4.5, bh=3.2, pin1=(17.5, 9.4), pads=[
    (1, 17.5, 9.4, 1.2, 1.0, 'CANH_T', 'smd'), (2, 17.5, 12.6, 1.2, 1.0, 'CANL_T', 'smd'),
    (3, 21.5, 12.6, 1.2, 1.0, 'CAN_L', 'smd'), (4, 21.5, 9.4, 1.2, 1.0, 'CAN_H', 'smd')])
FP['R1'] = r0603('R1', 24.0, 10.2, True, 'CAN_H', 'TERM_MID')
FP['R2'] = r0603('R2', 25.4, 11.8, True, 'TERM_MID', 'CAN_L')
FP['C3'] = r0603('C3', 27.4, 11.0, False, 'TERM_MID', 'GND')
FP['D1'] = dict(ref='D1', cx=33.0, cy=11.0, bw=1.3, bh=2.9, pin1=(32.0, 10.05), pads=[
    (1, 32.0, 10.05, 1.0, 1.0, 'CAN_H', 'smd'), (2, 32.0, 11.95, 1.0, 1.0, 'CAN_L', 'smd'),
    (3, 34.0, 11.0, 1.0, 1.0, 'GND', 'smd')])
FP['J1'] = dict(ref='J1', cx=39.5, cy=11.0, bw=2.54, bh=7.62, pin1=(39.5, 8.46), pads=[
    (1, 39.5, 8.46, 1.7, 1.0, 'CAN_H', 'th'), (2, 39.5, 11.0, 1.7, 1.0, 'GND', 'th'),
    (3, 39.5, 13.54, 1.7, 1.0, 'CAN_L', 'th')])
BOARD_EDGE_X = 42.0

VALUES = {
    'U1': 'CAN 트랜시버 SOIC-8\n(예: TJA1051T/3, MCP2562)',
    'C1': '100 nF 0603', 'L1': 'CMC 51 µH 4.5×3.2\n(예: ACT45B)',
    'R1': '60.4 Ω 0603', 'R2': '60.4 Ω 0603', 'C3': '4.7 nF 0603',
    'D1': 'CAN TVS SOT-23\n(예: PESD1CAN)', 'J1': '커넥터 3핀 2.54\n(DB9면 2=L, 7=H, 3=GND)',
}

# ---------------- routing ----------------
# (net, width_mm, layer, points)  layer: 'TOP' or 'INNER'
ROUTES = [
    ('CANH_T', 0.30, 'TOP', [(10.7, 10.365), (11.6, 10.365), (12.565, 9.4), (17.5, 9.4)]),
    ('CANL_T', 0.30, 'TOP', [(10.7, 11.635), (11.6, 11.635), (12.565, 12.6), (17.5, 12.6)]),
    ('CAN_H', 0.30, 'TOP', [(21.5, 9.4), (30.0, 9.4), (30.65, 10.05), (32.0, 10.05)]),
    ('CAN_L', 0.30, 'TOP', [(21.5, 12.6), (30.0, 12.6), (30.65, 11.95), (32.0, 11.95)]),
    ('CAN_H', 0.30, 'TOP', [(32.0, 10.05), (32.5, 10.05), (34.09, 8.46), (39.5, 8.46)]),
    ('CAN_L', 0.30, 'TOP', [(32.0, 11.95), (32.5, 11.95), (34.09, 13.54), (39.5, 13.54)]),
    ('TERM_MID', 0.30, 'TOP', [(24.0, 11.0), (26.6, 11.0)]),
    ('GND', 0.30, 'TOP', [(28.2, 11.0), (29.3, 11.0)]),
    ('GND', 0.50, 'TOP', [(34.0, 11.0), (39.5, 11.0)]),
    ('GND', 0.50, 'TOP', [(2.4, 10.2), (3.3, 10.2)]),
    ('GND', 0.40, 'TOP', [(3.3, 10.2), (5.3, 10.365)]),
    ('VCC', 0.50, 'TOP', [(2.4, 11.8), (3.3, 11.8), (5.3, 11.635)]),
    ('VCC', 0.50, 'INNER', [(2.4, 11.8), (2.4, 15.2), (0.4, 15.2)]),
    ('TXD', 0.20, 'TOP', [(5.3, 9.095), (0.4, 9.095)]),
    ('RXD', 0.20, 'TOP', [(5.3, 12.905), (0.4, 12.905)]),
    ('STB', 0.20, 'TOP', [(10.7, 9.095), (10.7, 7.3), (9.9, 6.5), (0.4, 6.5)]),
]
VIAS = [  # (x, y, net)
    (2.4, 10.2, 'GND'), (2.4, 11.8, 'VCC'), (29.3, 11.0, 'GND'), (34.9, 11.0, 'GND'),
    (19.5, 7.2, 'GND'), (19.5, 14.8, 'GND'), (36.8, 7.0, 'GND'), (36.8, 15.0, 'GND'),
]
VIA_D, VIA_DRILL = 0.6, 0.3
GND_SHAPES = [  # top-layer copper pours (x1,y1,x2,y2)
    (30.4, 5.5, 42.0, 16.5),
]

NET_COLOR = {'CAN_H': '#d35400', 'CAN_L': '#d35400', 'CANH_T': '#d35400', 'CANL_T': '#d35400',
             'VCC': '#c0392b', 'GND': '#1e8449', 'TERM_MID': '#8e44ad',
             'TXD': '#2471a3', 'RXD': '#2471a3', 'STB': '#2471a3', 'VIO': '#7f8c8d'}

def seg_len(pts):
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))

# ---------------- svg helpers ----------------
def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def text(x, y, s, size=11, anchor='middle', weight='normal', fill='#111', rot=0, family='sans'):
    tf = f' transform="rotate({rot} {x:.1f} {y:.1f})"' if rot else ''
    lines = s.split('\n')
    out = []
    for i, ln in enumerate(lines):
        dy = 0 if i == 0 else size * 1.15
        out.append(f'<text x="{x:.1f}" y="{y + i * size * 1.15:.1f}" font-size="{size}" text-anchor="{anchor}" '
                   f'font-weight="{weight}" fill="{fill}" font-family="Noto Sans KR, Apple SD Gothic Neo, Arial, sans-serif"{tf}>{esc(ln)}</text>')
    return '\n'.join(out)

def rect_mm(cx, cy, w, h, **kw):
    style = ' '.join(f'{k.replace("_", "-")}="{v}"' for k, v in kw.items())
    return f'<rect x="{X(cx - w / 2):.1f}" y="{Y(cy - h / 2):.1f}" width="{w * SC:.1f}" height="{h * SC:.1f}" {style}/>'

def line_mm(x1, y1, x2, y2, **kw):
    style = ' '.join(f'{k.replace("_", "-")}="{v}"' for k, v in kw.items())
    return f'<line x1="{X(x1):.1f}" y1="{Y(y1):.1f}" x2="{X(x2):.1f}" y2="{Y(y2):.1f}" {style}/>'

def circle_mm(cx, cy, d, **kw):
    style = ' '.join(f'{k.replace("_", "-")}="{v}"' for k, v in kw.items())
    return f'<circle cx="{X(cx):.1f}" cy="{Y(cy):.1f}" r="{d / 2 * SC:.1f}" {style}/>'

def grid():
    out = []
    for i in range(0, int(W_MM) + 1):
        major = i % 5 == 0
        out.append(line_mm(i, 0, i, H_MM, stroke='#d5d8dc' if major else '#eceff1', stroke_width=1 if major else 0.6))
        if major:
            out.append(text(X(i), Y(0) - 6, str(i), size=9, fill='#7f8c8d'))
    for j in range(0, int(H_MM) + 1):
        major = j % 5 == 0
        out.append(line_mm(0, j, W_MM, j, stroke='#d5d8dc' if major else '#eceff1', stroke_width=1 if major else 0.6))
        if major:
            out.append(text(X(0) - 8, Y(j) + 3, str(j), size=9, fill='#7f8c8d', anchor='end'))
    out.append(text(X(W_MM / 2), Y(0) - 20, '단위: mm (1 mm 격자 / 5 mm 굵은 격자) — Top view, 부품면', size=10, fill='#566573'))
    return '\n'.join(out)

def board_edge():
    return '\n'.join([
        line_mm(BOARD_EDGE_X, 0, BOARD_EDGE_X, H_MM, stroke='#b7950b', stroke_width=3),
        rect_mm((BOARD_EDGE_X + W_MM) / 2, H_MM / 2, W_MM - BOARD_EDGE_X, H_MM, fill='#f9e79f', fill_opacity=0.35, stroke='none'),
        text(X(BOARD_EDGE_X + 1.0), Y(2.0), 'PCB 외곽선\n(Edge)', size=9, fill='#7d6608', anchor='middle'),
    ])

def footprint(fp, faded=False, show_nets=True):
    out = []
    op = 0.45 if faded else 1.0
    out.append(rect_mm(fp['cx'], fp['cy'], fp['bw'], fp['bh'], fill='none', stroke='#212f3d', stroke_width=1.6, stroke_opacity=op))
    for (num, cx, cy, w, h, net, kind) in fp['pads']:
        if kind == 'smd':
            out.append(rect_mm(cx, cy, w, h, fill='#e8a090', stroke='#922b21', stroke_width=1, fill_opacity=op, stroke_opacity=op))
        else:
            if num == 1:
                out.append(rect_mm(cx, cy, w, w, fill='#e8a090', stroke='#922b21', stroke_width=1, fill_opacity=op, stroke_opacity=op))
            else:
                out.append(circle_mm(cx, cy, w, fill='#e8a090', stroke='#922b21', stroke_width=1, fill_opacity=op, stroke_opacity=op))
            out.append(circle_mm(cx, cy, h, fill='#fff', stroke='#922b21', stroke_width=0.8, stroke_opacity=op))
        out.append(text(X(cx), Y(cy) + 3, str(num), size=7, fill='#5b2c6f', weight='bold'))
    if 'pin1' in fp and fp['ref'] != 'J1':
        out.append(circle_mm(fp['cx'] - fp['bw'] / 2 - 0.5, fp['cy'] - fp['bh'] / 2 - 0.5, 0.35, fill='#212f3d', stroke='none', fill_opacity=op))
    if fp['ref'] == 'L1':  # winding hint
        out.append(line_mm(17.5, 9.4, 21.5, 9.4, stroke='#212f3d', stroke_width=1, stroke_dasharray='4 3', stroke_opacity=op))
        out.append(line_mm(17.5, 12.6, 21.5, 12.6, stroke='#212f3d', stroke_width=1, stroke_dasharray='4 3', stroke_opacity=op))
    return '\n'.join(out)

def refdes_labels(placement=True):
    out = []
    lab = {  # ref: (x, y, anchor)
        'U1': (8.0, 16.6, 'middle'), 'C1': (3.3, 16.6, 'middle'), 'L1': (19.5, 16.6, 'middle'),
        'R1': (24.0, 7.0, 'middle'), 'R2': (25.4, 15.5, 'middle'), 'C3': (27.4, 16.6, 'middle'),
        'D1': (33.0, 16.6, 'middle'), 'J1': (39.5, 17.6, 'middle'),
    }
    for ref, (x, y, a) in lab.items():
        out.append(text(X(x), Y(y), ref, size=12, weight='bold', anchor=a, fill='#1b2631'))
        if placement:
            out.append(text(X(x), Y(y) + 13, VALUES[ref], size=8.5, anchor=a, fill='#566573'))
    # U1 pin functions
    pins = {1: 'TXD', 2: 'GND', 3: 'VCC', 4: 'RXD', 5: 'VIO/NC', 6: 'CANL', 7: 'CANH', 8: 'STB'}
    for (num, cx, cy, w, h, net, kind) in FP['U1']['pads']:
        if num <= 4:
            out.append(text(X(cx + 1.1), Y(cy) + 3, pins[num], size=7.5, anchor='start', fill='#1a5276'))
        else:
            out.append(text(X(cx - 1.1), Y(cy) + 3, pins[num], size=7.5, anchor='end', fill='#1a5276'))
    # connector pins
    for (num, cx, cy, w, h, net, kind) in FP['J1']['pads']:
        out.append(text(X(cx + 1.3), Y(cy) + 3, net, size=8, anchor='start', fill='#1a5276', weight='bold'))
    # TVS pins
    out.append(text(X(31.2), Y(10.05) + 3, 'H', size=7.5, anchor='end', fill='#1a5276'))
    out.append(text(X(31.2), Y(11.95) + 3, 'L', size=7.5, anchor='end', fill='#1a5276'))
    out.append(text(X(34.0), Y(9.9), 'GND', size=7.5, anchor='middle', fill='#1a5276'))
    return '\n'.join(out)

def hdim(x1, x2, y, label, color='#1f618d'):
    out = [line_mm(x1, y, x2, y, stroke=color, stroke_width=1),
           line_mm(x1, y - 0.4, x1, y + 0.4, stroke=color, stroke_width=1),
           line_mm(x2, y - 0.4, x2, y + 0.4, stroke=color, stroke_width=1),
           text(X((x1 + x2) / 2), Y(y) - 4, label, size=9, fill=color, weight='bold')]
    return '\n'.join(out)

def vdim(x, y1, y2, label, color='#1f618d', side=1):
    out = [line_mm(x, y1, x, y2, stroke=color, stroke_width=1),
           line_mm(x - 0.4, y1, x + 0.4, y1, stroke=color, stroke_width=1),
           line_mm(x - 0.4, y2, x + 0.4, y2, stroke=color, stroke_width=1),
           text(X(x) + 6 * side, Y((y1 + y2) / 2) + 3, label, size=9, fill=color, weight='bold', anchor='start' if side > 0 else 'end')]
    return '\n'.join(out)

def callout(x, y, tx, ty, label, color='#1f618d', anchor='start', size=9):
    return '\n'.join([line_mm(x, y, tx, ty, stroke=color, stroke_width=1),
                      text(X(tx) + (4 if anchor == 'start' else -4), Y(ty) + 3, label, size=size, fill=color, anchor=anchor, weight='bold')])

def flow_arrows():
    out = []
    y = 3.2
    stops = [(1.0, 'MCU (외부)'), (8.0, 'U1 트랜시버'), (26.0, '종단 R1/R2/C3'), (19.5, 'L1 CMC'), (33.0, 'D1 TVS'), (39.5, 'J1 커넥터')]
    out.append(line_mm(0.5, y, 41.5, y, stroke='#17a589', stroke_width=2, marker_end='url(#arrow)'))
    for x, lab in stops:
        out.append(line_mm(x, y, x, y + 0.6, stroke='#17a589', stroke_width=1.5))
        out.append(text(X(x), Y(y) - 7, lab, size=8.5, fill='#0e6655', weight='bold'))
    return '\n'.join(out)

def route_svg(net, w, layer, pts):
    color = NET_COLOR[net]
    d = ' '.join(f'{X(px):.1f},{Y(py):.1f}' for px, py in pts)
    if layer == 'INNER':
        return f'<polyline points="{d}" fill="none" stroke="{color}" stroke-width="{w * SC:.1f}" stroke-linecap="round" stroke-linejoin="round" stroke-opacity="0.35" stroke-dasharray="6 5"/>'
    return f'<polyline points="{d}" fill="none" stroke="{color}" stroke-width="{w * SC:.1f}" stroke-linecap="round" stroke-linejoin="round" stroke-opacity="0.9"/>'

def via_svg(x, y, net):
    return '\n'.join([circle_mm(x, y, VIA_D, fill=NET_COLOR[net], stroke='#111', stroke_width=0.8),
                      circle_mm(x, y, VIA_DRILL, fill='#fff', stroke='none')])

def gnd_shape_svg():
    out = []
    for (x1, y1, x2, y2) in GND_SHAPES:
        out.append(f'<rect x="{X(x1):.1f}" y="{Y(y1):.1f}" width="{(x2 - x1) * SC:.1f}" height="{(y2 - y1) * SC:.1f}" fill="url(#hatch)" stroke="#1e8449" stroke-width="1.2" stroke-dasharray="5 3"/>')
    return '\n'.join(out)


def halos():
    out = []
    for (net, w, layer, pts) in ROUTES:
        if layer != 'TOP' or net == 'GND':
            continue
        d = ' '.join(f'{X(px):.1f},{Y(py):.1f}' for px, py in pts)
        out.append(f'<polyline points="{d}" fill="none" stroke="#fff" stroke-width="{(w + 0.6) * SC:.1f}" stroke-linecap="round" stroke-linejoin="round"/>')
    for fp in FP.values():
        for (num, cx, cy, w, h, net, kind) in fp['pads']:
            if net == 'GND':
                continue
            if kind == 'th':
                out.append(circle_mm(cx, cy, w + 0.6, fill='#fff', stroke='none'))
            else:
                out.append(rect_mm(cx, cy, w + 0.6, h + 0.6, fill='#fff', stroke='none'))
    return '\n'.join(out)

def legend(items, x, y):
    out = [f'<rect x="{x}" y="{y}" width="330" height="{18 + 17 * len(items)}" fill="#fff" stroke="#bdc3c7" rx="6"/>']
    for i, (color, lab, dash) in enumerate(items):
        yy = y + 16 + i * 17
        extra = ' stroke-dasharray="6 5" stroke-opacity="0.5"' if dash else ''
        out.append(f'<line x1="{x + 12}" y1="{yy}" x2="{x + 42}" y2="{yy}" stroke="{color}" stroke-width="6" stroke-linecap="round"{extra}/>')
        out.append(text(x + 52, yy + 4, lab, size=9.5, anchor='start'))
    return '\n'.join(out)

def notes_box(title, lines, x, y, w):
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{30 + 16 * len(lines)}" fill="#fbfcfc" stroke="#bdc3c7" rx="6"/>',
           text(x + 12, y + 18, title, size=11, weight='bold', anchor='start', fill='#1b2631')]
    for i, ln in enumerate(lines):
        out.append(text(x + 12, y + 38 + i * 16, ln, size=9.5, anchor='start', fill='#2c3e50'))
    return '\n'.join(out)

DEFS = '''<defs>
<marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#17a589"/></marker>
<pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="8" stroke="#1e8449" stroke-width="1.2" stroke-opacity="0.5"/></pattern>
</defs>'''

def wrap(body, width, height, title, subtitle):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" font-family="Noto Sans KR, Apple SD Gothic Neo, Arial, sans-serif">
<rect width="100%" height="100%" fill="#ffffff"/>
{DEFS}
{text(24, 34, title, size=18, weight='bold', anchor='start')}
{text(24, 56, subtitle, size=11, anchor='start', fill='#7b241c')}
{body}
</svg>'''

# ---------------- drawing 1: placement ----------------
def placement():
    parts = [grid(), board_edge(), flow_arrows()]
    for fp in FP.values():
        parts.append(footprint(fp))
    parts.append(refdes_labels(placement=True))
    # dimensions
    parts.append(hdim(3.3, 5.3, 20.2, 'C1↔U1 VCC핀 2.0 (≤ 2)'))
    parts.append(hdim(8.0, 19.5, 21.6, 'U1↔L1 중심 11.5 (≤ 15)'))
    parts.append(hdim(21.5, 32.0, 21.6, 'L1↔D1 10.5'))
    parts.append(hdim(32.0, 39.5, 20.2, 'D1↔J1 7.5 (≤ 10)'))
    parts.append(hdim(40.35, 42.0, 5.6, '1.65 (≥ 1.0)'))
    parts.append(vdim(15.2, 9.4, 12.6, '3.2 (L1 피치)', side=-1))
    parts.append(vdim(43.4, 8.46, 13.54, '5.08', side=1))
    parts.append(callout(19.5, 12.6, 16.0, 19.0, 'L1 아래 타 신호 배선 금지 (Keep-out)', anchor='start'))
    parts.append(callout(26.6, 11.0, 27.0, 5.6, '종단은 버스 양단 노드만 실장 (중간 노드 DNP)', anchor='start'))
    parts.append(callout(34.0, 11.5, 35.5, 19.0, 'D1 GND → 비아 직결 + J1 GND 최단', anchor='start'))
    parts.append(callout(3.3, 10.2, 1.0, 19.0, 'C1 GND/VCC 비아 패드 직결', anchor='start'))
    notes = [
        '1) 신호 흐름을 좌→우 일직선으로: MCU → U1 → L1 CMC → 종단(R1/R2/C3) → D1 TVS → J1 → 보드 에지. 되돌아가는 경로 없음.',
        '2) C1(100 nF): U1 VCC(3)·GND(2) 핀 바로 옆, 같은 면. 패드 중심 간 ≤ 2 mm, GND/VCC 비아는 C1 패드에 직결.',
        '3) D1(TVS): 커넥터 핀에서 ≤ 10 mm, CAN_H/CAN_L 선이 D1 패드를 "통과"하도록(스텁 0). GND 핀은 비아 직결.',
        '4) L1(CMC): U1과 D1 사이 일직선. 몸체 아래 다른 신호 배선·비아 금지. 권선 짝(1-4 / 2-3)은 데이터시트로 확인.',
        '5) 종단 R1/R2/C3(분할 종단 60.4 Ω×2 + 4.7 nF): 선이 저항 패드를 통과하도록 배치, C3 GND는 비아 직결. 버스 양단 노드만 실장.',
        '6) J1: CAN_H와 CAN_L 사이에 GND 핀. DB9 등 실제 커넥터 핀 배열에 맞춰 위치만 바꾸고 순서(TVS→커넥터)는 유지.',
        '7) 금지: CAN 라인 아래 GND 플레인 분할·슬롯, 스위칭 전원/클럭/고속 신호와 5 mm 이내 근접, U1·D1을 다른 면에 배치.',
        '8) 이 도면의 부품·값·핀 배열은 예시입니다. 실제 회로도(OrCAD) 수령 후 동일 형식으로 실제 부품(PSM 이름 기준) 배치도를 작성합니다.',
    ]
    parts.append(notes_box('배치 규칙 (이 블록 기준)', notes, 24, Y(H_MM) + 40, 1330))
    body = '\n'.join(parts)
    return wrap(body, 1380, Y(H_MM) + 40 + 30 + 16 * len(notes) + 30,
                '샘플 — CAN 인터페이스 블록 배치도 (Top, 패키지 심볼 외형 기준)',
                '※ 예시 부품으로 그린 형식 샘플입니다. 실제 회로도를 받으면 실제 부품·핀·값으로 다시 작성합니다.')

# ---------------- drawing 2: routing / shapes ----------------
def routing():
    parts = [grid(), board_edge(), gnd_shape_svg(), halos()]
    for fp in FP.values():
        parts.append(footprint(fp, faded=True))
    for (net, w, layer, pts) in ROUTES:
        parts.append(route_svg(net, w, layer, pts))
    for (x, y, net) in VIAS:
        parts.append(via_svg(x, y, net))
    parts.append(refdes_labels(placement=False))
    # width callouts
    parts.append(callout(14.5, 9.4, 12.5, 5.8, 'CAN_H/CAN_L: W 0.30, 대칭·등장, 45° 꺾기', anchor='start'))
    parts.append(callout(4.3, 11.7, 2.5, 19.2, 'VCC 0.50 (내층 → 비아 → C1 → U1)', anchor='start'))
    parts.append(callout(3.0, 9.095, 1.0, 5.0, 'TXD/RXD/STB: W 0.20', anchor='start'))
    parts.append(callout(25.2, 11.0, 23.0, 20.8, '종단 중점 W 0.30, C3 → GND 비아 직결', anchor='start'))
    parts.append(callout(37.0, 11.0, 35.5, 19.2, 'GND 0.50: D1 GND → 비아 → J1 GND', anchor='start'))
    parts.append(callout(31.0, 6.4, 27.5, 5.0, 'Top GND 채움(shape): D1~J1 구역, 클리어런스 0.30', anchor='start'))
    parts.append(callout(19.5, 14.8, 13.0, 19.2, 'GND 스티칭 비아 0.6/0.3 (간격 ≤ 5 mm)', anchor='start'))
    parts.append(callout(30.3, 12.6, 30.3, 22.4, 'D1 패드로 수렴 (스텁 0), 3W 이격 유지', anchor='start'))
    lt = seg_len(ROUTES[0][3]); lb = seg_len(ROUTES[2][3]) + seg_len(ROUTES[4][3])
    leg = legend([('#d35400', f'CAN_H / CAN_L  W 0.30 (U1→L1 {lt:.1f} mm, L1→J1 {lb:.1f} mm, 편차 0)', False),
                  ('#c0392b', 'VCC  W 0.50 (점선: 내층/하면 배선)', True),
                  ('#1e8449', 'GND  W 0.40~0.50, 채움(shape) = 빗금', False),
                  ('#8e44ad', '종단 중점(TERM_MID)  W 0.30', False),
                  ('#2471a3', 'TXD / RXD / STB  W 0.20', False)], 24, Y(H_MM) + 40)
    parts.append(leg)
    rules = [
        '배선 규칙(샘플값)   CAN_H/CAN_L: W 0.30 mm, 두 선 길이 편차 ≤ 2 mm, 타 신호와 ≥ 0.90 mm(3W), Top 단층·비아 0개, 90° 금지(45°).',
        '                       VCC 0.50 / GND 스터브 0.40~0.50 / TXD·RXD·STB 0.20 / 최소 클리어런스 0.20 / 비아 0.60 홀 0.30.',
        'Shape(동박 채움)    L2 = GND 플레인 전면, CAN 라인 아래 분할·슬롯 없음. Top GND 채움은 D1~J1 구역만, 트레이스 클리어런스 0.30.',
        '                       D1·C3·C1의 GND는 서멀 릴리프 없이 직결(direct connect). CAN 라인 양옆 스티칭 비아 간격 ≤ 5 mm.',
        '임피던스              4층(L2 GND, 프리프레그 ≈ 0.2 mm) 기준 차동 120 Ω 목표 시 W/S는 제조사 계산값으로 확정(대략 W 0.15~0.2, S 0.2~0.3).',
        '                       2층 1.6 mm 보드는 120 Ω 매칭이 불가 → 대칭·최단·연속 GND 참조만 유지.',
        '적용 방법(Allegro)  위 값은 Constraint Manager의 Physical CSet(CAN_DIFF: W 0.30) / Spacing CSet(CAN: 0.90) / Diff Pair(CAN_H+CAN_L)로 넣고,',
        '                       R1·R2·D1 패드는 "선 통과형" 배치 유지. 이 도면은 예시이며 실제 회로도 수령 후 실제 넷 이름으로 다시 작성합니다.',
    ]
    parts.append(notes_box('배선·Shape 규칙 (이 블록 기준)', rules, 370, Y(H_MM) + 40, 984))
    body = '\n'.join(parts)
    return wrap(body, 1380, Y(H_MM) + 40 + 30 + 16 * len(rules) + 30,
                '샘플 — CAN 인터페이스 블록 배선도 (Top, 실제 배선폭 축척 표시 + GND shape)',
                '※ 예시 부품·샘플 규칙값입니다. 실제 회로도·층 구성·제조사 임피던스 값을 받으면 실제 넷/부품으로 다시 작성합니다.')

open('can_block_placement.svg', 'w', encoding='utf-8').write(placement())
open('can_block_routing.svg', 'w', encoding='utf-8').write(routing())
print('CANH_T len %.2f mm, CAN_H bus len %.2f mm' % (seg_len(ROUTES[0][3]), seg_len(ROUTES[2][3]) + seg_len(ROUTES[4][3])))
print('CANL_T len %.2f mm, CAN_L bus len %.2f mm' % (seg_len(ROUTES[1][3]), seg_len(ROUTES[3][3]) + seg_len(ROUTES[5][3])))
