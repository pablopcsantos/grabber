@echo off
setlocal
cd /d "%~dp0"

echo ================================================================
echo Grabber - build portavel para Windows
echo ================================================================

where py >nul 2>nul
if errorlevel 1 (
  echo ERRO: Python nao foi encontrado pelo comando py.
  echo Instale Python 3.11 ou superior apenas na maquina usada para o build.
  pause
  exit /b 1
)

if not exist ".venv-build" py -m venv .venv-build
call .venv-build\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements-build.txt

set "ICON_ARGS="
if exist "assets\grabber.ico" set "ICON_ARGS=--icon=assets\grabber.ico --add-data=assets\grabber.ico;assets"
if exist "assets\grabber.png" set "ICON_ARGS=%ICON_ARGS% --add-data=assets\grabber.png;assets"

python -m PyInstaller --noconfirm --clean --onefile --windowed --name Grabber %ICON_ARGS% app.py
if errorlevel 1 (
  echo Build falhou.
  pause
  exit /b 1
)

echo.
echo Build concluido: dist\Grabber.exe
echo Copie o EXE para o pendrive e execute sem instalar Python.
pause
