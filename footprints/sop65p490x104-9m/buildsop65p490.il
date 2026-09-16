/*=====================================================================
  buildsop65p490.il
  SOP65P490X104-9M   (Infineon PG-TSSOP-8, 노출다이패드)
  대상 부품: 2EDN7524R  (EiceDRIVER 2EDN752x/2EDN852x)

  근거: Infineon Datasheet Rev. 2.7 (2025-03-18)
        - p.5  1.2 Package Versions : "R" = PG-TSSOP-8
        - p.7  Figure 2 Pin Configuration PG-TSSOP-8, Top View
               1 ENA / 2 INA / 3 GND / 4 INB / 5 OUTB / 6 VDD / 7 OUTA / 8 ENB
               + Exposed Pad (GND 핀에 연결할 것)
        - p.27 Figure 23 PG-TSSOP-8 outline
               피치 0.65 (3 x 0.65 = 1.95) / 리드스팬 4.9±0.1 / 바디 3±0.1 x 3±0.1
               리드폭 0.31 +0.07/-0.06 / 리드발 0.546±0.1 / 높이 1.04 MAX
               노출다이패드 1.71±0.13 x 2.05±0.1
        - p.28 Figure 24 PG-TSSOP-8 footprint  (벤더 권장랜드 = 있음)
               Copper / Solder Mask / Stencil Apertures 를 각각 제공
               리드패드 0.4 x 1.3, 피치 0.65, 패드중심 ±2.2
               노출패드 동판 2.05 x 1.75
               솔더마스크 = 동판 + 0.05/변
               스텐실  리드 = 동판과 동일 / 노출패드 = 2x2 창, 간극 0.2

  검증: p.28 도면은 축척이 맞다. 벡터를 실측해 피치로 스케일을 잡으면
        (0.65mm / 14.43pt) 리드패드 8.88 x 28.85pt = 0.400 x 1.300,
        노출패드 45.51 x 38.82pt = 2.050 x 1.749 로 라벨과 ±0.002 내 일치.
        "2.2" 는 패드 '중심' 오프셋임을 실측으로 확인했다
        (패드중심 174.965pt, 중심선 223.78pt -> 48.8pt = 2.200mm).

  실행:
    copy seed.dra sop65p490x104-9m.dra
    echo skill load("<절대경로>/buildsop65p490.il") > run.scr
    allegro.exe -nograph -s run.scr sop65p490x104-9m.dra

  좌표계: p.7 Pin Configuration (Top View) 방향.
          핀1 = 좌상단, 1~4 좌측 위->아래, 5~8 우측 아래->위.
          (p.27/p.28 도면은 이를 90도 돌려 그렸지만, 핀배치 정본은
           "Top View" 라고 명시된 p.7 이므로 그쪽 방향을 따랐다.
           LT8304 때와 동일한 처리.)
 =====================================================================*/

WORKDIR = "D:/fp/sop65p490/"                ; <<< 사용자 수정: 로그 출력 폴더

SYM      = "sop65p490x104-9m"
PAD_LEAD = "R145_40"                        ; 1.45 x 0.40 (토 0.15 연장분 포함)
PAD_EP   = "R175_205"                       ; 1.75 x 2.05 노출패드

;--- 데이터시트 원문값 (mm) --------------------------------------------
PITCH    = 0.65        ; p.27  3 x 0.65 = 1.95
SPAN_E   = 4.9         ; p.27  리드스팬 (±0.1)
SPAN_MAX = 5.0         ; 최대재료조건
BODY     = 3.1         ; p.27  3±0.1 -> max 3.1 (양방향 동일)
;--- 벤더 권장랜드 (p.28) ----------------------------------------------
DS_LW    = 0.4         ; 리드패드 폭   (피치 방향)
DS_LL    = 1.3         ; 리드패드 길이 (리드 방향)
DS_LC    = 2.2         ; 리드패드 중심 오프셋
EP_X     = 1.75        ; 노출패드 (리드 방향)
EP_Y     = 2.05        ; 노출패드 (피치 방향)
MASK_EXP = 0.05        ; p.28 솔더마스크 = 동판 + 0.05/변  (규칙 6: 데이터시트 우선)
IEDGE    = DS_LC - DS_LL/2.0            ; 1.55  힐 -- 원문 유지
;--- 사내 규칙 2 적용: 토만 연장 ---------------------------------------
TOE_REQ  = 0.50
LEAD_TIP = SPAN_MAX/2.0                 ; 2.50
OEDGE    = LEAD_TIP + TOE_REQ           ; 3.00
LEAD_L   = OEDGE - IEDGE                ; 1.45
LEAD_C   = (OEDGE + IEDGE)/2.0          ; 2.275
;--- 페이스트: p.28 Stencil Apertures 그대로 ---------------------------
PST_OFF  = LEAD_C - DS_LC               ; 0.075  로컬 +x = 부품 중심 방향
; 노출패드 스텐실 2x2, 간극 0.2 -> 창은 동판 안에 정확히 타일링되게 계산
STGAP    = 0.2
WIN_X    = (EP_X - STGAP)/2.0           ; 0.775
WIN_Y    = (EP_Y - STGAP)/2.0           ; 0.925
WCX      = (WIN_X + STGAP)/2.0          ; 0.4875
WCY      = (WIN_Y + STGAP)/2.0          ; 0.5625

