@echo off
REM ============================================================
REM Cursor Builder - PyInstaller 스탠드얼론 빌드 스크립트
REM 실행: build.bat
REM 산출물: dist\CursorBuilder.exe (단일 실행 파일, GUI)
REM ============================================================
setlocal
cd /d "%~dp0"

REM 1) 의존성 설치 (필요 시)
python -m pip install --upgrade pip >nul 2>&1
python -m pip install -r requirements.txt

REM 2) 빌드 (아이콘이 있으면 적용, 없으면 생략)
set "ICON_OPT="
if exist icons\app.ico set "ICON_OPT=--icon icons\app.ico"

python -m PyInstaller ^
  --onefile ^
  --windowed ^
  --name CursorBuilder ^
  %ICON_OPT% ^
  --add-data "locales;locales" ^
  --hidden-import PIL._tkinter_finder ^
  --collect-all ttkbootstrap ^
  main.py

echo.
echo 빌드 완료: dist\CursorBuilder.exe
pause
