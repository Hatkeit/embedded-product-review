import math
def sim(Lp,Vin,Cs,Ls,Ipk_ref,Rc,Cc,Llk=0.16e-6,a=7.5,Vo=342.0,f=100e3,Vf=1.5,Coss=1e-9,cycles=260,dt=0.5e-9):
    T=1/f; VOR=(Vo+Vf)/a; n_per=int(round(T/dt)); Lm=Lp; Se=VOR/Lm; D0=VOR/(VOR+Vin)
    ip=im=0.0; vD=Vin; vCs=0.0; iLs=0.0; on=False; vCc=60.0
    m=None
    for k in range(cycles*n_per):
        if k%n_per==0:
            on=True; t0=k
            if k//n_per>=cycles-5 and m is None: m=dict(vds=0,pr=0.0,n=0,vcc_max=0,vcc_min=1e9,vcs=0)
        if on and ip>=Ipk_ref+Se*(D0*T-(k-t0)*dt) and (k-t0)*dt>200e-9: on=False
        vCc-=vCc/(Rc*Cc)*dt
        if on:
            vD=0.0
            if im>ip+1e-9:
                ip+=(Vin+VOR)/Llk*dt; im-=VOR/Lm*dt
                if ip>im: ip=im
            else: ip+=Vin/(Llk+Lm)*dt; im=ip
            vX=-vCs
            if iLs>0 or vX<0:
                if vX>=Vin-1e-6 and iLs>0: vCs=-Vin; iLs-=Vin/Ls*dt
                else: iLs+=vCs/Ls*dt; vCs-=max(iLs,0)/Cs*dt
                if iLs<=0: iLs=0.0
        else:
            sec=(im>ip+1e-9) or (Lm/(Lm+Llk)*(Vin-vD)<-VOR and im>0)
            if sec:
                ip+=(Vin+VOR-vD)/Llk*dt; im-=VOR/Lm*dt
                if im<0: im=0.0
            else: ip+=(Vin-vD)/(Llk+Lm)*dt; im=ip
            vX=vD-vCs
            d1=vX>=Vin-1e-6 and (ip*Cs/(Cs+Coss)+iLs)>0
            dc=(vD-Vin)>=vCc-1e-6 and ip>0
            if d1:
                Ct=Cs+Coss+(Cc if dc else 0.0)
                dv=ip/Ct*dt; vD+=dv; vCs=vD-Vin
                if dc: vCc=vD-Vin
                if iLs>0: iLs=max(0.0,iLs-Vin/Ls*dt)
            else:
                Ct=Coss+(Cc if dc else 0.0)
                vD+=(ip+iLs)/Ct*dt
                if dc: vCc=vD-Vin
                vCs-=iLs/Cs*dt; vX=vD-vCs
                if iLs>0 or vX<0: iLs=max(0.0,iLs-vX/Ls*dt)
            if vD<0: vD=0.0
        if m is not None:
            m['n']+=1; m['vds']=max(m['vds'],vD); m['pr']+=vCc*vCc/Rc*dt
            m['vcc_max']=max(m['vcc_max'],vCc); m['vcc_min']=min(m['vcc_min'],vCc); m['vcs']=max(m['vcs'],vCs)
    tt=m['n']*dt
    return m['vds'],m['pr']/tt,m['vcc_min'],m['vcc_max'],m['vcs']
def ipk(Lp,Vin,P=250,eta=0.93,a=7.5,f=100e3):
    VOR=343.5/a; D=VOR/(VOR+Vin); return P/eta/(Vin*D)+Vin*D/f/Lp/2
Cs=82.5e-9; Ls=10e-6
print("Lp12, Cs82.5n, Ls10u  (RCD 없음 Vds: 30V 107.0 / 37.6V 113.8 / 50V 126.0)")
for Rc in (2.2e3,3.3e3,4.7e3,6.8e3,10e3):
    row=[]
    for Vin in (30.0,37.6,50.0):
        v,p,c0,c1,vc=sim(12e-6,Vin,Cs,Ls,ipk(12e-6,Vin),Rc,100e-9)
        row.append(f"Vin{Vin:4.1f}: Vds={v:6.1f} Vcc={c0:4.1f}~{c1:4.1f} P_R={p:4.2f}W")
    print(f"Rc={Rc/1e3:4.1f}k | "+" | ".join(row))
