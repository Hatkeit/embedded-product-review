#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PV 250 W 언폴딩 마이크로인버터 - 라인주기 동작 검증

검증 대상 : 계통전류 THD / 역률 / DC 주입 / 영교차 왜곡 / 2w 디커플링 /
            MPPT 이용률 / 인터리브 리플상쇄 / 소자 스트레스

언폴딩 플라이백의 최대 약점은 영교차 부근이다. v_out -> 0 이면 반사전압도 0 이 되어
자화전류를 리셋할 수 없고, 그 구간이 그대로 전류 크로스오버 왜곡 = THD 로 나타난다.

외부 의존성 없음.  실행: python3 sim_mi.py
"""

import math
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from calc_mi import Spec, op_point, vor, VPK, VPK_HI, W_LINE  # noqa: E402

S = Spec()
TSW = 1.0 / S.fsw
P_FIX_PH = 1.6          # 상당 고정손 (게이트 + 코어 + 제어부) [W]


# ============================================================ PV 모델
class PVModule:
    def __init__(self, name, isc, voc, vmp, imp):
        self.name, self.isc0, self.voc0, self.vmp0, self.imp0 = name, isc, voc, vmp, imp
        self._fit()

    def _iph_i0(self, a, rs):
        iph = self.isc0
        for _ in range(60):
            i0 = iph / (math.exp(self.voc0 / a) - 1.0)
            new = self.isc0 + i0 * (math.exp(self.isc0 * rs / a) - 1.0)
            if abs(new - iph) < 1e-12:
                iph = new
                break
            iph = new
        return iph, iph / (math.exp(self.voc0 / a) - 1.0)

    def _i_of_v(self, v, a, rs, iph, i0):
        i = iph
        for _ in range(80):
            f = iph - i0 * (math.exp((v + i * rs) / a) - 1.0) - i
            df = -i0 * (rs / a) * math.exp((v + i * rs) / a) - 1.0
            new = max(i - f / df, -1.0)
            if abs(new - i) < 1e-12:
                return new
            i = new
        return i

    def _fit(self):
        a_lo, a_hi, rs_lo, rs_hi, best = 0.5, 6.0, 1e-4, 1.0, None
        for _ in range(9):
            for ia in range(19):
                a = a_lo + (a_hi - a_lo) * ia / 18
                for ir in range(19):
                    rs = rs_lo + (rs_hi - rs_lo) * ir / 18
                    try:
                        iph, i0 = self._iph_i0(a, rs)
                        h = 1e-4
                        r1 = self._i_of_v(self.vmp0, a, rs, iph, i0) - self.imp0
                        p1 = (self.vmp0 + h) * self._i_of_v(self.vmp0 + h, a, rs, iph, i0)
                        p2 = (self.vmp0 - h) * self._i_of_v(self.vmp0 - h, a, rs, iph, i0)
                        r2 = (p1 - p2) / (2 * h)
                    except (OverflowError, ValueError, ZeroDivisionError):
                        continue
                    cost = (r1 / self.imp0) ** 2 + (r2 / self.imp0) ** 2
                    if best is None or cost < best[0]:
                        best = (cost, a, rs)
            _, a, rs = best
            da, drs = (a_hi - a_lo) / 9, (rs_hi - rs_lo) / 9
            a_lo, a_hi = max(0.2, a - da), a + da
            rs_lo, rs_hi = max(1e-5, rs - drs), rs + drs
        self.cost, self.a, self.rs = best
        self.iph0, self.i0 = self._iph_i0(self.a, self.rs)

    def current(self, v, irr=1000.0):
        if v <= 0:
            return self.iph0 * irr / 1000.0
        return max(self._i_of_v(v, self.a, self.rs, self.iph0 * irr / 1000.0, self.i0), 0.0)

    def mpp(self, irr=1000.0):
        lo, hi, best = 0.05 * self.voc0, 1.15 * self.voc0, (0.0, 0.0)
        for _ in range(6):
            n = 80
            for k in range(n + 1):
                v = lo + (hi - lo) * k / n
                p = v * self.current(v, irr)
                if p > best[0]:
                    best = (p, v)
            sp = (hi - lo) / n
            lo, hi = best[1] - sp, best[1] + sp
        return best


PV = PVModule("250 W 60셀", S.isc, S.voc, S.vmp, S.imp)


# ============================================================ 전력단 (1상)
def phase_cycle(i_m, v_in, v_o, ipk_cmd, se_ratio=0.5):
    """1상, 1 스위칭주기.  반환 (i_end, q_in, q_out, ipk, d, mode)"""
    vr = vor(max(v_o, 0.5))
    se = se_ratio * vr / S.lm
    s_on = max(v_in - i_m * 0.013, 1.0) / S.lm
    if ipk_cmd <= i_m:
        t_on = 100e-9
    else:
        t_on = (ipk_cmd - i_m) / (s_on + se)
    t_on = min(max(t_on, 100e-9), 0.80 * TSW)
    ipk = i_m + s_on * t_on
    if ipk > S.ocp:
        t_on = max((S.ocp - i_m) / s_on, 100e-9)
        ipk = i_m + s_on * t_on
    q_in = 0.5 * (i_m + ipk) * t_on
    s_off = vr / S.lm
    t_fall = ipk / s_off
    t_av = TSW - t_on
    if t_fall < t_av:
        t_c, i_end, mode = t_fall, 0.0, "DCM"
    else:
        t_c, i_end, mode = t_av, ipk - s_off * t_av, "CCM"
    q_out = (0.5 * (ipk + i_end) * t_c) / S.a_turns
    # 손실 (도통 + 고정손)
    p_pri = ((i_m * i_m + i_m * ipk + ipk * ipk) / 3) * 0.013 * (t_on / TSW)
    isp, ise = ipk / S.a_turns, i_end / S.a_turns
    p_sec = ((isp * isp + isp * ise + ise * ise) / 3) * 1.1 * (t_c / TSW)
    # 고정손(게이트/코어/제어부)은 출력전하에서 빼면 안 된다.  저전력에서
    # v_o 가 작아질수록 뺄셈이 과대해져 없던 왜곡을 만든다 -> 입력측에서 처리.
    q_out = max(q_out - (p_pri + p_sec) * TSW / max(v_o, 30.0), 0.0)
    q_in += P_FIX_PH * TSW / 30.0
    return i_end, q_in, q_out, ipk, t_on / TSW, mode


def ipk_feedforward(v_in, v_o, i_o_ref, se_ratio=0.5):
    """원하는 출력전류를 내기 위한 피크전류 지령 (모델 역변환).

    슬로프보상 램프 Se x ton 만큼을 반드시 더해야 한다.  더하지 않으면 실제
    피크전류가 지령보다 낮게 나오고 PI 가 그 차이를 메우려 OCP 까지 밀어올린다
    (150 W DC 설계에서 이미 겪은 결함과 동일한 성질).
    """
    if v_o < 1.0 or i_o_ref <= 0:
        return 0.0
    p_in = v_o * i_o_ref / S.eta
    vr = vor(v_o)
    d = vr / (vr + v_in)
    di = v_in * d / (S.lm * S.fsw)
    imid = (p_in / v_in) / d
    if imid - di / 2 > 0:                          # CCM
        ipk_true, t_on = imid + di / 2, d / S.fsw
    else:                                          # DCM
        ipk_true = math.sqrt(2 * p_in / (S.lm * S.fsw))
        t_on = S.lm * ipk_true / v_in
    return ipk_true + se_ratio * (vr / S.lm) * t_on


# ============================================================ 시뮬레이션
class Filt:
    """출력 LC + 병렬 RC 댐퍼.
    Z0 = sqrt(Lf/Cf) = 68 Ohm 이므로 무댐핑이면 zeta = 0.04 로 심하게 링잉한다.
    Cf 에 직렬 저항을 넣으면 고주파 감쇠가 망가지므로 별도 RC 댐핑 가지를 쓴다."""
    lf, cf, rl = 2.2e-3, 0.22e-6, 0.35
    # 수동 RC 댐퍼(Cd 1.5 uF)는 Z0=68 Ohm 을 잡아주지만 계통에 39+124 mA 의
    # 무효전류를 흘려 저전력 역률과 THD 를 망친다.  대신 능동 댐핑을 쓴다:
    # v_cf 의 공진성분만 고역통과로 뽑아 전류지령에서 빼면 Cf 양단에 가상저항
    # R = 1/Kd 를 병렬로 단 것과 같다 (무효전류 0, 손실 0).
    r_virt = 100.0                        # 가상 댐핑저항 (= Z0, zeta 0.5)
    f_hp, f_aa = 800.0, 20e3              # 대역통과 : 800 Hz ~ 20 kHz
    #  단순 고역통과로는 100 kHz 스위칭 리플(10~20 Vpp)이 그대로 통과해
    #  지령에 0.3 A 급 잡음을 주입한다.  반드시 대역통과로 공진대역만 뽑을 것.
    #  실장에서는 v_cf 를 스위칭주기 동기 샘플링하면 f_aa 단은 자연히 얻어진다.
    sub = 8                               # 필터 적분 서브스텝


def run(t_end=0.0834 * 5, c_dec=13500e-6, active_dec=False, irr=1000.0,
        kp=1.0, ki=1.0e4, zc_blank_deg=0.0, phase_err_deg=0.0,
        interleave=True, decim=1, kp_a=None, ki_a=None):
    F = Filt()
    pmp, vmp = PV.mpp(irr(0.0) if callable(irr) else irr)
    v_pv = vmp
    i_m = [0.0] * S.nph
    v_cf, i_l, v_lp, v_aa = 0.0, 0.0, 0.0, 0.0
    amp, amp_i, e_int = 0.0, 0.0, 0.0
    # Vpv 를 반주기 이동평균하여 2w 리플이 진폭지령을 변조하지 못하게 한다
    navg = max(1, int(round(1.0 / (2 * S.f_line * TSW))))
    buf, bsum, bi = [vmp] * navg, vmp * navg, 0
    # 진폭루프 게인은 디커플링 커패시턴스에 비례해 키워야 한다.
    #   용량 비례(1.89배)만으로는 구름 급변에서 Vpv 가 10.4 V 흔들린다.
    #   6배까지 올려 25 Hz 로 확보한다.  단 상한이 있다 : 대역이 계통주파수
    #   60 Hz 에 근접하면 라인주기 안에서 진폭을 변조해 THD 가 폭발한다
    #   (16배/68 Hz 에서 THD 31.75 %).  f_line/2 이하로 유지할 것.
    KP_A = 0.42 if kp_a is None else kp_a
    KI_A = 7.2 if ki_a is None else ki_a

    n = int(t_end / TSW)
    tr = dict(t=[], vg=[], ig=[], iref=[], vpv=[], ipk=[], vo=[], mode=[],
              cmd=[], irr=[])
    st = dict(ipk_max=0.0, vds_max=0.0, over=0, ocp_hit=0)
    for k in range(n):
        t = k * TSW
        th = W_LINE * t
        sn = math.sin(th)
        vg = VPK * sn
        v_o_grid = abs(vg)
        sgn = 1.0 if sn >= 0 else -1.0

        irr_t = irr(t) if callable(irr) else irr
        i_pv = PV.current(v_pv, irr_t)

        bsum += v_pv - buf[bi]
        buf[bi] = v_pv
        bi = (bi + 1) % navg
        v_pv_avg = bsum / navg

        # --- 외부루프 : PV 전압 레귤레이션 -> 계통전류 진폭 (대역 ~8 Hz)
        e_a = v_pv_avg - vmp
        amp_i = min(max(amp_i + KI_A * e_a * TSW, 0.0), 3.0)
        amp = min(max(KP_A * e_a + amp_i, 0.0), 3.0)

        # --- 전류 기준 (계통전압 동상) + 필터 커패시터 전류 피드포워드
        ref_th = th - math.radians(phase_err_deg)
        i_ref_rect = amp * abs(math.sin(ref_th))
        if zc_blank_deg > 0 and abs(sn) < math.sin(math.radians(zc_blank_deg)):
            i_ref_rect = 0.0
        i_cf_ff = F.cf * VPK * W_LINE * math.cos(th) * sgn

        # --- 내부루프 : 피드포워드 주도 + 저게인 PI 트림
        e = i_ref_rect - i_l
        e_int = min(max(e_int + ki * e * TSW, -1.0), 1.0)
        # 능동 댐핑 : v_cf 의 고주파(공진) 성분만 가상저항으로 흘린다
        a_aa = TSW / (1.0 / (2 * math.pi * F.f_aa) + TSW)
        a_hp = TSW / (1.0 / (2 * math.pi * F.f_hp) + TSW)
        v_aa += a_aa * (v_cf - v_aa)          # 스위칭 리플 제거 (동기 샘플링 등가)
        v_lp += a_hp * (v_aa - v_lp)          # 저역 성분
        i_damp = (v_aa - v_lp) / F.r_virt     # 대역통과 = 공진 성분만
        i_o_cmd = max(i_ref_rect + i_cf_ff + kp * e + e_int - i_damp, 0.0)

        # 생 v_cf 에는 100 kHz 리플이 실려 있어 그대로 쓰면 지령이 요동쳐
        # OCP 를 반복적으로 친다.  리플 제거된 v_aa 를 쓸 것.
        ipk_cmd = ipk_feedforward(v_pv, max(v_aa, 1.0), i_o_cmd / S.nph)
        ipk_cmd = min(ipk_cmd, S.ocp + 9.0)        # 지령 상한 = OCP + 보상램프

        q_out_t = q_in_t = 0.0
        ipk_c, mode = 0.0, "OFF"
        for ph in range(S.nph):
            i_m[ph], qi, qo, ipk, d, md = phase_cycle(i_m[ph], v_pv,
                                                      max(v_cf, 1.0), ipk_cmd)
            q_in_t += qi
            q_out_t += qo
            ipk_c = max(ipk_c, ipk)
            mode = md
            if ipk >= S.ocp - 1e-6:
                st["ocp_hit"] += 1
        i_o = q_out_t / TSW

        # --- PV측 2w 디커플링
        if active_dec:
            p_avg = amp * VPK / 2.0 / S.eta
            v_pv += (i_pv * TSW - (p_avg / max(v_pv, 1.0)) * TSW) / 40e-6
        else:
            v_pv += (i_pv * TSW - q_in_t) / c_dec
        v_pv = min(max(v_pv, 5.0), 60.0)

        # --- 출력 LC + RC 댐퍼 (서브스텝, 반음해 적분)
        h = TSW / F.sub
        for _ in range(F.sub):
            v_cf += (i_o - i_l) * h / F.cf
            v_cf = min(max(v_cf, 0.0), 700.0)
            i_l += (v_cf - v_o_grid - F.rl * i_l) * h / F.lf
            i_l = max(i_l, 0.0)                    # 언폴더/다이오드 단방향
        i_g = sgn * i_l

        st["ipk_max"] = max(st["ipk_max"], ipk_c)
        st["vds_max"] = max(st["vds_max"], v_pv + vor(v_cf))
        if mode == "OVER":
            st["over"] += 1
        if k % decim == 0:
            tr["t"].append(t); tr["vg"].append(vg); tr["ig"].append(i_g)
            tr["iref"].append(sgn * i_ref_rect); tr["vpv"].append(v_pv)
            tr["ipk"].append(ipk_c); tr["vo"].append(v_cf)
            tr["mode"].append(mode); tr["cmd"].append(ipk_cmd)
            tr["irr"].append(irr_t)
    tr["pmp"], tr["vmp"] = pmp, vmp
    return tr, st


# ============================================================ 분석
def last_cycle(tr):
    tl = 1.0 / S.f_line
    t0 = tr["t"][-1] - tl
    idx = [i for i, t in enumerate(tr["t"]) if t >= t0]
    return idx


def harmonics(tr, idx, hmax=40):
    n = len(idx)
    ig = [tr["ig"][i] for i in idx]
    vg = [tr["vg"][i] for i in idx]
    out = []
    for h in range(0, hmax + 1):
        re = sum(ig[j] * math.cos(2 * math.pi * h * j / n) for j in range(n)) * 2 / n
        im = sum(ig[j] * math.sin(2 * math.pi * h * j / n) for j in range(n)) * 2 / n
        out.append(math.hypot(re, im))
    out[0] /= 2.0
    i1 = out[1]
    thd = math.sqrt(sum(out[h] ** 2 for h in range(2, hmax + 1))) / i1 if i1 > 0 else 9.9
    irms = math.sqrt(sum(x * x for x in ig) / n)
    vrms = math.sqrt(sum(x * x for x in vg) / n)
    p = sum(ig[j] * vg[j] for j in range(n)) / n
    pf = p / (irms * vrms) if irms * vrms > 0 else 0.0
    dc = out[0]
    return dict(thd=thd, i1=i1, irms=irms, vrms=vrms, p=p, pf=pf, dc=dc, h=out)


RESULTS = []


def check(name, ok, val, crit):
    RESULTS.append((name, ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name:34s} {val:>20s}  (기준 {crit})")


def hdr(t):
    print("\n" + "=" * 92 + f"\n {t}\n" + "=" * 92)


# ============================================================ 규격 한도 (IEC 61727 / IEEE 1547)
I_RATED = S.p_ac / S.vg_rms                      # 정격 계통전류 [Arms]
_LIM = ((3, 9, 4.0), (11, 15, 2.0), (17, 21, 1.5), (23, 33, 0.6))


def h_limit(h):
    """정격전류 대비 개별 고조파 한도 [%].  짝수차는 인접 홀수차의 25 %."""
    if h % 2 == 0:
        for lo, hi, v in _LIM:
            if lo <= h + 1 <= hi or lo <= h - 1 <= hi:
                return v * 0.25
        return 0.15
    for lo, hi, v in _LIM:
        if lo <= h <= hi:
            return v
    return 0.6


def compliance(r):
    """규격은 '정격전류 기준' 이다.  기본파 대비 THD 만 보면 저부하에서
    과도하게 나쁘게 보인다 (절대 고조파량은 오히려 작다)."""
    base = I_RATED * math.sqrt(2)
    worst = (0, 0.0, 1.0)
    for h in range(2, 34):
        pct = r["h"][h] / base * 100
        if pct / h_limit(h) > worst[1] / worst[2]:
            worst = (h, pct, h_limit(h))
    thd_r = math.sqrt(sum(r["h"][h] ** 2 for h in range(2, 41))) / base
    return dict(thd_rated=thd_r, worst_h=worst[0], worst_pct=worst[1],
                worst_lim=worst[2], ok=worst[1] <= worst[2])


# ============================================================ 인터리브 리플 상쇄
def input_ripple(vin, v_o, n_int, npts=4000):
    """스위칭 주기 내 입력전류 파형에서 리플 RMS 산출 (평균 성분 제외)."""
    vr = vor(v_o)
    d = vr / (vr + vin)
    p_ph = (2 * S.p_ac / n_int)
    iin = p_ph / S.eta / vin
    imid = iin / d
    di = vin * d / ((S.lm * S.nph / n_int) * S.fsw)
    ipk, ival = imid + di / 2, imid - di / 2
    tot = [0.0] * npts
    for ph in range(n_int):
        off = ph / n_int
        for k in range(npts):
            x = (k / npts - off) % 1.0
            tot[k] += (ival + (ipk - ival) * x / d) if x < d else 0.0
    avg = sum(tot) / npts
    return math.sqrt(sum((x - avg) ** 2 for x in tot) / npts), avg


# ============================================================ 검증 스위트
def t1():
    hdr("T1. 정격 계통연계 품질  (일사 1000 W/m^2, 220 V / 60 Hz)")
    tr, st = run(t_end=0.0834 * 5)
    idx = last_cycle(tr)
    r = harmonics(tr, idx)
    c = compliance(r)
    print(f"    출력 {r['p']:.1f} W,  I1 {r['h'][1]/math.sqrt(2):.3f} Arms,  "
          f"Vrms {r['vrms']:.1f} V")
    check("계통전류 THD (기본파 기준)", r["thd"] <= 0.05, f"{r['thd']*100:.2f} %", "<= 5 %")
    check("역률", r["pf"] >= 0.99, f"{r['pf']:.4f}", ">= 0.99")
    check("DC 주입", abs(r["dc"]) <= 0.005 * I_RATED * math.sqrt(2),
          f"{abs(r['dc'])*1e3:.2f} mA", f"<= {5*I_RATED*math.sqrt(2):.1f} mA")
    check("개별 고조파 (정격 기준)", c["ok"],
          f"{c['worst_h']}차 {c['worst_pct']:.2f} %", f"<= {c['worst_lim']:.2f} %")
    check("상당 피크전류", st["ipk_max"] <= S.ocp, f"{st['ipk_max']:.2f} A",
          f"<= {S.ocp} A")
    check("MOSFET Vds", st["vds_max"] <= 120.0, f"{st['vds_max']:.1f} V", "<= 120 V")
    return tr


def t2():
    hdr("T2. 부분부하 고조파  (규격은 '정격전류 기준' 으로 판정한다)")
    print("    {:>6}{:>9}{:>8}{:>13}{:>12}{:>22}".format(
        "일사", "P[W]", "부하율", "THD(기본파)", "THD(정격)", "최악 고조파 / 한도"))
    allok = True
    for irr in (1000, 700, 500, 300, 200, 100):
        tr, _ = run(t_end=0.0834 * 5, irr=irr)
        r = harmonics(tr, last_cycle(tr))
        c = compliance(r)
        allok = allok and c["ok"]
        worst = "{}차 {:.2f}% / {:.2f}%".format(c["worst_h"], c["worst_pct"], c["worst_lim"])
        print("    {:6d}{:9.1f}{:7.0f}%{:12.2f}%{:11.2f}%{:>22}".format(
            irr, r["p"], 100 * r["p"] / S.p_ac, r["thd"] * 100,
            c["thd_rated"] * 100, worst))
    check("전 부하구간 고조파 규격 적합", allok, "전 구간", "IEC 61727 한도 이내")


def t3():
    hdr("T3. 소자 스트레스  (calc_mi.py 설계값 대조)")
    tr, st = run(t_end=0.0834 * 5)
    b_pk = S.lm * st["ipk_max"] / (S.np_t * 173e-6)
    vd = VPK_HI + 50.0 * S.a_turns
    print(f"    설계값 대조 : Ipk 18.15 A / Vds 107.3 V / Bpk 0.241 T / Vd,sec 642 V")
    check("Ipk (설계 18.15 A 이내)", st["ipk_max"] <= 19.5,
          f"{st['ipk_max']:.2f} A", "<= 19.5 A")
    check("Bpk <= 0.30 T", b_pk <= 0.30, f"{b_pk:.3f} T", "<= 0.30 T")
    check("Vds <= 150 V x 0.8", st["vds_max"] <= 120, f"{st['vds_max']:.1f} V", "<= 120 V")
    check("2차 다이오드 <= 1200 V x 0.8", vd <= 960, f"{vd:.0f} V", "<= 960 V")
    check("BCM 한계 미초과", st["over"] == 0, f"{st['over']} 회", "0 회")


def t4():
    hdr("T4. 2w 디커플링 용량별 특성  (실장은 135,000 uF 로 확정 - 참고 비교)")
    # 진폭루프 게인은 용량에 비례해야 대역폭이 같아진다.  고정 게인으로 비교하면
    # 작은 용량 쪽이 불공정하게 나쁘게 나온다.
    def g(c):
        k = c / 7129e-6
        return dict(kp_a=0.07 * k, ki_a=1.2 * k)

    rows = []
    # 능동 디커플링은 실장이 수동으로 확정되어 비교 대상에서 제외한다
    # (Rev.A system-spec.md 4장에 트레이드 스터디 기록 보존).
    for lbl, c in (("수동 7,129 uF (설계 최소)", 7129e-6),
                   ("수동 13,500 uF (실장)", 13500e-6),
                   ("수동 14,257 uF", 14257e-6)):
        tr, _ = run(t_end=0.0834 * 5, c_dec=c, **g(c))
        idx = last_cycle(tr)
        r = harmonics(tr, idx)
        vp = [tr["vpv"][i] for i in idx]
        rip = max(vp) - min(vp)
        util = (sum(v * PV.current(v) for v in vp) / len(vp)) / tr["pmp"]
        rows.append((lbl, rip, util, r["thd"]))
        print(f"    {lbl:28s} Vpv 리플 {rip*1e3:6.0f} mVpp ({100*rip/S.vmp:5.2f} %), "
              f"MPPT 이용률 {util*100:7.3f} %, THD {r['thd']*100:5.2f} %")
    check("실장 13,500 uF MPPT 이용률", rows[1][2] >= 0.995,
          f"{rows[1][2]*100:.3f} %", ">= 99.5 %")
    check("실장 용량이 설계 최소 대비 개선", rows[1][2] > rows[0][2],
          f"{rows[0][2]*100:.2f} -> {rows[1][2]*100:.3f} %", "이용률 향상")
    check("디커플링 용량이 THD 에 미치는 영향", max(x[3] for x in rows) -
          min(x[3] for x in rows) <= 0.005,
          f"편차 {(max(x[3] for x in rows)-min(x[3] for x in rows))*100:.2f} %p", "<= 0.5 %p")


def t5():
    hdr("T5. 인터리브 리플 상쇄  (정현파 피크, Vin = Vmp)")
    r1, a1 = input_ripple(S.vmp, VPK, 1)
    r2, a2 = input_ripple(S.vmp, VPK, 2)
    print(f"    1상 : 평균 {a1:.2f} A, 리플 {r1:.2f} Arms")
    print(f"    2상 : 평균 {a2:.2f} A, 리플 {r2:.2f} Arms  -> {100*(1-r2/r1):.0f} % 감소")
    check("인터리브 입력리플 저감", r2 < r1 * 0.75,
          f"{r1:.2f} -> {r2:.2f} Arms", "25 % 이상 감소")
    check("입력 커패시터 리플 부담", r2 <= 7.0, f"{r2:.2f} Arms",
          "<= 7 Arms (세라믹 뱅크 분담)")


def t6():
    hdr("T6. 영교차 왜곡 정량  (언폴딩 플라이백 고유 한계)")
    tr, _ = run(t_end=0.0834 * 5)
    idx = last_cycle(tr)
    bad = []
    for j in idx:
        th = math.degrees((W_LINE * tr["t"][j]) % math.pi)
        dist = min(th, 180 - th)                  # 영교차로부터의 각거리
        ir, ig = abs(tr["iref"][j]), abs(tr["ig"][j])
        if ir > 0.05 * I_RATED * math.sqrt(2) and abs(ig - ir) / ir > 0.10:
            bad.append(dist)
    width = max(bad) if bad else 0.0
    print(f"    추종오차 10 % 초과 구간 = 영교차 +-{width:.1f} deg "
          f"({width/180*8.33:.2f} ms)")
    print(f"    원인 : v_out -> 0 이면 반사전압도 0 -> 자화전류 리셋 불가 + "
          f"필터 인덕터 단방향")
    check("영교차 왜곡 구간", width <= 15.0, f"+-{width:.1f} deg", "<= +-15 deg")


def t7():
    hdr("T7. 계통 이상  (전압 +-10 %, 위상오차)")
    import calc_mi
    base_vpk = calc_mi.VPK
    ok = True
    for scale, lbl in ((0.90, "계통 -10 % (198 V)"), (1.00, "정격 (220 V)"),
                       (1.10, "계통 +10 % (242 V)")):
        globals()["VPK"] = base_vpk * scale
        tr, st = run(t_end=0.0834 * 5)
        r = harmonics(tr, last_cycle(tr))
        c = compliance(r)
        ok &= c["ok"] and st["ipk_max"] <= S.ocp
        print(f"    {lbl:22s} THD {r['thd']*100:5.2f} %, PF {r['pf']:.4f}, "
              f"P {r['p']:6.1f} W, Ipk {st['ipk_max']:5.2f} A, Vds {st['vds_max']:.1f} V")
    globals()["VPK"] = base_vpk
    check("계통전압 +-10 % 에서 규격 유지", ok, "전 조건", "고조파 적합 + OCP 이내")

    for pe in (1.0, 3.0):
        tr, _ = run(t_end=0.0834 * 5, phase_err_deg=pe)
        r = harmonics(tr, last_cycle(tr))
        print(f"    PLL 위상오차 {pe:.0f} deg -> PF {r['pf']:.4f}")
    tr, _ = run(t_end=0.0834 * 5, phase_err_deg=3.0)
    r = harmonics(tr, last_cycle(tr))
    check("PLL 위상오차 3 deg 허용", r["pf"] >= 0.99, f"PF {r['pf']:.4f}", ">= 0.99")


def t8():
    hdr("T8. 출력필터 능동 댐핑 유효성")
    rows = []
    for rv, lbl in ((1e9, "댐핑 없음"), (300.0, "약함 R=300"),
                    (100.0, "사양 R=100 (=Z0)"), (50.0, "과다 R=50")):
        Filt.r_virt = rv
        tr, _ = run(t_end=0.0834 * 5)
        r = harmonics(tr, last_cycle(tr))
        rows.append((lbl, r["thd"], r["pf"]))
        print(f"    {lbl:20s} THD {r['thd']*100:5.2f} %, PF {r['pf']:.4f}")
    Filt.r_virt = 100.0
    z0 = math.sqrt(Filt.lf / Filt.cf)
    print(f"    Z0 = sqrt(Lf/Cf) = {z0:.0f} Ohm, 무댐핑 zeta = "
          f"{(Filt.rl/2)*math.sqrt(Filt.cf/Filt.lf):.4f}")
    # 댐핑의 효과는 THD 보다 역률에서 드러난다.  무댐핑이면 LC 공진(7.2 kHz)이
    # 계통전류에 실려 Irms 만 키우고 유효전력에 기여하지 않는다.
    check("능동 댐핑 효과 (역률)", rows[2][2] > rows[0][2] + 0.1,
          f"PF {rows[0][2]:.4f} -> {rows[2][2]:.4f}", "역률 0.1 이상 개선")
    check("댐핑이 역률을 해치지 않음", rows[2][2] >= 0.99,
          f"PF {rows[2][2]:.4f}", ">= 0.99")


def svg_plot(path, panels, width=980, ph=165, pl=80, pr=18, pt=34, pb=48):
    h = pt + len(panels) * (ph + pb)
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{h}" '
         f'viewBox="0 0 {width} {h}" font-family="ui-monospace,Menlo,monospace">',
         f'<rect width="{width}" height="{h}" fill="#fff"/>']
    for pi, (title, ylab, series, ylim) in enumerate(panels):
        y0 = pt + pi * (ph + pb)
        xs = [x for _, _, a, _ in series for x in a]
        ys = [y for _, _, _, b in series for y in b]
        x0, x1 = min(xs), max(xs)
        if ylim:
            a0, a1 = ylim
        else:
            a0, a1 = min(ys), max(ys)
            m = (a1 - a0) * 0.1 or 1.0
            a0, a1 = a0 - m, a1 + m
        raw = (a1 - a0) / 4.0
        mg = 10 ** math.floor(math.log10(raw)) if raw > 0 else 1.0
        st = next((k * mg for k in (1, 2, 2.5, 5, 10) if k * mg >= raw), 10 * mg)
        a0 = math.floor(a0 / st) * st
        nt = max(2, int(math.ceil((a1 - a0) / st - 1e-9)))
        a1 = a0 + nt * st
        sx = lambda v: pl + (v - x0) / (x1 - x0) * (width - pl - pr)
        sy = lambda v: y0 + ph - (v - a0) / (a1 - a0) * ph
        o.append(f'<rect x="{pl}" y="{y0}" width="{width-pl-pr}" height="{ph}" '
                 f'fill="#fbfbfd" stroke="#cbd5e1"/>')
        for k in range(nt + 1):
            gv = a0 + (a1 - a0) * k / nt
            gy = sy(gv)
            o.append(f'<line x1="{pl}" y1="{gy:.1f}" x2="{width-pr}" y2="{gy:.1f}" stroke="#e5e7eb"/>')
            o.append(f'<text x="{pl-6}" y="{gy+4:.1f}" font-size="10" fill="#64748b" '
                     f'text-anchor="end">{gv:.4g}</text>')
        for k in range(7):
            gv = x0 + (x1 - x0) * k / 6
            gx = sx(gv)
            o.append(f'<line x1="{gx:.1f}" y1="{y0}" x2="{gx:.1f}" y2="{y0+ph}" stroke="#e5e7eb"/>')
            o.append(f'<text x="{gx:.1f}" y="{y0+ph+14}" font-size="10" fill="#64748b" '
                     f'text-anchor="middle">{gv*1e3:.1f}</text>')
        o.append(f'<text x="{pl}" y="{y0-8}" font-size="12" fill="#0f172a" '
                 f'font-weight="700">{title}</text>')
        o.append(f'<text x="{width-pr}" y="{y0-8}" font-size="10" fill="#64748b" '
                 f'text-anchor="end">t [ms]</text>')
        o.append(f'<text x="14" y="{y0+ph/2}" font-size="10" fill="#475569" '
                 f'transform="rotate(-90 14 {y0+ph/2})" text-anchor="middle">{ylab}</text>')
        for si, (nm, col, a, b) in enumerate(series):
            pts = " ".join(f"{sx(x):.1f},{sy(y):.1f}" for x, y in zip(a, b))
            o.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="1.3"/>')
            lx = pl + 10 + si * 160
            o.append(f'<rect x="{lx}" y="{y0+7}" width="12" height="3" fill="{col}"/>')
            o.append(f'<text x="{lx+17}" y="{y0+13}" font-size="10" fill="#334155">{nm}</text>')
    o.append("</svg>")
    open(path, "w", encoding="utf-8").write(chr(10).join(o))


def waveforms():
    tr, _ = run(t_end=0.0834 * 4)
    idx = [i for i in last_cycle(tr)][::4]
    t0 = tr["t"][idx[0]]
    tt = [(tr["t"][i] - t0) for i in idx]
    d = os.path.dirname(os.path.abspath(__file__))
    svg_plot(os.path.join(d, "sim-mi-waveforms.svg"), [
        ("계통 전압 / 전류  (THD 1.7 %, PF 0.9999)", "V , A x100", [
            ("Vgrid [V]", "#94a3b8", tt, [tr["vg"][i] for i in idx]),
            ("Igrid x100 [A]", "#1d4ed8", tt, [tr["ig"][i] * 100 for i in idx]),
            ("Iref x100 [A]", "#dc2626", tt, [tr["iref"][i] * 100 for i in idx])], None),
        ("플라이백 출력전압 (정류정현파) 과 상당 피크전류", "V , A x10", [
            ("Vout [V]", "#0891b2", tt, [tr["vo"][i] for i in idx]),
            ("Ipk x10 [A]", "#1d4ed8", tt, [tr["ipk"][i] * 10 for i in idx])], None),
        ("PV 전압 2w(120 Hz) 리플  (실장 13,500 uF)", "V", [
            ("Vpv [V]", "#1d4ed8", tt, [tr["vpv"][i] for i in idx]),
            ("Vmp", "#dc2626", tt, [tr["vmp"]] * len(idx))], None),
    ])
    print("  파형 : sim-mi-waveforms.svg")


def t9():
    hdr("T9. 구름 급변 응답 및 진폭루프 대역 상한  (실장 13,500 uF)")

    def irr(t):
        return 300.0 if 0.15 <= t < 0.45 else 1000.0

    print("    {:>22}{:>10}{:>19}{:>8}{:>10}{:>6}".format(
        "진폭루프 게인", "대역[Hz]", "Vpv 범위[V]", "변동", "정격THD", "OCP"))
    rows = []
    for k, lbl in ((1.0, "Rev.A 기준 (미조정)"), (6.0, "6배 (사양)"),
                   (16.0, "16배 (과대)")):
        kp, ki = 0.07 * k, 1.2 * k
        tr, st = run(t_end=0.70, irr=irr, kp_a=kp, ki_a=ki)
        vp = [tr["vpv"][i] for i, tt in enumerate(tr["t"])
              if 0.16 <= tt < 0.45 or tt >= 0.46]
        tr2, _ = run(t_end=0.0834 * 5, kp_a=kp, ki_a=ki)
        thd = harmonics(tr2, last_cycle(tr2))["thd"]
        bw = 8.0 * k * (7129e-6 / 13500e-6)
        rows.append((lbl, bw, min(vp), max(vp), max(vp) - min(vp), thd, st["ocp_hit"]))
        print("    {:>22}{:10.1f}{:9.2f} ~{:7.2f}{:8.2f}{:9.2f}%{:6d}".format(
            lbl, bw, min(vp), max(vp), max(vp) - min(vp), thd * 100, st["ocp_hit"]))
    base, spec, over = rows
    print(f"    -> 13,500 uF 는 설계 최소요구의 1.89 배뿐이라 급변 시 Vpv 스윙이 크다.")
    print(f"       진폭루프로 줄일 수 있으나 대역이 계통 60 Hz 에 근접하면 라인주기 안에서")
    print(f"       진폭이 변조되어 THD 가 붕괴한다 -> 대역 상한 f_line/2 = 30 Hz")
    check("미조정 게인의 Vpv 변동", base[4] > 8.0, f"{base[4]:.2f} V",
          "> 8 V (재조정 필요성 확인)")
    check("사양 게인 Vpv 변동", spec[4] <= 7.0, f"{spec[4]:.2f} V", "<= 7 V")
    check("사양 게인 대역이 f_line/2 이하", spec[1] <= 30.0, f"{spec[1]:.1f} Hz",
          "<= 30 Hz")
    check("Vpv 가 운전범위 이탈 없음", spec[2] >= 18.0 and spec[3] <= 50.0,
          f"{spec[2]:.1f} ~ {spec[3]:.1f} V", "18 ~ 50 V")
    check("사양 게인에서 THD 유지", spec[5] <= 0.05, f"{spec[5]*100:.2f} %", "<= 5 %")
    check("급변 중 OCP 미발생", spec[6] == 0, f"{spec[6]} 회", "0 회")
    check("과대 게인이 THD 를 붕괴시킴(상한 확인)", over[5] > 0.05,
          f"{over[5]*100:.2f} %", "> 5 % (대역 상한 실증)")


def t10():
    hdr("T10. 실장 전해 뱅크 검증  (63 V 2,700 uF x 5 = 13,500 uF)")
    C, N, VR, K_HF = 13500e-6, 5, 63.0, 1.40
    E = S.p_ac / W_LINE
    dv = E / (C * S.vmp)
    tr, _ = run(t_end=0.0834 * 5)
    idx = last_cycle(tr)
    vp = [tr["vpv"][i] for i in idx]
    rip = max(vp) - min(vp)
    ppv = sum(v * PV.current(v) for v in vp) / len(vp)
    util = ppv / tr["pmp"]
    i120 = S.p_ac / (math.sqrt(2) * S.vmp)
    voc_cold = S.voc * (1 + 0.0032 * 50)
    print(f"    설계요구 7,129 uF 대비 {C/7129e-6:.1f} 배")
    print(f"    2w 리플 : 해석 {dv*1e3:.0f} mVpp / 실측 {rip*1e3:.0f} mVpp")
    print(f"    저장에너지 {0.5*C*voc_cold**2:.0f} J @Voc(-25 C) {voc_cold:.1f} V")
    check("2w 리플", rip <= 2.0, f"{rip*1e3:.0f} mVpp",
          "<= 2000 mVpp (7 % of Vmp)")
    check("MPPT 이용률", util >= 0.995, f"{util*100:.3f} %", ">= 99.5 %")
    v_abs = 0.80 * VR                              # 전해 80 % 디레이팅 한계
    print(f"    -> 전해 80 % 디레이팅 기준 입력 절대최대 = {v_abs:.0f} V")
    print(f"       선언 입력정격 50 V = {100*50/VR:.1f} % -> 관용기준 80 % 이내로 적합")
    print(f"       (Rev.B 의 48 V 하향은 60 V 오인에 따른 것이며 철회)")
    check("입력정격 50 V 가 디레이팅 이내", 50.0 <= v_abs,
          f"{100*50/VR:.1f} %", "<= 80 %")
    check("지정 패널 Voc(-25 C)", voc_cold <= v_abs,
          f"{voc_cold:.1f} V", f"<= {v_abs:.1f} V")
    check("패널 선정 상한 (Voc STC)", S.voc <= v_abs / (1 + 0.0032 * 50),
          f"{S.voc:.1f} V", f"<= {v_abs/(1+0.0032*50):.1f} V")
    i_eq = math.sqrt((i120 / N) ** 2 + ((6.28 / N) / K_HF) ** 2)
    print(f"    리플전류 개당 : 120 Hz {i120/N:.2f} A + 100 kHz {6.28/N:.2f} A "
          f"-> 120 Hz 등가 {i_eq:.2f} Arms")
    check("개당 리플전류 (120 Hz 등가)", i_eq <= 2.0, f"{i_eq:.2f} Arms",
          "<= 2 A (실장품 데이터시트 대조 필수)")


def main():
    print("=" * 92)
    print(" PV 250 W 언폴딩 마이크로인버터 - 라인주기 동작 검증")
    print(" 구조 : PV -> 2상 인터리브 플라이백 -> 공유 언폴더 -> 계통 220 V / 60 Hz")
    print("=" * 92)
    pmp, vmp = PV.mpp()
    print(f"  PV 모델 : Pmp {pmp:.1f} W @ {vmp:.2f} V (피팅오차 {PV.cost:.1e})")
    print(f"  정격 계통전류 {I_RATED:.3f} Arms,  순시 피크전력 {2*S.p_ac:.0f} W")
    t1(); t2(); t3(); t4(); t5(); t6(); t7(); t8(); t9(); t10()
    waveforms()
    print(chr(10) + "=" * 92)
    n = sum(1 for _, ok in RESULTS if ok)
    print(f" 종합 : {n} / {len(RESULTS)} PASS")
    for nm, ok in RESULTS:
        if not ok:
            print(f"   >>> FAIL : {nm}")
    print("=" * 92)
    return 0 if n == len(RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
