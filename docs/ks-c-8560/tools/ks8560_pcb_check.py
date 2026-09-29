#!/usr/bin/env python3
"""KS C 8560:2020 8.3.4 절연거리 — PCB 설계 데이터 사전 검증 도구.

Allegro 넷리스트(pstxnet.dat)로 절연 도메인을 나누고, IPC-2581 PCB 형상에서
도메인 간 동박 최소거리를 측정해 KS C 8560 표 4·5 기준과 대조한다.

사용법:
    pip install shapely
    python3 ks8560_pcb_check.py --pcb PCB.xml --net pstxnet.dat [--out report.md]

설계가 바뀌면 CONFIG의 앵커 넷·절연 부품 규칙을 먼저 확인할 것.
이 도구는 공인시험을 대체하지 않는다. 솔더마스크는 절연으로 보지 않으며,
내층(L2/L3) 거리는 적층 절연 인정 여부에 따라 판정이 달라지므로 참고값으로만 출력한다.
"""
import argparse, collections, math, re, sys
import xml.etree.ElementTree as ET
from shapely.geometry import Point, Polygon, LineString, box
from shapely import affinity
from shapely.ops import unary_union, nearest_points
from shapely.strtree import STRtree

CONFIG = {
    # 도메인 앵커 넷 (넷리스트 이름)
    "anchors": {"LV": ["PV_A+", "PV_B+", "GND"],          # PV/제어 (USB·CAN 포함)
                "HV": ["AC_L", "AC_N", "PHV", "PGND"],    # 계통/고압
                "PE": ["GND_EARTH"]},
    # 계통 전위에 준하는 노드 (C58 150 nF로 계통 단자와 결합)
    "hv_like": ["I_GRID_LK"],
    # 한쪽 도메인 안에서만 쓰이는 전류검출 변압기 — 권선 전체를 같은 도메인으로 병합
    "merge_xfmr_values": ["PA1005"],
    # 절연 부품 셀 이름 → 핀 그룹 (그룹 내부만 병합)
    "iso_cells": {
        "ELD207": [["1", "2", "3", "4"], ["5", "6", "7", "8"]],
        "PHOTODIODE_8": [["1", "2", "3"], ["4", "5", "6"]],          # MOC3063
        "OPTO ISOLATOR-A_6": [["1", "2"], ["3", "4"]],               # FOD817
        "AMC3301": [[str(i) for i in range(1, 9)], [str(i) for i in range(9, 17)]],
        "RELAY DPDT_8": [["1", "8"], ["3", "4"], ["5", "6"]],
    },
    "cmc_cells": ["TRANSFORMER AIR CORE"],   # CM 초크: 같은 도메인으로 병합
    "hi_r_ohm": 100e3,                       # 이 이상 저항은 병합하지 않고 교락 부품으로 기록
    # 판정 기준 [mm] — KS C 8560:2020 표 3·4·5, 강화절연은 인용표준 환산
    "checks": [
        ("강화절연 LV ↔ HV", "LV", "HV", {"OVC III": 5.5, "OVC II": 3.0, "기초 OVC II": 1.5}),
        ("기초절연 HV ↔ PE", "HV", "PE", {"OVC III": 3.0, "OVC II": 1.5}),
        ("기초절연 LV ↔ PE", "LV", "PE", {"71 Vdc OVC II": 0.2}),
    ],
    "outer_layers": ["TOP", "BOTTOM"],
    "inner_layers": ["L2", "L3"],
    "iso_refs": ["T2", "T4", "T6", "T8", "T9", "ISO1", "ISO2", "ISO3", "ISO4", "ISO5",
                 "U23", "U24", "C46", "C47", "C162", "C164", "R219", "R228"],
}

NS = "{http://webstds.ipc.org/2581}"
T = lambda e: e.tag.split("}")[1]


# ---------------------------------------------------------------- 넷리스트
def parse_netlist(path):
    nets, cur, lines = {}, None, open(path, encoding="utf-8", errors="replace").read().splitlines()
    i = 0
    while i < len(lines):
        L = lines[i]
        if L.startswith("NET_NAME"):
            cur = lines[i + 1].strip().strip("'"); nets[cur] = []; i += 2; continue
        m = re.match(r"NODE_NAME\s+(\S+)\s+(\S+)", L)
        if m and cur:
            cell = re.search(r"@([^@]+)\.NORMAL", lines[i + 1])
            nets[cur].append((m.group(1), m.group(2), cell.group(1).split(".")[-1] if cell else ""))
            i += 3; continue
        i += 1
    return nets


