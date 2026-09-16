/*=====================================================================
  buildsoic127.il
  SOIC127P600X175-9M   (Linear/ADI S8E = 8-Lead Plastic SOIC .150" Exposed Pad)
  대상 부품: LT8304 / LT8304-1

  근거: LT8304/LT8304-1 Data Sheet 8304fa
        - p.2  PIN CONFIGURATION (TOP VIEW), S8E PACKAGE
               1 TC / 2 RREF / 3 RFB / 4 SW / 5 GND / 6 VIN / 7 INTVCC / 8 EN_UVLO
               9 = EXPOSED PAD = GND, MUST BE SOLDERED TO PCB, θJA = 33 °C/W
        - p.26 PACKAGE DESCRIPTION  S8E (LTC DWG # 05-08-1857 Rev C)
               바디 E1 .150-.157 (3.810-3.988) / D .189-.197 (4.801-5.004)
               리드 스팬 E .228-.244 (5.791-6.197)
               높이 .053-.069 (1.346-1.752) / 피치 .050 (1.270) BSC
               리드폭 .014-.019 (0.355-0.483) TYP
               패키지 노출패드 .080-.099 (2.032-2.530) x .118-.139 (2.997-3.550)
        - p.26 RECOMMENDED SOLDER PAD LAYOUT  (벤더 권장랜드 = 있음)
               리드패드 .030±.005 (0.76) x .045±.005 (1.143)
               내측-내측 .160±.005 (4.06) / 외측 스팬 .245 (6.22) MIN
               노출패드 랜드 .089 (2.26) REF x .118 (2.99) REF
               피치 .050 (1.27) BSC

  !! p.26 도면은 Note 2 "DRAWING NOT TO SCALE" 명시. 벡터를 실측해도
     리드패드 10.17 x 22.17 pt (비 0.459) 가 라벨 0.76 x 1.143 (비 0.665) 과
     어긋난다. 도면은 치수의 '부착 위치'만 확인하는 데 쓰고(=.160 은 내측-내측,
     .045 는 패드 길이, .245 는 외측 스팬), 값 자체는 라벨을 정본으로 삼았다.
     확인: 4.06 + 2 x 1.143 = 6.346 >= 6.22 MIN  -> 모순 없음.

  실행:
    copy seed.dra soic127p600x175-9m.dra
    echo skill load("<절대경로>/buildsoic127.il") > run.scr
    allegro.exe -nograph -s run.scr soic127p600x175-9m.dra

  좌표계: p.2 TOP VIEW 방향. 원점 = 패키지 중심.
          핀1 = 좌상단, 1~4 좌측 위->아래, 5~8 우측 아래->위.
          (p.26 기구도면은 이를 90도 돌려 그렸지만, 핀배치 정본은
           "TOP VIEW" 라고 명시된 p.2 이므로 그쪽 방향을 따랐다.)
 =====================================================================*/

WORKDIR = "D:/fp/soic127/"                  ; <<< 사용자 수정: 로그 출력 폴더

SYM      = "soic127p600x175-9m"
PAD_LEAD = "R157_76"                        ; 1.57 x 0.76 (토 0.50 연장분 포함)
PAD_EP   = "R226_299"                       ; 2.26 x 2.99 노출패드

;--- 데이터시트 원문값 (mm) --------------------------------------------
PITCH    = 1.27        ; .050 BSC
BODY_X   = 3.988       ; E1 max  (리드에 수직)
BODY_Y   = 5.004       ; D  max  (리드 줄과 나란한 방향)
SPAN_E   = 6.197       ; E  max  리드 끝-끝
;--- 벤더 권장랜드 ------------------------------------------------------
DS_LW    = 0.76        ; 리드패드 폭   (피치 방향)
DS_LL    = 1.143       ; 리드패드 길이 (리드 방향)
DS_INNER = 4.06        ; 내측-내측
EP_X     = 2.26        ; 노출패드 랜드 (리드에 수직)
EP_Y     = 2.99        ; 노출패드 랜드 (피치 방향)
IEDGE    = DS_INNER/2.0                 ; 2.03   힐 -- 원문 유지
;--- 사내 규칙 2 적용: 토만 연장 ---------------------------------------
TOE_REQ  = 0.50
LEAD_TIP = SPAN_E/2.0                   ; 3.0985 리드 끝 (최대재료조건)
OEDGE    = 3.60                         ; = ceil(3.0985 + 0.50) -> 노출 0.5015
LEAD_L   = OEDGE - IEDGE                ; 1.57
LEAD_C   = (OEDGE + IEDGE)/2.0          ; 2.815
;--- 페이스트: 벤더 랜드량 유지 (규칙 4 이탈, 보고서 참조) --------------
PST_C    = IEDGE + DS_LL/2.0            ; 2.6015
PST_OFF  = LEAD_C - PST_C               ; 0.2135  로컬 +x = 부품 중심 방향

