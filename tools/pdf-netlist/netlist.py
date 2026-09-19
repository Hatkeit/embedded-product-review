import sys,re,json,math,collections
sys.path.insert(0,'v2')
from extract import extract,REFDES,rect_dist,seg_pt_dist,UF
FOOT=re.compile(r'^(RESC|CAPC|DIOM|SON|SOT|SOP|SOIC|QFN|LQFP|DSO|XFMR|BEADC|MPX|RT0603|XTAL|hdr|RLYRR|HoLR|TSSOP|SOD|sot|SMD|c1608|c3216|CAPRR|CAPCC|USB-C|ESP32-S3$|DQN|DOA|MP2334|PX)',re.I)
def is_value(s):
    return bool(re.search(r'\d',s)) and bool(re.search(r'(nF|uF|pF|mH|uH|KF|KB|MF|F|B|M|m|V|VAC|W|K|k)$',s)) or re.fullmatch(r'[\d.]+',s) is not None
NETNAME=re.compile(r'^/?[A-Z][A-Za-z0-9_+\-]{1,20}$')
MISC={'NC','A3','MicroInv','Application','Drawn','Checked','Approved','Description','Revision','Update','Size','Page','of','conalog.com','DM.Shin','GRID','ADC','500W','V2000','V1200','TPM','CAN','OTA','BOOT','USB-C','ESP32','easydsp','EX_Enable','DC/AC','ADC/AIN','MOSFET','Temp','CAP','DC/DC','PV','DCLINK'}
def classify(s):
    if REFDES.match(s): return 'ref'
    if re.fullmatch(r'\d+',s): return 'num'
    if FOOT.match(s): return 'foot'
    if s in MISC: return 'misc'
    if is_value(s): return 'val'
    if re.search(r'\d{3,}',s) or re.match(r'\d',s): return 'part'
    if re.fullmatch(r'[AB]\d{1,2}',s) or re.fullmatch(r'MH\d',s) or re.fullmatch(r'[A-Z]+\d+[A-Z]+\d+[A-Z]*',s): return 'part'
    if NETNAME.match(s) and not re.search(r'[a-z]{2,}',s): return 'name'
    return 'other'
def cluster(items,tol):
    u=UF()
    for a in range(len(items)):
        u.u(a,a)
        for b in range(a+1,len(items)):
            if rect_dist(items[a],items[b])<=tol: u.u(a,b)
    g=collections.defaultdict(list)
    for a in range(len(items)): g[u.f(a)].append(items[a])
    out=[]
    for its in g.values():
        out.append(((min(x[0] for x in its),min(x[1] for x in its),max(x[2] for x in its),max(x[3] for x in its)),its))
    return out
