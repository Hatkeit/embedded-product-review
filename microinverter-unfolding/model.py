"""
플라이백 + 언폴딩(unfolding) 브리지 마이크로인버터 상태방정식 모델.

토폴로지
    PV ─┬─ C_pv ── 플라이백(1:n, L_m, Q/D) ── C_f ── 언폴딩 H-브리지(s_u) ── L_g ── v_g
        (Norton 등가)

상태벡터  x = [v_pv, i_m, v_c, i_g]
    v_pv : PV 입력(디커플링) 커패시터 전압          [V]
    i_m  : 플라이백 자화전류 (1차측 환산)            [A]
    v_c  : 언폴딩 브리지 입력(정류파형) 커패시터 전압 [V]  (v_c >= 0)
    i_g  : 계통 인덕터 전류                          [A]
입력      u = [I_n, v_g]
    I_n  : PV Norton 등가 전류원  (i_pv = I_n - v_pv / r_pv)
    v_g  : 계통 전압
제어      q ∈ {0,1} (주 스위치), s_u = sign(v_g) ∈ {+1,-1} (언폴딩 극성)

제공 함수
    switched_matrices : 3개 스위칭 모드(ON / 다이오드 / DCM 휴지)의 (A_k, B)
    averaged_rhs      : CCM/DCM 통합 평균화 상태방정식 (Sun 등, 2001 방식의 d2 보정)
    ccm_small_signal  : CCM 소신호 (A, B_d, B_u) — 선형화 결과의 해석식
    dcm_reduced       : DCM 축약(i_m 대수화) 모델의 대신호/소신호 계수
    simulate_switched : 스위칭 모델 시뮬레이션 (DCM 영점 교차 처리 포함)
"""
from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np


@dataclass(frozen=True)
class Params:
    # PV (MPP 주변 선형 Norton 근사)
    V_mpp: float = 36.0
    I_mpp: float = 8.33
    # 디커플링 / 플라이백
    C_pv: float = 6.0e-3
    L_m: float = 2.7e-6
    n: float = 6.0          # N_s / N_p
    R_m: float = 0.02       # 1차측 환산 도통 저항
    f_s: float = 100e3
    # 출력 필터 / 계통
    C_f: float = 2.0e-6
    L_g: float = 1.0e-3
    R_g: float = 0.5
    V_g_pk: float = 311.0   # 220 Vrms
    f_line: float = 60.0

    @property
    def r_pv(self) -> float:
        # MPP 에서 dP/dv = 0  ⇒  동특성 저항 r_pv = V_mpp / I_mpp
        return self.V_mpp / self.I_mpp

    @property
    def I_n(self) -> float:
        return self.I_mpp + self.V_mpp / self.r_pv

    @property
    def T_s(self) -> float:
        return 1.0 / self.f_s

    @property
    def omega(self) -> float:
        return 2.0 * math.pi * self.f_line


# --------------------------------------------------------------------------
# 1. 스위칭 모델:  ẋ = A_k(s_u) x + B u ,  k ∈ {1: Q ON, 2: D ON, 3: 휴지(DCM)}
# --------------------------------------------------------------------------
def switched_matrices(p: Params, s_u: float):
    a_pv = -1.0 / (p.r_pv * p.C_pv)
    out = np.array([[0.0, -s_u / p.C_f],
                    [s_u / p.L_g, -p.R_g / p.L_g]])

    A1 = np.zeros((4, 4))
    A1[0, 0], A1[0, 1] = a_pv, -1.0 / p.C_pv
    A1[1, 0], A1[1, 1] = 1.0 / p.L_m, -p.R_m / p.L_m
    A1[2:, 2:] = out

    A2 = np.zeros((4, 4))
    A2[0, 0] = a_pv
    A2[1, 1], A2[1, 2] = -p.R_m / p.L_m, -1.0 / (p.n * p.L_m)
    A2[2, 1] = 1.0 / (p.n * p.C_f)
    A2[2:, 2:] = out

    A3 = np.zeros((4, 4))
    A3[0, 0] = a_pv
    A3[2:, 2:] = out

    B = np.array([[1.0 / p.C_pv, 0.0],
                  [0.0, 0.0],
                  [0.0, 0.0],
                  [0.0, -1.0 / p.L_g]])
    return A1, A2, A3, B


def grid_voltage(p: Params, t: float) -> float:
    return p.V_g_pk * math.sin(p.omega * t)


def unfolding_sign(v_g: float) -> float:
    return 1.0 if v_g >= 0.0 else -1.0


# --------------------------------------------------------------------------
# 2. 통합(CCM/DCM) 평균화 모델
# --------------------------------------------------------------------------
def diode_duty(p: Params, d1: float, v_pv: float, i_m: float) -> float:
    """d2 = min(1 - d1, 2 L_m f_s <i_m> / (d1 v_pv) - d1),  0 ≤ d2."""
    if i_m <= 0.0:
        return 0.0
    d1e = max(d1, 1e-9)
    d2_dcm = 2.0 * p.L_m * p.f_s * i_m / (d1e * max(v_pv, 1e-9)) - d1
    return min(max(d2_dcm, 0.0), 1.0 - d1)


