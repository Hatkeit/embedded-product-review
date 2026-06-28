/* ============================================================================
 *  HF-Link 사이클로컨버터형 단일단 절연 인버터 제어
 *  (DC 풀브리지 + 고주파 변압기 + AC측 사이클로컨버터)
 *  PSIM "Simplified C Block"
 * ----------------------------------------------------------------------------
 *  토폴로지 (입력 그림 Figure 2-1)
 *    Vin(DC) ─[풀브리지 Q1~Q4]─HFAC→[변압기 n]→[L1]─[사이클로컨버터 S1A/B,S2A/B]→ 계통
 *    - 중간 DC 링크 없음(단일단). 효과 출력전압 = n·Vin
 *    - 사이클로컨버터 = 4상한(양방향) 스위치: S1A+S1B(상), S2A+S2B(하) 각각 등맞대기
 *
 *  사양 (예: 저전압 PV/배터리 입력 단일단 마이크로인버터)
 *    - 입력 Vin    : 약 50 V (가변)         - 변압비 n : 8  => n·Vin ≈ 400 V
 *    - 계통        : 220 Vrms / 60 Hz (피크 311 V < 400 V)
 *    - 전력        : 250 W,  역률 1
 *    - HF 링크     : fs = 50 kHz (풀브리지·사이클로 동기)
 *    - 출력 필터   : L1 = 5 mH
 *
 *  제어 = 2계층
 *    (A) 제어법 : SOGI-PLL + PR 전류제어 -> 인버터 전압지령 v_inv_ref
 *                 변조지수 m = v_inv_ref / (n·Vin)        (-1~1)
 *    (B) 변조   : HF 풀브리지가 |m| 듀티로 PWM(능동/프리휠),
 *                 사이클로컨버터가 sign(m)·(HF극성)에 따라 출력 극성 언폴딩
 *       => HF 1주기 평균 출력 = n·Vin·m = v_inv_ref  (검증완료)
 *
 *  입출력 (Simplified C Block : 입력 3 / 출력 11)
 *    입력  x[0]=Vgrid  x[1]=Igrid(+: 인버터->계통)  x[2]=Vin(DC 입력)
 *    출력  y[0..3]  = Q1,Q2,Q3,Q4   (DC측 풀브리지 게이트, 1=ON)
 *          y[4..7]  = S1A,S1B,S2A,S2B (AC측 사이클로컨버터 게이트)
 *          y[8]=m   y[9]=iref   y[10]=theta   (모니터)
 *
 *  ※ 커뮤테이션 주의: 사이클로 상/하 전환 시 4상한 스위치는 매트릭스컨버터식
 *     4-step(다단계) 커뮤테이션 또는 RC/능동 클램프가 필요(인덕성 전류 단속 금지).
 *     본 코드는 제어법+변조 로직을 제공하며, 데드/오버랩 타이밍은 DT_HF 로 표기.
 * ==========================================================================*/

#define PI_C     3.14159265358979
#define F_GRID   60.0
#define W0       (2.0*PI_C*F_GRID)
#define VGRMS    220.0
#define P_REF    250.0

#define NTR      8.0          /* 변압비 n */
#define FS_HF    50000.0      /* HF 링크 주파수 [Hz] */
#define L1F      5.0e-3       /* 출력 필터 인덕턴스 (모니터/참고) */

/* PR 전류 제어기 (BW ~1.5kHz, L1=5mH 기준) */
#define KP_I     47.0
#define KI_R     2000.0
#define WC_R     10.0
/* SOGI-PLL */
#define SOGI_K   1.41421356
#define KP_PLL   180.0
#define KI_PLL   3200.0

#define IAMP_MAX 2.0
#define M_MAX    0.95
#define DT_HF    0.0          /* 커뮤테이션 오버랩 듀티(0~)·시뮬참고 */

/* ----------------------------- 상태 변수 ------------------------------- */
static int    cy_init = 0;
static double sogi_a = 0.0, sogi_b = 0.0;
static double theta  = 0.0,  w_pll = W0,  pll_int = 0.0;
static double xr1 = 0.0, xr2 = 0.0;

/* ----------------------------- 알고리즘 -------------------------------- */
double Ts  = delt;
double Vg  = x[0];
double Ig  = x[1];
double Vin = x[2];

