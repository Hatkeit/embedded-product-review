import pymupdf,re,json,math,sys,collections
sys.path.insert(0,'v2')
from decode import d,page_texts
BLUE=(0.26,0.0,1.0); RED=(1.0,0.0,0.0); BROWN=(0.67,0.54,0.27); ORANGE=(0.8,0.5,0.02); BLACK=(0.0,0.0,0.0)
REFDES=re.compile(r'^(R|C|L|D|U|Q|J|T|F|Y|EC|ZD|RV|LS|TH|ISO|TSW|TP|K|SW|X)\d{1,3}[A-H]?$')
def rc(c): return tuple(round(x,2) for x in c) if c else None
def tr(p,pt): 
    q=pymupdf.Point(pt)*p.rotation_matrix; return (round(q.x,2),round(q.y,2))
def trrect(p,r):
    a=tr(p,(r[0],r[1])); b=tr(p,(r[2],r[3])); return (min(a[0],b[0]),min(a[1],b[1]),max(a[0],b[0]),max(a[1],b[1]))
class UF:
    def __init__(s): s.p={}
    def f(s,x):
        s.p.setdefault(x,x)
        while s.p[x]!=x: s.p[x]=s.p[s.p[x]]; x=s.p[x]
        return x
    def u(s,a,b):
        ra,rb=s.f(a),s.f(b)
        if ra!=rb: s.p[ra]=rb
def seg_pt_dist(seg,pt):
    x1,y1,x2,y2=seg; px,py=pt
    dx,dy=x2-x1,y2-y1; L2=dx*dx+dy*dy
    if L2==0: return math.hypot(px-x1,py-y1)
    t=max(0,min(1,((px-x1)*dx+(py-y1)*dy)/L2))
    return math.hypot(px-(x1+t*dx),py-(y1+t*dy))
def rect_dist(a,b):
    dx=max(a[0]-b[2],b[0]-a[2],0); dy=max(a[1]-b[3],b[1]-a[3],0); return math.hypot(dx,dy)
