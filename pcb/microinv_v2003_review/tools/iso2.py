# -*- coding: utf-8 -*-
import json, re, sys, collections, math
sys.path.insert(0, '.')
from nl import parse_pstxnet
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union, nearest_points
N, CELL, PN = parse_pstxnet('pstxnet.dat'); X = json.load(open('brd_xref.json')); B = json.load(open('board.json'))
nl_nets = collections.defaultdict(set)
for n, nodes in N.items():
    for r, p in nodes: nl_nets[r].add(n)
ISOL = {'T2','T4','T6','T8','T9','ISO1','ISO2','ISO3','ISO4','ISO5','U23','U24','LS1'}
SURGE = {'D27','TH1','F2'} | {f'RV{i}' for i in range(1, 6)}
def big_r(r):
    d = ((X.get(r) or {}).get('device') or '').upper()
    m = re.search(r'_([\d.]+)(M|MF)\b', d); return bool(m)
parent = {n: n for n in N}
def f(a):
    while parent[a] != a: parent[a] = parent[parent[a]]; a = parent[a]
    return a
for r, ns in nl_nets.items():
    if r in ISOL or r in SURGE or r.startswith(('C', 'EC')) or (r.startswith('R') and big_r(r)): continue
    ns = [n for n in ns if n != 'NC']
    for a, b in zip(ns, ns[1:]): parent[f(a)] = f(b)
grp = collections.defaultdict(set)
for n in N: grp[f(n)].add(n)
SEED = [('GND', 'PRI'), ('PGND', 'HAZ'), ('PHV', 'HAZ'), ('AC_L', 'HAZ'), ('AC_L_IN', 'HAZ'), ('AC_N_IN', 'HAZ'),
        ('V_GRID_L', 'HAZ'), ('I_GRID_N', 'HAZ'), ('GND_EARTH', 'PE'), ('I_GRID_LK', 'PE'), ('N17817694', 'PE')]
dom = {}
for g, mem in grp.items():
    labs = sorted({lab for s, lab in SEED if s in mem})
    for m in mem: dom[m] = '+'.join(labs) if labs else 'FLOAT'
# AMC 고압측 전원(부품 U23/U24 1~8번 핀 쪽) → HAZ
pinnet = {(r, p): n for n, nodes in N.items() for r, p in nodes}
for r in ('U23', 'U24'):
    for p in range(1, 17):
        n = pinnet.get((r, str(p)))
        if n and dom.get(n) == 'FLOAT': dom[n] = 'HAZ' if p <= 8 else 'PRI'
print('도메인:', collections.Counter(dom.values()))
print('남은 FLOAT:', sorted(n for n, d in dom.items() if d == 'FLOAT'))
print('병합(다중 라벨):', {d for d in dom.values() if '+' in d})
json.dump(dom, open('net_domain_v2003.json', 'w'))
# 보드 폴리곤
P = json.load(open('polys.json'))
FPpads = [(f['ref'], p['x'], -p['y']) for f in B['footprints'] for p in f['pads']]
def near_ref(x, y):
    return min(FPpads, key=lambda t: (t[1]-x)**2 + (t[2]-y)**2)[0]
REQ = {'PRI-HAZ': 8.0, 'HAZ-PE': 4.0, 'PRI-PE': 1.8}
report = []
for layer, nets in P.items():
    per = collections.defaultdict(list)
    for net, polys in nets.items():
        d = dom.get(net, 'NONET')
        for pts, holes in polys:
            try:
                pg = Polygon(pts, holes); pg = pg if pg.is_valid else pg.buffer(0)
                per[d].append((net, pg))
            except Exception: pass
    U = {d: unary_union([g for _, g in v]) for d, v in per.items()}
    for pair, req in REQ.items():
        a, b = pair.split('-')
        if a not in U or b not in U: continue
        for net, g in per[a]:
            dd = g.distance(U[b])
            if dd < req:
                p1, p2 = nearest_points(g, U[b])
                nb = min(per[b], key=lambda t: t[1].distance(p1))[0]
                report.append(dict(layer=layer, pair=pair, req=req, d=round(dd, 3), x=round(p1.x, 1), y=round(p1.y, 1),
                                   net_a=net, net_b=nb, ref_a=near_ref(p1.x, p1.y), ref_b=near_ref(p2.x, p2.y)))
# 위치별로 묶어 최악값만
report.sort(key=lambda r: r['d'])
clusters = []
for r in report:
    for c in clusters:
        if c['pair'] == r['pair'] and c['layer'] == r['layer'] and math.hypot(c['x']-r['x'], c['y']-r['y']) < 6: break
    else: clusters.append(r)
json.dump(clusters, open('iso_violations.json', 'w'), ensure_ascii=False, indent=0)
print(f'\n요구치 미달 지점 {len(clusters)}곳 (6 mm 이내 중복 제거)')
for c in clusters[:45]:
    print(f"  {c['pair']:8s} {c['layer']:6s} {c['d']:6.2f} mm (요구 {c['req']}) @({c['x']},{c['y']})  {c['net_a']}[{c['ref_a']}] ↔ {c['net_b']}[{c['ref_b']}]")
