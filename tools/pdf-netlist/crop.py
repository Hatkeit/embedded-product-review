import pymupdf,sys
from PIL import Image
U='/root/.claude/uploads/35e36bf5-dc3c-5051-8323-16962b98011f/595576e1-sch_microinv_v2000.pdf'
d=pymupdf.open(U)
_cache={}
def crop(pg,x0,y0,x1,y1,name,dpi=300):
    if (pg,dpi) not in _cache:
        pm=d[pg].get_pixmap(dpi=dpi); _cache[(pg,dpi)]=Image.frombytes('RGB',(pm.width,pm.height),pm.samples)
    im=_cache[(pg,dpi)]; k=dpi/72
    im.crop((int(x0*k),int(y0*k),int(x1*k),int(y1*k))).save('v2/'+name+'.png')
if __name__=='__main__':
    a=sys.argv[1:]
    crop(int(a[0]),*[float(x) for x in a[1:5]],a[5],int(a[6]) if len(a)>6 else 300)
