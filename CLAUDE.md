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

---

## n8n Internal API — Authentication & Triggering

The n8n public API (`/api/v1/`) accepts `X-N8N-API-KEY` from the `user_api_keys` table but **cannot trigger manual executions** (405 Method Not Allowed).

The internal REST API (`/rest/workflows/{id}/run`) requires a **session JWT cookie** (`n8n-auth`).

### Deriving the JWT secret

```python
import hashlib, base64, jwt

# encryptionKey is in ~/.n8n/config  →  {"encryptionKey": "..."}
enc_key = 'gCCaoBEhmsTnlQ3BLfwV2iFL1VUBV5Pt'      # from ~/.n8n/config
base_key = ''.join(enc_key[i] for i in range(0, len(enc_key), 2))   # every other char
jwt_secret = hashlib.sha256(base_key.encode()).hexdigest()
```

### Deriving the `hash` field

```python
# email and password (bcrypt hash) come from the `user` table in ~/.n8n/database.sqlite
payload_str = f'{email}:{bcrypt_password_hash}'
hash_b64 = base64.b64encode(hashlib.sha256(payload_str.encode()).digest()).decode()
jwt_hash = hash_b64[:10]   # first 10 chars of base64(SHA256(email:bcrypt_hash))
```

### Building and using the token

```python
token = jwt.encode({'id': user_id, 'hash': jwt_hash, 'usedMfa': False},
                   jwt_secret, algorithm='HS256')
# Use as:  Cookie: n8n-auth=<token>
```

### Triggering a manual-trigger workflow

The `/rest/workflows/{id}/run` body must include `workflowData` (full workflow object with `id`).
Use `triggerToStartFrom` to select the manual trigger node — this hits the `isFullExecutionFromKnownTrigger` branch and avoids the partial-execution `destinationNode.nodeName` access:

```python
run_payload = {
    'workflowData': wf_data,   # full object from GET /rest/workflows/{id}
    'pinData': {},
    'triggerToStartFrom': {
        'name': 'When clicking \'Execute workflow\'',
        'data': {'main': [[{'json': {}}]]}
    }
}
```

**Do NOT include `runData` or `destinationNode: null`** — that routes into the partial-execution
code path which crashes with `Cannot read properties of null (reading 'nodeName')`.

### n8n PUT workflow restriction

`PUT /api/v1/workflows/{id}` only accepts these fields in `settings`:
```json
{ "settings": { "executionOrder": "v1" } }
```
Adding `binaryMode` or `availableInMCP` causes HTTP 400:
`"request/body/settings must NOT have additional properties"`.

---

## Wan 2.2 I2V Model Selection Guide

| Use case | Model | Shift |
|----------|-------|-------|
| Generating video from scratch (no start image) | `wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors` | 3.0 |
| Interpolating between two anchor frames | `wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors` | 1.0 |

**Why this matters:** The high-noise model is trained for near-pure-noise starting conditions. When used for frame-to-frame interpolation (where start and end frames are provided), it treats the images as weak hints and generates mostly from noise — producing blurry, unrecognisable results.

The low-noise model stays close to the input images. Combined with `Shift=1.0` (keeps the ModelSamplingSD3 sampler away from the high-noise regime), the interpolated frames maintain the visual design of the anchor images throughout.

**In Deck.json:**
```json
"Models": {
  "InterpolationUNet": "wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors"
},
"Samplers": {
  "Interpolation": { "Steps": 20, "CFG": 7.0, "Shift": 1.0,
                     "Sampler": "uni_pc_bh2", "Scheduler": "sgm_uniform" }
}
```

`Shift` tuning: `0.5` = very rigid (hugs input frames), `2.0` = more creative motion.

---

## Stop-Motion Keyframe Compositing (Python PIL)

### The problem solved

If only some keyframe positions have manual inserts, the AI generates the rest without access to the real card design. Since WanFirstLastFrameToVideo anchors **both ends** of a segment, ALL keyframe positions must use real card images for the design to be visible throughout the full animation.

The "random person/girl appears in Merge" bug was caused by dreamshaper_8 misinterpreting the riffle-shuffle prompt. Replacing ALL keyframes with composites bypasses dreamshaper entirely.

### Convention

- Keyframe images: `D:/data/cards/Standard/Keyframes/KF_{AnimType}_{Index}.png`
- Canvas size: **832 × 480 px** (matches `Geometries.Animation.Width/Height`)
- Background: dark green felt `#0F3C14` = `(15, 60, 20)`
- Source images: `IMAGE_Deck_Back.png` (680×1088 RGBA), `IMAGE_Deck_Front.png` (680×1096 RGBA)

### Reference keyframe layouts (Standard deck)

