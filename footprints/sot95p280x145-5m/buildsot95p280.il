/*=====================================================================
  buildsot95p280.il
  SOT95P280X145-5M   (TI DBV0005A = SOT-23-5)
  대상 부품: TLV7041 (TLV703x/704x 비교기)

  근거: TI SLVSE13J (2017-09 / rev 2024-11)
        - p.3  4.1 Pin Functions, Figure 4-1 "North West" Pinout, DBV, SOT-23-5, Top View
               Table 4-1 : OUT=1, V-=2, IN+=3, IN-=4, V+=5
        - p.59 PACKAGE OUTLINE  DBV0005A  4214839/K 08/2024  (JEDEC MO-178)
               리드스팬 E 2.6~3.0 / 피치 0.95 (2x0.95 = 1.9)
               바디 A(D) 2.75~3.05 / B(E1) 1.45~1.75 / 높이 1.45 MAX
               리드폭 0.3~0.5 / 리드발 0.3~0.6 TYP / 스탠드오프 0.00~0.15
        - p.60 EXAMPLE BOARD LAYOUT  (벤더 권장랜드 = 있음)
               패드 5X (1.1) x 5X (0.6), 피치 2X (0.95), 행간 (2.6), 핀스팬 (1.9)
               솔더마스크 NSMD(PREFERRED), 0.07 MIN ARROUND
        - p.61 EXAMPLE STENCIL DESIGN
               스텐실 = 랜드와 동일 (1.1 x 0.6), 0.125mm 스텐실 기준

  검증: p.60 도면에서 (2.6) 치수선의 화살표가 좌/우 패드의 '중심선'에 물리는 것을
        렌더링으로 확인했다 -> (2.6) = 패드 중심-중심.
        패드 외측 = 1.3 + 0.55 = 1.85, 내측 = 1.3 - 0.55 = 0.75.
        같은 데이터시트의 DCK(SC-70-5)/DDF 도면도 동일 규약이며
        모두 토 0.35 로 일관되어 교차검증된다.

  !! 이 데이터시트에는 SOT-23-5 핀아웃이 3종 있다 (TLV7041 / 7041S / 7041L).
     패키지·랜드는 완전히 동일하므로 풋프린트는 하나면 된다. 구분은 심볼/디바이스
     쪽에서 한다. 아래 핀이름은 표준 TLV7041("North West") 기준이다.

  실행:
    copy seed.dra sot95p280x145-5m.dra
    echo skill load("<절대경로>/buildsot95p280.il") > run.scr
    allegro.exe -nograph -s run.scr sot95p280x145-5m.dra

  좌표계: p.3 Top View 방향. 원점 = 패키지 중심.
          핀1 좌상 / 2 좌중 / 3 좌하 / 4 우하 / 5 우상.
 =====================================================================*/

WORKDIR = "D:/fp/sot95p280/"                ; <<< 사용자 수정: 로그 출력 폴더

SYM      = "sot95p280x145-5m"
PAD      = "R125_60"                        ; 1.25 x 0.60 (토 연장분 포함)

;--- 데이터시트 원문값 (mm) --------------------------------------------
PITCH    = 0.95        ; p.59
SPAN_MAX = 3.0         ; p.59 리드스팬 E max
BODY_D   = 3.05        ; p.59 A max  (3핀 줄 방향)
BODY_E1  = 1.75        ; p.59 B max  (리드 방향)
;--- 벤더 권장랜드 (p.60) ----------------------------------------------
DS_LL    = 1.1         ; 패드 길이 (리드 방향)
DS_LW    = 0.6         ; 패드 폭   (피치 방향)
DS_ROW   = 2.6         ; 좌우 패드 중심-중심
DS_LC    = DS_ROW/2.0                   ; 1.3
IEDGE    = DS_LC - DS_LL/2.0            ; 0.75  힐 -- 원문 유지
MASK_EXP = 0.07        ; p.60 NSMD, 0.07 MIN ARROUND (규칙 6: 데이터시트 우선)
;--- 사내 규칙 2 적용: 토만 연장 ---------------------------------------
TOE_REQ  = 0.50
LEAD_TIP = SPAN_MAX/2.0                 ; 1.50
OEDGE    = LEAD_TIP + TOE_REQ           ; 2.00
LAND_L   = OEDGE - IEDGE                ; 1.25
LAND_C   = (OEDGE + IEDGE)/2.0          ; 1.375
;--- 페이스트: p.61 Stencil (= 벤더 랜드 1.1) 를 단자 위로 오프셋 -------
PST_OFF  = LAND_C - DS_LC               ; 0.075  로컬 +x = 부품 중심 방향

;--- 그 외 -------------------------------------------------------------
SILK_W   = 0.1
ASSY_W   = 0.1
CLR      = 0.1
BX       = BODY_E1/2.0                  ; 0.875
BY       = BODY_D /2.0                  ; 1.525
PAD_YMAX = PITCH + DS_LW/2.0            ; 1.25
PB_X     = OEDGE + CLR                  ; 2.10
PB_Y     = BY + SILK_W/2.0 + CLR        ; 1.675

L_SILK = "PACKAGE GEOMETRY/SILKSCREEN_TOP"
L_ASSY = "PACKAGE GEOMETRY/ASSEMBLY_TOP"
L_PB   = "PACKAGE GEOMETRY/PLACE_BOUND_TOP"

