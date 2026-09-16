/*=====================================================================
  buildindc1608.il
  INDC1608X95M   (1608 metric / 0603 inch 칩 페라이트 비드)
  대상 부품: Murata BLM18SP300SN1D

  근거: Murata Reference Specification JENF243A_0003AM-01
        - p.1  3. Part Number and Rating
               BLM18SP300SN1D : 30±10Ω @100MHz, 정격전류 6000mA(85°C)/4000mA(125°C),
               DCR 0.008Ω max(초기) / 0.010Ω(시험후), -55~+125°C
        - p.5  5. Appearance and Dimensions
               L 1.6±0.15 / W 0.8±0.15 / T 0.8±0.15 (BLM18*****SN1*)
               전극 밴드 0.4±0.2 / no polarity
        - p.10 12.1 Land dimensions  (벤더 권장랜드 = 있음)
               <Applied to BLM18P, BLM18S, BLM18K types>  -- BLM18SP 는 여기 해당
               Reflow : a(랜드 간극) 0.7 / b(외측-외측) 2.0 / c(랜드 폭) 0.7
               Flow   : a 0.8 / b 2.5 / c 0.7
               -> 랜드 길이 = (b - a)/2 = 0.65, 내측 edge 0.35, 외측 edge 1.00

  !! 데이터시트 전 페이지에 "Reference Only" 워터마크가 있다.
     정식 승인 사양서가 아니므로, 양산 투입 전 Murata 승인 사양서로 재확인할 것.

  실행:
    copy seed.dra indc1608x95m.dra
    echo skill load("<절대경로>/buildindc1608.il") > run.scr
    allegro.exe -nograph -s run.scr indc1608x95m.dra

  좌표계: TOP VIEW. 원점 = 부품 중심. 무극성 2단자 (핀1 좌 / 핀2 우).
 =====================================================================*/

WORKDIR = "D:/fp/indc1608/"                 ; <<< 사용자 수정: 로그 출력 폴더

SYM      = "indc1608x95m"
PAD      = "R103_70"                        ; 1.03 x 0.70 (토 연장분 포함)

;--- 데이터시트 원문값 (mm) --------------------------------------------
BODY_L   = 1.6         ; p.5  L (±0.15)
BODY_W   = 0.8         ; p.5  W (±0.15)
BODY_T   = 0.8         ; p.5  T (±0.15)
TOL      = 0.15
ELEC     = 0.4         ; p.5  전극 밴드 (±0.2)
BODY_LMX = BODY_L + TOL        ; 1.75  최대재료조건
BODY_WMX = BODY_W + TOL        ; 0.95
BODY_TMX = BODY_T + TOL        ; 0.95
;--- 벤더 권장랜드 (p.10, Reflow) --------------------------------------
DS_A     = 0.7         ; 랜드 간극 (내측-내측)
DS_B     = 2.0         ; 외측-외측
DS_C     = 0.7         ; 랜드 폭
DS_LL    = (DS_B - DS_A)/2.0            ; 0.65  랜드 길이
IEDGE    = DS_A/2.0                     ; 0.35  힐 -- 원문 유지
DS_LC    = (IEDGE + IEDGE + DS_LL)/2.0  ; 0.675 벤더 랜드 중심
;--- 사내 규칙 2 적용: 토만 연장 ---------------------------------------
TOE_REQ  = 0.50
BODY_END = BODY_LMX/2.0                 ; 0.875  바디 끝 (최대재료조건)
OEDGE    = 1.38                         ; = round_up(0.875 + 0.50) -> 노출 0.505
LAND_L   = OEDGE - IEDGE                ; 1.03
LAND_C   = (OEDGE + IEDGE)/2.0          ; 0.865
;--- 페이스트: 규칙 4 (칩 = 데이터시트 솔더량 유지, offset 패드) --------
PST_OFF  = LAND_C - DS_LC               ; 0.19  로컬 +x = 부품 중심 방향

;--- 그 외 -------------------------------------------------------------
SILK_W   = 0.1
ASSY_W   = 0.1
CLR      = 0.1
BLX      = BODY_LMX/2.0                 ; 0.875
BWY      = BODY_WMX/2.0                 ; 0.475
SILK_Y   = DS_C/2.0 + SILK_W/2.0 + CLR  ; 0.50 -> 0.55 로 올려 여유 확보
SILK_Y   = 0.55
PB_X     = OEDGE + CLR                  ; 1.48
PB_Y     = SILK_Y + SILK_W/2.0 + CLR    ; 0.70

L_SILK = "PACKAGE GEOMETRY/SILKSCREEN_TOP"
L_ASSY = "PACKAGE GEOMETRY/ASSEMBLY_TOP"
L_PB   = "PACKAGE GEOMETRY/PLACE_BOUND_TOP"

;======================= 로그 =========================================
LOGP = outfile(strcat(WORKDIR "build_indc1608.log") "w")
procedure(LOG(fmt @rest a)
  let((s)
    s = lsprintf(fmt @a)
    printf("%s\n" s)
    fprintf(LOGP "%s\n" s)
    drain(LOGP)                      ; 에러 시 버퍼 유실 방지
  )
)

