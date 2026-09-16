#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PV 입력 액티브클램프 플라이백 (18-50 V / 400 V / 150 W) - 동작 검증 시뮬레이터

PSIM 회로(psim-circuit.md)와 동일한 구조를 사이클 단위로 모델링하여
"실제로 동작하는가"를 정량 검증한다.  PSIM Simplified C Block 코드
(psim_control.c)와 제어 알고리즘이 1:1 대응한다.

 - PV 단일다이오드 모델 (Isc/Voc/Vmp/Imp 피팅)
 - 사이클 단위 플라이백 (CCM/DCM 자동, 피크전류모드 + 슬로프보상)
 - 디지털 제어: MPPT(P&O) -> Vpv PI -> 전류지령,  Vout 리미트 PI, min-select
 - 외부 의존성 없음.  실행: python3 sim_verify.py
"""

import math

# ============================================================ PV 모듈 모델
class PVModule:
    """단일다이오드 4-파라미터 모델.  Isc/Voc/Vmp/Imp 에 피팅."""

    Q, K = 1.602176634e-19, 1.380649e-23

    def __init__(self, name, isc, voc, vmp, imp, ncell, beta_voc=-0.0032):
        self.name, self.ncell, self.beta_voc = name, ncell, beta_voc
        self.isc0, self.voc0, self.vmp0, self.imp0 = isc, voc, vmp, imp
        self._fit()

    # --- (a, rs) 가 주어졌을 때 Iph, I0 결정
    def _iph_i0(self, a, rs):
        iph = self.isc0
        for _ in range(60):
            i0 = iph / (math.exp(self.voc0 / a) - 1.0)
            iph_new = self.isc0 + i0 * (math.exp(self.isc0 * rs / a) - 1.0)
            if abs(iph_new - iph) < 1e-12:
                iph = iph_new
                break
            iph = iph_new
        return iph, iph / (math.exp(self.voc0 / a) - 1.0)

    def _i_of_v(self, v, a, rs, iph, i0):
        i = iph
        for _ in range(80):
            f = iph - i0 * (math.exp((v + i * rs) / a) - 1.0) - i
            df = -i0 * (rs / a) * math.exp((v + i * rs) / a) - 1.0
            step = f / df
            i_new = i - step
            if i_new < -1.0:
                i_new = -1.0
            if abs(i_new - i) < 1e-12:
                return i_new
            i = i_new
        return i

    def _residuals(self, a, rs):
        iph, i0 = self._iph_i0(a, rs)
        i_at_vmp = self._i_of_v(self.vmp0, a, rs, iph, i0)
        h = 1e-4
        p1 = (self.vmp0 + h) * self._i_of_v(self.vmp0 + h, a, rs, iph, i0)
        p2 = (self.vmp0 - h) * self._i_of_v(self.vmp0 - h, a, rs, iph, i0)
        return i_at_vmp - self.imp0, (p1 - p2) / (2 * h)

    def _fit(self):
        """(a, rs) 2차원 격자탐색 + 축소.  I(Vmp)=Imp 와 dP/dV|Vmp=0 동시 만족."""
        a_lo, a_hi = 0.5, 6.0 * max(1.0, self.ncell / 36.0)
        rs_lo, rs_hi = 1e-4, 1.5
        best = None
        for _ in range(9):
            for ia in range(19):
                a = a_lo + (a_hi - a_lo) * ia / 18.0
                for ir in range(19):
                    rs = rs_lo + (rs_hi - rs_lo) * ir / 18.0
                    try:
                        r1, r2 = self._residuals(a, rs)
                    except (OverflowError, ValueError, ZeroDivisionError):
                        continue
                    cost = (r1 / max(self.imp0, 1e-6)) ** 2 + (r2 / max(self.imp0, 1e-6)) ** 2
                    if best is None or cost < best[0]:
                        best = (cost, a, rs)
            _, a, rs = best
            da, drs = (a_hi - a_lo) / 9.0, (rs_hi - rs_lo) / 9.0
            a_lo, a_hi = max(0.2, a - da), a + da
            rs_lo, rs_hi = max(1e-5, rs - drs), rs + drs
        self.cost, self.a, self.rs = best
        self.iph0, self.i0 = self._iph_i0(self.a, self.rs)

    # --- 운전 조건에서의 I-V
    def current(self, v, irr=1000.0, tcell=25.0):
        if v <= 0.0:
            v = 0.0
        iph = self.iph0 * irr / 1000.0
        # 온도에 의한 Voc 이동을 등가 다이오드 포화전류 보정으로 반영
        dv = self.beta_voc * self.voc0 * (tcell - 25.0)
        i0 = self.i0 * math.exp(-dv / self.a)
        return max(self._i_of_v(v, self.a, self.rs, iph, i0), 0.0)

    def mpp(self, irr=1000.0, tcell=25.0):
        lo, hi = 0.05 * self.voc0, 1.2 * self.voc0
        best = (0.0, 0.0, 0.0)
        for _ in range(6):
            n = 60
            for k in range(n + 1):
                v = lo + (hi - lo) * k / n
                p = v * self.current(v, irr, tcell)
                if p > best[0]:
                    best = (p, v, p / v if v > 0 else 0.0)
            span = (hi - lo) / n
            lo, hi = best[1] - span, best[1] + span
        return best  # (Pmp, Vmp, Imp)


class ShadedArray:
    """모듈 2 서브스트링 직렬 + 바이패스 다이오드.  부분음영 시 다봉 P-V 곡선."""

    def __init__(self, sub, irr_a, irr_b, tcell=25.0, npts=1500):
        self.name = f"음영 배열 ({irr_a:.0f} / {irr_b:.0f} W/m^2)"
        self.sub, self.irr_a, self.irr_b, self.tcell = sub, irr_a, irr_b, tcell
        i_max = sub.current(0.0, max(irr_a, irr_b), tcell)
        tbl = []
        for k in range(npts + 1):
            i = i_max * k / npts
            v = (self._sub_v(i, irr_a) + self._sub_v(i, irr_b))
            if v > 0.0:
                tbl.append((v, i))
        tbl.sort()
        self.tbl = tbl
        self.voc0 = tbl[-1][0]
        self.isc0 = tbl[0][1]

    def _sub_v(self, i, irr):
        if i >= self.sub.current(0.0, irr, self.tcell):
            return -0.7
        lo, hi = 0.0, 1.5 * self.sub.voc0
        for _ in range(50):
            mid = 0.5 * (lo + hi)
            if self.sub.current(mid, irr, self.tcell) > i:
                lo = mid
            else:
                hi = mid
        return 0.5 * (lo + hi)

    def current(self, v, irr=1000.0, tcell=25.0):
        t = self.tbl
        if v <= t[0][0]:
            return t[0][1]
        if v >= t[-1][0]:
            return 0.0
        lo, hi = 0, len(t) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if t[mid][0] <= v:
                lo = mid
            else:
                hi = mid
        v0, i0 = t[lo]
        v1, i1 = t[hi]
        return i0 + (i1 - i0) * (v - v0) / (v1 - v0) if v1 > v0 else i0

    def mpp(self, irr=1000.0, tcell=25.0):
        best = max(self.tbl, key=lambda r: r[0] * r[1])
        return best[0] * best[1], best[0], best[1]


# ============================================================ 전력단 상수
class HW:
    fsw = 100e3
    tsw = 1.0 / fsw
    lm = 26.34e-6          # 자화 인덕턴스 (1차 환산)
    n_ps = 8.0             # Ns/Np
    np_t, ae = 9, 173e-6   # 자속 계산용
    vf_sec = 1.8           # 2차 SiC SBD
    rds_on = 0.010         # 1차 MOSFET (열간)
    r_pri = 0.0104         # 1차 권선(열간 x Fr=2.0) + PCB 배선
    r_sec = 1.52           # 2차 권선 (열간 x Fr=1.4)
    p_fix = 4.4            # 스위칭 + 게이트 + 코어 + 클램프 + 커패시터 + 제어부 [W]
                           # (design-spec.md 6.2절 손실예산과 정합)
    cin = 250e-6
    cout_hf = 4.7e-6
    d_max = 0.78
    t_on_min = 150e-9
    ipk_ocp = 18.9         # 사이클바이사이클 OCP (raw 전류센스 기준, HW 비교기)
    se_ratio = 0.60        # 슬로프보상 Se / Sf

    @property
    def ipk_cmd_max(self):
        """전류지령(DAC) 상한.  보상램프가 지령 레인지를 잠식하므로
        OCP 문턱값보다 Se x ton_max 만큼 높게 잡아야 저입력 전부하에 도달한다."""
        return self.ipk_ocp + self.se_ratio * (400.0 + self.vf_sec) / self.n_ps \
            / self.lm * self.d_max * self.tsw


HWc = HW()


def vor(vout):
    return (vout + HWc.vf_sec) / HWc.n_ps


def sf_slope(vout):
    """1차 환산 하강 기울기 [A/s]"""
    return vor(vout) / HWc.lm


# ============================================================ 제어기 (psim_control.c 와 동일)
class Ctrl:
    """MPPT(P&O) -> Vpv PI  /  Vout 리미트 PI  /  min-select + 백캘큘레이션 안티와인드업.
    psim_control.c 의 Simplified C Block 코드와 알고리즘이 1:1 대응한다."""

    KP_VIN, KI_VIN = 2.0, 4000.0          # A/V, A/(V*s)   교차 ~760 Hz (Cin 250 uF)
    KP_VO, KI_VO = 3.5, 1100.0            # A/V, A/(V*s)   교차 ~150 Hz (Cdc 100 uF)
    VO_REF_LIMIT = 420.0                   # 하류 인버터가 버스(400 V)를 세우는 구성
    VO_REF_REG = 400.0                     # 본 단이 버스를 세우는 구성
    VO_DB = 2.0                            # 리미터 불감대 [V]
    VO_RECOVER = 300.0                     # 리미터 적분기 상향 복귀율 [A/s]
    # 루프 C : 입력전력 리미트.  PV 오버사이징(DC/AC ratio > 1)에서 패널이
    # 정격 이상을 공급할 수 있으므로 반드시 필요하다.
    P_IN_MAX = 166.7                       # = 150 W 출력 / eta 0.90 [W]
    KP_P, KI_P = 0.020, 40.0               # A/W, A/(W*s)
    P_DB = 5.0                             # 불감대 [W]
    P_RECOVER = 300.0                      # 적분기 상향 복귀율 [A/s]
    SS_TIME = 0.020                        # 소프트스타트 20 ms
    F_CTRL = 25e3                          # 제어루프 25 kHz
    T_MPPT = 2.0e-3                        # MPPT 주기 2 ms
    DV_MIN, DV_MAX = 0.10, 1.50            # 적응 섭동 폭 [V]
    DV_K = 20.0                            # 섭동폭 = DV_K x |dP|/P
    IRR_TH = 0.08                          # |dP|/P 가 이 값을 넘으면 일사량 급변으로 판정
    SCAN_EN = True                         # 전역 MPP 스캔 (부분음영 대응)
    SCAN_HI, SCAN_LO = 0.95, 0.30          # 스캔 구간 = (SCAN_LO ~ SCAN_HI) x Voc_est
    SCAN_STEP = 1.20                       # 스캔 전압 스텝 [V]
    SCAN_DWELL = 2.0e-3                    # 스텝당 정착 대기 [s]
    T_RESCAN = 300.0                       # 재스캔 주기 [s] (실장 5 분, 시험 시 단축)
    TAU_I = 100e-6                         # 입력전류 필터
    AW_MARGIN = 0.5                        # min-select 대기 마진 [A]
    K_VOC = 0.80                           # 초기 Vpv 기준 = 0.80 x Voc (fractional-Voc 기동)

    def __init__(self, vpv_ref0, vo_ref=None):
        self.vo_ref = VO_REF if (vo_ref is None) else vo_ref
        self.tc = 1.0 / self.F_CTRL
        self.int_vin = 0.0
        self.int_vo = HWc.ipk_cmd_max      # 리미트 루프는 "무제한"에서 시작
        self.int_p = HWc.ipk_cmd_max
        self.vpv_ref = vpv_ref0
        self.p_prev = -1.0
        self.dirn = -1.0
        self.ipv_f = 0.0
        self.t_next_ctrl = 0.0
        self.t_next_mppt = self.T_MPPT
        self.ipk_cmd = 0.0
        self.mode = "SS"
        # --- 전역 MPP 스캔 상태
        self.voc_est = vpv_ref0 / self.K_VOC
        self.scan = self.SCAN_EN            # 기동 직후 1 회 전역 스캔
        self.scan_v = 0.0
        self.scan_best = (-1.0, vpv_ref0)
        self.t_next_scan = 0.0
        self.t_last_scan = 0.0

    @staticmethod
    def _clamp(x, lo, hi):
        return lo if x < lo else (hi if x > hi else x)

    def update(self, t, vpv, ipv, vout):
        alpha = HWc.tsw / (self.TAU_I + HWc.tsw)
        self.ipv_f += alpha * (ipv - self.ipv_f)

        self.voc_est = max(self.voc_est, vpv)

        # --- 전역 MPP 스캔 : 부분음영에서 P-V 곡선이 다봉(多峰)이 되면 단순 P&O 는
        #     기동점 근처의 국부 피크에 고착한다 (검증 결과 최대 45 % 발전손실).
        #     주기적으로 전 전압구간을 쓸어 전역 최대점을 찾은 뒤 P&O 로 복귀한다.
        if self.scan:
            if t >= self.t_next_scan:
                self.t_next_scan = t + self.SCAN_DWELL
                if self.scan_v <= 0.0:
                    self.scan_v = self.SCAN_HI * self.voc_est
                    self.scan_best = (-1.0, self.vpv_ref)
                else:
                    p = vpv * self.ipv_f
                    if p > self.scan_best[0]:
                        self.scan_best = (p, vpv)
                    self.scan_v -= self.SCAN_STEP
                if self.scan_v < self.SCAN_LO * self.voc_est:
                    self.vpv_ref = self.scan_best[1]
                    self.scan = False
                    self.scan_v = 0.0
                    self.p_prev = -1.0
                    self.t_last_scan = t
                    self.t_next_mppt = t + self.T_MPPT
                else:
                    self.vpv_ref = self._clamp(self.scan_v, 10.0, 60.0)
        else:
            if self.SCAN_EN and (t - self.t_last_scan) >= self.T_RESCAN:
                self.scan = True
                self.t_next_scan = t

            # --- MPPT : 개선형 Perturb & Observe (적응 스텝 + 일사량 급변 검출)
            #     전력 리미트가 동작 중이면 동작점이 MPP 밖에 고정되므로
            #     P&O 를 동결한다 (동결하지 않으면 기준전압이 표류한다).
            if t >= self.t_next_mppt and self.mode != "PL":
                self.t_next_mppt += self.T_MPPT
                p = vpv * self.ipv_f
                if self.p_prev >= 0.0:
                    dp = p - self.p_prev
                    ref = max(self.p_prev, 1.0)
                    if abs(dp) > self.IRR_TH * ref:
                        # 전압섭동으로 설명되지 않는 전력변화 = 일사량/음영 급변.
                        # 방향 판정을 건너뛰어 오방향 고착을 막는다.
                        self.p_prev = p
                    else:
                        if dp < 0.0:
                            self.dirn = -self.dirn
                        step = self._clamp(self.DV_K * abs(dp) / max(p, 1.0),
                                           self.DV_MIN, self.DV_MAX)
                        self.p_prev = p
                        self.vpv_ref = self._clamp(self.vpv_ref + self.dirn * step,
                                                   15.0, 52.0)
                else:
                    self.p_prev = p
                    self.vpv_ref = self._clamp(self.vpv_ref + self.dirn * self.DV_MIN,
                                               15.0, 52.0)

        if t < self.t_next_ctrl:
            return self.ipk_cmd
        self.t_next_ctrl += self.tc

        ipk_ss = HWc.ipk_cmd_max * min(1.0, t / self.SS_TIME)

        # 루프 A : PV 전압 레귤레이션 (Vpv > ref 이면 전류를 더 뽑아 Vpv 를 끌어내린다)
        e_vin = vpv - self.vpv_ref
        cmd_max = HWc.ipk_cmd_max
        self.int_vin = self._clamp(self.int_vin + self.KI_VIN * e_vin * self.tc,
                                   0.0, cmd_max)
        ipk_a = self.KP_VIN * e_vin + self.int_vin

        # 루프 B : 출력 400 V 리미트 (Vout 이 기준을 넘으면 전류지령을 줄인다)
        e_vo = self.vo_ref - vout
        # 비대칭 적분 : Vout 이 기준보다 충분히 낮으면(불감대 밖) 리미터는 개입할
        # 이유가 없으므로 적분기를 최소 VO_RECOVER 속도로 상향 복귀시킨다.
        # 이것이 없으면 e_vo 가 0 인 구간에서 적분기가 임의값에 래치되어
        # 전류지령을 영구히 제한한다 (실제로 관측된 결함).
        d_int = self.KI_VO * e_vo * self.tc
        if e_vo > self.VO_DB:
            d_int = max(d_int, self.VO_RECOVER * self.tc)
        self.int_vo = self._clamp(self.int_vo + d_int, 0.0, cmd_max)
        ipk_b = self.KP_VO * e_vo + self.int_vo

        # 루프 C : 입력전력 리미트 (비대칭 적분).  전류지령을 줄이면 동작점이
        # MPP 오른쪽(고전압/저전류)으로 이동하여 인출전력이 줄어든다.
        p_pv = vpv * self.ipv_f
        e_p = self.P_IN_MAX - p_pv
        d_p = self.KI_P * e_p * self.tc
        if e_p > self.P_DB:
            d_p = max(d_p, self.P_RECOVER * self.tc)
        self.int_p = self._clamp(self.int_p + d_p, 0.0, cmd_max)
        ipk_c = self.KP_P * e_p + self.int_p

        cmd = self._clamp(min(ipk_a, ipk_b, ipk_c, ipk_ss), 0.0, cmd_max)

        # --- min-select 안티와인드업 : 지령을 만들지 '않은' 루프는 적분기를
        #     역산(back-calculation)하여 cmd + 마진에 대기시킨다.  이것이 없으면
        #     버스가 정확히 400 V 로 고정될 때 e_vo = 0 이라 루프 B 가 0 에 묶여
        #     min-select 가 영구히 0 을 선택하는 데드락이 발생한다.
        if ipk_a > cmd + 1e-9:
            self.int_vin = self._clamp(cmd + self.AW_MARGIN - self.KP_VIN * e_vin,
                                       0.0, cmd_max)
        if ipk_b > cmd + 1e-9:
            self.int_vo = self._clamp(cmd + self.AW_MARGIN - self.KP_VO * e_vo,
                                      0.0, HWc.ipk_ocp)

        if cmd >= ipk_ss - 1e-9:
            self.mode = "SS"
        elif ipk_c <= min(ipk_a, ipk_b) + 1e-9:
            self.mode = "PL"
        elif ipk_b < ipk_a:
            self.mode = "VO"
        else:
            self.mode = "MPPT"
        self.ipk_cmd = cmd
        return cmd


# ============================================================ 사이클 단위 전력단
def cycle(i0, vin, vout, ipk_cmd, se_ratio=None):
    """1 스위칭 주기 해석.  반환: (i_end, q_in, q_out, ipk, d, mode)"""
    se = (se_ratio if se_ratio is not None else HWc.se_ratio) * sf_slope(vout)
    s_on = max(vin - i0 * (HWc.rds_on + HWc.r_pri), 1.0) / HWc.lm

    if ipk_cmd <= i0:
        t_on = HWc.t_on_min
    else:
        t_on = (ipk_cmd - i0) / (s_on + se)
    t_on = min(max(t_on, HWc.t_on_min), HWc.d_max * HWc.tsw)

    ipk = i0 + s_on * t_on
    if ipk > HWc.ipk_ocp:                       # 사이클바이사이클 OCP
        t_on = max((HWc.ipk_ocp - i0) / s_on, HWc.t_on_min)
        ipk = i0 + s_on * t_on

    q_in = 0.5 * (i0 + ipk) * t_on

    s_off = sf_slope(vout)
    t_fall = ipk / s_off
    t_avail = HWc.tsw - t_on
    if t_fall < t_avail:                        # DCM
        t_cond, i_end, mode = t_fall, 0.0, "DCM"
    else:                                       # CCM
        t_cond, i_end, mode = t_avail, ipk - s_off * t_avail, "CCM"

    q_out = (0.5 * (ipk + i_end) * t_cond) / HWc.n_ps

    # --- 손실 모델 (2차 다이오드 Vf 는 vor() 에 이미 반영되어 중복 계산하지 않음)
    p_pri = ((i0 * i0 + i0 * ipk + ipk * ipk) / 3.0) * (HWc.rds_on + HWc.r_pri) \
        * (t_on / HWc.tsw)
    is_pk, is_end = ipk / HWc.n_ps, i_end / HWc.n_ps
    p_sec = ((is_pk * is_pk + is_pk * is_end + is_end * is_end) / 3.0) * HWc.r_sec \
        * (t_cond / HWc.tsw)
    p_loss = p_pri + p_sec + HWc.p_fix
    q_out = max(q_out - p_loss * HWc.tsw / max(vout, 1.0), 0.0)
    return i_end, q_in, q_out, ipk, t_on / HWc.tsw, mode, p_loss


# ============================================================ 시나리오 실행
def run(pv, t_end, vout_mode="stiff", irr_profile=None, tcell=25.0,
        cdc=100e-6, p_sink=160.0, se_ratio=None, vpv_ref0=None, decim=20,
        vo_ref=None):
    """vout_mode: 'stiff' = 하류 인버터가 400 V 버스를 고정
                  'bus'   = 본 단이 버스를 세움 (sink 가 p_sink 만 소비)"""
    irr_profile = irr_profile or (lambda t: 1000.0)
    if vo_ref is None:
        vo_ref = Ctrl.VO_REF_REG if vout_mode == "bus" else Ctrl.VO_REF_LIMIT
    ctrl = Ctrl(vpv_ref0 if vpv_ref0 is not None else pv.voc0 * Ctrl.K_VOC, vo_ref)
    vin = pv.voc0
    vout = 400.0 if vout_mode == "stiff" else 30.0
    i_m = 0.0
    cout = HWc.cout_hf + (cdc if vout_mode == "bus" else 0.0)

    tr = dict(t=[], vpv=[], ipv=[], ppv=[], vout=[], ipk=[], d=[], cmd=[],
              ref=[], pmp=[], mode=[], ccm=[], pout=[])
    stats = dict(ipk_max=0.0, vout_max=0.0, vds_max=0.0, d_max=0.0,
                 dcm_cycles=0, cycles=0)
    n = int(t_end * HWc.fsw)
    for k in range(n):
        t = k * HWc.tsw
        irr = irr_profile(t)
        i_pv = pv.current(vin, irr, tcell)

        cmd = ctrl.update(t, vin, i_pv, vout)
        i_m, q_in, q_out, ipk, d, cmode, ploss = cycle(i_m, vin, vout, cmd, se_ratio)

        vin += (i_pv * HWc.tsw - q_in) / HWc.cin
        vin = min(max(vin, 0.5), 80.0)
        if vout_mode == "bus":
            i_sink = p_sink / max(vout, 1.0) if vout > 120.0 else 0.0
            vout += (q_out - i_sink * HWc.tsw) / cout
            vout = min(max(vout, 5.0), 700.0)

        stats["cycles"] += 1
        stats["ipk_max"] = max(stats["ipk_max"], ipk)
        stats["vout_max"] = max(stats["vout_max"], vout)
        stats["vds_max"] = max(stats["vds_max"], vin + vor(vout))
        stats["d_max"] = max(stats["d_max"], d)
        if cmode == "DCM":
            stats["dcm_cycles"] += 1

        if k % decim == 0:
            pmp, _, _ = pv.mpp(irr, tcell) if k % (decim * 25) == 0 else (
                tr["pmp"][-1] if tr["pmp"] else 0.0, 0, 0)
            tr["t"].append(t); tr["vpv"].append(vin); tr["ipv"].append(i_pv)
            tr["ppv"].append(vin * i_pv); tr["vout"].append(vout)
            tr["ipk"].append(ipk); tr["d"].append(d); tr["cmd"].append(cmd)
            tr["pout"].append(q_out * vout / HWc.tsw)
            tr["ref"].append(ctrl.vpv_ref); tr["pmp"].append(pmp)
            tr["mode"].append(ctrl.mode); tr["ccm"].append(1 if cmode == "CCM" else 0)
    return tr, stats, ctrl


def tail_mean(seq, frac=0.2):
    m = max(1, int(len(seq) * frac))
    return sum(seq[-m:]) / m


def b_peak(ipk):
    return HWc.lm * ipk / (HWc.np_t * HWc.ae)


# ============================================================ 검증 시나리오
PV_A = PVModule("PV-A (고전압형, Voc(STC) 43.0 V - 저온 Voc 규정 준수)",
                4.60, 43.0, 35.4, 4.24, 72)
PV_B = PVModule("PV-B (저전압/고전류형, Vmp 18.2 V, 150 W)", 8.90, 22.4, 18.2, 8.25, 36)
PV_C = PVModule("PV-C (설계 최악코너: 입력 166.7 W @ 18.3 V = 출력 150 W + 손실)",
                9.83, 22.6, 18.3, 9.11, 36)

PV_D = PVModule("PV-D (오버사이징: 220 W @ 19.0 V, DC/AC ratio 1.47)",
                12.90, 23.4, 19.0, 11.58, 36)

RESULTS = []


def check(name, ok, val, crit):
    RESULTS.append((name, ok, val, crit))
    print(f"  [{'PASS' if ok else 'FAIL':4s}] {name:38s} {val:>22s}  (기준 {crit})")


def hdr(t):
    print("\n" + "=" * 92 + f"\n {t}\n" + "=" * 92)


# ---------------------------------------------------------- T1 기동 + MPPT
def t1():
    hdr("T1. 기동 및 MPPT 수렴  (PV-A, 400 V 버스는 하류 인버터가 고정)")
    tr, st, _ = run(PV_A, 0.200)
    pmp, vmp, _ = PV_A.mpp()
    p_track = tail_mean(tr["ppv"])
    eff = p_track / pmp
    v_track = tail_mean(tr["vpv"])
    # MPPT 수렴 시각: 이후 계속 99 % 이상을 유지하는 최초 시점
    t_conv = None
    for i in range(len(tr["t"])):
        if all(p >= 0.99 * pmp for p in tr["ppv"][i:]):
            t_conv = tr["t"][i]
            break
    print(f"    Pmp(이론) = {pmp:.1f} W @ {vmp:.2f} V   |   추종 = {p_track:.1f} W @ {v_track:.2f} V")
    check("MPPT 추종 효율", eff >= 0.99, f"{eff*100:.2f} %", ">= 99 %")
    check("MPPT 수렴 시간 (기동 전역스캔 포함)",
          t_conv is not None and t_conv <= 0.100,
          f"{t_conv*1e3:.1f} ms" if t_conv else "미수렴", "<= 100 ms")
    check("기동 중 Ipk (OCP 이내)", st["ipk_max"] <= HWc.ipk_ocp * 1.02,
          f"{st['ipk_max']:.2f} A", f"<= {HWc.ipk_ocp} A")
    check("기동 중 MOSFET Vds", st["vds_max"] <= 120.0, f"{st['vds_max']:.1f} V", "<= 120 V")
    return tr


# ---------------------------------------------------------- T2 일사량 변동
def t2():
    hdr("T2. 일사량 급변 추종  (PV-A, 1000 -> 400 -> 1000 W/m^2)")

    def irr(t):
        return 400.0 if 0.150 <= t < 0.230 else 1000.0

    tr, st, _ = run(PV_A, 0.310, irr_profile=irr)

    def window(t0, t1):
        idx = [i for i, t in enumerate(tr["t"]) if t0 <= t < t1]
        return sum(tr["ppv"][i] for i in idx) / len(idx)

    p_lo_th = PV_A.mpp(400.0)[0]
    p_hi_th = PV_A.mpp(1000.0)[0]
    p_lo = window(0.210, 0.230)
    p_hi = window(0.290, 0.310)
    print(f"    400 W/m^2 : 이론 {p_lo_th:6.1f} W / 추종 {p_lo:6.1f} W")
    print(f"   1000 W/m^2 : 이론 {p_hi_th:6.1f} W / 추종 {p_hi:6.1f} W")
    check("저일사 재추종 효율", p_lo / p_lo_th >= 0.98, f"{100*p_lo/p_lo_th:.2f} %", ">= 98 %")
    check("복귀 후 추종 효율", p_hi / p_hi_th >= 0.99, f"{100*p_hi/p_hi_th:.2f} %", ">= 99 %")
    check("일사 급변 시 Vds", st["vds_max"] <= 120.0, f"{st['vds_max']:.1f} V", "<= 120 V")
    return tr


# ---------------------------------------------------------- T3 최악 코너
def t3():
    hdr("T3. 최악 설계 코너 검증  (PV-C, 18.3 V / 166.7 W 입력 = 150 W 출력) - 트랜스 사양 대조")
    tr, st, _ = run(PV_C, 0.120)
    pmp = PV_C.mpp()[0]
    p = tail_mean(tr["ppv"])
    po = tail_mean(tr["pout"])
    d = tail_mean(tr["d"])
    ipk = tail_mean(tr["ipk"])
    ccm = tail_mean([float(c) for c in tr["ccm"]])
    print(f"    PV 인출 {p:.1f} W / {pmp:.1f} W,  Vpv = {tail_mean(tr['vpv']):.2f} V,"
          f"  출력 {po:.1f} W,  효율 {100*po/p:.1f} %")
    print(f"    design-spec.md 대조 : D 0.736 / Ipk 15.09 A / Bpk 0.255 T / Pout 150 W")
    check("MPPT 추종 효율", p / pmp >= 0.99, f"{100*p/pmp:.2f} %", ">= 99 %")
    check("출력 전력 (설계 150 W)", abs(po - 150.0) <= 8.0, f"{po:.1f} W", "150 +-8 W")
    check("듀티 (설계값 0.736)", abs(d - 0.736) <= 0.03, f"{d:.3f}", "0.736 +-0.03")
    check("피크전류 (설계값 15.09 A)", abs(ipk - 15.09) <= 1.2, f"{ipk:.2f} A", "15.09 +-1.2 A")
    check("CCM 유지율", ccm >= 0.99, f"{ccm*100:.1f} %", ">= 99 %")
    check("피크 자속밀도 (설계값 0.255 T)", b_peak(st["ipk_max"]) <= 0.30,
          f"{b_peak(st['ipk_max']):.3f} T", "<= 0.30 T")
    check("변환 효율", po / p >= 0.90, f"{100*po/p:.1f} %", ">= 90 %")
    return tr


# ---------------------------------------------------------- T4 버스전압 리미트
def t4():
    hdr("T4. 출력 400 V 리미트 루프  (본 단이 버스를 세움, sink 는 70 W 만 소비)")
    tr, st, ctrl = run(PV_A, 0.300, vout_mode="bus", p_sink=70.0, cdc=100e-6)
    vo = tail_mean(tr["vout"])
    p = tail_mean(tr["ppv"])
    modes = tr["mode"][-len(tr["mode"]) // 5:]
    vo_mode = modes.count("VO") / len(modes)
    print(f"    정상상태 Vout = {vo:.1f} V,  PV 인출 = {p:.1f} W (sink 70 W + 손실),"
          f"  최대 Vout = {st['vout_max']:.1f} V")
    check("버스전압 정상상태", abs(vo - 400.0) <= 4.0, f"{vo:.1f} V", "400 +-4 V")
    check("버스전압 오버슈트", st["vout_max"] <= 440.0, f"{st['vout_max']:.1f} V", "<= 440 V (OVP)")
    check("Vout 리미트 루프 점유", vo_mode >= 0.9, f"{vo_mode*100:.0f} %", ">= 90 %")
    check("과잉전력 미인출", p <= 110.0, f"{p:.1f} W", "<= 110 W")
    return tr


# ---------------------------------------------------------- T5 슬로프 보상
def jacobian(vin, vout, cmd, se_ratio, i_nom, delta=0.05):
    """사이클간 섭동 전달률 lambda = d(i_end)/d(i_start).  |lambda| < 1 이면 안정."""
    a = cycle(i_nom, vin, vout, cmd, se_ratio)[0]
    b = cycle(i_nom + delta, vin, vout, cmd, se_ratio)[0]
    return (b - a) / delta


def jacobian_theory(vin, vout, se_ratio):
    """lambda = (Se - m2) / (m1 + Se),  m1 = Vin/Lm,  m2 = VOR/Lm"""
    m1, m2 = vin / HWc.lm, sf_slope(vout)
    se = se_ratio * m2
    return (se - m2) / (m1 + se)


def t5():
    hdr("T5. 슬로프 보상 유효성  (D = 0.735 > 0.5, 서브하모닉 발진)")
    vin, vout = 18.3, 400.0
    # 모든 Se 에서 "같은 물리적 동작점"(Ipk 14.90 A, D 0.735)이 되도록 지령을 보정한다.
    # 보정하지 않으면 저 Se 조건이 듀티 상한에 걸려 야코비안이 왜곡된다.
    ipk_op, ton_op = 14.90, 0.735 * HWc.tsw
    i_nom = ipk_op - sf_slope(vout) * (HWc.tsw - ton_op)
    cmd_of = lambda r: ipk_op + r * sf_slope(vout) * ton_op
    print(f"    동작점 Vin {vin} V / Vout {vout} V / Ipk {ipk_op} A / D 0.735,"
          f"  i_valley = {i_nom:.2f} A")
    print(f"    m1 = {vin/HWc.lm/1e6:.3f} A/us,  m2 = Sf = {sf_slope(vout)/1e6:.3f} A/us")
    print(f"    {'Se/Sf':>8}{'lambda(이론)':>14}{'lambda(측정)':>14}{'판정':>10}")
    lam = {}
    for r in (0.0, 0.20, 0.32, 0.60, 0.80):
        th = jacobian_theory(vin, vout, r)
        me = jacobian(vin, vout, cmd_of(r), r, i_nom)
        lam[r] = me
        print(f"    {r:8.2f}{th:14.3f}{me:14.3f}{'안정' if abs(me) < 1 else '발진':>10}")
    check("무보상(Se=0) 서브하모닉 발생", abs(lam[0.0]) > 1.0,
          f"|lambda| = {abs(lam[0.0]):.3f}", "> 1 (발진)")
    check("안정 경계 Se=0.32xSf 확인", abs(abs(lam[0.32]) - 1.0) < 0.05,
          f"|lambda| = {abs(lam[0.32]):.3f}", "= 1.0 (경계)")
    check("사양값(Se=0.6xSf) 안정", abs(lam[0.60]) < 0.60,
          f"|lambda| = {abs(lam[0.60]):.3f}", "< 0.6 (여유 확보)")
    check("이론식과 모델 일치", abs(lam[0.60] - jacobian_theory(vin, vout, 0.60)) < 0.02,
          f"오차 {abs(lam[0.60]-jacobian_theory(vin,vout,0.60)):.4f}", "< 0.02")

    # Se = 0.6 x Sf 가 전 듀티영역에서 무조건 안정인지 (Vin 스윕)
    worst = max(abs(jacobian_theory(v, 400.0, 0.60)) for v in (18, 24, 30, 36, 42, 50))
    check("전 입력범위 무조건 안정", worst < 1.0, f"max|lambda| = {worst:.3f}", "< 1.0")

    # 폐루프 듀티 지터 (MPPT 섭동 포함 - 안정성 지표가 아닌 품질 지표)
    tr, _, _ = run(PV_C, 0.100, se_ratio=0.60, decim=1)
    seg = tr["d"][int(len(tr["d"]) * 0.85):]
    jit = max(seg) - min(seg)
    print(f"    폐루프 듀티 지터(MPPT 섭동 포함) = {jit:.4f}")
    check("폐루프 듀티 지터", jit <= 0.03, f"{jit:.4f}", "<= 0.03")


# ---------------------------------------------------------- T6 환경 극한
def t6():
    hdr("T6. 환경 극한  (셀온도 -25 C 저온 Voc 상승 / +70 C 고온 Vmp 저하)")
    rows = []
    for tc in (-25.0, 25.0, 70.0):
        voc = 0.0
        lo, hi = 0.0, 2.0 * PV_A.voc0
        for _ in range(60):                      # I(V)=0 인 V 탐색
            mid = 0.5 * (lo + hi)
            if PV_A.current(mid, 1000.0, tc) > 1e-4:
                lo = mid
            else:
                hi = mid
        voc = 0.5 * (lo + hi)
        pm, vm, im = PV_A.mpp(1000.0, tc)
        rows.append((tc, voc, pm, vm))
        print(f"    T_cell {tc:+6.1f} C : Voc = {voc:5.2f} V,  MPP = {pm:6.1f} W @ {vm:5.2f} V")

    voc_cold = rows[0][1]
    vds_cold = voc_cold + vor(400.0)
    check("저온 Voc 시 MOSFET Vds", vds_cold <= 150.0 * 0.8,
          f"{vds_cold:.1f} V", "<= 120 V (150 V x 0.8)")
    check("저온 Voc 가 입력정격 50 V 이내", voc_cold <= 50.0,
          f"{voc_cold:.2f} V", "<= 50 V")
    check("패널 선정규칙 준수 (Voc STC)", PV_A.voc0 <= 50.0 / (1.0 + 0.0032 * 50.0),
          f"{PV_A.voc0:.1f} V", f"<= {50.0/(1.0+0.0032*50.0):.1f} V")

    tr, st, _ = run(PV_A, 0.120, tcell=70.0)
    pm70 = PV_A.mpp(1000.0, 70.0)[0]
    check("고온(70 C) MPPT 추종", tail_mean(tr["ppv"]) / pm70 >= 0.99,
          f"{100*tail_mean(tr['ppv'])/pm70:.2f} %", ">= 99 %")

    # 패널 선정 한계 : Voc(-25 C) <= 50 V 를 만족하는 Voc(STC) 상한
    voc_stc_max = 50.0 / (1.0 + 0.0032 * 50.0)
    print(f"    -> 입력정격 50 V 를 지키려면 패널 Voc(STC) <= {voc_stc_max:.1f} V 여야 함")
    return voc_stc_max


# ---------------------------------------------------------- T7 부분음영 다중 MPP
def substring_v(pvsub, i, irr, tcell=25.0):
    """서브스트링에 전류 i 가 흐를 때의 단자전압.  불가능하면 바이패스 다이오드(-0.7 V)."""
    if i >= pvsub.current(0.0, irr, tcell):
        return -0.7
    lo, hi = 0.0, 1.5 * pvsub.voc0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if pvsub.current(mid, irr, tcell) > i:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def t7():
    hdr("T7. 부분음영 다중 MPP  (모듈 2 서브스트링 + 바이패스 다이오드, 1000 / 250 W/m^2)")
    sub = PVModule("substring", 4.35, 22.8, 18.75, 4.00, 36)
    irr_a, irr_b = 1000.0, 250.0
    curve = []
    i_max = sub.current(0.0, irr_a)
    for k in range(1, 1201):
        i = i_max * k / 1200.0
        v = substring_v(sub, i, irr_a) + substring_v(sub, i, irr_b)
        if v > 0.5:
            curve.append((v, i, v * i))
    curve.sort()

    peaks = [j for j in range(1, len(curve) - 1)
             if curve[j][2] > curve[j - 1][2] and curve[j][2] >= curve[j + 1][2]]
    peaks = [curve[j] for j in peaks]
    # 근접 피크 병합
    merged = []
    for pk in sorted(peaks, key=lambda x: -x[2]):
        if all(abs(pk[0] - m[0]) > 2.0 for m in merged):
            merged.append(pk)
    merged.sort(key=lambda x: x[0])
    for v, i, pw in merged:
        print(f"    국부 MPP : {pw:6.1f} W @ {v:5.2f} V, {i:4.2f} A")
    gmpp = max(merged, key=lambda x: x[2])

    # 0.8 x Voc 에서 출발한 P&O 가 도달하는 국부 피크 (언덕오르기 추적)
    voc_arr = max(v for v, _, _ in curve)
    vstart = 0.80 * voc_arr
    idx = min(range(len(curve)), key=lambda j: abs(curve[j][0] - vstart))
    while True:
        nxt = None
        if idx + 1 < len(curve) and curve[idx + 1][2] > curve[idx][2]:
            nxt = idx + 1
        elif idx - 1 >= 0 and curve[idx - 1][2] > curve[idx][2]:
            nxt = idx - 1
        if nxt is None:
            break
        idx = nxt
    reached = curve[idx]
    print(f"    배열 Voc = {voc_arr:.2f} V,  P&O 기동점 0.8xVoc = {vstart:.2f} V")
    print(f"    P&O 도달점 = {reached[2]:.1f} W @ {reached[0]:.2f} V   |   "
          f"전역 MPP = {gmpp[2]:.1f} W @ {gmpp[0]:.2f} V")
    check("부분음영 시 다중 MPP 존재 확인", len(merged) >= 2,
          f"국부 MPP {len(merged)} 개", ">= 2")
    loss = 1.0 - reached[2] / gmpp[2]
    print(f"    [정적해석] 단순 P&O 만 쓰면 전역 MPP 대비 {100*loss:.1f} % 손실")
    check("부분음영 다봉 곡선에서 P&O 단독은 고착", loss > 0.02,
          f"손실 {100*loss:.1f} %", "> 2 % (전역스캔 필요성 확인)")

    # --- 전역 스캔을 켠 실제 동적 운전
    arr = ShadedArray(sub, irr_a, irr_b)
    tr, st, ctrl = run(arr, 0.250)
    p_dyn = tail_mean(tr["ppv"])
    print(f"    [동적검증] 전역스캔 ON : 추종 {p_dyn:.1f} W / 전역 MPP {gmpp[2]:.1f} W"
          f"  (Vpv = {tail_mean(tr['vpv']):.2f} V)")
    check("전역스캔 적용 시 전역 MPP 도달", p_dyn / gmpp[2] >= 0.97,
          f"{100*p_dyn/gmpp[2]:.1f} %", ">= 97 %")
    check("전역스캔 중 Ipk 안전", st["ipk_max"] <= HWc.ipk_ocp * 1.02,
          f"{st['ipk_max']:.2f} A", f"<= {HWc.ipk_ocp} A")
    return merged, gmpp, reached


# ---------------------------------------------------------- T8 입력전력 리미트
def t8():
    hdr("T8. 입력전력 리미트  (PV-D 220 W 오버사이징 패널 -> 정격 초과 인출 방지)")
    tr, st, _ = run(PV_D, 0.200)
    pmp = PV_D.mpp()[0]
    p_in = tail_mean(tr["ppv"])
    p_out = tail_mean(tr["pout"])
    print(f"    패널 가용 {pmp:.1f} W  ->  실제 인출 {p_in:.1f} W (리미트 {Ctrl.P_IN_MAX} W),"
          f"  출력 {p_out:.1f} W")
    print(f"    Vpv = {tail_mean(tr['vpv']):.2f} V (Vmp {PV_D.mpp()[1]:.2f} V 보다 높은 쪽),"
          f"  모드 = {tr['mode'][-1]}")
    check("입력전력 리미트 동작", abs(p_in - Ctrl.P_IN_MAX) <= 6.0,
          f"{p_in:.1f} W", f"{Ctrl.P_IN_MAX} +-6 W")
    check("출력이 정격 이내", p_out <= 158.0, f"{p_out:.1f} W", "<= 158 W")
    check("피크전류 설계값 이내", st["ipk_max"] <= HWc.ipk_ocp,
          f"{st['ipk_max']:.2f} A", f"<= {HWc.ipk_ocp} A")
    check("자속밀도 설계값 이내", b_peak(st["ipk_max"]) <= 0.30,
          f"{b_peak(st['ipk_max']):.3f} T", "<= 0.30 T")
    check("MPP 오른쪽(고전압측)에서 제한", tail_mean(tr["vpv"]) > PV_D.mpp()[1],
          f"{tail_mean(tr['vpv']):.2f} > {PV_D.mpp()[1]:.2f} V", "전류스트레스 저감 방향")
    return tr


# ---------------------------------------------------------- SVG 플롯
def svg_plot(path, panels, width=980, ph=170, pad_l=78, pad_r=18, pad_t=34, pad_b=48):
    """panels: [(title, ylabel, [(name, color, xs, ys)], ylim|None), ...]"""
    h = pad_t + len(panels) * (ph + pad_b)
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{h}" '
         f'viewBox="0 0 {width} {h}" font-family="ui-monospace,Menlo,monospace">',
         f'<rect width="{width}" height="{h}" fill="#ffffff"/>']
    for pi, (title, ylab, series, ylim) in enumerate(panels):
        y0 = pad_t + pi * (ph + pad_b)
        xs_all = [x for _, _, xs, _ in series for x in xs]
        ys_all = [y for _, _, _, ys in series for y in ys]
        xmin, xmax = min(xs_all), max(xs_all)
        if ylim:
            ymin, ymax = ylim
        else:
            ymin, ymax = min(ys_all), max(ys_all)
            m = (ymax - ymin) * 0.08 or 1.0
            ymin, ymax = ymin - m, ymax + m
        if ymax - ymin < 1e-9:
            ymax = ymin + 1.0
        raw = (ymax - ymin) / 4.0
        mag = 10 ** math.floor(math.log10(raw)) if raw > 0 else 1.0
        stepq = next((k * mag for k in (1, 2, 2.5, 5, 10) if k * mag >= raw), 10 * mag)
        ymin = math.floor(ymin / stepq) * stepq
        nt = max(2, int(math.ceil((ymax - ymin) / stepq - 1e-9)))
        ymax = ymin + nt * stepq
        sx = lambda v: pad_l + (v - xmin) / (xmax - xmin) * (width - pad_l - pad_r)
        sy = lambda v: y0 + ph - (v - ymin) / (ymax - ymin) * ph
        p.append(f'<rect x="{pad_l}" y="{y0}" width="{width-pad_l-pad_r}" height="{ph}" '
                 f'fill="#fbfbfd" stroke="#cbd5e1"/>')
        for k in range(nt + 1):
            gv = ymin + (ymax - ymin) * k / nt
            gy = sy(gv)
            p.append(f'<line x1="{pad_l}" y1="{gy:.1f}" x2="{width-pad_r}" y2="{gy:.1f}" '
                     f'stroke="#e5e7eb"/>')
            p.append(f'<text x="{pad_l-6}" y="{gy+4:.1f}" font-size="10" fill="#64748b" '
                     f'text-anchor="end">{gv:.4g}</text>')
        for k in range(6):
            gv = xmin + (xmax - xmin) * k / 5
            gx = sx(gv)
            p.append(f'<line x1="{gx:.1f}" y1="{y0}" x2="{gx:.1f}" y2="{y0+ph}" stroke="#e5e7eb"/>')
            p.append(f'<text x="{gx:.1f}" y="{y0+ph+14}" font-size="10" fill="#64748b" '
                     f'text-anchor="middle">{gv*1e3:.0f}</text>')
        p.append(f'<text x="{pad_l}" y="{y0-8}" font-size="12" fill="#0f172a" '
                 f'font-weight="700">{title}</text>')
        p.append(f'<text x="14" y="{y0+ph/2}" font-size="10" fill="#475569" '
                 f'transform="rotate(-90 14 {y0+ph/2})" text-anchor="middle">{ylab}</text>')
        p.append(f'<text x="{width-pad_r}" y="{y0-8}" font-size="10" fill="#64748b" '
                 f'text-anchor="end">t [ms]</text>')
        for si, (nm, col, xs, ys) in enumerate(series):
            pts = " ".join(f"{sx(x):.1f},{sy(y):.1f}" for x, y in zip(xs, ys))
            p.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="1.4"/>')
            lx = pad_l + 10 + si * 150
            p.append(f'<rect x="{lx}" y="{y0+7}" width="12" height="3" fill="{col}"/>')
            p.append(f'<text x="{lx+17}" y="{y0+13}" font-size="10" fill="#334155">{nm}</text>')
    p.append("</svg>")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(p))
    return path


def main():
    print("=" * 92)
    print(" PV 입력 액티브클램프 플라이백 (18-50 V / 400 V / 150 W) - 동작 검증")
    print("=" * 92)
    for pv in (PV_A, PV_B, PV_C, PV_D):
        pm, vm, im = pv.mpp()
        print(f"  {pv.name}")
        print(f"    Isc {pv.isc0} A / Voc {pv.voc0} V / MPP {pm:.1f} W @ {vm:.2f} V, {im:.2f} A"
              f"   (모델 피팅 오차 {pv.cost:.1e})")
    a = t1(); b = t2(); c = t3(); d = t4(); t5(); t6(); t7(); t8()

    svg_plot("docs/flyback-150w-400v/sim-t1-t2.svg", [
        ("T1  기동 + MPPT 수렴 (PV-A, 1000 W/m^2)", "V", [
            ("Vpv [V]", "#1d4ed8", a["t"], a["vpv"]),
            ("Vpv_ref [V]", "#0891b2", a["t"], a["ref"])], None),
        ("T1  PV 출력전력 vs 이론 MPP", "W", [
            ("Ppv [W]", "#1d4ed8", a["t"], a["ppv"]),
            ("Pmp 이론 [W]", "#dc2626", a["t"], a["pmp"])], (0, 170)),
        ("T2  일사량 1000 -> 400 -> 1000 W/m^2 추종", "W", [
            ("Ppv [W]", "#1d4ed8", b["t"], b["ppv"]),
            ("Pmp 이론 [W]", "#dc2626", b["t"], b["pmp"])], (0, 170)),
    ])
    svg_plot("docs/flyback-150w-400v/sim-t3-t4.svg", [
        ("T3  최악 코너 PV-C : 피크전류 / 듀티", "A , -", [
            ("Ipk [A]", "#1d4ed8", c["t"], c["ipk"]),
            ("Duty x10", "#0891b2", c["t"], [x * 10 for x in c["d"]])], (0, 18)),
        ("T3  PV-C 전력 추종 (입력 166.7 W @ 18.3 V)", "W", [
            ("Ppv [W]", "#1d4ed8", c["t"], c["ppv"]),
            ("Pmp 이론 [W]", "#dc2626", c["t"], c["pmp"])], (0, 180)),
        ("T4  출력 400 V 리미트 루프 동작", "V", [
            ("Vout [V]", "#1d4ed8", d["t"], d["vout"]),
            ("400 V 기준", "#dc2626", d["t"], [400.0] * len(d["t"]))], (0, 440)),
    ])

    print("\n" + "=" * 92)
    npass = sum(1 for _, ok, _, _ in RESULTS if ok)
    print(f" 종합 : {npass} / {len(RESULTS)} PASS")
    for nm, ok, val, crit in RESULTS:
        if not ok:
            print(f"   >>> FAIL : {nm} = {val} (기준 {crit})")
    print(" 파형 : sim-t1-t2.svg , sim-t3-t4.svg")
    print("=" * 92)
    return 0 if npass == len(RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
