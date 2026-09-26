import pcbnew, json
b = pcbnew.LoadBoard('/work/board.kicad_pcb'); mm = pcbnew.ToMM
CU = [l for l in b.GetEnabledLayers().CuStack()]
out = {b.GetLayerName(l): {} for l in CU}
def add(layer, net, ps):
    if not net: net = '<nonet>'
    d = out[b.GetLayerName(layer)].setdefault(net, [])
    for i in range(ps.OutlineCount()):
        o = ps.Outline(i); pts = [(round(mm(o.CPoint(k).x),3), round(-mm(o.CPoint(k).y),3)) for k in range(o.PointCount())]
        holes = []
        for h in range(ps.HoleCount(i)):
            hh = ps.Hole(i, h); holes.append([(round(mm(hh.CPoint(k).x),3), round(-mm(hh.CPoint(k).y),3)) for k in range(hh.PointCount())])
        if len(pts) >= 3: d.append([pts, holes])
ERR = pcbnew.FromMM(0.01)
for l in CU:
    for z in b.Zones():
        if z.GetIsRuleArea() or not z.IsOnLayer(l): continue
        fp = z.GetFilledPolysList(l)
        if fp and fp.OutlineCount(): add(l, z.GetNetname(), fp)
    for t in b.GetTracks():
        if not t.IsOnLayer(l): continue
        ps = pcbnew.SHAPE_POLY_SET(); t.TransformShapeToPolygon(ps, l, 0, ERR, pcbnew.ERROR_INSIDE); add(l, t.GetNetname(), ps)
    for f in b.GetFootprints():
        for p in f.Pads():
            if not p.IsOnLayer(l): continue
            ps = pcbnew.SHAPE_POLY_SET(); p.TransformShapeToPolygon(ps, l, 0, ERR, pcbnew.ERROR_INSIDE); add(l, p.GetNetname(), ps)
json.dump(out, open('/work/polys.json', 'w'))
print({k: sum(len(v) for v in d.values()) for k, d in out.items()})
