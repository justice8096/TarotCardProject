# Tarot Card Project

A tarot card layout, spread, and reader system. Differs from Rider-Waite by having more cards, compatible with both I-Ching balance model and Tarot action model.

## Tools & Stack

- **ComfyUI** — image and video generation workflows
- **n8n** — orchestration and automation
- **Perplexity** — research
- **TypeScript**

## Directory Structure

```
ComfyUI/           ComfyUI GUI workflow JSONs (Card_Dealer_*.json, Make_Images_For_Card.json, etc.)
n8n/               n8n orchestration workflow JSONs (Generate Dealer Animations.json, Generate Card Tarot Images.json, etc.)
data/              TarotSpreadsheet2.ods (card definitions)
Perplexity/        Research docs
```

## Data Paths

- Card images: `D:/data/cards/Standard/`
- Card back image: `D:/data/cards/Standard/IMAGE_Deck_Back.png`
- Dealer animations output: `D:/data/Dealer_Animations/`
- Tarot spreadsheet: `data/TarotSpreadsheet2.ods`

## ComfyUI Installation

- **Path**: `D:/ComfyUI_windows_portable/ComfyUI/`
- **Hardware**: 6GB VRAM, 32GB system RAM
- **LoadImage input dir**: `D:/ComfyUI_windows_portable/ComfyUI/input/` (images must be copied here for LoadImage node)
- **API endpoint**: `http://127.0.0.1:8188/prompt` (POST), `http://127.0.0.1:8188/history/{prompt_id}` (GET)

### Custom Nodes Installed

| Node Pack | Status | Notes |
|-----------|--------|-------|
| ComfyUI-VideoHelperSuite | Working | VHS_VideoCombine for MP4 output |
| FramePack-F1-T2V | Broken | No model loader produces FramePackMODEL type |
| FramePack-HY | No models | diffusers/ folder is empty, needs HunyuanVideo model download |

### Custom Nodes NOT Installed

- **AnimateDiff** (ComfyUI-AnimateDiff-Evolved) — do NOT generate workflows using AnimateDiff nodes

## Available Models (Wan 2.2 I2V)

All paths relative to `D:/ComfyUI_windows_portable/ComfyUI/`:

| Model | Path |
|-------|------|
| Wan 2.2 I2V high noise (14B fp8) | `models/diffusion_models/wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors` |
| Wan 2.2 I2V low noise (14B fp8) | `models/diffusion_models/wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors` |
| LightX2V 4-step LoRA (high noise) | `models/loras/wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors` |
| umt5_xxl text encoder (fp8) | `models/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors` |
| CLIP-L | `models/text_encoders/clip_l.safetensors` |
| Wan 2.1 VAE | `models/vae/wan_2.1_vae.safetensors` |

## Critical Compatibility Notes

These were discovered through debugging — do not repeat these mistakes:

1. **AnimateDiff is NOT installed** — don't use AnimateDiff nodes in any workflow
2. **DualCLIPLoader does NOT support type "wan"** — valid types: sdxl, sd3, flux, hunyuan_video, hidream, hunyuan_image, hunyuan_video_15, kandinsky5, kandinsky5_image, ltxv, newbie
3. **CLIPLoader (single) DOES support type "wan"** — Wan only needs one text encoder (umt5_xxl), not two
4. **FramePack F1-T2V and FramePack HY are incompatible** — they use different types (FramePackMODEL vs FP_DIFFUSERS_PIPELINE), cannot interoperate
5. **Card back image filename**: `IMAGE_Deck_Back.png` (not `CardBack.png`)
6. **ComfyUI GUI JSON vs API JSON**: GUI format uses `nodes[]` and `links[]` arrays with numeric IDs; API format uses `prompt` object with string node IDs ("1", "2", ...) containing `class_type` and `inputs`
7. **`WanImageToVideo` does NOT accept `end_image`** — it only supports `start_image`. For start+end frame pinning (stop-motion interpolation), use **`WanFirstLastFrameToVideo`** instead. It accepts both `start_image` and `end_image` as optional inputs with the same interface, and works with the same Wan 2.2 I2V model.

