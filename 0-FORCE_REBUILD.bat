@echo off
rem (PERBAIKAN) Karakter '&' diganti dengan 'dan' untuk menghindari error batch
TITLE FLOWORK - FULL RESET AND FORCE REBUILD

cls
echo =================================================================
echo        FLOWORK DOCKER - JURUS SAPU JAGAT DAN BANGUN ULANG PAKSA
echo =================================================================
echo.

rem --- (PENAMBAHAN KODE) LANGKAH 0/5: Generate file .env baru ---
echo --- [LANGKAH 0/5] Menghapus dan membuat ulang file .env dengan ID dan Token baru ---
echo [INFO] Memastikan image python:3.11-slim tersedia...
docker pull python:3.11-slim > nul
if %errorlevel% neq 0 (
    echo [ERROR] Gagal menarik image 'python:3.11-slim'. Pastikan Docker terhubung ke internet.
    pause
    exit /b 1
)
echo [INFO] Menggunakan container Docker untuk men-generate kredensial baru...

rem (COMMENT - BUG FIX) This logic is redundant with generate_env.py
rem (COMMENT) We will now call generate_env.py directly inside Docker.
rem (COMMENT) This centralizes token generation logic in one place.

rem (COMMENT) Generate NEW_ENGINE_ID
rem (COMMENT) set "NEW_ENGINE_ID="
rem (COMMENT) FOR /F "tokens=*" %%G IN ('docker run --rm python:3.11-slim python -c "import uuid; print(uuid.uuid4())"') DO (
rem (COMMENT)     set "NEW_ENGINE_ID=%%G"
rem (COMMENT) )

rem (COMMENT) Generate NEW_ENGINE_TOKEN
rem (COMMENT) set "NEW_ENGINE_TOKEN="
rem (COMMENT) FOR /F "tokens=*" %%G IN ('docker run --rm python:3.11-slim python -c "import secrets; print(f'dev_engine_{secrets.token_hex(16)}');"') DO (
rem (COMMENT)     set "NEW_ENGINE_TOKEN=%%G"
rem (COMMENT) )

rem (COMMENT) Validasi
rem (COMMENT) if not defined NEW_ENGINE_ID (
rem (COMMENT)     echo [ERROR] Gagal men-generate NEW_ENGINE_ID. Docker command gagal?
rem (COMMENT)     pause
rem (COMMENT)     exit /b 1
rem (COMMENT) )
rem (COMMENT) if not defined NEW_ENGINE_TOKEN (
rem (COMMENT)     echo [ERROR] Gagal men-generate NEW_ENGINE_TOKEN. Docker command gagal?
rem (COMMENT)     pause
rem (COMMENT)     exit /b 1
rem (COMMENT) )

rem (COMMENT) echo [SUCCESS] ID dan Token baru telah di-generate.
rem (COMMENT) echo [INFO]    Engine ID: %NEW_ENGINE_ID%
rem (COMMENT) echo [INFO]    Engine Token: %NEW_ENGINE_TOKEN:~0,20%...

rem --- (PENAMBAHAN KODE) Run the Python script inside Docker ---
rem (COMMENT) This command mounts the current directory (C:\FLOWORK) to /app
rem (COMMENT) and then executes the Python script. The script will
rem (COMMENT) generate and write the .env and docker-engine.conf files.
docker run --rm -v "%~dp0:/app" python:3.11-slim python /app/generate_env.py
if %errorlevel% neq 0 (
    echo [ERROR] Gagal menjalankan generate_env.py di dalam Docker.
    pause
    exit /b 1
)
echo [SUCCESS] File .env dan docker-engine.conf telah di-generate oleh generate_env.py.

