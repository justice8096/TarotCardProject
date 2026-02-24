@echo off
title n8n — Tarot Card Project
echo Starting n8n with required environment...
echo.
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