# ---------------------------------------------------------------- IPC-2581
def arcpts(x0, y0, x1, y1, cx, cy, cw, n=16):
    a0, a1, R = math.atan2(y0 - cy, x0 - cx), math.atan2(y1 - cy, x1 - cx), math.hypot(x0 - cx, y0 - cy)
    if cw:
        while a1 > a0: a1 -= 2 * math.pi
        if abs(a1 - a0) < 1e-9: a1 -= 2 * math.pi
    else:
        while a1 < a0: a1 += 2 * math.pi
        if abs(a1 - a0) < 1e-9: a1 += 2 * math.pi
    return [(cx + R * math.cos(a0 + (a1 - a0) * k / n), cy + R * math.sin(a0 + (a1 - a0) * k / n)) for k in range(1, n + 1)]


def polypts(el):
    pts = []
    for c in el:
        k, a = T(c), c.attrib
        if k == "PolyBegin": pts = [(float(a["x"]), float(a["y"]))]
        elif k == "PolyStepSegment": pts.append((float(a["x"]), float(a["y"])))
        elif k == "PolyStepCurve":
            pts += arcpts(*pts[-1], float(a["x"]), float(a["y"]), float(a["centerX"]), float(a["centerY"]),
                          a.get("clockwise") == "true")
    return pts


def parse_pcb(path, layers):
    r = ET.parse(path).getroot()
    prim = {}
    for es in r.iter(NS + "EntryStandard"):
        ch = list(es)[0]; k = T(ch)
        num = {x: float(v) for x, v in ch.attrib.items() if re.fullmatch(r"-?\d+(\.\d+)?", v)}
        if k == "Circle": g = Point(0, 0).buffer(num["diameter"] / 2, 32)
        elif k == "RectCenter": g = box(-num["width"] / 2, -num["height"] / 2, num["width"] / 2, num["height"] / 2)
        elif k == "Oval":
            w, h = num["width"], num["height"]; rr = min(w, h) / 2
            seg = [(-(w / 2 - rr), 0), ((w / 2 - rr), 0)] if w >= h else [(0, -(h / 2 - rr)), (0, (h / 2 - rr))]
            g = LineString(seg).buffer(rr, 32)
        elif k == "RectRound":
            w, h, rr = num["width"], num["height"], num.get("radius", 0)
            g = box(-w / 2 + rr, -h / 2 + rr, w / 2 - rr, h / 2 - rr).buffer(rr, 16) if rr else box(-w / 2, -h / 2, w / 2, h / 2)
        elif k == "Contour": g = Polygon(polypts(ch.find(NS + "Polygon"))).buffer(0)
        else: g = None
        prim[es.attrib["id"]] = g
    lw = {e.attrib["id"]: float(list(e)[0].attrib.get("lineWidth", 0)) for e in r.iter(NS + "EntryLineDesc")}

    def width(c):
        ld = c.find(NS + "LineDescRef")
        return max(lw.get(ld.attrib["id"], 0) if ld is not None else 0, 0.001)

    def feats(fe):
        for c in fe:
            k = T(c)
            if k == "Polyline":
                pts = polypts(c)
                if len(pts) >= 2: yield LineString(pts).buffer(width(c) / 2, 8)
            elif k == "Line":
                a = c.attrib
                yield LineString([(float(a["startX"]), float(a["startY"])), (float(a["endX"]), float(a["endY"]))]).buffer(width(c) / 2, 8)
            elif k == "Contour":
                p = Polygon(polypts(c.find(NS + "Polygon"))).buffer(0)
                for co in c.findall(NS + "Cutout"): p = p.difference(Polygon(polypts(co)).buffer(0))
                yield p

    def pad(p):
        loc, sp = p.find(NS + "Location"), p.find(NS + "StandardPrimitiveRef")
        if sp is None or prim.get(sp.attrib["id"]) is None: return None
        g = prim[sp.attrib["id"]]; xf = p.find(NS + "Xform")
        if xf is not None:
            if xf.attrib.get("mirror") == "true": g = affinity.scale(g, -1, 1, origin=(0, 0))
            if float(xf.attrib.get("rotation", 0)): g = affinity.rotate(g, float(xf.attrib["rotation"]), origin=(0, 0))
        return affinity.translate(g, float(loc.attrib["x"]), float(loc.attrib["y"]))

    cu = {L: collections.defaultdict(list) for L in layers}
    pinloc = collections.defaultdict(list)
    for lf in r.iter(NS + "LayerFeature"):
        L = lf.attrib.get("layerRef")
        if L not in cu: continue
        for s in lf.findall(NS + "Set"):
            net = s.attrib.get("net")
            if not net: continue
            for p in s.findall(NS + "Pad"):
                g = pad(p)
                if g is None: continue
                cu[L][net].append(g)
                pr = p.find(NS + "PinRef")
                if pr is not None: pinloc[(pr.attrib["componentRef"], pr.attrib["pin"])].append((L, g))
            for fe in s.findall(NS + "Features"): cu[L][net] += list(feats(fe))
    geo = {L: {n: unary_union(v) for n, v in d.items()} for L, d in cu.items()}
    bom = {}
    for bi in r.iter(NS + "BomItem"):
        v = ""
        for tx in bi.iter(NS + "Textual"): v = tx.attrib.get("textualCharacteristicValue", v)
        for rd in bi.iter(NS + "RefDes"): bom[rd.attrib["name"]] = v
    return geo, pinloc, bom


