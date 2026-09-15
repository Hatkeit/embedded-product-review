/*=====================================================================
  buildqfn32.il
  QFN50P500X500X90-33M   (Infineon PG-VQFN-32-13 / OPTIGA TPM SLB 9670)

  근거: SLB9670VQ20 Data Sheet Rev 1.5 (2024-08-07)
        - Figure 4  Package Dimensions  PG-VQFN-32-13-PO V01  (p.15)
        - Figure 6  Recommended Footprint PG-VQFN-32-13-FP V01 (p.15)

  실행:
    copy seed.dra qfn50p500x500x90-33m.dra
    echo skill load("<절대경로>/buildqfn32.il") > run.scr
    allegro.exe -nograph -s run.scr qfn50p500x500x90-33m.dra

  좌표계: TOP VIEW. 원점 = 패키지 중심.
          핀1 = 좌하단, 반시계(CCW).  Figure 4 저면도(시계방향)를 좌우 반전하여 도출,
          Figure 4 평면도의 index marking(좌하단 점)과 일치 확인함.
 =====================================================================*/

WORKDIR = "D:/fp/qfn32/"                    ; <<< 사용자 수정: 로그 출력 폴더

SYM      = "qfn50p500x500x90-33m"
PAD_LEAD = "R25_95"                         ; 0.25 x 0.95  (토 0.25 연장분 포함)
PAD_TH   = "S360_360"                       ; 3.6 x 3.6    (exposed pad)

;--- 데이터시트 원문값 -------------------------------------------------
BODY      = 5.0        ; Fig4  5 x 5
PITCH     = 0.5        ; Fig4  7 x 0.5 = 3.5
LEAD_W    = 0.25       ; Fig6  land width 0.25  (= Fig4 terminal 0.25 +0.05/-0.07)
DS_LEN    = 0.70       ; Fig6  land length 0.7
INNER     = 4.10       ; Fig6  land 내측-내측 span 4.1  -> 내측 edge = 2.05
TH        = 3.60       ; Fig6  thermal land 3.6 x 3.6
;--- 사내 규칙 2 적용: 토만 연장 ---------------------------------------
TOE_REQ   = 0.50       ; 바디 끝(2.5) 바깥 노출 동판 요구치
IEDGE     = INNER/2.0             ; 2.05
OEDGE     = BODY/2.0 + TOE_REQ    ; 3.00
LEAD_L    = OEDGE - IEDGE         ; 0.95
LEAD_C    = (OEDGE + IEDGE)/2.0   ; 2.525
;--- 규칙 4: 바텀터미네이티드 -> 페이스트는 데이터시트 솔더량 유지 ------
PST_C     = (IEDGE + IEDGE + DS_LEN)/2.0   ; 2.40  (벤더 랜드 2.05~2.75의 중심)
PST_OFF   = LEAD_C - PST_C                  ; +0.125 : 패드 로컬 +y = 부품 중심 방향
;--- 그 외 -------------------------------------------------------------
SILK_W    = 0.1
ASSY_W    = 0.1
CLR       = 0.1                    ; 규칙 7 이격
PAD_XMAX  = 1.75 + LEAD_W/2.0      ; 1.875  최외곽 패드 측면
PB        = OEDGE + CLR            ; 3.10  place bound
TH_HALF   = TH/2.0                 ; 1.8
PIN_TP    = 33                     ; <<< 확인 필요: pstchip.dat 의 exposed pad 핀번호

L_SILK = "PACKAGE GEOMETRY/SILKSCREEN_TOP"
L_ASSY = "PACKAGE GEOMETRY/ASSEMBLY_TOP"
L_PB   = "PACKAGE GEOMETRY/PLACE_BOUND_TOP"
L_PST  = "PACKAGE GEOMETRY/PASTEMASK_TOP"   ; 규칙 5. 팹/버전에 따라 "PASTEMASK_TOP/*" 일 수 있음