## Dealer Animation Workflows (Wan 2.2 I2V)

Four animations: Cut, Fan, Merge, Rotate. All share the same node graph, differing only in prompts and output filenames.

### Node Chain

```
UNETLoader(1) → LoraLoaderModelOnly(8) → ModelSamplingSD3(9) → KSampler(10)
CLIPLoader(2) → CLIPTextEncode(4,5) → WanImageToVideo(7) → KSampler(10)
VAELoader(3) → WanImageToVideo(7) + VAEDecode(11)
LoadImage(6) → WanImageToVideo(7)
KSampler(10) → VAEDecode(11) → VHS_VideoCombine(12)
```

### Key Settings

- **KSampler**: steps=4, cfg=1.0, sampler=uni_pc_bh2, scheduler=sgm_uniform, denoise=1.0
- **WanImageToVideo**: width=480, height=832, length=81, batch_size=1
- **VHS_VideoCombine**: frame_rate=12, format=video/h264-mp4
- **ModelSamplingSD3**: shift=1.0 (flow matching)
- **LightX2V LoRA**: strength=1.0 (enables 4-step generation)

### n8n Orchestration

- Workflow: `n8n/Generate Dealer Animations.json`
- Pattern: Manual Trigger → Set Parameters → Build Animation List (Code) → HTTP POST to ComfyUI → Wait 300s → GET Status
- Each animation type gets its own prompt and output filename via template variables

---

## Workflow Design Philosophy

These principles apply to **all** n8n flows in this project. Follow them in every new flow and every refactor.

### Core Goal: Accessibility Across Skill Levels

This project is designed so that contributors need expertise in **only one area** to participate:

| Role | What they touch | What they don't need to know |
|------|----------------|------------------------------|
| **Artist / Prompt Engineer** | `Deck.json` — prompts, negative prompts, model names | n8n, ComfyUI API, code |
| **Technical Director** | `Deck.json` — geometry, paths, sampler settings | Art, prompt craft |
| **Workflow Developer** | n8n flow JSON | Art direction, specific model names |
| **ComfyUI Specialist** | ComfyUI workflow graph inside HTTP body | n8n, business logic |

### Design Principles

#### 1. Deck.json is the single source of truth
Every deck-specific value lives in `Deck.json`. No deck names, model names, paths, dimensions, prompts, or sampler settings are hardcoded in the n8n flow. This means the **same flow works for any deck** — just change `DeckJsonPath` in Set Global Parameters.

#### 2. Safe defaults — never hard-fail on optional sections
Optional sections (`Models`, `Samplers`) have built-in fallbacks so a deck author only needs to fill in the required sections (`Assets`, `Geometries`, `Prompts`). Example pattern:
```javascript
const models = deck.Models || {};
const checkpoint = models.KeyframeCheckpoint || 'dreamshaper_8.safetensors';
```

#### 3. Completeness — each flow is self-contained
Every flow must be importable and runnable with only `DeckJsonPath` changed. No hidden dependencies on data from other flows except through the Deck.json file.

#### 4. Sequential processing with self-contained Code nodes (not SplitInBatches loops)

**Do NOT use SplitInBatches (Loop Over Items) for ComfyUI submit→poll workflows.**
The "done" output of SplitInBatches sends the original input items — not the enriched loop-back items with fields added during the loop (e.g. `SavedFilename`, `SavedPath`). This causes the next stage to silently receive incomplete data.

**Use a single self-contained Code node** that loops over all jobs internally, submits each one, polls until done, and returns all results at once:

```javascript
const axios = require('axios');
const allJobs = $input.all().map(item => item.json);
const sleep = ms => new Promise(r => setTimeout(r, ms));
const results = [];

for (const job of allJobs) {
  // submit to ComfyUI
  const submitRes = await axios.post(comfyUIAPI + '/prompt', { prompt: comfyPrompt });
  const promptId = submitRes.data.prompt_id;

  // poll until done
  let done = false;
  for (let attempt = 0; attempt < 60 && !done; attempt++) {
    await sleep(3000);
    const historyRes = await axios.get(comfyUIAPI + '/history/' + promptId);
    const entry = historyRes.data[promptId];
    if (entry?.outputs?.['7']?.images?.length > 0) {
      results.push({ ...job, SavedFilename: entry.outputs['7'].images[0].filename });
      done = true;
    }
  }
  if (!done) throw new Error('Timeout: ' + job.OutputPrefix);
}
return results.map(r => ({ json: r }));
```

#### 5. Informative errors, not silent failures
Every Code node that can produce zero output must throw an Error with a message that tells the user exactly what to fix:
```javascript
if (jobs.length === 0) {
  throw new Error(
    '[Build Keyframe Job List] No jobs created. ' +
    'Check that AnimationTypes matches keys in Deck.json Prompts.'
  );
}
```
Warnings for skipped (but non-fatal) conditions use `console.warn()`.

#### 6. Insertable / overridable assets
Future flows should check for manually placed assets before generating. The convention:
- Named `KF_<AnimType>_<Index>.png` for keyframes
- Named `<AnimType>_back.png` for card backs
- Placed in the deck's `Assets.Directory` or `Assets.AnimationKeyframes` folder
- If found, skip generation and use the existing file

This lets an artist drop a hand-crafted image in place of a generated one without touching any code or flow.

### Deck.json Schema

#### Required
```json
{
  "Assets": {
    "Directory": "D:/data/cards/MyDeck",
    "AnimationKeyframes": "D:/data/cards/MyDeck/keyframes",
    "Cut":    "D:/data/cards/MyDeck/animations/cut.mp4",
    "Fan":    "D:/data/cards/MyDeck/animations/fan.mp4",
    "Merge":  "D:/data/cards/MyDeck/animations/merge.mp4",
    "Rotate": "D:/data/cards/MyDeck/animations/rotate.mp4"
  },
  "Geometries": {
    "Animation": { "Width": 512, "Height": 896, "FrameRate": 24, "InterpolationFrames": 25 }
  },
  "Prompts": {
    "Cut": {
      "Negative": "bad quality, blurry, distorted",
      "Keyframes": ["frame 1 positive prompt", "frame 2 positive prompt"]
    }
  }
}
```

#### Optional (safe defaults built-in)
```json
{
  "Models": {
    "KeyframeCheckpoint": "dreamshaper_8.safetensors",
    "InterpolationUNet":  "wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors",
    "InterpolationCLIP":  "umt5_xxl_fp8_e4m3fn_scaled.safetensors",
    "InterpolationVAE":   "wan_2.1_vae.safetensors"
  },
  "Samplers": {
    "Keyframe":      { "Steps": 20, "CFG": 7.0, "Denoise": 1.0, "Sampler": "dpmpp_2m",    "Scheduler": "karras"      },
    "Interpolation": { "Steps": 20, "CFG": 7.0, "Denoise": 1.0, "Shift":  3.0, "Sampler": "uni_pc_bh2", "Scheduler": "sgm_uniform" }
  }
}
```

### n8n Data Flow Conventions

- After `Extract from File` (fromJson), parsed content is under `.data`: `$input.first().json.data`
- Cross-node references use `.first()` for single items: `$('NodeName').first().json`
- Accumulate all items with `$input.all()` at aggregation points (Build Interpolation Job List, Build FFmpeg Concat Commands)
- Job items carry **all** fields needed downstream — avoid repeated cross-node references inside loops
- ComfyUI Submit nodes output only `{prompt_id, number, node_errors}` — merge with job data in the Capture node