def averaged_rhs(p: Params, x, d1: float, s_u: float, v_g: float, I_n: float | None = None):
    """
    C_pv dv_pv/dt = I_n - v_pv/r_pv - d1/(d1+d2) · i_m
    L_m  di_m/dt  = d1 v_pv - d2 v_c / n - R_m i_m
    C_f  dv_c/dt  = d2/(d1+d2) · i_m / n - s_u i_g
    L_g  di_g/dt  = s_u v_c - v_g - R_g i_g
    """
    v_pv, i_m, v_c, i_g = x
    I_n = p.I_n if I_n is None else I_n
    d2 = diode_duty(p, d1, v_pv, i_m)
    ds = d1 + d2
    k_sw = d1 / ds if ds > 0 else 0.0
    k_d = d2 / ds if ds > 0 else 0.0
    return np.array([
        (I_n - v_pv / p.r_pv - k_sw * i_m) / p.C_pv,
        (d1 * v_pv - d2 * v_c / p.n - p.R_m * i_m) / p.L_m,
        (k_d * i_m / p.n - s_u * i_g) / p.C_f,
        (s_u * v_c - v_g - p.R_g * i_g) / p.L_g,
    ])


def ccm_averaged_rhs(p: Params, x, d: float, s_u: float, v_g: float, I_n: float | None = None):
    """CCM 쌍선형 평균 모델:  ẋ = [d A1 + (1-d) A2] x + B u."""
    A1, A2, _, B = switched_matrices(p, s_u)
    u = np.array([p.I_n if I_n is None else I_n, v_g])
    return (d * A1 + (1.0 - d) * A2) @ np.asarray(x) + B @ u


# --------------------------------------------------------------------------
# 3. CCM 소신호 모델 (동작점 = 계통 위상 θ 에서의 준정적 평형점)
# --------------------------------------------------------------------------
def ccm_operating_point(p: Params, theta: float, P: float, V_pv: float):
    """계통 위상 θ에서 CCM 준정적 동작점 (X, D). L_g 전압강하는 무시."""
    s_u = unfolding_sign(math.sin(theta))
    I_g = s_u * 2.0 * P / p.V_g_pk * abs(math.sin(theta))
    V_c = max(p.V_g_pk * abs(math.sin(theta)) + p.R_g * abs(I_g), 1e-3)
    D = V_c / (V_c + p.n * V_pv)             # V_c = n D/(1-D) V_pv  (R_m 무시)
    I_m = p.n * abs(I_g) / (1.0 - D)          # (1-D) I_m / n = s_u I_g
    X = np.array([V_pv, I_m, V_c, I_g])
    return X, D, s_u


def ccm_small_signal(p: Params, X, D: float, s_u: float):
    """
    x̃' = A x̃ + B_d d̃ + B_u ũ
    A   = D A1 + (1-D) A2
    B_d = (A1 - A2) X
    B_u = B
    """
    A1, A2, _, B = switched_matrices(p, s_u)
    A = D * A1 + (1.0 - D) * A2
    B_d = (A1 - A2) @ np.asarray(X)
    return A, B_d, B


# --------------------------------------------------------------------------
# 4. DCM 축약 모델 (자화전류 동특성이 f_s 수준으로 빨라 대수식으로 대체)
# --------------------------------------------------------------------------
def dcm_reduced(p: Params, d1: float, v_pv: float, v_c: float):
    """
    <i_sw> = d1² v_pv / (2 L_m f_s)            = v_pv / R_e,   R_e = 2 L_m f_s / d1²
    <i_d>  = d1² v_pv² / (2 L_m f_s v_c)        = (v_pv² / R_e) / v_c   (전력원)
    """
    R_e = 2.0 * p.L_m * p.f_s / d1 ** 2
    return v_pv / R_e, v_pv ** 2 / (R_e * v_c), R_e


def dcm_reduced_rhs(p: Params, x3, d1: float, s_u: float, v_g: float):
    """상태 x = [v_pv, v_c, i_g] 인 3차 DCM 모델."""
    v_pv, v_c, i_g = x3
    i_sw, i_d, _ = dcm_reduced(p, d1, v_pv, max(v_c, 1e-3))
    return np.array([
        (p.I_n - v_pv / p.r_pv - i_sw) / p.C_pv,
        (i_d - s_u * i_g) / p.C_f,
        (s_u * v_c - v_g - p.R_g * i_g) / p.L_g,
    ])


