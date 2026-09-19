import json,re,collections,sys
nl=json.load(open('v2/netlist.json'))
PAGES={0:'01 PV_A DCDC',1:'02 PV_B DCDC',2:'03 GRID',3:'04 PWR',4:'05 MCU',5:'06 ESP32/TPM',6:'07 ADC',7:'08 GRID_ProtA',8:'09 GRID_ProtB(ADC)',9:'10 NTC'}
# union across pages by name
class UF:
    def __init__(s): s.p={}
    def f(s,x):
        s.p.setdefault(x,x)
        while s.p[x]!=x: s.p[x]=s.p[s.p[x]]; x=s.p[x]
        return x
    def u(s,a,b):
        ra,rb=s.f(a),s.f(b)
        if ra!=rb: s.p[ra]=rb
uf=UF(); names=collections.defaultdict(set)
members=collections.defaultdict(list)
for pg,b in nl.items():
    for net,ns in b['netnames'].items():
        key=(pg,net); uf.u(key,key)
        for n in ns:
            uf.u(key,('N',n)); names[('N',n)].add(n)
    for ref,c in b['comps'].items():
        for p in c['pins']:
            key=(pg,p['net']) if p['net']!='None' else (pg,'NC_%s_%s_%s'%(ref,p['num'],p['inner'])); uf.u(key,key)
            members[key].append((pg,ref,p['num'],p['name'],p['inner']))
    for p in b['unassigned']:
        key=(pg,p['net']); uf.u(key,key); members[key].append((pg,'?',p['num'],p['name'],p['inner']))
groups=collections.defaultdict(lambda: dict(names=set(),members=[]))
for key,ms in members.items():
    g=groups[uf.f(key)]; g['members'].extend(ms)
for key,ns in names.items():
    groups[uf.f(key)]['names'].update(ns)
# also nets with names but no members
out=[]
for root,g in groups.items():
    nm='/'.join(sorted(g['names'])) if g['names'] else None
    out.append((nm,g['members']))
out.sort(key=lambda x:(x[0] is None, x[0] or ''))
json.dump([(nm,ms) for nm,ms in out],open('v2/global.json','w'))
if __name__=='__main__':
    k=0
    for nm,ms in out:
        if nm is None: k+=1; nm='N%03d'%k
        mem=sorted(set((int(pg),ref,num or '',name or '') for pg,ref,num,name,inner in ms))
        print(f"{nm} [{len(mem)}]: "+', '.join(f"p{pg}:{ref}.{num}{('('+name+')') if name else ''}" for pg,ref,num,name in mem))
