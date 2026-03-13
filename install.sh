#!/usr/bin/env bash
# install.sh — Tarot Card Project interactive installer for Linux/Mac
# Usage: chmod +x install.sh && ./install.sh
set -euo pipefail

# ── Helpers ──────────────────────────────────────────────────────────────────

GREEN='\033[0;32m'; YELLOW='\033[0;33m'; RED='\033[0;31m'
CYAN='\033[0;36m'; MAGENTA='\033[0;35m'; GRAY='\033[0;90m'; NC='\033[0m'

ok()      { echo -e "  ${GREEN}[OK]${NC} $1"; }
skip()    { echo -e "  ${YELLOW}[SKIP]${NC} $1"; }
err()     { echo -e "  ${RED}[ERR]${NC} $1"; }
section() { echo -e "\n${CYAN}=== $1 ===${NC}"; }

confirm() {
    read -rp "$1 [Y/n] " ans
    [[ -z "$ans" || "$ans" =~ ^[Yy] ]]
}

has_cmd() { command -v "$1" &>/dev/null; }

detect_pkg_manager() {
    if has_cmd brew; then echo "brew"
    elif has_cmd apt-get; then echo "apt"
    elif has_cmd dnf; then echo "dnf"
    elif has_cmd pacman; then echo "pacman"
    else echo "none"
    fi
}

pkg_install() {
    local pkg="$1"
    case "$PKG" in
        brew)   brew install "$pkg" ;;
        apt)    sudo apt-get install -y "$pkg" ;;
        dnf)    sudo dnf install -y "$pkg" ;;
        pacman) sudo pacman -S --noconfirm "$pkg" ;;
        *)      err "No package manager found. Install $pkg manually."; return 1 ;;
    esac
}

# ── Defaults ─────────────────────────────────────────────────────────────────

DEFAULT_DATA_DIR="$HOME/tarot-data"
DEFAULT_COMFYUI_DIR="$HOME/ComfyUI"

echo -e "\n${MAGENTA}Tarot Card Project — Interactive Installer${NC}"
echo "Press Enter to accept defaults, or type a custom path."
echo ""

read -rp "Data directory [$DEFAULT_DATA_DIR]: " DATA_DIR
DATA_DIR="${DATA_DIR:-$DEFAULT_DATA_DIR}"

read -rp "ComfyUI directory [$DEFAULT_COMFYUI_DIR]: " COMFYUI_DIR
COMFYUI_DIR="${COMFYUI_DIR:-$DEFAULT_COMFYUI_DIR}"

PKG=$(detect_pkg_manager)
INSTALLED=()
SKIPPED=()

# ── Phase 1: Prerequisites ──────────────────────────────────────────────────

section "Phase 1: Prerequisites"

if [[ "$PKG" == "none" ]]; then
    err "No supported package manager found (brew, apt, dnf, pacman)."
    err "Install packages manually and re-run."
    exit 1
fi
ok "Package manager: $PKG"

# ── Phase 2: Core Tools ─────────────────────────────────────────────────────

section "Phase 2: Core Tools"

# Git
if has_cmd git; then
    skip "Git already installed ($(git --version))"
elif confirm "Install Git?"; then
    pkg_install git
    INSTALLED+=("Git")
else SKIPPED+=("Git"); fi

# Python
if has_cmd python3; then
    skip "Python already installed ($(python3 --version))"
elif confirm "Install Python 3?"; then
    case "$PKG" in
        brew) brew install python3 ;;
        apt)  sudo apt-get install -y python3 python3-pip python3-venv ;;
        dnf)  sudo dnf install -y python3 python3-pip ;;
        pacman) sudo pacman -S --noconfirm python python-pip ;;
    esac
    INSTALLED+=("Python")
else SKIPPED+=("Python"); fi

# Node.js
if has_cmd node; then
    skip "Node.js already installed ($(node --version))"
