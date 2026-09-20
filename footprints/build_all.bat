@echo off
rem =====================================================================
rem  build_all.bat  -  SKILL 스크립트 9종을 일괄 빌드하고 1차 점검한다
rem
rem  하는 일 (부품마다):
rem    1) 씨앗 .dra 를 <심볼>.dra 로 복사
rem    2) .il 의 WORKDIR 한 줄만 실제 경로로 바꿔 작업폴더에 복사 (원본 불변)
rem    3) run.scr 을 만들고 allegro.exe -nograph 로 실행
rem    4) 로그에서 패드스택 실패 / DRC 값 / .psm 생성 여부를 점검
rem    5) extracta 로 COMPOSITE_PAD 를 뽑아 expected.txt 대조 준비
rem
rem  주의: 이 배치는 검증을 '대신' 해주지 않는다. 최종 판정은 extracta 출력을
rem        각 폴더의 expected.txt 와 직접 대조해서 내려야 한다.
rem =====================================================================

setlocal

rem ==================== 사용자 설정 ====================
set "ALLEGRO=C:\Cadence\SPB_23.1\tools\bin\allegro.exe"
set "EXTRACTA=C:\Cadence\SPB_23.1\tools\bin\extracta.exe"
set "SRC=D:\fp\scripts"                                   rem *.il 이 있는 폴더
set "WORK=D:\fp\build"                                    rem 산출물이 나올 폴더
set "SEED=D:\fp\seed.dra"                                 rem 씨앗 .dra (기존 심볼 복사본)
set "CTRL=D:\fp\cpad_bv.txt"                              rem share\pcb\text\views\cpad_bv.txt 복사본
rem ====================================================

if not exist "%ALLEGRO%"  ( echo [ERROR] allegro.exe 없음 : %ALLEGRO%  & exit /b 1 )
if not exist "%SEED%"     ( echo [ERROR] 씨앗 .dra 없음   : %SEED%     & exit /b 1 )
if not exist "%SRC%"      ( echo [ERROR] 스크립트 폴더 없음 : %SRC%     & exit /b 1 )
if not exist "%WORK%" mkdir "%WORK%"

set /a FAIL=0
set "WS=%WORK:\=/%"

call :build qfn50p500x500x90-33m  buildqfn32
call :build caprr750w80d185h420   buildcaprr750
call :build diom2014x90m          builddiom2014
call :build indm8084x550-8m       buildindm8084
call :build soic127p600x175-9m    buildsoic127
call :build sop65p490x104-9m      buildsop65p490
call :build indc1608x95m          buildindc1608
call :build sot95p280x145-5m      buildsot95p280
call :build sot95p237x112-3m      buildsot95p237

echo.
echo =====================================================================
if %FAIL%==0 (
  echo  빌드 9종 모두 1차 점검 통과. 이제 %WORK%\*_cpad.txt 를
  echo  각 폴더의 expected.txt 와 대조하십시오.
) else (
  echo  문제 %FAIL% 건. 위의 [ERROR] / [WARN] 줄과 해당 로그를 확인하십시오.
)
echo =====================================================================
exit /b %FAIL%


rem ---------------------------------------------------------------------
:build
rem  %1 = 심볼 이름 (소문자)   %2 = 스크립트 이름 (확장자 제외)
set "SYM=%~1"
set "ILN=%~2"
set "LOG=build_%ILN:~5%.log"

echo.
echo ---------- %SYM% ----------

if not exist "%SRC%\%ILN%.il" (
  echo   [ERROR] %ILN%.il 없음
  set /a FAIL+=1
  goto :eof
)

rem --- WORKDIR 치환본을 작업폴더에 생성 (원본 .il 은 수정하지 않는다) ---
powershell -NoProfile -Command "(Get-Content -Raw '%SRC%\%ILN%.il') -replace '(?m)^WORKDIR\s*=.*$', 'WORKDIR = \"%WS%/\"' | Set-Content -Encoding UTF8 '%WORK%\%ILN%.il'"
if errorlevel 1 (
  echo   [ERROR] WORKDIR 치환 실패
  set /a FAIL+=1
  goto :eof
)

copy /y "%SEED%" "%WORK%\%SYM%.dra" >nul
if exist "%WORK%\%LOG%" del /q "%WORK%\%LOG%"

pushd "%WORK%"
echo skill load("%WS%/%ILN%.il") > run.scr
"%ALLEGRO%" -nograph -s run.scr "%SYM%.dra"
popd

rem --- 1차 점검 ---
if not exist "%WORK%\%LOG%" (
  echo   [ERROR] 로그가 없다. Allegro 기동 실패 또는 라이선스 문제.
  set /a FAIL+=1
  goto :eof
)

findstr /i /c:"Illegal figure size" "%WORK%\%LOG%" >nul 2>&1
if not errorlevel 1 (
  echo   [ERROR] 패드스택 생성 실패 - 정사각 패드에 RECTANGLE 을 쓴 경우. 로그 확인.
  set /a FAIL+=1
)

findstr /i /c:"SPMHA1" "%WORK%\%LOG%" >nul 2>&1
if not errorlevel 1 (
  echo   [ERROR] 중복 핀번호로 심볼 생성 중단.
  set /a FAIL+=1
)

for /f "tokens=*" %%L in ('findstr /c:"DRC = " "%WORK%\%LOG%" 2^>nul') do echo   %%L
findstr /c:"DRC = 0" "%WORK%\%LOG%" >nul 2>&1
if errorlevel 1 (
  echo   [WARN] DRC 가 0 이 아니거나 값을 못 읽었다. 로그의 DRC 줄을 직접 확인할 것.
  set /a FAIL+=1
)

if not exist "%WORK%\%SYM%.psm" (
  echo   [ERROR] .psm 미생성.
  set /a FAIL+=1
) else (
  echo   OK : %SYM%.dra / %SYM%.psm 생성됨
)

rem --- extracta : COMPOSITE_PAD 추출 ---
rem  함정 회피 - 출력 파일이 이미 있으면 stdin 대기로 멈추므로 먼저 지우고,
rem              항상 <nul 로 실행한다. .dra 가 없으면 아예 돌리지 않는다.
if not exist "%EXTRACTA%" goto :eof
if not exist "%CTRL%"     goto :eof
if not exist "%WORK%\%SYM%.dra" goto :eof
if exist "%WORK%\%SYM%_cpad.txt" del /q "%WORK%\%SYM%_cpad.txt"
pushd "%WORK%"
"%EXTRACTA%" "%SYM%.dra" "%CTRL%" "%SYM%_cpad.txt" <nul
popd
if exist "%WORK%\%SYM%_cpad.txt" echo   extracta -^> %SYM%_cpad.txt

goto :eof
