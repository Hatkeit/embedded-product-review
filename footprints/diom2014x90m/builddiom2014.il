/*=====================================================================
  builddiom2014.il
  DIOM2014X90M   (SOD-323 / BAS100CS-AU  100V 0.5A Schottky)

  근거: BAS100CS-AU-REV.00S (November 1, 2017)
        - p.1  SURFACE MOUNT SCHOTTKY DIODES / Mechanical Data : Case SOD-323
        - p.4  SOD-323 Dimension    : 바디 1.75~1.95 x 1.15~1.35, 높이 0.70~0.90,
                                      전장 2.30~2.70, 리드폭 0.25~0.35,
                                      리드길이 0.30 MIN, 스탠드오프 0.05~0.15
        - p.4  SOD-323 Pad Layout   : 벤더 권장랜드 있음
                                      span 2.90 / 패드 0.73 x 0.50 / 피치 2.17

  실행:
    copy seed.dra diom2014x90m.dra
    echo skill load("<절대경로>/builddiom2014.il") > run.scr
    allegro.exe -nograph -s run.scr diom2014x90m.dra

  좌표계: TOP VIEW. 원점 = 바디 중심.
          핀1 = 캐소드(K, 띠 표시) 좌측 / 핀2 = 애노드(A) 우측.
          !! 핀1/핀2 극성 배정은 pstchip.dat 로 반드시 확인할 것 (규칙 8).
             반대라면 아래 MKPIN 두 줄의 번호만 맞바꾸면 된다.
 =====================================================================*/

WORKDIR = "D:/fp/diom2014/"                 ; <<< 사용자 수정: 로그 출력 폴더

SYM      = "diom2014x90m"
PAD      = "R113_50"                        ; 1.13 x 0.50 (토 0.40 연장분 포함)

;--- 데이터시트 원문값 -------------------------------------------------
BODY_L   = 1.95        ; p.4 바디 길이 MAX (1.75~1.95)
BODY_W   = 1.35        ; p.4 바디 폭   MAX (1.15~1.35)
BODY_H   = 0.90        ; p.4 높이      MAX (0.70~0.90)
OVERALL  = 2.70        ; p.4 전장      MAX (2.30~2.70)
;--- 벤더 권장랜드 (p.4 Pad Layout) ------------------------------------
DS_SPAN  = 2.90        ; 외측-외측
DS_PITCH = 2.17        ; 중심-중심
DS_PADX  = 0.73        ; 패드 길이 (리드축)
DS_PADY  = 0.50        ; 패드 폭
IEDGE    = DS_SPAN/2.0 - DS_PADX        ; 0.72  내측 edge (힐) -- 원문 유지
;--- 사내 규칙 2 적용: 토만 연장 ---------------------------------------
TOE_REQ  = 0.50        ; 리드 끝 바깥 노출 동판 요구치
LEAD_TIP = OVERALL/2.0                  ; 1.35  리드 끝 (최대재료조건)
OEDGE    = LEAD_TIP + TOE_REQ           ; 1.85
PAD_X    = OEDGE - IEDGE                ; 1.13
PAD_C    = (OEDGE + IEDGE)/2.0          ; 1.285
;--- 페이스트: 벤더 랜드량 유지 (아래 '이탈' 주석 참조) -----------------
PST_C    = DS_PITCH/2.0                 ; 1.085
PST_OFF  = PAD_C - PST_C                ; 0.20  패드 로컬 +x = 부품 중심 방향

;--- 그 외 -------------------------------------------------------------
SILK_W   = 0.1
ASSY_W   = 0.1
CLR      = 0.1
BL       = BODY_L/2.0                   ; 0.975
BW       = BODY_W/2.0                   ; 0.675
KBAR     = -0.55                        ; 캐소드 띠 x 위치 (패드까지 0.12 확보)
PB_X     = OEDGE + CLR                  ; 1.95
PB_Y     = BW    + CLR                  ; 0.775

L_SILK = "PACKAGE GEOMETRY/SILKSCREEN_TOP"
L_ASSY = "PACKAGE GEOMETRY/ASSEMBLY_TOP"
L_PB   = "PACKAGE GEOMETRY/PLACE_BOUND_TOP"

;======================= 로그 =========================================
LOGP = outfile(strcat(WORKDIR "build_diom2014.log") "w")
procedure(LOG(fmt @rest a)
  let((s)
    s = lsprintf(fmt @a)
    printf("%s\n" s)
    fprintf(LOGP "%s\n" s)
    drain(LOGP)                      ; 에러 시 버퍼 유실 방지
  )
)

