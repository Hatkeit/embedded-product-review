# -*- coding: utf-8 -*-
"""Allegro 17.4 .brd 에서 참조번호 → 디바이스(프리미티브) → 배치 심볼(PSM) 추출.
KiCad 10 allegro_parser.cpp 의 0x06/0x07/0x2B/0x2D 레이아웃을 따름 (V172+)."""
import struct, re, json, collections
D = open('board.brd', 'rb').read()
u32 = lambda o: struct.unpack_from('<I', D, o)[0]
# 1) 문자열 테이블
S = {}; o = 0x1200
while o + 5 < len(D):
    sid = u32(o); e = D.find(b'\0', o + 4)
    if e < 0 or e - (o + 4) > 400: break
    s = D[o+4:e]
    try: s = s.decode('latin-1')
    except Exception: break
    if sid == 0 or (s and not all(32 <= ord(c) < 127 or ord(c) > 159 for c in s)): break
    S[sid] = s
    o = e + 1
    if o % 4: o += 4 - o % 4
print('strings', len(S), 'end', hex(o))
RD = re.compile(r'^[A-Z]{1,4}\d{1,4}$')
# 2) 블록 스캔
b06, b07, b2b, b2d = {}, {}, {}, {}
for off in range(o, len(D) - 64):
    t = D[off]
    if t == 0x06:
        key, nxt, dev, sym, first = struct.unpack_from('<5I', D, off + 4)
        if dev in S and sym in S and first and key:
            b06[key] = dict(dev=S[dev], sym=S[sym], first=first, next=nxt)
    elif t == 0x07:
        key, nxt, up1, u2, u3, fp, rd = struct.unpack_from('<7I', D, off + 4)
        if rd in S and RD.match(S[rd]) and key and fp:
            b07[key] = dict(ref=S[rd], fp=fp, next=nxt)
    elif t == 0x2B:
        key, fps = struct.unpack_from('<2I', D, off + 4)
        nxt, first = struct.unpack_from('<2I', D, off + 4 + 12 + 16)
        if fps in S and first and key and re.match(r'^[A-Za-z0-9_\-\.]+$', S[fps] or '-'):
            b2b[key] = dict(sym=S[fps], first=first, next=nxt)
    elif t == 0x2D:
        layer = D[off + 1]
        key, nxt = struct.unpack_from('<2I', D, off + 3)
        # V172+: m_Unknown1(u32), u16, u16, m_Unknown4(u32), flags, rot, x, y, instref
        base = off + 3 + 8
        un1 = u32(base); base += 4
        base += 4          # u16 + u16
        base += 4          # m_Unknown4
        flags, rot = struct.unpack_from('<2I', D, base); x, y = struct.unpack_from('<2i', D, base + 8)
        inst = u32(base + 16)
        if key and layer in (0, 1) and rot % 1000 == 0 and rot <= 360000:
            b2d[key] = dict(layer=layer, next=nxt, rot=rot/1000, x=x, y=y, inst=inst)
print('0x06', len(b06), '0x07', len(b07), '0x2B', len(b2b), '0x2D', len(b2d))
# 3) 연결
ref_dev, ref_sym_place = {}, {}
for k, c in b06.items():
    cur, seen = c['first'], set()
    while cur in b07 and cur not in seen:
        seen.add(cur); ref_dev[b07[cur]['ref']] = (c['dev'], c['sym']); cur = b07[cur]['next']
for k, f in b2b.items():
    cur, seen = f['first'], set()
    while cur in b2d and cur not in seen:
        seen.add(cur); inst = b2d[cur]['inst']
        if inst in b07: ref_sym_place[b07[inst]['ref']] = f['sym']
        cur = b2d[cur]['next']
print('refdes→device', len(ref_dev), '| refdes→placed symbol', len(ref_sym_place))
out = {r: dict(device=ref_dev.get(r, (None, None))[0], dev_sym=ref_dev.get(r, (None, None))[1], placed_sym=ref_sym_place.get(r))
       for r in set(ref_dev) | set(ref_sym_place)}
json.dump(out, open('brd_xref.json', 'w'), ensure_ascii=False, indent=0)
for r in ['T2', 'T9', 'U17', 'EC1', 'Q1', 'ISO1', 'U16', 'LS1', 'J1', 'C48']:
    print(r, out.get(r))
mism = [(r, v['dev_sym'], v['placed_sym']) for r, v in out.items() if v['dev_sym'] and v['placed_sym'] and v['dev_sym'] != v['placed_sym']]
print('device 심볼 ≠ 배치 심볼:', len(mism), mism[:10])
