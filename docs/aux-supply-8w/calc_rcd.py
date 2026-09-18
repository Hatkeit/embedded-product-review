#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RCD 클램프 (R_cl / C_cl / D_cl) 시정수 · 소자 설계   (PS-AUX-8W Rev.D)

  전력단 값은 calc_aux.py 를 그대로 인계한다 (Lp, Ipk, VOR, fsw, k_clamp, k_llk).
  계산 항목
    1. 누설 에너지·클램프 손실, 클램프 전압 (Vcl = k_clamp x VOR 목표)
    2. 시정수 4개 : 누설 리셋 t_reset, R·C 방전, Llk-C_cl 공진, 리셋 후 링잉
    3. C_cl : 리플 ΔV, 실효 용량(X7R DC 바이어스), RMS 전류, 내압
    4. R_cl : 손실·정격, 누설 공차(1~3 %)와 부하에 따른 클램프 전압 자기조정, 무부하 고정손실
    5. D_cl : 역전압, 피크/평균 전류, trr 요구
    6. 기동 시 C_cl 충전 사이클, 부하과도 응답 시정수
    7. 판정

외부 의존성 없음.  실행: python3 calc_rcd.py
"""

import io
import math
import contextlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import calc_aux as A                                   # noqa: E402

RESULTS = []


def chk(name, ok, val, crit):
    RESULTS.append((name, ok))
    print(f"  [{'PASS' if ok else 'FAIL':4s}] {name:34s} {val:>22s}  (기준 {crit})")


def vcl_self(r, p0, vor):
    """R 고정 시 클램프 전압 자기조정 : Vcl²/R = P0·Vcl/(Vcl-VOR)  ->  Vcl = [VOR + sqrt(VOR² + 4·P0·R)]/2"""
    return 0.5 * (vor + math.sqrt(vor ** 2 + 4 * p0 * r))


def main():
    S = A.S
    with contextlib.redirect_stdout(io.StringIO()):
        A.main()
    D = A.dcm_design(5)
    lp, ipk, vor, fsw = D["lp"], D["ipk"], D["vor"], S.fsw
    T = 1 / fsw
    print("=" * 92)
    print(" RCD 클램프 시정수 · 소자 설계  (PS-AUX-8W Rev.D)")
    print("=" * 92)
    print(f"  전력단 : Lp {lp*1e6:.1f} uH, Ipk {ipk:.2f} A, VOR {vor:.1f} V, fsw {fsw/1e3:.0f} kHz (T {T*1e6:.0f} us), "
          f"Vin {S.vin_min:.0f}~{S.vin_max:.0f} V")

    # ------------------------------------------------ 1. 누설 에너지 / 클램프 전압 / 손실
    print("\n-- 1. 누설 에너지와 클램프 손실 " + "-" * 61)
    llk = S.k_llk * lp
    e_lk = 0.5 * llk * ipk ** 2
    p0 = e_lk * fsw
    vcl = S.k_clamp * vor
    k_v = vcl / (vcl - vor)
    p_cl = p0 * k_v
    e_cyc = e_lk * k_v
    q_cyc = e_cyc / vcl
    i_cl_avg = p_cl / vcl
    print(f"    Llk = {S.k_llk*100:.0f} % x Lp = {llk*1e6:.2f} uH  ->  E_lk = 0.5·Llk·Ipk² = {e_lk*1e6:.2f} uJ/cycle,  P0 = {p0:.3f} W")
    print(f"    클램프 전압 Vcl = {S.k_clamp:.1f} x VOR = {vcl:.1f} V  (Vcl - VOR = {vcl-vor:.1f} V 가 누설 리셋 전압)")
    print(f"    승수 Vcl/(Vcl-VOR) = {k_v:.2f}  ->  클램프 흡수 에너지 {e_cyc*1e6:.2f} uJ/cycle,  P_cl = {p_cl:.2f} W")
    print(f"      (누설 에너지 {p0:.2f} W + 리셋 중 클램프로 새는 자화 에너지 {p_cl-p0:.2f} W)")
    print(f"    사이클당 전하 Q = E/Vcl = {q_cyc*1e9:.0f} nC,  평균 클램프 전류 {i_cl_avg*1e3:.1f} mA")

    # ------------------------------------------------ 2. 시정수
    print("\n-- 2. 시정수 " + "-" * 80)
    r_cl = vcl ** 2 / p_cl
    r_cl_sel = 4.3e3
    c_cl_nom = 22e-9
    c_cl_sel = 47e-9                        # Rev.D : X7R DC 바이어스 감소를 고려해 47 nF (아래 3장)
    k_dc = 0.60                             # 100 V X7R 1210 @ ~55 V DC 바이어스 실효 용량 (제조사 곡선으로 확인)
    c_eff = c_cl_sel * k_dc
    t_reset = llk * ipk / (vcl - vor)
    tau_rc = r_cl_sel * c_eff
    f_res = 1 / (2 * math.pi * math.sqrt(llk * c_eff))
    t_qres = 1 / (4 * f_res)
    c_par = 150e-12                         # Q1 Coss(~100 pF @50 V) + D_cl Cj(~20 pF) + 권선 용량
    f_ring = 1 / (2 * math.pi * math.sqrt(llk * c_par))
    z_ring = math.sqrt(llk / c_par)
    print(f"    (a) 누설 리셋 시간   t_reset = Llk·Ipk/(Vcl-VOR) = {t_reset*1e9:.0f} ns  ({t_reset/T*100:.1f} % of T)")
    print(f"        -> D_cl 은 주기당 {t_reset*1e9:.0f} ns 만 도통. trr <= {t_reset*1e9/3:.0f} ns 급 초고속 필요")
    print(f"    (b) R·C 방전 시정수  tau = R_cl·C_eff = {r_cl_sel/1e3:.1f} k x {c_eff*1e9:.0f} nF = {tau_rc*1e6:.0f} us = {tau_rc/T:.1f} T")
    print(f"        -> 리플 ΔV = Q/C_eff = {q_cyc/c_eff:.1f} V ({q_cyc/c_eff/vcl*100:.0f} %),  "
          f"동일하게 Vcl·T/tau = {vcl*T/tau_rc:.1f} V.  설계 기준 tau >= 5 T (리플 <= 20 %)")
    print(f"    (c) Llk-C_cl 공진    f = 1/(2π√(Llk·C_eff)) = {f_res/1e6:.2f} MHz, 1/4 주기 {t_qres*1e9:.0f} ns")
    print(f"        -> t_reset {t_reset*1e9:.0f} ns < {t_qres*1e9:.0f} ns : 리셋 중 C_cl 은 정전압원으로 동작 (ΔV 가 작다는 뜻과 동치)")
    print(f"    (d) 리셋 후 링잉      f = 1/(2π√(Llk·C_par)) = {f_ring/1e6:.1f} MHz (C_par {c_par*1e12:.0f} pF 가정), "
          f"특성임피던스 {z_ring:.0f} Ohm")
    print(f"        -> RCD 는 이 링잉을 감쇠하지 못한다 (다이오드 OFF). v_ring 10 V 로 Vds 에 가산(calc_aux). "
          f"RC 스너버(R {z_ring:.0f} Ohm/C 220 pF)는 손실 {c_par*1.5*(S.vin_max+vcl)**2*fsw:.2f} W -> DNP 풋프린트만")
    print(f"    (e) 부하과도 시 Vcl 정착  5·tau = {5*tau_rc*1e6:.0f} us  (SS 10 ms, 루프 fc 4.5 kHz 보다 빠름 -> 상호작용 없음)")

    # ------------------------------------------------ 3. C_cl
    print("\n-- 3. C_cl 선정 " + "-" * 77)
    print("    {:>14}{:>10}{:>10}{:>10}{:>12}{:>10}".format("C_cl", "C_eff", "tau[T]", "ΔV[V]", "ΔV/Vcl", "Vds_pk[V]"))
    for c, k in ((22e-9, 1.0), (22e-9, k_dc), (33e-9, k_dc), (47e-9, k_dc), (100e-9, k_dc)):
        ce = c * k
        dv = q_cyc / ce
        vds = S.vin_max + vcl + dv / 2 + S.v_ring
        tag = "필름/C0G (감소 없음)" if k == 1.0 else "X7R 100 V @55 V 바이어스"
        mark = "  <= 채택" if (c == c_cl_sel and k == k_dc) else ""
        print(f"    {c*1e9:>10.0f} nF{ce*1e9:>10.1f}{r_cl_sel*ce/T:>10.1f}{dv:>10.1f}{dv/vcl*100:>11.0f} %{vds:>10.1f}   {tag}{mark}")
    i_c_rms = ipk * math.sqrt(t_reset / (3 * T))
    v_c_max = vcl + q_cyc / c_eff / 2
    print(f"    C_cl RMS 전류 (삼각 펄스 {ipk:.2f} A x {t_reset*1e9:.0f} ns / {T*1e6:.0f} us) = {i_c_rms*1e3:.0f} mA")
    print(f"    C_cl 최대 전압 = Vcl + ΔV/2 = {v_c_max:.1f} V  -> 100 V 품 ({v_c_max/100*100:.0f} %).  "
          f"권장 : 47 nF/100 V X7R 1210 (또는 22 nF/100 V 필름·C0G)")

    # ------------------------------------------------ 4. R_cl : 손실, 누설 공차, 부하, 무부하 고정손실
    print("\n-- 4. R_cl 선정과 클램프 전압 자기조정 " + "-" * 55)
    print(f"    R_cl = Vcl²/P_cl = {vcl:.1f}² / {p_cl:.2f} = {r_cl/1e3:.2f} k -> E24 {r_cl_sel/1e3:.1f} kOhm")
    print(f"    손실 {vcl**2/r_cl_sel:.2f} W -> 정격 2 W (2512 x1 또는 1 W 2512 x2 직/병렬로 열 분산, 온도상승 <= 60 K)")
    print("\n    (a) 누설 공차 : R_cl 고정이면 Vcl 은 Vcl(Vcl-VOR) = P0·R 로 자기조정된다")
    print("    {:>8}{:>10}{:>10}{:>12}{:>10}{:>12}{:>12}".format("Llk", "P0[W]", "Vcl[V]", "Vcl-VOR", "P_cl[W]", "Vds_pk[V]", "t_reset"))
    vds_llk = {}
    for k in (0.01, 0.015, 0.02, 0.025, 0.03):
        l = k * lp
        p0k = 0.5 * l * ipk ** 2 * fsw
        v = vcl_self(r_cl_sel, p0k, vor)
        pk = v ** 2 / r_cl_sel
        vds = S.vin_max + v + q_cyc / c_eff / 2 + S.v_ring
        tr = l * ipk / (v - vor)
        vds_llk[k] = vds
        print(f"    {k*100:>6.1f} %{p0k:>10.3f}{v:>10.1f}{v-vor:>12.1f}{pk:>10.2f}{vds:>12.1f}{tr*1e9:>9.0f} ns"
              + ("  <= 설계점" if k == S.k_llk else ""))
    vcl_max_allow = 120.0 - S.vin_max - S.v_ring - q_cyc / c_eff / 2
    p0_3 = 0.5 * 0.03 * lp * ipk ** 2 * fsw
    r_max_3 = vcl_max_allow * (vcl_max_allow - vor) / p0_3
    print(f"    -> Vds <= 120 V 를 지키는 Vcl 상한 {vcl_max_allow:.1f} V.  실측 누설이 3 % 면 R_cl <= {r_max_3/1e3:.1f} k 로 낮춘다")
    print(f"       실측 누설이 1 % 면 R_cl 을 {vcl**2/(0.5*0.01*lp*ipk**2*fsw*k_v)/1e3:.1f} k 로 올려야 Vcl {vcl:.0f} V 가 유지된다 "
          f"(4.3 k 그대로면 Vcl 이 {vcl_self(r_cl_sel, 0.5*0.01*lp*ipk**2*fsw, vor):.0f} V 로 내려와 자화 에너지를 먹는다)")
    print("\n    (b) 부하 의존 : Ipk 가 줄면 P0 가 줄고 Vcl 은 VOR 쪽으로 내려온다")
    print("    {:>8}{:>10}{:>10}{:>12}{:>10}".format("부하", "Ipk[A]", "Vcl[V]", "Vcl-VOR", "P_cl[W]"))
    for frac in (1.0, 0.5, 0.25, 0.1, 0.0):
        ipk_f = ipk * math.sqrt(frac)                    # DCM : P ∝ Ipk²
        p0f = 0.5 * llk * ipk_f ** 2 * fsw
        v = vcl_self(r_cl_sel, p0f, vor)
        print(f"    {frac*100:>6.0f} %{ipk_f:>10.2f}{v:>10.1f}{v-vor:>12.1f}{v**2/r_cl_sel:>10.2f}")
    p_stand = vor ** 2 / r_cl_sel
    print(f"    -> 무부하 고정손실 VOR²/R_cl = {p_stand:.2f} W : 클램프가 VOR 에 붙어 자화 에너지를 계속 먹는다.")
    print(f"       (경부하 효율을 중시하면 R_cl 을 키우고 Vcl 을 올린다 — Vds 여유 {120-S.vin_max-vcl-S.v_ring:.0f} V 안에서. "
          f"또는 TVS 클램프 : 고정손실 0, 동적손실 {p0:.2f} W x 승수)")

    # ------------------------------------------------ 5. D_cl
    print("\n-- 5. D_cl 선정 " + "-" * 77)
    print(f"    역전압 = Vin,max + Vcl(3 % 누설) + 링잉 = {vds_llk[0.03]:.0f} V -> 200 V 품 ({vds_llk[0.03]/200*100:.0f} %)")
    print(f"    순방향 : 피크 {ipk:.2f} A ({t_reset*1e9:.0f} ns 삼각파), 평균 {i_cl_avg*1e3:.1f} mA, RMS {i_c_rms*1e3:.0f} mA -> 1 A 품")
    print(f"    trr <= {t_reset*1e9/3:.0f} ns, 순방향 회복 전압 낮은 품 (ES1D/US1D 급, SMA).  Vf 손실 {0.9*i_cl_avg*1e3:.0f} mW")

    # ------------------------------------------------ 6. 기동 / 과도
    print("\n-- 6. 기동 시 C_cl 충전 " + "-" * 69)
    e_chg = 0.5 * c_eff * vor ** 2
    ipk_ss = 0.5
    e_ss = 0.5 * lp * ipk_ss ** 2
    n_cyc = e_chg / e_ss
    print(f"    C_cl 이 0 -> VOR({vor:.0f} V) 까지 : 에너지 {e_chg*1e6:.0f} uJ.  SS 초기 Ipk {ipk_ss:.1f} A 면 사이클당 {e_ss*1e6:.1f} uJ "
          f"-> 약 {n_cyc:.0f} 사이클 ({n_cyc*T*1e6:.0f} us)")
    print(f"    그 동안은 2차가 도통하지 못하고 자화 에너지가 전부 클램프로 간다 — SS 10 ms 대비 무시 가능")

    # ------------------------------------------------ 7. 판정
    print("\n-- 7. 판정 " + "-" * 81)
    chk("R·C >= 5 T (리플 <= 20 %)", tau_rc >= 5 * T, f"{tau_rc/T:.1f} T", ">= 5 T")
    chk("리플 ΔV/Vcl", q_cyc / c_eff / vcl <= 0.20, f"{q_cyc/c_eff/vcl*100:.0f} %", "<= 20 %")
    chk("t_reset < 1/4 공진주기", t_reset < t_qres, f"{t_reset*1e9:.0f} ns", f"< {t_qres*1e9:.0f} ns")
    chk("Vds 피크 (누설 2 %, 리플 포함)", vds_llk[0.02] <= 120, f"{vds_llk[0.02]:.1f} V", "<= 120 V")
    chk("Vds 피크 (누설 3 % 코너)", vds_llk[0.03] <= 120, f"{vds_llk[0.03]:.1f} V", "<= 120 V")
    chk("R_cl 정격 여유", vcl_self(r_cl_sel, p0_3, vor) ** 2 / r_cl_sel <= 2.0 * 0.5,
        f"{vcl_self(r_cl_sel, p0_3, vor)**2/r_cl_sel:.2f} W", "<= 1.0 W (2 W x 50 %)")
    chk("C_cl 내압", v_c_max <= 100 * 0.8, f"{v_c_max:.0f} V", "<= 80 V (100 V x 80 %)")
    chk("D_cl 역전압", vds_llk[0.03] <= 200 * 0.8, f"{vds_llk[0.03]:.0f} V", "<= 160 V")
    chk("무부하 고정손실", p_stand <= 0.30, f"{p_stand:.2f} W", "<= 0.30 W")
    n_ok = sum(1 for _, o in RESULTS if o)
    print(f"\n  종합 : {n_ok} / {len(RESULTS)} PASS")
    print("=" * 92)
    return 0 if n_ok == len(RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