LOG("=== build %s ===" SYM)
LOG("vendor land %.2f x %.2f  ie=%.2f oe=%.2f c=%.3f" DS_LL DS_C IEDGE IEDGE+DS_LL DS_LC)
LOG("applied land %.2f x %.2f  ie=%.2f oe=%.2f c=%.3f poff=%.2f"
    LAND_L DS_C IEDGE OEDGE LAND_C PST_OFF)
LOG("toe exposed = %.3f (>= %.2f)" OEDGE-BODY_END TOE_REQ)
LOG("land gap = %.2f (>= 0.20)" 2.0*IEDGE)

;======================= 0. 설계 범위 =================================
axlDBChangeDesignExtents(list(-15.0:-15.0 15.0:15.0))

;======================= 1. 패드스택 ==================================
; 함정: 정사각이면 'SQUARE. 1.03 x 0.70 이므로 'RECTANGLE 로 안전.
let((pl)
  pl = list()
  pl = cons(make_axlPadStackPad(?layer "TOP"            ?type 'REGULAR
            ?figure 'RECTANGLE ?figureSize LAND_L:DS_C) pl)
  ; 규칙 6: 칩 패밀리 관례 -- 마스크는 동판을 따라간다 (1:1).
  ;         데이터시트가 별도 마스크 비율을 주지 않는다.
  pl = cons(make_axlPadStackPad(?layer "SOLDERMASK_TOP" ?type 'REGULAR
            ?figure 'RECTANGLE ?figureSize LAND_L:DS_C) pl)
  ; 규칙 4: 칩 -> 데이터시트 솔더량 유지. 벤더 랜드(0.65) 만큼만 단자 위로 오프셋.
  pl = cons(make_axlPadStackPad(?layer "PASTEMASK_TOP"  ?type 'REGULAR
            ?figure 'RECTANGLE ?figureSize DS_LL:DS_C ?offset PST_OFF:0.0) pl)
  axlDBCreatePadStack(PAD nil pl t)
  axlPadstackToDisk(PAD)
  LOG("padstack %s copper %.2fx%.2f paste %.2fx%.2f off %.2f"
      PAD LAND_L DS_C DS_LL DS_C PST_OFF)
)

;======================= 2. 핀 ========================================
procedure(MKPIN(num x rot)
  axlDBCreatePin(PAD x:0.0
    make_axlPinText(?number num ?offset 0.0:0.0
      ?text make_axlTextOrientation(?textBlock "1" ?rotation 0.0
            ?mirrored nil ?justify "center"))
    rot)
)
MKPIN("1" (-LAND_C)   0.0)
MKPIN("2" ( LAND_C) 180.0)

;======================= 3. 레이어 초기화 =============================
axlDeleteByLayer(list(L_SILK L_ASSY L_PB
                      "REF DES/SILKSCREEN_TOP" "REF DES/ASSEMBLY_TOP"))

;======================= 4. 실크 (규칙 7: 패드에서 0.1) ===============
; 패드는 y ±0.35 / x 0.35~1.38 를 차지한다.
; 가로선 y=±0.55 (선폭 0.1 -> 0.50~0.60) 는 패드 상단 0.35 에서 0.15 떨어져 안전.
; 세로 끝선은 패드 안으로 들어가므로 그리지 않는다.
axlDBCreateLine(list((-BLX):SILK_Y    BLX:SILK_Y)    SILK_W L_SILK)
axlDBCreateLine(list((-BLX):(-SILK_Y) BLX:(-SILK_Y)) SILK_W L_SILK)

;======================= 5. 어셈블리 (한 붓) ==========================
; 무극성이므로 극성 표시 없음.
axlDBCreateLine(
  list((-BLX):(-BWY) BLX:(-BWY) BLX:BWY (-BLX):BWY (-BLX):(-BWY))
  ASSY_W L_ASSY)

;======================= 6. PLACE_BOUND (채운 사각형) =================
axlDBCreateRectangle(list((-PB_X):(-PB_Y) PB_X:PB_Y) t L_PB)

;======================= 7. REFDES (규칙 12) ==========================
RX = -PB_X + 0.4               ; -1.08
RY = DS_C/2.0 + 0.35           ;  0.70
foreach(lyr list("REF DES/SILKSCREEN_TOP" "REF DES/ASSEMBLY_TOP")
  axlDBCreateText("#REFDES" RX:RY
    make_axlTextOrientation(?textBlock "21" ?rotation 0.0
      ?mirrored nil ?justify "left") lyr))

;======================= 8. 정리 / 검증 / 저장 ========================
axlPurgePadstacks('padstacks nil)

nDRC = axlDRCUpdate(t)                  ; 반드시 강제 실행
LOG("DRC = %L" nDRC)

axlSaveDesign(?noConfirm t)
axlCompileSymbol(?symbol SYM ?type "PACKAGE")

LOG("=== done: %s ===" SYM)
close(LOGP)