LOG("=== build %s ===" SYM)
LOG("IEDGE=%.3f OEDGE=%.3f PAD=%.2fx%.2f PAD_C=%.3f PST_OFF=%.3f"
    IEDGE OEDGE PAD_X DS_PADY PAD_C PST_OFF)
LOG("toe exposed = %.3f (>=%.2f)" OEDGE-LEAD_TIP TOE_REQ)

;======================= 0. 설계 범위 =================================
axlDBChangeDesignExtents(list(-15.0:-15.0 15.0:15.0))

;======================= 1. 패드스택 ==================================
let((pl)
  pl = list()
  pl = cons(make_axlPadStackPad(?layer "TOP"            ?type 'REGULAR
            ?figure 'RECTANGLE ?figureSize PAD_X:DS_PADY) pl)
  ; 규칙 6: 마스크는 동판을 따라간다 (1:1)
  pl = cons(make_axlPadStackPad(?layer "SOLDERMASK_TOP" ?type 'REGULAR
            ?figure 'RECTANGLE ?figureSize PAD_X:DS_PADY) pl)
  ; 페이스트는 벤더 랜드(0.73)만큼만, 단자 위로 오프셋
  ;  -> 규칙 4(리드부품 = 랜드 전체) 이탈. 사유는 보고서 참조.
  ;     규칙대로 랜드 전체를 덮으려면 아래 두 줄을 PAD_X / offset 0 으로 바꾼다.
  pl = cons(make_axlPadStackPad(?layer "PASTEMASK_TOP"  ?type 'REGULAR
            ?figure 'RECTANGLE ?figureSize DS_PADX:DS_PADY
            ?offset PST_OFF:0.0) pl)
  axlDBCreatePadStack(PAD nil pl t)
  axlPadstackToDisk(PAD)
  LOG("padstack %s copper %.2fx%.2f paste %.2fx%.2f off %.3f"
      PAD PAD_X DS_PADY DS_PADX DS_PADY PST_OFF)
)

;======================= 2. 핀 ========================================
procedure(MKPIN(num x rot)
  axlDBCreatePin(PAD x:0.0
    make_axlPinText(?number num ?offset 0.0:0.0
      ?text make_axlTextOrientation(?textBlock "1" ?rotation 0.0
            ?mirrored nil ?justify "center"))
    rot)
)
MKPIN("1" (-PAD_C)   0.0)      ; 캐소드 (K) -- 띠 쪽
MKPIN("2" ( PAD_C) 180.0)      ; 애노드 (A)

;======================= 3. 레이어 초기화 =============================
axlDeleteByLayer(list(L_SILK L_ASSY L_PB
                      "REF DES/SILKSCREEN_TOP" "REF DES/ASSEMBLY_TOP"))

;======================= 4. 실크 (규칙 7: 패드에서 0.1) ===============
; 패드는 y ±0.25 / x 0.72~1.85 를 차지한다.
; 바디 상·하 가로선(y=±0.675)은 패드에서 0.425 떨어져 안전.
; 세로 끝선(x=±0.975)은 패드 안에 들어가므로 그리지 않는다.
axlDBCreateLine(list((-BL):BW    BL:BW)    SILK_W L_SILK)
axlDBCreateLine(list((-BL):(-BW) BL:(-BW)) SILK_W L_SILK)
; 캐소드 띠
axlDBCreateLine(list(KBAR:(-BW) KBAR:BW) SILK_W L_SILK)

;======================= 5. 어셈블리 (한 붓) ==========================
axlDBCreateLine(
  list((-BL):(-BW) BL:(-BW) BL:BW (-BL):BW (-BL):(-BW))
  ASSY_W L_ASSY)
axlDBCreateLine(list(KBAR:(-BW) KBAR:BW) ASSY_W L_ASSY)

;======================= 6. PLACE_BOUND (채운 사각형) =================
axlDBCreateRectangle(list((-PB_X):(-PB_Y) PB_X:PB_Y) t L_PB)

;======================= 7. REFDES (규칙 12) ==========================
RX = -PB_X + 0.4               ; -1.55
RY = DS_PADY/2.0 + 0.35        ;  0.60  (패드 상단 0.25 + 0.35)
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
