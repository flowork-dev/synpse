REM#######################################################################
REM WEBSITE https://flowork.cloud
REM File NAME : C:\FLOWORK\2-STOP_DOCKER_(SAFE).bat total lines 29 
REM#######################################################################

@echo off
TITLE FLOWORK - Docker Stopper v1.4 (Safe Mode)

cls
echo =================================================================
echo        FLOWORK DOCKER STACK STOPPER (SAFE MODE)
echo =================================================================
echo.
echo --- [LANGKAH 1/2] Mematikan dan menghapus semua container Flowork ---
rem (PERBAIKAN KUNCI) Flag '-v' dihapus agar volume data (termasuk database) TIDAK ikut terhapus.
rem Ini akan menjaga data user, engine, dan preset Anda tetap aman saat Docker dimatikan.
docker-compose down --remove-orphans

echo.
echo --- [LANGKAH 2/2] Membersihkan container sisa (hantu) ---
docker container prune -f

echo.
echo -----------------------------------------------------------------
echo [SUCCESS] Semua service Flowork telah dimatikan. Data Anda aman.
echo -----------------------------------------------------------------
echo.
pause
