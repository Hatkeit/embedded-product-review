/* =====================================================================
 *  PSIM  Simplified C Block  -  PV 입력 액티브클램프 플라이백 제어기
 *  18-50 V (PV) / 400 V / 150 W
 *
 *  sim_verify.py 의 Ctrl 클래스와 알고리즘이 1:1 대응한다.
 *  (수치 변경 시 양쪽을 반드시 함께 고칠 것)
 *
 *  -- 블록 설정 ------------------------------------------------------
 *    Input  Ports : 3      Output Ports : 4
 *    Sampling Frequency : 25000   (= F_CTRL, 스위칭 100 kHz 의 1/4)
 *
 *    in[0] = Vpv   [V]   PV 단자전압      (분압 후 환산값)
 *    in[1] = Ipv   [A]   PV 전류          (션트 + 차동증폭 후 환산값)
 *    in[2] = Vout  [V]   400 V 버스 전압  (포토커플러 절연 피드백 환산값)
 *
 *    out[0] = Ipk*  [A]  피크전류 지령 (비교기 기준, 슬로프보상 램프 감산 전)
 *    out[1] = Vpv_ref [V] MPPT 기준전압   (모니터용)
 *    out[2] = mode       0 = 소프트스타트, 1 = MPPT, 2 = 출력전압 리미트,
 *                        3 = 전역 MPP 스캔, 4 = 입력전력 리미트
 *    out[3] = Ppv   [W]  PV 전력 (모니터용)
 *
 *  -- 하드웨어 전제 --------------------------------------------------
 *    * 피크전류모드 : out[0] 에서 슬로프보상 램프(Se = 0.6 x Sf)를 감산한
 *      값을 비교기 기준으로 쓴다.  OCP 비교기는 램프가 섞이지 않은 raw
 *      전류센스에 18.9 A 로 별도 설치한다.
 *    * out[0] 의 최대값이 OCP(18.9 A) 보다 높은 것은 정상이다.  보상램프가
 *      지령 레인지를 잠식하므로 그만큼 위로 확장하지 않으면 저입력 전부하에
 *      도달하지 못한다 (검증 T3 에서 확인된 결함).
 * ===================================================================== */

/* ---------------- 튜닝 상수 ---------------- */
#define F_CTRL        25000.0   /* 제어 주기 [Hz]                        */
#define IPK_OCP          18.9   /* HW 과전류 문턱 (raw 센스) [A]          */
#define SE_RATIO          0.60  /* 슬로프보상 Se / Sf                     */
#define LM            26.34e-6  /* 자화 인덕턴스 [H]                      */
#define N_PS              8.0   /* Ns / Np                                */
#define VF_SEC            1.8   /* 2차 SiC SBD 순전압 [V]                 */
#define D_MAX             0.78  /* 최대 듀티                              */
#define FSW             100e3   /* 스위칭 주파수 [Hz]                     */

#define KP_VIN            2.0   /* PV 전압루프 [A/V]                      */
#define KI_VIN         4000.0   /* PV 전압루프 [A/(V*s)]                  */
#define KP_VO             3.5   /* 출력 리미트루프 [A/V]                  */
#define KI_VO          1100.0   /* 출력 리미트루프 [A/(V*s)]              */

/* 리미터 기준전압.  하류 인버터가 400 V 를 세우는 구성에서는 반드시 그보다
 * 높게(420 V) 두어야 두 레귤레이터가 서로 싸우지 않는다.  본 단이 버스를
 * 직접 세우는 구성이면 400.0 으로 바꾼다. */
#define VO_REF          420.0
#define VO_DB             2.0   /* 리미터 불감대 [V]                      */
#define VO_RECOVER      300.0   /* 리미터 적분기 상향 복귀율 [A/s]        */

/* 루프 C : 입력전력 리미트.  PV 오버사이징(DC/AC ratio > 1)에서는 패널이
 * 정격 이상을 공급할 수 있으므로 반드시 필요하다.  전류지령을 줄이면 동작점이
 * MPP 오른쪽(고전압/저전류)으로 이동해 인출전력이 줄고 전류 스트레스도 준다. */
#define P_IN_MAX        166.7   /* = 150 W 출력 / eta 0.90 [W]            */
#define KP_P              0.020 /* [A/W]                                  */
#define KI_P             40.0   /* [A/(W*s)]                              */
#define P_DB              5.0   /* 불감대 [W]                             */
#define P_RECOVER       300.0   /* 적분기 상향 복귀율 [A/s]               */

#define SS_TIME          0.020  /* 소프트스타트 [s]                       */
#define TAU_I           100e-6  /* 입력전류 필터 시정수 [s]               */
#define AW_MARGIN         0.5   /* min-select 대기 마진 [A]               */
#define K_VOC             0.80  /* 기동 기준전압 = K_VOC x Voc            */

