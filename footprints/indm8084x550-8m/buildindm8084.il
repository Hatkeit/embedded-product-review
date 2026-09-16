/*=====================================================================
  buildindm8084.il
  INDM8084X550-8M   (Eaton EE5.0 SMT / ECST1V0805-1100-R)
  SMT 전류센스 트랜스포머, 8단자

  근거: Eaton Technical Data ELX1187, Effective April 2022
        - p.1  EE5.0 SMT package (8.38 x 8.00 x 5.50 mm)
        - p.2  Mechanical parameters : A=8.38max, B=8.00max, C=5.50max,
                                       D=1.85±0.3(소형단자 피치), E=0.6(단자폭),
                                       F=0.25ref, G=0.7±0.2, 탭폭 2.0
        - p.2  Recommended PCB Layout : 소형패드 1.2 x 1.6, 피치 1.85
                                        대형탭패드 2.7 x 3.0, 탭간 갭 2.7
                                        세로 체인 1.6 / 1.3 / 3.0 / 1.3 / 1.6
        - p.2  Schematic : Pri = 8(dot)-7 , Sec = 1(dot)-3 , 2/4/5/6 = NC

  !! 권장 레이아웃 도면은 축척이 아니다. 래스터 원본(504x444)을 실측한 결과
     소형패드 폭:높이 = 44:59 px 로 라벨 1.2:1.6 과 일치하지만,
     피치는 96 px (= 라벨대로면 1.85 가 아니라 2.62) 로 어긋난다.
     따라서 도면 형상이 아니라 치수 라벨을 정본으로 삼아 재구성했다.

  실행:
    copy seed.dra indm8084x550-8m.dra
    echo skill load("<절대경로>/buildindm8084.il") > run.scr
    allegro.exe -nograph -s run.scr indm8084x550-8m.dra

  좌표계: TOP VIEW. 원점 = 패키지 중심.
 =====================================================================*/

WORKDIR = "D:/fp/indm8084/"                 ; <<< 사용자 수정: 로그 출력 폴더

SYM      = "indm8084x550-8m"
PAD_SM   = "R120_189"                       ; 소형단자 1.20 x 1.89
PAD_TAB  = "R315_300"                       ; 대형탭   3.15 x 3.00

;=====================================================================
;  !! 미확인 가정 : p.2 핀번호 평면도가 TOP VIEW 라고 보았다.
;     (4/5/6 = 위쪽 줄, 3/2/1 = 아래쪽 줄, 7 = 좌측 탭, 8 = 우측 탭)
;     측면도 2개로 교차검증을 시도했으나 패드 배치가 좌우대칭이라
;     TOP/BOTTOM 을 구분할 수 없었다. pstchip.dat 와 실물로 확인할 것.
;     BOTTOM VIEW 로 판명되면 아래 SX 를 -1.0 으로 바꾸기만 하면 된다
;     (핀 x 좌표와 회전이 함께 뒤집힌다).
;     뒤집히면 1<->3, 7<->8 이 바뀌므로 트랜스포머 극성이 반전된다.
SX = 1.0
;=====================================================================

;--- 데이터시트 원문값 -------------------------------------------------
ENV_X    = 8.00        ; B  탭 끝-끝 (x)
ENV_Y    = 8.38        ; A  소형단자 끝-끝 (y)
PITCH    = 1.85        ; D  소형단자 피치
;--- 벤더 권장랜드 (p.2 Recommended PCB Layout) ------------------------
DS_SMX   = 1.2         ; 소형패드 폭
DS_SMY   = 1.6         ; 소형패드 높이
DS_TABX  = 2.7         ; 탭패드 폭
DS_TABY  = 3.0         ; 탭패드 높이
DS_GAP   = 2.7         ; 탭패드 내측-내측
VGAP     = 1.3         ; 탭패드와 소형패드 세로 간격
TAB_IE   = DS_GAP/2.0                   ; 1.35  탭 내측 edge -- 원문 유지
SM_IE    = DS_TABY/2.0 + VGAP           ; 2.80  소형 내측 edge -- 원문 유지
;--- 사내 규칙 2 적용: 토만 연장 ---------------------------------------
TOE_REQ  = 0.50
TAB_TIP  = ENV_X/2.0                    ; 4.00  탭 끝
SM_TIP   = ENV_Y/2.0                    ; 4.19  소형단자 끝
TAB_OE   = TAB_TIP + TOE_REQ            ; 4.50
SM_OE    = SM_TIP  + TOE_REQ            ; 4.69
TAB_W    = TAB_OE - TAB_IE              ; 3.15
SM_H     = SM_OE  - SM_IE               ; 1.89
TAB_C    = (TAB_OE + TAB_IE)/2.0        ; 2.925
SM_C     = (SM_OE  + SM_IE )/2.0        ; 3.745
;--- 페이스트: 벤더 랜드량 유지 (규칙 4 이탈, 보고서 참조) --------------
TAB_PC   = TAB_IE + DS_TABX/2.0         ; 2.70
SM_PC    = SM_IE  + DS_SMY /2.0         ; 3.60
TAB_POFF = TAB_C - TAB_PC               ; 0.225  로컬 +x = 부품 중심 방향
SM_POFF  = SM_C  - SM_PC                ; 0.145  로컬 +y = 부품 중심 방향