def extract(i,TOL=1.2):
    p=d[i]
    wires=[];pins=[];junc=[];bodies_items=[];black=[]
    for g in p.get_drawings():
        c=rc(g.get('color')); f=rc(g.get('fill'))
        for it in g['items']:
            if it[0]=='l':
                a=tr(p,it[1]); b=tr(p,it[2]); seg=(a[0],a[1],b[0],b[1])
                if c==BLUE: wires.append(seg)
                elif c==BROWN: pins.append(seg)
                elif c==ORANGE or f==ORANGE: bodies_items.append((min(a[0],b[0]),min(a[1],b[1]),max(a[0],b[0]),max(a[1],b[1])))
                elif c==BLACK or f==BLACK:
                    if math.hypot(a[0]-b[0],a[1]-b[1])<30: black.append(seg)
            elif it[0]=='c':
                r=trrect(p,g['rect'])
                if c==RED and f==RED: junc.append(((r[0]+r[2])/2,(r[1]+r[3])/2))
                elif c==ORANGE or f==ORANGE: bodies_items.append(r)
                elif c==BROWN: bodies_items.append(r)  # pin circle (inversion bubble) treat as body
            elif it[0] in ('re','qu'):
                r=trrect(p,g['rect'])
                if c==ORANGE or f==ORANGE: bodies_items.append(r)
    # merge collinear touching brown pin segments
    def merge_pins(pins):
        pins=[list(s) for s in pins]; changed=True
        while changed:
            changed=False
            for a in range(len(pins)):
                for b in range(a+1,len(pins)):
                    sa,sb=pins[a],pins[b]
                    ha=abs(sa[1]-sa[3])<0.3; hb=abs(sb[1]-sb[3])<0.3
                    va=abs(sa[0]-sa[2])<0.3; vb=abs(sb[0]-sb[2])<0.3
                    if ha and hb and abs(sa[1]-sb[1])<0.3:
                        xa=sorted([sa[0],sa[2]]); xb=sorted([sb[0],sb[2]])
                        if xa[1]>=xb[0]-0.6 and xb[1]>=xa[0]-0.6:
                            pins[a]=[min(xa[0],xb[0]),sa[1],max(xa[1],xb[1]),sa[1]]; pins.pop(b); changed=True; break
                    elif va and vb and abs(sa[0]-sb[0])<0.3:
                        ya=sorted([sa[1],sa[3]]); yb=sorted([sb[1],sb[3]])
                        if ya[1]>=yb[0]-0.6 and yb[1]>=ya[0]-0.6:
                            pins[a]=[sa[0],min(ya[0],yb[0]),sa[0],max(ya[1],yb[1])]; pins.pop(b); changed=True; break
                if changed: break
        return [tuple(s) for s in pins]
    pins=merge_pins(pins)
    # net union-find over wire + black segments
    segs=[('w',s) for s in wires]+[('b',s) for s in black]
    uf=UF()
    pts=[]
    for k,(t,s) in enumerate(segs):
        uf.u(('s',k),('s',k))
    # endpoints touching other segments
    for k,(t,s) in enumerate(segs):
        for e in ((s[0],s[1]),(s[2],s[3])):
            for m,(t2,s2) in enumerate(segs):
                if m==k: continue
                tol=TOL if (t=='w' and t2=='w') else (1.5 if (t=='b' and t2=='b') else 2.0)
                # wire-wire: end-to-end only (OrCAD draws a junction dot for every T-connection); symbols: endpoint-on-segment
                if t=='w' and t2=='w':
                    if min(math.hypot(e[0]-s2[0],e[1]-s2[1]),math.hypot(e[0]-s2[2],e[1]-s2[3]))<=tol: uf.u(('s',k),('s',m))
                else:
                    # symbol segments must be axis-aligned (port chevrons are diagonal and handled by label rule)
                    ax=lambda q: abs(q[0]-q[2])<0.3 or abs(q[1]-q[3])<0.3
                    if (t=='w' or ax(s)) and (t2=='w' or ax(s2)):
                        if seg_pt_dist(s2,e)<=tol: uf.u(('s',k),('s',m))
    # ground-symbol bars: parallel horizontal black segments, same centre x, small vertical gap
    bl=[(k,s) for k,(t,s) in enumerate(segs) if t=='b' and abs(s[1]-s[3])<0.3 and abs(s[0]-s[2])>=3.0]
    for a in range(len(bl)):
        ka,sa=bl[a]; cxa=(sa[0]+sa[2])/2
        for b in range(a+1,len(bl)):
            kb,sb=bl[b]; cxb=(sb[0]+sb[2])/2
            if abs(cxa-cxb)<=1.0 and abs(sa[1]-sb[1])<=2.6: uf.u(('s',ka),('s',kb))
    # junctions: merge all segments passing through
    for jp in junc:
        ks=[k for k,(t,s) in enumerate(segs) if seg_pt_dist(s,jp)<=2.0]
        for k in ks[1:]: uf.u(('s',ks[0]),('s',k))
    # pins -> nets
    pinrec=[]
    for k,s in enumerate(pins):
        net=None; outer=None
        for e in ((s[0],s[1]),(s[2],s[3])):
            for m,(t,s2) in enumerate(segs):
                if seg_pt_dist(s2,e)<=TOL: net=uf.f(('s',m)); outer=e; break
            if net: break
        pinrec.append(dict(seg=s,net=net,outer=outer))
    # pin-to-pin direct touching (e.g. pins joined without wire)
    for a in range(len(pins)):
        for b in range(a+1,len(pins)):
            sa,sb=pins[a],pins[b]
            for e in ((sa[0],sa[1]),(sa[2],sa[3])):
                if seg_pt_dist(sb,e)<=TOL:
                    # create pseudo net
                    if pinrec[a]['net'] is None and pinrec[b]['net'] is None:
                        key=('pp',a,b); pinrec[a]['net']=key; pinrec[b]['net']=key
                    elif pinrec[a]['net'] is None: pinrec[a]['net']=pinrec[b]['net']
                    elif pinrec[b]['net'] is None: pinrec[b]['net']=pinrec[a]['net']
                    else: uf.u(pinrec[a]['net'],pinrec[b]['net'])
    for r in pinrec:
        if r['net'] is not None and r['net'][0]=='s': r['net']=uf.f(r['net'])
    # bodies: cluster orange items
    buf=UF()
    for a in range(len(bodies_items)):
        buf.u(a,a)
        for b in range(a+1,len(bodies_items)):
            if rect_dist(bodies_items[a],bodies_items[b])<=2.5: buf.u(a,b)
    groups=collections.defaultdict(list)
    for a in range(len(bodies_items)): groups[buf.f(a)].append(bodies_items[a])
    bodies=[]; body_items=[]
    for k,items in groups.items():
        bodies.append((min(x[0] for x in items),min(x[1] for x in items),max(x[2] for x in items),max(x[3] for x in items))); body_items.append(items)
    # assign pins to bodies via inner end
    for r in pinrec:
        s=r['seg']; ends=[(s[0],s[1]),(s[2],s[3])]
        best=None
        for e in ends:
            for bi,bb in enumerate(bodies):
                dd=rect_dist((e[0],e[1],e[0],e[1]),bb)
                if best is None or dd<best[0]: best=(dd,bi,e)
        r['body']=best[1] if best and best[0]<=3.0 else None
        r['inner']=best[2] if best else None
    # texts
    texts=page_texts(i)
    for t in texts:
        t['bb']=trrect(p,(t['x0'],t['y0'],t['x1'],t['y1']))
    # display-level merge of split text fragments
    texts.sort(key=lambda t:(t['bb'][0],t['bb'][1]))
    merged=[]
    for t in texts:
        s=t['t']
        if not s.strip(): continue
        bb=t['bb']; horiz=(bb[2]-bb[0])>=(bb[3]-bb[1]) or len(s.strip())==1
        done=False
        for m in merged:
            if m['col']!=t['col'] or abs(m['size']-t['size'])>0.2: continue
            mb=m['bb']; mh=m['horiz']
            if len(m['t'].strip())>1 and len(s.strip())>1 and mh!=horiz: continue
            if len(m['t'].strip())==1 and len(s.strip())>1: mh=horiz; m['horiz']=horiz
            if mh:
                if abs((mb[1]+mb[3])/2-(bb[1]+bb[3])/2)>1.5: continue
                gap=bb[0]-mb[2]; gap2=mb[0]-bb[2]
                if -1.8<=gap<2.6: m['t']=m['t']+s
                elif -1.8<=gap2<2.6: m['t']=s+m['t']
                else: continue
            else:
                if abs((mb[0]+mb[2])/2-(bb[0]+bb[2])/2)>1.5: continue
                gap=mb[1]-bb[3]; gap2=bb[1]-mb[3]
                if -1.8<=gap<2.6: m['t']=m['t']+s
                elif -1.8<=gap2<2.6: m['t']=s+m['t']
                else: continue
            m['bb']=(min(mb[0],bb[0]),min(mb[1],bb[1]),max(mb[2],bb[2]),max(mb[3],bb[3])); done=True; break
        if not done:
            t2=dict(t); t2['horiz']=horiz; merged.append(t2)
    texts=merged
    # net labels: geometry-aware association
    seg_by_net=collections.defaultdict(list)
    for k,(t,s) in enumerate(segs): seg_by_net[uf.f(('s',k))].append((t,s))
    wire_segs=[(k,s) for k,(t,s) in enumerate(segs) if t=='w']
    for t in texts:
        s=t['t'].strip(); t['nearnet']=None
        if not s or re.fullmatch(r'\d+',s) or REFDES.match(s): continue
        bb=t['bb']; horiz=(bb[2]-bb[0])>=(bb[3]-bb[1])
        red=(t['col']==16711680)
        best=None
        if red:
            cx=(bb[0]+bb[2])/2; cy=(bb[1]+bb[3])/2
            for k,ws in wire_segs:
                for e_ in ((ws[0],ws[1]),(ws[2],ws[3])):
                    if horiz:
                        if abs(e_[1]-cy)<=3.5 and (bb[2]-0.5<=e_[0]<=bb[2]+12.5 or bb[0]-12.5<=e_[0]<=bb[0]+0.5):
                            dd=min(abs(e_[0]-bb[2]),abs(e_[0]-bb[0]))+3*abs(e_[1]-cy)
                            if best is None or dd<best[0]: best=(dd,uf.f(('s',k)))
                    else:
                        if abs(e_[0]-cx)<=3.5 and (bb[3]-0.5<=e_[1]<=bb[3]+12.5 or bb[1]-12.5<=e_[1]<=bb[1]+0.5):
                            dd=min(abs(e_[1]-bb[3]),abs(e_[1]-bb[1]))+3*abs(e_[0]-cx)
                            if best is None or dd<best[0]: best=(dd,uf.f(('s',k)))
        else:
            for net,ss in seg_by_net.items():
                for typ,sg in ss:
                    if typ=='w':
                        hs=abs(sg[1]-sg[3])<0.3; vs=abs(sg[0]-sg[2])<0.3
                        if horiz and hs:
                            if not (min(sg[0],sg[2])-1<=bb[2] and max(sg[0],sg[2])+1>=bb[0]): continue
                            dy=sg[1]-bb[3]
                            if -0.6<=dy<=2.8: dd=abs(dy)
                            else: continue
                        elif (not horiz) and vs:
                            if not (min(sg[1],sg[3])-1<=bb[3] and max(sg[1],sg[3])+1>=bb[1]): continue
                            dx=min(abs(bb[0]-sg[0]),abs(sg[0]-bb[2]))
                            if dx<=2.8: dd=dx
                            else: continue
                        else: continue
                    else:
                        if not re.match(r'^(GND|PGND|FGND|AGND|VDD|VCC|VDDA|PHV|VSS|PV_)',s): continue
                        dd=rect_dist(bb,(min(sg[0],sg[2]),min(sg[1],sg[3]),max(sg[0],sg[2]),max(sg[1],sg[3])))
                        if dd>3.0: continue
                    if best is None or dd<best[0]: best=(dd,net)
        t['nearnet']=best
    return dict(page=i,wires=wires,black=black,pins=pinrec,junc=junc,bodies=bodies,body_items=body_items,texts=texts,segs=segs,uf=uf)
if __name__=='__main__':
    i=int(sys.argv[1]); r=extract(i)
    print('wires',len(r['wires']),'pins',len(r['pins']),'bodies',len(r['bodies']),'junc',len(r['junc']))
    print('pins w/o net',sum(1 for x in r['pins'] if x['net'] is None),'pins w/o body',sum(1 for x in r['pins'] if x['body'] is None))
    for t in r['texts']:
        if t.get('nearnet') and t['nearnet'][0]<=3.0: print('LBL',t['t'],t['col'],round(t['nearnet'][0],1),t['nearnet'][1])
