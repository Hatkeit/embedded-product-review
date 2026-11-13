#!/usr/bin/env python3
"""V2000 플라이백 LCD 스너버 시간영역 검증 (이상 스위치·이상 다이오드, 고정 출력전압).

상태: ip(1차 전류), im(자화 전류), vD(드레인), vCs(=vD-vX), iLs
제어: 고정 주파수 피크전류 제어 + 슬로프 보상(Se = VOR/Lm, D>0.5 저조파 진동 방지).
실행: python3 lcd_snubber_sim.py
"""
import math

def analytic(Lp, Vin, Cs, Ls, Llk=0.16e-6, a=7.5, Vo=342.0, P=250.0, f=100e3, eta=0.93, Vf=1.5):
    T = 1 / f; VOR = (Vo + Vf) / a
    D = VOR / (VOR + Vin); Imid = P / eta / (Vin * D); dI = Vin * D * T / Lp
    Ipk, Iv = Imid + dI / 2, Imid - dI / 2
    Vc = VOR + Ipk * math.sqrt(Llk / Cs)
    w = 1 / math.sqrt(Ls * Cs); Ires = Vc * math.sqrt(Cs / Ls)
    t1 = (math.pi - math.acos(Vin / Vc)) / w
    t2 = Ls * Ires * math.sqrt(1 - (Vin / Vc) ** 2) / Vin
    return dict(VOR=VOR, D=D, Ipk=Ipk, Iv=Iv, Vc=Vc, Vds=Vin + Vc, Ires=Ires, t_inv=t1 + t2, t_on=D * T)

def simulate(Lp, Vin, Cs, Ls, Ipk_ref, Llk=0.16e-6, a=7.5, Vo=342.0, f=100e3, Vf=1.5,
             Coss=1e-9, cycles=30, dt=0.25e-9):
    T = 1 / f; VOR = (Vo + Vf) / a; n_per = int(round(T / dt)); Lm = Lp
    Se = VOR / Lm; D0 = VOR / (VOR + Vin)      # 보상 램프: 정상상태 턴오프 시점에서 Ipk_ref와 일치
    ip = im = 0.0; vD = Vin; vCs = 0.0; iLs = 0.0; on = False
    meas = None
    for k in range(cycles * n_per):
        ph = k % n_per
        if ph == 0:
            on = True; t_on_start = k
            if k // n_per >= cycles - 5 and meas is None:
                meas = dict(vds=0.0, vcs_max=-1e9, vcs_min=1e9, isw_on=0.0, e_out=0.0, q_d1=0.0,
                            ils2=0.0, isw2=0.0, n=0, tinv=[], ton=[], ipk=0.0)
            inv_done = False
        if on and ip >= Ipk_ref + Se * (D0 * T - (k - t_on_start) * dt) and (k - t_on_start) * dt > 200e-9:
            on = False
            if meas is not None: meas['ton'].append((k - t_on_start) * dt)
        iD1 = 0.0
        if on:
            vD = 0.0
            if im > ip + 1e-9:                     # 2차 다이오드 도통 중(턴온 직후 전류 전이)
                ip += (Vin + VOR) / Llk * dt; im -= VOR / Lm * dt
                if ip > im: ip = im
            else:
                ip += Vin / (Llk + Lm) * dt; im = ip
            vX = -vCs
            if iLs > 0 or vX < 0:
                if vX >= Vin - 1e-6 and iLs > 0:   # D1 도통: Cs는 -Vin에 고정, Ls 전류는 입력으로
                    vCs = -Vin; iD1 = iLs; iLs -= Vin / Ls * dt
                else:
                    iLs += vCs / Ls * dt; vCs -= max(iLs, 0.0) / Cs * dt
                if iLs <= 0:
                    iLs = 0.0
                    if meas is not None and not inv_done and (k - t_on_start) * dt > 100e-9:
                        meas['tinv'].append((k - t_on_start) * dt); inv_done = True
            isw = ip + (iLs if iD1 == 0.0 else 0.0)
        else:
            sec = (im > ip + 1e-9) or (Lm / (Lm + Llk) * (Vin - vD) < -VOR and im > 0)
            if sec:
                ip += (Vin + VOR - vD) / Llk * dt; im -= VOR / Lm * dt
                if im < 0: im = 0.0
            else:
                ip += (Vin - vD) / (Llk + Lm) * dt; im = ip
            vX = vD - vCs
            d1 = vX >= Vin - 1e-6 and (ip * Cs / (Cs + Coss) + iLs) > 0   # 허용오차: 부동소수 비교로 인한 D1 채터링 방지
            if d1:
                dv = ip / (Cs + Coss) * dt; vD += dv; vCs = vD - Vin
                iD1 = ip * Cs / (Cs + Coss) + iLs
                if iLs > 0: iLs = max(0.0, iLs - Vin / Ls * dt)
            else:
                vD += (ip + iLs) / Coss * dt; vCs -= iLs / Cs * dt
                vX = vD - vCs
                if iLs > 0 or vX < 0: iLs = max(0.0, iLs - vX / Ls * dt)
            if vD < 0: vD = 0.0                    # 바디 다이오드
            isw = 0.0
        if meas is not None:
            m = meas; m['n'] += 1
            m['vds'] = max(m['vds'], vD); m['vcs_max'] = max(m['vcs_max'], vCs); m['vcs_min'] = min(m['vcs_min'], vCs)
            m['ipk'] = max(m['ipk'], ip)
            if on and iLs > 0 and iD1 == 0.0: m['isw_on'] = max(m['isw_on'], isw)   # 공진 구간의 스위치 전류 최대
            if (not on) and im > ip: m['e_out'] += VOR * (im - ip) * dt
            m['q_d1'] += iD1 * dt; m['ils2'] += iLs * iLs * dt; m['isw2'] += isw * isw * dt
    tt = meas['n'] * dt
    return dict(Vds=meas['vds'], Vc=meas['vcs_max'], Vcs_min=meas['vcs_min'], Isw_on=meas['isw_on'],
                Pout=meas['e_out'] / tt, Id1=meas['q_d1'] / tt, Pret=Vin * meas['q_d1'] / tt,
                ILs_rms=math.sqrt(meas['ils2'] / tt), Isw_rms=math.sqrt(meas['isw2'] / tt),
                t_inv=sum(meas['tinv']) / max(1, len(meas['tinv'])), t_on=sum(meas['ton']) / max(1, len(meas['ton'])),
                Ipk=meas['ipk'])

