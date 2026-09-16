#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PV 250 W 언폴딩 마이크로인버터 - 설계 계산 및 검증

구조 : PV 1장 -> 2상 인터리브 플라이백(180도) -> 공유 언폴딩 브리지 -> 계통 220 V/60 Hz
핵심 : 플라이백 출력은 상수 400 V 가 아니라 0~Vpk 의 정류정현파이며,
       평균 250 W 에 대해 순시 피크는 500 W (p(t) = 2P sin^2(wt)) 이다.

외부 의존성 없음.  실행: python3 calc_mi.py
"""

import math

MU0 = 4e-7 * math.pi
RHO20 = 1.72e-8
CU_TC = 0.00393


def rcu(tc):
    return RHO20 * (1 + CU_TC * (tc - 20))


# ================================================================= 사양
class Spec:
    # --- 계통 (한국)
    vg_rms, f_line = 220.0, 60.0
    vg_tol_hi = 1.10                      # 계통 상한 +10 %
    # --- PV (250 W급 60셀 모듈)
    voc, isc, vmp, imp, ncell = 37.6, 8.80, 30.5, 8.20, 60
    beta_voc, gamma_p = -0.0032, -0.0040  # /degC
    # --- 변환기
    p_ac = 250.0                          # 평균 AC 출력
    nph = 2                               # 인터리브 상수
    fsw = 100e3
    eta = 0.93
    vf_sec = 1.8                          # 1200 V SiC SBD
    a_turns = 6.0                         # Ns/Np
    np_t, ns_t, naux_t = 10, 60, 4
    lm = 23.0e-6                          # 상당 자화 인덕턴스
    kr = 0.60                             # 정현파 피크에서의 전류리플비
    ocp = 23.0                            # 상당 사이클바이사이클 OCP


S = Spec()
W_LINE = 2 * math.pi * S.f_line
VPK = S.vg_rms * math.sqrt(2)
VPK_HI = S.vg_rms * S.vg_tol_hi * math.sqrt(2)
P_INST_PK = 2 * S.p_ac                    # 순시 피크 전력 (전체)
P_PH_PK = P_INST_PK / S.nph               # 상당 순시 피크


def vor(v_out):
    return (v_out + S.vf_sec) / S.a_turns


# ================================================================= 라인주기 동작점
def op_point(theta, vin, p_ac=None, vpk=None):
    """라인 위상 theta 에서 1개 상(phase)의 스위칭주기 동작량."""
    p_ac = S.p_ac if p_ac is None else p_ac
    vpk = VPK if vpk is None else vpk
    s = abs(math.sin(theta))
    v_o = vpk * s
    p_ph = (2 * p_ac / S.nph) * s * s            # 상당 순시 출력전력
    if p_ph < 1e-6 or v_o < 1.0:
        return dict(theta=theta, v_o=v_o, p=0.0, d=0.0, ipk=0.0, ival=0.0,
                    irms=0.0, isec_rms=0.0, mode="OFF", vor=vor(v_o))
    vr = vor(v_o)
    p_in = p_ph / S.eta
    iin = p_in / vin
    d_ccm = vr / (vr + vin)
    imid = iin / d_ccm
    di = vin * d_ccm / (S.lm * S.fsw)
    ipk, ival = imid + di / 2, imid - di / 2
    if ival > 0:                                  # --- CCM
        irms = math.sqrt(d_ccm * (imid ** 2 + di ** 2 / 12))
        is_mid = (p_ph / v_o) / (1 - d_ccm)
        dis = di / S.a_turns
        isec_rms = math.sqrt((1 - d_ccm) * (is_mid ** 2 + dis ** 2 / 12))
        return dict(theta=theta, v_o=v_o, p=p_ph, d=d_ccm, ipk=ipk, ival=ival,
                    irms=irms, isec_rms=isec_rms, mode="CCM", vor=vr)
    # --- DCM : 주기당 전달에너지 = p_in/fsw = 0.5*Lm*Ipk^2
    ipk = math.sqrt(2 * p_in / (S.lm * S.fsw))
    t_on = S.lm * ipk / vin
    t_off = S.lm * ipk / vr
    d = t_on * S.fsw
    if t_on + t_off > 1.0 / S.fsw:                # DCM 불가 -> BCM 한계 초과
        mode = "OVER"
    else:
        mode = "DCM"
    irms = ipk * math.sqrt(d / 3.0)
    isec_rms = (ipk / S.a_turns) * math.sqrt(t_off * S.fsw / 3.0)
    return dict(theta=theta, v_o=v_o, p=p_ph, d=d, ipk=ipk, ival=0.0,
                irms=irms, isec_rms=isec_rms, mode=mode, vor=vr)


def line_scan(vin, n=721, p_ac=None, vpk=None):
    return [op_point(math.pi * k / (n - 1), vin, p_ac, vpk) for k in range(n)]


def line_rms(pts, key):
    return math.sqrt(sum(p[key] ** 2 for p in pts) / len(pts))


# ================================================================= 코어
class Core:
    def __init__(self, name, ae, le, ve, bob_w, bob_h, mlt, rth):
        self.name, self.ae, self.le, self.ve = name, ae, le, ve
        self.bob_w, self.bob_h, self.mlt, self.rth = bob_w, bob_h, mlt, rth


CORES = [
    Core("ETD34", 97.1e-6, 78.6e-3, 7.64e-6, 21.0e-3, 5.0e-3, 60e-3, 19.0),
    Core("ETD39", 125e-6, 92.2e-3, 11.5e-6, 25.5e-3, 5.9e-3, 69e-3, 15.0),
    Core("ETD44", 173e-6, 103e-3, 17.8e-6, 29.0e-3, 5.4e-3, 80e-3, 12.0),
    Core("PQ32/30", 161e-6, 74.7e-3, 12.0e-6, 17.5e-3, 6.4e-3, 67e-3, 16.0),
]
BSAT_100 = 0.41


class Wind:
    p_t, p_w, p_ins = 0.20e-3, 0.0, 0.06e-3       # 1차 동박 (폭은 코어별)
    s_dia, s_od = 0.32e-3, 0.47e-3                # 2차 TIW
    s_par = 2                                     # 2차 병렬 가닥수
    a_dia, a_od = 0.25e-3, 0.40e-3                # 보조 TIW


W = Wind()
SKIN = math.sqrt(rcu(100) / (math.pi * S.fsw * MU0))


def core_fit(core, np_t, ns_t, ipk_ocp):
    b_ocp = S.lm * ipk_ocp / (np_t * core.ae)
    p_w = core.bob_w - 7.0e-3                      # 양단 기계 마진 3.5 mm
    layers = math.ceil(ns_t * W.s_par * W.s_od / core.bob_w)
    build = (np_t * (W.p_t + W.p_ins) + layers * W.s_od + W.a_od + 5 * 0.06e-3)
    return dict(core=core, np=np_t, ns=ns_t, b_ocp=b_ocp, p_w=p_w,
                layers=layers, build=build, fill=build / core.bob_h)


# ================================================================= 2w 전력 디커플링
def decoupling():
    e_swing = S.p_ac / W_LINE                      # [J] 반주기 저장/방출 에너지
    rows = []
    for dv_pp_pct in (5.0, 10.0, 20.0):
        dv_pp = S.vmp * dv_pp_pct / 100
        c = e_swing / (S.vmp * dv_pp)
        # MPPT 이용률 : P(V) 를 MPP 근처 2차근사, 리플 평균 손실
        # d2P/dV2 ~ -2*Pmp/ (Vmp^2 * k), 실측 근사 k=0.28 (60셀 결정질)
        k = 0.28
        util = 1.0 - ((dv_pp / 2) / S.vmp) ** 2 / (2 * k)
        rows.append((dv_pp_pct, dv_pp, c, util))
    # 능동 디커플링 : 필름 커패시터를 넓은 전압범위로 스윙
    act = []
    for v_lo, v_hi in ((150.0, 250.0), (200.0, 400.0), (250.0, 450.0)):
        c = 2 * e_swing / (v_hi ** 2 - v_lo ** 2)
        act.append((v_lo, v_hi, c))
    i_rip = S.p_ac / (math.sqrt(2) * S.vmp)        # 디커플링 커패시터 120 Hz 리플전류
    # 능동 디커플링 변환기가 처리하는 평균전력 : 라인주기당 2회 x e_swing
    p_proc = 2 * e_swing * S.f_line
    return e_swing, rows, act, i_rip, p_proc


def cap_life(base_h, base_t, t_core):
    return base_h * 2 ** ((base_t - t_core) / 10.0)


# ================================================================= 출력
def main():
    ln = print
    ln("=" * 86)
    ln(" PV 250 W 언폴딩 마이크로인버터 - 설계 계산  (2상 인터리브 + 공유 언폴더)")
    ln("=" * 86)
    ln(f"  계통                 : {S.vg_rms:.0f} V / {S.f_line:.0f} Hz,  "
       f"Vpk {VPK:.1f} V,  Vpk(+10%) {VPK_HI:.1f} V")
    ln(f"  PV 모듈              : Voc {S.voc} V, Isc {S.isc} A, "
       f"Vmp {S.vmp} V, Imp {S.imp} A  ({S.vmp*S.imp:.0f} W)")
    ln(f"    저온(-25 C) Voc    : {S.voc*(1-S.beta_voc*50):.1f} V "
       f"-> 입력정격 50 V {'이내 OK' if S.voc*(1+0.0032*50) <= 50 else '초과'}")
    ln(f"  평균 AC 출력         : {S.p_ac:.0f} W   ->  순시 피크 {P_INST_PK:.0f} W "
       f"(p(t) = 2P sin^2)")
    ln(f"  상당 순시 피크       : {P_PH_PK:.0f} W  ({S.nph}상 인터리브)")
    ln(f"  계통 전류            : {S.p_ac/S.vg_rms:.2f} Arms, 피크 "
       f"{S.p_ac/S.vg_rms*math.sqrt(2):.2f} A")
    ln("")

    # ---------------- 권선비 트레이드
    ln("-- 권선비 a = Ns/Np 트레이드 (정현파 피크, Vin = Vmp 30.5 V) " + "-" * 24)
    ln("{:>4}{:>11}{:>9}{:>10}{:>11}{:>12}{:>11}".format(
        "a", "VOR@Vpk+", "D@peak", "Imid[A]", "Ipk[A]", "Vds,ACF[V]", "Vd,sec[V]"))
    for a in (4, 5, 6, 7, 8, 10):
        vr_hi = (VPK_HI + S.vf_sec) / a
        vr = (VPK + S.vf_sec) / a
        d = vr / (vr + S.vmp)
        imid = (P_PH_PK / S.eta / S.vmp) / d
        ipk = imid * (1 + S.kr / 2)
        vds = 50.0 + vr_hi
        vd = VPK_HI + 50.0 * a
        mark = "  <= 채택" if a == S.a_turns else ""
        ln(f"{a:4d}{vr_hi:11.1f}{d:9.3f}{imid:10.2f}{ipk:11.2f}{vds:12.1f}{vd:11.0f}{mark}")
    ln("")

    # ---------------- 라인주기 스캔
    ln("-- 라인주기 동작 (a=6, Lm=23 uH/상, Vin=Vmp 30.5 V) " + "-" * 32)
    pts = line_scan(S.vmp)
    ln("{:>8}{:>9}{:>9}{:>8}{:>9}{:>9}{:>9}{:>7}".format(
        "위상[deg]", "Vout[V]", "Pph[W]", "D", "Ipk[A]", "Ival[A]", "Irms[A]", "모드"))
    for deg in (5, 15, 30, 45, 60, 75, 90):
        p = op_point(math.radians(deg), S.vmp)
        ln(f"{deg:8d}{p['v_o']:9.1f}{p['p']:9.1f}{p['d']:8.3f}{p['ipk']:9.2f}"
           f"{p['ival']:9.2f}{p['irms']:9.2f}{p['mode']:>7}")
    ipk_max = max(p["ipk"] for p in pts)
    irms_line = line_rms(pts, "irms")
    isec_line = line_rms(pts, "isec_rms")
    dcm_frac = sum(1 for p in pts if p["mode"] == "DCM") / len(pts)
    over = [p for p in pts if p["mode"] == "OVER"]
    ln(f"\n  상당 최대 피크전류   = {ipk_max:.2f} A   (OCP {S.ocp} A)")
    ln(f"  상당 라인주기 RMS    = 1차 {irms_line:.2f} A / 2차 {isec_line:.3f} A")
    ln(f"  DCM 구간 비율        = {dcm_frac*100:.0f} %  (영교차 부근은 자연히 DCM)")
    ln(f"  BCM 한계 초과 구간   = {len(over)} 개  {'(없음 OK)' if not over else '(재설계 필요)'}")

    # 입력전압 코너
    ln("\n  입력전압별 최대 피크전류 :")
    for vin, pac, note in ((25.0, 191.0, "70 C, Pmp 205 W"),
                           (30.5, 250.0, "STC 정격"),
                           (33.6, 250.0, "0 C, 전력리미트 250 W"),
                           (42.0, 150.0, "저일사"),
                           (50.0, 60.0, "Voc 부근")):
        pp = line_scan(vin, 361, pac)
        ln(f"    Vin {vin:4.1f} V, P_AC {pac:5.1f} W ({note:22s}) -> "
           f"Ipk {max(q['ipk'] for q in pp):5.2f} A, "
           f"Irms {line_rms(pp,'irms'):5.2f} A")
    ln("")

    # ---------------- 코어 선정
    ln("-- 코어 선정 (Bpk@OCP 기준, N97 Bsat(100C) = 0.41 T) " + "-" * 31)
    ln("{:>10}{:>7}{:>7}{:>10}{:>10}{:>11}{:>9}{:>8}".format(
        "코어", "Np", "Ns", "Bpk@Ipk", "Bpk@OCP", "포화마진", "2차층수", "점유율"))
    best = None
    for c in CORES:
        f = core_fit(c, S.np_t, S.ns_t, S.ocp)
        b_pk = S.lm * ipk_max / (S.np_t * c.ae)
        marg = 1 - f["b_ocp"] / BSAT_100
        ok = f["b_ocp"] <= 0.33 and f["fill"] <= 0.85
        ln(f"{c.name:>10}{S.np_t:7d}{S.ns_t:7d}{b_pk:10.3f}{f['b_ocp']:10.3f}"
           f"{marg*100:10.0f} %{f['layers']:9d}{f['fill']*100:7.0f} %"
           + ("  <= 채택" if ok and best is None else ""))
        if ok and best is None:
            best = (c, f, b_pk)
    core, fit, b_pk = best
    lg_ideal = MU0 * S.np_t ** 2 * core.ae / S.lm
    fr = 1 + (lg_ideal / math.sqrt(core.ae)) * math.log(2 * core.bob_w / lg_ideal)
    ln(f"\n  선정 : {core.name},  AL = {S.lm/S.np_t**2*1e9:.0f} nH/T^2,  "
       f"갭 {lg_ideal*fr*1e3:.2f} mm (프린징 F={fr:.2f})")
    ln(f"  표피두께 @100 kHz,100 C = {SKIN*1e3:.3f} mm  "
       f"-> 1차 동박 0.20 t, 2차 TIW phi{W.s_dia*1e3:.2f} x{W.s_par} (< 2delta)")

    # ---------------- 손실
    p_w = min(fit["p_w"], 22e-3)
    a_pri = W.p_t * p_w
    a_sec = W.s_par * math.pi * (W.s_dia / 2) ** 2
    r_pri = RHO20 * (S.np_t * core.mlt) / a_pri
    r_sec = RHO20 * (S.ns_t * (core.mlt + 4e-3)) / a_sec
    hot = rcu(100) / RHO20
    p_cu_p = irms_line ** 2 * r_pri * hot * 2.0
    p_cu_s = isec_line ** 2 * r_sec * hot * 1.4
    # 코어손 : 라인주기 평균 (Steinmetz, N97 100kHz/200mT/100C = 400 kW/m^3)
    pv_sum = 0.0
    for p in pts:
        if p["mode"] == "OFF":
            continue
        di = (p["ipk"] - p["ival"]) if p["mode"] == "CCM" else p["ipk"]
        b_ac = S.lm * di / (2 * S.np_t * core.ae)
        pv_sum += 400e3 * (b_ac * 1e3 / 200.0) ** 2.5
    p_core = pv_sum / len(pts) * core.ve
    p_xfmr = p_cu_p + p_cu_s + p_core
    ln(f"\n-- 상당 트랜스포머 손실 " + "-" * 60)
    ln(f"  1차 동박 0.20 x {p_w*1e3:.0f} mm = {a_pri*1e6:.2f} mm^2, "
       f"DCR {r_pri*1e3:.2f} mOhm  -> {p_cu_p:.2f} W")
    ln(f"  2차 TIW phi{W.s_dia*1e3:.2f} x{W.s_par} = {a_sec*1e6:.3f} mm^2, "
       f"DCR {r_sec:.2f} Ohm  -> {p_cu_s:.2f} W")
    ln(f"  코어손(라인주기 평균) -> {p_core:.2f} W")
    ln(f"  합계 {p_xfmr:.2f} W/상  -> dT {p_xfmr*core.rth:.0f} K  "
       f"(2상 합계 {2*p_xfmr:.2f} W)")

    # ---------------- 2w 디커플링
    e_sw, passive, active, i_rip, p_proc = decoupling()
    ln("\n" + "=" * 86)
    ln(" 2w(120 Hz) 전력 디커플링 트레이드 스터디")
    ln("=" * 86)
    ln(f"  버퍼링 필요 에너지   = P/w = {e_sw*1e3:.0f} mJ")
    ln(f"  디커플링 리플전류    = P/(sqrt2 x Vmp) = {i_rip:.2f} Arms @120 Hz")
    ln("\n  [A] 수동 : PV측 대용량 전해")
    ln("  {:>10}{:>9}{:>10}{:>11}{:>11}{:>12}".format(
        "리플(pp)", "dV[V]", "C[uF]", "용량기준", "리플기준", "MPPT이용률"))
    n_rip = math.ceil(i_rip / 2.2)                 # 1500 uF/50 V 저ESR 1개당 2.2 Arms
    for pct, dv, c, util in passive:
        n_c = math.ceil(c * 1e6 / 1500)
        ln(f"  {pct:9.0f}%{dv:9.2f}{c*1e6:10.0f}{n_c:8d} 개"
           f"{n_rip:8d} 개{util*100:11.2f}%")
    ln(f"    (1500 uF/50 V 저ESR 기준, 1개당 120 Hz 리플 허용 2.2 Arms "
       f"-> 리플만으로 최소 {n_rip} 개)")
    ln("\n  [B] 능동 : 필름 커패시터 + 양방향 벅부스트")
    ln("  {:>10}{:>10}{:>12}{:>16}".format("V_lo[V]", "V_hi[V]", "C[uF]", "실장"))
    for v_lo, v_hi, c in active:
        impl = f"450 V 필름 {math.ceil(c*1e6/10)} x 10 uF"
        ln(f"  {v_lo:10.0f}{v_hi:10.0f}{c*1e6:12.1f}   {impl}")
    ln(f"    처리전력 = 2 x E x f_line = {p_proc:.1f} W")
    for eff in (0.95, 0.96, 0.97):
        ln(f"      변환효율 {eff*100:.0f} % -> 추가손실 {p_proc*(1-eff):.2f} W "
           f"(전체효율 -{100*p_proc*(1-eff)/S.p_ac:.2f} %p)")
    ln("\n  [수명] 옥외 패널 배면 주위온도별 예상 수명")
    ln("  {:>10}{:>18}{:>18}{:>16}".format("주위[C]", "전해 코어온도", "전해 수명", "필름 수명"))
    for ta in (45, 60, 75):
        tcore = ta + 12                                   # 리플 자기발열
        life_e = cap_life(5000, 105, tcore)               # 105C/5000h 장수명품
        life_f = cap_life(100000, 85, tcore - 8)          # 필름 (자기발열 작음)
        ln(f"  {ta:10d}{tcore:15d} C{life_e/8760:15.1f} 년"
           f"{min(life_f/8760, 40.0):13.0f} 년+")
    ln("")

    # ---------------- 언폴더 / 출력필터
    ig_rms = S.p_ac / S.vg_rms
    ig_pk = ig_rms * math.sqrt(2)
    ln("-- 언폴딩 브리지 및 출력 필터 " + "-" * 54)
    ln(f"  언폴더 전류          : {ig_rms:.2f} Arms / {ig_pk:.2f} A peak")
    ln(f"  언폴더 전압스트레스  : {VPK_HI:.0f} V + 계통 서지 -> 650 V 정격")
    for name, vdrop, rds in (("Si MOSFET 650 V, 0.3 Ohm", None, 0.30),
                             ("IGBT 650 V, Vce 1.5 V", 1.5, None)):
        loss = (2 * ig_rms ** 2 * rds) if rds else (2 * 2 / math.pi * ig_pk * vdrop)
        ln(f"    {name:28s} -> 도통손 {loss:.2f} W  "
           f"({'MOSFET 유리' if rds else ''})")
    ln(f"  언폴더 스위칭        : {2*S.f_line:.0f} Hz 정류(영교차) -> 스위칭손 무시 가능")
    # 출력 LC 필터 : 100 kHz 리플을 계통 규격 이하로
    lf, cf = 2.2e-3, 0.47e-6
    fc = 1 / (2 * math.pi * math.sqrt(lf * cf))
    att = (S.fsw * S.nph / fc) ** 2
    ln(f"  출력필터 Lf {lf*1e3:.1f} mH / Cf {cf*1e6:.2f} uF -> fc {fc:.0f} Hz, "
       f"인터리브 리플({S.fsw*S.nph/1e3:.0f} kHz) 감쇠 {20*math.log10(att):.0f} dB")
    ln(f"  필터 무효전류        : {2*math.pi*S.f_line*cf*S.vg_rms*1e3:.1f} mA "
       f"({100*2*math.pi*S.f_line*cf*S.vg_rms/ig_rms:.1f} % of Ig) -> 역률 영향 경미")
    ln("")

    # ---------------- 검증 판정
    ln("-- 설계 검증 판정 " + "-" * 66)
    vds_max = 50.0 + (VPK_HI + S.vf_sec) / S.a_turns
    vd_sec = VPK_HI + 50.0 * S.a_turns
    checks = [
        ("상당 Ipk <= OCP", ipk_max <= S.ocp, f"{ipk_max:.2f} A", f"<= {S.ocp} A"),
        ("Bpk(정상) <= 0.30 T", b_pk <= 0.30, f"{b_pk:.3f} T", "<= 0.30 T"),
        ("Bpk(OCP) <= 0.33 T", fit["b_ocp"] <= 0.33, f"{fit['b_ocp']:.3f} T", "<= 0.33 T"),
        ("Vds(ACF) <= 150V x 0.8", vds_max <= 120, f"{vds_max:.1f} V", "<= 120 V"),
        ("2차 다이오드 <= 1200V x 0.8", vd_sec <= 960, f"{vd_sec:.0f} V", "<= 960 V"),
        ("BCM 한계 미초과", not over, f"{len(over)} 개 초과", "0 개"),
        ("권선 빌드 <= 85 %", fit["fill"] <= 0.85, f"{fit['fill']*100:.0f} %", "<= 85 %"),
        ("상당 온도상승 <= 40 K", p_xfmr * core.rth <= 40,
         f"{p_xfmr*core.rth:.0f} K", "<= 40 K"),
        ("2차 도체경 <= 2 x 표피두께", W.s_dia <= 2 * SKIN,
         f"{W.s_dia*1e3:.2f} vs {2*SKIN*1e3:.2f} mm", "OK"),
        ("저온 Voc <= 입력정격 50 V", S.voc * (1 + 0.0032 * 50) <= 50.0,
         f"{S.voc*(1+0.0032*50):.1f} V", "<= 50 V"),
    ]
    npass = 0
    for name, ok, val, crit in checks:
        npass += ok
        ln(f"  [{'PASS' if ok else 'FAIL'}] {name:30s} : {val:>22s}  (기준 {crit})")
    ln(f"\n  종합 : {npass} / {len(checks)} PASS")
    ln("=" * 86)
    return 0 if npass == len(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
