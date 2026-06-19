/* ============================================================================
 *  단상 계통연계형 인버터 제어 알고리즘  (Single-Phase Grid-Tied Inverter)
 *  PSIM "Simplified C Block" 용 소스
 * ----------------------------------------------------------------------------
 *  사양 (Specification)
 *    - DC 링크 전압  Vdc      = 400 V
 *    - 정격 출력     Po       = 250 W
 *    - 계통 전압     Vgrid    = 220 Vrms (peak 311.13 V), 60 Hz
 *    - 토폴로지      단상 풀브리지(H-Bridge) + L 필터, 유니폴라 SPWM
 *    - 스위칭 주파수 fsw      = 20 kHz  (제어 샘플링 = 50 us, delt 사용)
 *
 *  제어 구조 (Control Architecture)
 *    1) SOGI-PLL          : 계통 전압 위상(theta)·주파수·진폭 추정
 *    2) 외부 루프          : 전력 지령(MODE 0) 또는 DC 링크 전압(MODE 1) -> 전류 진폭 Iamp
 *    3) 전류 지령          : iref = Iamp * sin(theta)   (역률 1, 계통 동기)
 *    4) PR 전류 제어기      : 60Hz 에서 무한 이득 -> 정상상태 오차 0
 *    5) 계통 전압 피드포워드 : 동특성 개선
 *    6) 변조신호 m 출력     : 유니폴라 SPWM 비교용 (-1 ~ +1)
 *
 *  C 블록 입출력 (Simplified C Block I/O)
 *    입력  x[0] = Vgrid  계통 전압 측정 [V]
 *          x[1] = Igrid  인덕터(계통) 전류 측정 [A]  (+: 인버터->계통 방향)
 *          x[2] = Vdc    DC 링크 전압 측정 [V]
 *    출력  y[0] = m      변조 지령 (-1~1) -> 삼각파 캐리어와 비교 (PWM)
 *          y[1] = theta  PLL 위상 [rad]      (모니터링)
 *          y[2] = iref   전류 지령 [A]        (모니터링)
 *          y[3] = Iamp   전류 진폭 지령 [A]   (모니터링)
 *          y[4] = Vamp   계통 전압 진폭 추정 [V] (모니터링)
 *          y[5] = ferr   PLL 위상오차 (모니터링)
 * ==========================================================================*/

/* ----------------------------- 설정 / 파라미터 -------------------------- */
#define MODE         0          /* 0 = 전력지령(250W) 제어, 1 = DC링크전압 제어 */

#define PI_CONST     3.14159265358979
#define F_GRID       60.0                       /* 계통 주파수 [Hz]         */
#define W0           (2.0*PI_CONST*F_GRID)       /* 계통 각주파수 [rad/s]    */

#define VDC_REF      400.0       /* DC 링크 전압 지령 [V]  (MODE 1)          */
#define P_REF        250.0       /* 유효전력 지령 [W]      (MODE 0)          */
#define VGRID_RMS    220.0
#define VGRID_PEAK   (VGRID_RMS*1.41421356)      /* 311.13 V                */

#define L_FILT       5.0e-3      /* 필터 인덕턴스 [H]                        */
#define R_FILT       0.1         /* 필터 등가저항 [ohm]                      */

/* --- SOGI-PLL 이득 --- */
#define SOGI_K       1.41421356  /* SOGI 댐핑 게인 (sqrt2)                   */
#define KP_PLL       180.0       /* PLL 비례이득 (정규화 오차 기준)          */
#define KI_PLL       3200.0      /* PLL 적분이득                             */

/* --- PR 전류 제어기 이득 (BW ~ 1.5kHz) --- */
#define KP_I         47.0        /* 비례이득 = wc*L                          */
#define KI_R         2000.0      /* 공진 이득 (60Hz 부스트)                  */
#define WC_R         10.0        /* 공진 대역폭 [rad/s] (선택도 조절)        */

/* --- DC 링크 전압 PI (MODE 1) --- */
#define KP_V         0.5
#define KI_V         20.0

#define IAMP_MAX     2.0         /* 전류 진폭 제한 [A] (정격 1.61A 의 ~1.2배) */
#define M_MAX        0.98        /* 변조 지수 제한                            */

/* ----------------------------- 상태 변수 ------------------------------- */
static int    init_done = 0;
/* SOGI 상태 */
static double sogi_a = 0.0;      /* v'  (in-phase)   */
static double sogi_b = 0.0;      /* qv' (quadrature) */
/* PLL 상태 */
static double theta  = 0.0;
static double w_pll  = W0;
static double pll_int = 0.0;
/* PR 공진 적분기 상태 */
static double xr1 = 0.0;
static double xr2 = 0.0;
/* DC 전압 PI 적분기 */
static double vdc_int = 0.0;

/* ----------------------------- 알고리즘 -------------------------------- */
double Ts   = delt;             /* PSIM 시뮬레이션 스텝 = 제어 주기 */
double Vg   = x[0];             /* 계통 전압 측정 */
double Ig   = x[1];             /* 계통 전류 측정 */
double Vdc  = x[2];             /* DC 링크 전압 측정 */

