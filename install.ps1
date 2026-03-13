# install.ps1 — Tarot Card Project interactive installer for Windows
# Run: powershell -ExecutionPolicy Bypass -File install.ps1

$ErrorActionPreference = "Stop"

# ── Helpers ──────────────────────────────────────────────────────────────────

function Write-Status  { param($msg) Write-Host "  [OK] $msg" -ForegroundColor Green }
function Write-Skip    { param($msg) Write-Host "  [SKIP] $msg" -ForegroundColor Yellow }
function Write-Err     { param($msg) Write-Host "  [ERR] $msg" -ForegroundColor Red }
function Write-Section { param($msg) Write-Host "`n=== $msg ===" -ForegroundColor Cyan }

function Confirm-Step {
    param([string]$Prompt)
    $answer = Read-Host "$Prompt [Y/n]"
    return ($answer -eq '' -or $answer -match '^[Yy]')
}

function Test-Command {
    param([string]$Name)
    $null = Get-Command $Name -ErrorAction SilentlyContinue
    return $?
}

# ── Defaults ─────────────────────────────────────────────────────────────────

$DefaultDataDir    = "D:/data"
$DefaultComfyUIDir = "D:/ComfyUI_windows_portable"
$DefaultComfyUI    = "$DefaultComfyUIDir/ComfyUI"

# Let user override paths
Write-Host "`nTarot Card Project — Interactive Installer" -ForegroundColor Magenta
Write-Host "Press Enter to accept defaults, or type a custom path.`n"

$DataDir = Read-Host "Data directory [$DefaultDataDir]"
if (-not $DataDir) { $DataDir = $DefaultDataDir }

$ComfyUIDir = Read-Host "ComfyUI portable directory [$DefaultComfyUIDir]"
if (-not $ComfyUIDir) { $ComfyUIDir = $DefaultComfyUIDir }
$ComfyUI = "$ComfyUIDir/ComfyUI"

$installed = @()
$skipped   = @()

# ── Phase 1: Prerequisites ──────────────────────────────────────────────────

Write-Section "Phase 1: Prerequisites"

if (-not (Test-Command winget)) {
    Write-Err "winget not found. Install App Installer from the Microsoft Store first."
    exit 1
}
Write-Status "winget available"

# ── Phase 2: Core Tools ─────────────────────────────────────────────────────

Write-Section "Phase 2: Core Tools"

# Git
if (Test-Command git) {
    Write-Skip "Git already installed ($(git --version))"
} elseif (Confirm-Step "Install Git?") {
    winget install --id Git.Git -e --accept-source-agreements --accept-package-agreements
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    $installed += "Git"
} else { $skipped += "Git" }

# Python
if (Test-Command python) {
    $pyVer = python --version 2>&1
    Write-Skip "Python already installed ($pyVer)"
} elseif (Confirm-Step "Install Python 3.12?") {
    winget install --id Python.Python.3.12 -e --accept-source-agreements --accept-package-agreements
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    $installed += "Python"
} else { $skipped += "Python" }

# Node.js
if (Test-Command node) {
    $nodeVer = node --version 2>&1
    Write-Skip "Node.js already installed ($nodeVer)"
} elseif (Confirm-Step "Install Node.js LTS?") {
    winget install --id OpenJS.NodeJS.LTS -e --accept-source-agreements --accept-package-agreements
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    $installed += "Node.js"
} else { $skipped += "Node.js" }

# FFmpeg
if (Test-Command ffmpeg) {
    Write-Skip "FFmpeg already installed"
} elseif (Confirm-Step "Install FFmpeg?") {
    winget install --id Gyan.FFmpeg -e --accept-source-agreements --accept-package-agreements
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    $installed += "FFmpeg"
} else { $skipped += "FFmpeg" }

# Ollama
if (Test-Command ollama) {
    Write-Skip "Ollama already installed"
} elseif (Confirm-Step "Install Ollama (local LLM serving)?") {
    winget install --id Ollama.Ollama -e --accept-source-agreements --accept-package-agreements
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    $installed += "Ollama"
} else { $skipped += "Ollama" }

