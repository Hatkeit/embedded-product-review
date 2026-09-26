# -*- coding: utf-8 -*-
import json, collections, sys
from shapely.geometry import Polygon
from shapely.ops import unary_union
P = json.load(open('polys.json')); dom = json.load(open('net_domain_v2003.json'))
V = json.load(open('iso_violations.json')); B = json.load(open('board.json'))
SC = 4.0; M = 30
def X(x): return M + x*SC
def Y(y): return M + (250 - y)*SC
COL = {'PRI': '#3b82c4', 'HAZ': '#d64545', 'PE': '#d4a017', 'FLOAT': '#8e8e8e', 'NONET': '#c9c9c9'}
def path(g):
    out = []
    geoms = getattr(g, 'geoms', [g])
    for p in geoms:
        if p.is_empty: continue
        for ring in [p.exterior] + list(p.interiors):
            c = list(ring.coords)
            out.append('M' + ' L'.join(f'{X(x):.1f},{Y(y):.1f}' for x, y in c) + 'Z')
    return ' '.join(out)
labels = {'T2','T4','T6','T8','T9','ISO1','ISO2','ISO3','ISO4','ISO5','U23','U24','U17','U18','U16','LS1','L7','L8','F1','R219','R228','C46','C47','C69','J24','Q13','Q14','D3','D8','D14','D19','EC1','EC7','J1','J6','J11','J15','R6','R43'}
for layer in ['TOP', 'L2', 'L3', 'BOTTOM']:
    per = collections.defaultdict(list)
    for net, polys in P[layer].items():
        d = dom.get(net, 'NONET')
        for pts, holes in polys:
            try:
                g = Polygon(pts, holes); per[d].append(g if g.is_valid else g.buffer(0))
            except Exception: pass
    W = int(2*M + 250*SC); H = int(2*M + 250*SC + 70)
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" font-family="Noto Sans KR, Arial"><rect width="100%" height="100%" fill="#fff"/>',
           f'<rect x="{X(0)}" y="{Y(250)}" width="{250*SC}" height="{250*SC}" fill="#f4f1e8" stroke="#333" stroke-width="1.5"/>']
    for d in ['NONET', 'FLOAT', 'PE', 'PRI', 'HAZ']:
        if per.get(d):
            svg.append(f'<path d="{path(unary_union(per[d]))}" fill="{COL[d]}" fill-opacity="0.78" fill-rule="evenodd" stroke="none"/>')
    for f in B['footprints']:
        if f['ref'] in labels:
            svg.append(f'<text x="{X(f["x"]):.0f}" y="{Y(-f["y"]):.0f}" font-size="11" font-weight="bold" text-anchor="middle" fill="#111" stroke="#fff" stroke-width="2.5" paint-order="stroke">{f["ref"]}</text>')
    k = 0
    for i, v in enumerate(V):
        if v['layer'] != layer: continue
        k += 1
        c = '#000' if v['pair'] == 'PRI-HAZ' else '#7a4b00'
        svg.append(f'<circle cx="{X(v["x"]):.1f}" cy="{Y(v["y"]):.1f}" r="9" fill="none" stroke="{c}" stroke-width="2.4"/>')
        svg.append(f'<text x="{X(v["x"])+10:.0f}" y="{Y(v["y"])-8:.0f}" font-size="10" font-weight="bold" fill="{c}" stroke="#fff" stroke-width="2" paint-order="stroke">{v["d"]:.1f}</text>')
    lg = [('1차 PV·제어 (GND 기준)', 'PRI'), ('계통 연결 위험부 (PHV·PGND·AC)', 'HAZ'), ('PE / 섀시', 'PE'), ('분압 중간점 등', 'FLOAT')]
    for j, (t, d) in enumerate(lg):
        svg.append(f'<rect x="{M + j*245}" y="{H-50}" width="16" height="16" fill="{COL[d]}"/><text x="{M + j*245 + 22}" y="{H-37}" font-size="13">{t}</text>')
    svg.append(f'<text x="{M}" y="{H-12}" font-size="13" font-weight="bold">{layer} — 원: 요구치 미달 지점 (숫자 = 실측 mm). 1차↔위험부 요구 8.0 / 위험부↔PE 4.0 / 1차↔PE 1.8 (KS C 8560 표 4·5)</text>')
    svg.append('</svg>')
    open(f'maps/iso_{layer}.svg', 'w', encoding='utf-8').write('\n'.join(svg))
    open(f'maps/iso_{layer}.html', 'w').write(f'<!doctype html><html><body style="margin:0"><img src="iso_{layer}.svg"></body></html>')
    print(layer, k, 'marks')
