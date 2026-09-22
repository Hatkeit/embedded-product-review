# -*- coding: utf-8 -*-
"""KS C 8560:2020 표 3/4/5 기반 절연거리 산출 + 표 13 온도 한계."""

# 표 3 — 저전압 회로에 대한 절연 전압 (시스템전압 -> OVC별 임펄스 전압 V)
TBL3 = [
    (50, 71,   {'I': 330,  'II': 500,  'III': 800,   'IV': 1500},  (1770, 1250)),
    (100, 141, {'I': 500,  'II': 800,  'III': 1500,  'IV': 2500},  (1840, 1300)),
    (150, 213, {'I': 800,  'II': 1500, 'III': 2500,  'IV': 4000},  (1910, 1350)),
    (300, 424, {'I': 1500, 'II': 2500, 'III': 4000,  'IV': 6000},  (2120, 1500)),
    (600, 849, {'I': 2500, 'II': 4000, 'III': 6000,  'IV': 8000},  (2550, 1800)),
    (1000, 1500, {'I': 4000, 'II': 6000, 'III': 8000, 'IV': 12000}, (3110, 2200)),
]
# 표 4 — 공간거리 (임펄스 V, 임시과전압 최대값 V, 동작전압 순환첨두값 V, PD1, PD2, PD3)
TBL4 = [
    (None, 110, 71,   0.01, 0.20, 0.80),   # PWB 오염등급2 에서는 0.10 (각주 a)
    (None, 225, 141,  0.01, 0.20, 0.80),
    (330,  340, 212,  0.01, 0.20, 0.80),
    (500,  530, 330,  0.04, 0.20, 0.80),
    (800,  700, 440,  0.10, 0.20, 0.80),
    (1500, 960, 600,  0.50, 0.50, 0.80),
    (2500, 1600, 1000, 1.5, 1.5, 1.5),
    (4000, 2600, 1600, 3.0, 3.0, 3.0),
    (6000, 3700, 2300, 5.5, 5.5, 5.5),
    (8000, 4800, 3000, 8.0, 8.0, 8.0),
    (12000, 7400, 4600, 14.0, 14.0, 14.0),
]
# 표 5 — 연면거리 (RMS 동작전압, PWB_PD1, PWB_PD2, 기타PD1, PD2-I, PD2-II, PD2-IIIab, PD3-I, PD3-II, PD3-IIIa)
TBL5 = [
    (63,   0.04, 0.063, 0.20, 0.63, 0.90, 1.25, 1.6, 1.8, 2.0),
    (80,   0.063, 0.10, 0.22, 0.67, 0.95, 1.3, 1.7, 1.9, 2.1),
    (100,  0.10, 0.16, 0.25, 0.71, 1.0, 1.4, 1.8, 2.0, 2.2),
    (125,  0.16, 0.25, 0.28, 0.75, 1.05, 1.5, 1.9, 2.1, 2.4),
    (160,  0.25, 0.40, 0.32, 0.80, 1.1, 1.6, 2.0, 2.2, 2.5),
    (200,  0.40, 0.63, 0.42, 1.0, 1.4, 2.0, 2.5, 2.8, 3.2),
    (250,  0.56, 1.0, 0.56, 1.25, 1.8, 2.5, 3.2, 3.6, 4.0),
    (320,  0.75, 1.6, 0.75, 1.6, 2.2, 3.2, 4.0, 4.5, 5.0),
    (400,  1.0, 2.0, 1.0, 2.0, 2.8, 4.0, 5.0, 5.6, 6.3),
    (500,  1.3, 2.5, 1.3, 2.5, 3.6, 5.0, 6.3, 7.1, 8.0),
    (630,  1.8, 3.2, 1.8, 3.2, 4.5, 6.3, 8.0, 9.0, 10.0),
]
def clearance(impulse_v, pd=2):
    col = {1: 3, 2: 4, 3: 5}[pd]
    for row in TBL4:
        if row[0] is not None and row[0] >= impulse_v: return row[col], row[0]
    return TBL4[-1][col], TBL4[-1][0]
def clearance_by_tov(tov_peak, pd=2):
    """임시 과전압(최대값) 기준, 표 4 2열 + 보간 (비고 1)"""
    col = {1: 3, 2: 4, 3: 5}[pd]
    prev = None
    for row in TBL4:
        if row[1] >= tov_peak:
            if prev is None: return row[col]
            f = (tov_peak - prev[1]) / (row[1] - prev[1])
            return round(prev[col] + f * (row[col] - prev[col]), 2)
        prev = row
    return TBL4[-1][col]