elif confirm "Install Node.js LTS?"; then
    case "$PKG" in
        brew) brew install node ;;
        apt)  curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash - && sudo apt-get install -y nodejs ;;
        dnf)  sudo dnf install -y nodejs ;;
        pacman) sudo pacman -S --noconfirm nodejs npm ;;
    esac
    INSTALLED+=("Node.js")
else SKIPPED+=("Node.js"); fi

# FFmpeg
if has_cmd ffmpeg; then
    skip "FFmpeg already installed"
elif confirm "Install FFmpeg?"; then
    pkg_install ffmpeg
    INSTALLED+=("FFmpeg")
else SKIPPED+=("FFmpeg"); fi

# Ollama
if has_cmd ollama; then
    skip "Ollama already installed"
elif confirm "Install Ollama (local LLM serving)?"; then
    curl -fsSL https://ollama.com/install.sh | sh
    INSTALLED+=("Ollama")
else SKIPPED+=("Ollama"); fi

# n8n
if has_cmd n8n; then
    skip "n8n already installed"
elif confirm "Install n8n (workflow orchestration)?"; then
    npm install -g n8n
    INSTALLED+=("n8n")
else SKIPPED+=("n8n"); fi

# TypeScript
if has_cmd tsc; then
    skip "TypeScript already installed"
elif confirm "Install TypeScript?"; then
    npm install -g typescript
    INSTALLED+=("TypeScript")
else SKIPPED+=("TypeScript"); fi

# huggingface-cli
HF_INSTALLED=false
if has_cmd huggingface-cli; then
    skip "huggingface-cli already installed"
    HF_INSTALLED=true
elif confirm "Install huggingface-cli (needed for model downloads)?"; then
    pip3 install huggingface_hub[cli]
    HF_INSTALLED=true
    INSTALLED+=("huggingface-cli")
else SKIPPED+=("huggingface-cli"); fi

# ComfyUI
if [[ -f "$COMFYUI_DIR/main.py" ]]; then
    skip "ComfyUI already installed at $COMFYUI_DIR"
elif confirm "Install ComfyUI (git clone)?"; then
    git clone https://github.com/comfyanonymous/ComfyUI.git "$COMFYUI_DIR"
    echo -e "  ${GRAY}Installing Python dependencies...${NC}"
    pip3 install -r "$COMFYUI_DIR/requirements.txt"
    INSTALLED+=("ComfyUI")
else SKIPPED+=("ComfyUI"); fi

# ── Phase 3: ComfyUI Custom Nodes ───────────────────────────────────────────

section "Phase 3: ComfyUI Custom Nodes"

CUSTOM_NODES="$COMFYUI_DIR/custom_nodes"
if [[ -d "$CUSTOM_NODES" ]]; then
    declare -A NODE_REPOS=(
        ["ComfyUI-VideoHelperSuite"]="https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git"
    )
    for name in "${!NODE_REPOS[@]}"; do
        dest="$CUSTOM_NODES/$name"
        if [[ -d "$dest" ]]; then
            skip "$name already installed"
        elif confirm "Install ComfyUI node: $name?"; then
            git clone "${NODE_REPOS[$name]}" "$dest"
            if [[ -f "$dest/requirements.txt" ]]; then
                pip3 install -r "$dest/requirements.txt"
            fi
            INSTALLED+=("$name")
        else SKIPPED+=("$name"); fi
    done
else
    skip "ComfyUI custom_nodes directory not found — skipping"
fi

# ── Phase 4: Directory Structure ────────────────────────────────────────────

section "Phase 4: Directory Structure"

DIRS=(
    "$DATA_DIR/cards/Standard/Keyframes"
    "$DATA_DIR/cards/Standard/Narration"
    "$DATA_DIR/cards/Standard/Music"
    "$DATA_DIR/cards/Standard/Cards"
    "$DATA_DIR/Full_Images"
    "$DATA_DIR/Card_Part_Images"
    "$DATA_DIR/errors"
    "$DATA_DIR/Dealer_Animations"
)

