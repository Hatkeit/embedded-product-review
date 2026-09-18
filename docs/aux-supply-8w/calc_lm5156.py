#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LM5156H 주변회로 설계 - 시정수 · 소자값 · 루프 · 기동 검증   (PS-AUX-8W Rev.D)

  기존 보드의 NCP1031DR2(U600) 를 TI LM5156H (HTSSOP-14, 외부 MOSFET) 로 대체한다.
  전력단(Lp, Ipk, 권선비, 코어)은 calc_aux.py 결과를 그대로 가져오고,
  이 파일은 컨트롤러 핀별 주변회로를 데이터시트(SNVSBV2, 2020-09) 수치로 설계·검증한다.

  검증 항목
    1. 전류센스 Rcs / 전류제한 (문턱 100 mV +-7 %)
    2. RT (fsw 100 kHz), 최대 듀티, 공차 코너에서의 DCM 유지
    3. UVLO 분압 (기동 16 V / 정지 14 V, 5 uA 히스테리시스 전류)
    4. 소프트스타트 C_SS, VCC/BIAS, 게이트 전하, 피드백 분압, PGOOD
    5. 슬로프보상 (고정 40 mV 램프, RSL) 과 COMP 동작점
    6. Type-2 보상망 설계 + 루프 보드선도 (저항부하 / 정전력부하)
    7. 사이클 평균 기동·부하과도 시뮬레이션 (SS 램프, COMP 클램프, 전류제한 포함)

