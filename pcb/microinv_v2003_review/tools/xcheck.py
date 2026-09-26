# -*- coding: utf-8 -*-
import json, re, collections, sys
sys.path.insert(0, '.')
from nl import parse_pstchip, parse_pstxnet
P = parse_pstchip('pstchip.dat'); N, CELL, PNAME = parse_pstxnet('pstxnet.dat')
B = json.load(open('board.json')); X = json.load(open('brd_xref.json'))
def key(r):
    m = re.match(r'([A-Za-z_]+)(\d+)', r or '')
    return (m.group(1), int(m.group(2))) if m else ('~' + str(r), 0)
FP = {f['ref']: f for f in B['footprints']}
# --- 회로도 PDF refdes ---
txt = open('sch.txt', encoding='utf-8', errors='replace').read()
sch_refs = set(re.findall(r'\b((?:C|R|D|U|Q|L|T|J|EC|ISO|RV|F|TH|LS|TSW|Y|ZD)\d{1,3})\b', txt))
net_refs = {r for n in N.values() for r, _ in n}
brd_refs = set(FP)
print('== 1. 참조번호 집합 ==')
print(f'  회로도 PDF {len(sch_refs)} / 넷리스트 {len(net_refs)} / 보드 {len(brd_refs)}')
print('  보드에만 있음 :', sorted(brd_refs - net_refs, key=key))
print('  넷리스트에만  :', sorted(net_refs - brd_refs, key=key))
print('  PDF에만(넷·보드 없음):', sorted(sch_refs - net_refs - brd_refs, key=key)[:40])
# --- 디바이스 → 프리미티브 매칭 ---
def find_prim(dev):
    if dev is None: return None
    c = [p for p in P if p.startswith(dev)] or [p for p in P if p[:31] == dev[:31]]
    return c[0] if len(c) == 1 else (c if c else None)
rows = []
for r in sorted(brd_refs, key=key):
    x = X.get(r, {}); prim = find_prim(x.get('device'))
    rows.append((r, x.get('device'), prim, x.get('dev_sym')))
amb = [(r, d, p) for r, d, p, s in rows if isinstance(p, list)]
nf = [(r, d) for r, d, p, s in rows if p is None]
print('\n== 2. 보드 디바이스 → 넷리스트 프리미티브 ==')
print('  모호(여러 후보):', len(amb), amb[:5])
print('  넷리스트에 없는 디바이스:', len(nf), nf[:20])
prim_of = {r: p for r, d, p, s in rows if isinstance(p, str)}
# PSM 일치
psm_mis = []
for r, d, p, s in rows:
    if isinstance(p, str):
        j = P[p]['props'].get('JEDEC_TYPE')
        if j != s: psm_mis.append((r, j, s))
print('  JEDEC_TYPE ≠ 보드 심볼:', len(psm_mis), psm_mis[:20])
# --- 핀 ↔ 패드 번호 ---
print('\n== 3. 핀 번호 ↔ 패드 번호 ==')
pin_issues = []
for r, p in prim_of.items():
    sym_pins = {n for (_, nums, _) in P[p]['pins'] for n in nums}
    pads = {pd['num'] for pd in FP[r]['pads'] if pd['num']}
    miss = sym_pins - pads; extra = pads - sym_pins
    if miss or extra: pin_issues.append((r, p[:40], sorted(miss)[:8], sorted(extra)[:8], len(sym_pins), len(pads)))
print('  불일치 부품:', len(pin_issues))
for it in pin_issues[:40]: print('   ', it)
# --- 넷 연결 (이름 무관 분할 비교) ---
print('\n== 4. 넷 연결 (넷리스트 vs 보드) ==')
nl_pin = {(r, p): n for n, nodes in N.items() for r, p in nodes}
bd_pin = {(f['ref'], pd['num']): pd['net'] for f in B['footprints'] for pd in f['pads'] if pd['num']}
# 넷리스트 넷 → 보드 넷 대응
m = collections.defaultdict(collections.Counter)
for k, n in nl_pin.items():
    if k in bd_pin: m[n][bd_pin[k]] += 1
split = {n: c for n, c in m.items() if len(c) > 1}
print('  넷리스트 넷이 보드에서 여러 넷으로 갈라짐:', len(split))
for n, c in list(split.items())[:15]: print(f'    {n}: {dict(c.most_common(4))}')
rev = collections.defaultdict(collections.Counter)
for k, bn in bd_pin.items():
    if k in nl_pin: rev[bn][nl_pin[k]] += 1
merged = {bn: c for bn, c in rev.items() if len(c) > 1 and bn}
print('  보드 한 넷에 넷리스트 여러 넷이 합쳐짐:', len(merged))
for bn, c in list(merged.items())[:15]: print(f'    {bn}: {dict(c.most_common(5))}')
nopad = [k for k in nl_pin if k not in bd_pin]
print('  넷리스트 핀인데 보드에 패드 없음:', len(nopad), nopad[:12])
unconn = [(k, bd_pin[k]) for k in bd_pin if k not in nl_pin and bd_pin[k] and k[0] in net_refs]
print('  보드에서 넷이 붙었는데 넷리스트엔 없는 핀:', len(unconn), unconn[:12])
same_name = sum(1 for n, c in m.items() if len(c) == 1 and list(c)[0] == n)
print(f'  이름까지 같은 넷 {same_name} / 대응 넷 {len(m)}')
json.dump(dict(prim_of=prim_of, psm_mis=psm_mis, pin_issues=pin_issues, split={k: dict(v) for k, v in split.items()},
               merged={k: dict(v) for k, v in merged.items()}, nopad=nopad), open('xcheck.json', 'w'), ensure_ascii=False)
