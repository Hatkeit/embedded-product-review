"""
상태방정식 검증 스크립트.

1) 스위칭 모델(주기 평균) vs 통합 평균화 모델 vs DCM 축약 모델 — 시간영역 비교
2) CCM 평균 모델: 통합 모델이 CCM 에서 쌍선형 모델과 일치하는지
3) CCM 소신호 해석식(A, B_d) vs 평균 모델의 수치 야코비안
결과 그림: microinverter_unfolding.png
"""
import math
import sys
import time

import numpy as np
from scipy.integrate import solve_ivp

import model as m


def main(plot: bool = True) -> int:
    p = m.Params()
    P_ref = 280.0
    n_cycles = 2
    t_end = n_cycles / p.f_line
    x0 = [p.V_mpp, 0.0, 0.0, 0.0]
    ok = True

    # ---- 1. 스위칭 모델 -------------------------------------------------
    t0 = time.time()
    t_sw, x_sw, duty = m.simulate_switched(p, t_end, x0, P_ref)
    print(f"[switched] {len(t_sw)} 스위칭 주기 적분 ({time.time() - t0:.1f} s)")

    # ---- 1b. 통합 평균화 모델 ------------------------------------------
    def f_avg(t, x):
        v_g = m.grid_voltage(p, t)
        d1 = m.feedforward_duty(p, t, x[0], P_ref)
        return m.averaged_rhs(p, x, d1, m.unfolding_sign(v_g), v_g)

    sol = solve_ivp(f_avg, (0, t_end), x0, method="LSODA", t_eval=t_sw,
                    rtol=1e-7, atol=1e-9, max_step=p.T_s)
    x_av = sol.y.T

    # ---- 1c. DCM 축약 모델 ---------------------------------------------
    def f_red(t, x):
        v_g = m.grid_voltage(p, t)
        d1 = m.feedforward_duty(p, t, x[0], P_ref)
        if d1 <= 0:
            v_pv, v_c, i_g = x
            s_u = m.unfolding_sign(v_g)
            return np.array([(p.I_n - v_pv / p.r_pv) / p.C_pv,
                             -s_u * i_g / p.C_f,
                             (s_u * v_c - v_g - p.R_g * i_g) / p.L_g])
        return m.dcm_reduced_rhs(p, x, d1, m.unfolding_sign(v_g), v_g)

    sol_r = solve_ivp(f_red, (0, t_end), [x0[0], x0[2], x0[3]], method="LSODA",
                      t_eval=t_sw, rtol=1e-7, atol=1e-9, max_step=p.T_s)
    x_rd = sol_r.y.T

    names = ["v_pv [V]", "i_m [A]", "v_c [V]", "i_g [A]"]
    print("\n주기평균 스위칭 모델 대비 오차 (RMS / 신호 피크)")
    for k, nm in enumerate(names):
        span = np.max(np.abs(x_sw[:, k])) or 1.0
        e_av = np.sqrt(np.mean((x_av[:, k] - x_sw[:, k]) ** 2)) / span
        line = f"  {nm:9s} 통합평균 {100 * e_av:6.3f} %"
        if k != 1:
            kr = {0: 0, 2: 1, 3: 2}[k]
            e_rd = np.sqrt(np.mean((x_rd[:, kr] - x_sw[:, k]) ** 2)) / span
            line += f"   DCM축약 {100 * e_rd:6.3f} %"
        print(line)
        if k != 1 and e_av > 0.02:   # i_m 은 리플 평균이라 별도 판정
            ok = False

    # 모드 확인: 최대 d1+d2
    d2 = np.array([m.diode_duty(p, d, v, i) for d, v, i in zip(duty, x_av[:, 0], x_av[:, 1])])
    ccm = (duty > 0) & (duty + d2 >= 1.0 - 1e-9)
    vg_abs = np.abs(p.V_g_pk * np.sin(p.omega * t_sw))
    print(f"  CCM 주기 비율 {100 * ccm.mean():.1f} %"
          + (f" — 모두 |v_g| < {vg_abs[ccm].max():.0f} V (영점 부근, v_c 가 작아 감자 불완전)" if ccm.any() else ""))

    P_out = np.mean(x_sw[len(t_sw) // 2:, 3] * np.array(
        [m.grid_voltage(p, t) for t in t_sw[len(t_sw) // 2:]]))
    print(f"  계통 주입 평균전력 (마지막 사이클) = {P_out:.1f} W  (지령 {P_ref:.0f} W, 차이는 R_m·R_g 도통손실)")

    # ---- 2. CCM 에서 통합 모델 == 쌍선형 모델 -----------------------------
    theta = math.radians(70)
    pc = m.Params(L_m=40e-6)       # CCM 이 되도록 큰 L_m
    X, D, s_u = m.ccm_operating_point(pc, theta, 280.0, pc.V_mpp)
    v_g = pc.V_g_pk * math.sin(theta)
    f_u = m.averaged_rhs(pc, X, D, s_u, v_g)
    f_c = m.ccm_averaged_rhs(pc, X, D, s_u, v_g)
    d2 = m.diode_duty(pc, D, X[0], X[1])
    err = np.max(np.abs(f_u - f_c) / (np.abs(f_c) + 1.0))
    print(f"\n[CCM] θ=70°, D={D:.4f}, d2={d2:.4f} (=1-D 이면 CCM), 통합 vs 쌍선형 최대 상대차 {err:.2e}")
    ok &= abs(d2 - (1 - D)) < 1e-12 and err < 1e-9

    # ---- 3. 소신호 해석식 vs 수치 야코비안 --------------------------------
    A, B_d, B_u = m.ccm_small_signal(pc, X, D, s_u)
    J_x = m.numerical_jacobian(lambda x: m.ccm_averaged_rhs(pc, x, D, s_u, v_g), X)
    J_d = m.numerical_jacobian(lambda d: m.ccm_averaged_rhs(pc, X, d[0], s_u, v_g), [D])[:, 0]
    e_A = np.max(np.abs(A - J_x) / (np.abs(A) + 1e-3))
    e_B = np.max(np.abs(B_d - J_d) / (np.abs(B_d) + 1e-3))
    print(f"[소신호] A 상대오차 {e_A:.2e}, B_d 상대오차 {e_B:.2e}")
    ok &= e_A < 1e-5 and e_B < 1e-5
    eig = np.linalg.eigvals(A)
    print("  CCM 극점 [Hz]: " + ", ".join(f"{z.real / (2 * math.pi):+.1f}{z.imag / (2 * math.pi):+.1f}j" for z in eig))

    # ---- 4. DCM 소신호 해석식 vs 수치 야코비안 (정류 좌표계, s_u = +1) ----
    D, V_pv, V_c = 0.40, 37.0, 250.0
    A, B_d, _ = m.dcm_small_signal(p, D, V_pv, V_c)
    J_x = m.numerical_jacobian(lambda x: m.dcm_reduced_rhs(p, x, D, 1.0, V_c), [V_pv, V_c, 1.0])
    J_d = m.numerical_jacobian(lambda d: m.dcm_reduced_rhs(p, [V_pv, V_c, 1.0], d[0], 1.0, V_c), [D])[:, 0]
    e_A = np.max(np.abs(A - J_x) / (np.abs(A) + 1e-3))
    e_B = np.max(np.abs(B_d - J_d) / (np.abs(B_d) + 1e-3))
    print(f"[DCM 소신호] A 상대오차 {e_A:.2e}, B_d 상대오차 {e_B:.2e}")
    ok &= e_A < 1e-5 and e_B < 1e-5
    eig = np.linalg.eigvals(A)
    print("  DCM 극점 [Hz]: " + ", ".join(f"{z.real / (2 * math.pi):+.1f}{z.imag / (2 * math.pi):+.1f}j" for z in eig))

    if plot:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(4, 1, figsize=(9, 10), sharex=True)
        ms = t_sw * 1e3
        for k, nm in enumerate(names):
            ax[k].plot(ms, x_sw[:, k], lw=2.2, color="#94a3b8", label="switched (cycle-avg)")
            ax[k].plot(ms, x_av[:, k], lw=1.0, color="#1d4ed8", label="unified averaged")
            if k != 1:
                kr = {0: 0, 2: 1, 3: 2}[k]
                ax[k].plot(ms, x_rd[:, kr], lw=1.0, ls="--", color="#0891b2", label="DCM reduced-order")
            ax[k].set_ylabel(nm)
            ax[k].grid(alpha=0.3)
        ax[2].plot(ms, np.abs(p.V_g_pk * np.sin(p.omega * t_sw)), lw=0.8, color="#f97316", label="|v_g|")
        ax[0].legend(loc="lower right", fontsize=8)
        ax[2].legend(loc="upper right", fontsize=8)
        ax[-1].set_xlabel("t [ms]")
        fig.suptitle("Flyback + unfolding microinverter: switched vs averaged state equations")
        fig.tight_layout()
        fig.savefig("microinverter_unfolding.png", dpi=110)
        print("\n그림 저장: microinverter_unfolding.png")

    print("\n결과:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(plot="--no-plot" not in sys.argv))