외부 의존성 없음.  실행: python3 calc_lm5156.py
"""

import io
import math
import contextlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import calc_aux as A                                   # noqa: E402

# ================================================================= 데이터시트 (SNVSBV2)
class DS:
    """LM5156H / LM51561H 데이터시트 수치.  괄호는 절 번호."""
    vbias_min, vbias_max, vbias_abs = 3.5, 60.0, 65.0   # (8.3) 내부 레귤레이터 사용 시
    vcc_reg = 6.85                                      # (8.5) VCC 레귤레이션 목표
    vcc_ext_max, vcc_abs = 16.0, 18.0                   # (8.3) 외부 VCC 권장 최대 / (8.1) abs
    vcc_uvlo_r, vcc_uvlo_hys = 2.85, 0.063              # (8.5)
    ivcc_cl = 0.035                                     # (8.5) VCC 소싱 전류제한 최소 35 mA
    i_op, i_op_max = 490e-6, 580e-6                     # (8.5) 동작전류
    v_en_r = 0.52                                       # (8.5) EN 문턱 (0.4~0.7)
    v_uvlo_r, v_uvlo_f = 1.5, 1.45                      # (8.5) UVLO 문턱 (+-5 %)
    i_uvlo = 5e-6                                       # (8.5) 히스테리시스 전류 (4~6 uA)
    i_ss = 10e-6                                        # (8.5) 소프트스타트 전류 (9~11)
    k_rt, rt_off = 2.21e10, 955.0                       # (9.3.4) RT = 2.21e10/f - 955
    fsw_tol = 0.15                                      # (8.5) 85~115 kHz @ 220 k
    d_max_min = 0.90                                    # (8.5) DMAX2 최소 (RT 220 k)
    t_on_min = 50e-9                                    # (8.5) @ RT 9.09 k (100 kHz 는 더 짧지 않음)
    v_clth, clth_tol = 0.100, 0.07                      # (8.5) 전류제한 문턱 93~107 mV
    i_slope = 30e-6                                     # (9.3.7) 램프 전류 30 uA x fRT/fSYNC
    v_slope = 0.040                                     # (9.3.7) 고정 램프 40 mV (한 주기)
    v_slope_off = 0.17                                  # (9.3.7) PWM 비교기 오프셋
    g_comp = 0.142                                      # (9.3.7) COMP -> PWM 비교기 이득
    rsl_max = 2000.0                                    # (9.3.7)
    v_ref, ref_tol = 1.000, 0.01                        # (8.5)
    gm, r_o, bw_ea = 2e-3, 10e6, 7e6                    # (8.5)(9.3.9)
    comp_hi, comp_lo = 2.5, 1.15                        # (8.5) COMP 클램프
    ovp_r, uv_f = 1.10, 0.90                            # (8.5) OVP 110 % / PGOOD UV 90 %
    pgood_deglitch = 25e-6                              # (9.3.10)
    r_pg_min = 10e3                                     # (9.3.10)
    t_start, t_shdn, t_vcc_dly = 65e-6, 35e-6, 50e-6    # (9.3.1) 내부 지연
    rf_range, cf_range = (10.0, 200.0), (100e-12, 2e-9) # (9.3.8)
    rth_ja = 44.1                                       # (8.4) HTSSOP-14 JEDEC
    tj_max = 150.0
    hiccup = "LM51561H 만 (64 사이클 -> 32768 사이클 휴지)"   # (9.3.11)


E24 = [1.0, 1.1, 1.2, 1.3, 1.5, 1.6, 1.8, 2.0, 2.2, 2.4, 2.7, 3.0,
       3.3, 3.6, 3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1]
E96 = [round(10 ** (i / 96), 2) for i in range(96)]


def e_round(x, series=E96):
    dec = 10 ** math.floor(math.log10(x))
    m = x / dec
    best = min(series + [10.0], key=lambda v: abs(math.log(v / m)))
    return best * dec


def fmt_r(r):
    return f"{r/1e6:.3g} M" if r >= 1e6 else (f"{r/1e3:.3g} k" if r >= 1e3 else f"{r:.3g} ")


def fmt_c(c):
    return f"{c*1e6:.3g} uF" if c >= 1e-6 else (f"{c*1e9:.3g} nF" if c >= 1e-9 else f"{c*1e12:.3g} pF")


RESULTS = []


def chk(name, ok, val, crit):
    RESULTS.append((name, ok))
    print(f"  [{'PASS' if ok else 'FAIL':4s}] {name:34s} {val:>22s}  (기준 {crit})")


# ================================================================= 전력단 인계
def power_stage():
    """calc_aux.main() 을 조용히 실행해 P_in 수렴값과 채택 설계를 가져온다."""
    with contextlib.redirect_stdout(io.StringIO()):
        A.main()
    D = A.dcm_design(5)
    W = A.wind(A.CORES[2], D)
    return D, W


def main():
    S = A.S
    D, W = power_stage()
    lp, ipk, vor = D["lp"], D["ipk"], D["vor"]
    p_in = A.P_in
    fsw = S.fsw
    print("=" * 92)
    print(" LM5156H 주변회로 설계  -  NCP1031DR2(U600) 대체,  PS-AUX-8W Rev.D")
    print("=" * 92)
    print(f"  전력단 (calc_aux.py) : Lp {lp*1e6:.1f} uH, Ipk {ipk:.2f} A @18 V, VOR {vor:.1f} V, "
          f"D@18V {D['d_min']:.3f}, P_in {p_in:.2f} W")
    print(f"  트랜스 : {W['core'].name}  Np:Ns1:Ns2:Naux = {W['np']}:{W['ns1']}:{W['ns2']}:{W['naux']}"
          f"  (VCC 권선 {W['v_aux']:.2f} V)")

    # ------------------------------------------------ 1. 전류센스 / 전류제한
    print("\n-- 1. 전류센스 Rcs 와 전류제한 (CS 핀, DS 9.3.8) " + "-" * 40)
    rcs_max = DS.v_clth * (1 - DS.clth_tol) / (ipk * S.cs_margin)
    rcs = S.rcs                                         # E24 33 mOhm (calc_aux.py 와 동일 값)
    assert rcs <= rcs_max, "Rcs 가 전류제한 여유 조건을 넘는다"
    i_cl_min = DS.v_clth * (1 - DS.clth_tol) / rcs
    i_cl_typ = DS.v_clth / rcs
    i_cl_max = DS.v_clth * (1 + DS.clth_tol) / rcs
    p_rcs = D["irms_min"] ** 2 * rcs
    b_cl = lp * i_cl_max / (W["np"] * W["core"].ae)
    print(f"    요구 : I_CL(min) >= Ipk x {S.cs_margin:.2f} = {ipk*S.cs_margin:.2f} A "
          f"-> Rcs <= 93 mV / {ipk*S.cs_margin:.2f} A = {rcs_max*1e3:.1f} mOhm")
    print(f"    선정 : Rcs = {rcs*1e3:.0f} mOhm, 1 %, 0.25 W (2010 또는 2512 저인덕턴스 금속판)")
    print(f"    전류제한 I_CL = {i_cl_min:.2f} / {i_cl_typ:.2f} / {i_cl_max:.2f} A (min/typ/max)  "
          f"<- RSL = 0 이면 듀티 무관 (Eq.10)")
    print(f"    Rcs 손실 {p_rcs*1e3:.0f} mW,  CS 핀 DC 최대 {i_cl_max*rcs*1e3:.0f} mV (abs 300 mV)")
    print(f"    전류제한 최대에서 Bpk = {b_cl:.3f} T  (Bsat {A.BSAT} T, 기준 <= 0.33 T)")
    # CS 필터
    rf, cf = 100.0, 470e-12
    tau_cs = rf * cf
    t_off_min = (1 - D["d_min"]) / fsw
    print(f"    CS RC 필터 : R_F {rf:.0f} Ohm, C_F {cf*1e12:.0f} pF -> tau {tau_cs*1e9:.0f} ns")
    print(f"      Eq.13 : 3 x tau = {3*tau_cs*1e6:.2f} us <= (1-D)/fsw = {t_off_min*1e6:.2f} us  "
          f"{'OK' if 3*tau_cs <= t_off_min else 'NG'}")
    print(f"      전류제한 무효 구간 : t_on < 2 x tau = {2*tau_cs*1e9:.0f} ns  "
          f"(정격 t_on {D['d_min']/fsw*1e6:.2f} us @18 V)")

    # ------------------------------------------------ 2. RT / 최대듀티 / DCM 코너
    print("\n-- 2. 스위칭 주파수 RT (DS Eq.5) 와 최대 듀티 (DS Eq.16/17) " + "-" * 28)
    rt_calc = DS.k_rt / fsw - DS.rt_off
    rt = e_round(rt_calc, E24)                           # 데이터시트 기준값 220 k (E24)
    f_rt = DS.k_rt / (rt + DS.rt_off)
    print(f"    RT = 2.21e10 / {fsw/1e3:.0f} kHz - 955 = {rt_calc/1e3:.1f} k -> {fmt_r(rt)}Ohm 1 % "
          f"-> fsw {f_rt/1e3:.1f} kHz (+-{DS.fsw_tol*100:.0f} %)")
    d_max1 = 1 - 0.1                                     # fSYNC = fRT
    d_max2 = 1 - 100e-9 * fsw
    d_max = min(d_max1, d_max2)
    print(f"    DMAX = min(1-0.1, 1-100 ns x fsw) = {d_max:.2f} (데이터시트 최소 {DS.d_max_min:.2f})")
    print(f"    설계 D@18 V = {D['d_min']:.3f}  -> 여유 {DS.d_max_min - D['d_min']:.2f}")
    # 공차 코너 : tsum ∝ sqrt(Lp x fsw) (DCM 전류모드에서 Ipk 는 전력에 맞춰 재조정)
    lp_tol = 0.05                                        # 갭 코어 AL 공차 +-5 % 로 지정
    tsum_worst = D["tsum_min"] * math.sqrt((1 + lp_tol) * (1 + DS.fsw_tol))
    print(f"    DCM 코너 : Lp +{lp_tol*100:.0f} %, fsw +{DS.fsw_tol*100:.0f} % -> "
          f"(t_on+t_off)/T = {D['tsum_min']:.2f} x sqrt({1+lp_tol:.2f} x {1+DS.fsw_tol:.2f}) = {tsum_worst:.2f} T")
    print(f"      -> Lp 공차는 +-{lp_tol*100:.0f} % 로 지정한다 (+-10 % 면 {D['tsum_min']*math.sqrt(1.10*1.15):.2f} T, 기준 초과)")
    print(f"    스펙트럼확산(DITHOFF=GND) 시 fsw 최대 +15.6 % 추가 -> DCM 여유 소진.  **DITHOFF = VCC (OFF)**")

    # ------------------------------------------------ 3. UVLO
    print("\n-- 3. 라인 UVLO 분압 (EN/UVLO/SYNC 핀, DS Eq.1/2) " + "-" * 38)
    v_on, v_off = 16.0, 14.0
    r_uvlot_calc = (v_on * DS.v_uvlo_f / DS.v_uvlo_r - v_off) / DS.i_uvlo
    r_uvlot = e_round(r_uvlot_calc)
    r_uvlob_calc = DS.v_uvlo_r * r_uvlot / (v_on - DS.v_uvlo_r)
    r_uvlob = e_round(r_uvlob_calc)
    k_div = r_uvlob / (r_uvlot + r_uvlob)
    v_on_act = DS.v_uvlo_r / k_div
    r_par = r_uvlot * r_uvlob / (r_uvlot + r_uvlob)
    v_off_act = (DS.v_uvlo_f - DS.i_uvlo * r_par) / k_div
    v_pin_max = S.vin_max * k_div + DS.i_uvlo * r_par
    c_uvlo = 10e-9
    tau_uvlo = r_par * c_uvlo
    v_en_vin = DS.v_en_r / k_div
    print(f"    목표 : 기동 {v_on:.1f} V / 정지 {v_off:.1f} V  (PV 운전 하한 18 V 아래, 채터링 방지 히스테리시스 2 V)")
    print(f"    R_UVLOT = ({v_on:.0f} x 1.45/1.5 - {v_off:.0f}) / 5 uA = {r_uvlot_calc/1e3:.0f} k -> E96 {fmt_r(r_uvlot)}Ohm")
    print(f"    R_UVLOB = 1.5 x R_UVLOT / ({v_on:.0f} - 1.5) = {r_uvlob_calc/1e3:.1f} k -> E96 {fmt_r(r_uvlob)}Ohm")
    print(f"    실제 : 기동 {v_on_act:.2f} V / 정지 {v_off_act:.2f} V (문턱 +-5 % -> 기동 {v_on_act*0.95:.1f}~{v_on_act*1.05:.1f} V)")
    print(f"    셧다운(EN 0.52 V) : Vin < {v_en_vin:.1f} V -> BIAS 전류 2.6 uA")
    print(f"    핀 전압 @50 V = {v_pin_max:.2f} V (abs V_BIAS+0.3),  분압 전류 @50 V {S.vin_max/(r_uvlot+r_uvlob)*1e6:.0f} uA")
    print(f"    C_UVLO {fmt_c(c_uvlo)} -> tau = R_T||R_B x C = {tau_uvlo*1e6:.0f} us  (기동 딥/부하과도 시 채터링 필터)")
    # 정지 전압에서 전력단 상태
    d_off = D["d_min"] * S.vin_min / v_off_act
    tsum_off = d_off + D["tsum_min"] - D["d_min"]
    print(f"    정지 직전 {v_off_act:.1f} V 전부하 : D = {d_off:.2f} (DMAX {DS.d_max_min:.2f}), "
          f"(t_on+t_off)/T = {tsum_off:.2f} -> {'DCM' if tsum_off <= 1 else 'CCM 경계'} (운전범위 밖, 과도 구간)")

    # ------------------------------------------------ 4. SS / VCC / BIAS / FB / PGOOD
    print("\n-- 4. 소프트스타트 · VCC/BIAS · 피드백 · PGOOD " + "-" * 44)
    t_ss = 10e-3
    c_ss = DS.i_ss * t_ss / DS.v_ref
    c_ss = e_round(c_ss, E24)
    t_ss_act = c_ss * DS.v_ref / DS.i_ss
    #  S1 출력 커패시터 : 세라믹 22 uF x3 (X7R, 6 V DC 바이어스로 60 %) + POL 입력 커패시터 ~20 uF
    #  + 폴리머 100 uF/10 V (부하스텝 언더슈트 억제용, Rev.D 추가).  ESR 30 mOhm -> 영점 53 kHz (fc 밖)
    c_out = 66e-6 * 0.6 + 20e-6 + 100e-6
    i_chg = c_out * S.v_s1 / t_ss_act
    print(f"    C_SS = 10 uA x {t_ss*1e3:.0f} ms / 1.0 V = {fmt_c(DS.i_ss*t_ss/DS.v_ref)} -> {fmt_c(c_ss)} "
          f"-> t_SS {t_ss_act*1e3:.1f} ms (9~11 uA : {c_ss*DS.v_ref/11e-6*1e3:.1f}~{c_ss*DS.v_ref/9e-6*1e3:.1f} ms)")
    print(f"    출력 충전전류 C_out {c_out*1e6:.0f} uF x 6 V / {t_ss_act*1e3:.0f} ms = {i_chg*1e3:.0f} mA "
          f"(<< I_s1 {A.I_s1:.2f} A -> 기동 중 전류제한 미도달)")
    print(f"    기동 순서 : BIAS -> 내부 VCC 6.85 V -> UVLO > 1.5 V -> 65 us -> SS 램프 {t_ss_act*1e3:.0f} ms "
          f"-> PGOOD (FB > 0.9 V, 25 us 디글리치)")
    # VCC
    v_aux = W["v_aux"]
    v_aux_nl = v_aux * 1.8
    q_g = 40e-9
    i_gate = q_g * fsw
    i_vcc = DS.i_op_max + i_gate
    p_ic_int = S.vin_max * i_vcc
    p_ic_ext = v_aux * i_vcc + S.vin_max * 0.05e-3
    print(f"    VCC : Naux {W['naux']} T -> {v_aux:.1f} V (> 6.85 V 외부급전 조건), 무부하 x1.8 = {v_aux_nl:.1f} V "
          f"(<= 16 V 권장, abs 18 V) {'OK' if v_aux_nl <= DS.vcc_ext_max else 'NG -> 제너 필요'}")
    print(f"    게이트 전하 Eq.18 : Qg {q_g*1e9:.0f} nC x {fsw/1e3:.0f} kHz = {i_gate*1e3:.1f} mA <= 35 mA")
    print(f"    IC 손실 : 내부 레귤레이터(기동/Naux 부족) @50 V = {p_ic_int:.3f} W -> dTj {p_ic_int*DS.rth_ja:.0f} K ; "
          f"외부 VCC 정상운전 = {p_ic_ext:.3f} W -> dTj {p_ic_ext*DS.rth_ja:.0f} K")
    r_bias, c_bias, c_vcc = 10.0, 1e-6, 2.2e-6
    print(f"    BIAS : R_BIAS {r_bias:.0f} Ohm + C_BIAS {fmt_c(c_bias)} (tau {r_bias*c_bias*1e6:.0f} us), "
          f"C_VCC {fmt_c(c_vcc)} (권장 1~4.7 uF), 강하 {r_bias*i_vcc*1e3:.1f} mV")
    print(f"    BIAS 범위 : PV {S.vin_min:.0f}~{S.vin_max:.0f} V  (동작 3.5~60 V, abs 65 V)  -> 여유 {DS.vbias_max-S.vin_max:.0f} V")
    # FB
    r_fbb = 10e3
    r_fbt = e_round(r_fbb * (S.v_s1 / DS.v_ref - 1))
    v_s1_set = DS.v_ref * (1 + r_fbt / r_fbb)
    print(f"    FB : R_FBT {fmt_r(r_fbt)}/ R_FBB {fmt_r(r_fbb)}(1 %) -> S1 {v_s1_set:.3f} V "
          f"(VREF +-1 %, 저항 1 % -> +-{(0.01+2*0.01*r_fbt/(r_fbt+r_fbb))*100:.1f} %)")
    print(f"      OVP {DS.ovp_r*100:.0f} % -> {v_s1_set*DS.ovp_r:.2f} V 에서 스위칭 정지,  PGOOD UV {DS.uv_f*100:.0f} % -> {v_s1_set*DS.uv_f:.2f} V")
    r_pg = 24.9e3
    print(f"    PGOOD : R_PG {fmt_r(r_pg)}Ohm -> VCC_3V3 (>= 10 k, PGOOD <= V_BIAS+0.3 V).  MCU nPGOOD 입력")

    # ------------------------------------------------ 5. 슬로프보상 / COMP 동작점
    print("\n-- 5. 슬로프보상 (DS 9.3.7) 과 COMP 동작점 " + "-" * 48)
    m2 = vor / lp                                        # 1차 환산 하강 기울기 [A/s]
    s_need = 0.5 * m2 * rcs * 1.2                        # Eq.8 (여유 1.2)
    s_fixed = DS.v_slope * fsw
    rsl_82 = (0.82 * m2 * rcs - s_fixed) / (DS.i_slope * fsw)
    print(f"    1차 환산 하강 기울기 m2 = VOR/Lp = {m2/1e6:.2f} A/us -> x Rcs = {m2*rcs/1e3:.1f} mV/us")
    print(f"    CCM 이라면 필요 램프 (Eq.8, x1.2) {s_need/1e3:.1f} mV/us,  고정 램프 40 mV x fsw = {s_fixed/1e3:.1f} mV/us")
    print(f"    82 % 보상용 RSL (Eq.9) = {rsl_82/1e3:.1f} kOhm > 최대 2 kOhm -> **CCM 에서는 보상 불가**")
    print(f"    => 본 설계는 전 운전범위 DCM (0.83 T) 이므로 서브하모닉 조건 자체가 성립하지 않는다.  RSL = 0 Ohm")
    print(f"       RSL 을 넣으면 전류제한이 D 에 따라 줄어든다 (RSL 1 k : -{DS.i_slope*1e3*D['d_min']/rcs:.2f} A @D {D['d_min']:.2f})")
    # COMP 동작점
    for vin, d in ((S.vin_min, D["d_min"]), (S.vin_max, D["d_max"])):
        v_cs_cmd = rcs * ipk + DS.v_slope * d + DS.v_slope_off
        v_comp = v_cs_cmd / DS.g_comp
        print(f"    V_COMP @ {vin:.0f} V 전부하 = (Rcs·Ipk {rcs*ipk*1e3:.0f} mV + 램프 {DS.v_slope*d*1e3:.0f} mV + 오프셋 170 mV) / 0.142 "
              f"= {v_comp:.2f} V  (클램프 {DS.comp_lo}~{DS.comp_hi} V)")
    v_comp_cl = (DS.v_clth + DS.v_slope * D["d_min"] + DS.v_slope_off) / DS.g_comp
    print(f"    전류제한 도달 V_COMP = {v_comp_cl:.2f} V < 상한 클램프 2.5 V -> 과부하 시 CL 비교기가 우선")

    # ------------------------------------------------ 6. 루프 보상 (Type-2)
    print("\n-- 6. 루프 보상 Type-2 (COMP 핀, DS 9.3.9) " + "-" * 49)
    eta_t = 0.90                                         # 트랜스+다이오드 전달효율
    v_o = S.v_s1
    p_o = A.P_fb_out
    r_load = v_o ** 2 / p_o
    k_fb = r_fbb / (r_fbt + r_fbb)
    fc_target = 4e3

    def k_mod(vin):
        return DS.g_comp / (rcs + DS.v_slope * lp * fsw / vin)      # dIpk/dVcomp

    g_i = lp * ipk * fsw * eta_t / v_o                    # d(i_out)/d(Ipk)
    g_conv = p_o / v_o ** 2                               # 컨버터 고유 출력 컨덕턴스 (DCM)

    def plant(f, vin, cpl):
        s = 2j * math.pi * f
        g_load = -p_o / v_o ** 2 if cpl else 1 / r_load
        y = s * c_out + g_conv + g_load
        return g_i * k_mod(vin) / y

    def zc(f, r, c, chf):
        s = 2j * math.pi * f
        z_rc = r + 1 / (s * c)
        y = 1 / z_rc + s * chf + 1 / DS.r_o
        return 1 / y

    def loop(f, vin, cpl, r, c, chf):
        delay = complex(math.cos(-2 * math.pi * f * 0.5 / fsw), math.sin(-2 * math.pi * f * 0.5 / fsw))
        return plant(f, vin, cpl) * k_fb * DS.gm * zc(f, r, c, chf) * delay

    # R_COMP : fc 에서 |T| = 1 (중역에서 Zc ~ R_COMP)
    g_pl = abs(plant(fc_target, S.vin_min, False))
    r_comp = e_round(1 / (g_pl * k_fb * DS.gm))
    f_p = (g_conv + 1 / r_load) / (2 * math.pi * c_out)
    c_comp = e_round(1 / (2 * math.pi * r_comp * f_p / 2), E24)   # 영점 = 플랜트 극점 / 2
    c_hf = e_round(1 / (2 * math.pi * r_comp * fsw / 2), E24)     # 고주파 극점 = fsw/2
    print(f"    플랜트 (DCM 전류모드, S1 기준) : 변조기 이득 0.142/(Rcs + 40 mV·Lp·fsw/Vin) = "
          f"{k_mod(S.vin_min):.2f} A/V @18 V, {k_mod(S.vin_max):.2f} A/V @50 V")
    print(f"      출력 컨덕턴스 (컨버터 {g_conv:.3f} + 부하 {1/r_load:.3f}) S, C_out {c_out*1e6:.0f} uF -> 극점 {f_p:.0f} Hz")
    print(f"    설계 : fc {fc_target/1e3:.0f} kHz (fsw/25) -> R_COMP {fmt_r(r_comp)}Ohm,  영점 f_p/2 -> C_COMP {fmt_c(c_comp)},  "
          f"고주파 극점 fsw/2 -> C_HF {fmt_c(c_hf)}")
    print(f"      시정수 : R_COMP·C_COMP = {r_comp*c_comp*1e6:.0f} us (영점 {1/(2*math.pi*r_comp*c_comp):.0f} Hz),  "
          f"R_COMP·C_HF = {r_comp*c_hf*1e9:.0f} ns (극점 {1/(2*math.pi*r_comp*c_hf)/1e3:.0f} kHz)")
    freqs = [10 ** (2 + i / 40) for i in range(120)]    # 100 Hz ~ 100 kHz
    loop_res = {}
    for vin in (S.vin_min, S.vin_max):
        for cpl in (False, True):
            mags = [abs(loop(f, vin, cpl, r_comp, c_comp, c_hf)) for f in freqs]
            fc = pm = gm_db = None
            for i in range(1, len(freqs)):
                if mags[i - 1] >= 1 > mags[i]:
                    fc = freqs[i]
                    ph = math.degrees(math.atan2(loop(fc, vin, cpl, r_comp, c_comp, c_hf).imag,
                                                 loop(fc, vin, cpl, r_comp, c_comp, c_hf).real))
                    pm = 180 + ph if ph <= 0 else ph - 180
                    break
            for i in range(1, len(freqs)):
                t0 = loop(freqs[i - 1], vin, cpl, r_comp, c_comp, c_hf)
                t1 = loop(freqs[i], vin, cpl, r_comp, c_comp, c_hf)
                p0 = math.degrees(math.atan2(t0.imag, t0.real))
                p1 = math.degrees(math.atan2(t1.imag, t1.real))
                if p0 > -180 >= p1 or (p0 < 0 < p1):
                    gm_db = -20 * math.log10(abs(t1))
                    break
            loop_res[(vin, cpl)] = (fc, pm, gm_db)
            print(f"      Vin {vin:2.0f} V, {'정전력 부하 (POL)' if cpl else '저항 부하      '} : "
                  f"fc {fc/1e3 if fc else 0:.1f} kHz, PM {pm if pm else 0:.0f} deg, "
                  f"GM {gm_db if gm_db is not None else 99:.0f} dB")
    pm_min = min(v[1] for v in loop_res.values() if v[1] is not None)
    fc_max = max(v[0] for v in loop_res.values() if v[0] is not None)
    # C_out 감도
    print("      C_out 감도 (정전력 부하, 18 V) :", end="")
    c_save = c_out
    for cx in (30e-6, 60e-6, 120e-6):
        c_out = cx
        mags = [abs(loop(f, S.vin_min, True, r_comp, c_comp, c_hf)) for f in freqs]
        fcx = next((freqs[i] for i in range(1, len(freqs)) if mags[i - 1] >= 1 > mags[i]), None)
        t = loop(fcx, S.vin_min, True, r_comp, c_comp, c_hf)
        pmx = 180 + math.degrees(math.atan2(t.imag, t.real))
        print(f"  {cx*1e6:.0f} uF -> fc {fcx/1e3:.1f} kHz / PM {pmx:.0f} deg", end="")
    c_out = c_save
    print()

    # ------------------------------------------------ 7. 기동 / 부하과도 시뮬레이션
    print("\n-- 7. 기동 · 부하과도 시뮬레이션 (사이클 평균, dt 1 us) " + "-" * 38)

    def simulate(vin, cpl=True, t_end=30e-3, t_step=20e-3, p_lo=0.5):
        dt = 1e-6
        v_o_s, v_ss, v_cc, v_comp = 0.0, 0.0, 0.0, DS.comp_lo
        t = 0.0
        t_ss0 = DS.t_start + DS.t_vcc_dly
        stats = dict(t_reg=None, t_pg=None, v_max=0.0, cl_hits=0, ccm=0, v_min_step=99.0,
                     t_settle=None, ipk_max=0.0)
        n = 0
        cyc_ipk = 0.0
        while t < t_end:
            if t >= t_ss0:
                v_ss = min(v_ss + DS.i_ss / c_ss * dt, 1.2)
            ref = min(v_ss, DS.v_ref)
            err = ref - v_o_s * k_fb
            i_ea = max(min(DS.gm * err, 180e-6), -180e-6)
            i_rc = (v_comp - v_cc) / r_comp
            v_comp += (i_ea - i_rc - v_comp / DS.r_o) / c_hf * dt
            v_cc += i_rc / c_comp * dt
            v_comp = max(min(v_comp, DS.comp_hi), 0.0)
            if n % 10 == 0:                              # 스위칭 주기마다 Ipk 결정
                cmd = (DS.g_comp * v_comp - DS.v_slope_off)
                ipk_c = max(cmd, 0.0) / (rcs + DS.v_slope * lp * fsw / vin)
                if ipk_c >= i_cl_typ:
                    ipk_c = i_cl_typ
                    if t > t_ss0 + t_ss_act:
                        stats["cl_hits"] += 1
                cyc_ipk = ipk_c
                if lp * ipk_c * (1 / vin + 1 / vor) > 1 / fsw:
                    stats["ccm"] += 1
                stats["ipk_max"] = max(stats["ipk_max"], ipk_c)
            i_out = 0.5 * lp * cyc_ipk ** 2 * fsw * eta_t / max(v_o_s, 0.5)
            if v_o_s > 4.5:
                p_ld = p_o * (p_lo if t < t_step else 1.0)
            else:
                p_ld = 0.05
            i_ld = p_ld / max(v_o_s, 0.5) if cpl else v_o_s / r_load
            v_o_s += (i_out - i_ld) / c_out * dt
            v_o_s = max(v_o_s, 0.0)
            if stats["t_reg"] is None and v_o_s >= 0.98 * v_s1_set:
                stats["t_reg"] = t
            if stats["t_pg"] is None and v_o_s >= DS.uv_f * v_s1_set:
                stats["t_pg"] = t + DS.pgood_deglitch
            if t < t_step:
                stats["v_max"] = max(stats["v_max"], v_o_s)
            else:
                stats["v_min_step"] = min(stats["v_min_step"], v_o_s)
                if abs(v_o_s - v_s1_set) > 0.02 * v_s1_set:
                    stats["t_settle"] = t - t_step
            t += dt
            n += 1
        return stats

    sim = {}
    for vin in (S.vin_min, S.vin_max):
        st = simulate(vin)
        sim[vin] = st
        print(f"    Vin {vin:2.0f} V : 레귤 도달 {st['t_reg']*1e3:.1f} ms, PGOOD {st['t_pg']*1e3:.1f} ms, "
              f"기동 오버슈트 {(st['v_max']/v_s1_set-1)*100:+.1f} %, Ipk 최대 {st['ipk_max']:.2f} A, "
              f"SS 후 전류제한 {st['cl_hits']} 회, CCM {st['ccm']} 사이클")
        print(f"              부하 50->100 % 스텝 : 언더슈트 {(1-st['v_min_step']/v_s1_set)*100:.1f} %, "
              f"정착(+-2 %) {st['t_settle']*1e6 if st['t_settle'] else 0:.0f} us")

    # ------------------------------------------------ 8. 시정수 요약
    print("\n-- 8. 시정수 · 타이밍 요약 " + "-" * 66)
    r_cl, c_cl = 4.3e3, 47e-9 * 0.6                     # C_eff : X7R DC 바이어스 60 % (calc_rcd.py)
    rows = [
        ("스위칭 주기 T = 1/fsw", 1 / f_rt, "RT 220 k"),
        ("정격 t_on @18 V", D["d_min"] / fsw, f"D {D['d_min']:.3f}"),
        ("정격 t_on @50 V", D["d_max"] / fsw, f"D {D['d_max']:.3f}"),
        ("t_off (2차 도통) ", lp * ipk / vor, "Lp·Ipk/VOR"),
        ("CS 필터 R_F·C_F", tau_cs, "리딩엣지 스파이크"),
        ("RCD 클램프 R_cl·C_eff", r_cl * c_cl, f"{r_cl*c_cl*fsw:.1f} T (calc_rcd.py)"),
        ("BIAS 필터 R_BIAS·C_BIAS", r_bias * c_bias, ""),
        ("UVLO 필터 (R_T||R_B)·C_UVLO", tau_uvlo, ""),
        ("내부 기동 지연", DS.t_start, "DS 9.3.1"),
        ("VCC UV 후 SS 시작 지연", DS.t_vcc_dly, "DS 9.3.3"),
        ("소프트스타트 t_SS", t_ss_act, f"C_SS {fmt_c(c_ss)}"),
        ("PGOOD 디글리치", DS.pgood_deglitch, "내부"),
        ("셧다운 지연 (UVLO < 0.52 V)", DS.t_shdn, "내부"),
        ("보상 영점 R_COMP·C_COMP", r_comp * c_comp, f"{1/(2*math.pi*r_comp*c_comp):.0f} Hz"),
        ("보상 극점 R_COMP·C_HF", r_comp * c_hf, f"{1/(2*math.pi*r_comp*c_hf)/1e3:.0f} kHz"),
        ("플랜트 극점 C_out/(G_conv+G_load)", 1 / (2 * math.pi * f_p), f"{f_p:.0f} Hz"),
    ]
    for nm, tv, note in rows:
        unit = "ms" if tv >= 1e-3 else ("us" if tv >= 1e-6 else "ns")
        val = tv * (1e3 if unit == "ms" else 1e6 if unit == "us" else 1e9)
        print(f"    {nm:34s} {val:8.2f} {unit}   {note}")

    # ------------------------------------------------ 9. 판정
    print("\n-- 9. 판정 " + "-" * 81)
    chk("전류제한 최소 >= Ipk x 1.15", i_cl_min >= ipk * S.cs_margin, f"{i_cl_min:.2f} A", f">= {ipk*S.cs_margin:.2f} A")
    chk("전류제한 최대에서 Bpk", b_cl <= 0.33, f"{b_cl:.3f} T", "<= 0.33 T")
    chk("CS 필터 Eq.13", 3 * tau_cs <= t_off_min, f"{3*tau_cs*1e6:.2f} us", f"<= {t_off_min*1e6:.2f} us")
    chk("최대 듀티 (DS 최소 0.90)", D["d_min"] <= DS.d_max_min - 0.1, f"{D['d_min']:.3f}", "<= 0.80")
    chk(f"DCM 유지 (Lp +{lp_tol*100:.0f} %, fsw +15 %)", tsum_worst <= 0.92, f"{tsum_worst:.2f} T", "<= 0.92 T")
    chk("UVLO 기동/정지 전압", 15.0 <= v_on_act <= 17.0 and 13.0 <= v_off_act <= 15.0,
        f"{v_on_act:.1f} / {v_off_act:.1f} V", "16 +-1 / 14 +-1 V")
    chk("UVLO 핀 전압 @50 V", v_pin_max <= 5.0, f"{v_pin_max:.2f} V", "<= 5 V (abs V_BIAS+0.3)")
    chk("VCC 외부급전 조건", DS.vcc_reg < v_aux and v_aux_nl <= DS.vcc_ext_max,
        f"{v_aux:.1f} V (무부하 {v_aux_nl:.1f})", "6.85 < V < 16 V")
    chk("게이트 전하 Eq.18", i_gate <= DS.ivcc_cl, f"{i_gate*1e3:.1f} mA", "<= 35 mA")
    chk("IC 온도상승 (내부 레귤 @50 V)", p_ic_int * DS.rth_ja <= 30, f"{p_ic_int*DS.rth_ja:.0f} K", "<= 30 K")
    chk("BIAS 전압 여유", S.vin_max <= DS.vbias_max, f"{S.vin_max:.0f} V", "<= 60 V")
    chk("피드백 설정 전압", abs(v_s1_set - S.v_s1) <= 0.03, f"{v_s1_set:.3f} V", "6.0 +-0.03 V")
    chk("COMP 동작점 < 상한 클램프", v_comp_cl < DS.comp_hi, f"{v_comp_cl:.2f} V", "< 2.5 V")
    chk("루프 PM (4 조건 최소)", pm_min >= 50, f"{pm_min:.0f} deg", ">= 50 deg")
    chk("루프 fc <= fsw/10", fc_max <= fsw / 10, f"{fc_max/1e3:.1f} kHz", "<= 10 kHz")
    chk("기동 오버슈트", max((s["v_max"] / v_s1_set - 1) for s in sim.values()) <= 0.05,
        f"{max((s['v_max']/v_s1_set-1) for s in sim.values())*100:+.1f} %", "<= +5 %")
    chk("SS 이후 전류제한 미도달", all(s["cl_hits"] == 0 for s in sim.values()),
        f"{max(s['cl_hits'] for s in sim.values())} 회", "0 회")
    chk("전 시뮬 DCM 유지", all(s["ccm"] == 0 for s in sim.values()),
        f"{max(s['ccm'] for s in sim.values())} 사이클", "0")
    chk("부하스텝 언더슈트", max(1 - s["v_min_step"] / v_s1_set for s in sim.values()) <= 0.05,
        f"{max(1-s['v_min_step']/v_s1_set for s in sim.values())*100:.1f} %", "<= 5 %")
    n_ok = sum(1 for _, o in RESULTS if o)
    print(f"\n  종합 : {n_ok} / {len(RESULTS)} PASS")
    print("=" * 92)
    return 0 if n_ok == len(RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