def numerical_jacobian(f, x0, eps=1e-6):
    x0 = np.asarray(x0, float)
    f0 = np.asarray(f(x0))
    J = np.zeros((f0.size, x0.size))
    for k in range(x0.size):
        h = eps * max(1.0, abs(x0[k]))
        xp, xm = x0.copy(), x0.copy()
        xp[k] += h
        xm[k] -= h
        J[:, k] = (np.asarray(f(xp)) - np.asarray(f(xm))) / (2 * h)
    return J


# --------------------------------------------------------------------------
# 5. 제어(피드포워드) 및 스위칭 시뮬레이션
# --------------------------------------------------------------------------
def feedforward_duty(p: Params, t: float, v_pv: float, P_ref: float, d_max: float = 0.6) -> float:
    """DCM 플라이백 전력 피드포워드: p(t) = 2P sin²(ωt) = v_pv² d1² / (2 L_m f_s)."""
    p_inst = 2.0 * P_ref * math.sin(p.omega * t) ** 2
    d1 = math.sqrt(2.0 * p.L_m * p.f_s * p_inst) / max(v_pv, 1.0)
    return min(d1, d_max)


def simulate_switched(p: Params, t_end: float, x0, P_ref: float, steps_per_period: int = 200):
    """
    RK4 로 스위칭 모델 적분. 주기마다 듀티를 샘플링(디지털 PWM),
    ON/OFF 경계에 스텝을 정렬하고 다이오드 전류 영점 교차는 선형 보간으로 분할.
    반환: 주기 평균 상태 (t_mid, x_avg) 와 주기 시작 순간 상태 (t, x) 및 샘플 파형.
    """
    x = np.array(x0, float)
    t = 0.0
    T = p.T_s
    h_nom = T / steps_per_period
    mats = {s: switched_matrices(p, s) for s in (1.0, -1.0)}

    def rhs(tt, xx, mode):
        v_g = grid_voltage(p, tt)
        A1, A2, A3, B = mats[unfolding_sign(v_g)]
        A = (A1, A2, A3)[mode - 1]
        return A @ xx + B @ np.array([p.I_n, v_g])

    def rk4(tt, xx, h, mode):
        k1 = rhs(tt, xx, mode)
        k2 = rhs(tt + h / 2, xx + h / 2 * k1, mode)
        k3 = rhs(tt + h / 2, xx + h / 2 * k2, mode)
        k4 = rhs(tt + h, xx + h * k3, mode)
        return xx + h / 6 * (k1 + 2 * k2 + 2 * k3 + k4)

    n_per = int(round(t_end / T))
    t_avg = np.empty(n_per)
    x_avg = np.empty((n_per, 4))
    duty = np.empty(n_per)
    for k in range(n_per):
        t0 = t
        d1 = feedforward_duty(p, t0, x[0], P_ref)
        duty[k] = d1
        acc = np.zeros(4)
        # ON 구간
        t_on = d1 * T
        n_on = max(1, math.ceil(t_on / h_nom)) if t_on > 0 else 0
        for _ in range(n_on):
            h = t_on / n_on
            xn = rk4(t, x, h, 1)
            acc += 0.5 * (x + xn) * h
            x, t = xn, t + h
        # OFF 구간 (다이오드 → 전류 0 도달 시 휴지)
        t_off_end = t0 + T
        while t < t_off_end - 1e-15:
            h = min(h_nom, t_off_end - t)
            mode = 2 if x[1] > 0.0 else 3
            xn = rk4(t, x, h, mode)
            if mode == 2 and xn[1] < 0.0:
                f = x[1] / (x[1] - xn[1])
                hf = f * h
                xn = rk4(t, x, hf, 2)
                xn[1] = 0.0
                acc += 0.5 * (x + xn) * hf
                x, t = xn, t + hf
                continue
            if mode == 3:
                xn[1] = 0.0
            acc += 0.5 * (x + xn) * h
            x, t = xn, t + h
        t_avg[k] = t0 + T / 2
        x_avg[k] = acc / T
    return t_avg, x_avg, duty


def dcm_small_signal(p: Params, D: float, V_pv: float, V_c: float):
    """
    DCM 축약 모델의 정류 좌표계(i_r = s_u i_g, v_g,r = |v_g|) 소신호.
    상태 x̃ = [ṽ_pv, ṽ_c, ĩ_r],  입력 d̃, ṽ_g,r
    """
    I_sw, I_d, R_e = dcm_reduced(p, D, V_pv, V_c)
    A = np.array([
        [-(1.0 / p.r_pv + 1.0 / R_e) / p.C_pv, 0.0, 0.0],
        [2.0 * I_d / (V_pv * p.C_f), -I_d / (V_c * p.C_f), -1.0 / p.C_f],
        [0.0, 1.0 / p.L_g, -p.R_g / p.L_g],
    ])
    B_d = np.array([-2.0 * I_sw / (D * p.C_pv), 2.0 * I_d / (D * p.C_f), 0.0])
    B_vg = np.array([0.0, 0.0, -1.0 / p.L_g])
    return A, B_d, B_vg
