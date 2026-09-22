# -*- coding: utf-8 -*-
"""Parser for OrCAD Capture -> Allegro packager files (pstchip.dat, pstxprt.dat, pstxnet.dat)."""
import re, collections

def parse_pstchip(path):
    txt = open(path, encoding='utf-8', errors='replace').read()
    prims = {}
    for m in re.finditer(r"primitive '([^']*)';(.*?)end_primitive;", txt, re.S):
        name, body = m.group(1), m.group(2)
        pins = []
        pin_sec = re.search(r"pin(.*?)end_pin;", body, re.S)
        if pin_sec:
            for pm in re.finditer(r"'([^']*)':\s*((?:\s*[A-Z_]+='[^']*';)*)", pin_sec.group(1)):
                pname = pm.group(1)
                props = dict(re.findall(r"([A-Z_]+)='([^']*)';", pm.group(2)))
                pins.append((pname, props.get('PIN_NUMBER', ''), props.get('PINUSE', '')))
        body_sec = re.search(r"body(.*?)end_body;", body, re.S)
        props = dict(re.findall(r"([A-Z_0-9]+)='([^']*)';", body_sec.group(1))) if body_sec else {}
        prims[name] = dict(pins=pins, props=props)
    return prims

def parse_pstxprt(path):
    txt = open(path, encoding='utf-8', errors='replace').read()
    parts = {}
    for m in re.finditer(r"PART_NAME\s+(\S+)\s+'([^']*)':;\s*(.*?)(?=PART_NAME|\Z)", txt, re.S):
        ref, dev, rest = m.group(1), m.group(2), m.group(3)
        pages = sorted(set(int(p) for p in re.findall(r"page(\d+)_", rest, re.I)))
        parts[ref] = dict(device=dev, pages=pages)
    return parts

def parse_pstxnet(path):
    txt = open(path, encoding='utf-8', errors='replace').read()
    nets = collections.OrderedDict()
    cur = None
    for line in txt.splitlines():
        if line.startswith('NET_NAME'):
            cur = None
            continue
        m = re.match(r"^'([^']*)'\s*$", line)
        if m and cur is None:
            cur = m.group(1); nets[cur] = []
            continue
        m = re.match(r"^NODE_NAME\s+(\S+)\s+(\S+)", line)
        if m and cur is not None:
            nets[cur].append((m.group(1), m.group(2)))
    return nets

def load(dirpath='.'):
    prims = parse_pstchip(f'{dirpath}/pstchip.dat')
    parts = parse_pstxprt(f'{dirpath}/pstxprt.dat')
    nets = parse_pstxnet(f'{dirpath}/pstxnet.dat')
    for ref, p in parts.items():
        pr = prims.get(p['device'], {'pins': [], 'props': {}})
        p['psm'] = pr['props'].get('JEDEC_TYPE', '')
        p['value'] = pr['props'].get('VALUE', '')
        p['part'] = pr['props'].get('PART_NAME', '')
        p['props'] = pr['props']
        p['npins'] = len(pr['pins'])
        p['pins'] = pr['pins']
    pin2net = {}
    for n, nodes in nets.items():
        for ref, pin in nodes:
            pin2net[(ref, pin)] = n
    return prims, parts, nets, pin2net

if __name__ == '__main__':
    prims, parts, nets, pin2net = load('.')
    print('parts:', len(parts), ' primitives:', len(prims), ' nets:', len(nets))
    print('\n--- body property keys ---')
    keys = collections.Counter(k for pr in prims.values() for k in pr['props'])
    print(keys.most_common())
    print('\n--- parts per page ---')
    pp = collections.Counter(p['pages'][0] if p['pages'] else 0 for p in parts.values())
    print(sorted(pp.items()))
    print('\n--- packages (JEDEC_TYPE) ---')
    pk = collections.Counter(p['psm'] for p in parts.values())
    for k, v in sorted(pk.items(), key=lambda x: -x[1]):
        print(f'{v:4d}  {k}')
    print('\n--- non-passive parts (prefix not C/R) ---')
    for ref in sorted(parts, key=lambda r: (re.match(r'[A-Z]+', r).group(0), int(re.search(r'\d+', r).group(0)))):
        p = parts[ref]
        if re.match(r'^(C|R)\d', ref):
            continue
        print(f"{ref:6s} pg{p['pages']!s:6s} {p['psm']:28s} {p['part'][:30]:30s} {p['value'][:28]:28s} pins={p['npins']}")