;--- 그 외 -------------------------------------------------------------
SILK_W   = 0.1
ASSY_W   = 0.1
CLR      = 0.1
EX       = ENV_X/2.0                    ; 4.00
EY       = ENV_Y/2.0                    ; 4.19
SM_XMAX  = PITCH + DS_SMX/2.0           ; 2.45  소형패드 측면 최외곽
SILK_HX  = SM_XMAX + CLR                ; 2.55  가로 실크 끝
SILK_VY  = DS_TABY/2.0 + CLR            ; 1.60  세로 실크 끝
PB_X     = TAB_OE + CLR                 ; 4.60
PB_Y     = SM_OE  + CLR                 ; 4.79

L_SILK = "PACKAGE GEOMETRY/SILKSCREEN_TOP"
L_ASSY = "PACKAGE GEOMETRY/ASSEMBLY_TOP"
L_PB   = "PACKAGE GEOMETRY/PLACE_BOUND_TOP"

;======================= 로그 =========================================
LOGP = outfile(strcat(WORKDIR "build_indm8084.log") "w")
procedure(LOG(fmt @rest a)
  let((s)
    s = lsprintf(fmt @a)
    printf("%s\n" s)
    fprintf(LOGP "%s\n" s)
    drain(LOGP)                      ; 에러 시 버퍼 유실 방지
  )
)

LOG("=== build %s   SX=%.1f ===" SYM SX)
LOG("small: %.2f x %.2f  ie=%.2f oe=%.2f c=%.3f poff=%.3f"
    DS_SMX SM_H SM_IE SM_OE SM_C SM_POFF)
LOG("tab  : %.2f x %.2f  ie=%.2f oe=%.2f c=%.3f poff=%.3f"
    TAB_W DS_TABY TAB_IE TAB_OE TAB_C TAB_POFF)
LOG("toe exposed: small %.3f / tab %.3f  (>= %.2f)"
    SM_OE-SM_TIP TAB_OE-TAB_TIP TOE_REQ)

;======================= 0. 설계 범위 =================================
axlDBChangeDesignExtents(list(-15.0:-15.0 15.0:15.0))

