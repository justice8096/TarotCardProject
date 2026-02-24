# Tarot Card Project — Installation Guide

This project uses **n8n** to orchestrate AI pipelines, **ComfyUI** for image and video generation, and **Python** for image compositing. Everything is driven by a single `Deck.json` file — no code changes needed to create a new deck.

---

## Prerequisites

| Tool | Version | Download |
|------|---------|----------|
| **Python** | 3.10+ | https://python.org — check "Add to PATH" during install |
| **Node.js** | 20+ (LTS) | https://nodejs.org |
| **Git** | Any | https://git-scm.com |
| **FFmpeg** | Any recent | https://ffmpeg.org/download.html — add `bin/` folder to PATH |
| **ComfyUI** | Latest portable | https://github.com/comfyanonymous/ComfyUI/releases |
| **GPU** | NVIDIA, 6GB+ VRAM | AMD/CPU may work with different model quantisations |

---

## Quick Start

```bat
git clone https://github.com/justice8096/TarotCardProject.git
cd TarotCardProject
setup.bat
```

`setup.bat` will:
- Verify all prerequisites
- Install Python packages (`Pillow`, `PyJWT`, `requests`)
- Install n8n globally via npm
- Create required data directories under `D:\data\cards\Standard\`
- Create `start_n8n.bat` (already included in the repo)
- Report any missing AI models

---

## Directory Layout

```
TarotCardProject/
├── CLAUDE.md                  ← Claude Code project context (AI assistant notes)
├── INSTALL.md                 ← This file
├── setup.bat                  ← One-time setup script
├── start_n8n.bat              ← Run this every time to launch n8n
├── n8n/                       ← n8n workflow JSON files
│   ├── Generate Dealer Stop Motion.json
│   ├── Normalize Deck Structure.json
│   └── ...
├── ComfyUI/                   ← ComfyUI workflow JSON files
│   ├── Make_Deck_Front_Transparent.json
│   ├── Make_Symmetric_Card.json
│   └── ...
└── data/                      ← Reference data (spreadsheets, docs)

D:\data\cards\Standard\        ← Runtime data (created by setup.bat)
├── Deck.json                  ← Your deck definition (prompts, paths, geometry)
├── IMAGE_Deck_Back.png        ← Card back artwork
├── IMAGE_Deck_Front.png       ← Card front artwork
├── Keyframes\                 ← Manually placed keyframe PNGs (optional overrides)
│   ├── KF_Cut_0.png
│   ├── KF_Fan_2.png
│   └── ...
├── CUT_Deck.mp4               ← Output animations
├── FAN_Deck.mp4
├── MERGE_Deck.mp4
└── ROTATE_Deck.mp4

D:\ComfyUI_windows_portable\   ← ComfyUI installation
└── ComfyUI\
    ├── models\
    │   ├── diffusion_models\  ← Wan 2.2 I2V models go here
    │   ├── text_encoders\     ← umt5_xxl goes here
    │   ├── vae\               ← wan_2.1_vae goes here
    │   └── checkpoints\       ← dreamshaper_8 goes here
    └── input\                 ← ComfyUI reads images from here (auto-managed)
```

---

## ComfyUI Setup

### 1. Install ComfyUI

Download the **Windows portable** from the [releases page](https://github.com/comfyanonymous/ComfyUI/releases), extract to `D:\ComfyUI_windows_portable\`.

### 2. Install required custom nodes

Open ComfyUI → Manager → Install Custom Nodes:

| Node Pack | Why needed |
|-----------|-----------|
| **ComfyUI-VideoHelperSuite** | `VHS_VideoCombine` — saves interpolation clips as MP4 |

Do **not** install AnimateDiff — it is not used and conflicts with this workflow.

### 3. Download AI models

All models go in `D:\ComfyUI_windows_portable\ComfyUI\models\`.

#### Wan 2.2 I2V (video interpolation) — required

| File | Folder | Use | Source |
|------|--------|-----|--------|
| `wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors` | `diffusion_models/` | Frame interpolation | [Hugging Face — Kijai/WanVideo_comfy](https://huggingface.co/Kijai/WanVideo_comfy/tree/main) |
| `wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors` | `diffusion_models/` | Scratch generation | Same |
| `umt5_xxl_fp8_e4m3fn_scaled.safetensors` | `text_encoders/` | Text encoder | Same |
| `wan_2.1_vae.safetensors` | `vae/` | VAE | Same |

> **Choose low-noise for interpolation, high-noise for generating from nothing.**
> See `CLAUDE.md` → "Wan 2.2 I2V Model Selection Guide" for details.

#### DreamShaper 8 (keyframe generation) — optional

Only needed if you want AI-generated keyframes (not manual card composites).

| File | Folder | Source |
|------|--------|--------|
| `dreamshaper_8.safetensors` | `checkpoints/` | [Civitai — DreamShaper](https://civitai.com/models/4384/dreamshaper) |

### 4. Start ComfyUI

```bat
D:\ComfyUI_windows_portable\run_nvidia_gpu.bat
```

ComfyUI runs at `http://127.0.0.1:8188`.