;--- 그 외 -------------------------------------------------------------
SILK_W   = 0.1
ASSY_W   = 0.1
CLR      = 0.1
BX       = BODY_X/2.0                   ; 1.994
BY       = BODY_Y/2.0                   ; 2.502
PAD_YMAX = 1.5*PITCH + DS_LW/2.0        ; 2.285  리드패드 최외곽 (피치 방향)
PB_X     = OEDGE + CLR                  ; 3.70
PB_Y     = BY    + CLR                  ; 2.602  (바디가 패드보다 바깥)

L_SILK = "PACKAGE GEOMETRY/SILKSCREEN_TOP"
L_ASSY = "PACKAGE GEOMETRY/ASSEMBLY_TOP"
L_PB   = "PACKAGE GEOMETRY/PLACE_BOUND_TOP"
L_PST  = "PACKAGE GEOMETRY/PASTEMASK_TOP"   ; 규칙 5

;======================= 로그 =========================================
LOGP = outfile(strcat(WORKDIR "build_soic127.log") "w")
procedure(LOG(fmt @rest a)
  let((s)
    s = lsprintf(fmt @a)
    printf("%s\n" s)
    fprintf(LOGP "%s\n" s)
    drain(LOGP)                      ; 에러 시 버퍼 유실 방지
  )
)

LOG("=== build %s ===" SYM)
LOG("lead %.2f x %.2f  ie=%.2f oe=%.2f c=%.4f poff=%.4f"
    LEAD_L DS_LW IEDGE OEDGE LEAD_C PST_OFF)
LOG("toe exposed = %.4f (>= %.2f)" OEDGE-LEAD_TIP TOE_REQ)
LOG("EP land %.2f x %.2f" EP_X EP_Y)

;======================= 0. 설계 범위 =================================
axlDBChangeDesignExtents(list(-15.0:-15.0 15.0:15.0))