;======================= 1. 패드스택 ==================================
; 함정: 정사각이면 'SQUARE. 여기는 둘 다 직사각이라 'RECTANGLE 로 안전.
procedure(MKPADSTACK(name cx cy px py ox oy)
  let((pl)
    pl = list()
    pl = cons(make_axlPadStackPad(?layer "TOP"            ?type 'REGULAR
              ?figure 'RECTANGLE ?figureSize cx:cy) pl)
    ; 규칙 6: 마스크는 동판을 따라간다 (1:1)
    pl = cons(make_axlPadStackPad(?layer "SOLDERMASK_TOP" ?type 'REGULAR
              ?figure 'RECTANGLE ?figureSize cx:cy) pl)
    ; 페이스트는 벤더 랜드만큼만, 단자 위로 오프셋
    pl = cons(make_axlPadStackPad(?layer "PASTEMASK_TOP"  ?type 'REGULAR
              ?figure 'RECTANGLE ?figureSize px:py ?offset ox:oy) pl)
    axlDBCreatePadStack(name nil pl t)
    axlPadstackToDisk(name)
    LOG("padstack %s copper %.2fx%.2f paste %.2fx%.2f off %.3f:%.3f"
        name cx cy px py ox oy)
  )
)

MKPADSTACK(PAD_SM  DS_SMX SM_H   DS_SMX DS_SMY  0.0      SM_POFF)
MKPADSTACK(PAD_TAB TAB_W  DS_TABY DS_TABX DS_TABY TAB_POFF 0.0)

;======================= 2. 핀 ========================================
; 회전은 좌표 부호에서 유도한다 -> SX 를 뒤집으면 회전도 따라 뒤집힌다.
procedure(MKPIN(ps num x y vert)
  let((rot))
    rot = if(vert
             then if(y < 0.0 then 0.0 else 180.0)     ; 소형단자: 아래줄 0, 위줄 180
             else if(x < 0.0 then 0.0 else 180.0))    ; 탭     : 좌 0, 우 180
    axlDBCreatePin(ps x:y
      make_axlPinText(?number num ?offset 0.0:0.0
        ?text make_axlTextOrientation(?textBlock "1" ?rotation 0.0
              ?mirrored nil ?justify "center"))
      rot)
    LOG("  pin %s at %.3f:%.3f rot %.0f" num x y rot)
  )
)

; 아래줄 (평면도 기준 좌->우 : 3, 2, 1)
MKPIN(PAD_SM "3" SX*(-PITCH) (-SM_C) t)
MKPIN(PAD_SM "2" 0.0         (-SM_C) t)
MKPIN(PAD_SM "1" SX*( PITCH) (-SM_C) t)
; 윗줄 (평면도 기준 좌->우 : 4, 5, 6)
MKPIN(PAD_SM "4" SX*(-PITCH)   SM_C  t)
MKPIN(PAD_SM "5" 0.0           SM_C  t)
MKPIN(PAD_SM "6" SX*( PITCH)   SM_C  t)
; 탭 (Pri) : 7 = 좌, 8 = 우
MKPIN(PAD_TAB "7" SX*(-TAB_C) 0.0 nil)
MKPIN(PAD_TAB "8" SX*( TAB_C) 0.0 nil)

;======================= 3. 레이어 초기화 =============================
axlDeleteByLayer(list(L_SILK L_ASSY L_PB
                      "REF DES/SILKSCREEN_TOP" "REF DES/ASSEMBLY_TOP"))

;======================= 4. 실크 (규칙 7: 패드에서 0.1) ===============
; 패드가 4변을 모두 점유하므로 모서리 ㄱ자만 그린다.
;   가로선(y=±4.19) : 소형패드 측면 2.45 에서 0.10 떨어진 2.55 에서 끝
;   세로선(x=±4.00) : 탭패드 상하 1.50 에서 0.10 떨어진 1.60 에서 끝
foreach(c list(list(-1.0 -1.0) list(1.0 -1.0) list(1.0 1.0) list(-1.0 1.0))
  let((sx sy)
    sx = car(c)  sy = cadr(c)
    axlDBCreateLine(list((sx*SILK_HX):(sy*EY) (sx*EX):(sy*EY) (sx*EX):(sy*SILK_VY))
                    SILK_W L_SILK)))
; 핀1 도트 (핀1 쪽 모서리 바깥)
P1X = SX*4.25
P1Y = -4.45
axlDBCreateCircle(list(P1X:P1Y 0.20) SILK_W L_SILK)

;======================= 5. 어셈블리 (한 붓) ==========================
axlDBCreateLine(
  list((-EX):(-EY) EX:(-EY) EX:EY (-EX):EY (-EX):(-EY))
  ASSY_W L_ASSY)
axlDBCreateCircle(list(P1X:P1Y 0.20) ASSY_W L_ASSY)

;======================= 6. PLACE_BOUND (채운 사각형) =================
axlDBCreateRectangle(list((-PB_X):(-PB_Y) PB_X:PB_Y) t L_PB)

;======================= 7. REFDES (규칙 12) ==========================
RX = -PB_X + 0.4               ; -4.20
RY = SM_OE + 0.35              ;  5.04
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