---

## n8n Setup

### 1. Start n8n

Always use `start_n8n.bat` — it sets the required environment variables:

```bat
start_n8n.bat
```

Then open `http://localhost:5678` and complete the first-run account setup.

> **Why the environment variables matter:**
> - `NODE_FUNCTION_ALLOW_BUILTIN=*` — lets Code nodes use `fs`, `path`, `child_process`
> - `NODE_FUNCTION_ALLOW_EXTERNAL=*` — lets Code nodes use `axios`
> - `N8N_RUNNERS_TASK_TIMEOUT=28800` — 8 hours; Wan 2.2 14B takes 10–30 min per clip and all clips run in one Code node task

### 2. Import workflows

In n8n: **Workflows → Import from file**, then import each JSON from the `n8n/` folder:

| Workflow | Purpose |
|----------|---------|
| `Generate Dealer Stop Motion.json` | Main pipeline: keyframes → video interpolation → MP4s |
| `Normalize Deck Structure.json` | Utility: validate and fill missing fields in Deck.json |

### 3. Configure the deck path

Open **Generate Dealer Stop Motion** → **Set Global Parameters** node → set `DeckJsonPath` to your `Deck.json` path (default: `D:/data/cards/Standard/Deck.json`).

---

## Deck.json — Minimal Configuration

Create `D:\data\cards\Standard\Deck.json`:

```json
{
  "data": {
    "Name": "Standard",
    "Assets": {
      "Directory":          "D:\\data\\cards\\Standard",
      "AnimationKeyframes": "D:\\data\\cards\\Standard\\Keyframes",
      "BackImage":          "D:\\data\\cards\\Standard\\IMAGE_Deck_Back.png",
      "FrontImage":         "D:\\data\\cards\\Standard\\IMAGE_Deck_Front.png",
      "Cut":    "D:\\data\\cards\\Standard\\CUT_Deck.mp4",
      "Fan":    "D:\\data\\cards\\Standard\\FAN_Deck.mp4",
      "Merge":  "D:\\data\\cards\\Standard\\MERGE_Deck.mp4",
      "Rotate": "D:\\data\\cards\\Standard\\ROTATE_Deck.mp4"
    },
    "Geometries": {
      "Animation": {
        "Width": 832, "Height": 480,
        "FrameRate": 12, "InterpolationFrames": 13
      }
    },
    "Models": {
      "InterpolationUNet": "wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors",
      "InterpolationCLIP": "umt5_xxl_fp8_e4m3fn_scaled.safetensors",
      "InterpolationVAE":  "wan_2.1_vae.safetensors",
      "KeyframeCheckpoint": "dreamshaper_8.safetensors"
    },
    "Samplers": {
      "Interpolation": {
        "Steps": 20, "CFG": 7.0, "Shift": 1.0,
        "Sampler": "uni_pc_bh2", "Scheduler": "sgm_uniform", "Denoise": 1.0
      }
    },
    "Prompts": {
      "Cut": {
        "Negative": "blurry, low quality, distorted, watermark, text, deformed hands, extra fingers, CGI, 3D render, cartoon",
        "Keyframes": [
          "a complete deck of tarot cards resting face-down on dark green felt, papyrus-textured card backs, soft warm studio lighting",
          "two hands splitting a tarot deck on dark green felt, left hand holding top half lifted slightly, right hand holding bottom half",
          "two hands completing a cut, top half of tarot deck placed face-down beside bottom half on dark green felt"
        ]
      },
      "Fan": {
        "Negative": "blurry, low quality, distorted, watermark, text, deformed hands, extra fingers, CGI, 3D render, cartoon",
        "Keyframes": [
          "a complete tarot deck held square in two hands above dark green felt, papyrus-textured card backs",
          "two hands spreading a tarot deck into a partial arc on dark green felt, cards fanning left to right",
          "a full tarot deck fanned into a wide elegant arc on dark green felt, all papyrus-textured card backs visible"
        ]
      },
      "Merge": {
        "Negative": "blurry, low quality, distorted, watermark, text, deformed hands, extra fingers, CGI, 3D render, cartoon",
        "Keyframes": [
          "two halves of a tarot deck held apart in two hands above dark green felt, papyrus-textured card backs",
          "two hands performing a riffle shuffle, thumbs releasing alternating tarot cards from each half, cards beginning to interleave",
          "two hands pressing a freshly shuffled tarot deck flat on dark green felt, papyrus-textured card backs"
        ]
      },
      "Rotate": {
        "Negative": "blurry, low quality, distorted, watermark, text, deformed hands, extra fingers, CGI, 3D render, cartoon",
        "Keyframes": [
          "a single tarot card lying face-down on dark green felt, papyrus-textured card back, soft warm studio lighting",
          "a single tarot card mid-rotation on dark green felt, card at 45-degree angle, papyrus-textured card back",
          "a single tarot card rotated 180 degrees on dark green felt, now face-up, ornate card front design"
        ]
      }
    }
  }
}
```

