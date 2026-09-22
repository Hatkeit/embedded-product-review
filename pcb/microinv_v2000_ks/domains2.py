# -*- coding: utf-8 -*-
"""Domain classification with capacitors treated as NON-conducting (they bridge, they don't merge)."""
import re, collections, json
from inv_parse import load
prims, parts, nets, _ = load('.')
pin2net = {}
for n, nodes in nets.items():
    for ref, pin in nodes: pin2net[(ref, pin)] = n
def pnets(ref):
    out = []
    for (pname, pnum, puse) in parts[ref]['pins']:
        for num in pnum.strip('()').split(','):
            n = pin2net.get((ref, num.strip()))
            if n and n != 'NC': out.append((num.strip(), n))
    return out

ISOL = {'T1','T2','T3','T4','T5','T6','T7','T8','T9','ISO1','ISO2','ISO3','ISO4','U23','U24','LS1'}
NONCOND = lambda r: r.startswith('C') and not r.startswith('CN')   # capacitors do not conduct DC

parent = {n: n for n in nets}
def find(a):
    while parent[a] != a: parent[a] = parent[parent[a]]; a = parent[a]
    return a
def union(a, b):
    ra, rb = find(a), find(b)
    if ra != rb: parent[ra] = rb
for ref in parts:
    if ref in ISOL or NONCOND(ref): continue
    ns = list(dict.fromkeys(n for _, n in pnets(ref)))
    for a, b in zip(ns, ns[1:]): union(a, b)
groups = collections.defaultdict(list)
for n in nets: groups[find(n)].append(n)
SEED = {'GND':'P','VDD_3V3':'P','PV_A+':'P','PV_B+':'P','VCC_5V0':'P','VDD_U5':'P',
        'PGND':'S','PHV':'S','AC_L':'S','AC_N':'S','AC_L_IN':'S','VCC_12V0':'S','GND_EARTH':'E'}
label = {}
for root, mem in groups.items():
    ls = sorted({SEED[s] for s in SEED if s in mem})
    lab = '+'.join(ls) if ls else 'FLOAT'
    for m in mem: label[m] = lab
print('domain counts:', dict(collections.Counter(label.values())))
for lab in sorted(set(label.values())):
    named = sorted(n for n in nets if label[n] == lab and not re.match(r'^N\d+$', n))
    tot = sum(1 for n in nets if label[n] == lab)
    print(f'\n[{lab}] {tot} nets | named: {", ".join(named)}')
json.dump(label, open('net_domains.json','w'))

print('\n=== 도메인 경계를 넘는 부품 ===')
def key(r): return (re.match(r'[A-Z]+', r).group(0), int(re.search(r'\d+', r).group(0)))
cross = []
for ref in sorted(parts, key=key):
    d = collections.defaultdict(list)
    for num, n in pnets(ref): d[label.get(n,'?')].append(f'{num}:{n}')
    real = [k for k in d if k in ('P','S','E')]
    if len(real) > 1 or (len(d) > 1 and 'FLOAT' in d and real):
        cross.append((ref, d))
        kind = '절연부품' if ref in ISOL else ('브리지(캡/저항)' if NONCOND(ref) or ref.startswith('R') else '★도통 경로')
        print(f"{ref:6s} {kind:14s} {parts[ref]['psm'][:26]:26s} {parts[ref]['value'][:22]:22s} " +
              ' | '.join(f'{k}[{",".join(v[:3])}]' for k,v in sorted(d.items()))[:130])
print('\ncrossing parts:', len(cross))