# ---------------------------------------------------------------- 도메인
def rval(v):
    if not v or "NC" in v.upper(): return None
    m = re.search(r"(\d+(?:\.\d+)?)\s*mR", v)
    if m: return float(m.group(1)) * 1e-3
    m = re.match(r"\s*([\d.]+)\s*(m|K|M)?", v)
    return float(m.group(1)) * {None: 1, "m": 1e-3, "K": 1e3, "M": 1e6}[m.group(2)] if m else None


def domains(nets, bom, cfg):
    par = {n: n for n in nets}
    def f(x):
        while par[x] != x: par[x] = par[par[x]]; x = par[x]
        return x
    def u(a, b): par[f(a)] = f(b)
    comp = collections.defaultdict(list)
    for n, nodes in nets.items():
        for ref, pin, cell in nodes: comp[ref].append((pin, n, cell))
    bridges = []
    for ref, pins in comp.items():
        cell, pn = pins[0][2], {p: n for p, n, _ in pins}
        ns = [n for _, n, _ in pins if n != "NC"]
        val = bom.get(ref, "")
        iso = next((g for k, g in cfg["iso_cells"].items() if k in cell), None)
        if iso:
            for grp in iso:
                g = [pn[p] for p in grp if pn.get(p, "NC") != "NC"]
                for x in g[1:]: u(g[0], x)
            bridges.append((ref, "ISO", sorted(set(ns)), val)); continue
        if any(k in cell for k in cfg["cmc_cells"]) or any(k in val for k in cfg["merge_xfmr_values"]):
            for x in ns[1:]: u(ns[0], x)
            continue
        if ref.startswith("T"):
            bridges.append((ref, "XFMR", sorted(set(ns)), val)); continue
        if ref.startswith(("C", "EC", "RV")) or ref == "TH1" or "GDT" in cell or "VARISTOR" in cell or val.startswith("SL14"):
            bridges.append((ref, "CAP/SURGE", ns, val)); continue
        if ref.startswith("R"):
            rv = rval(val)
            if rv is None: continue
            if rv >= cfg["hi_r_ohm"]:
                bridges.append((ref, "HI-R", ns, val)); continue
        for x in ns[1:]: u(ns[0], x)
    label = {}
    for dom, anchors in cfg["anchors"].items():
        roots = {f(a) for a in anchors if a in nets}
        for n in nets:
            if f(n) in roots: label[n] = dom
    for a in cfg["hv_like"]:
        for n in nets:
            if a in nets and f(n) == f(a): label[n] = "HV"
    # 미분류 소형 도메인: 교락 부품 이웃이 한 도메인뿐이면 그 도메인으로
    nb = collections.defaultdict(set)
    for ref, kind, ns, _ in bridges:
        for x in ns:
            for y in ns:
                if x != y: nb[f(x)].add(f(y))
    root_lab = {f(n): l for n, l in label.items()}
    for n in nets:
        if n in label or n == "NC": continue
        ls = {root_lab.get(x) for x in nb[f(n)]} - {None}
        if len(ls) == 1: label[n] = ls.pop()
    return label, bridges, comp


# ---------------------------------------------------------------- 측정
def near_pin(pt, L, pinloc):
    best = None
    for (ref, pin), lst in pinloc.items():
        for LL, g in lst:
            if LL == L:
                d = g.distance(pt)
                if best is None or d < best[0]: best = (d, f"{ref}.{pin}")
    return best[1] if best else "?"


