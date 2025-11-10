REM#######################################################################
REM WEBSITE https://flowork.cloud
REM File NAME : C:\FLOWORK\4-DOCKER_LOGS.bat total lines 69 
REM#######################################################################

@echo off
TITLE FLOWORK - Docker Log Viewer v1.2 (Open Core MVP)

cls
echo =================================================================
echo                 FLOWORK - DOCKER LOG VIEWER
echo =================================================================
echo.
echo [INFO] Script ini akan menampilkan 100 baris log terakhir dari
echo        service Gateway, Core Engine, dan Cloudflare Tunnel
echo        untuk membantu debugging setup Open Core MVP.
echo.
echo -----------------------------------------------------------------
echo.

echo --- [1/3] Menampilkan Log untuk: flowork_gateway ---
echo.
rem --- (PENAMBAHAN KODE OLEH GEMINI - BUG FIX NAMA LOG) ---
rem (English Hardcode) The service name in docker-compose.yml is 'flowork_gateway'.
rem (COMMENT) docker-compose logs --tail="100" gateway
docker-compose logs --tail="100" flowork_gateway
rem --- (AKHIR PENAMBAHAN KODE) ---

echo.
echo -----------------------------------------------------------------
echo.

rem (PERBAIKAN) Bagian untuk momod-api dihapus karena tidak lagi di Docker
rem echo --- [2/3] Menampilkan Log untuk: flowork_momod-api ---
rem echo.
rem docker-compose logs --tail="100" momod-api
rem echo.
rem echo -----------------------------------------------------------------
rem echo.

rem (PERBAIKAN) Nomor urut disesuaikan
echo --- [2/3] Menampilkan Log untuk: flowork_core ---
echo.
rem --- (PENAMBAHAN KODE OLEH GEMINI - BUG FIX NAMA LOG) ---
rem (English Hardcode) The service name in docker-compose.yml is 'flowork_core'.
rem (COMMENT) docker-compose logs --tail="100" core
docker-compose logs --tail="100" flowork_core
rem --- (AKHIR PENAMBAHAN KODE) ---

echo.
echo -----------------------------------------------------------------
echo.

rem (PENAMBAHAN) Menampilkan log cloudflared, penting untuk koneksi WSS
echo --- [3/3] Menampilkan Log untuk: flowork_cloudflared ---
echo.
rem --- (PENAMBAHAN KODE OLEH GEMINI - BUG FIX NAMA LOG) ---
rem (English Hardcode) The service name in docker-compose.yml is 'flowork_cloudflared'.
rem (COMMENT) docker-compose logs --tail="100" cloudflared
docker-compose logs --tail="100" flowork_cloudflared
rem --- (AKHIR PENAMBAHAN KODE) ---

echo.
echo -----------------------------------------------------------------
echo [SUCCESS] Log telah ditampilkan. Tekan tombol apa saja untuk menutup.
echo -----------------------------------------------------------------
echo.
pause
