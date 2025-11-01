@echo off
TITLE FLOWORK Core - Dependency Installer

REM ## Menentukan path root server secara dinamis dari lokasi skrip ini.
set "SERVER_ROOT_PATH=%~dp0"
set "SERVER_ROOT_PATH=%SERVER_ROOT_PATH:~0,-1%"

set "PYTHON_EXE=%SERVER_ROOT_PATH%\python\python.exe"

echo [INFO] Using bundled Python at: %PYTHON_EXE%

echo [INFO] Attempting to repair/upgrade Pip...
"%PYTHON_EXE%" -m pip install --upgrade pip setuptools --user --no-warn-script-location > nul 2>&1
if %errorlevel% neq 0 (
    echo [WARN] Failed to upgrade pip, might be okay. Continuing...
) else (
    echo [SUCCESS] Pip is healthy.
)

REM ## PENAMBAHAN: Menggunakan file requirements baru yang lebih simpel untuk dependensi dasar.
echo [INFO] Step 1: Installing core libraries...
"%PYTHON_EXE%" -m pip install -r "%SERVER_ROOT_PATH%\requirements-core.txt"

REM ## PENAMBAHAN: Instalasi khusus untuk library AI/ML langsung dari source code GitHub agar lebih stabil.
echo [INFO] Step 2: Installing AI/ML libraries (diffusers, transformers)...
"%PYTHON_EXE%" -m pip install git+https://github.com/huggingface/diffusers.git
"%PYTHON_EXE%" -m pip install git+https://github.com/huggingface/transformers.git
"%PYTHON_EXE%" -m pip install git+https://github.com/huggingface/accelerate.git

REM ## PENAMBAHAN: Ini bagian pentingnya. Kita kasih tau build-system di mana letak CMake.
echo [INFO] Step 3: Preparing environment for local compilation...
set "CMAKE_ARGS=-DCMAKE_TOOLCHAIN_FILE=%SERVER_ROOT_PATH%vendor\vcpkg\scripts\buildsystems\vcpkg.cmake"

REM ## PENAMBAHAN: Sekarang kita paksa pip untuk install llama-cpp-python dari folder vendor lokal TANPA DEPENDENSINYA.
echo [INFO] Step 4: Compiling and installing llama-cpp-python from local source...
"%PYTHON_EXE%" -m pip install --no-dependencies --force-reinstall --no-cache-dir --verbose "%SERVER_ROOT_PATH%\vendor\llama.cpp"

REM ## PENAMBAHAN: Membersihkan environment variable setelah selesai.
set "CMAKE_ARGS="

if %errorlevel% neq 0 (
    echo [FATAL] An error occurred during installation. Please check the messages above.
    pause
    exit /b 1
)

echo.
echo [SUCCESS] All dependencies installed correctly.
echo [INFO] You can now run '1.start_core.bat' or 'start_all.bat'.
pause