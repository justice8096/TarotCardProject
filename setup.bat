@echo off
setlocal enabledelayedexpansion
title Tarot Card Project — Setup

echo ============================================================
echo  Tarot Card Project — Setup Script
echo  Creates directories, installs Python deps, checks tools
echo ============================================================
echo.

:: ── 1. Check Python ───────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.10+ from https://python.org
    echo         Make sure "Add Python to PATH" is checked during install.
    pause & exit /b 1
)
for /f "tokens=*" %%v in ('python --version') do echo [OK] %%v

:: ── 2. Check Node.js ──────────────────────────────────────────
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js not found. Install Node.js 20+ from https://nodejs.org
    pause & exit /b 1
)
for /f "tokens=*" %%v in ('node --version') do echo [OK] Node.js %%v

:: ── 3. Check Git ──────────────────────────────────────────────
git --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Git not found. Install from https://git-scm.com
    pause & exit /b 1
)
for /f "tokens=*" %%v in ('git --version') do echo [OK] %%v

:: ── 4. Check FFmpeg ───────────────────────────────────────────
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo [WARN] FFmpeg not found in PATH.
    echo        Download from https://ffmpeg.org/download.html and add to PATH.
    echo        Required for concatenating animation clips into MP4 files.
) else (
    echo [OK] FFmpeg found
)

:: ── 5. Install Python packages ────────────────────────────────
echo.
echo Installing Python packages...
pip install Pillow PyJWT requests --quiet
if errorlevel 1 (
    echo [ERROR] pip install failed. Check your Python/pip installation.
    pause & exit /b 1
)
echo [OK] Python packages installed (Pillow, PyJWT, requests)

:: ── 6. Install n8n (if not already installed) ─────────────────
echo.
n8n --version >nul 2>&1
if errorlevel 1 (
    echo Installing n8n globally (this may take a few minutes)...
    npm install -g n8n
    if errorlevel 1 (
        echo [ERROR] n8n install failed.
        pause & exit /b 1
    )
    echo [OK] n8n installed
) else (
    for /f "tokens=*" %%v in ('n8n --version') do echo [OK] n8n %%v already installed
)

:: ── 7. Create required data directories ───────────────────────
echo.
echo Creating data directories...

set CARD_DIR=D:\data\cards\Standard
set KF_DIR=%CARD_DIR%\Keyframes

for %%d in (
    "D:\data\cards\Standard"
    "D:\data\cards\Standard\Keyframes"
    "D:\data\cards\Standard\animations"
) do (
    if not exist %%d (
        mkdir %%d
        echo [CREATED] %%d
    ) else (
        echo [EXISTS]  %%d
    )
)

:: ── 8. Create start_n8n.bat ───────────────────────────────────
echo.
echo Creating start_n8n.bat...
(
echo @echo off
echo title n8n — Tarot Card Project
echo echo Starting n8n with required environment...
echo echo.
echo set NODE_FUNCTION_ALLOW_BUILTIN=*
echo set NODE_FUNCTION_ALLOW_EXTERNAL=*
echo set N8N_RUNNERS_TASK_TIMEOUT=28800
echo echo NODE_FUNCTION_ALLOW_BUILTIN = * (fs, path, child_process enabled^)
echo echo NODE_FUNCTION_ALLOW_EXTERNAL = * (axios and other npm packages enabled^)
echo echo N8N_RUNNERS_TASK_TIMEOUT   = 28800 (8 hours — needed for long AI jobs^)
echo echo.
echo echo Open http://localhost:5678 in your browser once started.
echo echo.
echo n8n start
) > start_n8n.bat
echo [OK] start_n8n.bat created

:: ── 9. Check for ComfyUI ──────────────────────────────────────
echo.
if exist "D:\ComfyUI_windows_portable\ComfyUI\main.py" (
    echo [OK] ComfyUI found at D:\ComfyUI_windows_portable\
) else (
    echo [WARN] ComfyUI not found at D:\ComfyUI_windows_portable\
    echo        Download the Windows portable from:
    echo        https://github.com/comfyanonymous/ComfyUI/releases
    echo        Extract to D:\ComfyUI_windows_portable\
)

:: ── 10. Check for required ComfyUI models ─────────────────────
echo.
echo Checking ComfyUI models...
set COMFY=D:\ComfyUI_windows_portable\ComfyUI

set MISSING_MODELS=0
for %%m in (
    "models\diffusion_models\wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors"
    "models\diffusion_models\wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors"
    "models\text_encoders\umt5_xxl_fp8_e4m3fn_scaled.safetensors"
    "models\vae\wan_2.1_vae.safetensors"
    "models\checkpoints\dreamshaper_8.safetensors"
) do (
    if exist "%COMFY%\%%~m" (
        echo [OK] %%~m
    ) else (
        echo [MISS] %%~m
        set MISSING_MODELS=1
    )
)

if "!MISSING_MODELS!"=="1" (
    echo.
    echo [WARN] Some models are missing. See INSTALL.md for download links.
)

:: ── Done ──────────────────────────────────────────────────────
echo.
echo ============================================================
echo  Setup complete!
echo.
echo  Next steps:
echo    1. If any models are missing, see INSTALL.md for downloads
echo    2. Copy your Deck.json to D:\data\cards\Standard\Deck.json
echo    3. Run start_n8n.bat to launch n8n
echo    4. Open http://localhost:5678 and import workflows from n8n\
echo    5. Start ComfyUI (D:\ComfyUI_windows_portable\run_nvidia_gpu.bat)
echo    6. Run the "Generate Dealer Stop Motion" workflow in n8n
echo ============================================================
echo.
pause
