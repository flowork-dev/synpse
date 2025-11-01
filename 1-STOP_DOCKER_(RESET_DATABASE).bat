@echo off
TITLE FLOWORK - Docker Stopper v1.3 (JURUS SAPU JAGAT)

cls
echo =================================================================
echo        FLOWORK DOCKER STACK STOPPER (JURUS SAPU JAGAT)
echo =================================================================
echo.
echo --- [LANGKAH 1/2] Mematikan dan menghapus semua service Flowork ---
echo (Ini akan menghapus container, jaringan, dan volume data...)
docker-compose down -v --remove-orphans

echo.
echo --- [LANGKAH 2/2] Memburu dan membersihkan semua container sisa (hantu) ---
docker container prune -f

echo.
echo -----------------------------------------------------------------
echo [SUCCESS] Jurus Sapu Jagat selesai! Semua service dan sisa container telah dibersihkan.
echo -----------------------------------------------------------------
echo.
pause