double vd, vq, Vamp, ferr, Iamp, iref, ierr, u_res, u_pr, vinv_ref, Veff, m;
double ph, localph, dmag;
int    halfA, active, s_pos, top_on;
double Q1=0,Q2=0,Q3=0,Q4=0, S1A=0,S1B=0,S2A=0,S2B=0;

if (cy_init == 0) { theta=0.0; w_pll=W0; cy_init=1; }
if (Vin < 1.0) Vin = 1.0;

/* === (A) 제어법 ======================================================== */
/* 1) SOGI : 직교신호 */
{
    double e = SOGI_K*(Vg - sogi_a) - sogi_b;
    sogi_a += Ts * (w_pll * e);
    sogi_b += Ts * (w_pll * sogi_a);
}
/* 2) Park + SRF-PLL */
{
    double ct=cos(theta), st=sin(theta);
    vd =  sogi_a*ct + sogi_b*st;
    vq = -sogi_a*st + sogi_b*ct;
    Vamp = sqrt(vd*vd+vq*vq); if (Vamp<1.0) Vamp=1.0;
    ferr = vd/Vamp;
    pll_int += Ts*KI_PLL*ferr;
    w_pll = W0 + KP_PLL*ferr + pll_int;
    theta += Ts*w_pll;
    if (theta>=2.0*PI_C) theta-=2.0*PI_C;
    if (theta<0.0)       theta+=2.0*PI_C;
}
/* 3) 전류 진폭 지령 (전력모드: P=Vamp*Iamp/2) */
Iamp = 2.0*P_REF/Vamp;
if (Iamp>IAMP_MAX) Iamp=IAMP_MAX;
if (Iamp<0.0)      Iamp=0.0;
iref = Iamp*sin(theta);

/* 4) PR 전류 제어 + 계통전압 피드포워드 */
ierr = iref - Ig;
xr1 += Ts*xr2;
xr2 += Ts*(ierr - W0*W0*xr1 - 2.0*WC_R*xr2);
u_res = KI_R*(2.0*WC_R*xr2);
u_pr  = KP_I*ierr + u_res;
vinv_ref = u_pr + Vg;

/* 5) 변조지수 m = v_inv_ref / (n·Vin) */
Veff = NTR*Vin;
m = vinv_ref / Veff;
if (m >  M_MAX) { m =  M_MAX; if (ierr>0.0) xr2 -= Ts*(ierr - W0*W0*xr1 - 2.0*WC_R*xr2); }
if (m < -M_MAX) { m = -M_MAX; if (ierr<0.0) xr2 -= Ts*(ierr - W0*W0*xr1 - 2.0*WC_R*xr2); }

/* === (B) 변조 -> 게이트 ================================================ */
/* HF 캐리어 위상 (t 사용) */
ph = t*FS_HF;
ph = ph - floor(ph);                 /* 0..1 */
halfA   = (ph < 0.5);                 /* 전반 = 1차 +극성, 후반 = -극성 */
localph = halfA ? (ph*2.0) : ((ph-0.5)*2.0);   /* 각 반주기 내 0..1 */
dmag    = fabs(m);
if (dmag > M_MAX) dmag = M_MAX;
active  = (localph < dmag);           /* PWM 능동구간(아니면 프리휠) */
s_pos   = (m >= 0.0);

/* --- DC측 풀브리지 ---
 *   능동 & halfA : +Vp (Q1,Q4)   /  능동 & halfB : -Vp (Q2,Q3)
 *   프리휠       : 상단 단락(Q1,Q3) -> 1차 0V */
if (active) {
    if (halfA) { Q1=1; Q4=1; }
    else       { Q2=1; Q3=1; }
} else {
    Q1=1; Q3=1;                       /* top freewheel */
}

/* --- AC측 사이클로컨버터(언폴딩) ---
 *   출력 극성 sign(m) 유지하도록 HF 극성에 맞춰 상/하 선택
 *   top_on = (halfA == s_pos)
 *   선택된 양방향 스위치는 직렬 2소자(A,B) 동시 ON */
top_on = (halfA == s_pos);
if (top_on) { S1A=1; S1B=1; }
else        { S2A=1; S2B=1; }
/* (DT_HF>0 이면 전환구간 상/하 오버랩으로 4상한 전류경로 확보 — 회로단에서 적용) */

/* --- 출력 --- */
y[0]=Q1; y[1]=Q2; y[2]=Q3; y[3]=Q4;
y[4]=S1A; y[5]=S1B; y[6]=S2A; y[7]=S2B;
y[8]=m;  y[9]=iref; y[10]=theta;