---

## n8n Code Node Sandbox Restrictions (v2.7.5)

These apply to **all Code nodes** in n8n. Test environment: n8n 2.7.5, self-hosted on Windows.

### What is blocked by default

| API | Error | Status |
|-----|-------|--------|
| `fetch()` | `fetch is not defined` | Blocked — global not available |
| `require('http')` | `Module 'http' is disallowed` | Blocked — built-in HTTP modules |
| `require('https')` | `Module 'https' is disallowed` | Blocked — built-in HTTP modules |
| `$helpers.httpRequest()` | `$helpers is not defined` | Not available in Code nodes (only in custom node SDK) |

### What works

| API | How to enable | Notes |
|-----|---------------|-------|
| `require('axios')` | Set `NODE_FUNCTION_ALLOW_EXTERNAL=*` | Ships bundled with n8n; cleanest HTTP option |
| `require('fs')` | Set `NODE_FUNCTION_ALLOW_BUILTIN=*` | File read/write/copy operations |
| `require('path')` | Set `NODE_FUNCTION_ALLOW_BUILTIN=*` | Path joining |
| `require('child_process')` | Set `NODE_FUNCTION_ALLOW_BUILTIN=*` | Run shell commands (replaces Execute Command node) |

### Required n8n startup flags

```cmd
set NODE_FUNCTION_ALLOW_BUILTIN=* && set NODE_FUNCTION_ALLOW_EXTERNAL=* && set N8N_RUNNERS_TASK_TIMEOUT=28800 && n8n start
```

| Flag | Purpose | Default | Required value |
|------|---------|---------|---------------|
| `NODE_FUNCTION_ALLOW_BUILTIN` | Allows `fs`, `path`, `child_process` etc. in Code nodes | restricted | `*` |
| `NODE_FUNCTION_ALLOW_EXTERNAL` | Allows npm packages like `axios` in Code nodes | restricted | `*` |
| `N8N_RUNNERS_TASK_TIMEOUT` | Max seconds a single Code node task may run | **300** | `28800` (8 hrs) |

**Why 28800?** Wan 2.2 I2V (14B fp8) on 6GB VRAM takes 10–30 min per clip. 8 interpolation pairs × 30 min = 240 min worst case. The Code node runs ALL clips in one task, so the task timeout must cover the full batch (28800s = 8 hrs).

**Common mistakes:**
- `ODE_FUNCTION_ALLOW_EXTERNAL` (missing leading `N`) — silently ignored
- Single quotes in Windows `set`: `set FOO='bar'` sets value to `'bar'` including the quotes

### Execute Command node is unavailable

`n8n-nodes-base.executeCommand` is unrecognized in this n8n 2.7.5 setup. **Replace with a Code node using `child_process`:**

```javascript
const { execSync }  = require('child_process');
const fs            = require('fs');
const path          = require('path');

// Write any input files needed
fs.mkdirSync(path.dirname(outputPath), { recursive: true });
fs.writeFileSync(inputFilePath, content, 'utf8');

// Run the command
try {
  execSync(`ffmpeg -y -f concat -safe 0 -i "${listPath}" -c copy "${outputPath}"`,
           { encoding: 'utf8' });
} catch (e) {
  throw new Error('Command failed: ' + (e.stderr || e.message));
}
```

---

## Generate Dealer Stop Motion — Current Architecture

```
Set Global Parameters
  └─ Read Deck.json → Parse Deck.json → Build Keyframe Job List (N items)
       └─ Generate All Keyframes (Code: axios loop, submit+poll each job)
            └─ Build Interpolation Job List
                 └─ Generate All Interpolations (Code: axios+fs loop, copy+submit+poll each pair)
                      └─ Build FFmpeg Concat Commands
                           └─ FFmpeg Concat Clips (Code: fs+child_process, write list+run ffmpeg)
                                └─ Report Results
```