| File | Contents |
|------|----------|
| `KF_Cut_0.png` | Complete deck stack (10 cards, card back) centred |
| `KF_Cut_1.png` | Two half-stacks of 5 separated (top half left/raised, bottom half right/lower) |
| `KF_Cut_2.png` | Reassembled deck stack (same as frame 0) |
| `KF_Fan_0.png` | Deck stack (card back) |
| `KF_Fan_1.png` | Partial fan — 12 cards, −28° to +28°, pivot 280px below canvas |
| `KF_Fan_2.png` | Full fan — 22 cards, −58° to +58°, pivot 280px below canvas |
| `KF_Merge_0.png` | Two stacks of 5 at W/4 and 3W/4 (far apart) |
| `KF_Merge_1.png` | Two stacks of 5 at W/2±80 (about to interleave) |
| `KF_Merge_2.png` | Single merged deck stack of 10 |
| `KF_Rotate_0.png` | Single large card (255px wide) face-down (card back) |
| `KF_Rotate_1.png` | Card squeezed to ~12% width (edge-on, mid-flip) |
| `KF_Rotate_2.png` | Single large card face-up (card front) |

### Core Python functions

```python
from PIL import Image
import math, os

W, H = 832, 480
FELT = (15, 60, 20, 255)

def scale_card(img, w):
    return img.resize((w, int(img.height * w / img.width)), Image.LANCZOS)

def make_canvas():
    return Image.new('RGBA', (W, H), FELT)

def clip_paste(canvas, img, cx, cy):
    """Alpha-composite img centred at (cx,cy), clipping to canvas."""
    px, py = cx - img.width//2, cy - img.height//2
    sx0,sy0 = max(0,-px), max(0,-py)
    sx1,sy1 = min(img.width,W-px), min(img.height,H-py)
    dx, dy = max(0,px), max(0,py)
    if sx0 < sx1 and sy0 < sy1:
        canvas.alpha_composite(img.crop((sx0,sy0,sx1,sy1)), (dx,dy))

def darken(img, f):
    r,g,b,a = img.split()
    return Image.merge('RGBA', (r.point(lambda p:int(p*f)),
                                g.point(lambda p:int(p*f)),
                                b.point(lambda p:int(p*f)), a))

def draw_stack(canvas, card, cx, cy, n, dx=2, dy=-1):
    """n-card stack. Top card at (cx,cy); deeper cards offset by (dx,dy).
    Draw order: bottom→top so top card is on top visually."""
    for i in range(n-1, -1, -1):   # i=0 → top, i=n-1 → bottom
        clip_paste(canvas, darken(card, max(0.60, 1.0 - i*0.038)), cx+i*dx, cy+i*dy)

def draw_fan(canvas, card, pivot_x, pivot_y, n, a0, a1, radius):
    """n cards in an arc; centres at `radius` from (pivot_x, pivot_y)."""
    for i in range(n):
        t = i / max(n-1, 1)
        angle = a0 + t*(a1-a0)
        ar = math.radians(angle)
        cx = int(pivot_x + radius * math.sin(ar))
        cy = int(pivot_y - radius * math.cos(ar))
        rot = card.rotate(-angle, expand=True, resample=Image.BICUBIC)
        clip_paste(canvas, rot, cx, cy)
```

### Recommended card sizes

| Usage | Width | Approx height |
|-------|-------|---------------|
| Stack cards (Cut/Merge) | 95 px | 152 px |
| Fan cards | 60 px | 96 px |
| Single large card (Rotate) | 255 px | 408 px |

### Fan geometry note

With `pivot_y = H + 280 = 760` and `radius = 340`:
- Angle 0°: card centre at y = 760−340 = 420 (near bottom of canvas) ✓
- Angle ±58°: card centre at x ≈ 128 or 704 (within 832px canvas) ✓
- Extreme-angle cards clip at bottom edge naturally — this looks realistic.

---

## Card Narration — Local TTS via ComfyUI Orpheus

### Architecture

```
Set Global Parameters
  └─ Read Deck.json → Parse Deck.json → Build Narration Job List (N items per card×orientation)
       └─ Generate All Narrations (Code: axios loop, submit+poll each job, copy to NarrationDirectory)
            └─ Report Results
```

**n8n workflow**: `n8n/Generate Card Narrations.json`

### TTS Engine: Orpheus TTS

| Node | Class | Purpose |
|------|-------|---------|
| `OrpheusModelLoader` | `OrpheusModelLoader` | Loads 3B LLM + SNAC 24kHz decoder |
| `OrpheusGenerate` | `OrpheusGenerate` | Generates speech → ComfyUI `AUDIO` |
| `SaveAudioMP3` | `SaveAudioMP3` | Saves to `output/<subfolder>/<filename>.mp3` |

