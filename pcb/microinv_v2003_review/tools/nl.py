# -*- coding: utf-8 -*-
"""OrCAD→Allegro packager 파일 파서 (pstxprt 없이 pstxnet 노드 경로에서 refdes→cell 추출)."""
import re, collections
def parse_pstchip(path):
    txt = open(path, encoding='utf-8', errors='replace').read()
    prims = {}
    for m in re.finditer(r"primitive '([^']*)';(.*?)end_primitive;", txt, re.S):
        name, body = m.group(1), m.group(2)
        pins = []
        ps = re.search(r"\bpin\b(.*?)end_pin;", body, re.S)
        if ps:
            for pm in re.finditer(r"'([^']*)':\s*((?:\s*[A-Z_]+='[^']*';)*)", ps.group(1)):
                props = dict(re.findall(r"([A-Z_]+)='([^']*)';", pm.group(2)))
                nums = [n.strip() for n in props.get('PIN_NUMBER', '').strip('()').split(',') if n.strip()]
                pins.append((pm.group(1), nums, props.get('PINUSE', '')))
        bs = re.search(r"\bbody\b(.*?)end_body;", body, re.S)
        props = dict(re.findall(r"([A-Z_0-9]+)='([^']*)';", bs.group(1))) if bs else {}
        prims[name] = dict(pins=pins, props=props, npins=sum(len(p[1]) for p in pins))
    return prims
def parse_pstxnet(path):
    lines = open(path, encoding='utf-8', errors='replace').read().splitlines()
    nets = collections.OrderedDict(); cell = {}; pinname = {}
    cur = None; i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith('NET_NAME'):
            cur = lines[i+1].strip().strip("'"); nets[cur] = []; i += 2; continue
        m = re.match(r"^NODE_NAME\s+(\S+)\s+(\S+)", ln)
        if m and cur is not None:
            ref, pin = m.group(1), m.group(2)
            nets[cur].append((ref, pin))
            path = lines[i+1] if i+1 < len(lines) else ''
            cm = re.search(r"@[^@]*@([^.]+)\.(.+?)\.NORMAL", path)
            if cm: cell[ref] = cm.group(2)
            pm = re.search(r"'([^']*)':;", lines[i+2] if i+2 < len(lines) else '')
            if pm: pinname[(ref, pin)] = pm.group(1)
            i += 3; continue
        i += 1
    return nets, cell, pinname
