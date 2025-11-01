@echo off
TITLE FLOWORK Gateway - Dependency Installer

REM #######################################################################
REM # Skrip ini HANYA untuk menginstal library untuk Gateway
REM # dari file requirements.txt di folder ini.
REM #######################################################################

echo [INFO] Starting FLOWORK Gateway dependency installation...
echo.

REM ## Otomatis mendeteksi lokasi folder gateway (tempat .bat ini berada)
set "GATEWAY_ROOT_PATH=%~dp0"

REM ## Tentukan path ke Python & requirements.txt di dalam folder ini
set "PYTHON_EXE=%GATEWAY_ROOT_PATH%python\python.exe"
set "REQUIREMENTS_FILE=%GATEWAY_ROOT_PATH%requirements.txt"

REM ## Validasi path
if not exist "%PYTHON_EXE%" (
    echo [FATAL] Bundled Python not found at: %PYTHON_EXE%
    pause
    exit /b 1
)
if not exist "%REQUIREMENTS_FILE%" (
    echo [FATAL] requirements.txt not found at: %REQUIREMENTS_FILE%
    pause
    exit /b 1
)

echo [INFO] Python and requirements.txt found.
echo [INFO] Installing libraries for the Gateway... please wait.
echo ----------------------------------------------------------------------

REM ## Jalankan pip install
"%PYTHON_EXE%" -m pip install -r "%REQUIREMENTS_FILE%"

echo ----------------------------------------------------------------------
echo [SUCCESS] Gateway dependencies installed successfully.
echo.
pause