for d in "${DIRS[@]}"; do
    if [[ -d "$d" ]]; then
        skip "$d exists"
    else
        mkdir -p "$d"
        ok "Created $d"
    fi
done

# ── Phase 5: AI Model Downloads ─────────────────────────────────────────────

section "Phase 5: AI Model Downloads"

if ! $HF_INSTALLED; then
    skip "huggingface-cli not installed — skipping model downloads"
    echo -e "  ${YELLOW}Run 'pip3 install huggingface_hub[cli]' then re-run.${NC}"
else
    MODELS_DIR="$COMFYUI_DIR/models"

    # Format: "repo|file_in_repo|local_subdir|output_name|label|size"
    MODEL_LIST=(
        "Comfy-Org/Wan_2.2_ComfyUI_repackaged|split_files/diffusion_models/wan2.2_i2v_720p_14B_fp8_scaled.safetensors|diffusion_models|wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors|Wan 2.2 I2V high noise (14B fp8)|~14 GB"
        "Comfy-Org/Wan_2.2_ComfyUI_repackaged|split_files/diffusion_models/wan2.2_i2v_720p_14B_fp8_scaled.safetensors|diffusion_models|wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors|Wan 2.2 I2V low noise (14B fp8)|~14 GB"
        "Kijai/WanVideo_comfy|lightx2v_loras/wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors|loras|wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors|LightX2V 4-step LoRA|~1.2 GB"
        "Comfy-Org/Wan_2.2_ComfyUI_repackaged|split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors|text_encoders|umt5_xxl_fp8_e4m3fn_scaled.safetensors|umt5_xxl text encoder (fp8)|~6.7 GB"
        "Comfy-Org/stable-diffusion-3.5-fp8|text_encoders/clip_l.safetensors|text_encoders|clip_l.safetensors|CLIP-L text encoder|~250 MB"
        "Comfy-Org/Wan_2.2_ComfyUI_repackaged|split_files/vae/wan_2.1_vae.safetensors|vae|wan_2.1_vae.safetensors|Wan 2.1 VAE|~250 MB"
        "Lykon/DreamShaper|DreamShaper_8_pruned.safetensors|checkpoints|dreamshaper_8.safetensors|DreamShaper 8|~2 GB"
        "Comfy-Org/HiDream_I1_ComfyUI_repackaged|split_files/diffusion_models/hidream_i1_full_fp8.safetensors|diffusion_models|hidream_i1_full_fp8.safetensors|HiDream I1 Full (fp8)|~17 GB"
        "stabilityai/stable-audio-open-1.0|model.safetensors|checkpoints|stable-audio-open-1.0.safetensors|Stable Audio Open 1.0|~1 GB"
        "google-t5/t5-base|model.safetensors|text_encoders|t5-base.safetensors|T5-base text encoder|~900 MB"
        "stabilityai/stable-zero123|stable_zero123.ckpt|checkpoints|stable_zero123.ckpt|Stable Zero123|~5 GB"
        "ShoukanLabs/Orpheus-GGUF|orpheus-3b-0.1-ft-UD-Q6_K_XL.gguf|gguf|orpheus-3b-0.1-ft-UD-Q6_K_XL.gguf|Orpheus 3B GGUF (Q6_K_XL)|~2 GB"
        "briaai/RMBG-2.0|model.pth|custom_nodes|RMBG-2.0.pth|RMBG 2.0 (background removal)|~200 MB"
    )

    for entry in "${MODEL_LIST[@]}"; do
        IFS='|' read -r repo file subdir outname label size <<< "$entry"
        dest_path="$MODELS_DIR/$subdir/$outname"
        if [[ -f "$dest_path" ]]; then
            skip "$label already exists"
        elif confirm "Download $label ($size)?"; then
            dest_dir="$MODELS_DIR/$subdir"
            mkdir -p "$dest_dir"
            huggingface-cli download "$repo" "$file" --local-dir "$dest_dir"
            # Rename if the downloaded file path differs from output name
            downloaded="$dest_dir/$file"
            if [[ -f "$downloaded" && "$file" != "$outname" ]]; then
                mv "$downloaded" "$dest_path"
            fi
            INSTALLED+=("$label")
        else SKIPPED+=("$label"); fi
    done
