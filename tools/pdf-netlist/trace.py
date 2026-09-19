import sys,math,collections; sys.path.insert(0,'v2')
from extract import extract,seg_pt_dist
def build_adj(r):
    segs=r['segs']; junc=r['junc']; TOL=1.2
    adj=collections.defaultdict(set)
    def link(a,b,why): adj[a].add((b,why)); adj[b].add((a,why))
    for k,(t,s) in enumerate(segs):
        for e in ((s[0],s[1]),(s[2],s[3])):
            for m,(t2,s2) in enumerate(segs):
                if m==k: continue
                tol=TOL if (t=='w' and t2=='w') else (1.5 if (t=='b' and t2=='b') else 2.0)
                if t=='w' and t2=='w':
                    if min(math.hypot(e[0]-s2[0],e[1]-s2[1]),math.hypot(e[0]-s2[2],e[1]-s2[3]))<=tol: link(k,m,'ee')
                else:
                    if seg_pt_dist(s2,e)<=tol: link(k,m,'sym')
    bl=[(k,s) for k,(t,s) in enumerate(segs) if t=='b' and abs(s[1]-s[3])<0.3 and abs(s[0]-s[2])>=3.0]
    for a in range(len(bl)):
        ka,sa=bl[a]; cxa=(sa[0]+sa[2])/2
        for b in range(a+1,len(bl)):
            kb,sb=bl[b]; cxb=(sb[0]+sb[2])/2
            if abs(cxa-cxb)<=1.0 and abs(sa[1]-sb[1])<=2.6: link(ka,kb,'bar')
    for jp in junc:
        ks=[k for k,(t,s) in enumerate(segs) if seg_pt_dist(s,jp)<=2.0]
        for k in ks[1:]: link(ks[0],k,'junc@%s'%(tuple(round(x) for x in jp),))
    return adj
def path(r,adj,A,B):
    segs=r['segs']
    prev={A:None}; q=collections.deque([A])
    while q:
        x=q.popleft()
        if x==B: break
        for y,why in adj[x]:
            if y not in prev: prev[y]=(x,why); q.append(y)
    out=[]; x=B
    while x is not None and prev.get(x):
        px,why=prev[x]; out.append((x,segs[x][0],tuple(round(v,1) for v in segs[x][1]),why)); x=px
    return list(reversed(out))
if __name__=='__main__':
    pg=int(sys.argv[1]); r=extract(pg); adj=build_adj(r); segs=r['segs']
    def find(seg):
        for k,(t,s) in enumerate(segs):
            if tuple(round(x,1) for x in s)==seg: return k
    A=find(tuple(float(x) for x in sys.argv[2:6])); B=find(tuple(float(x) for x in sys.argv[6:10]))
    print(A,B)
    for p in path(r,adj,A,B): print(p)
