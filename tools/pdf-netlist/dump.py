import json,re,collections,sys
nl=json.load(open('v2/netlist.json')); G=json.load(open('v2/global.json'))
# map (pg,netid) -> name
name_of={}
k=0
for nm,ms in G:
    if nm is None: k+=1; nm='N%03d'%k
    for pg,ref,num,pname,inner in ms: name_of[(str(pg),)]=None
# rebuild mapping from members: need netid; reload from netlist
import globalnet as g
uf=g.uf
lab={}
k=0
for root,grp in g.groups.items():
    nm='/'.join(sorted(grp['names'])) if grp['names'] else None
    if nm is None: k+=1; nm='N%03d'%k
    lab[root]=nm
def netname(pg,netid,ref='',num='',inner=''):
    if netid=='None': return 'nc'
    return lab.get(uf.f((pg,netid)),'?')
pages=[int(x) for x in sys.argv[1:]] or range(10)
def keyref(r):
    m=re.match(r'([A-Z]+)(\d+)([A-Z]*)',r); return (m.group(1),int(m.group(2)),m.group(3))
for pg in pages:
    b=nl[str(pg)]
    print(f'===== page {pg} ({g.PAGES[pg]})')
    for ref in sorted(b['comps'],key=keyref):
        c=b['comps'][ref]
        pins=sorted(c['pins'],key=lambda p:(int(p['num']) if p['num'] and p['num'].isdigit() else 99, p['inner']))
        ps=' | '.join(f"{p['num'] or '-'}{'('+p['name']+')' if p['name'] else ''}={netname(str(pg),p['net'])}" for p in pins)
        print(f"{ref:6s} {' '.join(c['lines'])[:40]:40s} :: {ps}")
    if b['unassigned']:
        print('  UNASSIGNED:',' | '.join(f"{p['num'] or '-'}{'('+p['name']+')' if p['name'] else ''}@{p['inner']}={netname(str(pg),p['net'])}" for p in b['unassigned']))