---

## Manual Keyframes (Recommended)

Instead of letting AI generate keyframes, drop pre-composited PNG files into the Keyframes folder. The workflow detects them automatically and skips AI generation for that position.

**Naming convention:** `KF_{AnimType}_{Index}.png` — e.g. `KF_Rotate_0.png`

**Canvas size:** exactly **832 × 480 px**

To generate all keyframes from your own card art using the compositing script:

```python
# Run from repo root — requires Pillow
python make_keyframes.py
```

> See `CLAUDE.md` → "Stop-Motion Keyframe Compositing (Python PIL)" for the full script
> and geometry reference.

---

## Running the Animation Pipeline

1. Make sure ComfyUI is running (`http://127.0.0.1:8188`)
2. Make sure n8n is running (`start_n8n.bat` → `http://localhost:5678`)
3. In n8n, open **Generate Dealer Stop Motion**
4. Click **▶ Execute workflow**
5. Watch the execution log — each stage lights up as it completes
6. Output MP4s appear in `D:\data\cards\Standard\` after ~30 minutes

---

## Using This Repo as a Template with Claude Code

This project is structured so Claude Code can work on it autonomously using the `CLAUDE.md` file at the repo root.

### For contributors using Claude Code

1. Clone the repo and open the folder in VS Code (or run `claude` in the terminal from the repo root)
2. Claude Code automatically reads `CLAUDE.md` on startup — no extra setup needed
3. All project-specific context (tool quirks, model names, API patterns, design principles) is in `CLAUDE.md`

### For creating your own deck

1. Click **Use this template** on GitHub (or fork the repo)
2. Run `setup.bat`
3. Replace `IMAGE_Deck_Back.png` and `IMAGE_Deck_Front.png` with your own card art
4. Edit `Deck.json` to update prompts for your art style
5. Run `make_keyframes.py` to generate composited keyframes from your card art
6. Run the n8n animation pipeline

### Making GitHub recognise this as a template

In the GitHub repo → **Settings** → scroll to **Template repository** → enable the checkbox.
Anyone can then use **"Use this template"** to start their own deck.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `fetch is not defined` in n8n Code node | Use `axios` instead; make sure n8n started with `NODE_FUNCTION_ALLOW_EXTERNAL=*` |
| `Module 'fs' is disallowed` | Start n8n with `NODE_FUNCTION_ALLOW_BUILTIN=*` |
| Code node times out after 5 minutes | Start n8n with `N8N_RUNNERS_TASK_TIMEOUT=28800` |
| ComfyUI clips look noisy / unrecognisable | Switch to `wan2.2_i2v_low_noise` and set `Shift: 1.0` in Deck.json |
| `WanImageToVideo` crashes with `end_image` error | Replace with `WanFirstLastFrameToVideo` — the only node that accepts both start and end frames |
| n8n PUT workflow returns HTTP 400 | Remove all settings fields except `executionOrder` from the PUT body |
| Random people appear in generated keyframes | Add `person, woman, man, face, portrait` to the Negative prompt, or supply manual keyframe PNGs |
