REM#######################################################################
REM WEBSITE https://flowork.cloud
REM File NAME : C:\FLOWORK\0-FORCE_REBUILD.bat total lines 185 
REM#######################################################################

@echo off
rem (PERBAIKAN) Karakter '&' diganti dengan 'dan' untuk menghindari error batch
TITLE FLOWORK - FULL RESET AND FORCE REBUILD
cd /d "%~dp0"

cls
echo =================================================================
echo     FLOWORK DOCKER - JURUS SAPU JAGAT DAN BANGUN ULANG PAKSA
echo =================================================================
echo.

rem --- (MODIFIKASI KODE OLEH GEMINI - REFACTOR FIX) ---
rem (English Hardcode) STEP 0/5: Nuke ONLY the database/config directory.
rem (English Hardcode) We MUST NOT delete the root /modules, /plugins, etc.
echo --- [LANGKAH 0/5] Menghancurkan folder database lama (Sapu Jagat)... ---
echo [INFO] Menghapus C:\FLOWORK\data (termasuk DBs dan docker-engine.conf)...
rmdir /S /Q "%~dp0\\data"

rem --- (PENAMBAHAN KODE OLEH GEMINI - REFACTOR FIX) ---
rem (English Hardcode) The rmdir commands below are COMMENTED OUT
rem (English Hardcode) to prevent deleting permanent user data (modules, plugins, etc.)
rem (English Hardcode) This is the fix for the data loss bug.
rem echo [INFO] Menghapus C:\FLOWORK\ai_models...
rem rmdir /S /Q "%~dp0\\ai_models"
rem echo [INFO] Menghapus C:\FLOWORK\ai_providers...
rem rmdir /S /Q "%~dp0\\ai_providers"
rem echo [INFO] Menghapus C:\FLOWORK\assets...
rem rmdir /S /Q "%~dp0\\assets"
rem echo [INFO] Menghapus C:\FLOWORK\formatters...
rem rmdir /S /Q "%~dp0\\formatters"
rem echo [INFO] Menghapus C:\FLOWORK\modules...
rem rmdir /S /Q "%~dp0\\modules"
rem echo [INFO] Menghapus C:\FLOWORK\plugins...
rem rmdir /S /Q "%~dp0\\plugins"
rem echo [INFO] Menghapus C:\FLOWORK\scanners...
rem rmdir /S /Q "%~dp0\\scanners"
rem echo [INFO] Menghapus C:\FLOWORK\tools...
rem rmdir /S /Q "%~dp0\\tools"
rem echo [INFO] Menghapus C:\FLOWORK\triggers...
rem rmdir /S /Q "%~dp0\\triggers"
rem --- (AKHIR PENAMBAHAN KODE) ---

rem (COMMENT) Legacy paths, kept commented out for history.
rem (COMMENT) rmdir /S /Q "%~dp0\\flowork-gateway\\data"
rem (COMMENT) rmdir /S /Q "%~dp0\\flowork-core-data"
echo [SUCCESS] Folder database lama bersih. Folder data utama (modules, plugins) AMAN.
echo.
rem --- (AKHIR MODIFIKASI KODE) ---


rem --- (PENAMBAHAN KODE OLEH GEMINI - BUG FIX STALE KEY 0x5ff...) ---
echo --- [LANGKAH BARU 1/6] Menghancurkan sisa container DAN VOLUME lama ---
echo [INFO] Menjalankan 'docker-compose down --volumes' untuk membunuh key lama (0x5ff...).
echo [INFO] Ini adalah FIX untuk bug "salah key" yang nyangkut di Docker Volume.
docker-compose down -v --remove-orphans
echo [SUCCESS] Semua sisa-sisa lama dan volume data lama sudah bersih.
echo.
rem --- (AKHIR PENAMBAHAN KODE) ---


rem --- (MODIFIKASI KODE) Nama langkah diubah dari 0/5 jadi 2/6 ---
echo --- [LANGKAH 2/6] Membuat ulang file .env dan semua folder data (jika belum ada) ---
echo [INFO] Memastikan image python:3.11-slim tersedia...
docker pull python:3.11-slim > nul
if %errorlevel% neq 0 (
    echo [ERROR] Gagal menarik image 'python:3.11-slim'. Pastikan Docker terhubung ke internet.
    pause
    exit /b 1
)
echo [INFO] Menggunakan container Docker untuk men-generate kredensial dan folder baru...

rem (COMMENT - BUG FIX) This logic is redundant with generate_env.py
rem (COMMENT) We will now call generate_env.py directly inside Docker.
rem (COMMENT) This centralizes token generation logic in one place.

rem (COMMENT) Generate NEW_ENGINE_ID
rem (COMMENT) set "NEW_ENGINE_ID="
rem (COMMENT) FOR /F "tokens=*" %%G IN ('docker run --rm python:3.11-slim python -c "import uuid; print(uuid.uuid4())"') DO (
rem (COMMENT)     set "NEW_ENGINE_ID=%%G"
rem (COMMENT) )
rem (COMMENT) set "NEW_ENGINE_ID=%NEW_ENGINE_ID: =%"
rem (COMMENT) set "NEW_ENGINE_ID=%NEW_ENGINE_ID: =%"