def build(i):
    r=extract(i)
    pins=r['pins']; texts=r['texts']; uf=r['uf']
    bodies=[(bb,its) for bb,its in zip(r['bodies'],r['body_items'])]
    blk=[t for t in texts if t['col']==0 and t['t'].strip()]
    for t in blk: t['cls']=classify(t['t'].strip())
    blk.sort(key=lambda t:(round(t['bb'][0]),t['bb'][1]))
    stacks=[]; used=set()
    for a,t in enumerate(blk):
        if a in used or t['cls']!='ref': continue
        st=[t]; used.add(a); cur=t; changed=True
        while changed:
            changed=False
            for b,u in enumerate(blk):
                if b in used: continue
                if abs(u['bb'][0]-cur['bb'][0])<2.5 and 0<=u['bb'][1]-cur['bb'][3]<3.5 and u['cls'] in ('val','foot','part','other','misc','name'):
                    st.append(u); used.add(b); cur=u; changed=True; break
        stacks.append(st)
    for st in stacks:
        t=st[0]
        for b,u in enumerate(blk):
            if b in used: continue
            if abs(u['bb'][1]-t['bb'][1])<1.5 and 0<u['bb'][0]-t['bb'][2]<12 and u['cls'] in ('val','foot','part'):
                st.append(u); used.add(b)
    def sbbox(st): return (min(x['bb'][0] for x in st),min(x['bb'][1] for x in st),max(x['bb'][2] for x in st),max(x['bb'][3] for x in st))
    def assign(bodies):
        body_ref=collections.defaultdict(list); comps={}
        for st in stacks:
            sb=sbbox(st); ref=st[0]['t'].strip()
            best=min(((rect_dist(sb,bb),bi) for bi,(bb,its) in enumerate(bodies)),default=None)
            comps[ref]=dict(ref=ref,lines=[x['t'].strip() for x in st[1:]],body=best[1] if best and best[0]<=25 else None,bdist=round(best[0],1) if best else None,pins=[],sbb=sb)
            if comps[ref]['body'] is not None: body_ref[comps[ref]['body']].append(ref)
        return comps,body_ref
    comps,body_ref=assign(bodies)
    # split multi-ref bodies with tighter clustering
    for _ in range(3):
        multi=[bi for bi,v in body_ref.items() if len(v)>1]
        if not multi: break
        newb=[]
        for bi,(bb,its) in enumerate(bodies):
            if bi in multi:
                sub=cluster(its,0.6)
                newb.extend(sub if len(sub)>1 else [(bb,its)])
            else: newb.append((bb,its))
        bodies=newb; comps,body_ref=assign(bodies)
    # fallback: stacks without body -> nearest refdes-less body within 60pt
    for ref,c in comps.items():
        if c['body'] is None:
            cand=[(rect_dist(c['sbb'],bb),bi) for bi,(bb,its) in enumerate(bodies) if bi not in body_ref]
            cand=[x for x in cand if x[0]<=60]
            if cand:
                dd,bi=min(cand); c['body']=bi; c['bdist']=round(dd,1); body_ref[bi].append(ref)
    # transformers: absorb refdes-less bodies within 15pt (iterative)
    absorbed={}
    for ref,c in comps.items():
        if ref.startswith('T') and c['body'] is not None:
            grp={c['body']}; changed=True
            while changed:
                changed=False
                for bi,(bb,its) in enumerate(bodies):
                    if bi in grp or bi in body_ref: continue
                    if any(rect_dist(bb,bodies[g][0])<=15 for g in grp): grp.add(bi); changed=True
            for g in grp: absorbed[g]=ref
    # pin numbers & names
    nums=[t for t in texts if t['col']==0 and re.fullmatch(r'\d+',t['t'].strip())]
    names=[t for t in texts if (t['col']&0xFF)>=0x80 and (t['col']>>16)==0 and t['t'].strip()]
    for pr in pins:
        s=pr['seg']
        bn=None
        for t in nums:
            bb=t['bb']; tc=((bb[0]+bb[2])/2,(bb[1]+bb[3])/2); dd=seg_pt_dist(s,tc)
            if dd<=4.5 and (bn is None or dd<bn[0]): bn=(dd,t['t'].strip())
        pr['num']=bn[1] if bn else None
        # body by inner end
        ends=[(s[0],s[1]),(s[2],s[3])]; best=None
        for e in ends:
            for bi,(bb,its) in enumerate(bodies):
                dd=rect_dist((e[0],e[1],e[0],e[1]),bb)
                if best is None or dd<best[0]: best=(dd,bi,e)
        pr['body']=best[1] if best and best[0]<=7.0 else None; pr['inner']=best[2] if best else None
        bm=None
        for t in names:
            bb=t['bb']; dd=rect_dist((pr['inner'][0],pr['inner'][1],pr['inner'][0],pr['inner'][1]),bb)
            if dd<=6 and (bm is None or dd<bm[0]): bm=(dd,t['t'].strip())
        pr['name']=bm[1] if bm else None
    # net names
    netnames=collections.defaultdict(set)
    for t in texts:
        s=t['t'].strip()
        if not s or ((t['col']&0xFF)>=0x80 and (t['col']>>16)==0) or t['size']>8: continue
        nn=t.get('nearnet')
        if not nn or nn[0]>(24.0 if t['col']==16711680 else 3.0): continue
        if t['col']==16711680 or classify(s)=='name':
            if s in MISC: continue
            netnames[nn[1]].add(s)
    unassigned=[]
    for pr in pins:
        e=pr['inner'] or (pr['seg'][0],pr['seg'][1])
        ref=None
        if pr['body'] is not None:
            if pr['body'] in absorbed: ref=absorbed[pr['body']]
            else:
                refs=body_ref.get(pr['body'],[])
                if len(refs)==1: ref=refs[0]
                elif len(refs)>1:
                    ic=[rf for rf in refs if re.match(r'(U|ISO|J|LS|TSW|Y|Q|T)\d',rf)]
                    if (pr['name'] or (pr['num'] and pr['num'].isdigit() and int(pr['num'])>2)) and ic:
                        ref=min(ic,key=lambda rf: rect_dist((e[0],e[1],e[0],e[1]),comps[rf]['sbb']))
                    else: ref=min(refs,key=lambda rf: rect_dist((e[0],e[1],e[0],e[1]),comps[rf]['sbb']))
        if ref is None:
            cand=[(rect_dist((e[0],e[1],e[0],e[1]),bodies[bi][0]),bi) for bi in list(body_ref)+list(absorbed)]
            cand=[x for x in cand if x[0]<=25]
            if cand:
                dd,bi=min(cand)
                if bi in absorbed: ref=absorbed[bi]
                else:
                    refs=body_ref[bi]; ref=refs[0] if len(refs)==1 else min(refs,key=lambda rf: rect_dist((e[0],e[1],e[0],e[1]),comps[rf]['sbb']))
        rec=dict(num=pr['num'],name=pr['name'],net=str(pr['net']),pos=(round(pr['seg'][0]),round(pr['seg'][1])),inner=(round(e[0]),round(e[1])))
        if ref: comps[ref]['pins'].append(rec)
        else: unassigned.append(rec)
    multi={k:v for k,v in body_ref.items() if len(v)>1}
    return dict(page=i,comps=comps,netnames={str(k):sorted(v) for k,v in netnames.items()},unassigned=unassigned,nbodies=len(bodies),multi=multi)
if __name__=='__main__':
    out={}
    for i in range(10):
        b=build(i); out[i]=b
        noref=[c['ref'] for c in b['comps'].values() if c['body'] is None]
        print('page',i,'comps',len(b['comps']),'unassigned pins',len(b['unassigned']),'multi',list(b['multi'].values()),'w/o body',noref)
    json.dump(out,open('v2/netlist.json','w'),default=str)