# n8n
if (Test-Command n8n) {
    Write-Skip "n8n already installed"
} elseif (Confirm-Step "Install n8n (workflow orchestration)?") {
    npm install -g n8n
    $installed += "n8n"
} else { $skipped += "n8n" }

# TypeScript
if (Test-Command tsc) {
    Write-Skip "TypeScript already installed"
} elseif (Confirm-Step "Install TypeScript?") {
    npm install -g typescript
    $installed += "TypeScript"
} else { $skipped += "TypeScript" }

# huggingface-cli (needed for model downloads)
$hfInstalled = $false
if (Test-Command huggingface-cli) {
    Write-Skip "huggingface-cli already installed"
    $hfInstalled = $true
} elseif (Confirm-Step "Install huggingface-cli (needed for model downloads)?") {
    pip install huggingface_hub[cli]
    $hfInstalled = $true
    $installed += "huggingface-cli"
} else { $skipped += "huggingface-cli" }

# ComfyUI
if (Test-Path "$ComfyUI/main.py") {
    Write-Skip "ComfyUI already installed at $ComfyUI"
} elseif (Confirm-Step "Install ComfyUI (portable)?") {
    Write-Host "  Downloading ComfyUI portable..." -ForegroundColor Gray
    $zipUrl = "https://github.com/comfyanonymous/ComfyUI/releases/latest/download/ComfyUI_windows_portable_nvidia.7z"
    $zipPath = "$env:TEMP\ComfyUI_portable.7z"
    Invoke-WebRequest -Uri $zipUrl -OutFile $zipPath -UseBasicParsing
    if (Test-Command 7z) {
        7z x $zipPath -o"$ComfyUIDir" -y
    } else {
        Write-Err "7z not found. Extract $zipPath to $ComfyUIDir manually, then re-run."
    }
    $installed += "ComfyUI"
} else { $skipped += "ComfyUI" }

# ── Phase 3: ComfyUI Custom Nodes ───────────────────────────────────────────

Write-Section "Phase 3: ComfyUI Custom Nodes"

$customNodes = "$ComfyUI/custom_nodes"
if (Test-Path $customNodes) {
    $nodeRepos = @(
        @{ Name = "ComfyUI-VideoHelperSuite"; Url = "https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git" }
    )
    foreach ($repo in $nodeRepos) {
        $dest = "$customNodes/$($repo.Name)"
        if (Test-Path $dest) {
            Write-Skip "$($repo.Name) already installed"
        } elseif (Confirm-Step "Install ComfyUI node: $($repo.Name)?") {
            git clone $repo.Url $dest
            if (Test-Path "$dest/requirements.txt") {
                & "$ComfyUIDir/python_embeded/python.exe" -m pip install -r "$dest/requirements.txt"
            }
            $installed += $repo.Name
        } else { $skipped += $repo.Name }
    }
} else {
    Write-Skip "ComfyUI custom_nodes directory not found — skipping"
}

# ── Phase 4: Directory Structure ────────────────────────────────────────────

Write-Section "Phase 4: Directory Structure"

$dirs = @(
    "$DataDir/cards/Standard/Keyframes",
    "$DataDir/cards/Standard/Narration",
    "$DataDir/cards/Standard/Music",
    "$DataDir/cards/Standard/Cards",
    "$DataDir/Full_Images",
    "$DataDir/Card_Part_Images",
    "$DataDir/errors",
    "$DataDir/Dealer_Animations"
)

foreach ($d in $dirs) {
    if (Test-Path $d) {
        Write-Skip "$d exists"
    } else {
        New-Item -ItemType Directory -Path $d -Force | Out-Null
        Write-Status "Created $d"
    }
}

# ── Phase 5: AI Model Downloads ─────────────────────────────────────────────

Write-Section "Phase 5: AI Model Downloads"

