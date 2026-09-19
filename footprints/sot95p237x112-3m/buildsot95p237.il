/*=====================================================================
  buildsot95p237.il
  SOT95P237X112-3M   (TI DBZ0003A = SOT-23-3)
  대상 부품: REF3030 (REF30/REF30E 전압 레퍼런스)

  근거: TI SBVS032K (2002-03 / rev 2025-12)
        - p.3  Figure 5-1 DBZ Package 3-Pin SOT-23 Top View
               Table 5-1 : 1 IN / 2 OUT / 3 GND
        - p.34 PACKAGE OUTLINE  DBZ0003A  4214838/F 08/2024  (JEDEC TO-236 참조)
               리드스팬 E 2.10~2.64 / 피치 0.95 (핀스팬 1.9)
               바디 A(D) 2.80~3.04 / B(E1) 1.2~1.4 / 높이 1.12 MAX
               리드폭 0.3~0.5 / 리드발 0.2~0.6 TYP / 스탠드오프 0.01~0.10
        - p.35 EXAMPLE BOARD LAYOUT  (벤더 권장랜드 = 있음)
               패드 3X (1.3) x 3X (0.6), 행간 (2.1), 핀1/2 오프셋 2X (0.95)
               솔더마스크 NSMD(PREFERRED), 0.07 MIN ALL AROUND
        - p.36 EXAMPLE STENCIL DESIGN
               스텐실 = 랜드와 동일 (1.3 x 0.6), 0.125mm 스텐실 기준

  검증: p.35 를 렌더링해 (2.1) 치수선 화살표가 좌측 패드열과 핀3 패드의
        '중심선'에 물리는 것을 확인했다 -> (2.1) = 패드 중심-중심.
        패드 외측 = 1.05 + 0.65 = 1.70, 리드 끝 = 2.64/2 = 1.32 -> 토 0.38.
        같은 TI 규약의 DBV/DCK/DDF 도면도 모두 토 0.35~0.38 로 일관된다.

  실행:
    copy seed.dra sot95p237x112-3m.dra
    echo skill load("<절대경로>/buildsot95p237.il") > run.scr
    allegro.exe -nograph -s run.scr sot95p237x112-3m.dra

  좌표계: p.3 Top View 방향. 원점 = 패키지 중심.
          핀1 좌상(IN) / 핀2 좌하(OUT) / 핀3 우중(GND).
          피치 방향 = y, 리드 방향 = x.
 =====================================================================*/

WORKDIR = "D:/fp/sot95p237/"                ; <<< 사용자 수정: 로그 출력 폴더

SYM      = "sot95p237x112-3m"
PAD      = "R142_60"                        ; 1.42 x 0.60 (토 연장분 포함)

;--- 데이터시트 원문값 (mm) --------------------------------------------
PITCH    = 0.95        ; p.34 (핀1-핀2 = 1.9)
SPAN_MAX = 2.64        ; p.34 리드스팬 E max
BODY_D   = 3.04        ; p.34 A max  (2핀 줄 방향 = y)
BODY_E1  = 1.4         ; p.34 B max  (리드 방향 = x)
;--- 벤더 권장랜드 (p.35) ----------------------------------------------
DS_LL    = 1.3         ; 패드 길이 (리드 방향)
DS_LW    = 0.6         ; 패드 폭   (피치 방향)
DS_ROW   = 2.1         ; 좌우 패드 중심-중심
DS_LC    = DS_ROW/2.0                   ; 1.05
IEDGE    = DS_LC - DS_LL/2.0            ; 0.40  힐 -- 원문 유지
MASK_EXP = 0.07        ; p.35 NSMD, 0.07 MIN ALL AROUND (규칙 6: 데이터시트 우선)
;--- 사내 규칙 2 적용: 토만 연장 ---------------------------------------
TOE_REQ  = 0.50
LEAD_TIP = SPAN_MAX/2.0                 ; 1.32
OEDGE    = LEAD_TIP + TOE_REQ           ; 1.82
LAND_L   = OEDGE - IEDGE                ; 1.42
LAND_C   = (OEDGE + IEDGE)/2.0          ; 1.11
;--- 페이스트: p.36 Stencil (= 벤더 랜드 1.3) 을 단자 위로 오프셋 -------
PST_OFF  = LAND_C - DS_LC               ; 0.06  로컬 +x = 부품 중심 방향

;--- 그 외 -------------------------------------------------------------
SILK_W   = 0.1
ASSY_W   = 0.1
CLR      = 0.1
BX       = BODY_E1/2.0                  ; 0.70
BY       = BODY_D /2.0                  ; 1.52
PAD_YMAX = PITCH + DS_LW/2.0            ; 1.25
PB_X     = OEDGE + CLR                  ; 1.92
PB_Y     = BY + SILK_W/2.0 + CLR        ; 1.67
CHAM     = 0.40                         ; 어셈블리 핀1 챔퍼

