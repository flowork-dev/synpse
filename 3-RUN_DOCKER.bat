REM#######################################################################
REM WEBSITE https://flowork.cloud
REM File NAME : C:\FLOWORK\3-RUN_DOCKER.bat total lines 126 
REM#######################################################################

@echo off
TITLE FLOWORK - Docker Launcher v1.8 (Path Fix)
cd /d "%~dp0"

cls
echo =================================================================
echo           FLOWORK DOCKER STACK LAUNCHER
echo =================================================================
echo.
echo --- [STEP 1/4] Ensuring Docker Desktop is running ---
docker info > nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker Desktop is not running. Please start it and run this script again.
    pause
    exit /b 1
)
echo [SUCCESS] Docker Desktop is active.
echo.

rem Otomatis mematikan container lama (tanpa menghapus database)
echo --- [STEP 2/4] Stopping any old running containers (Safe Mode) ---
docker-compose down
echo [SUCCESS] Old containers stopped.
echo.


echo --- [STEP 3/4] Building (or rebuilding) and starting all services ---
echo (The container's internal command now handles all initial setup)
docker-compose up --build -d
if %errorlevel% neq 0 (
    echo [ERROR] Docker Compose failed to build or start containers.
    pause
    exit /b 1
)
echo.
echo --- [STEP 4/4] Displaying the status of running containers ---
echo.
docker-compose ps
echo.
echo -----------------------------------------------------------
echo [INFO] Main GUI is accessible at https://flowork.cloud
echo ------------------------------------------------------------
echo.
echo [IMPORTANT!] If the Core Engine still fails to authenticate after a few minutes,
echo             please check the logs using 'docker-compose logs core'.
echo.

rem Menampilkan log tunnel (singkat)
echo --- [AUTO-LOG] Displaying Cloudflare Tunnel status (last 50 lines)... ---
echo.
rem --- (PENAMBAHAN KODE OLEH GEMINI - FIX NAMA SERVICE) ---
rem (English Hardcode) The service name is 'flowork_cloudflared', not 'cloudflared'.
rem (COMMENT) docker-compose logs --tail="50" cloudflared
docker-compose logs --tail="50" flowork_cloudflared
rem --- (AKHIR PENAMBAHAN KODE) ---
echo.
echo -----------------------------------------------------------------
echo.

rem --- (PERBAIKAN KODE OLEH GEMINI) ---
rem (English Hardcode) The original 'docker compose logs' command is unreliable
rem (English Hardcode) because the key is only printed ONCE when the user is first created.
rem (English Hardcode) The 'create_admin.py' script saves the key to the 'flowork-gateway/data'
rem (English Hardcode) volume, which is the reliable source of truth. We will now 'TYPE' (cat) that file.
echo --- [ AUTO-LOG (PENTING) ] MENCARI PRIVATE KEY ANDA... ---
echo.
echo    Your Login Private Key should appear below (inside the warning box):
echo    (If empty/not found, you MUST run '1-STOP_DOCKER_(RESET_DATABASE).bat' ONCE)
echo.

rem --- (PENAMBAHAN KODE OLEH GEMINI - REFACTOR) ---
rem (English Hardcode) Path updated to reflect the new centralized '/data' folder
rem (COMMENT - BUG #1 FIX) The line below was incorrect. It pointed to the global /data folder,
rem (COMMENT - BUG #1 FIX) but create_admin.py (running inside the gateway container)
rem (COMMENT - BUG #1 FIX) saves the key relative to its /app mount, which is /flowork-gateway/data on the host.
rem set "KEY_FILE_PATH=%~dp0\data\DO_NOT_DELETE_private_key.txt"
rem (COMMENT) set "KEY_FILE_PATH=%~dp0\flowork-gateway\data\DO_NOT_DELETE_private_key.txt"
rem --- (AKHIR PENAMBAHAN KODE) ---

rem --- (PENAMBAHAN KODE OLEH GEMINI - BUG #1 FIX) ---
rem (English Hardcode) This is the CORRECT path based on the 'docker-compose.yml' volume mount
rem (English Hardcode) for 'flowork_gateway' which maps './flowork-gateway' to '/app'.
rem (English Hardcode) AND... the '0-FORCE_REBUILD.bat' script now creates the key in the *root* /data folder.
rem (English Hardcode) THIS IS THE CORRECT PATH.
rem (COMMENT) set "KEY_FILE_PATH=%~dp0\flowork-gateway\data\DO_NOT_DELETE_private_key.txt"
set "KEY_FILE_PATH=%~dp0\data\DO_NOT_DELETE_private_key.txt"
rem --- (AKHIR PENAMBAHAN KODE) ---

if exist "%KEY_FILE_PATH%" (
    echo [INFO] Reading key from saved file: %KEY_FILE_PATH%
    echo.
    echo !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    echo !!! YOUR LOGIN PRIVATE KEY IS:
    rem --- START PENAMBAHAN KODE (FIX FORMATTING) ---
    echo.
    TYPE "%KEY_FILE_PATH%"
    echo.
    rem --- AKHIR PENAMBAHAN KODE ---
    echo !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    echo.
) else (
    echo [ERROR] Key file not found at %KEY_FILE_PATH%
    echo [ERROR] This can happen on first run if the container is still starting.
    echo [ERROR] Trying to find it in the logs as a fallback...
    echo.
    rem (COMMENT) This is the unreliable original command, kept as a fallback for the very first run.
    docker compose logs gateway | findstr /C:"!!! Generated NEW Private Key:" /C:"0x"
)
rem (COMMENT) This line is now replaced by the logic above.
rem (COMMENT) docker compose logs gateway | findstr /C:"!!! YOUR LOGIN PRIVATE KEY IS" /C:"0x"
rem --- (AKHIR PERBAIKAN KODE) ---

echo.
echo -----------------------------------------------------------------
rem --- (PENAMBAHAN KODE OLEH GEMINI - FIX SINTAKS BATCH) ---
rem (English Hardcode) Added 'echo' to fix '[INFO] is not recognized' error
echo [INFO] Copy the Private Key line above (it already includes '0x') and use it to log in.
rem --- (AKHIR PENAMBAHAN KODE) ---
echo.
pause