if (-not $hfInstalled) {
    Write-Skip "huggingface-cli not installed — skipping model downloads"
    Write-Host "  Run 'pip install huggingface_hub[cli]' then re-run this script." -ForegroundColor Yellow
} else {
    $modelsDir = "$ComfyUI/models"

    # Each entry: HF repo, filename in repo, local subdirectory, display name, approximate size
    $models = @(
        @{ Repo="Comfy-Org/Wan_2.2_ComfyUI_repackaged"; File="split_files/diffusion_models/wan2.2_i2v_720p_14B_fp8_scaled.safetensors"; Dest="diffusion_models"; OutName="wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors"; Label="Wan 2.2 I2V high noise (14B fp8)"; Size="~14 GB" },
        @{ Repo="Comfy-Org/Wan_2.2_ComfyUI_repackaged"; File="split_files/diffusion_models/wan2.2_i2v_720p_14B_fp8_scaled.safetensors"; Dest="diffusion_models"; OutName="wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors"; Label="Wan 2.2 I2V low noise (14B fp8)"; Size="~14 GB" },
        @{ Repo="Kijai/WanVideo_comfy"; File="lightx2v_loras/wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors"; Dest="loras"; OutName="wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors"; Label="LightX2V 4-step LoRA"; Size="~1.2 GB" },
        @{ Repo="Comfy-Org/Wan_2.2_ComfyUI_repackaged"; File="split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors"; Dest="text_encoders"; OutName="umt5_xxl_fp8_e4m3fn_scaled.safetensors"; Label="umt5_xxl text encoder (fp8)"; Size="~6.7 GB" },
        @{ Repo="Comfy-Org/stable-diffusion-3.5-fp8"; File="text_encoders/clip_l.safetensors"; Dest="text_encoders"; OutName="clip_l.safetensors"; Label="CLIP-L text encoder"; Size="~250 MB" },
        @{ Repo="Comfy-Org/Wan_2.2_ComfyUI_repackaged"; File="split_files/vae/wan_2.1_vae.safetensors"; Dest="vae"; OutName="wan_2.1_vae.safetensors"; Label="Wan 2.1 VAE"; Size="~250 MB" },
        @{ Repo="Lykon/DreamShaper"; File="DreamShaper_8_pruned.safetensors"; Dest="checkpoints"; OutName="dreamshaper_8.safetensors"; Label="DreamShaper 8"; Size="~2 GB" },
        @{ Repo="Comfy-Org/HiDream_I1_ComfyUI_repackaged"; File="split_files/diffusion_models/hidream_i1_full_fp8.safetensors"; Dest="diffusion_models"; OutName="hidream_i1_full_fp8.safetensors"; Label="HiDream I1 Full (fp8)"; Size="~17 GB" },
        @{ Repo="stabilityai/stable-audio-open-1.0"; File="model.safetensors"; Dest="checkpoints"; OutName="stable-audio-open-1.0.safetensors"; Label="Stable Audio Open 1.0"; Size="~1 GB" },
        @{ Repo="google-t5/t5-base"; File="model.safetensors"; Dest="text_encoders"; OutName="t5-base.safetensors"; Label="T5-base text encoder"; Size="~900 MB" },
        @{ Repo="stabilityai/stable-zero123"; File="stable_zero123.ckpt"; Dest="checkpoints"; OutName="stable_zero123.ckpt"; Label="Stable Zero123"; Size="~5 GB" },
        @{ Repo="ShoukanLabs/Orpheus-GGUF"; File="orpheus-3b-0.1-ft-UD-Q6_K_XL.gguf"; Dest="gguf"; OutName="orpheus-3b-0.1-ft-UD-Q6_K_XL.gguf"; Label="Orpheus 3B GGUF (Q6_K_XL)"; Size="~2 GB" },
        @{ Repo="briaai/RMBG-2.0"; File="model.pth"; Dest="custom_nodes"; OutName="RMBG-2.0.pth"; Label="RMBG 2.0 (background removal)"; Size="~200 MB" }
    )

    foreach ($m in $models) {
        $destPath = "$modelsDir/$($m.Dest)/$($m.OutName)"
        if (Test-Path $destPath) {
            Write-Skip "$($m.Label) already exists"
        } elseif (Confirm-Step "Download $($m.Label) ($($m.Size))?") {
            $destDir = "$modelsDir/$($m.Dest)"
            if (-not (Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir -Force | Out-Null }
            huggingface-cli download $m.Repo $m.File --local-dir $destDir
            # Rename if needed
            $downloaded = "$destDir/$($m.File)"
            if ((Test-Path $downloaded) -and ($m.File -ne $m.OutName)) {
                Move-Item $downloaded $destPath -Force
            }
            $installed += $m.Label
        } else { $skipped += $m.Label }
    }
}

# ── Phase 6: Ollama Models ──────────────────────────────────────────────────

Write-Section "Phase 6: Ollama Models"

if (Test-Command ollama) {
    $ollamaModels = @(
        @{ Name="gemma3n"; Label="Gemma 3N (for tarot meanings)" },
        @{ Name="mistral"; Label="Mistral (for narration styles)" }
    )
    foreach ($om in $ollamaModels) {
        # Check if model is already pulled
        $existing = ollama list 2>&1 | Select-String $om.Name
        if ($existing) {
            Write-Skip "$($om.Label) already pulled"
        } elseif (Confirm-Step "Pull Ollama model: $($om.Label)?") {
            ollama pull $om.Name
            $installed += "Ollama:$($om.Name)"
        } else { $skipped += "Ollama:$($om.Name)" }
    }
} else {
    Write-Skip "Ollama not installed — skipping model pulls"
}

# ── Phase 7: Config Generation ──────────────────────────────────────────────

Write-Section "Phase 7: Configuration"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$configPath = "$scriptDir/config.json"

if (Test-Path $configPath) {
    Write-Skip "config.json already exists at $configPath"
} elseif (Confirm-Step "Generate config.json?") {
    $config = @{
        "_comment"             = "Machine-specific configuration for the TarotCardProject."
        "_usage"               = "Set the TAROT_CONFIG environment variable to the absolute path of this file."
        DataDir                = $DataDir -replace '\\','/'
        CardsDir               = "$DataDir/cards" -replace '\\','/'
        DefaultDeckDir         = "$DataDir/cards/Standard" -replace '\\','/'
        DefaultDeckJsonPath    = "$DataDir/cards/Standard/Deck.json" -replace '\\','/'
        LegacyDeckJsonPath     = "$DataDir/cards/Deck.json" -replace '\\','/'
        FullImagesDir          = "$DataDir/Full_Images" -replace '\\','/'
        CardPartImagesDir      = "$DataDir/Card_Part_Images" -replace '\\','/'
        ErrorsDir              = "$DataDir/errors" -replace '\\','/'
        SpreadsheetPath        = "$DataDir/TarotSpreadsheet2.ods" -replace '\\','/'
        LegacySpreadsheetPath  = "$DataDir/CardImages.ods" -replace '\\','/'
        ComfyUIDir             = "$ComfyUI" -replace '\\','/'
        ComfyUIAPI             = "http://127.0.0.1:8188"
        OllamaAPI              = "http://127.0.0.1:11434"
    } | ConvertTo-Json -Depth 3
    Set-Content -Path $configPath -Value $config -Encoding UTF8
    Write-Status "Generated $configPath"
    $installed += "config.json"
} else { $skipped += "config.json" }

# ── Phase 8: Summary ────────────────────────────────────────────────────────

Write-Section "Summary"

if ($installed.Count -gt 0) {
    Write-Host "`n  Installed:" -ForegroundColor Green
    foreach ($i in $installed) { Write-Host "    + $i" -ForegroundColor Green }
}
if ($skipped.Count -gt 0) {
    Write-Host "`n  Skipped:" -ForegroundColor Yellow
    foreach ($s in $skipped) { Write-Host "    - $s" -ForegroundColor Yellow }
}

Write-Host "`n  Next steps:" -ForegroundColor Cyan
Write-Host "    1. Start ComfyUI:  run $ComfyUIDir\run_nvidia_gpu.bat"
Write-Host "    2. Start n8n with required flags:"
Write-Host '       set NODE_FUNCTION_ALLOW_BUILTIN=* && set NODE_FUNCTION_ALLOW_EXTERNAL=* && set N8N_RUNNERS_TASK_TIMEOUT=28800 && n8n start'
Write-Host "    3. Import n8n workflows from the n8n/ folder"
Write-Host "    4. Import ComfyUI workflows from the ComfyUI/ folder"
Write-Host ""
