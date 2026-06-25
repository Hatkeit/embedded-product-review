/* ============================================================================
 *  능동 전력디커플링(APD) 제어 알고리즘
 *  Active Power Decoupling — 단상 인버터 2ω(120Hz) 맥동 흡수
 *  PSIM "Simplified C Block"
 * ----------------------------------------------------------------------------
 *  목적
 *    단상 인버터는 순시전력 p(t)=P(1-cos2ωt) 로 인해 120Hz 맥동전력이
 *    DC 링크로 역류한다. 대용량 전해캡(예 470µF) 대신, 소형 필름캡(Cd)을
 *    능동 하프브리지(리플 포트)로 크게 스윙시켜 2ω 에너지를 흡수한다.
 *    => DC 링크 벌크캡을 ~20µF 수준으로 줄이면서도 Vdc 리플을 억제.
 *       (전해캡 회피 -> 마이크로인버터 장수명 유지)
 *
 *  토폴로지 (DC 링크에 병렬로 추가되는 리플 포트)
 *      Vdc+ ──┬── Sd1 ──┬── Ld ──┬──────┐
 *             │         │        │     Cd (필름, 예 40µF/400V)
 *             │        Sd2       │      │
 *      Vdc- ──┴─────────┴────────┴──────┘
 *    Cd 전압 vCd 를 2ω 로 스윙시켜 에너지 ½Cd·vCd² 가 맥동을 상쇄.
 *
 *  제어 (캐스케이드 + 2ω 피드포워드)
 *    1) 에너지 기준 :  ½Cd·vCd_ref² = ½Cd·Vd0² + (P/2ω)·sin(2θ)
 *         vCd_ref = sqrt( Vd0² + (P/(ω·Cd))·sin(2θ) )
 *    2) 전압 루프(느림): vCd -> vCd_ref,  PI -> i_Ld 보정
 *       + 캡전류 피드포워드 i_ff = P·cos(2θ)/vCd_ref   (← 2ω 본체 담당)
 *    3) 전류 루프(빠름): i_Ld -> i_Ld_ref,  PI -> 듀티
 *       + 듀티 피드포워드 d_ff = vCd/Vdc
 *
 *  입출력 (Simplified C Block)
 *    입력  x[0] = Vdc    DC 링크 전압 [V]
 *          x[1] = iLd    APD 인덕터 전류 [A] (+: 링크->Cd 충전 방향)
 *          x[2] = vCd    디커플링 캡 전압 [V]
 *          x[3] = theta  계통 위상 [rad] (인버터 PLL 의 y[1] 연결)
 *          x[4] = Pest   추정 유효전력 [W] (인버터 Vamp*Iamp/2, 없으면 정격)
 *    출력  y[0] = d_apd   하프브리지 듀티 (0~1) -> Sd1/Sd2 PWM
 *          y[1] = vCd_ref (모니터)
 *          y[2] = iLd_ref (모니터)
 *          y[3] = p_apd   APD 흡수전력 추정 (모니터)
 * ==========================================================================*/

#define PI_C     3.14159265358979
#define W0_APD   (2.0*PI_C*60.0)   /* 계통 각주파수 */
#define CD       40.0e-6           /* 디커플링 캡 [F]  */
#define VD0      200.0             /* Cd 평균 전압 [V] */
#define PEST_DEF 250.0             /* Pest 미입력 시 기본 정격 [W] */

/* 전압 루프(느림) : vCd_ref - vCd -> iLd 보정 */
#define KP_VC    0.6
#define KI_VC    30.0
#define ILD_MAX  8.0               /* APD 인덕터 전류 제한 [A] */

/* 전류 루프(빠름) : iLd_ref - iLd -> 듀티 보정 */
#define KP_ILD   12.0
#define KI_ILD   800.0

#define DAPD_MIN 0.02
#define DAPD_MAX 0.98

/* ----------------------------- 상태 변수 ------------------------------- */
static double vc_int  = 0.0;     /* 전압 루프 적분기 (iLd 누적) */
static double ild_int = 0.0;     /* 전류 루프 적분기 (듀티 누적) */

/* ----------------------------- 알고리즘 -------------------------------- */
double Ts    = delt;
double Vdc   = x[0];
double iLd   = x[1];
double vCd   = x[2];
double theta = x[3];
double Pest  = x[4];

double s2, c2, vCd_ref, i_ff, iLd_ref, ierr, verr, vmid_ref, d_apd, p_apd;

if (Pest < 1.0) Pest = PEST_DEF;     /* 미연결 보호 */
if (Vdc  < 1.0) Vdc  = 1.0;

s2 = sin(2.0*theta);
c2 = cos(2.0*theta);

/* --- 1) 에너지 기반 캡 전압 기준 --- */
{
    double arg = VD0*VD0 + (Pest/(W0_APD*CD))*s2;
    if (arg < 100.0) arg = 100.0;     /* sqrt 보호 (vCd_ref >= 10V) */
    vCd_ref = sqrt(arg);
}

/* --- 2) 전압 루프(느림) + 2ω 캡전류 피드포워드 ---
 * i_ff = Cd·d(vCd_ref)/dt = P·cos(2θ)/vCd_ref  (2ω 본체)
 * PI 는 평균/저주파 오차만 보정 */
i_ff = Pest * c2 / vCd_ref;
verr = vCd_ref - vCd;
vc_int += Ts * KI_VC * verr;
if (vc_int >  ILD_MAX) vc_int =  ILD_MAX;
if (vc_int < -ILD_MAX) vc_int = -ILD_MAX;
iLd_ref = i_ff + KP_VC * verr + vc_int;
if (iLd_ref >  ILD_MAX) iLd_ref =  ILD_MAX;
if (iLd_ref < -ILD_MAX) iLd_ref = -ILD_MAX;

/* --- 3) 전류 루프(빠름) + 듀티 피드포워드 ---
 * Ld·diLd/dt = d·Vdc - vCd  ->  vmid_ref = vCd + PI(iLd_ref - iLd) */
ierr = iLd_ref - iLd;
ild_int += Ts * KI_ILD * ierr;
if (ild_int >  Vdc) ild_int =  Vdc;
if (ild_int < -Vdc) ild_int = -Vdc;
vmid_ref = vCd + KP_ILD * ierr + ild_int;
d_apd = vmid_ref / Vdc;

if (d_apd > DAPD_MAX) { d_apd = DAPD_MAX; if (ierr > 0.0) ild_int -= Ts*KI_ILD*ierr; }
if (d_apd < DAPD_MIN) { d_apd = DAPD_MIN; if (ierr < 0.0) ild_int -= Ts*KI_ILD*ierr; }

p_apd = vCd * iLd;     /* APD 가 흡수 중인 순시전력(추정) */

/* --- 출력 --- */
y[0] = d_apd;
y[1] = vCd_ref;
y[2] = iLd_ref;
y[3] = p_apd;
