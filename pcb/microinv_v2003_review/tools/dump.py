import pcbnew, json, math
b = pcbnew.LoadBoard('/work/board.kicad_pcb')
mm = pcbnew.ToMM
L = lambda lid: b.GetLayerName(lid)
out = {}
bb = b.GetBoardEdgesBoundingBox()
out['board'] = dict(w=mm(bb.GetWidth()), h=mm(bb.GetHeight()), x0=mm(bb.GetX()), y0=mm(bb.GetY()),
                    copper_layers=b.GetCopperLayerCount(), thickness=mm(b.GetDesignSettings().GetBoardThickness()))
out['layers'] = [L(l) for l in b.GetEnabledLayers().Seq()]
# stackup
try:
    st = b.GetDesignSettings().GetStackupDescriptor()
    out['stackup'] = [dict(name=it.GetLayerName(), type=it.GetTypeName(), thick=mm(it.GetThickness()),
                           mat=it.GetMaterial(), er=it.GetEpsilonR()) for it in st.GetList()]
except Exception as e:
    out['stackup'] = str(e)
ds = b.GetDesignSettings()
out['rules'] = dict(min_clear=mm(ds.m_MinClearance), min_track=mm(ds.m_TrackMinWidth), min_via=mm(ds.m_ViasMinSize),
                    min_drill=mm(ds.m_MinThroughDrill), min_ring=mm(ds.m_ViasMinAnnularWidth), hole_to_hole=mm(ds.m_HoleToHoleMin),
                    edge_clear=mm(ds.m_CopperEdgeClearance))
# net classes
fps = []
def pshape(p):
    for f in (lambda: p.GetShape(pcbnew.F_Cu), lambda: p.GetShape(pcbnew.PADSTACK.ALL_LAYERS), lambda: p.GetShape()):
        try: return int(f())
        except Exception: pass
    return -1
def psz(p):
    for f in (lambda: p.GetSize(pcbnew.F_Cu), lambda: p.GetSize(pcbnew.PADSTACK.ALL_LAYERS), lambda: p.GetSize()):
        try: return f()
        except Exception: pass
    return pcbnew.VECTOR2I(0,0)
for f in b.GetFootprints():
    pads = []
    for p in f.Pads():
        dr = p.GetDrillSize()
        pads.append(dict(num=p.GetNumber(), net=p.GetNetname(), shape=pshape(p),
                         sx=round(mm(psz(p).x),4),
                         sy=round(mm(psz(p).y),4),
                         dx=round(mm(dr.x),4), dy=round(mm(dr.y),4), attr=int(p.GetAttribute()),
                         x=round(mm(p.GetPosition().x),4), y=round(mm(p.GetPosition().y),4),
                         orient=round(p.GetOrientationDegrees(),2), plated=p.GetAttribute()==pcbnew.PAD_ATTRIB_PTH,
                         layers=[L(l) for l in p.GetLayerSet().Seq()][:4]))
    cb = f.GetCourtyard(pcbnew.F_CrtYd) if False else None
    bbx = f.GetBoundingBox(False)
    fps.append(dict(ref=f.GetReference(), value=f.GetValue(), fpid=str(f.GetFPID().GetLibItemName()),
                    x=round(mm(f.GetPosition().x),3), y=round(mm(f.GetPosition().y),3), rot=round(f.GetOrientationDegrees(),2),
                    side='BOTTOM' if f.IsFlipped() else 'TOP', w=round(mm(bbx.GetWidth()),2), h=round(mm(bbx.GetHeight()),2),
                    attrs=int(f.GetAttributes()), pads=pads,
                    fields={fl.GetName(): fl.GetText() for fl in f.GetFields()}))
out['footprints'] = fps
tr = []; vi = []
for t in b.GetTracks():
    if t.GetClass() == 'PCB_VIA':
        v = pcbnew.Cast_to_PCB_VIA(t) if hasattr(pcbnew,'Cast_to_PCB_VIA') else t
        vi.append(dict(net=t.GetNetname(), x=round(mm(t.GetPosition().x),3), y=round(mm(t.GetPosition().y),3),
                       d=round(mm(v.GetWidth(pcbnew.F_Cu)) if hasattr(v,'GetWidth') else 0,3), drill=round(mm(v.GetDrillValue()),3),
                       vt=int(v.GetViaType())))
    else:
        tr.append(dict(net=t.GetNetname(), layer=L(t.GetLayer()), w=round(mm(t.GetWidth()),3), len=round(mm(t.GetLength()),3),
                       x1=round(mm(t.GetStart().x),3), y1=round(mm(t.GetStart().y),3), x2=round(mm(t.GetEnd().x),3), y2=round(mm(t.GetEnd().y),3),
                       arc=t.GetClass()=='PCB_ARC'))
out['tracks'] = tr; out['vias'] = vi
zs = []
for z in b.Zones():
    try: area = mm(mm(z.GetFilledArea())) if False else z.GetFilledArea()/1e12
    except Exception: area = None
    zbb = z.GetBoundingBox()
    zs.append(dict(net=z.GetNetname(), layers=[L(l) for l in z.GetLayerSet().Seq()], keepout=z.GetIsRuleArea(),
                   no_copper=z.GetDoNotAllowZoneFills() if z.GetIsRuleArea() else None,
                   no_tracks=z.GetDoNotAllowTracks() if z.GetIsRuleArea() else None,
                   no_vias=z.GetDoNotAllowVias() if z.GetIsRuleArea() else None,
                   area_mm2=round(area,1) if area else None, filled=z.IsFilled(),
                   bbox=[round(mm(zbb.GetX()),2), round(mm(zbb.GetY()),2), round(mm(zbb.GetRight()),2), round(mm(zbb.GetBottom()),2)],
                   clearance=round(mm(z.GetLocalClearance() or 0),3) if hasattr(z,'GetLocalClearance') and z.GetLocalClearance() is not None else None,
                   min_width=round(mm(z.GetMinThickness()),3), name=z.GetZoneName(), priority=z.GetAssignedPriority()))
out['zones'] = zs
out['nets'] = sorted(str(n) for n in b.GetNetsByName().keys())
# board outline segments / cutouts
edges = []
for d in b.GetDrawings():
    if d.GetLayer() == pcbnew.Edge_Cuts:
        bbd = d.GetBoundingBox()
        edges.append(dict(shape=d.ShowShape() if hasattr(d,'ShowShape') else str(d.GetShape()),
                          bbox=[round(mm(bbd.GetX()),2), round(mm(bbd.GetY()),2), round(mm(bbd.GetRight()),2), round(mm(bbd.GetBottom()),2)]))
out['edges'] = edges
json.dump(out, open('/work/board.json','w'), ensure_ascii=False)
print('footprints', len(fps), 'tracks', len(tr), 'vias', len(vi), 'zones', len(zs), 'edges', len(edges))
print('board', out['board']); print('rules', out['rules']); print('layers', out['layers'])
