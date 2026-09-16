#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
18-50 Vin / 400 Vout / 150 W CCM Flyback - 설계 검증 계산기

설계사양서(design-spec.md)에 실린 모든 수치를 재현한다.
외부 의존성 없음.  실행:  python3 calc.py
"""

import math

MU0 = 4e-7 * math.pi
RHO_CU_20 = 1.72e-8          # Ohm*m @20C
CU_TEMP_COEF = 0.00393       # 1/K


def r_cu(temp_c):
    return RHO_CU_20 * (1 + CU_TEMP_COEF * (temp_c - 20))


# ---------------------------------------------------------------- 사양
class Spec:
    vin_min, vin_nom, vin_max = 18.0, 48.0, 50.0
    vout = 400.0
    pout = 150.0
    eta = 0.90               # 목표 효율(ACF 기준) - 설계 마진용
    fsw = 100e3
    vf_diode = 1.8           # 1200 V SiC SBD @2 A
    n_ps = 8.0               # Ns/Np (승압비)
    kr = 0.40                # 저입력 전류리플비 dI/Imid
    np_turns = 9
    ns_turns = 72
    naux_turns = 4


S = Spec()
vor = (S.vout + S.vf_diode) / S.n_ps          # 반사전압 (1차 환산)
iout = S.pout / S.vout
pin = S.pout / S.eta


def duty(vin):
    return vor / (vor + vin)


# ---------------------------------------------------------------- 자화 인덕턴스
d_max = duty(S.vin_min)
iin_dc_min = pin / S.vin_min
i_mid_min = iin_dc_min / d_max
di_min = S.kr * i_mid_min
lm = S.vin_min * d_max / (di_min * S.fsw)


def leg(vin):
    """주어진 입력에서의 1차/2차 전류 지표"""
    d = duty(vin)
    iin_dc = pin / vin
    i_mid = iin_dc / d
    di = vin * d / (lm * S.fsw)
    ipk = i_mid + di / 2
    ival = i_mid - di / 2
    ccm = ival > 0
    irms_p = math.sqrt(d * (i_mid ** 2 + di ** 2 / 12))
    # 2차측(출력 기준, 손실 제외)
    is_mid = iout / (1 - d)
    dis = di / S.n_ps
    is_pk = is_mid + dis / 2
    irms_s = math.sqrt((1 - d) * (is_mid ** 2 + dis ** 2 / 12))
    icout = math.sqrt(max(irms_s ** 2 - iout ** 2, 0.0))
    icin = math.sqrt(max(irms_p ** 2 - iin_dc ** 2, 0.0))
    return dict(vin=vin, d=d, iin_dc=iin_dc, i_mid=i_mid, di=di, ipk=ipk,
                ival=ival, ccm=ccm, irms_p=irms_p, is_pk=is_pk,
                irms_s=irms_s, icout=icout, icin=icin)


CORNERS = [leg(v) for v in (S.vin_min, S.vin_nom, S.vin_max)]

# ---------------------------------------------------------------- 코어 (ETD44/22/15, N97)
class Core:
    name = "ETD44/22/15"
    ae = 173e-6        # m^2
    le = 103e-3        # m
    ve = 17.8e-6       # m^3
    aw = 214e-6        # m^2  (코어 창면적)
    bob_w = 29.0e-3    # 보빈 권선폭
    bob_h = 5.4e-3     # 보빈 권선높이
    mlt = 80e-3        # 평균 1턴 길이
    rth = 12.0         # K/W (자연대류, 실장 기준 추정)
    bsat_100c = 0.41   # T


C = Core()
al = lm / S.np_turns ** 2


def b_peak(ipk):
    return lm * ipk / (S.np_turns * C.ae)


def b_ac_amp(di):
    return lm * di / (2 * S.np_turns * C.ae)


lg_ideal = MU0 * S.np_turns ** 2 * C.ae / lm
# 프린징 보정 (McLyman): F = 1 + (lg/sqrt(Ae)) * ln(2*G/lg), G = 보빈 권선폭
fringe = 1 + (lg_ideal / math.sqrt(C.ae)) * math.log(2 * C.bob_w / lg_ideal)
lg_real = lg_ideal * fringe       # 실제로 가공해야 할 갭(자속 등가 보정)

# ---------------------------------------------------------------- 코어손 (N97 스타인메츠 근사)
# Pv[kW/m^3] = k * f[kHz]^a * B[mT]^b , @100C  -> N97 실측 앵커: 100kHz/200mT ≈ 400 kW/m^3
def pv_n97(f_hz, b_amp_t):
    b_mt = b_amp_t * 1e3
    return 400e3 * (f_hz / 100e3) ** 1.45 * (b_mt / 200.0) ** 2.5   # W/m^3


core_loss = [pv_n97(S.fsw, b_ac_amp(c["di"])) * C.ve for c in CORNERS]

# ---------------------------------------------------------------- 권선
class Wind:
    # 1차: 동박 0.2 t x 22 mm
    p_t, p_w = 0.20e-3, 22.0e-3
    p_area = p_t * p_w
    p_ins = 0.06e-3               # 절연테이프 두께/턴
    # 2차: TIW(3중절연) 도체경 0.40 mm, 외경 0.55 mm
    s_dia, s_od = 0.40e-3, 0.55e-3
    s_area = math.pi * (s_dia / 2) ** 2
    # 보조: TIW 도체경 0.30 mm, 외경 0.45 mm
    a_dia, a_od = 0.30e-3, 0.45e-3
    a_area = math.pi * (a_dia / 2) ** 2


W = Wind()
skin = math.sqrt(r_cu(100) / (math.pi * S.fsw * MU0))

r_pri_20 = RHO_CU_20 * (S.np_turns * C.mlt) / W.p_area
r_sec_20 = RHO_CU_20 * (S.ns_turns * (C.mlt + 4e-3)) / W.s_area
r_aux_20 = RHO_CU_20 * (S.naux_turns * (C.mlt + 8e-3)) / W.a_area
hot = r_cu(100) / RHO_CU_20

FR_PRI, FR_SEC = 2.0, 1.4      # 샌드위치 권선 가정 AC 저항비
worst = CORNERS[0]
p_cu_pri = worst["irms_p"] ** 2 * r_pri_20 * hot * FR_PRI
p_cu_sec = worst["irms_s"] ** 2 * r_sec_20 * hot * FR_SEC
p_cu_aux = 0.02
p_core_worst = max(core_loss)
p_xfmr = p_cu_pri + p_cu_sec + p_cu_aux + p_core_worst
dt_rise = p_xfmr * C.rth

# 권선 빌드(창 높이) 점검
sec_layers = math.ceil(S.ns_turns * W.s_od / C.bob_w)
build = (S.np_turns * (W.p_t + W.p_ins)          # 1차 동박(분할 합계)
         + sec_layers * W.s_od                    # 2차
         + 1 * W.a_od                             # 보조
         + 5 * 0.06e-3)                           # 절연 테이프 5층

# ---------------------------------------------------------------- 클램프 / 소자 스트레스
LLK = 0.30e-6                       # 누설 사양 상한
V_CLAMP_RATIO = 1.5                 # RCD 클램프 전압 / VOR
v_clamp = V_CLAMP_RATIO * vor
p_rcd = 0.5 * LLK * worst["ipk"] ** 2 * S.fsw * v_clamp / (v_clamp - vor)
r_rcd = v_clamp ** 2 / p_rcd
c_rcd = v_clamp / (0.05 * v_clamp * r_rcd * S.fsw)

vds_acf = S.vin_max + vor
vds_rcd = S.vin_max + v_clamp
vd_sec = S.vout + S.vin_max * S.n_ps

# ACF 클램프 커패시터: 공진주기 >= 3 x Toff_max
toff_max = (1 - d_max) / S.fsw
c_clamp = (3 * toff_max / (2 * math.pi)) ** 2 / LLK

# 출력/입력 커패시터
c_out_ripple = iout * d_max / (S.fsw * 4.0)       # dV = 4 V
c_in_ripple = worst["i_mid"] * d_max / (S.fsw * 1.0)   # dV = 1 V

# 전력소자 손실 개략 (ACF 기준)
RDSON_HOT = 0.015
p_fet_cond = worst["irms_p"] ** 2 * RDSON_HOT
p_diode = iout * S.vf_diode


# ---------------------------------------------------------------- 권선비 트레이드 스터디
def turns_ratio_sweep(ratios=(4, 6, 8, 10, 12)):
    """a = Ns/Np 스윕. Vds는 RCD(Vclamp = 1.5 x VOR) 기준으로 통일."""
    rows = []
    for a in ratios:
        v_or = (S.vout + S.vf_diode) / a
        d = v_or / (v_or + S.vin_min)
        vds = S.vin_max + V_CLAMP_RATIO * v_or
        vr = S.vout + S.vin_max * a
        i_mid = (pin / S.vin_min) / d
        rows.append(dict(a=a, vor=v_or, d=d, vds=vds, vr=vr, imid=i_mid,
                         vds_acf=S.vin_max + v_or))
    return rows


# ---------------------------------------------------------------- 대체 코어 타당성
def alt_core(name, ae, bob_w, bob_h, b_ocp_limit=0.32):
    """동일 Lm/Ipk에서 필요한 Np와 권선 빌드를 산출."""
    ocp = 1.25 * worst["ipk"]
    np_min = math.ceil(lm * ocp / (b_ocp_limit * ae))
    ns = int(np_min * S.n_ps)
    layers = math.ceil(ns * W.s_od / bob_w)
    bld = (np_min * (W.p_t + W.p_ins) + layers * W.s_od + W.a_od + 5 * 0.06e-3)
    return dict(name=name, np=np_min, ns=ns, layers=layers,
                build=bld, bob_h=bob_h, fill=bld / bob_h)


# ---------------------------------------------------------------- 출력
def main():
    ln = lambda *a: print(*a)
    ln("=" * 74)
    ln(" 18-50 Vin / 400 V / 150 W  CCM 플라이백 - 설계 검증")
    ln("=" * 74)
    ln(f"  Iout                 = {iout*1e3:8.1f} mA")
    ln(f"  Pin (eta={S.eta:.2f})       = {pin:8.1f} W")
    ln(f"  권선비 Ns/Np         = {S.n_ps:8.1f}  ({S.np_turns}T : {S.ns_turns}T : {S.naux_turns}T)")
    ln(f"  반사전압 VOR         = {vor:8.1f} V")
    ln(f"  Dmax @{S.vin_min:.0f}V           = {d_max:8.3f}")
    ln(f"  Lm (Kr={S.kr:.2f})           = {lm*1e6:8.2f} uH")
    ln(f"  AL                   = {al*1e9:8.0f} nH/T^2")
    ln(f"  스위칭 주파수        = {S.fsw/1e3:8.0f} kHz")
    ln("")
    ln("-- 입력 코너별 전류 " + "-" * 54)
    hdr = ("Vin", "D", "Iin,dc", "Imid", "dI", "Ipk", "Ivly", "Ip,rms",
           "Is,pk", "Is,rms", "Cin,rms", "Cout,rms", "CCM")
    ln(("{:>5}" + "{:>8}" * 11 + "{:>5}").format(*hdr))
    for c in CORNERS:
        ln(("{vin:5.0f}{d:8.3f}{iin_dc:8.2f}{i_mid:8.2f}{di:8.2f}{ipk:8.2f}"
            "{ival:8.2f}{irms_p:8.2f}{is_pk:8.2f}{irms_s:8.3f}{icin:8.2f}"
            "{icout:8.3f}").format(**c) + ("{:>5}".format("O" if c["ccm"] else "DCM")))
    ln("")
    ln("-- 자기설계 (" + C.name + ", N97) " + "-" * 40)
    for c in CORNERS:
        ln(f"  Vin={c['vin']:3.0f}V : Bpk = {b_peak(c['ipk']):.3f} T, "
           f"Bac(amp) = {b_ac_amp(c['di'])*1e3:5.1f} mT, "
           f"Pcore = {pv_n97(S.fsw, b_ac_amp(c['di']))*C.ve:5.2f} W")
    ocp = 1.25 * worst["ipk"]
    ln(f"  OCP {ocp:.1f} A 시 Bpk    = {b_peak(ocp):.3f} T  (Bsat@100C = {C.bsat_100c} T, "
       f"마진 {100*(1-b_peak(ocp)/C.bsat_100c):.0f} %)")
    ln(f"  이상 갭 lg           = {lg_ideal*1e3:8.3f} mm")
    ln(f"  프린징계수 F         = {fringe:8.3f}")
    ln(f"  가공 갭 (센터레그)   = {lg_real*1e3:8.3f} mm  -> 사양 {round(lg_real*1e3,2):.2f} mm")
    ln("")
    ln("-- 권선/손실 " + "-" * 61)
    ln(f"  표피두께 @100kHz,100C= {skin*1e3:8.3f} mm")
    ln(f"  1차 동박 {W.p_t*1e3:.2f}t x {W.p_w*1e3:.0f}mm = {W.p_area*1e6:.2f} mm^2, "
       f"J = {worst['irms_p']/(W.p_area*1e6):.2f} A/mm^2")
    ln(f"  2차 TIW phi{W.s_dia*1e3:.2f}      = {W.s_area*1e6:.3f} mm^2, "
       f"J = {worst['irms_s']/(W.s_area*1e6):.2f} A/mm^2")
    ln(f"  DCR@20C  1차/2차/보조= {r_pri_20*1e3:.2f} mOhm / {r_sec_20:.3f} Ohm / "
       f"{r_aux_20*1e3:.1f} mOhm")
    ln(f"  동손(100C) 1차/2차   = {p_cu_pri:.2f} W / {p_cu_sec:.2f} W")
    ln(f"  코어손(최악)         = {p_core_worst:.2f} W")
    ln(f"  트랜스 총손실        = {p_xfmr:.2f} W -> dT = {dt_rise:.0f} K (Rth={C.rth} K/W)")
    ln(f"  2차 층수             = {sec_layers} 층 ({math.ceil(S.ns_turns/sec_layers)} T/층)")
    ln(f"  권선 빌드            = {build*1e3:.2f} mm / 보빈창 {C.bob_h*1e3:.1f} mm "
       f"(점유율 {100*build/C.bob_h:.0f} %)")
    ln("")
    ln("-- 소자 스트레스 / 스너버 " + "-" * 48)
    ln(f"  Vds,max (ACF, 스파이크 없음) = {vds_acf:6.1f} V -> 150 V MOSFET "
       f"({100*vds_acf/150:.0f} % 사용)")
    ln(f"  Vds,max (RCD, Vc=1.5*VOR)    = {vds_rcd:6.1f} V + 링잉 -> 200 V MOSFET "
       f"({100*vds_rcd/200:.0f} % 사용)")
    ln(f"  2차 다이오드 VR              = {vd_sec:6.1f} V -> 1200 V SiC "
       f"({100*vd_sec/1200:.0f} % 사용)")
    ln(f"  RCD 클램프 손실(Llk={LLK*1e6:.2f}uH)  = {p_rcd:6.2f} W  "
       f"(= Pout의 {100*p_rcd/S.pout:.1f} %)")
    ln(f"    -> R = {r_rcd:.0f} Ohm / {math.ceil(p_rcd*2)} W, C = {c_rcd*1e6:.2f} uF / 100 V")
    ln(f"  ACF 클램프 커패시터 Cc >=    = {c_clamp*1e6:6.2f} uF  "
       f"(Tres >= 3 x Toff,max = {3*toff_max*1e6:.1f} us)")
    ln(f"  Cout (dV=4V)                 = {c_out_ripple*1e6:6.2f} uF -> 4.7 uF/630 V 필름")
    ln(f"  Cin  (dV=1V @18V)            = {c_in_ripple*1e6:6.1f} uF, "
       f"리플 {worst['icin']:.2f} Arms")
    ln(f"  MOSFET 도통손(Rds={RDSON_HOT*1e3:.0f}mOhm) = {p_fet_cond:6.2f} W")
    ln(f"  2차 다이오드 손실            = {p_diode:6.2f} W")
    ln("")
    ln("-- 권선비 a=Ns/Np 트레이드 스터디 (Vds는 RCD, Vclamp=1.5xVOR 기준) " + "-" * 8)
    ln("{:>4}{:>9}{:>9}{:>11}{:>11}{:>11}{:>9}".format(
        "a", "VOR[V]", "Dmax", "Vds,RCD", "Vds,ACF", "Vd,sec[V]", "Imid[A]"))
    for r in turns_ratio_sweep():
        ln("{a:4d}{vor:9.1f}{d:9.3f}{vds:11.1f}{vds_acf:11.1f}{vr:11.0f}{imid:9.2f}".format(**r))
    ln("")
    ln("-- 대체 코어 타당성 (Bpk@OCP <= 0.32 T 조건) " + "-" * 29)
    ln("{:>12}{:>6}{:>6}{:>8}{:>12}{:>9}".format(
        "core", "Np", "Ns", "2차층수", "빌드[mm]", "점유율"))
    for c in (alt_core("ETD44", 173e-6, 29.0e-3, 5.4e-3),
              alt_core("ETD39", 125e-6, 25.5e-3, 5.9e-3),
              alt_core("ETD49", 211e-6, 33.0e-3, 6.7e-3)):
        ln("{name:>12}{np:6d}{ns:6d}{layers:8d}{build:12.2f}{fill:9.0%}".format(
            **{**c, "build": c["build"] * 1e3}))
    ln("")
    ln("-- 설계 검증 판정 " + "-" * 56)
    checks = [
        ("Dmax <= 0.78", d_max <= 0.78, f"{d_max:.3f}"),
        ("전 범위 CCM 유지", all(c["ccm"] for c in CORNERS),
         "Ivalley>0"),
        ("Bpk(정상) <= 0.30 T", b_peak(worst["ipk"]) <= 0.30,
         f"{b_peak(worst['ipk']):.3f} T"),
        ("Bpk(OCP) <= 0.35 T", b_peak(ocp) <= 0.35, f"{b_peak(ocp):.3f} T"),
        ("Vds(ACF) <= 150V*0.8", vds_acf <= 150 * 0.8, f"{vds_acf:.0f} V"),
        ("Vd,sec <= 1200V*0.8", vd_sec <= 1200 * 0.8, f"{vd_sec:.0f} V"),
        ("권선 빌드 <= 보빈창 85%", build <= C.bob_h * 0.85,
         f"{100*build/C.bob_h:.0f} %"),
        ("트랜스 온도상승 <= 40 K", dt_rise <= 40, f"{dt_rise:.0f} K"),
        ("1차 전류밀도 <= 6 A/mm^2",
         worst["irms_p"] / (W.p_area * 1e6) <= 6.0,
         f"{worst['irms_p']/(W.p_area*1e6):.2f} A/mm^2"),
        ("2차 도체경 <= 2 x 표피두께", W.s_dia <= 2 * skin,
         f"{W.s_dia*1e3:.2f} vs {2*skin*1e3:.2f} mm"),
    ]
    for name, ok, val in checks:
        ln(f"  [{'PASS' if ok else 'FAIL'}] {name:28s} : {val}")
    ln("")
    ln(f"  [참고] RCD 방식 클램프 손실 {p_rcd:.1f} W -> 단독으로 효율 "
       f"{100*p_rcd/pin:.1f} %p 손실. ACF 채택 근거.")
    ln("=" * 74)


if __name__ == "__main__":
    main()
