/* ============================================================================
 *  IIBC DC/DC 컨버터 제어 알고리즘 (마이크로인버터 전단)
 *  Isolated Interleaved Boost Converter  —  PSIM "Simplified C Block"
 * ----------------------------------------------------------------------------
 *  참고: Ravyts et al., Energies 2020, 13, 834 (IIBC, n=5, 400V 출력)
 *
 *  역할 (2단형 마이크로인버터)
 *    PV 모듈(10~30V) --[IIBC 부스트]--> 400V DC 링크
 *    - 입력측 : P&O MPPT 로 최대전력점 추종 (PV 전압 제어)
 *    - 출력측 : DC 링크 400V 는 후단 DC/AC 인버터(MODE 1)가 정전압 제어
 *      => 본 DC/DC 단은 "전력을 끌어올리는" 역할, 버스전압은 후단이 잡는다
 *
 *  사양
 *    - 입력 Vpv     : 10 ~ 30 V (40-cell PV 모듈)
 *    - 출력 Vdc     : 400 V (후단이 정전압 유지)
 *    - 전력         : ~250 W
 *    - 변압비 n     : 5  (이상적 이득 G = 2n/(1-d))
 *    - 스위칭 fsw   : 100 kHz  (제어주기 = delt, 권장 10 us)
 *    - 인터리브     : 2개 브랜치 180도 위상차
 *
 *  제어 구조 (3계층)
 *    1) MPPT(P&O)         : 주기적으로 Vpv_ref 를 ±dV 섭동 -> 최대전력점
 *    2) PV 전압 루프 PI    : Vpv -> Vpv_ref 추종, 출력 = 입력전류 지령 iL_ref
 *    3) 입력 전류 루프 PI  : iL_total -> iL_ref 추종, 출력 = duty d
 *       + duty 피드포워드 d_ff = 1 - 2n*Vpv/Vdc
 *
 *  입출력 (Simplified C Block)
 *    입력  x[0] = Vpv   PV 전압 [V]
 *          x[1] = Ipv   PV(입력) 전류 합 [A]
 *          x[2] = Vdc   DC 링크 전압 [V]
 *    출력  y[0] = d     duty (0~1) -> 두 인터리브 캐리어(180도)와 비교
 *          y[1] = Vpv_ref  (모니터)
 *          y[2] = iL_ref   (모니터)
 *          y[3] = Ppv      (모니터)
 *          y[4] = d_ff     (모니터)
 * ==========================================================================*/

#define N_TR        5.0        /* 변압비 n                                  */
#define VDC_NOM     400.0      /* 공칭 DC 링크 전압                          */

/* MPPT (P&O) */
#define MPPT_ENABLE 1          /* 1 = MPPT 동작, 0 = 고정 Vpv_ref(VPV_FIX)   */
#define VPV_FIX     25.0       /* 고정 동작점 [V] (MPPT_ENABLE=0 일 때)      */
#define MPPT_DV     0.20       /* P&O 섭동 스텝 [V]                          */
#define MPPT_TS     2.0e-3     /* P&O 갱신 주기 [s]                          */
#define VPV_MIN     8.0
#define VPV_MAX     35.0

/* PV 전압 루프 PI (외부) : err = Vpv - Vpv_ref -> iL_ref */
#define KP_VPV      2.0
#define KI_VPV      400.0
#define ILREF_MAX   30.0       /* 입력전류 지령 상한 [A] (인터리브 합)        */

/* 입력 전류 루프 PI (내부) : err = iL_ref - Ipv -> duty 보정 */
#define KP_IL       0.02
#define KI_IL       40.0

#define D_MIN       0.05
#define D_MAX       0.95

/* ----------------------------- 상태 변수 ------------------------------- */
static int    dc_init = 0;
static double Vpv_ref = VPV_FIX;
static double vpv_int = 0.0;     /* PV 전압 루프 적분기 (iL_ref 누적) */
static double il_int  = 0.0;     /* 전류 루프 적분기 (duty 누적)     */
static double t_mppt  = 0.0;     /* MPPT 타이머 */
static double P_prev  = 0.0;     /* 직전 전력 */
static double dV_dir  = MPPT_DV; /* 현재 섭동 방향 */

/* ----------------------------- 알고리즘 -------------------------------- */
double Ts  = delt;
double Vpv = x[0];
double Ipv = x[1];
double Vdc = x[2];

double Ppv, iL_ref, ierr, d_ff, d;

if (dc_init == 0) {
    Vpv_ref = (MPPT_ENABLE ? 20.0 : VPV_FIX);
    dc_init = 1;
}

Ppv = Vpv * Ipv;

/* --- 1) MPPT : Perturb & Observe --- */
if (MPPT_ENABLE) {
    t_mppt += Ts;
    if (t_mppt >= MPPT_TS) {
        t_mppt = 0.0;
        double dP = Ppv - P_prev;
        /* dP/dV 부호로 섭동 방향 결정 :
         * 전력이 증가했으면 같은 방향 유지, 감소했으면 반전 */
        if (dP < 0.0) dV_dir = -dV_dir;
        Vpv_ref += dV_dir;
        if (Vpv_ref > VPV_MAX) Vpv_ref = VPV_MAX;
        if (Vpv_ref < VPV_MIN) Vpv_ref = VPV_MIN;
        P_prev = Ppv;
    }
} else {
    Vpv_ref = VPV_FIX;
}

/* --- 2) PV 전압 루프 ---
 * PV 에서 전류를 더 뽑으면 Vpv 가 내려간다(IV 곡선).
 * Vpv > Vpv_ref 이면 더 뽑아야 하므로 iL_ref 증가.  err = Vpv - Vpv_ref */
{
    double everr = Vpv - Vpv_ref;
    vpv_int += Ts * KI_VPV * everr;
    if (vpv_int > ILREF_MAX) vpv_int = ILREF_MAX;   /* 와인드업 방지 */
    if (vpv_int < 0.0)       vpv_int = 0.0;
    iL_ref = KP_VPV * everr + vpv_int;
    if (iL_ref > ILREF_MAX) iL_ref = ILREF_MAX;
    if (iL_ref < 0.0)       iL_ref = 0.0;
}

/* --- 3) 입력 전류 루프 + duty 피드포워드 ---
 * 부스트: duty 증가 -> 입력전류 증가.  err = iL_ref - Ipv (양의 이득)
 * 피드포워드: 정상상태 d_ff = 1 - 2n*Vpv/Vdc  (이득 2n/(1-d)) */
d_ff = 1.0 - (2.0 * N_TR * Vpv) / Vdc;
if (d_ff < D_MIN) d_ff = D_MIN;
if (d_ff > D_MAX) d_ff = D_MAX;

ierr = iL_ref - Ipv;
il_int += Ts * KI_IL * ierr;
if (il_int >  0.5) il_int =  0.5;     /* duty 보정 적분 제한 */
if (il_int < -0.5) il_int = -0.5;

d = d_ff + KP_IL * ierr + il_int;
if (d > D_MAX) { d = D_MAX; if (ierr > 0.0) il_int -= Ts * KI_IL * ierr; }
if (d < D_MIN) { d = D_MIN; if (ierr < 0.0) il_int -= Ts * KI_IL * ierr; }

/* --- 출력 --- */
y[0] = d;
y[1] = Vpv_ref;
y[2] = iL_ref;
y[3] = Ppv;
y[4] = d_ff;