;======================= 로그 =========================================
LOGP = outfile(strcat(WORKDIR "build_qfn32.log") "w")
procedure(LOG(fmt @rest a)
  let((s)
    s = lsprintf(fmt @a)
    printf("%s\n" s)
    fprintf(LOGP "%s\n" s)
    drain(LOGP)                      ; 에러 시 버퍼 유실 방지
  )
)

LOG("=== build %s ===" SYM)
LOG("IEDGE=%.3f OEDGE=%.3f LEAD_L=%.3f LEAD_C=%.3f PST_OFF=%.3f PB=%.3f"
    IEDGE OEDGE LEAD_L LEAD_C PST_OFF PB)

;======================= 0. 설계 범위 =================================
axlDBChangeDesignExtents(list(-15.0:-15.0 15.0:15.0))

;======================= 1. 패드스택 ==================================
procedure(MK_LEADPAD()
  let((pl)
    pl = list()
    pl = cons(make_axlPadStackPad(?layer "TOP"            ?type 'REGULAR
              ?figure 'RECTANGLE ?figureSize LEAD_W:LEAD_L) pl)
    ; 규칙 6: 마스크는 동판을 따라간다 (1:1)
    pl = cons(make_axlPadStackPad(?layer "SOLDERMASK_TOP" ?type 'REGULAR
              ?figure 'RECTANGLE ?figureSize LEAD_W:LEAD_L) pl)
    ; 규칙 4: 페이스트는 벤더 랜드(0.7) 만큼만, 단자 위로 오프셋
    pl = cons(make_axlPadStackPad(?layer "PASTEMASK_TOP"  ?type 'REGULAR
              ?figure 'RECTANGLE ?figureSize LEAD_W:DS_LEN
              ?offset 0.0:PST_OFF) pl)
    axlDBCreatePadStack(PAD_LEAD nil pl t)
    axlPadstackToDisk(PAD_LEAD)
    LOG("padstack %s  copper %.2fx%.2f  paste %.2fx%.2f off %.3f"
        PAD_LEAD LEAD_W LEAD_L LEAD_W DS_LEN PST_OFF)
  )
)

procedure(MK_THPAD()
  let((pl)
    pl = list()
    ; 함정: 정사각은 반드시 'SQUARE. 'RECTANGLE 이면 Illegal figure size 로 실패
    pl = cons(make_axlPadStackPad(?layer "TOP"            ?type 'REGULAR
              ?figure 'SQUARE ?figureSize TH:TH) pl)
    pl = cons(make_axlPadStackPad(?layer "SOLDERMASK_TOP" ?type 'REGULAR
              ?figure 'SQUARE ?figureSize TH:TH) pl)
    ; 규칙 5: PASTEMASK 를 패드스택에 넣지 않는다 (윈도우페인은 심볼 레벨)
    axlDBCreatePadStack(PAD_TH nil pl t)
    axlPadstackToDisk(PAD_TH)
    LOG("padstack %s  copper %.2fx%.2f  paste=NONE(심볼레벨)" PAD_TH TH TH)
  )
)

MK_LEADPAD()
MK_THPAD()

;======================= 2. 핀 ========================================
procedure(MKPIN(num x y rot)
  axlDBCreatePin(PAD_LEAD x:y
    make_axlPinText(?number num ?offset 0.0:0.0
      ?text make_axlTextOrientation(?textBlock "1" ?rotation 0.0
            ?mirrored nil ?justify "center"))
    rot)
)

; 1..8   하변  좌->우   (rot 0   : 패드 0.25(x) x 0.95(y))
for(i 1 8
  MKPIN(sprintf(nil "%d" i) -1.75+0.5*(i-1) -LEAD_C 0.0))
; 9..16  우변  하->상   (rot 90  : 0.95(x) x 0.25(y))
for(i 9 16
  MKPIN(sprintf(nil "%d" i)  LEAD_C -1.75+0.5*(i-9) 90.0))
; 17..24 상변  우->좌   (rot 180)
for(i 17 24
  MKPIN(sprintf(nil "%d" i)  1.75-0.5*(i-17) LEAD_C 180.0))
; 25..32 좌변  상->하   (rot 270)
for(i 25 32
  MKPIN(sprintf(nil "%d" i) -LEAD_C  1.75-0.5*(i-25) 270.0))

; exposed pad
axlDBCreatePin(PAD_TH 0.0:0.0
  make_axlPinText(?number sprintf(nil "%d" PIN_TP) ?offset 0.0:0.0
    ?text make_axlTextOrientation(?textBlock "1" ?rotation 0.0
          ?mirrored nil ?justify "center"))
  0.0)

LOG("pins created: 32 perimeter + 1 thermal (pin %d)" PIN_TP)

;======================= 3. 레이어 초기화 =============================
axlDeleteByLayer(list(L_SILK L_ASSY L_PB L_PST
                      "REF DES/SILKSCREEN_TOP" "REF DES/ASSEMBLY_TOP"))

;======================= 4. 페이스트 윈도우페인 (규칙 5) ==============
; 3 x 3, 창 1.0 x 1.0, 피치 1.3  -> 9.00 / 12.96 = 69.4%  (50~80% 내)
WIN  = 1.0
WP   = 1.3
foreach(cy list(-WP 0.0 WP)
  foreach(cx list(-WP 0.0 WP)
    axlDBCreateRectangle(
      list((cx-WIN/2.0):(cy-WIN/2.0) (cx+WIN/2.0):(cy+WIN/2.0)) t L_PST)))
LOG("paste windowpane 3x3 %.2fx%.2f @pitch %.2f  coverage %.1f%%"
    WIN WIN WP 100.0*9.0*WIN*WIN/(TH*TH))

;======================= 5. 실크 (규칙 7: 패드에서 0.1) ===============
; 패드 측면 최외곽 = ±1.875 -> 실크는 ±1.975 에서 끝난다
SK = PAD_XMAX + CLR        ; 1.975
BH = BODY/2.0              ; 2.5
foreach(c list(list(-1.0 -1.0) list(1.0 -1.0) list(1.0 1.0) list(-1.0 1.0))
  let((sx sy)
    sx = car(c)  sy = cadr(c)
    axlDBCreateLine(list((sx*SK):(sy*BH) (sx*BH):(sy*BH) (sx*BH):(sy*SK))
                    SILK_W L_SILK)))
; 핀1 도트 (좌하단 바깥)
axlDBCreateCircle(list(-2.75:-2.75 0.15) SILK_W L_SILK)

;======================= 6. 어셈블리 (한 붓, 핀1 챔퍼) ================
axlDBCreateLine(
  list(-BH:-1.7  -1.7:-BH   BH:-BH   BH:BH   -BH:BH   -BH:-1.7)
  ASSY_W L_ASSY)

;======================= 7. PLACE_BOUND (채운 사각형) =================
axlDBCreateRectangle(list((-PB):(-PB) PB:PB) t L_PB)

;======================= 8. REFDES (규칙 12) ==========================
; x = place bound 좌측 + 0.4 , y = 패드 상단 + 0.35
RX = -PB + 0.4          ; -2.70
RY = OEDGE + 0.35       ;  3.35
foreach(lyr list("REF DES/SILKSCREEN_TOP" "REF DES/ASSEMBLY_TOP")
  axlDBCreateText("#REFDES" RX:RY
    make_axlTextOrientation(?textBlock "21" ?rotation 0.0
      ?mirrored nil ?justify "left") lyr))

;======================= 9. 정리 / 검증 / 저장 ========================
axlPurgePadstacks('padstacks nil)

nDRC = axlDRCUpdate(t)                  ; 반드시 강제 실행
LOG("DRC = %L" nDRC)

axlSaveDesign(?noConfirm t)
axlCompileSymbol(?symbol SYM ?type "PACKAGE")

LOG("=== done: %s ===" SYM)
close(LOGP)