;--- 그 외 -------------------------------------------------------------
SILK_W   = 0.1
ASSY_W   = 0.1
CLR      = 0.1
BH       = BODY/2.0                     ; 1.55
PAD_YMAX = 1.5*PITCH + DS_LW/2.0        ; 1.175
PB_X     = OEDGE + CLR                  ; 3.10
PB_Y     = BH    + CLR                  ; 1.65  (바디가 패드보다 바깥)

L_SILK = "PACKAGE GEOMETRY/SILKSCREEN_TOP"
L_ASSY = "PACKAGE GEOMETRY/ASSEMBLY_TOP"
L_PB   = "PACKAGE GEOMETRY/PLACE_BOUND_TOP"
L_PST  = "PACKAGE GEOMETRY/PASTEMASK_TOP"   ; 규칙 5

;======================= 로그 =========================================
LOGP = outfile(strcat(WORKDIR "build_sop65p490.log") "w")
procedure(LOG(fmt @rest a)
  let((s)
    s = lsprintf(fmt @a)
    printf("%s\n" s)
    fprintf(LOGP "%s\n" s)
    drain(LOGP)                      ; 에러 시 버퍼 유실 방지
  )
)

LOG("=== build %s ===" SYM)
LOG("lead %.2f x %.2f  ie=%.2f oe=%.2f c=%.3f poff=%.3f"
    LEAD_L DS_LW IEDGE OEDGE LEAD_C PST_OFF)
LOG("toe exposed = %.3f (>= %.2f)" OEDGE-LEAD_TIP TOE_REQ)
LOG("EP %.2f x %.2f  window %.3f x %.3f  coverage %.2f%%"
    EP_X EP_Y WIN_X WIN_Y 100.0*4.0*WIN_X*WIN_Y/(EP_X*EP_Y))
LOG("mask web between lead pads = %.3f" PITCH-(DS_LW+2*MASK_EXP))

;======================= 0. 설계 범위 =================================
axlDBChangeDesignExtents(list(-15.0:-15.0 15.0:15.0))