rem (COMMENT) Generate NEW_ENGINE_TOKEN
rem (COMMENT) set "NEW_ENGINE_TOKEN="
rem (COMMENT) FOR /F "tokens=*" %%G IN ('docker run --rm python:3.11-slim python -c "import secrets; print(f\"dev_engine_{secrets.token_hex(16)}\")"') DO (
rem (COMMENT)     set "NEW_ENGINE_TOKEN=%%G"
rem (COMMENT) )
rem (COMMENT) set "NEW_ENGINE_TOKEN=%NEW_ENGINE_TOKEN: =%"
rem (COMMENT) set "NEW_ENGINE_TOKEN=%NEW_ENGINE_TOKEN: =%"

rem (COMMENT) Call the centralized Python script
docker run --rm -v "%~dp0:/app" -w /app python:3.11-slim python generate_env.py --force
if %errorlevel% neq 0 (
    echo [ERROR] Gagal menjalankan generate_env.py.
    pause
    exit /b 1
)

echo [SUCCESS] File .env dan semua folder data telah di-generate/diverifikasi.
echo.

rem --- (MODIFIKASI KODE) Nama langkah diubah dari 1/5 jadi 3/6 ---
echo --- [LANGKAH 3/6] Memastikan Docker Desktop berjalan ---
docker info > nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker Desktop tidak berjalan. Nyalakan dulu dan jalankan lagi skrip ini.
    pause
    exit /b 1
)
echo [SUCCESS] Docker Desktop aktif.
echo.

rem --- (MODIFIKASI KODE) Nama langkah diubah dari 2/5 jadi 4/6 ---
rem --- (MODIFIKASI KODE OLEH GEMINI) Perintah 'down' dipindah ke LANGKAH BARU 1/6
echo --- [LANGKAH 4/6] Memastikan semua container mati (tanpa hapus volume) ---
rem (COMMENT) 'rmdir' commands moved to STEP 0
rem (COMMENT) echo [INFO] Menghapus data gateway lama (bind mount) untuk memastikan reset total...
rem (COMMENT) rmdir /S /Q "%~dp0\\flowork-gateway\\data"
rem --- (PENAMBAHAN KODE - ROADMAP 4.1 FIX) ---
rem (GEMINI COMMENT) This line is the BUG.
rem (English Hardcode) It deletes the 'flowork-core-data' folder
rem (English Hardcode) right after generate_env.py (Step 0) creates it.
rem (English Hardcode) This causes the bind mount to fail on 'docker-compose up'.
rem (English Hardcode) We are commenting it out (Rule #2).
rem rmdir /S /Q "%~dp0\\flowork-core-data"
rem --- (AKHIR PENAMBAHAN KODE) ---

rem --- (PENAMBAHAN KODE OLEH GEMINI - BUG FIX STALE KEY 0x5ff...) ---
rem (English Hardcode) We moved the '-v' command to the NEW STEP 1/6,
rem (English Hardcode) BEFORE generate_env.py runs.
rem (English Hardcode) The command here (STEP 4/6) is now just a safety check
rem (English Hardcode) to ensure containers are down before build.
rem (English Hardcode) This fixes BOTH Bug #7 AND the stale key bug.
rem (COMMENT - BUG #7 FIX) docker-compose down -v --remove-orphans
docker-compose down --remove-orphans
rem --- (AKHIR PENAMBAHAN KODE) ---

echo [SUCCESS] Semua sisa-sisa lama sudah bersih.
echo.

rem --- (MODIFIKASI KODE) Nama langkah diubah dari 3/5 jadi 5/6 ---
echo --- [LANGKAH 5/6] Membangun ulang SEMUA service tanpa cache ---
docker-compose build --no-cache
if %errorlevel% neq 0 (
    echo [ERROR] Proses build untuk service gagal. Periksa error di atas.
    pause
    exit /b 1
)
echo [SUCCESS] Semua image sudah siap dari nol.
echo.

rem --- (MODIFIKASI KODE) Nama langkah diubah dari 4/5 jadi 6/6 ---
echo --- [LANGKAH 6/6] Menyalakan semua service yang sudah baru ---
docker-compose up -d
echo.
docker-compose ps
echo.
echo -----------------------------------------------------------
echo [INFO] Main GUI is accessible at https://flowork.cloud
echo ------------------------------------------------------------
echo.

rem (PERBAIKAN KUNCI) Bagian ini diubah agar tidak "follow" dan menambahkan pencarian key
echo --- [AUTO-LOG] Displaying Cloudflare Tunnel status (last 50 lines)... ---
echo.
rem --- (PENAMBAHAN KODE OLEH GEMINI - BUG FIX NAMA LOG) ---
rem (English Hardcode) The service name in docker-compose.yml is 'flowork_cloudflared'.
rem (COMMENT) docker-compose logs --tail="50" cloudflared
docker-compose logs --tail="50" flowork_cloudflared
rem --- (AKHIR PENAMBAHAN KODE) ---
echo.
echo -----------------------------------------------------------------
echo.
echo --- [ AUTO-LOG (PENTING) ] MENCARI PRIVATE KEY BARU ANDA... ---
echo.
echo     Generated NEW Private Key akan muncul...
echo.
pause