;======================= 로그 =========================================
LOGP = outfile(strcat(WORKDIR "build_sot95p280.log") "w")
procedure(LOG(fmt @rest a)
  let((s)
    s = lsprintf(fmt @a)
    printf("%s\n" s)
    fprintf(LOGP "%s\n" s)
    drain(LOGP)                      ; 에러 시 버퍼 유실 방지
  )
)

LOG("=== build %s ===" SYM)
LOG("vendor land %.2f x %.2f  row c-c %.2f -> ie=%.2f oe=%.2f" DS_LL DS_LW DS_ROW IEDGE DS_LC+DS_LL/2.0)
LOG("applied land %.2f x %.2f  ie=%.2f oe=%.2f c=%.3f poff=%.3f"
    LAND_L DS_LW IEDGE OEDGE LAND_C PST_OFF)
LOG("toe exposed = %.2f (>= %.2f)" OEDGE-LEAD_TIP TOE_REQ)
LOG("copper gap = %.2f  mask web = %.2f" PITCH-DS_LW PITCH-(DS_LW+2*MASK_EXP))

;======================= 0. 설계 범위 =================================
axlDBChangeDesignExtents(list(-15.0:-15.0 15.0:15.0))

;======================= 1. 패드스택 ==================================
; 함정: 정사각이면 'SQUARE. 1.25 x 0.60 이므로 'RECTANGLE 로 안전.
let((pl)
  pl = list()
  pl = cons(make_axlPadStackPad(?layer "TOP"            ?type 'REGULAR
            ?figure 'RECTANGLE ?figureSize LAND_L:DS_LW) pl)
  ; 규칙 6: 데이터시트가 별도 마스크를 주므로 우선 (NSMD, 동판 + 0.07/변)
  pl = cons(make_axlPadStackPad(?layer "SOLDERMASK_TOP" ?type 'REGULAR
            ?figure 'RECTANGLE
            ?figureSize (LAND_L+2*MASK_EXP):(DS_LW+2*MASK_EXP)) pl)
  ; 페이스트 = p.61 Stencil (1.1 x 0.6) 을 단자 위로 오프셋
  pl = cons(make_axlPadStackPad(?layer "PASTEMASK_TOP"  ?type 'REGULAR
            ?figure 'RECTANGLE ?figureSize DS_LL:DS_LW ?offset PST_OFF:0.0) pl)
  axlDBCreatePadStack(PAD nil pl t)
  axlPadstackToDisk(PAD)
  LOG("padstack %s copper %.2fx%.2f mask %.2fx%.2f paste %.2fx%.2f off %.3f"
      PAD LAND_L DS_LW LAND_L+2*MASK_EXP DS_LW+2*MASK_EXP DS_LL DS_LW PST_OFF)
)

;======================= 2. 핀 ========================================
procedure(MKPIN(num x y rot)
  axlDBCreatePin(PAD x:y
    make_axlPinText(?number num ?offset 0.0:0.0
      ?text make_axlTextOrientation(?textBlock "1" ?rotation 0.0
            ?mirrored nil ?justify "center"))
    rot)
)
; 좌측 : 1 OUT (상) / 2 V- (중) / 3 IN+ (하)
MKPIN("1" (-LAND_C)   PITCH  0.0)
MKPIN("2" (-LAND_C)   0.0    0.0)
MKPIN("3" (-LAND_C) (-PITCH) 0.0)
; 우측 : 4 IN- (하) / 5 V+ (상)
MKPIN("4" LAND_C (-PITCH) 180.0)
MKPIN("5" LAND_C   PITCH  180.0)

;======================= 3. 레이어 초기화 =============================
axlDeleteByLayer(list(L_SILK L_ASSY L_PB
                      "REF DES/SILKSCREEN_TOP" "REF DES/ASSEMBLY_TOP"))

;======================= 4. 실크 (규칙 7: 패드에서 0.1) ===============
; 리드는 좌우로 나오므로 바디 상·하변에만 실크를 긋는다.
; 가로선 y=±1.525 (선폭 0.1 -> 1.475~1.575) 는 패드 상단 1.25 에서 0.225 떨어져 안전.
axlDBCreateLine(list((-BX):BY    BX:BY)    SILK_W L_SILK)
axlDBCreateLine(list((-BX):(-BY) BX:(-BY)) SILK_W L_SILK)
; 핀1 도트 (바디 안쪽, 핀1 모서리). 패드 내측 0.75 까지 0.13 확보.
axlDBCreateCircle(list(-0.45:1.15 0.12) SILK_W L_SILK)

;======================= 5. 어셈블리 (한 붓) ==========================
axlDBCreateLine(
  list((-BX):(-BY) BX:(-BY) BX:BY (-BX):BY (-BX):(-BY))
  ASSY_W L_ASSY)
axlDBCreateCircle(list(-0.45:1.15 0.12) ASSY_W L_ASSY)

;======================= 6. PLACE_BOUND (채운 사각형) =================
axlDBCreateRectangle(list((-PB_X):(-PB_Y) PB_X:PB_Y) t L_PB)

;======================= 7. REFDES (규칙 12) ==========================
RX = -PB_X + 0.4               ; -1.70
RY = PAD_YMAX + 0.35           ;  1.60
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