;======================= 1. 패드스택 ==================================
; 함정: 정사각이면 'SQUARE. 여기는 둘 다 직사각이라 'RECTANGLE 로 안전.
let((pl)
  pl = list()
  pl = cons(make_axlPadStackPad(?layer "TOP"            ?type 'REGULAR
            ?figure 'RECTANGLE ?figureSize LEAD_L:DS_LW) pl)
  ; 규칙 6: 데이터시트가 별도 마스크를 주므로 그것을 우선 (동판 + 0.05/변)
  pl = cons(make_axlPadStackPad(?layer "SOLDERMASK_TOP" ?type 'REGULAR
            ?figure 'RECTANGLE
            ?figureSize (LEAD_L+2*MASK_EXP):(DS_LW+2*MASK_EXP)) pl)
  ; 페이스트 = p.28 Stencil Apertures (1.3 x 0.4) 를 단자 위로 오프셋
  pl = cons(make_axlPadStackPad(?layer "PASTEMASK_TOP"  ?type 'REGULAR
            ?figure 'RECTANGLE ?figureSize DS_LL:DS_LW ?offset PST_OFF:0.0) pl)
  axlDBCreatePadStack(PAD_LEAD nil pl t)
  axlPadstackToDisk(PAD_LEAD)
  LOG("padstack %s copper %.2fx%.2f mask %.2fx%.2f paste %.2fx%.2f off %.3f"
      PAD_LEAD LEAD_L DS_LW LEAD_L+2*MASK_EXP DS_LW+2*MASK_EXP DS_LL DS_LW PST_OFF)
)

let((pl)
  pl = list()
  pl = cons(make_axlPadStackPad(?layer "TOP"            ?type 'REGULAR
            ?figure 'RECTANGLE ?figureSize EP_X:EP_Y) pl)
  pl = cons(make_axlPadStackPad(?layer "SOLDERMASK_TOP" ?type 'REGULAR
            ?figure 'RECTANGLE
            ?figureSize (EP_X+2*MASK_EXP):(EP_Y+2*MASK_EXP)) pl)
  ; 규칙 5: 열패드에는 PASTEMASK 를 넣지 않는다 (윈도우페인은 심볼 레벨)
  axlDBCreatePadStack(PAD_EP nil pl t)
  axlPadstackToDisk(PAD_EP)
  LOG("padstack %s copper %.2fx%.2f mask %.2fx%.2f paste=NONE(심볼레벨)"
      PAD_EP EP_X EP_Y EP_X+2*MASK_EXP EP_Y+2*MASK_EXP)
)

;======================= 2. 핀 ========================================
procedure(MKPIN(ps num x y rot)
  axlDBCreatePin(ps x:y
    make_axlPinText(?number num ?offset 0.0:0.0
      ?text make_axlTextOrientation(?textBlock "1" ?rotation 0.0
            ?mirrored nil ?justify "center"))
    rot)
)

; 좌측 1~4 : 위 -> 아래   (1 ENA / 2 INA / 3 GND / 4 INB)
for(i 1 4
  MKPIN(PAD_LEAD sprintf(nil "%d" i) (-LEAD_C) (0.975-PITCH*(i-1)) 0.0))
; 우측 5~8 : 아래 -> 위   (5 OUTB / 6 VDD / 7 OUTA / 8 ENB)
for(i 5 8
  MKPIN(PAD_LEAD sprintf(nil "%d" i) LEAD_C (-0.975+PITCH*(i-5)) 180.0))
; 노출 다이패드 = 핀 9 (GND 핀에 연결)
MKPIN(PAD_EP "9" 0.0 0.0 0.0)

LOG("pins: 8 gullwing + 1 exposed diepad (pin 9)")

;======================= 3. 레이어 초기화 =============================
axlDeleteByLayer(list(L_SILK L_ASSY L_PB L_PST
                      "REF DES/SILKSCREEN_TOP" "REF DES/ASSEMBLY_TOP"))

;======================= 4. 페이스트 윈도우페인 (규칙 5 / p.28) =======
; 2x2, 창 0.775 x 0.925, 간극 0.2 -> 동판 1.75 x 2.05 에 정확히 타일링
; 커버리지 79.9%  (데이터시트 라벨 0.93/0.78 을 그대로 쓰면 80.9% 이고
;                  동판을 변당 0.005 넘어선다. 타일링이 맞는 값을 썼다.)
foreach(cy list((-WCY) WCY)
  foreach(cx list((-WCX) WCX)
    axlDBCreateRectangle(
      list((cx-WIN_X/2.0):(cy-WIN_Y/2.0) (cx+WIN_X/2.0):(cy+WIN_Y/2.0)) t L_PST)))

;======================= 5. 실크 (규칙 7: 패드에서 0.1) ===============
; 리드는 좌우로 나오므로 바디 상·하변에만 실크를 긋는다.
; 가로선 y=±1.55 : 리드패드 최외곽 1.175 에서 0.325 떨어져 안전.
axlDBCreateLine(list((-BH):BH    BH:BH)    SILK_W L_SILK)
axlDBCreateLine(list((-BH):(-BH) BH:(-BH)) SILK_W L_SILK)
; 핀1 도트 (바디 안쪽, 핀1 모서리)
axlDBCreateCircle(list(-1.20:1.32 0.12) SILK_W L_SILK)

;======================= 6. 어셈블리 (한 붓) ==========================
axlDBCreateLine(
  list((-BH):(-BH) BH:(-BH) BH:BH (-BH):BH (-BH):(-BH))
  ASSY_W L_ASSY)
axlDBCreateCircle(list(-1.20:1.32 0.12) ASSY_W L_ASSY)

;======================= 7. PLACE_BOUND (채운 사각형) =================
axlDBCreateRectangle(list((-PB_X):(-PB_Y) PB_X:PB_Y) t L_PB)

;======================= 8. REFDES (규칙 12) ==========================
RX = -PB_X + 0.4               ; -2.70
RY = PAD_YMAX + 0.35           ;  1.525
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