L_SILK = "PACKAGE GEOMETRY/SILKSCREEN_TOP"
L_ASSY = "PACKAGE GEOMETRY/ASSEMBLY_TOP"
L_PB   = "PACKAGE GEOMETRY/PLACE_BOUND_TOP"

;======================= 로그 =========================================
LOGP = outfile(strcat(WORKDIR "build_sot95p237.log") "w")
procedure(LOG(fmt @rest a)
  let((s)
    s = lsprintf(fmt @a)
    printf("%s\n" s)
    fprintf(LOGP "%s\n" s)
    drain(LOGP)                      ; 에러 시 버퍼 유실 방지
  )
)

LOG("=== build %s ===" SYM)
LOG("vendor land %.2f x %.2f  row c-c %.2f -> ie=%.2f oe=%.2f"
    DS_LL DS_LW DS_ROW IEDGE DS_LC+DS_LL/2.0)
LOG("applied land %.2f x %.2f  ie=%.2f oe=%.2f c=%.3f poff=%.2f"
    LAND_L DS_LW IEDGE OEDGE LAND_C PST_OFF)
LOG("toe exposed = %.2f (>= %.2f)" OEDGE-LEAD_TIP TOE_REQ)
LOG("copper gap = %.2f  mask web = %.2f" 2*PITCH-DS_LW 2*PITCH-(DS_LW+2*MASK_EXP))

;======================= 0. 설계 범위 =================================
axlDBChangeDesignExtents(list(-15.0:-15.0 15.0:15.0))

;======================= 1. 패드스택 ==================================
; 함정: 정사각이면 'SQUARE. 1.42 x 0.60 이므로 'RECTANGLE 로 안전.
let((pl)
  pl = list()
  pl = cons(make_axlPadStackPad(?layer "TOP"            ?type 'REGULAR
            ?figure 'RECTANGLE ?figureSize LAND_L:DS_LW) pl)
  ; 규칙 6: 데이터시트가 별도 마스크를 주므로 우선 (NSMD, 동판 + 0.07/변)
  pl = cons(make_axlPadStackPad(?layer "SOLDERMASK_TOP" ?type 'REGULAR
            ?figure 'RECTANGLE
            ?figureSize (LAND_L+2*MASK_EXP):(DS_LW+2*MASK_EXP)) pl)
  ; 페이스트 = p.36 Stencil (1.3 x 0.6) 을 단자 위로 오프셋
  pl = cons(make_axlPadStackPad(?layer "PASTEMASK_TOP"  ?type 'REGULAR
            ?figure 'RECTANGLE ?figureSize DS_LL:DS_LW ?offset PST_OFF:0.0) pl)
  axlDBCreatePadStack(PAD nil pl t)
  axlPadstackToDisk(PAD)
  LOG("padstack %s copper %.2fx%.2f mask %.2fx%.2f paste %.2fx%.2f off %.2f"
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
MKPIN("1" (-LAND_C)   PITCH  0.0)     ; IN
MKPIN("2" (-LAND_C) (-PITCH) 0.0)     ; OUT
MKPIN("3"   LAND_C    0.0  180.0)     ; GND

;======================= 3. 레이어 초기화 =============================
axlDeleteByLayer(list(L_SILK L_ASSY L_PB
                      "REF DES/SILKSCREEN_TOP" "REF DES/ASSEMBLY_TOP"))

;======================= 4. 실크 (규칙 7: 패드에서 0.1) ===============
; 리드는 좌우(±x)로 나오므로 바디 상·하변에만 실크를 긋는다.
; 가로선 y=±1.52 (선폭 0.1 -> 1.47~1.57) 는 패드 상단 1.25 에서 0.22 떨어져 안전.
axlDBCreateLine(list((-BX):BY    BX:BY)    SILK_W L_SILK)
axlDBCreateLine(list((-BX):(-BY) BX:(-BY)) SILK_W L_SILK)
; 핀1 도트. 바디 안쪽 자유대역이 |x| < 0.40 뿐이라 중앙 상단에 둔다
; (핀1이 어느 '끝'인지 표시. 좌우 구분은 어셈블리 챔퍼가 맡는다)
axlDBCreateCircle(list(0.0:1.15 0.12) SILK_W L_SILK)

;======================= 5. 어셈블리 (한 붓, 핀1 챔퍼) ================
axlDBCreateLine(
  list((-BX):(BY-CHAM)  ((-BX)+CHAM):BY  BX:BY  BX:(-BY)  (-BX):(-BY)  (-BX):(BY-CHAM))
  ASSY_W L_ASSY)

;======================= 6. PLACE_BOUND (채운 사각형) =================
axlDBCreateRectangle(list((-PB_X):(-PB_Y) PB_X:PB_Y) t L_PB)

;======================= 7. REFDES (규칙 12) ==========================
RX = -PB_X + 0.4               ; -1.52
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
