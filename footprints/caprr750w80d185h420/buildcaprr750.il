/*=====================================================================
  buildcaprr750.il
  CAPRR750W80D185H420   (Rubycon ZLJ  63ZLJ2700M18X40)
  래디얼 리드 알루미늄 전해 커패시터 / 스루홀 2핀

  근거: Rubycon ZLJ series datasheet (RADIAL LEAD ALUMINUM ELECTROLYTIC)
        - p.2 ◆寸法図/DIMENSIONS  : φD=18 열 -> F=7.5, φd=0.8
                                     F±0.5 / φD+0.5 MAX / L+α MAX (L≧20: α=2.0)
                                     리드길이 15 MIN
        - p.3 ◆標準品一覧表        : 63Vdc 2700μF = 18×40
  !! 이 데이터시트에는 권장 랜드패턴(recommended footprint)이 없다.
     홀경·랜드경은 IPC-7251 로 유도했으며 근거를 아래에 명시한다.

  실행:
    copy seed.dra caprr750w80d185h420.dra
    echo skill load("<절대경로>/buildcaprr750.il") > run.scr
    allegro.exe -nograph -s run.scr caprr750w80d185h420.dra

  좌표계: TOP VIEW. 원점 = 리드 2개의 중점(부품 중심).
          핀1 = (+) 양극, 좌측 / 핀2 = (-) 음극(슬리브 띠), 우측.
 =====================================================================*/

WORKDIR = "D:/fp/caprr750/"                 ; <<< 사용자 수정: 로그 출력 폴더

SYM      = "caprr750w80d185h420"
PAD_POS  = "S200H110"                       ; 핀1 (+) 사각 2.0 / 드릴 1.1
PAD_NEG  = "C200H110"                       ; 핀2 (-) 원형 2.0 / 드릴 1.1

;--- 데이터시트 원문값 -------------------------------------------------
F_PITCH  = 7.5         ; p.2 φD=18 -> F=7.5  (±0.5)
LEAD_D   = 0.8         ; p.2 φD=18 -> φd=0.8
CASE_D   = 18.0        ; p.3 18×40
CASE_L   = 40.0
CASE_DMX = CASE_D + 0.5        ; 18.5  (φD+0.5 MAX)
CASE_HMX = CASE_L + 2.0        ; 42.0  (L≧20 -> α=2.0)

;--- IPC-7251 유도값 (데이터시트에 랜드 규정 없음) ----------------------
;  드릴 = 리드경 + 0.3  (Level B, 수삽/웨이브 대형 리드)
;  랜드 = 드릴 + 0.9    (환형링 0.45/측, Class 2 최소 0.25 대비 여유)
DRILL    = LEAD_D + 0.3        ; 1.1
LAND     = DRILL  + 0.9        ; 2.0
ANNULAR  = (LAND - DRILL)/2.0  ; 0.45
PLANE_D  = LAND + 0.6          ; 2.6  내층 THERMAL/ANTI

;--- 그 외 -------------------------------------------------------------
SILK_W   = 0.1
ASSY_W   = 0.1
CLR      = 0.1                 ; 규칙 7 이격
BODY_R   = CASE_DMX/2.0        ; 9.25
PB       = BODY_R + CLR        ; 9.35
PAD_TOP  = LAND/2.0            ; 1.0  (패드 상단)

L_SILK = "PACKAGE GEOMETRY/SILKSCREEN_TOP"
L_ASSY = "PACKAGE GEOMETRY/ASSEMBLY_TOP"
L_PB   = "PACKAGE GEOMETRY/PLACE_BOUND_TOP"

;======================= 로그 =========================================
LOGP = outfile(strcat(WORKDIR "build_caprr750.log") "w")
procedure(LOG(fmt @rest a)
  let((s)
    s = lsprintf(fmt @a)
    printf("%s\n" s)
    fprintf(LOGP "%s\n" s)
    drain(LOGP)                      ; 에러 시 버퍼 유실 방지
  )
)

LOG("=== build %s ===" SYM)
LOG("F=%.2f leadD=%.2f drill=%.2f land=%.2f annular=%.3f PB=%.2f"
    F_PITCH LEAD_D DRILL LAND ANNULAR PB)

;======================= 0. 설계 범위 =================================
axlDBChangeDesignExtents(list(-20.0:-20.0 20.0:20.0))

