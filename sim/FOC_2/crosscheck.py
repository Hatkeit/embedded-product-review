#!/usr/bin/env python3
"""FOC_2 PSIM 교차검증 — 동작점·손실·버스 전압을 Python으로 계산한다.

용도: PSIM 결과(psim-build-guide.md)와 같은 입력으로 같은 양을 계산해 비교 기준을 만든다.
의존성: numpy 만.

  python3 crosscheck.py                       # 기본 sweep, 결과를 crosscheck_results.md 로 저장
  python3 crosscheck.py --motor motor.json    # 모터 파라미터가 확정되면 dq 모델 FOC·회생 시뮬레이션 추가

표기 규율 (docs/01 과 동일)
  ✅ 데이터시트 원문   🔍 검색 확인(원문 대조 전)   🔢 유도   ❓ 미확인
  ❓ 값은 절대 추정값으로 채우지 않는다. 대신
    - sweep 변수로 두거나 (fsw, 데드타임, 버스 커패시턴스 …)
    - 선형 계수로 출력한다 (예: 다이오드 손실 [W/V], 오버랩 손실 [W/nC])
전류는 모두 상전류 RMS. 진폭 = RMS × √2.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

SQ2, SQ3 = math.sqrt(2), math.sqrt(3)

# ─────────────────────────────────────────────────────────────────────────────
# 1. 입력 파라미터 (plan.md §3 표와 1:1 대응. 바꿀 때는 양쪽을 같이 바꾼다)
# ─────────────────────────────────────────────────────────────────────────────

# 동작점 — docs/01 §1 (✅ Elmo MAN-G-TWI Ver. 2.011)
VDC_NOM = 85.0          # ✅
VDC_MAX = 95.0          # ✅
I_RMS = 35.3            # ✅ 연속 RMS 제한 Ic
P_CATALOG = 4000.0      # ✅
LOSS_BUDGET = 40.0      # 🔢 docs/01 §2.3


@dataclass
class Device:
    """MOSFET 파라미터. None = ❓ (데이터시트 원문에서 아직 못 읽음)."""
    name: str
    path: str
    vds: float                      # V
    rds25_max: float                # Ω, VGS=10 V, 25 °C max
    qg: float | None                # C, VGS=10 V typ
    qgd: float | None               # C, typ (측정 조건은 status 참조)
    vpl: float | None               # V, Miller plateau
    qoss: float | None              # C (측정 VDS 조건 ❓)
    qrr: float | None               # C (dI/dt 조건은 status 참조)
    rthjc: float | None             # K/W max
    vsd: float | None = None        # V, 바디 다이오드 순방향 (❓ 양쪽 다)
    rg_int: float | None = None     # Ω, 내부 게이트 저항 (❓ 양쪽 다)
    status: dict = field(default_factory=dict)


DEVICES = [
    Device(
        name="IPT017N12NM6", path="B (120 V Si)", vds=120, rds25_max=1.7e-3,
        qg=113e-9, qgd=25e-9, vpl=5.0, qoss=266e-9, qrr=301e-9, rthjc=0.38,
        status=dict(
            vds="🔍 DS Rev 2.0 Table 1 (검색 요약)", rds25_max="🔍 DS Rev 2.0 Table 1",
            qg="🔍 DS Rev 2.0 Table 1", qoss="🔍 DS Rev 2.0 Table 1 (VDS 조건 ❓)",
            qrr="🔍 DS Rev 2.0 Table 1, @1000 A/µs (IF·VR 조건 ❓)",
            qgd="🔍 검색 요약, typ 25 / max 38 nC @60 V, 75 A",
            vpl="🔍 검색 요약, 5.0 V", rthjc="🔍 제3자 DB(discoveree) 0.38 K/W max — 원문 미대조",
            vsd="❓", rg_int="❓ (형제 IPTC017N12NM6 typ 1.1 Ω — 다른 품번, 사용 안 함)",
        ),
    ),
    Device(
        name="IPT025N15NM6", path="C (150 V Si)", vds=150, rds25_max=2.5e-3,
        qg=105e-9, qgd=None, vpl=None, qoss=310e-9, qrr=184e-9, rthjc=None,
        status=dict(
            vds="🔍 DS Rev 2.0 (2024-04-16) Table 1", rds25_max="🔍 DS Rev 2.0 Table 1",
            qg="🔍 제품 페이지 typ @10 V. ⚠ docs/FOC_1 은 같은 Table 1 을 'Qg 310 / Qgd 105 nC' 로 읽음 — 원문 대조 필수",
            qoss="🔍 DS Rev 2.0 Table 1 (추출 텍스트 라벨 깨짐, 순서로 매칭) ⚠ 위와 같은 불일치",
            qrr="🔍 DS Rev 2.0 Table 1, @500 A/µs", qgd="❓", vpl="❓", rthjc="❓",
            vsd="❓", rg_int="❓",
        ),
    ),
]

# 게이트 드라이버 6ED2742S01Q — docs/02b §3.3
DRV_V = 12.0            # 🔍 차지펌프 게이트 전원
DRV_I_SRC = 1.0         # 🔍 소스 1 A
DRV_I_SNK = 2.0         # 🔍 싱크 2 A

# Rds(on) 온도 계수 — docs/01 §2.4 의 가정. 소자 곡선(❓)으로 대체할 때 이 값만 바꾼다.
RDS_TJ_FACTOR = 1.5

# ❓ 미정 → sweep
FSW_SWEEP = [20e3, 40e3, 60e3, 80e3, 100e3]     # Hz
TD_SWEEP = [50e-9, 100e-9, 200e-9, 500e-9]      # s
PF_SWEEP = [1.0, 0.95, 0.9, 0.8]
C_BUS_SWEEP = [100e-6, 220e-6, 470e-6, 1000e-6]  # F
SHUNT_R = 1e-3          # Ω — docs/01 §4 #3 의 "1 mΩ 가정"을 그대로 씀 (선정 전)

# 결과 표 기준 조건 (sweep 중 한 점을 대표로 보여줄 뿐, 선정값이 아님)
REF_FSW, REF_TD = 40e3, 100e-9


# ─────────────────────────────────────────────────────────────────────────────
# 2. 동작점
# ─────────────────────────────────────────────────────────────────────────────

def op_point(vdc: float, irms: float, pf: float, m_frac: float = 1.0) -> dict:
    """SVPWM 선형 한계(선간 피크 = Vdc)의 m_frac 배 전압에서의 동작점.

    m = Vph_pk / (Vdc/2). 선형 한계 m = 2/√3 = 1.1547.
    """
    vph_pk = m_frac * vdc / SQ3
    vph_rms = vph_pk / SQ2
    p = 3 * vph_rms * irms * pf
    return dict(vdc=vdc, irms=irms, ipk=irms * SQ2, pf=pf, m=vph_pk / (vdc / 2),
                vph_pk=vph_pk, vph_rms=vph_rms, vll_rms=vph_rms * SQ3, p_out=p)


# ─────────────────────────────────────────────────────────────────────────────
# 3. 해석식 손실 (닫힌 식) — PSIM과 시간영역 계산 양쪽의 기준
# ─────────────────────────────────────────────────────────────────────────────

def gate_currents(dev: Device, rg_ext: float = 0.0):
    """플래토 구간 게이트 전류. Rg_int ❓ 이면 드라이버 피크 전류로만 제한(=최선 경우)."""
    rg = rg_ext + (dev.rg_int or 0.0)
    if dev.vpl is None:
        return None, None
    ion = DRV_I_SRC if rg == 0 else min(DRV_I_SRC, (DRV_V - dev.vpl) / rg)
    ioff = DRV_I_SNK if rg == 0 else min(DRV_I_SNK, dev.vpl / rg)
    return ion, ioff


def overlap_time(dev: Device, rg_ext: float = 0.0):
    """전압 전이 시간 합 t_vf + t_vr = Qgd/Ig_on + Qgd/Ig_off.

    전류 전이(Qgs2 구간)는 Qgs2 ❓ 라서 빠짐 → 오버랩 손실은 하한이다.
    Qgd 는 데이터시트 측정 전압(60 V)의 값을 그대로 씀 (85/95 V 보정 안 함).
    """
    ion, ioff = gate_currents(dev, rg_ext)
    if dev.qgd is None or ion is None:
        return None
    return dev.qgd / ion + dev.qgd / ioff


def analytic_losses(dev: Device, op: dict, fsw: float, td: float, rg_ext: float = 0.0) -> dict:
    """인버터 전체(6 스위치) 손실. 동기 정류 가정(데드타임 외에는 채널 도통)."""
    ipk, irms, vdc, m, pf = op["ipk"], op["irms"], op["vdc"], op["m"], op["pf"]
    iabs = 2 * ipk / math.pi                       # 기본파 1주기 평균 |i|
    r = dev.rds25_max * RDS_TJ_FACTOR

    # 도통: 레그당 i²R × (1 − 2·td·fsw) — 데드타임 동안은 다이오드가 도통
    p_cond = 3 * irms**2 * r * (1 - 2 * td * fsw)
    # 데드타임 다이오드: 레그당 2·td·fsw·Vsd·|i|
    k_dt = 3 * 2 * td * fsw * iabs                 # [W/V]
    p_dt = k_dt * dev.vsd if dev.vsd is not None else None
    # 하드 스위칭 V-I 오버랩: 레그당 주기마다 하드 턴온 1회 + 턴오프 1회
    k_ov = 3 * fsw * 0.5 * vdc * iabs              # [W/s] × (t_on+t_off)
    t_ov = overlap_time(dev, rg_ext)
    p_ov = k_ov * t_ov if t_ov is not None else None
    # Qoss·Vdc, Qrr·Vdc: 레그당 주기마다 1회 (하드 턴온)
    p_qoss = 3 * fsw * dev.qoss * vdc if dev.qoss is not None else None
    p_qrr = 3 * fsw * dev.qrr * vdc if dev.qrr is not None else None
    p_gate = 6 * fsw * dev.qg * DRV_V if dev.qg is not None else None  # Qg@10V × 12 V → 하한

    # 하단 션트: 동기 정류라 양방향 전류가 (1−d) 동안 흐름 → ∫(1−d)·i² = Irms²/2.
    # (1−d) 의 기본파·영상분(홀수 고조파)은 i²(0·2차)와 직교 → m·PF 무관.
    # (IGBT 반주기 식 Ipk²(1/8 − m·cosφ/3π) 는 여기 해당 안 됨)
    i_low_rms2 = irms**2 / 2
    p_sh_low = 3 * i_low_rms2 * SHUNT_R
    p_sh_inline = 3 * irms**2 * SHUNT_R

    parts = dict(cond=p_cond, dt=p_dt, overlap=p_ov, qoss=p_qoss, qrr=p_qrr, gate=p_gate)
    known = [v for v in parts.values() if v is not None]
    return dict(
        **parts, k_dt_per_V=k_dt, k_ov_per_nC=(k_ov * (1 / DRV_I_SRC + 1 / DRV_I_SNK) * 1e-9),
        shunt_low=p_sh_low, shunt_inline=p_sh_inline, i_low_rms=math.sqrt(i_low_rms2),
        total_known=sum(known), complete=len(known) == len(parts),
        i_fet_rms=irms / SQ2, r_tj=r,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 4. 시간영역 계산 — 스위칭 주기 단위로 SVPWM 듀티를 만들어 손실·전류를 적분
#    (해석식의 가정을 독립적으로 확인. PSIM 파형과 같은 정의로 RMS 계산)
# ─────────────────────────────────────────────────────────────────────────────

def svpwm_duty(v_abc: np.ndarray, vdc: float) -> np.ndarray:
    """min-max 영상분 주입 SVPWM. v_abc shape (3, N) → duty (3, N)."""
    v0 = -(v_abc.max(axis=0) + v_abc.min(axis=0)) / 2
    return np.clip(0.5 + (v_abc + v0) / vdc, 0.0, 1.0)


def time_domain(dev: Device, op: dict, fsw: float, td: float, fe: float = 100.0,
                cycles: int = 1, rg_ext: float = 0.0, vsd: float = 1.0) -> dict:
    """정현 전류원 부하. 주기 평균 상태로 레그별·소자별 손실을 누적.

    vsd 가 ❓ 이면 1 V 로 계산 → 결과의 dt 항은 [W/V] 계수로 읽는다.
    """
    n = int(round(fsw / fe)) * cycles
    th = 2 * math.pi * fe * (np.arange(n) + 0.5) / fsw
    phi = math.acos(max(-1.0, min(1.0, op["pf"])))   # PF < 0 → 회생 (전류가 전압과 반대 방향)
    sh = np.array([0, -2 * math.pi / 3, 2 * math.pi / 3])[:, None]
    v = op["vph_pk"] * np.cos(th + sh)
    i = op["ipk"] * np.cos(th + sh - phi)
    d = svpwm_duty(v, op["vdc"])
    r = dev.rds25_max * RDS_TJ_FACTOR
    tdf = td * fsw
    pos = i > 0

    # 데드타임은 양쪽 턴온 엣지를 td 지연시켜 삽입 → 상·하단 채널 모두 주기당 td 씩 짧아짐
    hi = dict(cond=np.clip(d - tdf, 0, None) * i**2 * r)
    lo = dict(cond=np.clip(1 - d - tdf, 0, None) * i**2 * r)
    # 다이오드: i>0 이면 하단 바디 다이오드가 두 데드타임 모두 도통
    hi["dt"] = np.where(~pos, 2 * tdf * vsd * np.abs(i), 0.0)
    lo["dt"] = np.where(pos, 2 * tdf * vsd * np.abs(i), 0.0)
    t_ov = overlap_time(dev, rg_ext) or 0.0
    e_sw = 0.5 * op["vdc"] * np.abs(i) * t_ov + ((dev.qoss or 0) + (dev.qrr or 0)) * op["vdc"]
    hi["sw"] = np.where(pos, e_sw * fsw, 0.0)     # i>0: 상단이 하드 스위칭
    lo["sw"] = np.where(~pos, e_sw * fsw, 0.0)

    # 인버터 입력(DC 링크) 전류: 중앙정렬 PWM 한 주기 안의 상태 구간으로 정확히 계산
    order = np.argsort(-d, axis=0)
    ds = np.take_along_axis(d, order, axis=0)
    is_ = np.take_along_axis(i, order, axis=0)
    ds4 = np.vstack([ds, np.zeros((1, n))])
    w = ds4[:-1] - ds4[1:]                         # 상위 k개 레그만 ON인 시간 비율
    cum = np.cumsum(is_, axis=0)
    idc_avg_T = (w * cum).sum(axis=0)
    idc_ms_T = (w * cum**2).sum(axis=0)
    idc_avg = idc_avg_T.mean()
    idc_rms = math.sqrt(idc_ms_T.mean())

    i_low_ms = ((1 - d) * i**2).mean(axis=1)       # 하단 션트 (상별)
    per_dev = {k: (hi[k].mean(axis=1), lo[k].mean(axis=1)) for k in hi}
    total = {k: float(sum(a.sum() + b.sum() for a, b in [per_dev[k]])) for k in per_dev}
    worst_dev = max(float(per_dev["cond"][0][0] + per_dev["dt"][0][0] + per_dev["sw"][0][0]),
                    float(per_dev["cond"][1][0] + per_dev["dt"][1][0] + per_dev["sw"][1][0]))
    return dict(
        cond=total["cond"], dt_per_V=total["dt"] / vsd, sw=total["sw"],
        idc_avg=idc_avg, idc_rms=idc_rms, icap_rms=math.sqrt(max(idc_rms**2 - idc_avg**2, 0)),
        p_dc=idc_avg * op["vdc"], i_low_rms=float(np.sqrt(i_low_ms.mean())),
        p_shunt_low=float(i_low_ms.sum() * SHUNT_R), p_shunt_dc=idc_rms**2 * SHUNT_R,
        p_per_device_max=worst_dev, d_min=float(d.min()), d_max=float(d.max()),
    )


def stall_losses(dev: Device, irms: float, fsw: float, td: float, vdc: float, vsd: float = 1.0) -> dict:
    """정지(fe = 0)·전기각이 A상 피크에 고정된 최악 경우. 듀티 ≈ 0.5 (m ≈ 0).

    i = [Ipk, −Ipk/2, −Ipk/2] (DC). docs/FOC_1 design-review R5 와 같은 조건.
    반환: 소자별 최대 손실과 회전 중(1주기 평균) 소자 1개 손실의 비.
    """
    ipk = irms * SQ2
    i = np.array([ipk, -ipk / 2, -ipk / 2])
    d = 0.5
    r = dev.rds25_max * RDS_TJ_FACTOR
    tdf = td * fsw
    t_ov = overlap_time(dev) or 0.0
    e_sw = 0.5 * vdc * np.abs(i) * t_ov + ((dev.qoss or 0) + (dev.qrr or 0)) * vdc
    pos = i > 0
    hi = (d - tdf) * i**2 * r + np.where(~pos, 2 * tdf * vsd * np.abs(i), 0) + np.where(pos, e_sw * fsw, 0)
    lo = (1 - d - tdf) * i**2 * r + np.where(pos, 2 * tdf * vsd * np.abs(i), 0) + np.where(~pos, e_sw * fsw, 0)
    rot = time_domain(dev, op_point(vdc, irms, 1.0), fsw, td, vsd=vsd)
    worst = float(max(hi.max(), lo.max()))
    return dict(worst=worst, total=float(hi.sum() + lo.sum()), rot_dev=rot["p_per_device_max"],
                ratio=worst / rot["p_per_device_max"],
                cond_worst=float(((d - tdf) * i**2 * r).max()), cond_rot=rot["cond"] / 6)


# ─────────────────────────────────────────────────────────────────────────────
# 5. 데드타임 전압 오차, 회생 버스 전압
# ─────────────────────────────────────────────────────────────────────────────

def deadtime_voltage(op: dict, fsw: float, td: float) -> dict:
    """레그 평균전압 오차 ±td·fsw·Vdc (전류 부호), 기본파 피크 = 4/π 배."""
    dv = td * fsw * op["vdc"]
    v1 = 4 / math.pi * dv
    return dict(dv_leg=dv, v1_pk=v1, ratio=v1 / op["vph_pk"])


def regen_capacitor(c: float, v0: float, vlim: float) -> float:
    """V0→Vlim 사이에서 버스 커패시터가 흡수할 수 있는 에너지 [J]."""
    return 0.5 * c * (vlim**2 - v0**2)


def regen_dvdt(c: float, v: float, p: float) -> float:
    """공급이 전류를 받지 못할 때(단방향 전원) 회생 전력 p 에 의한 dV/dt [V/s]."""
    return p / (c * v)


# ─────────────────────────────────────────────────────────────────────────────
# 6. (선택) 모터 dq 모델 + PI 전류 루프 + 회생 제동 — 모터 파라미터 확정 후에만
# ─────────────────────────────────────────────────────────────────────────────

MOTOR_KEYS = ["Rs", "Ld", "Lq", "pole_pairs", "psi_pm", "J", "omega_m0", "iq_motoring",
              "iq_braking", "bw_current_hz", "C_bus", "V_supply", "R_supply",
              "V_chop_on", "V_chop_off", "R_brake", "fsw", "td", "t_end"]


def foc_sim(mp: dict) -> dict:
    """평균화 dq 모델. 1 Ts 연산 지연, 데드타임 전압 오차, 전압 원 제한, 버스 커패시터,
    단방향 공급(다이오드), 히스테리시스 제동 초퍼를 포함한다.
    0 ~ t_end/2 : iq_motoring 으로 정속 유지(TL = 부하 토크로 평형), 이후 iq_braking 으로 제동.
    """
    missing = [k for k in MOTOR_KEYS if mp.get(k) is None]
    if missing:
        raise ValueError(f"❓ 모터/시스템 파라미터 미입력: {missing}")
    Rs, Ld, Lq, pp, psi = mp["Rs"], mp["Ld"], mp["Lq"], mp["pole_pairs"], mp["psi_pm"]
    J, fsw, td = mp["J"], mp["fsw"], mp["td"]
    Ts = 1 / fsw
    wc = 2 * math.pi * mp["bw_current_hz"]
    kp_d, ki_d, kp_q, ki_q = Ld * wc, Rs * wc, Lq * wc, Rs * wc
    sub = 10
    dt = Ts / sub
    steps = int(mp["t_end"] / Ts)
    id_ = iq = 0.0
    wm = mp["omega_m0"]
    vbus = mp["V_supply"]
    xi_d = xi_q = 0.0
    vd_cmd = vq_cmd = 0.0
    chop = False
    TL = 1.5 * pp * psi * mp["iq_motoring"]        # 정속 평형 부하 토크
    log = dict(t=[], vbus=[], wm=[], id=[], iq=[], p_chop=[])
    e_chop = 0.0
    for k in range(steps):
        t = k * Ts
        iq_ref = mp["iq_motoring"] if t < mp["t_end"] / 2 else mp["iq_braking"]
        tl = TL if t < mp["t_end"] / 2 else 0.0
        we = pp * wm
        # PI (전향 보상 포함), 이번 주기 계산 → 다음 주기 인가 (1 Ts 지연)
        ed, eq = 0.0 - id_, iq_ref - iq
        vd_new = kp_d * ed + xi_d - we * Lq * iq
        vq_new = kp_q * eq + xi_q + we * (Ld * id_ + psi)
        vmax = vbus / SQ3
        mag = math.hypot(vd_new, vq_new)
        if mag > vmax:
            vd_new, vq_new = vd_new * vmax / mag, vq_new * vmax / mag
        else:
            xi_d += ki_d * ed * Ts
            xi_q += ki_q * eq * Ts
        vd_app, vq_app = vd_cmd, vq_cmd
        vd_cmd, vq_cmd = vd_new, vq_new
        for _ in range(sub):
            # 데드타임 오차: abc 에서 −sign(i)·td·fsw·Vdc → dq (전류 벡터 방향 근사)
            ia_mag = math.hypot(id_, iq)
            dv = 4 / math.pi * td * fsw * vbus
            ed_dt = -dv * id_ / ia_mag if ia_mag > 1e-3 else 0.0
            eq_dt = -dv * iq / ia_mag if ia_mag > 1e-3 else 0.0
            vd, vq = vd_app + ed_dt, vq_app + eq_dt
            did = (vd - Rs * id_ + we * Lq * iq) / Ld
            diq = (vq - Rs * iq - we * (Ld * id_ + psi)) / Lq
            te = 1.5 * pp * (psi * iq + (Ld - Lq) * id_ * iq)
            p_inv = 1.5 * (vd_app * id_ + vq_app * iq)   # 인버터 무손실 근사
            i_sup = max(0.0, (mp["V_supply"] - vbus) / mp["R_supply"])
            if vbus > mp["V_chop_on"]:
                chop = True
            elif vbus < mp["V_chop_off"]:
                chop = False
            i_ch = vbus / mp["R_brake"] if chop else 0.0
            e_chop += vbus * i_ch * dt
            vbus += (i_sup - p_inv / vbus - i_ch) / mp["C_bus"] * dt
            id_ += did * dt
            iq += diq * dt
            wm += (te - tl) / J * dt
            wm = max(wm, 0.0)
        log["t"].append(t)
        log["vbus"].append(vbus)
        log["wm"].append(wm)
        log["id"].append(id_)
        log["iq"].append(iq)
    vb = np.array(log["vbus"])
    return dict(vbus_max=float(vb.max()), vbus_min=float(vb.min()), e_chop=e_chop,
                wm_end=log["wm"][-1], iq_end=log["iq"][-1])


# ─────────────────────────────────────────────────────────────────────────────
# 7. 리포트
# ─────────────────────────────────────────────────────────────────────────────

def f(x, nd=2, unit=""):
    return "❓" if x is None else f"{x:.{nd}f}{unit}"


def report(motor: dict | None) -> str:
    L = []
    w = L.append
    w("# FOC_2 Python 교차검증 결과 (자동 생성)\n")
    w("`python3 crosscheck.py` 로 생성. 손으로 고치지 말 것 — 입력은 `crosscheck.py` §1.\n")
    w(f"공통 가정: Rds(on)@Tj = Rds25,max × {RDS_TJ_FACTOR} (docs/01 §2.4 가정), "
      f"게이트 {DRV_V:.0f} V · 소스 {DRV_I_SRC:.0f} A / 싱크 {DRV_I_SNK:.0f} A (🔍 6ED2742S01Q), "
      f"Rg_ext = 0 · Rg_int ❓ → **스위칭 손실은 드라이버 전류 한계만 반영한 하한**. "
      f"션트 {SHUNT_R*1e3:.0f} mΩ (docs/01 §4 #3 가정).\n")

    # 7.1 동작점
    w("## 1. 동작점 🔢\n")
    w("| 케이스 | Vdc | I (RMS / 진폭) | PF | m | V상 RMS | V선간 RMS | P_out | 4.0 kW 대비 |")
    w("|---|---|---|---|---|---|---|---|---|")
    ops = {
        "OP1 공칭·선형한계": op_point(VDC_NOM, I_RMS, 1.0),
        "OP2 최대·선형한계": op_point(VDC_MAX, I_RMS, 1.0),
        "OP3 공칭·Elmo 96 %": op_point(VDC_NOM, I_RMS, 1.0, 0.96),
        "OP4 최대·Elmo 96 %": op_point(VDC_MAX, I_RMS, 1.0, 0.96),
        "OP5 저속 (m 5 %)": op_point(VDC_NOM, I_RMS, 1.0, 0.05),
        "OP6 회생 (PF −1)": op_point(VDC_NOM, I_RMS, -1.0),
    }
    for k, o in ops.items():
        w(f"| {k} | {o['vdc']:.0f} V | {o['irms']:.1f} / {o['ipk']:.1f} A | {o['pf']:.2f} | "
          f"{o['m']:.3f} | {o['vph_rms']:.2f} V | {o['vll_rms']:.2f} V | {o['p_out']:.0f} W | "
          f"{o['p_out']/P_CATALOG*100:.1f} % |")
    o2 = ops["OP2 최대·선형한계"]
    pf_need = P_CATALOG / (3 * o2["vph_rms"] * I_RMS)
    w(f"\n- 95 V·선형한계에서 4.0 kW 에 필요한 역률: **{pf_need:.3f}** "
      f"(= 4000 / {3*o2['vph_rms']*I_RMS:.0f}). 공칭 85 V 로는 PF 1.0 에서도 "
      f"{ops['OP1 공칭·선형한계']['p_out']:.0f} W (docs/01 §2.2 와 일치해야 함).")
    w("- 'Elmo 96 %' 는 원문 '최대 출력 전압 = DC 버스의 96 %' 를 선간 피크 = 0.96·Vdc 로 해석한 경우. "
      "해석 자체가 ❓ (선간 RMS 기준일 수도 있음).\n")

    # 7.2 손실 — 기준점
    w(f"## 2. 인버터 손실 — OP1 (85 V, 35.3 A RMS, PF 1), fsw {REF_FSW/1e3:.0f} kHz, td {REF_TD*1e9:.0f} ns 🔢\n")
    w("fsw·td 는 **선정값이 아니라 표시용 기준점**. 전체는 §3 sweep.\n")
    w("| 항목 | " + " | ".join(f"{d.path} {d.name}" for d in DEVICES) + " |")
    w("|---|" + "---|" * len(DEVICES))
    op = ops["OP1 공칭·선형한계"]
    an = [analytic_losses(d, op, REF_FSW, REF_TD) for d in DEVICES]
    td_ = [time_domain(d, op, REF_FSW, REF_TD) for d in DEVICES]
    rows = [
        ("스위치 RMS 전류 (A)", [f(a["i_fet_rms"]) for a in an]),
        ("Rds(on)@Tj (mΩ)", [f(a["r_tj"] * 1e3, 3) for a in an]),
        ("도통 (W) — 해석식", [f(a["cond"]) for a in an]),
        ("도통 (W) — 시간영역", [f(t["cond"]) for t in td_]),
        ("V-I 오버랩 (W)", [f(a["overlap"]) for a in an]),
        ("  └ 계수 (W per nC Qgd)", [f(a["k_ov_per_nC"], 3) for a in an]),
        ("Qoss·Vdc (W)", [f(a["qoss"]) for a in an]),
        ("Qrr·Vdc (W)", [f(a["qrr"]) for a in an]),
        ("스위칭 합 (W) — 시간영역", [f(t["sw"]) if a["overlap"] is not None else "❓ (Qgd)" for a, t in zip(an, td_)]),
        ("게이트 구동 (W)", [f(a["gate"], 3) for a in an]),
        ("데드타임 다이오드 (W)", [f(a["dt"]) for a in an]),
        ("  └ 계수 (W per V Vsd) 해석/시간영역", [f"{a['k_dt_per_V']:.3f} / {t['dt_per_V']:.3f}" for a, t in zip(an, td_)]),
        ("**알려진 항목 합 (W)**", [f"**{a['total_known']:.2f}**" + ("" if a["complete"] else " + ❓") for a in an]),
        ("40 W 예산 대비", [f"{a['total_known']/LOSS_BUDGET*100:.1f} %" + ("" if a["complete"] else " + ❓") for a in an]),
        ("최대 손실 소자 1개 (W, Vsd 1 V)", [f(t["p_per_device_max"]) for t in td_]),
    ]
    for name, vals in rows:
        w(f"| {name} | " + " | ".join(vals) + " |")
    t0 = td_[0]
    w("\n**션트·DC 링크 (소자 무관, OP1)**\n")
    w("| 항목 | 해석식 | 시간영역 |")
    w("|---|---|---|")
    w(f"| 하단 션트 전류 RMS (상당) | {an[0]['i_low_rms']:.2f} A | {t0['i_low_rms']:.2f} A |")
    w(f"| 하단 션트 3개 손실 | {an[0]['shunt_low']:.3f} W | {t0['p_shunt_low']:.3f} W |")
    w(f"| 인라인 션트 3개 손실 | {an[0]['shunt_inline']:.3f} W | — |")
    w(f"| DC 링크 단일 션트 손실 | — | {t0['p_shunt_dc']:.3f} W |")
    w(f"| DC 입력 전류 평균 | {op['p_out']/op['vdc']:.2f} A (무손실) | {t0['idc_avg']:.2f} A |")
    w(f"| DC 링크 전류 RMS | — | {t0['idc_rms']:.2f} A |")
    w(f"| **버스 커패시터 리플 전류 RMS** | — | **{t0['icap_rms']:.2f} A** |")
    w(f"| 듀티 범위 | — | {t0['d_min']:.3f} – {t0['d_max']:.3f} |")
    w("\n- docs/01 §4 #3 의 '3 × 25² × 1 mΩ = 1.9 W' 와 일치. 동기 정류에서는 하단 션트 RMS = I/√2 로 "
      "m·PF 와 무관하다 (데드타임 중 하단 다이오드 전류는 무시 — 오차 2·td·fsw 이하).\n")

    w("### 하단 션트 샘플링 창이 변조 한계를 줄이는 양 (85 V, PF 1) 🔢\n")
    w("SVPWM 최대 듀티 d_max = ½ + (√3/4)·m. 하단 ON 시간 ≥ t_min 을 요구하면 "
      "d_max = 1 − t_min·fsw → m_max = (d_max − ½)·4/√3. t_min (ADC 샘플+정착, 드라이버 지연) ❓ → sweep. "
      "**1상 기준(보수적)** — 2상 전류로 3상째를 재구성하면 완화된다.\n")
    w("| fsw \\ t_min | 0.5 µs | 1 µs | 2 µs |")
    w("|---|---|---|---|")
    for fs in FSW_SWEEP:
        cells = []
        for tm in [0.5e-6, 1e-6, 2e-6]:
            dmax = 1 - tm * fs
            mmax = min((dmax - 0.5) * 4 / SQ3, 2 / SQ3)
            pmax = 3 * (mmax * VDC_NOM / 2) / SQ2 * I_RMS
            cells.append(f"m {mmax:.3f} → {pmax:.0f} W")
        w(f"| {fs/1e3:.0f} kHz | " + " | ".join(cells) + " |")
    w("")

    w("### 정지 상태 (fe = 0, A상 피크 고정, 85 V) — docs/FOC_1 R5 🔢\n")
    w("| 소자 | 도통: 정지 최악 소자 / 회전 평균 소자 | 전체(도통+다이오드 1 V+스위칭) 최악 소자 | 회전 중 최악 소자 | 비 | 인버터 총합 (정지) |")
    w("|---|---|---|---|---|---|")
    for d in DEVICES:
        st = stall_losses(d, I_RMS, REF_FSW, REF_TD, VDC_NOM)
        note = "" if d.qgd else " (오버랩 ❓ 제외)"
        w(f"| {d.name} | {st['cond_worst']:.2f} / {st['cond_rot']:.2f} W ({st['cond_worst']/st['cond_rot']:.2f}×) | "
          f"{st['worst']:.2f} W{note} | {st['rot_dev']:.2f} W | {st['ratio']:.2f}× | {st['total']:.2f} W |")
    w("\n도통만 보면 정확히 2.0× (FOC_1 R5 와 일치). 스위칭 손실은 더 나쁘다 — 레그의 하드 스위칭이 "
      "한 소자(A상 상단)에 전부 몰리고(회전 중에는 상·하단이 반주기씩 나눔), 오버랩 항은 |i| 가 피크로 고정된다. "
      "열 설계·PSIM S2 는 이 케이스를 별도로 돌린다.\n")

    # 7.3 sweep
    w("## 3. Sweep — 알려진 손실 합 (W), OP1 기준 🔢\n")
    for d in DEVICES:
        w(f"### {d.path} {d.name}\n")
        w("| fsw \\ td | " + " | ".join(f"{t*1e9:.0f} ns" for t in TD_SWEEP) + " |")
        w("|---|" + "---|" * len(TD_SWEEP))
        for fs in FSW_SWEEP:
            cells = []
            for tdv in TD_SWEEP:
                a = analytic_losses(d, op, fs, tdv)
                extra = a["k_dt_per_V"]
                cells.append(f"{a['total_known']:.1f} + {extra:.2f}·Vsd" + ("" if d.qgd else " + ❓"))
            w(f"| {fs/1e3:.0f} kHz | " + " | ".join(cells) + " |")
        w("")
    w("`+ x·Vsd` = 데드타임 다이오드 손실 (Vsd ❓, 단위 V). `+ ❓` = Qgd ❓ 로 V-I 오버랩 미포함.\n")

    w("### 동작점별 (fsw 40 kHz, td 100 ns, 경로 B)\n")
    w("| 동작점 | P_out | 손실 합 (+ Vsd 항) | η (알려진 항목만) | 하단 션트 3개 | 커패시터 리플 RMS |")
    w("|---|---|---|---|---|---|")
    for k, o in ops.items():
        a = analytic_losses(DEVICES[0], o, REF_FSW, REF_TD)
        t = time_domain(DEVICES[0], o, REF_FSW, REF_TD)
        pin = abs(o["p_out"]) + a["total_known"]
        eta = abs(o["p_out"]) / pin * 100 if o["pf"] > 0 else float("nan")
        w(f"| {k} | {o['p_out']:.0f} W | {a['total_known']:.2f} + {a['k_dt_per_V']:.2f}·Vsd W | "
          f"{'—' if math.isnan(eta) else f'{eta:.2f} %'} | {t['p_shunt_low']:.3f} W | {t['icap_rms']:.2f} A |")
    w("")
    w("### 역률 sweep (85 V, 선형한계, 경로 B, 40 kHz/100 ns)\n")
    w("| PF | P_out | 하단 션트 3개 | 커패시터 리플 RMS |")
    w("|---|---|---|---|")
    for pf in PF_SWEEP:
        o = op_point(VDC_NOM, I_RMS, pf)
        t = time_domain(DEVICES[0], o, REF_FSW, REF_TD)
        w(f"| {pf:.2f} | {o['p_out']:.0f} W | {t['p_shunt_low']:.3f} W | {t['icap_rms']:.2f} A |")
    w("\n도통·스위칭 손실은 동기 정류에서 PF·m 와 무관 (모든 행이 같은 값) — PSIM 에서 확인할 항목.\n")

    # 7.4 dead time
    w("## 4. 데드타임 전압 오차 (OP1) 🔢\n")
    w("| fsw \\ td | " + " | ".join(f"{t*1e9:.0f} ns" for t in TD_SWEEP) + " |")
    w("|---|" + "---|" * len(TD_SWEEP))
    for fs in FSW_SWEEP:
        cells = []
        for tdv in TD_SWEEP:
            r = deadtime_voltage(op, fs, tdv)
            cells.append(f"{r['v1_pk']:.2f} V ({r['ratio']*100:.1f} %)")
        w(f"| {fs/1e3:.0f} kHz | " + " | ".join(cells) + " |")
    w("\n값 = 기본파 오차 피크 (4/π)·td·fsw·Vdc, 괄호는 상전압 피크 대비. 6스텝 형태의 5·7차 고조파 전류를 만든다.\n")

    # 7.5 regen
    w("## 5. 회생 제동 — 버스 전압 상승 🔢\n")
    w("소자 전압 한계: docs/02 §2.2 의 80 % 디레이팅 → 120 V 소자 96 V, 150 V 소자 120 V. "
      "오버슈트 여유를 따로 빼지 않은 값이라 실제 허용 상승은 더 작다.\n")
    w("### 커패시터 흡수 가능 에너지 [J] (초퍼 없이)\n")
    w("| C_bus | 85→96 V (B) | 95→96 V (B) | 85→120 V (C) | 95→120 V (C) |")
    w("|---|---|---|---|---|")
    for c in C_BUS_SWEEP:
        w(f"| {c*1e6:.0f} µF | {regen_capacitor(c,85,96):.3f} | {regen_capacitor(c,95,96):.3f} | "
          f"{regen_capacitor(c,85,120):.3f} | {regen_capacitor(c,95,120):.3f} |")
    p_reg = ops["OP6 회생 (PF −1)"]["p_out"]
    w(f"\n### 정격 회생 전력 {abs(p_reg):.0f} W 가 단방향 전원 버스로 들어올 때 dV/dt\n")
    w("| C_bus | dV/dt @85 V | 85→96 V 도달 시간 | 85→120 V 도달 시간 |")
    w("|---|---|---|---|")
    for c in C_BUS_SWEEP:
        dvdt = regen_dvdt(c, 85, abs(p_reg))
        t96 = regen_capacitor(c, 85, 96) / abs(p_reg)
        t120 = regen_capacitor(c, 85, 120) / abs(p_reg)
        w(f"| {c*1e6:.0f} µF | {dvdt/1e3:.1f} V/ms | {t96*1e3:.2f} ms | {t120*1e3:.2f} ms |")
    w("\n- 경로 B 를 95 V 공급에서 쓰면 커패시터가 흡수할 여유는 1 V 뿐이다 → **초퍼 임계 ≈ 공급 최대 전압 직상**, "
      "또는 FW 버스전압 제한(회생 iq 제한)이 필수. 경로 C 는 같은 C 로 3.6배(85 V 시작) ~ 28배(95 V 시작) 흡수.")
    w("- 실제 회생 에너지 = 관성·속도로 정해짐 (J ❓, ω ❓) → 모터 사양 입력 후 §6 시뮬레이션.\n")

    # 7.6 motor sim
    w("## 6. 모터 dq 모델 FOC·회생 시뮬레이션\n")
    if motor is None:
        w("❓ 미실행 — 모터 파라미터 없음. `motor_params.template.json` 을 채워 "
          "`python3 crosscheck.py --motor motor.json` 로 실행.\n")
    else:
        r = foc_sim(motor)
        w(f"입력: `{motor.get('_file','')}`\n")
        w("| 항목 | 값 |")
        w("|---|---|")
        w(f"| 버스 전압 최대 | {r['vbus_max']:.2f} V |")
        w(f"| 버스 전압 최소 | {r['vbus_min']:.2f} V |")
        w(f"| 초퍼 소산 에너지 | {r['e_chop']:.3f} J |")
        w(f"| 종료 시 기계 속도 | {r['wm_end']:.1f} rad/s |")
        w("")

    # 7.7 PSIM 비교 체크 표
    w(f"## 7. PSIM 비교 체크 표 — OP1, fsw {REF_FSW/1e3:.0f} kHz, td {REF_TD*1e9:.0f} ns\n")
    w("PSIM 열은 사용자가 채운다. 판정 기준은 plan.md §5. 소자 1개 값은 A상 상단(S1) 기준.\n")
    w("| # | 항목 | 단위 | Python | PSIM | 차이 % | 판정 기준 |")
    w("|---|---|---|---|---|---|---|")
    vdt = deadtime_voltage(op, REF_FSW, REF_TD)
    rows = [
        ("E1", "상전압 기본파 RMS", "V", f"{op['vph_rms']:.2f}", "±1 %"),
        ("E2", "상전류 RMS / 진폭", "A", f"{op['irms']:.2f} / {op['ipk']:.2f}", "±1 %"),
        ("E3", "출력 전력 (3상 합)", "W", f"{op['p_out']:.0f}", "±2 %"),
        ("E4", "스위치 1개 RMS 전류", "A", f"{an[0]['i_fet_rms']:.2f}", "±2 %"),
        ("E5", "DC 입력 전류 평균 (무손실)", "A", f"{t0['idc_avg']:.2f}", "±2 % (손실분 보정 후)"),
        ("E6", "버스 커패시터 리플 RMS", "A", f"{t0['icap_rms']:.2f}", "±5 %"),
        ("E7", "하단 션트 전류 RMS (1상)", "A", f"{t0['i_low_rms']:.2f}", "±2 %"),
        ("E8", "하단 션트 3개 손실", "W", f"{t0['p_shunt_low']:.3f}", "±5 %"),
        ("E9", "데드타임 기본파 전압 오차 피크", "V", f"{vdt['v1_pk']:.2f}", "±20 % (PSIM 은 Coss 충방전으로 실효 데드타임이 줄어듦)"),
    ]
    for d, a, t in zip(DEVICES, an, td_):
        tag = d.path.split()[0]
        sw = f"{t['sw']/6:.3f}" if a["overlap"] is not None else "❓ (Qgd)"
        swt = f"{t['sw']:.2f}" if a["overlap"] is not None else "❓ (Qgd)"
        rows += [
            (f"{tag}1", f"{d.name} 도통 손실, 소자 1개", "W", f"{a['cond']/6:.3f}", "±5 % (같은 Rds@Tj 입력 시)"),
            (f"{tag}2", f"{d.name} 도통 손실, 6개 합", "W", f"{a['cond']:.2f}", "±5 %"),
            (f"{tag}3", f"{d.name} 스위칭 손실, 소자 1개 (오버랩+Qoss+Qrr)", "W", sw, "plan.md §5.2 참조"),
            (f"{tag}4", f"{d.name} 스위칭 손실, 6개 합", "W", swt, "plan.md §5.2 참조"),
            (f"{tag}5", f"{d.name} 다이오드 손실 6개 합 (Vsd 1 V 당)", "W/V", f"{a['k_dt_per_V']:.3f}", "±10 %"),
            (f"{tag}6", f"{d.name} 인버터 총손실 (알려진 항목)", "W", f"{a['total_known']:.2f}", "plan.md §5.2 참조"),
        ]
    for d in DEVICES:
        st = stall_losses(d, I_RMS, REF_FSW, REF_TD, VDC_NOM)
        tag = d.path.split()[0]
        rows.append((f"{tag}7", f"{d.name} 정지 시 S1 도통 손실 (A상 피크 고정)", "W", f"{st['cond_worst']:.3f}", "±5 %"))
    c470 = 470e-6
    rows += [
        ("R1", "회생 dV/dt, C 470 µF, 정격 회생, 단방향 전원", "V/ms", f"{regen_dvdt(c470, 85, abs(p_reg))/1e3:.1f}", "±5 %"),
        ("R2", "85→96 V 도달 시간, C 470 µF", "ms", f"{regen_capacitor(c470, 85, 96)/abs(p_reg)*1e3:.3f}", "±5 %"),
    ]
    for r_ in rows:
        w(f"| {r_[0]} | {r_[1]} | {r_[2]} | {r_[3]} |  |  | {r_[4]} |")
    w("")

    # 7.8 status
    w("## 8. 소자 입력값과 상태\n")
    w("| 파라미터 | " + " | ".join(d.name for d in DEVICES) + " |")
    w("|---|" + "---|" * len(DEVICES))
    for key, unit, scale in [("vds", "V", 1), ("rds25_max", "mΩ", 1e3), ("qg", "nC", 1e9),
                             ("qgd", "nC", 1e9), ("vpl", "V", 1), ("qoss", "nC", 1e9),
                             ("qrr", "nC", 1e9), ("rthjc", "K/W", 1), ("vsd", "V", 1), ("rg_int", "Ω", 1)]:
        cells = []
        for d in DEVICES:
            v = getattr(d, key)
            cells.append(("❓" if v is None else f"{v*scale:g} {unit}") + f" — {d.status.get(key,'')}")
        w(f"| {key} | " + " | ".join(cells) + " |")
    w("")
    return "\n".join(L)


def export_energy_tables(outdir: Path, vdc: float = VDC_NOM) -> list[Path]:
    """PSIM 열 모듈 Device Database 입력용 E(Id) 표 (psim-build-guide.md §5 방법 A).

    Eon = ½·V·I·t_vf + Qoss·V,  Eoff = ½·V·I·t_vr,  Err(diode) = Qrr·V (별도 열).
    PSIM 에서 다이오드 Err 를 0 으로 둘 경우에만 Err 를 Eon 에 합산해 넣는다 (이중 계상 방지).
    Qgd ❓ 소자는 내보내지 않는다.
    """
    paths = []
    for d in DEVICES:
        ion, ioff = gate_currents(d)
        if d.qgd is None or ion is None:
            continue
        t_vf, t_vr = d.qgd / ion, d.qgd / ioff
        p = outdir / f"energy_{d.name}_{vdc:.0f}V.csv"
        lines = [f"# {d.name} @ Vdc={vdc:.0f} V, Rg_ext=0, Ig_on={ion} A, Ig_off={ioff} A — 🔢 crosscheck.py 해석식 (하한)",
                 "Id_A,Eon_uJ,Eoff_uJ,Err_diode_uJ"]
        for i in [0, 5, 10, 20, 30, 40, 50, 60, 75, 100]:
            eon = 0.5 * vdc * i * t_vf + d.qoss * vdc
            eoff = 0.5 * vdc * i * t_vr
            lines.append(f"{i},{eon*1e6:.3f},{eoff*1e6:.3f},{d.qrr*vdc*1e6:.3f}")
        p.write_text("\n".join(lines) + "\n", encoding="utf-8")
        paths.append(p)
    return paths


def self_check():
    """해석식 ↔ 시간영역 일치 확인 (회귀 테스트)."""
    op = op_point(VDC_NOM, I_RMS, 0.9)
    for d in DEVICES:
        a = analytic_losses(d, op, REF_FSW, REF_TD)
        t = time_domain(d, op, REF_FSW, REF_TD, cycles=2)
        assert abs(a["cond"] - t["cond"]) / a["cond"] < 0.01, (d.name, a["cond"], t["cond"])
        assert abs(a["k_dt_per_V"] - t["dt_per_V"]) / a["k_dt_per_V"] < 0.01
        assert abs(a["shunt_low"] - t["p_shunt_low"]) / a["shunt_low"] < 0.01
        sw_an = sum(x for x in (a["overlap"], a["qoss"], a["qrr"]) if x is not None)
        assert abs(sw_an - t["sw"]) / sw_an < 0.01, (d.name, sw_an, t["sw"])
        assert abs(t["p_dc"] - op["p_out"]) / op["p_out"] < 0.01  # 무손실 전력 평형
    # docs/01 §2.2 재현
    assert abs(op_point(VDC_NOM, I_RMS, 1.0)["p_out"] - 3675) < 2


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--motor", type=Path, help="모터/시스템 파라미터 JSON (template 참조)")
    ap.add_argument("--out", type=Path, default=Path(__file__).with_name("crosscheck_results.md"))
    args = ap.parse_args()
    self_check()
    motor = None
    if args.motor:
        motor = {k: v for k, v in json.loads(args.motor.read_text()).items() if not k.startswith("_")}
        motor["_file"] = str(args.motor)
    export_energy_tables(args.out.parent)
    text = report(motor)
    args.out.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