;======================= 1. 패드스택 ==================================
; 함정: 정사각이면 'SQUARE. 여기는 둘 다 직사각이라 'RECTANGLE 로 안전.
let((pl)
  pl = list()
  pl = cons(make_axlPadStackPad(?layer "TOP"            ?type 'REGULAR
            ?figure 'RECTANGLE ?figureSize LEAD_L:DS_LW) pl)
  ; 규칙 6: 마스크는 동판을 따라간다 (1:1)
  pl = cons(make_axlPadStackPad(?layer "SOLDERMASK_TOP" ?type 'REGULAR
            ?figure 'RECTANGLE ?figureSize LEAD_L:DS_LW) pl)
  ; 페이스트는 벤더 랜드(1.143)만큼만, 단자 위로 오프셋
  pl = cons(make_axlPadStackPad(?layer "PASTEMASK_TOP"  ?type 'REGULAR
            ?figure 'RECTANGLE ?figureSize DS_LL:DS_LW ?offset PST_OFF:0.0) pl)
  axlDBCreatePadStack(PAD_LEAD nil pl t)
  axlPadstackToDisk(PAD_LEAD)
  LOG("padstack %s copper %.2fx%.2f paste %.3fx%.2f off %.4f"
      PAD_LEAD LEAD_L DS_LW DS_LL DS_LW PST_OFF)
)

let((pl)
  pl = list()
  pl = cons(make_axlPadStackPad(?layer "TOP"            ?type 'REGULAR
            ?figure 'RECTANGLE ?figureSize EP_X:EP_Y) pl)
  pl = cons(make_axlPadStackPad(?layer "SOLDERMASK_TOP" ?type 'REGULAR
            ?figure 'RECTANGLE ?figureSize EP_X:EP_Y) pl)
  ; 규칙 5: 열패드에는 PASTEMASK 를 넣지 않는다 (윈도우페인은 심볼 레벨)
  axlDBCreatePadStack(PAD_EP nil pl t)
  axlPadstackToDisk(PAD_EP)
  LOG("padstack %s copper %.2fx%.2f paste=NONE(심볼레벨)" PAD_EP EP_X EP_Y)
)

;======================= 2. 핀 ========================================
procedure(MKPIN(ps num x y rot)
  axlDBCreatePin(ps x:y
    make_axlPinText(?number num ?offset 0.0:0.0
      ?text make_axlTextOrientation(?textBlock "1" ?rotation 0.0
            ?mirrored nil ?justify "center"))
    rot)
)

; 좌측 1~4 : 위 -> 아래
for(i 1 4
  MKPIN(PAD_LEAD sprintf(nil "%d" i) (-LEAD_C) (1.905-PITCH*(i-1)) 0.0))
; 우측 5~8 : 아래 -> 위
for(i 5 8
  MKPIN(PAD_LEAD sprintf(nil "%d" i) LEAD_C (-1.905+PITCH*(i-5)) 180.0))
; 노출패드 = 핀 9 (GND)
MKPIN(PAD_EP "9" 0.0 0.0 0.0)

LOG("pins: 8 gullwing + 1 exposed pad (pin 9 = GND)")

;======================= 3. 레이어 초기화 =============================
axlDeleteByLayer(list(L_SILK L_ASSY L_PB L_PST
                      "REF DES/SILKSCREEN_TOP" "REF DES/ASSEMBLY_TOP"))

;======================= 4. 페이스트 윈도우페인 (규칙 5) ==============
; 2(x) x 3(y), 창 0.95 x 0.83  -> 6 x 0.7885 / (2.26 x 2.99) = 70.0%
WX = 0.95   WY = 0.83
foreach(cy list(-1.08 0.0 1.08)
  foreach(cx list(-0.655 0.655)
    axlDBCreateRectangle(
      list((cx-WX/2.0):(cy-WY/2.0) (cx+WX/2.0):(cy+WY/2.0)) t L_PST)))
LOG("paste windowpane 2x3 %.2fx%.2f  coverage %.1f%%"
    WX WY 100.0*6.0*WX*WY/(EP_X*EP_Y))

;======================= 5. 실크 (규칙 7: 패드에서 0.1) ===============
; 리드는 좌우로 나오므로 바디 상·하변에만 실크를 긋는다.
; 가로선 y=±2.502 : 리드패드 최외곽 2.285 에서 0.167 떨어져 안전.
axlDBCreateLine(list((-BX):BY    BX:BY)    SILK_W L_SILK)
axlDBCreateLine(list((-BX):(-BY) BX:(-BY)) SILK_W L_SILK)
; 핀1 도트 (바디 안쪽, 핀1 모서리)
axlDBCreateCircle(list(-1.5:2.1 0.15) SILK_W L_SILK)

;======================= 6. 어셈블리 (한 붓) ==========================
axlDBCreateLine(
  list((-BX):(-BY) BX:(-BY) BX:BY (-BX):BY (-BX):(-BY))
  ASSY_W L_ASSY)
axlDBCreateCircle(list(-1.5:2.1 0.15) ASSY_W L_ASSY)

;======================= 7. PLACE_BOUND (채운 사각형) =================
axlDBCreateRectangle(list((-PB_X):(-PB_Y) PB_X:PB_Y) t L_PB)

;======================= 8. REFDES (규칙 12) ==========================
RX = -PB_X + 0.4               ; -3.30
RY = PAD_YMAX + 0.35           ;  2.635
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