;======================= 1. 패드스택 ==================================
; 주의: make_axlPadStackDrill 의 키워드는 SPB 버전에 따라 다르다.
;       23.1 에서 거부되면 ?figureSize DRILL (스칼라) 형태로 바꿔 시도할 것.
procedure(MKDRILL()
  make_axlPadStackDrill(?figure 'CIRCLE ?figureSize DRILL:DRILL ?plated t)
)

; fig: 'SQUARE 또는 'CIRCLE
;  함정: 가로=세로인 정사각에 'RECTANGLE 을 쓰면 Illegal figure size 로 실패한다.
procedure(MKPADSTACK(name fig)
  let((pl)
    pl = list()
    pl = cons(make_axlPadStackPad(?layer "TOP" ?type 'REGULAR
              ?figure fig ?figureSize LAND:LAND) pl)
    pl = cons(make_axlPadStackPad(?layer "BOTTOM" ?type 'REGULAR
              ?figure fig ?figureSize LAND:LAND) pl)
    pl = cons(make_axlPadStackPad(?layer "DEFAULT INTERNAL" ?type 'REGULAR
              ?figure fig ?figureSize LAND:LAND) pl)
    pl = cons(make_axlPadStackPad(?layer "DEFAULT INTERNAL" ?type 'THERMAL
              ?figure 'CIRCLE ?figureSize PLANE_D:PLANE_D) pl)
    pl = cons(make_axlPadStackPad(?layer "DEFAULT INTERNAL" ?type 'ANTI
              ?figure 'CIRCLE ?figureSize PLANE_D:PLANE_D) pl)
    ; 규칙 6: 마스크는 동판을 따라간다 (1:1)
    pl = cons(make_axlPadStackPad(?layer "SOLDERMASK_TOP" ?type 'REGULAR
              ?figure fig ?figureSize LAND:LAND) pl)
    pl = cons(make_axlPadStackPad(?layer "SOLDERMASK_BOTTOM" ?type 'REGULAR
              ?figure fig ?figureSize LAND:LAND) pl)
    ; 스루홀 -> PASTEMASK 없음
    axlDBCreatePadStack(name MKDRILL() pl t)
    axlPadstackToDisk(name)
    LOG("padstack %s  fig=%L land=%.2f drill=%.2f" name fig LAND DRILL)
  )
)

MKPADSTACK(PAD_POS 'SQUARE)     ; 핀1 = 사각 (극성 표시)
MKPADSTACK(PAD_NEG 'CIRCLE)     ; 핀2 = 원형

;======================= 2. 핀 ========================================
procedure(MKPIN(ps num x y)
  axlDBCreatePin(ps x:y
    make_axlPinText(?number num ?offset 0.0:0.0
      ?text make_axlTextOrientation(?textBlock "1" ?rotation 0.0
            ?mirrored nil ?justify "center"))
    0.0)
)

MKPIN(PAD_POS "1" (-F_PITCH/2.0) 0.0)    ; (+) 양극
MKPIN(PAD_NEG "2" ( F_PITCH/2.0) 0.0)    ; (-) 음극

LOG("pins: 1(+) at %.3f, 2(-) at %.3f" -F_PITCH/2.0 F_PITCH/2.0)

;======================= 3. 레이어 초기화 =============================
axlDeleteByLayer(list(L_SILK L_ASSY L_PB
                      "REF DES/SILKSCREEN_TOP" "REF DES/ASSEMBLY_TOP"))

;======================= 4. 실크 ======================================
; 바디 외곽 = 최대경 φ18.5. 패드 최원점 = sqrt((3.75+1.0)^2 + 1.0^2) = 4.85
; -> 실크 원(9.25)과 패드는 4.4 이상 떨어져 규칙 7(0.1) 충족
axlDBCreateCircle(list(0.0:0.0 BODY_R) SILK_W L_SILK)

; 극성: (+) 마크 -- 핀1 바깥쪽
PX = -6.0
axlDBCreateLine(list((PX-0.6):0.0 (PX+0.6):0.0) SILK_W L_SILK)
axlDBCreateLine(list(PX:(-0.6) PX:0.6) SILK_W L_SILK)
; 극성: (-) 마크 -- 핀2 바깥쪽 (슬리브 띠 쪽)
NX = 6.0
axlDBCreateLine(list((NX-0.6):0.0 (NX+0.6):0.0) SILK_W L_SILK)

;======================= 5. 어셈블리 ==================================
axlDBCreateCircle(list(0.0:0.0 BODY_R) ASSY_W L_ASSY)
axlDBCreateLine(list((PX-0.6):0.0 (PX+0.6):0.0) ASSY_W L_ASSY)
axlDBCreateLine(list(PX:(-0.6) PX:0.6) ASSY_W L_ASSY)

;======================= 6. PLACE_BOUND (채운 사각형) =================
axlDBCreateRectangle(list((-PB):(-PB) PB:PB) t L_PB)

;======================= 7. REFDES (규칙 12) ==========================
RX = -PB + 0.4                 ; -8.95
RY_ASSY = PAD_TOP + 0.35       ;  1.35  <- 규칙 12 문자 그대로
RY_SILK = BODY_R  + 0.35       ;  9.60  <- 이탈: 1.35 면 φ18 바디 밑에 깔려 안 보임
axlDBCreateText("#REFDES" RX:RY_SILK
  make_axlTextOrientation(?textBlock "21" ?rotation 0.0
    ?mirrored nil ?justify "left") "REF DES/SILKSCREEN_TOP")
axlDBCreateText("#REFDES" RX:RY_ASSY
  make_axlTextOrientation(?textBlock "21" ?rotation 0.0
    ?mirrored nil ?justify "left") "REF DES/ASSEMBLY_TOP")

;======================= 8. 정리 / 검증 / 저장 ========================
axlPurgePadstacks('padstacks nil)

nDRC = axlDRCUpdate(t)                  ; 반드시 강제 실행
LOG("DRC = %L" nDRC)

axlSaveDesign(?noConfirm t)
axlCompileSymbol(?symbol SYM ?type "PACKAGE")

LOG("=== done: %s ===" SYM)
close(LOGP)