def creepage(vrms, kind='PWB_PD2'):
    idx = {'PWB_PD1':1,'PWB_PD2':2,'PD1':3,'PD2_I':4,'PD2_II':5,'PD2_IIIa':6,'PD3_I':7,'PD3_II':8,'PD3_IIIa':9}[kind]
    for row in TBL5:
        if row[0] >= vrms: return row[idx]
    return TBL5[-1][idx]

# ---- 이 제품의 전압 파라미터 ----
V_PV_MAX   = 60      # PV 최대 개방전압 (EC 63V, TVS SMCJ64A 기준 추정)
V_AC       = 220     # 계통 공칭
V_PHV      = 400     # 내부 고압 DC 버스
HIPOT_IN   = V_PV_MAX + 1200   # 8.3.2 입력측
HIPOT_OUT  = V_AC + 1200       # 8.3.2 출력측

# 표 13 — 재질/구성요소 전체 온도 한계값 (℃)
TBL13 = [('커패시터 — 전해액 타입', 65), ('커패시터 — 전해액 이외', 90), ('외부 연결 결선 단자', 60),
         ('결선 구획 내 접촉 지점', 60), ('퓨즈', 90), ('인쇄회로기판(PCB)', 105), ('절연 물질', 90)]
T_AMB_OUT = 45   # 옥외 기준 주위온도 (40±5) 의 상한

def report():
    print('=== KS C 8560:2020 기반 절연거리 산출 ===')
    print(f'PV 최대 개방전압 {V_PV_MAX} V / 계통 {V_AC} Vrms / 내부 PHV {V_PHV} Vdc')
    print(f'내전압 시험 (8.3.2): 입력측 {HIPOT_IN} Vrms, 출력측 {HIPOT_OUT} Vrms, 각 1분\n')
    imp_pv = 2500                       # 표 3 비고 4
    imp_ac = TBL3[3][2]['III']          # 300 Vrms 행, OVC III
    print(f'PV 회로 임펄스 = {imp_pv} V (표 3 비고 4, OVC II 최소)')
    print(f'AC 회로 임펄스 = {imp_ac} V (표 3, 시스템 300 Vrms 행 × OVC III)')
    c_pv, _ = clearance(imp_pv); c_ac, _ = clearance(imp_ac)
    c_ac_r, step = clearance(imp_ac + 1)   # 62109-1: 보강절연은 한 단계 위 임펄스 (4000 -> 6000)
    print(f'\n[공간거리 표 4, 오염등급 2]')
    print(f'  PV 내부/PV↔주변 기본 : {c_pv} mm  (임펄스 {imp_pv} V)')
    print(f'  AC↔주변 기본          : {c_ac} mh'.replace('mh','mm') + f'  (임펄스 {imp_ac} V)')
    print(f'  1차↔2차 보강          : {c_ac_r} mm  (임펄스 한 단계 위 {step} V)')
    tov_in = HIPOT_IN * 1.414; tov_out = HIPOT_OUT * 1.414
    print(f'  내전압 관점 입력측    : {clearance_by_tov(tov_in)} mm  (시험전압 첨두 {tov_in:.0f} V, 표 4 2열 보간)')
    print(f'  내전압 관점 출력측    : {clearance_by_tov(tov_out)} mm  (시험전압 첨두 {tov_out:.0f} V, 표 4 2열 보간)')
    print(f'\n[연면거리 표 5, 오염등급 2, FR-4 = 재료그룹 IIIa (175≤CTI<400)]')
    for v, lab in [(V_PV_MAX, 'PV 63 V'), (250, 'AC 250 V'), (V_PHV, 'PHV 400 V')]:
        print(f'  {lab:12s} PWB열 {creepage(v,"PWB_PD2"):5.3f} mm | 다른절연체 IIIa {creepage(v,"PD2_IIIa"):5.2f} mm')
    print(f'  1차↔2차 보강 = 400 V 기본 {creepage(400,"PD2_IIIa")} × 2 = {creepage(400,"PD2_IIIa")*2} mm')
    print(f'\n[표 13 온도 한계 — 옥외 기준 주위온도 {T_AMB_OUT} ℃ 에서 허용 상승]')
    for name, lim in TBL13:
        print(f'  {name:26s} {lim:3d} ℃  → 허용 상승 {lim - T_AMB_OUT:3d} K')
if __name__ == '__main__':
    report()