History polling key: `outputs['3'].audio[0]` (has `.filename` and `.subfolder`).

**Why Orpheus over TTS Audio Suite:** Orpheus is self-contained (no reference audio files needed), uses named voices that map naturally to card personalities, and supports emotional elements (sigh, gasp) suited to tarot narration.

### Deck.json Narration Schema

#### Required (add to `Prompts.Narration`)
```json
{
  "Prompts": {
    "Narration": {
      "Voice": "Female",
      "Tone": "Mysterious and Kind",
      "DefaultVoice": "tara",
      "DefaultElement": "none",
      "VoiceMap": {
        "Female": "tara",   "Male": "leo",        "Neutral": "zac",
        "Young Female": "jess", "Young Male": "dan",
        "Mature Female": "leah", "Mature Male": "bob",
        "Warm Female": "mia",    "Mystical": "tara",  "Authoritative": "leo"
      },
      "ElementMap": {
        "Warm and uplifting": "none",  "Mysterious and Kind": "none",
        "Somber and reflective": "sigh", "Warning": "sigh", "Grief": "sigh",
        "Joyful": "none",  "Contemplative": "none",  "Surprised": "gasp"
      }
    }
  }
}
```

#### Required (add to `Models`)
```json
{
  "Models": {
    "NarrationTTS":  "canopylabs/orpheus-3b-0.1-ft",
    "NarrationSNAC": "hubertsiuzdak/snac_24khz"
  }
}
```

#### Required (add to `Samplers`)
```json
{
  "Samplers": {
    "Narration": {
      "Temperature": 0.6,
      "TopP": 0.95,
      "RepetitionPenalty": 1.1,
      "MaxNewTokens": 2700,
      "Quality": "128k"
    }
  }
}
```

#### Required (add to `Assets`)
```json
{
  "Assets": {
    "NarrationDirectory": "D:/data/cards/Standard/Narration"
  }
}
```

### Card JSON Structure

Each card JSON (e.g. `Cards/Ace_of_Cups.json`) has `data.Cards.records[]`. Each record has:
- `Orientation`: `"upright"`, `"reversed"`, or `"between"`
- `Description`: prose card meaning (used as narration body)
- `Advice`: actionable advice sentence
- `Affirmation`: affirmation text (multiline — newlines replaced with spaces)
- `Assets.Narration`: output filename e.g. `"NARRATION_Ace_of_Cups_upright.mp3"`
- `Prompts.Narration.Voice`: voice descriptor (e.g. `"Female"`) → VoiceMap → Orpheus voice
- `Prompts.Narration.Tone`: tone descriptor (e.g. `"Warm and uplifting"`) → ElementMap → element
- `Prompts.Narration.Content`: **LLM prompt guidance** (NOT the narration script; describes what to say)

### Script Assembly

The narration script is assembled from structured fields — **not** from `Prompts.Narration.Content` (which is LLM guidance, not spoken text):

```javascript
const script = [
  `${cardName}, ${orientation} position.`,
  record.Description,
  record.Advice ? `Advice: ${record.Advice}` : null,
  record.Affirmation ? record.Affirmation.replace(/\n/g, ' ') : null
].filter(Boolean).join(' ');
```

### Orpheus Voice Reference

| Voice | Character |
|-------|-----------|
| `tara` | Default female narrator — warm, clear |
| `leah` | Mature female — grounded, wise |
| `jess` | Young female — bright, energetic |
| `leo`  | Male narrator — authoritative |
| `dan`  | Young male — approachable |
| `mia`  | Warm female — nurturing |
| `zac`  | Neutral — balanced |
| `zoe`  | Female — expressive |
| `bob`  | Mature male — deep |
| `rebeca` | Female — dynamic |
| `lisa` | Female — calm |

Emotional elements: `none`, `laugh`, `chuckle`, `sigh`, `cough`, `sniffle`, `groan`, `yawn`, `gasp`
Element position: `none` (no element), `append` (after text), `prepend` (before text), `pipe` (replaces `|` chars in text)

### Insertable Narration Files

Drop a hand-crafted MP3 into `Assets.NarrationDirectory` matching the filename in `Assets.Narration` and the workflow will skip that card entirely.

Convention: `NARRATION_{CardName}_{orientation}.mp3` (e.g. `NARRATION_Ace_of_Cups_upright.mp3`)

### Performance Notes

- Orpheus 3B on 6GB VRAM: ~30–120s per card reading
- 246 jobs (82 cards × 3 orientations) = ~2–8 hours total
- Model stays in VRAM across consecutive ComfyUI queue items (no reload penalty)
- n8n Code node timeout must be ≥ 28800s — set via `N8N_RUNNERS_TASK_TIMEOUT=28800`
- Orpheus downloads models from HuggingFace on first run; subsequent runs use cached weights