rem --- (COMMENT) Tulis file .env ---
rem (COMMENT) This section is now handled by generate_env.py
rem (COMMENT) echo [INFO] Menulis file .env baru...
rem (COMMENT) set "ENV_PATH=%~dp0\.env"
rem (COMMENT) (
rem (COMMENT)     echo #######################################################################
rem (COMMENT)     echo # WEBSITE https://flowork.cloud
rem (COMMENT)     echo # File NAME : C:\FLOWORK\.env
rem (COMMENT)     echo # CATATAN: File ini digenerate ulang oleh 0-FORCE_REBUILD.bat
rem (COMMENT)     echo #######################################################################
rem (COMMENT)     echo JWT_SECRET_KEY=e8a3b5d7c1f0a9b2c8d4e6f3a1b0c9d8e7f6a5b4c3d2e1f0a9b8c7d6e5f4a3b2
rem (COMMENT)     echo FLOWORK_MASTER_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDOK2XQAbPhhAo+\nAmHSPE6GcYWFpxEMHXR3BKeTgIomECpFgj6r+RR1YOMh6duv/Hg3IVPwlrsxWu8a\nGCi0Q4RDwZOEtj18CH4FU7n0sx6wAb0o28YsdlivD0p7Zz9cW0ARZdl2M1CiM5z/\nFSltUdn+lBgc8n5mxWUT01k0KQ4ds+BfJ9nRwFVnatDNJpHNTt7wPemMuo4On1F3\nhr5HeNCmeVDfqLXmyMC9L0U8KOMQtk2solzev2UxvyKitC0Y/1ZwPjGOTv/eWf49\nd1HPKRAZCchReJFufj8LIReYpcemGYCSawM0mV25SXplzcr30ibg6jG/rMbFkjfs\n4QT1LiOtAgMBAAECggEAEYFhaxb2uHUNdZRrZksILXKU8FmhVFKcuyciOQXKAej1\n3eI5z6cd7WJLoGtXfVesUWoIBlgvqF72b4dezwEiL6qcPvSsv2WGzCb+yN/7zamb\nVeb+d0BmAuWc4MhOFFmlh/sKfhAyjk/5lzZE+gSs9zVV35qLajVKggA8OI/GPg+k\nec/8WURswmLfQ2wspPqapRr9rTH0AOJttwGo+vHkZW83BFkvJTOFsALILJpHFRPi\noimreTtB2g9Senu86fE96xlzlf1Rxwk+Yu2tggaFCsqrQBKi4NfX0BXPIB7p70RQ\nTW9n5NNalrfTH7WeOUwnoMOOqrYMIe4Ty4mS3p8D1QKBgQD8b5KrxDwmofL2ZPnQ\nofDdqPw/+exUAnl5BzdXPSZ/FI/E8oN35Fy1O0WPQntMNemOpBh0AJ1qO0eaVPpY\nlWcSD04+xkOULqMhHM7xo5ERcBbIXQYcbfy7mp5PwRuDsn7e2nh1aai2a3P+cB0n\nFZKk2jjRMqEJ5aj0/w6YcnAswwKBgQDRFJh5w/ulxITezPhjczAqFssGd7ULKqEc\nj7uZEOf513P98nRUc5Bbd6jooweZVPHgXc8b3UMGzJERb3TCGV786sLCGyvF4Hg0\nK6ZlUW+ulmnK0lgZLmwxLS1BtBiQ3SIGsWHVk+EC2dOrcKVahMtW2Xh1Tikrey2O\nC6J8eYcmzwKBgQC1qal4mSjceHF7peEtpkzLh7+4XqgXMQyv72SBEI2yqF5qUkgQ\nMLQS7Eu7tBE9IBMrRqYeXQ7rkyuNQhhDRYk+MuuRO2cIraNRwgSfWqGcVfjfSiqK\nrRBTBgtlw8eEOCEbSUek31u9o4h/E7m3FcxJfI2k5vWDRNYZMbAUP07AtwKBgBWf\npa1iQZKBYqSQWlgev6p6tQC0PLss64DCtMo932ANkmd/PdzGHvX2yDdXNR/8kw97\nZEIjfh0j5xUAi/jPGu3Zcc8VdE+Aya3Lnef4pi5OTB635nikPnhPjdCvyaKh3DUI\n/29RXgIneSbP/aoA9e7DixvGu6dNlAaO2X06LGotAoGAGaS142dquefEX5AMj7od\nKXqJs8EqBQ4L1OBqjeOmMwBhQW6yMNzIxrHuSCGGzPKlB5/U7IvO4y5bG8HgwlwG\nHORvcU+5Vij4SKvVNDXOR6gGd0Y3ARvwPHvZ39eoPv7Zi82yfD53oFhrjwvqaqWe\nyZfN5iu7WksKlUgGPeIUnSA=\n-----END PRIVATE KEY-----"
rem (COMMENT)     echo GATEWAY_SECRET_TOKEN=flork_sec_9f8e7d6c5b4a3c2d1e0f9b8a7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d
rem (COMMENT)     echo CLOUDFLARED_TOKEN=eyJhIjoiZmFmNjU2ODU5YmZkYjMyNDZiYjFkZTZiNjAzMTFmZjAiLCJ0IjoiNWQ2NDEyYWQtMDliZC00M2Y4LWJkOGYtNjBkNmQ2MjkxODA5IiwicyI6Ik9HRTRPR0UxWmpBdFpEazJZUzAwWWpZekxUaGtabUl0TkdWaVpEbGxOREppWXpNeCJ9
rem (COMMENT)     echo.
rem (COMMENT)     echo FLOWORK_ENGINE_ID=%NEW_ENGINE_ID%
rem (COMMENT)     echo FLOWORK_ENGINE_TOKEN=%NEW_ENGINE_TOKEN%
rem (COMMENT) ) > "%ENV_PATH%"
rem (COMMENT) echo [SUCCESS] File .env baru telah ditulis.