if __name__ == "__main__":
    print("== Ls 스윕 (Cs = 330 nF x4 = 82.5 nF): 공진 구간 스위치 전류가 턴오프 피크를 넘으면 피크전류 비교기 조기 트립 위험")
    for Lp in (12e-6, 24e-6):
        for Vin in (30.0, 37.6):
            for Lsx in (6.8e-6, 10e-6, 15e-6, 22e-6):
                an = analytic(Lp, Vin, 82.5e-9, Lsx); r = simulate(Lp, Vin, 82.5e-9, Lsx, an['Ipk'])
                print(f"  Lp={Lp*1e6:.0f}u Vin={Vin:4.1f} Ls={Lsx*1e6:4.1f}u  Vds={r['Vds']:6.1f}  t_inv/t_on={r['t_inv']*1e6:4.2f}/{r['t_on']*1e6:4.2f}"
                      f"  Isw_bump={r['Isw_on']:5.1f}  Ipk={r['Ipk']:5.1f}  {'조기트립 위험' if r['Isw_on'] > r['Ipk'] - 1.0 else 'OK'}  ILs_rms={r['ILs_rms']:.2f}")
    Ls = 10e-6
    cases = [(Lp, Vin, n) for Lp in (12e-6, 24e-6) for Vin in (30.0, 37.6) for n in (4,)]
    cases += [(12e-6, 37.6, 3), (12e-6, 37.6, 5), (12e-6, 18.0, 4), (12e-6, 50.0, 4)]
    print("Lp  Vin  Cs      | 해석: Ipk  Vds   t_inv/t_on | 시뮬: Ipk  Pout  Vds    Vcs(min)  t_inv/t_on  Isw_on  ILs_rms Id1  Pret")
    for Lp, Vin, n in cases:
        Cs = 330e-9 / n
        an = analytic(Lp, Vin, Cs, Ls)
        ipk_ref = an['Ipk'] if Vin > 20 else 22.4          # 18 V는 전류 제한 운전
        s = simulate(Lp, Vin, Cs, Ls, ipk_ref)
        print(f"{Lp*1e6:3.0f} {Vin:5.1f} {Cs*1e9:5.1f}n(x{n}) | {an['Ipk']:5.1f} {an['Vds']:6.1f} {an['t_inv']*1e6:4.2f}/{an['t_on']*1e6:4.2f} |"
              f" {s['Ipk']:5.1f} {s['Pout']:5.0f} {s['Vds']:6.1f} {s['Vcs_min']:7.1f}   {s['t_inv']*1e6:4.2f}/{s['t_on']*1e6:4.2f}   {s['Isw_on']:5.1f}  {s['ILs_rms']:5.2f} {s['Id1']:5.2f} {s['Pret']:5.1f}")