def check(geo, pinloc, label, cfg, layers, thr_filter=None):
    rows = []
    for title, A, B, req in cfg["checks"]:
        thr = max(req.values())
        for L in layers:
            an = [n for n in geo[L] if label.get(n) == A]; bn = [n for n in geo[L] if label.get(n) == B]
            if not an or not bn: continue
            bg = [geo[L][n] for n in bn]; tree = STRtree(bg)
            for na in an:
                ga = geo[L][na]
                for idx in tree.query(ga.buffer(thr)):
                    d = ga.distance(bg[idx])
                    if d < thr:
                        p, _ = nearest_points(ga, bg[idx])
                        fails = [k for k, v in req.items() if d < v]
                        rows.append((title, L, round(d, 3), na, bn[idx], (round(p.x, 1), round(p.y, 1)),
                                     near_pin(p, L, pinloc), fails))
    return sorted(rows, key=lambda r: (r[0], r[2]))


def iso_gaps(geo, pinloc, label, comp, refs, layers):
    out = []
    for ref in refs:
        pins = {p: n for p, n, _ in comp.get(ref, [])}
        side = lambda n: label.get(n)
        best = None
        for L in layers:
            hv = [g for (r, p), lst in pinloc.items() if r == ref and side(pins.get(p)) == "HV" for LL, g in lst if LL == L]
            lv = [g for (r, p), lst in pinloc.items() if r == ref and side(pins.get(p)) == "LV" for LL, g in lst if LL == L]
            if hv and lv:
                d = unary_union(hv).distance(unary_union(lv))
                if best is None or d < best[0]: best = (d, L)
        out.append((ref, best))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pcb", required=True); ap.add_argument("--net", required=True); ap.add_argument("--out")
    a = ap.parse_args(); cfg = CONFIG
    layers = cfg["outer_layers"] + cfg["inner_layers"]
    nets = parse_netlist(a.net)
    geo, pinloc, bom = parse_pcb(a.pcb, layers)
    label, bridges, comp = domains(nets, bom, cfg)
    cnt = collections.Counter(label.get(n, "?") for n in nets)
    pcb_nets = {x for L in geo for x in geo[L]}
    missing = sorted(n for n in pcb_nets if n not in nets and not n.startswith("Unused_"))   # Unused_ = 미사용 핀
    unrouted = sorted(n for n in nets if n not in pcb_nets and n != "NC")

    o = ["# KS C 8560 8.3.4 절연거리 사전 검증 결과", "",
         f"- PCB: `{a.pcb}`", f"- 넷리스트: `{a.net}`",
         f"- 도메인 분류: " + ", ".join(f"{k} {v}넷" for k, v in cnt.most_common()),
         f"- 회로도↔PCB 넷 불일치: PCB 전용 {len(missing)}개" + (f" {missing[:5]}" if missing else "")
         + f", 동박 없는 회로도 넷 {len(unrouted)}개" + (f" {unrouted[:5]}" if unrouted else ""), ""]
    for scope, lays in (("외층 (공간거리·연면거리)", cfg["outer_layers"]), ("내층 (참고 — 적층 절연 인정 여부에 따름)", cfg["inner_layers"])):
        rows = check(geo, pinloc, label, cfg, lays)
        o += [f"## {scope}", ""]
        if not rows: o += ["기준 미달 없음.", ""]; continue
        o += ["| 검사 | 층 | 거리 mm | 넷 A | 넷 B | 위치 | 인접 핀 | 미달 기준 |", "|---|---|---:|---|---|---|---|---|"]
        seen = set()
        for t, L, d, na, nb_, xy, pin, fails in rows:
            if (t, L, na, nb_) in seen: continue
            seen.add((t, L, na, nb_))
            o.append(f"| {t} | {L} | {d:.2f} | {na} | {nb_} | {xy} | {pin} | {', '.join(fails)} |")
        o.append("")
    o += ["## 절연 부품 풋프린트 (HV 패드 ↔ LV 패드)", "", "| 부품 | 값 | 최소간격 |", "|---|---|---|"]
    for ref, best in iso_gaps(geo, pinloc, label, comp, cfg["iso_refs"], cfg["outer_layers"]):
        o.append(f"| {ref} | {bom.get(ref, '')[:30]} | {('%.2f mm (%s)' % best) if best else '— (한쪽 측만)'} |")
    o += ["", "## LV ↔ HV 장벽 교락 부품 (넷리스트)", "", "| 부품 | 종류 | 값 |", "|---|---|---|"]
    for ref, kind, ns, val in sorted(bridges):
        doms = {label.get(n) for n in ns}
        if {"LV", "HV"} <= doms: o.append(f"| {ref} | {kind} | {val[:40]} |")
    txt = "\n".join(o) + "\n"
    (open(a.out, "w", encoding="utf-8").write(txt) if a.out else sys.stdout.write(txt))


if __name__ == "__main__":
    main()