double vd, vq, Vamp, ferr;
double Iamp, iref, ierr, u_res, u_pr, vinv_ref, m;

if (init_done == 0) {
    theta  = 0.0;
    w_pll  = W0;
    init_done = 1;
}

/* --- 1) SOGI : 직교 신호 생성 (전향 오일러 적분) ---
 *   dv'/dt  = w*( K*(Vg - v') - qv' )
 *   dqv'/dt = w*v'
 *   v'  : 계통 전압과 동상,  qv' : 90도 지상 */
{
    double e_sogi = SOGI_K * (Vg - sogi_a) - sogi_b;
    double da = w_pll * e_sogi;
    double db = w_pll * sogi_a;
    sogi_a += Ts * da;
    sogi_b += Ts * db;
}

/* --- 2) Park 변환 & SRF-PLL ---
 *   v' = V*sin(theta_g), qv' = -V*cos(theta_g)
 *   vd = v'*cos + qv'*sin = V*sin(theta_g - theta)  -> 위상오차(0 으로 제어)
 *   vq = -v'*sin + qv'*cos = -V*cos(theta_g - theta) -> 잠금시 -V */
{
    double ct = cos(theta);
    double st = sin(theta);
    vd =  sogi_a*ct + sogi_b*st;      /* 위상 오차항 */
    vq = -sogi_a*st + sogi_b*ct;      /* 진폭 관련항 */
    Vamp = sqrt(vd*vd + vq*vq);       /* 계통 전압 진폭 추정 */
    if (Vamp < 1.0) Vamp = 1.0;       /* 0 나눗셈 보호 */

    ferr = vd / Vamp;                 /* 정규화 위상 오차 -> 0 으로 제어 */

    pll_int += Ts * KI_PLL * ferr;    /* 적분기 */
    w_pll = W0 + KP_PLL * ferr + pll_int;

    theta += Ts * w_pll;              /* 위상 적분 */
    if (theta >= 2.0*PI_CONST) theta -= 2.0*PI_CONST;
    if (theta <  0.0)          theta += 2.0*PI_CONST;
}

/* --- 3) 외부 루프 : 전류 진폭 지령 Iamp 산출 --- */
if (MODE == 1) {
    /* DC 링크 전압 제어 : Vdc > Vref 이면 더 많이 송전(Iamp 증가) */
    double everr = Vdc - VDC_REF;
    vdc_int += Ts * KI_V * everr;
    if (vdc_int >  IAMP_MAX) vdc_int =  IAMP_MAX;   /* 적분 와인드업 방지 */
    if (vdc_int < 0.0)       vdc_int = 0.0;
    Iamp = KP_V * everr + vdc_int;
} else {
    /* 전력 지령 제어 : P = Vamp*Iamp/2  ->  Iamp = 2P/Vamp */
    Iamp = 2.0 * P_REF / Vamp;
}
if (Iamp >  IAMP_MAX) Iamp =  IAMP_MAX;
if (Iamp <  0.0)      Iamp =  0.0;

/* --- 4) 전류 지령 (계통 동상, 역률 1) --- */
iref = Iamp * sin(theta);

/* --- 5) PR(비례공진) 전류 제어기 ---
 *   공진부 R(s) = 2*wc*s / (s^2 + 2*wc*s + w0^2),  60Hz 에서 이득=1
 *   상태공간(전향 오일러):
 *     xr1' = xr2
 *     xr2' = err - w0^2*xr1 - 2*wc*xr2
 *     u_res = KI_R * (2*wc*xr2) */
ierr = iref - Ig;
{
    double dxr1 = xr2;
    double dxr2 = ierr - W0*W0*xr1 - 2.0*WC_R*xr2;
    xr1 += Ts * dxr1;
    xr2 += Ts * dxr2;
    u_res = KI_R * (2.0*WC_R*xr2);
}
u_pr = KP_I * ierr + u_res;

/* --- 6) 계통 전압 피드포워드 + 변조신호 생성 ---
 * 풀브리지(H-Bridge) 차동 출력 = m*Vdc (범위 -Vdc~+Vdc).
 * 따라서 m = vinv_ref / Vdc 로 정규화 (반브리지의 Vdc/2 아님).
 * 계통 피크 311V < Vdc(400V) 이므로 선형 변조영역에서 동작. */
vinv_ref = u_pr + Vg;               /* 인버터 출력 전압 지령 */
m = vinv_ref / Vdc;                 /* Vdc 로 정규화 (-1~1) */

/* 변조지수 포화 + 적분 와인드업 방지 :
 * 포화 시 공진 적분기를 오차와 같은 방향으로 더 키우지 않도록 동결(되감기) */
if (m > M_MAX) {
    m = M_MAX;
    if (ierr > 0.0) xr2 -= Ts * (ierr - W0*W0*xr1 - 2.0*WC_R*xr2);
}
else if (m < -M_MAX) {
    m = -M_MAX;
    if (ierr < 0.0) xr2 -= Ts * (ierr - W0*W0*xr1 - 2.0*WC_R*xr2);
}

/* --- 출력 --- */
y[0] = m;
y[1] = theta;
y[2] = iref;
y[3] = Iamp;
y[4] = Vamp;
y[5] = ferr;
