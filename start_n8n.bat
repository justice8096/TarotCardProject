@echo off
title n8n — Tarot Card Project
echo Starting n8n with required environment...
echo.

REM ─────────────────────────────────────────────────────────────────────────────
REM  HuggingFace token — required for gated models (Orpheus TTS, etc.)
REM  Get your token at: https://huggingface.co/settings/tokens
REM  Then replace the placeholder below with your actual token.
REM ─────────────────────────────────────────────────────────────────────────────
if "%HF_TOKEN%"=="" (
    echo WARNING: HF_TOKEN is not set.
    echo          Gated HuggingFace models ^(e.g. Orpheus TTS^) will fail to download.
    echo          Get your token at https://huggingface.co/settings/tokens
    echo          Then set it below: set HF_TOKEN=hf_xxxxxxxxxxxx
    echo.
) else (
    echo HF_TOKEN                    = SET
)

set NODE_FUNCTION_ALLOW_BUILTIN=*
set NODE_FUNCTION_ALLOW_EXTERNAL=*
set N8N_RUNNERS_TASK_TIMEOUT=28800
echo NODE_FUNCTION_ALLOW_BUILTIN = * (fs, path, child_process enabled)
echo NODE_FUNCTION_ALLOW_EXTERNAL = * (axios and other npm packages enabled)
echo N8N_RUNNERS_TASK_TIMEOUT   = 28800 (8 hours — needed for long AI jobs)
echo.
echo Open http://localhost:5678 in your browser once started.
echo.
n8n start