#define T_MPPT          2.0e-3  /* MPPT 주기 [s]                          */
#define DV_MIN            0.10  /* 적응 섭동폭 하한 [V]                   */
#define DV_MAX            1.50  /* 적응 섭동폭 상한 [V]                   */
#define DV_K             20.0   /* 섭동폭 = DV_K x |dP|/P                 */
#define IRR_TH            0.08  /* 일사량 급변 판정 |dP|/P                */

#define SCAN_EN              1  /* 전역 MPP 스캔 사용 (부분음영 대응)     */
#define SCAN_HI           0.95
#define SCAN_LO           0.30
#define SCAN_STEP         1.20  /* 스캔 전압 스텝 [V]                     */
#define SCAN_DWELL      2.0e-3  /* 스텝당 정착 대기 [s]                   */
#define T_RESCAN        300.0   /* 재스캔 주기 [s]                        */

#define VPV_MIN          15.0
#define VPV_MAX          52.0

/* ---------------- 상태 변수 ---------------- */
static int    init_done = 0;
static double tc, cmd_max;
static double int_vin, int_vo, int_p, vpv_ref, p_prev, dirn, ipv_f, ipk_cmd;
static double t_next_ctrl, t_next_mppt;
static double voc_est, scan_v, scan_best_p, scan_best_v, t_next_scan, t_last_scan;
static int    scanning, mode;

static double clampd(double x, double lo, double hi)
{
   if (x < lo) return lo;
   if (x > hi) return hi;
   return x;
}

