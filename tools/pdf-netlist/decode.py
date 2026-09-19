import pymupdf,re,json
U='/root/.claude/uploads/35e36bf5-dc3c-5051-8323-16962b98011f/595576e1-sch_microinv_v2000.pdf'
d=pymupdf.open(U)
encmap={}  # font xref -> {code: char}
def font_map(xref):
    if xref in encmap: return encmap[xref]
    m={}
    if 'Type3' in d.xref_get_key(xref,'Subtype')[1]:
        e=d.xref_get_key(xref,'Encoding')
        obj=d.xref_object(int(e[1].split()[0])) if e[0]=='xref' else e[1]
        diff=re.search(r'/Differences\s*\[(.*?)\]',obj,re.S).group(1)
        toks=diff.split(); code=None
        for t in toks:
            if t.startswith('/'):
                gid=int(t[2:]); m[code]=chr(gid+29); code+=1
            else: code=int(t)
    encmap[xref]=m; return m
def page_texts(i):
    p=d[i]
    fx={}
    for f in p.get_fonts(full=True):
        fx[f[3]]=f[0]   # basefont name -> xref? f[3] is name used in page resources? use f[4]? 
    # build map from font 'name' as reported in spans: spans report s['font'] like 'Type3 (213 0 R)'
    out=[]
    items=[]
    for b in p.get_text('rawdict')['blocks']:
        for l in b.get('lines',[]):
            dirv=l['dir']
            for s in l['spans']:
                fn=s['font']; mm=re.search(r'\((\d+) 0 R\)',fn)
                txt=''
                if mm:
                    m=font_map(int(mm.group(1)))
                    for ch in s['chars']:
                        c=ord(ch['c']); txt+=m.get(c,'?')
                else:
                    txt=''.join(ch['c'] for ch in s['chars'])
                items.append([txt,list(s['bbox']),s['color'],round(s['size'],1),dirv])
    # merge items with same direction, aligned, small gap
    def proj(bb,dx,dy):
        cs=[bb[0]*dx+bb[1]*dy, bb[2]*dx+bb[1]*dy, bb[0]*dx+bb[3]*dy, bb[2]*dx+bb[3]*dy]
        return min(cs),max(cs)
    def perp(bb,dx,dy):
        cs=[-bb[0]*dy+bb[1]*dx, -bb[2]*dy+bb[1]*dx, -bb[0]*dy+bb[3]*dx, -bb[2]*dy+bb[3]*dx]
        return (min(cs)+max(cs))/2
    items.sort(key=lambda it: (it[4], proj(it[1],*it[4])[0]))
    merged=[]
    for it in items:
        done=False
        for pr in merged:
            if pr[4]!=it[4] or it[2]!=pr[2] or abs(it[3]-pr[3])>0.2: continue
            dx,dy=it[4]
            if abs(perp(it[1],dx,dy)-perp(pr[1],dx,dy))>1.5: continue
            gap=proj(it[1],dx,dy)[0]-proj(pr[1],dx,dy)[1]
            if -1.0<=gap<2.6:
                pr[0]+=it[0]; pr[1]=[min(pr[1][0],it[1][0]),min(pr[1][1],it[1][1]),max(pr[1][2],it[1][2]),max(pr[1][3],it[1][3])]; done=True; break
        if not done: merged.append(it)
    for txt,bb,col,size,dirv in merged:
        x0,y0,x1,y1=bb
        out.append(dict(t=txt,x0=round(x0,1),y0=round(y0,1),x1=round(x1,1),y1=round(y1,1),col=col,size=size,dir=dirv))
    return out
if __name__=='__main__':
    allt={i:page_texts(i) for i in range(len(d))}
    json.dump(allt,open('v2/texts.json','w'))
    for i in allt: print(i,len(allt[i]))
    for s in allt[0][:60]: print(s)