rem --- (COMMENT) Tulis file docker-engine.conf ---
rem (COMMENT) This section is now handled by generate_env.py
rem (COMMENT) echo [INFO] Menulis file docker-engine.conf baru...
rem (COMMENT) set "CONF_PATH=%~dp0\flowork-core-data\docker-engine.conf"
rem (COMMENT) rem Pastikan folder ada
rem (COMMENT) if not exist "%~dp0\flowork-core-data" mkdir "%~dp0\flowork-core-data"
rem (COMMENT) (
rem (COMMENT)     echo {
rem (COMMENT)     echo     "gateway_api_url": "http://gateway:8000",
rem (COMMENT)     echo     "gateway_webapp_url": "https://flowork.cloud",
rem (COMMENT)     echo     "engine_token": "%NEW_ENGINE_TOKEN%"
rem (COMMENT)     echo }
rem (COMMENT) ) > "%CONF_PATH%"
rem (COMMENT) echo [SUCCESS] File docker-engine.conf baru telah ditulis.
echo.
rem --- (AKHIR PENAMBAHAN KODE) ---

echo --- [LANGKAH 1/5] Memastikan Docker Desktop berjalan ---
docker info > nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker Desktop tidak jalan. Nyalakan dulu, baru jalankan lagi skrip ini.
    pause
    exit /b 1
)
echo [SUCCESS] Docker Desktop aktif.
echo.

echo --- [LANGKAH 2/5] Menghancurkan semua container dan volume lama (Sapu Jagat) ---
docker-compose down -v --remove-orphans
echo [SUCCESS] Semua sisa-sisa lama sudah bersih.
echo.

echo --- [LANGKAH 3/5] Membangun ulang SEMUA service tanpa cache ---
docker-compose build --no-cache
if %errorlevel% neq 0 (
    echo [ERROR] Proses build untuk service gagal. Periksa error di atas.
    pause
    exit /b 1
)
echo [SUCCESS] Semua image sudah siap dari nol.
echo.

echo --- [LANGKAH 4/5] Menyalakan semua service yang sudah baru ---
docker-compose up -d
echo.
docker-compose ps
echo.
echo -----------------------------------------------------------
echo [SUCCESS] All Flowork services have been started.
echo [INFO] Please wait a moment for all services to become healthy.
echo [INFO] Main GUI is accessible at https://flowork.cloud
echo [INFO] Admin Panel is accessible at https://momod.flowork.cloud
echo [INFO] Main API is accessible at https://api.flowork.cloud
echo [INFO] --- For Local Debugging Only ---
echo [INFO] Core Dashboard at http://localhost:5001
echo [INFO] RabbitMQ Mgmt at http://localhost:15672
echo ------------------------------------------------------------
echo.

rem (PERBAIKAN KUNCI) Bagian ini diubah agar tidak "follow" dan menambahkan pencarian key
echo --- [AUTO-LOG] Displaying Cloudflare Tunnel status (last 50 lines)... ---
echo.
docker-compose logs --tail="50" cloudflared
echo.
echo -----------------------------------------------------------------
echo.
echo --- [ AUTO-LOG (PENTING) ] MENCARI PRIVATE KEY BARU ANDA... ---
echo.
echo    Generated NEW Private Key akan muncul di bawah ini:
echo.
docker compose logs gateway | findstr "Generated"
echo.
echo -----------------------------------------------------------------
echo [INFO] Salin 'Generated NEW Private Key' di atas dan gunakan untuk login.
echo.
pause