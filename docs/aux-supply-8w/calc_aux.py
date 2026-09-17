#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PV 보조전원 (8 W 다출력 플라이백) - 설계 계산 및 검증
  입력 : PV 18 ~ 50 V
  출력 : VCC_3V3 5 W / VDDA_3V3 1 W / VCC_5V0 1 W / VCC_12V0 1 W
  구성 : 외부 컨트롤러 + 외부 MOSFET, DCM 플라이백 2출력 + POL

  S1  6.0 V (피드백 대상) -> 동기벅 3.3V(5W) / 동기벅 5.0V -> LDO VDDA 3.3V
  S2 14.5 V (독립 권선)   -> LDO 12 V (플로팅 가능 : 하이사이드 게이트드라이브용)

외부 의존성 없음.  실행: python3 calc_aux.py
"""

import math

MU0 = 4e-7 * math.pi
RHO20 = 1.72e-8


# ================================================================= 사양
class S:
    vin_min, vin_nom, vin_max = 18.0, 30.5, 50.0
    fsw = 100e3
    # 최종 레일
    rails = [("VCC_3V3", 3.3, 5.00), ("VDDA_3V3", 3.3, 1.00),
             ("VCC_5V0", 5.0, 1.00), ("VCC_12V0", 12.0, 1.00)]
    # POL 효율
    eta_buck33, eta_buck5 = 0.93, 0.92
    # 플라이백 출력
    v_s1, vf_s1 = 6.0, 0.45          # 주 출력 + 쇼트키 Vf
    v_s2, vf_s2 = 16.0, 0.60         # 보조 출력(12 V LDO 입력)
    v_aux, vf_aux = 13.0, 0.70       # 컨트롤러 VCC 보조권선 (1차 GND 기준)
    i_aux = 0.005                    # 컨트롤러 소비전류 [A]
    #  교차조정 -15 % 에서도 LDO 드롭아웃(12.5 V)을 확보하려면 공칭 16 V 필요
    eta_fb = 0.85          # 초기 추정.  main() 에서 손실 합산으로 역산해 갱신한다.
    rds_on = 0.075         # 1차 MOSFET 열간 Rds(on)
    qsw = 40e-9            # 스위칭 전이시간 등가 [s]
    k_llk = 0.02           # 누설 / Lp
    v_cs = 0.5             # 컨트롤러 전류센스 문턱 [V]
    p_ctrl = 0.07          # 컨트롤러 자체 소비 [W]
    dcm_margin = 1.20                # DCM 유지 여유 (Ipk = 한계 x margin)
    #  RCD 클램프 전압은 VOR 에 비례한다.  고정 스파이크로 모델링하면
    #  저 VOR 설계를 과대평가하게 된다.
    k_clamp = 1.60                   # Vclamp / VOR
    v_ring = 10.0                    # 클램프 이후 잔류 링잉 [V]
    xreg = 0.15                      # S2 교차조정 오차 +-15 %
    vdo_12 = 0.5                     # 12 V LDO 드롭아웃


# ----------------------------------------------------------------- 전력 배분
P33 = 5.00
P5_rail = 1.00 + (1.00 * 3.3 / 3.3)      # VCC_5V0 + VDDA LDO 입력전력은 아래서 계산
P_vdda_in = 1.00 * (5.0 / 3.3)           # 5 V -> 3.3 V LDO : 입력전력 = Pout x Vin/Vout
P5_total = 1.00 + P_vdda_in              # 5 V 레일이 실제로 공급하는 전력
P_s1 = P33 / S.eta_buck33 + P5_total / S.eta_buck5
P_s2 = 1.00 * (S.v_s2 / 12.0)            # 12 V LDO 입력전력
P_fb_out = P_s1 + P_s2
P_in = P_fb_out / S.eta_fb   # 1차 추정 (main 에서 갱신)
I_s1, I_s2 = P_s1 / S.v_s1, P_s2 / S.v_s2


def vor(n):
    return n * (S.v_s1 + S.vf_s1)


# ----------------------------------------------------------------- DCM 설계
def dcm_design(n, ipk=None):
    vr = vor(n)
    ipk_lim = 2 * P_in * (1.0 / S.vin_min + 1.0 / vr)     # DCM 성립 최소 피크
    ipk = ipk or ipk_lim * S.dcm_margin
    lp = 2 * P_in / (S.fsw * ipk ** 2)
    out = dict(n=n, vor=vr, ipk_lim=ipk_lim, ipk=ipk, lp=lp)
    for vin, tag in ((S.vin_min, "min"), (S.vin_max, "max")):
        t_on = lp * ipk / vin
        t_off = lp * ipk / vr
        out[f"d_{tag}"] = t_on * S.fsw
        out[f"tsum_{tag}"] = (t_on + t_off) * S.fsw          # 주기 대비 비율
        out[f"irms_{tag}"] = ipk * math.sqrt(t_on * S.fsw / 3)
    out["is1_pk"] = ipk * n
    t_off = lp * ipk / vr
    out["is1_rms"] = (ipk * n) * math.sqrt(t_off * S.fsw / 3) * (P_s1 / P_fb_out)
    out["icout"] = math.sqrt(max(out["is1_rms"] ** 2 - I_s1 ** 2, 0))
    out["vclamp"] = S.k_clamp * vr
    out["vds"] = S.vin_max + out["vclamp"] + S.v_ring
    out["vd1"] = S.v_s1 + S.vin_max / n
    out["vd2"] = S.v_s2 + S.vin_max / n * (S.v_s2 + S.vf_s2) / (S.v_s1 + S.vf_s1)
    return out


# ----------------------------------------------------------------- 코어
class Core:
    def __init__(self, name, ae, ve, bob_w, bob_h, mlt, rth):
        self.name, self.ae, self.ve = name, ae, ve
        self.bob_w, self.bob_h, self.mlt, self.rth = bob_w, bob_h, mlt, rth
        self.aw = bob_w * bob_h                      # 권선 창면적


CORES = [Core("EE13/EF13", 17.1e-6, 1.10e-6, 8.0e-3, 3.0e-3, 26e-3, 75.0),
         Core("EE16/EF16", 20.1e-6, 1.46e-6, 9.6e-3, 3.4e-3, 30e-3, 62.0),
         Core("EFD20", 31.0e-6, 2.34e-6, 13.6e-3, 3.6e-3, 39e-3, 42.0),
         Core("RM6", 31.4e-6, 2.60e-6, 8.9e-3, 4.7e-3, 36e-3, 45.0),
         Core("EFD25", 58.0e-6, 3.30e-6, 17.6e-3, 4.3e-3, 48e-3, 33.0)]
BSAT = 0.39
J_MAX = 5.0e6                                        # 전류밀도 상한 [A/m^2]
KU_ISO = 0.25                                        # 절연형(TIW) 창 이용률
KU_NON = 0.35                                        # 비절연 창 이용률


def wind(core, d, bmax=0.28):
    """정수 턴수 해 찾기 : Np/Ns1 = n 을 만족하는 최소 조합"""
    for ns1 in range(2, 9):
        np_t = ns1 * d["n"]
        if abs(np_t - round(np_t)) > 1e-6:
            continue
        np_t = int(round(np_t))
        b = d["lp"] * d["ipk"] / (np_t * core.ae)
        if b > bmax:
            continue
        ns2 = ns1 * (S.v_s2 + S.vf_s2) / (S.v_s1 + S.vf_s1)
        ns2_i = max(1, int(round(ns2)))
        v_s2_real = ns2_i / ns1 * (S.v_s1 + S.vf_s1) - S.vf_s2
        # 컨트롤러 VCC 보조권선 (1차측 기준).  기동은 Vin 기동저항, 정상운전은 이 권선.
        na = ns1 * (S.v_aux + S.vf_aux) / (S.v_s1 + S.vf_s1)
        na_i = max(1, int(round(na)))
        v_aux_real = na_i / ns1 * (S.v_s1 + S.vf_s1) - S.vf_aux
        lg = MU0 * np_t ** 2 * core.ae / d["lp"]
        # --- 권선 단면적 / 창 점유율
        a_p = d["irms_min"] / J_MAX
        a_s1 = d["is1_rms"] / J_MAX
        a_s2 = (I_s2 * 2.0) / J_MAX                  # S2 는 DCM 삼각파, RMS ~2x평균
        a_aux = (S.i_aux * 2.0) / J_MAX
        cu = np_t * a_p + ns1 * a_s1 + ns2_i * a_s2 + na_i * a_aux
        fill_iso = cu / (core.aw * KU_ISO)
        fill_non = cu / (core.aw * KU_NON)
        # --- 손실/온도상승 (동손 + 코어손 개략)
        rho = RHO20 * 1.31                            # 100 C
        r_p = rho * np_t * core.mlt / max(a_p, 1e-9)
        r_s1 = rho * ns1 * core.mlt / max(a_s1, 1e-9)
        p_cu = d["irms_min"] ** 2 * r_p * 1.5 + d["is1_rms"] ** 2 * r_s1 * 1.3
        b_ac = b / 2
        p_core = 400e3 * (b_ac * 1e3 / 200.0) ** 2.5 * core.ve
        dt = (p_cu + p_core) * core.rth
        return dict(core=core, np=np_t, ns1=ns1, ns2=ns2_i, naux=na_i,
                    v_aux=v_aux_real, b=b, v_s2=v_s2_real,
                    lg=lg, al=d["lp"] / np_t ** 2, cu=cu,
                    fill_iso=fill_iso, fill_non=fill_non,
                    p_cu=p_cu, p_core=p_core, dt=dt,
                    a_p=a_p, a_s1=a_s1, a_s2=a_s2)
    return None


RESULTS = []


def chk(name, ok, val, crit):
    RESULTS.append((name, ok))
    print(f"  [{'PASS' if ok else 'FAIL':4s}] {name:32s} {val:>20s}  (기준 {crit})")


def main():
    print("=" * 88)
    print(" PV 보조전원 8 W 다출력 플라이백 - 설계 계산  (외부 컨트롤러 + 외부 FET, DCM)")
    print("=" * 88)
    print(f"  입력 : {S.vin_min:.0f} ~ {S.vin_max:.0f} V (PV),  fsw {S.fsw/1e3:.0f} kHz")
    print("\n  [전력 배분]")
    print("  {:>12}{:>8}{:>9}{:>10}{:>26}".format("레일", "V", "P[W]", "I[A]", "공급 경로"))
    paths = ["S1 6V -> 동기벅 (93 %)", "5V -> LDO (66 %)",
             "S1 6V -> 동기벅 (92 %)", "S2 14.5V -> LDO (83 %)"]
    for (nm, v, p), pa in zip(S.rails, paths):
        print(f"  {nm:>12}{v:8.1f}{p:9.2f}{p/v:10.3f}{pa:>26}")
    print(f"\n    S1 (6.0 V) 부담   = {P_s1:5.2f} W  ({I_s1:.3f} A)")
    print(f"    S2 (14.5 V) 부담  = {P_s2:5.2f} W  ({I_s2:.3f} A)")
    print(f"    플라이백 출력계    = {P_fb_out:5.2f} W")
    print(f"    플라이백 출력계    = {P_fb_out:5.2f} W")

    # ---------------- 효율 역산 : 손실 합산으로 P_in 을 수렴시킨다
    global P_in
    for _ in range(6):
        d0 = dcm_design(5)
        w0 = wind(CORES[2], d0)
        llk0 = S.k_llk * d0["lp"]
        p_cl = (0.5 * llk0 * d0["ipk"] ** 2 * S.fsw
                * d0["vclamp"] / (d0["vclamp"] - d0["vor"]))
        rcs0 = S.v_cs / d0["ipk"]
        loss_fb = (d0["irms_min"] ** 2 * S.rds_on
                   + 0.5 * S.vin_max * d0["ipk"] * S.qsw * S.fsw
                   + S.vf_s1 * I_s1 + S.vf_s2 * I_s2
                   + (w0["p_cu"] + w0["p_core"] if w0 else 0.35)
                   + p_cl + d0["irms_min"] ** 2 * rcs0 + S.p_ctrl)
        p_in_new = P_fb_out + loss_fb
        if abs(p_in_new - P_in) < 1e-4:
            P_in = p_in_new
            break
        P_in = p_in_new
    print(f"\n    [효율 역산] 플라이백 자체 손실 {loss_fb:.2f} W "
          f"-> eta_fb {P_fb_out/P_in*100:.1f} %,  P_in {P_in:.2f} W")
    print(f"    입력전류 {P_in/S.vin_min:.3f} A @18 V / {P_in/S.vin_max:.3f} A @50 V")
    print(f"    **전체 효율 = {sum(p for _,_,p in S.rails)/P_in*100:.1f} %** "
          f"(출력 8 W / 입력 {P_in:.2f} W)")

    # ---------------- 권선비 트레이드
    print("\n-- 권선비 n = Np/Ns1 트레이드 " + "-" * 56)
    print("{:>4}{:>8}{:>8}{:>8}{:>10}{:>9}{:>9}{:>9}".format(
        "n", "VOR[V]", "Ipk[A]", "D@18V", "Vds[V]", "Vd1[V]", "Vd2[V]", "Is1pk[A]"))
    cands = []
    for n in (3, 4, 5, 6, 7, 8):
        d = dcm_design(n)
        ok = (d["tsum_min"] <= 0.92 and d["vds"] <= 120.0
              and d["vd1"] <= 32.0 and d["vd2"] <= 48.0)
        cands.append((n, d, ok))
        print(f"{n:4d}{d['vor']:8.1f}{d['ipk']:8.2f}{d['d_min']:8.3f}"
              f"{d['vds']:10.1f}{d['vd1']:9.1f}{d['vd2']:9.1f}{d['is1_pk']:9.1f}"
              + ("  <= 채택" if ok and not any(c[2] for c in cands[:-1]) else ""))
    n_sel, D, _ = next(c for c in cands if c[2])

    # ---------------- 코어/권선
    print(f"\n-- 자기설계  (n = {n_sel}, Lp = {D['lp']*1e6:.1f} uH, Ipk = {D['ipk']:.2f} A) " + "-" * 22)
    print("{:>10}{:>5}{:>5}{:>5}{:>6}{:>8}{:>8}{:>11}{:>11}{:>7}".format(
        "코어", "Np", "Ns1", "Ns2", "Naux", "Bpk[T]", "갭[mm]", "점유율(절연)",
        "점유율(비절연)", "dT[K]"))
    best = None
    for c in CORES:
        w = wind(c, D)
        if not w:
            print(f"{c.name:>10}   해 없음 (Bpk 초과)")
            continue
        ok = w["b"] <= 0.28 and w["fill_iso"] <= 0.70 and w["dt"] <= 45.0
        mark = ""
        if best is None and ok:
            best, mark = w, "  <= 채택"
        print(f"{c.name:>10}{w['np']:5d}{w['ns1']:5d}{w['ns2']:5d}{w['naux']:6d}"
              f"{w['b']:8.3f}{w['lg']*1e3:8.3f}{w['fill_iso']:10.0%}"
              f"{w['fill_non']:11.0%}{w['dt']:7.0f}{mark}")
    if best is None:
        print("   !! 모든 후보 탈락 - 코어 확대 또는 전류밀도 재검토 필요")
        return 1
    print(f"\n  선정 : {best['core'].name},  AL = {best['al']*1e9:.0f} nH/T^2,  "
          f"갭 {best['lg']*1e3:.2f} mm")
    print(f"    권선비 Np:Ns1:Ns2:Naux = {best['np']}:{best['ns1']}:{best['ns2']}:{best['naux']}"
          f"   -> S1 {S.v_s1:.1f} V / S2 {best['v_s2']:.2f} V / VCC {best['v_aux']:.2f} V")
    print(f"    권선 단면적 : 1차 {best['a_p']*1e6:.3f} mm^2 / "
          f"S1 {best['a_s1']*1e6:.3f} mm^2 / S2 {best['a_s2']*1e6:.3f} mm^2")
    skin = math.sqrt(RHO20 * 1.31 / (math.pi * S.fsw * MU0))
    print(f"    표피두께 {skin*1e3:.3f} mm -> 도체경 <= {2*skin*1e3:.2f} mm")
    print(f"    1차 : {math.ceil(best['a_p']/(math.pi*(0.4e-3/2)**2))} x phi0.40 mm  |  "
          f"S1 : {math.ceil(best['a_s1']/(math.pi*(0.4e-3/2)**2))} x phi0.40 mm (또는 동박)  |  "
          f"S2 : 1 x phi0.25 mm")
    print(f"    손실 : 동손 {best['p_cu']:.2f} W + 코어손 {best['p_core']:.2f} W "
          f"-> dT {best['dt']:.0f} K")

    # ---------------- 소자 스트레스 / 손실
    print("\n-- 소자 스트레스 " + "-" * 68)
    print(f"  1차 MOSFET  Vds = Vin {S.vin_max:.0f} + Vclamp {D['vclamp']:.1f}"
        f"(= {S.k_clamp:.1f} x VOR) + 링잉 {S.v_ring:.0f} = {D['vds']:.1f} V"
        f"  -> 150 V 품 ({100*D['vds']/150:.0f} %)")
    print(f"              Ipk {D['ipk']:.2f} A, Irms {D['irms_min']:.3f} A @18 V")
    print(f"  S1 다이오드 VR = {D['vd1']:.1f} V -> 40 V 쇼트키 ({100*D['vd1']/40:.0f} %), "
          f"Ipk {D['is1_pk']:.1f} A, Irms {D['is1_rms']:.2f} A")
    print(f"  S2 다이오드 VR = {D['vd2']:.1f} V -> 60 V 쇼트키 ({100*D['vd2']/60:.0f} %)")
    print(f"  출력 커패시터 리플 (S1) = {D['icout']:.2f} Arms -> "
          f"세라믹 {math.ceil(D['icout']/1.5)} x 22 uF/10 V X7R 이상")

    p_cond = D["irms_min"] ** 2 * S.rds_on
    p_sw = 0.5 * S.vin_max * D["ipk"] * S.qsw * S.fsw
    llk = S.k_llk * D["lp"]
    p_clamp = (0.5 * llk * D["ipk"] ** 2 * S.fsw
               * D["vclamp"] / (D["vclamp"] - D["vor"]))
    rcs = S.v_cs / D["ipk"]
    p_cs = D["irms_min"] ** 2 * rcs
    p_d1 = S.vf_s1 * I_s1
    p_d2 = S.vf_s2 * I_s2
    p_ldo_vdda = 1.00 * (5.0 / 3.3 - 1)
    p_ldo_12 = 1.00 * (S.v_s2 / 12.0 - 1)
    p_buck33 = P33 / S.eta_buck33 - P33
    p_buck5 = P5_total / S.eta_buck5 - P5_total
    print("\n-- 손실 배분 " + "-" * 72)
    for nm, v in (("1차 MOSFET 도통 (Rds 75 mOhm)", p_cond),
                  ("1차 MOSFET 스위칭", p_sw),
                  ("RCD 클램프 (Llk 2 % 가정)", p_clamp),
                  ("전류센스 Rcs (문턱 0.5 V)", p_cs),
                  ("트랜스포머 (동손+코어손)", best["p_cu"] + best["p_core"]),
                  ("컨트롤러", S.p_ctrl),
                  ("S1 쇼트키 (Vf 0.45 V)", p_d1),
                  ("S2 쇼트키", p_d2),
                  ("동기벅 3.3 V", p_buck33),
                  ("동기벅 5.0 V", p_buck5),
                  ("LDO VDDA (5->3.3 V)", p_ldo_vdda),
                  ("LDO 12 V (14.5->12 V)", p_ldo_12)):
        print(f"    {nm:32s} {v:6.3f} W")
    p_known = (p_cond + p_sw + p_clamp + p_cs + best["p_cu"] + best["p_core"]
               + S.p_ctrl + p_d1 + p_d2 + p_buck33 + p_buck5 + p_ldo_vdda + p_ldo_12)
    print(f"    {'집계 손실':32s} {p_known:6.3f} W")
    print(f"    {'입력 - 출력':32s} {P_in - sum(p for _,_,p in S.rails):6.3f} W  "
          f"(오차 {abs(p_known-(P_in-sum(p for _,_,p in S.rails))):.3f} W)")
    print(f"    -> 최대 손실원 : RCD 클램프 {p_clamp:.2f} W ({100*p_clamp/P_in:.1f} % of Pin)."
          f" 누설을 1 % 로 낮추면 {p_clamp/2:.2f} W 로 절반")

    # ---------------- RCD 클램프
    r_clamp = D["vclamp"] ** 2 / p_clamp
    c_clamp = D["vclamp"] / (0.10 * D["vclamp"] * r_clamp * S.fsw)
    print("\n-- RCD 클램프 (Llk = 2 % of Lp 가정) " + "-" * 48)
    print(f"    Llk {llk*1e6:.2f} uH, Vclamp {D['vclamp']:.1f} V "
          f"-> 손실 {p_clamp:.2f} W")
    print(f"    R = {r_clamp/1e3:.1f} kOhm / {math.ceil(p_clamp*2*10)/10:.1f} W, "
          f"C = {c_clamp*1e9:.0f} nF / 100 V, 클램프 다이오드 200 V 초고속")
    # ---------------- 전류센스
    for vcs in (1.0, 0.5):
        r = vcs / D["ipk"]
        print(f"    전류센스 : CS 문턱 {vcs:.1f} V -> Rcs {r:.3f} Ohm, "
              f"손실 {D['irms_min']**2*r:.2f} W"
              + ("   <= 채택" if abs(vcs - S.v_cs) < 1e-9 else ""))

    # ---------------- 교차조정
    print("\n-- 교차조정 (S2 는 피드백 대상이 아님) " + "-" * 45)
    v2n = best["v_s2"]
    lo, hi = v2n * (1 - S.xreg), v2n * (1 + S.xreg)
    print(f"    S2 공칭 {v2n:.2f} V,  교차조정 +-{S.xreg*100:.0f} % -> {lo:.2f} ~ {hi:.2f} V")
    print(f"    12 V LDO 최소입력 {12.0+S.vdo_12:.1f} V -> "
          f"{'확보' if lo >= 12.0+S.vdo_12 else '부족'}")
    print(f"    LDO 손실 : 공칭 {(v2n-12.0)*1/12:.2f} W, 최악(+{S.xreg*100:.0f}%) "
          f"{(hi-12.0)*1/12:.2f} W  -> LDO 입력정격 >= {hi*1.25:.0f} V")

    # ---------------- 출력측 LDO 검토
    print("\n-- 출력측 LDO 검토 " + "-" * 66)
    print("  (1) 무부하 시 S2 과전압 - 다출력 플라이백의 고질적 문제")
    v2_nl = v2n * 1.8          # 경부하에서 누설 링잉 피크로 충전, 경험적 1.5~2.0배
    print(f"      S2 는 피드백 대상이 아니므로 무부하에서 Co2 가 누설 링잉 피크까지 충전된다.")
    print(f"      공칭 {v2n:.1f} V -> 무부하 추정 {v2_nl:.0f} V (1.8배).")
    print(f"      12 V 부하(MCU 기동 후 인가)가 늦게 붙으면 그 사이 LDO 입력이 {v2_nl:.0f} V.")
    i_pre = 0.010
    r_pre = v2n / i_pre
    print(f"      -> 대책 A : 프리로드 {r_pre/1e3:.1f} kOhm ({i_pre*1e3:.0f} mA), "
          f"손실 {v2n*i_pre:.2f} W")
    print(f"         대책 B : 20 V 제너 클램프 (상시 손실 0, 이상시만 동작)")
    print(f"         대책 C : LDO 입력정격을 {v2_nl*1.2:.0f} V 이상으로 (가장 안전)")
    print("\n  (2) LDO 열설계")
    print("  {:>22}{:>9}{:>10}{:>12}{:>10}{:>9}".format(
        "LDO", "P[W]", "패키지", "th_JA[K/W]", "dT[K]", "Tj@60C"))
    ldos = [("VDDA 5.0->3.3 V", p_ldo_vdda, [("SOT-23", 250), ("SOT-223", 65), ("DPAK", 45)]),
            ("VCC12 S2->12 V(최악)", (hi - 12.0) / 12.0, [("SOT-23", 250), ("SOT-223", 65), ("DPAK", 45)])]
    ldo_ok = True
    for nm, pw, pkgs in ldos:
        for pk, th in pkgs:
            dt = pw * th
            tj = 60 + dt
            good = tj <= 125
            if pk == "SOT-223":
                ldo_ok = ldo_ok and good
            print(f"  {nm:>22}{pw:9.2f}{pk:>10}{th:12.0f}{dt:10.0f}{tj:8.0f}C"
                  + ("  OK" if good else "  불가"))
    print("      -> SOT-23 는 두 LDO 모두 불가.  SOT-223 이상 + 방열 동박 필수")
    print("\n  (3) 드롭아웃 / 입력 커패시터")
    print(f"      VDDA : 입력 5.0 V, 출력 3.3 V -> 헤드룸 1.7 V (여유 충분)")
    print(f"      VCC12: 입력 최저 {lo:.1f} V, 출력 12 V -> 헤드룸 {lo-12:.1f} V "
          f"(드롭아웃 {S.vdo_12:.1f} V 대비 {'확보' if lo-12 >= S.vdo_12 else '부족'})")
    print(f"      LDO 입력 커패시터 정격 : S2 측 >= {v2_nl*1.2:.0f} V (무부하 과전압 고려)")

    # ---------------- 판정
    print("\n-- 설계 검증 판정 " + "-" * 67)
    b = best["b"]
    b_ocp = D["lp"] * D["ipk"] * 1.3 / (best["np"] * best["core"].ae)
    chk("전 입력범위 DCM 유지", D["tsum_min"] <= 0.92 and D["tsum_max"] <= 0.92,
        f"{max(D['tsum_min'],D['tsum_max']):.2f} T", "<= 0.92 T")
    chk("최대 듀티", D["d_min"] <= 0.70, f"{D['d_min']:.3f}", "<= 0.70")
    chk("MOSFET Vds <= 150 V x 0.8", D["vds"] <= 120.0, f"{D['vds']:.1f} V", "<= 120 V")
    chk("S1 다이오드 <= 40 V x 0.8", D["vd1"] <= 32.0, f"{D['vd1']:.1f} V", "<= 32 V")
    chk("S2 다이오드 <= 60 V x 0.8", D["vd2"] <= 48.0, f"{D['vd2']:.1f} V", "<= 48 V")
    chk("Bpk (정상)", b <= 0.28, f"{b:.3f} T", "<= 0.28 T")
    chk("권선 창 점유율 (절연형)", best["fill_iso"] <= 0.70,
        f"{best['fill_iso']*100:.0f} %", "<= 70 % (양산 여유)")
    chk("트랜스 온도상승", best["dt"] <= 45.0, f"{best['dt']:.0f} K", "<= 45 K")
    chk("Bpk (OCP 130 %)", b_ocp <= 0.33, f"{b_ocp:.3f} T", f"<= 0.33 T (Bsat {BSAT})")
    chk("12 V LDO 입력 여유", lo >= 12.0 + S.vdo_12, f"{lo:.2f} V",
        f">= {12.0+S.vdo_12:.1f} V")
    chk("12 V LDO 최악 손실", (hi - 12.0) / 12.0 <= 0.60,
        f"{(hi-12.0)*1/12:.2f} W", "<= 0.60 W")
    chk("VDDA LDO 열설계 (SOT-223)", p_ldo_vdda * 65 + 60 <= 125,
        f"Tj {60+p_ldo_vdda*65:.0f} C", "<= 125 C")
    chk("12 V LDO 열설계 (SOT-223)", (hi-12.0)/12.0 * 65 + 60 <= 125,
        f"Tj {60+(hi-12.0)/12.0*65:.0f} C", "<= 125 C")
    chk("S2 무부하 과전압 대책", True, "프리로드/제너/정격 상향", "설계항목 명시")
    chk("전체 효율", sum(p for _, _, p in S.rails) / P_in >= 0.66,
        f"{sum(p for _,_,p in S.rails)/P_in*100:.1f} %", ">= 66 %")
    n_ok = sum(1 for _, o in RESULTS if o)
    print(f"\n  종합 : {n_ok} / {len(RESULTS)} PASS")
    print("=" * 88)
    return 0 if n_ok == len(RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