fi

# ── Phase 6: Ollama Models ──────────────────────────────────────────────────

section "Phase 6: Ollama Models"

if has_cmd ollama; then
    OLLAMA_MODELS=(
        "gemma3n|Gemma 3N (for tarot meanings)"
        "mistral|Mistral (for narration styles)"
    )
    for entry in "${OLLAMA_MODELS[@]}"; do
        IFS='|' read -r name label <<< "$entry"
        if ollama list 2>/dev/null | grep -q "$name"; then
            skip "$label already pulled"
        elif confirm "Pull Ollama model: $label?"; then
            ollama pull "$name"
            INSTALLED+=("Ollama:$name")
        else SKIPPED+=("Ollama:$name"); fi
    done
else
    skip "Ollama not installed — skipping model pulls"
fi

# ── Phase 7: Config Generation ──────────────────────────────────────────────

section "Phase 7: Configuration"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG_PATH="$SCRIPT_DIR/config.json"

if [[ -f "$CONFIG_PATH" ]]; then
    skip "config.json already exists at $CONFIG_PATH"
elif confirm "Generate config.json?"; then
    cat > "$CONFIG_PATH" <<CONF
{
    "_comment": "Machine-specific configuration for the TarotCardProject.",
    "_usage": "Set the TAROT_CONFIG environment variable to the absolute path of this file.",
    "DataDir": "$DATA_DIR",
    "CardsDir": "$DATA_DIR/cards",
    "DefaultDeckDir": "$DATA_DIR/cards/Standard",
    "DefaultDeckJsonPath": "$DATA_DIR/cards/Standard/Deck.json",
    "LegacyDeckJsonPath": "$DATA_DIR/cards/Deck.json",
    "FullImagesDir": "$DATA_DIR/Full_Images",
    "CardPartImagesDir": "$DATA_DIR/Card_Part_Images",
    "ErrorsDir": "$DATA_DIR/errors",
    "SpreadsheetPath": "$DATA_DIR/TarotSpreadsheet2.ods",
    "LegacySpreadsheetPath": "$DATA_DIR/CardImages.ods",
    "ComfyUIDir": "$COMFYUI_DIR",
    "ComfyUIAPI": "http://127.0.0.1:8188",
    "OllamaAPI": "http://127.0.0.1:11434"
}
CONF
    ok "Generated $CONFIG_PATH"
    INSTALLED+=("config.json")
else SKIPPED+=("config.json"); fi

# ── Phase 8: Summary ────────────────────────────────────────────────────────

section "Summary"

if [[ ${#INSTALLED[@]} -gt 0 ]]; then
    echo -e "\n  ${GREEN}Installed:${NC}"
    for i in "${INSTALLED[@]}"; do echo -e "    ${GREEN}+ $i${NC}"; done
fi
if [[ ${#SKIPPED[@]} -gt 0 ]]; then
    echo -e "\n  ${YELLOW}Skipped:${NC}"
    for s in "${SKIPPED[@]}"; do echo -e "    ${YELLOW}- $s${NC}"; done
fi

echo -e "\n  ${CYAN}Next steps:${NC}"
echo "    1. Start ComfyUI:  cd $COMFYUI_DIR && python main.py"
echo '    2. Start n8n with required flags:'
echo '       NODE_FUNCTION_ALLOW_BUILTIN=* NODE_FUNCTION_ALLOW_EXTERNAL=* N8N_RUNNERS_TASK_TIMEOUT=28800 n8n start'
echo "    3. Import n8n workflows from the n8n/ folder"
echo "    4. Import ComfyUI workflows from the ComfyUI/ folder"
echo ""