/* ---------------- 본체 ---------------- */
{
   double vpv  = in[0];
   double ipv  = in[1];
   double vout = in[2];
   double alpha, ipk_ss, e_vin, e_vo, e_p, ipk_a, ipk_b, ipk_c, cmd, d_int;
   double p_pv, d_p;
   double vor, sf, p, dp, pref, step;

   if (!init_done) {
      init_done = 1;
      tc = 1.0 / F_CTRL;

      /* 전류지령 상한 = OCP + 슬로프보상 램프.  보상램프가 지령 레인지를
       * 잠식하므로 이만큼 확장하지 않으면 D = Dmax 부근에서 실제 피크전류가
       * OCP 훨씬 아래에서 막혀 정격출력에 도달하지 못한다. */
      vor     = (400.0 + VF_SEC) / N_PS;
      sf      = vor / LM;
      cmd_max = IPK_OCP + SE_RATIO * sf * (D_MAX / FSW);

      int_vin     = 0.0;
      int_vo      = cmd_max;          /* 리미터는 "무제한" 에서 시작 */
      int_p       = cmd_max;
      vpv_ref     = K_VOC * vpv;
      voc_est     = vpv;
      p_prev      = -1.0;
      dirn        = -1.0;
      ipv_f       = 0.0;
      ipk_cmd     = 0.0;
      t_next_ctrl = 0.0;
      t_next_mppt = T_MPPT;
      scanning    = SCAN_EN;          /* 기동 직후 1 회 전역 스캔 */
      scan_v      = 0.0;
      scan_best_p = -1.0;
      scan_best_v = vpv_ref;
      t_next_scan = 0.0;
      t_last_scan = 0.0;
      mode        = 0;
   }

   /* --- 입력전류 1차 필터 (션트 + RC) --- */
   alpha  = tc / (TAU_I + tc);
   ipv_f += alpha * (ipv - ipv_f);

   if (vpv > voc_est) voc_est = vpv;

   /* ================= 전역 MPP 스캔 =================
    * 부분음영이면 P-V 곡선이 다봉이 되어 단순 P&O 는 기동점 근처의 국부
    * 피크에 고착한다 (검증 T7 : 전역 MPP 대비 45 % 발전손실).
    * 전 전압구간을 쓸어 최대점을 찾은 뒤 P&O 로 복귀한다. */
   if (scanning) {
      mode = 3;
      if (t >= t_next_scan) {
         t_next_scan = t + SCAN_DWELL;
         if (scan_v <= 0.0) {
            scan_v      = SCAN_HI * voc_est;
            scan_best_p = -1.0;
            scan_best_v = vpv_ref;
         } else {
            p = vpv * ipv_f;
            if (p > scan_best_p) { scan_best_p = p; scan_best_v = vpv; }
            scan_v -= SCAN_STEP;
         }
         if (scan_v < SCAN_LO * voc_est) {
            vpv_ref     = scan_best_v;
            scanning    = 0;
            scan_v      = 0.0;
            p_prev      = -1.0;
            t_last_scan = t;
            t_next_mppt = t + T_MPPT;
         } else {
            vpv_ref = clampd(scan_v, 10.0, 60.0);
         }
      }
   } else {
      if (SCAN_EN && (t - t_last_scan) >= T_RESCAN) {
         scanning    = 1;
         t_next_scan = t;
      }

      /* ================= MPPT : 개선형 P&O =================
       * 전력 리미트가 동작 중이면 동작점이 MPP 밖에 고정되므로 P&O 를
       * 동결한다.  동결하지 않으면 기준전압이 표류한다. */
      if (t >= t_next_mppt && mode != 4) {
         t_next_mppt += T_MPPT;
         p = vpv * ipv_f;
         if (p_prev >= 0.0) {
            dp   = p - p_prev;
            pref = (p_prev > 1.0) ? p_prev : 1.0;
            if (dp > IRR_TH * pref || -dp > IRR_TH * pref) {
               /* 전압섭동으로 설명되지 않는 전력변화 = 일사량/음영 급변.
                * 방향 판정을 건너뛰어 오방향 고착을 막는다. */
               p_prev = p;
            } else {
               if (dp < 0.0) dirn = -dirn;
               step   = DV_K * ((dp < 0.0) ? -dp : dp) / ((p > 1.0) ? p : 1.0);
               step   = clampd(step, DV_MIN, DV_MAX);
               p_prev = p;
               vpv_ref = clampd(vpv_ref + dirn * step, VPV_MIN, VPV_MAX);
            }
         } else {
            p_prev  = p;
            vpv_ref = clampd(vpv_ref + dirn * DV_MIN, VPV_MIN, VPV_MAX);
         }
      }
   }

   /* ================= 전류지령 생성 ================= */
   if (t >= t_next_ctrl) {
      t_next_ctrl += tc;

      ipk_ss = cmd_max * ((t < SS_TIME) ? (t / SS_TIME) : 1.0);

      /* 루프 A : PV 전압 레귤레이션.
       * Vpv 가 기준보다 높으면 전류를 더 뽑아 동작점을 MPP 쪽으로 끌어내린다
       * (부호 주의 - 반대로 걸면 PV 는 즉시 Voc 또는 단락으로 발산한다). */
      e_vin   = vpv - vpv_ref;
      int_vin = clampd(int_vin + KI_VIN * e_vin * tc, 0.0, cmd_max);
      ipk_a   = KP_VIN * e_vin + int_vin;

      /* 루프 B : 출력 400 V 리미트 (비대칭 적분).
       * Vout 이 기준보다 충분히 낮으면 리미터는 개입할 이유가 없으므로
       * 적분기를 최소 VO_RECOVER 속도로 상향 복귀시킨다.  이것이 없으면
       * e_vo = 0 인 구간에서 적분기가 임의값에 래치되어 전류지령을 영구히
       * 제한한다 (검증 T3 에서 실제로 관측된 결함). */
      e_vo  = VO_REF - vout;
      d_int = KI_VO * e_vo * tc;
      if (e_vo > VO_DB && d_int < VO_RECOVER * tc) d_int = VO_RECOVER * tc;
      int_vo = clampd(int_vo + d_int, 0.0, cmd_max);
      ipk_b  = KP_VO * e_vo + int_vo;

      /* 루프 C : 입력전력 리미트 (비대칭 적분) */
      p_pv = vpv * ipv_f;
      e_p  = P_IN_MAX - p_pv;
      d_p  = KI_P * e_p * tc;
      if (e_p > P_DB && d_p < P_RECOVER * tc) d_p = P_RECOVER * tc;
      int_p = clampd(int_p + d_p, 0.0, cmd_max);
      ipk_c = KP_P * e_p + int_p;

      cmd = ipk_a;
      if (ipk_b < cmd) cmd = ipk_b;
      if (ipk_c < cmd) cmd = ipk_c;
      if (ipk_ss < cmd) cmd = ipk_ss;
      cmd = clampd(cmd, 0.0, cmd_max);

      /* min-select 안티와인드업 (백캘큘레이션) :
       * 지령을 만들지 '않은' 루프의 적분기를 역산해 cmd + 마진에 대기시킨다. */
      if (ipk_a > cmd + 1e-9)
         int_vin = clampd(cmd + AW_MARGIN - KP_VIN * e_vin, 0.0, cmd_max);
      if (ipk_b > cmd + 1e-9)
         int_vo  = clampd(cmd + AW_MARGIN - KP_VO * e_vo, 0.0, cmd_max);
      if (ipk_c > cmd + 1e-9)
         int_p   = clampd(cmd + AW_MARGIN - KP_P * e_p, 0.0, cmd_max);

      if (!scanning) {
         if (cmd >= ipk_ss - 1e-9)                          mode = 0;
         else if (ipk_c <= ipk_a && ipk_c <= ipk_b)         mode = 4;
         else if (ipk_b < ipk_a)                            mode = 2;
         else                                               mode = 1;
      }
      ipk_cmd = cmd;
   }

   out[0] = ipk_cmd;
   out[1] = vpv_ref;
   out[2] = (double)mode;
   out[3] = vpv * ipv_f;
}
